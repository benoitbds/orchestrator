'use client';
import { useState } from 'react';
import { UploadDropzone } from '@/components/UploadDropzone';
import { TabsBacklog } from '@/components/TabsBacklog';
import { EmptyState } from '@/components/EmptyState';
import { ConversationPanel, ChatMessage } from '@/components/chat/ConversationPanel';
import { SectionHeader } from '@/components/layout/SectionHeader';
import { LanguageToggle } from '@/components/LanguageToggle';
import { Inbox } from 'lucide-react';
import { useLanguage } from '@/context/LanguageContext';
import { getDict } from '@/i18n/dictionary';

export default function Home() {
  const { lang } = useLanguage();
  const t = getDict(lang);
  const [messages, setMessages] = useState<ChatMessage[]>(() =>
    Array.from({ length: 1000 }).map((_, i) => ({
      id: `${i}`,
      role: i % 2 ? 'assistant' : 'user',
      content: `Message ${i}`,
      timestamp: new Date().toLocaleTimeString(),
    }))
  );
  const handleClear = () => setMessages([]);
  const [backlogItems] = useState<string[]>([]);
  const [tab, setTab] = useState<'diagram' | 'tree' | 'table'>('diagram');
  return (
    <div className="h-screen flex flex-col bg-muted">
      <header className="p-4 border-b flex justify-between items-center bg-white shadow-soft">
        <h1 className="text-xl font-bold">Agent 4 BA</h1>
        <LanguageToggle />
      </header>
      <div className="flex-1 grid grid-cols-12 gap-4 p-4">
        <div className="col-span-3 bg-white rounded-2xl shadow-soft p-4 flex flex-col">
          <SectionHeader title={t.projects} />
          <div className="flex-1" />
          <SectionHeader title={t.documents} />
          <UploadDropzone onFilesAccepted={() => {}} />
        </div>
        <div className="col-span-6 bg-white rounded-2xl shadow-soft p-4 flex flex-col">
          <SectionHeader title={t.backlog} />
          <TabsBacklog active={tab} onChange={setTab} onCreateItem={() => {}} />
          <div className="flex-1 flex items-center justify-center">
            {backlogItems.length === 0 ? (
              <EmptyState
                icon={<Inbox className="h-8 w-8" />}
                title={t.emptyBacklogTitle}
                subtitle={t.emptyBacklogSubtitle}
                primaryAction={{ label: t.createFirstItem, onClick: () => {} }}
                secondaryAction={{ label: t.importDocument, onClick: () => {} }}
              />
            ) : null}
          </div>
        </div>
        <div className="col-span-3 bg-white rounded-2xl shadow-soft p-4 flex flex-col">
          <SectionHeader title={t.conversationHistory} />
          <ConversationPanel messages={messages} onClear={handleClear} />
        </div>
      </div>
    </div>
  );
}
