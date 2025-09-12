import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { forwardRef, useImperativeHandle, act } from 'react';

vi.mock('@/context/ProjectContext', () => ({
  useProjects: () => ({ currentProject: { id: 1 } })
}));

vi.mock('@/components/project/ProjectPanel', () => ({ ProjectPanel: () => <div /> }));
vi.mock('@/lib/firebase', () => ({ auth: { currentUser: { getIdToken: vi.fn().mockResolvedValue(null) } } }));
vi.mock('@/components/StatusBar', () => ({ default: () => <div /> }));
vi.mock('@/components/BacklogPane', () => ({ default: () => <div /> }));
vi.mock('@/components/HistoryPanel', () => ({ default: () => <div /> }));
vi.mock('@/components/RunsPanel', () => ({ default: () => <div /> }));

const refreshItems = vi.fn();
vi.mock('@/context/BacklogContext', () => ({
  useBacklog: () => ({ refreshItems }),
  BacklogProvider: ({ children }: any) => <div>{children}</div>
}));

const push = vi.fn();
const clear = vi.fn();
vi.mock('@/components/StreamViewer', () => ({
  __esModule: true,
  default: forwardRef((_props: any, ref: any) => {
    useImperativeHandle(ref, () => ({ push, clear }));
    return <div data-testid="viewer" />;
  })
}));

class MockWS {
  onopen: any;
  onmessage: any;
  onclose: any;
  sent: any[] = [];
  close = vi.fn();
  send = vi.fn((msg: any) => { this.sent.push(msg); });
}
const ws = new MockWS();
vi.mock('@/lib/ws', () => ({ connectWS: () => ws }));

const api = vi.fn();
vi.mock('@/lib/api', () => ({ apiFetch: (...args: any[]) => api(...args) }));

import Home from '../page';

beforeEach(() => {
  push.mockReset();
  clear.mockReset();
  refreshItems.mockReset();
  ws.onopen = null;
  ws.onmessage = null;
  ws.onclose = null;
  ws.sent = [];
  api.mockReset();
});

describe.skip('handleRun', () => {
  it('displays immediate html and refreshes backlog', async () => {
    api.mockResolvedValueOnce({ json: async () => ({ run_id: 1, html: '<p>hi</p>' }) });
    render(<Home />);
    await act(async () => {
      fireEvent.change(
        screen.getByLabelText('Chat message'),
        { target: { value: 'test' } }
      );
      fireEvent.click(screen.getByText('Lancer'));
    });
    await waitFor(() => expect(push).toHaveBeenCalled());
    expect(refreshItems).toHaveBeenCalled();
    const body = JSON.parse(api.mock.calls[0][1].body);
    expect(body.project_id).toBe(1);
  });

  it('sends run_id over websocket', async () => {
    api.mockResolvedValueOnce({ json: async () => ({ run_id: 2, html: '' }) });
    render(<Home />);
    await act(async () => {
      fireEvent.change(
        screen.getByLabelText('Chat message'),
        { target: { value: 'test' } }
      );
      fireEvent.click(screen.getByText('Lancer'));
    });
    ws.onopen?.();
    expect(ws.sent[0]).toBe(JSON.stringify({ run_id: 2 }));
  });

  it('handles done message and refreshes backlog', async () => {
    api
      .mockResolvedValueOnce({ json: async () => ({ run_id: 3, html: '' }) })
      .mockResolvedValueOnce({ json: async () => ({ status: 'done', html: '<p>w</p>' }) });
    render(<Home />);
    await act(async () => {
      fireEvent.change(
        screen.getByLabelText('Chat message'),
        { target: { value: 'test' } }
      );
      fireEvent.click(screen.getByText('Lancer'));
    });
    ws.onopen?.();
    ws.onmessage?.({ data: JSON.stringify({ status: 'done' }) });
    await waitFor(() => expect(push).toHaveBeenLastCalledWith({ node: 'write', state: { result: '<p>w</p>' } }));
    expect(refreshItems).toHaveBeenCalled();
  });

  it('polls when websocket is silent', async () => {
    vi.useFakeTimers();
    api
      .mockResolvedValueOnce({ json: async () => ({ run_id: 4, html: '' }) })
      .mockResolvedValueOnce({ json: async () => ({ status: 'done', html: '<p>p</p>', summary: 's' }) });
    render(<Home />);
    await act(async () => {
      fireEvent.change(
        screen.getByLabelText('Chat message'),
        { target: { value: 'test' } }
      );
      fireEvent.click(screen.getByText('Lancer'));
    });
    ws.onopen?.();
    await act(async () => {
      await vi.advanceTimersByTimeAsync(7000);
    });
    expect(push).toHaveBeenLastCalledWith({ node: 'write', state: { result: '<p>p</p>' } });
    expect(ws.close).toHaveBeenCalled();
    vi.useRealTimers();
  });
});
