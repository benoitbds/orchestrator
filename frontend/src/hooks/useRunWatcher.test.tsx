import { renderHook, act } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import useRunWatcher from './useRunWatcher';

declare global {
  // eslint-disable-next-line no-var
  var fetch: any;
}

const mockWs = {
  send: vi.fn(),
  close: vi.fn(),
  onopen: null as any,
  onmessage: null as any,
  onclose: null as any,
  onerror: null as any,
};

vi.mock('@/lib/ws', () => ({
  connectWS: vi.fn(() => mockWs),
}));

vi.mock('@/lib/api', () => ({
  http: (url: string) => fetch(url),
}));

import { connectWS } from '@/lib/ws';

describe('useRunWatcher', () => {
  it('does nothing when runId is null', () => {
    renderHook(() => useRunWatcher({ runId: null }));
    expect(connectWS).not.toHaveBeenCalled();
  });

  it('invokes callbacks on messages', () => {
    const onStep = vi.fn();
    const onFinal = vi.fn();
    renderHook(() => useRunWatcher({ runId: '1', onStep, onFinal }));
    act(() => {
      mockWs.onopen?.(new Event('open'));
      mockWs.onmessage?.({ data: JSON.stringify({ type: 'step', node: 'plan' }) });
      mockWs.onmessage?.({ data: JSON.stringify({ type: 'final', status: 'done' }) });
    });
    expect(onStep).toHaveBeenCalled();
    expect(onFinal).toHaveBeenCalled();
    expect(mockWs.close).toHaveBeenCalled();
  });
});
