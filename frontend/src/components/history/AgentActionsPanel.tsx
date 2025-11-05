'use client';

import { useState } from 'react';
import { useAgentActions } from '@/hooks/useAgentActions';
import { useRunsStore } from '@/stores/useRunsStore';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';

interface Props {
  runId?: string;
}

export function AgentActionsPanel({ runId }: Props) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const toggle = (id: string) => setOpen((p) => ({ ...p, [id]: !p[id] }));
  const { actions, done } = useAgentActions(runId);
  const { getCurrentRun } = useRunsStore();
  const currentRun = getCurrentRun();
  const status = done ? 'done' : currentRun?.status === 'running' ? 'running' : 'idle';

  const badge =
    status === 'running'
      ? 'Running…'
      : status === 'done'
      ? 'Done'
      : undefined;

  const iconFor = (phase: string, ok?: boolean) => {
    if (phase === 'request') return <Loader2 className="h-4 w-4 animate-spin" />;
    if (phase === 'response' && ok !== false) return <CheckCircle className="h-4 w-4 text-green-600" />;
    if (phase === 'response' && ok === false) return <AlertCircle className="h-4 w-4 text-rose-600" />;
    return null;
  };

  const preview = (obj: any) => {
    try {
      const str = JSON.stringify(obj);
      return str.length > 60 ? str.slice(0, 57) + '…' : str;
    } catch {
      return '';
    }
  };

  return (
    <div className="border rounded-md overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b text-sm font-medium">
        <span>Agent actions ({actions.length})</span>
        {badge && <span className="text-xs">{badge}</span>}
      </div>
      <div className="max-h-96 overflow-y-auto divide-y text-sm">
        {actions.map((action, idx) => (
          <div key={action.id} className="px-3 py-2">
            <button
              className="w-full text-left flex items-start justify-between"
              onClick={() => toggle(action.id)}
            >
              <div className="flex items-center gap-2">
                {iconFor(action.phase, action.ok)}
                <span>
                  {action.tool} ({action.phase})
                </span>
                <code className="text-xs opacity-70">
                  {preview(action.payload)}
                </code>
                {action.phase === 'response' && action.ok === false ? (
                  <span className="ml-2 text-xs text-rose-600">Failed</span>
                ) : null}
              </div>
            </button>
            {open[action.id] && (
              <pre className="mt-1 bg-muted rounded p-2 text-xs max-h-40 overflow-auto">
                {JSON.stringify(action.payload, null, 2)}
              </pre>
            )}
          </div>
        ))}
        {!actions.length && (
          <div className="px-3 py-2 text-xs text-muted-foreground">
            No actions yet
          </div>
        )}
      </div>
    </div>
  );
}

