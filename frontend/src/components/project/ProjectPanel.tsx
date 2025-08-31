"use client";

import { useState } from 'react';
import { Plus, Folder, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { useProjects } from '@/context/ProjectContext';
import { toast } from 'sonner';
import { http } from '@/lib/api';

export function ProjectPanel() {
  const { projects, currentProject, setCurrentProject, refreshProjects } = useProjects();
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [isCreating, setIsCreating] = useState(false);
  const [newProject, setNewProject] = useState({
    name: '',
    description: ''
  });

  const handleProjectChange = (projectId: string) => {
    const project = projects.find(p => p.id.toString() === projectId);
    if (project) {
      setCurrentProject(project);
    }
  };

  const handleCreateProject = async () => {
    if (!newProject.name.trim()) {
      toast.error('Project name is required');
      return;
    }

    setIsCreating(true);
    try {
      const response = await http('/projects', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: newProject.name.trim(),
          description: newProject.description.trim() || undefined
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to create project');
      }

      const createdProject = await response.json();
      await refreshProjects();
      setCurrentProject(createdProject);
      setNewProject({ name: '', description: '' });
      setIsCreateOpen(false);
      toast.success('Project created successfully');
    } catch (error) {
      toast.error(error instanceof Error ? error.message : 'Failed to create project');
    } finally {
      setIsCreating(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="p-4 border-b">
        <div className="flex items-center justify-between mb-3">
          <h2 className="font-semibold flex items-center gap-2">
            <Folder className="h-4 w-4" />
            Projects
          </h2>
          <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" size="sm">
                <Plus className="h-4 w-4" />
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create New Project</DialogTitle>
              </DialogHeader>
              <div className="space-y-4">
                <div>
                  <div className="text-sm font-medium mb-2">Name</div>
                  <Input
                    value={newProject.name}
                    onChange={(e) => setNewProject(prev => ({ ...prev, name: e.target.value }))}
                    placeholder="Enter project name"
                  />
                </div>
                <div>
                  <div className="text-sm font-medium mb-2">Description (optional)</div>
                  <Textarea
                    value={newProject.description}
                    onChange={(e) => setNewProject(prev => ({ ...prev, description: e.target.value }))}
                    placeholder="Enter project description"
                    rows={3}
                  />
                </div>
                <div className="flex justify-end gap-2">
                  <Button variant="outline" onClick={() => setIsCreateOpen(false)}>
                    Cancel
                  </Button>
                  <Button onClick={handleCreateProject} disabled={isCreating}>
                    {isCreating ? 'Creating...' : 'Create'}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
        </div>

        {/* Project Selector */}
        <Select
          value={currentProject?.id.toString() || ''}
          onValueChange={handleProjectChange}
        >
          <SelectTrigger>
            <SelectValue placeholder="Select a project" />
          </SelectTrigger>
          <SelectContent>
            {projects.map((project) => (
              <SelectItem key={project.id} value={project.id.toString()}>
                <div>
                  <div className="font-medium">{project.name}</div>
                  {project.description && (
                    <div className="text-xs text-muted-foreground truncate max-w-40">
                      {project.description}
                    </div>
                  )}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Current Project Details */}
      {currentProject ? (
        <Card className="m-4 p-4">
          <div className="space-y-3">
            <div className="flex items-start justify-between">
              <div>
                <h3 className="font-medium">{currentProject.name}</h3>
                {currentProject.description && (
                  <p className="text-sm text-muted-foreground mt-1">
                    {currentProject.description}
                  </p>
                )}
              </div>
              <Badge variant="secondary">
                <Info className="h-3 w-3 mr-1" />
                Active
              </Badge>
            </div>
          </div>
        </Card>
      ) : (
        <div className="flex-1 flex items-center justify-center p-4">
          <div className="text-center text-muted-foreground">
            <Folder className="h-8 w-8 mx-auto mb-2 opacity-50" />
            <p className="text-sm">Select or create a project to get started</p>
          </div>
        </div>
      )}
    </div>
  );
}