import { render, screen, fireEvent } from '@testing-library/react';
import { vi } from 'vitest';
import { ItemTree } from '../ItemTree';
import { BacklogTable } from '../BacklogTable';
import { DiagramView } from '../backlog/DiagramView';
import { useItems } from '@/lib/hooks';

vi.mock('@/lib/hooks', () => ({ useItems: vi.fn() }));
vi.mock('@/components/backlog/useAutoFit', () => ({ useAutoFit: () => () => {} }));
vi.mock('@/lib/layout', () => ({ getLayout: vi.fn().mockResolvedValue([]), saveLayout: vi.fn() }));
vi.mock('d3-selection', () => ({ select: () => ({ call: () => {}, select: () => ({ attr: () => {} }) }) }));
vi.mock('d3-zoom', () => ({
  zoom: () => {
    const obj: any = {
      scaleExtent: () => obj,
      on: () => obj,
      scaleBy: () => {},
    };
    return obj;
  },
}));

// provide canvas measureText
beforeAll(() => {
  HTMLCanvasElement.prototype.getContext = () => ({
    measureText: () => ({ width: 100 }),
  }) as any;
});

const mockedUseItems = useItems as unknown as ReturnType<typeof vi.fn>;

describe('Backlog title click behavior', () => {
  it('ItemTree - title click calls onEdit', () => {
    mockedUseItems.mockReturnValue({
      tree: [{ id: 1, title: 'Tree Item', type: 'Epic', children: [] }],
      isLoading: false,
      error: null,
    });
    const onEdit = vi.fn();
    render(<ItemTree projectId={1} onEdit={onEdit} />);
    fireEvent.click(screen.getByText('Tree Item'));
    expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ id: 1 }));
  });

  it('ItemTree - clicking container does not call onEdit', () => {
    mockedUseItems.mockReturnValue({
      tree: [{ id: 2, title: 'No Edit', type: 'Epic', children: [] }],
      isLoading: false,
      error: null,
    });
    const onEdit = vi.fn();
    const { container } = render(<ItemTree projectId={1} onEdit={onEdit} />);
    fireEvent.click(container.querySelector('[data-item-id="2"]')!);
    expect(onEdit).not.toHaveBeenCalled();
  });

  it('BacklogTable - title click calls onEdit', () => {
    mockedUseItems.mockReturnValue({
      data: [{ id: 3, title: 'Table Item', type: 'Epic' }],
      isLoading: false,
      error: null,
    });
    const onEdit = vi.fn();
    render(<BacklogTable projectId={1} onEdit={onEdit} />);
    fireEvent.click(screen.getByText('Table Item'));
    expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ id: 3 }));
  });

  it('BacklogTable - modifier button triggers onEdit once', () => {
    mockedUseItems.mockReturnValue({
      data: [{ id: 4, title: 'Btn Item', type: 'Epic' }],
      isLoading: false,
      error: null,
    });
    const onEdit = vi.fn();
    render(<BacklogTable projectId={1} onEdit={onEdit} />);
    fireEvent.click(screen.getByText('Modifier'));
    expect(onEdit).toHaveBeenCalledTimes(1);
  });

  it('DiagramView - title click calls onEdit', async () => {
    mockedUseItems.mockReturnValue({
      data: [{ id: 5, title: 'Diagram Item', type: 'Epic', parent_id: null }],
      isLoading: false,
      error: null,
    });
    const onEdit = vi.fn();
    render(<DiagramView projectId={1} onEdit={onEdit} />);
    const title = await screen.findByText('Diagram Item');
    fireEvent.click(title);
    expect(onEdit).toHaveBeenCalledWith(expect.objectContaining({ id: 5 }));
  });

  it('DiagramView - clicking node body does not call onEdit', async () => {
    mockedUseItems.mockReturnValue({
      data: [{ id: 6, title: 'No Title', type: 'Epic', parent_id: null }],
      isLoading: false,
      error: null,
    });
    const onEdit = vi.fn();
    const { container } = render(<DiagramView projectId={1} onEdit={onEdit} />);
    await screen.findByText('No Title');
    fireEvent.click(container.querySelector('rect')!);
    expect(onEdit).not.toHaveBeenCalled();
  });
});
