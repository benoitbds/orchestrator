"use client";

import { useState, useEffect, useRef } from 'react';
import { Copy, User, Bot, CheckCircle, AlertCircle, Clock, Settings, ChevronDown, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { toast } from 'sonner';
import { useRunsStore, type AgentEvent } from '@/stores/useRunsStore';
import { useAgentStream } from '@/hooks/useAgentStream';
import { ChatComposer } from './ChatComposer';
import { cn } from '@/lib/utils';
import { apiFetch } from '@/lib/api';

interface Message {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: number;
  runId?: string;
  status?: 'sending' | 'completed' | 'failed';
}

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

interface AgentAreaProps {
  onItemHighlight?: (itemId: number) => void;
  onBacklogRefresh?: () => Promise<void>;
  currentProject?: { id: number; name: string; description?: string };
}

export function AgentArea({ onItemHighlight, onBacklogRefresh, currentProject }: AgentAreaProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [expandedTools, setExpandedTools] = useState<Set<string>>(new Set());
  const scrollRef = useRef<HTMLDivElement>(null);
  const [isNearBottom, setIsNearBottom] = useState(true);
  const [userHasScrolled, setUserHasScrolled] = useState(false);

  const { currentRunId, startRun, isRunning, runs, getCurrentRun } = useRunsStore();

  // WebSocket connection
  useAgentStream(currentRunId, {
    onFinish: async (summary) => {
      // Update the agent message with final content
      setMessages(prev => prev.map(msg => 
        msg.runId === currentRunId 
          ? { ...msg, content: summary, status: 'completed' as const }
          : msg
      ));

      // Refresh backlog data
      if (currentProject && onBacklogRefresh) {
        await onBacklogRefresh();
      }
    },
    onError: (error) => {
      setMessages(prev => prev.map(msg => 
        msg.runId === currentRunId 
          ? { ...msg, content: `Error: ${error}`, status: 'failed' as const }
          : msg
      ));
    }
  });

  const handleSend = async (objective: string) => {
    if (!currentProject) {
      toast.error('Please select a project first');
      return;
    }

    try {
      const response = await apiFetch('/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          objective, 
          project_id: currentProject.id 
        }),
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(errorText || 'Failed to start chat');
      }

      const { run_id } = await response.json();
      
      if (!run_id) {
        throw new Error('No run ID received');
      }

      // Add user message
      const userMessage: Message = {
        id: `user-${Date.now()}`,
        type: 'user',
        content: objective,
        timestamp: Date.now(),
      };

      // Add placeholder agent message
      const agentMessage: Message = {
        id: `agent-${Date.now()}`,
        type: 'agent',
        content: 'Processing your request...',
        timestamp: Date.now(),
        runId: run_id,
        status: 'sending',
      };

      setMessages(prev => [...prev, userMessage, agentMessage]);
      startRun(run_id);
    } catch (error) {
      console.error('Failed to send message:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to send message');
    }
  };

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

    return events.sort((a, b) => a.timestamp - b.timestamp);
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
        <div className="flex-1 flex items-center justify-center p-8">
          <div className="text-center text-muted-foreground">
            <Bot className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <h3 className="text-lg font-medium mb-2">Ready to help with your backlog</h3>
            <p className="text-sm max-w-md">
              Start a conversation to analyze, create, or manage your backlog items. 
              I can help you with features, user stories, capabilities, and more.
            </p>
          </div>
        </div>
        <ChatComposer
          onSend={handleSend}
          isSending={isRunning()}
          projectId={currentProject?.id}
        />
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full">
      {/* Unified Timeline Feed */}
      <div 
        ref={scrollRef}
        className="flex-1 overflow-y-auto scroll-smooth p-4 space-y-3"
        onScroll={handleScroll}
        aria-live="polite"
        aria-label="Agent conversation timeline"
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
                  "flex gap-3 max-w-4xl",
                  msg.type === 'user' ? "justify-end" : "justify-start"
                )}
              >
                {msg.type === 'agent' && (
                  <div className="flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                      <Bot className="h-4 w-4 text-primary-foreground" />
                    </div>
                  </div>
                )}

                <Card className={cn(
                  "max-w-[80%] p-4",
                  msg.type === 'user' 
                    ? "bg-primary text-primary-foreground" 
                    : "bg-muted/50"
                )}>
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {msg.type === 'user' && (
                          <User className="h-4 w-4" />
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
                        className="h-6 w-6 p-0 opacity-60 hover:opacity-100"
                      >
                        <Copy className="h-3 w-3" />
                      </Button>
                    </div>

                    <div 
                      className="prose prose-sm max-w-none dark:prose-invert"
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
                            className="h-6 px-2 text-xs"
                            onClick={() => handleItemIdClick(itemId)}
                          >
                            Item #{itemId}
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
                    <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center">
                      <User className="h-4 w-4" />
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
                <Card className="max-w-2xl w-full bg-indigo-50 dark:bg-indigo-950/20 border-indigo-200 dark:border-indigo-800">
                  <div className="p-3">
                    <div className="flex items-center gap-2">
                      <Settings className="h-4 w-4 text-indigo-600" />
                      <Badge variant="secondary" className="bg-indigo-100 text-indigo-700 dark:bg-indigo-900 dark:text-indigo-300">
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
                          className="h-6 px-2 text-xs"
                        >
                          {isExpanded ? 'Hide' : 'Show'} details
                          {isExpanded ? (
                            <ChevronDown className="h-3 w-3 ml-1" />
                          ) : (
                            <ChevronRight className="h-3 w-3 ml-1" />
                          )}
                        </Button>
                        
                        {isExpanded && (
                          <pre className="text-xs bg-muted p-2 rounded mt-2 overflow-x-auto">
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
                <Card className="max-w-2xl w-full bg-emerald-50 dark:bg-emerald-950/20 border-emerald-200 dark:border-emerald-800">
                  <div className="p-3">
                    <div className="flex items-center gap-2">
                      <CheckCircle className="h-4 w-4 text-emerald-600" />
                      <Badge variant="secondary" className="bg-emerald-100 text-emerald-700 dark:bg-emerald-900 dark:text-emerald-300">
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
                <Card className="max-w-2xl w-full bg-rose-50 dark:bg-rose-950/20 border-rose-200 dark:border-rose-800">
                  <div className="p-3">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="h-4 w-4 text-rose-600" />
                      <Badge variant="secondary" className="bg-rose-100 text-rose-700 dark:bg-rose-900 dark:text-rose-300">
                        Error
                      </Badge>
                      <span className="text-xs text-muted-foreground ml-auto">
                        {new Date(event.timestamp).toLocaleTimeString()}
                      </span>
                    </div>
                    {event.content && (
                      <div className="mt-2 text-sm text-rose-700 dark:text-rose-300">
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
        <div className="absolute bottom-20 right-4">
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

      {/* Chat Composer - Always at bottom */}
      <ChatComposer
        onSend={handleSend}
        isSending={isRunning()}
        projectId={currentProject?.id}
      />
    </div>
  );
}