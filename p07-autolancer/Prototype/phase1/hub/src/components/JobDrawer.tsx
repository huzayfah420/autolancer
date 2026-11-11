"use client";
// Side drawer for one job: the AI's reasons, the rule decision, score breakdown and versions.
import { useEffect, useState } from "react";
import Notice from "@/components/Notice";
import { Decision, Eligible, Markers } from "@/components/Badges";
import { get, post } from "@/lib/api";
import { money, when } from "@/lib/format";
import type { JobDetail } from "@/lib/types";

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="mt-5">
      <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</h3>
      {children}
    </section>
  );
}

export default function JobDrawer({ id, onClose, onChanged }: { id: number; onClose: () => void; onChanged: () => void }) {
  const [job, setJob] = useState<JobDetail | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // The parent keys this component by id, so a new job always starts from an empty state.
  useEffect(() => {
    get<JobDetail>(`/jobs/${id}`).then(setJob).catch((e) => setError(e.message));
  }, [id]);

  // Escape closes the drawer, and focus moves into it when it opens (NFR-010).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function retry() {
    setBusy(true);
    setError(null);
    try {
      setJob(await post<JobDetail>(`/jobs/${id}/assess`));
      onChanged();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const ai = job?.ai_output;
  return (
    <div className="fixed inset-0 z-20 flex justify-end bg-black/30" onClick={onClose}>
      <aside role="dialog" aria-modal="true" aria-label={job?.title ?? "Job details"}
        className="h-full w-full max-w-xl overflow-y-auto bg-white p-6 shadow-xl" onClick={(e) => e.stopPropagation()}>
        <button autoFocus className="float-right text-sm text-slate-500 hover:text-slate-900" onClick={onClose}>Close ✕</button>
        {error && <Notice kind="error">{error}</Notice>}
        {!job ? (
          <p className="text-sm text-slate-500">Loading…</p>
        ) : (
          <>
            <h2 className="pr-16 text-lg font-semibold">{job.title}</h2>
            <div className="mt-1 text-sm text-slate-500">
              {job.source_id} · {job.category} · {money(job.budget_min, job.currency)}–{money(job.budget_max, job.currency)} · due in {job.deadline_days} days
              <Markers job={job} />
            </div>
            <div className="mt-3 flex items-center gap-2">
              <Decision job={job} />
              <Eligible job={job} />
              {job.score !== null && <span className="text-sm text-slate-600">score {job.score.toFixed(1)}</span>}
            </div>

            {job.status === "unassessed" && (
              <div className="mt-4">
                <Notice kind="error">{job.unassessed_reason}</Notice>
                <button className="btn" disabled={busy} onClick={retry}>{busy ? "Retrying…" : "Retry assessment"}</button>
              </div>
            )}
            {(job.status === "stale" || job.status === "pending") && (
              <div className="mt-4">
                <Notice kind="warn">
                  {job.status === "stale"
                    ? "The listing, your profile or your policy changed since this assessment. It is not eligible until re-assessed."
                    : "This job has not been assessed yet."}
                </Notice>
                <button className="btn" disabled={busy} onClick={retry}>{busy ? "Assessing…" : "Assess now"}</button>
              </div>
            )}

            {!!job.rule_reasons.length && (
              <Section title="Decision reasons (application rules)">
                <ul className="ml-5 list-disc text-sm">{job.rule_reasons.map((r) => <li key={r}>{r}</li>)}</ul>
              </Section>
            )}

            {ai && (
              <>
                <Section title={`AI assessment${job.reused_ai_output ? " (reused after a policy-only change)" : ""}`}>
                  <dl className="grid grid-cols-[9rem_1fr] gap-y-1 text-sm">
                    <dt className="text-slate-500">Category</dt><dd>{ai.category}</dd>
                    <dt className="text-slate-500">Fit</dt><dd>{ai.fit.toFixed(2)}</dd>
                    <dt className="text-slate-500">Effort</dt><dd>{ai.effort_hours_min}–{ai.effort_hours_max} hours</dd>
                    <dt className="text-slate-500">Price estimate</dt><dd>{money(ai.price_min, job.currency)}–{money(ai.price_max, job.currency)}</dd>
                    <dt className="text-slate-500">Uncertainty</dt><dd>{ai.uncertainty}</dd>
                  </dl>
                </Section>
                <Section title="Why it fits (or not)">
                  <ul className="ml-5 list-disc text-sm">{ai.fit_reasons.map((r) => <li key={r}>{r}</li>)}</ul>
                </Section>
                {!!ai.deliverables.length && (
                  <Section title="Expected deliverables">
                    <ul className="ml-5 list-disc text-sm">{ai.deliverables.map((d) => <li key={d}>{d}</li>)}</ul>
                  </Section>
                )}
                {!!ai.assumptions.length && (
                  <Section title="Assumptions behind the estimates">
                    <ul className="ml-5 list-disc text-sm">{ai.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
                  </Section>
                )}
                <Section title="Expected return">
                  <p className="text-sm">{ai.expected_return_basis}</p>
                  {job.score_breakdown && (
                    <p className="mt-1 text-sm text-slate-500">
                      Basis used for ranking: {money(job.score_breakdown.expected_return.price, job.currency)} for about{" "}
                      {job.score_breakdown.expected_return.effort_hours} hours ≈ {money(job.score_breakdown.expected_return.hourly_rate, job.currency)}/hour.
                    </p>
                  )}
                </Section>
                {!!ai.open_questions.length && (
                  <Section title="Open questions for the client">
                    <ul className="ml-5 list-disc text-sm">{ai.open_questions.map((q) => <li key={q}>{q}</li>)}</ul>
                  </Section>
                )}
              </>
            )}

            {job.score_breakdown && (
              <Section title="Score breakdown (0–1 × weight)">
                <table className="text-sm">
                  <tbody>
                    {Object.entries(job.score_breakdown.parts).map(([k, v]) => (
                      <tr key={k}>
                        <td className="pr-4 capitalize text-slate-500">{k}</td>
                        <td className="pr-4">{v.toFixed(2)}</td>
                        <td className="text-slate-500">× {job.score_breakdown!.weights[k]}</td>
                      </tr>
                    ))}
                    <tr><td className="pr-4 font-medium">Total</td><td className="font-medium" colSpan={2}>{job.score_breakdown.total} / 100</td></tr>
                  </tbody>
                </table>
              </Section>
            )}

            <Section title="Listing">
              <p className="whitespace-pre-wrap text-sm">{job.description}</p>
              <p className="mt-2 text-sm text-slate-500">
                Skills: {job.skills.join(", ")} · Client: {job.client.name ?? "—"} (not used by the AI)
              </p>
            </Section>

            <Section title="Versions">
              <p className="text-sm">
                Assessed with listing v{job.assessed_with?.listing ?? "—"}, profile v{job.assessed_with?.profile ?? "—"}, policy v{job.assessed_with?.policy ?? "—"}.
                Current: listing v{job.current_versions.listing}, profile v{job.current_versions.profile}, policy v{job.current_versions.policy ?? "—"}.
              </p>
            </Section>

            <Section title="Assessment history">
              <ul className="text-sm">
                {job.history.map((h) => (
                  <li key={h.id} className="border-t border-slate-100 py-1">
                    {when(h.created_at)} · {h.status === "assessed" ? `${h.classification} (${h.score})` : `unassessed: ${h.unassessed_reason}`}
                    <span className="text-slate-500"> · L{h.versions.listing}/P{h.versions.profile}/Pol{h.versions.policy}</span>
                  </li>
                ))}
              </ul>
            </Section>
          </>
        )}
      </aside>
    </div>
  );
}
