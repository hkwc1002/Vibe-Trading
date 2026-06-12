import { RiskBadge } from "@/components/low-absorb/workbench/RiskSummaryCards";
import type { LowAbsorbSentimentMetric } from "@/types/lowAbsorb";

export function ChainOverview({ items }: { items: LowAbsorbSentimentMetric[] }) {
  return (
    <section className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
      {items.map((item) => (
        <article key={item.id} className="rounded-lg border bg-card p-4 shadow-sm">
          <div className="flex items-start justify-between gap-3">
            <div>
              <p className="text-xs font-medium text-muted-foreground">{item.label}</p>
              <p className="mt-2 text-xl font-semibold text-foreground">{item.value}</p>
            </div>
            <RiskBadge level={item.riskLevel} />
          </div>
          <p className="mt-3 text-xs leading-5 text-muted-foreground">{item.detail}</p>
        </article>
      ))}
    </section>
  );
}
