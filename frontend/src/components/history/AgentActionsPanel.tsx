'use client';

import { useState } from 'react';
import { AgentStep } from '@/hooks/useRunStream';
import { Loader2, CheckCircle, AlertCircle } from 'lucide-react';

interface Props {
  steps: AgentStep[];
  status: 'idle' | 'running' | 'done' | 'error';
}

export function AgentActionsPanel({ steps, status }: Props) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const toggle = (id: string) => setOpen((p) => ({ ...p, [id]: !p[id] }));

  const badge =
    status === 'running'
      ? 'Running…'
      : status === 'done'
      ? 'Done'
      : status === 'error'
      ? 'Failed'
      : undefined;

  const iconFor = (s: AgentStep['state']) => {
    if (s === 'running') return <Loader2 className="h-4 w-4 animate-spin" />;
    if (s === 'success') return <CheckCircle className="h-4 w-4 text-green-600" />;
    if (s === 'failed') return <AlertCircle className="h-4 w-4 text-rose-600" />;
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
        <span>Agent actions ({steps.length})</span>
        {badge && <span className="text-xs">{badge}</span>}
      </div>
      <div className="max-h-96 overflow-y-auto divide-y text-sm">
        {steps.map((s, idx) => (
          <div key={s.id} className="px-3 py-2">
            <button
              className="w-full text-left flex items-start justify-between"
              onClick={() => toggle(s.id)}
            >
              <div className="flex items-center gap-2">
                {iconFor(s.state)}
                <span>
                  {s.tool} #{idx + 1}
                </span>
                <code className="text-xs opacity-70">
                  {preview(s.request)}
                </code>
                {s.state === 'failed' && s.error ? (
                  <span className="ml-2 text-xs text-rose-600">Failed: {s.error}</span>
                ) : null}
              </div>
            </button>
            {open[s.id] && (
              <pre className="mt-1 bg-muted rounded p-2 text-xs max-h-40 overflow-auto">
                {JSON.stringify(
                  s.ok
                    ? { request: s.request, result: s.result }
                    : { request: s.request, error: s.error },
                  null,
                  2,
                )}
              </pre>
            )}
          </div>
        ))}
        {!steps.length && (
          <div className="px-3 py-2 text-xs text-muted-foreground">
            No actions yet
          </div>
        )}
      </div>
    </div>
  );
}

