import { Card, CardContent } from "@/components/ui/card";

interface Item {
  objective: string;
  summary: string;
}

export default function HistoryPanel({ history }: { history: string[] }) {
  return (
    <section className="space-y-4">
      {history.map((html, i) => (
        <article
          key={i}
          className="prose p-3 rounded bg-slate-100"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      ))}
    </section>
  );
}
