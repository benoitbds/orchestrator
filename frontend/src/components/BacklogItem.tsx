export interface BacklogItemProps {
  id: string;
  title: string;
  status?: string;
  tags?: string[];
}

export function BacklogItem({ title, status, tags }: BacklogItemProps) {
  return (
    <li className="flex items-center justify-between px-2 py-1 text-sm hover:bg-accent/50">
      <span className="truncate">{title}</span>
      <div className="ml-2 flex items-center gap-1">
        {status && (
          <span className="rounded bg-muted px-1 py-0.5 text-[10px] text-muted-foreground">
            {status}
          </span>
        )}
        {tags?.map((tag) => (
          <span
            key={tag}
            className="rounded bg-secondary px-1 py-0.5 text-[10px] text-secondary-foreground"
          >
            {tag}
          </span>
        ))}
      </div>
    </li>
  );
}

