"use client";

import { useState, useEffect } from "react";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useProjects } from "@/context/ProjectContext";
import { useRunsStore } from "@/stores/useRunsStore";
import { useBacklog } from "@/context/BacklogContext";
import { useLangGraphStream } from "@/hooks/useLangGraphStream";
import { auth } from "@/lib/firebase";
import { ChatComposer } from "@/components/chat/ChatComposer";
import { BacklogPanel } from "@/components/backlog/BacklogPanel";
import { ProjectPanel } from "@/components/project/ProjectPanel";
import { AgentActionsPanel } from "@/components/AgentActionsPanel";
import { ProjectHistory } from "@/components/project/ProjectHistory";
import { useMessagesStore, type Message } from "@/stores/useMessagesStore";
import { useHistory } from "@/store/useHistory";
import { toast } from "sonner";
import { APP_CONFIG } from "@/lib/constants";
import { safeId } from "@/lib/safeId";
import { ProfileMenu } from "@/components/ProfileMenu";
import type { AgentRunPayload } from "@/lib/api";
import { apiFetch } from "@/lib/api";

interface PendingApproval {
  run_id: string;
  step_index: number;
  agent: string;
  objective: string;
  created_at: string;
  timeout_at: string;
  context?: unknown;
}

export default AgentShell;

// Disable SSR for this page since it requires client-side context providers
export async function getServerSideProps() {
  return { props: {} };
}

export function AgentShell() {
  const [activeTab, setActiveTab] = useState("backlog");
  const [isHydrated, setIsHydrated] = useState(false);
  const [runId, setRunId] = useState<string | null>(null);
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null);

  const { currentProject } = useProjects();
  const { refreshItems, addItemRealtime, addPlaceholder, removePlaceholder } = useBacklog();
  const { startRun, isRunning: isOldRunning, getCurrentRun } = useRunsStore();
  const { addMessage, updateMessage } = useMessagesStore();
  
  // Multi-agent streaming with real-time item creation
  const {
    agentActions,
    isComplete: isLangGraphComplete,
    currentStatus: langGraphStatus,
    progress: langGraphProgress,
    startAgentExecution,
  } = useLangGraphStream(
    runId,
    // onItemCreated callback
    (item) => {
      console.log('[AgentShell] Item created, adding to backlog:', item);
      addItemRealtime(item as any); // Type assertion needed
    },
    // onItemCreating callback
    (data) => {
      console.log('[AgentShell] Item creating, adding placeholder:', data);
      if (data.temp_id && data.title) {
        addPlaceholder({
          id: data.temp_id as string,
          title: data.title as string,
          type: data.item_type as string,
          project_id: currentProject?.id || 0,
          parent_id: (data.parent_id as number) || null,
          description: 'Creating...',
          ia_review_status: 'pending',
          isLoading: true
        } as any);
      }
    }
  );

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
    console.log('[AgentShell] Completion check:', { isLangGraphComplete, runId, projectId: currentProject?.id });
    if (isLangGraphComplete && runId && currentProject) {
      console.log('[AgentShell] Refreshing backlog items...');
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
      
      // Refresh immediately and again after 2 seconds to ensure backend changes are reflected
      refreshItems();
      setTimeout(() => refreshItems(), 2000);
      console.log('[AgentShell] Backlog refresh triggered');
    }
  }, [isLangGraphComplete, runId, currentProject, agentActions, refreshItems, updateMessage]);

  // Reset runId when switching projects to avoid showing actions from other projects
  useEffect(() => {
    if (currentProject) {
      setRunId(null);
    }
  }, [currentProject?.id]);

  // Check for pending approvals
  useEffect(() => {
    if (!runId || isLangGraphComplete) return;
    
    const checkApprovals = async () => {
      try {
        const response = await apiFetch(`/approvals/${runId}`);
        if (!response.ok) return;
        
        const data = await response.json();
        console.log('[AgentShell] Approval check:', data);
        
        if (data.pending_approvals && data.pending_approvals.length > 0) {
          console.log('[AgentShell] Setting pending approval:', data.pending_approvals[0]);
          setPendingApproval(data.pending_approvals[0]);
        } else {
          console.log('[AgentShell] No pending approvals');
          setPendingApproval(null);
        }
      } catch (error) {
        console.error('Failed to check approvals:', error);
      }
    };
    
    // Check immediately and then every 2 seconds
    checkApprovals();
    const interval = setInterval(checkApprovals, 2000);
    return () => clearInterval(interval);
  }, [runId, isLangGraphComplete]);

  const handleApprovalDecision = async (decision: 'approve' | 'reject' | 'modify', reason: string) => {
    console.log(`Decision: ${decision}, Reason: ${reason}`);
    setPendingApproval(null);
  };

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
          meta,
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
              <ProjectPanel onAnalyzeDocument={(objective) => handleSend(objective)} />
            </TabsContent>

            <TabsContent value="backlog" className="flex-1 flex flex-col m-0">
              {/* User Input on top */}
              <div className="border-b">
                <ChatComposer
                  onSendMessage={handleSend}
                  isLoading={isRunning()}
                  projectId={currentProject?.id}
                  pendingApproval={pendingApproval}
                  onApprovalDecision={handleApprovalDecision}
                />
              </div>
              {/* Backlog below */}
              <div className="flex-1">
                <BacklogPanel />
              </div>
            </TabsContent>

            <TabsContent value="history" className="flex-1 m-0">
              <Tabs defaultValue="actions" className="flex-1 flex flex-col">
                <TabsList className="grid w-full grid-cols-2">
                  <TabsTrigger value="actions">Agent Actions</TabsTrigger>
                  <TabsTrigger value="execution">Execution History</TabsTrigger>
                </TabsList>
                
                <TabsContent value="actions" className="flex-1 overflow-y-auto p-2 m-0">
                  <AgentActionsPanel 
                    actions={agentActions}
                    isComplete={isLangGraphComplete}
                    currentStatus={langGraphStatus}
                    progress={langGraphProgress}
                  />
                </TabsContent>
                
                <TabsContent value="execution" className="flex-1 overflow-y-auto p-2 m-0">
                  {currentProject && (
                    <ProjectHistory projectId={currentProject.id} />
                  )}
                </TabsContent>
              </Tabs>
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
          <ProjectPanel onAnalyzeDocument={(objective) => handleSend(objective)} />
        </div>

        <div className="w-1/2 border-r flex flex-col">
          <ChatComposer
            onSendMessage={handleSend}
            isLoading={isRunning()}
            projectId={currentProject?.id}
            pendingApproval={pendingApproval}
            onApprovalDecision={handleApprovalDecision}
          />
          <BacklogPanel />
        </div>

        <div className="w-1/4 overflow-hidden flex flex-col">
          <Tabs defaultValue="actions" className="flex-1 flex flex-col">
            <TabsList className="grid w-full grid-cols-2 rounded-none">
              <TabsTrigger value="actions">Agent Actions</TabsTrigger>
              <TabsTrigger value="history">Execution History</TabsTrigger>
            </TabsList>
            
            <TabsContent value="actions" className="flex-1 overflow-y-auto p-2 m-0">
              <AgentActionsPanel 
                actions={agentActions}
                isComplete={isLangGraphComplete}
                currentStatus={langGraphStatus}
                progress={langGraphProgress}
              />
            </TabsContent>
            
            <TabsContent value="history" className="flex-1 overflow-y-auto p-2 m-0">
              {currentProject && (
                <ProjectHistory projectId={currentProject.id} />
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
}
