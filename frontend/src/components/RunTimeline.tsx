"use client";
import { useEffect, useRef, useState } from "react";
import { Loader2 } from "lucide-react";
import useRunWatcher from "@/hooks/useRunWatcher";
import { Step, normalizeStep } from "@/models/run";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

interface TimelineProps {
  runId: string | null;
  initialSteps?: Step[];
  onStep?: (step: Step) => void;
  onFinal?: (payload: any) => void;
}

const LABELS: Record<string, string> = {
  plan: "Planification",
  "tool:create_item": "Création",
  "tool:update_item": "Mise à jour",
  error: "Erreur",
  final: "Terminé",
};

export default function RunTimeline({ runId, initialSteps = [], onStep, onFinal }: TimelineProps) {
  const [steps, setSteps] = useState<Step[]>(initialSteps);
  const [running, setRunning] = useState<boolean>(!!runId);
  const [selected, setSelected] = useState<Step | null>(null);
  const listRef = useRef<HTMLUListElement | null>(null);

  useEffect(() => {
    setSteps(initialSteps);
  }, [initialSteps]);

  useEffect(() => {
    setRunning(!!runId);
  }, [runId]);

  useRunWatcher({
    runId,
    onStep: msg => {
      setSteps(prev => {
        const step = normalizeStep(msg);
        step.order = step.order ?? prev.length + 1;
        step.timestamp = step.timestamp ?? new Date().toISOString();
        onStep?.(step);
        return [...prev, step];
      });
    },
    onFinal: payload => {
      setSteps(prev => [
        ...prev,
        {
          order: prev.length + 1,
          node: "final",
          timestamp: new Date().toISOString(),
          content: "",
        },
      ]);
      setRunning(false);
      onFinal?.(payload);
    },
  });

  useEffect(() => {
    if (!listRef.current) return;
    listRef.current.scrollTop = listRef.current.scrollHeight;
  }, [steps]);

  return (
    <div>
      <div className="flex items-center gap-2 mb-2">
        <h2 className="font-semibold">Timeline</h2>
        {running && <Loader2 className="h-3 w-3 animate-spin" />}
      </div>
      <ul className="divide-y rounded border max-h-64 overflow-auto" ref={listRef}>
        {steps.map(s => (
          <li
            key={s.order}
            className="p-2 cursor-pointer hover:bg-muted/50"
            onClick={() => setSelected(s)}
          >
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs w-6">{s.order}</span>
              <span className="text-sm font-medium flex-1">{LABELS[s.node] || s.node}</span>
              {s.timestamp && (
                <span className="text-xs text-muted-foreground">
                  {new Date(s.timestamp).toLocaleTimeString()}
                </span>
              )}
            </div>
            {s.content && (
              <p className="text-xs text-muted-foreground truncate">
                {typeof s.content === "string" ? s.content : JSON.stringify(s.content)}
              </p>
            )}
          </li>
        ))}
        {steps.length === 0 && (
          <li className="p-2 text-sm text-muted-foreground">No steps yet</li>
        )}
      </ul>
      <Dialog open={!!selected} onOpenChange={o => !o && setSelected(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Step {selected?.order}: {LABELS[selected?.node || ""] || selected?.node}
            </DialogTitle>
          </DialogHeader>
          <div className="mt-2 whitespace-pre-wrap text-sm">
            {typeof selected?.content === "string"
              ? selected?.content
              : JSON.stringify(selected?.content, null, 2)}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
