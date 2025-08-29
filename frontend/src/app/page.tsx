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
import type { AgentTimelineStep } from "@/components/AgentTimeline";
import BacklogPane from "@/components/BacklogPane";
import AgentHistory from "@/components/AgentHistory";
import { BacklogProvider, useBacklog } from "@/context/BacklogContext";
import { ProjectPanel } from "@/components/ProjectPanel";
import { mutate } from 'swr';

export default function Home() {
  return (
    <BacklogProvider>
      <HomeContent />
    </BacklogProvider>
  );
}

function HomeContent() {
  const [objective, setObjective] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const viewerRef = useRef<any>(null);
  const historyRef = useRef<any>(null);
  const { currentProject } = useProjects();
  const { refreshItems } = useBacklog();

  // Function to refresh all backlog related data
  const refreshAllBacklogData = useCallback(async () => {
    if (currentProject) {
      // Refresh BacklogContext data
      await refreshItems();
      
      // Also refresh SWR cache used by individual components
      await mutate(`/items?project_id=${currentProject.id}`);
      
      // Refresh agent history using ref
      if (historyRef.current?.refreshHistory) {
        historyRef.current.refreshHistory();
      }
      
      console.log('Backlog data and agent history refreshed after agent operation');
    }
  }, [currentProject, refreshItems]);
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

    if (html) {
      viewerRef.current?.push({ node: 'write', state: { result: html } });
      await refreshAllBacklogData();
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
        
        // Refresh backlog data when tool operations complete successfully
        if (msg.node && msg.node.includes('tool:') && msg.node.includes(':response') && parsed?.ok) {
          console.log('Tool operation completed successfully, refreshing backlog data');
          refreshAllBacklogData().catch(console.error);
        }
      }

      if (msg.status === 'done') {
        ws.close();
        http(`/runs/${run_id}`)
          .then(r => r.json())
          .then(async run => {
            viewerRef.current?.push({ node: 'write', state: { result: run.html || '' } });
            await refreshAllBacklogData();
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
          await refreshAllBacklogData();
          setIsLoading(false);
        } else if (data.status === 'failed') {
          ws.close();
          setIsLoading(false);
        } else {
          setTimeout(poll, 1000);
        }
      };
      poll();
    }, 7000);
  }, [currentProject, objective, refreshAllBacklogData]);

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

            <AgentHistory ref={historyRef} />
          </div>
        </main>
      </div>
    </>
  );
}
