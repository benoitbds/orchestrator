"use client";
import { useState, useRef, useCallback } from "react";
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
import { BacklogProvider, useBacklog } from "@/context/BacklogContext";
import { ProjectPanel } from "@/components/ProjectPanel";
import RunsPanel from "@/components/RunsPanel";

export default function Home() {
  return (
    <BacklogProvider>
      <HomeContent />
    </BacklogProvider>
  );
}

function HomeContent() {
  const [objective, setObjective] = useState("");
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const viewerRef = useRef<any>(null);
  const { currentProject } = useProjects();
  const { refreshItems } = useBacklog();
  const [runsRefreshKey, setRunsRefreshKey] = useState(0);
  const [steps, setSteps] = useState<AgentTimelineStep[]>([]);

  const handleRun = useCallback(async () => {
    if (!currentProject) return;
    setIsLoading(true);
    setSteps([]);
    viewerRef.current?.clear?.();
    const runObjective = objective;
    const resp = await http('/chat', {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ objective: runObjective, project_id: currentProject.id }),
    });
    const { run_id, html } = await resp.json();
    setRunsRefreshKey(k => k + 1);

    if (html) {
      viewerRef.current?.push({ node: 'write', state: { result: html } });
      refreshItems();
      setIsLoading(false);
    }

    let wsEvent = false;
    const ws = connectWS('/stream');
    ws.onopen = () => {
      console.log('WS open', { run_id });
      ws.send(JSON.stringify({ run_id }));
    };
    ws.onmessage = evt => {
      wsEvent = true;
      const msg = JSON.parse(evt.data);
      console.log('WS message', msg);
      if (msg.node) {
        let parsed: any;
        try {
          parsed = msg.content ? JSON.parse(msg.content) : undefined;
        } catch {
          parsed = msg.content;
        }
        viewerRef.current?.push({ node: msg.node, state: parsed });
        setSteps(s => [
          ...s,
          { runId: msg.run_id, node: msg.node, content: parsed, timestamp: msg.timestamp },
        ]);
      }

      if (msg.status === 'done') {
        ws.close();
        http(`/runs/${run_id}`)
          .then(r => r.json())
          .then(run => {
            viewerRef.current?.push({ node: 'write', state: { result: run.html || '' } });
            setHistory(h => [
              ...h,
              {
                objective: runObjective,
                html: run.html || '',
                summary: run.summary,
                timestamp: new Date().toLocaleString(),
              },
            ]);
            refreshItems();
            setRunsRefreshKey(k => k + 1);
            setIsLoading(false);
          });
      }
    };
    ws.onclose = () => {
      setIsLoading(false);
    };

    setTimeout(() => {
      if (wsEvent) return;
      const poll = async () => {
        const r = await http(`/runs/${run_id}`);
        const data = await r.json();
        if (data.status === 'done') {
          ws.close();
          viewerRef.current?.push({ node: 'write', state: { result: data.html || '' } });
          setHistory(h => [
            ...h,
            {
              objective: runObjective,
              html: data.html || '',
              summary: data.summary,
              timestamp: new Date().toLocaleString(),
            },
          ]);
          refreshItems();
          setRunsRefreshKey(k => k + 1);
          setIsLoading(false);
        } else if (data.status === 'failed') {
          ws.close();
          setIsLoading(false);
          setRunsRefreshKey(k => k + 1);
        } else {
          setTimeout(poll, 1000);
        }
      };
      poll();
    }, 7000);
  }, [currentProject, objective, refreshItems]);

  return (
    <>
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
    </>
  );
}
