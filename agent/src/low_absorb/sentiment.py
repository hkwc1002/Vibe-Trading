"""Macro sentiment gate helpers for Low Absorb."""

from __future__ import annotations

from datetime import date, datetime, time
from decimal import Decimal
from typing import Callable

from .config import LowAbsorbConfig
from .data_provider import MarketBreadth
from .models import SentimentSnapshot


def macro_gate_passed(snapshot: SentimentSnapshot | None) -> bool:
    """Return whether the macro sentiment gate allows recommendation work."""

    return bool(snapshot and snapshot.gate_passed)


def market_breadth_gate_passed(
    breadth: MarketBreadth | None,
    *,
    config: LowAbsorbConfig,
    at: datetime,
) -> bool:
    """Fail-closed macro gate for the 14:45 scan-tail funnel."""

    if breadth is None:
        return False
    if abs((at - breadth.captured_at).total_seconds()) > config.max_data_staleness_seconds:
        return False
    if breadth.total_market_turnover_cny <= config.min_market_turnover_cny:
        return False
    return breadth.limit_break_rate < config.max_limit_break_rate


# ── Global risk appetite helpers ─────────────────────────────────────────────

_GLOBAL_TECH_TICKERS = ["NVDA", "MSFT", "AVGO"]


def compute_global_risk_appetite(
    provider: object,
    *,
    trade_date: date | None = None,
) -> tuple[Decimal | None, str | None]:
    """Derive a 0-100 global risk-appetite score from overseas daily bars.

    Uses the given provider's ``get_daily_bars`` to fetch recent daily
    closes for key US tech tickers.  Returns ``(score, error)`` where
    exactly one of them is ``None``.
    """
    today = trade_date or date.today()
    lookback = 10

    try:
        bars_by_ticker = provider.get_daily_bars(_GLOBAL_TECH_TICKERS, today, lookback)  # type: ignore[union-attr]
    except Exception as exc:
        return None, f"全球行情数据获取失败: {exc}"

    daily_returns: list[Decimal] = []
    for ticker in _GLOBAL_TECH_TICKERS:
        bars = bars_by_ticker.get(ticker, [])
        for i in range(1, len(bars)):
            prev_close = bars[i - 1].close
            if prev_close > 0:
                daily_returns.append((bars[i].close - prev_close) / prev_close)

    if not daily_returns:
        return None, "全球行情数据为空，无法计算风险偏好"

    avg_return = sum(daily_returns, Decimal("0")) / Decimal(str(len(daily_returns)))
    scaled = (avg_return + Decimal("0.02")) * Decimal("2500")
    score = max(Decimal("0"), min(Decimal("100"), scaled))
    return score.quantize(Decimal("1")), None


