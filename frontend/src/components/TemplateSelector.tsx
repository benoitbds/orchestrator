"use client";
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import dynamic from 'next/dynamic';

const FileText = dynamic(
  () => import('lucide-react').then((mod) => ({ default: mod.FileText })),
  { ssr: false }
);

interface Template {
  name: string;
  description: string;
}

interface TemplateSelectorProps {
  templates: Record<string, Template>;
  onSelectTemplate: (templateKey: string) => void;
  type: 'Epic' | 'Feature';
}

export function TemplateSelector({ templates, onSelectTemplate, type }: TemplateSelectorProps) {
  const templateKeys = Object.keys(templates);

  if (templateKeys.length === 0) {
    return null;
  }

  return (
    <div className="border-b pb-4 mb-4">
      <div className="flex items-start gap-4">
        <div className="flex-1 space-y-2">
          <Label htmlFor="template" className="flex items-center gap-2">
            <FileText className="h-4 w-4" />
            Utiliser un template
            <Badge variant="secondary" className="text-xs">Optionnel</Badge>
          </Label>
          <Select onValueChange={onSelectTemplate}>
            <SelectTrigger id="template">
              <SelectValue placeholder={`Sélectionner un template ${type}...`} />
            </SelectTrigger>
            <SelectContent>
              {templateKeys.map(key => (
                <SelectItem key={key} value={key}>
                  <div className="flex flex-col">
                    <span className="font-medium">{templates[key].name}</span>
                    <span className="text-xs text-muted-foreground">{templates[key].description}</span>
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <p className="text-xs text-muted-foreground">
            Les templates pré-remplissent les champs avec des placeholders intelligents à personnaliser
          </p>
        </div>
      </div>
    </div>
  );
}
