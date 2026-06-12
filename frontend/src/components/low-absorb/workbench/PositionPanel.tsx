import type { LowAbsorbPosition } from "@/types/lowAbsorb";
import { RiskBadge } from "./RiskSummaryCards";

const HEADERS = ["股票", "成本", "现价", "止损", "仓位", "初始风险", "当前风险", "R 倍数", "10:00 监督状态", "操作"];

export function PositionPanel({ positions }: { positions: LowAbsorbPosition[] }) {
  return (
    <section className="rounded-lg border bg-card">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-foreground">人工持仓</h2>
        <p className="mt-1 text-xs text-muted-foreground">R-risk matrix 仅基于本地 mock 人工成交记录展示。</p>
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
              <tr key={position.id} data-testid={`position-row-${position.id}`} className="align-top">
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
  );
}

