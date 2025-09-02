import { Virtuoso } from "react-virtuoso";
import { BacklogItem, BacklogItemProps } from "./BacklogItem";

interface BacklogColumnVirtuosoProps {
  items: BacklogItemProps[];
}

export function BacklogColumnVirtuoso({ items }: BacklogColumnVirtuosoProps) {
  return (
    <div className="flex flex-1 min-h-0 flex-col">
      <Virtuoso
        className="flex-1"
        data={items}
        overscan={200}
        components={{
          Header: () => (
            <div className="sticky top-0 z-10 flex items-center gap-2 border-b bg-background px-3 py-2">
              <span className="font-medium">Backlog</span>
              <input
                placeholder="Search"
                className="ml-auto h-7 w-32 rounded border px-2 py-1 text-sm"
              />
            </div>
          ),
        }}
        itemContent={(_, item) => <BacklogItem {...item} />}
      />
    </div>
  );
}

