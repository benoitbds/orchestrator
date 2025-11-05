import React from 'react';
import { AgentAction } from '@/hooks/useLangGraphStream';
import { AgentExecutionStream } from '@/components/agent/AgentExecutionStream';
import { AgentExecutionEvent } from '@/types/agent-execution';

interface Props {
  actions: AgentAction[];
  isComplete: boolean;
  currentStatus?: string;
  progress?: number;
}

function convertActionsToEvents(actions: AgentAction[]): AgentExecutionEvent[] {
  const events: AgentExecutionEvent[] = [];
  const timestamp = new Date().toISOString();

  actions.forEach((action, idx) => {
    const agentName = action.agent || 'UnknownAgent';
    
    events.push({
      type: 'agent_started',
      agent_name: agentName,
      narration_text: action.thought || `Processing with ${agentName}`,
      todos: action.todos?.map(t => t.text) || action.data?.workflow_steps?.map((s: { objective?: string; description?: string }) => 
        s.objective || s.description || 'Step'
      ),
      timestamp: new Date(Date.now() + idx * 100).toISOString()
    });
    
    if (action.narrations && action.narrations.length > 0) {
      action.narrations.forEach((narration, narrationIdx) => {
        events.push({
          type: 'agent_narration',
          agent_name: agentName,
          narration_text: narration,
          timestamp: new Date(Date.now() + idx * 100 + 5 + narrationIdx).toISOString()
        });
      });
    }

    action.tools?.forEach((tool) => {
      events.push({
        type: 'tool_call_start',
        agent_name: agentName,
        tool_name: tool.name,
        arguments: tool.args || {},
        context: `Calling ${tool.name}`,
        timestamp: new Date(Date.now() + idx * 100 + 10).toISOString()
      });

      if (tool.result) {
        try {
          const result = JSON.parse(tool.result);
          
          events.push({
            type: 'tool_call_result',
            agent_name: agentName,
            tool_name: tool.name,
            result_summary: getResultSummary(tool.name, result),
            success: true,
            timestamp: new Date(Date.now() + idx * 100 + 20).toISOString()
          });

          if (tool.name.includes('create') && result.id) {
            events.push({
              type: 'item_created_realtime',
              agent_name: agentName,
              item: {
                id: result.id,
                title: result.title || `Item ${result.id}`,
                type: result.type || 'Unknown',
                priority: result.priority,
                business_value: result.business_value,
                parent_id: result.parent_id,
                parent_title: result.parent_title
              },
              animation_hint: 'fade-in',
              timestamp: new Date(Date.now() + idx * 100 + 30).toISOString()
            });
          }

          if (tool.name === 'bulk_create_features' && result.features_created) {
            result.features_created.forEach((id: number, featureIdx: number) => {
              events.push({
                type: 'item_created_realtime',
                agent_name: agentName,
                item: {
                  id,
                  title: `Feature ${id}`,
                  type: 'Feature'
                },
                animation_hint: 'slide-in',
                timestamp: new Date(Date.now() + idx * 100 + 30 + featureIdx * 10).toISOString()
              });
            });
          }

          if (tool.name === 'generate_children_items' && result.items_created) {
            result.items_created.forEach((item: { id: number; title: string; type: string }, itemIdx: number) => {
              events.push({
                type: 'item_created_realtime',
                agent_name: agentName,
                item: {
                  id: item.id,
                  title: item.title,
                  type: item.type
                },
                animation_hint: 'slide-in',
                timestamp: new Date(Date.now() + idx * 100 + 30 + itemIdx * 10).toISOString()
              });
            });
          }
        } catch {
          events.push({
            type: 'tool_call_result',
            agent_name: agentName,
            tool_name: tool.name,
            result_summary: String(tool.result).substring(0, 100),
            success: true,
            timestamp: new Date(Date.now() + idx * 100 + 20).toISOString()
          });
        }
      }
    });

    events.push({
      type: 'agent_completed',
      agent_name: agentName,
      summary: `Completed ${action.tools?.length || 0} tool calls`,
      metrics: {
        items_created: action.data?.items_created ?? countItemsCreated(action),
        duration_ms: 1000
      },
      timestamp: new Date(Date.now() + idx * 100 + 50).toISOString()
    });
  });

  return events;
}

