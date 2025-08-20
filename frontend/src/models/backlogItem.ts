// Base item interface
export interface ItemBase {
  id: number;
  title: string;
  description: string | null;
  type: "Epic" | "Capability" | "Feature" | "US" | "UC";
  project_id: number;
  parent_id: number | null;
  /** Indique si cet item a été généré par l'IA et doit être validé */
  generated_by_ai?: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

// Epic/Capability extras
export interface EpicExtras {
  state: "Funnel" | "Reviewing" | "Analyzing" | "Backlog" | "Implementing" | "Done";
  benefit_hypothesis: string;
  leading_indicators?: string | null;
  mvp_definition?: string | null;
  wsjf?: number | null;
}

// Feature extras
export interface FeatureExtras {
  benefit_hypothesis: string;
  acceptance_criteria: string;
  wsjf?: number | null;
  program_increment?: string | null;
  owner?: string | null;
}

// Story (US/UC) extras
export interface StoryExtras {
  story_points: number;
  acceptance_criteria: string;
  invest_compliant: boolean;
  iteration?: string | null;
  status: "Todo" | "Doing" | "Done";
}

// Typed item interfaces
export interface EpicItem extends ItemBase, EpicExtras {
  type: "Epic";
}

export interface CapabilityItem extends ItemBase, EpicExtras {
  type: "Capability";
}

export interface FeatureItem extends ItemBase, FeatureExtras {
  type: "Feature";
}

export interface USItem extends ItemBase, StoryExtras {
  type: "US";
}

export interface UCItem extends ItemBase, StoryExtras {
  type: "UC";
}

// Union type for all items
export type BacklogItem = EpicItem | CapabilityItem | FeatureItem | USItem | UCItem;

// Type guards for discriminating union
export const isEpic = (item: BacklogItem): item is EpicItem => item.type === "Epic";
export const isCapability = (item: BacklogItem): item is CapabilityItem => item.type === "Capability";
export const isFeature = (item: BacklogItem): item is FeatureItem => item.type === "Feature";
export const isUS = (item: BacklogItem): item is USItem => item.type === "US";
export const isUC = (item: BacklogItem): item is UCItem => item.type === "UC";
