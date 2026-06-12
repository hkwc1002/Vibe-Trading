import { RiskBadge } from "@/components/low-absorb/workbench/RiskSummaryCards";
import type { LowAbsorbSentimentMetric } from "@/types/lowAbsorb";

export function SentimentOverview({ metrics }: { metrics: LowAbsorbSentimentMetric[] }) {
  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {metrics.map((metric) => (
        <article key={metric.id} className="rounded-lg border bg-card p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-muted-foreground">{metric.label}</p>
              <p className="mt-2 text-2xl font-semibold tabular-nums text-foreground">{metric.value}</p>
            </div>
            <RiskBadge level={metric.riskLevel} />
          </div>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">{metric.detail}</p>
        </article>
      ))}
    </section>
  );
}
