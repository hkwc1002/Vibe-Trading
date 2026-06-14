import type { LowAbsorbWorkbenchMock } from "@/types/lowAbsorb";
import { RiskBadge, RiskSummaryCards } from "./RiskSummaryCards";

export function WorkbenchOverview({ data }: { data: LowAbsorbWorkbenchMock }) {
  const candidates = data.signals.filter((signal) => signal.status !== "已拦截").slice(0, 2);
  const highRiskPositions = data.positions.filter((position) => position.riskLevel !== "normal");
  const riskRows = highRiskPositions.length ? highRiskPositions : data.positions;

  return (
    <div className="space-y-5">
      <RiskSummaryCards cards={data.dashboardCards} />

      <div className="grid gap-4 xl:grid-cols-[1.1fr_1fr_1fr]">
        <section className="rounded-lg border bg-card p-4">
          <h2 className="text-base font-semibold text-foreground">优先任务队列</h2>
          <h3 className="sr-only">今日待处理事项</h3>
          <p className="mt-1 text-xs text-muted-foreground">今日待处理事项按人工执行顺序排列。</p>
          <div className="mt-3 space-y-3">
            {data.tasks.map((task) => (
              <div key={task.id} className="rounded-md border bg-background p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-medium text-muted-foreground">{task.time}</p>
                    <p className="mt-1 text-sm font-medium text-foreground">{task.title}</p>
                  </div>
                  <RiskBadge level={task.riskLevel} />
                </div>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">{task.detail}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border bg-card p-4">
          <h2 className="text-base font-semibold text-foreground">重点候选</h2>
          <div className="mt-3 space-y-3">
            {candidates.map((signal) => (
              <div key={signal.id} className="rounded-md border bg-background p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">{signal.stockName}</p>
                    <p className="mt-1 text-xs text-muted-foreground">{signal.stockCode} · {signal.branch}</p>
                  </div>
                  <RiskBadge level={signal.riskLevel} label={signal.grade} />
                </div>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">{signal.reason}</p>
                {signal.chainExplanation && (
                  <p className="mt-2 rounded-md bg-muted px-2 py-1 text-xs leading-5 text-muted-foreground">
                    {signal.chainExplanation}
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>

        <section className="rounded-lg border bg-card p-4">
          <h2 className="text-base font-semibold text-foreground">高风险持仓</h2>
          <h3 className="sr-only">持仓风险摘要</h3>
          <p className="mt-1 text-xs text-muted-foreground">持仓风险摘要</p>
          <div className="mt-3 space-y-3">
            {riskRows.map((position) => (
              <div key={position.id} className="rounded-md border bg-background p-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-sm font-semibold text-foreground">{position.stockName}</p>
                    <p className="mt-1 text-xs text-muted-foreground">当前风险 {position.currentRisk} · {position.rMultiple}</p>
                  </div>
                  <RiskBadge level={position.riskLevel} />
                </div>
                <p className="mt-2 text-xs leading-5 text-muted-foreground">{position.note}</p>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}
