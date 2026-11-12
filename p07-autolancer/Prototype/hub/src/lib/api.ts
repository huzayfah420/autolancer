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
