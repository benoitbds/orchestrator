import useSWR from 'swr';
import { BacklogItem } from '@/models/backlogItem';
import { apiFetch } from '@/lib/api';

const fetcher = (url: string) => apiFetch(url).then(res => res.json());

export type TreeNode = BacklogItem & {
  children: TreeNode[];
};

export function useItems(projectId: number | null, options?: { review?: 'all' | 'pending' | 'approved' }) {
  const review = options?.review ?? 'all';
  const key = projectId ? `/items?project_id=${projectId}&review=${review}` : null;
  const { data, error, isLoading, mutate } = useSWR<BacklogItem[]>(key, fetcher);

  const tree = buildTree(data || []);

  return {
    tree,
    data: data || [],
    error,
    isLoading,
    mutate,
  };
}

function buildTree(items: BacklogItem[]): TreeNode[] {
  const tree: TreeNode[] = [];
  const childrenOf: { [key: number]: TreeNode[] } = {};

  items.forEach(item => {
    const node: TreeNode = { ...item, children: [] };
    if (item.parent_id === null) {
      tree.push(node);
    } else {
      if (!childrenOf[item.parent_id]) {
        childrenOf[item.parent_id] = [];
      }
      childrenOf[item.parent_id].push(node);
    }
  });

  function attachChildren(node: TreeNode) {
    if (childrenOf[node.id]) {
      node.children = childrenOf[node.id];
      node.children.forEach(attachChildren);
    }
  }

  tree.forEach(attachChildren);

  return tree;
}
