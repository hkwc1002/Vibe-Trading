import { cn } from "@/lib/utils";
import type { LowAbsorbDashboardCard, LowAbsorbRiskLevel } from "@/types/lowAbsorb";

const RISK_STYLES: Record<LowAbsorbRiskLevel, string> = {
  normal: "border-green-200 bg-green-50 text-green-700 dark:border-green-900/60 dark:bg-green-950/30 dark:text-green-300",
  watch: "border-blue-200 bg-blue-50 text-blue-700 dark:border-blue-900/60 dark:bg-blue-950/30 dark:text-blue-300",
  warning: "border-amber-200 bg-amber-50 text-amber-700 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-300",
  danger: "border-red-200 bg-red-50 text-red-700 dark:border-red-900/60 dark:bg-red-950/30 dark:text-red-300",
};

const RISK_LABELS: Record<LowAbsorbRiskLevel, string> = {
  normal: "正常",
  watch: "观察",
  warning: "预警",
  danger: "高风险",
};

export function RiskBadge({ level, label }: { level: LowAbsorbRiskLevel; label?: string }) {
  return (
    <span className={cn("inline-flex items-center rounded-md border px-2 py-0.5 text-xs font-medium", RISK_STYLES[level])}>
      {label ?? RISK_LABELS[level]}
    </span>
  );
}

export function RiskSummaryCards({ cards }: { cards: LowAbsorbDashboardCard[] }) {
  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
      {cards.map((card) => (
        <article key={card.id} className="rounded-lg border bg-card p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-muted-foreground">{card.label}</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-foreground">{card.value}</p>
            </div>
            <RiskBadge level={card.riskLevel} />
          </div>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">{card.detail}</p>
          <dl className="mt-4 grid gap-2 text-xs">
            <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-2">
              <dt className="text-muted-foreground">当前状态</dt>
              <dd className="font-medium text-foreground">{card.currentStatus ?? card.value}</dd>
            </div>
            <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-2">
              <dt className="text-muted-foreground">关键指标</dt>
              <dd className="text-foreground">{card.keyMetrics?.join(" / ") ?? card.detail}</dd>
            </div>
            <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-2">
              <dt className="text-muted-foreground">趋势变化</dt>
              <dd className="text-foreground">{card.trend ?? "等待下一次刷新"}</dd>
            </div>
            <div className="grid grid-cols-[72px_minmax(0,1fr)] gap-2">
              <dt className="text-muted-foreground">下一步</dt>
              <dd className="font-medium text-foreground">{card.nextAction ?? "人工复核"}</dd>
            </div>
          </dl>
        </article>
      ))}
    </section>
  );
}
