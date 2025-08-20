"use client";
import { useState } from 'react';
import { useProjects } from '@/context/ProjectContext';
import { ItemTree } from '@/components/ItemTree';
import { BacklogTable } from '@/components/BacklogTable';
import { BacklogDiagram } from '@/components/BacklogDiagram';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { ItemDialog } from './ItemDialog';
import { BacklogItem } from '@/models/backlogItem';
import { mutate } from 'swr';
import { http } from '@/lib/api';

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
    try {
      const method = item.id ? 'PATCH' : 'POST';
      const url = item.id ? `/items/${item.id}` : '/items';

      console.log('Saving item:', item); // Debug log

      const response = await http(url, {
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
      
      mutate(`/items?project_id=${currentProject?.id}`);
    } catch (error) {
      console.error('Save error:', error);
      alert(`Erreur: ${error.message}`);
    }
  };

  return (
    <div className="p-4 border rounded-md bg-gray-50">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-medium">Backlog</h3>
        <Button size="sm" onClick={handleNewItem} disabled={!currentProject}>
          Nouvel item
        </Button>
      </div>
      
      <Tabs defaultValue="tree" className="w-full">
        <TabsList className="grid w-full grid-cols-3 mb-4">
          <TabsTrigger value="diagram">Vue Diagramme</TabsTrigger>
          <TabsTrigger value="tree">Vue Arbre</TabsTrigger>
          <TabsTrigger value="table">Vue Table</TabsTrigger>
        </TabsList>
        
        <TabsContent value="tree">
          <ItemTree projectId={currentProject?.id ?? null} onEdit={handleEditItem} />
        </TabsContent>
        
        <TabsContent value="table">
          <BacklogTable projectId={currentProject?.id ?? null} onEdit={handleEditItem} />
        </TabsContent>
        
        <TabsContent value="diagram">
          <BacklogDiagram projectId={currentProject?.id ?? null} onEdit={handleEditItem} />
        </TabsContent>
      </Tabs>
      
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
