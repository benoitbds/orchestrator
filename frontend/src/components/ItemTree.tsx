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

function Item({ item, onEdit, level = 0 }: { item: TreeNode, onEdit: (item: BacklogItem) => void, level?: number }) {
  // Construction du tooltip avec infos SAFe
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
    <div>
      <div 
        className={`flex items-center gap-2 p-2 rounded-md hover:bg-gray-100 cursor-pointer`} 
        style={{ paddingLeft: `${level * 20 + 8}px` }}
        title={getTooltipContent()}
      >
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
