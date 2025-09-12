export const labelMap: Record<string, string> = {
  "tool:list_items": "List backlog items",
  "tool:generate_items_from_parent": "Generate child items",
  "tool:search_documents": "Search documents",
  "tool:create_item": "Create backlog item",
  "tool:update_item": "Update backlog item",
};

export function toLabel(node?: string) {
  if (!node) return "Agent step";
  const key = node.split(":").slice(0, 2).join(":");
  return labelMap[key] ?? node.replaceAll("_", " ");
}

export function hashText(s: string) {
  let h = 0,
    i = 0;
  while (i < s.length) h = (h * 31 + s.charCodeAt(i++)) | 0;
  return String(h);
}
