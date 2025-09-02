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
    <Tabs defaultValue="tree" className="w-full h-full flex flex-col">
      <TabsList className="grid w-full grid-cols-3 mb-4 flex-shrink-0">
        <TabsTrigger value="diagram">Vue Diagramme</TabsTrigger>
        <TabsTrigger value="tree">Vue Arbre</TabsTrigger>
        <TabsTrigger value="table">Vue Table</TabsTrigger>
      </TabsList>

      <TabsContent value="tree" className="flex-1 min-h-0 overflow-y-auto mt-0">
        <div className="h-full overflow-y-auto">
          <ItemTree projectId={projectId} onEdit={onEdit} />
        </div>
      </TabsContent>

      <TabsContent value="table" className="flex-1 min-h-0 overflow-y-auto mt-0">
        <div className="h-full overflow-y-auto">
          <BacklogTable projectId={projectId} onEdit={onEdit} />
        </div>
      </TabsContent>

      <TabsContent value="diagram" className="flex-1 min-h-0 overflow-y-auto mt-0">
        <div className="h-full overflow-y-auto">
          <DiagramView projectId={projectId} />
        </div>
      </TabsContent>
    </Tabs>
  );
}
