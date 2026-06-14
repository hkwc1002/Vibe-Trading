import { authHeaders } from "@/lib/apiAuth";
import type {
  LowAbsorbApiCloseReport,
  LowAbsorbApiNotificationResult,
  LowAbsorbApiPosition,
  LowAbsorbApiSettings,
  LowAbsorbApiSignal,
  LowAbsorbApiSnapshot,
  LowAbsorbApiTradePlan,
  LowAbsorbChainSnapshot,
  LowAbsorbCostChainComponent,
  LowAbsorbManualFillRequest,
  LowAbsorbPositionCloseRequest,
  LowAbsorbPositionPatchRequest,
  LowAbsorbSettingsPatchRequest,
  LowAbsorbSupervisionRequest,
  LowAbsorbSentimentSnapshot,
} from "@/types/lowAbsorb";

const BASE = "";

class LowAbsorbApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "LowAbsorbApiError";
    this.status = status;
  }
}

async function errorFromResponse(response: Response): Promise<LowAbsorbApiError> {
  let detail = `HTTP ${response.status}`;
  try {
    const body = await response.json();
    detail = body.detail || body.message || detail;
  } catch {
    // Keep the HTTP status fallback when the backend returns non-JSON.
  }
  return new LowAbsorbApiError(detail, response.status);
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const { headers, ...rest } = options ?? {};
  const mergedHeaders: Record<string, string> = { "Content-Type": "application/json", ...authHeaders() };
  if (headers) {
    new Headers(headers).forEach((value, key) => {
      mergedHeaders[key] = value;
    });
  }
  const response = await fetch(`${BASE}${path}`, { ...rest, headers: mergedHeaders });
  if (!response.ok) {
    throw await errorFromResponse(response);
  }
  const text = await response.text();
  return text ? JSON.parse(text) : ({} as T);
}

function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, {
    method: "POST",
    body: body === undefined ? undefined : JSON.stringify(body),
  });
}

function patch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, {
    method: "PATCH",
    body: JSON.stringify(body),
  });
}

export const lowAbsorbApi = {
  getSnapshot: () => request<LowAbsorbApiSnapshot>("/low-absorb/snapshot"),
  scanTail: (body?: { trade_date?: string; at?: string; symbols?: string[] }) =>
    post<LowAbsorbApiSnapshot & { data_source?: string; message?: string }>("/low-absorb/scan-tail", body),
  listSignals: () => request<LowAbsorbApiSignal[]>("/low-absorb/signals"),
  getSignal: (signalId: string) => request<LowAbsorbApiSignal>(`/low-absorb/signals/${encodeURIComponent(signalId)}`),
  patchSignal: (signalId: string, body: Partial<LowAbsorbApiSignal>) =>
    patch<LowAbsorbApiSignal>(`/low-absorb/signals/${encodeURIComponent(signalId)}`, body),
  notifySignal: (signalId: string, force = false) =>
    post<LowAbsorbApiNotificationResult>(`/low-absorb/signals/${encodeURIComponent(signalId)}/notify?force=${force}`),

  createTradePlan: (plan: LowAbsorbApiTradePlan) => post<LowAbsorbApiTradePlan>("/low-absorb/trade-plans", plan),
  listTradePlans: () => request<LowAbsorbApiTradePlan[]>("/low-absorb/trade-plans"),
  sendTradePlanToFeishu: (planId: string, force = false) =>
    post<LowAbsorbApiNotificationResult>(`/low-absorb/trade-plans/${encodeURIComponent(planId)}/send-feishu?force=${force}`),

  recordFill: (body: LowAbsorbManualFillRequest) =>
    post<{ fill: Record<string, unknown>; position: LowAbsorbApiPosition; risk: Record<string, unknown> }>("/low-absorb/fills", body),
  recordPlanFill: (planId: string, body: LowAbsorbManualFillRequest) =>
    post<{ fill: Record<string, unknown>; position: LowAbsorbApiPosition }>(
      `/low-absorb/trade-plans/${encodeURIComponent(planId)}/manual-fills`,
      body,
    ),
  listPositions: () => request<LowAbsorbApiPosition[]>("/low-absorb/positions"),
  getPosition: (positionId: string) =>
    request<LowAbsorbApiPosition>(`/low-absorb/positions/${encodeURIComponent(positionId)}`),
  patchPosition: (positionId: string, body: LowAbsorbPositionPatchRequest) =>
    patch<LowAbsorbApiPosition>(`/low-absorb/positions/${encodeURIComponent(positionId)}`, body),
  closePosition: (positionId: string, body: LowAbsorbPositionCloseRequest = {}) =>
    post<LowAbsorbApiPosition>(`/low-absorb/positions/${encodeURIComponent(positionId)}/close`, body),

  superviseMorning: (body: LowAbsorbSupervisionRequest) =>
    post<{ positions: Array<Record<string, unknown>> }>("/low-absorb/supervise/morning", body),
  supervisePosition: (positionId: string, body: LowAbsorbSupervisionRequest) =>
    post<Record<string, unknown>>(`/low-absorb/supervise/position/${encodeURIComponent(positionId)}`, body),
  sendRiskAlert: (positionId: string, first30mClose: string, industryAlpha: string, supervisionStatus: string, force = false) =>
    post<LowAbsorbApiNotificationResult>(
      `/low-absorb/positions/${encodeURIComponent(positionId)}/risk-alert?first_30m_close=${encodeURIComponent(first30mClose)}&industry_alpha=${encodeURIComponent(industryAlpha)}&supervision_status=${encodeURIComponent(supervisionStatus)}&force=${force}`,
    ),

  listReports: () => request<{ reports: LowAbsorbApiCloseReport[] }>("/low-absorb/reports"),
  createCloseReport: (tradeDate: string) =>
    post<LowAbsorbApiCloseReport>(`/low-absorb/reports/close?trade_date=${encodeURIComponent(tradeDate)}`),
  notifyCloseReport: (reportId?: string, force = false) => {
    const params = new URLSearchParams();
    params.set("force", String(force));
    if (reportId) params.set("report_id", reportId);
    return post<LowAbsorbApiNotificationResult>(`/low-absorb/reports/close/notify?${params.toString()}`);
  },

  getSentimentSnapshot: () => request<LowAbsorbSentimentSnapshot>("/low-absorb/sentiment/snapshot"),
  getChainSnapshot: () => request<LowAbsorbChainSnapshot>("/low-absorb/chain/snapshot"),
  patchCostChainModel: (version: string, components: LowAbsorbCostChainComponent[]) =>
    patch<{ version: string; components: LowAbsorbCostChainComponent[] }>(
      `/low-absorb/chain/cost-models/${encodeURIComponent(version).replace("%2F", "/")}`,
      { components },
    ),
  getBacktestSummary: () => request<Record<string, unknown>>("/low-absorb/backtest/summary"),
  runBacktest: () => post<Record<string, unknown>>("/low-absorb/backtest/run"),

  getSettings: () => request<LowAbsorbApiSettings>("/low-absorb/settings"),
  patchSettings: (body: LowAbsorbSettingsPatchRequest) => patch<LowAbsorbApiSettings>("/low-absorb/settings", body),
  sendTestNotification: (force = false) =>
    post<LowAbsorbApiNotificationResult>(`/low-absorb/notify/test?force=${force}`),
};

export { LowAbsorbApiError };
