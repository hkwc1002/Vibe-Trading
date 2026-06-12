"""Workbench API for manual-execution Low Absorb state."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..data_provider import FixtureMarketDataProvider, IntradayBar
from ..models import (
    CloseReport,
    LowAbsorbSignal,
    ManualFill,
    ManualPosition,
    ManualTradePlan,
    PositionStatus,
    SignalStatus,
    TradePlanStatus,
)
from ..notifier import FeishuNotifier
from ..reconciler import ManualFillReconciler
from ..report import build_close_report
from ..risk import calculate_position_risk
from ..storage import InMemoryLowAbsorbStorage
from ..supervisor import build_position_risk_matrix, supervise_position_morning

router = APIRouter(prefix="/low-absorb", tags=["low-absorb"])
_STORAGE = InMemoryLowAbsorbStorage()


class ManualFillRequest(BaseModel):
    fill_id: str = Field(..., min_length=1)
    plan_id: str | None = None
    signal_id: str | None = None
    stock_code: str | None = None
    stock_name: str | None = None
    side: Literal["BUY", "SELL"] = "BUY"
    planned_price: Decimal | None = Field(default=None, gt=0)
    actual_price: Decimal | None = Field(default=None, gt=0)
    fill_price: Decimal | None = Field(default=None, gt=0)
    quantity: int = Field(..., gt=0)
    fee: Decimal = Field(default=Decimal("0"), ge=0)
    fees: Decimal = Field(default=Decimal("0"), ge=0)
    executed_at: datetime | None = None
    filled_at: datetime | None = None
    execution_note: str | None = None
    subjective_reason: str | None = None
    note: str = ""


class SignalPatchRequest(BaseModel):
    status: SignalStatus | None = None
    intercept_reasons: list[str] | None = None


class PositionPatchRequest(BaseModel):
    current_price: Decimal | None = Field(default=None, gt=0)
    current_stop_price: Decimal | None = Field(default=None, ge=0)
    status: PositionStatus | None = None
    note: str | None = None
    notes: list[str] | None = None


class PositionCloseRequest(BaseModel):
    closed_at: datetime | None = None
    note: str = ""


class PositionSupervisionRequest(BaseModel):
    trade_date: date
    observed_at: datetime
    open_price: Decimal = Field(..., gt=0)
    current_price: Decimal = Field(..., gt=0)
    industry_return: Decimal = Decimal("0")
    send_feishu: bool = False


def reset_workbench_state() -> None:
    """Clear process-local Low Absorb state for tests and local development."""

    _STORAGE.clear()


def seed_workbench_state(
    *,
    signals: list[LowAbsorbSignal] | None = None,
    trade_plans: list[ManualTradePlan] | None = None,
    fills: list[ManualFill] | None = None,
    positions: list[ManualPosition] | None = None,
) -> None:
    """Seed process-local state without connecting to any broker or backend store."""

    _STORAGE.seed(signals=signals, trade_plans=trade_plans, fills=fills, positions=positions)


def _get_plan(plan_id: str) -> ManualTradePlan:
    plan = _STORAGE.trade_plans.get(plan_id)
    if plan is None:
        raise HTTPException(status_code=404, detail="manual trade plan not found")
    return plan


def _replace_plan(plan: ManualTradePlan) -> ManualTradePlan:
    _STORAGE.trade_plans[plan.plan_id] = plan
    return plan


def _notifier() -> FeishuNotifier:
    return FeishuNotifier(storage=_STORAGE)


def _get_signal(signal_id: str) -> LowAbsorbSignal:
    signal = _STORAGE.signals.get(signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="signal not found")
    return signal


def _get_position(position_id: str) -> ManualPosition:
    position = _STORAGE.positions.get(position_id)
    if position is None:
        raise HTTPException(status_code=404, detail="manual position not found")
    return position


def _get_latest_report() -> CloseReport:
    if not _STORAGE.reports:
        raise HTTPException(status_code=404, detail="close report not found")
    return list(_STORAGE.reports.values())[-1]


def _request_price(request: ManualFillRequest) -> Decimal:
    price = request.actual_price or request.fill_price
    if price is None:
        raise HTTPException(status_code=422, detail="actual_price or fill_price is required")
    return price


def _request_time(request: ManualFillRequest) -> datetime:
    executed_at = request.executed_at or request.filled_at
    if executed_at is None:
        raise HTTPException(status_code=422, detail="executed_at or filled_at is required")
    return executed_at


def _build_fill_from_request(request: ManualFillRequest, plan: ManualTradePlan | None = None) -> ManualFill:
    stock_code = request.stock_code or (plan.stock_code if plan else None)
    stock_name = request.stock_name or (plan.stock_name if plan else None)
    if stock_code is None or stock_name is None:
        raise HTTPException(status_code=422, detail="stock_code and stock_name are required without plan_id")
    return ManualFill(
        fill_id=request.fill_id,
        plan_id=request.plan_id or (plan.plan_id if plan else None),
        signal_id=request.signal_id or (plan.signal_id if plan else None),
        stock_code=stock_code,
        stock_name=stock_name,
        side=request.side,
        planned_price=request.planned_price,
        actual_price=_request_price(request),
        quantity=request.quantity,
        fee=request.fee,
        fees=request.fees,
        executed_at=_request_time(request),
        execution_note=request.execution_note,
        subjective_reason=request.subjective_reason,
        note=request.note,
    )


def _provider_from_supervision_request(position: ManualPosition, request: PositionSupervisionRequest):
    return FixtureMarketDataProvider(
        intraday_bars={
            position.stock_code: [
                IntradayBar(
                    symbol=position.stock_code,
                    trade_date=request.trade_date,
                    at=request.observed_at,
                    open=request.open_price,
                    high=max(request.open_price, request.current_price),
                    low=min(request.open_price, request.current_price),
                    close=request.current_price,
                    volume=Decimal("0"),
                )
            ]
        },
        industry_returns={position.branch or "": request.industry_return},
    )


def _supervise_position(position: ManualPosition, request: PositionSupervisionRequest) -> dict[str, object]:
    result = supervise_position_morning(
        position=position,
        provider=_provider_from_supervision_request(position, request),
        trade_date=request.trade_date,
        observed_at=request.observed_at,
    )
    notification = None
    if request.send_feishu and result.should_notify_feishu:
        risk = calculate_position_risk(position)
        notification = _notifier().send_risk_alert(
            position=position,
            risk=risk,
            first_30m_close=result.first_30m_close or result.current_price,
            industry_alpha=result.industry_alpha or Decimal("0"),
            supervision_status=result.status.value,
        )
    return {"result": result, "notification": notification}


@router.get("/workbench")
def get_workbench() -> dict[str, list[object]]:
    positions = list(_STORAGE.positions.values())
    return {
        "signals": list(_STORAGE.signals.values()),
        "trade_plans": list(_STORAGE.trade_plans.values()),
        "positions": positions,
        "risk_matrix": build_position_risk_matrix(positions),
        "notifications": list(_STORAGE.notifications.values()),
        "reports": list(_STORAGE.reports.values()),
    }


@router.get("/snapshot")
def get_snapshot() -> dict[str, list[object]]:
    return get_workbench()


@router.post("/scan-tail")
def scan_tail_placeholder() -> dict[str, object]:
    return {"signals": [], "trade_plans": [], "message": "scan-tail requires an injected market data provider"}


@router.get("/signals")
def list_signals() -> list[LowAbsorbSignal]:
    return list(_STORAGE.signals.values())


@router.get("/signals/{signal_id}")
def get_signal(signal_id: str) -> LowAbsorbSignal:
    return _get_signal(signal_id)


@router.patch("/signals/{signal_id}")
def patch_signal(signal_id: str, request: SignalPatchRequest) -> LowAbsorbSignal:
    signal = _get_signal(signal_id)
    updates = request.model_dump(exclude_unset=True, exclude_none=True)
    patched = signal.model_copy(update=updates)
    _STORAGE.signals[patched.signal_id] = patched
    return patched


@router.post("/trade-plans")
def create_trade_plan(plan: ManualTradePlan) -> ManualTradePlan:
    _STORAGE.trade_plans[plan.plan_id] = plan
    return plan


@router.get("/trade-plans")
def list_trade_plans() -> list[ManualTradePlan]:
    return list(_STORAGE.trade_plans.values())


@router.post("/trade-plans/{plan_id}/feishu")
def push_trade_plan_to_feishu(plan_id: str):
    plan = _get_plan(plan_id)
    signal = _STORAGE.signals.get(plan.signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="signal not found")
    result = _notifier().send_buy_recommendation(plan=plan, signal=signal)
    if result.ok:
        _replace_plan(plan.model_copy(update={"status": TradePlanStatus.SENT_TO_FEISHU}))
    return result


@router.post("/trade-plans/{plan_id}/send-feishu")
def send_trade_plan_to_feishu(plan_id: str, force: bool = False):
    plan = _get_plan(plan_id)
    signal = _STORAGE.signals.get(plan.signal_id)
    if signal is None:
        raise HTTPException(status_code=404, detail="signal not found")
    result = _notifier().send_buy_recommendation(plan=plan, signal=signal, force=force)
    if result.ok:
        _replace_plan(plan.model_copy(update={"status": TradePlanStatus.SENT_TO_FEISHU}))
    return result


@router.post("/notify/test")
def send_notifier_test(force: bool = False):
    return _notifier().send_test_notification(force=force)


@router.post("/signals/{signal_id}/notify")
def notify_signal(signal_id: str, force: bool = False):
    signal = _get_signal(signal_id)
    plan = next((item for item in _STORAGE.trade_plans.values() if item.signal_id == signal_id), None)
    if plan is None:
        raise HTTPException(status_code=404, detail="manual trade plan not found")
    result = _notifier().send_buy_recommendation(plan=plan, signal=signal, force=force)
    if result.ok:
        _replace_plan(plan.model_copy(update={"status": TradePlanStatus.SENT_TO_FEISHU}))
    return result


@router.post("/trade-plans/{plan_id}/manual-fills")
def record_manual_fill(plan_id: str, request: ManualFillRequest) -> dict[str, object]:
    plan = _get_plan(plan_id)
    fill = _build_fill_from_request(request.model_copy(update={"plan_id": plan.plan_id}), plan)
    position = ManualFillReconciler(_STORAGE).record_fill(fill)
    _replace_plan(plan.model_copy(update={"status": TradePlanStatus.MANUAL_FILLED}))
    return {"fill": fill, "position": position}


@router.post("/fills")
def record_fill(request: ManualFillRequest) -> dict[str, object]:
    plan = _STORAGE.trade_plans.get(request.plan_id or "")
    fill = _build_fill_from_request(request, plan)
    position = ManualFillReconciler(_STORAGE).record_fill(fill)
    if plan is not None and fill.side == "BUY":
        _replace_plan(plan.model_copy(update={"status": TradePlanStatus.MANUAL_FILLED}))
    return {"fill": fill, "position": position, "risk": calculate_position_risk(position)}


@router.get("/positions")
def list_positions() -> list[ManualPosition]:
    return list(_STORAGE.positions.values())


@router.get("/positions/{position_id}")
def get_position(position_id: str) -> ManualPosition:
    return _get_position(position_id)


@router.patch("/positions/{position_id}")
def patch_position(position_id: str, request: PositionPatchRequest) -> ManualPosition:
    position = _get_position(position_id)
    updates = request.model_dump(exclude_unset=True, exclude_none=True)
    patched = position.model_copy(update=updates)
    _STORAGE.positions[patched.position_id] = patched
    return patched


@router.post("/positions/{position_id}/close")
def close_position(position_id: str, request: PositionCloseRequest | None = None) -> ManualPosition:
    position = _get_position(position_id)
    request = request or PositionCloseRequest()
    notes = [*position.notes]
    if request.note:
        notes.append(request.note)
    closed = position.model_copy(
        update={
            "status": PositionStatus.MANUAL_EXITED,
            "closed_at": request.closed_at or datetime.now(),
            "notes": notes,
        }
    )
    _STORAGE.positions[closed.position_id] = closed
    return closed


@router.get("/risk-matrix")
def get_risk_matrix():
    return build_position_risk_matrix(list(_STORAGE.positions.values()))


@router.post("/supervise/morning")
def supervise_morning(request: PositionSupervisionRequest) -> dict[str, list[object]]:
    rows = [_supervise_position(position, request) for position in _STORAGE.positions.values()]
    return {"positions": rows}


@router.post("/supervise/position/{position_id}")
def supervise_single_position(position_id: str, request: PositionSupervisionRequest) -> dict[str, object]:
    return _supervise_position(_get_position(position_id), request)


@router.post("/reports/close")
def create_close_report(trade_date: date):
    report = build_close_report(
        report_id=f"close-{trade_date:%Y%m%d}",
        trade_date=trade_date,
        signals=list(_STORAGE.signals.values()),
        trade_plans=list(_STORAGE.trade_plans.values()),
        positions=list(_STORAGE.positions.values()),
        review_items=["复核人工成交回填、R 风险矩阵和次日 10:00 监督项。"],
    )
    _STORAGE.reports[report.report_id] = report
    return report


@router.post("/reports/close/notify")
def notify_close_report(force: bool = False):
    return _notifier().send_close_report(report=_get_latest_report(), force=force)


@router.post("/positions/{position_id}/risk-alert")
def notify_position_risk_alert(
    position_id: str,
    first_30m_close: Decimal,
    industry_alpha: Decimal,
    supervision_status: str = "HOLD_WITH_WARNING",
    force: bool = False,
):
    position = _get_position(position_id)
    risk = calculate_position_risk(position)
    return _notifier().send_risk_alert(
        position=position,
        risk=risk,
        first_30m_close=first_30m_close,
        industry_alpha=industry_alpha,
        supervision_status=supervision_status,
        force=force,
    )
