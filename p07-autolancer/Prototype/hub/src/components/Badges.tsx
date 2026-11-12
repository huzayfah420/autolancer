// Small status markers shared by the feed table and the drawer.
import type { JobItem } from "@/lib/types";

const CLASS_STYLE: Record<string, string> = {
  pursue: "bg-emerald-100 text-emerald-800",
  clarify: "bg-amber-100 text-amber-900",
  decline: "bg-slate-200 text-slate-700",
};

export function Decision({ job }: { job: JobItem }) {
  if (job.status === "unassessed") return <span className="badge bg-red-100 text-red-800">unassessed</span>;
  if (job.status === "pending") return <span className="badge bg-slate-100 text-slate-600">not assessed yet</span>;
  // "pursue" only stays green when the system may act on it. A closed listing is struck
  // through, and one the rules hold for the owner is shown as needing review.
  const held = job.classification === "pursue" && job.status === "assessed" && !job.pursue_eligible && !job.is_closed;
  const style = job.is_closed
    ? "bg-slate-100 text-slate-500 line-through"
    : held
      ? "bg-amber-100 text-amber-900"
      : (CLASS_STYLE[job.classification ?? ""] ?? "");
  const title = job.is_closed
    ? "Decision from before the listing closed; no longer actionable"
    : held
      ? "Suitable, but held for your review. Open the job for the reason."
      : undefined;
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`badge whitespace-nowrap ${style}`} title={title}>
        {job.classification}{held && " · needs review"}
      </span>
      {job.status === "stale" && <span className="badge bg-orange-100 text-orange-800" title="Listing, profile or policy changed since this assessment">stale</span>}
    </span>
  );
}

export function Markers({ job }: { job: JobItem }) {
  return (
    <>
      {job.is_new && <span className="badge ml-1 bg-blue-100 text-blue-800">new</span>}
      {job.is_changed && <span className="badge ml-1 bg-violet-100 text-violet-800">changed</span>}
      {job.is_closed && (
        <span className="badge ml-1 bg-red-100 text-red-800" title="No longer listed on the marketplace as of the last fetch">
          closed
        </span>
      )}
      {job.simulated && <span className="badge ml-1 bg-slate-100 text-slate-500">simulated</span>}
    </>
  );
}

export function Eligible({ job }: { job: JobItem }) {
  return job.pursue_eligible ? (
    <span className="badge bg-emerald-600 text-white" title="Qualifies for automatic pursuit under the active policy">
      pursue-eligible
    </span>
  ) : null;
}
