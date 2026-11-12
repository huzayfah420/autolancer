// Display helpers shared by the pages.

export const money = (n: number, currency = "USD") =>
  new Intl.NumberFormat("en-US", { style: "currency", currency, maximumFractionDigits: 0 }).format(n);

// API timestamps are UTC; SQLite drops the offset, so a bare timestamp is read as UTC.
export const when =(iso: string | null) => (iso ? new Date(iso.endsWith("Z") || iso.includes("+") ? iso : iso + "Z").toLocaleString() : "never");

// Amounts under $1 keep four decimals (zero excepted), so a small AI cap never shows as $0.00.
export const usd = (n: number) => `$${n.toFixed(n > 0 && n < 1 ? 4 : 2)}`;
