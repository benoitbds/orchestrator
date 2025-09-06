import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface Message {
  id: string;
  type: "user" | "agent";
  content: string;
  timestamp: number;
  runId?: string;
  status?: "sending" | "completed" | "failed";
  projectId?: number;
}

type MessagesState = {
  messages: Message[];

  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  replaceRunId: (tempId: string, realId: string) => void;
  clearMessages: () => void;
  getMessagesForProject: (projectId?: number) => Message[];
};

export const useMessagesStore = create<MessagesState>()(
  persist(
    (set, get) => ({
      messages: [],

      addMessage: (message: Message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      updateMessage: (id: string, updates: Partial<Message>) =>
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg,
          ),
        })),

      replaceRunId: (tempId: string, realId: string) =>
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.runId === tempId ? { ...msg, runId: realId } : msg,
          ),
        })),

      clearMessages: () =>
        set(() => ({
          messages: [],
        })),

      getMessagesForProject: (projectId?: number) => {
        const { messages } = get();
        if (!projectId) return messages;
        return messages.filter((msg) => msg.projectId === projectId);
      },
    }),
    {
      name: "agent-messages-storage",
      skipHydration: true,
    },
  ),
);
