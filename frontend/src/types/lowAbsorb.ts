export type LowAbsorbRiskLevel = "normal" | "watch" | "warning" | "danger";

export type LowAbsorbDashboardCard = {
  id: string;
  label: string;
  value: string;
  detail: string;
  riskLevel: LowAbsorbRiskLevel;
  currentStatus?: string;
  keyMetrics?: string[];
  trend?: string;
  nextAction?: string;
};

export type LowAbsorbTask = {
  id: string;
  time: string;
  title: string;
  detail: string;
  riskLevel: LowAbsorbRiskLevel;
};

export type LowAbsorbSignal = {
  id: string;
  stockCode: string;
  stockName: string;
  branch: string;
  grade: string;
  ma20Deviation: string;
  volumeRatio: string;
  lowerShadowAtr: string;
  reason: string;
  interceptReason: string;
  status: string;
  riskLevel: LowAbsorbRiskLevel;
  chainExplanation?: string;
  branchStrength?: string;
  costSignalWeight?: string;
  priorityScore?: string;
  downgradeReason?: string;
  blockReason?: string;
  sectorRole?: string;
};

export type LowAbsorbFeishuPreview = {
  title: string;
  status: string;
  lines: string[];
};

export type LowAbsorbTradePlan = {
  id: string;
  signalId: string;
  stockCode: string;
  stockName: string;
  entryRange: string;
  stopLoss: string;
  positionSize: string;
  maxRisk: string;
  initialRisk: string;
  feishuStatus: string;
  status: string;
  manualOrderText: string;
  riskLevel: LowAbsorbRiskLevel;
  feishuPreview: LowAbsorbFeishuPreview;
  chainExplanation?: string;
  branchStrength?: string;
  costSignalWeight?: string;
  priorityScore?: string;
  downgradeReason?: string;
  blockReason?: string;
  sectorRole?: string;
};

export type LowAbsorbPosition = {
  id: string;
  stockCode: string;
  stockName: string;
  cost: string;
  lastPrice: string;
  stopLoss: string;
  stopLossDistance: string;
  positionSize: string;
  initialRisk: string;
  currentRisk: string;
  rMultiple: string;
  supervisionStatus: string;
  riskLevel: LowAbsorbRiskLevel;
  note: string;
};

export type LowAbsorbWorkbenchMock = {
  dashboardCards: LowAbsorbDashboardCard[];
  tasks: LowAbsorbTask[];
  signals: LowAbsorbSignal[];
  tradePlans: LowAbsorbTradePlan[];
  positions: LowAbsorbPosition[];
  blockedSignals: LowAbsorbSignal[];
};

export type LowAbsorbSentimentMetric = {
  id: string;
  label: string;
  value: string;
  detail: string;
  riskLevel: LowAbsorbRiskLevel;
};

export type LowAbsorbSentimentGate = {
  id: string;
  label: string;
  value: string;
  status: "通过" | "观察" | "拦截";
};

export type LowAbsorbMonitorPreview = {
  id: string;
  source: string;
  title: string;
  status: string;
  detail: string;
};

export type LowAbsorbSentimentMock = {
  metrics: LowAbsorbSentimentMetric[];
  aShareGates: LowAbsorbSentimentGate[];
  globalGates: LowAbsorbSentimentGate[];
  socialPreviews: LowAbsorbMonitorPreview[];
  newsPreviews: LowAbsorbMonitorPreview[];
  rules: string[];
};

export type LowAbsorbSentimentGauge = {
  id: string;
  label: string;
  score: number | string;
  status: string;
  detail: string;
};

export type LowAbsorbInstrumentPanel = {
  id: string;
  label: string;
  value: string | number;
  status: string;
  explanation: string;
};

export type LowAbsorbSentimentEvent = {
  id: string;
  time: string;
  source: string;
  title: string;
  impact: string;
};

export type LowAbsorbSentimentSnapshot = {
  tradingPermission: {
    status: string;
    summary: string;
    nextAction: string;
    blockedReasons?: string[];
  };
  gauges: LowAbsorbSentimentGauge[];
  instrumentPanels: LowAbsorbInstrumentPanel[];
  socialEvents: LowAbsorbSentimentEvent[];
  newsEvents: LowAbsorbSentimentEvent[];
};

