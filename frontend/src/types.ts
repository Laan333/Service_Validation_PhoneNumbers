export type MetricsSummary = {
  total: number;
  valid: number;
  invalid: number;
  success_rate: number;
  reasons: Record<string, number>;
};

export type MetricsPoint = {
  bucket: string;
  total: number;
  valid: number;
  invalid: number;
};

export type RecentValidation = {
  lead_id: string;
  contact_phone_raw: string;
  normalized_phone: string | null;
  status: string;
  reason: string | null;
  source: string;
  processed_at: string;
};

export type CrmMockLead = {
  ID: string;
  TITLE?: string;
  CONTACT_PHONE?: string;
  DATE_CREATE?: string;
  [key: string]: unknown;
};

export type ReplayLogItem = {
  ts: string;
  message: string;
  level: "info" | "success" | "error";
};
