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
  return (
    <span className="inline-flex items-center gap-1">
      <span className={`badge ${CLASS_STYLE[job.classification ?? ""] ?? ""}`}>{job.classification}</span>
      {job.status === "stale" && <span className="badge bg-orange-100 text-orange-800" title="Listing, profile or policy changed since this assessment">stale</span>}
    </span>
  );
}

export function Markers({ job }: { job: JobItem }) {
  return (
    <>
      {job.is_new && <span className="badge ml-1 bg-blue-100 text-blue-800">new</span>}
      {job.is_changed && <span className="badge ml-1 bg-violet-100 text-violet-800">changed</span>}
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
