export interface BacklogItem {
  id: number;
  title: string;
  description: string | null;
  type: string;
  project_id: number;
  parent_id: number | null;
}
