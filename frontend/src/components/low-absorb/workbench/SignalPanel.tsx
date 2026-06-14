import type { LowAbsorbSignal } from "@/types/lowAbsorb";
import { cn } from "@/lib/utils";
import { RiskBadge } from "./RiskSummaryCards";

const HEADERS = ["股票代码", "股票名称", "所属分支", "信号等级", "MA20 偏离", "量比", "下影线 ATR", "入选理由", "拦截原因", "状态", "操作"];

type SignalPanelProps = {
  signals: LowAbsorbSignal[];
  selectedId?: string | null;
  onSelect?: (signal: LowAbsorbSignal) => void;
  onSendFeishu?: (signal: LowAbsorbSignal) => void;
};

export function SignalPanel({ signals, selectedId, onSelect, onSendFeishu }: SignalPanelProps) {
  const aGradeCount = signals.filter((signal) => signal.grade.startsWith("A")).length;
  const bGradeCount = signals.filter((signal) => signal.grade.startsWith("B")).length;
  const rejected = signals.filter((signal) => signal.interceptReason !== "无" || signal.status.includes("INVALID"));
  const best = signals
    .filter((signal) => signal.interceptReason === "无")
    .sort((left, right) => Number(right.priorityScore ?? 0) - Number(left.priorityScore ?? 0))[0] ?? signals[0];
  const funnel = ["股票池", "宏观闸门", "产业链闸门", "主板过滤", "技术过滤", "交易计划"];

  return (
    <div className="space-y-4">
      <section className="rounded-lg border bg-card p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-semibold text-foreground">信号漏斗</h2>
            <p className="mt-1 text-xs text-muted-foreground">信号先通过决策漏斗，再进入下方明细表。</p>
          </div>
          <RiskBadge level={rejected.length ? "warning" : "normal"} label={`${signals.length} 个信号`} />
        </div>
        <div className="mt-4 grid gap-2 md:grid-cols-6">
          {funnel.map((stage, index) => (
            <div key={stage} className="rounded-md border bg-background p-3">
              <p className="text-[11px] font-medium text-muted-foreground">Step {index + 1}</p>
              <p className="mt-1 text-sm font-semibold text-foreground">{stage}</p>
            </div>
          ))}
        </div>
      </section>

      <section className="grid gap-4 xl:grid-cols-[0.85fr_1fr_1fr]">
        <article className="rounded-lg border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">信号等级仪表</h2>
          <dl className="mt-4 grid gap-3">
            <div className="rounded-md border bg-background p-3">
              <dt className="text-xs text-muted-foreground">A 级信号</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums text-foreground">{aGradeCount}</dd>
            </div>
            <div className="rounded-md border bg-background p-3">
              <dt className="text-xs text-muted-foreground">B 级信号</dt>
              <dd className="mt-1 text-2xl font-semibold tabular-nums text-foreground">{bGradeCount}</dd>
            </div>
            <div className="rounded-md border bg-background p-3">
              <dt className="text-xs text-muted-foreground">拒绝原因</dt>
              <dd className="mt-1 text-sm text-foreground">{rejected.map((signal) => signal.interceptReason).join("；") || "暂无"}</dd>
            </div>
          </dl>
        </article>

        <article className="rounded-lg border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">最佳候选卡</h2>
          {best ? (
            <div className="mt-4 rounded-md border bg-background p-3">
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-base font-semibold text-foreground">{best.stockName}</p>
                  <p className="mt-1 text-xs text-muted-foreground">{best.stockCode} · {best.branch}</p>
                </div>
                <RiskBadge level={best.riskLevel} label={best.grade} />
              </div>
              <p className="mt-3 text-xs leading-5 text-muted-foreground">{best.chainExplanation || best.reason}</p>
            </div>
          ) : (
            <p className="mt-4 text-sm text-muted-foreground">暂无候选。</p>
          )}
        </article>

        <article className="rounded-lg border bg-card p-4">
          <h2 className="text-sm font-semibold text-foreground">信号雷达</h2>
          <div className="mt-4 space-y-3">
            {signals.slice(0, 4).map((signal) => (
              <div key={signal.id} className="grid grid-cols-[92px_minmax(0,1fr)_48px] items-center gap-2 text-xs">
                <span className="truncate text-muted-foreground">{signal.stockName}</span>
                <div className="h-2 rounded-full bg-muted">
                  <div
                    className="h-2 rounded-full bg-primary"
                    style={{ width: `${Math.min(100, Math.max(12, Number(signal.priorityScore ?? 50)))}%` }}
                  />
                </div>
                <span className="text-right tabular-nums text-foreground">{signal.priorityScore ?? "-"}</span>
              </div>
            ))}
          </div>
        </article>
      </section>

      <section className="rounded-lg border bg-card">
        <div className="border-b px-4 py-3">
          <h2 className="text-base font-semibold text-foreground">今日信号</h2>
          <p className="mt-1 text-xs text-muted-foreground">下方表格用于复核每一条信号的闸门、技术指标和人工动作。</p>
        </div>
        <div className="overflow-x-auto">
        <table className="w-full min-w-[1120px] text-left text-xs">
          <thead className="bg-muted/50 text-muted-foreground">
            <tr>
              {HEADERS.map((header) => (
                <th key={header} className="whitespace-nowrap px-3 py-2 font-medium">{header}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y">
            {signals.map((signal) => (
              <tr
                key={signal.id}
                data-testid={`signal-row-${signal.id}`}
                className={cn("align-top", selectedId === signal.id && "bg-primary/5")}
                onClick={() => onSelect?.(signal)}
              >
                <td className="whitespace-nowrap px-3 py-3 font-mono text-foreground">{signal.stockCode}</td>
                <td className="whitespace-nowrap px-3 py-3 font-medium text-foreground">{signal.stockName}</td>
                <td className="whitespace-nowrap px-3 py-3 text-muted-foreground">{signal.branch}</td>
                <td className="whitespace-nowrap px-3 py-3"><RiskBadge level={signal.riskLevel} label={signal.grade} /></td>
                <td className="whitespace-nowrap px-3 py-3 tabular-nums">{signal.ma20Deviation}</td>
                <td className="whitespace-nowrap px-3 py-3 tabular-nums">{signal.volumeRatio}</td>
                <td className="whitespace-nowrap px-3 py-3 tabular-nums">{signal.lowerShadowAtr}</td>
                <td className="max-w-[220px] px-3 py-3 leading-5 text-muted-foreground">{signal.reason}</td>
                <td className="max-w-[180px] px-3 py-3 leading-5 text-muted-foreground">{signal.interceptReason}</td>
                <td className="whitespace-nowrap px-3 py-3">{signal.status}</td>
                <td className="px-3 py-3">
                  <div className="flex flex-wrap gap-1.5">
                    <button type="button" onClick={(event) => { event.stopPropagation(); onSelect?.(signal); }} className="rounded-md border px-2 py-1 text-xs hover:bg-muted">生成交易计划</button>
                    <button type="button" onClick={(event) => { event.stopPropagation(); onSendFeishu?.(signal); }} className="rounded-md border px-2 py-1 text-xs hover:bg-muted">推送飞书</button>
                    <button type="button" className="rounded-md border px-2 py-1 text-xs hover:bg-muted">标记失效</button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
    </div>
  );
}
