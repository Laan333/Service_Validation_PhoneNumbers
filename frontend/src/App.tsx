import { type CSSProperties, useEffect, useMemo, useState } from "react";

import { fetchRecent, fetchSummary, fetchTimeseries } from "./api";
import type { MetricsPoint, MetricsSummary, RecentValidation } from "./types";

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
  const filtered = useMemo(
    () =>
      recent.filter((item) =>
        `${item.lead_id} ${item.contact_phone_raw} ${item.normalized_phone ?? ""} ${item.reason ?? ""}`
          .toLowerCase()
          .includes(query.toLowerCase()),
      ),
    [query, recent],
  );
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Latest Processed Leads</h2>
        <input
          className="search-input"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search by lead or phone..."
        />
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
            {filtered.map((item) => (
              <tr key={`${item.lead_id}-${item.processed_at}`}>
                <td>{item.lead_id}</td>
                <td>{item.contact_phone_raw || "-"}</td>
                <td>{item.normalized_phone ?? "-"}</td>
                <td>
                  <StatusPill status={item.status} />
                </td>
                <td>{item.reason ?? "-"}</td>
                <td>
                  <span className="source-chip">{item.source}</span>
                </td>
                <td>{new Date(item.processed_at).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
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

  useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [summaryData, timeseriesData, recentItems] = await Promise.all([
          fetchSummary(),
          fetchTimeseries(days),
          fetchRecent(20),
        ]);
        if (!cancelled) {
          setSummary(summaryData);
          setPoints(timeseriesData);
          setRecent(recentItems);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Unexpected dashboard error.");
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
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
          <TrendPanel points={points} />
          <ReasonsPanel reasons={summary.reasons} />
          <RecentPanel recent={recent} />
        </>
      )}
    </main>
  );
}

export default App;
