// Thin client for the Autolancer API. Every call sends the owner's Supabase access token.
import { supabase } from "./supabase";

const API_URL = (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

// FastAPI returns either {detail: "text"} or {detail: [{loc, msg}, ...]} for validation errors.
function readableDetail(body: unknown, status: number): string {
  const detail = (body as { detail?: unknown })?.detail;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((d: { loc?: (string | number)[]; msg?: string }) => {
        const field = (d.loc ?? []).filter((p) => p !== "body").join(".");
        return field ? `${field}: ${d.msg}` : d.msg;
      })
      .join("; ");
  }
  return `Request failed (HTTP ${status})`;
}

export async function api<T>(path: string, init: RequestInit = {}): Promise<T> {
  const { data } = await supabase().auth.getSession();
  const token = data.session?.access_token;
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...init.headers,
      },
    });
  } catch {
    throw new ApiError(0, "Cannot reach the Autolancer API. Check that it is running.");
  }
  const body = await res.json().catch(() => null);
  if (res.status === 401) {
    // Session missing or expired: sign out locally; AuthGate then sends the owner to /login.
    await supabase().auth.signOut();
  }
  if (!res.ok) throw new ApiError(res.status, readableDetail(body, res.status));
  return body as T;
}

// Small helpers so pages read naturally.
export const get = <T>(path: string) => api<T>(path);
export const post = <T>(path: string, body?: unknown) =>
  api<T>(path, { method: "POST", body: body === undefined ? undefined : JSON.stringify(body) });
export const put = <T>(path: string, body: unknown) => api<T>(path, { method: "PUT", body: JSON.stringify(body) });
export const del = <T>(path: string) => api<T>(path, { method: "DELETE" });

type AssessCounts = { assessed: number; reused: number; unassessed: number; already_current: number };

// A changed profile or policy makes stored assessments stale. This re-assesses the affected
// jobs straight away (row 8, UC-002 A1/E3) and returns a sentence describing the outcome,
// or "" when there was nothing to do. Jobs left over stay marked stale on the Jobs page.
export async function reassessAffected(): Promise<string> {
  try {
    const r = await post<AssessCounts>("/jobs/assess");
    const parts = [];
    if (r.assessed) parts.push(`${r.assessed} re-assessed by the AI`);
    if (r.reused) parts.push(`${r.reused} re-ranked without a new AI call`);
    if (r.unassessed) parts.push(`${r.unassessed} could not be assessed (see the Jobs page)`);
    return parts.length ? ` Affected jobs: ${parts.join(", ")}.` : "";
  } catch (e) {
    // 409 = no policy saved yet, so nothing can be assessed and nothing is stale.
    if (e instanceof ApiError && e.status === 409) return "";
    return " Affected jobs could not be re-assessed now; use “Assess” on the Jobs page.";
  }
}
