export function ChainTopologyCard({ nodes }: { nodes: string[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <h2 className="text-sm font-semibold text-foreground">AI 成本拓扑 placeholder</h2>
        <span className="text-xs text-muted-foreground">可替换为图形化拓扑</span>
      </div>
      <div className="mt-4 grid gap-2 sm:grid-cols-4 lg:grid-cols-8">
        {nodes.map((node) => (
          <div key={node} className="flex min-h-16 items-center justify-center rounded-md border bg-background px-3 py-2 text-center text-sm font-medium text-foreground">
            {node}
          </div>
        ))}
      </div>
    </section>
  );
}
