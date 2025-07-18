import { Card, CardContent } from "@/components/ui/card";

interface Item {
  objective: string;
  summary: string;
}

export default function HistoryPanel({ history }: { history: Item[] }) {
  return (
    <section className="space-y-2">
      <h2 className="text-lg font-semibold">Historique</h2>

      {history.length === 0 && (
        <p className="text-sm text-muted-foreground">Aucune exécution.</p>
      )}

      {history.map((h, idx) => (
        <Card key={idx}>
          <CardContent className="p-3">
            <p className="font-medium">{h.objective}</p>
            <p className="text-sm text-muted-foreground">{h.summary}</p>
          </CardContent>
        </Card>
      ))}
    </section>
  );
}
