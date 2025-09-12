"use client";

import { useState } from "react";
import { auth } from "@/lib/firebase";
import {
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  GoogleAuthProvider,
  signInWithPopup,
} from "firebase/auth";

// shadcn/ui
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

function getFirebaseErrorMessage(errorCode: string): string {
  switch (errorCode) {
    case 'auth/email-already-in-use':
      return 'An account with this email already exists. Try signing in instead.';
    case 'auth/weak-password':
      return 'Password should be at least 6 characters long.';
    case 'auth/invalid-email':
      return 'Please enter a valid email address.';
    case 'auth/operation-not-allowed':
      return 'Email/password accounts are not enabled. Please contact support.';
    case 'auth/user-not-found':
      return 'No account found with this email address.';
    case 'auth/wrong-password':
      return 'Incorrect password. Please try again.';
    case 'auth/user-disabled':
      return 'This account has been disabled. Please contact support.';
    case 'auth/too-many-requests':
      return 'Too many failed attempts. Please try again later.';
    default:
      return '';
  }
}

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [pwd, setPwd] = useState("");
  const [loading, setLoading] = useState<"none"|"signin"|"signup"|"google">("none");
  const [err, setErr] = useState<string | null>(null);

  async function doSignIn() {
    setErr(null); setLoading("signin");
    try { 
      await signInWithEmailAndPassword(auth, email, pwd); 
      window.location.href = "/"; 
    }
    catch (e: any) { 
      console.error('Signin error:', e);
      const errorMessage = getFirebaseErrorMessage(e.code) || e.message || "Sign in failed";
      setErr(errorMessage);
    }
    finally { setLoading("none"); }
  }

  async function doSignUp() {
    setErr(null); setLoading("signup");
    console.log('Attempting signup with email:', email, 'length:', email.length);
    try { 
      await createUserWithEmailAndPassword(auth, email, pwd); 
      window.location.href = "/"; 
    }
    catch (e: any) { 
      console.error('Signup error:', e);
      const errorMessage = getFirebaseErrorMessage(e.code) || e.message || "Sign up failed";
      setErr(errorMessage);
    }
    finally { setLoading("none"); }
  }

  async function doGoogle() {
    setErr(null); setLoading("google");
    try { await signInWithPopup(auth, new GoogleAuthProvider()); window.location.href = "/"; }
    catch (e: any) { setErr(e.message ?? "Google sign-in failed"); }
    finally { setLoading("none"); }
  }

  return (
    <div className="min-h-dvh flex items-center justify-center bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-slate-50 to-slate-100 p-6">
      <Card className="w-full max-w-md shadow-lg">
        <CardHeader>
          <CardTitle className="text-2xl">Sign in</CardTitle>
          <CardDescription>Access your Agent 4 BA workspace</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid gap-2">
            <Label htmlFor="email">Email</Label>
            <Input 
              id="email" 
              type="email" 
              placeholder="you@example.com" 
              value={email} 
              onChange={(e)=>setEmail(e.target.value)}
              required
            />
          </div>
          <div className="grid gap-2">
            <Label htmlFor="password">Password</Label>
            <Input 
              id="password" 
              type="password" 
              placeholder="••••••••" 
              value={pwd} 
              onChange={(e)=>setPwd(e.target.value)}
              required
              minLength={6}
            />
          </div>
          {err && <p className="text-sm text-red-600">{err}</p>}
        </CardContent>
        <CardFooter className="flex flex-col gap-2">
          <Button className="w-full" onClick={doSignIn} disabled={loading!=="none"}>
            {loading==="signin" ? "Signing in..." : "Sign in"}
          </Button>
          <Button variant="secondary" className="w-full" onClick={doSignUp} disabled={loading!=="none"}>
            {loading==="signup" ? "Creating..." : "Create account"}
          </Button>
          <div className="relative my-1 w-full text-center text-xs text-slate-500">
            <span className="bg-white px-2 relative z-10">or</span>
            <div className="absolute inset-x-0 top-1/2 -translate-y-1/2 border-t"></div>
          </div>
          <Button variant="outline" className="w-full" onClick={doGoogle} disabled={loading!=="none"}>
            {loading==="google" ? "Connecting..." : "Continue with Google"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
