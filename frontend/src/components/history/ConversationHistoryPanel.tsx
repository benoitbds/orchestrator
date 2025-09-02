import { useCallback, useState } from 'react';
import type { HistoryRun, Step } from '@/types/history';
import { UserPromptCard } from './UserPromptCard';
import { AgentPlanCard } from './AgentPlanCard';
import { ExecutionTimeline } from './ExecutionTimeline';
import { FinalAnswerCard } from './FinalAnswerCard';
import { RightFiltersDrawer, Filters } from './RightFiltersDrawer';

export function ConversationHistoryPanel({ run }: { run: HistoryRun }) {
  const [filters, setFilters] = useState<Filters>({ status: 'all', kind: 'all', time: '1h', group: 'run' });

  const predicate = useCallback(
    (s: Step) => {
      if (filters.status !== 'all' && s.status !== filters.status) return false;
      if (filters.kind !== 'all' && s.kind !== filters.kind) return false;
      return true;
    },
    [filters]
  );

  return (
    <div className="h-full flex gap-4">
      <div className="flex-1 min-h-0 overflow-y-auto space-y-4">
        <UserPromptCard prompt={run.userPrompt} time={run.startedAt} />
        <AgentPlanCard bullets={run.agentPlan.bullets} rationale={run.agentPlan.rationale} />
        <ExecutionTimeline steps={run.steps} filter={predicate} />
        <FinalAnswerCard run={run} />
      </div>
      <RightFiltersDrawer onChange={setFilters} />
    </div>
  );
}
