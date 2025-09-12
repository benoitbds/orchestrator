"use client";
import { ReactNode, useEffect, useState } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { usePathname, useRouter } from "next/navigation";

import { auth } from "@/lib/firebase";

export function AuthGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [isAuthed, setAuthed] = useState(false);

  const pathname = usePathname();
  const router = useRouter();

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

  useEffect(() => {
    if (ready && !isAuthed && !isPublic) {
      router.push('/login');
    }
  }, [ready, isAuthed, isPublic, router]);

  if (isPublic) return <>{children}</>;
  if (!ready) return null; // or a loader

  if (!isAuthed)
    return null; // redirect will happen via useEffect
  return <>{children}</>;
}
