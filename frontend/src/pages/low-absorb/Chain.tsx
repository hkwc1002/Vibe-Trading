import { useEffect, useMemo, useState } from "react";
import { lowAbsorbApi } from "@/lib/lowAbsorbApi";
import { formatCnyYi, formatPctDecimal, formatRatio } from "@/lib/lowAbsorbFormat";
import type { LowAbsorbChainSector, LowAbsorbChainSnapshot, LowAbsorbCostChainComponent } from "@/types/lowAbsorb";
import { cn } from "@/lib/utils";
import { LowAbsorbPageShell } from "./shared";

const EMPTY_CHAIN: LowAbsorbChainSnapshot = {
  activeVersion: "GB300 NVL72",
  sectorTabs: [
    { id: "cost-overview", label: "成本总览" },
    { id: "gpu", label: "GPU/加速卡" },
    { id: "hbm", label: "HBM/存储" },
    { id: "cpo", label: "CPO/光模块" },
    { id: "pcb", label: "PCB/高速板" },
    { id: "odm", label: "服务器ODM" },
    { id: "cooling", label: "液冷散热" },
    { id: "power", label: "电源连接器" },
  ],
  costModels: [
    { version: "GB200 NVL72", is_editable: false, components: [] },
    { version: "GB300 NVL72", is_editable: false, components: [] },
    { version: "custom/manual", is_editable: true, components: [] },
  ],
  costTable: [],
  sectors: [],
};

function display(value: string | number) {
  return String(value);
}

function displaySectorMetric(label: string, value: string | number) {
  if (label === "成交额" || label === "资金流") return formatCnyYi(value);
  if (label === "涨跌幅" || label === "趋势斜率") return formatPctDecimal(value);
  if (label === "量比" || label === "RS 强度") return formatRatio(value);
  return display(value);
}

function confidenceLabel(value?: string) {
  if (value === "high") return "高";
  if (value === "medium") return "中";
  if (value === "low") return "低";
  return value || "未知";
}

function displayCostVersion(version: string): string {
  return version === "custom/manual" ? "自定义/手动" : version;
}

function sourceTypeLabel(value?: string): string {
  if (value === "broker_estimate") return "机构估算";
  if (value === "official") return "官方资料";
  if (value === "industry_research") return "产业研究";
  if (value === "manual") return "手动维护";
  return value || "未知来源";
}

function stockRoleLabel(role: LowAbsorbChainSector["stocks"][number]["role"]): string {
  const labels: Record<LowAbsorbChainSector["stocks"][number]["role"], string> = {
    leader: "龙头",
    core_middle_cap: "中军",
    sentiment_stock: "情绪股",
    mainboard_mapping: "主板映射",
    watch_only: "观察股",
  };
  return labels[role] ?? role;
}

