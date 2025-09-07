import { create } from 'zustand';
import { useMemo } from 'react';

export type AgentActionPhase = 'request' | 'response' | 'unknown';
export type AgentAction = {
  id: string;
  runId: string;
  tool: string;
  phase: AgentActionPhase;
  createdAt: number;
  payload: any;
  ok?: boolean;
};

type ActionsByRun = Record<string, Record<string, AgentAction>>;

type AgentActionsState = {
  actions: ActionsByRun;
  done: Record<string, boolean>;
  addFromMessage: (msg: any) => void;
  clear: (runId?: string) => void;
};

function hashString(str: string): string {
  let hash = 2166136261;
  for (let i = 0; i < str.length; i++) {
    hash ^= str.charCodeAt(i);
    hash +=
      (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
  }
  return (hash >>> 0).toString(16);
}

function deriveToolPhase(msg: any): { tool?: string; phase: AgentActionPhase } {
  if (msg.tool && msg.phase) {
    return { tool: msg.tool, phase: msg.phase };
  }
  const node: string | undefined = msg.node;
  if (typeof node === 'string' && node.startsWith('tool:')) {
    const parts = node.split(':');
    return { tool: parts[1], phase: (parts[2] as AgentActionPhase) || 'unknown' };
  }
  return { phase: 'unknown' };
}

export const useAgentActionsStore = create<AgentActionsState>((set) => ({
  actions: {},
  done: {},
  addFromMessage: (msg: any) =>
    set((state) => {
      const runId: string | undefined = msg.run_id;
      if (!runId) return state;

      if (msg.status === 'done') {
        return { ...state, done: { ...state.done, [runId]: true } };
      }

      const { tool, phase } = deriveToolPhase(msg);
      if (!tool) return state;

      const payload =
        phase === 'request'
          ? msg.args || msg.data || {}
          : phase === 'response'
          ? msg.data || msg.result || {}
          : msg.args || msg.data || msg.result || {};
      const ok = phase === 'response' ? msg.ok ?? true : undefined;
      const hash = hashString(
        JSON.stringify(payload).slice(0, 512),
      );
      const id = `${runId}:${tool}:${phase}:${hash}`;
      const runActions = state.actions[runId] || {};
      if (runActions[id]) return state; // dedupe
      const action: AgentAction = {
        id,
        runId,
        tool,
        phase,
        createdAt: Date.now(),
        payload,
        ok,
      };
      return {
        actions: {
          ...state.actions,
          [runId]: { ...runActions, [id]: action },
        },
      };
    }),
  clear: (runId?: string) =>
    set((state) => {
      if (!runId) return { actions: {}, done: {} };
      const { [runId]: _removed, ...rest } = state.actions;
      const { [runId]: _d, ...restDone } = state.done;
      return { actions: rest, done: restDone };
    }),
}));

export function useAgentActions(runId: string | undefined) {
  const actionsMap = useAgentActionsStore((s) =>
    runId ? s.actions[runId] : undefined,
  );
  const done = useAgentActionsStore((s) => !!(runId && s.done[runId]));
  const actions = useMemo(() => {
    if (!actionsMap) return [] as AgentAction[];
    return Object.values(actionsMap).sort((a, b) => b.createdAt - a.createdAt);
  }, [actionsMap]);
  const addFromMessage = useAgentActionsStore((s) => s.addFromMessage);
  const clear = useAgentActionsStore((s) => s.clear);
  return { actions, addFromMessage, clear, done };
}
