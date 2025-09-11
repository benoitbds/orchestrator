import { useEffect, useRef, useState } from "react";
import { useRunsStore } from "@/stores/useRunsStore";
import { useHistory } from "@/store/useHistory";
import { toLabel } from "@/lib/historyAdapter";
import { safeId } from "@/lib/safeId";
import { http } from "@/lib/api";
import { useAgentActionsStore } from "@/hooks/useAgentActions";
import { getWSUrl } from "@/lib/ws";

// Phases for a run lifecycle
export type RunPhase =
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

interface RunState {
  tempRunId: string;
  realRunId?: string;
  phase: RunPhase;
  ws?: WebSocket | null;
  wsId?: string;
  objectiveSent: boolean;
  reconnectAttempts: number;
  keepAliveTimer?: any;
}

const now = () => Date.now();
let startRunDebounce = 0;

function backoffDelay(attempt: number) {
  const base = Math.min(1000 * Math.pow(2, attempt), 10_000);
  const jitter = Math.floor(Math.random() * 300);
  return base + jitter;
}

export function useAgentStream(
  runId: string | undefined,
  options: UseAgentStreamOptions = {},
): { connected: boolean; disconnect: () => void } {
  const [connected, setConnected] = useState(false);
  const runRef = useRef<RunState | null>(null);

  const { pushEvent, finishRun, failRun, upgradeRunId, appendSummaryOnce } =
    useRunsStore();

  // --- helpers --------------------------------------------------------------
  const safeCloseSocket = (tag: string) => {
    const r = runRef.current;
    if (!r?.ws) return;
    try {
      r.ws.close();
    } catch {
      /* noop */
    }
    r.ws = null;
  };

  const cleanupRun = (tag = "cleanup", wsId?: string) => {
    const r = runRef.current;
    if (!r) return;
    if (wsId && r.wsId !== wsId) return; // stale caller

    if (r.keepAliveTimer) {
      clearInterval(r.keepAliveTimer);
      r.keepAliveTimer = undefined;
    }

    safeCloseSocket(tag);
    runRef.current = null;
    setConnected(false);
  };

  const openSocket = (url: string, wsId: string): Promise<WebSocket> => {
    return new Promise((resolve, reject) => {
      let settled = false;
      const ws = new WebSocket(url);

      ws.onopen = () => {
        if (settled) return;
        settled = true;
        resolve(ws);
      };

      ws.onerror = (e) => {
        if (settled) return;
        settled = true;
        reject(e);
      };

      ws.onclose = (e) => {
        if (!settled) {
          settled = true;
          reject(e);
        }
      };
    });
  };

  const startRunInternal = async (
    objective?: string,
    projectId?: number,
  ) => {
    const t = now();
    if (t - startRunDebounce < 300) {
      // debounce rapid submissions
      return;
    }
    startRunDebounce = t;

    cleanupRun("startRun:pre");

    // reset actions for new run
    useAgentActionsStore.getState().clear();

    const tempRunId = runId ?? safeId();
    runRef.current = {
      tempRunId,
      phase: "connecting",
      objectiveSent: false,
      ws: null,
      wsId: safeId(),
      reconnectAttempts: 0,
    };

    const r = runRef.current;
    const WS_URL = getWSUrl("/stream");

    try {
      const ws = await openSocket(WS_URL, r.wsId!);

      if (!runRef.current || r.wsId !== runRef.current.wsId) {
        try {
          ws.close();
        } catch {
          /* noop */
        }
        return; // stale socket
      }

      r.ws = ws;
      setConnected(true);

      ws.onmessage = (ev) => {
        if (!runRef.current || r.wsId !== runRef.current.wsId) return;
        const msg = JSON.parse(ev.data);
        const current = runRef.current!;
        // forward to agent actions store
        useAgentActionsStore.getState().addFromMessage(msg);

        if (msg.status === "started" && msg.run_id) {
          if (!current.realRunId) {
            current.realRunId = msg.run_id;
            current.phase = "streaming";
            current.reconnectAttempts = 0;
            upgradeRunId(current.tempRunId, msg.run_id);
            useHistory.getState().promoteTurn(current.tempRunId, msg.run_id);
            options.onRunIdUpdate?.(current.tempRunId, msg.run_id);
            current.keepAliveTimer = setInterval(() => {
              try {
                current.ws?.readyState === 1 &&
                  current.ws?.send(JSON.stringify({ type: "ping" }));
              } catch {
                /* noop */
              }
            }, 25_000);
          }
          return;
        }

        if (msg.run_id && current.realRunId && msg.run_id !== current.realRunId) {
          return;
        }

        if (msg.error) {
          failRun(current.realRunId ?? current.tempRunId, msg.error);
          useHistory
            .getState()
            .finalizeTurn(current.realRunId ?? current.tempRunId, false);
          options.onError?.(msg.error);
          current.phase = "error";
          cleanupRun("error", current.wsId);
          return;
        }

        if (msg.node?.startsWith("tool:")) {
          const turnId = current.realRunId ?? current.tempRunId;
          if (msg.node.endsWith(":request")) {
            useHistory.getState().appendAction(turnId, {
              id: msg.id || safeId(),
              label: toLabel(msg.node),
              technicalName: msg.node,
              startedAt: msg.ts ? Date.parse(msg.ts) : Date.now(),
              status: "running",
              debug: { input: msg.args },
            });
          } else if (msg.node.endsWith(":response")) {
            const finished = msg.ts ? Date.parse(msg.ts) : Date.now();
            const state = useHistory.getState();
            const real = state.promoted[turnId] || turnId;
            const action = state.turns[real]?.actions.find((a) => a.id === msg.id);
            const duration = action?.startedAt
              ? finished - action.startedAt
              : undefined;
            state.patchAction(turnId, msg.id, {
              status: msg.error || msg.ok === false ? "failed" : "succeeded",
              finishedAt: finished,
              durationMs: duration,
              debug: { output: msg.result, error: msg.error },
            });
          }
          pushEvent(current.realRunId ?? current.tempRunId, msg);
          return;
        }

        if (msg.node === "write" && msg.summary) {
          const id = current.realRunId ?? current.tempRunId;
          appendSummaryOnce(id, msg.summary);
          useHistory.getState().setAgentTextOnce(id, msg.summary);
          return;
        }

        if (msg.status === "done") {
          if (!current.realRunId || msg.run_id === current.realRunId) {
            current.phase = "finished";
            const id = current.realRunId ?? current.tempRunId;
            const { runs } = useRunsStore.getState();
            const summary = runs[id]?.summary || msg.summary || "Task completed";
            finishRun(id, summary);
            useHistory.getState().finalizeTurn(id, true);
            options.onFinish?.(summary);
            if (current.keepAliveTimer) {
              clearInterval(current.keepAliveTimer);
              current.keepAliveTimer = undefined;
            }
            safeCloseSocket("done");
            setConnected(false);
          }
        }
      };

      ws.onclose = (e) => {
        if (!runRef.current || r.wsId !== runRef.current.wsId) return;
        setConnected(false);
        const current = runRef.current!;

        if (
          (e.code === 1005 || e.code === 1006) &&
          current.realRunId &&
          (current.phase === "started" || current.phase === "streaming")
        ) {
          const attempt = ++current.reconnectAttempts;
          if (attempt <= 4) {
            const delay = backoffDelay(attempt);
            setTimeout(async () => {
              if (!runRef.current || r.wsId !== runRef.current.wsId) return;
              try {
                const reWs = await openSocket(WS_URL, r.wsId!);
                if (!runRef.current || r.wsId !== runRef.current.wsId) {
                  try {
                    reWs.close();
                  } catch {
                    /* noop */
                  }
                  return;
                }
                current.ws = reWs;
                setConnected(true);
                reWs.onmessage = ws.onmessage!;
                reWs.onclose = ws.onclose!;
                reWs.onerror = ws.onerror!;
                try {
                  reWs.send(JSON.stringify({ action: "subscribe", run_id: current.realRunId }));
                } catch {
                  /* noop */
                }
              } catch {
                // Next attempt handled by subsequent onclose
              }
            }, delay);
            return;
          }
        }

        if (current.keepAliveTimer) {
          clearInterval(current.keepAliveTimer);
          current.keepAliveTimer = undefined;
        }
        const finalize = async () => {
          const id = current.realRunId ?? current.tempRunId;
          if (current.realRunId) {
            try {
              const res = await http(`/runs/${current.realRunId}`);
              if (res.ok) {
                const data = await res.json();
                if (data.status === "done") {
                  const summary = data.summary || "Task completed";
                  current.phase = "finished";
                  appendSummaryOnce(id, summary);
                  useHistory.getState().setAgentTextOnce(id, summary);
                  finishRun(current.realRunId, summary);
                  useHistory.getState().finalizeTurn(id, true);
                  options.onFinish?.(summary);
                } else {
                  current.phase = "error";
                  failRun(id, "Run closed before completion");
                  useHistory.getState().finalizeTurn(id, false);
                  options.onError?.("Run closed before completion");
                }
              } else {
                current.phase = "error";
                failRun(id, "Run closed before completion");
                useHistory.getState().finalizeTurn(id, false);
                options.onError?.("Run closed before completion");
              }
            } catch {
              current.phase = "error";
              failRun(id, "Run closed before completion");
              useHistory.getState().finalizeTurn(id, false);
              options.onError?.("Run closed before completion");
            }
          } else {
            current.phase = "error";
            failRun(id, "Run closed before completion");
            useHistory.getState().finalizeTurn(id, false);
            options.onError?.("Run closed before completion");
          }
          cleanupRun(`close:${e.code}`, r.wsId);
        };
        finalize();
      };

      ws.onerror = () => {
        // ignored - onclose will handle
      };

      if (!r.objectiveSent) {
        r.objectiveSent = true;
        if (objective && projectId) {
          ws.send(JSON.stringify({ action: "start", objective, project_id: projectId }));
        } else if (runId) {
          ws.send(JSON.stringify({ action: "subscribe", run_id: runId }));
        }
      }
    } catch (e) {
      if (runRef.current) runRef.current.phase = "error";
      setConnected(false);
      options.onError?.(
        e instanceof Error ? e.message : "Failed to connect WebSocket",
      );
    }
  };

  // --- effects --------------------------------------------------------------
  useEffect(() => {
    if (!runId && !options.objective) {
      cleanupRun();
      return;
    }

    startRunInternal(options.objective, options.projectId);

    return () => {
      cleanupRun();
    };
  }, [runId, options.objective, options.projectId]);

  const disconnect = () => {
    cleanupRun("disconnect");
  };

  return { connected, disconnect };
}

