import { useEffect, useState, useRef } from 'react';
import { useHistory } from '@/store/useHistory';
import type { AgentAction as HistoryAction } from '@/types/history';

export interface StreamEvent {
  type: 'agent_start' | 'agent_thinking' | 'agent_narration' | 'todo_updated' | 
        'tool_call_start' | 'tool_call_end' | 'agent_end' | 'token_stream' | 
        'status_update' | 'error' | 'complete' | 'item_created' | 'item_creating' | 
        'connected' | 'keepalive';
  agent: string;
  timestamp: string;
  data: Record<string, unknown>;
  run_id: string;
  iteration: number;
}

export interface StepInfo {
  step_index: number;
  total_steps: number;
  step_description: string;
}

export interface TodoItem {
  id: string;
  text: string;
  status: 'pending' | 'in_progress' | 'completed';
}

export interface AgentAction {
  id: string; // Unique identifier: run_id-agent-iteration-timestamp
  agent: string;
  status: 'running' | 'done' | 'error';
  message: string;
  tools: ToolCall[];
  timestamp: string;
  iteration: number; // Agent iteration number
  stepInfo?: StepInfo; // Workflow step context
  data?: Record<string, unknown>; // Additional data from agent_end event
  narrations?: string[]; // Human-readable narration messages
  todos?: TodoItem[]; // Todo checklist items
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: string;
  error?: string;
  status: 'running' | 'done' | 'error';
}

