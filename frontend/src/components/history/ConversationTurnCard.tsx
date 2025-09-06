import type { ConversationTurn } from '@/types/conversation';
import { UserMessage } from './UserMessage';
import { AgentActionsAccordion } from './AgentActionsAccordion';
import { AgentResponse } from './AgentResponse';

export function ConversationTurnCard({ turn }: { turn: ConversationTurn }) {
  return (
    <div data-testid="turn-card" className="rounded-2xl border p-3 md:p-4 bg-card space-y-2">
      <UserMessage text={turn.userText} timestamp={turn.createdAt} />
      {turn.actions.length > 0 && <AgentActionsAccordion actions={turn.actions} />}
      {turn.agentText && <AgentResponse text={turn.agentText} status={turn.status} />}
    </div>
  );
}
