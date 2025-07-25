"use client";
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { BacklogItem } from '@/models/backlogItem';
import { useItems } from '@/lib/hooks';
import { useBacklog } from '@/context/BacklogContext';
import { mutate } from 'swr';

interface ItemDialogProps {
  isOpen: boolean;
  onClose: () => void;
  item?: BacklogItem;
  projectId: number;
  onSave: (item: Partial<BacklogItem>) => Promise<void>;
}

export function ItemDialog({ isOpen, onClose, item, projectId, onSave }: ItemDialogProps) {
  const { deleteItem } = useBacklog();
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [type, setType] = useState<'Epic' | 'Feature' | 'US' | 'UC'>('US');
  const [parentId, setParentId] = useState<number | null>(null);
  const { data: items } = useItems(projectId);

  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  useEffect(() => {
    if (item) {
      setTitle(item.title);
      setDescription(item.description || '');
      setType(item.type);
      setParentId(item.parent_id);
    } else {
      setTitle('');
      setDescription('');
      setType('US');
      setParentId(null);
    }
  }, [item, isOpen]);

  const handleSubmit = async () => {
    await onSave({
      id: item?.id,
      title,
      description,
      type,
      parent_id: parentId,
      project_id: projectId,
    });
    onClose();
  };

  // Logique de filtrage des parents selon le type sélectionné
  const getPossibleParents = () => {
    if (!items) return [];
    
    switch (type) {
      case 'Feature':
        return items.filter(i => i.type === 'Epic');
      case 'US':
        return items.filter(i => i.type === 'Feature');
      case 'UC':
        return items.filter(i => i.type === 'US');
      case 'Epic':
      default:
        return []; // Les Epics n'ont pas de parent
    }
  };
  
  const possibleParents = getPossibleParents();

  const getDescendants = (rootId: number): BacklogItem[] => {
    const result: BacklogItem[] = [];
    const traverse = (parentId: number) => {
      items?.forEach(i => {
        if (i.parent_id === parentId) {
          result.push(i);
          traverse(i.id);
        }
      });
    };
    traverse(rootId);
    return result;
  };
  const descendants = item ? getDescendants(item.id) : [];

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{item ? 'Modifier' : 'Nouvel'} item</DialogTitle>
        </DialogHeader>
        <div className="grid gap-4 py-4">
          <Input
            placeholder="Titre"
            value={title}
            onChange={e => setTitle(e.target.value)}
          />
          <Input
            placeholder="Description"
            value={description}
            onChange={e => setDescription(e.target.value)}
          />
          <Select value={type} onValueChange={(v: any) => setType(v)}>
            <SelectTrigger>
              <SelectValue placeholder="Type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="Epic">Epic</SelectItem>
              <SelectItem value="Feature">Feature</SelectItem>
              <SelectItem value="US">US</SelectItem>
              <SelectItem value="UC">UC</SelectItem>
            </SelectContent>
          </Select>
          <Select value={parentId?.toString() || "null"} onValueChange={(v: any) => setParentId(v === "null" ? null : Number(v))}>
            <SelectTrigger>
              <SelectValue placeholder="Parent" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="null">Aucun</SelectItem>
              {possibleParents.map(p => (
                <SelectItem key={p.id} value={p.id.toString()}>
                  {p.title}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <DialogFooter>
          {item && (
            <Button variant="destructive" onClick={() => setShowDeleteConfirm(true)}>
              Supprimer
            </Button>
          )}
          <Button onClick={handleSubmit}>Enregistrer</Button>
        </DialogFooter>
      </DialogContent>
      <Dialog open={showDeleteConfirm} onOpenChange={setShowDeleteConfirm}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Confirmation de suppression</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            {descendants.length > 0 ? (
              <>
                <p>L'item suivant et ses sous-items seront supprimés :</p>
                <ul className="list-disc ml-6">
                  {descendants.map(d => (
                    <li key={d.id}>{d.title}</li>
                  ))}
                </ul>
              </>
            ) : (
              <p>Voulez-vous supprimer cet item ?</p>
            )}
          </div>
          <DialogFooter>
            <Button onClick={() => setShowDeleteConfirm(false)}>Annuler</Button>
            <Button
              variant="destructive"
              onClick={async () => {
                if (item) {
                  await deleteItem(item.id);
                  // rafraîchir la liste des items
                  mutate(`/api/items?project_id=${projectId}`);
                  setShowDeleteConfirm(false);
                  onClose();
                }
              }}
            >
              Supprimer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </Dialog>
  );
}
''
