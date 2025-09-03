import { render, screen } from '@testing-library/react';
import { vi } from 'vitest';
import RunDetail from './[run_id]/page';

vi.mock('@/lib/ws', () => ({
  connectWS: () => ({
    send: vi.fn(),
    close: vi.fn(),
    onopen: null,
    onmessage: null,
    onerror: null,
  }),
}));

vi.mock('next/link', () => ({
  default: ({ children, ...props }: any) => <a {...props}>{children}</a>,
}));

beforeEach(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = 'http://api.test';
});

afterEach(() => {
  vi.restoreAllMocks();
});

it('shows run details when run exists', async () => {
  global.fetch = vi
    .fn()
    .mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({
        run_id: '1',
        objective: 'test',
        status: 'running',
        created_at: new Date().toISOString(),
      }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ events: [] }),
    })
    .mockResolvedValueOnce({
      ok: true,
      json: async () => ({ tokens: 0, cost: 0, by_agent: {} }),
    });
  render(<RunDetail params={{ run_id: '1' }} />);
  expect(await screen.findByText('Run 1')).toBeInTheDocument();
});

it('handles 404 gracefully', async () => {
  const warn = vi.spyOn(console, 'warn').mockImplementation(() => {});
  global.fetch = vi.fn().mockResolvedValue({
    ok: false,
    status: 404,
    json: async () => ({}),
  });
  render(<RunDetail params={{ run_id: '2' }} />);
  expect(
    await screen.findByText('Run not found or has been deleted'),
  ).toBeInTheDocument();
  expect(warn).toHaveBeenCalled();
});
