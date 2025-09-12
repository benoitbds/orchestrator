"use client";
import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import RunTimeline from "@/components/RunTimeline";
import { http } from "@/lib/api";
import { getWSUrl } from "@/lib/ws";

interface Run {
  run_id: string;
  objective: string;
  status: "running" | "done";
  created_at: string;
  completed_at?: string | null;
  html?: string | null;
  summary?: string | null;
}

export default function RunDetail({ params }: { params: { run_id: string } }) {
  const [run, setRun] = useState<Run | null>(null);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        const res = await http(`/runs/${params.run_id}`);
        if (res.ok) {
          const data = await res.json();
          if (!cancelled) setRun(data);
        } else if (res.status === 404) {
          console.warn(`Run ${params.run_id} not found`);
          if (!cancelled) setError("Run not found or has been deleted");
        } else {
          console.warn(`Failed to fetch run ${params.run_id}: ${res.status}`);
          if (!cancelled) setError("Failed to load run");
        }
      } catch (e) {
        console.warn("Error loading run", e);
        if (!cancelled) setError("Failed to load run");
      }
    }
    load();

    (async () => {
      const url = await getWSUrl("/stream");
      const ws = new WebSocket(url);
      wsRef.current = ws;
      ws.onopen = () => {
        ws.send(JSON.stringify({ run_id: params.run_id }));
      };
      ws.onmessage = (evt) => {
        const msg = JSON.parse(evt.data);
        setRun((prev) => {
          if (!prev) return prev;
          if (msg.status === "done") {
            ws.close();
            return {
              ...prev,
              status: "done",
              html: msg.html ?? prev.html,
              summary: msg.summary ?? prev.summary,
              completed_at: msg.completed_at ?? prev.completed_at,
            };
          }
          return prev;
        });
      };
      ws.onerror = () => ws.close();
    })();
    return () => {
      cancelled = true;
      wsRef.current?.close();
    };
  }, [params.run_id]);

  if (error)
    return (
      <div className="p-6 space-y-2">
        <p>{error}</p>
        <Link href="/" className="text-blue-500 underline">
          Back to runs
        </Link>
      </div>
    );

  if (!run) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6 space-y-4">
      <div className="space-y-1">
        <h1 className="text-xl font-semibold">Run {run.run_id}</h1>
        <p className="text-sm text-muted-foreground">Objective: {run.objective}</p>
        <p className="text-sm text-muted-foreground">Status: {run.status}</p>
        <p className="text-sm text-muted-foreground">
          Started: {new Date(run.created_at).toLocaleString()}
        </p>
        {run.completed_at && (
          <p className="text-sm text-muted-foreground">
            Ended: {new Date(run.completed_at).toLocaleString()}
          </p>
        )}
      </div>
      <RunTimeline runId={run.run_id} refreshKey={run.status} />
      {run.status === "done" && (
        <div className="space-y-4">
          {run.summary && <p>{run.summary}</p>}
          {run.html && (
            <div className="prose" dangerouslySetInnerHTML={{ __html: run.html }} />
          )}
        </div>
      )}
    </div>
  );
}
