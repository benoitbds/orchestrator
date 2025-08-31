import { describe, it, expect, vi, beforeEach } from 'vitest';
vi.mock('./api', () => ({
  http: vi.fn(),
}));

import { getLayout, saveLayout } from './layout';
import { http } from './api';

const fetchMock = http as unknown as ReturnType<typeof vi.fn>;

describe('layout api helpers', () => {
  beforeEach(() => {
    fetchMock.mockReset();
  });

  it('gets layout', async () => {
    fetchMock.mockResolvedValue({ ok: true, json: () => Promise.resolve({ nodes: [{ item_id: 1, x: 0, y: 0 }] }) });
    const nodes = await getLayout(5);
    expect(fetchMock).toHaveBeenCalledWith('/projects/5/layout');
    expect(nodes).toHaveLength(1);
  });

  it('saves layout', async () => {
    fetchMock.mockResolvedValue({ ok: true });
    await saveLayout(2, [{ item_id: 1, x: 1, y: 1 }]);
    expect(fetchMock).toHaveBeenCalledWith('/projects/2/layout', expect.objectContaining({ method: 'PUT' }));
  });

  it('throws on error', async () => {
    fetchMock.mockResolvedValue({ ok: false });
    await expect(getLayout(1)).rejects.toThrow();
  });
});
