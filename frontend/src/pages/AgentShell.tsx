"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useProjects } from "@/context/ProjectContext";
import { useRunsStore } from "@/stores/useRunsStore";
import { useBacklog } from "@/context/BacklogContext";
import { mutate } from "swr";
import { useAgentStream } from "@/hooks/useAgentStream";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { BacklogPanel } from "@/components/backlog/BacklogPanel";
import { ProjectPanel } from "@/components/project/ProjectPanel";
import { ConversationHistory } from "@/components/agent/ConversationHistory";
import { useMessagesStore, type Message } from "@/stores/useMessagesStore";
import { toast } from "sonner";
import { APP_CONFIG } from "@/lib/constants";

export function AgentShell() {
  const [highlightItemId, setHighlightItemId] = useState<number>();
  const [activeTab, setActiveTab] = useState("backlog");
  const [isHydrated, setIsHydrated] = useState(false);
  const [pendingObjective, setPendingObjective] = useState<string>();

  const { currentProject } = useProjects();
  const { refreshItems } = useBacklog();
  const { currentRunId, startRun, isRunning, getCurrentRun } = useRunsStore();
  const {
    messages,
    addMessage,
    replaceRunId,
    updateMessage,
    getMessagesForProject,
  } = useMessagesStore();

  useEffect(() => {
    const rehydrateStores = async () => {
      await useRunsStore.persist.rehydrate();
      await useMessagesStore.persist.rehydrate();
      setIsHydrated(true);
    };
    rehydrateStores();
  }, []);

  const currentMessages = isHydrated
    ? getMessagesForProject(currentProject?.id)
    : [];

  useAgentStream(currentRunId, {
    objective: pendingObjective,
    projectId: currentProject?.id,
    onRunIdUpdate: (tempRunId: string, realRunId: string) => {
      replaceRunId(tempRunId, realRunId);
    },
    onFinish: async (summary) => {
      const { messages: allMessages, updateMessage: updateMsg } =
        useMessagesStore.getState();
      const agentMessage = allMessages.find(
        (msg) =>
          msg.type === "agent" &&
          msg.projectId === currentProject?.id &&
          msg.status === "sending",
      );
      if (agentMessage) {
        updateMsg(agentMessage.id, { content: summary, status: "completed" });
      }
      setPendingObjective(undefined);
      if (currentProject) {
        await refreshItems();
        await mutate(`/items?project_id=${currentProject.id}`);
      }
    },
    onError: (error) => {
      const { messages: allMessages, updateMessage: updateMsg } =
        useMessagesStore.getState();
      const agentMessage = allMessages.find(
        (msg) =>
          msg.type === "agent" &&
          msg.projectId === currentProject?.id &&
          msg.status === "sending",
      );
      if (agentMessage) {
        updateMsg(agentMessage.id, {
          content: `Error: ${error}`,
          status: "failed",
        });
      }
      setPendingObjective(undefined);
    },
  });

  const handleSend = async (objective: string) => {
    if (!currentProject) {
      toast.error("Please select a project first");
      return;
    }

    const tempRunId = crypto.randomUUID();

    const userMessage: Message = {
      id: `user-${Date.now()}`,
      type: "user",
      content: objective,
      timestamp: Date.now(),
      projectId: currentProject.id,
      runId: tempRunId,
    };

    const agentMessage: Message = {
      id: `agent-${Date.now()}`,
      type: "agent",
      content: "Processing your request...",
      timestamp: Date.now(),
      runId: tempRunId,
      status: "sending",
      projectId: currentProject.id,
    };

    addMessage(userMessage);
    addMessage(agentMessage);

    setPendingObjective(objective);
    startRun(tempRunId);
  };

  const getStatusBadge = () => {
    const currentRun = getCurrentRun();
    if (currentRun?.status === "running") {
      return (
        <Badge variant="secondary" className="animate-pulse">
          Running
        </Badge>
      );
    }
    return <Badge variant="outline">Idle</Badge>;
  };

  const handleItemHighlight = (itemId: number) => {
    setHighlightItemId(itemId);
    setTimeout(() => setHighlightItemId(undefined), 2000);
  };

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
          <BacklogPanel
            highlightItemId={highlightItemId}
            onItemClick={handleItemHighlight}
          />
        </div>

        <div className="w-1/4">
          <ConversationHistory
            messages={currentMessages}
            onItemHighlight={handleItemHighlight}
          />
        </div>
      </div>
    </div>
  );
}
