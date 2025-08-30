"use client";
import { BacklogProvider } from "@/context/BacklogContext";
import { AgentLayout } from "@/components/layout/AgentLayout";
import { Toaster } from "sonner";

export default function Home() {
  return (
    <BacklogProvider>
      <AgentLayout />
      <Toaster richColors position="top-right" />
    </BacklogProvider>
  );
}
