import { useEffect, useRef, useCallback } from 'react';
import { toast } from 'sonner';

export interface DocumentAnalysisEvent {
  type: 'document_analysis_started' | 'document_analysis_progress' | 
        'document_analysis_completed' | 'document_analysis_failed';
  doc_id: number;
  status?: string;
  chunk_count?: number;
  embeddings_count?: number;
  error?: string;
}

interface UseDocumentAnalysisOptions {
  projectId: number | null;
  onAnalysisComplete?: (docId: number) => void;
  onAnalysisError?: (docId: number, error: string) => void;
}

export function useDocumentAnalysis({
  projectId,
  onAnalysisComplete,
  onAnalysisError
}: UseDocumentAnalysisOptions) {
  const wsRef = useRef<WebSocket | null>(null);

  const handleDocumentEvent = useCallback((event: DocumentAnalysisEvent) => {
    console.log('Document analysis event:', event);

    switch (event.type) {
      case 'document_analysis_started':
        toast.info('Document analysis started...', {
          description: `Analyzing document #${event.doc_id}`
        });
        break;

      case 'document_analysis_progress':
        if (event.chunk_count) {
          toast.info('Generating embeddings...', {
            description: `Processing ${event.chunk_count} chunks`
          });
        }
        break;

      case 'document_analysis_completed':
        toast.success('Document analysis complete!', {
          description: `${event.chunk_count} chunks indexed with ${event.embeddings_count} embeddings`
        });
        onAnalysisComplete?.(event.doc_id);
        break;

      case 'document_analysis_failed':
        toast.error('Document analysis failed', {
          description: event.error || 'Unknown error'
        });
        onAnalysisError?.(event.doc_id, event.error || 'Unknown error');
        break;
    }
  }, [onAnalysisComplete, onAnalysisError]);

  useEffect(() => {
    if (!projectId) return;

    // Connect to WebSocket for this project
    const wsProtocol = typeof window !== 'undefined' && window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = typeof window !== 'undefined' ? window.location.host : 'localhost:8000';
    
    // We need a WebSocket endpoint for project events
    // For now, we'll use a general endpoint or poll for updates
    // TODO: Create /ws/project/{project_id} endpoint for document events
    
    // Fallback: Use polling every 3 seconds to check document status
    const pollInterval = setInterval(async () => {
      // This will be handled by the parent component via refetch
      // The WebSocket implementation can be added later
    }, 3000);

    return () => {
      clearInterval(pollInterval);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [projectId, handleDocumentEvent]);

  return {
    // For now, just expose the handler for testing
    handleDocumentEvent
  };
}
