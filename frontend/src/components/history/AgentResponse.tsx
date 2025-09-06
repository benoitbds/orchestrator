import { Badge } from '@/components/ui/badge';

interface AgentResponseProps {
  text?: string;
  status: 'running' | 'completed' | 'failed';
}

export function AgentResponse({ text, status }: AgentResponseProps) {
  const badge =
    status === 'completed' ? (
      <Badge className="bg-green-500 text-white text-[10px] px-1">✓</Badge>
    ) : status === 'failed' ? (
      <Badge className="bg-red-500 text-white text-[10px] px-1">⚠</Badge>
    ) : null;
  return (
    <div className="flex items-start gap-2">
      <div className="mr-auto max-w-[78%] rounded-2xl px-3 py-2 bg-muted">
        <p className="text-sm whitespace-pre-wrap">
          {text}
          {status === 'running' && <span className="animate-pulse"> …</span>}
        </p>
      </div>
      {badge}
    </div>
  );
}
