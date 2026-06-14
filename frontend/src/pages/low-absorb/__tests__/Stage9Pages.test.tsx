import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LOW_ABSORB_BACKTEST_MOCK } from "@/mocks/lowAbsorb";
import { Backtest } from "../Backtest";
import { Chain } from "../Chain";
import { Sentiment } from "../Sentiment";

describe("Low Absorb Stage 9 pages", () => {
  it("renders sentiment permission gauges, instrument panels, and event streams", async () => {
    render(<Sentiment />);

    expect(await screen.findByText("交易许可系统")).toBeInTheDocument();
    expect(screen.getByText("全球情绪仪表")).toBeInTheDocument();
    expect(screen.getByText("A 股情绪仪表")).toBeInTheDocument();
    expect(screen.getByText("成交额闸门")).toBeInTheDocument();
    expect(screen.getByText("炸板率闸门")).toBeInTheDocument();
    expect(screen.getByText("涨跌家数宽度")).toBeInTheDocument();
    expect(screen.getByText("AI 资金温度")).toBeInTheDocument();
    expect(screen.getByText("全球风险偏好")).toBeInTheDocument();
    expect(screen.getByText("情绪结论")).toBeInTheDocument();
    expect(screen.getByText("社交事件流")).toBeInTheDocument();
    expect(screen.getByText("新闻事件流")).toBeInTheDocument();

    // Fallback data (API fail) shows 观察 with yellow indicator, never 允许
    const observeElements = screen.getAllByText("观察");
    expect(observeElements.length).toBeGreaterThanOrEqual(1);
    // First matching element should have the yellow permission badge class
    expect(observeElements[0].className).toContain("yellow");
    // No 允许 badge should exist in fallback mode
    expect(screen.queryByText("允许")).not.toBeInTheDocument();
  });

  it("renders AI Chain cost overview and sector navigation", async () => {
    render(<Chain />);

    expect(await screen.findByText("英伟达 AI 服务器成本链")).toBeInTheDocument();
    for (const tab of ["成本总览", "GPU/加速卡", "CPO/光模块", "电源连接器"]) {
      expect(screen.getByRole("button", { name: tab })).toBeInTheDocument();
    }
    expect(screen.getByText("成本权重")).toBeInTheDocument();
    expect(screen.getByText("信号权重")).toBeInTheDocument();
  });

  it("switches backtest tabs and renders metric cards plus historical rows", async () => {
    render(<Backtest />);
    const user = userEvent.setup();

    expect(screen.getByText("胜率")).toBeInTheDocument();
    expect(screen.getByText("平均 R")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "历史信号" }));
    const row = screen.getByTestId(`historical-signal-${LOW_ABSORB_BACKTEST_MOCK.historicalSignals[0].id}`);
    expect(within(row).getByText(LOW_ABSORB_BACKTEST_MOCK.historicalSignals[0].stock)).toBeInTheDocument();
    expect(screen.getByText("是否命中止损")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "参数敏感性" }));
    expect(screen.getByRole("heading", { name: "参数敏感性" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "分支归因" }));
    expect(screen.getByRole("heading", { name: "分支归因" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "改进建议" }));
    expect(screen.getByRole("heading", { name: "改进建议" })).toBeInTheDocument();
  });
});
