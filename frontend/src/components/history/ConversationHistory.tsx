import { useHistory } from '@/store/useHistory';
import { ConversationTurnCard } from './ConversationTurnCard';

export default function ConversationHistory() {
  const { orderDesc, turns } = useHistory();
  if (!orderDesc.length) {
    return <div className="text-sm text-muted-foreground p-3">No conversation yet</div>;
  }
  return (
    <div className="flex flex-col gap-3">
      {orderDesc.map((id) => (
        <ConversationTurnCard key={id} turn={turns[id]} />
      ))}
    </div>
  );
}
