"use client";
import Link from "next/link";

interface Step {
  step: string;
  start: string;
  end: string;
}

interface Run {
  run_id: string;
  status: string;
  steps?: Step[];
}

const colors: Record<string, string> = {
  plan: "bg-blue-400",
  execute: "bg-yellow-400",
  write: "bg-green-400",
};

export default function RunTimeline({ run }: { run: Run }) {
  const steps = run.steps ?? [];
  const durations = steps.map(
    s => new Date(s.end).getTime() - new Date(s.start).getTime(),
  );
  const total = durations.reduce((a, b) => a + b, 0) || 1;
  return (
    <div className="space-y-1">
      <div className="flex h-2 w-full overflow-hidden rounded">
        {steps.length === 0 ? (
          <div
            data-testid="timeline-loading"
            className="h-full w-full animate-pulse rounded bg-gray-200"
          />
        ) : (
          steps.map((s, i) => (
            <div
              key={s.step}
              className={`${colors[s.step] || "bg-gray-400"} h-full`}
              style={{ width: `${(durations[i] / total) * 100}%` }}
              title={s.step}
            />
          ))
        )}
      </div>
      <Link href={`/runs/${run.run_id}`} className="text-xs text-blue-500 hover:underline">
        Détails du run
      </Link>
    </div>
  );
}
