export function getWSUrl(path = "/stream"): string {
  const explicit = process.env.NEXT_PUBLIC_WS_URL;
  if (explicit && explicit.trim().length > 0) return explicit;
  if (typeof window !== "undefined") {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    const host = window.location.host;
    return `${proto}://${host}${path}`;
  }
  return `wss://agent4ba.baq.ovh${path}`;

}
