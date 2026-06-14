import type { LowAbsorbBacktestMetric } from "@/types/lowAbsorb";

export function BacktestOverview({ metrics }: { metrics: LowAbsorbBacktestMetric[] }) {
  const metricsList = Array.isArray(metrics) ? metrics : [];
  const winRate = metricsList.find((m) => m.id === "win-rate");
  const avgR = metricsList.find((m) => m.id === "avg-r");
  const profitFactor = metricsList.find((m) => m.id === "profit-factor");
  const drawdown = metricsList.find((m) => m.id === "drawdown");

  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">回测总览</h2>
      <p className="mt-2 text-sm leading-6 text-muted-foreground">
        当前页面展示策略回测契约和示例数据。真实回测引擎、行情拉取和参数寻优将在后端接口接入后运行。
      </p>
      {metricsList.length > 0 && (
        <div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {winRate && (
            <div className="rounded-md border bg-background p-3 text-center">
              <p className="text-xs text-muted-foreground">整体胜率</p>
              <p className="mt-1 text-lg font-semibold text-foreground">{winRate.value}</p>
            </div>
          )}
          {avgR && (
            <div className="rounded-md border bg-background p-3 text-center">
              <p className="text-xs text-muted-foreground">均值 R</p>
              <p className="mt-1 text-lg font-semibold text-foreground">{avgR.value}</p>
            </div>
          )}
          {profitFactor && (
            <div className="rounded-md border bg-background p-3 text-center">
              <p className="text-xs text-muted-foreground">盈亏比</p>
              <p className="mt-1 text-lg font-semibold text-foreground">{profitFactor.value}</p>
            </div>
          )}
          {drawdown && (
            <div className="rounded-md border bg-background p-3 text-center">
              <p className="text-xs text-muted-foreground">最大回撤</p>
              <p className="mt-1 text-lg font-semibold text-foreground">{drawdown.value}</p>
            </div>
          )}
        </div>
      )}
    </section>
  );
}
