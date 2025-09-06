import { useEffect, useRef, useState } from "react";
import { useRunsStore } from "@/stores/useRunsStore";
import { connectWS } from "@/lib/ws";

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
          options.onError?.(data.error);
          current.phase = "error";
          cleanupRun();
          return;
        }

        if (data.node?.startsWith("tool:")) {
          pushEvent(current.realRunId ?? current.tempRunId, data);
          return;
        }

        if (data.node === "write" && data.summary) {
          appendSummaryOnce(
            current.realRunId ?? current.tempRunId,
            data.summary,
          );
          return;
        }

        if (data.status === "done") {
          const id = current.realRunId ?? current.tempRunId;
          const { runs } = useRunsStore.getState();
          const summary = runs[id]?.summary || data.summary || "Task completed";
          finishRun(id, summary);
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
