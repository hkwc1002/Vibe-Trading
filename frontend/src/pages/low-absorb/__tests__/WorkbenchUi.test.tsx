import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { LOW_ABSORB_MOCK } from "@/mocks/lowAbsorb";
import { lowAbsorbApi } from "@/lib/lowAbsorbApi";
import type { LowAbsorbApiSnapshot } from "@/types/lowAbsorb";
import { Workbench } from "../Workbench";

const FORBIDDEN_STANDALONE_LABELS = ["买入", "卖出", "下单", "自动交易"];

vi.mock("@/lib/lowAbsorbApi", () => ({
  lowAbsorbApi: {
    getSnapshot: vi.fn(),
    scanTail: vi.fn(),
    sendTradePlanToFeishu: vi.fn(),
    recordFill: vi.fn(),
    listPositions: vi.fn(),
  },
}));

const api = vi.mocked(lowAbsorbApi);

const API_SIGNAL = {
  signal_id: "sig-601138-20260612",
  trade_date: "2026-06-12",
  stock_code: "601138",
  stock_name: "工业富联",
  branch_name: "AI 服务器",
  grade: "A",
  ma20_deviation_pct: "0.006",
  volume_ratio: "0.60",
  lower_shadow_atr: "0.62",
  reason: "尾盘低吸漏斗通过",
  intercept_reasons: [],
  status: "CANDIDATE",
};

const API_PLAN = {
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
  rationale: "生成依据：尾盘低吸漏斗通过",
  manual_order_text: "601138 工业富联，人工低吸区间 19.72-20.12，参考止损 19.50。",
  status: "RECOMMENDED",
};

const API_POSITION = {
  position_id: "pos-601138-plan-601138-20260612",
  plan_id: "plan-601138-20260612",
  stock_code: "601138",
  stock_name: "工业富联",
  avg_cost: "19.88",
  current_price: "20.10",
  current_stop_price: "19.50",
  quantity: 1000,
  position_weight: "0.12",
  status: "ACTIVE_POSITION",
  notes: ["人工成交已回填"],
};

const API_RISK = {
  position_id: "pos-601138-plan-601138-20260612",
  stock_code: "601138",
  stock_name: "工业富联",
  initial_risk_amount: "380.00",
  current_risk_amount: "380.00",
  r_multiple: "0.58",
  risk_level: "warning" as const,
  needs_supervision: true,
  supervision_status: "10:00 需监督",
};

const API_SNAPSHOT = {
  signals: [API_SIGNAL],
  trade_plans: [API_PLAN],
  positions: [API_POSITION],
  risk_matrix: [API_RISK],
  notifications: [],
  reports: [],
} satisfies LowAbsorbApiSnapshot;

function expectNoStandaloneExecutionLabels() {
  for (const label of FORBIDDEN_STANDALONE_LABELS) {
    expect(screen.queryByRole("button", { name: label })).not.toBeInTheDocument();
  }
}

