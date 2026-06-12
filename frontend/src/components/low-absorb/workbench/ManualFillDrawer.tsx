import type { LowAbsorbTradePlan } from "@/types/lowAbsorb";

export function ManualFillDrawer({ plan }: { plan: LowAbsorbTradePlan }) {
  return (
    <section className="rounded-lg border bg-card p-4">
      <h2 className="text-base font-semibold text-foreground">人工成交记录</h2>
      <p className="mt-1 text-xs text-muted-foreground">仅使用本地 mock 数据，暂未连接后端服务。</p>
      <div className="mt-4 grid gap-3 text-xs sm:grid-cols-2">
        <div className="rounded-md border bg-background p-3">
          <p className="text-muted-foreground">标的</p>
          <p className="mt-1 font-medium text-foreground">{plan.stockCode} {plan.stockName}</p>
        </div>
        <div className="rounded-md border bg-background p-3">
          <p className="text-muted-foreground">计划状态</p>
          <p className="mt-1 font-medium text-foreground">{plan.status}</p>
        </div>
        <div className="rounded-md border bg-background p-3 sm:col-span-2">
          <p className="text-muted-foreground">可复制人工信息</p>
          <p className="mt-1 leading-5 text-foreground">{plan.manualOrderText}</p>
        </div>
      </div>
      <button type="button" className="mt-4 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
        记录人工成交
      </button>
    </section>
  );
}

