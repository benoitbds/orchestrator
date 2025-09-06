export interface RunEvent {
  run_id: string;
  seq: number;
  event_type: 'plan' | 'tool_call' | 'tool_result' | 'assistant_answer' | 'status_update' | 'error';
  ts: string;
  elapsed_ms?: number;
  model?: string;
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  cost_eur?: number;
  tool_call_id?: string;
  data?: any;
}

export interface ConversationRun {
  id: string;
  request_id?: string;
  objective: string;
  status: 'running' | 'completed' | 'error';
  created_at: string;
  completed_at?: string;
  events: RunEvent[];
}

export interface CompactViewData {
  objective: string;
  answer: string;
  toolCount: number;
  duration: number;
  status: 'running' | 'completed' | 'error';
}

export interface DisplayMode {
  mode: 'compact' | 'debug';
}

export interface EventFilters {
  types: Set<string>;  // 'plan', 'tool_call', 'tool_result', 'assistant_answer', 'error'
  showTokens: boolean;
  showCosts: boolean;
}

export interface TokenUsage {
  prompt_tokens?: number;
  completion_tokens?: number;
  total_tokens?: number;
  cost_eur?: number;
}