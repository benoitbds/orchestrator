import { useEffect, useRef, useState } from 'react';
import { useRunsStore, type AgentEvent } from '@/stores/useRunsStore';
import { connectWS } from '@/lib/ws';

interface UseAgentStreamOptions {
  onFinish?: (summary: string) => void;
  onError?: (error: string) => void;
}

export function useAgentStream(
  runId: string | undefined,
  options: UseAgentStreamOptions = {}
): { 
  connected: boolean;
  disconnect: () => void;
} {
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();
  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const baseDelay = 1000;

  const { pushEvent, finishRun, failRun } = useRunsStore();

  const disconnect = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = undefined;
    }
    
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    setConnected(false);
    reconnectAttemptsRef.current = 0;
  };

  const connect = () => {
    if (!runId || wsRef.current) return;

    try {
      const ws = connectWS('/stream');
      wsRef.current = ws;

      ws.onopen = () => {
        console.log('WebSocket connected for run:', runId);
        setConnected(true);
        reconnectAttemptsRef.current = 0;
        
        // Send initial run_id
        ws.send(JSON.stringify({ run_id: runId }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          console.log('WebSocket message:', data);

          // Handle error messages
          if (data.error) {
            console.error('WebSocket error:', data.error);
            failRun(runId, data.error);
            options.onError?.(data.error);
            disconnect();
            return;
          }

          // Create agent event
          const agentEvent: AgentEvent = {
            node: data.node || 'unknown',
            ts: data.timestamp || data.ts,
            ok: data.ok,
            result: data.result,
            args: data.args,
            error: data.error,
            content: data.content,
          };

          // Push event to store
          pushEvent(runId, agentEvent);

          // Handle completion
          if (data.status === 'done' || data.node === 'write') {
            const summary = data.summary || data.content || 'Task completed';
            finishRun(runId, summary);
            options.onFinish?.(summary);
            disconnect();
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason);
        setConnected(false);
        wsRef.current = null;

        // Auto-reconnect if the run is still active and we haven't exceeded max attempts
        if (
          !event.wasClean &&
          reconnectAttemptsRef.current < maxReconnectAttempts &&
          useRunsStore.getState().isRunning()
        ) {
          const delay = baseDelay * Math.pow(2, reconnectAttemptsRef.current);
          console.log(`Reconnecting in ${delay}ms (attempt ${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);
          
          reconnectTimeoutRef.current = setTimeout(() => {
            reconnectAttemptsRef.current++;
            connect();
          }, delay);
        }
      };

      ws.onerror = (error) => {
        console.error('WebSocket error:', error);
      };
    } catch (error) {
      console.error('Failed to connect WebSocket:', error);
      setConnected(false);
    }
  };

  useEffect(() => {
    if (runId) {
      connect();
    } else {
      disconnect();
    }

    return () => {
      disconnect();
    };
  }, [runId]);

  return { connected, disconnect };
}