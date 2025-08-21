import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import BacklogPane from '../BacklogPane';
import { ItemTree } from '../ItemTree';

// Mocks
vi.mock('@/context/ProjectContext', () => ({
  useProjects: () => ({ currentProject: { id: 1 } }),
}));

vi.mock('@/components/ItemDialog', () => ({
  ItemDialog: () => null,
}));

vi.mock('next/dynamic', () => ({
  default: () => () => <svg />,
}));

const useItemsMock = vi.fn();
vi.mock('@/lib/hooks', () => ({
  useItems: (...args: any[]) => useItemsMock(...args),
}));

const sampleTree: any = [
  {
    id: 1,
    title: 'Epic 1',
    type: 'Epic',
    parent_id: null,
    project_id: 1,
    description: null,
    state: 'Backlog',
    benefit_hypothesis: '',
    children: [
      {
        id: 2,
        title: 'Capability 1',
        type: 'Capability',
        parent_id: 1,
        project_id: 1,
        description: null,
        state: 'Backlog',
        benefit_hypothesis: '',
        children: [],
      },
    ],
  },
];

const sampleData: any = [
  {
    id: 1,
    title: 'Epic 1',
    type: 'Epic',
    parent_id: null,
    project_id: 1,
    description: null,
    state: 'Backlog',
    benefit_hypothesis: '',
  },
  {
    id: 2,
    title: 'Capability 1',
    type: 'Capability',
    parent_id: 1,
    project_id: 1,
    description: null,
    state: 'Backlog',
    benefit_hypothesis: '',
  },
];

beforeEach(() => {
  useItemsMock.mockReturnValue({ tree: sampleTree, data: sampleData, isLoading: false, error: null });
});

describe('BacklogPane tabs', () => {
  it('shows tree view by default', () => {
    render(<BacklogPane />);
    expect(screen.getByText('Epic 1')).toBeInTheDocument();
  });

  it('switches to table view', () => {
    render(<BacklogPane />);
    fireEvent.click(screen.getByRole('tab', { name: /Vue Table/i }));
    expect(screen.getByText('Epic 1')).toBeInTheDocument();
  });

  it('switches to diagram view', () => {
    render(<BacklogPane />);
    fireEvent.click(screen.getByRole('tab', { name: /Vue Diagramme/i }));
    expect(screen.getByText('Epic 1')).toBeInTheDocument();
  });
});

describe('ItemTree edge cases', () => {
  it('collapses node to hide children', () => {
    render(<ItemTree projectId={1} onEdit={() => {}} />);
    const toggle = screen.getByLabelText('Collapse');
    fireEvent.click(toggle);
    expect(screen.queryByText('Capability 1')).not.toBeInTheDocument();
  });

  it('shows loading state', () => {
    useItemsMock.mockReturnValueOnce({ tree: [], data: [], isLoading: true, error: null });
    const { container } = render(<ItemTree projectId={1} onEdit={() => {}} />);
    expect(container.querySelector('svg')).toBeTruthy();
  });
});
