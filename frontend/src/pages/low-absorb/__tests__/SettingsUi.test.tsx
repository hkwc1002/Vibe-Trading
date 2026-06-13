import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { vi } from "vitest";

import { lowAbsorbApi } from "@/lib/lowAbsorbApi";
import { Settings } from "../Settings";

vi.mock("@/lib/lowAbsorbApi", () => ({
  lowAbsorbApi: {
    getSettings: vi.fn(),
    patchSettings: vi.fn(),
    sendTestNotification: vi.fn(),
  },
}));

const api = vi.mocked(lowAbsorbApi);

const SETTINGS = {
  config: {
    min_market_turnover_cny: "500000000000",
    max_limit_break_rate: "0.45",
    ma20_deviation_min: "0",
    ma20_deviation_max: "0.012",
    max_volume_ratio_5d: "0.65",
    min_lower_shadow_atr: "0.5",
  },
  maskedWebhook: "https://open.feishu.cn/open-apis/bot/v2/hook/****",
  webhookConfigured: true,
};

describe("Low Absorb Settings UI", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getSettings.mockResolvedValue(SETTINGS);
    api.patchSettings.mockResolvedValue({
      ...SETTINGS,
      config: { ...SETTINGS.config, max_limit_break_rate: "0.33" },
    });
    api.sendTestNotification.mockResolvedValue({
      notification_id: "fs-test",
      ok: false,
      notification_type: "NOTIFIER_TEST",
      idempotency_key: "notifier-test",
      sent_at: null,
      skipped: false,
      error: "missing webhook",
      sent: false,
      message: "missing webhook",
    });
  });

  it("loads masked webhook and editable core thresholds", async () => {
    render(<Settings />);

    expect(await screen.findByText("https://open.feishu.cn/open-apis/bot/v2/hook/****")).toBeInTheDocument();
    expect(screen.getByLabelText("两市成交额下限")).toHaveValue("500000000000");
    expect(screen.getByLabelText("炸板率上限")).toHaveValue("0.45");
    expect(screen.queryByText("secret-token")).not.toBeInTheDocument();
  });

  it("updates webhook and thresholds without exposing the full webhook after save", async () => {
    render(<Settings />);
    const user = userEvent.setup();

    await screen.findByLabelText("飞书 Webhook");
    await user.type(screen.getByLabelText("飞书 Webhook"), "https://open.feishu.cn/open-apis/bot/v2/hook/secret-token");
    await user.clear(screen.getByLabelText("炸板率上限"));
    await user.type(screen.getByLabelText("炸板率上限"), "0.33");
    await user.click(screen.getByRole("button", { name: "保存设置" }));

    expect(api.patchSettings).toHaveBeenCalledWith({
      feishu_webhook: "https://open.feishu.cn/open-apis/bot/v2/hook/secret-token",
      config: expect.objectContaining({ max_limit_break_rate: "0.33" }),
    });
    expect(screen.queryByDisplayValue("https://open.feishu.cn/open-apis/bot/v2/hook/secret-token")).not.toBeInTheDocument();
    expect(screen.getByText("https://open.feishu.cn/open-apis/bot/v2/hook/****")).toBeInTheDocument();
  });

  it("sends a notifier test card from the settings page", async () => {
    render(<Settings />);
    const user = userEvent.setup();

    await user.click(await screen.findByRole("button", { name: "发送测试通知" }));

    expect(api.sendTestNotification).toHaveBeenCalledTimes(1);
    expect(screen.getByText("missing webhook")).toBeInTheDocument();
  });
});
