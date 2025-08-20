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
