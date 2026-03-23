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
