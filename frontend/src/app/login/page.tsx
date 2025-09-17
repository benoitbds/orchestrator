"use client";

import { useState } from "react";
import { auth } from "@/lib/firebase";
import {
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithEmailAndPassword,
  signInWithPopup,
} from "firebase/auth";

import { AgentIdentity } from "@/components/branding/AgentIdentity";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

export type FirebaseLoadingState = "idle" | "signin" | "signup" | "google";

export function getFirebaseErrorMessage(errorCode?: string): string {
  switch (errorCode) {
    case "auth/email-already-in-use":
      return "An account with this email already exists. Try signing in instead.";
    case "auth/weak-password":
      return "Password should be at least 6 characters long.";
    case "auth/invalid-email":
      return "Please enter a valid email address.";
    case "auth/operation-not-allowed":
      return "Email/password accounts are not enabled. Please contact support.";
    case "auth/user-not-found":
      return "No account found with this email address.";
    case "auth/wrong-password":
      return "Incorrect password. Please try again.";
    case "auth/user-disabled":
      return "This account has been disabled. Please contact support.";
    case "auth/too-many-requests":
      return "Too many failed attempts. Please try again later.";
    default:
      return "";
  }
}

function resolveErrorMessage(error: unknown, fallback: string): string {
  if (typeof error === "object" && error !== null) {
    const firebaseError = error as { code?: string; message?: string };
    const friendly = getFirebaseErrorMessage(firebaseError.code);
    if (friendly) {
      return friendly;
    }
    if (firebaseError.message) {
      return firebaseError.message;
    }
  }
  if (typeof error === "string" && error.trim().length > 0) {
    return error;
  }
  return fallback;
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState<FirebaseLoadingState>("idle");
  const [error, setError] = useState<string | null>(null);

  const isBusy = loading !== "idle";

  async function runAuthFlow(
    state: Exclude<FirebaseLoadingState, "idle">,
    action: () => Promise<unknown>,
    fallbackMessage: string,
  ) {
    setError(null);
    setLoading(state);
    try {
      await action();
      window.location.href = "/";
    } catch (err) {
      setError(resolveErrorMessage(err, fallbackMessage));
    } finally {
      setLoading("idle");
    }
  }

  const handleSignIn = () =>
    runAuthFlow(
      "signin",
      () => signInWithEmailAndPassword(auth, email, password),
      "Sign in failed",
    );

  const handleSignUp = () =>
    runAuthFlow(
      "signup",
      () => createUserWithEmailAndPassword(auth, email, password),
      "Sign up failed",
    );

  const handleGoogle = () =>
    runAuthFlow(
      "google",
      () => signInWithPopup(auth, new GoogleAuthProvider()),
      "Google sign-in failed",
    );

  return (
    <div className="relative min-h-dvh overflow-hidden bg-slate-950">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,_rgba(190,242,100,0.18),_transparent_65%)]"
      />
      <div className="absolute inset-0 bg-[linear-gradient(135deg,_rgba(15,118,110,0.3),_transparent_55%),linear-gradient(200deg,_rgba(190,242,100,0.18),_transparent_65%)]" />
      <div className="relative z-10 flex min-h-dvh items-center justify-center px-4 py-12">
        <div className="grid w-full max-w-5xl gap-8 rounded-3xl border border-lime-500/30 bg-white/5 p-6 shadow-[0_25px_70px_rgba(15,23,42,0.65)] backdrop-blur-xl md:p-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,380px)]">
          <section className="hidden flex-col justify-between gap-8 text-slate-200 lg:flex">
            <div className="space-y-6">
              <AgentIdentity className="w-full border-lime-500/20 bg-slate-950/70" />
              <p className="text-sm leading-relaxed text-slate-300">
                Connect to Agent4BA and orchestrate your product backlog with an autonomous partner. Align your objectives, generate actionable plans, and review AI-assisted delivery steps in one command center.
              </p>
            </div>
            <ul className="space-y-3 text-sm text-slate-200">
              {[
                "Draft backlog items from plain-language objectives",
                "Prioritize initiatives with explainable recommendations",
                "Track autonomous agent runs and review decision history",
              ].map((feature) => (
                <li key={feature} className="flex items-start gap-3">
                  <span className="mt-1 h-2 w-2 rounded-full bg-lime-300" aria-hidden />
                  <span>{feature}</span>
                </li>
              ))}
            </ul>
          </section>

          <Card className="relative border border-lime-500/30 bg-slate-950/80 text-slate-100 backdrop-blur-md">
            <CardHeader className="space-y-2 text-center lg:text-left">
              <CardTitle className="text-2xl font-semibold text-lime-200">
                Welcome back
              </CardTitle>
              <CardDescription className="text-slate-300">
                Sign in to access your Agent4BA workspace
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-5">
              <div className="grid gap-3">
                <Label htmlFor="email" className="text-sm font-medium text-slate-200">
                  Email
                </Label>
                <Input
                  id="email"
                  type="email"
                  autoComplete="email"
                  placeholder="you@example.com"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  disabled={isBusy}
                  className="border-slate-700 bg-slate-900/80 text-slate-100 placeholder:text-slate-500"
                />
              </div>
              <div className="grid gap-3">
                <Label htmlFor="password" className="text-sm font-medium text-slate-200">
                  Password
                </Label>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(event) => setPassword(event.target.value)}
                  required
                  minLength={6}
                  disabled={isBusy}
                  className="border-slate-700 bg-slate-900/80 text-slate-100 placeholder:text-slate-500"
                />
              </div>
              {error && (
                <p className="rounded-md border border-red-500/30 bg-red-500/10 px-3 py-2 text-sm text-red-200" role="alert" aria-live="assertive">
                  {error}
                </p>
              )}
            </CardContent>
            <CardFooter className="flex flex-col gap-3">
              <Button className="w-full bg-lime-400 text-slate-900 hover:bg-lime-300" onClick={handleSignIn} disabled={isBusy}>
                {loading === "signin" ? "Signing in..." : "Sign in"}
              </Button>
              <Button
                variant="secondary"
                className="w-full border border-lime-500/30 bg-slate-900/70 text-lime-200 hover:text-slate-900 hover:bg-lime-200"
                onClick={handleSignUp}
                disabled={isBusy}
              >
                {loading === "signup" ? "Creating..." : "Create account"}
              </Button>
              <div className="relative my-1 w-full text-center text-xs uppercase tracking-[0.35em] text-slate-500">
                <span className="relative z-10 bg-slate-950/80 px-2">or</span>
                <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 border-t border-slate-700" aria-hidden />
              </div>
              <Button
                variant="outline"
                className="w-full border-lime-500/40 bg-slate-900/60 text-lime-200 hover:bg-lime-200 hover:text-slate-900"
                onClick={handleGoogle}
                disabled={isBusy}
              >
                {loading === "google" ? "Connecting..." : "Continue with Google"}
              </Button>
              <p className="text-center text-xs text-slate-400">
                Need help? Contact your workspace admin to manage access.
              </p>
            </CardFooter>
          </Card>
        </div>
      </div>
    </div>
  );
}