export function useLangGraphStream(
  runId: string | null,
  onItemCreated?: (item: Record<string, unknown>) => void,
  onItemCreating?: (data: Record<string, unknown>) => void
) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [agentActions, setAgentActions] = useState<AgentAction[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);
  const pendingMessageRef = useRef<any>(null);
  const { appendAction, patchAction } = useHistory();

  useEffect(() => {
    if (!runId) return;

    const wsProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = typeof window !== 'undefined' ? window.location.host : 'localhost:8000';
    const wsUrl = `${wsProtocol}//${wsHost}/ws/agents/${runId}`;
    
    console.log('[useLangGraphStream] Creating WebSocket connection:', {
      runId,
      wsUrl,
      protocol: wsProtocol,
      host: wsHost
    });
    
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[useLangGraphStream] ✅ WebSocket OPENED successfully');
      console.log('[useLangGraphStream] Run ID:', runId);
      console.log('[useLangGraphStream] ReadyState:', ws.readyState, '(OPEN=1)');
      console.log('[useLangGraphStream] URL:', wsUrl);
      console.log('[useLangGraphStream] Protocol:', ws.protocol);
      console.log('[useLangGraphStream] Extensions:', ws.extensions);
      
      // Send pending message if any
      if (pendingMessageRef.current) {
        console.log('[useLangGraphStream] 📤 Sending pending message after connection opened');
        ws.send(JSON.stringify(pendingMessageRef.current));
        pendingMessageRef.current = null;
      } else {
        console.log('[useLangGraphStream] ℹ️ No pending message to send');
      }
    };

    ws.onmessage = (event) => {
      console.log('[useLangGraphStream] 📩 Received message:', event.data);
      const streamEvent: StreamEvent = JSON.parse(event.data);
      console.log('[useLangGraphStream] 📋 Parsed event type:', streamEvent.type);
      
      // Handle special message types
      if (streamEvent.type === 'connected') {
        console.log('[useLangGraphStream] ✅ Server confirmed connection:', streamEvent.data);
        return;
      }
      
      if (streamEvent.type === 'keepalive') {
        console.log('[useLangGraphStream] 💓 Keepalive received');
        return;
      }
      
      setEvents(prev => [...prev, streamEvent]);
      
      // Update agent actions for UI
      switch (streamEvent.type) {
        case 'agent_start':
          const actionId = `${streamEvent.run_id}-${streamEvent.agent}-${streamEvent.iteration}-${Date.now()}`;
          const todos = streamEvent.data.todos as string[] | undefined;
          const newAction: AgentAction = {
            id: actionId,
            agent: streamEvent.agent,
            status: 'running' as const,
            message: String(streamEvent.data.message || 'Starting...'),
            tools: [],
            timestamp: streamEvent.timestamp,
            iteration: streamEvent.iteration,
            stepInfo: streamEvent.data.step_info as StepInfo | undefined,
            todos: todos?.map((text, idx) => ({
              id: `${streamEvent.agent}-todo-${idx}`,
              text,
              status: 'pending' as const
            }))
          };
          setAgentActions(prev => {
            // Deduplication: check if action with exact same ID already exists
            const exists = prev.find(a => a.id === actionId);
            if (exists) {
              console.warn('[useLangGraphStream] Duplicate agent_start detected:', actionId);
              return prev;
            }
            return [...prev, newAction];
          });
          
          if (runId) {
            const historyAction: HistoryAction = {
              id: `${runId}-${streamEvent.agent}-${Date.now()}`,
              label: streamEvent.agent,
              technicalName: streamEvent.agent,
              startedAt: Date.now(),
              status: 'running',
            };
            appendAction(runId, historyAction);
          }
          break;
        
        case 'agent_thinking':
          setAgentActions(prev => {
            const updated = [...prev];
            const agentAction = updated.find(a => 
              a.agent === streamEvent.agent && 
              a.iteration === streamEvent.iteration &&
              a.status === 'running'
            );
            if (agentAction) {
              agentAction.message = String(streamEvent.data.message || 'Analyzing...');
            }
            return updated;
          });
          break;
        
        case 'agent_narration':
          setAgentActions(prev => {
            const updated = [...prev];
            const agentAction = updated.find(a => 
              a.agent === streamEvent.agent && 
              a.iteration === streamEvent.iteration &&
              a.status === 'running'
            );
            if (agentAction) {
              if (!agentAction.narrations) {
                agentAction.narrations = [];
              }
              agentAction.narrations.push(String(streamEvent.data.message));
            }
            return updated;
          });
          break;
        
        case 'todo_updated':
          setAgentActions(prev => {
            const updated = [...prev];
            const agentAction = updated.find(a => 
              a.agent === streamEvent.agent && 
              a.iteration === streamEvent.iteration &&
              a.status === 'running'
            );
            if (agentAction && agentAction.todos) {
              const todo = agentAction.todos.find(t => t.id === streamEvent.data.todo_id);
              if (todo) {
                todo.status = streamEvent.data.status as 'pending' | 'in_progress' | 'completed';
              }
            }
            return updated;
          });
          break;
        
        case 'tool_call_start':
          setAgentActions(prev => {
            const updated = [...prev];
            const agentAction = updated.find(a => 
              a.agent === streamEvent.agent && 
              a.iteration === streamEvent.iteration &&
              a.status === 'running'
            );
            if (agentAction) {
              agentAction.tools.push({
                name: String(streamEvent.data.tool_name),
                args: streamEvent.data.args as Record<string, unknown>,
                status: 'running' as const
              });
            }
            return updated;
          });
          break;
        
        case 'tool_call_end':
          setAgentActions(prev => {
            const updated = [...prev];
            const agentAction = updated.find(a => 
              a.agent === streamEvent.agent && 
              a.iteration === streamEvent.iteration &&
              a.status === 'running'
            );
            if (agentAction) {
              const tool = agentAction.tools.find(t => 
                t.name === streamEvent.data.tool_name && t.status === 'running'
              );
              if (tool) {
                tool.status = streamEvent.data.error ? 'error' as const : 'done' as const;
                tool.result = streamEvent.data.result ? String(streamEvent.data.result) : undefined;
                tool.error = streamEvent.data.error ? String(streamEvent.data.error) : undefined;
              }
            }
            return updated;
          });
          break;
        
        case 'agent_end':
          setAgentActions(prev => {
            const updated = [...prev];
            const agentAction = updated.find(a => 
              a.agent === streamEvent.agent && 
              a.iteration === streamEvent.iteration &&
              a.status === 'running'
            );
            if (agentAction) {
              agentAction.status = streamEvent.data.success ? 'done' as const : 'error' as const;
              agentAction.message = String(streamEvent.data.message);
              agentAction.data = streamEvent.data; // Store all data for agent-specific details
            }
            return updated;
          });
          
          if (runId) {
            const actionId = `${runId}-${streamEvent.agent}-`;
            patchAction(runId, actionId, {
              status: streamEvent.data.success ? 'succeeded' : 'failed',
              finishedAt: Date.now(),
            });
          }
          break;
        
        case 'status_update':
          setCurrentStatus(String(streamEvent.data.message));
          // Progress is sent as 0.0 to 1.0, convert to 0-100 for display
          const progressValue = Number(streamEvent.data.progress) || 0;
          setProgress(progressValue * 100);
          break;
        
        case 'item_creating':
          console.log('[useLangGraphStream] Item creating:', streamEvent.data);
          if (onItemCreating) {
            onItemCreating(streamEvent.data);
          }
          break;
        
        case 'item_created':
          console.log('[useLangGraphStream] Item created:', streamEvent.data);
          if (onItemCreated && streamEvent.data.item) {
            onItemCreated(streamEvent.data.item as Record<string, unknown>);
          }
          break;
        
        case 'complete':
          console.log('[useLangGraphStream] Received complete event');
          setIsComplete(true);
          setCurrentStatus('Completed successfully');
          setProgress(100);
          break;
        
        case 'error':
          setError(String(streamEvent.data?.message || streamEvent.data || 'Unknown error'));
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('[useLangGraphStream] ❌ WebSocket ERROR');
      console.error('[useLangGraphStream] Error object:', error);
      console.error('[useLangGraphStream] ReadyState:', ws.readyState, '- States: CONNECTING=0, OPEN=1, CLOSING=2, CLOSED=3');
      console.error('[useLangGraphStream] URL:', wsUrl);
      console.error('[useLangGraphStream] Protocol:', window.location.protocol);
      console.error('[useLangGraphStream] Host:', window.location.host);
      setError('WebSocket connection failed');
    };

    ws.onclose = (event) => {
      console.log('[useLangGraphStream] 🔴 WebSocket CLOSED');
      console.log('[useLangGraphStream] Run ID:', runId);
      console.log('[useLangGraphStream] Close code:', event.code, '-', getCloseCodeDescription(event.code));
      console.log('[useLangGraphStream] Close reason:', event.reason || 'No reason provided');
      console.log('[useLangGraphStream] Was clean:', event.wasClean);
      console.log('[useLangGraphStream] ReadyState:', ws.readyState);
      
      // Common close codes:
      // 1000 = Normal closure
      // 1001 = Going away
      // 1002 = Protocol error
      // 1003 = Unsupported data
      // 1006 = Abnormal closure (no close frame)
      // 1011 = Server error
      if (event.code === 1006) {
        console.error('[useLangGraphStream] ⚠️ Abnormal closure - connection failed or server rejected');
      }
      
      // Only set completion if we received a complete event
      if (!isComplete && event.code !== 1000) {
        setError(`Connection closed unexpectedly (code: ${event.code})`);
      }
    };

    return () => {
      console.log('[useLangGraphStream] 🧹 Cleanup: closing WebSocket for run', runId);
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close(1000, 'Component unmounting');
      }
    };
  }, [runId]);

  const startAgentExecution = (payload: {
    project_id: number;
    objective: string;
    token: string;
    meta?: Record<string, unknown>;
  }) => {
    console.log('[useLangGraphStream] startAgentExecution called with payload:', {
      project_id: payload.project_id,
      objective: payload.objective.substring(0, 50),
      hasToken: !!payload.token,
      hasMeta: !!payload.meta
    });
    console.log('[useLangGraphStream] WebSocket readyState:', wsRef.current?.readyState);
    console.log('[useLangGraphStream] WebSocket.OPEN constant:', WebSocket.OPEN);
    
    const message = {
      type: 'start_agents',
      payload
    };
    
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('[useLangGraphStream] WebSocket is OPEN - Sending start_agents message immediately');
      wsRef.current.send(JSON.stringify(message));
    } else if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      console.log('[useLangGraphStream] WebSocket is CONNECTING - Queueing message for when connection opens');
      pendingMessageRef.current = message;
    } else {
      console.error('[useLangGraphStream] Cannot send message - WebSocket not available!', {
        readyState: wsRef.current?.readyState,
        states: {
          CONNECTING: WebSocket.CONNECTING,
          OPEN: WebSocket.OPEN,
          CLOSING: WebSocket.CLOSING,
          CLOSED: WebSocket.CLOSED
        }
      });
      setError('WebSocket connection not available');
    }
  };

  return {
    events,
    agentActions,
    isComplete,
    error,
    currentStatus,
    progress,
    isConnected: wsRef.current?.readyState === WebSocket.OPEN,
    startAgentExecution
  };
}

function getCloseCodeDescription(code: number): string {
  const descriptions: Record<number, string> = {
    1000: 'Normal Closure',
    1001: 'Going Away',
    1002: 'Protocol Error',
    1003: 'Unsupported Data',
    1005: 'No Status Received',
    1006: 'Abnormal Closure (no close frame - connection failed or rejected)',
    1007: 'Invalid Frame Payload Data',
    1008: 'Policy Violation',
    1009: 'Message Too Big',
    1010: 'Mandatory Extension',
    1011: 'Internal Server Error',
    1015: 'TLS Handshake Failure'
  };
  return descriptions[code] || `Unknown (${code})`;
}