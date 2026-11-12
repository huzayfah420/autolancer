"use client";
// Policy page (row 5): each valid save creates a new version; the API rejects invalid values.
import { useEffect, useState } from "react";
import Notice from "@/components/Notice";
import { get, post } from "@/lib/api";
import { money, usd, when } from "@/lib/format";
import type { Options, Policy, PolicyFields } from "@/lib/types";

const DEFAULTS: PolicyFields = {
  allowed_actions: ["discover_jobs", "assess_jobs"],
  max_bid: 1500,
  daily_proposal_limit: 3,
  workload_limit: 2,
  daily_ai_cap_usd: 0.5,
  review_conditions: ["high_uncertainty"],
  min_job_budget: 200,
  excluded_keywords: [],
  min_deadline_days: 0,
};

// Numeric inputs: label, field and the HTML hints (the API is still the real validator).
const NUMBERS: { field: keyof PolicyFields; label: string; step: string }[] = [
  { field: "max_bid", label: "Maximum bid (USD)", step: "1" },
  { field: "min_job_budget", label: "Minimum job budget (USD)", step: "1" },
  { field: "daily_proposal_limit", label: "Daily proposal limit", step: "1" },
  { field: "workload_limit", label: "Workload limit (active projects)", step: "1" },
  { field: "daily_ai_cap_usd", label: "Daily AI spending cap (USD)", step: "any" },
  { field: "min_deadline_days", label: "Minimum days to deadline (0 = no limit)", step: "1" },
];

type History = { active: Policy | null; history: Policy[] };

export default function PolicyPage() {
  const [options, setOptions] = useState<Options | null>(null);
  const [data, setData] = useState<History | null>(null);
  const [form, setForm] = useState<PolicyFields>(DEFAULTS);
  const [keywords, setKeywords] = useState("");
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  // Show the history and pre-fill the form with the active version (or defaults).
  function apply(d: History) {
    setData(d);
    // Copy only the editable fields: the API rejects unknown keys such as version/created_at.
    const base = d.active ?? DEFAULTS;
    setForm(Object.fromEntries(Object.keys(DEFAULTS).map((k) => [k, base[k as keyof PolicyFields]])) as PolicyFields);
    setKeywords(base.excluded_keywords.join(", "));
  }

  useEffect(() => {
    get<Options>("/options").then(setOptions);
    get<History>("/policy").then(apply).catch((e) => setMsg({ kind: "error", text: e.message }));
  }, []);

  async function save(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setMsg(null);
    try {
      const body = { ...form, excluded_keywords: keywords.split(",").map((k) => k.trim()).filter(Boolean) };
      const saved = await post<Policy>("/policy", body);
      apply(await get<History>("/policy"));
      setMsg({ kind: "ok", text: `Saved as version ${saved.version}. Affected jobs are queued for re-assessment.` });
    } catch (err) {
      // E3: the previous version stays active; show why this one was rejected.
      setMsg({ kind: "error", text: `Not saved. ${(err as Error).message}` });
    } finally {
      setBusy(false);
    }
  }

  const toggle = (field: "allowed_actions" | "review_conditions", key: string, on: boolean) =>
    setForm({ ...form, [field]: on ? [...form[field], key] : form[field].filter((x) => x !== key) });

  if (!options || !data) return <p className="text-sm text-slate-500">Loading…</p>;

  return (
    <div className="max-w-3xl">
      <div className="mb-4 flex items-baseline gap-3">
        <h1 className="text-2xl font-semibold">Autonomy policy</h1>
        <span className="text-sm text-slate-500">
          {data.active ? `active version ${data.active.version}` : "no policy saved yet"}
        </span>
      </div>
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}

      <form className="card space-y-5" onSubmit={save}>
        <fieldset>
          <legend className="label">Allowed actions</legend>
          {Object.entries(options.allowed_actions).map(([key, text]) => (
            <label key={key} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.allowed_actions.includes(key)}
                onChange={(e) => toggle("allowed_actions", key, e.target.checked)} />
              {text}
            </label>
          ))}
        </fieldset>

        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {NUMBERS.map(({ field, label, step }) => (
            <div key={field}>
              <label className="label" htmlFor={field}>{label}</label>
              <input id={field} type="number" step={step} required className="input"
                value={form[field] as number}
                onChange={(e) => setForm({ ...form, [field]: e.target.value === "" ? "" : Number(e.target.value) })} />
            </div>
          ))}
        </div>

        <fieldset>
          <legend className="label">Review conditions (hold the job for you)</legend>
          {Object.entries(options.review_conditions).map(([key, text]) => (
            <label key={key} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={form.review_conditions.includes(key)}
                onChange={(e) => toggle("review_conditions", key, e.target.checked)} />
              {text}
            </label>
          ))}
        </fieldset>

        <div>
          <label className="label" htmlFor="kw">Excluded keywords (comma-separated)</label>
          <input id="kw" className="input" placeholder="crypto, gambling" value={keywords}
            onChange={(e) => setKeywords(e.target.value)} />
        </div>

        <button className="btn" disabled={busy}>{busy ? "Saving…" : "Save as new version"}</button>
      </form>

      <h2 className="mb-2 mt-8 text-lg font-medium">Version history</h2>
      {data.history.length === 0 ? (
        <p className="text-sm text-slate-500">No versions yet.</p>
      ) : (
        <div className="card overflow-x-auto p-0">
          <table className="w-full text-left text-sm">
            <thead className="bg-slate-100 text-slate-600">
              <tr>
                {["Version", "Saved", "Max bid", "Min budget", "Proposals/day", "Workload", "AI cap", "Min days", "Actions", "Review", "Excluded"].map((h) => (
                  <th key={h} className="px-3 py-2 font-medium">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.history.map((p, i) => (
                <tr key={p.version} className="border-t border-slate-100 align-top">
                  <td className="px-3 py-2">
                    v{p.version} {i === 0 && <span className="badge bg-emerald-100 text-emerald-800">active</span>}
                  </td>
                  <td className="px-3 py-2 whitespace-nowrap">{when(p.created_at)}</td>
                  <td className="px-3 py-2">{money(p.max_bid)}</td>
                  <td className="px-3 py-2">{money(p.min_job_budget)}</td>
                  <td className="px-3 py-2">{p.daily_proposal_limit}</td>
                  <td className="px-3 py-2">{p.workload_limit}</td>
                  <td className="px-3 py-2">{usd(p.daily_ai_cap_usd)}</td>
                  <td className="px-3 py-2">{p.min_deadline_days || "none"}</td>
                  <td className="px-3 py-2">{p.allowed_actions.join(", ") || "none"}</td>
                  <td className="px-3 py-2">{p.review_conditions.join(", ") || "none"}</td>
                  <td className="px-3 py-2">{p.excluded_keywords.join(", ") || "none"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
