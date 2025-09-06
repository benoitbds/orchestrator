"use client";

import { useState, useEffect } from 'react';
import { ToggleGroup, ToggleGroupItem } from '@/components/ui/toggle-group';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { RefreshCw, Filter, LayoutGrid, List } from 'lucide-react';
import { CompactConversationCard } from './CompactConversationCard';
import { DebugTimelineView } from './DebugTimelineView';
import type { ConversationRun, DisplayMode, EventFilters } from '@/types/events';
import { cn } from '@/lib/utils';

interface ConversationHistoryPanelProps {
  runs: ConversationRun[];
  isLoading?: boolean;
  onRefresh?: () => void;
  className?: string;
}

export function ConversationHistoryPanel({ 
  runs, 
  isLoading = false, 
  onRefresh,
  className 
}: ConversationHistoryPanelProps) {
  const [displayMode, setDisplayMode] = useState<DisplayMode['mode']>('compact');
  const [expandedRuns, setExpandedRuns] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState<EventFilters>({
    types: new Set(['plan', 'tool_call', 'tool_result', 'assistant_answer', 'error']),
    showTokens: false,
    showCosts: false,
  });

  // Persist display mode preference
  useEffect(() => {
    const savedMode = localStorage.getItem('conversation-display-mode') as DisplayMode['mode'];
    if (savedMode && ['compact', 'debug'].includes(savedMode)) {
      setDisplayMode(savedMode);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('conversation-display-mode', displayMode);
  }, [displayMode]);

  const handleExpandRun = (runId: string) => {
    const newExpanded = new Set(expandedRuns);
    if (newExpanded.has(runId)) {
      newExpanded.delete(runId);
    } else {
      newExpanded.add(runId);
    }
    setExpandedRuns(newExpanded);
  };

  const toggleFilter = (type: string) => {
    const newTypes = new Set(filters.types);
    if (newTypes.has(type)) {
      newTypes.delete(type);
    } else {
      newTypes.add(type);
    }
    setFilters({ ...filters, types: newTypes });
  };

  const getFilteredRuns = () => {
    return runs.map(run => ({
      ...run,
      events: run.events.filter(event => 
        filters.types.has(event.event_type)
      ),
    }));
  };

  const filteredRuns = getFilteredRuns();

  if (runs.length === 0 && !isLoading) {
    return (
      <div className={cn("flex flex-col h-full", className)}>
        <div className="p-4 border-b">
          <h2 className="font-semibold">Conversation History</h2>
        </div>
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center text-muted-foreground">
            <LayoutGrid className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No conversations yet</p>
            <p className="text-xs mt-1">Start a conversation to see it here</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="p-4 border-b space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold">Conversation History</h2>
          {onRefresh && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onRefresh}
              disabled={isLoading}
              className="h-8 w-8 p-0"
            >
              <RefreshCw className={cn("h-4 w-4", isLoading && "animate-spin")} />
            </Button>
          )}
        </div>
        
        {/* Display Mode Toggle */}
        <div className="flex items-center justify-between">
          <ToggleGroup
            type="single"
            value={displayMode}
            onValueChange={(value) => value && setDisplayMode(value as DisplayMode['mode'])}
            className="bg-muted/50 p-1 rounded-lg"
            size="sm"
          >
            <ToggleGroupItem value="compact" className="text-xs px-3">
              <LayoutGrid className="h-3 w-3 mr-1" />
              Compact
            </ToggleGroupItem>
            <ToggleGroupItem value="debug" className="text-xs px-3">
              <List className="h-3 w-3 mr-1" />
              Debug
            </ToggleGroupItem>
          </ToggleGroup>
          
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <span>{filteredRuns.length} run{filteredRuns.length !== 1 ? 's' : ''}</span>
          </div>
        </div>

        {/* Filters (Debug mode only) */}
        {displayMode === 'debug' && (
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-xs font-medium text-muted-foreground">
              <Filter className="h-3 w-3" />
              Event Types
            </div>
            <div className="flex flex-wrap gap-1">
              {['plan', 'tool_call', 'tool_result', 'assistant_answer', 'error'].map(type => (
                <Button
                  key={type}
                  variant={filters.types.has(type) ? "default" : "outline"}
                  size="sm"
                  className="h-6 px-2 text-xs"
                  onClick={() => toggleFilter(type)}
                >
                  {type.replace('_', ' ')}
                </Button>
              ))}
            </div>
            
            <div className="flex items-center gap-2">
              <Button
                variant={filters.showTokens ? "default" : "outline"}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setFilters({ ...filters, showTokens: !filters.showTokens })}
              >
                Tokens
              </Button>
              <Button
                variant={filters.showCosts ? "default" : "outline"}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setFilters({ ...filters, showCosts: !filters.showCosts })}
              >
                Costs
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {isLoading && (
          <div className="flex items-center justify-center py-8">
            <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        )}

        {displayMode === 'compact' ? (
          // Compact Mode
          <>
            {filteredRuns.map(run => (
              <CompactConversationCard
                key={run.id}
                run={run}
                onExpand={handleExpandRun}
              />
            ))}
          </>
        ) : (
          // Debug Mode
          <div className="space-y-6">
            {filteredRuns.map(run => (
              <div key={run.id} className="space-y-3">
                {/* Run Header */}
                <div className="flex items-center justify-between p-3 bg-muted/30 rounded-lg">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-sm">Run {run.id.slice(-8)}</span>
                      <Badge variant="outline" className="text-xs">
                        {run.events.length} events
                      </Badge>
                      <Badge 
                        variant={run.status === 'completed' ? 'default' : 
                                run.status === 'error' ? 'destructive' : 'secondary'}
                        className="text-xs"
                      >
                        {run.status}
                      </Badge>
                    </div>
                    <div className="text-xs text-muted-foreground">
                      {run.objective}
                    </div>
                  </div>
                  <div className="text-xs text-muted-foreground">
                    {new Date(run.created_at).toLocaleString()}
                  </div>
                </div>
                
                {/* Timeline */}
                <DebugTimelineView
                  events={run.events}
                  runId={run.id}
                  showFilters={false}
                />
              </div>
            ))}
          </div>
        )}

        {filteredRuns.length === 0 && !isLoading && runs.length > 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <Filter className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No events match the current filters</p>
            <p className="text-xs mt-1">Try adjusting your filter settings</p>
          </div>
        )}
      </div>
    </div>
  );
}