"use client";
import { useEffect, useState } from "react";
import RunTimeline from "@/components/RunTimeline";
import { http } from "@/lib/api";

interface Run {
  run_id: string;
  status: string;
  html?: string | null;
  summary?: string | null;
  steps: { step: string; start: string; end: string }[];
}

export default function RunDetail({ params }: { params: { runId: string } }) {
  const [run, setRun] = useState<Run | null>(null);
  useEffect(() => {
    let cancelled = false;
    const fetchRun = async () => {
      const res = await http(`/runs/${params.runId}`);
      if (!res.ok) return;
      const data = await res.json();
      if (!cancelled) {
        setRun(data);
        if (data.status !== "success") {
          setTimeout(fetchRun, 1000);
        }
      }
    };
    fetchRun();
    return () => {
      cancelled = true;
    };
  }, [params.runId]);

  if (!run) return <div className="p-6">Chargement...</div>;

  return (
    <div className="p-6 space-y-4">
      <h1 className="text-xl font-semibold">Run {params.runId}</h1>
      <RunTimeline run={run} />
      {run.status === "success" && (
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
