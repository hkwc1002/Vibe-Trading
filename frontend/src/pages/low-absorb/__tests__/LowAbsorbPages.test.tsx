import { render, screen } from "@testing-library/react";
import { vi } from "vitest";

import { Backtest } from "../Backtest";
import { Chain } from "../Chain";
import { Reports } from "../Reports";
import { Sentiment } from "../Sentiment";
import { Settings } from "../Settings";

vi.mock("@/lib/lowAbsorbApi", () => ({
  lowAbsorbApi: {
    getSettings: vi.fn().mockResolvedValue({
      config: {
        min_market_turnover_cny: "500000000000",
        max_limit_break_rate: "0.45",
        ma20_deviation_min: "0",
        ma20_deviation_max: "0.012",
        max_volume_ratio_5d: "0.65",
        min_lower_shadow_atr: "0.5",
        data_provider_mode: "auto",
        global_market_provider: "yfinance",
        eastmoney_min_interval_seconds: "1.0",
        enable_fixture_fallback: true,
      },
      maskedWebhook: null,
      webhookConfigured: false,
    }),
    patchSettings: vi.fn(),
    sendTestNotification: vi.fn(),
    getSentimentSnapshot: vi.fn().mockResolvedValue({
      tradingPermission: {
        status: "允许观察",
        summary: "双情绪时钟用于决定是否允许生成主板低吸人工交易建议。",
        nextAction: "执行 14:45 扫描",
      },
      gauges: [
        { id: "global", label: "全球情绪仪表", value: 68, status: "risk-on", detail: "外盘风险偏好温和" },
        { id: "a-share", label: "A 股情绪仪表", value: 61, status: "watch", detail: "A 股可观察" },
      ],
      instrumentPanels: [
        { id: "turnover", label: "成交额闸门", status: "pass", value: "5,400 亿", detail: "成交额达标" },
        { id: "break", label: "炸板率闸门", status: "pass", value: "31%", detail: "炸板率可控" },
        { id: "breadth", label: "涨跌家数宽度", status: "watch", value: "1.25", detail: "涨跌家数温和" },
        { id: "capital", label: "AI 资金温度", status: "pass", value: "偏热", detail: "AI 链资金活跃" },
        { id: "global-risk", label: "全球风险偏好", status: "pass", value: "风险偏好上行", detail: "全球风险偏好支持" },
        { id: "conclusion", label: "情绪结论", status: "watch", value: "允许观察", detail: "允许生成建议但需人工确认" },
      ],
      socialEvents: [{ time: "14:20", source: "社交账号", title: "AI 服务器讨论升温", severity: "medium" }],
      newsEvents: [{ time: "13:50", source: "新闻", title: "产业链订单预期改善", severity: "low" }],
    }),
    getChainSnapshot: vi.fn().mockResolvedValue({
      activeVersion: "GB300 NVL72",
      sectorTabs: [
        "成本总览",
        "GPU/加速卡",
        "HBM/存储",
        "CPO/光模块",
        "PCB/高速板",
        "服务器ODM",
        "液冷散热",
        "电源连接器",
      ],
      costModels: [
        { version: "GB300 NVL72", is_editable: false, components: [] },
        { version: "custom/manual", is_editable: true, components: [] },
      ],
      costTable: [
        {
          component: "服务器ODM",
          cost_weight: "0.16",
          cost_increase_vs_previous_generation: "0.08",
          related_sector: "服务器ODM",
          a_share_leaders: ["工业富联"],
          tradable_mainboard_mapping: ["601138"],
          signal_weight: "0.70",
          data_source: "后端示例",
          as_of: "2026-06-13",
        },
      ],
      sectors: [],
    }),
    patchCostChainModel: vi.fn(),
  },
}));

const FORBIDDEN_ACTION_LABELS = ["买入", "卖出", "下单", "自动交易"];

function expectNoBrokerExecutionLabels() {
  for (const label of FORBIDDEN_ACTION_LABELS) {
    expect(screen.queryByRole("button", { name: label })).not.toBeInTheDocument();
  }
}

describe("AI Low Absorb pages", () => {
  it.each([
    [
      Sentiment,
      "市场情绪",
      "将双情绪时钟作为交易许可系统，明确说明今天是否允许生成主板低吸人工交易建议。",
    ],
    [
      Chain,
      "AI 产业链",
      "以英伟达 AI 服务器成本链为核心的板块研究工作台，输出会反馈到交易工作台的信号排序和交易计划解释。",
    ],
    [
      Backtest,
      "策略回测",
      "展示低吸策略回测指标、参数、历史信号、敏感性、分支归因和改进建议的示例工作区。",
    ],
    [Reports, "复盘报告", "展示收盘报告、人工成交复盘和策略复盘材料的占位工作区。"],
    [Settings, "系统设置", "管理低吸扫描阈值、数据源、飞书通知和人工执行工作台偏好。"],
  ])("renders the %s shell", async (Page, title, description) => {
    render(<Page />);

    expect(await screen.findByRole("heading", { name: title })).toBeInTheDocument();
    expect(await screen.findByText(description)).toBeInTheDocument();
    expectNoBrokerExecutionLabels();
  });

  it.each([[Reports]])("keeps placeholder cards on unfinished pages", (Page) => {
    render(<Page />);

    expect(screen.getAllByTestId("low-absorb-placeholder-card")).toHaveLength(3);
    expect(screen.getByText("暂无业务数据接入")).toBeInTheDocument();
  });
});
