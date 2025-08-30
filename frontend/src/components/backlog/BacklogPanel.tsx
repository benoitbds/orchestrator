"use client";

import { useEffect, useRef } from 'react';
import { useProjects } from '@/context/ProjectContext';
import BacklogPane from '@/components/BacklogPane';
import { cn } from '@/lib/utils';

interface BacklogPanelProps {
  className?: string;
  highlightItemId?: number;
  onItemClick?: (itemId: number) => void;
}

export function BacklogPanel({ className, highlightItemId, onItemClick }: BacklogPanelProps) {
  const { currentProject } = useProjects();
  const panelRef = useRef<HTMLDivElement>(null);

  // Scroll to highlighted item
  useEffect(() => {
    if (highlightItemId && panelRef.current) {
      const itemElement = panelRef.current.querySelector(`[data-item-id="${highlightItemId}"]`);
      if (itemElement) {
        itemElement.scrollIntoView({ 
          behavior: 'smooth', 
          block: 'center' 
        });
        
        // Add temporary highlight effect
        itemElement.classList.add('ring-2', 'ring-primary', 'ring-offset-2');
        setTimeout(() => {
          itemElement.classList.remove('ring-2', 'ring-primary', 'ring-offset-2');
        }, 2000);
      }
    }
  }, [highlightItemId]);

  if (!currentProject) {
    return (
      <div className={cn("flex items-center justify-center p-8 text-center", className)}>
        <div className="text-muted-foreground">
          <h3 className="font-medium mb-2">No Project Selected</h3>
          <p className="text-sm">
            Select a project to view and manage your backlog items.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div ref={panelRef} className={cn("flex flex-col h-full", className)}>
      <div className="p-4 border-b">
        <h2 className="font-semibold">Backlog</h2>
        <p className="text-sm text-muted-foreground mt-1">
          {currentProject.name}
        </p>
      </div>
      
      <div className="flex-1 overflow-hidden">
        <BacklogPane />
      </div>
    </div>
  );
}