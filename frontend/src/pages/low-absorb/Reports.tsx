import { useEffect, useState } from "react";
import { ClipboardCheck, FileText, History, Loader2, Send } from "lucide-react";
import { lowAbsorbApi } from "@/lib/lowAbsorbApi";
import type { LowAbsorbApiCloseReport, LowAbsorbApiNotificationResult } from "@/types/lowAbsorb";
import { LowAbsorbPageShell } from "./shared";

function todayStr(): string {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${y}-${m}-${day}`;
}

export function Reports() {
  const [reports, setReports] = useState<LowAbsorbApiCloseReport[]>([]);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [notifying, setNotifying] = useState(false);
  const [notifyResult, setNotifyResult] = useState<LowAbsorbApiNotificationResult | null>(null);

  const loadReports = () => {
    setLoading(true);
    lowAbsorbApi
      .listReports()
      .then((data) => {
        setReports(data.reports ?? []);
      })
      .catch(() => {
        setReports([]);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  useEffect(() => {
    loadReports();
  }, []);

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await lowAbsorbApi.createCloseReport(todayStr());
      await loadReports();
    } catch {
      // silently fail — the UI stays usable
    } finally {
      setGenerating(false);
    }
  };

  const handleNotify = async (reportId?: string) => {
    setNotifying(true);
    setNotifyResult(null);
    try {
      const result = await lowAbsorbApi.notifyCloseReport(reportId);
      setNotifyResult(result);
    } catch {
      setNotifyResult({
        ok: false,
        message: "推送失败",
      } as LowAbsorbApiNotificationResult);
    } finally {
      setNotifying(false);
    }
  };

  const latestReport = reports.length > 0 ? reports[reports.length - 1] : null;
  const archive = reports.length > 1 ? reports.slice(0, -1).reverse() : [];

  return (
    <LowAbsorbPageShell
      title="复盘报告"
      description="展示收盘报告、人工成交复盘和策略复盘材料。"
    >
      <div className="flex flex-wrap gap-3">
        <button
          type="button"
          onClick={handleGenerate}
          disabled={generating}
          className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
        >
          {generating ? <Loader2 className="h-4 w-4 animate-spin" /> : <FileText className="h-4 w-4" />}
          生成复盘报告
        </button>
      </div>

      {latestReport && (
        <section className="rounded-lg border bg-card p-5 shadow-sm">
          <div className="flex items-start justify-between gap-4">
            <div>
              <h2 className="text-lg font-semibold text-foreground">
                最新报告 &mdash; {latestReport.trade_date}
              </h2>
              <p className="mt-1 text-sm text-muted-foreground">{latestReport.summary}</p>
            </div>
            <button
              type="button"
              onClick={() => handleNotify(latestReport.report_id)}
              disabled={notifying}
              className="inline-flex items-center gap-2 rounded-md border px-3 py-2 text-sm font-medium text-foreground hover:bg-muted disabled:opacity-50"
            >
              {notifying ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              推送飞书
            </button>
          </div>

          <div className="mt-4 grid gap-3 md:grid-cols-3">
            <div className="rounded-md border bg-background p-3">
              <p className="text-xs text-muted-foreground">今日信号</p>
              <p className="mt-1 text-xl font-semibold tabular-nums text-foreground">
                {latestReport.signals.length}
              </p>
            </div>
            <div className="rounded-md border bg-background p-3">
              <p className="text-xs text-muted-foreground">交易计划</p>
              <p className="mt-1 text-xl font-semibold tabular-nums text-foreground">
                {latestReport.trade_plans.length}
              </p>
            </div>
            <div className="rounded-md border bg-background p-3">
              <p className="text-xs text-muted-foreground">持仓</p>
              <p className="mt-1 text-xl font-semibold tabular-nums text-foreground">
                {latestReport.positions.length}
              </p>
            </div>
          </div>

          {latestReport.review_items.length > 0 && (
            <div className="mt-4">
              <h3 className="text-sm font-medium text-foreground">复核事项</h3>
              <ul className="mt-2 space-y-1">
                {latestReport.review_items.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2 text-sm text-muted-foreground">
                    <ClipboardCheck className="mt-0.5 h-3.5 w-3.5 shrink-0" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {notifyResult && (
            <div
              className={`mt-3 rounded-md border p-3 text-sm ${
                notifyResult.ok
                  ? "border-green-200 bg-green-50 text-green-800"
                  : "border-yellow-200 bg-yellow-50 text-yellow-800"
              }`}
            >
              {notifyResult.ok
                ? "飞书推送成功"
                : `推送失败：${notifyResult.message || notifyResult.error || "未知错误"}`}
            </div>
          )}
        </section>
      )}

      {archive.length > 0 && (
        <section className="rounded-lg border bg-card p-5 shadow-sm">
          <h2 className="text-base font-semibold text-foreground">历史归档</h2>
          <div className="mt-4 space-y-2">
            {archive.map((report) => (
              <div
                key={report.report_id}
                className="flex items-center justify-between rounded-md border bg-background p-3"
              >
                <div className="flex items-center gap-3">
                  <History className="h-4 w-4 text-muted-foreground" />
                  <div>
                    <p className="text-sm font-medium text-foreground">{report.trade_date}</p>
                    <p className="text-xs text-muted-foreground">{report.summary}</p>
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => handleNotify(report.report_id)}
                  disabled={notifying}
                  className="inline-flex items-center gap-1 rounded-md border px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted disabled:opacity-50"
                >
                  <Send className="h-3 w-3" />
                  推送
                </button>
              </div>
            ))}
          </div>
        </section>
      )}

      {loading && (
        <div className="flex items-center justify-center py-12 text-muted-foreground">
          <Loader2 className="mr-2 h-5 w-5 animate-spin" />
          加载中...
        </div>
      )}

      {!loading && reports.length === 0 && (
        <section className="flex min-h-[200px] flex-col items-center justify-center rounded-lg border border-dashed bg-muted/20 p-8 text-center">
          <h2 className="text-base font-medium text-foreground">暂无复盘报告</h2>
          <p className="mt-2 max-w-xl text-sm leading-6 text-muted-foreground">
            点击上方"生成复盘报告"按钮创建首份报告。
          </p>
        </section>
      )}
    </LowAbsorbPageShell>
  );
}
