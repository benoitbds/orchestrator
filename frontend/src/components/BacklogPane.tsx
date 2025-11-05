"use client";
import { useState } from 'react';
import { useProjects } from '@/context/ProjectContext';
import { useBacklog } from '@/context/BacklogContext';
import { Button } from '@/components/ui/button';
import { ItemDialog } from './ItemDialog';
import { BacklogItem } from '@/models/backlogItem';
import { apiFetch } from '@/lib/api';
import { BacklogViewTabs } from '@/components/BacklogViewTabs';

export default function BacklogPane() {
  const { currentProject } = useProjects();
  const { refreshItems } = useBacklog();
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
    try {
      const method = item.id ? 'PATCH' : 'POST';
      const url = item.id ? `/items/${item.id}` : '/items';

      console.log('Saving item:', item); // Debug log

      const response = await apiFetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item),
      });

      if (!response.ok) {
        const error = await response.text();
        console.error('Save failed:', response.status, error);
        alert(`Erreur lors de la sauvegarde: ${error}`);
        return;
      }

      const result = await response.json();
      console.log('Save successful:', result); // Debug log
      
      // Refresh via BacklogContext (which uses SWR internally)
      await refreshItems();
      
      setIsDialogOpen(false);
    } catch (error) {
      console.error('Save error:', error);
      alert(`Erreur: ${error instanceof Error ? error.message : String(error)}`);
    }
  };

  return (
    <div className="p-4 h-full flex flex-col">
      <div className="flex justify-end items-center mb-4 flex-shrink-0">
        <Button size="sm" onClick={handleNewItem} disabled={!currentProject}>
          Nouvel item
        </Button>
      </div>
      
      <div className="flex-1 min-h-0">
        <BacklogViewTabs
          projectId={currentProject?.id ?? null}
          onEdit={handleEditItem}
        />
      </div>
      
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
