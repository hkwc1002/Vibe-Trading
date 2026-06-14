import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { lowAbsorbApi } from "@/lib/lowAbsorbApi";
import type {
  LowAbsorbApiSnapshot,
  LowAbsorbChainSnapshot,
  LowAbsorbSentimentSnapshot,
} from "@/types/lowAbsorb";
import { Chain } from "../Chain";
import { Sentiment } from "../Sentiment";
import { Workbench } from "../Workbench";

const FORBIDDEN_STANDALONE_LABELS = ["买入", "卖出", "下单", "自动交易"];

vi.mock("@/lib/lowAbsorbApi", () => ({
  lowAbsorbApi: {
    getSnapshot: vi.fn(),
    scanTail: vi.fn(),
    sendTradePlanToFeishu: vi.fn(),
    recordFill: vi.fn(),
    listPositions: vi.fn(),
    getSentimentSnapshot: vi.fn(),
    getChainSnapshot: vi.fn(),
    patchCostChainModel: vi.fn(),
  },
}));

const api = vi.mocked(lowAbsorbApi);

const API_SNAPSHOT = {
  sentiment: {
    tradingPermission: {
      status: "允许观察",
      nextAction: "执行 14:45 扫描",
      summary: "双情绪时钟允许生成建议",
    },
  },
  signals: [
    {
      signal_id: "sig-601138-20260612",
      trade_date: "2026-06-12",
      stock_code: "601138",
      stock_name: "工业富联",
      branch_name: "服务器ODM",
      grade: "A",
      ma20_deviation_pct: "0.006",
      volume_ratio: "0.60",
      lower_shadow_atr: "0.62",
      reason: "尾盘低吸漏斗通过",
      intercept_reasons: [],
      status: "CANDIDATE",
      chain_explanation: "AI 产业链：服务器ODM 分支 RS 1.18，成本链权重 0.70。",
      branch_strength: "1.18",
      cost_signal_weight: "0.70",
      priority_score: "98.8",
      sector_role: "mainboard_mapping",
    },
    {
      signal_id: "sig-000977-20260612",
      trade_date: "2026-06-12",
      stock_code: "000977",
      stock_name: "浪潮信息",
      branch_name: "服务器ODM",
      grade: "B",
      ma20_deviation_pct: "0.018",
      volume_ratio: "0.92",
      lower_shadow_atr: "0.22",
      reason: "主线相关但技术闸门不足",
      intercept_reasons: ["MA20 偏离超限", "下影线 ATR 不足"],
      status: "INVALIDATED",
      chain_explanation: "AI 产业链：服务器ODM 强，但技术闸门拦截。",
      branch_strength: "1.18",
      cost_signal_weight: "0.70",
      priority_score: "41.0",
      block_reason: "技术过滤未通过",
      sector_role: "mainboard_mapping",
    },
  ],
  trade_plans: [
    {
      plan_id: "plan-601138-20260612",
      signal_id: "sig-601138-20260612",
      trade_date: "2026-06-12",
      stock_code: "601138",
      stock_name: "工业富联",
      entry_low: "19.72",
      entry_high: "20.12",
      stop_loss: "19.50",
      planned_position_pct: "0.12",
      max_risk_pct: "0.005",
      initial_risk_cny: "62.00",
      open_stop_risk_cny: "62.00",
      r_multiple: "0",
      rationale: "生成依据：尾盘低吸漏斗通过。AI 产业链：服务器ODM 分支 RS 1.18，成本链权重 0.70。",
      manual_order_text: "601138 工业富联，人工低吸区间 19.72-20.12，参考止损 19.50。",
      status: "RECOMMENDED",
      chain_explanation: "AI 产业链：服务器ODM 分支 RS 1.18，成本链权重 0.70。",
      branch_strength: "1.18",
      cost_signal_weight: "0.70",
      priority_score: "98.8",
      sector_role: "mainboard_mapping",
    },
  ],
  positions: [
    {
      position_id: "pos-601138-plan-601138-20260612",
      plan_id: "plan-601138-20260612",
      stock_code: "601138",
      stock_name: "工业富联",
      avg_cost: "19.88",
      current_price: "19.70",
      current_stop_price: "19.50",
      quantity: 1000,
      position_weight: "0.12",
      status: "ACTIVE_POSITION",
      notes: ["10:00 需监督"],
    },
  ],
  risk_matrix: [
    {
      position_id: "pos-601138-plan-601138-20260612",
      stock_code: "601138",
      stock_name: "工业富联",
      initial_risk_amount: "380.00",
      current_risk_amount: "380.00",
      r_multiple: "-0.47",
      risk_level: "warning",
      needs_supervision: true,
      supervision_status: "10:00 需监督",
    },
  ],
  notifications: [],
  reports: [],
} satisfies LowAbsorbApiSnapshot;

