import type { RunData, AgentEvent } from '@/stores/useRunsStore';
import type { Message } from '@/stores/useMessagesStore';
import type { ConversationTurn, AgentAction } from '@/types/conversation';

const TOOL_LABELS: Record<string, string> = {
  generate_items_from_parent: 'Generate child items',
};

function humanize(name: string): string {
  return name
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

function mapEventToAction(event: AgentEvent, id: string): AgentAction {
  const startedAt = event.ts || event.timestamp;
  const finishedAt = event.ts || event.timestamp;
  const status: AgentAction['status'] =
    event.ok === undefined ? 'running' : event.ok ? 'succeeded' : 'failed';
  const label = TOOL_LABELS[event.node] || humanize(event.node);
  const durationMs = startedAt && finishedAt ? Date.parse(finishedAt) - Date.parse(startedAt) : undefined;
  return {
    id,
    label,
    technicalName: event.node,
    startedAt,
    finishedAt: status === 'running' ? undefined : finishedAt,
    status,
    durationMs,
    debug: {
      input: event.args,
      output: event.result,
      error: event.error,
    },
  };
}

export function mapRunsToTurns(
  runs: Record<string, RunData>,
  messages: Message[]
): ConversationTurn[] {
  return Object.entries(runs).map(([id, run]) => {
    const userMsg = messages.find((m) => m.runId === id && m.type === 'user');
    const agentMsg = messages.find((m) => m.runId === id && m.type === 'agent');
    const actions = run.events
      .filter((e) => !['user', 'prompt', 'assistant', 'write'].includes(e.node))
      .map((e, idx) => mapEventToAction(e, `${id}-${idx}`));

    return {
      id,
      createdAt: new Date(run.startedAt).toISOString(),
      userText: userMsg?.content || '',
      actions,
      agentText: agentMsg?.content,
      status: run.status,
    };
  });
}
