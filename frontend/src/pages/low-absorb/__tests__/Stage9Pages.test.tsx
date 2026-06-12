import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { LOW_ABSORB_BACKTEST_MOCK, LOW_ABSORB_CHAIN_MOCK } from "@/mocks/lowAbsorb";
import { Backtest } from "../Backtest";
import { Chain } from "../Chain";
import { Sentiment } from "../Sentiment";

describe("Low Absorb Stage 9 pages", () => {
  it("renders sentiment status cards, social preview, and market gate checklist", () => {
    render(<Sentiment />);

    expect(screen.getByText("综合情绪分")).toBeInTheDocument();
    expect(screen.getByText("A 股情绪闸门")).toBeInTheDocument();
    expect(screen.getByText("成交额闸门")).toBeInTheDocument();
    expect(screen.getByText("社交账号监听 preview")).toBeInTheDocument();
    expect(screen.getByText("新闻事件监听 preview")).toBeInTheDocument();
    expect(screen.getByText("情绪规则 preview")).toBeInTheDocument();
  });

  it("renders chain branch strength table and stock mapping table", () => {
    render(<Chain />);

    expect(screen.getByText("AI 成本拓扑 placeholder")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "分支 RS 表" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "个股映射表" })).toBeInTheDocument();
    expect(screen.getAllByText(LOW_ABSORB_CHAIN_MOCK.branches[0].name).length).toBeGreaterThan(0);
    expect(screen.getByText(LOW_ABSORB_CHAIN_MOCK.stockMappings[0].stockName)).toBeInTheDocument();
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
