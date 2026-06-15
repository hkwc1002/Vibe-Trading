"""Backtest API for Low Absorb — daily-level real backtest engine."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from ..backtest.engine import BacktestEngine
from ..config import LowAbsorbConfig
from ..models import BacktestRunRequest
from .workbench import get_workbench_storage

router = APIRouter(prefix="/low-absorb/backtest", tags=["low-absorb"])


def _build_engine() -> BacktestEngine:
    """Create a BacktestEngine wired to the active storage and data provider."""
    storage = get_workbench_storage()
    config = storage.get_config()
    try:
        from ..a_stock_provider import AStockLowAbsorbProvider as Provider
        provider: Any = Provider()
    except Exception:
        from ..fallback_provider import FallbackMarketDataProvider as Provider
        provider = Provider()
    return BacktestEngine(config=config, data_provider=provider, storage=storage)


def build_backtest_snapshot() -> dict[str, object]:
    """Return the backtest snapshot (kept for backward compatibility)."""
    return {
        "metrics": [
            {"id": "win-rate", "label": "胜率", "value": "—", "detail": "运行真实回测后更新"},
            {"id": "avg-r", "label": "平均 R", "value": "—", "detail": "运行真实回测后更新"},
            {"id": "drawdown", "label": "最大回撤", "value": "—", "detail": "运行真实回测后更新"},
            {"id": "samples", "label": "样本数", "value": "—", "detail": "运行真实回测后更新"},
        ],
        "parameters": [
            {"id": "turnover", "label": "成交额阈值", "value": str(LowAbsorbConfig().min_market_turnover_cny)},
            {"id": "ma20", "label": "MA20 偏离范围", "value": f"{LowAbsorbConfig().ma20_deviation_min} 至 {LowAbsorbConfig().ma20_deviation_max}"},
        ],
        "suggestions": [
            "通过 POST /low-absorb/backtest/runs 提交真实回测请求。",
            "回测结果为策略研究参考，不构成投资建议和收益承诺。",
        ],
        "message": "真实回测引擎已接入。使用 POST /low-absorb/backtest/runs 提交回测请求。",
    }


@router.get("")
def get_backtest_runs() -> dict[str, list[object]]:
    storage = get_workbench_storage()
    runs = storage.list_backtest_runs()
    return {"runs": [r.model_dump(mode="json") for r in runs]}


@router.get("/summary")
def get_backtest_summary() -> dict[str, object]:
    return build_backtest_snapshot()


@router.post("/run")
def run_backtest_legacy() -> dict[str, object]:
    return {
        "runId": None,
        "status": "USE_POST_RUNS",
        "message": "请使用 POST /low-absorb/backtest/runs 提交包含 start_date、end_date、symbols 的回测请求。",
    }


def _envelope(data: Any = None, error: str | None = None) -> dict[str, object]:
    return {"success": error is None, "data": data, "error": error}


class BacktestCreateRequest(BaseModel):
    """Request body for creating a backtest run."""

    start_date: str
    end_date: str
    symbols: list[str] | None = None
    cost_chain_version: str = "GB200 NVL72"
    config_snapshot_id: str | None = None
    include_manual_fill_assumption: bool = False


@router.post("/runs")
def create_backtest_run(body: BacktestCreateRequest) -> dict[str, object]:
    """Create and execute a daily-level backtest run."""
    try:
        parsed_start = date.fromisoformat(body.start_date)
        parsed_end = date.fromisoformat(body.end_date)
    except (ValueError, TypeError) as e:
        return _envelope(error=f"日期格式无效: {e}")

    request = BacktestRunRequest(
        start_date=parsed_start,
        end_date=parsed_end,
        symbols=body.symbols,
        cost_chain_version=body.cost_chain_version,
        config_snapshot_id=body.config_snapshot_id,
        include_manual_fill_assumption=body.include_manual_fill_assumption,
    )

    engine = _build_engine()
    result = engine.run(request)

    return _envelope(data=result.model_dump(mode="json"))


@router.get("/runs")
def list_backtest_runs() -> dict[str, object]:
    """List all backtest runs."""
    storage = get_workbench_storage()
    runs = storage.list_backtest_runs()
    return _envelope(data={"runs": [r.model_dump(mode="json") for r in runs]})


@router.get("/runs/{run_id}")
def get_backtest_run(run_id: str) -> dict[str, object]:
    """Get a specific backtest run by ID (returns full BacktestResult if available)."""
    storage = get_workbench_storage()

    # Try full result first; fall back to run summary
    result = storage.get_backtest_result(run_id)
    if result is not None:
        return _envelope(data=result.model_dump(mode="json"))

    run = storage.get_backtest_run(run_id)
    if run is None:
        return _envelope(error=f"未找到回测任务: {run_id}")
    return _envelope(data=run.model_dump(mode="json"))
