import type { LowAbsorbMonitorPreview } from "@/types/lowAbsorb";

export function NewsMonitorPreview({ items }: { items: LowAbsorbMonitorPreview[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">新闻事件监听预览</h2>
      <div className="mt-4 grid gap-3 md:grid-cols-2">
        {items.map((item) => (
          <article key={item.id} className="rounded-md border bg-background p-3">
            <p className="text-sm font-medium text-foreground">{item.title}</p>
            <p className="mt-1 text-xs text-muted-foreground">{item.source} · {item.status}</p>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">{item.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
