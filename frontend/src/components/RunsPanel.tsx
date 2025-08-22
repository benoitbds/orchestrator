"use client";
import { useEffect, useState } from "react";
import RunProgress from "./RunProgress";
import { useProjects } from "@/context/ProjectContext";
import { fetchRuns } from "@/state/data";

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
    async function loadRuns() {
      try {
        const data = await fetchRuns(currentProject.id);
        !cancelled && setRuns(data);
      } catch (e) {
        console.warn("Error fetching runs", e);
        !cancelled && setRuns([]);
      }
    }
    loadRuns();
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
