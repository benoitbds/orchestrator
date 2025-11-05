"use client";
import { ToolCall } from '@/types/agent-execution';
import { Badge } from '@/components/ui/badge';
import { cn } from '@/lib/utils';
import dynamic from 'next/dynamic';

const Wrench = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.Wrench })),
  { ssr: false }
);
const CheckCircle2 = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.CheckCircle2 })),
  { ssr: false }
);
const XCircle = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.XCircle })),
  { ssr: false }
);

interface ToolCallDisplayProps {
  call: ToolCall;
}

const TOOL_LABELS: Record<string, string> = {
  // Backlog tools
  'generate_children_items': 'Création des User Stories enfants',
  'create_backlog_item_tool': 'Création d\'un item backlog',
  'update_backlog_item_tool': 'Mise à jour d\'un item',
  'get_backlog_item_tool': 'Récupération d\'un item',
  'list_backlog_items': 'Listage des items du backlog',
  'delete_backlog_item': 'Suppression d\'un item',
  'move_backlog_item': 'Déplacement d\'un item',
  'summarize_project_backlog': 'Récapitulatif du backlog',
  'bulk_create_features': 'Création en masse de Features',
  
  // Document tools
  'draft_features_from_documents': 'Génération de features depuis les documents',
  'search_documents': 'Recherche dans les documents',
  'list_documents': 'Listage des documents du projet',
  'get_document_content': 'Récupération du contenu d\'un document',
  'analyze_document_structure': 'Analyse de la structure du document'
};

function getToolLabel(toolName: string): string {
  return TOOL_LABELS[toolName] || toolName.replace(/_/g, ' ');
}

export function ToolCallDisplay({ call }: ToolCallDisplayProps) {
  const humanLabel = getToolLabel(call.tool_name);
  
  return (
    <div className="space-y-1 animate-in fade-in duration-300">
      <div className="flex items-start gap-2 text-sm">
        <Wrench className="h-4 w-4 mt-0.5 text-purple-500" />
        <div className="flex-1 space-y-1">
          <div className="flex items-center gap-2">
            <span className="font-medium">{humanLabel}</span>
            {call.result_summary && (
              call.success ? (
                <CheckCircle2 className="h-3 w-3 text-green-500" />
              ) : (
                <XCircle className="h-3 w-3 text-red-500" />
              )
            )}
          </div>
          
          <div className="pl-4 space-y-0.5 text-xs text-muted-foreground">
            <div className="flex items-start gap-1">
              <span className="select-none">⎿</span>
              <div className="flex-1 space-y-0.5">
                {call.context && (
                  <div>{call.context}</div>
                )}
                
                {Object.keys(call.arguments).length > 0 && (
                  <div className="space-y-0.5">
                    {Object.entries(call.arguments).map(([key, value]) => (
                      <div key={key} className="flex gap-2">
                        <span className="text-muted-foreground/70">{key}:</span>
                        <span className="font-mono text-xs">
                          {typeof value === 'string' && value.length > 60
                            ? `${value.substring(0, 60)}...`
                            : String(value)}
                        </span>
                      </div>
                    ))}
                  </div>
                )}
                
                {call.result_summary && (
                  <div className={cn(
                    "mt-1 flex items-start gap-1",
                    call.success ? "text-green-600 dark:text-green-400" : "text-red-600 dark:text-red-400"
                  )}>
                    <span className="select-none">→</span>
                    <span>{call.result_summary}</span>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
