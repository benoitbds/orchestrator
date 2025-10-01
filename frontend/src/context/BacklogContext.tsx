"use client";
import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { BacklogItem } from '@/models/backlogItem';
import { useProjects } from '@/context/ProjectContext';
import { apiFetch } from '@/lib/api';

interface BacklogContextType {
  items: BacklogItem[];
  isLoading: boolean;
  createItem: (item: Omit<BacklogItem, 'id'>) => Promise<BacklogItem | null>;
  updateItem: (id: number, item: Omit<BacklogItem, 'id'>) => Promise<BacklogItem | null>;
  deleteItem: (id: number) => Promise<boolean>;
  refreshItems: () => Promise<void>;
}

const BacklogContext = createContext<BacklogContextType | undefined>(undefined);

export const BacklogProvider = ({ children }: { children: ReactNode }) => {
  const { currentProject } = useProjects();
  const [items, setItems] = useState<BacklogItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const fetchItems = async () => {
    if (!currentProject) {
      setItems([]);
      return;
    }
    setIsLoading(true);
    try {
      const res = await apiFetch(`/items?project_id=${currentProject.id}`);
      const data = await res.json();
      setItems(data);
    } catch (err) {
      console.error('Failed to fetch backlog items:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const createItem = async (item: Omit<BacklogItem, 'id'>) => {
    if (!currentProject) return null;
    try {
      const res = await apiFetch(`/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item),
      });
      if (!res.ok) throw new Error('Failed');
      const newItem = await res.json();
      await fetchItems();
      return newItem;
    } catch (err) {
      console.error('Create item error', err);
      return null;
    }
  };

  const updateItem = async (id: number, item: Omit<BacklogItem, 'id'>) => {
    try {
      const res = await apiFetch(`/api/items/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item),
      });
      if (!res.ok) throw new Error('Failed');
      const up = await res.json();
      await fetchItems();
      return up;
    } catch (err) {
      console.error('Update item error', err);
      return null;
    }
  };

  const deleteItem = async (id: number) => {
    try {
      const res = await apiFetch(`/api/items/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed');
      await fetchItems();
      return true;
    } catch (err) {
      console.error('Delete item error', err);
      return false;
    }
  };

  useEffect(() => {
    fetchItems();
  }, [currentProject]);

  const refreshItems = fetchItems;

  return (
    <BacklogContext.Provider value={{ items, isLoading, createItem, updateItem, deleteItem, refreshItems }}>
      {children}
    </BacklogContext.Provider>
  );
};

export const useBacklog = () => {
  const ctx = useContext(BacklogContext);
  if (!ctx) throw new Error('useBacklog must be used within BacklogProvider');
  return ctx;
};
