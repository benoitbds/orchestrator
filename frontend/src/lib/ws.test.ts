import { describe, it, expect, beforeEach, afterAll, vi } from 'vitest';

vi.mock('./firebase', () => ({
  auth: {
    currentUser: { getIdToken: vi.fn().mockResolvedValue('tok') },
  },
}));

import { getWSUrl } from './ws';

const originalEnv = { ...process.env };
let originalWindow: any = global.window;

beforeEach(() => {
  process.env = { ...originalEnv };
  delete (global as any).window;
});

afterAll(() => {
  global.window = originalWindow;
});

describe('getWSUrl', () => {
  it('returns explicit override when provided', async () => {
    process.env.NEXT_PUBLIC_WS_URL = 'wss://override.example/stream';
    await expect(getWSUrl()).resolves.toBe('wss://override.example/stream');
  });

  it('derives ws url from window location (http)', async () => {
    (global as any).window = {
      location: { protocol: 'http:', host: 'localhost:3000' },
    } as any;
    await expect(getWSUrl('/chat')).resolves.toBe('ws://localhost:3000/chat?token=tok');
  });

  it('derives wss url from window location (https)', async () => {
    (global as any).window = {
      location: { protocol: 'https:', host: 'agent4ba.baq.ovh' },
    } as any;
    await expect(getWSUrl()).resolves.toBe('wss://agent4ba.baq.ovh/stream?token=tok');
  });

  it('falls back to NEXT_PUBLIC_DOMAIN when window undefined', async () => {
    process.env.NEXT_PUBLIC_DOMAIN = 'example.org';
    await expect(getWSUrl('/foo')).resolves.toBe('wss://example.org/foo');
  });

  it('falls back to default domain when no env', async () => {
    await expect(getWSUrl()).resolves.toBe('wss://agent4ba.baq.ovh/stream');
  });

  it('omits token when no user', async () => {
    const { auth } = await import('./firebase');
    (auth as any).currentUser = null;
    await expect(getWSUrl()).resolves.toBe('wss://agent4ba.baq.ovh/stream');
  });
});
