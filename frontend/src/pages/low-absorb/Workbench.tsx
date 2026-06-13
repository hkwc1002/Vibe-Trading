import { useCallback, useMemo, useState, useEffect } from "react";
import { FeishuPreviewCard } from "@/components/low-absorb/workbench/FeishuPreviewCard";
import { ManualFillDrawer } from "@/components/low-absorb/workbench/ManualFillDrawer";
import { PositionPanel } from "@/components/low-absorb/workbench/PositionPanel";
import { SignalPanel } from "@/components/low-absorb/workbench/SignalPanel";
import { TradePlanPanel } from "@/components/low-absorb/workbench/TradePlanPanel";
import { WorkbenchOverview } from "@/components/low-absorb/workbench/WorkbenchOverview";
import { lowAbsorbApi } from "@/lib/lowAbsorbApi";
import { cn } from "@/lib/utils";
import { LOW_ABSORB_MOCK } from "@/mocks/lowAbsorb";
import type {
  LowAbsorbApiPosition,
  LowAbsorbApiRisk,
  LowAbsorbApiSignal,
  LowAbsorbApiSnapshot,
  LowAbsorbApiTradePlan,
  LowAbsorbPosition,
  LowAbsorbRiskLevel,
  LowAbsorbSignal,
  LowAbsorbTradePlan,
  LowAbsorbWorkbenchMock,
} from "@/types/lowAbsorb";
import { LowAbsorbPageShell } from "./shared";

type WorkbenchTab = "总览" | "今日信号" | "交易计划" | "人工持仓";
type Selection =
  | { kind: "signal"; id: string }
  | { kind: "plan"; id: string }
  | { kind: "position"; id: string };

const TABS: WorkbenchTab[] = ["总览", "今日信号", "交易计划", "人工持仓"];

function asNumber(value: string | number | null | undefined): number {
  const parsed = Number(value ?? 0);
  return Number.isFinite(parsed) ? parsed : 0;
}

function pct(value: string | number | null | undefined): string {
  return `${(asNumber(value) * 100).toFixed(2)}%`;
}

function riskFromStatus(status: string): LowAbsorbRiskLevel {
  if (status.includes("INVALID") || status.includes("EXIT")) return "danger";
  if (status.includes("SENT") || status.includes("FILLED")) return "watch";
  return "normal";
}

function mapSignal(signal: LowAbsorbApiSignal): LowAbsorbSignal {
  return {
    id: signal.signal_id,
    stockCode: signal.stock_code,
    stockName: signal.stock_name,
    branch: signal.branch_name,
    grade: signal.grade,
    ma20Deviation: pct(signal.ma20_deviation_pct),
    volumeRatio: String(signal.volume_ratio),
    lowerShadowAtr: String(signal.lower_shadow_atr),
    reason: signal.reason,
    interceptReason: signal.intercept_reasons?.join("；") || "无",
    status: signal.status,
    riskLevel: riskFromStatus(signal.status),
  };
}

function mapPlan(plan: LowAbsorbApiTradePlan): LowAbsorbTradePlan {
  const sent = plan.status === "SENT_TO_FEISHU";
  return {
    id: plan.plan_id,
    signalId: plan.signal_id,
    stockCode: plan.stock_code,
    stockName: plan.stock_name,
    entryRange: `${plan.entry_low}-${plan.entry_high}`,
    stopLoss: String(plan.stop_loss),
    positionSize: pct(plan.planned_position_pct),
    maxRisk: pct(plan.max_risk_pct),
    initialRisk: `${plan.initial_risk_cny} 元`,
    feishuStatus: sent ? "已推送" : "待推送",
    status: plan.status,
    manualOrderText: plan.manual_order_text,
    riskLevel: riskFromStatus(plan.status),
    feishuPreview: {
      title: "14:45 低吸交易计划｜人工执行",
      status: sent ? "已推送" : "待推送",
      lines: [
        `${plan.stock_code} ${plan.stock_name}`,
        `建议低吸区间：${plan.entry_low}-${plan.entry_high}`,
        `参考止损：${plan.stop_loss}`,
        `建议仓位：${pct(plan.planned_position_pct)}`,
        `初始 R 风险：${plan.initial_risk_cny} 元`,
        plan.rationale,
      ],
    },
  };
}

