// Root layout: plain HTML shell. Auth and navigation live in the (hub) route group.
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Autolancer Hub",
  description: "Owner hub for the Autolancer Phase 1 prototype",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en">
      <body className="min-h-screen">{children}</body>
    </html>
  );
}
