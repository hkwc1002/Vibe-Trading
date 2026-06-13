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
      },
      maskedWebhook: null,
      webhookConfigured: false,
    }),
    patchSettings: vi.fn(),
    sendTestNotification: vi.fn(),
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
    [Sentiment, "市场情绪", "展示宏观情绪闸门、A 股风险偏好、全球风险偏好和未来监听接口的 mock 工作区。"],
    [Chain, "AI 产业链", "展示 AI 产业链分支强弱、成本拓扑占位和个股映射表，作为后续真实产业链 API 的前端 contract。"],
    [Backtest, "策略回测", "展示低吸策略回测指标、参数、历史信号、敏感性、分支归因和改进建议的 mock 工作区。"],
    [Reports, "复盘报告", "展示收盘报告、人工成交复盘和策略复盘材料的占位工作区。"],
    [Settings, "系统设置", "管理低吸扫描阈值、飞书通知和人工执行工作台偏好。"],
  ])("renders the %s shell", (Page, title, description) => {
    render(<Page />);

    expect(screen.getByRole("heading", { name: title })).toBeInTheDocument();
    expect(screen.getByText(description)).toBeInTheDocument();
    expectNoBrokerExecutionLabels();
  });

  it.each([[Reports]])("keeps placeholder cards on unfinished pages", (Page) => {
    render(<Page />);

    expect(screen.getAllByTestId("low-absorb-placeholder-card")).toHaveLength(3);
    expect(screen.getByText("暂无业务数据接入")).toBeInTheDocument();
  });
});
