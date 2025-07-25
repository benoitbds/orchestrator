"use client";
import { useState } from 'react';
import { useProjects } from '@/context/ProjectContext';
import { ItemTree } from '@/components/ItemTree';
import { Button } from '@/components/ui/button';
import { ItemDialog } from './ItemDialog';
import { BacklogItem } from '@/models/backlogItem';
import { mutate } from 'swr';

export default function BacklogPane() {
  const { currentProject } = useProjects();
  const [isDialogOpen, setIsDialogOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<BacklogItem | undefined>(undefined);

  const handleNewItem = () => {
    setEditingItem(undefined);
    setIsDialogOpen(true);
  };

  const handleEditItem = (item: BacklogItem) => {
    setEditingItem(item);
    setIsDialogOpen(true);
  };

  const handleSave = async (item: Partial<BacklogItem>) => {
    const method = item.id ? 'PATCH' : 'POST';
    const url = item.id ? `/api/items/${item.id}` : '/api/items';

    await fetch(url, {
      method,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item),
    });

    mutate(`/api/items?project_id=${currentProject?.id}`);
  };

  return (
    <div className="p-4 border rounded-md bg-gray-50">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-medium">Backlog</h3>
        <Button size="sm" onClick={handleNewItem} disabled={!currentProject}>
          Nouvel item
        </Button>
      </div>
      <ItemTree projectId={currentProject?.id ?? null} onEdit={handleEditItem} />
      {currentProject && (
        <ItemDialog
          isOpen={isDialogOpen}
          onClose={() => setIsDialogOpen(false)}
          item={editingItem}
          projectId={currentProject.id}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
