import { describe, it, expect, vi } from 'vitest';
import { apiFetch, runAgent } from './api';


vi.mock('./firebase', () => ({
  auth: {
    currentUser: { getIdToken: vi.fn().mockResolvedValue('test-token') },
  },
}));

describe('runAgent', () => {
  const payload = { project_id: 1, objective: 'test' };

  it('posts payload and returns response json', async () => {
    const json = vi.fn().mockResolvedValue({ id: 1 });
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json });
    (global as any).fetch = fetchMock;
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://api';
    const data = await runAgent(payload);

    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe('http://api/agent/run');
    const headers = call[1].headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer test-token');
    expect(headers.get('Content-Type')).toBe('application/json');
    expect(call[1].body).toBe(JSON.stringify(payload));
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

describe('apiFetch', () => {

  it('attaches Authorization header when token present', async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true });
    (global as any).fetch = fetchMock;
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://api';
    await apiFetch('/test');

    const call = fetchMock.mock.calls[0];
    expect(call[0]).toBe('http://api/test');
    const headers = call[1].headers as Headers;
    expect(headers.get('Authorization')).toBe('Bearer test-token');
    expect(call[1].credentials).toBe('include');

  });
});
