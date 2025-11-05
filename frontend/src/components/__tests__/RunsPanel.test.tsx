import { render, screen, waitFor } from '@testing-library/react';
import RunsPanel from '../RunsPanel';
import { vi } from 'vitest';
vi.mock('@/lib/firebase', () => ({ auth: { currentUser: { getIdToken: vi.fn().mockResolvedValue(null) } } }));

vi.mock('@/context/ProjectContext', () => ({
  useProjects: () => ({ currentProject: { id: 1 } }),
}));

vi.mock('next/link', () => ({
  default: ({ children, ...props }: any) => <a {...props}>{children}</a>,
}));

declare global {
   
  var fetch: any;
}

beforeAll(() => {
  process.env.NEXT_PUBLIC_API_BASE_URL = 'http://api.test';
});

afterEach(() => {
  vi.clearAllMocks();
});

it('renders runs when API returns an array', async () => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => [{ run_id: '1', status: 'ok', steps: [] }],
  });

  render(<RunsPanel />);
  expect(await screen.findByText('Détails du run')).toBeInTheDocument();
});

it('supports object with runs property', async () => {
  global.fetch = vi.fn().mockResolvedValue({
    ok: true,
    status: 200,
    json: async () => ({ runs: [{ run_id: '2', status: 'ok', steps: [] }] }),
  });

  render(<RunsPanel />);
  expect(await screen.findByText('Détails du run')).toBeInTheDocument();
});

it('falls back to empty list on fetch error', async () => {
  global.fetch = vi.fn().mockRejectedValue(new Error('fail'));

  render(<RunsPanel />);
  await waitFor(() => {
    expect(screen.queryByText('Détails du run')).not.toBeInTheDocument();
  });
});

it('refetches when refreshKey changes', async () => {
  const fetchMock = vi.fn().mockImplementation(() => {
    if (fetchMock.mock.calls.length === 0) {
      return Promise.resolve({ ok: true, status: 200, json: async () => [] });
    }
    return Promise.resolve({
      ok: true,
      status: 200,
      json: async () => [{ run_id: '3', status: 'ok', steps: [] }],
    });
  });
  global.fetch = fetchMock;

  const { rerender } = render(<RunsPanel refreshKey={0} />);
  rerender(<RunsPanel refreshKey={1} />);

  expect(await screen.findByText('Détails du run')).toBeInTheDocument();
});
