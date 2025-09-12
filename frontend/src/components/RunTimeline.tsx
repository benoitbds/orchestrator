"use client";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { apiFetch } from "@/lib/api";
import { getRunCost, RunCost } from "@/lib/runs";
import { Bot, ChevronDown, ChevronUp, User, Wrench } from "lucide-react";

interface BaseEvent {
  id?: string;
  type: string;
  timestamp: string;
}

interface AgentStart extends BaseEvent {
  type: "agent.span.start";
  name: string;
}

interface AgentEnd extends BaseEvent {
  type: "agent.span.end";
  name: string;
  duration: number;
}

interface MessageEvent extends BaseEvent {
  type: "message";
  role: string;
  content: string;
  ref?: string;
}

interface ToolCall extends BaseEvent {
  type: "tool.call";
  name: string;
}

interface ToolResult extends BaseEvent {
  type: "tool.result";
  name: string;
}

export type TimelineEvent =
  | AgentStart
  | AgentEnd
  | MessageEvent
  | ToolCall
  | ToolResult;

export default function RunTimeline({
  runId,
  refreshKey,
}: {
  runId: string;
  refreshKey?: unknown;
}) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [cost, setCost] = useState<RunCost | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [costLoading, setCostLoading] = useState(true);
  const [costError, setCostError] = useState(false);
  const [showCost, setShowCost] = useState(false);
  const [modal, setModal] = useState<{ title: string; content: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function loadTimeline() {
      try {
        setLoading(true);
        const res = await apiFetch(`/runs/${runId}/timeline`);
        if (!res.ok) throw new Error('failed');
        const data = await res.json();
        if (!cancelled) {
          setEvents(data.events || []);
          setError(null);
        }
      } catch {
        if (!cancelled) setError('Failed to load timeline');
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    loadTimeline();
    return () => {
      cancelled = true;
    };
  }, [runId]);

  useEffect(() => {
    let cancelled = false;
    async function loadCost() {
      try {
        setCostLoading(true);
        const data = await getRunCost(runId);
        if (!cancelled) {
          setCost(data);
          setCostError(false);
        }
      } catch {
        if (!cancelled) {
          setCost(null);
          setCostError(true);
        }
      } finally {
        if (!cancelled) setCostLoading(false);
      }
    }
    loadCost();
    return () => {
      cancelled = true;
    };
  }, [runId, refreshKey]);

  function roleIcon(role: string) {
    switch (role) {
      case "user":
        return <User className="mt-1 size-4" />;
      default:
        return <Bot className="mt-1 size-4" />;
    }
  }

  async function openMessage(evt: MessageEvent) {
    try {
      if (evt.ref) {
        const res = await apiFetch(`/blobs/${evt.ref}`);
        const text = res.ok ? await res.text() : "Failed to load content";
        setModal({ title: `${evt.role} message`, content: text });
      } else {
        setModal({ title: `${evt.role} message`, content: evt.content });
      }
    } catch {
      setModal({ title: `${evt.role} message`, content: "Failed to load content" });
    }
  }

  function renderEvent(evt: TimelineEvent, idx: number) {
    switch (evt.type) {
      case "agent.span.start":
        return (
          <Badge variant="secondary">▶ Agent {evt.name}</Badge>
        );
      case "agent.span.end":
        return (
          <Badge variant="outline">■ Agent {evt.name} ({evt.duration.toFixed(2)}s)</Badge>
        );
      case "message":
        return (
          <div className="flex items-start gap-2">
            {roleIcon(evt.role)}
            <div className="flex-1 truncate rounded bg-muted p-2 text-sm">
              {evt.content}
            </div>
            <Button
              variant="link"
              className="h-auto p-0"
              onClick={() => openMessage(evt)}
            >
              View
            </Button>
          </div>
        );
      case "tool.call":
        return (
          <div className="ml-4 flex items-center gap-1 text-xs text-muted-foreground">
            <Wrench className="size-3" /> call {evt.name}
          </div>
        );
      case "tool.result":
        return (
          <div className="ml-4 flex items-center gap-1 text-xs text-muted-foreground">
            <Wrench className="size-3" /> result {evt.name}
          </div>
        );
      default:
        return null;
    }
  }

  if (loading) return <div>Loading timeline...</div>;
  if (error) return <div className="text-destructive">{error}</div>;

  return (
    <div className="relative">
      <div className="absolute right-0 -top-2">
        {costLoading && (
          <Badge className="animate-pulse">Loading...</Badge>
        )}
        {!costLoading && cost && (
          <div>
            <Badge
              className="cursor-pointer"
              onClick={() => setShowCost((c) => !c)}
            >
              Tokens: {cost.total_tokens} | Cost: €{cost.cost_eur.toFixed(4)}
              {showCost ? (
                <ChevronUp className="ml-1 size-3" />
              ) : (
                <ChevronDown className="ml-1 size-3" />
              )}
            </Badge>
            {showCost && (
              <div className="mt-2 rounded border bg-background p-2">
                {cost.by_agent.length > 0 ? (
                  <table className="text-xs">
                    <thead>
                      <tr>
                        <th className="pr-2 text-left">agent</th>
                        <th className="pr-2 text-right">prompt</th>
                        <th className="pr-2 text-right">completion</th>
                        <th className="pr-2 text-right">total</th>
                        <th className="text-right">€</th>
                      </tr>
                    </thead>
                    <tbody>
                      {cost.by_agent.map((row) => (
                        <tr key={row.agent}>
                          <td className="pr-2">{row.agent}</td>
                          <td className="pr-2 text-right">{row.prompt_tokens}</td>
                          <td className="pr-2 text-right">{row.completion_tokens}</td>
                          <td className="pr-2 text-right">{row.total_tokens}</td>
                          <td className="text-right">€{row.cost_eur.toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                ) : (
                  <div className="text-xs text-muted-foreground">No cost data</div>
                )}
              </div>
            )}
          </div>
        )}
        {!costLoading && costError && (
          <Badge variant="destructive">Cost unavailable</Badge>
        )}
      </div>
      <ul className="space-y-4 border-l pl-4">
        {events.map((evt, idx) => (
          <li key={evt.id || idx} className="relative">
            <span className="absolute -left-2 top-1 size-2 rounded-full bg-primary" />
            {renderEvent(evt, idx)}
          </li>
        ))}
        {events.length === 0 && (
          <li className="text-sm text-muted-foreground">No events</li>
        )}
      </ul>
      <Dialog open={!!modal} onOpenChange={(o) => !o && setModal(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>{modal?.title}</DialogTitle>
          </DialogHeader>
          <div className="whitespace-pre-wrap text-sm">{modal?.content}</div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
