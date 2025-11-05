"use client";
import { AgentExecutionState } from '@/types/agent-execution';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import { TodoChecklist } from './TodoChecklist';
import { ToolCallDisplay } from './ToolCallDisplay';
import { ItemCreatedDisplay } from './ItemCreatedDisplay';
import dynamic from 'next/dynamic';

const ChevronDown = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.ChevronDown })),
  { ssr: false }
);
const ChevronRight = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.ChevronRight })),
  { ssr: false }
);
const Bot = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Bot })),
  { ssr: false }
);
const CheckCircle2 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.CheckCircle2 })),
  { ssr: false }
);
const XCircle = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.XCircle })),
  { ssr: false }
);
const Loader2 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Loader2 })),
  { ssr: false }
);

interface AgentNarrationBlockProps {
  state: AgentExecutionState;
  onToggleExpand: () => void;
}

export function AgentNarrationBlock({ state, onToggleExpand }: AgentNarrationBlockProps) {
  const getStatusBadge = () => {
    switch (state.status) {
      case 'running':
        return (
          <Badge variant="default" className="gap-1">
            <Loader2 className="h-3 w-3 animate-spin" />
            Running
          </Badge>
        );
      case 'completed':
        return (
          <Badge variant="outline" className="gap-1 border-green-500 text-green-700 dark:text-green-400">
            <CheckCircle2 className="h-3 w-3" />
            Completed
          </Badge>
        );
      case 'error':
        return (
          <Badge variant="destructive" className="gap-1">
            <XCircle className="h-3 w-3" />
            Error
          </Badge>
        );
    }
  };

  const getDuration = () => {
    if (!state.timestamp_end) return null;
    const start = new Date(state.timestamp_start).getTime();
    const end = new Date(state.timestamp_end).getTime();
    const duration = (end - start) / 1000;
    return `${duration.toFixed(1)}s`;
  };

  return (
    <div className={cn(
      "border rounded-lg transition-all duration-200",
      state.status === 'running' ? 'border-blue-500 shadow-sm' : 'border-border'
    )}>
      <button
        onClick={onToggleExpand}
        className="w-full flex items-center justify-between p-4 hover:bg-accent/50 transition-colors rounded-t-lg"
      >
        <div className="flex items-center gap-3">
          <Bot className={cn(
            "h-5 w-5",
            state.status === 'running' && "text-blue-500",
            state.status === 'completed' && "text-green-500"
          )} />
          <div className="flex flex-col items-start">
            <span className="font-semibold">{state.agent_name}</span>
            {state.summary && state.status === 'completed' && (
              <span className="text-xs text-muted-foreground">{state.summary}</span>
            )}
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {getDuration() && (
            <span className="text-xs text-muted-foreground">{getDuration()}</span>
          )}
          {getStatusBadge()}
          {state.expanded ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )}
        </div>
      </button>

      {state.expanded && (
        <div className="px-4 pb-4 space-y-3 animate-in fade-in duration-200">
          {state.narration && (
            <div className="flex items-start gap-2 text-sm">
              <span className="text-blue-500 mt-0.5">●</span>
              <span>{state.narration}</span>
            </div>
          )}
          
          {state.narrations && state.narrations.length > 0 && (
            <div className="space-y-2 bg-blue-50 dark:bg-blue-950/20 p-3 rounded-lg border border-blue-200 dark:border-blue-800">
              <div className="text-xs font-semibold text-blue-700 dark:text-blue-300 uppercase tracking-wide">
                Agent Narration
              </div>
              {state.narrations.map((narration, idx) => (
                <div key={idx} className="flex items-start gap-2 text-sm">
                  <span className="text-blue-500 mt-0.5">💬</span>
                  <span className="text-blue-900 dark:text-blue-100">{narration}</span>
                </div>
              ))}
            </div>
          )}

          {state.thinking && (
            <div className="flex items-start gap-2 text-sm text-muted-foreground animate-pulse">
              <span className="text-blue-500 mt-0.5">●</span>
              <span>{state.thinking}</span>
            </div>
          )}

          {state.progress !== undefined && state.progress < 100 && (
            <div className="space-y-1">
              <div className="flex items-center justify-between text-xs text-muted-foreground">
                <span>Progress</span>
                <span>{state.progress}%</span>
              </div>
              <div className="w-full bg-secondary rounded-full h-2 overflow-hidden">
                <div 
                  className="bg-blue-500 h-full transition-all duration-500 ease-out"
                  style={{ width: `${state.progress}%` }}
                />
              </div>
            </div>
          )}

          {state.todos.length > 0 && (
            <TodoChecklist todos={state.todos} />
          )}

          {state.tool_calls.length > 0 && (
            <div className="space-y-2">
              {state.tool_calls.map((call, idx) => (
                <ToolCallDisplay key={idx} call={call} />
              ))}
            </div>
          )}

          {state.items_created.length > 0 && (
            <div className="space-y-2">
              {state.items_created.map((item, idx) => (
                <ItemCreatedDisplay key={item.id || idx} item={item} />
              ))}
            </div>
          )}

          {state.status === 'completed' && state.metrics && (
            <div className="mt-3 pt-3 border-t">
              <div className="flex items-start gap-2 text-sm">
                <span className="text-green-500 mt-0.5">●</span>
                <div className="space-y-1">
                  <span className="font-medium">Execution Summary</span>
                  <div className="pl-4 space-y-0.5 text-xs text-muted-foreground">
                    {state.metrics.items_created !== undefined && (
                      <div>✓ {state.metrics.items_created} items created</div>
                    )}
                    {state.metrics.duration_ms !== undefined && (
                      <div>Duration: {(state.metrics.duration_ms / 1000).toFixed(1)}s</div>
                    )}
                    {state.metrics.suggestions && Array.isArray(state.metrics.suggestions) && (
                      <div className="mt-2 space-y-1">
                        <div className="font-medium text-blue-600 dark:text-blue-400">💡 Suggestions:</div>
                        {(state.metrics.suggestions as string[]).map((suggestion, idx) => (
                          <div key={idx} className="pl-2 text-muted-foreground">
                            • {suggestion}
                          </div>
                        ))}
                      </div>
                    )}
                    {Object.entries(state.metrics).map(([key, value]) => {
                      if (key !== 'items_created' && key !== 'duration_ms' && key !== 'suggestions') {
                        return (
                          <div key={key}>
                            {key}: {String(value)}
                          </div>
                        );
                      }
                      return null;
                    })}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
