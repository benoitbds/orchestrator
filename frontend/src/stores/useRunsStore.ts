import { create } from "zustand";
import { persist } from "zustand/middleware";

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

const hashString = (str: string): string => {
  let hash = 2166136261;
  for (let i = 0; i < str.length; i++) {
    hash ^= str.charCodeAt(i);
    hash +=
      (hash << 1) + (hash << 4) + (hash << 7) + (hash << 8) + (hash << 24);
  }
  return (hash >>> 0).toString(16);
};

export type RunData = {
  events: AgentEvent[];
  summary?: string;
  startedAt: number;
  finishedAt?: number;
  status: "running" | "completed" | "failed";
  lastSummaryHash?: string;
};

type RunState = {
  currentRunId?: string;
  runs: Record<string, RunData>;

  startRun: (runId: string) => void;
  pushEvent: (runId: string, event: AgentEvent) => void;
  finishRun: (runId: string, summary: string) => void;
  failRun: (runId: string, error: string) => void;
  upgradeRunId: (tempId: string, realId: string) => void;
  appendSummaryOnce: (runId: string, summary: string) => void;
  setCurrent: (runId?: string) => void;
  clearRuns: () => void;

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
              status: "running",
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
                events: [
                  ...run.events,
                  { ...event, ts: event.ts || new Date().toISOString() },
                ],
              },
            },
          };
        }),

      appendSummaryOnce: (runId: string, summary: string) =>
        set((state) => {
          const run = state.runs[runId];
          if (!run) return state;
          const hash = hashString(summary);
          if (run.lastSummaryHash === hash) return state;
          return {
            runs: {
              ...state.runs,
              [runId]: { ...run, summary, lastSummaryHash: hash },
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
                status: "completed",
              },
            },
            currentRunId:
              state.currentRunId === runId ? undefined : state.currentRunId,
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
                status: "failed",
                summary: error,
              },
            },
            currentRunId:
              state.currentRunId === runId ? undefined : state.currentRunId,
          };
        }),

      upgradeRunId: (tempId: string, realId: string) =>
        set((state) => {
          const run = state.runs[tempId];
          if (!run) return state;
          const { [tempId]: _removed, ...rest } = state.runs;
          return {
            runs: { ...rest, [realId]: run },
            currentRunId:
              state.currentRunId === tempId ? realId : state.currentRunId,
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
        return runs[currentRunId]?.status === "running";
      },
    }),
    {
      name: "agent-runs-storage",
      // Don't persist currentRunId to avoid reconnecting to old runs
      partialize: (state) => ({ runs: state.runs }),
      skipHydration: true,
    },
  ),
);
