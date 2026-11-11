"use client";
// Connections page (row 2): connect the Marketplace Simulator and see its status and operations.
import { useEffect, useLayoutEffect, useState } from "react";
import Notice from "@/components/Notice";
import { get, put } from "@/lib/api";
import { when } from "@/lib/format";
import type { Connection } from "@/lib/types";

const STATUS_STYLE = {
  connected: "bg-emerald-100 text-emerald-800",
  unavailable: "bg-red-100 text-red-800",
  disconnected: "bg-slate-200 text-slate-700",
};

export default function ConnectionsPage() {
  const [conn, setConn] = useState<Connection | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    get<Connection[]>("/connections").then((c) => setConn(c[0])).catch((e) => setError(e.message));
  }, []);

  // The page stays mounted (hidden) after navigating away; clear it so a return shows fresh status.
  useLayoutEffect(() => () => { setConn(null); setError(null); }, []);

  // Turning it on asks the simulator for its capabilities; turning it off leaves it disconnected.
  async function setEnabled(enabled: boolean) {
    setBusy(true);
    setError(null);
    try {
      setConn(await put<Connection>("/connections/simulator", { enabled }));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="mb-4 text-2xl font-semibold">Connections</h1>
      {error && <Notice kind="error">{error}</Notice>}
      {!conn ? (
        <p className="text-sm text-slate-500">Loading…</p>
      ) : (
        <div className="card">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-medium">Marketplace Simulator</h2>
            <span className={`badge ${STATUS_STYLE[conn.status]}`}>{conn.status}</span>
            <label className="ml-auto flex cursor-pointer items-center gap-2 text-sm">
              <input type="checkbox" className="h-4 w-4" checked={conn.enabled} disabled={busy}
                onChange={(e) => setEnabled(e.target.checked)} />
              Enabled
            </label>
          </div>
          <p className="mt-1 text-sm text-slate-500">
            A stand-in marketplace with made-up listings. All its data is marked as simulated.
          </p>

          <dl className="mt-4 grid grid-cols-[10rem_1fr] gap-y-2 text-sm">
            <dt className="text-slate-500">Account</dt>
            <dd>{conn.account_name ?? "—"}</dd>
            <dt className="text-slate-500">Supported operations</dt>
            <dd>
              {conn.operations.length ? (
                conn.operations.map((op) => <span key={op} className="badge mr-1 bg-slate-100 font-mono">{op}</span>)
              ) : (
                <span className="text-slate-500">none available</span>
              )}
            </dd>
            <dt className="text-slate-500">Details</dt>
            <dd>{conn.status_detail ?? "—"}</dd>
            <dt className="text-slate-500">Last checked</dt>
            <dd>{when(conn.checked_at)}</dd>
          </dl>

          {conn.status === "unavailable" && (
            <div className="mt-4">
              <Notice kind="warn">The simulator could not be reached. Job fetching stays disabled until it reconnects.</Notice>
              <button className="btn" disabled={busy} onClick={() => setEnabled(true)}>Try again</button>
            </div>
          )}
          {conn.status === "disconnected" && (
            <p className="mt-4 text-sm text-slate-500">Disconnected: its operations are unavailable and job fetching is off.</p>
          )}
        </div>
      )}
    </div>
  );
}
