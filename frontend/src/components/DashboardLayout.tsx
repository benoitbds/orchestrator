import { ScrollArea } from "@/components/ui/scroll-area";

export default function DashboardLayout() {
  return (
    <div className="flex h-dvh flex-col">
      <header className="shrink-0 border-b p-4">Header</header>

      <div className="grid flex-1 min-h-0 grid-cols-[16rem_1fr_20rem]">
        <aside className="flex min-h-0 flex-col border-r">
          <ScrollArea className="h-full p-4">
            {Array.from({ length: 50 }).map((_, i) => (
              <div key={i} className="py-1">
                Sidebar Item {i + 1}
              </div>
            ))}
          </ScrollArea>
        </aside>

        <section className="flex min-h-0 flex-col border-r">
          <ScrollArea className="h-full p-4">
            {Array.from({ length: 50 }).map((_, i) => (
              <div key={i} className="py-1">
                Backlog Item {i + 1}
              </div>
            ))}
          </ScrollArea>
        </section>

        <section className="flex min-h-0 flex-col">
          <ScrollArea className="h-full p-4">
            {Array.from({ length: 50 }).map((_, i) => (
              <div key={i} className="py-1">
                Message {i + 1}
              </div>
            ))}
          </ScrollArea>
        </section>
      </div>

      <footer className="shrink-0 border-t p-4">Footer</footer>
    </div>
  );
}
