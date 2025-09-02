'use client';
import { useState, useRef } from 'react';
import { useVirtualizer } from '@tanstack/react-virtual';
import { Button } from '@/components/ui/button';
import { MessageBubble } from './MessageBubble';
import { useLanguage } from '@/context/LanguageContext';

export interface ChatMessage {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

interface ConversationPanelProps {
  messages: ChatMessage[];
  onClear?: () => void;
}

export function ConversationPanel({ messages, onClear }: ConversationPanelProps) {
  const { lang } = useLanguage();
  const labels = {
    fr: { all: 'Tous', user: 'Utilisateur', assistant: 'Assistant', clear: 'Effacer' },
    en: { all: 'All', user: 'User', assistant: 'Assistant', clear: 'Clear' },
  }[lang];
  const [filter, setFilter] = useState<'all' | 'user' | 'assistant'>('all');
  const parentRef = useRef<HTMLDivElement>(null);
  const filtered = messages.filter(m => filter === 'all' || m.role === filter);
  const rowVirtualizer = useVirtualizer({
    count: filtered.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 72,
    overscan: 5,
  });
  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between border-b px-4 py-2">
        <div className="flex gap-2">
          {(['all', 'user', 'assistant'] as const).map(key => (
            <Button
              key={key}
              variant={filter === key ? 'default' : 'secondary'}
              onClick={() => setFilter(key)}
            >
              {labels[key]}
            </Button>
          ))}
        </div>
        <Button variant="ghost" onClick={onClear} aria-label={labels.clear}>
          {labels.clear}
        </Button>
      </div>
      <div ref={parentRef} className="flex-1 overflow-y-auto p-4">
        <div
          style={{ height: `${rowVirtualizer.getTotalSize()}px`, width: '100%', position: 'relative' }}
        >
          {rowVirtualizer.getVirtualItems().map(virtual => {
            const message = filtered[virtual.index];
            return (
              <div
                key={message.id}
                ref={rowVirtualizer.measureElement}
                style={{
                  position: 'absolute',
                  top: 0,
                  left: 0,
                  width: '100%',
                  transform: `translateY(${virtual.start}px)`,
                }}
              >
                <MessageBubble {...message} />
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
