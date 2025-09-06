// src/lib/runs.ts
import { http } from './api';

export interface AgentCost {
  agent: string;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  cost_eur: number;
}

export interface RunCost {
  total_tokens: number;
  cost_eur: number;
  by_agent: AgentCost[];
}

export async function getRunCost(runId: string): Promise<RunCost> {
  const res = await http(`/runs/${runId}/cost`);
  if (!res.ok) throw new Error('Failed to load run cost');
  return res.json();
}
