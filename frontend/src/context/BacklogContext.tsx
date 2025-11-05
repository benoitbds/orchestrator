"use client";
import { createContext, useContext, useCallback, ReactNode } from 'react';
import useSWR from 'swr';
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
  addItemRealtime: (item: BacklogItem) => void;
  addPlaceholder: (placeholder: Partial<BacklogItem> & { id: string | number }) => void;
  removePlaceholder: (id: string | number) => void;
}

const BacklogContext = createContext<BacklogContextType | undefined>(undefined);

const fetcher = async (url: string) => {
  const res = await apiFetch(url);
  if (!res.ok) throw new Error('Failed to fetch');
  return res.json();
};

export const BacklogProvider = ({ children }: { children: ReactNode }) => {
  const { currentProject } = useProjects();
  
  const swrKey = currentProject ? `/items?project_id=${currentProject.id}` : null;
  
  const { data, error, mutate, isLoading } = useSWR<BacklogItem[]>(
    swrKey,
    fetcher,
    {
      refreshInterval: 30000,
      dedupingInterval: 30000,
      revalidateOnFocus: false,
      revalidateOnReconnect: false,
    }
  );
  
  const items = data || [];
  
  // Add item to local state immediately (optimistic update)
  const addItemRealtime = useCallback((item: BacklogItem) => {
    mutate((current) => {
      if (!current) return [item];
      // Check if item already exists
      if (current.some(i => i.id === item.id)) return current;
      return [...current, item];
    }, false); // Don't revalidate
  }, [mutate]);
  
  // Add placeholder for items being created
  const addPlaceholder = useCallback((placeholder: Partial<BacklogItem> & { id: string | number }) => {
    mutate((current) => {
      if (!current) return [placeholder as BacklogItem];
      return [...current, placeholder as BacklogItem];
    }, false);
  }, [mutate]);
  
  // Remove placeholder when real item arrives
  const removePlaceholder = useCallback((id: string | number) => {
    mutate((current) => {
      if (!current) return current;
      return current.filter(item => item.id !== id);
    }, false);
  }, [mutate]);

  const createItem = useCallback(async (item: Omit<BacklogItem, 'id'>) => {
    if (!currentProject) return null;
    try {
      const res = await apiFetch(`/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item),
      });
      if (!res.ok) throw new Error('Failed');
      const newItem = await res.json();
      await mutate();
      return newItem;
    } catch (err) {
      console.error('Create item error', err);
      return null;
    }
  }, [currentProject, mutate]);

  const updateItem = useCallback(async (id: number, item: Omit<BacklogItem, 'id'>) => {
    try {
      const res = await apiFetch(`/api/items/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(item),
      });
      if (!res.ok) throw new Error('Failed');
      const up = await res.json();
      await mutate();
      return up;
    } catch (err) {
      console.error('Update item error', err);
      return null;
    }
  }, [mutate]);

  const deleteItem = useCallback(async (id: number) => {
    try {
      const res = await apiFetch(`/api/items/${id}`, { method: 'DELETE' });
      if (!res.ok) throw new Error('Failed');
      await mutate();
      return true;
    } catch (err) {
      console.error('Delete item error', err);
      return false;
    }
  }, [mutate]);

  const refreshItems = useCallback(async () => {
    await mutate(undefined, { revalidate: true });
  }, [mutate]);

  return (
    <BacklogContext.Provider value={{ 
      items, 
      isLoading, 
      createItem, 
      updateItem, 
      deleteItem, 
      refreshItems,
      addItemRealtime,
      addPlaceholder,
      removePlaceholder
    }}>
      {children}
    </BacklogContext.Provider>
  );
};

export const useBacklog = () => {
  const ctx = useContext(BacklogContext);
  if (!ctx) throw new Error('useBacklog must be used within BacklogProvider');
  return ctx;
};
