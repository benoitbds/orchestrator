"use client";
import { ItemSummary } from '@/types/agent-execution';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';

const Sparkles = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Sparkles })),
  { ssr: false }
);

interface ItemCreatedDisplayProps {
  item: ItemSummary;
}

export function ItemCreatedDisplay({ item }: ItemCreatedDisplayProps) {
  const getTypeColor = (type: string) => {
    switch (type) {
      case 'Epic':
        return 'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200';
      case 'Feature':
        return 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200';
      case 'US':
        return 'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200';
      case 'UC':
        return 'bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200';
      default:
        return 'bg-gray-100 text-gray-800 dark:bg-gray-900 dark:text-gray-200';
    }
  };

  const getPriorityColor = (priority?: string) => {
    switch (priority) {
      case 'Critical':
      case 'Critique':
        return 'text-red-600 dark:text-red-400';
      case 'High':
      case 'Haute':
        return 'text-orange-600 dark:text-orange-400';
      case 'Medium':
      case 'Moyenne':
        return 'text-yellow-600 dark:text-yellow-400';
      default:
        return 'text-gray-600 dark:text-gray-400';
    }
  };

  return (
    <div className={cn(
      "space-y-1 animate-in",
      item.animation_hint === 'slide-in' ? 'slide-in-from-left' : 'fade-in',
      "duration-500"
    )}>
      <div className="flex items-start gap-2 text-sm">
        <Sparkles className="h-4 w-4 mt-0.5 text-green-500" />
        <div className="flex-1 space-y-1">
          <div className="font-medium">Item Created</div>
          
          <div className="pl-4 space-y-1 text-xs">
            <div className="flex items-start gap-1">
              <span className="select-none text-muted-foreground">⎿</span>
              <div className="flex-1 space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-green-600 dark:text-green-400">✓</span>
                  <Badge variant="outline" className={cn("text-xs", getTypeColor(item.type))}>
                    {item.type}
                  </Badge>
                  <span className="font-medium">{item.title}</span>
                  <span className="text-muted-foreground">(ID: {item.id})</span>
                </div>
                
                <div className="flex items-center gap-3 flex-wrap text-muted-foreground">
                  {item.priority && (
                    <div className="flex items-center gap-1">
                      <span>Priority:</span>
                      <span className={getPriorityColor(item.priority)}>{item.priority}</span>
                    </div>
                  )}
                  {item.business_value !== undefined && (
                    <div className="flex items-center gap-1">
                      <span>Business Value:</span>
                      <span className="font-medium">{item.business_value}/10</span>
                    </div>
                  )}
                  {item.parent_title && (
                    <div className="flex items-center gap-1">
                      <span>Parent:</span>
                      <span className="italic">{item.parent_title}</span>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
