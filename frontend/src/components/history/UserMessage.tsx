import { format } from 'date-fns';

interface UserMessageProps {
  text: string;
  timestamp: string;
}

export function UserMessage({ text, timestamp }: UserMessageProps) {
  const time = format(new Date(timestamp), 'HH:mm');
  return (
    <div className="flex justify-end items-end gap-2">
      <div className="ml-auto max-w-[78%] rounded-2xl px-3 py-2 bg-primary text-primary-foreground">
        <p className="text-sm whitespace-pre-wrap">{text}</p>
      </div>
      <span className="text-[10px] text-muted-foreground">{time}</span>
    </div>
  );
}
