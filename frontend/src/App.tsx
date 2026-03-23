import { type CSSProperties, useEffect, useMemo, useState } from "react";

import {
  deleteAllRecent,
  deleteRecentById,
  fetchMockLeads,
  fetchRecent,
  fetchSummary,
  fetchTimeseries,
  fetchAdvanced,
  sendLeadToWebhook,
} from "./api";
import type { AdvancedMetrics, CrmMockLead, MetricsPoint, MetricsSummary, RecentValidation, ReplayLogItem } from "./types";

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

function AdvancedPanel({ advanced }: { advanced: AdvancedMetrics }) {
  const pct = (value: number) => `${(value * 100).toFixed(1)}%`;
  return (
    <section className="panel">
      <h2>Advanced Analytics</h2>
      <div className="advanced-grid">
        <article className="mini-card">
          <span>LLM Share</span>
          <strong>{pct(advanced.llm_share)}</strong>
        </article>
        <article className="mini-card">
          <span>LLM Success</span>
          <strong>{pct(advanced.llm_success_rate)}</strong>
        </article>
        <article className="mini-card">
          <span>Deterministic Success</span>
          <strong>{pct(advanced.deterministic_success_rate)}</strong>
        </article>
        <article className="mini-card">
          <span>Normalization Coverage</span>
          <strong>{pct(advanced.normalization_coverage)}</strong>
        </article>
        <article className="mini-card">
          <span>Invalid Share</span>
          <strong>{pct(advanced.invalid_share)}</strong>
        </article>
      </div>
      <div className="advanced-split">
        <div>
          <h4>Source Split</h4>
          <ul className="reason-list">
            {Object.entries(advanced.source_split).map(([source, count]) => (
              <li key={source}>
                <span>{source}</span>
                <strong>{count}</strong>
              </li>
            ))}
          </ul>
        </div>
        <div>
          <h4>Top Rejection Reasons</h4>
          <ul className="reason-list">
            {advanced.top_reasons.map((item) => (
              <li key={item.reason}>
                <span>{item.reason}</span>
                <strong>{item.count}</strong>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function RecentPanel({
  recent,
  mockLeads,
  onDeleteOne,
  onDeleteAll,
}: {
  recent: RecentValidation[];
  mockLeads: CrmMockLead[];
  onDeleteOne: (id: number) => Promise<void>;
  onDeleteAll: () => Promise<void>;
}) {
  const [query, setQuery] = useState("");
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(10);
  const [selectedRecord, setSelectedRecord] = useState<RecentValidation | null>(null);
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

  const selectedMock = useMemo(() => {
    if (!selectedRecord) {
      return null;
    }
    return mockLeads.find((lead) => String(lead.ID) === selectedRecord.lead_id) ?? null;
  }, [mockLeads, selectedRecord]);

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
          <button className="action-btn danger" disabled={filtered.length === 0} onClick={() => void onDeleteAll()}>
            Delete all
          </button>
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
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {paged.map((item) => (
              <tr
                key={`${item.lead_id}-${item.processed_at}`}
                className="clickable-row"
                onClick={() => setSelectedRecord(item)}
                title="Click to view details"
              >
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
                <td>
                  <button
                    className="action-btn ghost compact danger"
                    onClick={(event) => {
                      event.stopPropagation();
                      void onDeleteOne(item.id);
                    }}
                  >
                    Delete
                  </button>
                </td>
              </tr>
            ))}
            {paged.length === 0 && (
              <tr>
                <td colSpan={8} className="empty-table">
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
      {selectedRecord && (
        <div className="modal-backdrop" onClick={() => setSelectedRecord(null)}>
          <div className="modal-card" onClick={(event) => event.stopPropagation()}>
            <div className="modal-header">
              <h3>Lead {selectedRecord.lead_id}</h3>
              <button className="close-btn" onClick={() => setSelectedRecord(null)} aria-label="Close details">
                ×
              </button>
            </div>
            <div className="modal-grid">
              <div>
                <span className="meta-label">Raw phone</span>
                <p>{selectedRecord.contact_phone_raw || "-"}</p>
              </div>
              <div>
                <span className="meta-label">Normalized</span>
                <p>{selectedRecord.normalized_phone ?? "-"}</p>
              </div>
              <div>
                <span className="meta-label">Status</span>
                <p>
                  <StatusPill status={selectedRecord.status} />
                </p>
              </div>
              <div>
                <span className="meta-label">Reason</span>
                <p>{prettifyReason(selectedRecord.reason)}</p>
              </div>
              <div>
                <span className="meta-label">Source</span>
                <p>{selectedRecord.source}</p>
              </div>
              <div>
                <span className="meta-label">Processed at</span>
                <p>{formatDate(selectedRecord.processed_at)}</p>
              </div>
            </div>
            <div className="mock-details">
              <h4>Mock payload</h4>
              {selectedMock ? (
                <div className="payload-list">
                  {Object.entries(selectedMock).map(([key, value]) => (
                    <div key={key} className="payload-item">
                      <span>{key}</span>
                      <strong>{String(value ?? "-")}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <p className="muted-text">No matching object found in loaded mock.json for this lead id.</p>
              )}
            </div>
          </div>
        </div>
      )}
    </section>
  );
}

function ReplayPanel({
  mockCount,
  logs,
  running,
  onRun,
  onClear,
  onReloadMock,
}: {
  mockCount: number;
  logs: ReplayLogItem[];
  running: boolean;
  onRun: () => Promise<void>;
  onClear: () => void;
  onReloadMock: () => Promise<void>;
}) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Mock Replay (Webhook)</h2>
        <div className="button-row">
          <button className="action-btn ghost" disabled={running} onClick={() => void onReloadMock()}>
            Reload mock.json
          </button>
          <button className="action-btn" disabled={running} onClick={() => void onRun()}>
            {running ? "Running..." : "Run Mock Replay"}
          </button>
          <button className="action-btn ghost" disabled={running} onClick={onClear}>
            Clear Logs
          </button>
        </div>
      </div>
      <p className="panel-subtitle">
        Sends leads from `mock.json` to webhook one by one and prints detailed live events. Loaded leads: {mockCount}.
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
  const [advanced, setAdvanced] = useState<AdvancedMetrics | null>(null);
  const [days, setDays] = useState<number>(7);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [replayRunning, setReplayRunning] = useState(false);
  const [replayLogs, setReplayLogs] = useState<ReplayLogItem[]>([]);
  const [mockLeads, setMockLeads] = useState<CrmMockLead[]>([]);

  const appendReplayLog = (message: string, level: ReplayLogItem["level"] = "info") => {
    const item: ReplayLogItem = { ts: new Date().toLocaleTimeString(), message, level };
    setReplayLogs((prev) => [item, ...prev].slice(0, 120));
  };

  const loadMockLeads = async () => {
    const { items, sourcePath } = await fetchMockLeads();
    setMockLeads(items);
    appendReplayLog(`Loaded ${items.length} leads from ${sourcePath}`, "info");
    return items;
  };

  const loadDashboard = async (periodDays: number, keepLoadingState = true) => {
    if (keepLoadingState) {
      setLoading(true);
      setRefreshing(false);
    } else {
      setRefreshing(true);
    }
    try {
      const [summaryData, timeseriesData, recentItems, advancedData] = await Promise.all([
        fetchSummary(),
        fetchTimeseries(periodDays),
        fetchRecent(20),
        fetchAdvanced(),
      ]);
      setSummary(summaryData);
      setPoints(timeseriesData);
      setRecent(recentItems);
      setAdvanced(advancedData);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unexpected dashboard error.");
    } finally {
      if (keepLoadingState) {
        setLoading(false);
      } else {
        setRefreshing(false);
      }
    }
  };

  const runMockReplay = async () => {
    setReplayRunning(true);
    appendReplayLog("Preparing leads from mock.json...", "info");
    try {
      const leads = mockLeads.length > 0 ? mockLeads : await loadMockLeads();
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

  const handleDeleteOne = async (recordId: number) => {
    try {
      await deleteRecentById(recordId);
      appendReplayLog(`Deleted record #${recordId}.`, "success");
      await loadDashboard(days, false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to delete record.";
      appendReplayLog(msg, "error");
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm("Delete all processed records? This cannot be undone.")) {
      return;
    }
    try {
      const deleted = await deleteAllRecent();
      appendReplayLog(`Deleted ${deleted} records.`, "success");
      await loadDashboard(days, false);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Failed to delete all records.";
      appendReplayLog(msg, "error");
    }
  };

  useEffect(() => {
    let cancelled = false;
    let firstLoadDone = false;
    async function load() {
      if (!cancelled) {
        await loadDashboard(days, !firstLoadDone);
        if (!firstLoadDone) {
          try {
            await loadMockLeads();
          } catch (err) {
            const msg = err instanceof Error ? err.message : "Failed to preload mock.json.";
            appendReplayLog(msg, "error");
          }
        }
        firstLoadDone = true;
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
          {refreshing && <span className="live-indicator">Updating data...</span>}
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
          {advanced && <AdvancedPanel advanced={advanced} />}
          <ReplayPanel
            mockCount={mockLeads.length}
            logs={replayLogs}
            running={replayRunning}
            onRun={runMockReplay}
            onClear={() => setReplayLogs([])}
            onReloadMock={async () => {
              try {
                await loadMockLeads();
              } catch (err) {
                const msg = err instanceof Error ? err.message : "Failed to reload mock.json.";
                appendReplayLog(msg, "error");
              }
            }}
          />
          <TrendPanel points={points} />
          <ReasonsPanel reasons={summary.reasons} />
          <RecentPanel recent={recent} mockLeads={mockLeads} onDeleteOne={handleDeleteOne} onDeleteAll={handleDeleteAll} />
        </>
      )}
    </main>
  );
}

export default App;
