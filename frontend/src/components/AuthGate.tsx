"use client";
import { ReactNode, useEffect, useState } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "@/lib/firebase";

export function AuthGate({ children }: { children: ReactNode }) {
  const [ready, setReady] = useState(false);
  const [isAuthed, setAuthed] = useState(false);

  useEffect(() => {
    return onAuthStateChanged(auth, (u) => {
      setAuthed(!!u);
      setReady(true);
    });
  }, []);

  if (!ready) return null;
  if (!isAuthed)
    return (
      <div style={{ padding: 24 }}>
        Please <a href="/login">sign in</a>.
      </div>
    );
  return <>{children}</>;
}
