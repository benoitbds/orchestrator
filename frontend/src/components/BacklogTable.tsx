"use client";
import { useState, useMemo, useEffect } from 'react';
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
const CpuIcon = dynamic(() => import('lucide-react').then(mod => ({ default: mod.Cpu })), { ssr: false });
import clsx from 'clsx';
import { toast } from 'sonner';
import { validateItem, validateItems } from '@/lib/api';

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
  const [reviewFilter, setReviewFilter] = useState<'all' | 'pending' | 'approved'>('all');
  const { data: items, isLoading, error, mutate } = useItems(projectId, { review: reviewFilter });
  const [searchTerm, setSearchTerm] = useState('');
  const [typeFilter, setTypeFilter] = useState<string>('all');
  const [sortField, setSortField] = useState<SortField>('wsjf');
  const [sortDirection, setSortDirection] = useState<SortDirection>('desc');
  const [selectedIds, setSelectedIds] = useState<number[]>([]);
  const [validatingId, setValidatingId] = useState<number | null>(null);
  const [bulkValidating, setBulkValidating] = useState(false);

  // Flatten tree data pour la table
  const flatItems = useMemo(() => {
    if (!items) return [];
    return items;
  }, [items]);

  const processedItems = useMemo(() => {
    let filtered = flatItems;

    if (searchTerm) {
      filtered = filtered.filter(item =>
        item.title.toLowerCase().includes(searchTerm.toLowerCase()) ||
        item.description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    if (typeFilter !== 'all') {
      filtered = filtered.filter(item => item.type === typeFilter);
    }

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

  const isPending = (item: BacklogItem) => {
    if (item.ia_review_status) {
      return item.ia_review_status === 'pending';
    }
    return !!item.generated_by_ai;
  };

  const selectableIds = useMemo(
    () => processedItems.filter(isPending).map((item) => item.id),
    [processedItems]
  );

  useEffect(() => {
    setSelectedIds((prev) => prev.filter((id) => selectableIds.includes(id)));
  }, [selectableIds]);

  useEffect(() => {
    setSelectedIds([]);
  }, [reviewFilter, projectId]);

  const allSelected = selectableIds.length > 0 && selectableIds.every((id) => selectedIds.includes(id));

  const toggleSelectAll = (checked: boolean) => {
    if (checked) {
      setSelectedIds(selectableIds);
    } else {
      setSelectedIds([]);
    }
  };

  const toggleSelect = (id: number, checked: boolean) => {
    setSelectedIds((prev) => {
      if (checked) {
        return prev.includes(id) ? prev : [...prev, id];
      }
      return prev.filter((value) => value !== id);
    });
  };

  const handleValidateSingle = async (event: React.MouseEvent, id: number) => {
    event.stopPropagation();
    try {
      setValidatingId(id);
      await validateItem(id);
      await mutate();
      setSelectedIds((prev) => prev.filter((value) => value !== id));
      toast.success('Item validé');
    } catch (err) {
      toast.error('Validation impossible');
    } finally {
      setValidatingId(null);
    }
  };

  const handleBulkValidate = async () => {
    if (!selectedIds.length) return;
    try {
      setBulkValidating(true);
      await validateItems(selectedIds);
      await mutate();
      setSelectedIds([]);
      toast.success('Éléments validés');
    } catch (err) {
      toast.error('Impossible de valider la sélection');
    } finally {
      setBulkValidating(false);
    }
  };

  // Filtrage et tri
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
        <Select value={reviewFilter} onValueChange={(value: string) => setReviewFilter(value as 'all' | 'pending' | 'approved')}>
          <SelectTrigger className="w-44">
            <SelectValue placeholder="Filtrer" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tous</SelectItem>
            <SelectItem value="pending">À valider (IA)</SelectItem>
            <SelectItem value="approved">Validés</SelectItem>
          </SelectContent>
        </Select>
        <Button
          variant="outline"
          disabled={!selectedIds.length || bulkValidating}
          onClick={handleBulkValidate}
        >
          {bulkValidating ? 'Validation…' : `Valider la sélection (${selectedIds.length})`}
        </Button>
      </div>

      {/* Table */}
      <div className="border rounded-lg overflow-hidden">
        <table className="w-full">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 w-10">
                <input
                  type="checkbox"
                  className="h-4 w-4"
                  checked={allSelected && selectableIds.length > 0}
                  disabled={!selectableIds.length}
                  onChange={(e) => toggleSelectAll(e.target.checked)}
                  aria-label="Sélectionner tout"
                />
              </th>
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
            {processedItems.map((item) => {
              const pending = isPending(item);
              const iaFields = item.ia_fields || [];
              const titleHighlighted = pending && iaFields.includes('title');
              const descriptionHighlighted = pending && iaFields.includes('description');
              const titleClasses = clsx(
                'font-medium cursor-pointer',
                pending && 'bg-amber-100 px-1 rounded'
              );
              const descriptionClasses = clsx(
                'text-sm text-gray-500 truncate max-w-xs',
                pending && 'bg-amber-50 px-1 rounded'
              );

              return (
                <tr
                  key={item.id}
                  className="border-t hover:bg-gray-50 cursor-pointer"
                  onClick={() => onEdit(item)}
                  data-item-id={item.id}
                >
                  <td
                    className="px-4 py-3"
                    onClick={(e) => e.stopPropagation()}
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4"
                      disabled={!pending}
                      checked={selectedIds.includes(item.id)}
                      onChange={(e) => toggleSelect(item.id, e.target.checked)}
                      aria-label={`Sélectionner ${item.title}`}
                    />
                  </td>
                  <td className="px-4 py-3">
                    <Badge className={`${getBadgeColor(item)} text-white`}>
                      {item.type}
                    </Badge>
                  </td>
                  <td className="px-4 py-3">
                    <div>
                      <div className="flex items-center gap-2">
                        <span
                          className={titleClasses}
                          onClick={(e) => {
                            e.stopPropagation();
                            onEdit(item);
                          }}
                        >
                          {item.title}
                        </span>
                        {pending && (
                          <Badge className="bg-purple-600 text-white text-xs flex items-center gap-1">
                            <CpuIcon className="w-3 h-3" />
                            IA
                          </Badge>
                        )}
                      </div>
                      {item.description && (
                        <div className={descriptionClasses}>{item.description}</div>
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
                    <div className="flex gap-2">
                      {pending && (
                        <Button
                          variant="outline"
                          size="sm"
                          onClick={(e) => handleValidateSingle(e, item.id)}
                          disabled={validatingId === item.id}
                        >
                          {validatingId === item.id ? 'Validation…' : 'Valider'}
                        </Button>
                      )}
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          onEdit(item);
                        }}
                      >
                        Modifier
                      </Button>
                    </div>
                  </td>
                </tr>
              );
            })}
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