function CostOverview({ snapshot, onSaveManual }: { snapshot: LowAbsorbChainSnapshot; onSaveManual: (rows: LowAbsorbCostChainComponent[]) => void }) {
  const [draftRows, setDraftRows] = useState<LowAbsorbCostChainComponent[]>(snapshot.costTable);

  useEffect(() => {
    setDraftRows(snapshot.costTable);
  }, [snapshot.costTable]);

  function updateRow(index: number, key: "cost_weight" | "signal_weight", value: string) {
    setDraftRows((rows) => rows.map((row, rowIndex) => rowIndex === index ? { ...row, [key]: value } : row));
  }

  return (
    <section className="space-y-4">
      <article className="rounded-lg border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">英伟达 AI 服务器成本链</h2>
            <p className="mt-2 max-w-3xl text-sm leading-6 text-muted-foreground">
              成本权重与信号权重来自后端配置或可编辑设置；官方资料用于确认规格，产业资料仅作为估算来源并显示置信度。
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            {snapshot.costModels.map((model) => (
              <span key={model.version} className="rounded-md border bg-background px-3 py-2 text-xs font-medium text-foreground">
                {displayCostVersion(model.version)}
              </span>
            ))}
          </div>
        </div>
      </article>

      <article className="rounded-lg border bg-card p-4 shadow-sm">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-base font-semibold text-foreground">成本总览</h2>
          <button type="button" onClick={() => onSaveManual(draftRows)} className="rounded-md border px-3 py-2 text-xs font-medium hover:bg-muted">
            保存自定义/手动版本
          </button>
        </div>
        <div className="mt-4 overflow-x-auto rounded-md border">
          <table className="min-w-[1420px] w-full text-left text-xs">
            <thead className="bg-muted/60 text-muted-foreground">
              <tr>
                <th className="px-3 py-2 font-medium">组件</th>
                <th className="px-3 py-2 font-medium">成本权重</th>
                <th className="px-3 py-2 font-medium">权重区间</th>
                <th className="px-3 py-2 font-medium">代际成本增幅</th>
                <th className="px-3 py-2 font-medium">相关板块</th>
                <th className="px-3 py-2 font-medium">A 股龙头</th>
                <th className="px-3 py-2 font-medium">可交易主板映射</th>
                <th className="px-3 py-2 font-medium">信号权重</th>
                <th className="px-3 py-2 font-medium">来源与置信度</th>
                <th className="px-3 py-2 font-medium">截至日期</th>
              </tr>
            </thead>
            <tbody className="divide-y">
              {draftRows.map((row, index) => (
                <tr key={`${row.component}-${index}`}>
                  <td className="px-3 py-2 font-medium text-foreground">{row.component}</td>
                  <td className="px-3 py-2">
                    <input aria-label={`${row.component} 成本权重`} className="w-20 rounded-md border bg-background px-2 py-1" value={display(row.cost_weight)} onChange={(event) => updateRow(index, "cost_weight", event.target.value)} />
                  </td>
                  <td className="px-3 py-2 tabular-nums text-muted-foreground">{(row.cost_weight_range || []).map(display).join(" - ") || "-"}</td>
                  <td className="px-3 py-2 tabular-nums text-muted-foreground">{formatPctDecimal(row.cost_increase_vs_previous_generation)}</td>
                  <td className="px-3 py-2 text-muted-foreground">{row.related_sector}</td>
                  <td className="px-3 py-2 text-muted-foreground">{row.a_share_leaders.join("、")}</td>
                  <td className="px-3 py-2 font-mono text-muted-foreground">{row.tradable_mainboard_mapping.join("、")}</td>
                  <td className="px-3 py-2">
                    <input aria-label={`${row.component} 信号权重`} className="w-20 rounded-md border bg-background px-2 py-1" value={display(row.signal_weight)} onChange={(event) => updateRow(index, "signal_weight", event.target.value)} />
                  </td>
                  <td className="max-w-[260px] px-3 py-2 text-muted-foreground">
                    <div className="flex flex-wrap gap-1">
                      <span className="rounded-md border bg-background px-2 py-0.5 text-[11px] text-foreground">{sourceTypeLabel(row.source_type || row.data_source)}</span>
                      <span className="rounded-md border bg-background px-2 py-0.5 text-[11px] text-foreground">{confidenceLabel(row.confidence)}</span>
                      {row.is_estimated && <span className="rounded-md border bg-background px-2 py-0.5 text-[11px] text-foreground">估算</span>}
                    </div>
                    <p className="mt-1 leading-5">{row.source_title || row.data_source}</p>
                    {row.methodology_note && <p className="mt-1 leading-5">{row.methodology_note}</p>}
                  </td>
                  <td className="px-3 py-2 text-muted-foreground">{row.as_of}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </article>
    </section>
  );
}

function SectorWorkspace({ sector }: { sector: LowAbsorbChainSector }) {
  return (
    <section data-testid={`chain-sector-${sector.sector_id}`} className="space-y-4">
      <article className="rounded-lg border bg-card p-5 shadow-sm">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-semibold text-foreground">{sector.label}</h2>
            <p className="mt-1 text-sm text-muted-foreground">板块指数：{sector.sector_index}</p>
          </div>
          <span className="rounded-md border px-3 py-2 text-xs font-medium text-foreground">RS 强度 {formatRatio(sector.rs_strength)}</span>
        </div>
        <dl className="mt-4 grid gap-3 md:grid-cols-4 xl:grid-cols-8">
          {[
            ["涨跌幅", sector.price_change_pct],
            ["成交额", sector.turnover_cny],
            ["量比", sector.volume_ratio],
            ["RS 强度", sector.rs_strength],
            ["资金流", sector.fund_flow_cny],
            ["趋势斜率", sector.trend_slope],
            ["涨停数", sector.limit_up_count],
            ["炸板数", sector.limit_break_count],
          ].map(([label, value]) => (
            <div key={label} className="rounded-md border bg-background p-3">
              <dt className="text-xs text-muted-foreground">{label}</dt>
              <dd className="mt-1 text-sm font-semibold tabular-nums text-foreground">{displaySectorMetric(String(label), value as string | number)}</dd>
            </div>
          ))}
        </dl>
      </article>

      <section className="grid gap-3 xl:grid-cols-5">
        {sector.stocks.slice(0, 5).map((stock) => (
          <article key={`${stock.role}-${stock.stock_code}`} className="rounded-lg border bg-card p-4 shadow-sm">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-sm font-semibold text-foreground">{stock.stock_name}</h3>
                <p className="mt-1 font-mono text-xs text-muted-foreground">{stock.stock_code}</p>
              </div>
              <span className="rounded-md border px-2 py-1 text-[11px] font-medium text-foreground">{stockRoleLabel(stock.role)}</span>
            </div>
            <dl className="mt-3 space-y-2 text-xs">
              <div className="flex justify-between gap-2"><dt className="text-muted-foreground">强度评分</dt><dd className="font-medium text-foreground">{display(stock.strength_score)}</dd></div>
              <div className="flex justify-between gap-2"><dt className="text-muted-foreground">量能状态</dt><dd className="font-medium text-foreground">{stock.volume_condition}</dd></div>
              <div className="flex justify-between gap-2"><dt className="text-muted-foreground">低吸适配度</dt><dd className="font-medium text-foreground">{stock.low_absorb_suitability}</dd></div>
            </dl>
            <p className="mt-3 text-xs leading-5 text-muted-foreground">{stock.reason}</p>
            <p className="mt-2 rounded-md bg-muted px-2 py-1 text-xs text-muted-foreground">{stock.current_recommendation}</p>
          </article>
        ))}
      </section>
    </section>
  );
}

export function Chain() {
  const [snapshot, setSnapshot] = useState<LowAbsorbChainSnapshot>(EMPTY_CHAIN);
  const [activeTab, setActiveTab] = useState("cost-overview");
  const [message, setMessage] = useState("");

  useEffect(() => {
    lowAbsorbApi.getChainSnapshot().then(setSnapshot).catch(() => setSnapshot(EMPTY_CHAIN));
  }, []);

  const activeSector = useMemo(
    () => snapshot.sectors.find((sector) => sector.sector_id === activeTab),
    [activeTab, snapshot.sectors],
  );

  async function handleSaveManual(rows: LowAbsorbCostChainComponent[]) {
    const result = await lowAbsorbApi.patchCostChainModel("custom/manual", rows);
    setSnapshot((current) => ({
      ...current,
      costModels: current.costModels.map((model) => model.version === result.version ? { ...model, components: result.components } : model),
      costTable: result.components.length ? result.components : current.costTable,
    }));
    setMessage("自定义/手动成本链设置已保存");
  }

  return (
    <LowAbsorbPageShell
      title="AI 产业链"
      description="以英伟达 AI 服务器成本链为核心的板块研究工作台，输出会反馈到交易工作台的信号排序和交易计划解释。"
    >
      <div className="flex flex-wrap gap-2 border-b pb-3">
        {snapshot.sectorTabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            onClick={() => setActiveTab(tab.id)}
            className={cn(
              "rounded-md px-3 py-2 text-sm font-medium transition-colors",
              activeTab === tab.id ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:bg-muted hover:text-foreground",
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>
      {message && <p className="rounded-md border bg-muted px-3 py-2 text-sm text-muted-foreground">{message}</p>}
      {activeTab === "cost-overview" ? <CostOverview snapshot={snapshot} onSaveManual={handleSaveManual} /> : activeSector ? <SectorWorkspace sector={activeSector} /> : <p className="text-sm text-muted-foreground">该板块暂无数据。</p>}
    </LowAbsorbPageShell>
  );
}
