// Display helpers shared by the pages.

export const money = (n: number, currency = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);

// API timestamps are UTC; SQLite drops the offset, so a bare timestamp is read as UTC.
export const when =(iso: string | null) => (iso ? new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z").toLocaleString() : "never");

export const usd = (n: number) => `$${n.toFixed(n < 1 ? 4 : 2)}`;
