import { useEffect, useRef, useState } from "react";
import { useRunsStore } from "@/stores/useRunsStore";
import { connectWS } from "@/lib/ws";
import { useHistory } from "@/store/useHistory";
import { toLabel } from "@/lib/historyAdapter";

type RunPhase =
  | "idle"
  | "connecting"
  | "started"
  | "streaming"
  | "finished"
  | "error";

interface UseAgentStreamOptions {
  onFinish?: (summary: string) => void;
  onError?: (error: string) => void;
  onRunIdUpdate?: (tempRunId: string, realRunId: string) => void;
  objective?: string;
  projectId?: number;
}

export function useAgentStream(
  runId: string | undefined,
  options: UseAgentStreamOptions = {},
): { connected: boolean; disconnect: () => void } {
  const [connected, setConnected] = useState(false);
  const runRef = useRef<{
    tempRunId: string;
    realRunId?: string;
    phase: RunPhase;
    ws?: WebSocket | null;
    objectiveSent: boolean;
    reconnectAttempts: number;
  } | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const maxReconnectAttempts = 5;
  const baseDelay = 1000;

  const { pushEvent, finishRun, failRun, upgradeRunId, appendSummaryOnce } =
    useRunsStore();

  const cleanupRun = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }
    const r = runRef.current;
    if (r?.ws) {
      try {
        r.ws.close();
      } catch {}
    }
    runRef.current = null;
    setConnected(false);
  };

  const connect = () => {
    const r = runRef.current;
    if (!r) return;
    try {
      const ws = connectWS("/stream");
      r.ws = ws;

      ws.onopen = () => {
        setConnected(true);
        r.reconnectAttempts = 0;
        if (r.phase === "connecting" && !r.objectiveSent) {
          if (options.objective && options.projectId) {
            ws.send(
              JSON.stringify({
                objective: options.objective,
                project_id: options.projectId,
              }),
            );
            r.objectiveSent = true;
          }
        } else if (r.realRunId) {
          ws.send(JSON.stringify({ run_id: r.realRunId }));
        }
      };

      ws.onmessage = (ev) => {
        const data = JSON.parse(ev.data);
        const current = runRef.current;
        if (!current) return;

        if (data.status === "started" && data.run_id) {
          if (!current.realRunId) {
            current.realRunId = data.run_id;
            current.phase = "streaming";
            upgradeRunId(current.tempRunId, data.run_id);
            useHistory.getState().promoteTurn(current.tempRunId, data.run_id);
            options.onRunIdUpdate?.(current.tempRunId, data.run_id);
          }
          return;
        }

        if (
          data.run_id &&
          current.realRunId &&
          data.run_id !== current.realRunId
        ) {
          return;
        }

        if (data.error) {
          failRun(current.realRunId ?? current.tempRunId, data.error);
          useHistory
            .getState()
            .finalizeTurn(current.realRunId ?? current.tempRunId, false);
          options.onError?.(data.error);
          current.phase = "error";
          cleanupRun();
          return;
        }

        if (data.node?.startsWith("tool:")) {
          const turnId = current.realRunId ?? current.tempRunId;
          if (data.node.endsWith(":request")) {
            useHistory.getState().appendAction(turnId, {
              id: data.id || crypto.randomUUID(),
              label: toLabel(data.node),
              technicalName: data.node,
              startedAt: data.ts ? Date.parse(data.ts) : Date.now(),
              status: "running",
              debug: { input: data.args },
            });
          } else if (data.node.endsWith(":response")) {
            const finished = data.ts ? Date.parse(data.ts) : Date.now();
            const state = useHistory.getState();
            const real = state.promoted[turnId] || turnId;
            const action = state.turns[real]?.actions.find((a) => a.id === data.id);
            const duration = action?.startedAt
              ? finished - action.startedAt
              : undefined;
            state.patchAction(turnId, data.id, {
              status: data.error || data.ok === false ? "failed" : "succeeded",
              finishedAt: finished,
              durationMs: duration,
              debug: { output: data.result, error: data.error },
            });
          }
          pushEvent(current.realRunId ?? current.tempRunId, data);
          return;
        }

        if (data.node === "write" && data.summary) {
          const id = current.realRunId ?? current.tempRunId;
          appendSummaryOnce(id, data.summary);
          useHistory.getState().setAgentTextOnce(id, data.summary);
          return;
        }

        if (data.status === "done") {
          const id = current.realRunId ?? current.tempRunId;
          const { runs } = useRunsStore.getState();
          const summary = runs[id]?.summary || data.summary || "Task completed";
          finishRun(id, summary);
          useHistory.getState().finalizeTurn(id, true);
          options.onFinish?.(summary);
          current.phase = "finished";
          cleanupRun();
        }
      };

      ws.onclose = (e) => {
        setConnected(false);
        const current = runRef.current;
        if (
          current &&
          (e.code === 1005 || e.code === 1006) &&
          current.realRunId &&
          (current.phase === "started" || current.phase === "streaming") &&
          current.reconnectAttempts < maxReconnectAttempts
        ) {
          const delay = baseDelay * Math.pow(2, current.reconnectAttempts);
          reconnectTimeoutRef.current = setTimeout(() => {
            current.reconnectAttempts += 1;
            connect();
          }, delay);
          return;
        }
        cleanupRun();
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
      };
    } catch (err) {
      console.error("Failed to connect WebSocket:", err);
      setConnected(false);
    }
  };

  useEffect(() => {
    if (!runId) {
      cleanupRun();
      return;
    }

    if (!runRef.current || runRef.current.tempRunId !== runId) {
      cleanupRun();
      runRef.current = {
        tempRunId: runId,
        phase: "connecting",
        objectiveSent: false,
        ws: null,
        reconnectAttempts: 0,
      };
      connect();
    }

    return () => {
      cleanupRun();
    };
  }, [runId, options.objective, options.projectId]);

  const disconnect = () => {
    cleanupRun();
  };

  return { connected, disconnect };
}
