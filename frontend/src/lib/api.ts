import { auth } from "./firebase";

function getAPIBaseUrl(): string {
  const explicit = process.env.NEXT_PUBLIC_API_BASE_URL;
  if (explicit && explicit.trim().length > 0) return explicit;
  
  if (typeof window !== "undefined") {
    const proto = window.location.protocol;
    const host = window.location.host;
    return `${proto}//${host}/api`;
  }
  
  return "https://agent4ba.baq.ovh/api";
}

export async function apiFetch(path: string, init?: RequestInit) {
  const headers = new Headers(init?.headers);
  try {
    const token = await auth.currentUser?.getIdToken();
    if (token) {
      headers.set("Authorization", `Bearer ${token}`);
      console.log(`[apiFetch] ${path} - Token added (length: ${token.length})`);
    } else {
      console.warn(`[apiFetch] ${path} - No token available`);
    }
  } catch (e) {
    console.error(`[apiFetch] ${path} - Error getting token:`, e);
  }
  return fetch(`${getAPIBaseUrl()}${path}`, {
    ...init,
    headers,
    credentials: "include",
  });
}

export interface AgentRunMetadata {
  action?: 'generate_children' | 'create_item' | 'update_item' | 'analyze';
  target_type?: 'Epic' | 'Feature' | 'US' | 'UC' | 'Capability';
  parent_id?: number;
  parent_type?: 'Epic' | 'Feature' | 'US' | 'UC' | 'Capability';
}

export interface AgentRunPayload {
  project_id: number;
  objective: string;
  meta?: AgentRunMetadata;
}


export async function validateItem(id: number, fields?: string[]) {
  const res = await apiFetch(`/api/items/${id}/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ fields: fields ?? null }),
  });
  if (!res.ok) {
    throw new Error("Failed to validate item");
  }
  return res.json();
}

export async function validateItems(ids: number[]) {
  const res = await apiFetch(`/api/items/validate`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ids }),
  });
  if (!res.ok) {
    throw new Error("Failed to validate items");
  }
  return res.json();
}

export async function getItem(id: number, projectId: number) {
  console.log(`getItem called: id=${id}, projectId=${projectId}`);
  const res = await apiFetch(`/api/items/${id}`);
  console.log(`API response status: ${res.status}`);
  
  if (!res.ok) {
    if (res.status === 404) {
      console.error(`Item #${id} not found (404)`);
      return null;
    }
    throw new Error(`Failed to fetch item #${id}: ${res.status}`);
  }
  const item = await res.json();
  console.log(`Fetched item:`, item);
  
  // Verify it belongs to the correct project
  if (item.project_id !== projectId) {
    console.warn(`Item #${id} belongs to project ${item.project_id}, not ${projectId}`);
    return null;
  }
  
  return item;
}

export interface ResolvedReference {
  originalText: string;
  expandedText: string;
  itemId: number;
  itemType: string;
  itemTitle: string;
}

export async function resolveShortRefs(input: string, projectId: number): Promise<{
  text: string;
  references: ResolvedReference[];
}> {
  const rx = /\[(Epic|Feature|US|UC|Capability)\s*#(\d+)\]/gi;
  const matches = [...input.matchAll(rx)];
  
  if (matches.length === 0) {
    return { text: input, references: [] };
  }

  let output = input;
  const references: ResolvedReference[] = [];
  
  for (const match of matches) {
    const [fullMatch, type, idStr] = match;
    const id = Number(idStr);
    
    console.log(`Resolving reference: ${fullMatch} (ID: ${id}, project: ${projectId})`);
    
    const item = await getItem(id, projectId);
    if (!item) {
      console.error(`Item #${id} not found or doesn't belong to project ${projectId}`);
      
      // Try to help the user by showing what items exist
      try {
        const allItemsRes = await apiFetch(`/items?project_id=${projectId}&limit=10`);
        if (allItemsRes.ok) {
          const allItems = await allItemsRes.json();
          console.log(`Available items in project ${projectId}:`, allItems.map((i: any) => ({id: i.id, type: i.type, title: i.title})));
        }
      } catch (e) {
        // Ignore
      }
      
      throw new Error(`Item #${id} not found in this project. It may have been deleted. Please refresh and select again.`);
    }
    
    console.log(`Fetched item #${id}:`, { id: item.id, type: item.type, title: item.title, project_id: item.project_id });
    
    const label = `${item.type} "${item.title}" (ID: ${item.id})`;
    output = output.replace(fullMatch, label);
    
    references.push({
      originalText: fullMatch,
      expandedText: label,
      itemId: item.id,
      itemType: item.type,
      itemTitle: item.title
    });
    
    console.log(`Added reference:`, references[references.length - 1]);
  }
  
  return { text: output, references };
}

export function extractIntentMetadata(input: string, references: ResolvedReference[]): AgentRunMetadata | null {
  if (references.length === 0) {
    return null;
  }
  
  const lowerInput = input.toLowerCase();
  
  // The LAST reference is the parent (the one user selected/mentioned)
  const parentRef = references[references.length - 1];
  
  // Detect what type of children to create
  // Remove the parent reference from input to avoid false positives
  const inputWithoutParent = input.replace(parentRef.originalText, '').toLowerCase();
  
  const ucKeywords = ['use case', 'cas d\'usage', 'use-case', ' uc ', 'ucs'];
  const usKeywords = ['user stor', ' us ', 'stories', 'story'];
  const featureKeywords = ['feature', 'fonctionnalit'];
  const epicKeywords = ['epic'];
  
  let targetType: AgentRunMetadata['target_type'] | null = null;
  
  // Priority: more specific keywords first
  if (ucKeywords.some(kw => inputWithoutParent.includes(kw))) {
    targetType = 'UC';
  } else if (usKeywords.some(kw => inputWithoutParent.includes(kw))) {
    targetType = 'US';
  } else if (featureKeywords.some(kw => inputWithoutParent.includes(kw))) {
    targetType = 'Feature';
  } else if (epicKeywords.some(kw => inputWithoutParent.includes(kw))) {
    targetType = 'Epic';
  }
  
  const createKeywords = ['cr[ée]', 'g[ée]n[ée]r', 'ajout', 'create', 'generate', 'add'];
  const isCreate = createKeywords.some(kw => new RegExp(kw, 'i').test(lowerInput));
  
  if (isCreate && targetType) {
    console.log(`Extracted metadata: Creating ${targetType} under ${parentRef.itemType} #${parentRef.itemId}`);
    return {
      action: 'generate_children',
      target_type: targetType,
      parent_id: parentRef.itemId,
      parent_type: parentRef.itemType as AgentRunMetadata['parent_type']
    };
  }
  
  return null;
}
