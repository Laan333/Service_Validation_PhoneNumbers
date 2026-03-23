import type {
  AdvancedMetrics,
  CrmMockLead,
  InvalidReasonCountItem,
  LlmTimeseriesPoint,
  MetricsPoint,
  MetricsSummary,
  MismatchByCcItem,
  RecentListFilters,
  RecentValidation,
} from "./types";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "";

export async function fetchSummary(): Promise<MetricsSummary> {
  const response = await fetch(`${apiBase}/api/v1/metrics/summary`);
  if (!response.ok) {
    throw new Error("Failed to load summary metrics.");
  }
  return (await response.json()) as MetricsSummary;
}

export async function fetchTimeseries(days = 7): Promise<MetricsPoint[]> {
  const response = await fetch(`${apiBase}/api/v1/metrics/timeseries?days=${days}`);
  if (!response.ok) {
    throw new Error("Failed to load timeseries metrics.");
  }
  const data = (await response.json()) as { points: MetricsPoint[] };
  return data.points;
}

export async function fetchRecent(limit = 20, filters?: RecentListFilters): Promise<RecentValidation[]> {
  const params = new URLSearchParams();
  params.set("limit", String(limit));
  if (filters?.geoMismatchOnly) {
    params.set("geo_mismatch_only", "true");
  }
  if (filters && filters.confidence !== "all") {
    params.set("confidence", filters.confidence);
  }
  if (filters && filters.status !== "all") {
    params.set("status", filters.status);
  }
  const response = await fetch(`${apiBase}/api/v1/metrics/recent?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Failed to load recent validations.");
  }
  const data = (await response.json()) as { items: RecentValidation[] };
  return data.items;
}

export async function fetchMismatchByCc(limit = 24, days?: number): Promise<MismatchByCcItem[]> {
  const params = new URLSearchParams({ limit: String(limit) });
  if (days != null) {
    params.set("days", String(days));
  }
  const response = await fetch(`${apiBase}/api/v1/metrics/chart/mismatch-by-cc?${params.toString()}`);
  if (!response.ok) {
    throw new Error("Failed to load mismatch-by-CC chart.");
  }
  const data = (await response.json()) as { items: MismatchByCcItem[] };
  return data.items;
}

export async function fetchLlmTimeseries(days = 7): Promise<LlmTimeseriesPoint[]> {
  const response = await fetch(`${apiBase}/api/v1/metrics/chart/llm-timeseries?days=${days}`);
  if (!response.ok) {
    throw new Error("Failed to load LLM timeseries.");
  }
  const data = (await response.json()) as { points: LlmTimeseriesPoint[] };
  return data.points;
}

export async function fetchInvalidReasonsChart(days?: number): Promise<InvalidReasonCountItem[]> {
  const qs = days != null ? `?days=${days}` : "";
  const response = await fetch(`${apiBase}/api/v1/metrics/chart/invalid-reasons${qs}`);
  if (!response.ok) {
    throw new Error("Failed to load invalid reasons chart.");
  }
  const data = (await response.json()) as { items: InvalidReasonCountItem[] };
  return data.items;
}

export async function fetchAdvanced(): Promise<AdvancedMetrics> {
  const response = await fetch(`${apiBase}/api/v1/metrics/advanced`);
  if (!response.ok) {
    throw new Error("Failed to load advanced analytics.");
  }
  return (await response.json()) as AdvancedMetrics;
}

export async function deleteRecentById(recordId: number): Promise<number> {
  const response = await fetch(`${apiBase}/api/v1/metrics/recent/${recordId}`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error(`Failed to delete record ${recordId}.`);
  }
  const data = (await response.json()) as { deleted: number };
  return data.deleted;
}

export async function deleteAllRecent(): Promise<number> {
  const response = await fetch(`${apiBase}/api/v1/metrics/recent`, { method: "DELETE" });
  if (!response.ok) {
    throw new Error("Failed to delete all records.");
  }
  const data = (await response.json()) as { deleted: number };
  return data.deleted;
}

export async function fetchMockLeads(): Promise<{ items: CrmMockLead[]; sourcePath: string }> {
  const response = await fetch(`${apiBase}/api/v1/dev/mock-leads`);
  if (!response.ok) {
    throw new Error("Failed to load mock leads.");
  }
  const data = (await response.json()) as { items: CrmMockLead[]; source_path: string };
  return { items: data.items, sourcePath: data.source_path };
}

export async function sendLeadToWebhook(payload: CrmMockLead): Promise<{
  lead_id: string;
  status: string;
  normalized_phone: string | null;
  reason: string | null;
  source: string;
}> {
  const response = await fetch(`${apiBase}/api/v1/webhooks/crm/lead`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`Webhook failed with status ${response.status}.`);
  }
  return (await response.json()) as {
    lead_id: string;
    status: string;
    normalized_phone: string | null;
    reason: string | null;
    source: string;
  };
}
