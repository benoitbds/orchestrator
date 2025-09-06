"use client";

import { useState } from 'react';
import { ChevronDown, ChevronRight, Clock, Settings, AlertCircle, CheckCircle } from 'lucide-react';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import type { ConversationRun, CompactViewData } from '@/types/events';
import { DebugTimelineView } from './DebugTimelineView';

interface CompactConversationCardProps {
  run: ConversationRun;
  onExpand?: (runId: string) => void;
}

export function CompactConversationCard({ run, onExpand }: CompactConversationCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  // Extract compact view data from events
  const compactData: CompactViewData = {
    objective: run.objective,
    answer: extractAnswer(run.events),
    toolCount: run.events.filter(e => e.event_type === 'tool_call').length,
    duration: extractDuration(run.events),
    status: run.status,
  };

  const handleToggleExpand = () => {
    if (!isExpanded && onExpand) {
      onExpand(run.id);
    }
    setIsExpanded(!isExpanded);
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
    return `${Math.floor(ms / 60000)}m ${Math.floor((ms % 60000) / 1000)}s`;
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'running':
        return <Clock className="h-4 w-4 text-blue-500 animate-spin" />;
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <Card className="w-full">
      <div className="p-4">
        {/* Compact View */}
        <div className="space-y-3">
          {/* Header with status */}
          <div className="flex items-start justify-between">
            <div className="flex-1 pr-4">
              <div className="flex items-center gap-2 mb-2">
                <span className="font-medium text-sm">You</span>
                <span className="text-xs text-muted-foreground">
                  {new Date(run.created_at).toLocaleString()}
                </span>
                {getStatusIcon(compactData.status)}
              </div>
              <div className="text-sm bg-muted/50 p-3 rounded-md">
                {compactData.objective}
              </div>
            </div>
          </div>

          {/* Answer */}
          {compactData.answer && (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">Agent</span>
              </div>
              <div className="text-sm bg-primary/5 p-3 rounded-md border border-primary/10">
                {compactData.answer}
              </div>
            </div>
          )}

          {/* Actions Summary */}
          <div className="flex items-center justify-between">
            <div 
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-full bg-muted/50 cursor-pointer hover:bg-muted/70 transition-colors",
                isExpanded && "bg-muted/70"
              )}
              onClick={handleToggleExpand}
            >
              <Settings className="h-3 w-3 text-muted-foreground" />
              <span className="text-xs font-medium">
                Actions: {compactData.toolCount} tool{compactData.toolCount !== 1 ? 's' : ''}
              </span>
              <span className="text-xs text-muted-foreground">•</span>
              <span className="text-xs text-muted-foreground">
                {formatDuration(compactData.duration)}
              </span>
              {isExpanded ? (
                <ChevronDown className="h-3 w-3 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-3 w-3 text-muted-foreground" />
              )}
            </div>
            
            <Badge 
              variant={compactData.status === 'completed' ? 'default' : 
                      compactData.status === 'error' ? 'destructive' : 'secondary'}
              className="text-xs"
            >
              {compactData.status}
            </Badge>
          </div>
        </div>

        {/* Expanded Debug View */}
        {isExpanded && (
          <div className="mt-4 pt-4 border-t">
            <DebugTimelineView events={run.events} runId={run.id} />
          </div>
        )}
      </div>
    </Card>
  );
}

// Helper functions
function extractAnswer(events: any[]): string {
  const answerEvent = events
    .filter(e => e.event_type === 'assistant_answer')
    .pop();
  
  if (answerEvent?.data?.content) {
    return answerEvent.data.content;
  }
  
  // Fallback: look for the last non-tool response
  const lastResponse = events
    .filter(e => e.event_type === 'assistant_answer' || (e.event_type === 'status_update' && e.data?.status === 'completed'))
    .pop();
    
  return lastResponse?.data?.message || lastResponse?.data?.content || 'Processing...';
}

function extractDuration(events: any[]): number {
  if (events.length === 0) return 0;
  
  const lastEvent = events[events.length - 1];
  return lastEvent.elapsed_ms || 0;
}