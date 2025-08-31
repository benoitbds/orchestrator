"use client";
import { BacklogProvider } from "@/context/BacklogContext";
import { AgentShell } from "@/pages/AgentShell";
import { Toaster } from "sonner";

export default function Home() {
  return (
    <BacklogProvider>
      <AgentShell />
      <Toaster richColors position="top-right" />
    </BacklogProvider>
  );
}
