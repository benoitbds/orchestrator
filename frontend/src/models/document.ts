// src/models/document.ts
export type DocumentStatus = "UPLOADED" | "ANALYZING" | "ANALYZED" | "ERROR";

export interface Document {
  id: number;
  project_id: number;
  filename: string;
  content?: string | null;
  embedding?: number[] | null;
  status: DocumentStatus;
  meta?: Record<string, unknown> | null;
}
