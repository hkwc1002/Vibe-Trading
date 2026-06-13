import { useEffect, useState } from "react";
import { Bell, Send, SlidersHorizontal, Webhook } from "lucide-react";
import { lowAbsorbApi } from "@/lib/lowAbsorbApi";
import type { LowAbsorbApiSettings } from "@/types/lowAbsorb";
import { LowAbsorbPageShell } from "./shared";

const THRESHOLDS = [
  ["min_market_turnover_cny", "两市成交额下限"],
  ["max_limit_break_rate", "炸板率上限"],
  ["ma20_deviation_min", "MA20 偏离下限"],
  ["ma20_deviation_max", "MA20 偏离上限"],
  ["max_volume_ratio_5d", "5 日量比上限"],
  ["min_lower_shadow_atr", "下影线 ATR 下限"],
] as const;

function configToForm(config: Record<string, unknown>): Record<string, string> {
  return Object.fromEntries(THRESHOLDS.map(([key]) => [key, String(config[key] ?? "")]));
}

export function Settings() {
  const [settings, setSettings] = useState<LowAbsorbApiSettings | null>(null);
  const [webhook, setWebhook] = useState("");
  const [thresholds, setThresholds] = useState<Record<string, string>>({});
  const [message, setMessage] = useState("");

  useEffect(() => {
    let alive = true;
    lowAbsorbApi.getSettings().then((value) => {
      if (!alive) return;
      setSettings(value);
      setThresholds(configToForm(value.config));
    }).catch((error) => {
      if (!alive) return;
      setMessage(error instanceof Error ? error.message : "设置加载失败");
    });
    return () => {
      alive = false;
    };
  }, []);

  async function saveSettings() {
    const next = await lowAbsorbApi.patchSettings({
      ...(webhook ? { feishu_webhook: webhook } : {}),
      config: thresholds,
    });
    setSettings(next);
    setThresholds(configToForm(next.config));
    setWebhook("");
    setMessage("设置已保存");
  }

  async function sendTestNotification() {
    const result = await lowAbsorbApi.sendTestNotification();
    setMessage(result.message || result.error || "测试通知已处理");
  }

  return (
    <LowAbsorbPageShell
      title="系统设置"
      description="管理低吸扫描阈值、飞书通知和人工执行工作台偏好。"
    >
      <section className="grid gap-4 lg:grid-cols-[1fr_360px]">
        <div className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <div className="mb-4 flex items-center gap-2">
              <SlidersHorizontal className="h-4 w-4 text-primary" aria-hidden="true" />
              <h2 className="text-base font-semibold text-foreground">核心阈值</h2>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {THRESHOLDS.map(([key, label]) => (
                <label key={key} className="grid gap-1 text-sm">
                  <span className="text-xs font-medium text-muted-foreground">{label}</span>
                  <input
                    aria-label={label}
                    value={thresholds[key] ?? ""}
                    onChange={(event) => setThresholds((current) => ({ ...current, [key]: event.target.value }))}
                    className="rounded-md border bg-background px-3 py-2 text-foreground"
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="rounded-lg border bg-card p-4">
            <div className="mb-4 flex items-center gap-2">
              <Webhook className="h-4 w-4 text-primary" aria-hidden="true" />
              <h2 className="text-base font-semibold text-foreground">飞书通知</h2>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border bg-background p-3 text-sm">
                <p className="text-xs text-muted-foreground">当前 Webhook</p>
                <p className="mt-1 break-all font-mono text-foreground">{settings?.maskedWebhook ?? "未配置"}</p>
              </div>
              <label className="grid gap-1 text-sm">
                <span className="text-xs font-medium text-muted-foreground">飞书 Webhook</span>
                <input
                  aria-label="飞书 Webhook"
                  value={webhook}
                  onChange={(event) => setWebhook(event.target.value)}
                  placeholder="粘贴新的 webhook，保存后仅显示掩码"
                  className="rounded-md border bg-background px-3 py-2 text-foreground"
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <button type="button" onClick={() => void saveSettings()} className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
                  保存设置
                </button>
                <button type="button" onClick={() => void sendTestNotification()} className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted">
                  <Send className="h-4 w-4" aria-hidden="true" />
                  发送测试通知
                </button>
              </div>
            </div>
          </div>
        </div>

        <aside className="space-y-4">
          <div className="rounded-lg border bg-card p-4">
            <div className="mb-3 flex items-center gap-2">
              <Bell className="h-4 w-4 text-primary" aria-hidden="true" />
              <h2 className="text-base font-semibold text-foreground">状态</h2>
            </div>
            <dl className="grid gap-3 text-sm">
              <div className="rounded-md border bg-background p-3">
                <dt className="text-xs text-muted-foreground">Webhook</dt>
                <dd className="mt-1 font-medium text-foreground">{settings?.webhookConfigured ? "已配置" : "未配置"}</dd>
              </div>
              <div className="rounded-md border bg-background p-3">
                <dt className="text-xs text-muted-foreground">最近操作</dt>
                <dd className="mt-1 text-foreground">{message || "等待操作"}</dd>
              </div>
            </dl>
          </div>
        </aside>
      </section>
    </LowAbsorbPageShell>
  );
}
