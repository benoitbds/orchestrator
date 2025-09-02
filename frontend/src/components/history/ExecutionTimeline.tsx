import { Badge } from '@/components/ui/badge';
import { ChevronDown, ChevronRight, ExternalLink } from 'lucide-react';
import { useCallback, useMemo, useState } from 'react';
import type { Step, ErrorInfo } from '@/types/history';
import { formatTime, ms } from '@/lib/history-utils';

const statusToVariant: Record<Step['status'], 'default' | 'secondary' | 'destructive' | 'outline'> = {
  completed: 'default',
  running: 'secondary',
  failed: 'destructive',
  timeout: 'destructive',
  queued: 'outline',
};

function ErrorBox({ e }: { e: ErrorInfo }) {
  return (
    <div className="mt-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm">
      <div className="font-medium text-red-700">Error{e.code ? `: ${e.code}` : ''}</div>
      <div className="text-red-800">{e.message}</div>
      {e.hint && <div className="mt-1 text-red-900/90">Hint: {e.hint}</div>}
      {e.docUrl && (
        <a className="mt-2 inline-flex items-center gap-1 text-red-700 underline" href={e.docUrl} target="_blank" rel="noreferrer">
          Provider docs <ExternalLink className="h-3 w-3" />
        </a>
      )}
    </div>
  );
}

export function ExecutionTimeline({ steps, filter }: { steps: Step[]; filter?: (s: Step) => boolean }) {
  const [open, setOpen] = useState<Record<string, boolean>>({});
  const toggle = useCallback((id: string) => setOpen((o) => ({ ...o, [id]: !o[id] })), []);
  const list = filter ? steps.filter(filter) : steps;
  const onKey = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'r') {
        const last = list[list.length - 1];
        if (last) toggle(last.id);
        e.preventDefault();
      }
    },
    [list, toggle]
  );

  const rows = useMemo(
    () =>
      list.map((s) => {
        const variant = statusToVariant[s.status];
        return (
          <div key={s.id} className="group">
            <div className="grid grid-cols-[auto_1fr_auto] items-center gap-2 py-2">
              <button onClick={() => toggle(s.id)} className="mr-1 inline-flex items-center text-muted-foreground">
                {open[s.id] ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
              </button>
              <div className="flex items-center gap-2">
                <span className="tabular-nums text-xs text-muted-foreground">{formatTime(s.t)}</span>
                <Badge variant={variant}>{s.status}</Badge>
                <span className="text-xs uppercase tracking-wide text-muted-foreground">{s.kind}</span>
                <span className="font-medium">{s.title}</span>
              </div>
              <div className="text-xs text-muted-foreground">{ms(s.latencyMs)}</div>
            </div>
            {open[s.id] && (
              <div className="ml-6 rounded-lg border bg-muted/30 p-3 text-sm" onKeyDown={onKey}>
                {s.summary && <div className="mb-2">{s.summary}</div>}
                {s.details?.error ? (
                  <ErrorBox e={s.details.error} />
                ) : (
                  <div className="grid gap-2 md:grid-cols-2">
                    {s.details?.input && (
                      <div>
                        <div className="mb-1 text-xs font-semibold">Input</div>
                        <pre className="max-h-64 overflow-auto rounded bg-background p-2 text-xs">
                          {JSON.stringify(s.details.input, null, 2)}
                        </pre>
                      </div>
                    )}
                    {s.details?.output && (
                      <div>
                        <div className="mb-1 text-xs font-semibold">Output</div>
                        <pre className="max-h-64 overflow-auto rounded bg-background p-2 text-xs">
                          {JSON.stringify(s.details.output, null, 2)}
                        </pre>
                      </div>
                    )}
                  </div>
                )}
              </div>
            )}
            <div className="border-b" />
          </div>
        );
      }),
    [list, open, toggle, onKey]
  );

  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm" onKeyDown={onKey} tabIndex={0}>
      <div className="mb-2 text-sm font-semibold">Execution Timeline</div>
      <div className="max-h-[50vh] min-h-[20vh] overflow-y-auto">
        {rows.length ? rows : <div className="text-sm text-muted-foreground">No steps</div>}
      </div>
    </div>
  );
}
