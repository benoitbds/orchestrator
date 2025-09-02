import { useMemo } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { Copy, Database, Download } from 'lucide-react';
import type { HistoryRun } from '@/types/history';
import { ms } from '@/lib/history-utils';

function Markdown({ text }: { text: string }) {
  return <pre className="whitespace-pre-wrap break-words text-sm">{text}</pre>;
}

export function FinalAnswerCard({ run }: { run: HistoryRun }) {
  if (!run.finalAnswer) {
    return (
      <div className="rounded-2xl border bg-white p-4 shadow-sm">
        <div className="text-sm font-semibold">Final Answer</div>
        <div className="mt-2 text-sm text-destructive">Run did not complete successfully.</div>
      </div>
    );
  }

  const { markdown, json, html } = run.finalAnswer;
  const meta = useMemo(() => {
    const parts = [] as string[];
    if (run.modelMeta) parts.push(`${run.modelMeta.provider}/${run.modelMeta.model}`);
    if (run.modelMeta?.tokens != null) parts.push(`${run.modelMeta.tokens} tokens`);
    if (run.stats?.durationMs != null) parts.push(ms(run.stats.durationMs));
    return parts.join(' • ');
  }, [run]);

  return (
    <div className="rounded-2xl border bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <div className="text-sm font-semibold">Final Answer</div>
        <div className="flex gap-2">
          <Button size="sm" variant="secondary" onClick={() => navigator.clipboard.writeText(markdown ?? '')}>
            <Copy className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="secondary">
            <Download className="h-4 w-4" />
          </Button>
          <Button size="sm" variant="secondary">
            <Database className="h-4 w-4" />
          </Button>
        </div>
      </div>
      <Tabs defaultValue={markdown ? 'md' : json ? 'json' : 'html'} className="mt-2">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="md">Markdown</TabsTrigger>
          <TabsTrigger value="json">JSON</TabsTrigger>
          <TabsTrigger value="html">HTML</TabsTrigger>
        </TabsList>
        <TabsContent value="md">{markdown ? <Markdown text={markdown} /> : <div className="text-sm text-muted-foreground">No markdown</div>}</TabsContent>
        <TabsContent value="json">
          {json ? (
            <pre className="whitespace-pre-wrap break-words text-sm">{JSON.stringify(json, null, 2)}</pre>
          ) : (
            <div className="text-sm text-muted-foreground">No JSON</div>
          )}
        </TabsContent>
        <TabsContent value="html">
          {html ? (
            <div dangerouslySetInnerHTML={{ __html: html }} />
          ) : (
            <div className="text-sm text-muted-foreground">No HTML</div>
          )}
        </TabsContent>
      </Tabs>
      {meta && <div className="mt-2 text-xs text-muted-foreground">{meta}</div>}
    </div>
  );
}
