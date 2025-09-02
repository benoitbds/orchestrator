'use client';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Button } from '@/components/ui/button';
import { useLanguage } from '@/context/LanguageContext';
import { getDict } from '@/i18n/dictionary';

interface TabsBacklogProps {
  active: 'diagram' | 'tree' | 'table';
  onChange: (k: 'diagram' | 'tree' | 'table') => void;
  onCreateItem: () => void;
}

export function TabsBacklog({ active, onChange, onCreateItem }: TabsBacklogProps) {
  const { lang } = useLanguage();
  const t = getDict(lang);
  return (
    <div className="flex items-center justify-between border-b pb-2 mb-4">
      <Tabs value={active} onValueChange={v => onChange(v as TabsBacklogProps['active'])}>
        <TabsList className="bg-transparent">
          <TabsTrigger
            value="diagram"
            className="data-[state=active]:border-b-2 data-[state=active]:border-primary"
          >
            {t.diagramView}
          </TabsTrigger>
          <TabsTrigger
            value="tree"
            className="data-[state=active]:border-b-2 data-[state=active]:border-primary"
          >
            {t.treeView}
          </TabsTrigger>
          <TabsTrigger
            value="table"
            className="data-[state=active]:border-b-2 data-[state=active]:border-primary"
          >
            {t.tableView}
          </TabsTrigger>
        </TabsList>
      </Tabs>
      <Button onClick={onCreateItem}>{t.newItem}</Button>
    </div>
  );
}
