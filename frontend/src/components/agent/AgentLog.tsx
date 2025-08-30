"use client";

import { useState, useMemo } from 'react';
import { Copy, ChevronDown, ChevronRight, Clock, CheckCircle, AlertCircle, Settings } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { useRunsStore, type AgentEvent } from '@/stores/useRunsStore';
import { cn } from '@/lib/utils';

type EventFilter = 'all' | 'tools' | 'write' | 'errors';

interface EventWithMeta extends AgentEvent {
  runId: string;
  duration?: number;
}

interface AgentLogProps {
  className?: string;
  compact?: boolean;
}

export function AgentLog({ className, compact = false }: AgentLogProps) {
  const [filter, setFilter] = useState<EventFilter>('all');
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [expandedRuns, setExpandedRuns] = useState<Set<string>>(new Set());

  const { runs, currentRunId } = useRunsStore();

  const filteredEvents = useMemo(() => {
    const allEvents: EventWithMeta[] = [];
    
    Object.entries(runs).forEach(([runId, run]) => {
      // Calculate durations for tool calls
      const toolCallDurations = new Map<string, number>();
      
      run.events.forEach((event, index) => {
        if (event.node.includes(':request')) {
          const toolName = event.node.split(':')[1];
          const requestTime = new Date(event.ts || '').getTime();
          
          // Find corresponding response
          const responseEvent = run.events.slice(index + 1).find(e => 
            e.node.includes(':response') && e.node.split(':')[1] === toolName
          );
          
          if (responseEvent) {
            const responseTime = new Date(responseEvent.ts || '').getTime();
            toolCallDurations.set(event.node, responseTime - requestTime);
          }
        }
      });
      
      run.events.forEach(event => {
        const eventWithMeta: EventWithMeta = {
          ...event,
          runId,
          duration: toolCallDurations.get(event.node),
        };
        
        // Apply filter
        switch (filter) {
          case 'tools':
            if (event.node.startsWith('tool:')) allEvents.push(eventWithMeta);
            break;
          case 'write':
            if (event.node === 'write') allEvents.push(eventWithMeta);
            break;
          case 'errors':
            if (event.error || event.ok === false) allEvents.push(eventWithMeta);
            break;
          default:
            allEvents.push(eventWithMeta);
        }
      });
    });
    
    return allEvents.sort((a, b) => 
      new Date(b.ts || '').getTime() - new Date(a.ts || '').getTime()
    );
  }, [runs, filter]);

  const handleCopyEvent = async (event: EventWithMeta) => {
    try {
      const eventData = {
        node: event.node,
        timestamp: event.ts,
        args: event.args,
        result: event.result,
        error: event.error,
        duration: event.duration,
      };
      
      await navigator.clipboard.writeText(JSON.stringify(eventData, null, 2));
      toast.success('Event copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy event');
    }
  };

  const toggleEventExpanded = (eventId: string) => {
    const newExpanded = new Set(expandedEvents);
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId);
    } else {
      newExpanded.add(eventId);
    }
    setExpandedEvents(newExpanded);
  };

  const toggleRunExpanded = (runId: string) => {
    const newExpanded = new Set(expandedRuns);
    if (newExpanded.has(runId)) {
      newExpanded.delete(runId);
    } else {
      newExpanded.add(runId);
    }
    setExpandedRuns(newExpanded);
  };

  const getEventIcon = (event: AgentEvent) => {
    if (event.error || event.ok === false) return AlertCircle;
    if (event.node === 'write') return CheckCircle;
    if (event.node.startsWith('tool:')) return Settings;
    return Clock;
  };

  const getEventColor = (event: AgentEvent) => {
    if (event.error || event.ok === false) return 'text-red-500';
    if (event.node === 'write') return 'text-green-500';
    if (event.node.startsWith('tool:')) return 'text-indigo-500';
    return 'text-amber-500';
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatEventContent = (event: AgentEvent) => {
    if (event.args && Object.keys(event.args).length > 0) {
      return JSON.stringify(event.args, null, 2);
    }
    if (event.result && typeof event.result === 'object') {
      return JSON.stringify(event.result, null, 2);
    }
    if (event.content) {
      return typeof event.content === 'string' ? event.content : JSON.stringify(event.content, null, 2);
    }
    if (event.error) {
      return event.error;
    }
    return '';
  };

  const groupedByRun = useMemo(() => {
    const groups: Record<string, EventWithMeta[]> = {};
    filteredEvents.forEach(event => {
      if (!groups[event.runId]) {
        groups[event.runId] = [];
      }
      groups[event.runId].push(event);
    });
    return groups;
  }, [filteredEvents]);

  return (
    <div className={cn("flex flex-col h-full", className)}>
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h3 className="font-semibold">Agent Log</h3>
          <Badge variant="secondary">
            {filteredEvents.length} events
          </Badge>
        </div>
        
        {/* Filters */}
        <div className="flex gap-1 flex-wrap">
          {(['all', 'tools', 'write', 'errors'] as EventFilter[]).map((filterType) => (
            <Button
              key={filterType}
              variant={filter === filterType ? "default" : "outline"}
              size="sm"
              onClick={() => setFilter(filterType)}
              className="capitalize"
            >
              {filterType}
            </Button>
          ))}
        </div>
      </div>

      {/* Events List */}
      <div className="flex-1 overflow-y-auto">
        {Object.keys(groupedByRun).length === 0 ? (
          <div className="p-8 text-center text-muted-foreground">
            <Settings className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <h4 className="font-medium mb-2">No events yet</h4>
            <p className="text-sm">Agent events will appear here when you start a conversation.</p>
          </div>
        ) : (
          <div className="p-4 space-y-4">
            {Object.entries(groupedByRun).map(([runId, events]) => {
              const run = runs[runId];
              const isCurrentRun = currentRunId === runId;
              const isRunExpanded = isCurrentRun || expandedRuns.has(runId);
              
              return (
                <Card key={runId} className="overflow-hidden">
                  {/* Run Header */}
                  <div 
                    className="p-3 bg-muted/50 flex items-center justify-between cursor-pointer hover:bg-muted/70 transition-colors"
                    onClick={() => toggleRunExpanded(runId)}
                  >
                    <div className="flex items-center gap-2">
                      {isRunExpanded ? (
                        <ChevronDown className="h-4 w-4" />
                      ) : (
                        <ChevronRight className="h-4 w-4" />
                      )}
                      <span className="font-medium text-sm">
                        Run {runId.slice(-8)}
                      </span>
                      {isCurrentRun && (
                        <Badge variant="secondary" className="text-xs">
                          Current
                        </Badge>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <span>{events.length} events</span>
                      {run && (
                        <Badge 
                          variant={run.status === 'completed' ? 'default' : run.status === 'failed' ? 'destructive' : 'secondary'}
                          className="text-xs"
                        >
                          {run.status}
                        </Badge>
                      )}
                    </div>
                  </div>
                  
                  {/* Run Events */}
                  {isRunExpanded && (
                    <div className="divide-y">
                      {events.map((event, index) => {
                        const eventId = `${runId}-${index}`;
                        const isExpanded = expandedEvents.has(eventId);
                        const Icon = getEventIcon(event);
                        const content = formatEventContent(event);
                        
                        return (
                          <div key={eventId} className="p-3">
                            <div className="flex items-start gap-3">
                              <Icon className={cn("h-4 w-4 mt-0.5 flex-shrink-0", getEventColor(event))} />
                              
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center justify-between">
                                  <div className="flex items-center gap-2">
                                    <span className="text-sm font-medium">
                                      {event.node}
                                    </span>
                                    {event.duration && (
                                      <Badge variant="outline" className="text-xs">
                                        {formatDuration(event.duration)}
                                      </Badge>
                                    )}
                                  </div>
                                  
                                  <div className="flex items-center gap-1">
                                    <span className="text-xs text-muted-foreground">
                                      {event.ts ? new Date(event.ts).toLocaleTimeString() : ''}
                                    </span>
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => handleCopyEvent(event)}
                                      className="h-6 w-6 p-0"
                                    >
                                      <Copy className="h-3 w-3" />
                                    </Button>
                                  </div>
                                </div>
                                
                                {content && (
                                  <div className="mt-2">
                                    <Button
                                      variant="ghost"
                                      size="sm"
                                      onClick={() => toggleEventExpanded(eventId)}
                                      className="h-6 px-2 text-xs"
                                    >
                                      {isExpanded ? 'Hide' : 'Show'} details
                                      {isExpanded ? (
                                        <ChevronDown className="h-3 w-3 ml-1" />
                                      ) : (
                                        <ChevronRight className="h-3 w-3 ml-1" />
                                      )}
                                    </Button>
                                    
                                    {isExpanded && (
                                      <pre className="text-xs bg-muted p-2 rounded mt-2 overflow-x-auto">
                                        {content}
                                      </pre>
                                    )}
                                  </div>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}