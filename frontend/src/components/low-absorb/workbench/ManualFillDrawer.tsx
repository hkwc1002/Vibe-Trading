import { useState } from "react";
import type { LowAbsorbTradePlan } from "@/types/lowAbsorb";

type ManualFillDrawerProps = {
  plan: LowAbsorbTradePlan;
  onSubmit?: (values: { actualPrice: string; quantity: number; note: string }) => void;
};

export function ManualFillDrawer({ plan, onSubmit }: ManualFillDrawerProps) {
  const [actualPrice, setActualPrice] = useState("");
  const [quantity, setQuantity] = useState("100");
  const [note, setNote] = useState("用户已在国内券商 App 手动处理并回填。");

  return (
    <section className="rounded-lg border bg-card p-4">
      <h2 className="text-base font-semibold text-foreground">人工成交记录</h2>
      <p className="mt-1 text-xs text-muted-foreground">仅记录用户已在外部券商 App 手动完成的成交。</p>
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
      <form
        className="mt-4 grid gap-3 text-sm"
        onSubmit={(event) => {
          event.preventDefault();
          onSubmit?.({ actualPrice, quantity: Number(quantity), note });
        }}
      >
        <label className="grid gap-1">
          <span className="text-xs font-medium text-muted-foreground">成交价格</span>
          <input
            aria-label="成交价格"
            value={actualPrice}
            onChange={(event) => setActualPrice(event.target.value)}
            placeholder={plan.entryRange.split("-")[0]?.trim() || "0"}
            className="rounded-md border bg-background px-3 py-2 text-foreground"
          />
        </label>
        <label className="grid gap-1">
          <span className="text-xs font-medium text-muted-foreground">成交数量</span>
          <input
            aria-label="成交数量"
            value={quantity}
            onChange={(event) => setQuantity(event.target.value)}
            inputMode="numeric"
            className="rounded-md border bg-background px-3 py-2 text-foreground"
          />
        </label>
        <label className="grid gap-1">
          <span className="text-xs font-medium text-muted-foreground">备注</span>
          <textarea
            aria-label="备注"
            value={note}
            onChange={(event) => setNote(event.target.value)}
            className="min-h-20 rounded-md border bg-background px-3 py-2 text-foreground"
          />
        </label>
        <button type="submit" className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90">
          提交人工成交记录
        </button>
      </form>
    </section>
  );
}
