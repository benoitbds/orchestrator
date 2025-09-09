import { useHistory } from '@/store/useHistory';
import { ConversationTurnCard } from './ConversationTurnCard';

export default function ConversationHistory({ projectId }: { projectId?: number }) {
  const { orderDesc, turns } = useHistory();
  const ids = projectId
    ? orderDesc.filter((id) => turns[id]?.projectId === projectId)
    : orderDesc;
  if (!ids.length) {
    return <div className="text-sm text-muted-foreground p-3">No conversation yet</div>;
  }
  return (
    <div className="flex flex-col gap-3">
      {ids.map((id) => (
        <ConversationTurnCard key={id} turn={turns[id]} />
      ))}
    </div>
  );
}
