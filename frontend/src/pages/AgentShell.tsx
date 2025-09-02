"use client";

import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { useProjects } from '@/context/ProjectContext';
import { useRunsStore } from '@/stores/useRunsStore';
import { useBacklog } from '@/context/BacklogContext';
import { mutate } from 'swr';
import { useAgentStream } from '@/hooks/useAgentStream';
import { ChatComposer } from '@/components/agent/ChatComposer';
import { BacklogPanel } from '@/components/backlog/BacklogPanel';
import { ProjectPanel } from '@/components/project/ProjectPanel';
import { ConversationHistory } from '@/components/agent/ConversationHistory';
import { useMessagesStore, type Message } from '@/stores/useMessagesStore';
import { toast } from 'sonner';
import { http } from '@/lib/api';
import { APP_CONFIG } from '@/lib/constants';


export function AgentShell() {
  const [highlightItemId, setHighlightItemId] = useState<number>();
  const [activeTab, setActiveTab] = useState("backlog");
  const [isHydrated, setIsHydrated] = useState(false);
  const [pendingObjective, setPendingObjective] = useState<string>();

  const { currentProject } = useProjects();
  const { refreshItems } = useBacklog();
  const { currentRunId, startRun, isRunning, getCurrentRun } = useRunsStore();
  const { messages, addMessage, updateMessage, getMessagesForProject } = useMessagesStore();

  // Handle hydration for persisted stores
  useEffect(() => {
    const rehydrateStores = async () => {
      // Manually rehydrate the stores after component mounts
      await useRunsStore.persist.rehydrate();
      await useMessagesStore.persist.rehydrate();
      setIsHydrated(true);
    };
    rehydrateStores();
  }, []);

  // Get messages for current project
  const currentMessages = isHydrated ? getMessagesForProject(currentProject?.id) : [];

  // WebSocket connection
  useAgentStream(currentRunId, {
    objective: pendingObjective,
    projectId: currentProject?.id,
    onRunIdUpdate: (tempRunId: string, realRunId: string) => {
      console.log('Run ID updated:', { tempRunId, realRunId });
      // Update the agent message with the real run ID
      const { messages: allMessages, updateMessage: updateMsg } = useMessagesStore.getState();
      const agentMessage = allMessages.find(msg => 
        msg.runId === tempRunId && 
        msg.type === 'agent' && 
        msg.projectId === currentProject?.id
      );
      if (agentMessage) {
        updateMsg(agentMessage.id, { runId: realRunId });
      }
    },
    onFinish: async (summary) => {
      console.log('onFinish called with:', { summary, currentRunId, projectId: currentProject?.id });
      // Update the agent message with final content - get fresh messages from store
      const { messages: allMessages, updateMessage: updateMsg } = useMessagesStore.getState();
      const agentMessage = allMessages.find(msg => 
        msg.type === 'agent' && 
        msg.projectId === currentProject?.id &&
        msg.status === 'sending'
      );
      console.log('All messages:', allMessages.length, 'Found agent message:', agentMessage);
      if (agentMessage) {
        console.log('Updating message with summary:', summary);
        updateMsg(agentMessage.id, { content: summary, status: 'completed' });
      } else {
        console.error('Agent message not found');
      }

      // Clear pending objective
      setPendingObjective(undefined);

      // Refresh backlog data
      if (currentProject) {
        await refreshItems();
        await mutate(`/items?project_id=${currentProject.id}`);
      }
    },
    onError: (error) => {
      console.log('onError called with error:', error);
      const { messages: allMessages, updateMessage: updateMsg } = useMessagesStore.getState();
      const agentMessage = allMessages.find(msg => 
        msg.type === 'agent' && 
        msg.projectId === currentProject?.id &&
        msg.status === 'sending'
      );
      if (agentMessage) {
        updateMsg(agentMessage.id, { content: `Error: ${error}`, status: 'failed' });
      }
      setPendingObjective(undefined);
    }
  });

  const handleSend = async (objective: string) => {
    if (!currentProject) {
      toast.error('Please select a project first');
      return;
    }

    // Generate a temporary run ID for tracking
    const tempRunId = `temp-${Date.now()}`;

    // Add user message immediately
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: 'user',
      content: objective,
      timestamp: Date.now(),
      projectId: currentProject.id,
    };

    // Add placeholder agent message
    const agentMessage: Message = {
      id: `agent-${Date.now()}`,
      type: 'agent',
      content: 'Processing your request...',
      timestamp: Date.now(),
      runId: tempRunId,
      status: 'sending',
      projectId: currentProject.id,
    };

    console.log('Adding messages:', { userMessage, agentMessage });
    addMessage(userMessage);
    addMessage(agentMessage);
    
    // Set pending objective for WebSocket
    setPendingObjective(objective);
    
    // Start run with temp ID
    startRun(tempRunId);
  };

  const getStatusBadge = () => {
    const currentRun = getCurrentRun();
    if (currentRun?.status === 'running') {
      return <Badge variant="secondary" className="animate-pulse">Running</Badge>;
    }
    return <Badge variant="outline">Idle</Badge>;
  };

  const handleItemHighlight = (itemId: number) => {
    setHighlightItemId(itemId);
    // Brief highlight that fades after 2 seconds
    setTimeout(() => setHighlightItemId(undefined), 2000);
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
              <h1 className="text-xl font-bold">{APP_CONFIG.name}</h1>
              {getStatusBadge()}
            </div>
          </div>
        </header>

        {/* Mobile Tabs - 3 tabs for new layout */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-3 rounded-none">
            <TabsTrigger value="projects">Projects</TabsTrigger>
            <TabsTrigger value="backlog">Backlog</TabsTrigger>
            <TabsTrigger value="history">History</TabsTrigger>
          </TabsList>

          <div className="flex-1 flex flex-col overflow-hidden">
            <TabsContent value="projects" className="flex-1 m-0">
              <ProjectPanel />
            </TabsContent>

            <TabsContent value="backlog" className="flex-1 flex flex-col m-0">
              {/* User Input on top */}
              <div className="border-b">
                <ChatComposer
                  onSend={handleSend}
                  isSending={isRunning()}
                  projectId={currentProject?.id}
                />
              </div>
              {/* Backlog below */}
              <div className="flex-1">
                <BacklogPanel 
                  highlightItemId={highlightItemId}
                  onItemClick={setHighlightItemId}
                />
              </div>
            </TabsContent>

            <TabsContent value="history" className="flex-1 m-0">
              <ConversationHistory 
                messages={currentMessages}
                onItemHighlight={handleItemHighlight}
              />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    );
  }

  // Desktop 3-Panel Layout
  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Desktop Header */}
      <header className="border-b p-4">
        <div className="container max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">{APP_CONFIG.name}</h1>
            {getStatusBadge()}
          </div>
        </div>
      </header>

      {/* Desktop 3-Panel Layout */}
      <div className="flex-1 grid grid-cols-12 gap-4 p-4 container max-w-7xl mx-auto overflow-hidden">
        {/* Left Panel - Project Management */}
        <div className="col-span-3 border rounded-2xl overflow-hidden shadow-sm">
          <ProjectPanel />
        </div>

        {/* Center Panel - User Input (top) + Backlog (60% height) */}
        <div className="col-span-6 flex flex-col gap-4">
          {/* User Input Section */}
          <div className="border rounded-2xl shadow-sm">
            <ChatComposer
              onSend={handleSend}
              isSending={isRunning()}
              projectId={currentProject?.id}
            />
          </div>
          
          {/* Backlog Section - 60% of remaining space */}
          <div className="flex-1 border rounded-2xl shadow-sm">
            <BacklogPanel 
              highlightItemId={highlightItemId}
              onItemClick={setHighlightItemId}
            />
          </div>
        </div>

        {/* Right Panel - Conversation History */}
        <div className="col-span-3 border rounded-2xl overflow-hidden shadow-sm">
          <ConversationHistory 
            messages={currentMessages}
            onItemHighlight={handleItemHighlight}
          />
        </div>
      </div>
    </div>
  );
}