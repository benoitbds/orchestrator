"use client";
import { useState } from "react";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";

export interface TimelineStep {
  order: number;
  node: string;
  timestamp: string;
  content: string;
}

interface TimelineProps {
  steps: TimelineStep[];
}

export default function RunTimeline({ steps }: TimelineProps) {
  const [selected, setSelected] = useState<TimelineStep | null>(null);
  return (
    <div>
      <ul className="divide-y rounded border">
        {steps.map((s) => (
          <li
            key={s.order}
            className="p-2 cursor-pointer hover:bg-muted/50"
            onClick={() => setSelected(s)}
          >
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs w-6">{s.order}</span>
              <span className="text-sm font-medium flex-1">{s.node}</span>
              <span className="text-xs text-muted-foreground">
                {new Date(s.timestamp).toLocaleTimeString()}
              </span>
            </div>
            <p className="text-xs text-muted-foreground truncate">
              {s.content}
            </p>
          </li>
        ))}
        {steps.length === 0 && (
          <li className="p-2 text-sm text-muted-foreground">No steps yet</li>
        )}
      </ul>
      <Dialog open={!!selected} onOpenChange={(o) => !o && setSelected(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>
              Step {selected?.order}: {selected?.node}
            </DialogTitle>
          </DialogHeader>
          <div className="mt-2 whitespace-pre-wrap text-sm">
            {selected?.content}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
