"use client";

import { useEffect } from 'react';
import { useHistory } from '@/store/useHistory';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { History, CheckCircle2, XCircle, Clock } from 'lucide-react';
import type { ConversationTurn, AgentAction } from '@/types/history';

interface ProjectHistoryProps {
  projectId: number;
}

const StatusIcon = ({ status }: { status: AgentAction['status'] }) => {
  switch (status) {
    case 'succeeded':
      return <CheckCircle2 className="h-4 w-4 text-green-600" />;
    case 'failed':
      return <XCircle className="h-4 w-4 text-red-600" />;
    case 'running':
      return <Clock className="h-4 w-4 text-blue-600 animate-pulse" />;
    default:
      return <Clock className="h-4 w-4 text-gray-400" />;
  }
};

const PhaseIcon = ({ phase }: { phase: ConversationTurn['phase'] }) => {
  switch (phase) {
    case 'completed':
      return <Badge variant="secondary" className="bg-green-100 text-green-800">Completed</Badge>;
    case 'failed':
      return <Badge variant="secondary" className="bg-red-100 text-red-800">Failed</Badge>;
    case 'running':
      return <Badge variant="secondary" className="bg-blue-100 text-blue-800">Running</Badge>;
    default:
      return null;
  }
};

const AgentActionItem = ({ action }: { action: AgentAction }) => {
  const getAgentIcon = (agent: string) => {
    switch (agent) {
      case 'router': return '🔀';
      case 'backlog': return '📋';
      case 'document': return '📄';
      case 'planner': return '📊';
      case 'writer': return '✍️';
      case 'conversation': return '💬';
      case 'integration': return '🔗';
      default: return '🤖';
    }
  };

  return (
    <div className="flex items-start gap-3 py-2 px-3 rounded-md hover:bg-gray-50">
      <StatusIcon status={action.status} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm">{getAgentIcon(action.label)}</span>
          <span className="font-medium text-sm capitalize">{action.label}</span>
          {action.finishedAt && (
            <span className="text-xs text-muted-foreground">
              {new Date(action.finishedAt).toLocaleTimeString()}
            </span>
          )}
        </div>
        {action.technicalName && action.technicalName !== action.label && (
          <div className="text-xs text-muted-foreground mt-1">
            {action.technicalName}
          </div>
        )}
      </div>
    </div>
  );
};

const TurnCard = ({ turn }: { turn: ConversationTurn }) => {
  const formattedTime = new Date(turn.createdAt).toLocaleString();
  
  return (
    <Card className="p-4 mb-3">
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className="font-medium text-sm">User Query</span>
            <PhaseIcon phase={turn.phase} />
          </div>
          <p className="text-sm text-muted-foreground">{turn.userText}</p>
          <p className="text-xs text-muted-foreground mt-1">{formattedTime}</p>
        </div>
      </div>
      
      {turn.actions.length > 0 && (
        <div className="mt-3 pt-3 border-t">
          <div className="text-xs font-medium text-muted-foreground mb-2">
            Agent Actions ({turn.actions.length})
          </div>
          <div className="space-y-1">
            {turn.actions.map((action) => (
              <AgentActionItem key={action.id} action={action} />
            ))}
          </div>
        </div>
      )}
      
      {turn.agentText && (
        <div className="mt-3 pt-3 border-t">
          <div className="text-xs font-medium text-muted-foreground mb-1">Response</div>
          <p className="text-sm">{turn.agentText}</p>
        </div>
      )}
    </Card>
  );
};

export function ProjectHistory({ projectId }: ProjectHistoryProps) {
  const { getTurnsByProject } = useHistory();
  const turns = getTurnsByProject(projectId);

  useEffect(() => {
    useHistory.persist.rehydrate();
  }, []);

  if (turns.length === 0) {
    return (
      <Card className="p-8 text-center">
        <History className="h-12 w-12 mx-auto mb-3 text-gray-300" />
        <p className="text-sm text-muted-foreground">
          No agent execution history yet
        </p>
        <p className="text-xs text-muted-foreground mt-1">
          Run an agent to see the history here
        </p>
      </Card>
    );
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 mb-4">
        <History className="h-5 w-5" />
        <h3 className="font-semibold">Agent Execution History</h3>
        <Badge variant="outline">{turns.length}</Badge>
      </div>
      
      <div className="space-y-3 max-h-[600px] overflow-y-auto">
        {turns.map((turn) => (
          <TurnCard key={turn.turnId} turn={turn} />
        ))}
      </div>
    </div>
  );
}
