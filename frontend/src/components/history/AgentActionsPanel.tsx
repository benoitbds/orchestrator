'use client';

import { useState } from 'react';
import { useAgentActions } from '@/hooks/useAgentActions';

interface Props {
  runId?: string;
}

export function AgentActionsPanel({ runId }: Props) {
  const { actions, done } = useAgentActions(runId);
  const [openIds, setOpenIds] = useState<Record<string, boolean>>({});

  const toggle = (id: string) => {
    setOpenIds((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const formatTime = (ts: number) => new Date(ts).toLocaleTimeString();

  const badge = (a: { phase: string; ok?: boolean }) => {
    if (a.phase === 'request') return '→ request';
    if (a.phase === 'response') {
      return a.ok === false ? '✗ response' : '✓ response';
    }
    return a.phase;
  };

  return (
    <div className="border rounded-md overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b text-sm font-medium">
        <span>Agent actions ({actions.length})</span>
        {done && <span className="text-xs text-green-600">Done</span>}
      </div>
      <div className="max-h-96 overflow-y-auto divide-y text-sm">
        {actions.map((a) => (
          <div key={a.id} className="px-3 py-2">
            <button
              className="w-full text-left flex items-start justify-between"
              onClick={() => toggle(a.id)}
            >
              <div className="flex items-center gap-2">
                <span>⚙️</span>
                <code>{a.tool}</code>
                <span className="text-xs opacity-70">{badge(a)}</span>
              </div>
              <span className="text-xs opacity-70">{formatTime(a.createdAt)}</span>
            </button>
            {openIds[a.id] && (
              <pre className="mt-1 bg-muted rounded p-2 text-xs max-h-40 overflow-auto">
                {JSON.stringify(a.payload, null, 2)}
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
