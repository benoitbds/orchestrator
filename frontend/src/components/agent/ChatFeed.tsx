"use client";

import { useEffect, useRef, useState } from 'react';
import { Copy, User, Bot, CheckCircle, AlertCircle, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { useRunsStore, type AgentEvent } from '@/stores/useRunsStore';
import { cn } from '@/lib/utils';

interface Message {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: number;
  runId?: string;
  events?: AgentEvent[];
  status?: 'sending' | 'completed' | 'failed';
}

interface ChatFeedProps {
  messages: Message[];
  className?: string;
}

export function ChatFeed({ messages, className }: ChatFeedProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [userHasScrolled, setUserHasScrolled] = useState(false);

  const { runs } = useRunsStore();

  const handleCopy = async (content: string) => {
    try {
      await navigator.clipboard.writeText(content);
      toast.success('Copied to clipboard');
    } catch (error) {
      toast.error('Failed to copy');
    }
  };

  const scrollToBottom = () => {
    if (scrollRef.current && isNearBottom && !userHasScrolled) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  };

  const handleScroll = () => {
    if (!scrollRef.current) return;
    
    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;
    const distanceFromBottom = scrollHeight - scrollTop - clientHeight;
    
    setIsNearBottom(distanceFromBottom < 100);
    setUserHasScrolled(true);
    
    // Reset user scrolled flag after a delay
    setTimeout(() => setUserHasScrolled(false), 1000);
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isNearBottom, userHasScrolled]);

  const renderToolBadges = (events: AgentEvent[]) => {
    const toolEvents = events.filter(e => e.node.startsWith('tool:'));
    const tools = new Set<string>();
    
    toolEvents.forEach(event => {
      const toolName = event.node.split(':')[1];
      if (toolName) tools.add(toolName);
    });

    return Array.from(tools).map(tool => (
      <Badge 
        key={tool} 
        variant="secondary" 
        className="text-xs"
      >
        {tool}
      </Badge>
    ));
  };

  const getMessageStatus = (message: Message) => {
    if (message.type === 'user') return null;
    
    if (message.runId) {
      const run = runs[message.runId];
      if (run) {
        switch (run.status) {
          case 'running':
            return { icon: Clock, color: 'text-blue-500', text: 'Processing' };
          case 'completed':
            return { icon: CheckCircle, color: 'text-green-500', text: 'Completed' };
          case 'failed':
            return { icon: AlertCircle, color: 'text-red-500', text: 'Failed' };
        }
      }
    }
    
    return message.status === 'sending' 
      ? { icon: Clock, color: 'text-blue-500', text: 'Sending' }
      : null;
  };

  const formatContent = (content: string) => {
    // Basic markdown-like formatting
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-sm">$1</code>')
      .replace(/\n/g, '<br />');
  };

  if (messages.length === 0) {
    return (
      <div className={cn("flex-1 flex items-center justify-center p-8", className)}>
        <div className="text-center text-muted-foreground">
          <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
          <h3 className="text-lg font-medium mb-2">Ready to help with your backlog</h3>
          <p className="text-sm max-w-md">
            Start a conversation to analyze, create, or manage your backlog items. 
            I can help you with features, user stories, capabilities, and more.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className={cn("flex-1 flex flex-col", className)}>
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto scroll-smooth p-4 space-y-4"
        onScroll={handleScroll}
      >
        {messages.map((message) => {
          const status = getMessageStatus(message);
          const runEvents = message.runId ? runs[message.runId]?.events || [] : [];
          
          return (
            <div
              key={message.id}
              className={cn(
                "flex gap-3 max-w-4xl",
                message.type === 'user' ? "justify-end" : "justify-start"
              )}
            >
              {message.type === 'agent' && (
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary-foreground" />
                  </div>
                </div>
              )}

              <Card className={cn(
                "max-w-[80%] p-4",
                message.type === 'user' 
                  ? "bg-primary text-primary-foreground" 
                  : "bg-muted/50"
              )}>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      {message.type === 'user' && (
                        <User className="h-4 w-4" />
                      )}
                      <span className="text-xs font-medium">
                        {message.type === 'user' ? 'You' : 'Agent'}
                      </span>
                      <span className="text-xs opacity-70">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleCopy(message.content)}
                      className="h-6 w-6 p-0 opacity-60 hover:opacity-100"
                    >
                      <Copy className="h-3 w-3" />
                    </Button>
                  </div>

                  <div 
                    className="prose prose-sm max-w-none dark:prose-invert"
                    dangerouslySetInnerHTML={{ 
                      __html: formatContent(message.content) 
                    }}
                  />

                  {/* Tool badges and status */}
                  {message.type === 'agent' && (
                    <div className="flex items-center justify-between pt-2">
                      <div className="flex gap-1">
                        {renderToolBadges(runEvents)}
                      </div>
                      
                      {status && (
                        <div className="flex items-center gap-1 text-xs">
                          <status.icon className={cn("h-3 w-3", status.color)} />
                          <span className={status.color}>{status.text}</span>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </Card>

              {message.type === 'user' && (
                <div className="flex-shrink-0">
                  <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                    <User className="h-4 w-4" />
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Scroll to bottom button */}
      {!isNearBottom && (
        <div className="absolute bottom-4 right-4">
          <Button
            variant="secondary"
            size="sm"
            onClick={() => {
              setIsNearBottom(true);
              setUserHasScrolled(false);
              scrollToBottom();
            }}
            className="shadow-lg"
          >
            Scroll to bottom
          </Button>
        </div>
      )}
    </div>
  );
}