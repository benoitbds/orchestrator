import useSWR from 'swr';
import { BacklogItem } from '@/models/backlogItem';

const fetcher = (url: string) => fetch(url).then(res => res.json());

export interface TreeNode extends BacklogItem {
  children: TreeNode[];
}

export function useItems(projectId: number | null) {
  const { data, error, isLoading } = useSWR<BacklogItem[]>(
    projectId ? `/api/items?project_id=${projectId}` : null,
    fetcher
  );

  const tree = buildTree(data || []);

  return {
    tree,
    data: data || [],
    error,
    isLoading,
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
