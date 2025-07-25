"use client";
import { useState, useMemo } from 'react';
import { BacklogItem, isEpic, isCapability, isFeature, isUS, isUC } from '@/models/backlogItem';
import { useItems } from '@/lib/hooks';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import dynamic from 'next/dynamic';

const Loader2 = dynamic(() => import('lucide-react').then(mod => ({ default: mod.Loader2 })), { ssr: false });
const ArrowUpDown = dynamic(() => import('lucide-react').then(mod => ({ default: mod.ArrowUpDown })), { ssr: false });
const ArrowUp = dynamic(() => import('lucide-react').then(mod => ({ default: mod.ArrowUp })), { ssr: false });
const ArrowDown = dynamic(() => import('lucide-react').then(mod => ({ default: mod.ArrowDown })), { ssr: false });

const typeColors: { [key: string]: string } = {
  Epic: 'bg-purple-500',
  Capability: 'bg-purple-400',
  Feature: 'bg-blue-500',
  US: 'bg-green-500',
  UC: 'bg-yellow-500',
};

const stateColors: { [key: string]: string } = {
  Funnel: 'bg-gray-400',
  Reviewing: 'bg-orange-400',
  Analyzing: 'bg-yellow-500',
  Backlog: 'bg-blue-400',
  Implementing: 'bg-indigo-500',
  Done: 'bg-green-500',
};

const statusColors: { [key: string]: string } = {
  Todo: 'bg-gray-400',
  Doing: 'bg-yellow-500',
  Done: 'bg-green-500',
};

type SortField = 'title' | 'type' | 'wsjf' | 'story_points' | 'program_increment';
type SortDirection = 'asc' | 'desc' | null;

interface BacklogTableProps {
  projectId: number | null;
  onEdit: (item: BacklogItem) => void;
}

