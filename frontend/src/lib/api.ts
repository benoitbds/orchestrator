import { auth } from './firebase';

export function getApiBaseUrl(): string {
  let base = process.env.NEXT_PUBLIC_API_BASE_URL ?? '/api';
  if (!base) return '';
  base = base.replace(/\/+$/, '');
  return base;
}

async function getToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null;
  const user = auth.currentUser;
  return user ? await user.getIdToken() : null;
}

export async function http(path: string, init?: RequestInit) {
  const base = getApiBaseUrl();
  const url = `${base}${path.startsWith('/') ? path : '/' + path}`;
  const headers = new Headers(init?.headers);
  const token = await getToken();
  if (token) headers.set('Authorization', `Bearer ${token}`);
  return fetch(url, { ...init, headers });
}

export async function runAgent(payload: { project_id: number; objective: string }) {
  const res = await http(`/agent/run`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error('Agent run failed');
  return res.json();
}
