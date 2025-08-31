"use client";

import { useState } from 'react';
import { Trash } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { getApiBaseUrl } from '@/lib/api';
import { deleteDocument } from '@/lib/documents';
import type { Document } from '@/models/document';

interface DocumentListProps {
  documents: Document[];
  refetch: () => Promise<void>;
}

export function DocumentList({ documents, refetch }: DocumentListProps) {
  const [deletingId, setDeletingId] = useState<number | null>(null);

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

  if (documents.length === 0) {
    return <p className="text-sm text-muted-foreground">No documents uploaded.</p>;
  }

  return (
    <ul className="list-disc list-inside space-y-1">
      {documents.map((doc) => (
        <li key={doc.id} className="flex items-center gap-2">
          <a
            href={`${getApiBaseUrl()}/documents/${doc.id}/content`}
            className="text-blue-500 hover:underline"
            download
          >
            {doc.filename}
          </a>
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
      ))}
    </ul>
  );
}
