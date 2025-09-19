import type { Document } from '@/models/document';
import { apiFetch } from './api';

export async function listDocuments(projectId: number): Promise<Document[]> {
  const response = await apiFetch(`/documents?project_id=${projectId}`);
  if (!response.ok) {
    throw new Error('Failed to list documents');
  }
  return response.json();
}

export async function uploadDocument(projectId: number, file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await apiFetch(`/projects/${projectId}/documents`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw new Error('Failed to upload document');
  }
  return response.json();
}

export async function deleteDocument(docId: number) {
  if (!Number.isInteger(docId) || docId <= 0) {
    throw new Error('Invalid document ID');
  }
  const res = await apiFetch(`/documents/${docId}`, {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
  });
  if (!res.ok) throw new Error('Failed to delete document');
  return res.json();
}

export async function analyzeDocument(docId: number): Promise<Document> {
  if (!Number.isInteger(docId) || docId <= 0) {
    throw new Error('Invalid document ID');
  }
  const response = await apiFetch(`/documents/${docId}/analyze`, {
    method: "POST",
  });
  let data: unknown = null;
  try {
    data = await response.json();
  } catch (error) {
    // ignore JSON parsing errors for non-JSON responses
  }
  if (!response.ok) {
    const detail = typeof data === 'object' && data && 'detail' in (data as Record<string, unknown>) ? (data as Record<string, unknown>).detail : null;
    throw new Error((detail as string | null) || 'Failed to analyze document');
  }
  return data as Document;
}
