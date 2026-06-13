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
  return (
    <section className="rounded-lg border bg-card">
      <div className="border-b px-4 py-3">
        <h2 className="text-base font-semibold text-foreground">今日信号</h2>
        <p className="mt-1 text-xs text-muted-foreground">本表仅展示本地 mock 信号，不包含后端扫描或券商执行连接。</p>
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
  );
}
