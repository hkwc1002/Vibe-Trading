import type { LowAbsorbChainBranch } from "@/types/lowAbsorb";

export function BranchStrengthTable({ branches }: { branches: LowAbsorbChainBranch[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">分支 RS 表</h2>
      <div className="mt-4 overflow-x-auto rounded-md border">
        <table className="min-w-[720px] w-full text-left text-sm">
          <thead className="bg-muted/60 text-xs text-muted-foreground">
            <tr>
              <th className="px-3 py-2 font-medium">分支</th>
              <th className="px-3 py-2 font-medium">相对强度</th>
              <th className="px-3 py-2 font-medium">排名</th>
              <th className="px-3 py-2 font-medium">斜率</th>
              <th className="px-3 py-2 font-medium">候选数</th>
              <th className="px-3 py-2 font-medium">状态</th>
            </tr>
          </thead>
          <tbody className="divide-y">
            {branches.map((branch) => (
              <tr key={branch.id}>
                <td className="px-3 py-2 font-medium text-foreground">{branch.name}</td>
                <td className="px-3 py-2 tabular-nums text-muted-foreground">{branch.relativeStrength}</td>
                <td className="px-3 py-2 tabular-nums text-muted-foreground">{branch.rank}</td>
                <td className="px-3 py-2 tabular-nums text-muted-foreground">{branch.slope}</td>
                <td className="px-3 py-2 tabular-nums text-muted-foreground">{branch.candidates}</td>
                <td className="px-3 py-2 text-muted-foreground">{branch.status}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
