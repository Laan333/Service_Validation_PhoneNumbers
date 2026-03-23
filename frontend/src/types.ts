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
  id: number;
  lead_id: string;
  contact_phone_raw: string;
  normalized_phone: string | null;
  status: string;
  reason: string | null;
  source: string;
  processed_at: string;
  client_ip?: string | null;
  ip_country?: string | null;
  assumed_dial_cc?: string | null;
  geo_mismatch?: boolean;
  validation_confidence?: string;
  default_cc_applied?: boolean;
};

/** Same fields as ``mock.json`` / Bitrix-style webhook body. */
export type CrmMockLead = {
  ID: string;
  TITLE?: string;
  STAGE_ID?: string;
  CURRENCY_ID?: string;
  CONTACT_ID?: string;
  CONTACT_NAME?: string;
  CONTACT_EMAIL?: string;
  CONTACT_PHONE?: string;
  SOURCE_ID?: string;
  COMMENTS?: string;
  UTM_SOURCE?: string;
  UTM_MEDIUM?: string;
  UTM_CAMPAIGN?: string;
  UTM_CONTENT?: string;
  DATE_CREATE?: string;
  VISITOR_IP?: string;
};

export type ReplayLogItem = {
  ts: string;
  message: string;
  level: "info" | "success" | "error";
};

export type AdvancedMetrics = {
  llm_share: number;
  llm_success_rate: number;
  deterministic_success_rate: number;
  normalization_coverage: number;
  invalid_share: number;
  top_reasons: Array<{ reason: string; count: number }>;
  source_split: Record<string, number>;
};

export type MismatchByCcItem = {
  assumed_dial_cc: string;
  count: number;
};

export type LlmTimeseriesPoint = {
  bucket: string;
  llm: number;
  deterministic: number;
};

export type InvalidReasonCountItem = {
  reason: string;
  count: number;
};

export type RecentListFilters = {
  geoMismatchOnly: boolean;
  confidence: "all" | "deterministic" | "llm";
  status: "all" | "valid" | "invalid";
};
