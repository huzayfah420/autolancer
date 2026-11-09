// Shapes returned by the API (see api/app/routers and api/app/services/feed.py).

export type Options = {
  services: string[];
  allowed_actions: Record<string, string>;
  review_conditions: Record<string, string>;
};

export type Connection = {
  provider: string;
  enabled: boolean;
  status: "connected" | "unavailable" | "disconnected";
  account_name: string | null;
  operations: string[];
  status_detail: string | null;
  checked_at: string | null;
};

export type Evidence = { kind: "link" | "text"; title: string; content: string };

export type Profile = {
  version: number;
  services: string[];
  skills_summary: string;
  evidence: Evidence[];
  pending_draft: string | null;
  pending_unsupported_claims: string[] | null;
  updated_at: string;
};

export type PolicyFields = {
  allowed_actions: string[];
  max_bid: number;
  daily_proposal_limit: number;
  workload_limit: number;
  daily_ai_cap_usd: number;
  review_conditions: string[];
  min_job_budget: number;
  excluded_keywords: string[];
};

export type Policy = PolicyFields & { version: number; created_at: string };

export type JobStatus = "assessed" | "stale" | "unassessed" | "pending";
export type Classification = "pursue" | "clarify" | "decline";

export type JobItem = {
  id: number;
  source_id: string;
  title: string;
  category: string;
  budget_min: number;
  budget_max: number;
  currency: string;
  deadline_days: number;
  skills: string[];
  url: string;
  simulated: boolean;
  version: number;
  is_new: boolean;
  is_changed: boolean;
  status: JobStatus;
  unassessed_reason: string | null;
  classification: Classification | null;
  score: number | null;
  fit: number | null;
  uncertainty: "low" | "medium" | "high" | null;
  pursue_eligible: boolean;
  rule_reasons: string[];
};

export type Feed = {
  items: JobItem[];
  needs_assessment: number;
  last_fetch_at: string | null;
  last_fetch_attempt_at: string | null;
  last_fetch_error: string | null;
  connected: boolean;
  policy_version: number | null;
  profile_version: number;
  ai_spent_today: number;
  ai_daily_cap: number;
};

export type AIOutput = {
  category: string;
  fit: number;
  fit_reasons: string[];
  deliverables: string[];
  effort_hours_min: number;
  effort_hours_max: number;
  price_min: number;
  price_max: number;
  uncertainty: "low" | "medium" | "high";
  open_questions: string[];
};

type Versions = { listing: number; profile: number; policy: number | null };

export type JobDetail = JobItem & {
  description: string;
  client: { name?: string; country?: string; rating?: number };
  posted_at: string;
  ai_output: AIOutput | null;
  score_breakdown: { parts: Record<string, number>; weights: Record<string, number>; total: number } | null;
  reused_ai_output: boolean;
  assessed_with: Versions | null;
  current_versions: Versions;
  history: {
    id: number;
    created_at: string;
    status: string;
    classification: string | null;
    score: number | null;
    unassessed_reason: string | null;
    versions: Versions;
  }[];
};
