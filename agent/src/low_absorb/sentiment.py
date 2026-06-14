"""Macro sentiment gate helpers for Low Absorb."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

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


def build_sentiment_permission_snapshot(config: LowAbsorbConfig | None = None) -> dict[str, object]:
    """Return a fixture-backed trading-permission view for the dashboard."""

    config = config or LowAbsorbConfig()
    turnover = Decimal("612000000000")
    limit_break = Decimal("0.20")
    allowed = turnover > config.min_market_turnover_cny and limit_break < config.max_limit_break_rate
    status = "允许观察" if allowed else "暂停生成"
    return {
        "tradingPermission": {
            "status": status,
            "summary": "双情绪时钟用于决定是否允许生成 Low Absorb 人工交易建议。",
            "nextAction": "执行 14:45 扫描" if allowed else "等待情绪闸门恢复",
            "blockedReasons": [] if allowed else ["市场成交额或炸板率未通过宏观闸门"],
        },
        "gauges": [
            {
                "id": "global",
                "label": "全球情绪",
                "score": 62,
                "status": "中性偏暖",
                "detail": "海外科技风险未形成明显压制。",
            },
            {
                "id": "a_share",
                "label": "A 股情绪",
                "score": 71,
                "status": status,
                "detail": "成交额达标，炸板率低于阈值。",
            },
        ],
        "instrumentPanels": [
            {
                "id": "market_turnover",
                "label": "market turnover gate",
                "value": str(turnover),
                "status": "通过" if turnover > config.min_market_turnover_cny else "拦截",
                "explanation": "两市成交额必须超过配置阈值。",
            },
            {
                "id": "limit_break",
                "label": "limit-break gate",
                "value": str(limit_break),
                "status": "通过" if limit_break < config.max_limit_break_rate else "拦截",
                "explanation": "炸板率过高时暂停生成新计划。",
            },
            {
                "id": "advance_decline",
                "label": "advance/decline breadth",
                "value": "3120 / 1790",
                "status": "观察",
                "explanation": "上涨家数占优，但不是单独放行条件。",
            },
            {
                "id": "ai_capital_temperature",
                "label": "AI capital temperature",
                "value": "73",
                "status": "通过",
                "explanation": "AI 链资金温度高于全市场均值。",
            },
            {
                "id": "global_risk_appetite",
                "label": "global risk appetite",
                "value": "62",
                "status": "观察",
                "explanation": "全球风险偏好中性偏暖。",
            },
            {
                "id": "sentiment_conclusion",
                "label": "sentiment conclusion",
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
