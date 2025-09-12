"use client";
import { ReactNode, useEffect, useState } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { usePathname } from "next/navigation";
import { auth } from "@/lib/firebase";

export function AuthGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [isAuthed, setAuthed] = useState(false);
  const pathname = usePathname();

  // Public routes that must render without auth
  const isPublic = (() => {
    if (!pathname) return false;
    if (pathname === "/login") return true;
    // Add other public paths here if needed, e.g. /privacy, /terms
    return false;
  })();

  useEffect(() => {
    return onAuthStateChanged(auth, (u) => {
      setAuthed(!!u);
      setReady(true);
    });
  }, []);

  if (isPublic) return <>{children}</>;
  if (!ready) return null; // or a loader
  if (!isAuthed)
    return (
      <div style={{ padding: 24 }}>
        Please <a href="/login">sign in</a>.
      </div>
    );
  return <>{children}</>;
}
