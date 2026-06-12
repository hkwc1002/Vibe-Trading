import { useState } from "react";

import { BacktestMetricCards } from "@/components/low-absorb/backtest/BacktestMetricCards";
import { BacktestOverview } from "@/components/low-absorb/backtest/BacktestOverview";
import { BacktestParameterPanel } from "@/components/low-absorb/backtest/BacktestParameterPanel";
import { BranchAttributionPanel } from "@/components/low-absorb/backtest/BranchAttributionPanel";
import { HistoricalSignalTable } from "@/components/low-absorb/backtest/HistoricalSignalTable";
import { ImprovementSuggestions } from "@/components/low-absorb/backtest/ImprovementSuggestions";
import { SensitivityMatrix } from "@/components/low-absorb/backtest/SensitivityMatrix";
import { cn } from "@/lib/utils";
import { LOW_ABSORB_BACKTEST_MOCK } from "@/mocks/lowAbsorb";
import { LowAbsorbPageShell } from "./shared";

const TABS = ["回测总览", "策略参数", "历史信号", "参数敏感性", "分支归因", "改进建议"] as const;
type BacktestTab = (typeof TABS)[number];

export function Backtest() {
  const [activeTab, setActiveTab] = useState<BacktestTab>("回测总览");

  return (
    <LowAbsorbPageShell
      title="策略回测"
      description="展示低吸策略回测指标、参数、历史信号、敏感性、分支归因和改进建议的 mock 工作区。"
    >
      <div className="flex flex-wrap gap-2 border-b pb-2">
        {TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setActiveTab(tab)}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition",
              activeTab === tab
                ? "bg-primary text-primary-foreground"
                : "bg-muted text-muted-foreground hover:bg-muted/80 hover:text-foreground",
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {activeTab === "回测总览" && (
        <>
          <BacktestOverview />
          <BacktestMetricCards metrics={LOW_ABSORB_BACKTEST_MOCK.metrics} />
        </>
      )}
      {activeTab === "策略参数" && (
        <BacktestParameterPanel parameters={LOW_ABSORB_BACKTEST_MOCK.parameters} />
      )}
      {activeTab === "历史信号" && (
        <HistoricalSignalTable rows={LOW_ABSORB_BACKTEST_MOCK.historicalSignals} />
      )}
      {activeTab === "参数敏感性" && (
        <SensitivityMatrix rows={LOW_ABSORB_BACKTEST_MOCK.sensitivity} />
      )}
      {activeTab === "分支归因" && (
        <BranchAttributionPanel rows={LOW_ABSORB_BACKTEST_MOCK.branchAttribution} />
      )}
      {activeTab === "改进建议" && (
        <ImprovementSuggestions suggestions={LOW_ABSORB_BACKTEST_MOCK.suggestions} />
      )}
    </LowAbsorbPageShell>
  );
}
