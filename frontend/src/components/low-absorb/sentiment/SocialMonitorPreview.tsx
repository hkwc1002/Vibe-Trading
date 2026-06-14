import type { LowAbsorbMonitorPreview } from "@/types/lowAbsorb";

export function SocialMonitorPreview({ items }: { items: LowAbsorbMonitorPreview[] }) {
  return <MonitorPreview title="社交账号监听预览" items={items} />;
}

function MonitorPreview({ title, items }: { title: string; items: LowAbsorbMonitorPreview[] }) {
  return (
    <section className="rounded-lg border bg-card p-4 shadow-sm">
      <h2 className="text-sm font-semibold text-foreground">{title}</h2>
      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <article key={item.id} className="rounded-md border bg-background p-3">
            <div className="flex items-center justify-between gap-3">
              <p className="text-sm font-medium text-foreground">{item.title}</p>
              <span className="rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground">{item.status}</span>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">{item.source}</p>
            <p className="mt-2 text-xs leading-5 text-muted-foreground">{item.detail}</p>
          </article>
        ))}
      </div>
    </section>
  );
}