function mapPosition(position: LowAbsorbApiPosition, risk?: LowAbsorbApiRisk): LowAbsorbPosition {
  const riskLevel = risk?.risk_level ?? riskFromStatus(position.status);
  return {
    id: position.position_id,
    stockCode: position.stock_code,
    stockName: position.stock_name,
    cost: String(position.avg_cost ?? position.cost_price ?? "-"),
    lastPrice: String(position.current_price ?? "-"),
    stopLoss: String(position.current_stop_price ?? position.stop_loss ?? "-"),
    positionSize: `${position.quantity} 股 / ${pct(position.position_weight ?? position.position_pct)}`,
    initialRisk: risk ? `${risk.initial_risk_amount} 元` : "-",
    currentRisk: risk ? `${risk.current_risk_amount} 元` : "-",
    rMultiple: risk ? `${risk.r_multiple}R` : "-",
    supervisionStatus: risk?.supervision_status || (risk?.needs_supervision ? "10:00 需监督" : "正常跟踪"),
    riskLevel,
    note: position.notes?.join("；") || position.note || "暂无备注",
  };
}

function snapshotToWorkbench(snapshot: LowAbsorbApiSnapshot): LowAbsorbWorkbenchMock {
  const signals = snapshot.signals.map(mapSignal);
  const tradePlans = snapshot.trade_plans.map(mapPlan);
  const positions = snapshot.positions.map((position) =>
    mapPosition(position, snapshot.risk_matrix.find((risk) => risk.position_id === position.position_id)),
  );
  return {
    dashboardCards: [
      { id: "market", label: "市场状态", value: "API", detail: "后端策略闸门已接入", riskLevel: "normal" },
      { id: "signals", label: "今日信号", value: String(signals.length), detail: "来自 /low-absorb/snapshot", riskLevel: signals.length ? "watch" : "normal" },
      { id: "feishu", label: "待推送飞书", value: String(tradePlans.filter((plan) => plan.feishuStatus !== "已推送").length), detail: "计划可推送飞书推荐卡", riskLevel: "watch" },
      { id: "fills", label: "待成交回填", value: String(tradePlans.filter((plan) => plan.status !== "MANUAL_FILLED").length), detail: "等待用户记录人工成交", riskLevel: "warning" },
      { id: "risk", label: "当前持仓风险", value: String(positions.length), detail: "基于人工持仓 R-risk", riskLevel: positions.some((item) => item.riskLevel === "danger") ? "danger" : "watch" },
      { id: "supervision", label: "明日 10:00 需监督", value: String(positions.filter((item) => item.supervisionStatus.includes("10:00")).length), detail: "开盘抗噪后检查", riskLevel: "warning" },
    ],
    tasks: [
      { id: "scan", time: "14:45", title: "执行尾盘低吸扫描", detail: "生成信号与人工交易计划后再推送飞书。", riskLevel: "watch" },
      { id: "fills", time: "手动成交后", title: "回填人工成交", detail: "仅记录外部券商 App 已完成的人工成交。", riskLevel: "warning" },
    ],
    signals,
    tradePlans,
    positions,
  };
}

