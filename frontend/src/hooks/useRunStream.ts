import { useCallback, useEffect, useRef, useState } from 'react';
import { getWSUrl } from '@/lib/ws';
import { auth } from '@/lib/firebase';

export type AgentStep = {
  id: string;
  tool: string;
  startedAt: number;
  finishedAt?: number;
  request: any;
  result?: any;
  ok?: boolean;
  error?: string | null;
  state: 'pending' | 'running' | 'success' | 'failed';
};

export type ChatMessage = {
  id: string;
  ts: number;
  text: string;
};

export function parseNode(
  node: string,
):
  | { kind: 'tool'; phase: 'request' | 'response'; tool: string }
  | { kind: 'write' } {
  if (node === 'write') return { kind: 'write' };
  if (node.startsWith('tool:')) {
    const [, tool, phase] = node.split(':');
    return { kind: 'tool', tool, phase: phase as 'request' | 'response' };
  }
  throw new Error('Unknown node: ' + node);
}

function getClientSessionId(): string {
  try {
    const key = 'client_session_id';
    let id = typeof localStorage !== 'undefined' ? localStorage.getItem(key) : null;
    if (!id) {
      id = crypto.randomUUID();
      if (typeof localStorage !== 'undefined') {
        localStorage.setItem(key, id);
      }
    }
    return id;
  } catch {
    return crypto.randomUUID();
  }
}

interface UseRunStreamOptions {
  objective?: string;
  projectId: number;
  autoStart: boolean;
}

export function useRunStream(options: UseRunStreamOptions) {
  const { objective, projectId, autoStart } = options;
  const [runId, setRunId] = useState<string>();
  const [status, setStatus] = useState<'idle' | 'running' | 'done' | 'error'>('idle');
  const [steps, setSteps] = useState<AgentStep[]>([]);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const manualClose = useRef(false);
  const seqRef = useRef<Record<string, number>>({});
  const reconnectTimer = useRef<number | undefined>(undefined);

  const closeSocket = () => {
    if (wsRef.current) {
      try {
        wsRef.current.close();
      } catch {
        /* noop */
      }
      wsRef.current = null;
    }
  };

  const handleMessage = (ev: MessageEvent) => {
    try {
      const msg = JSON.parse(ev.data);
      if (msg.status === 'started' || msg.status === 'existing' || msg.status === 'subscribed') {
        if (msg.run_id) {
          setRunId(msg.run_id);
          setStatus('running');
        }
        return;
      }
      if (msg.status === 'done') {
        if (status !== 'error') {
          setStatus('done');
        }
        closeSocket();
        return;
      }
      if (msg.node) {
        const parsed = parseNode(msg.node);
        if (parsed.kind === 'write' && msg.summary) {
          setMessages((m) => [
            ...m,
            { id: `m${Date.now()}`, ts: Date.now(), text: msg.summary },
          ]);
          return;
        }
        if (parsed.kind === 'tool') {
          const tool = parsed.tool;
          if (parsed.phase === 'request') {
            const seq = (seqRef.current[tool] = (seqRef.current[tool] || 0) + 1);
            const id = `${tool}_${seq}`;
            setSteps((s) => [
              ...s,
              {
                id,
                tool,
                startedAt: Date.now(),
                request: msg.args ?? {},
                state: 'running',
              },
            ]);
            return;
          }
          if (parsed.phase === 'response') {
            setSteps((s) => {
              const idx = [...s].reverse().findIndex(
                (st) => st.tool === tool && st.state === 'running',
              );
              if (idx === -1) {
                const seq = (seqRef.current[tool] = (seqRef.current[tool] || 0) + 1);
                return [
                  ...s,
                  {
                    id: `${tool}_${seq}`,
                    tool,
                    startedAt: Date.now(),
                    finishedAt: Date.now(),
                    request: {},
                    ok: false,
                    error: 'orphan_response',
                    state: 'failed',
                  },
                ];
              }
              const realIdx = s.length - 1 - idx;
              const step = s[realIdx];
              const ok = msg.ok !== false;
              const updated: AgentStep = {
                ...step,
                finishedAt: Date.now(),
                result: msg.result ?? undefined,
                ok,
                error: msg.error ?? null,
                state: ok ? 'success' : 'failed',
              };
              if (!ok) {
                setStatus('error');
                setError(msg.error || 'error');
              }
              const newSteps = [...s];
              newSteps[realIdx] = updated;
              return newSteps;
            });
            return;
          }
        }
      }
    } catch (e) {
      // ignore malformed messages
    }
  };

  const openSocket = useCallback(async () => {
    manualClose.current = false;
    closeSocket();
    const base = getWSUrl('/stream');
    const token = auth.currentUser
      ? await auth.currentUser.getIdToken().catch(() => null)
      : null;
    const url = token ? `${base}?token=${encodeURIComponent(token)}` : base;
    const ws = new WebSocket(url);
    wsRef.current = ws;
    ws.onmessage = handleMessage;
    ws.onclose = () => {
      if (!manualClose.current && status === 'running' && runId) {
        const timer = window.setTimeout(() => {
          openSocket();
          if (wsRef.current && runId) {
            wsRef.current.onopen = () => {
              try {
                wsRef.current?.send(
                  JSON.stringify({ action: 'subscribe', run_id: runId }),
                );
              } catch {
                /* noop */
              }
            };
          }
        }, 1000);
        reconnectTimer.current = timer;
      }
    };
  }, [runId, status]);

  const start = useCallback(() => {
    setSteps([]);
    setMessages([]);
    setRunId(undefined);
    setError(null);
    setStatus('idle');
    seqRef.current = {};
    openSocket();
    const ws = wsRef.current;
    if (!ws) return;
    ws.onopen = () => {
      const payload: any = {
        action: 'start',
        objective: objective ?? '',
        project_id: projectId,
        client_session_id: getClientSessionId(),
      };
      ws.send(JSON.stringify(payload));
    };
  }, [objective, projectId, openSocket]);

  const stop = useCallback(() => {
    manualClose.current = true;
    setStatus('idle');
    closeSocket();
  }, []);

  useEffect(() => {
    if (autoStart) {
      start();
    }
    return () => {
      manualClose.current = true;
      closeSocket();
      if (reconnectTimer.current) window.clearTimeout(reconnectTimer.current);
    };
  }, [autoStart, start]);

  return { runId, status, steps, messages, start, stop, error };
}

