"use client";
// Profile page (rows 3-4): services, skills summary, evidence, and "Draft my profile".
import { useEffect, useState } from "react";
import Notice from "@/components/Notice";
import { ApiError, del, get, post, put } from "@/lib/api";
import type { Evidence, Options, Profile } from "@/lib/types";

type Form = Pick<Profile, "services" | "skills_summary" | "evidence">;

// "E2" -> "E2: <title of the 2nd saved evidence item>".
function evidenceLabel(profile: Profile, id: string) {
  const item = profile.evidence[Number(id.slice(1)) - 1];
  return item ? `${id}: ${item.title}` : id;
}

export default function ProfilePage() {
  const [options, setOptions] = useState<Options | null>(null);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [form, setForm] = useState<Form | null>(null);
  const [msg, setMsg] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const [busy, setBusy] = useState(false);

  // Keep the saved profile and the editable form separate so we know when there are unsaved edits.
  function load(p: Profile) {
    setProfile(p);
    setForm({ services: p.services, skills_summary: p.skills_summary, evidence: p.evidence });
  }

  useEffect(() => {
    get<Options>("/options").then(setOptions);
    get<Profile>("/profile").then(load).catch((e) => setMsg({ kind: "error", text: e.message }));
  }, []);

  const dirty =
    !!profile && !!form &&
    JSON.stringify(form) !== JSON.stringify({ services: profile.services, skills_summary: profile.skills_summary, evidence: profile.evidence });

  // Runs an API action, shows its outcome and reloads the profile it returns.
  async function run(action: () => Promise<Profile>, okText: string) {
    setBusy(true);
    setMsg(null);
    try {
      load(await action());
      setMsg({ kind: "ok", text: okText });
    } catch (e) {
      setMsg({ kind: "error", text: e instanceof ApiError ? e.message : "Something went wrong." });
    } finally {
      setBusy(false);
    }
  }

  if (!form || !options || !profile) return <p className="text-sm text-slate-500">Loading…</p>;

  const setEvidence = (i: number, patch: Partial<Evidence>) =>
    setForm({ ...form, evidence: form.evidence.map((e, j) => (j === i ? { ...e, ...patch } : e)) });

  return (
    <div className="max-w-3xl">
      <div className="mb-4 flex items-baseline gap-3">
        <h1 className="text-2xl font-semibold">Profile</h1>
        <span className="text-sm text-slate-500">version {profile.version}</span>
      </div>
      {msg && <Notice kind={msg.kind}>{msg.text}</Notice>}

      <form className="card space-y-5"
        onSubmit={(e) => { e.preventDefault(); run(() => put<Profile>("/profile", form), "Profile saved."); }}>
        <div>
          <span className="label">Services you offer</span>
          <div className="flex flex-wrap gap-4">
            {options.services.map((s) => (
              <label key={s} className="flex items-center gap-2 text-sm capitalize">
                <input type="checkbox" checked={form.services.includes(s)}
                  onChange={(e) => setForm({
                    ...form,
                    services: e.target.checked ? [...form.services, s] : form.services.filter((x) => x !== s),
                  })} />
                {s}
              </label>
            ))}
          </div>
        </div>

        <div>
          <label className="label" htmlFor="summary">Skills summary</label>
          <textarea id="summary" rows={4} maxLength={3000} className="input"
            value={form.skills_summary} onChange={(e) => setForm({ ...form, skills_summary: e.target.value })} />
        </div>

        <div>
          <span className="label">Evidence of past work (links or text samples)</span>
          <div className="space-y-3">
            {form.evidence.map((ev, i) => (
              <div key={i} className="rounded-md border border-slate-200 p-3">
                <div className="mb-2 flex gap-2">
                  <select className="input w-28" value={ev.kind}
                    onChange={(e) => setEvidence(i, { kind: e.target.value as Evidence["kind"] })}>
                    <option value="link">Link</option>
                    <option value="text">Text</option>
                  </select>
                  <input className="input" placeholder="Title, e.g. Cash-flow model for a retailer" required
                    value={ev.title} onChange={(e) => setEvidence(i, { title: e.target.value })} />
                  <button type="button" className="btn-secondary"
                    onClick={() => setForm({ ...form, evidence: form.evidence.filter((_, j) => j !== i) })}>
                    Remove
                  </button>
                </div>
                {ev.kind === "link" ? (
                  <input className="input" type="url" placeholder="https://…" required
                    value={ev.content} onChange={(e) => setEvidence(i, { content: e.target.value })} />
                ) : (
                  <textarea className="input" rows={3} placeholder="Paste a short sample of the work" required
                    value={ev.content} onChange={(e) => setEvidence(i, { content: e.target.value })} />
                )}
              </div>
            ))}
          </div>
          <button type="button" className="btn-secondary mt-3"
            onClick={() => setForm({ ...form, evidence: [...form.evidence, { kind: "link", title: "", content: "" }] })}>
            Add evidence
          </button>
        </div>

        <div className="flex gap-3">
          <button className="btn" disabled={busy || !dirty}>Save profile</button>
          <button type="button" className="btn-secondary" disabled={busy || dirty || !profile.services.length}
            title={dirty ? "Save your changes first" : undefined}
            onClick={() => run(() => post<Profile>("/profile/draft"), "Draft ready. Review it below.")}>
            {busy ? "Working…" : "Draft my profile"}
          </button>
          {dirty && <span className="self-center text-sm text-amber-700">Unsaved changes</span>}
        </div>
      </form>

      {profile.pending_draft && (
        <div className="card mt-6">
          <h2 className="mb-2 text-lg font-medium">AI draft</h2>
          <p className="whitespace-pre-wrap text-sm">{profile.pending_draft}</p>
          {!!profile.pending_claims?.length && (
            <div className="mt-4">
              <p className="mb-1 text-sm font-medium">Claims and the evidence behind them</p>
              <ul className="ml-5 list-disc text-sm">
                {profile.pending_claims.map((c) => (
                  <li key={c.text}>
                    {c.text}
                    <span className="text-slate-500">
                      {" "}— {c.evidence_ids.map((id) => evidenceLabel(profile, id)).join("; ")}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          )}
          {!!profile.pending_unsupported_claims?.length && (
            <div className="mt-4">
              <Notice kind="warn">
                <p className="font-medium">Claims without evidence (left out of the draft):</p>
                <ul className="ml-5 list-disc">
                  {profile.pending_unsupported_claims.map((c) => <li key={c}>{c}</li>)}
                </ul>
              </Notice>
            </div>
          )}
          <div className="mt-4 flex gap-3">
            <button className="btn" disabled={busy}
              onClick={() => run(() => post<Profile>("/profile/draft/accept"), "Draft accepted as your skills summary.")}>
              Accept draft
            </button>
            <button className="btn-secondary" disabled={busy}
              onClick={() => run(() => del<Profile>("/profile/draft"), "Draft ignored. Your profile is unchanged.")}>
              Ignore
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
