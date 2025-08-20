"use client";
import { useEffect, useState } from "react";
import { Badge } from "@/components/ui/badge";
import { http } from "@/lib/api";
import { connectWS } from "@/lib/ws";

export default function StatusBar() {
  const [apiOk, setApiOk] = useState<boolean | null>(null);
  const [wsOk, setWsOk] = useState<boolean | null>(null);

  useEffect(() => {
    const check = () => {
      http("/health")
        .then(r => r.json())
        .then(d => setApiOk(d.status === "ok"))
        .catch(() => setApiOk(false));
      try {
        const ws = connectWS("/stream");
        ws.onopen = () => {
          setWsOk(true);
          ws.close();
        };
        ws.onerror = () => setWsOk(false);
      } catch {
        setWsOk(false);
      }
    };
    check();
    const id = setInterval(check, 5000);
    return () => clearInterval(id);
  }, []);

  const render = (label: string, state: boolean | null, okText: string, downText: string) => {
    const variant = state === null ? "secondary" : state ? "default" : "destructive";
    const text = state === null ? `${label}: …` : state ? `${label}: ${okText}` : `${label}: ${downText}`;
    return <Badge variant={variant}>{text}</Badge>;
  };

  return (
    <div className="fixed top-0 left-0 right-0 flex gap-2 p-2 text-xs z-50">
      {render("API", apiOk, "OK", "Down")}
      {render("WS", wsOk, "Connected", "Disconnected")}
    </div>
  );
}
