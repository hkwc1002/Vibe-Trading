export type LowAbsorbRiskLevel = "normal" | "watch" | "warning" | "danger";

export type LowAbsorbDashboardCard = {
  id: string;
  label: string;
  value: string;
  detail: string;
  riskLevel: LowAbsorbRiskLevel;
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
};

export type LowAbsorbPosition = {
  id: string;
  stockCode: string;
  stockName: string;
  cost: string;
  lastPrice: string;
  stopLoss: string;
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

export type LowAbsorbApiSignal = Record<string, unknown>;
export type LowAbsorbApiTradePlan = Record<string, unknown>;
export type LowAbsorbApiManualFill = Record<string, unknown>;
export type LowAbsorbApiPosition = Record<string, unknown>;
export type LowAbsorbApiRisk = Record<string, unknown>;
export type LowAbsorbApiCloseReport = Record<string, unknown>;

export type LowAbsorbApiSnapshot = {
  signals: LowAbsorbApiSignal[];
  trade_plans: LowAbsorbApiTradePlan[];
  positions: LowAbsorbApiPosition[];
  risk_matrix: LowAbsorbApiRisk[];
  notifications: LowAbsorbApiNotificationResult[];
  reports: LowAbsorbApiCloseReport[];
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
};

export type LowAbsorbSettingsPatchRequest = {
  feishu_webhook?: string;
};
