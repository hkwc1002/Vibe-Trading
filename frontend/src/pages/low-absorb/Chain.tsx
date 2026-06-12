import { BranchRulePanel } from "@/components/low-absorb/chain/BranchRulePanel";
import { BranchStrengthTable } from "@/components/low-absorb/chain/BranchStrengthTable";
import { ChainOverview } from "@/components/low-absorb/chain/ChainOverview";
import { ChainTopologyCard } from "@/components/low-absorb/chain/ChainTopologyCard";
import { StockMappingTable } from "@/components/low-absorb/chain/StockMappingTable";
import { LOW_ABSORB_CHAIN_MOCK } from "@/mocks/lowAbsorb";
import { LowAbsorbPageShell } from "./shared";

export function Chain() {
  return (
    <LowAbsorbPageShell
      title="AI 产业链"
      description="展示 AI 产业链分支强弱、成本拓扑占位和个股映射表，作为后续真实产业链 API 的前端 contract。"
    >
      <ChainOverview items={LOW_ABSORB_CHAIN_MOCK.overview} />
      <ChainTopologyCard nodes={LOW_ABSORB_CHAIN_MOCK.topologyNodes} />
      <div className="grid gap-4 2xl:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)]">
        <BranchStrengthTable branches={LOW_ABSORB_CHAIN_MOCK.branches} />
        <StockMappingTable rows={LOW_ABSORB_CHAIN_MOCK.stockMappings} />
      </div>
      <BranchRulePanel rules={LOW_ABSORB_CHAIN_MOCK.rules} />
    </LowAbsorbPageShell>
  );
}