def build_sentiment_permission_snapshot(
    config: LowAbsorbConfig | None = None,
    *,
    global_risk_appetite: Decimal | None = None,
    global_risk_error: str | None = None,
    a_share_turnover_cny: Decimal | None = None,
    a_share_limit_break_rate: Decimal | None = None,
    a_share_advance_count: int | None = None,
    a_share_decline_count: int | None = None,
) -> dict[str, object]:
    """Return a trading-permission view for the sentiment dashboard.

    When real market data parameters are provided the gate logic uses them
    instead of hardcoded fixture values.  A ``None`` or errored global-risk
    input forces the conclusion to "观察" or "拦截" so that stale / missing
    overseas data can never yield a false "允许".
    """
    config = config or LowAbsorbConfig()

    # ── Resolve A-share inputs ──
    # When the caller provides global_risk_appetite (real-data path) but
    # A-share values are None, the data was expected but unavailable.
    a_share_provided = a_share_turnover_cny is not None and a_share_limit_break_rate is not None
    a_share_data_missing = False
    global_provided = global_risk_appetite is not None and global_risk_error is None

    if global_provided and not a_share_provided:
        # Real-data path: A-share breadth was requested but unavailable
        a_share_ok = False
        a_share_data_missing = True
        turnover = a_share_turnover_cny
        limit_break = a_share_limit_break_rate
    elif a_share_provided:
        turnover = a_share_turnover_cny
        limit_break = a_share_limit_break_rate
        a_share_ok = turnover > config.min_market_turnover_cny and limit_break < config.max_limit_break_rate  # type: ignore[operator]
    else:
        # Legacy / all-fixture path: use default values
        turnover = Decimal("612000000000")
        limit_break = Decimal("0.20")
        a_share_ok = turnover > config.min_market_turnover_cny and limit_break < config.max_limit_break_rate

    # ── Resolve global risk appetite ──
    global_available = global_risk_appetite is not None and global_risk_error is None
    if global_available:
        global_score = int(global_risk_appetite)  # type: ignore[arg-type]
        global_status = "偏暖" if global_score >= 60 else ("偏冷" if global_score < 40 else "中性")
        global_detail = f"全球风险偏好评分 {global_score}。"
    else:
        global_score = 0
        global_status = "数据缺失"
        global_detail = global_risk_error or "全球行情数据不可用，无法评估风险偏好。"

    # ── Compute overall permission ──
    if a_share_data_missing:
        status = "拦截"
        blocked = ["A 股行情数据不可用，无法判断市场宽度闸门"]
    elif not a_share_ok:
        status = "拦截"
        blocked = ["市场成交额或炸板率未通过宏观闸门"]
    elif not global_available:
        status = "观察"
        blocked = ["全球风险偏好数据不可用，降级为观察"]
    elif global_score < 30:
        status = "拦截"
        blocked = [f"全球风险偏好评分过低（{global_score}），市场风险较高"]
    elif global_score < 50:
        status = "观察"
        blocked = [f"全球风险偏好评分偏低（{global_score}），建议观望"]
    else:
        status = "允许"
        blocked = []

    summary = "双情绪时钟用于决定是否允许生成 Low Absorb 人工交易建议。"
    next_action = "执行 14:45 扫描" if status == "允许" else "等待情绪闸门恢复"

    return {
        "tradingPermission": {
            "status": status,
            "summary": summary,
            "nextAction": next_action,
            "blockedReasons": blocked,
        },
        "gauges": [
            {
                "id": "global",
                "label": "全球情绪",
                "score": global_score,
                "status": global_status,
                "detail": global_detail,
            },
            {
                "id": "a_share",
                "label": "A 股情绪",
                "score": 0 if a_share_data_missing else (71 if a_share_ok else 30),
                "status": "数据缺失" if a_share_data_missing else ("允许" if a_share_ok else status),
                "detail": "A 股行情数据不可用。" if a_share_data_missing else ("成交额达标，炸板率低于阈值。" if a_share_ok else "成交额或炸板率未通过。"),
            },
        ],
        "instrumentPanels": [
            {
                "id": "market_turnover",
                "label": "成交额闸门",
                "value": str(turnover) if not a_share_data_missing else "—",
                "status": "数据缺失" if a_share_data_missing else ("通过" if turnover > config.min_market_turnover_cny else "拦截"),
                "explanation": "两市成交额必须超过配置阈值。" if not a_share_data_missing else "A 股行情数据不可用，无法计算成交额闸门。",
            },
            {
                "id": "limit_break",
                "label": "炸板率闸门",
                "value": str(limit_break) if not a_share_data_missing else "—",
                "status": "数据缺失" if a_share_data_missing else ("通过" if limit_break < config.max_limit_break_rate else "拦截"),
                "explanation": "炸板率过高时暂停生成新计划。" if not a_share_data_missing else "A 股行情数据不可用，无法计算炸板率闸门。",
            },
            {
                "id": "advance_decline",
                "label": "涨跌家数宽度",
                "value": f"{a_share_advance_count} / {a_share_decline_count}" if a_share_advance_count is not None and a_share_decline_count is not None else "—",
                "status": "观察",
                "explanation": "上涨家数占优，但不是单独放行条件。",
            },
            {
                "id": "ai_capital_temperature",
                "label": "AI 资金温度",
                "value": "73" if a_share_ok else "—",
                "status": "通过" if a_share_ok else "数据不足",
                "explanation": "AI 链资金温度高于全市场均值。",
            },
            {
                "id": "global_risk_appetite",
                "label": "全球风险偏好",
                "value": str(global_score) if global_available else "—",
                "status": global_status,
                "detail": global_detail,
                "explanation": "海外风险状态影响交易许可。",
            },
            {
                "id": "sentiment_conclusion",
                "label": "情绪结论",
                "value": status,
                "status": status,
                "explanation": "该结论只允许生成建议，不代表自动执行。",
            },
        ],
        "socialEvents": [
            {
                "id": "social-ai-server",
                "time": "14:20",
                "source": "社交监控",
                "title": "AI 服务器讨论热度延续",
                "impact": "提高主线观察权重",
            },
            {
                "id": "social-cpo",
                "time": "14:33",
                "source": "社交监控",
                "title": "CPO 分歧扩大",
                "impact": "等待技术闸门确认",
            },
        ],
        "newsEvents": [
            {
                "id": "news-supply-chain",
                "time": "13:55",
                "source": "新闻监控",
                "title": "AI 服务器供应链订单线索",
                "impact": "支持服务器ODM分支研究",
            },
            {
                "id": "news-power",
                "time": "14:05",
                "source": "新闻监控",
                "title": "电源连接器成本占比受关注",
                "impact": "纳入成本链权重观察",
            },
        ],
    }
