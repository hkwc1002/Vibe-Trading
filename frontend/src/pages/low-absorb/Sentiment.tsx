import { useEffect, useState } from "react";
import { lowAbsorbApi } from "@/lib/lowAbsorbApi";
import type { LowAbsorbSentimentGauge, LowAbsorbSentimentSnapshot } from "@/types/lowAbsorb";
import { LowAbsorbPageShell } from "./shared";

const PERMISSION_COLORS: Record<string, string> = {
  "允许": "bg-green-100 border-green-500 text-green-800",
  "观察": "bg-yellow-100 border-yellow-500 text-yellow-800",
  "拦截": "bg-red-100 border-red-500 text-red-800",
};

const FALLBACK_SENTIMENT: LowAbsorbSentimentSnapshot = {
  tradingPermission: {
    status: "观察",
    summary: "双情绪时钟用于决定是否允许生成主板低吸人工交易建议。",
    nextAction: "等待情绪闸门恢复",
    blockedReasons: ["情绪 API 不可用，暂停生成新建议"],
  },
  gauges: [
    { id: "global", label: "全球情绪", score: 0, status: "数据缺失", detail: "情绪 API 不可用，无法获取全球情绪数据。" },
    { id: "a_share", label: "A 股情绪", score: 0, status: "数据缺失", detail: "情绪 API 不可用，无法获取 A 股情绪数据。" },
  ],
  instrumentPanels: [
    { id: "market_turnover", label: "成交额闸门", value: "—", status: "数据缺失", explanation: "情绪 API 不可用。" },
    { id: "limit_break", label: "炸板率闸门", value: "—", status: "数据缺失", explanation: "情绪 API 不可用。" },
    { id: "advance_decline", label: "涨跌家数宽度", value: "—", status: "数据缺失", explanation: "情绪 API 不可用。" },
    { id: "ai_capital_temperature", label: "AI 资金温度", value: "—", status: "数据缺失", explanation: "情绪 API 不可用。" },
    { id: "global_risk_appetite", label: "全球风险偏好", value: "—", status: "数据缺失", explanation: "情绪 API 不可用。" },
    { id: "sentiment_conclusion", label: "情绪结论", value: "观察", status: "观察", explanation: "情绪 API 不可用，暂停生成新建议。" },
  ],
  socialEvents: [],
  newsEvents: [],
};

function Gauge({ gauge }: { gauge: LowAbsorbSentimentGauge }) {
  const score = Math.max(0, Math.min(100, Number(gauge.score)));
  return (
    <article className="rounded-lg border bg-card p-5 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h2 className="text-base font-semibold text-foreground">{gauge.label}仪表</h2>
          <p className="mt-1 text-xs text-muted-foreground">{gauge.detail}</p>
        </div>
        <span className="rounded-md border px-2 py-1 text-xs font-medium text-foreground">{gauge.status}</span>
      </div>
      <div className="mt-5 flex items-center gap-4">
        <div className="relative h-28 w-28 rounded-full border-[10px] border-muted">
          <div
            className="absolute inset-[-10px] rounded-full border-[10px] border-primary"
            style={{ clipPath: `polygon(0 0, ${score}% 0, ${score}% 100%, 0 100%)` }}
          />
          <div className="absolute inset-0 flex items-center justify-center rounded-full bg-card">
            <span className="text-2xl font-semibold tabular-nums text-foreground">{gauge.score}</span>
          </div>
        </div>
        <div className="min-w-0 text-sm leading-6 text-muted-foreground">
          <p>双情绪时钟的一部分，用于判断交易建议是否允许生成。</p>
          <p className="mt-1">状态：{gauge.status}</p>
        </div>
      </div>
    </article>
  );
}

export function Sentiment() {
  const [snapshot, setSnapshot] = useState<LowAbsorbSentimentSnapshot>(FALLBACK_SENTIMENT);

  useEffect(() => {
    lowAbsorbApi.getSentimentSnapshot().then(setSnapshot).catch(() => setSnapshot(FALLBACK_SENTIMENT));
  }, []);

  return (
    <LowAbsorbPageShell
      title="市场情绪"
      description="将双情绪时钟作为交易许可系统，明确说明今天是否允许生成主板低吸人工交易建议。"
    >
      <section className="rounded-lg border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">交易许可系统</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">{snapshot.tradingPermission.summary}</p>
          </div>
          <div className="rounded-md border bg-background px-4 py-3 text-right">
            <p className="text-xs text-muted-foreground">当前结论</p>
            <p className={`mt-1 inline-block rounded-md border px-3 py-1 text-xl font-semibold ${PERMISSION_COLORS[snapshot.tradingPermission.status] ?? "text-foreground"}`}>{snapshot.tradingPermission.status}</p>
            <p className="mt-1 text-xs text-muted-foreground">下一步：{snapshot.tradingPermission.nextAction}</p>
          </div>
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        {snapshot.gauges.map((gauge) => <Gauge key={gauge.id} gauge={gauge} />)}
      </section>

      <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {snapshot.instrumentPanels.map((panel) => (
          <article key={panel.id} className="rounded-lg border bg-card p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-sm font-semibold text-foreground">{panel.label}</h2>
                <p className="mt-2 text-2xl font-semibold tabular-nums text-foreground">{panel.value}</p>
              </div>
              <span className="rounded-md border px-2 py-1 text-xs font-medium text-foreground">{panel.status}</span>
            </div>
            <p className="mt-3 text-xs leading-5 text-muted-foreground">{panel.explanation}</p>
          </article>
        ))}
      </section>

      <section className="grid gap-4 xl:grid-cols-2">
        {[
          ["社交事件流", snapshot.socialEvents],
          ["新闻事件流", snapshot.newsEvents],
        ].map(([title, events]) => (
          <article key={title as string} className="rounded-lg border bg-card p-4 shadow-sm">
            <h2 className="text-base font-semibold text-foreground">{title as string}</h2>
            <div className="mt-4 space-y-3">
              {(events as LowAbsorbSentimentSnapshot["socialEvents"]).map((event) => (
                <div key={event.id} className="rounded-md border bg-background p-3">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <p className="text-sm font-medium text-foreground">{event.title}</p>
                      <p className="mt-1 text-xs text-muted-foreground">{event.time} · {event.source}</p>
                    </div>
                    <span className="rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground">{event.impact}</span>
                  </div>
                </div>
              ))}
            </div>
          </article>
        ))}
      </section>
    </LowAbsorbPageShell>
  );
}
