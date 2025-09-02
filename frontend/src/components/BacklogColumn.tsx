import { BacklogItem, BacklogItemProps } from "./BacklogItem";

interface BacklogColumnProps {
  items: BacklogItemProps[];
}

export function BacklogColumn({ items }: BacklogColumnProps) {
  return (
    <div className="flex min-h-0 flex-col overflow-y-auto">
      <div className="sticky top-0 z-10 flex items-center gap-2 border-b bg-background px-3 py-2">
        <span className="font-medium">Backlog</span>
        <input
          placeholder="Search"
          className="ml-auto h-7 w-32 rounded border px-2 py-1 text-sm"
        />
      </div>

      <ul className="divide-y divide-border">
        {items.map((item) => (
          <BacklogItem key={item.id} {...item} />
        ))}
      </ul>
    </div>
  );
}

