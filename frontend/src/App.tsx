import { type CSSProperties, useEffect, useMemo, useState } from "react";

import { fetchMockLeads, fetchRecent, fetchSummary, fetchTimeseries, sendLeadToWebhook } from "./api";
import type { MetricsPoint, MetricsSummary, RecentValidation, ReplayLogItem } from "./types";

function StatusPill({ status }: { status: string }) {
  return <span className={`status-pill ${status === "valid" ? "status-ok" : "status-bad"}`}>{status}</span>;
}

function KpiCards({ summary }: { summary: MetricsSummary }) {
  const successPercent = (summary.success_rate * 100).toFixed(1);
  const donutStyle = { "--progress": `${successPercent}%` } as CSSProperties;
  return (
    <section className="kpi-grid">
      <article className="kpi-card">
        <span>Total Leads</span>
        <strong>{summary.total}</strong>
      </article>
      <article className="kpi-card success">
        <span>Successful</span>
        <strong>{summary.valid}</strong>
      </article>
      <article className="kpi-card danger">
        <span>Failed</span>
        <strong>{summary.invalid}</strong>
      </article>
      <article className="kpi-card">
        <span>Success Rate</span>
        <div className="success-donut" style={donutStyle}>
          <strong>{successPercent}%</strong>
        </div>
      </article>
    </section>
  );
}

function TrendPanel({ points }: { points: MetricsPoint[] }) {
  const maxTotal = Math.max(...points.map((point) => point.total), 1);
  return (
    <section className="panel">
      <h2>Validation Dynamics</h2>
      <div className="bars">
        {points.map((point) => (
          <div key={point.bucket} className="bar-row">
            <span>{new Date(point.bucket).toLocaleDateString()}</span>
            <div className="bar-track">
              <div className="bar-fill" style={{ width: `${(point.total / maxTotal) * 100}%` }} />
            </div>
            <strong>{point.total}</strong>
          </div>
        ))}
      </div>
    </section>
  );
}

function ReasonsPanel({ reasons }: { reasons: Record<string, number> }) {
  const entries = Object.entries(reasons).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((acc, [, count]) => acc + count, 0) || 1;
  return (
    <section className="panel">
      <h2>Failure Reasons</h2>
      <ul className="reason-list">
        {entries.map(([reason, count]) => (
          <li key={reason}>
            <div className="reason-meta">
              <span>{reason}</span>
              <small>{((count / total) * 100).toFixed(1)}%</small>
            </div>
            <strong>{count}</strong>
          </li>
        ))}
      </ul>
    </section>
  );
}

