import { useCallback, useState } from 'react';
import { Button } from '@/components/ui/button';

export function AgentPlanCard({ bullets, rationale }: { bullets: string[]; rationale?: string }) {
  const [show, setShow] = useState(false);
  const toggle = useCallback(() => setShow((s) => !s), []);
  const onKey = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'r') {
        toggle();
        e.preventDefault();
      }
    },
    [toggle]
  );
  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm" onKeyDown={onKey} tabIndex={0}>
      <div className="mb-2 text-sm font-semibold">Agent Plan (visible)</div>
      <ul className="mb-2 list-disc pl-4 text-sm">
        {bullets.map((b, i) => (
          <li key={i}>{b}</li>
        ))}
      </ul>
      {rationale && show && <p className="mb-2 text-sm text-muted-foreground">{rationale}</p>}
      {rationale && (
        <Button variant="ghost" size="sm" onClick={toggle} aria-expanded={show}>
          {show ? 'Hide' : 'Show more'} (Ctrl+R)
        </Button>
      )}
    </div>
  );
}
