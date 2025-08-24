import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { forwardRef, useImperativeHandle, act } from 'react';

vi.mock('@/context/ProjectContext', () => ({
  useProjects: () => ({ currentProject: { id: 1 } })
}));

vi.mock('@/components/ProjectPanel', () => ({ ProjectPanel: () => <div /> }));
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

const http = vi.fn();
vi.mock('@/lib/api', () => ({ http: (...args: any[]) => http(...args) }));

import Home from '../page';

beforeEach(() => {
  push.mockReset();
  clear.mockReset();
  refreshItems.mockReset();
  ws.onopen = null;
  ws.onmessage = null;
  ws.onclose = null;
  ws.sent = [];
  http.mockReset();
});

describe('handleRun', () => {
  it('displays immediate html and refreshes backlog', async () => {
    http.mockResolvedValueOnce({ json: async () => ({ run_id: 1, html: '<p>hi</p>' }) });
    render(<Home />);
    await act(async () => {
      fireEvent.change(screen.getByPlaceholderText('Votre objectif…'), { target: { value: 'test' } });
      fireEvent.click(screen.getByText('Lancer'));
    });
    await waitFor(() => expect(push).toHaveBeenCalled());
    expect(refreshItems).toHaveBeenCalled();
    const body = JSON.parse(http.mock.calls[0][1].body);
    expect(body.project_id).toBe(1);
  });

  it('sends run_id over websocket', async () => {
    http.mockResolvedValueOnce({ json: async () => ({ run_id: 2, html: '' }) });
    render(<Home />);
    await act(async () => {
      fireEvent.change(screen.getByPlaceholderText('Votre objectif…'), { target: { value: 'test' } });
      fireEvent.click(screen.getByText('Lancer'));
    });
    ws.onopen?.();
    expect(ws.sent[0]).toBe(JSON.stringify({ run_id: 2 }));
  });

  it('handles done message and refreshes backlog', async () => {
    http
      .mockResolvedValueOnce({ json: async () => ({ run_id: 3, html: '' }) })
      .mockResolvedValueOnce({ json: async () => ({ status: 'done', html: '<p>w</p>' }) });
    render(<Home />);
    await act(async () => {
      fireEvent.change(screen.getByPlaceholderText('Votre objectif…'), { target: { value: 'test' } });
      fireEvent.click(screen.getByText('Lancer'));
    });
    ws.onopen?.();
    ws.onmessage?.({ data: JSON.stringify({ status: 'done' }) });
    await waitFor(() => expect(push).toHaveBeenLastCalledWith({ node: 'write', state: { result: '<p>w</p>' } }));
    expect(refreshItems).toHaveBeenCalled();
  });
});
