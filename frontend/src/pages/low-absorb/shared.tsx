import type { ReactNode } from "react";
import type { LucideIcon } from "lucide-react";

export type PlaceholderCard = {
  title: string;
  description: string;
  icon: LucideIcon;
};

type LowAbsorbPageShellProps = {
  title: string;
  description: string;
  children: ReactNode;
};

export function LowAbsorbPageShell({ title, description, children }: LowAbsorbPageShellProps) {
  return (
    <div className="min-h-full bg-background p-6">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="space-y-2">
          <p className="text-xs font-semibold uppercase tracking-wide text-primary">
            AI Low Absorb
          </p>
          <h1 className="text-2xl font-semibold tracking-tight text-foreground">
            {title}
          </h1>
          <p className="max-w-3xl text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        </header>
        {children}
      </div>
    </div>
  );
}

export function PlaceholderGrid({ cards }: { cards: PlaceholderCard[] }) {
  return (
    <section className="grid gap-4 md:grid-cols-3">
      {cards.map(({ title, description, icon: Icon }) => (
        <article
          key={title}
          data-testid="low-absorb-placeholder-card"
          className="rounded-lg border bg-card p-4 shadow-sm"
        >
          <div className="mb-3 flex h-9 w-9 items-center justify-center rounded-md bg-primary/10 text-primary">
            <Icon className="h-4 w-4" aria-hidden="true" />
          </div>
          <h3 className="text-sm font-medium text-foreground">{title}</h3>
          <p className="mt-2 text-sm leading-6 text-muted-foreground">
            {description}
          </p>
        </article>
      ))}
    </section>
  );
}

export function EmptyContentArea({ title = "暂无业务数据接入" }: { title?: string }) {
  return (
    <section className="flex min-h-[280px] flex-col items-center justify-center rounded-lg border border-dashed bg-muted/20 p-8 text-center">
      <h2 className="text-base font-medium text-foreground">{title}</h2>
      <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
        当前版本仅搭建人工执行工作台导航壳。后续数据、信号、飞书通知和人工成交回填将通过后端服务接入。
      </p>
    </section>
  );
}

