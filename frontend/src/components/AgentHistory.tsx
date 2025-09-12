"use client";
import { useState, useEffect, forwardRef, useImperativeHandle } from 'react';
import { useProjects } from '@/context/ProjectContext';
import { apiFetch } from '@/lib/api';
import { Badge } from '@/components/ui/badge';

interface AgentExchange {
  id: string;
  objective: string;
  summary: string;
  timestamp: string;
  status: string;
}

const AgentHistory = forwardRef<any, {}>((props, ref) => {
  const { currentProject } = useProjects();
  const [exchanges, setExchanges] = useState<AgentExchange[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const fetchHistory = async () => {
    if (!currentProject) {
      setExchanges([]);
      return;
    }

    setIsLoading(true);
    try {
      const response = await apiFetch(`/runs?project_id=${currentProject.id}`);
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
      .replace(/\s+/g, ' ')
      .replace(/^\s+|\s+$/g, '')
      .trim();
    
    return cleaned || 'No content available';
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
    refreshHistory
  }));

  if (!currentProject) {
    return (
      <div className="p-4 border rounded-md bg-gray-50">
        <h3 className="font-medium mb-2">Historique Agent</h3>
        <p className="text-gray-500 text-sm">Sélectionnez un projet pour voir l'historique</p>
      </div>
    );
  }

  return (
    <div className="p-4 border rounded-md bg-gray-50">
      <div className="flex justify-between items-center mb-4">
        <h3 className="font-medium">Historique Agent - {currentProject.name}</h3>
        <Badge variant="secondary">{exchanges.length} échanges</Badge>
      </div>

      {isLoading ? (
        <div className="text-gray-500 text-sm">Chargement...</div>
      ) : exchanges.length === 0 ? (
        <div className="text-gray-500 text-sm">Aucun échange trouvé</div>
      ) : (
        <div className="space-y-3 max-h-96 overflow-y-auto">
          {exchanges.map((exchange) => (
            <div key={exchange.id} className="bg-white p-3 rounded border-l-4 border-blue-400">
              <div className="flex justify-between items-start mb-2">
                <div className="flex-1">
                  <div className="font-medium text-sm text-gray-800 mb-1">
                    {exchange.objective}
                  </div>
                  <div className="text-xs text-gray-500">
                    {exchange.timestamp}
                  </div>
                </div>
                <Badge 
                  variant={exchange.status === 'done' ? 'default' : 'secondary'}
                  className="ml-2"
                >
                  {exchange.status}
                </Badge>
              </div>
              
              <div className="text-sm text-gray-700 bg-gray-50 p-2 rounded max-h-20 overflow-y-auto">
                {exchange.summary}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});

AgentHistory.displayName = "AgentHistory";
export default AgentHistory;