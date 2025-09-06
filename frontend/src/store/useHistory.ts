import { create } from 'zustand';
import type { ConversationTurn, AgentAction } from '@/types/history';
import { hashText } from '@/lib/historyAdapter';

export type HistoryState = {
  turns: Record<string, ConversationTurn>;
  orderDesc: string[];
  promoted: Record<string, string>;
  createTurn: (tempId: string, userText: string) => void;
  promoteTurn: (tempId: string, realId: string) => void;
  appendAction: (turnId: string, action: AgentAction) => void;
  patchAction: (
    turnId: string,
    actionId: string,
    patch: Partial<AgentAction>,
  ) => void;
  setAgentTextOnce: (turnId: string, text: string) => void;
  finalizeTurn: (turnId: string, ok: boolean) => void;
};

export const useHistory = create<HistoryState>((set, get) => ({
  turns: {},
  orderDesc: [],
  promoted: {},
  createTurn: (tempId, userText) =>
    set((s) => ({
      turns: {
        ...s.turns,
        [tempId]: {
          turnId: tempId,
          createdAt: Date.now(),
          userText,
          actions: [],
          phase: 'running',
        },
      },
      orderDesc: [tempId, ...s.orderDesc],
    })),
  promoteTurn: (tempId, realId) =>
    set((s) => {
      const turn = s.turns[tempId];
      if (!turn) return s;
      const { [tempId]: _removed, ...rest } = s.turns;
      return {
        turns: { ...rest, [realId]: { ...turn, turnId: realId } },
        orderDesc: s.orderDesc.map((id) => (id === tempId ? realId : id)),
        promoted: { ...s.promoted, [tempId]: realId },
      };
    }),
  appendAction: (turnId, action) =>
    set((s) => {
      const realId = s.promoted[turnId] || turnId;
      const turn = s.turns[realId];
      if (!turn) return s;
      return {
        turns: {
          ...s.turns,
          [realId]: {
            ...turn,
            actions: [...turn.actions, action].sort(
              (a, b) => (a.startedAt ?? 0) - (b.startedAt ?? 0),
            ),
          },
        },
      };
    }),
  patchAction: (turnId, actionId, patch) =>
    set((s) => {
      const realId = s.promoted[turnId] || turnId;
      const turn = s.turns[realId];
      if (!turn) return s;
      const actions = turn.actions.map((a) =>
        a.id === actionId ? { ...a, ...patch } : a,
      );
      return { turns: { ...s.turns, [realId]: { ...turn, actions } } };
    }),
  setAgentTextOnce: (turnId, text) =>
    set((s) => {
      const realId = s.promoted[turnId] || turnId;
      const turn = s.turns[realId];
      if (!turn) return s;
      const h = hashText(text);
      if (turn.lastSummaryHash === h) return s;
      return {
        turns: {
          ...s.turns,
          [realId]: { ...turn, agentText: text, lastSummaryHash: h },
        },
      };
    }),
  finalizeTurn: (turnId, ok) =>
    set((s) => {
      const realId = s.promoted[turnId] || turnId;
      const turn = s.turns[realId];
      if (!turn) return s;
      return {
        turns: {
          ...s.turns,
          [realId]: { ...turn, phase: ok ? 'completed' : 'failed' },
        },
      };
    }),
}));
