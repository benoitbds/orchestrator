export type AgentAction = {
  id: string;
  label: string;
  technicalName?: string;
  startedAt?: string;
  finishedAt?: string;
  status: 'pending' | 'running' | 'succeeded' | 'failed';
  durationMs?: number;
  debug?: { input?: any; output?: any; error?: any };
};

export type ConversationTurn = {
  id: string;
  createdAt: string;
  userText: string;
  actions: AgentAction[];
  agentText?: string;
  status: 'running' | 'completed' | 'failed';
};
