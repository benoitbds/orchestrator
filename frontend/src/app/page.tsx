"use client";
import { useState, useRef } from "react";
import { connectWS } from "@/lib/ws";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import StreamViewer from "@/components/StreamViewer";
import HistoryPanel from "@/components/HistoryPanel";

export default function Home() {
  const [objective, setObjective] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const viewerRef = useRef<any>(null);

  const handleRun = async () => {
    // API relative : même origin => pas de CORS
    const res = await fetch("/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective }),
    }).then(r => r.json());

    setHistory(h => [...h, res.html]);

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

      <form
        onSubmit={e => {
          e.preventDefault();
          handleRun();
        }}
        className="flex gap-2"
      >
        <Input
          placeholder="Votre objectif…"
          value={objective}
          onChange={e => setObjective(e.target.value)}
        />
        <Button type="submit">Lancer</Button>
      </form>

      <StreamViewer ref={viewerRef} />

      <HistoryPanel history={history} />
    </main>
  );
}
