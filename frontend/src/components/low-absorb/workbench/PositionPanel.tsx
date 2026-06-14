import type { LowAbsorbPosition } from "@/types/lowAbsorb";
import { cn } from "@/lib/utils";
import { RiskBadge } from "./RiskSummaryCards";

const HEADERS = ["股票", "成本", "现价", "止损", "仓位", "初始风险", "当前风险", "R 倍数", "10:00 监督状态", "操作"];

type PositionPanelProps = {
  positions: LowAbsorbPosition[];
  selectedId?: string | null;
  onSelect?: (position: LowAbsorbPosition) => void;
};

export function PositionPanel({ positions, selectedId, onSelect }: PositionPanelProps) {
  const warningCount = positions.filter((position) => position.riskLevel !== "normal").length;
  const supervisionCount = positions.filter((position) => position.supervisionStatus.includes("10:00")).length;
  const first = positions[0];
  const stopDistance = first && Number(first.lastPrice) && Number(first.stopLoss)
    ? `${(((Number(first.lastPrice) - Number(first.stopLoss)) / Number(first.lastPrice)) * 100).toFixed(2)}%`
    : "-";

  return (
    <div className="space-y-4">
      <section className="grid gap-4 xl:grid-cols-[1fr_1fr_1.2fr]">
        <article className="rounded-lg border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">组合风险仪表</h2>
          <div className="mt-4 flex items-end justify-between gap-4">
            <div>
              <p className="text-3xl font-semibold tabular-nums text-foreground">{warningCount}</p>
              <p className="mt-1 text-xs text-muted-foreground">预警持仓</p>
            </div>
            <RiskBadge level={warningCount ? "warning" : "normal"} />
          </div>
          <div className="mt-4 h-2 rounded-full bg-muted">
            <div className={cn("h-2 rounded-full", warningCount ? "bg-amber-500" : "bg-green-500")} style={{ width: `${positions.length ? Math.max(18, (warningCount / positions.length) * 100) : 0}%` }} />
          </div>
        </article>

        <article className="rounded-lg border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">开放风险卡</h2>
          <dl className="mt-4 grid grid-cols-2 gap-3 text-sm">
            <div className="rounded-md border bg-background p-3">
              <dt className="text-xs text-muted-foreground">初始风险</dt>
              <dd className="mt-1 font-semibold text-foreground">{first?.initialRisk ?? "-"}</dd>
            </div>
            <div className="rounded-md border bg-background p-3">
              <dt className="text-xs text-muted-foreground">当前风险</dt>
              <dd className="mt-1 font-semibold text-foreground">{first?.currentRisk ?? "-"}</dd>
            </div>
            <div className="rounded-md border bg-background p-3">
              <dt className="text-xs text-muted-foreground">R 倍数</dt>
              <dd className="mt-1 font-semibold text-foreground">{first?.rMultiple ?? "-"}</dd>
            </div>
            <div className="rounded-md border bg-background p-3">
              <dt className="text-xs text-muted-foreground">止损距离</dt>
              <dd className="mt-1 font-semibold text-foreground">{stopDistance}</dd>
            </div>
          </dl>
        </article>

        <article className="rounded-lg border bg-card p-4">
          <div className="flex items-start justify-between gap-3">
            <div>
              <h2 className="text-sm font-semibold text-foreground">早盘监督面板</h2>
              <p className="mt-1 text-xs text-muted-foreground">09:30-10:00 抗噪后执行 10:00 监督。</p>
            </div>
            <RiskBadge level={supervisionCount ? "warning" : "normal"} label={`${supervisionCount} 个`} />
          </div>
          <div className="mt-4">
            <p className="text-xs font-medium text-muted-foreground">风险热力条</p>
            <div className="mt-2 grid grid-cols-6 gap-1">
              {positions.concat(positions).slice(0, 6).map((position, index) => (
                <div
                  key={`${position.id}-${index}`}
                  className={cn(
                    "h-8 rounded-md border",
                    position.riskLevel === "danger" && "border-red-200 bg-red-100",
                    position.riskLevel === "warning" && "border-amber-200 bg-amber-100",
                    position.riskLevel === "watch" && "border-blue-200 bg-blue-100",
                    position.riskLevel === "normal" && "border-green-200 bg-green-100",
                  )}
                  title={`${position.stockName} ${position.rMultiple}`}
                />
              ))}
            </div>
          </div>
        </article>
      </section>

      <section className="rounded-lg border bg-card">
        <div className="border-b px-4 py-3">
          <h2 className="text-base font-semibold text-foreground">人工持仓</h2>
          <p className="mt-1 text-xs text-muted-foreground">持仓风险矩阵保留下方，用于逐笔复核 R 风险和监督状态。</p>
        </div>
        <div className="overflow-x-auto">
        <table className="w-full min-w-[980px] text-left text-xs">
          <thead className="bg-muted/50 text-muted-foreground">
            <tr>
              {HEADERS.map((header) => (
                <th key={header} className="whitespace-nowrap px-3 py-2 font-medium">{header}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {positions.map((position) => (
              <tr
                key={position.id}
                data-testid={`position-row-${position.id}`}
                className={cn("align-top", selectedId === position.id && "bg-primary/5")}
                onClick={() => onSelect?.(position)}
              >
                <td className="whitespace-nowrap px-3 py-3">
                  <div className="font-medium text-foreground">{position.stockName}</div>
                  <div className="mt-1 font-mono text-muted-foreground">{position.stockCode}</div>
                </td>
                <td className="whitespace-nowrap px-3 py-3 tabular-nums">{position.cost}</td>
                <td className="whitespace-nowrap px-3 py-3 tabular-nums">{position.lastPrice}</td>
                <td className="whitespace-nowrap px-3 py-3 tabular-nums">{position.stopLoss}</td>
                <td className="whitespace-nowrap px-3 py-3 tabular-nums">{position.positionSize}</td>
                <td className="whitespace-nowrap px-3 py-3 tabular-nums">{position.initialRisk}</td>
                <td className="whitespace-nowrap px-3 py-3 tabular-nums">{position.currentRisk}</td>
                <td className="whitespace-nowrap px-3 py-3"><RiskBadge level={position.riskLevel} label={position.rMultiple} /></td>
                <td className="whitespace-nowrap px-3 py-3">{position.supervisionStatus}</td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-1.5">
                    <button type="button" className="rounded-md border px-2 py-1 text-xs hover:bg-muted">记录卖出</button>
                    <button type="button" className="rounded-md border px-2 py-1 text-xs hover:bg-muted">调整备注</button>
                    <button type="button" className="rounded-md border px-2 py-1 text-xs hover:bg-muted">生成风控提醒</button>
                    <button type="button" className="rounded-md border px-2 py-1 text-xs hover:bg-muted">归档持仓</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
    </div>
  );
}
