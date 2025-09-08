import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useAgentStream } from './useAgentStream';
import { useRunsStore } from '@/stores/useRunsStore';

class MockWebSocket {
  url: string;
  onopen: (() => void) | null = null;
  onmessage: ((ev: { data: string }) => void) | null = null;
  onclose: ((ev: { code: number }) => void) | null = null;
  sent: string[] = [];
  static last?: MockWebSocket;
  constructor(url: string) {
    this.url = url;
    MockWebSocket.last = this;
    setTimeout(() => this.onopen && this.onopen(), 0);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {}
}

(global as any).WebSocket = MockWebSocket as any;

describe('useAgentStream on close', () => {
  beforeEach(() => {
    MockWebSocket.last = undefined;
    useRunsStore.getState().clearRuns();
    vi.resetAllMocks();
  });

  it('finalizes run with summary when backend is done', async () => {
    const tempId = 'temp1';
    const realId = 'real1';
    const summary = 'result summary';
    useRunsStore.getState().startRun(tempId);
    const onFinish = vi.fn();

    (global as any).fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'done', summary }),
    });

    renderHook(() => useAgentStream(tempId, { objective: 'test', projectId: 1, onFinish }));

    await waitFor(() => {
      if (!MockWebSocket.last) throw new Error('ws not ready');
    });

    act(() => {
      MockWebSocket.last?.onmessage?.({ data: JSON.stringify({ status: 'started', run_id: realId }) });
    });

    act(() => {
      MockWebSocket.last?.onclose?.({ code: 1000 });
    });

    await waitFor(() => expect(onFinish).toHaveBeenCalledWith(summary));
    const run = useRunsStore.getState().runs[realId];
    expect(run.status).toBe('completed');
    expect(run.summary).toBe(summary);
  });

  it('marks run failed when summary fetch fails', async () => {
    const tempId = 'temp2';
    const realId = 'real2';
    useRunsStore.getState().startRun(tempId);
    const onError = vi.fn();

    (global as any).fetch = vi.fn().mockRejectedValue(new Error('network'));

    renderHook(() => useAgentStream(tempId, { objective: 'test', projectId: 1, onError }));

    await waitFor(() => {
      if (!MockWebSocket.last) throw new Error('ws not ready');
    });

    act(() => {
      MockWebSocket.last?.onmessage?.({ data: JSON.stringify({ status: 'started', run_id: realId }) });
    });

    act(() => {
      MockWebSocket.last?.onclose?.({ code: 1000 });
    });

    await waitFor(() => expect(onError).toHaveBeenCalled());
    const run = useRunsStore.getState().runs[realId];
    expect(run.status).toBe('failed');
  });
});

