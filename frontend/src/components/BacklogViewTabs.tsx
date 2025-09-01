"use client";
import { ItemTree } from '@/components/ItemTree';
import { BacklogTable } from '@/components/BacklogTable';
import { DiagramView } from '@/components/backlog/DiagramView';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { BacklogItem } from '@/models/backlogItem';

interface BacklogViewTabsProps {
  projectId: number | null;
  onEdit: (item: BacklogItem) => void;
}

export function BacklogViewTabs({ projectId, onEdit }: BacklogViewTabsProps) {
  return (
    <Tabs defaultValue="tree" className="w-full">
      <TabsList className="grid w-full grid-cols-3 mb-4">
        <TabsTrigger value="diagram">Vue Diagramme</TabsTrigger>
        <TabsTrigger value="tree">Vue Arbre</TabsTrigger>
        <TabsTrigger value="table">Vue Table</TabsTrigger>
      </TabsList>

      <TabsContent value="tree">
        <ItemTree projectId={projectId} onEdit={onEdit} />
      </TabsContent>

      <TabsContent value="table">
        <BacklogTable projectId={projectId} onEdit={onEdit} />
      </TabsContent>

      <TabsContent value="diagram">
        <DiagramView projectId={projectId} />
      </TabsContent>
    </Tabs>
  );
}
