"use client";
import { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { Project } from '@/models/project'; // Nous créerons ce modèle
import { apiFetch } from '@/lib/api';

interface ProjectContextType {
  projects: Project[];
  currentProject: Project | null;
  setCurrentProject: (project: Project | null) => void;
  isLoading: boolean;
  createProject: (name: string, description?: string) => Promise<Project | null>;
  updateProject: (id: number, name: string, description?: string) => Promise<Project | null>;
  deleteProject: (id: number) => Promise<boolean>;
  refreshProjects: () => Promise<void>;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export const ProjectProvider = ({ children }: { children: ReactNode }) => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [currentProject, setCurrentProject] = useState<Project | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const fetchProjects = async () => {
    setIsLoading(true);
    try {
      const response = await apiFetch(`/projects`);
      const data = await response.json();
      setProjects(data);
      if (data.length > 0 && !currentProject) {
        setCurrentProject(data[0]); // Sélectionner le premier par défaut si aucun n'est sélectionné
      } else if (data.length === 0) {
        setCurrentProject(null);
      }
    } catch (error) {
      console.error("Failed to fetch projects:", error);
    } finally {
      setIsLoading(false);
    }
  };

  const createProject = async (name: string, description?: string) => {
    try {
      const response = await apiFetch(`/projects`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description }),
      });
      if (!response.ok) throw new Error('Failed to create project');
      const newProject = await response.json();
      await fetchProjects(); // Refresh projects list
      setCurrentProject(newProject); // Select the newly created project
      return newProject;
    } catch (error) {
      console.error("Error creating project:", error);
      return null;
    }
  };

  const updateProject = async (id: number, name: string, description?: string) => {
    try {
      const response = await apiFetch(`/projects/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, description }),
      });
      if (!response.ok) throw new Error('Failed to update project');
      const updatedProject = await response.json();
      await fetchProjects(); // Refresh projects list
      if (currentProject?.id === id) {
        setCurrentProject(updatedProject); // Update current project if it was the one updated
      }
      return updatedProject;
    } catch (error) {
      console.error("Error updating project:", error);
      return null;
    }
  };

  const deleteProject = async (id: number) => {
    try {
      const response = await apiFetch(`/projects/${id}`, {
        method: 'DELETE',
      });
      if (!response.ok) throw new Error('Failed to delete project');
      await fetchProjects(); // Refresh projects list
      if (currentProject?.id === id) {
        setCurrentProject(projects.length > 0 ? projects[0] : null); // Select first project or null
      }
      return true;
    } catch (error) {
      console.error("Error deleting project:", error);
      return false;
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const refreshProjects = fetchProjects; // Alias for clarity

  return (
    <ProjectContext.Provider value={{
      projects,
      currentProject,
      setCurrentProject,
      isLoading,
      createProject,
      updateProject,
      deleteProject,
      refreshProjects
    }}>
      {children}
    </ProjectContext.Provider>
  );
};

export const useProjects = () => {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error('useProjects must be used within a ProjectProvider');
  }
  return context;
};
