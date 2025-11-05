import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { validateItem } from '@/lib/api';
import { BacklogTable } from '../BacklogTable';
import { ItemTree } from '../ItemTree';
import { DiagramView } from '../backlog/DiagramView';
import { ItemDialog } from '../ItemDialog';
import { useItems } from '@/lib/hooks';

vi.mock('@/lib/hooks', () => ({ useItems: vi.fn() }));
vi.mock('@/context/BacklogContext', () => ({ useBacklog: () => ({ deleteItem: vi.fn(), refreshItems: vi.fn() }) }));
vi.mock('@/lib/api', () => ({
  apiFetch: vi.fn(),
  validateItem: vi.fn().mockResolvedValue({}),
  validateItems: vi.fn().mockResolvedValue([]),
}));
vi.mock('@/components/backlog/useAutoFit', () => ({ useAutoFit: () => () => {} }));
vi.mock('@/lib/layout', () => ({ getLayout: vi.fn().mockResolvedValue([]), saveLayout: vi.fn() }));
vi.mock('d3-selection', () => ({ select: () => ({ call: () => {}, select: () => ({ attr: () => {} }) }) }));
vi.mock('d3-zoom', () => ({
  zoom: () => {
    const obj: any = { scaleExtent: () => obj, on: () => obj, scaleBy: () => {} };
    return obj;
  },
}));

beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = () => ({
    measureText: () => ({ width: 100 }),
  }) as any;
});

const mockedUseItems = useItems as unknown as ReturnType<typeof vi.fn>;
const mockedValidateItem = validateItem as unknown as ReturnType<typeof vi.fn>;

beforeEach(() => {
  mockedUseItems.mockReset();
  mockedValidateItem.mockReset();
});

describe('IA badge rendering', () => {
  it('shows IA badge in BacklogTable', () => {
    mockedUseItems.mockReturnValue({
      data: [{ id: 1, title: 'Table Item', type: 'Epic', project_id: 1, parent_id: null, ia_review_status: 'pending' }],
      tree: [],
      isLoading: false,
      error: null,
      mutate: vi.fn(),
    });
    render(<BacklogTable projectId={1} onEdit={() => {}} />);
    expect(screen.getByText('IA')).toBeInTheDocument();
  });

  it('shows IA badge in ItemTree', () => {
    mockedUseItems.mockReturnValue({
      tree: [{ id: 2, title: 'Tree Item', type: 'Epic', project_id: 1, parent_id: null, ia_review_status: 'pending', children: [] }],
      data: [],
      isLoading: false,
      error: null,
      mutate: vi.fn(),
    });
    render(<ItemTree projectId={1} onEdit={() => {}} />);
    expect(screen.getByText('IA')).toBeInTheDocument();
  });

  it('shows IA badge in DiagramView', async () => {
    mockedUseItems.mockReturnValue({
      data: [{ id: 3, title: 'Node', type: 'Epic', project_id: 1, parent_id: null, ia_review_status: 'pending' }],
      tree: [],
      isLoading: false,
      error: null,
      mutate: vi.fn(),
    });
    render(<DiagramView projectId={1} onEdit={() => {}} />);
    await screen.findByText('Node');
    expect(screen.getByText('IA')).toBeInTheDocument();
  });

  it('hides IA badge for non-AI items in DiagramView', async () => {
    mockedUseItems.mockReturnValue({
      data: [{ id: 4, title: 'Clean', type: 'Epic', project_id: 1, parent_id: null, ia_review_status: 'approved' }],
      tree: [],
      isLoading: false,
      error: null,
      mutate: vi.fn(),
    });
    render(<DiagramView projectId={1} onEdit={() => {}} />);
    await screen.findByText('Clean');
    expect(screen.queryByText('IA')).toBeNull();
  });

  it('validates item from ItemDialog', async () => {
    mockedUseItems.mockReturnValue({ data: [], tree: [], isLoading: false, error: null, mutate: vi.fn() });
    const onSave = vi.fn().mockResolvedValue(undefined);
    const item = {
      id: 5,
      title: 'AI Item',
      type: 'Epic',
      project_id: 1,
      parent_id: null,
      description: null,
      ia_review_status: 'pending',
    } as any;
    render(
      <ItemDialog isOpen={true} onClose={() => {}} item={item} projectId={1} onSave={onSave} />
    );
    fireEvent.click(screen.getByText('Valider'));
    await waitFor(() => expect(mockedValidateItem).toHaveBeenCalledWith(5));
  });
});