export function BacklogTable({ projectId, onEdit }: BacklogTableProps) {
  const { data: items, isLoading, error } = useItems(projectId);
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('wsjf');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');

  // Flatten tree data pour la table
  const flatItems = useMemo(() => {
    if (!items) return [];
    return items;
  }, [items]);

  // Filtrage et tri
  const processedItems = useMemo(() => {
    let filtered = flatItems;

    // Filtre par recherche
    if (searchTerm) {
      filtered = filtered.filter(item =>
        item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Filtre par type
    if (typeFilter !== 'all') {
      filtered = filtered.filter(item => item.type === typeFilter);
    }

    // Tri
    if (sortField && sortDirection) {
      filtered = [...filtered].sort((a, b) => {
        let aValue: any = '';
        let bValue: any = '';

        switch (sortField) {
          case 'title':
            aValue = a.title;
            bValue = b.title;
            break;
          case 'type':
            aValue = a.type;
            bValue = b.type;
            break;
          case 'wsjf':
            aValue = (isEpic(a) || isCapability(a) || isFeature(a)) ? (a.wsjf || 0) : 0;
            bValue = (isEpic(b) || isCapability(b) || isFeature(b)) ? (b.wsjf || 0) : 0;
            break;
          case 'story_points':
            aValue = (isUS(a) || isUC(a)) ? (a.story_points || 0) : 0;
            bValue = (isUS(b) || isUC(b)) ? (b.story_points || 0) : 0;
            break;
          case 'program_increment':
            aValue = isFeature(a) ? (a.program_increment || '') : '';
            bValue = isFeature(b) ? (b.program_increment || '') : '';
            break;
        }

        if (typeof aValue === 'string') {
          return sortDirection === 'asc' 
            ? aValue.localeCompare(bValue)
            : bValue.localeCompare(aValue);
        } else {
          return sortDirection === 'asc' ? aValue - bValue : bValue - aValue;
        }
      });
    }

    return filtered;
  }, [flatItems, searchTerm, typeFilter, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(
        sortDirection === 'asc' ? 'desc' : sortDirection === 'desc' ? null : 'asc'
      );
      if (sortDirection === 'desc') {
        setSortField('title'); // Reset to default
      }
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const getSortIcon = (field: SortField) => {
    if (sortField !== field) return <ArrowUpDown className="h-4 w-4" />;
    if (sortDirection === 'asc') return <ArrowUp className="h-4 w-4" />;
    if (sortDirection === 'desc') return <ArrowDown className="h-4 w-4" />;
    return <ArrowUpDown className="h-4 w-4" />;
  };

  const getBadgeColor = (item: BacklogItem) => {
    // Toujours utiliser la couleur du type
    return typeColors[item.type] || 'bg-gray-500';
  };

  const getStateBadgeColor = (item: BacklogItem) => {
    if ((isEpic(item) || isCapability(item)) && item.state) {
      return stateColors[item.state] || 'bg-gray-400';
    }
    if ((isUS(item) || isUC(item)) && item.status) {
      return statusColors[item.status] || 'bg-gray-400';
    }
    return 'bg-gray-400';
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <Loader2 className="animate-spin" />
        <span className="ml-2">Chargement...</span>
      </div>
    );
  }

  if (error) {
    return <div className="text-red-500">Erreur de chargement des éléments.</div>;
  }

  return (
    <div className="space-y-4">
      {/* Filtres et recherche */}
      <div className="flex gap-4 items-center">
        <Input
          placeholder="Rechercher..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="max-w-sm"
        />
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous les types</SelectItem>
            <SelectItem value="Epic">Epic</SelectItem>
            <SelectItem value="Capability">Capability</SelectItem>
            <SelectItem value="Feature">Feature</SelectItem>
            <SelectItem value="US">US</SelectItem>
            <SelectItem value="UC">UC</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left">
                <Button
                  variant="ghost"
                  onClick={() => handleSort('type')}
                  className="font-semibold"
                >
                  Type {getSortIcon('type')}
                </Button>
              </th>
              <th className="px-4 py-3 text-left">
                <Button
                  variant="ghost"
                  onClick={() => handleSort('title')}
                  className="font-semibold"
                >
                  Titre {getSortIcon('title')}
                </Button>
              </th>
              <th className="px-4 py-3 text-left">
                <Button
                  variant="ghost"
                  onClick={() => handleSort('wsjf')}
                  className="font-semibold"
                >
                  WSJF {getSortIcon('wsjf')}
                </Button>
              </th>
              <th className="px-4 py-3 text-left">
                <Button
                  variant="ghost"
                  onClick={() => handleSort('story_points')}
                  className="font-semibold"
                >
                  Points {getSortIcon('story_points')}
                </Button>
              </th>
              <th className="px-4 py-3 text-left">
                <Button
                  variant="ghost"
                  onClick={() => handleSort('program_increment')}
                  className="font-semibold"
                >
                  PI {getSortIcon('program_increment')}
                </Button>
              </th>
              <th className="px-4 py-3 text-left">Détails</th>
              <th className="px-4 py-3"></th>
            </tr>
          </thead>
          <tbody>
            {processedItems.map((item) => (
              <tr
                key={item.id}
                className="border-t hover:bg-gray-50 cursor-pointer"
                onClick={() => onEdit(item)}
              >
                <td className="px-4 py-3">
                  <Badge className={`${getBadgeColor(item)} text-white`}>
                    {item.type}
                  </Badge>
                </td>
                <td className="px-4 py-3">
                  <div>
                    <div className="font-medium">{item.title}</div>
                    {item.description && (
                      <div className="text-sm text-gray-500 truncate max-w-xs">
                        {item.description}
                      </div>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  {(isEpic(item) || isCapability(item) || isFeature(item)) && item.wsjf ? (
                    <Badge variant="outline">{item.wsjf}</Badge>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {(isUS(item) || isUC(item)) && item.story_points ? (
                    <Badge variant="outline">{item.story_points}pts</Badge>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {isFeature(item) && item.program_increment ? (
                    <Badge variant="outline">{item.program_increment}</Badge>
                  ) : (
                    <span className="text-gray-400">-</span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-1 flex-wrap">
                    {(isEpic(item) || isCapability(item)) && item.state && (
                      <Badge variant="secondary" className="text-xs">
                        {item.state}
                      </Badge>
                    )}
                    {(isUS(item) || isUC(item)) && item.status && (
                      <Badge variant="secondary" className="text-xs">
                        {item.status}
                      </Badge>
                    )}
                    {(isUS(item) || isUC(item)) && item.iteration && (
                      <Badge variant="secondary" className="text-xs">
                        {item.iteration}
                      </Badge>
                    )}
                    {isFeature(item) && item.owner && (
                      <Badge variant="secondary" className="text-xs">
                        {item.owner}
                      </Badge>
                    )}
                  </div>
                </td>
                <td className="px-4 py-3">
                  <Button variant="ghost" size="sm" onClick={(e) => {
                    e.stopPropagation();
                    onEdit(item);
                  }}>
                    Modifier
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {processedItems.length === 0 && (
        <div className="text-center py-8 text-gray-500">
          Aucun élément trouvé
        </div>
      )}
    </div>
  );
}