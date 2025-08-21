"use client";
import { useEffect, useState } from "react";
import Timeline, { TimelineStep } from "@/components/Timeline";
import { http } from "@/lib/api";

interface Run {
  run_id: string;
  status: "running" | "done";
  html?: string | null;
  summary?: string | null;
  steps: TimelineStep[];
}

export default function RunDetail({ params }: { params: { runId: string } }) {
  const [run, setRun] = useState<Run | null>(null);
  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    let cancelled = false;
    const fetchRun = async () => {
      const res = await http(`/runs/${params.runId}`);
      if (!res.ok) return;
      const data = await res.json();
      if (!cancelled) {
        setRun(data);
        if (data.status === "running") {
          timer = setTimeout(fetchRun, 3000);
        }
      }
    };
    fetchRun();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [params.runId]);

  if (!run) return <div className="p-6">Loading...</div>;

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Run {params.runId}</h1>
      <Timeline steps={run.steps} />
      {run.status === "done" && (
        <>
          {run.html && (
            <div className="prose" dangerouslySetInnerHTML={{ __html: run.html }} />
          )}
          {run.summary && <p>{run.summary}</p>}
        </>
      )}
    </div>
  );
}