export function Workbench() {
  const [activeTab, setActiveTab] = useState<WorkbenchTab>("总览");
  const [data, setData] = useState<LowAbsorbWorkbenchMock>(LOW_ABSORB_MOCK);
  const [dataMode, setDataMode] = useState<"loading" | "api" | "demo">("loading");
  const [message, setMessage] = useState("");
  const [selection, setSelection] = useState<Selection | null>(null);

  const loadSnapshot = useCallback(async () => {
    try {
      const snapshot = await lowAbsorbApi.getSnapshot();
      setData(snapshotToWorkbench(snapshot));
      setDataMode("api");
      setMessage("API 数据已同步");
    } catch (error) {
      setData(LOW_ABSORB_MOCK);
      setDataMode("demo");
      setMessage(error instanceof Error ? error.message : "API 暂不可用");
    }
  }, []);

  useEffect(() => {
    void loadSnapshot();
  }, [loadSnapshot]);

  const selectedPlan = useMemo(() => {
    if (selection?.kind === "plan") {
      return data.tradePlans.find((plan) => plan.id === selection.id) ?? data.tradePlans[0];
    }
    if (selection?.kind === "signal") {
      return data.tradePlans.find((plan) => plan.signalId === selection.id) ?? data.tradePlans[0];
    }
    return data.tradePlans[0];
  }, [data.tradePlans, selection]);

  const selectedSignal = useMemo(() => {
    if (selection?.kind === "signal") return data.signals.find((signal) => signal.id === selection.id);
    if (selectedPlan) return data.signals.find((signal) => signal.id === selectedPlan.signalId);
    return data.signals[0];
  }, [data.signals, selectedPlan, selection]);

  const selectedPosition = useMemo(() => {
    if (selection?.kind === "position") return data.positions.find((position) => position.id === selection.id);
    return data.positions[0];
  }, [data.positions, selection]);

  async function handleScanTail() {
    const snapshot = await lowAbsorbApi.scanTail();
    setData(snapshotToWorkbench(snapshot));
    setDataMode("api");
    setMessage(snapshot.message || "14:45 扫描已完成");
  }

  async function handleSendPlanToFeishu(plan: LowAbsorbTradePlan) {
    const result = await lowAbsorbApi.sendTradePlanToFeishu(plan.id);
    setMessage(result.message || (result.ok ? "飞书推荐已推送" : "飞书推荐未推送"));
  }

  async function handleSignalFeishu(signal: LowAbsorbSignal) {
    const plan = data.tradePlans.find((item) => item.signalId === signal.id);
    if (plan) {
      await handleSendPlanToFeishu(plan);
      setSelection({ kind: "plan", id: plan.id });
    }
  }

  async function handleManualFill(plan: LowAbsorbTradePlan, values: { actualPrice: string; quantity: number; note: string }) {
    await lowAbsorbApi.recordFill({
      fill_id: `fill-${plan.id}-${Date.now()}`,
      plan_id: plan.id,
      signal_id: plan.signalId,
      stock_code: plan.stockCode,
      stock_name: plan.stockName,
      side: "BUY",
      actual_price: values.actualPrice,
      quantity: values.quantity,
      executed_at: new Date().toISOString(),
      note: values.note,
    });
    await loadSnapshot();
    setMessage("人工成交已记录，持仓风险已刷新");
  }

  return (
    <LowAbsorbPageShell
      title="交易工作台"
      description="围绕信号、计划、飞书建议、人工成交和持仓监督的人工执行工作区。"
    >
      <div className="flex flex-wrap items-center justify-between gap-3 rounded-lg border bg-card px-4 py-3">
        <div>
          <p className="text-sm font-medium text-foreground">
            {dataMode === "demo" ? "演示数据模式" : dataMode === "loading" ? "正在同步 API" : "API 数据模式"}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{message || "人工执行流程由后端策略与本地记录驱动。"}</p>
        </div>
        <button
          type="button"
          onClick={() => void handleScanTail()}
          className="rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:opacity-90"
        >
          执行 14:45 扫描
        </button>
      </div>

      <div className="flex flex-wrap gap-2 border-b pb-3">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              activeTab === tab
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      <div className="grid gap-4 xl:grid-cols-[minmax(0,1fr)_360px]">
        <section className="space-y-4">
          <div>
            <h2 className="text-xl font-semibold tracking-tight text-foreground">
              {activeTab}
            </h2>
            <p className="mt-1 text-sm text-muted-foreground">
              信号、计划、人工成交与持仓风险均来自 Low Absorb API；网络不可用时仅回落到演示数据。
            </p>
          </div>

          {activeTab === "总览" && <WorkbenchOverview data={data} />}
          {activeTab === "今日信号" && (
            <SignalPanel
              signals={data.signals}
              selectedId={selection?.kind === "signal" ? selection.id : selectedSignal?.id}
              onSelect={(signal) => setSelection({ kind: "signal", id: signal.id })}
              onSendFeishu={(signal) => void handleSignalFeishu(signal)}
            />
          )}
          {activeTab === "交易计划" && (
            <TradePlanPanel
              plans={data.tradePlans}
              selectedId={selectedPlan?.id}
              onSelect={(plan) => setSelection({ kind: "plan", id: plan.id })}
              onSendFeishu={(plan) => void handleSendPlanToFeishu(plan)}
              onRecordFill={(plan) => setSelection({ kind: "plan", id: plan.id })}
            />
          )}
          {activeTab === "人工持仓" && (
            <PositionPanel
              positions={data.positions}
              selectedId={selection?.kind === "position" ? selection.id : selectedPosition?.id}
              onSelect={(position) => setSelection({ kind: "position", id: position.id })}
            />
          )}
        </section>

        <aside className="space-y-4 rounded-lg border bg-card p-4 xl:sticky xl:top-4 xl:self-start">
          <div>
            <h2 className="text-base font-semibold text-foreground">交易计划详情</h2>
            <p className="mt-1 text-xs text-muted-foreground">右侧详情抽屉用于复核信号、计划、飞书预览、人工成交和风险说明。</p>
          </div>
          {selectedSignal && (
            <div className="rounded-md border bg-background p-3 text-xs">
              <p className="font-medium text-foreground">信号详情</p>
              <p className="mt-2 text-muted-foreground">{selectedSignal.stockCode} {selectedSignal.stockName} · {selectedSignal.branch}</p>
              <p className="mt-2 leading-5 text-muted-foreground">{selectedSignal.reason}</p>
            </div>
          )}
          {selectedPlan && (
            <>
              <FeishuPreviewCard preview={selectedPlan.feishuPreview} />
              <ManualFillDrawer plan={selectedPlan} onSubmit={(values) => void handleManualFill(selectedPlan, values)} />
            </>
          )}
          {selectedPosition && (
            <div className="rounded-md border bg-background p-3 text-xs">
              <p className="font-medium text-foreground">风险解释</p>
              <p className="mt-2 text-muted-foreground">{selectedPosition.stockCode} {selectedPosition.stockName}</p>
              <p className="mt-2 leading-5 text-muted-foreground">
                当前风险 {selectedPosition.currentRisk}，R 倍数 {selectedPosition.rMultiple}，监督状态 {selectedPosition.supervisionStatus}。
              </p>
            </div>
          )}
        </aside>
      </div>

      <div className="sticky bottom-0 z-10 rounded-lg border bg-background/95 p-3 shadow-sm backdrop-blur">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-foreground">统一动作</p>
            <p className="text-xs text-muted-foreground">所有动作仅生成建议、通知或记录人工处理结果。</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button type="button" onClick={() => selectedPlan && navigator.clipboard?.writeText(selectedPlan.manualOrderText)} className="rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted">复制人工下单信息</button>
            <button type="button" onClick={() => selectedPlan && void handleSendPlanToFeishu(selectedPlan)} className="rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted">推送飞书</button>
            <button type="button" onClick={() => selectedPlan && setSelection({ kind: "plan", id: selectedPlan.id })} className="rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted">记录人工成交</button>
            <button type="button" className="rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted">生成风控提醒</button>
          </div>
        </div>
      </div>
    </LowAbsorbPageShell>
  );
}
