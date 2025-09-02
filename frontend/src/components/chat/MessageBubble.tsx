'use client';
import React from 'react';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';

interface MessageBubbleProps {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export function MessageBubble({ role, content, timestamp }: MessageBubbleProps) {
  const isUser = role === 'user';
  return (
    <div className={cn('flex flex-col max-w-[75%]', isUser ? 'ml-auto items-end' : 'mr-auto items-start')}>
      <div className={cn('rounded-2xl px-4 py-2', isUser ? 'bg-primary text-white' : 'bg-muted text-foreground')}>
        {isUser ? <p>{content}</p> : <ReactMarkdown>{content}</ReactMarkdown>}
      </div>
      {timestamp && (
        <span className="mt-1 text-xs text-muted-foreground">{timestamp}</span>
      )}
    </div>
  );
}
