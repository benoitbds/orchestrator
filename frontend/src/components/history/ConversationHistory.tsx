'use client';

import { useMemo } from 'react';
import { useRunsStore } from '@/stores/useRunsStore';
import { useMessagesStore } from '@/stores/useMessagesStore';
import { mapRunsToTurns } from '@/lib/mapRunsToTurns';
import type { ConversationTurn } from '@/types/conversation';
import { ConversationTurnCard } from './ConversationTurnCard';

interface Props {
  turns?: ConversationTurn[];
}

export function ConversationHistory({ turns: external }: Props) {
  const runs = useRunsStore((s) => s.runs);
  const messages = useMessagesStore((s) => s.messages);
  const turns = useMemo(
    () => external ?? mapRunsToTurns(runs, messages),
    [external, runs, messages]
  );
  const sorted = useMemo(
    () => [...turns].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()),
    [turns]
  );

  if (sorted.length === 0) {
    return <div className="text-sm text-muted-foreground">No conversation yet</div>;
  }

  return (
    <div className="flex flex-col gap-4">
      {sorted.map((t) => (
        <ConversationTurnCard key={t.id} turn={t} />
      ))}
    </div>
  );
}
