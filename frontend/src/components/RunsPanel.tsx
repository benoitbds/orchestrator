"use client";
import { useEffect, useState } from "react";
import RunTimeline from "./RunTimeline";
import { useProjects } from "@/context/ProjectContext";
import { http } from "@/lib/api";

interface Run {
  run_id: string;
  status: string;
  steps: { step: string; start: string; end: string }[];
}

export default function RunsPanel() {
  const { currentProject } = useProjects();
  const [runs, setRuns] = useState<Run[]>([]);

  useEffect(() => {
    if (!currentProject) return;
    http(`/runs?project_id=${currentProject.id}`)
      .then(r => r.json())
      .then(data => {
        if (Array.isArray(data)) {
          setRuns(data);
        } else if (data && Array.isArray((data as any).runs)) {
          setRuns((data as any).runs);
        } else {
          setRuns([]);
        }
      })
      .catch(() => setRuns([]));
  }, [currentProject]);

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-800">Historique des runs</h2>
      {runs.map(run => (
        <RunTimeline key={run.run_id} run={run} />
      ))}
    </section>
  );
}