export type LowAbsorbChainBranch = {
  id: string;
  name: string;
  relativeStrength: string;
  rank: number;
  slope: string;
  candidates: number;
  status: "强势" | "中性" | "偏弱";
};

export type LowAbsorbChainStockMapping = {
  id: string;
  stockCode: string;
  stockName: string;
  branch: string;
  role: string;
  signalStatus: string;
  riskLevel: LowAbsorbRiskLevel;
};

export type LowAbsorbChainMock = {
  overview: LowAbsorbSentimentMetric[];
  topologyNodes: string[];
  branches: LowAbsorbChainBranch[];
  stockMappings: LowAbsorbChainStockMapping[];
  rules: string[];
};

export type LowAbsorbCostChainComponent = {
  component: string;
  cost_weight: string | number;
  cost_weight_range?: Array<string | number>;
  cost_increase_vs_previous_generation: string | number;
  related_sector: string;
  a_share_leaders: string[];
  tradable_mainboard_mapping: string[];
  signal_weight: string | number;
  data_source: string;
  source_type?: string;
  source_url?: string;
  source_title?: string;
  confidence?: "high" | "medium" | "low" | string;
  is_estimated?: boolean;
  methodology_note?: string;
  as_of: string;
};

export type LowAbsorbCostChainModel = {
  version: string;
  is_editable: boolean;
  components: LowAbsorbCostChainComponent[];
};

export type LowAbsorbChainSectorStock = {
  role: "leader" | "core_middle_cap" | "sentiment_stock" | "mainboard_mapping" | "watch_only";
  stock_code: string;
  stock_name: string;
  strength_score: string | number;
  volume_condition: string;
  low_absorb_suitability: string;
  reason: string;
  current_recommendation: string;
};

export type LowAbsorbChainSector = {
  sector_id: string;
  label: string;
  sector_index: string;
  price_change_pct: string | number;
  turnover_cny: string | number;
  volume_ratio: string | number;
  rs_strength: string | number;
  fund_flow_cny: string | number;
  trend_slope: string | number;
  limit_up_count: number;
  limit_break_count: number;
  stocks: LowAbsorbChainSectorStock[];
};

export type LowAbsorbChainSnapshot = {
  activeVersion: string;
  sectorTabs: Array<{ id: string; label: string }>;
  costModels: LowAbsorbCostChainModel[];
  costTable: LowAbsorbCostChainComponent[];
  sectors: LowAbsorbChainSector[];
  topologyNodes?: string[];
  branches?: LowAbsorbChainBranch[];
  stockMappings?: LowAbsorbChainStockMapping[];
};

export type LowAbsorbBacktestMetric = {
  id: string;
  label: string;
  value: string;
  detail: string;
};

export type LowAbsorbBacktestParameter = {
  id: string;
  label: string;
  value: string;
  detail: string;
};

export type LowAbsorbHistoricalSignal = {
  id: string;
  tradeDate: string;
  stock: string;
  branch: string;
  grade: string;
  nextDayReturn: string;
  maxFloatLoss: string;
  finalR: string;
  stopHit: string;
};

export type LowAbsorbSensitivityCell = {
  id: string;
  parameter: string;
  conservative: string;
  base: string;
  aggressive: string;
};

export type LowAbsorbBranchAttribution = {
  id: string;
  branch: string;
  samples: number;
  averageR: string;
  contribution: string;
};

export type LowAbsorbBacktestMock = {
  metrics: LowAbsorbBacktestMetric[];
  parameters: LowAbsorbBacktestParameter[];
  historicalSignals: LowAbsorbHistoricalSignal[];
  sensitivity: LowAbsorbSensitivityCell[];
  branchAttribution: LowAbsorbBranchAttribution[];
  suggestions: string[];
};

export type LowAbsorbApiSignal = {
  signal_id: string;
  trade_date: string;
  stock_code: string;
  stock_name: string;
  branch_name: string;
  grade: string;
  ma20_deviation_pct: string | number;
  volume_ratio: string | number;
  lower_shadow_atr: string | number;
  reason: string;
  intercept_reasons?: string[];
  status: string;
  chain_explanation?: string;
  branch_strength?: string | number;
  cost_signal_weight?: string | number;
  priority_score?: string | number;
  downgrade_reason?: string;
  block_reason?: string;
  sector_role?: string;
};

