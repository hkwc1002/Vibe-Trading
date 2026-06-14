import type { LowAbsorbFeishuPreview } from "@/types/lowAbsorb";

export function FeishuPreviewCard({ preview }: { preview: LowAbsorbFeishuPreview }) {
  return (
    <section className="rounded-lg border bg-card p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h2 className="text-base font-semibold text-foreground">飞书推荐预览</h2>
          <p className="mt-1 text-xs text-muted-foreground">仅用于建议与提醒，不构成交易执行。</p>
        </div>
        <span className="rounded-md border bg-muted px-2 py-1 text-xs text-muted-foreground">{preview.status}</span>
      </div>
      <div className="mt-4 rounded-md border bg-background p-3">
        <h3 className="text-sm font-semibold text-foreground">{preview.title}</h3>
        <ul className="mt-3 space-y-2 text-xs leading-5 text-muted-foreground">
          {preview.lines.map((line) => (
            <li key={line}>{line}</li>
          ))}
        </ul>
      </div>
    </section>
  );
}
