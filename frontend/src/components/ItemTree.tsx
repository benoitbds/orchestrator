"use client";
import dynamic from 'next/dynamic';

const Loader2 = dynamic(() => import('lucide-react').then(mod => ({ default: mod.Loader2 })), { ssr: false });
const Pencil = dynamic(() => import('lucide-react').then(mod => ({ default: mod.Pencil })), { ssr: false });
const CpuIcon = dynamic(() => import('lucide-react').then(mod => ({ default: mod.Cpu })), { ssr: false });
const ChevronRight = dynamic(() => import('lucide-react').then(mod => ({ default: mod.ChevronRight })), { ssr: false });
const ChevronDown = dynamic(() => import('lucide-react').then(mod => ({ default: mod.ChevronDown })), { ssr: false });
import { useItems, TreeNode } from '@/lib/hooks';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { useState } from 'react';
import { BacklogItem } from '@/models/backlogItem';
import { mutate } from 'swr';
import { http } from '@/lib/api';

const typeColors: { [key: string]: string } = {
  Epic: 'bg-purple-500',
  Capability: 'bg-purple-400', 
  Feature: 'bg-blue-500',
  US: 'bg-green-500',
  UC: 'bg-yellow-500',
};

// Couleurs pour les états des Epics/Capabilities
const stateColors: { [key: string]: string } = {
  Funnel: 'bg-gray-400',
  Reviewing: 'bg-orange-400',
  Analyzing: 'bg-yellow-500',
  Backlog: 'bg-blue-400',
  Implementing: 'bg-indigo-500',
  Done: 'bg-green-500',
};

// Couleurs pour les statuts des Stories (US/UC)
const statusColors: { [key: string]: string } = {
  Todo: 'bg-gray-400',
  Doing: 'bg-yellow-500',
  Done: 'bg-green-500',
};

const allowedParent: Record<string, string | null> = {
  Epic: null,
  Capability: 'Epic',
  Feature: 'Capability',
  US: 'Feature',
  UC: 'US',
};

// Fonction pour obtenir la couleur du badge principal selon le type et l'état
const getBadgeColor = (item: TreeNode): string => {
  // Toujours utiliser la couleur du type pour plus de clarté
  return typeColors[item.type] || 'bg-gray-500';
};

// Fonction pour obtenir la couleur du badge d'état/statut
const getStateBadgeColor = (item: TreeNode): string => {
  if ((item.type === 'Epic' || item.type === 'Capability') && 'state' in item && item.state) {
    return stateColors[item.state] || 'bg-gray-400';
  }
  if ((item.type === 'US' || item.type === 'UC') && 'status' in item && item.status) {
    return statusColors[item.status] || 'bg-gray-400';
  }
  return 'bg-gray-400';
};

interface ItemProps {
  item: TreeNode;
  onEdit: (item: BacklogItem) => void;
  level?: number;
  collapsed: Set<number>;
  toggle: (id: number) => void;
  onDragStart: (item: TreeNode) => void;
  onDrop: (parent: TreeNode | null) => void;
}

