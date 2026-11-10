// Coloured message box used for errors, warnings and confirmations.
const STYLES = {
  error: "border-red-200 bg-red-50 text-red-800",
  warn: "border-amber-200 bg-amber-50 text-amber-900",
  ok: "border-emerald-200 bg-emerald-50 text-emerald-800",
  info: "border-slate-200 bg-slate-100 text-slate-700",
};

export default function Notice({ kind, children }: { kind: keyof typeof STYLES; children: React.ReactNode }) {
  return <div className={`mb-4 rounded-md border px-3 py-2 text-sm ${STYLES[kind]}`}>{children}</div>;
}
