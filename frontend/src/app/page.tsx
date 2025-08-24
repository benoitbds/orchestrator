"use client";
import { useState, useRef } from "react";
import { Loader2 } from "lucide-react";
import { useProjects } from "@/context/ProjectContext";
import { connectWS } from "@/lib/ws";
import { http } from "@/lib/api";
import StatusBar from "@/components/StatusBar";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import StreamViewer from "@/components/StreamViewer";
import HistoryPanel, { HistoryItem } from "@/components/HistoryPanel";
import type { AgentTimelineStep } from "@/components/AgentTimeline";
import BacklogPane from "@/components/BacklogPane";
import { BacklogProvider } from "@/context/BacklogContext";
import { ProjectPanel } from "@/components/ProjectPanel";
import RunsPanel from "@/components/RunsPanel";

export default function Home() {
  const [objective, setObjective] = useState("");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const viewerRef = useRef<any>(null);
  const { currentProject } = useProjects();
  const [runsRefreshKey, setRunsRefreshKey] = useState(0);
  const [steps, setSteps] = useState<AgentTimelineStep[]>([]);

  const handleRun = async () => {
    setIsLoading(true);
    setSteps([]);
    viewerRef.current?.clear?.();
    const runObjective = objective;
    const resp = await http('/chat', {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective: runObjective, project_id: currentProject?.id }),
    });
    const data = await resp.json();
    const runId = data.run_id;
    setRunsRefreshKey(k => k + 1);

    // poll run result
    const poll = async () => {
      const r = await http(`/runs/${runId}`);
      const data = await r.json();
      if (data.status === "success") {
        setHistory(h => [
          ...h,
          {
            objective: runObjective,
            html: data.html ?? "",
            summary: data.summary,
            timestamp: new Date().toLocaleString(),
          },
        ]);
        setIsLoading(false);
        setRunsRefreshKey(k => k + 1);
      } else if (data.status === "failed") {
        setIsLoading(false);
        setRunsRefreshKey(k => k + 1);
      } else {
        setTimeout(poll, 1000);
      }
    };
    poll();

    // WebSocket streaming
    const ws = connectWS('/stream');
    ws.onopen = () => ws.send(JSON.stringify({ run_id: runId }));
    ws.onmessage = evt => {
      const chunk = JSON.parse(evt.data);
      if (chunk.node) {
        let parsed: any;
        try {
          parsed = chunk.content ? JSON.parse(chunk.content) : undefined;
        } catch {
          parsed = chunk.content;
        }
        viewerRef.current?.push({ node: chunk.node, state: parsed });
        setSteps(s => [
          ...s,
          { runId: chunk.run_id, node: chunk.node, content: parsed, timestamp: chunk.timestamp },
        ]);
      }
    };
    ws.onclose = () => {
      setIsLoading(false);
    };
  };

  return (
    <BacklogProvider>
      <StatusBar />
      <div className="flex h-screen pt-8">
        {/* Panel de gestion des projets à gauche */}
        <ProjectPanel className="flex-shrink-0" />
        
        {/* Contenu principal */}
        <main className="flex-1 flex flex-col gap-6 p-6 overflow-auto">
          <div className="max-w-3xl mx-auto w-full space-y-6">
            <h1 className="text-2xl font-bold">Agent 4 BA</h1>

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
                disabled={isLoading}
              />
              <Button type="submit" disabled={isLoading}>
                {isLoading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                Lancer
              </Button>
            </form>

            <StreamViewer ref={viewerRef} timelineSteps={steps} />

            <BacklogPane />

            <HistoryPanel history={history} />
            <RunsPanel refreshKey={runsRefreshKey} />
          </div>
        </main>
      </div>
    </BacklogProvider>
  );
}
