import type { LowAbsorbBranchAttribution } from "@/types/lowAbsorb";

export function BranchAttributionPanel({ rows }: { rows: LowAbsorbBranchAttribution[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">分支归因</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {rows.map((row) => (
          <article key={row.id} className="rounded-md border bg-background p-3">
            <p className="text-sm font-medium text-foreground">{row.branch}</p>
            <p className="mt-2 text-xs text-muted-foreground">样本数：{row.samples}</p>
            <p className="mt-1 text-xs text-muted-foreground">平均 R：{row.averageR}</p>
            <p className="mt-1 text-xs text-muted-foreground">贡献：{row.contribution}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
