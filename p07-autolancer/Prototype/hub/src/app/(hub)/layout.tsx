// Every page in this group requires a signed-in owner.
import AuthGate from "@/components/AuthGate";

export default function HubLayout({ children }: { children: React.ReactNode }) {
  return <AuthGate>{children}</AuthGate>;
}
