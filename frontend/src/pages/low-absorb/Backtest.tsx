import { useEffect, useState } from "react";

import { BacktestMetricCards } from "@/components/low-absorb/backtest/BacktestMetricCards";
import { BacktestOverview } from "@/components/low-absorb/backtest/BacktestOverview";
import { BacktestParameterPanel } from "@/components/low-absorb/backtest/BacktestParameterPanel";
import { BranchAttributionPanel } from "@/components/low-absorb/backtest/BranchAttributionPanel";
import { HistoricalSignalTable } from "@/components/low-absorb/backtest/HistoricalSignalTable";
import { ImprovementSuggestions } from "@/components/low-absorb/backtest/ImprovementSuggestions";
import { SensitivityMatrix } from "@/components/low-absorb/backtest/SensitivityMatrix";
import { cn } from "@/lib/utils";
import { lowAbsorbApi } from "@/lib/lowAbsorbApi";
import { LOW_ABSORB_BACKTEST_MOCK } from "@/mocks/lowAbsorb";
import type { LowAbsorbBacktestMock } from "@/types/lowAbsorb";
import { LowAbsorbPageShell } from "./shared";

const TABS = ["回测总览", "策略参数", "历史信号", "参数敏感性", "分支归因", "改进建议"] as const;
type BacktestTab = (typeof TABS)[number];

const FALLBACK_BACKTEST: LowAbsorbBacktestMock = LOW_ABSORB_BACKTEST_MOCK;

export function Backtest() {
  const [activeTab, setActiveTab] = useState<BacktestTab>("回测总览");
  const [data, setData] = useState<LowAbsorbBacktestMock>(FALLBACK_BACKTEST);

  useEffect(() => {
    lowAbsorbApi
      .getBacktestSummary()
      .then((res) => setData(res as unknown as LowAbsorbBacktestMock))
      .catch(() => {
        /* silently keep mock fallback */
      });
  }, []);

  return (
    <LowAbsorbPageShell
      title="策略回测"
      description="展示低吸策略回测指标、参数、历史信号、敏感性、分支归因和改进建议的示例工作区。"
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
          <BacktestOverview metrics={data.metrics} />
          <BacktestMetricCards metrics={data.metrics} />
        </>
      )}
      {activeTab === "策略参数" && (
        <BacktestParameterPanel parameters={data.parameters} />
      )}
      {activeTab === "历史信号" && (
        <HistoricalSignalTable rows={data.historicalSignals} />
      )}
      {activeTab === "参数敏感性" && (
        <SensitivityMatrix rows={data.sensitivity} />
      )}
      {activeTab === "分支归因" && (
        <BranchAttributionPanel rows={data.branchAttribution} />
      )}
      {activeTab === "改进建议" && (
        <ImprovementSuggestions suggestions={data.suggestions} />
      )}
    </LowAbsorbPageShell>
  );
}
