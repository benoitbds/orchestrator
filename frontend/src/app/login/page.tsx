"use client";
import { useState } from "react";
import { auth } from "@/lib/firebase";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithPopup,
} from "firebase/auth";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [pwd, setPwd] = useState("");
  const [err, setErr] = useState<string | null>(null);

  async function doSignIn() {
    setErr(null);
    try {
      await signInWithEmailAndPassword(auth, email, pwd);
      window.location.href = "/";
    } catch (e: any) {
      setErr(e.message ?? "Sign in failed");
    }
  }

  async function doSignUp() {
    setErr(null);
    try {
      await createUserWithEmailAndPassword(auth, email, pwd);
      window.location.href = "/";
    } catch (e: any) {
      setErr(e.message ?? "Sign up failed");
    }
  }

  async function doGoogle() {
    setErr(null);
    try {
      await signInWithPopup(auth, new GoogleAuthProvider());
      window.location.href = "/";
    } catch (e: any) {
      setErr(e.message ?? "Google sign-in failed");
    }
  }

  return (
    <div style={{ maxWidth: 420, margin: "48px auto", fontFamily: "system-ui" }}>
      <h1>Sign in</h1>
      <input
        placeholder="email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        style={{ width: "100%", margin: "8px 0", padding: 8 }}
      />
      <input
        placeholder="password"
        type="password"
        value={pwd}
        onChange={(e) => setPwd(e.target.value)}
        style={{ width: "100%", margin: "8px 0", padding: 8 }}
      />
      {err && <div style={{ color: "crimson" }}>{err}</div>}
      <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
        <button onClick={doSignIn}>Sign in</button>
        <button onClick={doSignUp}>Create account</button>
        <button onClick={doGoogle}>Continue with Google</button>
      </div>
    </div>
  );
}
