"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useProjects } from "@/context/ProjectContext";
import { useRunsStore } from "@/stores/useRunsStore";
import { useBacklog } from "@/context/BacklogContext";
import { mutate } from "swr";
import { useLangGraphStream } from "@/hooks/useLangGraphStream";
import { auth } from "@/lib/firebase";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { BacklogPanel } from "@/components/backlog/BacklogPanel";
import { ProjectPanel } from "@/components/project/ProjectPanel";
import ConversationHistory from "@/components/history/ConversationHistory";
import { AgentActionsPanel } from "@/components/AgentActionsPanel";
import { useMessagesStore, type Message } from "@/stores/useMessagesStore";
import { useHistory } from "@/store/useHistory";
import { toast } from "sonner";
import { APP_CONFIG } from "@/lib/constants";
import { safeId } from "@/lib/safeId";
import { ProfileMenu } from "@/components/ProfileMenu";
import type { AgentRunPayload } from "@/lib/api";

export default AgentShell;

// Disable SSR for this page since it requires client-side context providers
export async function getServerSideProps() {
  return { props: {} };
}

export function AgentShell() {
  const [activeTab, setActiveTab] = useState("backlog");
  const [isHydrated, setIsHydrated] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);

  const { currentProject } = useProjects();
  const { refreshItems } = useBacklog();
  const { startRun, isRunning: isOldRunning, getCurrentRun } = useRunsStore();
  const { addMessage, updateMessage } = useMessagesStore();
  
  // Multi-agent streaming
  const {
    agentActions,
    isComplete: isLangGraphComplete,
    currentStatus: langGraphStatus,
    progress: langGraphProgress,
    startAgentExecution,
  } = useLangGraphStream(runId);

  useEffect(() => {
    const rehydrateStores = async () => {
      await useRunsStore.persist.rehydrate();
      await useMessagesStore.persist.rehydrate();
      await useHistory.persist.rehydrate();
      setIsHydrated(true);
    };
    rehydrateStores();
  }, []);

  // Handle completion
  useEffect(() => {
    if (isLangGraphComplete && runId && currentProject) {
      // Update message and refresh items
      const { messages: allMessages } = useMessagesStore.getState();
      const agentMessage = allMessages.find(
        (msg) =>
          msg.type === "agent" &&
          msg.projectId === currentProject.id &&
          msg.status === "sending" &&
          msg.runId === runId,
      );
      if (agentMessage) {
        const summary = agentActions.length > 0 
          ? `Completed ${agentActions.length} agent actions successfully`
          : "Task completed";
        updateMessage(agentMessage.id, { content: summary, status: "completed" });
      }
      
      refreshItems();
      mutate(`/items?project_id=${currentProject.id}`);
    }
  }, [isLangGraphComplete, runId, currentProject, agentActions, refreshItems, updateMessage]);

  const handleSend = async (objective: string, meta?: AgentRunPayload['meta']) => {
    if (!currentProject) {
      toast.error("Please select a project first");
      return;
    }

    try {
      const token = await auth.currentUser?.getIdToken();
      if (!token) {
        toast.error('Failed to get authentication token');
        return;
      }

      const newRunId = `run-${Date.now()}`;
      setRunId(newRunId);
      
      useHistory.getState().createTurn(newRunId, objective, currentProject.id);

      const userMessage: Message = {
        id: `user-${Date.now()}`,
        type: "user",
        content: objective,
        timestamp: Date.now(),
        projectId: currentProject.id,
        runId: newRunId,
      };

      const agentMessage: Message = {
        id: `agent-${Date.now()}`,
        type: "agent",
        content: "Processing your request...",
        timestamp: Date.now(),
        runId: newRunId,
        status: "sending",
        projectId: currentProject.id,
      };

      addMessage(userMessage);
      addMessage(agentMessage);
      startRun(newRunId);

      // Start LangGraph execution
      setTimeout(() => {
        startAgentExecution({
          project_id: currentProject.id,
          objective,
          token,
        });
      }, 500);
    } catch (error) {
      console.error('Authentication error:', error);
      toast.error('Authentication failed. Please login again.');
    }
  };

  const getStatusBadge = () => {
    if (runId && !isLangGraphComplete) {
      return (
        <Badge variant="secondary" className="animate-pulse">
          Running
        </Badge>
      );
    }
    if (isLangGraphComplete) {
      return <Badge variant="default">Complete</Badge>;
    }
    return <Badge variant="outline">Idle</Badge>;
  };

  const isRunning = () => !!(runId && !isLangGraphComplete);

  const [isMobile, setIsMobile] = useState(false);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
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
            <ProfileMenu />
          </div>
        </header>

        {/* Mobile Tabs - 3 tabs for new layout */}
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="flex-1 flex flex-col"
        >
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
                  onSendMessage={handleSend}
                  isLoading={isRunning()}
                  projectId={currentProject?.id}
                />
              </div>
              {/* Backlog below */}
              <div className="flex-1">
                <BacklogPanel />
              </div>
            </TabsContent>

            <TabsContent value="history" className="flex-1 m-0">
              <div className="p-2 flex flex-col gap-2">
                <AgentActionsPanel 
                  actions={agentActions}
                  isComplete={isLangGraphComplete}
                  currentStatus={langGraphStatus}
                  progress={langGraphProgress}
                />
                <ConversationHistory projectId={currentProject?.id} />
              </div>
            </TabsContent>
          </div>
        </Tabs>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Desktop Header */}
      <header className="border-b p-4">
        <div className="container max-w-7xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-2xl font-bold">{APP_CONFIG.name}</h1>
            {getStatusBadge()}
          </div>
          <ProfileMenu />
        </div>
      </header>

      {/* Desktop 3-Panel Layout */}
      <div className="flex flex-1 overflow-hidden">
        <div className="w-1/4 border-r">
          <ProjectPanel />
        </div>

        <div className="w-1/2 border-r flex flex-col">
          <ChatComposer
            onSendMessage={handleSend}
            isLoading={isRunning()}
            projectId={currentProject?.id}
          />
          <BacklogPanel />
        </div>

        <div className="w-1/4 p-2 flex flex-col gap-2 overflow-y-auto">
          <AgentActionsPanel 
            actions={agentActions}
            isComplete={isLangGraphComplete}
            currentStatus={langGraphStatus}
            progress={langGraphProgress}
          />
          <ConversationHistory projectId={currentProject?.id} />
        </div>
      </div>
    </div>
  );
}
