"use client";
import { useState, useEffect, useRef } from 'react';
import { AgentExecutionEvent, AgentExecutionState } from '@/types/agent-execution';
import { AgentNarrationBlock } from './AgentNarrationBlock';
import { cn } from '@/lib/utils';

interface AgentExecutionStreamProps {
  events: AgentExecutionEvent[];
  className?: string;
}

export function AgentExecutionStream({ events, className }: AgentExecutionStreamProps) {
  const [agentStates, setAgentStates] = useState<Map<string, AgentExecutionState>>(new Map());
  const scrollRef = useRef<HTMLDivElement>(null);
  const prevEventsLength = useRef(events.length);

  useEffect(() => {
    const newStates = new Map(agentStates);

    events.forEach(event => {
      const agentName = event.agent_name;
      let state = newStates.get(agentName);

      if (!state && event.type === 'agent_started') {
        state = {
          agent_name: agentName,
          status: 'running',
          narration: event.narration_text,
          narrations: [],
          todos: (event.todos || []).map((text, idx) => ({
            id: `${agentName}-todo-${idx}`,
            text,
            status: 'pending' as const
          })),
          tool_calls: [],
          items_created: [],
          expanded: true,
          timestamp_start: event.timestamp
        };
        newStates.set(agentName, state);
      } else if (state) {
        switch (event.type) {
          case 'agent_narration':
            if (!state.narrations) state.narrations = [];
            // Deduplicate: only add if not already present
            if (!state.narrations.includes(event.narration_text)) {
              state.narrations.push(event.narration_text);
            }
            break;
            
          case 'agent_thinking':
            state.thinking = event.step_description;
            state.progress = event.progress;
            break;

          case 'tool_call_start':
            state.tool_calls.push({
              tool_name: event.tool_name,
              context: event.context,
              arguments: event.arguments,
              timestamp: event.timestamp
            });
            break;

          case 'tool_call_result':
            const lastCall = state.tool_calls[state.tool_calls.length - 1];
            if (lastCall && lastCall.tool_name === event.tool_name) {
              lastCall.result_summary = event.result_summary;
              lastCall.success = event.success;
            }
            break;

          case 'item_created_realtime':
            state.items_created.push({
              id: event.item.id,
              title: event.item.title,
              type: event.item.type,
              priority: event.item.priority,
              business_value: event.item.business_value,
              parent_title: event.item.parent_title,
              animation_hint: event.animation_hint
            });
            break;

          case 'todo_updated':
            const todo = state.todos.find(t => t.id === event.todo_id);
            if (todo) {
              todo.status = event.status;
            }
            break;

          case 'agent_completed':
            state.status = 'completed';
            state.summary = event.summary;
            state.metrics = event.metrics;
            state.timestamp_end = event.timestamp;
            state.thinking = undefined;
            
            setTimeout(() => {
              const s = newStates.get(agentName);
              if (s) {
                s.expanded = false;
                setAgentStates(new Map(newStates));
              }
            }, 5000);
            break;
        }
      }
    });

    setAgentStates(newStates);
  }, [events]);

  useEffect(() => {
    if (events.length > prevEventsLength.current && scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
    prevEventsLength.current = events.length;
  }, [events]);

  const agentList = Array.from(agentStates.values()).sort((a, b) => 
    new Date(a.timestamp_start).getTime() - new Date(b.timestamp_start).getTime()
  );

  if (agentList.length === 0) {
    return (
      <div className={cn("text-center py-8 text-muted-foreground", className)}>
        <p>En attente de l&apos;exécution des agents...</p>
      </div>
    );
  }

  return (
    <div 
      ref={scrollRef}
      className={cn("space-y-4 overflow-y-auto max-h-[600px] pr-2", className)}
    >
      {agentList.map(agent => (
        <AgentNarrationBlock
          key={agent.agent_name}
          state={agent}
          onToggleExpand={() => {
            const newStates = new Map(agentStates);
            const state = newStates.get(agent.agent_name);
            if (state) {
              state.expanded = !state.expanded;
              setAgentStates(newStates);
            }
          }}
        />
      ))}
    </div>
  );
}
