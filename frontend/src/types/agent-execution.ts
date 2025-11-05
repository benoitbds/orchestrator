export interface AgentStartedEvent {
  type: 'agent_started';
  agent_name: string;
  narration_text: string;
  todos?: string[];
  timestamp: string;
}

export interface AgentNarrationEvent {
  type: 'agent_narration';
  agent_name: string;
  narration_text: string;
  timestamp: string;
}

export interface AgentThinkingEvent {
  type: 'agent_thinking';
  agent_name: string;
  step_description: string;
  progress?: number;
  timestamp: string;
}

export interface ToolCallStartEvent {
  type: 'tool_call_start';
  agent_name: string;
  tool_name: string;
  arguments: Record<string, unknown>;
  context?: string;
  timestamp: string;
}

export interface ToolCallResultEvent {
  type: 'tool_call_result';
  agent_name: string;
  tool_name: string;
  result_summary: string;
  items_affected?: number[];
  success: boolean;
  timestamp: string;
}

export interface ItemCreatedRealtimeEvent {
  type: 'item_created_realtime';
  agent_name: string;
  item: {
    id: number;
    title: string;
    type: string;
    priority?: string;
    business_value?: number;
    parent_id?: number;
    parent_title?: string;
  };
  animation_hint?: 'slide-in' | 'fade-in';
  timestamp: string;
}

export interface TodoUpdatedEvent {
  type: 'todo_updated';
  agent_name: string;
  todo_id: string;
  todo_text: string;
  status: 'pending' | 'in_progress' | 'completed';
  timestamp: string;
}

export interface AgentCompletedEvent {
  type: 'agent_completed';
  agent_name: string;
  summary: string;
  metrics?: {
    items_created?: number;
    duration_ms?: number;
    [key: string]: unknown;
  };
  timestamp: string;
}

export type AgentExecutionEvent =
  | AgentStartedEvent
  | AgentNarrationEvent
  | AgentThinkingEvent
  | ToolCallStartEvent
  | ToolCallResultEvent
  | ItemCreatedRealtimeEvent
  | TodoUpdatedEvent
  | AgentCompletedEvent;

export interface AgentExecutionState {
  agent_name: string;
  status: 'running' | 'completed' | 'error';
  narration?: string;
  narrations?: string[];
  todos: TodoItem[];
  tool_calls: ToolCall[];
  items_created: ItemSummary[];
  thinking?: string;
  progress?: number;
  summary?: string;
  metrics?: Record<string, unknown>;
  expanded: boolean;
  timestamp_start: string;
  timestamp_end?: string;
}

export interface TodoItem {
  id: string;
  text: string;
  status: 'pending' | 'in_progress' | 'completed';
}

export interface ToolCall {
  tool_name: string;
  context?: string;
  arguments: Record<string, unknown>;
  result_summary?: string;
  success?: boolean;
  timestamp: string;
}

export interface ItemSummary {
  id: number;
  title: string;
  type: string;
  priority?: string;
  business_value?: number;
  parent_title?: string;
  animation_hint?: string;
}
