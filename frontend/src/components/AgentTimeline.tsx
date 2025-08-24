"use client";
import { Loader2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";

export interface AgentTimelineStep {
  runId: string;
  node: string;
  content?: any;
  timestamp?: string;
}

interface AgentTimelineProps {
  steps: AgentTimelineStep[];
}

function truncate(text: string, max = 60): string {
  return text.length > max ? text.slice(0, max) + "…" : text;
}

function formatStep(step: AgentTimelineStep): { label: string; status: "pending" | "ok" | "error" } {
  const { node, content } = step;
  if (node.startsWith("tool:")) {
    const [, tool, phase] = node.split(":");
    if (phase === "request") {
      const args = content?.args ? JSON.stringify(content.args) : "";
      return {
        label: `${tool}(request) — ${truncate(args)}`,
        status: "pending",
      };
    }
    if (phase === "response") {
      const ok = content?.ok;
      const result = content?.result ? JSON.stringify(content.result) : "";
      return {
        label: `${tool}(response) — ok=${ok} ${truncate(result)}`,
        status: ok ? "ok" : "error",
      };
    }
  }
  if (node === "error") {
    const msg = typeof content === "string" ? content : content?.error;
    return { label: `error — ${truncate(msg || "")}`, status: "error" };
  }
  return { label: node, status: "ok" };
}

export default function AgentTimeline({ steps }: AgentTimelineProps) {
  const grouped = steps.reduce<Record<string, AgentTimelineStep[]>>((acc, s) => {
    acc[s.runId] = acc[s.runId] || [];
    acc[s.runId].push(s);
    return acc;
  }, {});

  if (steps.length === 0) {
    return <div className="text-sm text-muted-foreground">No steps yet</div>;
  }

  return (
    <div className="space-y-4">
      {Object.entries(grouped).map(([runId, runSteps]) => (
        <div key={runId}>
          <h3 className="mb-2 text-sm font-medium">Run {runId}</h3>
          <ul className="space-y-2">
            {runSteps.map((s, i) => {
              const { label, status } = formatStep(s);
              const time = s.timestamp ? new Date(s.timestamp).toLocaleTimeString() : "";
              return (
                <li key={i} className="rounded-md border p-2">
                  <div className="mb-1 flex items-center justify-between">
                    <span className="text-[10px] text-muted-foreground">{time}</span>
                    {status === "pending" ? (
                      <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />
                    ) : (
                      <Badge variant={status === "ok" ? "secondary" : "destructive"}>{status}</Badge>
                    )}
                  </div>
                  <code className="block truncate font-mono text-xs">{label}</code>
                </li>
              );
            })}
          </ul>
        </div>
      ))}
    </div>
  );
}
