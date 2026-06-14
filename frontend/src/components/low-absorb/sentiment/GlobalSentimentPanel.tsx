import type { LowAbsorbSentimentGate } from "@/types/lowAbsorb";

export function GlobalSentimentPanel({ gates }: { gates: LowAbsorbSentimentGate[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">全球风险偏好</h2>
      <div className="mt-4 overflow-hidden rounded-md border">
        <table className="w-full text-left text-sm">
          <thead className="bg-muted/60 text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">指标</th>
              <th className="px-3 py-2 font-medium">读数</th>
              <th className="px-3 py-2 font-medium">状态</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {gates.map((gate) => (
              <tr key={gate.id}>
                <td className="px-3 py-2 text-foreground">{gate.label}</td>
                <td className="px-3 py-2 text-muted-foreground">{gate.value}</td>
                <td className="px-3 py-2 text-muted-foreground">{gate.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
