"""AI-chain relative-strength and NVIDIA AI server cost-chain helpers."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from .config import LowAbsorbConfig
from .data_provider import ChainBranchStrength
from .models import ChainBranchSnapshot, ChainSectorStock, ChainSectorWorkspace, CostChainComponent, CostChainModel


NVIDIA_GB200_URL = "https://www.nvidia.com/en-us/data-center/gb200-nvl72/"
NVIDIA_GB300_URL = "https://www.nvidia.com/en-us/data-center/gb300-nvl72/"
TOMS_COOLING_URL = "https://www.tomshardware.com/pc-components/cooling/cooling-system-for-a-single-nvidia-blackwell-ultra-nvl72-rack-costs-a-staggering-usd50-000-set-to-increase-to-usd56-000-with-next-generation-nvl144-racks"
TOMS_RACK_PRICE_URL = "https://www.tomshardware.com/tech-industry/artificial-intelligence/price-of-nvidias-vera-rubin-nvl72-racks-skyrockets-to-as-much-as-usd8-8-million-apiece-but-server-makers-margins-will-be-tight-nvidia-is-moving-closer-to-shipping-entire-full-scale-systems"


def passed_chain_branches(branches: list[ChainBranchSnapshot]) -> list[ChainBranchSnapshot]:
    """Return branch snapshots that pass the relative-strength gate."""

    return [branch for branch in branches if branch.gate_passed]


SECTOR_TABS: tuple[dict[str, str], ...] = (
    {"id": "cost-overview", "label": "成本总览"},
    {"id": "gpu", "label": "GPU/加速卡"},
    {"id": "hbm", "label": "HBM/存储"},
    {"id": "cpo", "label": "CPO/光模块"},
    {"id": "pcb", "label": "PCB/高速板"},
    {"id": "odm", "label": "服务器ODM"},
    {"id": "cooling", "label": "液冷散热"},
    {"id": "power", "label": "电源连接器"},
)


def normalize_chain_sector(branch_name: str) -> str:
    aliases = {
        "AI 服务器": "服务器ODM",
        "服务器": "服务器ODM",
        "服务器ODM": "服务器ODM",
        "算力基础设施": "服务器ODM",
        "GPU": "GPU/加速卡",
        "加速卡": "GPU/加速卡",
        "HBM": "HBM/存储",
        "存储": "HBM/存储",
        "CPO": "CPO/光模块",
        "光模块": "CPO/光模块",
        "PCB": "PCB/高速板",
        "高速板": "PCB/高速板",
        "散热": "液冷散热",
        "液冷": "液冷散热",
        "电源": "电源连接器",
        "连接器": "电源连接器",
    }
    return aliases.get(branch_name, branch_name)


def chain_branch_allows_stock(branch_name: str, branches: list[ChainBranchStrength]) -> bool:
    """Reject a stock when its AI branch ranks last and the branch slope is negative."""

    normalized = normalize_chain_sector(branch_name)
    branch = next((item for item in branches if normalize_chain_sector(item.branch_name) == normalized), None)
    if branch is None:
        return False
    return not (branch.rank >= branch.total_branches and branch.slope < 0)


def _component(
    *,
    component: str,
    cost_weight: str,
    cost_range: tuple[str, str],
    increase: str,
    sector: str,
    leaders: list[str],
    mapping: list[str],
    signal_weight: str,
    source_type: str,
    source_url: str,
    source_title: str,
    confidence: str,
    is_estimated: bool,
    note: str,
) -> CostChainComponent:
    return CostChainComponent(
        component=component,
        cost_weight=Decimal(cost_weight),
        cost_weight_range=[Decimal(cost_range[0]), Decimal(cost_range[1])],
        cost_increase_vs_previous_generation=Decimal(increase),
        related_sector=sector,
        a_share_leaders=leaders,
        tradable_mainboard_mapping=mapping,
        signal_weight=Decimal(signal_weight),
        data_source=source_title,
        source_type=source_type,
        source_url=source_url,
        source_title=source_title,
        confidence=confidence,  # type: ignore[arg-type]
        is_estimated=is_estimated,
        methodology_note=note,
        as_of=date(2026, 6, 13),
    )


def _components_for_version(version: str, multiplier: Decimal) -> list[CostChainComponent]:
    official_url = NVIDIA_GB300_URL if version == "GB300 NVL72" else NVIDIA_GB200_URL
    official_note = (
        "NVIDIA 官方规格用于确认 NVL72 架构、GPU/CPU/内存/互联；成本权重为专业资料转述后的研究估算。"
    )
    estimate_note = (
        "权重为研究用途的区间化估算，不代表 NVIDIA 官方 BOM；用于 Low Absorb 产业链信号排序。"
    )
    rows = [
        _component(
            component="GPU/加速卡",
            cost_weight=str(Decimal("0.42") * multiplier),
            cost_range=("0.36", "0.50"),
            increase="0.12",
            sector="GPU/加速卡",
            leaders=["寒武纪", "海光信息"],
            mapping=["600089"],
            signal_weight="0.90",
            source_type="official_spec_and_estimate",
            source_url=official_url,
            source_title=f"NVIDIA {version} 官方规格 + 成本估算",
            confidence="medium",
            is_estimated=True,
            note=official_note,
        ),
        _component(
            component="HBM/存储",
            cost_weight=str(Decimal("0.18") * multiplier),
            cost_range=("0.14", "0.25"),
            increase="0.16",
            sector="HBM/存储",
            leaders=["兆易创新", "香农芯创"],
            mapping=["603986"],
            signal_weight="0.86",
            source_type="broker_estimate",
            source_url=TOMS_RACK_PRICE_URL,
            source_title="Tom's Hardware 转述 DigiTimes/Morgan Stanley 内存成本讨论",
            confidence="medium",
            is_estimated=True,
            note=estimate_note,
        ),
        _component(
            component="CPO/光模块",
            cost_weight=str(Decimal("0.08") * multiplier),
            cost_range=("0.05", "0.12"),
            increase="0.22",
            sector="CPO/光模块",
            leaders=["中际旭创", "新易盛"],
            mapping=["600522", "603083"],
            signal_weight="0.82",
            source_type="industry_estimate",
            source_url=NVIDIA_GB300_URL,
            source_title="NVIDIA ConnectX-8 / Quantum-X800 / Spectrum-X 规格映射",
            confidence="low",
            is_estimated=True,
            note="官方确认网络能力，A 股映射和权重为产业链研究估算。",
        ),
        _component(
            component="PCB/高速板",
            cost_weight=str(Decimal("0.07") * multiplier),
            cost_range=("0.04", "0.10"),
            increase="0.18",
            sector="PCB/高速板",
            leaders=["沪电股份", "胜宏科技"],
            mapping=["603228"],
            signal_weight="0.74",
            source_type="industry_estimate",
            source_url=TOMS_RACK_PRICE_URL,
            source_title="Tom's Hardware 转述高复杂度 PCB/电源/网络成本上升",
            confidence="low",
            is_estimated=True,
            note=estimate_note,
        ),
        _component(
            component="服务器ODM",
            cost_weight=str(Decimal("0.11") * multiplier),
            cost_range=("0.08", "0.16"),
            increase="0.08",
            sector="服务器ODM",
            leaders=["工业富联", "中科曙光"],
            mapping=["601138", "603019"],
            signal_weight="0.70",
            source_type="broker_estimate",
            source_url=TOMS_RACK_PRICE_URL,
            source_title="Tom's Hardware 转述 NVL72 rack 价格区间与 ODM 利润压力",
            confidence="medium",
            is_estimated=True,
            note="Rack 价格和 ODM 角色来自专业媒体转述；权重用于交易研究而非会计成本。",
        ),
        _component(
            component="液冷散热",
            cost_weight=str(Decimal("0.015") * multiplier),
            cost_range=("0.012", "0.025"),
            increase="0.20",
            sector="液冷散热",
            leaders=["英维克", "高澜股份"],
            mapping=["603912"],
            signal_weight="0.66",
            source_type="broker_estimate",
            source_url=TOMS_COOLING_URL,
            source_title="Tom's Hardware 转述 Morgan Stanley GB300 NVL72 液冷成本",
            confidence="medium",
            is_estimated=True,
            note="公开转述称 GB300 NVL72 单 rack 液冷约 49,860 美元，折算为整机权重区间。",
        ),
        _component(
            component="电源连接器",
            cost_weight=str(Decimal("0.055") * multiplier),
            cost_range=("0.035", "0.08"),
            increase="0.20",
            sector="电源连接器",
            leaders=["沃尔核材", "永贵电器"],
            mapping=["600089", "605333"],
            signal_weight="0.62",
            source_type="industry_estimate",
            source_url=TOMS_RACK_PRICE_URL,
            source_title="Tom's Hardware 转述电源与连接复杂度提升",
            confidence="low",
            is_estimated=True,
            note=estimate_note,
        ),
    ]
    return rows


def default_cost_chain_models() -> dict[str, CostChainModel]:
    gb200 = CostChainModel(
        version="GB200 NVL72",
        components=_components_for_version("GB200 NVL72", Decimal("0.92")),
    )
    gb300 = CostChainModel(
        version="GB300 NVL72",
        components=_components_for_version("GB300 NVL72", Decimal("1.00")),
    )
    manual = CostChainModel(
        version="custom/manual",
        is_editable=True,
        components=[
            item.model_copy(
                update={
                    "data_source": "editable backend settings",
                    "source_type": "manual",
                    "source_title": "用户自定义 custom/manual",
                    "source_url": "",
                    "confidence": "low",
                    "is_estimated": True,
                    "methodology_note": "用户可编辑版本，保存后用于信号权重。",
                }
            )
            for item in gb300.components
        ],
    )
    return {model.version: model for model in (gb200, gb300, manual)}


def cost_signal_weight_for_sector(sector: str, config: LowAbsorbConfig, model: CostChainModel | None = None) -> Decimal:
    normalized = normalize_chain_sector(sector)
    if normalized in config.chain_cost_signal_weights:
        return Decimal(config.chain_cost_signal_weights[normalized])
    component = next((item for item in (model.components if model else []) if item.related_sector == normalized), None)
    return component.signal_weight if component else Decimal("0")


def branch_strength_for_sector(sector: str, branches: list[ChainBranchStrength]) -> Decimal:
    normalized = normalize_chain_sector(sector)
    branch = next((item for item in branches if normalize_chain_sector(item.branch_name) == normalized), None)
    return branch.relative_strength if branch else Decimal("0")


def chain_priority_score(
    *,
    sector: str,
    branches: list[ChainBranchStrength],
    config: LowAbsorbConfig,
    model: CostChainModel | None = None,
) -> Decimal:
    branch_strength = branch_strength_for_sector(sector, branches)
    cost_weight = cost_signal_weight_for_sector(sector, config, model)
    return (branch_strength * Decimal("60")) + (cost_weight * Decimal("40"))


def chain_explanation_for_sector(
    *,
    sector: str,
    branches: list[ChainBranchStrength],
    config: LowAbsorbConfig,
    model: CostChainModel | None = None,
) -> str:
    normalized = normalize_chain_sector(sector)
    branch_strength = branch_strength_for_sector(normalized, branches)
    cost_weight = cost_signal_weight_for_sector(normalized, config, model)
    return (
        f"AI Chain：{normalized} 分支 RS {branch_strength:.2f}，"
        f"成本链权重 {cost_weight:.2f}，用于同等技术条件下的候选优先级排序。"
    )


def _stock(
    role: str,
    code: str,
    name: str,
    score: str,
    volume: str,
    suitability: str,
    reason: str,
    recommendation: str,
) -> ChainSectorStock:
    return ChainSectorStock(
        role=role,  # type: ignore[arg-type]
        stock_code=code,
        stock_name=name,
        strength_score=Decimal(score),
        volume_condition=volume,
        low_absorb_suitability=suitability,
        reason=reason,
        current_recommendation=recommendation,
    )


def default_chain_sectors() -> list[ChainSectorWorkspace]:
    return [
        ChainSectorWorkspace(
            sector_id="gpu",
            label="GPU/加速卡",
            sector_index="AI 加速卡指数",
            price_change_pct=Decimal("0.018"),
            turnover_cny=Decimal("42600000000"),
            volume_ratio=Decimal("1.18"),
            rs_strength=Decimal("1.22"),
            fund_flow_cny=Decimal("1200000000"),
            trend_slope=Decimal("0.08"),
            limit_up_count=2,
            limit_break_count=1,
            stocks=[
                _stock("leader", "688256", "寒武纪", "88", "放量强势", "观察", "弹性标杆但非主板", "watch-only"),
                _stock("core_middle_cap", "600089", "特变电工", "76", "缩量回踩", "可映射", "主板可交易映射", "进入候选池"),
                _stock("sentiment_stock", "300308", "中际旭创", "82", "高热度", "观察", "创业板不进入主板候选", "watch-only"),
            ],
        ),
        ChainSectorWorkspace(
            sector_id="hbm",
            label="HBM/存储",
            sector_index="先进存储指数",
            price_change_pct=Decimal("0.011"),
            turnover_cny=Decimal("31800000000"),
            volume_ratio=Decimal("1.04"),
            rs_strength=Decimal("1.12"),
            fund_flow_cny=Decimal("680000000"),
            trend_slope=Decimal("0.04"),
            limit_up_count=1,
            limit_break_count=0,
            stocks=[
                _stock("leader", "603986", "兆易创新", "80", "温和放量", "中性", "主板存储映射", "等待技术闸门"),
                _stock("watch_only", "301269", "华大九天", "67", "波动偏高", "观察", "非主板，仅作热度参考", "watch-only"),
            ],
        ),
        ChainSectorWorkspace(
            sector_id="cpo",
            label="CPO/光模块",
            sector_index="光模块指数",
            price_change_pct=Decimal("0.024"),
            turnover_cny=Decimal("51200000000"),
            volume_ratio=Decimal("1.32"),
            rs_strength=Decimal("1.31"),
            fund_flow_cny=Decimal("1660000000"),
            trend_slope=Decimal("0.10"),
            limit_up_count=3,
            limit_break_count=1,
            stocks=[
                _stock("leader", "300308", "中际旭创", "92", "强趋势", "观察", "非主板龙头用于热度锚", "watch-only"),
                _stock("core_middle_cap", "600522", "中天科技", "73", "缩量承接", "较好", "主板可映射", "可进入信号漏斗"),
                _stock("mainboard_mapping", "603083", "剑桥科技", "78", "分歧放量", "谨慎", "主板映射但波动高", "等待量能收缩"),
            ],
        ),
        ChainSectorWorkspace(
            sector_id="pcb",
            label="PCB/高速板",
            sector_index="高速 PCB 指数",
            price_change_pct=Decimal("0.009"),
            turnover_cny=Decimal("26800000000"),
            volume_ratio=Decimal("0.92"),
            rs_strength=Decimal("1.06"),
            fund_flow_cny=Decimal("280000000"),
            trend_slope=Decimal("0.02"),
            limit_up_count=1,
            limit_break_count=1,
            stocks=[
                _stock("leader", "002463", "沪电股份", "84", "趋势放量", "观察", "非主板映射", "watch-only"),
                _stock("mainboard_mapping", "603228", "景旺电子", "69", "缩量回踩", "较好", "主板高速板映射", "可进入信号漏斗"),
            ],
        ),
        ChainSectorWorkspace(
            sector_id="odm",
            label="服务器ODM",
            sector_index="AI 服务器指数",
            price_change_pct=Decimal("0.015"),
            turnover_cny=Decimal("48600000000"),
            volume_ratio=Decimal("1.08"),
            rs_strength=Decimal("1.18"),
            fund_flow_cny=Decimal("920000000"),
            trend_slope=Decimal("0.06"),
            limit_up_count=2,
            limit_break_count=0,
            stocks=[
                _stock("leader", "601138", "工业富联", "86", "缩量回踩", "较好", "主板服务器核心映射", "优先候选"),
                _stock("core_middle_cap", "603019", "中科曙光", "81", "温和承接", "较好", "主板中军", "可进入信号漏斗"),
                _stock("sentiment_stock", "000977", "浪潮信息", "79", "波动偏高", "谨慎", "情绪锚但技术需过滤", "等待技术闸门"),
            ],
        ),
        ChainSectorWorkspace(
            sector_id="cooling",
            label="液冷散热",
            sector_index="液冷散热指数",
            price_change_pct=Decimal("0.006"),
            turnover_cny=Decimal("16600000000"),
            volume_ratio=Decimal("0.88"),
            rs_strength=Decimal("0.98"),
            fund_flow_cny=Decimal("-120000000"),
            trend_slope=Decimal("-0.01"),
            limit_up_count=0,
            limit_break_count=1,
            stocks=[
                _stock("leader", "002837", "英维克", "70", "缩量", "观察", "非主板参考", "watch-only"),
                _stock("mainboard_mapping", "603912", "佳力图", "62", "弱修复", "一般", "主板映射但 RS 偏弱", "降级观察"),
            ],
        ),
        ChainSectorWorkspace(
            sector_id="power",
            label="电源连接器",
            sector_index="电源连接器指数",
            price_change_pct=Decimal("0.021"),
            turnover_cny=Decimal("23800000000"),
            volume_ratio=Decimal("1.20"),
            rs_strength=Decimal("1.25"),
            fund_flow_cny=Decimal("740000000"),
            trend_slope=Decimal("0.08"),
            limit_up_count=2,
            limit_break_count=0,
            stocks=[
                _stock("leader", "002130", "沃尔核材", "88", "强势", "观察", "非主板热度锚", "watch-only"),
                _stock("mainboard_mapping", "600089", "特变电工", "75", "缩量回踩", "较好", "主板可交易映射", "可进入信号漏斗"),
                _stock("watch_only", "301525", "儒竞科技", "66", "波动放大", "观察", "非主板只做观察", "watch-only"),
            ],
        ),
    ]


def build_chain_workspace_snapshot(
    *,
    config: LowAbsorbConfig,
    cost_models: dict[str, CostChainModel],
) -> dict[str, object]:
    active_version = config.active_cost_chain_version if config.active_cost_chain_version in cost_models else "GB300 NVL72"
    active_model = cost_models[active_version]
    sectors = default_chain_sectors()
    return {
        "activeVersion": active_version,
        "sectorTabs": list(SECTOR_TABS),
        "costModels": [model.model_dump(mode="json") for model in cost_models.values()],
        "costTable": [item.model_dump(mode="json") for item in active_model.components],
        "sectors": [sector.model_dump(mode="json") for sector in sectors],
        "topologyNodes": [tab["label"] for tab in SECTOR_TABS if tab["id"] != "cost-overview"],
        "branches": [
            {
                "id": sector.sector_id,
                "name": sector.label,
                "relativeStrength": str(sector.rs_strength),
                "rank": index + 1,
                "slope": str(sector.trend_slope),
                "candidates": len([stock for stock in sector.stocks if stock.role == "mainboard_mapping"]),
                "status": "强势" if sector.rs_strength >= Decimal("1.10") else "中性" if sector.rs_strength >= Decimal("1.00") else "偏弱",
            }
            for index, sector in enumerate(sorted(sectors, key=lambda item: item.rs_strength, reverse=True))
        ],
        "stockMappings": [
            {
                "id": f"{sector.sector_id}-{stock.stock_code}",
                "stockCode": stock.stock_code,
                "stockName": stock.stock_name,
                "branch": sector.label,
                "role": stock.role,
                "signalStatus": stock.current_recommendation,
                "riskLevel": "watch" if stock.current_recommendation != "watch-only" else "normal",
            }
            for sector in sectors
            for stock in sector.stocks
        ],
    }
