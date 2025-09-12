import { render, screen, act } from '@testing-library/react';
import { vi } from 'vitest';

let pathnameMock = '/';
vi.mock('next/navigation', () => ({
  usePathname: () => pathnameMock,
}));

const listeners: ((u: unknown) => void)[] = [];
vi.mock('firebase/auth', () => ({
  onAuthStateChanged: (_auth: unknown, cb: (u: unknown) => void) => {
    listeners.push(cb);
    return () => {};
  },
}));
vi.mock('@/lib/firebase', () => ({ auth: {} }));

import { AuthGate } from '../AuthGate';

describe('AuthGate', () => {
  beforeEach(() => {
    listeners.length = 0;
    pathnameMock = '/';
  });

  it('renders children when authenticated', () => {
    render(
      <AuthGate>
        <div>secret</div>
      </AuthGate>
    );
    act(() => listeners[0]({ uid: 'u1' }));
    expect(screen.getByText('secret')).toBeInTheDocument();
  });

  it('prompts when unauthenticated', () => {
    render(
      <AuthGate>
        <div>secret</div>
      </AuthGate>
    );
    act(() => listeners[0](null));
    expect(screen.getByText(/please/i)).toBeInTheDocument();
  });

  it('allows public paths without auth', () => {
    pathnameMock = '/login';
    render(
      <AuthGate>
        <div>public</div>
      </AuthGate>
    );
    expect(screen.getByText('public')).toBeInTheDocument();
  });
});
