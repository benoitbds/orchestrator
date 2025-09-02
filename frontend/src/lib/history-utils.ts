export function ms(n?: number): string {
  return n == null ? '' : `${n}ms`;
}

export function formatTime(t: string): string {
  const d = new Date(t);
  return d.toLocaleTimeString();
}
