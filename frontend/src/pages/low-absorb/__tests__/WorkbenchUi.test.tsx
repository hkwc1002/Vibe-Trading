import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LOW_ABSORB_MOCK } from "@/mocks/lowAbsorb";
import { Workbench } from "../Workbench";

const FORBIDDEN_STANDALONE_LABELS = ["买入", "卖出", "下单", "自动交易"];

function expectNoStandaloneExecutionLabels() {
  for (const label of FORBIDDEN_STANDALONE_LABELS) {
    expect(screen.queryByRole("button", { name: label })).not.toBeInTheDocument();
  }
}

describe("Low Absorb Workbench UI", () => {
  it("renders the overview dashboard with task, candidate, and risk sections", () => {
    render(<Workbench />);

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
    expect(screen.getAllByText(LOW_ABSORB_MOCK.signals[0].stockName).length).toBeGreaterThan(0);
    expectNoStandaloneExecutionLabels();
  });

  it("switches tabs and renders fixture rows", async () => {
    render(<Workbench />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "今日信号" }));
    expect(screen.getAllByRole("heading", { name: "今日信号" }).length).toBeGreaterThan(0);
    const signalRow = screen.getByTestId(`signal-row-${LOW_ABSORB_MOCK.signals[0].id}`);
    expect(within(signalRow).getByText(LOW_ABSORB_MOCK.signals[0].stockCode)).toBeInTheDocument();
    expect(within(signalRow).getByText(LOW_ABSORB_MOCK.signals[0].stockName)).toBeInTheDocument();
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
    const positionRow = screen.getByTestId(`position-row-${LOW_ABSORB_MOCK.positions[0].id}`);
    expect(within(positionRow).getByText(LOW_ABSORB_MOCK.positions[0].stockName)).toBeInTheDocument();
    expect(screen.getByText("R 倍数")).toBeInTheDocument();
    expect(screen.getAllByText("记录卖出").length).toBeGreaterThan(0);
    expect(screen.getAllByText("调整备注").length).toBeGreaterThan(0);
    expect(screen.getAllByText("生成风控提醒").length).toBeGreaterThan(0);
    expect(screen.getAllByText("归档持仓").length).toBeGreaterThan(0);
    expectNoStandaloneExecutionLabels();
  });

  it("renders manual fill and Feishu preview surfaces without backend connections", async () => {
    render(<Workbench />);
    const user = userEvent.setup();

    await user.click(screen.getByRole("button", { name: "交易计划" }));

    expect(screen.getByText("飞书推荐预览")).toBeInTheDocument();
    expect(screen.getByText("人工成交记录")).toBeInTheDocument();
    expect(screen.getByText("仅使用本地 mock 数据，暂未连接后端服务。")).toBeInTheDocument();
    expect(screen.getByText(LOW_ABSORB_MOCK.tradePlans[0].feishuPreview.title)).toBeInTheDocument();
  });
});
