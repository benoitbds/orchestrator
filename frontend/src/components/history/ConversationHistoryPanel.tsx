import ConversationHistory from './ConversationHistory';

export function ConversationHistoryPanel({ projectId }: { projectId?: number }) {
  return <ConversationHistory projectId={projectId} />;
}
