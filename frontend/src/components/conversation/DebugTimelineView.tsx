"use client";

import { useState } from 'react';
import { 
  ChevronDown, 
  ChevronRight, 
  Settings, 
  MessageSquare, 
  CheckCircle, 
  AlertCircle, 
  Copy,
  Zap
} from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import type { RunEvent, TokenUsage } from '@/types/events';

interface DebugTimelineViewProps {
  events: RunEvent[];
  runId: string;
  showFilters?: boolean;
}

export function DebugTimelineView({ events, runId, showFilters = false }: DebugTimelineViewProps) {
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());
  const [filters, setFilters] = useState({
    plan: true,
    tool_call: true,
    tool_result: true,
    assistant_answer: true,
    error: true,
    status_update: false,
  });

  const handleCopy = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      toast.success('Copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy');
    }
  };

  const toggleExpanded = (eventId: string) => {
    const newExpanded = new Set(expandedEvents);
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId);
    } else {
      newExpanded.add(eventId);
    }
    setExpandedEvents(newExpanded);
  };

  const formatTokens = (tokens: TokenUsage) => {
    const parts = [];
    if (tokens.prompt_tokens) parts.push(`${tokens.prompt_tokens} in`);
    if (tokens.completion_tokens) parts.push(`${tokens.completion_tokens} out`);
    if (tokens.total_tokens && !tokens.prompt_tokens && !tokens.completion_tokens) {
      parts.push(`${tokens.total_tokens} total`);
    }
    return parts.join(' • ');
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const getEventIcon = (eventType: string) => {
    switch (eventType) {
      case 'plan':
        return <MessageSquare className="h-4 w-4 text-blue-500" />;
      case 'tool_call':
        return <Settings className="h-4 w-4 text-indigo-500" />;
      case 'tool_result':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'assistant_answer':
        return <MessageSquare className="h-4 w-4 text-purple-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      case 'status_update':
        return <Zap className="h-4 w-4 text-yellow-500" />;
      default:
        return <MessageSquare className="h-4 w-4 text-gray-500" />;
    }
  };

  const getEventColor = (eventType: string) => {
    switch (eventType) {
      case 'plan':
        return 'bg-blue-50 dark:bg-blue-950/20 border-blue-200 dark:border-blue-800';
      case 'tool_call':
        return 'bg-indigo-50 dark:bg-indigo-950/20 border-indigo-200 dark:border-indigo-800';
      case 'tool_result':
        return 'bg-green-50 dark:bg-green-950/20 border-green-200 dark:border-green-800';
      case 'assistant_answer':
        return 'bg-purple-50 dark:bg-purple-950/20 border-purple-200 dark:border-purple-800';
      case 'error':
        return 'bg-red-50 dark:bg-red-950/20 border-red-200 dark:border-red-800';
      case 'status_update':
        return 'bg-yellow-50 dark:bg-yellow-950/20 border-yellow-200 dark:border-yellow-800';
      default:
        return 'bg-gray-50 dark:bg-gray-950/20 border-gray-200 dark:border-gray-800';
    }
  };

  // Filter events
  const filteredEvents = events.filter(event => 
    filters[event.event_type as keyof typeof filters] !== false
  );

  // Sort by sequence
  const sortedEvents = [...filteredEvents].sort((a, b) => a.seq - b.seq);

  if (sortedEvents.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <MessageSquare className="h-8 w-8 mx-auto mb-2 opacity-50" />
        <p className="text-sm">No events to display</p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {/* Filters */}
      {showFilters && (
        <div className="flex flex-wrap gap-2 p-3 bg-muted/30 rounded-lg">
          {Object.entries(filters).map(([type, enabled]) => (
            <Button
              key={type}
              variant={enabled ? "default" : "outline"}
              size="sm"
              className="h-7 px-2 text-xs"
              onClick={() => setFilters(prev => ({ ...prev, [type]: !prev[type as keyof typeof prev] }))}
            >
              {type.replace('_', ' ')}
            </Button>
          ))}
        </div>
      )}

      {/* Timeline */}
      <div className="space-y-3">
        {sortedEvents.map((event, index) => {
          const isExpanded = expandedEvents.has(`${runId}-${event.seq}`);
          const eventId = `${runId}-${event.seq}`;
          
          return (
            <Card key={eventId} className={cn("relative", getEventColor(event.event_type))}>
              {/* Timeline line */}
              {index < sortedEvents.length - 1 && (
                <div className="absolute left-6 top-12 w-0.5 h-6 bg-border" />
              )}
              
              <div className="p-4">
                {/* Header */}
                <div className="flex items-center gap-3">
                  <div className="flex-shrink-0">
                    {getEventIcon(event.event_type)}
                  </div>
                  
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Badge variant="secondary" className="text-xs">
                        {event.event_type.replace('_', ' ')}
                      </Badge>
                      
                      {event.event_type === 'tool_call' && event.data?.tool_name && (
                        <Badge variant="outline" className="text-xs">
                          {event.data.tool_name}
                        </Badge>
                      )}
                      
                      {event.elapsed_ms && (
                        <Badge variant="outline" className="text-xs">
                          {formatDuration(event.elapsed_ms)}
                        </Badge>
                      )}
                      
                      {event.model && (
                        <Badge variant="outline" className="text-xs">
                          {event.model}
                        </Badge>
                      )}
                    </div>
                    
                    {/* Tokens */}
                    {(event.prompt_tokens || event.completion_tokens || event.total_tokens) && (
                      <div className="mt-1 text-xs text-muted-foreground">
                        {formatTokens({
                          prompt_tokens: event.prompt_tokens,
                          completion_tokens: event.completion_tokens,
                          total_tokens: event.total_tokens,
                          cost_eur: event.cost_eur,
                        })}
                        {event.cost_eur && ` • €${event.cost_eur.toFixed(4)}`}
                      </div>
                    )}
                  </div>
                  
                  <div className="flex items-center gap-2 text-xs text-muted-foreground">
                    <span>{new Date(event.ts).toLocaleTimeString()}</span>
                    
                    {/* Expand button for events with data */}
                    {event.data && Object.keys(event.data).length > 0 && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleExpanded(eventId)}
                        className="h-6 w-6 p-0"
                      >
                        {isExpanded ? (
                          <ChevronDown className="h-3 w-3" />
                        ) : (
                          <ChevronRight className="h-3 w-3" />
                        )}
                      </Button>
                    )}
                  </div>
                </div>
                
                {/* Event Content */}
                {event.data && (
                  <div className="mt-3">
                    {/* Quick preview for some event types */}
                    {event.event_type === 'assistant_answer' && event.data.content && (
                      <div className="text-sm bg-background/60 p-3 rounded border">
                        {event.data.content}
                      </div>
                    )}
                    
                    {event.event_type === 'tool_result' && event.data.result && (
                      <div className="text-sm bg-background/60 p-3 rounded border">
                        {typeof event.data.result === 'string' 
                          ? event.data.result 
                          : `${Object.keys(event.data.result).length} result(s)`}
                      </div>
                    )}
                    
                    {/* Expanded JSON details */}
                    {isExpanded && (
                      <div className="mt-3 space-y-2">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-medium text-muted-foreground">Event Data</span>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => handleCopy(JSON.stringify(event.data, null, 2))}
                            className="h-6 w-6 p-0"
                          >
                            <Copy className="h-3 w-3" />
                          </Button>
                        </div>
                        <pre className="text-xs bg-background p-3 rounded border overflow-x-auto max-h-48 overflow-y-auto">
                          {JSON.stringify(event.data, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </Card>
          );
        })}
      </div>
    </div>
  );
}