describe("Low Absorb Workbench UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getSnapshot.mockResolvedValue(API_SNAPSHOT);
    api.scanTail.mockResolvedValue(API_SNAPSHOT);
    api.sendTradePlanToFeishu.mockResolvedValue({
      notification_id: "fs-1",
      ok: false,
      notification_type: "BUY_RECOMMENDATION",
      idempotency_key: "k",
      sent_at: null,
      skipped: false,
      error: "missing webhook",
      sent: false,
      message: "missing webhook",
    });
    api.recordFill.mockResolvedValue({ fill: {}, position: API_POSITION, risk: API_RISK });
    api.listPositions.mockResolvedValue([API_POSITION]);
  });

  it("loads the API snapshot on mount and renders overview sections", async () => {
    render(<Workbench />);

    expect((await screen.findAllByText("工业富联")).length).toBeGreaterThan(0);
    expect(api.getSnapshot).toHaveBeenCalledTimes(1);
    for (const label of [
      "市场状态",
      "今日信号",
      "待推送飞书",
      "待成交回填",
      "当前持仓风险",
      "明日 10:00 需监督",
    ]) {
      expect(screen.getAllByText(label).length).toBeGreaterThan(0);
    }

    expect(screen.getByRole("heading", { name: "今日待处理事项" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "重点候选" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "持仓风险摘要" })).toBeInTheDocument();
    expect(screen.getAllByText("工业富联").length).toBeGreaterThan(0);
    expectNoStandaloneExecutionLabels();
  });

  it("triggers scan-tail and refreshes API-backed signal rows", async () => {
    render(<Workbench />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "执行 14:45 扫描" }));
    expect(api.scanTail).toHaveBeenCalledTimes(1);

    await user.click(screen.getByRole("button", { name: "今日信号" }));
    expect(screen.getAllByRole("heading", { name: "今日信号" }).length).toBeGreaterThan(0);
    const signalRow = screen.getByTestId("signal-row-sig-601138-20260612");
    expect(within(signalRow).getByText("601138")).toBeInTheDocument();
    expect(within(signalRow).getByText("工业富联")).toBeInTheDocument();
    expect(screen.getAllByRole("button", { name: "生成交易计划" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "推送飞书" }).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("button", { name: "标记失效" }).length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "交易计划" }));
    expect(screen.getByRole("heading", { name: "交易计划" })).toBeInTheDocument();
    expect(screen.getAllByText("建议低吸区间").length).toBeGreaterThan(0);
    expect(screen.getAllByText("复制人工下单信息").length).toBeGreaterThan(0);
    expect(screen.getAllByText("记录人工成交").length).toBeGreaterThan(0);
    expect(screen.getAllByText("作废计划").length).toBeGreaterThan(0);

    await user.click(screen.getByRole("button", { name: "人工持仓" }));
    expect(screen.getAllByRole("heading", { name: "人工持仓" }).length).toBeGreaterThan(0);
    const positionRow = screen.getByTestId("position-row-pos-601138-plan-601138-20260612");
    expect(within(positionRow).getByText("工业富联")).toBeInTheDocument();
    expect(screen.getByText("R 倍数")).toBeInTheDocument();
    expect(screen.getAllByText("记录卖出").length).toBeGreaterThan(0);
    expect(screen.getAllByText("调整备注").length).toBeGreaterThan(0);
    expect(screen.getAllByText("生成风控提醒").length).toBeGreaterThan(0);
    expect(screen.getAllByText("归档持仓").length).toBeGreaterThan(0);
    expectNoStandaloneExecutionLabels();
  });

  it("opens detail drawer, sends Feishu recommendation, and records manual fill through the API", async () => {
    render(<Workbench />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "交易计划" }));
    await user.click(screen.getAllByRole("button", { name: "推送飞书" })[0]);

    expect(api.sendTradePlanToFeishu).toHaveBeenCalledWith("plan-601138-20260612");

    expect(screen.getByText("飞书推荐预览")).toBeInTheDocument();
    expect(screen.getByText("人工成交记录")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "交易计划详情" })).toBeInTheDocument();
    expect(screen.getByText("统一动作")).toBeInTheDocument();

    await user.clear(screen.getByLabelText("成交价格"));
    await user.type(screen.getByLabelText("成交价格"), "19.88");
    await user.clear(screen.getByLabelText("成交数量"));
    await user.type(screen.getByLabelText("成交数量"), "1000");
    await user.click(screen.getByRole("button", { name: "提交人工成交记录" }));

    expect(api.recordFill).toHaveBeenCalledWith(
      expect.objectContaining({
        plan_id: "plan-601138-20260612",
        stock_code: "601138",
        stock_name: "工业富联",
        actual_price: "19.88",
        quantity: 1000,
      }),
    );
    expect(api.getSnapshot).toHaveBeenCalledTimes(2);
  });

  it("falls back to demo mock data when the API snapshot fails", async () => {
    api.getSnapshot.mockRejectedValueOnce(new Error("offline"));

    render(<Workbench />);

    expect(await screen.findByText("演示数据模式")).toBeInTheDocument();
    expect(screen.getAllByText(LOW_ABSORB_MOCK.signals[0].stockName).length).toBeGreaterThan(0);
  });
});
