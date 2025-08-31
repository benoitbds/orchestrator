"use client";

import { useState, useRef, useEffect } from 'react';
import { Copy, User, Bot, CheckCircle, AlertCircle, Clock, Settings, ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { useRunsStore, type AgentEvent } from '@/stores/useRunsStore';
import { type Message } from '@/stores/useMessagesStore';
import { cn } from '@/lib/utils';

interface TimelineEvent {
  id: string;
  type: 'message' | 'tool' | 'write' | 'error';
  timestamp: number;
  runId?: string;
  content?: string;
  toolName?: string;
  duration?: number;
  agentEvent?: AgentEvent;
  message?: Message;
  status?: 'sending' | 'completed' | 'failed';
}

interface ConversationHistoryProps {
  messages: Message[];
  onItemHighlight?: (itemId: number) => void;
}

export function ConversationHistory({ messages, onItemHighlight }: ConversationHistoryProps) {
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
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

  const createTimelineEvents = (): TimelineEvent[] => {
    const events: TimelineEvent[] = [];

    // Add messages
    messages.forEach(msg => {
      events.push({
        id: msg.id,
        type: 'message',
        timestamp: msg.timestamp,
        runId: msg.runId,
        message: msg,
        status: msg.status,
      });
    });

    // Add agent events from runs
    Object.entries(runs).forEach(([runId, run]) => {
      const toolCallDurations = new Map<string, number>();
      
      // Calculate durations for tool calls
      run.events.forEach((event, index) => {
        if (event.node.includes(':request')) {
          const toolName = event.node.split(':')[1];
          const requestTime = new Date(event.ts || '').getTime();
          
          const responseEvent = run.events.slice(index + 1).find(e => 
            e.node.includes(':response') && e.node.split(':')[1] === toolName
          );
          
          if (responseEvent) {
            const responseTime = new Date(responseEvent.ts || '').getTime();
            toolCallDurations.set(event.node, responseTime - requestTime);
          }
        }
      });

      run.events.forEach(event => {
        const timestamp = event.ts ? new Date(event.ts).getTime() : Date.now();
        
        if (event.node.startsWith('tool:')) {
          events.push({
            id: `${runId}-${event.node}-${timestamp}`,
            type: 'tool',
            timestamp,
            runId,
            toolName: event.node.split(':')[1],
            duration: toolCallDurations.get(event.node),
            agentEvent: event,
          });
        } else if (event.node === 'write') {
          events.push({
            id: `${runId}-write-${timestamp}`,
            type: 'write',
            timestamp,
            runId,
            content: typeof event.content === 'string' ? event.content : JSON.stringify(event.content),
            agentEvent: event,
          });
        } else if (event.error || event.ok === false) {
          events.push({
            id: `${runId}-error-${timestamp}`,
            type: 'error',
            timestamp,
            runId,
            content: event.error || 'Unknown error',
            agentEvent: event,
          });
        }
      });
    });

    return events.sort((a, b) => b.timestamp - a.timestamp); // Reverse chronological
  };

  const timelineEvents = createTimelineEvents();

  const toggleToolExpanded = (toolId: string) => {
    const newExpanded = new Set(expandedTools);
    if (newExpanded.has(toolId)) {
      newExpanded.delete(toolId);
    } else {
      newExpanded.add(toolId);
    }
    setExpandedTools(newExpanded);
  };

  const formatDuration = (ms: number) => {
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatContent = (content: string) => {
    // Basic markdown-like formatting
    return content
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`(.*?)`/g, '<code class="bg-muted px-1 py-0.5 rounded text-sm">$1</code>')
      .replace(/\n/g, '<br />');
  };

  const extractItemIds = (content: string): number[] => {
    const itemIdRegex = /item[_\s]*(?:id)?[_\s]*[:#]?\s*(\d+)/gi;
    const matches = [];
    let match;
    while ((match = itemIdRegex.exec(content)) !== null) {
      matches.push(parseInt(match[1]));
    }
    return [...new Set(matches)]; // Remove duplicates
  };

  const handleItemIdClick = (itemId: number) => {
    if (onItemHighlight) {
      onItemHighlight(itemId);
    }
  };

  if (timelineEvents.length === 0) {
    return (
      <div className="flex flex-col h-full">
        <div className="p-4 border-b">
          <h2 className="font-semibold">Conversation History</h2>
        </div>
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center text-muted-foreground">
            <Bot className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">No conversations yet</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b">
        <h2 className="font-semibold">Conversation History</h2>
        <p className="text-xs text-muted-foreground mt-1">Latest first</p>
      </div>

      {/* Timeline Feed - Reverse chronological */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto scroll-smooth p-4 space-y-3"
        onScroll={handleScroll}
        aria-live="polite"
        aria-label="Conversation history timeline"
      >
        {timelineEvents.map((event) => {
          if (event.type === 'message' && event.message) {
            const msg = event.message;
            const status = msg.status;
            const itemIds = extractItemIds(msg.content);
            
            return (
              <div
                key={event.id}
                className={cn(
                  "flex gap-3",
                  msg.type === 'user' ? "justify-end" : "justify-start"
                )}
              >
                {msg.type === 'agent' && (
                  <div className="flex-shrink-0">
                    <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center">
                      <Bot className="h-3 w-3 text-primary-foreground" />
                    </div>
                  </div>
                )}

                <Card className={cn(
                  "max-w-[85%] p-3",
                  msg.type === 'user' 
                    ? "bg-primary text-primary-foreground" 
                    : "bg-muted/50"
                )}>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {msg.type === 'user' && (
                          <User className="h-3 w-3" />
                        )}
                        <span className="text-xs font-medium">
                          {msg.type === 'user' ? 'You' : 'Agent'}
                        </span>
                        <span className="text-xs opacity-70">
                          {new Date(msg.timestamp).toLocaleTimeString()}
                        </span>
                      </div>
                      
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleCopy(msg.content)}
                        className="h-5 w-5 p-0 opacity-60 hover:opacity-100"
                      >
                        <Copy className="h-2 w-2" />
                      </Button>
                    </div>

                    <div 
                      className="prose prose-xs max-w-none dark:prose-invert"
                      dangerouslySetInnerHTML={{ 
                        __html: formatContent(msg.content) 
                      }}
                    />

                    {/* Item ID badges */}
                    {itemIds.length > 0 && (
                      <div className="flex gap-1 pt-2 flex-wrap">
                        {itemIds.map(itemId => (
                          <Button
                            key={itemId}
                            variant="outline"
                            size="sm"
                            className="h-5 px-2 text-xs"
                            onClick={() => handleItemIdClick(itemId)}
                          >
                            #{itemId}
                          </Button>
                        ))}
                      </div>
                    )}

                    {/* Status indicator */}
                    {status && msg.type === 'agent' && (
                      <div className="flex items-center justify-end pt-2">
                        <div className="flex items-center gap-1 text-xs">
                          {status === 'sending' && <Clock className="h-3 w-3 text-blue-500" />}
                          {status === 'completed' && <CheckCircle className="h-3 w-3 text-green-500" />}
                          {status === 'failed' && <AlertCircle className="h-3 w-3 text-red-500" />}
                          <span className={cn(
                            status === 'sending' && 'text-blue-500',
                            status === 'completed' && 'text-green-500',
                            status === 'failed' && 'text-red-500'
                          )}>
                            {status === 'sending' ? 'Processing' : status}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                </Card>

                {msg.type === 'user' && (
                  <div className="flex-shrink-0">
                    <div className="w-6 h-6 rounded-full bg-muted flex items-center justify-center">
                      <User className="h-3 w-3" />
                    </div>
                  </div>
                )}
              </div>
            );
          }

          // Tool events embedded in timeline
          if (event.type === 'tool' && event.agentEvent) {
            const isExpanded = expandedTools.has(event.id);
            const toolContent = event.agentEvent.args && Object.keys(event.agentEvent.args).length > 0
              ? JSON.stringify(event.agentEvent.args, null, 2)
              : event.agentEvent.result
                ? JSON.stringify(event.agentEvent.result, null, 2)
                : '';

            return (
              <div key={event.id} className="flex justify-center">
                <Card className="max-w-full w-full bg-indigo-50 dark:bg-indigo-950/20 border-indigo-200 dark:border-indigo-800">
                  <div className="p-2">
                    <div className="flex items-center gap-2">
                      <Settings className="h-3 w-3 text-indigo-600" />
                      <Badge variant="secondary" className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300 text-xs">
                        {event.toolName}
                      </Badge>
                      {event.duration && (
                        <Badge variant="outline" className="text-xs">
                          {formatDuration(event.duration)}
                        </Badge>
                      )}
                      <span className="text-xs text-muted-foreground ml-auto">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    
                    {toolContent && (
                      <div className="mt-2">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => toggleToolExpanded(event.id)}
                          className="h-5 px-2 text-xs"
                        >
                          {isExpanded ? 'Hide' : 'Show'} details
                          {isExpanded ? (
                            <ChevronDown className="h-3 w-3 ml-1" />
                          ) : (
                            <ChevronRight className="h-3 w-3 ml-1" />
                          )}
                        </Button>
                        
                        {isExpanded && (
                          <pre className="text-xs bg-muted p-2 rounded mt-2 overflow-x-auto max-h-32 overflow-y-auto">
                            {toolContent}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                </Card>
              </div>
            );
          }

          // Write events
          if (event.type === 'write') {
            return (
              <div key={event.id} className="flex justify-center">
                <Card className="max-w-full w-full bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800">
                  <div className="p-2">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-3 w-3 text-emerald-600" />
                      <Badge variant="secondary" className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300 text-xs">
                        Completed
                      </Badge>
                      <span className="text-xs text-muted-foreground ml-auto">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                  </div>
                </Card>
              </div>
            );
          }

          // Error events
          if (event.type === 'error') {
            return (
              <div key={event.id} className="flex justify-center">
                <Card className="max-w-full w-full bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800">
                  <div className="p-2">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-3 w-3 text-rose-600" />
                      <Badge variant="secondary" className="bg-rose-100 text-rose-700 dark:bg-rose-900 dark:text-rose-300 text-xs">
                        Error
                      </Badge>
                      <span className="text-xs text-muted-foreground ml-auto">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    {event.content && (
                      <div className="mt-2 text-xs text-rose-700 dark:text-rose-300">
                        {event.content}
                      </div>
                    )}
                  </div>
                </Card>
              </div>
            );
          }

          return null;
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
            className="shadow-lg h-8 px-3 text-xs"
          >
            Scroll to bottom
          </Button>
        </div>
      )}
    </div>
  );
}