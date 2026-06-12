import { RiskBadge } from "@/components/low-absorb/workbench/RiskSummaryCards";
import type { LowAbsorbChainStockMapping } from "@/types/lowAbsorb";

export function StockMappingTable({ rows }: { rows: LowAbsorbChainStockMapping[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">个股映射表</h2>
      <div className="mt-4 overflow-x-auto rounded-md border">
        <table className="min-w-[760px] w-full text-left text-sm">
          <thead className="bg-muted/60 text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">股票</th>
              <th className="px-3 py-2 font-medium">所属分支</th>
              <th className="px-3 py-2 font-medium">产业角色</th>
              <th className="px-3 py-2 font-medium">信号状态</th>
              <th className="px-3 py-2 font-medium">风险</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="px-3 py-2">
                  <p className="font-medium text-foreground">{row.stockCode}</p>
                  <p className="text-xs text-muted-foreground">{row.stockName}</p>
                </td>
                <td className="px-3 py-2 text-muted-foreground">{row.branch}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.role}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.signalStatus}</td>
                <td className="px-3 py-2"><RiskBadge level={row.riskLevel} /></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
