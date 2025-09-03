"use client";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { http } from "@/lib/api";
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

interface CostInfo {
  tokens: number;
  cost: number;
  by_agent: Record<string, { tokens: number; cost: number }>;
}

export default function RunTimeline({ runId }: { runId: string }) {
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [cost, setCost] = useState<CostInfo | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCost, setShowCost] = useState(false);
  const [modal, setModal] = useState<{ title: string; content: string } | null>(null);

  useEffect(() => {
    let cancelled = false;
    async function load() {
      try {
        setLoading(true);
        const [tRes, cRes] = await Promise.all([
          http(`/runs/${runId}/timeline`),
          http(`/runs/${runId}/cost`),
        ]);
        if (!tRes.ok || !cRes.ok) throw new Error("fetch failed");
        const tData = await tRes.json();
        const cData = await cRes.json();
        if (!cancelled) {
          setEvents(tData.events || []);
          setCost(cData);
          setError(null);
        }
      } catch (e) {
        if (!cancelled) setError("Failed to load timeline");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, [runId]);

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
        const res = await http(`/blobs/${evt.ref}`);
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
      {cost && (
        <div className="absolute right-0 -top-2">
          <Badge
            className="cursor-pointer"
            onClick={() => setShowCost((c) => !c)}
          >
            Tokens: {cost.tokens} | Cost: €{cost.cost.toFixed(2)}
            {showCost ? (
              <ChevronUp className="ml-1 size-3" />
            ) : (
              <ChevronDown className="ml-1 size-3" />
            )}
          </Badge>
          {showCost && (
            <div className="mt-2 rounded border bg-background p-2">
              <table className="text-xs">
                <tbody>
                  {Object.entries(cost.by_agent || {}).map(([agent, info]) => (
                    <tr key={agent}>
                      <td className="pr-2">{agent}</td>
                      <td className="pr-2 text-right">{info.tokens}</td>
                      <td className="text-right">€{info.cost.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
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
