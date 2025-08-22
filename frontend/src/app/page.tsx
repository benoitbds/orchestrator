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
import BacklogPane from "@/components/BacklogPane";
import { BacklogProvider, useBacklog } from "@/context/BacklogContext";
import { ProjectPanel } from "@/components/ProjectPanel";
import RunsPanel from "@/components/RunsPanel";
import RunTimeline from "@/components/RunTimeline";
import { Step } from "@/models/run";

function HomeContent() {
  const [objective, setObjective] = useState("");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);
  const viewerRef = useRef<any>(null);
  const { currentProject } = useProjects();
  const [runsRefreshKey, setRunsRefreshKey] = useState(0);
  const { refreshItems } = useBacklog();

  const handleRun = async () => {
    setIsLoading(true);
    const runObjective = objective;
    const resp = await http('/chat', {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective: runObjective, project_id: currentProject?.id }),
    });
    const data = await resp.json();
    const runId = data.run_id;
    setCurrentRunId(runId);
    setRunsRefreshKey(k => k + 1);

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

    const ws = connectWS('/stream');
    ws.onopen = () => ws.send(JSON.stringify({ run_id: runId }));
    ws.onmessage = evt => {
      const chunk = JSON.parse(evt.data);
      viewerRef.current?.push(chunk);
    };
    ws.onclose = () => {
      setIsLoading(false);
    };
  };

  return (
    <>
      <StatusBar />
      <div className="flex h-screen pt-8">
        <ProjectPanel className="flex-shrink-0" />
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

            <StreamViewer ref={viewerRef} />
            <RunTimeline
              runId={currentRunId}
              onStep={(s: Step) => {
                if (s.node.startsWith('tool:')) {
                  refreshItems();
                }
              }}
              onFinal={(f: any) => {
                refreshItems();
                setRunsRefreshKey(k => k + 1);
                setIsLoading(false);
                const a = f.artifacts || {};
                const created = a.created_item_ids?.length ? `Created: ${a.created_item_ids.join(', ')}` : '';
                const updated = a.updated_item_ids?.length ? `Updated: ${a.updated_item_ids.join(', ')}` : '';
                const msg = [created, updated].filter(Boolean).join(' • ') || 'Run completed';
                if (typeof window !== 'undefined') window.alert(msg);
              }}
            />

            <BacklogPane />
            <HistoryPanel history={history} />
            <RunsPanel refreshKey={runsRefreshKey} />
          </div>
        </main>
      </div>
    </>
  );
}

export default function Home() {
  return (
    <BacklogProvider>
      <HomeContent />
    </BacklogProvider>
  );
}
