"use client";
import { useState, useRef } from "react";
import { useProjects } from "@/context/ProjectContext";
import { connectWS } from "@/lib/ws";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import StreamViewer from "@/components/StreamViewer";
import HistoryPanel from "@/components/HistoryPanel";
import BacklogPane from "@/components/BacklogPane";
import { BacklogProvider } from "@/context/BacklogContext";
import { ProjectPanel } from "@/components/ProjectPanel";

export default function Home() {
  const [objective, setObjective] = useState("");
  const [history, setHistory] = useState<string[]>([]);
  const viewerRef = useRef<any>(null);
  const { currentProject } = useProjects();

  const handleRun = async () => {
    // API relative : même origin => pas de CORS
        const apiUrl = process.env.NEXT_PUBLIC_API_URL;
    const res = await fetch(`${apiUrl}/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective, project_id: currentProject?.id }),
    }).then(r => r.json());

    setHistory(h => [...h, res.html]);

    // WebSocket streaming
    const ws = connectWS(objective, currentProject?.id);
    ws.onmessage = evt => {
      const chunk = JSON.parse(evt.data);
      viewerRef.current?.push(chunk);
    };
  };

  return (
    <BacklogProvider>
      <div className="flex h-screen">
        {/* Panel de gestion des projets à gauche */}
        <ProjectPanel className="flex-shrink-0" />
        
        {/* Contenu principal */}
        <main className="flex-1 flex flex-col gap-6 p-6 overflow-auto">
          <div className="max-w-3xl mx-auto w-full space-y-6">
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

            <BacklogPane />

            <HistoryPanel history={history} />
          </div>
        </main>
      </div>
    </BacklogProvider>
  );
}
