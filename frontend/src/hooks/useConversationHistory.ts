"use client";

import { useState, useEffect, useCallback, useRef } from 'react';
import type { ConversationRun, RunEvent } from '@/types/events';
import { safeId } from '@/lib/safeId';

export interface UseConversationHistoryOptions {
  autoRefresh?: boolean;
  refreshInterval?: number;
}

export function useConversationHistory(options: UseConversationHistoryOptions = {}) {
  const { autoRefresh = false, refreshInterval = 5000 } = options;
  const [runs, setRuns] = useState<ConversationRun[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const wsConnections = useRef<Map<string, WebSocket>>(new Map());

  // Fetch runs from the API
  const fetchRuns = useCallback(async () => {
    try {
      setIsLoading(true);
      setError(null);
      
      const response = await fetch('/api/runs');
      if (!response.ok) {
        throw new Error(`Failed to fetch runs: ${response.statusText}`);
      }
      
      const runsData = await response.json();
      
      // Fetch events for each run
      const runsWithEvents = await Promise.all(
        runsData.map(async (run: any) => {
          try {
            const eventsResponse = await fetch(`/api/runs/${run.run_id}/events`);
            if (eventsResponse.ok) {
              const eventsData = await eventsResponse.json();
              return {
                id: run.run_id,
                request_id: run.request_id,
                objective: run.objective,
                status: run.status,
                created_at: run.created_at,
                completed_at: run.completed_at,
                events: eventsData.events || [],
              };
            }
            return {
              id: run.run_id,
              request_id: run.request_id,
              objective: run.objective,
              status: run.status,
              created_at: run.created_at,
              completed_at: run.completed_at,
              events: [],
            };
          } catch (error) {
            console.warn(`Failed to fetch events for run ${run.run_id}:`, error);
            return {
              id: run.run_id,
              request_id: run.request_id,
              objective: run.objective,
              status: run.status,
              created_at: run.created_at,
              completed_at: run.completed_at,
              events: [],
            };
          }
        })
      );
      
      setRuns(runsWithEvents);
    } catch (err) {
      console.error('Failed to fetch conversation history:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch data');
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Subscribe to real-time events for a run
  const subscribeToRun = useCallback((runId: string) => {
    if (wsConnections.current.has(runId)) {
      return; // Already subscribed
    }

    try {
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const ws = new WebSocket(`${protocol}//${window.location.host}/api/stream`);
      
      ws.onopen = () => {
        ws.send(JSON.stringify({
          action: 'subscribe',
          run_id: runId,
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          
          if (data.event_type) {
            // This is a structured event
            setRuns(prevRuns => 
              prevRuns.map(run => 
                run.id === runId 
                  ? { ...run, events: [...run.events, data] }
                  : run
              )
            );
          } else if (data.status === 'done') {
            // Run completed
            setRuns(prevRuns =>
              prevRuns.map(run =>
                run.id === runId
                  ? { ...run, status: 'completed' }
                  : run
              )
            );
            // Close the connection
            ws.close();
            wsConnections.current.delete(runId);
          }
        } catch (error) {
          console.warn('Failed to parse WebSocket message:', error);
        }
      };

      ws.onerror = (error) => {
        console.error(`WebSocket error for run ${runId}:`, error);
      };

      ws.onclose = () => {
        wsConnections.current.delete(runId);
      };

      wsConnections.current.set(runId, ws);
    } catch (error) {
      console.error(`Failed to create WebSocket connection for run ${runId}:`, error);
    }
  }, []);

  // Start a new conversation run
  const startConversation = useCallback(async (objective: string, projectId?: number) => {
    try {
      const requestId = safeId();
      
      const response = await fetch('/api/agent/run_chat_tools', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          objective,
          project_id: projectId,
          request_id: requestId,
        }),
      });

      if (!response.ok) {
        throw new Error(`Failed to start conversation: ${response.statusText}`);
      }

      const result = await response.json();
      
      if (result.status === 'existing') {
        // Run already exists, just subscribe to it
        subscribeToRun(result.run_id);
      } else {
        // New run created
        const newRun: ConversationRun = {
          id: result.run_id,
          request_id: requestId,
          objective,
          status: 'running',
          created_at: new Date().toISOString(),
          events: [],
        };
        
        setRuns(prevRuns => [newRun, ...prevRuns]);
        subscribeToRun(result.run_id);
      }

      return result.run_id;
    } catch (error) {
      console.error('Failed to start conversation:', error);
      setError(error instanceof Error ? error.message : 'Failed to start conversation');
      throw error;
    }
  }, [subscribeToRun]);

  // Cleanup WebSocket connections
  useEffect(() => {
    return () => {
      wsConnections.current.forEach(ws => ws.close());
      wsConnections.current.clear();
    };
  }, []);

  // Auto-refresh
  useEffect(() => {
    if (autoRefresh && refreshInterval > 0) {
      const interval = setInterval(fetchRuns, refreshInterval);
      return () => clearInterval(interval);
    }
  }, [autoRefresh, refreshInterval, fetchRuns]);

  // Initial fetch
  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  // Subscribe to running conversations
  useEffect(() => {
    runs
      .filter(run => run.status === 'running')
      .forEach(run => subscribeToRun(run.id));
  }, [runs, subscribeToRun]);

  return {
    runs,
    isLoading,
    error,
    refresh: fetchRuns,
    startConversation,
    subscribeToRun,
  };
}