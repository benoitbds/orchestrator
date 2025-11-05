"use client";

import { useState } from 'react';
import { Trash } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { analyzeDocument, deleteDocument } from '@/lib/documents';
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
  onAnalyze?: (objective: string) => Promise<void>;
}

export function DocumentList({ documents, refetch, onAnalyze }: DocumentListProps) {
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [analyzingId, setAnalyzingId] = useState<number | null>(null);
  const apiBase = (process.env.NEXT_PUBLIC_API_BASE_URL || '').replace(/\/+$/, '');

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
    if (analyzingId !== null || !onAnalyze) return;
    setAnalyzingId(doc.id);
    let preprocessingComplete = false;
    try {
      await analyzeDocument(doc.id);
      preprocessingComplete = true;
      await refetch();

      const objective =
        `Analyze the document "${doc.filename}" and generate Features -> User Stories -> Use Cases with acceptance criteria. ` +
        `Use search_documents to cite relevant excerpts (page/section). De-duplicate and group by theme.`;

      // Delegate to parent component (AgentShell) to handle the agent execution
      await onAnalyze(objective);
      
      toast.success('Analysis started. Check the conversation history for progress.');
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
            {doc.status === 'UPLOADED' && (
              <Button
                variant="secondary"
                size="sm"
                aria-label={`Re-analyze ${doc.filename}`}
                disabled={analyzingId === doc.id}
                onClick={() => handleAnalyze(doc)}
              >
                Re-analyze
              </Button>
            )}
            {doc.status === 'ANALYZING' && (
              <span className="text-sm text-muted-foreground animate-pulse">
                Analyzing...
              </span>
            )}
            {doc.status === 'ERROR' && (
              <Button
                variant="outline"
                size="sm"
                aria-label={`Retry analysis for ${doc.filename}`}
                disabled={analyzingId === doc.id}
                onClick={() => handleAnalyze(doc)}
              >
                Retry
              </Button>
            )}
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