function RecentPanel({ recent }: { recent: RecentValidation[] }) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const filtered = useMemo(
    () =>
      recent.filter((item) =>
        `${item.lead_id} ${item.contact_phone_raw} ${item.normalized_phone ?? ""} ${item.reason ?? ""}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [query, recent],
  );
  const totalPages = Math.max(1, Math.ceil(filtered.length / pageSize));
  const safePage = Math.min(page, totalPages);
  const start = (safePage - 1) * pageSize;
  const paged = filtered.slice(start, start + pageSize);

  useEffect(() => {
    setPage(1);
  }, [query, pageSize]);

  const formatPhone = (value: string | null | undefined) => {
    if (!value) {
      return "-";
    }
    const compact = value.replace(/\s+/g, " ").trim();
    return compact.length > 22 ? `${compact.slice(0, 22)}...` : compact;
  };

  const formatDate = (value: string) => {
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) {
      return value;
    }
    return parsed.toLocaleString();
  };

  const prettifyReason = (reason: string | null) => {
    if (!reason) {
      return "-";
    }
    return reason.replace(/_/g, " ");
  };

  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Latest Processed Leads</h2>
        <div className="table-controls">
          <input
            className="search-input"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search by lead or phone..."
          />
          <select
            className="rows-select"
            value={pageSize}
            onChange={(event) => setPageSize(Number(event.target.value))}
            aria-label="Rows per page"
          >
            <option value={5}>5 rows</option>
            <option value={10}>10 rows</option>
            <option value={20}>20 rows</option>
          </select>
        </div>
      </div>
      <div className="table-wrapper">
        <table className="recent-table">
          <thead>
            <tr>
              <th>Lead</th>
              <th>Raw</th>
              <th>Normalized</th>
              <th>Status</th>
              <th>Reason</th>
              <th>Source</th>
              <th>At</th>
            </tr>
          </thead>
          <tbody>
            {paged.map((item) => (
              <tr key={`${item.lead_id}-${item.processed_at}`}>
                <td>{item.lead_id}</td>
                <td className="mono-cell" title={item.contact_phone_raw || "-"}>
                  {formatPhone(item.contact_phone_raw)}
                </td>
                <td className="mono-cell" title={item.normalized_phone ?? "-"}>
                  {formatPhone(item.normalized_phone)}
                </td>
                <td>
                  <StatusPill status={item.status} />
                </td>
                <td className="reason-cell">{prettifyReason(item.reason)}</td>
                <td>
                  <span className="source-chip">{item.source}</span>
                </td>
                <td>{formatDate(item.processed_at)}</td>
              </tr>
            ))}
            {paged.length === 0 && (
              <tr>
                <td colSpan={7} className="empty-table">
                  No rows match your current filters.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="pagination">
        <span>
          Showing {paged.length === 0 ? 0 : start + 1}-{Math.min(start + paged.length, filtered.length)} of {filtered.length}
        </span>
        <div className="button-row">
          <button className="action-btn ghost" disabled={safePage <= 1} onClick={() => setPage((prev) => Math.max(1, prev - 1))}>
            Prev
          </button>
          <span className="page-indicator">
            Page {safePage}/{totalPages}
          </span>
          <button
            className="action-btn ghost"
            disabled={safePage >= totalPages}
            onClick={() => setPage((prev) => Math.min(totalPages, prev + 1))}
          >
            Next
          </button>
        </div>
      </div>
    </section>
  );
}

function ReplayPanel({
  logs,
  running,
  onRun,
  onClear,
}: {
  logs: ReplayLogItem[];
  running: boolean;
  onRun: () => Promise<void>;
  onClear: () => void;
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Mock Replay (Webhook)</h2>
        <div className="button-row">
          <button className="action-btn" disabled={running} onClick={() => void onRun()}>
            {running ? "Running..." : "Run Mock Replay"}
          </button>
          <button className="action-btn ghost" disabled={running} onClick={onClear}>
            Clear Logs
          </button>
        </div>
      </div>
      <p className="panel-subtitle">
        Sends leads from `mock.json` to webhook one by one and prints detailed live events.
      </p>
      <div className="log-box">
        {logs.length === 0 && <div className="log-line">No replay events yet.</div>}
        {logs.map((log, idx) => (
          <div key={`${log.ts}-${idx}`} className={`log-line ${log.level}`}>
            <span className="log-ts">{log.ts}</span>
            <span>{log.message}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

function App() {
  const [summary, setSummary] = useState<MetricsSummary | null>(null);
  const [points, setPoints] = useState<MetricsPoint[]>([]);
  const [recent, setRecent] = useState<RecentValidation[]>([]);
  const [days, setDays] = useState<number>(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [replayRunning, setReplayRunning] = useState(false);
  const [replayLogs, setReplayLogs] = useState<ReplayLogItem[]>([]);

  const appendReplayLog = (message: string, level: ReplayLogItem["level"] = "info") => {
    const item: ReplayLogItem = { ts: new Date().toLocaleTimeString(), message, level };
    setReplayLogs((prev) => [item, ...prev].slice(0, 120));
  };

  const loadDashboard = async (periodDays: number, keepLoadingState = true) => {
    if (keepLoadingState) {
      setLoading(true);
    }
    setError(null);
    try {
      const [summaryData, timeseriesData, recentItems] = await Promise.all([
        fetchSummary(),
        fetchTimeseries(periodDays),
        fetchRecent(20),
      ]);
      setSummary(summaryData);
      setPoints(timeseriesData);
      setRecent(recentItems);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected dashboard error.");
    } finally {
      if (keepLoadingState) {
        setLoading(false);
      }
    }
  };

  const runMockReplay = async () => {
    setReplayRunning(true);
    appendReplayLog("Loading mock leads from backend...", "info");
    try {
      const leads = await fetchMockLeads();
      appendReplayLog(`Loaded ${leads.length} leads. Starting webhook replay...`, "info");
      for (let i = 0; i < leads.length; i += 1) {
        const lead = leads[i];
        const leadId = String(lead.ID ?? `unknown-${i + 1}`);
        const rawPhone = String(lead.CONTACT_PHONE ?? "");
        appendReplayLog(`[${i + 1}/${leads.length}] Sending lead ${leadId} (${rawPhone || "empty"})`, "info");
        try {
          const result = await sendLeadToWebhook(lead);
          appendReplayLog(
            `Lead ${leadId}: ${result.status} via ${result.source}, normalized=${result.normalized_phone ?? "-"}, reason=${result.reason ?? "-"}`,
            result.status === "valid" ? "success" : "error",
          );
        } catch (err) {
          const msg = err instanceof Error ? err.message : "Unknown webhook error.";
          appendReplayLog(`Lead ${leadId}: request failed (${msg})`, "error");
        }
      }
      appendReplayLog("Replay finished. Refreshing dashboard metrics...", "info");
      await loadDashboard(days, false);
      appendReplayLog("Dashboard updated after replay.", "success");
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to run replay.";
      appendReplayLog(msg, "error");
    } finally {
      setReplayRunning(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    async function load() {
      if (!cancelled) {
        await loadDashboard(days, true);
      }
    }
    load();
    const id = setInterval(load, 10000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, [days]);

  return (
    <main className="container">
      <header className="hero">
        <div>
          <h1>Phone Validator Dashboard</h1>
          <p>Live visibility over CRM phone quality and validation outcomes.</p>
        </div>
        <section className="controls">
          <label htmlFor="days">Period</label>
          <select id="days" value={days} onChange={(event) => setDays(Number(event.target.value))}>
            <option value={7}>Last 7 days</option>
            <option value={14}>Last 14 days</option>
            <option value={30}>Last 30 days</option>
          </select>
        </section>
      </header>

      {loading && <div className="state-card">Loading metrics...</div>}
      {error && <div className="state-card error">{error}</div>}

      {summary && !loading && !error && (
        <>
          <KpiCards summary={summary} />
          <ReplayPanel logs={replayLogs} running={replayRunning} onRun={runMockReplay} onClear={() => setReplayLogs([])} />
          <TrendPanel points={points} />
          <ReasonsPanel reasons={summary.reasons} />
          <RecentPanel recent={recent} />
        </>
      )}
    </main>
  );
}

export default App;
