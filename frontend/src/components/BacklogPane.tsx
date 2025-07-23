"use client";
import { useState } from 'react';
import { useBacklog } from '@/context/BacklogContext';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { useProjects } from '@/context/ProjectContext';

export default function BacklogPane() {
  const { items, createItem } = useBacklog();
  const { currentProject } = useProjects();
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [type, setType] = useState('Epic');

  const disabled = !currentProject;

  const handleCreate = async () => {
    await createItem({ title, type, description: '', parent_id: null, project_id: currentProject!.id });
    setTitle('');
    setOpen(false);
  };

  const renderItems = (parent: number | null, depth = 0) =>
    items
      .filter((i) => i.parent_id === parent)
      .map((i) => (
        <div key={i.id} style={{ marginLeft: depth * 16 }} className="flex items-center gap-2 py-1">
          <span>{i.type === 'Epic' ? '📦' : '📝'}</span>
          <span>{i.title}</span>
        </div>
      ));

  return (
    <div className="p-4 border rounded-md bg-gray-50">
      <div className="flex justify-between items-center mb-2">
        <h3 className="font-medium">Backlog</h3>
        <Button size="sm" onClick={() => setOpen(true)} disabled={disabled}>
          +
        </Button>
      </div>
      <div>{renderItems(null)}</div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Nouvel item</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <Input placeholder="Titre" value={title} onChange={(e) => setTitle(e.target.value)} />
          </div>
          <DialogFooter>
            <Button onClick={handleCreate}>Créer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
