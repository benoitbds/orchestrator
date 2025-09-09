export type ErrorInfo = { code?: string; message: string; hint?: string; docUrl?: string };
export type Step = {
  id: string;
  t: string;
  kind: 'LLM' | 'Tool' | 'DB' | 'System';
  title: string;
  status: 'queued' | 'running' | 'completed' | 'failed' | 'timeout';
  latencyMs?: number;
  summary?: string;
  details?: { input?: any; output?: any; error?: ErrorInfo };
};
export type HistoryRun = {
  id: string;
  startedAt: string;
  endedAt?: string;
  userPrompt: string;
  agentPlan: { bullets: string[]; rationale?: string };
  steps: Step[];
  finalAnswer?: { markdown?: string; json?: any; html?: string };
  modelMeta?: { provider: 'openai' | 'anthropic' | 'mistral'; model: string; tokens?: number };
  stats?: { durationMs?: number; toolCount: number; errorCount: number };
};

export type ActionStatus = "pending" | "running" | "succeeded" | "failed";

export type AgentAction = {
  id: string;
  label: string;
  technicalName?: string;
  startedAt?: number;
  finishedAt?: number;
  status: ActionStatus;
  durationMs?: number;
  debug?: { input?: any; output?: any; error?: any };
};

export type ConversationTurn = {
  turnId: string;
  createdAt: number;
  userText: string;
  projectId: number;
  actions: AgentAction[];
  agentText?: string;
  phase: "running" | "completed" | "failed";
  lastSummaryHash?: string;
};
