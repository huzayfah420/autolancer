"use client";
// Email/password sign-in (row 1). Any failure shows the same generic message (UC-001 E1).
import { useRouter } from "next/navigation";
import { useLayoutEffect, useState } from "react";
import Notice from "@/components/Notice";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [failed, setFailed] = useState(false);
  const [busy, setBusy] = useState(false);

  // Next.js keeps this page mounted (hidden) after sign-in. Clear the form when it is hidden,
  // so the email and password are not still there when the owner signs out.
  useLayoutEffect(() => () => { setEmail(""); setPassword(""); setFailed(false); setBusy(false); }, []);

  async function signIn(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setFailed(false);
    try {
      const { error } = await supabase().auth.signInWithPassword({ email, password });
      if (error) throw error;
      router.replace("/");
    } catch {
      // Never say whether the email exists or what went wrong.
      setFailed(true);
      setPassword("");
      setBusy(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <form onSubmit={signIn} className="card w-full max-w-sm">
        <h1 className="mb-1 text-xl font-semibold">Autolancer</h1>
        <p className="mb-5 text-sm text-slate-500">Sign in to the owner hub.</p>
        {failed && <Notice kind="error">Sign-in failed. Check your details and try again.</Notice>}
        <label className="label" htmlFor="email">Email</label>
        <input id="email" type="email" required autoComplete="email" className="input mb-3"
          value={email} onChange={(e) => setEmail(e.target.value)} />
        <label className="label" htmlFor="password">Password</label>
        <input id="password" type="password" required autoComplete="current-password" className="input mb-5"
          value={password} onChange={(e) => setPassword(e.target.value)} />
        <button className="btn w-full justify-center" disabled={busy}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
    </div>
  );
}
