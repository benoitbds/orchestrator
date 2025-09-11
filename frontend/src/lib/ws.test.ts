import { describe, it, expect, beforeEach, afterAll } from 'vitest';
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
  it('returns explicit override when provided', () => {
    process.env.NEXT_PUBLIC_WS_URL = 'wss://override.example/stream';
    expect(getWSUrl()).toBe('wss://override.example/stream');
  });

  it('derives ws url from window location (http)', () => {
    (global as any).window = {
      location: { protocol: 'http:', host: 'localhost:3000' },
    } as any;
    expect(getWSUrl('/chat')).toBe('ws://localhost:3000/chat');
  });

  it('derives wss url from window location (https)', () => {
    (global as any).window = {
      location: { protocol: 'https:', host: 'agent4ba.baq.ovh' },
    } as any;
    expect(getWSUrl()).toBe('wss://agent4ba.baq.ovh/stream');
  });

  it('falls back to NEXT_PUBLIC_DOMAIN when window undefined', () => {
    process.env.NEXT_PUBLIC_DOMAIN = 'example.org';
    expect(getWSUrl('/foo')).toBe('wss://example.org/foo');
  });

  it('falls back to default domain when no env', () => {
    expect(getWSUrl()).toBe('wss://agent4ba.baq.ovh/stream');
  });
});
