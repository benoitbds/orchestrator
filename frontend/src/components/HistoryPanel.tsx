"use client";

import { useState, forwardRef, useImperativeHandle, useRef, useEffect } from 'react';
import { 
  ChevronLeft, 
  ChevronRight,
  History,
  Clock,
  Play
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { useProjects } from '@/context/ProjectContext';
import { http } from '@/lib/api';
import AgentTimeline, { AgentTimelineStep } from './AgentTimeline';

interface HistoryPanelProps {
  className?: string;
  timelineSteps: AgentTimelineStep[];
}

interface AgentExchange {
  id: string;
  objective: string;
  summary: string;
  timestamp: string;
  status: string;
}

type Line = {
  node: string;
  state: any;
  timestamp: Date;
};

export const HistoryPanel = forwardRef<any, HistoryPanelProps>(({ className, timelineSteps }, ref) => {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [exchanges, setExchanges] = useState<AgentExchange[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [lines, setLines] = useState<Line[]>([]);
  const { currentProject } = useProjects();
  const innerRef = useRef<HTMLPreElement>(null);

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  const fetchHistory = async () => {
    if (!currentProject) {
      setExchanges([]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await http(`/runs?project_id=${currentProject.id}`);
      const data = await response.json();
      
      // Sort by most recent first and format data
      const formattedExchanges = data
        .sort((a: any, b: any) => new Date(b.timestamp || 0).getTime() - new Date(a.timestamp || 0).getTime())
        .map((run: any) => ({
          id: run.id,
          objective: run.objective || 'No objective',
          summary: extractPlainText(run.summary || run.html || 'No result'),
          timestamp: run.timestamp ? new Date(run.timestamp).toLocaleString() : 'Unknown time',
          status: run.status || 'unknown'
        }));

      setExchanges(formattedExchanges);
    } catch (error) {
      console.error('Failed to fetch agent history:', error);
      setExchanges([]);
    } finally {
      setIsLoading(false);
    }
  };

  // Extract plain text from HTML content, focusing on agent logs
  const extractPlainText = (content: string): string => {
    if (!content) return 'No content';
    
    // Remove HTML tags and extract meaningful content
    const withoutHTML = content.replace(/<[^>]*>/g, '');
    
    // Clean up extra whitespace and newlines
    const cleaned = withoutHTML
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&amp;/g, '&')
      .replace(/&quot;/g, '"')
      .replace(/&#x27;/g, "'")
      .replace(/\s+/g, ' ')
      .replace(/^\\s+|\\s+$/g, '')
      .trim();
    
    return cleaned || 'No content available';
  };

  const renderContent = (node: string, state: any) => {
    if (!state) {
      return <span className="text-gray-500 text-xs">Génération du contenu...</span>;
    }

    // Handle tool execution results with simplified display
    if (node === 'write' && state?.result) {
      const plainText = extractPlainText(state.result);
      
      return (
        <div className="space-y-1">
          <div className="text-green-600 font-semibold text-xs">✅ Agent Response</div>
          <div className="rounded border-l-2 border-green-400 bg-green-50 p-2">
            <div className="text-gray-700 text-xs whitespace-pre-wrap">
              {plainText || 'Operation completed'}
            </div>
          </div>
        </div>
      );
    }

    // Handle tool calls and other operations
    const displayContent = (() => {
      if (typeof state === 'string') {
        return extractPlainText(state);
      } else if (state && typeof state === 'object') {
        // For tool responses, show a simplified view
        if (state.ok !== undefined) {
          const status = state.ok ? '✅ Success' : '❌ Failed';
          const details = state.error || (state.result ? 'Operation completed' : '');
          return `${status}${details ? ': ' + details : ''}`;
        }
        return JSON.stringify(state, null, 2);
      }
      return String(state);
    })();

    return (
      <div className="space-y-1">
        <div className="text-blue-600 font-semibold text-xs">🔧 {node}</div>
        <div className="bg-gray-50 p-2 rounded text-xs border-l-2 border-blue-400">
          <pre className="text-gray-700 whitespace-pre-wrap font-mono text-xs leading-relaxed">
            {displayContent}
          </pre>
        </div>
      </div>
    );
  };

  useEffect(() => {
    fetchHistory();
  }, [currentProject]);

  // Refresh history when new runs complete
  const refreshHistory = () => {
    fetchHistory();
  };

  // Expose methods to parent component via ref
  useImperativeHandle(ref, () => ({
    toggleCollapse,
    refreshHistory,
    push({ node, state }: { node: string; state: any }) {
      console.log("HistoryPanel received chunk:", { node, state });

      setLines(ls => [{ node, state, timestamp: new Date() }, ...ls]);

      setTimeout(() => {
        const el = innerRef.current;
        if (el) el.scrollTop = 0;
      }, 0);
    },
    clear() {
      setLines([]);
    }
  }));

  if (!currentProject && !isCollapsed) {
    return (
      <div className={`
        bg-background border-l border-border transition-all duration-300 ease-in-out
        w-80
        ${className}
      `}>
        <div className="flex items-center justify-between p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleCollapse}
              className="size-6"
            >
              <ChevronRight className="size-4" />
            </Button>
            <History className="size-5 text-muted-foreground" />
            <h2 className="text-sm font-semibold">Historique</h2>
          </div>
        </div>
        <div className="p-4">
          <p className="text-gray-500 text-sm">Sélectionnez un projet pour voir l'historique</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`
      bg-background border-l border-border transition-all duration-300 ease-in-out
      ${isCollapsed ? 'w-12' : 'w-80'}
      ${className}
    `}>
      {/* Header avec bouton de collapse */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleCollapse}
            className="size-6"
          >
            {isCollapsed ? (
              <ChevronLeft className="size-4" />
            ) : (
              <ChevronRight className="size-4" />
            )}
          </Button>
          {!isCollapsed && (
            <>
              <History className="size-5 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Historique</h2>
            </>
          )}
        </div>
      </div>

      {/* Contenu du panel (caché si collapsed) */}
      {!isCollapsed && (
        <div className="flex flex-col h-full">
          {/* Section temps réel */}
          {lines.length > 0 && (
            <div className="border-b border-border">
              <div className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Play className="size-4 text-green-600" />
                  <h3 className="text-sm font-medium text-green-600">Exécution en cours</h3>
                </div>
                <AgentTimeline steps={timelineSteps} />
                <pre
                  ref={innerRef}
                  className="bg-gray-50 p-3 h-48 overflow-y-auto rounded text-xs font-mono border"
                >
                  {lines.map(({ node, state, timestamp }, i) => (
                    <div key={i} className="flex gap-2 items-start mb-2">
                      <span className="text-gray-400 text-xs min-w-[50px]">{timestamp.toLocaleTimeString()}</span>
                      <div className="flex-1">{renderContent(node, state)}</div>
                    </div>
                  ))}
                </pre>
              </div>
            </div>
          )}

          {/* Section historique */}
          <div className="flex-1 p-4 overflow-y-auto">
            <div className="flex justify-between items-center mb-3">
              <h3 className="text-sm font-medium">Historique - {currentProject?.name}</h3>
              <Badge variant="secondary" className="text-xs">{exchanges.length} échanges</Badge>
            </div>

            {isLoading ? (
              <div className="text-gray-500 text-sm">Chargement...</div>
            ) : exchanges.length === 0 ? (
              <div className="text-gray-500 text-sm">Aucun échange trouvé</div>
            ) : (
              <div className="space-y-2">
                {exchanges.map((exchange) => (
                  <div key={exchange.id} className="bg-white p-2 rounded border-l-4 border-blue-400 border">
                    <div className="flex justify-between items-start mb-1">
                      <div className="flex-1">
                        <div className="font-medium text-xs text-gray-800 mb-1">
                          {exchange.objective}
                        </div>
                        <div className="text-xs text-gray-500">
                          {exchange.timestamp}
                        </div>
                      </div>
                      <Badge 
                        variant={exchange.status === 'done' ? 'default' : 'secondary'}
                        className="ml-2 text-xs"
                      >
                        {exchange.status}
                      </Badge>
                    </div>
                    
                    <div className="text-xs text-gray-700 bg-gray-50 p-2 rounded max-h-16 overflow-y-auto">
                      {exchange.summary}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Indicateur collapsed */}
      {isCollapsed && (
        <div className="p-2">
          <Button
            variant="ghost"
            size="icon"
            className="w-full"
            onClick={toggleCollapse}
          >
            <Clock className="size-4 text-muted-foreground" />
          </Button>
        </div>
      )}
    </div>
  );
});

HistoryPanel.displayName = "HistoryPanel";