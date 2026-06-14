import type { LowAbsorbSensitivityCell } from "@/types/lowAbsorb";

export function SensitivityMatrix({ rows }: { rows: LowAbsorbSensitivityCell[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">参数敏感性</h2>
      <div className="mt-4 overflow-hidden rounded-md border">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted/60 text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">参数</th>
              <th className="px-3 py-2 font-medium">保守</th>
              <th className="px-3 py-2 font-medium">基准</th>
              <th className="px-3 py-2 font-medium">进取</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {rows.map((row) => (
              <tr key={row.id}>
                <td className="px-3 py-2 font-medium text-foreground">{row.parameter}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.conservative}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.base}</td>
                <td className="px-3 py-2 text-muted-foreground">{row.aggressive}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
