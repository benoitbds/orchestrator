import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { ConversationTurn, AgentAction } from '@/types/history';
import { hashText } from '@/lib/historyAdapter';

export type HistoryState = {
  turns: Record<string, ConversationTurn>;
  orderDesc: string[];
  promoted: Record<string, string>;
  createTurn: (tempId: string, userText: string, projectId: number) => void;
  promoteTurn: (tempId: string, realId: string) => void;
  appendAction: (turnId: string, action: AgentAction) => void;
  patchAction: (
    turnId: string,
    actionId: string,
    patch: Partial<AgentAction>,
  ) => void;
  setAgentTextOnce: (turnId: string, text: string) => void;
  finalizeTurn: (turnId: string, ok: boolean) => void;
  getTurnsByProject: (projectId: number) => ConversationTurn[];
  clearProjectTurns: (projectId: number) => void;
};

export const useHistory = create<HistoryState>()(
  persist(
    (set, get) => ({
      turns: {},
      orderDesc: [],
      promoted: {},
      createTurn: (tempId, userText, projectId) =>
        set((s) => ({
          turns: {
            ...s.turns,
            [tempId]: {
              turnId: tempId,
              createdAt: Date.now(),
              userText,
              projectId,
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
            orderDesc: s.orderDesc.map((id) =>
              id === tempId ? realId : id,
            ),
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
      getTurnsByProject: (projectId) => {
        const state = get();
        return state.orderDesc
          .filter((id) => state.turns[id]?.projectId === projectId)
          .map((id) => state.turns[id])
          .filter(Boolean);
      },
      clearProjectTurns: (projectId) =>
        set((s) => {
          const turnIdsToRemove = s.orderDesc.filter(
            (id) => s.turns[id]?.projectId === projectId
          );
          const newTurns = { ...s.turns };
          turnIdsToRemove.forEach((id) => delete newTurns[id]);
          return {
            turns: newTurns,
            orderDesc: s.orderDesc.filter((id) => !turnIdsToRemove.includes(id)),
          };
        }),
    }),
    {
      name: 'agent-history-storage',
      skipHydration: true,
    },
  ),
);