function getResultSummary(toolName: string, result: Record<string, unknown>): string {
  // Humanized summaries for all tools
  if (toolName === 'draft_features_from_documents') {
    const count = (result.features_created as unknown[])?.length || 0;
    return `${count} feature${count > 1 ? 's' : ''} extraite${count > 1 ? 's' : ''} depuis les documents`;
  }
  if (toolName === 'generate_children_items') {
    const children = result.children_created as any[];
    const count = children?.length || 0;
    const type = result.target_type || 'items';
    const typeLabel = type === 'US' ? 'User Stories' : type === 'UC' ? 'Use Cases' : type;
    return `${count} ${typeLabel} cr\u00e9\u00e9${count > 1 ? 's' : ''}`;
  }
  if (toolName === 'bulk_create_features') {
    const count = (result.features_created as unknown[])?.length || 0;
    return `${count} feature${count > 1 ? 's' : ''} cr\u00e9\u00e9e${count > 1 ? 's' : ''}`;
  }
  if (toolName === 'summarize_project_backlog') {
    const counts = result.counts as any;
    const total = counts?.total || 0;
    return `Backlog r\u00e9capitul\u00e9: ${total} items au total`;
  }
  if (toolName === 'list_documents') {
    const count = (result.documents as unknown[])?.length || 0;
    return `${count} document${count > 1 ? 's' : ''} list\u00e9${count > 1 ? 's' : ''}`;
  }
  if (toolName === 'search_documents') {
    const count = (result.results as unknown[])?.length || 0;
    return `${count} r\u00e9sultat${count > 1 ? 's' : ''} trouv\u00e9${count > 1 ? 's' : ''}`;
  }
  if (toolName === 'analyze_document_structure') {
    const sections = (result.sections as unknown[])?.length || 0;
    return `Structure analys\u00e9e: ${sections} section${sections > 1 ? 's' : ''} d\u00e9tect\u00e9e${sections > 1 ? 's' : ''}`;
  }
  if (toolName === 'list_backlog_items') {
    const count = (result.items as unknown[])?.length || 0;
    return `${count} item${count > 1 ? 's' : ''} du backlog`;
  }
  if (toolName === 'create_backlog_item_tool' && result.id) {
    const type = result.type || 'item';
    return `${type} cr\u00e9\u00e9: ${result.title || result.id}`;
  }
  if (toolName === 'get_document_content') {
    const wordCount = result.word_count || 0;
    return `Document r\u00e9cup\u00e9r\u00e9: ${wordCount} mots`;
  }
  
  // Generic fallbacks
  if (toolName.includes('update') && result.id) {
    return `\u00c9l\u00e9ment mis \u00e0 jour`;
  }
  if (toolName.includes('delete')) {
    return `\u00c9l\u00e9ment supprim\u00e9`;
  }
  
  return 'Op\u00e9ration r\u00e9ussie';
}

function countItemsCreated(action: AgentAction): number {
  let count = 0;
  action.tools?.forEach(tool => {
    if (!tool.result) return;
    try {
      const result = JSON.parse(tool.result);
      if (tool.name.includes('create') && result.id) count++;
      if (tool.name === 'bulk_create_features' && result.features_created) {
        count += (result.features_created as unknown[]).length;
      }
      if (tool.name === 'generate_children_items' && result.items_created) {
        count += (result.items_created as unknown[]).length;
      }
    } catch {
      // Ignore
    }
  });
  return count;
}

export const AgentActionsPanel: React.FC<Props> = ({
  actions,
  isComplete,
  currentStatus,
  progress
}) => {
  const events = convertActionsToEvents(actions);

  if (events.length === 0 && !currentStatus) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p>Aucune action d&apos;agent pour le moment</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {currentStatus && !isComplete && (
        <div className="flex items-center gap-3 p-4 bg-blue-50 dark:bg-blue-950 rounded-lg border border-blue-200 dark:border-blue-800">
          <div className="animate-spin h-4 w-4 border-2 border-blue-600 border-t-transparent rounded-full" />
          <span className="text-sm font-medium">{currentStatus}</span>
          {progress !== undefined && progress > 0 && (
            <span className="text-xs text-muted-foreground ml-auto">{progress}%</span>
          )}
        </div>
      )}

      <AgentExecutionStream events={events} />

      {isComplete && (
        <div className="mt-4 p-4 bg-green-50 dark:bg-green-950 rounded-lg border border-green-200 dark:border-green-800">
          <div className="flex items-center gap-2 text-green-700 dark:text-green-300">
            <span className="text-lg">✓</span>
            <span className="font-medium">Exécution terminée avec succès</span>
          </div>
        </div>
      )}
    </div>
  );
};
