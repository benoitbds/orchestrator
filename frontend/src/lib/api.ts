export function getApiBaseUrl(): string {
  let base = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api';
  if (!base) return '';
  base = base.replace(/\/+$/, '');
  return base;
}

export function http(path: string, init?: RequestInit) {
  const base = getApiBaseUrl();
  const url = `${base}${path.startsWith('/') ? path : '/' + path}`;
  return fetch(url, init);
}

export async function runAgent(payload: { project_id: number; objective: string }) {
  const res = await fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Agent run failed');
  return res.json();
}
