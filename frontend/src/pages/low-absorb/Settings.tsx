import { useEffect, useState } from "react";
import { Bell, Database, Send, SlidersHorizontal, Webhook } from "lucide-react";
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
  ["max_data_staleness_seconds", "数据新鲜度阈值（秒）"],
] as const;

const DATA_SOURCE_FIELDS = [
  ["data_provider_mode", "A 股数据源模式", ["auto", "real", "fixture"]],
  ["global_market_provider", "全球/美股数据源", ["auto", "yfinance", "stooq"]],
  ["active_cost_chain_version", "成本链版本", ["GB200 NVL72", "GB300 NVL72", "custom/manual"]],
] as const;

const NUMERIC_DATA_SOURCE_FIELDS = [["eastmoney_min_interval_seconds", "东财请求最小间隔（秒）"]] as const;

function configToForm(config: Record<string, unknown>): Record<string, string> {
  const keys = [
    ...THRESHOLDS.map(([key]) => key),
    ...DATA_SOURCE_FIELDS.map(([key]) => key),
    ...NUMERIC_DATA_SOURCE_FIELDS.map(([key]) => key),
  ];

  return Object.fromEntries(keys.map((key) => [key, String(config[key] ?? "")]));
}

function optionLabel(option: string): string {
  const labels: Record<string, string> = {
    auto: "自动",
    real: "真实数据",
    fixture: "示例数据",
    yfinance: "Yahoo Finance",
    stooq: "Stooq",
  };
  return labels[option] || option;
}

export function Settings() {
  const [settings, setSettings] = useState<LowAbsorbApiSettings | null>(null);
  const [webhook, setWebhook] = useState("");
  const [form, setForm] = useState<Record<string, string>>({});
  const [fallbackEnabled, setFallbackEnabled] = useState(true);
  const [message, setMessage] = useState("");

  useEffect(() => {
    let alive = true;
    lowAbsorbApi
      .getSettings()
      .then((value) => {
        if (!alive) return;
        setSettings(value);
        setForm(configToForm(value.config));
        setFallbackEnabled(Boolean(value.config.enable_fixture_fallback ?? true));
      })
      .catch((error) => {
        if (!alive) return;
        setMessage(error instanceof Error ? error.message : "设置加载失败");
      });
    return () => {
      alive = false;
    };
  }, []);

  function updateForm(key: string, value: string) {
    setForm((current) => ({ ...current, [key]: value }));
  }

  async function saveSettings() {
    const next = await lowAbsorbApi.patchSettings({
      ...(webhook ? { feishu_webhook: webhook } : {}),
      config: {
        ...form,
        enable_fixture_fallback: String(fallbackEnabled),
      },
    });
    setSettings(next);
    setForm(configToForm(next.config));
    setFallbackEnabled(Boolean(next.config.enable_fixture_fallback ?? fallbackEnabled));
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
      description="管理低吸扫描阈值、数据源、飞书通知和人工执行工作台偏好。"
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
                    value={form[key] ?? ""}
                    onChange={(event) => updateForm(key, event.target.value)}
                    className="rounded-md border bg-background px-3 py-2 text-foreground"
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="rounded-lg border bg-card p-4">
            <div className="mb-4 flex items-center gap-2">
              <Database className="h-4 w-4 text-primary" aria-hidden="true" />
              <h2 className="text-base font-semibold text-foreground">行情数据源</h2>
            </div>
            <div className="grid gap-3 md:grid-cols-2">
              {DATA_SOURCE_FIELDS.map(([key, label, options]) => (
                <label key={key} className="grid gap-1 text-sm">
                  <span className="text-xs font-medium text-muted-foreground">{label}</span>
                  <select
                    aria-label={label}
                    value={form[key] || "auto"}
                    onChange={(event) => updateForm(key, event.target.value)}
                    className="rounded-md border bg-background px-3 py-2 text-foreground"
                  >
                    {options.map((option) => (
                      <option key={option} value={option}>
                        {optionLabel(option)}
                      </option>
                    ))}
                  </select>
                </label>
              ))}
              {NUMERIC_DATA_SOURCE_FIELDS.map(([key, label]) => (
                <label key={key} className="grid gap-1 text-sm">
                  <span className="text-xs font-medium text-muted-foreground">{label}</span>
                  <input
                    aria-label={label}
                    value={form[key] ?? ""}
                    onChange={(event) => updateForm(key, event.target.value)}
                    className="rounded-md border bg-background px-3 py-2 text-foreground"
                  />
                </label>
              ))}
              <label className="flex items-center gap-2 rounded-md border bg-background px-3 py-2 text-sm">
                <input
                  type="checkbox"
                  checked={fallbackEnabled}
                  onChange={(event) => setFallbackEnabled(event.target.checked)}
                />
                <span>真实数据失败时启用示例数据回退</span>
              </label>
            </div>
          </div>

          <div className="rounded-lg border bg-card p-4">
            <div className="mb-4 flex items-center gap-2">
              <Webhook className="h-4 w-4 text-primary" aria-hidden="true" />
              <h2 className="text-base font-semibold text-foreground">飞书通知</h2>
            </div>
            <div className="grid gap-3">
              <div className="rounded-md border bg-background p-3 text-sm">
                <p className="text-xs text-muted-foreground">当前机器人地址</p>
                <p className="mt-1 break-all font-mono text-foreground">{settings?.maskedWebhook ?? "未配置"}</p>
              </div>
              <label className="grid gap-1 text-sm">
                <span className="text-xs font-medium text-muted-foreground">飞书机器人地址</span>
                <input
                  aria-label="飞书机器人地址"
                  value={webhook}
                  onChange={(event) => setWebhook(event.target.value)}
                  placeholder="粘贴新的飞书机器人地址，保存后仅显示掩码"
                  className="rounded-md border bg-background px-3 py-2 text-foreground"
                />
              </label>
              <div className="flex flex-wrap gap-2">
                <button
                  type="button"
                  onClick={() => void saveSettings()}
                  className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
                >
                  保存设置
                </button>
                <button
                  type="button"
                  onClick={() => void sendTestNotification()}
                  className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium hover:bg-muted"
                >
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
                <dt className="text-xs text-muted-foreground">机器人地址</dt>
                <dd className="mt-1 font-medium text-foreground">{settings?.webhookConfigured ? "已配置" : "未配置"}</dd>
              </div>
              <div className="rounded-md border bg-background p-3">
                <dt className="text-xs text-muted-foreground">A 股数据源</dt>
                <dd className="mt-1 font-medium text-foreground">{optionLabel(form.data_provider_mode || "auto")}</dd>
              </div>
              <div className="rounded-md border bg-background p-3">
                <dt className="text-xs text-muted-foreground">全球/美股</dt>
                <dd className="mt-1 font-medium text-foreground">{optionLabel(form.global_market_provider || "auto")}</dd>
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
