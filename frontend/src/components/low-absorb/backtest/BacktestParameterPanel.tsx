import type { LowAbsorbBacktestParameter } from "@/types/lowAbsorb";

export function BacktestParameterPanel({ parameters }: { parameters: LowAbsorbBacktestParameter[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">策略参数</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
        {parameters.map((parameter) => (
          <article key={parameter.id} className="rounded-md border bg-background p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-foreground">{parameter.label}</p>
              <p className="text-sm font-semibold text-foreground">{parameter.value}</p>
            </div>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">{parameter.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
