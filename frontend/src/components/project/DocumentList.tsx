"use client";

import { useState } from 'react';
import { Trash } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { runAgent } from '@/lib/api';
import { analyzeDocument, deleteDocument } from '@/lib/documents';
import { useHistory } from '@/store/useHistory';
import { useAgentStream } from '@/hooks/useAgentStream';
import type { Document, DocumentStatus } from '@/models/document';

const STATUS_BADGES: Record<DocumentStatus, { label: string; variant: 'default' | 'secondary' | 'destructive' | 'outline' }> = {
  UPLOADED: { label: 'Uploaded', variant: 'outline' },
  ANALYZING: { label: 'Analyzing', variant: 'secondary' },
  ANALYZED: { label: 'Analyzed', variant: 'default' },
  ERROR: { label: 'Error', variant: 'destructive' },
};

const getMetaError = (doc: Document): string | null => {
  if (!doc.meta || typeof doc.meta !== 'object') return null;
  const raw = (doc.meta as Record<string, unknown>).error;
  return typeof raw === 'string' ? raw : null;
};

interface DocumentListProps {
  documents: Document[];
  refetch: () => Promise<void>;
}

export function DocumentList({ documents, refetch }: DocumentListProps) {
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const [currentRunId, setCurrentRunId] = useState<string | undefined>(undefined);
  const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL || '').replace(/\/+$/, '');
  const { createTurn, promoteTurn } = useHistory();
  
  // WebSocket connection for the current analysis
  useAgentStream(currentRunId, {
    onFinish: async (summary) => {
      toast.success('Document analysis completed!');
      await refetch();
      setCurrentRunId(undefined);
    },
    onError: (error) => {
      toast.error(`Analysis failed: ${error}`);
      setCurrentRunId(undefined);
    }
  });

  const handleDelete = async (id: number) => {
    if (!confirm('Supprimer ce document ?')) return;
    try {
      setDeletingId(id);
      await deleteDocument(id);
      await refetch();
      toast.success('Document deleted');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to delete document');
    } finally {
      setDeletingId(null);
    }
  };

  const handleAnalyze = async (doc: Document) => {
    if (analyzingId !== null) return;
    setAnalyzingId(doc.id);
    let preprocessingComplete = false;
    try {
      await analyzeDocument(doc.id);
      preprocessingComplete = true;
      await refetch();

      const objective =
        `Analyze the document "${doc.filename}" and generate Features -> User Stories -> Use Cases with acceptance criteria. ` +
        `Use search_documents to cite relevant excerpts (page/section). De-duplicate and group by theme.`;

      const tempId = `temp-${Date.now()}`;
      createTurn(tempId, `Analyzing document: ${doc.filename}`, doc.project_id);

      const response = await runAgent({ project_id: doc.project_id, objective });

      if (response && response.run_id) {
        promoteTurn(tempId, response.run_id);
        setCurrentRunId(response.run_id);
      }

      toast.success('Analysis started. Check the conversation history for progress.');
      await refetch();
    } catch (e) {
      if (!preprocessingComplete) {
        const message = e instanceof Error ? e.message : 'Could not analyze document';
        toast.error(message);
      } else {
        toast.error('Could not start analysis');
      }
    } finally {
      setAnalyzingId(null);
    }
  };

  if (documents.length === 0) {
    return <p className="text-sm text-muted-foreground">No documents uploaded.</p>;
  }

  return (
    <ul className="list-disc list-inside space-y-1">
      {documents.map((doc) => {
        const statusInfo = STATUS_BADGES[doc.status];
        const errorMessage = getMetaError(doc);
        return (
          <li key={doc.id} className="flex flex-wrap items-center gap-2">
            <a
              href={`${apiBase}/documents/${doc.id}/content`}
              className="text-blue-500 hover:underline"
              download
            >
              {doc.filename}
            </a>
            <Badge variant={statusInfo.variant}>{statusInfo.label}</Badge>
            {errorMessage && (
              <span className="text-xs text-destructive" title={errorMessage}>
                {errorMessage}
              </span>
            )}
            <Button
              variant="secondary"
              size="sm"
              aria-label={`Analyze ${doc.filename}`}
              disabled={analyzingId === doc.id || doc.status === 'ANALYZING'}
              onClick={() => handleAnalyze(doc)}
            >
              Analyze
            </Button>
            <Button
              variant="destructive"
              size="icon"
              aria-label={`Delete ${doc.filename}`}
              disabled={deletingId === doc.id}
              onClick={() => handleDelete(doc.id)}
            >
              <Trash className="h-4 w-4" />
            </Button>
          </li>
        );
      })}
    </ul>
  );
}
