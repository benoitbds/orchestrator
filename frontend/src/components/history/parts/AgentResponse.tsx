export function AgentResponse({ text, phase }: { text: string; phase: 'running' | 'completed' | 'failed' }) {
  const badge =
    phase === 'completed' ? '✓' : phase === 'failed' ? '⚠️' : '…';
  return (
    <div className="mr-auto max-w-[78%] rounded-2xl bg-muted px-3 py-2">
      <div className="text-sm leading-relaxed whitespace-pre-wrap">{text}</div>
      <div className="mt-1 text-[11px] opacity-80">Status: {badge}</div>
    </div>
  );
}
