import { http } from "@/lib/api";

export async function fetchRuns(projectId: number) {
  const res = await http(`/runs?project_id=${projectId}`);
  if (!res.ok) throw new Error(`Failed to fetch runs: ${res.status}`);
  const data = await res.json();
  if (Array.isArray(data)) return data;
  if (data && Array.isArray((data as any).runs)) return (data as any).runs;
  return [];
}

export async function fetchItems(projectId: number) {
  const res = await http(`/items?project_id=${projectId}`);
  if (!res.ok) throw new Error(`Failed to fetch items: ${res.status}`);
  return await res.json();
}
