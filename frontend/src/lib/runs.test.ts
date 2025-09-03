import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { getRunCost } from './runs';

const sample = {
  total_tokens: 5,
  cost_eur: 0.1,
  by_agent: [
    {
      agent: 'a',
      prompt_tokens: 2,
      completion_tokens: 3,
      total_tokens: 5,
      cost_eur: 0.1,
    },
  ],
};

describe('getRunCost', () => {
  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://api';
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('fetches run cost', async () => {
    const json = vi.fn().mockResolvedValue(sample);
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json });
    (global as any).fetch = fetchMock;

    const data = await getRunCost('1');
    expect(fetchMock).toHaveBeenCalledWith('http://api/runs/1/cost', undefined);
    expect(data).toEqual(sample);
  });

  it('throws on non-ok response', async () => {
    (global as any).fetch = vi.fn().mockResolvedValue({ ok: false });
    await expect(getRunCost('1')).rejects.toThrow('Failed to load run cost');
  });

  it('propagates network errors', async () => {
    const err = new Error('net');
    (global as any).fetch = vi.fn().mockRejectedValue(err);
    await expect(getRunCost('1')).rejects.toThrow(err);
  });
});
