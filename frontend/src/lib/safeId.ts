export function safeId(): string {
  // Browser with modern Web Crypto
  const g = typeof globalThis !== "undefined" ? (globalThis as { crypto?: Crypto; msCrypto?: Crypto }) : {};
  const c: Crypto | undefined = g.crypto || g.msCrypto; // IE fallback if ever

  if (c?.randomUUID) {
    return c.randomUUID();
  }

  // Node.js >= 14.17 has crypto.randomUUID
  try {
    // avoid bundlers complaining on client
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const nodeCrypto = require("crypto");
    if (nodeCrypto?.randomUUID) return nodeCrypto.randomUUID();
  } catch {}

  // Fallback UUID v4 (RFC 4122) using getRandomValues if available
  const bytes = new Uint8Array(16);
  if (c?.getRandomValues) c.getRandomValues(bytes);
  else {
    // last-resort: Math.random (not cryptographically secure)
    for (let i = 0; i < 16; i++) bytes[i] = Math.floor(Math.random() * 256);
  }
  // Per RFC 4122 v4
  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;
  const toHex = (n: number) => n.toString(16).padStart(2, "0");
  const hex = Array.from(bytes, toHex).join("");
  return (
    hex.slice(0, 8) + "-" +
    hex.slice(8, 12) + "-" +
    hex.slice(12, 16) + "-" +
    hex.slice(16, 20) + "-" +
    hex.slice(20)
  );
}
