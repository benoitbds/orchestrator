import { initializeApp } from 'firebase/app';
import { getAuth } from 'firebase/auth';

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FB_API_KEY || 'test',
  authDomain: process.env.NEXT_PUBLIC_FB_AUTH_DOMAIN || 'test',
  projectId: process.env.NEXT_PUBLIC_FB_PROJECT_ID || 'test',
  storageBucket: process.env.NEXT_PUBLIC_FB_STORAGE_BUCKET,
  messagingSenderId: process.env.NEXT_PUBLIC_FB_MESSAGING_SENDER_ID,
  appId: process.env.NEXT_PUBLIC_FB_APP_ID || 'test',
};

let auth;
try {
  const app = initializeApp(firebaseConfig);
  auth = getAuth(app);
} catch {
  auth = { currentUser: null } as any;
}

export { auth };
