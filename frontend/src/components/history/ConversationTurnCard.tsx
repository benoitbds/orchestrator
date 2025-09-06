import type { ConversationTurn } from '@/types/history';
import { AgentActionsAccordion } from './actions/AgentActionsAccordion';
import { UserMessage } from './parts/UserMessage';
import { AgentResponse } from './parts/AgentResponse';

export function ConversationTurnCard({ turn }: { turn: ConversationTurn }) {
  return (
    <div data-testid="turn-card" className="rounded-2xl border bg-card p-3 md:p-4">
      <UserMessage text={turn.userText} ts={turn.createdAt} />
      <div className="my-2" />
      <AgentActionsAccordion actions={turn.actions} phase={turn.phase} />
      {turn.agentText ? (
        <>
          <div className="my-2" />
          <AgentResponse text={turn.agentText} phase={turn.phase} />
        </>
      ) : null}
    </div>
  );
}
