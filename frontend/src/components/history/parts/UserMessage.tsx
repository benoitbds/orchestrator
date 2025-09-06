export function UserMessage({ text, ts }: { text: string; ts: number }) {
  const time = new Date(ts).toLocaleTimeString();
  return (
    <div className="ml-auto max-w-[78%] rounded-2xl bg-primary text-primary-foreground px-3 py-2">
      <div className="text-sm leading-relaxed whitespace-pre-wrap">{text}</div>
      <div className="mt-1 text-[11px] opacity-80 text-right">{time}</div>
    </div>
  );
}
