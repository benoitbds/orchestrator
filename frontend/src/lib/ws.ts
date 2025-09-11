export function getWSUrl(path = "/stream"): string {
  // 1) Prefer explicit override from env in production or staging.
  const explicit = process.env.NEXT_PUBLIC_WS_URL;
  if (explicit && explicit.trim().length > 0) {
    return explicit;
  }

  // 2) Derive from current location (works for both dev and prod).
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host; // e.g., agent4ba.baq.ovh or localhost:3000
    return `${proto}://${host}${path}`;
  }

  // 3) SSR/build fallback (safe default for production).
  return `wss://${process.env.NEXT_PUBLIC_DOMAIN ?? "agent4ba.baq.ovh"}${path}`;
}
