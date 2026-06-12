import { useState } from "react";
import { PositionPanel } from "@/components/low-absorb/workbench/PositionPanel";
import { SignalPanel } from "@/components/low-absorb/workbench/SignalPanel";
import { TradePlanPanel } from "@/components/low-absorb/workbench/TradePlanPanel";
import { WorkbenchOverview } from "@/components/low-absorb/workbench/WorkbenchOverview";
import { cn } from "@/lib/utils";
import { LOW_ABSORB_MOCK } from "@/mocks/lowAbsorb";
import { LowAbsorbPageShell } from "./shared";

type WorkbenchTab = "总览" | "今日信号" | "交易计划" | "人工持仓";

const TABS: WorkbenchTab[] = ["总览", "今日信号", "交易计划", "人工持仓"];

export function Workbench() {
  const [activeTab, setActiveTab] = useState<WorkbenchTab>("总览");

  return (
    <LowAbsorbPageShell
      title="交易工作台"
      description="围绕信号、计划、飞书建议、人工成交和持仓监督的人工执行工作区。"
    >
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

      <section className="space-y-4">
        <div>
          <h2 className="text-xl font-semibold tracking-tight text-foreground">
            {activeTab}
          </h2>
          <p className="mt-1 text-sm text-muted-foreground">
            当前工作台仅使用本地 mock 数据，策略规则、扫描结果和风控判断后续由后端服务提供。
          </p>
        </div>

        {activeTab === "总览" && <WorkbenchOverview data={LOW_ABSORB_MOCK} />}
        {activeTab === "今日信号" && <SignalPanel signals={LOW_ABSORB_MOCK.signals} />}
        {activeTab === "交易计划" && <TradePlanPanel plans={LOW_ABSORB_MOCK.tradePlans} />}
        {activeTab === "人工持仓" && <PositionPanel positions={LOW_ABSORB_MOCK.positions} />}
      </section>
    </LowAbsorbPageShell>
  );
}

