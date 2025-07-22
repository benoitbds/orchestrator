"use client";
import { useProjects } from "@/context/ProjectContext";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useState, useEffect } from "react";

export default function ProjectSelector() {
  const {
    projects,
    currentProject,
    setCurrentProject,
    isLoading,
    createProject,
    updateProject,
    deleteProject,
  } = useProjects();

  const [isCreateDialogOpen, setIsCreateDialogOpen] = useState(false);
  const [isEditDialogOpen, setIsEditDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [newProjectName, setNewProjectName] = useState("");
  const [newProjectDescription, setNewProjectDescription] = useState("");
  const [editProjectName, setEditProjectName] = useState("");
  const [editProjectDescription, setEditProjectDescription] = useState("");

  useEffect(() => {
    if (isEditDialogOpen && currentProject) {
      setEditProjectName(currentProject.name);
      setEditProjectDescription(currentProject.description || "");
    }
  }, [isEditDialogOpen, currentProject]);

  const handleSelect = (projectId: string) => {
    const selected = projects.find((p) => p.id.toString() === projectId);
    setCurrentProject(selected || null);
  };

  const handleCreateProject = async () => {
    await createProject(newProjectName, newProjectDescription);
    setNewProjectName("");
    setNewProjectDescription("");
    setIsCreateDialogOpen(false);
  };

  const handleUpdateProject = async () => {
    if (currentProject) {
      await updateProject(
        currentProject.id,
        editProjectName,
        editProjectDescription
      );
      setIsEditDialogOpen(false);
    }
  };

  const handleDeleteProject = async () => {
    if (currentProject) {
      await deleteProject(currentProject.id);
      setIsDeleteDialogOpen(false);
    }
  };

  if (isLoading) {
    return <div>Chargement des projets...</div>;
  }

  return (
    <div className="p-4 space-y-4">
      <h2 className="text-lg font-semibold">Gestion des Projets</h2>
      
      {/* Sélecteur de projet */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-600">Projet actuel</label>
        <Select
          onValueChange={handleSelect}
          value={currentProject?.id.toString()}
          disabled={projects.length === 0}
        >
          <SelectTrigger className="w-full">
            <SelectValue placeholder="Sélectionner un projet" />
          </SelectTrigger>
          <SelectContent>
            {projects.map((project) => (
              <SelectItem key={project.id} value={project.id.toString()}>
                <div className="flex flex-col items-start">
                  <span className="font-medium">{project.name}</span>
                  {project.description && (
                    <span className="text-xs text-gray-500 truncate max-w-[200px]">
                      {project.description}
                    </span>
                  )}
                </div>
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Boutons d'actions */}
      <div className="space-y-2">
        <label className="text-sm font-medium text-gray-600">Actions</label>
        <div className="grid grid-cols-1 gap-2">
          <Button 
            onClick={() => setIsCreateDialogOpen(true)} 
            size="sm"
            className="w-full justify-start"
          >
            <span className="mr-2">+</span>
            Nouveau projet
          </Button>
          <Button
            onClick={() => setIsEditDialogOpen(true)}
            size="sm"
            variant="outline"
            disabled={!currentProject}
            className="w-full justify-start"
          >
            <span className="mr-2">✏️</span>
            Modifier le projet
          </Button>
          <Button
            onClick={() => setIsDeleteDialogOpen(true)}
            size="sm"
            variant="destructive"
            disabled={!currentProject}
            className="w-full justify-start"
          >
            <span className="mr-2">🗑️</span>
            Supprimer le projet
          </Button>
        </div>
      </div>

      {/* Informations du projet actuel */}
      {currentProject && (
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-600">Projet sélectionné</label>
          <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
            <h4 className="font-medium text-blue-900">{currentProject.name}</h4>
            {currentProject.description && (
              <p className="text-sm text-blue-700 mt-1">{currentProject.description}</p>
            )}
            <p className="text-xs text-blue-600 mt-2">ID: {currentProject.id}</p>
          </div>
        </div>
      )}

      {/* Create Project Dialog */}
      <Dialog open={isCreateDialogOpen} onOpenChange={setIsCreateDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Créer un nouveau projet</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <Input
              placeholder="Nom du projet"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
            />
            <Input
              placeholder="Description (optionnel)"
              value={newProjectDescription}
              onChange={(e) => setNewProjectDescription(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button onClick={handleCreateProject}>Créer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Edit Project Dialog */}
      <Dialog open={isEditDialogOpen} onOpenChange={setIsEditDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Modifier le projet</DialogTitle>
          </DialogHeader>
          <div className="grid gap-4 py-4">
            <Input
              placeholder="Nom du projet"
              value={editProjectName}
              onChange={(e) => setEditProjectName(e.target.value)}
            />
            <Input
              placeholder="Description (optionnel)"
              value={editProjectDescription}
              onChange={(e) => setEditProjectDescription(e.target.value)}
            />
          </div>
          <DialogFooter>
            <Button onClick={handleUpdateProject}>Enregistrer</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Delete Project Dialog */}
      <Dialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Supprimer le projet</DialogTitle>
          </DialogHeader>
          <div className="py-4">
            Êtes-vous sûr de vouloir supprimer le projet "
            {currentProject?.name}" ? Cette action est irréversible.
          </div>
          <DialogFooter>
            <Button variant="destructive" onClick={handleDeleteProject}>
              Supprimer
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
