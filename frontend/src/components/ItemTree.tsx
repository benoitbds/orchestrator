"use client";
import dynamic from 'next/dynamic';

const Loader2 = dynamic(() => import('lucide-react').then(mod => ({ default: mod.Loader2 })), { ssr: false });
const Pencil = dynamic(() => import('lucide-react').then(mod => ({ default: mod.Pencil })), { ssr: false });
import { useItems, TreeNode } from '@/lib/hooks';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { ItemDialog } from './ItemDialog';
import { BacklogItem } from '@/models/backlogItem';

const typeColors: { [key: string]: string } = {
  Epic: 'bg-purple-500',
  Feature: 'bg-blue-500',
  US: 'bg-green-500',
  UC: 'bg-yellow-500',
};

function Item({ item, onEdit, level = 0 }: { item: TreeNode, onEdit: (item: BacklogItem) => void, level?: number }) {
  return (
    <div>
      <div className={`flex items-center gap-2 p-2 rounded-md hover:bg-gray-100 cursor-pointer`} style={{ paddingLeft: `${level * 20 + 8}px` }}>
        <Badge className={`${typeColors[item.type]} text-white`}>{item.type}</Badge>
        <span className="flex-1">{item.title}</span>
        <Button variant="ghost" size="icon" className="ml-auto" onClick={() => onEdit(item)}>
          <Pencil className="h-4 w-4" />
        </Button>
      </div>
      {item.children?.map((child) => (
        <Item key={child.id} item={child as TreeNode} onEdit={onEdit} level={level + 1} />
      ))}
    </div>
  );
}

export function ItemTree({ projectId, onEdit }: { projectId: number | null, onEdit: (item: BacklogItem) => void }) {
  const { tree, isLoading, error } = useItems(projectId);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-4">
        <Loader2 className="animate-spin" />
      </div>
    );
  }

  if (error) {
    return <div className="text-red-500">Erreur de chargement des éléments.</div>;
  }

  return (
    <div className="space-y-1">
      {tree?.map((item) => (
        <Item key={item.id} item={item} onEdit={onEdit} />
      ))}
    </div>
  );
}
