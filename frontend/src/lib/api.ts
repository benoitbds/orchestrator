import { auth } from "./firebase";

export async function apiFetch(path: string, init?: RequestInit) {
  const headers = new Headers(init?.headers);
  try {
    const token = await auth.currentUser?.getIdToken();
    if (token) headers.set("Authorization", `Bearer ${token}`);
  } catch {}
  return fetch(`${process.env.NEXT_PUBLIC_API_BASE_URL}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
}

export async function runAgent(payload: { project_id: number; objective: string }) {
  const res = await apiFetch("/agent/run", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Agent run failed");
  return res.json();
}

export async function validateItem(id: number, fields?: string[]) {
  const res = await apiFetch(`/items/${id}/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields: fields ?? null }),
  });
  if (!res.ok) {
    throw new Error("Failed to validate item");
  }
  return res.json();
}

export async function validateItems(ids: number[]) {
  const res = await apiFetch(`/items/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!res.ok) {
    throw new Error("Failed to validate items");
  }
  return res.json();
}
