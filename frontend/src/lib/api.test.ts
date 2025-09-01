import { describe, it, expect, beforeEach, vi } from 'vitest';
import { getApiBaseUrl, runAgent } from './api';

describe('getApiBaseUrl', () => {
  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  });

  it('returns env value without trailing slash', () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://example.com/';
    expect(getApiBaseUrl()).toBe('http://example.com');
  });

  it('falls back to /api when env missing', () => {
    expect(getApiBaseUrl()).toBe('/api');
  });

  it('handles relative base', () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = '/backend/';
    expect(getApiBaseUrl()).toBe('/backend');
  });
});

describe('runAgent', () => {
  const payload = { project_id: 1, objective: 'test' };

  it('posts payload and returns response json', async () => {
    const json = vi.fn().mockResolvedValue({ id: 1 });
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json });
    (global as any).fetch = fetchMock;
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://api';

    const data = await runAgent(payload);

    expect(fetchMock).toHaveBeenCalledWith('http://api/agent/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    expect(data).toEqual({ id: 1 });
  });

  it('throws when response not ok', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false });
    (global as any).fetch = fetchMock;
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://api';

    await expect(runAgent(payload)).rejects.toThrow('Agent run failed');
  });

  it('propagates network errors', async () => {
    const err = new Error('network');
    const fetchMock = vi.fn().mockRejectedValue(err);
    (global as any).fetch = fetchMock;
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://api';

    await expect(runAgent(payload)).rejects.toThrow(err);
  });
});
