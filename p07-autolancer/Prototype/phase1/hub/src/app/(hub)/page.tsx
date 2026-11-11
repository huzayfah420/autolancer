"use client";
// Jobs feed (rows 6-9): fetch, assess, ranked list with filters, markers and the detail drawer.
import Link from "next/link";
import { useCallback, useEffect, useLayoutEffect, useState } from "react";
import { Decision, Eligible, Markers } from "@/components/Badges";
import JobDrawer from "@/components/JobDrawer";
import Notice from "@/components/Notice";
import { get, post } from "@/lib/api";
import { money, usd, when } from "@/lib/format";
import type { Feed } from "@/lib/types";

type Filters = { classification: string; category: string; status: string; eligible_only: boolean; changes_only: boolean; q: string };
const NO_FILTERS: Filters = { classification: "", category: "", status: "", eligible_only: false, changes_only: false, q: "" };

type FetchResult = {
  fetch: { ok: boolean; error: string | null; attempts: number; new?: number; changed?: number; unchanged?: number; filtered_out?: number; closed?: number };
  assessment: AssessResult | null;
};
type AssessResult = { assessed: number; reused: number; unassessed: number; already_current: number };

// Filters are applied by the API; empty values are left out of the query string.
function fetchFeed(filters: Filters) {
  const params = new URLSearchParams();
  Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, String(v)); });
  return get<Feed>(`/jobs?${params}`);
}

const assessText = (a: AssessResult) =>
  `Assessed ${a.assessed}, re-ranked ${a.reused} without a new AI call, ${a.unassessed} unassessed.`;

