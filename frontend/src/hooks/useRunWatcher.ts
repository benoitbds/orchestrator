import { useEffect, useRef } from 'react';
import { connectWS } from '@/lib/ws';
import { http } from '@/lib/api';

interface WatchOptions {
  runId: string | null;
  onStep?: (step: any) => void;
  onFinal?: (payload: any) => void;
  wsUrl?: string; // path or full URL
}

const BACKOFFS = [500, 1000, 2000, 5000];

export function useRunWatcher({ runId, onStep, onFinal, wsUrl = '/stream' }: WatchOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const retryRef = useRef(0);
  const closedRef = useRef(false);
  const reconnectTimer = useRef<NodeJS.Timeout | null>(null);
  const pollTimer = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (!runId) return;
    closedRef.current = false;
    retryRef.current = 0;

    const openSocket = () => {
      const ws = wsUrl.startsWith('ws') ? new WebSocket(wsUrl) : connectWS(wsUrl);
      wsRef.current = ws;
      ws.onopen = () => {
        retryRef.current = 0;
        try {
          ws.send(JSON.stringify({ run_id: runId }));
        } catch {}
      };
      ws.onmessage = evt => {
        try {
          const msg = JSON.parse(evt.data);
          if (msg.type === 'step') {
            onStep?.(msg);
          } else if (msg.type === 'final') {
            onFinal?.(msg);
            closedRef.current = true;
            ws.close();
          }
        } catch (e) {
          if (process.env.NODE_ENV === 'development') {
            console.debug('WS parse error', e);
          }
        }
      };
      ws.onerror = () => ws.close();
      ws.onclose = () => {
        if (closedRef.current) return;
        if (retryRef.current < BACKOFFS.length) {
          const delay = BACKOFFS[retryRef.current++];
          reconnectTimer.current = setTimeout(openSocket, delay);
        } else {
          startPolling();
        }
      };
    };

    const startPolling = () => {
      const start = Date.now();
      const poll = async () => {
        if (Date.now() - start > 60000) return; // stop after 60s
        try {
          const res = await http(`/runs/${runId}`);
          if (res.status === 404) return; // stop if not found
          if (res.ok) {
            const data = await res.json();
            if (data.status === 'done') {
              onFinal?.(data);
              return;
            }
          }
        } catch (e) {
          if (process.env.NODE_ENV === 'development') {
            console.debug('poll error', e);
          }
        }
        pollTimer.current = setTimeout(poll, 1000);
      };
      pollTimer.current = setTimeout(poll, 1000);
    };

    openSocket();

    return () => {
      closedRef.current = true;
      wsRef.current?.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
      if (pollTimer.current) clearTimeout(pollTimer.current);
    };
  }, [runId, wsUrl, onStep, onFinal]);
}

export default useRunWatcher;
