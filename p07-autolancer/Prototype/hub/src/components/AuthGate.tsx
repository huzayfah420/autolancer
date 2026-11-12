"use client";
// Shows the hub only to a signed-in owner; anyone else is sent to /login.
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { supabase } from "@/lib/supabase";

const NAV = [
  { href: "/", label: "Jobs" },
  { href: "/connections", label: "Connections" },
  { href: "/profile", label: "Profile" },
  { href: "/policy", label: "Policy" },
];

export default function AuthGate({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const pathname = usePathname();
  const [email, setEmail] = useState<string | null>(null);

  useEffect(() => {
    const sb = supabase();
    sb.auth.getSession().then(({ data }) => {
      if (!data.session) router.replace("/login");
      else setEmail(data.session.user.email ?? "owner");
    });
    // Sign-out (here or after a 401 from the API) returns to the login page.
    const { data: sub } = sb.auth.onAuthStateChange((event, session) => {
      if (event === "SIGNED_OUT" || !session) router.replace("/login");
    });
    return () => sub.subscription.unsubscribe();
  }, [router]);

  if (!email) return <p className="p-8 text-sm text-slate-500">Loading…</p>;

  return (
    <div>
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center gap-6 px-4 py-3">
          <span className="font-semibold">Autolancer</span>
          <nav className="flex gap-4 text-sm">
            {NAV.map((n) => (
              <Link
                key={n.href}
                href={n.href}
                className={pathname === n.href ? "font-semibold text-slate-900" : "text-slate-500 hover:text-slate-900"}
              >
                {n.label}
              </Link>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm text-slate-500">
            <span>{email}</span>
            <button className="btn-secondary" onClick={() => supabase().auth.signOut()}>
              Sign out
            </button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-4 py-6">{children}</main>
    </div>
  );
}
