import { useState } from 'react';
import { Loader2, Play, CheckCircle, XCircle } from 'lucide-react';
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import type { AgentAction } from '@/types/conversation';
import { cn } from '@/lib/utils';

interface AgentActionsAccordionProps {
  actions: AgentAction[];
}

const statusColors: Record<AgentAction['status'], string> = {
  running: 'bg-muted text-muted-foreground',
  succeeded: 'bg-green-500 text-white',
  failed: 'bg-red-500 text-white',
  pending: 'bg-muted text-muted-foreground',
};

const StatusIcon = ({ status }: { status: AgentAction['status'] }) => {
  if (status === 'running') return <Play className="h-3 w-3" />;
  if (status === 'succeeded') return <CheckCircle className="h-3 w-3" />;
  if (status === 'failed') return <XCircle className="h-3 w-3" />;
  return <Play className="h-3 w-3" />;
};

export function AgentActionsAccordion({ actions }: AgentActionsAccordionProps) {
  const [openDetails, setOpenDetails] = useState<Record<string, boolean>>({});
  const [open, setOpen] = useState(false);
  const running = actions.find((a) => a.status === 'running');

  const toggle = (id: string) => setOpenDetails((s) => ({ ...s, [id]: !s[id] }));

  return (
    <Accordion>
      <AccordionItem value="actions">
        <AccordionTrigger onClick={() => setOpen(!open)}>
          <div className="flex w-full items-center justify-between text-sm">
            <span>Agent actions ({actions.length})</span>
            {running && (
              <span className="ml-2 flex items-center gap-1 text-xs text-muted-foreground">
                • Running: {running.label}
                <Loader2 className="h-3 w-3 animate-spin" />
              </span>
            )}
          </div>
        </AccordionTrigger>
        <AccordionContent open={open}>
          <ul className="text-sm">
            {actions.map((a) => (
              <li key={a.id} className="border-b last:border-none py-1.5">
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <StatusIcon status={a.status} />
                    <span>{a.label}</span>
                    <Badge className={cn('text-[10px] px-1', statusColors[a.status])}>{a.status}</Badge>
                  </div>
                  <div className="flex items-center gap-2">
                    {a.durationMs !== undefined && (
                      <span className="text-xs text-muted-foreground">{a.durationMs}ms</span>
                    )}
                    {(a.debug?.input || a.debug?.output || a.debug?.error) && (
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-6 px-2 text-[10px]"
                        onClick={() => toggle(a.id)}
                      >
                        Details
                      </Button>
                    )}
                  </div>
                </div>
                {openDetails[a.id] && (
                  <div className="mt-1 space-y-1">
                    {a.debug?.input && (
                      <pre className="max-h-32 overflow-auto rounded bg-background p-2 text-xs">
                        {JSON.stringify(a.debug.input, null, 2)}
                      </pre>
                    )}
                    {a.debug?.output && (
                      <pre className="max-h-32 overflow-auto rounded bg-background p-2 text-xs">
                        {JSON.stringify(a.debug.output, null, 2)}
                      </pre>
                    )}
                    {a.debug?.error && (
                      <pre className="max-h-32 overflow-auto rounded bg-background p-2 text-xs text-red-500">
                        {JSON.stringify(a.debug.error, null, 2)}
                      </pre>
                    )}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}
