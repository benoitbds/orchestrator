import { render, screen, fireEvent, act } from '@testing-library/react';
import { vi } from 'vitest';

vi.mock('@/lib/firebase', () => ({ auth: {} }));
vi.mock('firebase/auth', () => ({
  signInWithEmailAndPassword: vi.fn(),
  createUserWithEmailAndPassword: vi.fn(),
  GoogleAuthProvider: vi.fn(),
  signInWithPopup: vi.fn(),
}));

import {
  signInWithEmailAndPassword,
  signInWithPopup,
} from 'firebase/auth';
import LoginPage from '../page';

describe('LoginPage', () => {
  beforeEach(() => {
    (signInWithEmailAndPassword as any).mockReset();
    (signInWithPopup as any).mockReset();
  });

  it('signs in with email and password', async () => {
    signInWithEmailAndPassword.mockResolvedValue({});
    render(<LoginPage />);
    fireEvent.change(screen.getByPlaceholderText('email'), {
      target: { value: 'a@b.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('password'), {
      target: { value: 'pwd' },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    });
    expect(signInWithEmailAndPassword).toHaveBeenCalledWith({}, 'a@b.com', 'pwd');
  });

  it('shows error when sign-in fails', async () => {
    signInWithEmailAndPassword.mockRejectedValue(new Error('nope'));
    render(<LoginPage />);
    fireEvent.change(screen.getByPlaceholderText('email'), {
      target: { value: 'a@b.com' },
    });
    fireEvent.change(screen.getByPlaceholderText('password'), {
      target: { value: 'pwd' },
    });
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Sign in' }));
    });
    expect(await screen.findByText('nope')).toBeInTheDocument();
  });
});