export type LowAbsorbApiTradePlan = {
  plan_id: string;
  signal_id: string;
  trade_date: string;
  stock_code: string;
  stock_name: string;
  entry_low: string | number;
  entry_high: string | number;
  stop_loss: string | number;
  planned_position_pct: string | number;
  max_risk_pct: string | number;
  initial_risk_cny: string | number;
  open_stop_risk_cny: string | number;
  r_multiple: string | number;
  rationale: string;
  manual_order_text: string;
  status: string;
  chain_explanation?: string;
  branch_strength?: string | number;
  cost_signal_weight?: string | number;
  priority_score?: string | number;
  downgrade_reason?: string;
  block_reason?: string;
  sector_role?: string;
};

export type LowAbsorbApiManualFill = Record<string, unknown>;

export type LowAbsorbApiPosition = {
  position_id: string;
  plan_id?: string | null;
  stock_code: string;
  stock_name: string;
  avg_cost?: string | number | null;
  cost_price?: string | number | null;
  current_price?: string | number | null;
  stop_loss?: string | number | null;
  current_stop_price?: string | number | null;
  quantity: number;
  position_weight?: string | number | null;
  position_pct?: string | number | null;
  status: string;
  notes?: string[];
  note?: string;
};

export type LowAbsorbApiRisk = {
  position_id: string;
  stock_code: string;
  stock_name: string;
  initial_risk_amount: string | number;
  current_risk_amount: string | number;
  r_multiple: string | number;
  risk_level: LowAbsorbRiskLevel;
  needs_supervision: boolean;
  supervision_status?: string;
};

export type LowAbsorbApiCloseReport = {
  report_id: string;
  trade_date: string;
  summary: string;
  signals: LowAbsorbApiSignal[];
  trade_plans: LowAbsorbApiTradePlan[];
  positions: LowAbsorbApiPosition[];
  review_items: string[];
};

export type LowAbsorbApiSnapshot = {
  signals: LowAbsorbApiSignal[];
  trade_plans: LowAbsorbApiTradePlan[];
  positions: LowAbsorbApiPosition[];
  risk_matrix: LowAbsorbApiRisk[];
  notifications: LowAbsorbApiNotificationResult[];
  reports: LowAbsorbApiCloseReport[];
  blocked_signals?: LowAbsorbApiSignal[];
  sentiment?: Partial<LowAbsorbSentimentSnapshot>;
  chain?: Partial<LowAbsorbChainSnapshot>;
};

export type LowAbsorbApiNotificationResult = {
  notification_id: string;
  ok: boolean;
  notification_type: string;
  idempotency_key: string;
  sent_at: string | null;
  skipped: boolean;
  error: string | null;
  sent: boolean;
  message: string;
};

export type LowAbsorbManualFillRequest = {
  fill_id: string;
  plan_id?: string | null;
  signal_id?: string | null;
  stock_code?: string | null;
  stock_name?: string | null;
  side?: "BUY" | "SELL";
  planned_price?: string | number | null;
  actual_price?: string | number | null;
  fill_price?: string | number | null;
  quantity: number;
  fee?: string | number;
  fees?: string | number;
  executed_at?: string | null;
  filled_at?: string | null;
  execution_note?: string | null;
  subjective_reason?: string | null;
  note?: string;
};

export type LowAbsorbPositionPatchRequest = {
  current_price?: string | number;
  current_stop_price?: string | number;
  status?: string;
  note?: string;
  notes?: string[];
};

export type LowAbsorbPositionCloseRequest = {
  closed_at?: string | null;
  note?: string;
};

export type LowAbsorbSupervisionRequest = {
  trade_date: string;
  observed_at: string;
  open_price: string | number;
  current_price: string | number;
  industry_return?: string | number;
  send_feishu?: boolean;
};

export type LowAbsorbApiSettings = {
  config: Record<string, unknown>;
  maskedWebhook: string | null;
  webhookConfigured?: boolean;
};

export type LowAbsorbSettingsPatchRequest = {
  feishu_webhook?: string;
  config?: Record<string, string>;
};
