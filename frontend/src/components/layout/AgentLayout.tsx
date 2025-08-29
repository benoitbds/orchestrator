"use client";

import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useProjects } from '@/context/ProjectContext';
import { useRunsStore } from '@/stores/useRunsStore';
import { useAgentStream } from '@/hooks/useAgentStream';
import { ChatFeed } from '@/components/agent/ChatFeed';
import { ChatComposer } from '@/components/agent/ChatComposer';
import { AgentLog } from '@/components/agent/AgentLog';
import { BacklogPanel } from '@/components/backlog/BacklogPanel';
import { mutate } from 'swr';
import { useBacklog } from '@/context/BacklogContext';
import { cn } from '@/lib/utils';

interface Message {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: number;
  runId?: string;
  status?: 'sending' | 'completed' | 'failed';
}

export function AgentLayout() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [highlightItemId, setHighlightItemId] = useState<number>();
  const [activeTab, setActiveTab] = useState("chat");

  const { projects, currentProject, setCurrentProject } = useProjects();
  const { refreshItems } = useBacklog();
  const { currentRunId, startRun, isRunning, getCurrentRun } = useRunsStore();

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
      if (currentProject) {
        await refreshItems();
        await mutate(`/items?project_id=${currentProject.id}`);
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

  const handleSend = (objective: string, runId: string) => {
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
      runId,
      status: 'sending',
    };

    setMessages(prev => [...prev, userMessage, agentMessage]);
    startRun(runId);
  };

  const handleProjectChange = (projectId: string) => {
    const project = projects.find(p => p.id.toString() === projectId);
    if (project) {
      setCurrentProject(project);
    }
  };

  const getStatusBadge = () => {
    const currentRun = getCurrentRun();
    if (currentRun?.status === 'running') {
      return <Badge variant="secondary" className="animate-pulse">Running</Badge>;
    }
    return <Badge variant="outline">Idle</Badge>;
  };

  // Mobile breakpoint check
  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);

  if (isMobile) {
    return (
      <div className="flex flex-col h-screen bg-background">
        {/* Mobile Header */}
        <header className="border-b p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold">Agent 4 BA</h1>
              {getStatusBadge()}
            </div>
            
            <Select
              value={currentProject?.id.toString() || ''}
              onValueChange={handleProjectChange}
            >
              <SelectTrigger className="w-40">
                <SelectValue placeholder="Select project" />
              </SelectTrigger>
              <SelectContent>
                {projects.map((project) => (
                  <SelectItem key={project.id} value={project.id.toString()}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </header>

        {/* Mobile Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-3 rounded-none">
            <TabsTrigger value="chat">Chat</TabsTrigger>
            <TabsTrigger value="backlog">Backlog</TabsTrigger>
            <TabsTrigger value="log">Journal</TabsTrigger>
          </TabsList>

          <div className="flex-1 flex flex-col overflow-hidden">
            <TabsContent value="chat" className="flex-1 flex flex-col m-0">
              <ChatFeed messages={messages} />
            </TabsContent>

            <TabsContent value="backlog" className="flex-1 m-0">
              <BacklogPanel 
                highlightItemId={highlightItemId}
                onItemClick={setHighlightItemId}
              />
            </TabsContent>

            <TabsContent value="log" className="flex-1 m-0">
              <AgentLog />
            </TabsContent>
          </div>

          {/* Mobile Composer - always visible */}
          <div className="border-t">
            <ChatComposer
              onSend={handleSend}
              isSending={isRunning()}
              projectId={currentProject?.id}
            />
          </div>
        </Tabs>
      </div>
    );
  }

  // Desktop Layout
  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Desktop Header */}
      <header className="border-b p-4">
        <div className="container max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">Agent 4 BA</h1>
            {getStatusBadge()}
          </div>
          
          <Select
            value={currentProject?.id.toString() || ''}
            onValueChange={handleProjectChange}
          >
            <SelectTrigger className="w-64">
              <SelectValue placeholder="Select a project" />
            </SelectTrigger>
            <SelectContent>
              {projects.map((project) => (
                <SelectItem key={project.id} value={project.id.toString()}>
                  <div>
                    <div className="font-medium">{project.name}</div>
                    {project.description && (
                      <div className="text-xs text-muted-foreground truncate">
                        {project.description}
                      </div>
                    )}
                  </div>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </header>

      {/* Desktop 3-Pane Layout */}
      <div className="flex-1 grid grid-cols-12 gap-4 p-4 container max-w-7xl mx-auto overflow-hidden">
        {/* Left Panel - Backlog */}
        <div className="col-span-3 border rounded-2xl overflow-hidden shadow-sm">
          <BacklogPanel 
            highlightItemId={highlightItemId}
            onItemClick={setHighlightItemId}
          />
        </div>

        {/* Center Panel - Chat */}
        <div className="col-span-6 border rounded-2xl overflow-hidden shadow-sm flex flex-col">
          <ChatFeed messages={messages} />
          <ChatComposer
            onSend={handleSend}
            isSending={isRunning()}
            projectId={currentProject?.id}
          />
        </div>

        {/* Right Panel - Agent Log */}
        <div className="col-span-3 border rounded-2xl overflow-hidden shadow-sm">
          <AgentLog />
        </div>
      </div>
    </div>
  );
}