function Item({ item, onEdit, level = 0, collapsed, toggle, onDragStart, onDrop }: ItemProps) {
  const isCollapsed = collapsed.has(item.id);
  const hasChildren = item.children && item.children.length > 0;

  const getTooltipContent = () => {
    const parts = [`${item.type}: ${item.title}`];

    if ((item.type === 'Epic' || item.type === 'Capability') && 'state' in item && item.state) {
      parts.push(`État: ${item.state}`);
    }
    if ((item.type === 'US' || item.type === 'UC') && 'status' in item && item.status) {
      parts.push(`Statut: ${item.status}`);
    }
    if ('wsjf' in item && item.wsjf) {
      parts.push(`WSJF: ${item.wsjf}`);
    }
    if ('program_increment' in item && item.program_increment) {
      parts.push(`PI: ${item.program_increment}`);
    }
    if ('iteration' in item && item.iteration) {
      parts.push(`Sprint: ${item.iteration}`);
    }
    if ('story_points' in item && item.story_points) {
      parts.push(`Points: ${item.story_points}`);
    }
    if ('owner' in item && item.owner) {
      parts.push(`Owner: ${item.owner}`);
    }

    return parts.join('\n');
  };

  return (
    <div
      draggable
      onDragStart={() => onDragStart(item)}
      onDragOver={(e) => e.preventDefault()}
      onDrop={() => onDrop(item)}
    >
      <div
        className={`flex items-center gap-2 p-2 rounded-md hover:bg-gray-100 cursor-pointer`}
        style={{ paddingLeft: `${level * 20 + 8}px` }}
        title={getTooltipContent()}
        data-item-id={item.id}
      >
        {hasChildren && (
          <button
            onClick={() => toggle(item.id)}
            aria-label={isCollapsed ? 'Expand' : 'Collapse'}
            className="p-0 w-4 h-4 text-gray-600"
          >
            {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
          </button>
        )}
        {/* Badge principal avec couleur selon state/status */}
        <Badge className={`${getBadgeColor(item)} text-white`}>
          {item.type}
        </Badge>

        {/* Badge d'état/statut avec couleur spécifique */}
        {((item.type === 'Epic' || item.type === 'Capability') && 'state' in item && item.state) && (
          <Badge className={`${getStateBadgeColor(item)} text-white text-xs`}>
            {item.state}
          </Badge>
        )}
        {((item.type === 'US' || item.type === 'UC') && 'status' in item && item.status) && (
          <Badge className={`${getStateBadgeColor(item)} text-white text-xs`}>
            {item.status}
          </Badge>
        )}

        {/* Badges additionnels pour infos SAFe */}
        <div className="flex gap-1">
          {'wsjf' in item && item.wsjf && (
            <Badge variant="outline" className="text-xs">
              WSJF: {item.wsjf}
            </Badge>
          )}
          {'story_points' in item && item.story_points && (
            <Badge variant="outline" className="text-xs">
              {item.story_points}pts
            </Badge>
          )}
          {'program_increment' in item && item.program_increment && (
            <Badge variant="outline" className="text-xs">
              PI: {item.program_increment}
            </Badge>
          )}
        </div>

        <div className="flex-1 flex items-center gap-2">
          <span
            className="cursor-pointer font-medium"
            onClick={() => onEdit(item)}
          >
            {item.title}
          </span>
          {item.generated_by_ai && (
            <Badge className="bg-purple-600 text-white text-xs flex items-center gap-1">
              <CpuIcon className="w-3 h-3" />
              IA
            </Badge>
          )}
        </div>
        <Button variant="ghost" size="icon" className="ml-auto" onClick={() => onEdit(item)}>
          <Pencil className="h-4 w-4" />
        </Button>
      </div>
      {hasChildren && !isCollapsed && (
        <div onDragOver={(e) => e.preventDefault()} onDrop={() => onDrop(item)}>
          {item.children?.map((child) => (
            <Item
              key={child.id}
              item={child as TreeNode}
              onEdit={onEdit}
              level={level + 1}
              collapsed={collapsed}
              toggle={toggle}
              onDragStart={onDragStart}
              onDrop={onDrop}
            />
          ))}
        </div>
      )}
    </div>
  );
}

export function ItemTree({ projectId, onEdit }: { projectId: number | null, onEdit: (item: BacklogItem) => void }) {
  const { tree, isLoading, error } = useItems(projectId);
  const [collapsed, setCollapsed] = useState<Set<number>>(new Set());
  const [dragged, setDragged] = useState<TreeNode | null>(null);

  const toggle = (id: number) => {
    setCollapsed(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id); else next.add(id);
      return next;
    });
  };

  const handleDrop = async (parent: TreeNode | null) => {
    if (!dragged) return;
    if (parent && contains(dragged, parent.id)) return;
    const parentType = parent ? parent.type : null;
    if (allowedParent[dragged.type] !== parentType) return;
    try {
      await http(`/items/${dragged.id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ parent_id: parent ? parent.id : null }),
      });
      mutate(`/items?project_id=${projectId}`);
    } catch (err) {
      console.error('Move error', err);
    } finally {
      setDragged(null);
    }
  };

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
    <div
      className="space-y-1 p-2"
      onDragOver={(e) => e.preventDefault()}
      onDrop={() => handleDrop(null)}
    >
      {tree?.map((item) => (
        <Item
          key={item.id}
          item={item}
          onEdit={onEdit}
          collapsed={collapsed}
          toggle={toggle}
          onDragStart={setDragged}
          onDrop={handleDrop}
        />
      ))}
    </div>
  );
}

function contains(node: TreeNode, id: number): boolean {
  if (node.id === id) return true;
  return node.children?.some(child => contains(child as TreeNode, id)) ?? false;
}
