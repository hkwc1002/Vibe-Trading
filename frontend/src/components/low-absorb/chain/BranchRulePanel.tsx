export function BranchRulePanel({ rules }: { rules: string[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">分支闸门规则</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-3">
        {rules.map((rule) => (
          <div key={rule} className="rounded-md border bg-background p-3 text-sm leading-6 text-muted-foreground">
            {rule}
          </div>
        ))}
      </div>
    </section>
  );
}