export default function JobsPage() {
  const [feed, setFeed] = useState<Feed | null>(null);
  const [filters, setFilters] = useState<Filters>(NO_FILTERS);
  const [selected, setSelected] = useState<number | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "error" | "warn"; text: string } | null>(null);
  const [busy, setBusy] = useState<string | null>(null);

  // Reload the feed whenever the filters change (state is set in the promise callbacks).
  const load = useCallback(
    () => fetchFeed(filters).then(setFeed).catch((e) => setMsg({ kind: "error", text: (e as Error).message })),
    [filters],
  );
  useEffect(() => { load(); }, [load]);

  // The page stays mounted (hidden) after navigating away. Filters are kept, but the last
  // action's message and the open drawer are cleared so they are not shown out of date.
  useLayoutEffect(() => () => { setMsg(null); setSelected(null); }, []);

  async function fetchJobs() {
    setBusy("fetch");
    setMsg(null);
    try {
      const r = await post<FetchResult>("/jobs/fetch");
      // A failed fetch is reported by the "last fetch failed" notice, which the reloaded feed carries.
      if (r.fetch.ok) {
        const f = r.fetch;
        setMsg({
          kind: "ok",
          text: `Fetched${f.attempts > 1 ? ` (succeeded on attempt ${f.attempts})` : ""}: ${f.new} new, ${f.changed} changed, ${f.unchanged} unchanged, ${f.filtered_out} filtered out${f.closed ? `, ${f.closed} no longer listed (closed)` : ""}. ${r.assessment ? assessText(r.assessment) : ""}`,
        });
      }
    } catch (e) {
      setMsg({ kind: "error", text: (e as Error).message });
    } finally {
      setBusy(null);
      load();
    }
  }

  async function assessAll() {
    setBusy("assess");
    setMsg(null);
    try {
      setMsg({ kind: "ok", text: assessText(await post<AssessResult>("/jobs/assess")) });
    } catch (e) {
      setMsg({ kind: "error", text: (e as Error).message });
    } finally {
      setBusy(null);
      load();
    }
  }

  // Retry one unassessed job straight from the table (row 7).
  async function retry(id: number) {
    setBusy(`retry-${id}`);
    setMsg(null);
    try {
      const job = await post<{ title: string; status: string; unassessed_reason: string | null }>(`/jobs/${id}/assess`);
      setMsg(job.status === "unassessed"
        ? { kind: "warn", text: `Still unassessed: ${job.unassessed_reason}` }
        : { kind: "ok", text: `“${job.title}” assessed.` });
    } catch (e) {
      setMsg({ kind: "error", text: (e as Error).message });
    } finally {
      setBusy(null);
      load();
    }
  }

  const set = (patch: Partial<Filters>) => setFilters({ ...filters, ...patch });

  return (
    <div>
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <h1 className="text-2xl font-semibold">Jobs</h1>
        <div className="ml-auto flex gap-2">
          {!!feed?.needs_assessment && (
            <button className="btn-secondary" disabled={!!busy || !feed.policy_version} onClick={assessAll}>
              {busy === "assess" ? "Assessing…" : `Assess ${feed.needs_assessment} job${feed.needs_assessment === 1 ? "" : "s"}`}
            </button>
          )}
          <button className="btn" disabled={!!busy || !feed?.connected || !feed.policy_version}
            title={feed && !feed.connected ? "Connect the Marketplace Simulator first" : feed && !feed.policy_version ? "Save a policy first" : undefined}
            onClick={fetchJobs}>
            {busy === "fetch" ? "Fetching…" : "Fetch jobs"}
          </button>
        </div>
      </div>

      {feed && (
        <p className="mb-3 text-sm text-slate-500">
          Last updated: {when(feed.last_fetch_at)} · AI spend today: {usd(feed.ai_spent_today)} of {usd(feed.ai_daily_cap)}
          {feed.policy_version && <> · policy v{feed.policy_version}</>} · profile v{feed.profile_version}
        </p>
      )}
      {feed && !feed.connected && (feed.connection_status === "unavailable" ? (
        <Notice kind="warn">The Marketplace Simulator is unavailable, so fetching is off. <Link className="underline" href="/connections">Try the connection again</Link>.</Notice>
      ) : (
        <Notice kind="info">The Marketplace Simulator is not connected. <Link className="underline" href="/connections">Connect it</Link> to fetch jobs.</Notice>
      ))}
      {feed && !feed.policy_version && (
        <Notice kind="info">No policy yet. <Link className="underline" href="/policy">Save a policy</Link>: the job filters and AI cap come from it.</Notice>
      )}
      {feed?.last_fetch_error && (
        <Notice kind="warn">
          The last fetch ({when(feed.last_fetch_attempt_at)}) failed after {feed.last_fetch_attempts} {feed.last_fetch_attempts === 1 ? "attempt" : "attempts"}: {feed.last_fetch_error}. The previous list is kept, as of {when(feed.last_fetch_at)}.
        </Notice>
      )}
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}

      <div className="mb-4 flex flex-wrap items-end gap-3 text-sm">
        <input className="input w-48" placeholder="Search title or skill" value={filters.q} onChange={(e) => set({ q: e.target.value })} />
        <select className="input w-36" value={filters.classification} onChange={(e) => set({ classification: e.target.value })}>
          <option value="">All decisions</option>
          <option value="pursue">Pursue</option>
          <option value="clarify">Clarify</option>
          <option value="decline">Decline</option>
        </select>
        <select className="input w-36" value={filters.category} onChange={(e) => set({ category: e.target.value })}>
          <option value="">All categories</option>
          {["finance", "software", "data", "research", "writing"].map((c) => <option key={c} value={c}>{c[0].toUpperCase() + c.slice(1)}</option>)}
        </select>
        <select className="input w-40" value={filters.status} onChange={(e) => set({ status: e.target.value })}>
          <option value="">Any status</option>
          <option value="assessed">Assessed</option>
          <option value="stale">Needs re-assessment</option>
          <option value="unassessed">Unassessed</option>
          <option value="pending">Not assessed yet</option>
        </select>
        <label className="flex items-center gap-2"><input type="checkbox" checked={filters.eligible_only} onChange={(e) => set({ eligible_only: e.target.checked })} />Pursue-eligible only</label>
        <label className="flex items-center gap-2"><input type="checkbox" checked={filters.changes_only} onChange={(e) => set({ changes_only: e.target.checked })} />New or changed only</label>
        {JSON.stringify(filters) !== JSON.stringify(NO_FILTERS) && (
          <button className="text-slate-500 underline" onClick={() => setFilters(NO_FILTERS)}>Clear</button>
        )}
      </div>

      {!feed ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : feed.items.length === 0 ? (
        <p className="text-sm text-slate-500">No jobs to show. {feed.last_fetch_at ? "Try clearing the filters."
          : feed.connected && feed.policy_version ? "Press “Fetch jobs” to load listings."
          : "Fetching is off until the simulator is connected and a policy is saved."}</p>
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-slate-600">
              <tr>
                {["Score", "Job", "Category", "Budget", "Due", "Decision", ""].map((h) => <th key={h} className="px-3 py-2 font-medium">{h}</th>)}
              </tr>
            </thead>
            <tbody>
              {feed.items.map((j) => (
                <tr key={j.id} className="cursor-pointer border-t border-slate-100 hover:bg-slate-50" onClick={() => setSelected(j.id)}>
                  <td className="px-3 py-2 font-mono">{j.score?.toFixed(1) ?? "—"}</td>
                  <td className="px-3 py-2">
                    {/* A real button, so the drawer opens from the keyboard too (NFR-010). */}
                    <button type="button" className="text-left font-medium hover:underline"
                      onClick={(e) => { e.stopPropagation(); setSelected(j.id); }}>
                      {j.title}
                    </button>
                    <Markers job={j} />
                    {j.status === "unassessed" && <div className="text-xs text-red-700">{j.unassessed_reason}</div>}
                  </td>
                  <td className="px-3 py-2 capitalize">{j.category}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{money(j.budget_min, j.currency)}–{money(j.budget_max, j.currency)}</td>
                  <td className="px-3 py-2 whitespace-nowrap">{j.deadline_days} days</td>
                  <td className="px-3 py-2"><Decision job={j} /></td>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <Eligible job={j} />
                    {j.status === "unassessed" && (
                      <button className="btn-secondary px-2 py-1 text-xs" disabled={!!busy}
                        onClick={(e) => { e.stopPropagation(); retry(j.id); }}>
                        {busy === `retry-${j.id}` ? "Retrying…" : "Retry"}
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected !== null && <JobDrawer key={selected} id={selected} onClose={() => setSelected(null)} onChanged={load} />}
    </div>
  );
}
