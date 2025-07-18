"use client";
import { useState, useRef } from "react";
import { connectWS } from "@/lib/ws";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import StreamViewer from "@/components/StreamViewer";
import HistoryPanel from "@/components/HistoryPanel";

export default function Home() {
  const [objective, setObjective] = useState("");
  const [history, setHistory]   = useState<any[]>([]);
  const viewerRef = useRef<any>(null);

  const handleRun = async () => {
    // POST /chat — on récupère le rendu final pour l’historique
    const res = await fetch("http://localhost:9080/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective }),
    }).then(r => r.json());

    setHistory(h => [...h, { objective, summary: res.summary }]);

    // WebSocket streaming
    const ws = connectWS(objective);
    ws.onmessage = evt => {
      const chunk = JSON.parse(evt.data);
      viewerRef.current?.push(chunk);
    };
  };

  return (
    <main className="flex flex-col gap-6 p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold">Orchestrator Assistant</h1>

      <div className="flex gap-2">
        <Input
          placeholder="Votre objectif…"
          value={objective}
          onChange={e => setObjective(e.target.value)}
        />
        <Button onClick={handleRun}>Lancer</Button>
      </div>

      <StreamViewer ref={viewerRef} />

      <HistoryPanel history={history} />
    </main>
  );
}
