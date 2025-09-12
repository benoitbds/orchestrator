import { auth } from './firebase';

async function getToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null;
  const user = auth.currentUser;
  return user ? await user.getIdToken() : null;
}

export async function getWSUrl(path = "/stream"): Promise<string> {
  // 1) Prefer explicit override from env in production or staging.
  const explicit = process.env.NEXT_PUBLIC_WS_URL;
  let base: string;
  if (explicit && explicit.trim().length > 0) {
    base = explicit;
  } else if (typeof window !== "undefined") {
    // 2) Derive from current location (works for both dev and prod).
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    base = `${proto}://${host}${path}`;
  } else {
    // 3) SSR/build fallback (safe default for production).
    base = `wss://${process.env.NEXT_PUBLIC_DOMAIN ?? "agent4ba.baq.ovh"}${path}`;
  }
  const token = await getToken();
  return token ? `${base}?token=${encodeURIComponent(token)}` : base;
}
