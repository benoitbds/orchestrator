// src/models/document.ts
export interface Document {
  id: number;
  project_id: number;
  filename: string;
  content?: string | null;
  embedding?: number[] | null;
}
