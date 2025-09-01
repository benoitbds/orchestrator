import { http } from '@/lib/api';

export interface LayoutNode {
  item_id: number;
  x: number;
  y: number;
  pinned?: boolean;
}

export async function getLayout(projectId: number): Promise<LayoutNode[]> {
  const res = await http(`/projects/${projectId}/layout`);
  if (!res.ok) {
    throw new Error('Failed to fetch layout');
  }
  const data = await res.json();
  return Array.isArray(data.nodes) ? data.nodes : [];
}

export async function saveLayout(projectId: number, nodes: LayoutNode[]): Promise<void> {
  const res = await http(`/projects/${projectId}/layout`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ nodes }),
  });
  if (!res.ok) {
    throw new Error('Failed to save layout');
  }
}
