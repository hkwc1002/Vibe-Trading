"""AI chain stock universe used by Low Absorb data providers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class AIChainStock:
    symbol: str
    name: str
    sector: str
    role: str
    mainboard_candidate: bool = True


AI_CHAIN_STOCKS: tuple[AIChainStock, ...] = (
    AIChainStock("601138", "工业富联", "服务器ODM", "leader"),
    AIChainStock("603019", "中科曙光", "服务器ODM", "core_middle_cap"),
    AIChainStock("000977", "浪潮信息", "服务器ODM", "sentiment_stock"),
    AIChainStock("600522", "中天科技", "CPO/光模块", "core_middle_cap"),
    AIChainStock("603083", "剑桥科技", "CPO/光模块", "mainboard_mapping"),
    AIChainStock("603228", "景旺电子", "PCB/高速板", "mainboard_mapping"),
    AIChainStock("002463", "沪电股份", "PCB/高速板", "leader", mainboard_candidate=False),
    AIChainStock("603986", "兆易创新", "HBM/存储", "leader"),
    AIChainStock("603912", "佳力图", "液冷散热", "mainboard_mapping"),
    AIChainStock("002837", "英维克", "液冷散热", "leader", mainboard_candidate=False),
    AIChainStock("600089", "特变电工", "电源连接器", "mainboard_mapping"),
    AIChainStock("605333", "沪光股份", "电源连接器", "mainboard_mapping"),
    AIChainStock("002130", "沃尔核材", "电源连接器", "leader", mainboard_candidate=False),
)


DEFAULT_BRANCH_STRENGTHS: dict[str, tuple[int, Decimal, Decimal]] = {
    "CPO/光模块": (1, Decimal("0.10"), Decimal("1.31")),
    "电源连接器": (2, Decimal("0.08"), Decimal("1.25")),
    "GPU/加速卡": (3, Decimal("0.08"), Decimal("1.22")),
    "服务器ODM": (4, Decimal("0.06"), Decimal("1.18")),
    "HBM/存储": (5, Decimal("0.04"), Decimal("1.12")),
    "PCB/高速板": (6, Decimal("0.02"), Decimal("1.06")),
    "液冷散热": (7, Decimal("-0.01"), Decimal("0.98")),
}


def default_ai_chain_mainboard_universe() -> list[str]:
    return [stock.symbol for stock in AI_CHAIN_STOCKS if stock.mainboard_candidate]


def default_ai_chain_sector_symbols() -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for stock in AI_CHAIN_STOCKS:
        if not stock.mainboard_candidate:
            continue
        mapping.setdefault(stock.sector, []).append(stock.symbol)
    return mapping


def default_symbol_industries() -> dict[str, str]:
    return {stock.symbol: stock.sector for stock in AI_CHAIN_STOCKS}


def default_symbol_names() -> dict[str, str]:
    return {stock.symbol: stock.name for stock in AI_CHAIN_STOCKS}


def default_sector_roles() -> dict[str, str]:
    return {stock.symbol: stock.role for stock in AI_CHAIN_STOCKS}
