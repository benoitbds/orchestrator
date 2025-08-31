import type { Document } from '@/models/document';
import { http } from './api';

export async function listDocuments(projectId: number): Promise<Document[]> {
  const response = await http(`/projects/${projectId}/documents`);
  if (!response.ok) {
    throw new Error('Failed to list documents');
  }
  return response.json();
}

export async function uploadDocument(projectId: number, file: File): Promise<Document> {
  const formData = new FormData();
  formData.append('file', file);
  const response = await http(`/projects/${projectId}/documents`, {
    method: 'POST',
    body: formData,
  });
  if (!response.ok) {
    throw new Error('Failed to upload document');
  }
  return response.json();
}
