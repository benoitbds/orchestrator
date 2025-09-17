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
import ConversationHistory from "@/components/history/ConversationHistory";
import { AgentActionsPanel } from "@/components/history/AgentActionsPanel";
import { useMessagesStore, type Message } from "@/stores/useMessagesStore";
import { useHistory } from "@/store/useHistory";
import { toast } from "sonner";
import { safeId } from "@/lib/safeId";
import { ProfileMenu } from "@/components/ProfileMenu";
import { AgentIdentity } from "@/components/branding/AgentIdentity";

export function AgentShell() {
  const [activeTab, setActiveTab] = useState("backlog");
  const [isHydrated, setIsHydrated] = useState(false);
  const [pendingObjective, setPendingObjective] = useState<string>();

  const { currentProject } = useProjects();
  const { refreshItems } = useBacklog();
  const { currentRunId, startRun, isRunning, getCurrentRun } = useRunsStore();
  const { addMessage, replaceRunId, updateMessage } = useMessagesStore();

  useEffect(() => {
    const rehydrateStores = async () => {
      await useRunsStore.persist.rehydrate();
      await useMessagesStore.persist.rehydrate();
      await useHistory.persist.rehydrate();
      setIsHydrated(true);
    };
    rehydrateStores();
  }, []);

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

    const tempRunId = safeId();
    useHistory.getState().createTurn(tempRunId, objective, currentProject.id);

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
        <Badge
          variant="secondary"
          className="border-emerald-400/40 bg-emerald-500/15 text-emerald-100 shadow-[0_0_10px_rgba(34,197,94,0.35)] animate-pulse"
        >
          Running
        </Badge>
      );
    }
    return (
      <Badge
        variant="outline"
        className="border-lime-500/40 bg-slate-900/70 text-lime-200"
      >
        Idle
      </Badge>
    );
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
        <header className="relative border-b border-lime-500/30 bg-slate-950/95 p-4 text-slate-100 shadow-lg">
          <div
            aria-hidden="true"
            className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(190,242,100,0.18),_transparent_70%)]"
          />
          <div className="relative z-10 flex flex-col gap-4">
            <div className="flex items-start justify-between gap-3">
              <AgentIdentity size="mobile" className="w-full max-w-[320px]" />
              <ProfileMenu />
            </div>
            <div className="flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.4em] text-lime-100/70">
              {getStatusBadge()}
              <span className="text-lime-300/80">Status</span>
            </div>
          </div>
        </header>

        {/* Mobile Tabs - 3 tabs for new layout */}
        <Tabs
          value={activeTab}
          onValueChange={setActiveTab}
          className="flex-1 flex flex-col"
        >
          <TabsList className="grid w-full grid-cols-3 rounded-none border-b border-lime-500/20 bg-slate-950/80 text-lime-100">
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
              <div className="border-b border-border/60 bg-background/80">
                <ChatComposer
                  onSendMessage={handleSend}
                  isLoading={isRunning()}
                  projectId={currentProject?.id}
                />
              </div>
              {/* Backlog below */}
              <div className="flex-1 bg-background/60">
                <BacklogPanel />
              </div>
            </TabsContent>

            <TabsContent value="history" className="flex-1 m-0">
              <div className="flex flex-col gap-2 bg-background/70 p-2">
                <AgentActionsPanel runId={currentRunId} />
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
      <header className="relative border-b border-lime-500/30 bg-slate-950/90 py-6 text-slate-100 shadow-lg">
        <div
          aria-hidden="true"
          className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(190,242,100,0.14),_transparent_70%)]"
        />
        <div className="relative z-10">
          <div className="container mx-auto flex max-w-7xl flex-col gap-6 px-4 md:flex-row md:items-start md:justify-between">
            <div className="flex flex-col gap-4 md:max-w-3xl">
              <AgentIdentity className="w-full max-w-3xl" />
              <div className="flex flex-wrap items-center gap-3 text-xs font-semibold uppercase tracking-[0.4em] text-lime-200/80">
                {getStatusBadge()}
                <span className="text-lime-300/80">Status Monitor</span>
              </div>
            </div>
            <div className="flex justify-end md:self-start">
              <ProfileMenu />
            </div>
          </div>
        </div>
      </header>

      {/* Desktop 3-Panel Layout */}
      <div className="flex flex-1 overflow-hidden bg-background">
        <div className="w-1/4 border-r border-border/60 bg-background/80 backdrop-blur-sm">
          <ProjectPanel />
        </div>

        <div className="w-1/2 border-r border-border/60 bg-background/70 backdrop-blur-sm flex flex-col">
          <ChatComposer
            onSendMessage={handleSend}
            isLoading={isRunning()}
            projectId={currentProject?.id}
          />
          <BacklogPanel />
        </div>

        <div className="w-1/4 flex flex-col gap-3 bg-background/80 p-3 backdrop-blur-sm">
          <AgentActionsPanel runId={currentRunId} />
          <ConversationHistory projectId={currentProject?.id} />
        </div>
      </div>
    </div>
  );
}
