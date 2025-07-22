import { Card, CardContent } from "@/components/ui/card";

export interface HistoryItem {
  objective: string;
  result: string;
  timestamp: string;
}

export default function HistoryPanel({ history }: { history: HistoryItem[] }) {
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-800 mb-4">Résultats</h2>
      {history.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <p>Aucun résultat pour le moment</p>
          <p className="text-sm">Lancez une tâche pour voir les résultats ici</p>
        </div>
      ) : (
        [...history].reverse().map((item, i) => (
          <Card key={i} className="transition-all hover:shadow-md">
            <CardContent className="p-4">
              <div className="flex justify-between items-start mb-2">
                <h3 className="font-medium text-gray-800 text-sm">
                  {item.objective}
                </h3>
                <span className="text-xs text-gray-500">
                  {item.timestamp}
                </span>
              </div>
              <div
                className="text-gray-700 bg-gray-50 p-3 rounded text-sm leading-relaxed"
                dangerouslySetInnerHTML={{ __html: item.result }}
              />
            </CardContent>
          </Card>
        ))
      )}
    </section>
  );
}