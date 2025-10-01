import React from 'react';
import { AgentAction, ToolCall } from '@/hooks/useLangGraphStream';

interface Props {
  actions: AgentAction[];
  isComplete: boolean;
  currentStatus?: string;
  progress?: number;
}

const StatusIcon: React.FC<{ status: 'running' | 'done' | 'error' }> = ({ status }) => {
  if (status === 'running') return <span className="text-blue-500 animate-pulse">⏺</span>;
  if (status === 'done') return <span className="text-green-500">✓</span>;
  return <span className="text-red-500">✗</span>;
};

const ToolCallItem: React.FC<{ tool: ToolCall }> = ({ tool }) => {
  const formatArgs = (args: Record<string, unknown>) => {
    const entries = Object.entries(args);
    if (entries.length === 0) return '()';
    
    const formatted = entries
      .slice(0, 2) // Show only first 2 args to keep UI clean
      .map(([k, v]) => {
        let value = typeof v === 'string' ? `"${v}"` : JSON.stringify(v);
        if (value.length > 30) {
          value = value.substring(0, 30) + '...';
        }
        return `${k}: ${value}`;
      })
      .join(', ');
    
    return `(${formatted}${entries.length > 2 ? ', ...' : ''})`;
  };

  return (
    <div className="ml-6 text-sm py-1 border-l-2 border-gray-100 pl-3">
      <div className="flex items-center">
        <StatusIcon status={tool.status} />
        <span className="ml-2 font-mono text-gray-700 font-medium">
          🔧 {tool.name}
        </span>
        <span className="ml-1 text-gray-500 text-xs">
          {formatArgs(tool.args)}
        </span>
      </div>
      
      {tool.result && (
        <div className="ml-8 text-gray-600 text-xs mt-1 bg-gray-50 rounded p-2">
          <span className="font-medium">Result:</span> {tool.result}
        </div>
      )}
      
      {tool.error && (
        <div className="ml-8 text-red-600 text-xs mt-1 bg-red-50 rounded p-2">
          <span className="font-medium">Error:</span> {tool.error}
        </div>
      )}
    </div>
  );
};

const AgentActionItem: React.FC<{ action: AgentAction }> = ({ action }) => {
  const getAgentIcon = (agent: string) => {
    switch (agent) {
      case 'router': return '🔀';
      case 'backlog': return '📋';
      case 'document': return '📄';
      case 'planner': return '📊';
      case 'writer': return '✍️';
      case 'integration': return '🔗';
      default: return '🤖';
    }
  };

  return (
    <div className="border-l-4 border-gray-200 pl-4 py-3 hover:bg-gray-50 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center">
          <StatusIcon status={action.status} />
          <span className="ml-3 text-lg">{getAgentIcon(action.agent)}</span>
          <span className="ml-2 font-semibold capitalize text-gray-800">
            {action.agent}Agent
          </span>
          {action.status === 'running' && (
            <div className="ml-3 flex space-x-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce"></div>
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
            </div>
          )}
        </div>
        <span className="text-xs text-gray-500">
          {new Date(action.timestamp).toLocaleTimeString()}
        </span>
      </div>
      
      <div className="mt-2 ml-8 text-gray-600">
        {action.message}
      </div>
      
      {action.tools.length > 0 && (
        <div className="mt-3 ml-8">
          {action.tools.map((tool, idx) => (
            <ToolCallItem key={idx} tool={tool} />
          ))}
        </div>
      )}
    </div>
  );
};

export const AgentActionsPanel: React.FC<Props> = ({ 
  actions, 
  isComplete, 
  currentStatus = '',
  progress = 0 
}) => {
  const runningCount = actions.filter(a => a.status === 'running').length;
  const completedCount = actions.filter(a => a.status === 'done').length;
  const errorCount = actions.filter(a => a.status === 'error').length;
  
  return (
    <div className="border rounded-lg bg-white shadow-sm">
      {/* Header */}
      <div className="border-b bg-gray-50 p-4 rounded-t-lg">
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-800">
            🤖 Agent Actions ({actions.length})
          </h2>
          <div className="flex items-center space-x-4 text-sm">
            {!isComplete && runningCount > 0 && (
              <span className="text-blue-600 font-medium">
                • Running ({runningCount} active)
              </span>
            )}
            {isComplete && (
              <span className="text-green-600 font-medium">
                ✅ Completed
              </span>
            )}
            <div className="text-gray-500">
              {completedCount} done • {errorCount} errors
            </div>
          </div>
        </div>
        
        {/* Progress bar */}
        {!isComplete && progress > 0 && (
          <div className="mt-3">
            <div className="flex justify-between text-sm text-gray-600 mb-1">
              <span>{currentStatus}</span>
              <span>{Math.round(progress)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-2">
              <div 
                className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                style={{ width: `${progress}%` }}
              ></div>
            </div>
          </div>
        )}
      </div>
      
      {/* Actions List - Reversed to show newest first */}
      <div className="max-h-[600px] overflow-y-auto">
        {actions.length === 0 ? (
          <div className="p-8 text-center text-gray-500">
            <div className="text-4xl mb-4">🤖</div>
            <p>No agent actions yet. Start an execution to see real-time updates.</p>
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {[...actions].reverse().map((action, idx) => (
              <AgentActionItem key={actions.length - 1 - idx} action={action} />
            ))}
          </div>
        )}
      </div>
      
      {/* Summary Footer */}
      {isComplete && actions.length > 0 && (
        <div className="border-t bg-green-50 p-4 rounded-b-lg">
          <div className="flex items-center text-green-800">
            <span className="text-lg">✅</span>
            <span className="ml-2 font-medium">
              Execution completed in {actions.length} steps
            </span>
          </div>
        </div>
      )}
    </div>
  );
};