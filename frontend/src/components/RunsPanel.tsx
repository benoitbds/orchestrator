"use client";
import { useEffect, useState } from "react";
import RunProgress from "./RunProgress";
import { useProjects } from "@/context/ProjectContext";
import { apiFetch } from "@/lib/api";

interface Run {
  run_id: string;
  status: string;
  steps: { step: string; start: string; end: string }[];
}

export default function RunsPanel({ refreshKey = 0 }: { refreshKey?: number }) {
  const { currentProject } = useProjects();
  const [runs, setRuns] = useState<Run[]>([]);

  useEffect(() => {
    if (!currentProject) return;
    let cancelled = false;
    const projectId = currentProject.id;
    async function fetchRuns() {
      try {
        const res = await apiFetch(`/runs?project_id=${projectId}`);
        if (res.ok) {
          const data = await res.json();
          if (Array.isArray(data)) {
            !cancelled && setRuns(data);
          } else if (data && Array.isArray((data as any).runs)) {
            !cancelled && setRuns((data as any).runs);
          } else {
            !cancelled && setRuns([]);
          }
        } else {
          console.warn(`Failed to fetch runs: ${res.status}`);
          !cancelled && setRuns([]);
        }
      } catch (e) {
        console.warn("Error fetching runs", e);
        !cancelled && setRuns([]);
      }
    }
    fetchRuns();
    return () => {
      cancelled = true;
    };
  }, [currentProject, refreshKey]);

  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold text-gray-800">Historique des runs</h2>
      {runs.map(run => (
        <RunProgress key={run.run_id} run={run} />
      ))}
    </section>
  );
}