const SENTIMENT_SNAPSHOT = {
  tradingPermission: {
    status: "允许观察",
    summary: "双情绪时钟用于决定是否允许生成主板低吸人工交易建议。",
    nextAction: "执行 14:45 扫描",
  },
  gauges: [
    { id: "global", label: "全球情绪", score: 62, status: "中性偏暖", detail: "海外科技风险未形成明显压制。" },
    { id: "a_share", label: "A 股情绪", score: 71, status: "允许观察", detail: "成交额达标，炸板率低于阈值。" },
  ],
  instrumentPanels: [
    { id: "market_turnover", label: "成交额闸门", value: "612000000000", status: "通过", explanation: "两市成交额必须超过配置阈值。" },
    { id: "limit_break", label: "炸板率闸门", value: "0.20", status: "通过", explanation: "炸板率过高时暂停生成新计划。" },
    { id: "advance_decline", label: "涨跌家数宽度", value: "3120 / 1790", status: "观察", explanation: "上涨家数占优。" },
    { id: "ai_capital_temperature", label: "AI 资金温度", value: "73", status: "通过", explanation: "AI 链资金温度高于全市场。" },
    { id: "global_risk_appetite", label: "全球风险偏好", value: "62", status: "观察", explanation: "全球风险偏好中性。" },
    { id: "sentiment_conclusion", label: "情绪结论", value: "允许观察", status: "允许观察", explanation: "只允许生成建议。" },
  ],
  socialEvents: [
    { id: "social-ai-server", time: "14:20", source: "社交监控", title: "AI 服务器讨论热度延续", impact: "提高主线观察权重" },
  ],
  newsEvents: [
    { id: "news-power", time: "14:05", source: "新闻监控", title: "电源连接器成本占比受关注", impact: "纳入成本链权重观察" },
  ],
} satisfies LowAbsorbSentimentSnapshot;

const CHAIN_SNAPSHOT = {
  activeVersion: "GB300 NVL72",
  sectorTabs: [
    { id: "cost-overview", label: "成本总览" },
    { id: "gpu", label: "GPU/加速卡" },
    { id: "hbm", label: "HBM/存储" },
    { id: "cpo", label: "CPO/光模块" },
    { id: "pcb", label: "PCB/高速板" },
    { id: "odm", label: "服务器ODM" },
    { id: "cooling", label: "液冷散热" },
    { id: "power", label: "电源连接器" },
  ],
  costModels: [
    { version: "GB300 NVL72", is_editable: false, components: [] },
    { version: "custom/manual", is_editable: true, components: [] },
  ],
  costTable: [
    {
      component: "服务器ODM",
      cost_weight: "0.16",
      cost_weight_range: ["0.12", "0.18"],
      cost_increase_vs_previous_generation: "0.08",
      related_sector: "服务器ODM",
      a_share_leaders: ["工业富联", "中科曙光"],
      tradable_mainboard_mapping: ["601138", "603019"],
      signal_weight: "0.70",
      data_source: "后端示例",
      source_type: "broker_estimate",
      source_url: "https://example.com/research",
      source_title: "Morgan Stanley 转述估算",
      confidence: "medium",
      is_estimated: true,
      methodology_note: "来源分级：官方规格 + 券商估算",
      as_of: "2026-06-13",
    },
  ],
  sectors: [
    {
      sector_id: "cpo",
      label: "CPO/光模块",
      sector_index: "光模块指数",
      price_change_pct: "0.024",
      turnover_cny: "51200000000",
      volume_ratio: "1.32",
      rs_strength: "1.31",
      fund_flow_cny: "1660000000",
      trend_slope: "0.10",
      limit_up_count: 3,
      limit_break_count: 1,
      stocks: [
        {
          role: "leader",
          stock_code: "300308",
          stock_name: "中际旭创",
          strength_score: "92",
          volume_condition: "强趋势",
          low_absorb_suitability: "观察",
          reason: "非主板龙头用于热度锚定",
          current_recommendation: "watch-only",
        },
        {
          role: "core_middle_cap",
          stock_code: "600522",
          stock_name: "中天科技",
          strength_score: "73",
          volume_condition: "缩量承接",
          low_absorb_suitability: "较好",
          reason: "主板可映射",
          current_recommendation: "可进入信号漏斗",
        },
      ],
    },
  ],
} satisfies LowAbsorbChainSnapshot;

function expectNoStandaloneExecutionLabels() {
  for (const label of FORBIDDEN_STANDALONE_LABELS) {
    expect(screen.queryByRole("button", { name: label })).not.toBeInTheDocument();
  }
}

