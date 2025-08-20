import { render, screen, waitFor } from '@testing-library/react';
import RunsPanel from '../RunsPanel';
import { vi } from 'vitest';

vi.mock('@/context/ProjectContext', () => ({
  useProjects: () => ({ currentProject: { id: 1 } }),
}));

vi.mock('next/link', () => ({
  default: ({ children, ...props }: any) => <a {...props}>{children}</a>,
}));

declare global {
  // eslint-disable-next-line no-var
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
    json: async () => [{ run_id: '1', status: 'ok', steps: [] }],
  });

  render(<RunsPanel />);
  expect(await screen.findByText('Détails du run')).toBeInTheDocument();
});

it('supports object with runs property', async () => {
  global.fetch = vi.fn().mockResolvedValue({
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
