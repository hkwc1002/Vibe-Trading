import { render, screen, within } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { Layout } from "../Layout";

vi.mock("@/lib/api", () => ({
  api: {
    listSessions: vi.fn().mockResolvedValue([]),
    deleteSession: vi.fn().mockResolvedValue({ status: "ok" }),
    renameSession: vi.fn().mockResolvedValue({ status: "ok" }),
  },
}));

describe("Layout AI Low Absorb navigation", () => {
  it("renders a grouped navigation section with all manual-execution pages", async () => {
    render(
      <MemoryRouter initialEntries={["/low-absorb"]}>
        <Layout />
      </MemoryRouter>,
    );

    const group = screen.getByLabelText("AI 主板低吸导航");
    expect(within(group).getByText("AI 主板低吸")).toBeInTheDocument();

    const expectedLinks = [
      ["交易工作台", "/low-absorb"],
      ["市场情绪", "/low-absorb/sentiment"],
      ["AI 产业链", "/low-absorb/chain"],
      ["策略回测", "/low-absorb/backtest"],
      ["复盘报告", "/low-absorb/reports"],
      ["系统设置", "/low-absorb/settings"],
    ];

    for (const [label, href] of expectedLinks) {
      const link = within(group).getByRole("link", { name: label });
      expect(link).toHaveAttribute("href", href);
    }
  });
});
