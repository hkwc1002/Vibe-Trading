import type { LowAbsorbHistoricalSignal } from "@/types/lowAbsorb";

export function HistoricalSignalTable({ rows }: { rows: LowAbsorbHistoricalSignal[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">历史信号</h2>
      <div className="mt-4 overflow-x-auto rounded-md border">
        <table className="min-w-[860px] w-full text-left text-sm">
          <thead className="bg-muted/60 text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">日期</th>
              <th className="px-3 py-2 font-medium">股票</th>
              <th className="px-3 py-2 font-medium">分支</th>
              <th className="px-3 py-2 font-medium">入选等级</th>
              <th className="px-3 py-2 font-medium">次日表现</th>
              <th className="px-3 py-2 font-medium">最大浮亏</th>
              <th className="px-3 py-2 font-medium">最终 R</th>
              <th className="px-3 py-2 font-medium">是否命中止损</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map((row) => (
              <tr key={row.id} data-testid={`historical-signal-${row.id}`}>
                <td className="px-3 py-2 text-muted-foreground">{row.tradeDate}</td>
                <td className="px-3 py-2 font-medium text-foreground">{row.stock}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.branch}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.grade}</td>
                <td className="px-3 py-2 tabular-nums text-muted-foreground">{row.nextDayReturn}</td>
                <td className="px-3 py-2 tabular-nums text-muted-foreground">{row.maxFloatLoss}</td>
                <td className="px-3 py-2 tabular-nums text-muted-foreground">{row.finalR}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.stopHit}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
