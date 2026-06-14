"""Backtest API for Low Absorb — returns example snapshot data."""

from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(prefix="/low-absorb/backtest", tags=["low-absorb"])


def build_backtest_snapshot() -> dict[str, object]:
    """Return an example backtest snapshot matching the frontend mock structure.

    The data mirrors LOW_ABSORB_BACKTEST_MOCK from frontend/src/mocks/lowAbsorb.ts.
    Real backtest engine integration will replace this when connected.
    """
    return {
        "metrics": [
            {"id": "win-rate", "label": "胜率", "value": "56.8%", "detail": "仅为示例统计"},
            {"id": "avg-r", "label": "平均 R", "value": "0.42R", "detail": "未接真实回测引擎"},
            {"id": "drawdown", "label": "最大回撤", "value": "-6.4%", "detail": "用于页面契约预览"},
            {"id": "samples", "label": "样本数", "value": "148", "detail": "覆盖近 18 个月信号"},
            {"id": "profit-factor", "label": "盈亏比", "value": "1.36", "detail": "按人工执行假设估算"},
            {"id": "best-branch", "label": "最佳分支", "value": "AI 服务器", "detail": "分支归因示例"},
        ],
        "parameters": [
            {"id": "turnover", "label": "成交额阈值", "value": "8,000 亿", "detail": "宏观闸门下限"},
            {"id": "limit-break", "label": "炸板率阈值", "value": "50%", "detail": "高风险情绪拦截"},
            {"id": "ma20", "label": "MA20 偏离范围", "value": "-5% 至 +1%", "detail": "尾盘回踩过滤"},
            {"id": "volume", "label": "量比阈值", "value": "≤ 0.85", "detail": "缩量低吸过滤"},
            {"id": "shadow", "label": "下影线 ATR 阈值", "value": "≥ 1.0", "detail": "承接强度过滤"},
            {"id": "alpha", "label": "10:00 Alpha 宽容", "value": "≥ 1%", "detail": "次日监督规则"},
        ],
        "historicalSignals": [
            {
                "id": "hist-1",
                "tradeDate": "2026-05-18",
                "stock": "601138 工业富联",
                "branch": "AI 服务器",
                "grade": "A",
                "nextDayReturn": "+2.8%",
                "maxFloatLoss": "-0.7%",
                "finalR": "1.4R",
                "stopHit": "否",
            },
            {
                "id": "hist-2",
                "tradeDate": "2026-05-22",
                "stock": "603019 中科曙光",
                "branch": "算力基础设施",
                "grade": "B+",
                "nextDayReturn": "+1.1%",
                "maxFloatLoss": "-1.2%",
                "finalR": "0.6R",
                "stopHit": "否",
            },
            {
                "id": "hist-3",
                "tradeDate": "2026-05-29",
                "stock": "002463 沪电股份",
                "branch": "PCB",
                "grade": "B",
                "nextDayReturn": "-1.6%",
                "maxFloatLoss": "-2.4%",
                "finalR": "-0.8R",
                "stopHit": "是",
            },
        ],
        "sensitivity": [
            {"id": "sen-ma20", "parameter": "MA20 偏离", "conservative": "0.31R", "base": "0.42R", "aggressive": "0.28R"},
            {"id": "sen-volume", "parameter": "量比阈值", "conservative": "0.37R", "base": "0.42R", "aggressive": "0.33R"},
            {"id": "sen-alpha", "parameter": "10:00 Alpha", "conservative": "0.35R", "base": "0.42R", "aggressive": "0.46R"},
        ],
        "branchAttribution": [
            {"id": "attr-server", "branch": "AI 服务器", "samples": 54, "averageR": "0.62R", "contribution": "42%"},
            {"id": "attr-cpo", "branch": "CPO", "samples": 31, "averageR": "0.38R", "contribution": "19%"},
            {"id": "attr-pcb", "branch": "PCB", "samples": 28, "averageR": "0.21R", "contribution": "11%"},
        ],
        "suggestions": [
            "弱分支末位且斜率为负时，继续保持强拦截。",
            "对 10:00 宽容阈值做分支级敏感性拆分。",
            "人工成交回填缺失的样本不纳入收益统计。",
        ],
        "message": "当前为示例回测数据，真实回测引擎接入后将自动更新。",
    }


@router.get("")
def get_backtest_runs() -> dict[str, list[object]]:
    return {"runs": []}


@router.get("/summary")
def get_backtest_summary() -> dict[str, object]:
    return build_backtest_snapshot()


@router.post("/run")
def run_backtest() -> dict[str, object]:
    return {
        "runId": None,
        "status": "BACKTEST_ENGINE_NOT_CONNECTED",
        "message": "回测引擎未接入，当前为实施例数据展示。",
    }
