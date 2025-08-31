import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export type AgentEvent = {
  node: string;
  ts?: string;
  ok?: boolean;
  result?: any;
  args?: any;
  error?: string;
  content?: any;
  timestamp?: string;
};

export type RunData = {
  events: AgentEvent[];
  summary?: string;
  startedAt: number;
  finishedAt?: number;
  status: 'running' | 'completed' | 'failed';
};

type RunState = {
  currentRunId?: string;
  runs: Record<string, RunData>;
  
  // Actions
  startRun: (runId: string) => void;
  pushEvent: (runId: string, event: AgentEvent) => void;
  finishRun: (runId: string, summary: string) => void;
  failRun: (runId: string, error: string) => void;
  setCurrent: (runId?: string) => void;
  clearRuns: () => void;
  
  // Getters
  getCurrentRun: () => RunData | undefined;
  getEvents: (runId: string) => AgentEvent[];
  isRunning: () => boolean;
};

export const useRunsStore = create<RunState>()(
  persist(
    (set, get) => ({
      currentRunId: undefined,
      runs: {},

  startRun: (runId: string) =>
    set((state) => ({
      currentRunId: runId,
      runs: {
        ...state.runs,
        [runId]: {
          events: [],
          startedAt: Date.now(),
          status: 'running',
        },
      },
    })),

  pushEvent: (runId: string, event: AgentEvent) =>
    set((state) => {
      const run = state.runs[runId];
      if (!run) return state;

      return {
        runs: {
          ...state.runs,
          [runId]: {
            ...run,
            events: [...run.events, { ...event, ts: event.ts || new Date().toISOString() }],
          },
        },
      };
    }),

  finishRun: (runId: string, summary: string) =>
    set((state) => {
      const run = state.runs[runId];
      if (!run) return state;

      return {
        runs: {
          ...state.runs,
          [runId]: {
            ...run,
            summary,
            finishedAt: Date.now(),
            status: 'completed',
          },
        },
        currentRunId: state.currentRunId === runId ? undefined : state.currentRunId,
      };
    }),

  failRun: (runId: string, error: string) =>
    set((state) => {
      const run = state.runs[runId];
      if (!run) return state;

      return {
        runs: {
          ...state.runs,
          [runId]: {
            ...run,
            finishedAt: Date.now(),
            status: 'failed',
            summary: error,
          },
        },
        currentRunId: state.currentRunId === runId ? undefined : state.currentRunId,
      };
    }),

  setCurrent: (runId?: string) =>
    set(() => ({
      currentRunId: runId,
    })),

  clearRuns: () =>
    set(() => ({
      currentRunId: undefined,
      runs: {},
    })),

  getCurrentRun: () => {
    const { currentRunId, runs } = get();
    return currentRunId ? runs[currentRunId] : undefined;
  },

  getEvents: (runId: string) => {
    const { runs } = get();
    return runs[runId]?.events || [];
  },

  isRunning: () => {
    const { currentRunId, runs } = get();
    if (!currentRunId) return false;
    return runs[currentRunId]?.status === 'running';
  },
    }),
    {
      name: 'agent-runs-storage',
      // Don't persist currentRunId to avoid reconnecting to old runs
      partialize: (state) => ({ runs: state.runs }),
      skipHydration: true,
    }
  )
);