describe("Low Absorb decision dashboards", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getSnapshot.mockResolvedValue(API_SNAPSHOT);
    api.scanTail.mockResolvedValue(API_SNAPSHOT);
    api.sendTradePlanToFeishu.mockResolvedValue({ ok: false, message: "missing webhook" } as never);
    api.recordFill.mockResolvedValue({ fill: {}, position: API_SNAPSHOT.positions[0], risk: API_SNAPSHOT.risk_matrix[0] });
    api.getSentimentSnapshot.mockResolvedValue(SENTIMENT_SNAPSHOT);
    api.getChainSnapshot.mockResolvedValue(CHAIN_SNAPSHOT);
    api.patchCostChainModel.mockResolvedValue({ version: "custom/manual", components: CHAIN_SNAPSHOT.costTable });
  });

  it("renders Workbench overview as a trade command center", async () => {
    render(<Workbench />);

    expect(await screen.findByText("交易许可")).toBeInTheDocument();
    expect(screen.getAllByText("当前状态").length).toBeGreaterThan(0);
    expect(screen.getAllByText("关键指标").length).toBeGreaterThan(0);
    expect(screen.getAllByText("趋势变化").length).toBeGreaterThan(0);
    expect(screen.getAllByText("下一步").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "优先任务队列" })).toBeInTheDocument();
    expect(screen.getByText("A 级计划待推送飞书")).toBeInTheDocument();
    expect(screen.getByText("成交待回填")).toBeInTheDocument();
    expect(screen.getAllByText("10:00 监督").length).toBeGreaterThan(0);
    expect(screen.getByRole("heading", { name: "重点候选" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "高风险持仓" })).toBeInTheDocument();
    expectNoStandaloneExecutionLabels();
  });

  it("renders signal dashboard before the detailed table", async () => {
    render(<Workbench />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "今日信号" }));

    expect(screen.getByText("信号漏斗")).toBeInTheDocument();
    for (const stage of ["股票池", "宏观闸门", "产业链闸门", "主板过滤", "技术过滤", "交易计划"]) {
      expect(screen.getAllByText(stage).length).toBeGreaterThan(0);
    }
    expect(screen.getByText("A 级信号")).toBeInTheDocument();
    expect(screen.getByText("B 级信号")).toBeInTheDocument();
    expect(screen.getByText("拒绝原因")).toBeInTheDocument();
    expect(screen.getByText("最佳候选卡")).toBeInTheDocument();
    expect(screen.getByText("信号雷达")).toBeInTheDocument();
    expect(screen.getByTestId("signal-row-sig-601138-20260612")).toBeInTheDocument();
  });

  it("renders position risk dashboard before the risk matrix", async () => {
    render(<Workbench />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "人工持仓" }));

    expect(screen.getByText("组合风险仪表")).toBeInTheDocument();
    expect(screen.getByText("开放风险卡")).toBeInTheDocument();
    expect(screen.getByText("风险热力条")).toBeInTheDocument();
    expect(screen.getByText("早盘监督面板")).toBeInTheDocument();
    expect(screen.getAllByText("初始风险").length).toBeGreaterThan(0);
    expect(screen.getAllByText("当前风险").length).toBeGreaterThan(0);
    expect(screen.getAllByText("R 倍数").length).toBeGreaterThan(0);
    expect(screen.getAllByText("止损距离").length).toBeGreaterThan(0);
    expect(screen.getByTestId("position-row-pos-601138-plan-601138-20260612")).toBeInTheDocument();
  });

  it("shows AI Chain explanation in trade plan detail", async () => {
    render(<Workbench />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "交易计划" }));

    expect(screen.getByText("AI 产业链解释")).toBeInTheDocument();
    expect(screen.getAllByText(/成本链权重 0.70/).length).toBeGreaterThan(0);
    expectNoStandaloneExecutionLabels();
  });

  it("renders market sentiment as a trading permission system", async () => {
    render(<Sentiment />);

    expect(await screen.findByText("交易许可系统")).toBeInTheDocument();
    expect(screen.getByText("全球情绪仪表")).toBeInTheDocument();
    expect(screen.getByText("A 股情绪仪表")).toBeInTheDocument();
    for (const label of ["成交额闸门", "炸板率闸门", "涨跌家数宽度", "AI 资金温度", "全球风险偏好", "情绪结论"]) {
      expect(screen.getByText(label)).toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { name: "社交事件流" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "新闻事件流" })).toBeInTheDocument();
  });

  it("renders AI Chain internal navigation and sector research workspace", async () => {
    render(<Chain />);
    const user = userEvent.setup();

    expect(await screen.findByText("英伟达 AI 服务器成本链")).toBeInTheDocument();
    expect(screen.getByText("GB300 NVL72")).toBeInTheDocument();
    expect(screen.getByText("自定义/手动")).toBeInTheDocument();
    expect(screen.getByText("成本权重")).toBeInTheDocument();
    expect(screen.getByText("信号权重")).toBeInTheDocument();
    expect(screen.getByText("来源与置信度")).toBeInTheDocument();
    expect(await screen.findByText("券商估算")).toBeInTheDocument();
    expect(screen.getByText("中")).toBeInTheDocument();
    expect(screen.getByText("估算")).toBeInTheDocument();

    for (const label of CHAIN_SNAPSHOT.sectorTabs.map((tab) => tab.label)) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }

    await user.click(screen.getByRole("button", { name: "CPO/光模块" }));
    expect(screen.getByText(/板块指数/)).toBeInTheDocument();
    expect(screen.getAllByText("RS 强度").length).toBeGreaterThan(0);
    expect(screen.getByText("龙头")).toBeInTheDocument();
    expect(screen.getByText("中军")).toBeInTheDocument();
    expect(within(screen.getByTestId("chain-sector-cpo")).getByText("中天科技")).toBeInTheDocument();
    expectNoStandaloneExecutionLabels();
  });
});
