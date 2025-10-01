import { useEffect, useState, useRef } from 'react';

export interface StreamEvent {
  type: 'agent_start' | 'agent_thinking' | 'tool_call_start' | 'tool_call_end' | 
        'agent_end' | 'token_stream' | 'status_update' | 'error' | 'complete';
  agent: string;
  timestamp: string;
  data: Record<string, unknown>;
  run_id: string;
  iteration: number;
}

export interface AgentAction {
  agent: string;
  status: 'running' | 'done' | 'error';
  message: string;
  tools: ToolCall[];
  timestamp: string;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
  result?: string;
  error?: string;
  status: 'running' | 'done' | 'error';
}

export function useLangGraphStream(runId: string | null) {
  const [events, setEvents] = useState<StreamEvent[]>([]);
  const [agentActions, setAgentActions] = useState<AgentAction[]>([]);
  const [isComplete, setIsComplete] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentStatus, setCurrentStatus] = useState<string>('');
  const [progress, setProgress] = useState<number>(0);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!runId) return;

    const wsUrl = `ws://localhost:8000/ws/agents/${runId}`;
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected for run:', runId);
    };

    ws.onmessage = (event) => {
      const streamEvent: StreamEvent = JSON.parse(event.data);
      
      setEvents(prev => [...prev, streamEvent]);
      
      // Update agent actions for UI
      switch (streamEvent.type) {
        case 'agent_start':
          setAgentActions(prev => [...prev, {
            agent: streamEvent.agent,
            status: 'running' as const,
            message: String(streamEvent.data.message || 'Starting...'),
            tools: [],
            timestamp: streamEvent.timestamp
          }]);
          break;
        
        case 'agent_thinking':
          setAgentActions(prev => {
            const updated = [...prev];
            const agentAction = updated.find(a => a.agent === streamEvent.agent && a.status === 'running');
            if (agentAction) {
              agentAction.message = String(streamEvent.data.message || 'Analyzing...');
            }
            return updated;
          });
          break;
        
        case 'tool_call_start':
          setAgentActions(prev => {
            const updated = [...prev];
            const agentAction = updated.find(a => a.agent === streamEvent.agent && a.status === 'running');
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
            const agentAction = updated.find(a => a.agent === streamEvent.agent && a.status === 'running');
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
            const agentAction = updated.find(a => a.agent === streamEvent.agent && a.status === 'running');
            if (agentAction) {
              agentAction.status = streamEvent.data.success ? 'done' as const : 'error' as const;
              agentAction.message = String(streamEvent.data.message);
            }
            return updated;
          });
          break;
        
        case 'status_update':
          setCurrentStatus(String(streamEvent.data.message));
          setProgress(Number(streamEvent.data.progress) || 0);
          break;
        
        case 'complete':
          setIsComplete(true);
          setCurrentStatus('Completed successfully');
          setProgress(100);
          break;
        
        case 'error':
          setError(String(streamEvent.data.message));
          break;
      }
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setError('WebSocket connection failed');
    };

    ws.onclose = () => {
      console.log('WebSocket closed for run:', runId);
    };

    return () => {
      ws.close();
    };
  }, [runId]);

  const startAgentExecution = (payload: {
    project_id: number;
    objective: string;
    token: string;
  }) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({
        type: 'start_agents',
        payload
      }));
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