import { HistoryRun } from './history';

const now = Date.now();
export const demoRun: HistoryRun = {
  id: 'demo',
  startedAt: new Date(now).toISOString(),
  userPrompt: 'Find the item and list related entries.',
  agentPlan: {
    bullets: ['Use find_item tool', 'Then list_items for context'],
    rationale: 'First locate the item then show related entries.',
  },
  steps: [
    {
      id: 's1',
      t: new Date(now + 100).toISOString(),
      kind: 'Tool',
      title: 'find_item',
      status: 'completed',
      latencyMs: 1600,
      details: { input: { id: 1 }, output: { item: { id: 1, name: 'Widget' } } },
    },
    {
      id: 's2',
      t: new Date(now + 2000).toISOString(),
      kind: 'Tool',
      title: 'list_items',
      status: 'completed',
      latencyMs: 474,
      details: { input: { parent: 1 }, output: { items: [1, 2, 3] } },
    },
    {
      id: 's3',
      t: new Date(now + 2600).toISOString(),
      kind: 'LLM',
      title: 'summarize',
      status: 'failed',
      latencyMs: 200,
      details: {
        error: {
          code: '429',
          message: 'Rate limit exceeded',
          hint: 'Reduce request rate',
          docUrl: 'https://example.com/429',
        },
      },
    },
    {
      id: 's4',
      t: new Date(now + 3000).toISOString(),
      kind: 'LLM',
      title: 'final answer',
      status: 'timeout',
      latencyMs: 30000,
      details: {
        error: { message: 'Request timed out', hint: 'Try again with a smaller prompt' },
      },
    },
  ],
  stats: { durationMs: 3200, toolCount: 2, errorCount: 2 },
};
