"use client";

import { useState } from 'react';
import { 
  ChevronLeft, 
  ChevronRight, 
  Plus, 
  Edit, 
  Trash2, 
  Folder,
  Settings
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { 
  Select, 
  SelectContent, 
  SelectItem, 
  SelectTrigger, 
  SelectValue 
} from '@/components/ui/select';
import { useProjects } from '@/context/ProjectContext';

interface ProjectPanelProps {
  className?: string;
}

export function ProjectPanel({ className }: ProjectPanelProps) {
  const [isCollapsed, setIsCollapsed] = useState(false);
  const { 
    projects, 
    currentProject, 
    setCurrentProject, 
    isLoading,
    createProject,
    updateProject,
    deleteProject
  } = useProjects();

  const toggleCollapse = () => {
    setIsCollapsed(!isCollapsed);
  };

  const handleProjectChange = (projectId: string) => {
    const project = projects.find(p => p.id.toString() === projectId);
    if (project) {
      setCurrentProject(project);
    }
  };

  const handleCreateProject = async () => {
    const name = prompt('Nom du nouveau projet:');
    if (name?.trim()) {
      const description = prompt('Description (optionnelle):') || undefined;
      await createProject(name.trim(), description);
    }
  };

  const handleEditProject = async () => {
    if (!currentProject) return;
    
    const name = prompt('Nouveau nom:', currentProject.name);
    if (name?.trim()) {
      const description = prompt('Description:', currentProject.description || '') || undefined;
      await updateProject(currentProject.id, name.trim(), description);
    }
  };

  const handleDeleteProject = async () => {
    if (!currentProject) return;
    
    const confirmed = confirm(`Êtes-vous sûr de vouloir supprimer le projet "${currentProject.name}" ?`);
    if (confirmed) {
      await deleteProject(currentProject.id);
    }
  };

  return (
    <div className={`
      bg-background border-r border-border transition-all duration-300 ease-in-out
      ${isCollapsed ? 'w-12' : 'w-80'}
      ${className}
    `}>
      {/* Header avec bouton de collapse */}
      <div className="flex items-center justify-between p-4 border-b border-border">
        <div className="flex items-center gap-2">
          {!isCollapsed && (
            <>
              <Folder className="size-5 text-muted-foreground" />
              <h2 className="text-sm font-semibold">Projets</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={handleCreateProject}
                disabled={isLoading}
                className="size-6"
              >
                <Plus className="size-4" />
              </Button>
            </>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={toggleCollapse}
          className="size-6"
        >
          {isCollapsed ? (
            <ChevronRight className="size-4" />
          ) : (
            <ChevronLeft className="size-4" />
          )}
        </Button>
      </div>

      {/* Contenu du panel (caché si collapsed) */}
      {!isCollapsed && (
        <div className="p-4 space-y-4">
          {/* Sélecteur de projet */}
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground font-medium">
              Projet actuel
            </label>
            <Select
              value={currentProject?.id.toString() || ''}
              onValueChange={handleProjectChange}
              disabled={isLoading}
            >
              <SelectTrigger className="w-full">
                <SelectValue 
                  placeholder={isLoading ? "Chargement..." : "Sélectionner un projet"} 
                />
              </SelectTrigger>
              <SelectContent>
                {projects.map((project) => (
                  <SelectItem key={project.id} value={project.id.toString()}>
                    <div className="flex items-center gap-2">
                      <Folder className="size-4 text-muted-foreground" />
                      <span>{project.name}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Actions sur les projets */}
          <div className="space-y-2">
            <label className="text-xs text-muted-foreground font-medium">
              Actions
            </label>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={handleEditProject}
                disabled={!currentProject || isLoading}
                className="flex-1"
              >
                <Edit className="size-4" />
                Modifier
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={handleDeleteProject}
                disabled={!currentProject || isLoading || projects.length <= 1}
                className="flex-1"
              >
                <Trash2 className="size-4" />
                Supprimer
              </Button>
            </div>
          </div>

          {/* Informations du projet actuel */}
          {currentProject && (
            <div className="space-y-2 pt-4 border-t border-border">
              <label className="text-xs text-muted-foreground font-medium">
                Détails du projet
              </label>
              <div className="bg-muted/50 rounded-md p-3 space-y-2">
                <div>
                  <div className="text-xs text-muted-foreground">Nom</div>
                  <div className="text-sm font-medium">{currentProject.name}</div>
                </div>
                {currentProject.description && (
                  <div>
                    <div className="text-xs text-muted-foreground">Description</div>
                    <div className="text-sm">{currentProject.description}</div>
                  </div>
                )}
                <div>
                  <div className="text-xs text-muted-foreground">ID</div>
                  <div className="text-sm font-mono">{currentProject.id}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Indicateur collapsed */}
      {isCollapsed && (
        <div className="p-2">
          <Button
            variant="ghost"
            size="icon"
            className="w-full"
            onClick={toggleCollapse}
          >
            <Settings className="size-4 text-muted-foreground" />
          </Button>
        </div>
      )}
    </div>
  );
}