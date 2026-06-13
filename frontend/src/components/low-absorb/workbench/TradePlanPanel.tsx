import type { LowAbsorbTradePlan } from "@/types/lowAbsorb";
import { cn } from "@/lib/utils";
import { RiskBadge } from "./RiskSummaryCards";

type TradePlanFieldKey =
  | "entryRange"
  | "stopLoss"
  | "positionSize"
  | "maxRisk"
  | "initialRisk"
  | "feishuStatus";

const PLAN_FIELDS: Array<[string, TradePlanFieldKey]> = [
  ["建议低吸区间", "entryRange"],
  ["参考止损", "stopLoss"],
  ["建议仓位", "positionSize"],
  ["单笔最大风险", "maxRisk"],
  ["初始 R 风险", "initialRisk"],
  ["飞书推送状态", "feishuStatus"],
];

type TradePlanPanelProps = {
  plans: LowAbsorbTradePlan[];
  selectedId?: string | null;
  onSelect?: (plan: LowAbsorbTradePlan) => void;
  onSendFeishu?: (plan: LowAbsorbTradePlan) => void;
  onRecordFill?: (plan: LowAbsorbTradePlan) => void;
};

export function TradePlanPanel({ plans, selectedId, onSelect, onSendFeishu, onRecordFill }: TradePlanPanelProps) {
  return (
    <div className="space-y-4">
      <section className="grid gap-4 lg:grid-cols-2">
        {plans.map((plan) => (
          <article
            key={plan.id}
            className={cn("rounded-lg border bg-card p-4", selectedId === plan.id && "border-primary/60 bg-primary/5")}
            onClick={() => onSelect?.(plan)}
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-base font-semibold text-foreground">{plan.stockName}</h2>
                <p className="mt-1 text-xs text-muted-foreground">{plan.stockCode} · {plan.status}</p>
              </div>
              <RiskBadge level={plan.riskLevel} />
            </div>
            <dl className="mt-4 grid gap-3 sm:grid-cols-2">
              {PLAN_FIELDS.map(([label, key]) => (
                <div key={label} className="rounded-md border bg-background p-3">
                  <dt className="text-xs text-muted-foreground">{label}</dt>
                  <dd className="mt-1 text-sm font-medium text-foreground">{plan[key]}</dd>
                </div>
              ))}
            </dl>
            <div className="mt-4 flex flex-wrap gap-2">
              <button type="button" onClick={(event) => { event.stopPropagation(); navigator.clipboard?.writeText(plan.manualOrderText); }} className="rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted">复制人工下单信息</button>
              <button type="button" onClick={(event) => { event.stopPropagation(); onSendFeishu?.(plan); }} className="rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted">推送飞书</button>
              <button type="button" onClick={(event) => { event.stopPropagation(); onRecordFill?.(plan); }} className="rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted">记录人工成交</button>
              <button type="button" className="rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted">作废计划</button>
            </div>
          </article>
        ))}
      </section>
    </div>
  );
}
