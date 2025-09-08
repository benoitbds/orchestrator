import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { BacklogTable } from '../BacklogTable';
import { ItemTree } from '../ItemTree';
import { DiagramView } from '../backlog/DiagramView';
import { ItemDialog } from '../ItemDialog';
import { useItems } from '@/lib/hooks';

vi.mock('@/lib/hooks', () => ({ useItems: vi.fn() }));
vi.mock('@/context/BacklogContext', () => ({ useBacklog: () => ({ deleteItem: vi.fn() }) }));
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

beforeEach(() => {
  mockedUseItems.mockReset();
});

describe('IA badge rendering', () => {
  it('shows IA badge in BacklogTable', () => {
    mockedUseItems.mockReturnValue({
      data: [{ id: 1, title: 'Table Item', type: 'Epic', generated_by_ai: true }],
      isLoading: false,
      error: null,
    });
    render(<BacklogTable projectId={1} onEdit={() => {}} />);
    expect(screen.getByText('IA')).toBeInTheDocument();
  });

  it('shows IA badge in ItemTree', () => {
    mockedUseItems.mockReturnValue({
      tree: [{ id: 2, title: 'Tree Item', type: 'Epic', generated_by_ai: true, children: [] }],
      isLoading: false,
      error: null,
    });
    render(<ItemTree projectId={1} onEdit={() => {}} />);
    expect(screen.getByText('IA')).toBeInTheDocument();
  });

  it('shows IA badge in DiagramView', async () => {
    mockedUseItems.mockReturnValue({
      data: [{ id: 3, title: 'Node', type: 'Epic', parent_id: null, generated_by_ai: true }],
      isLoading: false,
      error: null,
    });
    render(<DiagramView projectId={1} onEdit={() => {}} />);
    await screen.findByText('Node');
    expect(screen.getByText('IA')).toBeInTheDocument();
  });

  it('hides IA badge for non-AI items in DiagramView', async () => {
    mockedUseItems.mockReturnValue({
      data: [{ id: 4, title: 'Clean', type: 'Epic', parent_id: null }],
      isLoading: false,
      error: null,
    });
    render(<DiagramView projectId={1} onEdit={() => {}} />);
    await screen.findByText('Clean');
    expect(screen.queryByText('IA')).toBeNull();
  });

  it('clears generated_by_ai on save in ItemDialog', async () => {
    mockedUseItems.mockReturnValue({ data: [], isLoading: false, error: null });
    const onSave = vi.fn().mockResolvedValue(undefined);
    const item = {
      id: 5,
      title: 'AI Item',
      type: 'Epic',
      project_id: 1,
      parent_id: null,
      description: null,
      generated_by_ai: true,
    } as any;
    render(
      <ItemDialog isOpen={true} onClose={() => {}} item={item} projectId={1} onSave={onSave} />
    );
    fireEvent.click(screen.getByText('Valider'));
    await waitFor(() =>
      expect(onSave).toHaveBeenCalledWith(expect.objectContaining({ generated_by_ai: false }))
    );
  });
});

