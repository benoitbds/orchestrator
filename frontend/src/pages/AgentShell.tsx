"use client";

import { useState, useEffect } from 'react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { useProjects } from '@/context/ProjectContext';
import { useRunsStore } from '@/stores/useRunsStore';
import { useBacklog } from '@/context/BacklogContext';
import { mutate } from 'swr';
import { cn } from '@/lib/utils';
import { BacklogPanel } from '@/components/backlog/BacklogPanel';
import { AgentArea } from '@/components/agent/AgentArea';

interface Message {
  id: string;
  type: 'user' | 'agent';
  content: string;
  timestamp: number;
  runId?: string;
  status?: 'sending' | 'completed' | 'failed';
}

export function AgentShell() {
  const [highlightItemId, setHighlightItemId] = useState<number>();
  const [activeTab, setActiveTab] = useState("backlog");

  const { projects, currentProject, setCurrentProject } = useProjects();
  const { refreshItems } = useBacklog();
  const { getCurrentRun } = useRunsStore();

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

        {/* Mobile Tabs - Only 2 tabs now */}
        <Tabs value={activeTab} onValueChange={setActiveTab} className="flex-1 flex flex-col">
          <TabsList className="grid w-full grid-cols-2 rounded-none">
            <TabsTrigger value="backlog">Backlog</TabsTrigger>
            <TabsTrigger value="agent">Agent</TabsTrigger>
          </TabsList>

          <div className="flex-1 flex flex-col overflow-hidden">
            <TabsContent value="backlog" className="flex-1 m-0">
              <BacklogPanel 
                highlightItemId={highlightItemId}
                onItemClick={setHighlightItemId}
              />
            </TabsContent>

            <TabsContent value="agent" className="flex-1 flex flex-col m-0">
              <AgentArea 
                onItemHighlight={handleItemHighlight}
                onBacklogRefresh={refreshItems}
                currentProject={currentProject}
              />
            </TabsContent>
          </div>
        </Tabs>
      </div>
    );
  }

  // Desktop 2-Pane Layout
  return (
    <div className="flex flex-col h-screen bg-background">
      {/* Desktop Header - Remove ASCII, keep minimal */}
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

      {/* Desktop 2-Pane Layout */}
      <div className="flex-1 grid grid-cols-12 gap-4 p-4 container max-w-7xl mx-auto overflow-hidden">
        {/* Left Panel - Backlog (unchanged) */}
        <div className="col-span-4 md:col-span-12 border rounded-2xl overflow-hidden shadow-sm">
          <BacklogPanel 
            highlightItemId={highlightItemId}
            onItemClick={setHighlightItemId}
          />
        </div>

        {/* Right Panel - Agent Area (Chat + Log merged) */}
        <div className="col-span-8 md:col-span-12 border rounded-2xl overflow-hidden shadow-sm">
          <AgentArea 
            onItemHighlight={handleItemHighlight}
            onBacklogRefresh={refreshItems}
            currentProject={currentProject}
          />
        </div>
      </div>
    </div>
  );
}