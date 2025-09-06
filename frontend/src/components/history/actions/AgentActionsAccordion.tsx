import { AgentAction } from '@/types/history';
import { useState, useMemo } from 'react';

function StatusPill({ s }: { s: AgentAction['status'] }) {
  const cls =
    s === 'succeeded'
      ? 'bg-green-100 text-green-700'
      : s === 'failed'
      ? 'bg-red-100 text-red-700'
      : s === 'running'
      ? 'bg-zinc-100 text-zinc-700'
      : 'bg-zinc-50 text-zinc-500';
  return <span className={`px-2 py-[2px] text-[11px] rounded-full ${cls}`}>{s}</span>;
}

export function AgentActionsAccordion({
  actions,
  phase,
}: {
  actions: AgentAction[];
  phase: 'running' | 'completed' | 'failed';
}) {
  const [open, setOpen] = useState(false);
  const current = useMemo(() => actions.find((a) => a.status === 'running'), [actions]);
  const title = `Agent actions (${actions.length})` + (current ? ` • Running: ${current.label}` : '');

  return (
    <div className="rounded-xl border bg-background">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full text-left px-3 py-2 text-sm font-medium flex items-center justify-between"
      >
        <span>{open ? '▼' : '▶'} {title}</span>
        <span className="text-[11px] opacity-70">{phase === 'running' ? 'in progress…' : null}</span>
      </button>
      {open && (
        <div className="px-3 pb-2">
          {actions.map((a) => (
            <div key={a.id} className="flex items-start justify-between gap-2 py-1.5">
              <div className="text-sm">
                <div className="font-medium">{a.label}</div>
                {a.durationMs != null && (
                  <div className="text-[11px] opacity-70">{Math.round(a.durationMs)} ms</div>
                )}
              </div>
              <div className="flex items-center gap-2">
                <StatusPill s={a.status} />
                {a.debug ? <ActionDetails debug={a.debug} /> : null}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ActionDetails({ debug }: { debug: AgentAction['debug'] }) {
  const [open, setOpen] = useState(false);
  return (
    <div>
      <button
        className="text-[11px] underline opacity-80"
        onClick={() => setOpen((v) => !v)}
      >
        {open ? 'Hide details' : 'Details'}
      </button>
      {open && (
        <pre className="mt-1 max-h-48 overflow-auto text-[11px] bg-muted rounded p-2">
{JSON.stringify(debug, null, 2)}
        </pre>
      )}
    </div>
  );
}
