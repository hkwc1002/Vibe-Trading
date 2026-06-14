import { Clock3 } from "lucide-react";

export function TwinSentimentClock() {
  return (
    <section className="grid gap-4 lg:grid-cols-2">
      {[
        { title: "A 股情绪时钟", phase: "尾盘可观察", detail: "成交额与炸板率满足低吸扫描前置条件。" },
        { title: "全球风险时钟", phase: "中性偏稳", detail: "海外科技与汇率扰动暂未触发宏观拦截。" },
      ].map((item) => (
        <article key={item.title} className="rounded-lg border bg-card p-4 shadow-sm">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-md bg-primary/10 text-primary">
              <Clock3 className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <h2 className="text-sm font-semibold text-foreground">{item.title}</h2>
              <p className="text-xs text-muted-foreground">{item.phase}</p>
            </div>
          </div>
          <p className="mt-4 text-sm leading-6 text-muted-foreground">{item.detail}</p>
        </article>
      ))}
    </section>
  );
}
