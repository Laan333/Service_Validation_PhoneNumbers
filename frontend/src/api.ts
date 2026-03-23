import type { CrmMockLead, MetricsPoint, MetricsSummary, RecentValidation } from "./types";

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

export async function fetchRecent(limit = 20): Promise<RecentValidation[]> {
  const response = await fetch(`${apiBase}/api/v1/metrics/recent?limit=${limit}`);
  if (!response.ok) {
    throw new Error("Failed to load recent validations.");
  }
  const data = (await response.json()) as { items: RecentValidation[] };
  return data.items;
}

export async function fetchMockLeads(): Promise<CrmMockLead[]> {
  const response = await fetch(`${apiBase}/api/v1/dev/mock-leads`);
  if (!response.ok) {
    throw new Error("Failed to load mock leads.");
  }
  const data = (await response.json()) as { items: CrmMockLead[] };
  return data.items;
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
