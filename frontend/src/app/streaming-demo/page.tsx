'use client';

import React, { useState, useEffect } from 'react';
import { Badge } from '@/components/ui/badge';
import { AgentActionsPanel } from '@/components/AgentActionsPanel';
import { ApprovalModal } from '@/components/ApprovalModal';
import { BacklogPanel } from '@/components/backlog/BacklogPanel';
import { ProjectPanel } from '@/components/project/ProjectPanel';
import { ChatComposer } from '@/components/chat/ChatComposer';
import { useLangGraphStream } from '@/hooks/useLangGraphStream';
import { useAuth } from '@/context/AuthContext';
import { useProjects } from '@/context/ProjectContext';
import { BacklogProvider } from '@/context/BacklogContext';
import { auth } from '@/lib/firebase';
import { APP_CONFIG } from '@/lib/constants';
import { ProfileMenu } from '@/components/ProfileMenu';
import { toast } from 'sonner';
import { Toaster } from 'sonner';

interface PendingApproval {
  run_id: string;
  step_index: number;
  agent: string;
  objective: string;
  created_at: string;
  timeout_at: string;
  context?: unknown;
}

export default function StreamingDemoPage() {
  const { user } = useAuth();
  const { currentProject } = useProjects();
  const [runId, setRunId] = useState<string | null>(null);
  const [isStarted, setIsStarted] = useState(false);
  const [pendingApproval, setPendingApproval] = useState<PendingApproval | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  const {
    agentActions,
    isComplete,
    error,
    currentStatus,
    progress,
    isConnected,
    startAgentExecution
  } = useLangGraphStream(runId);

  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768);
    };

    checkMobile();
    window.addEventListener("resize", checkMobile);
    return () => window.removeEventListener("resize", checkMobile);
  }, []);

  const handleSend = async (objective: string) => {
    if (!currentProject) {
      toast.error("Please select a project first");
      return;
    }

    if (!user) {
      toast.error('Please login first');
      return;
    }

    try {
      const token = await auth.currentUser?.getIdToken();
      if (!token) {
        toast.error('Failed to get authentication token');
        return;
      }

      const newRunId = `demo-${Date.now()}`;
      setRunId(newRunId);
      setIsStarted(true);
      
      setTimeout(() => {
        startAgentExecution({
          project_id: currentProject.id,
          objective,
          token
        });
      }, 500);
    } catch (error) {
      console.error('Authentication error:', error);
      toast.error('Authentication failed. Please login again.');
    }
  };

  useEffect(() => {
    if (!runId || isComplete || !user) return;
    
    const checkApprovals = async () => {
      try {
        const token = await auth.currentUser?.getIdToken();
        if (!token) return;

        const response = await fetch(`/api/approvals/${runId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        const data = await response.json();
        
        if (data.pending_approvals && data.pending_approvals.length > 0) {
          setPendingApproval(data.pending_approvals[0]);
        } else {
          setPendingApproval(null);
        }
      } catch (error) {
        console.error('Failed to check approvals:', error);
      }
    };
    
    const interval = setInterval(checkApprovals, 2000);
    return () => clearInterval(interval);
  }, [runId, isComplete, user]);

  const handleApprovalDecision = (decision: 'approve' | 'reject' | 'modify', reason: string) => {
    console.log(`Decision: ${decision}, Reason: ${reason}`);
    setPendingApproval(null);
  };

  const getStatusBadge = () => {
    if (isStarted && !isComplete) {
      return (
        <Badge variant="secondary" className="animate-pulse">
          Running
        </Badge>
      );
    }
    if (isComplete) {
      return <Badge variant="default">Complete</Badge>;
    }
    return <Badge variant="outline">Idle</Badge>;
  };

  const isRunning = () => isStarted && !isComplete;

  if (!user) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center p-6">
        <div className="max-w-md mx-auto text-center bg-white rounded-lg shadow-sm border p-8">
          <h1 className="text-2xl font-bold mb-4">Authentication Required</h1>
          <p className="text-gray-600 mb-6">
            Please login to access the streaming demo.
          </p>
          <a 
            href="/login" 
            className="inline-block bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700"
          >
            Go to Login
          </a>
        </div>
      </div>
    );
  }

  if (isMobile) {
    return (
      <BacklogProvider>
        <div className="flex flex-col h-screen bg-background">
          <header className="border-b p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <h1 className="text-xl font-bold">{APP_CONFIG.name} - Streaming</h1>
                {getStatusBadge()}
              </div>
              <ProfileMenu />
            </div>
          </header>

          <div className="flex-1 flex flex-col overflow-hidden">
            <div className="border-b">
              <ChatComposer
                onSendMessage={handleSend}
                isLoading={isRunning()}
                projectId={currentProject?.id}
              />
            </div>
            
            <div className="flex-1 overflow-auto">
              <div className="p-2">
                {runId && (
                  <AgentActionsPanel
                    actions={agentActions}
                    isComplete={isComplete}
                    currentStatus={currentStatus}
                    progress={progress}
                  />
                )}
              </div>
            </div>
          </div>

          {pendingApproval && (
            <ApprovalModal
              runId={pendingApproval.run_id}
              stepIndex={pendingApproval.step_index}
              agent={pendingApproval.agent}
              objective={pendingApproval.objective}
              createdAt={pendingApproval.created_at}
              timeoutAt={pendingApproval.timeout_at}
              onDecision={handleApprovalDecision}
              onClose={() => setPendingApproval(null)}
            />
          )}
        </div>
        <Toaster richColors position="top-right" />
      </BacklogProvider>
    );
  }

  return (
    <BacklogProvider>
      <div className="flex flex-col h-screen bg-background">
        <header className="border-b p-4">
          <div className="container max-w-7xl mx-auto flex items-center justify-between">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold">{APP_CONFIG.name} - Streaming Demo</h1>
              {getStatusBadge()}
              {isConnected && (
                <Badge variant="outline" className="text-xs">
                  <div className="w-2 h-2 bg-green-500 rounded-full mr-1"></div>
                  Connected
                </Badge>
              )}
            </div>
            <ProfileMenu />
          </div>
        </header>

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

          <div className="w-1/4 overflow-auto">
            {runId && (
              <AgentActionsPanel
                actions={agentActions}
                isComplete={isComplete}
                currentStatus={currentStatus}
                progress={progress}
              />
            )}
            
            {!runId && (
              <div className="p-4 text-center text-muted-foreground">
                <p className="text-sm">Send a message to start agent execution</p>
              </div>
            )}

            {error && (
              <div className="m-4 p-4 bg-red-50 border border-red-200 rounded-md">
                <div className="text-red-800 text-sm">
                  <strong>Error:</strong> {error}
                </div>
              </div>
            )}
          </div>
        </div>

        {pendingApproval && (
          <ApprovalModal
            runId={pendingApproval.run_id}
            stepIndex={pendingApproval.step_index}
            agent={pendingApproval.agent}
            objective={pendingApproval.objective}
            createdAt={pendingApproval.created_at}
            timeoutAt={pendingApproval.timeout_at}
            onDecision={handleApprovalDecision}
            onClose={() => setPendingApproval(null)}
          />
        )}
      </div>
      <Toaster richColors position="top-right" />
    </BacklogProvider>
  );
}
