import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { DocumentList } from '../project/DocumentList';
import { toast } from 'sonner';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() }
}));

const deleteDocument = vi.fn();
vi.mock('@/lib/documents', () => ({
  deleteDocument: (...args: any[]) => deleteDocument(...args)
}));

const runAgent = vi.fn();
vi.mock('@/lib/api', () => ({
  getApiBaseUrl: () => '',
  runAgent: (...args: any[]) => runAgent(...args)
}));

const docs = [{ id: 1, project_id: 1, filename: 'doc.txt' }];

describe('DocumentList', () => {
  beforeEach(() => {
    deleteDocument.mockReset();
    runAgent.mockReset();
    (toast.success as any).mockReset();
    (toast.error as any).mockReset();
  });

  it('deletes document after confirmation', async () => {
    const refetch = vi.fn();
    let resolve: () => void;
    deleteDocument.mockImplementation(() => new Promise(r => { resolve = r; }));
    vi.spyOn(window, 'confirm').mockReturnValue(true);

    render(<DocumentList documents={docs} refetch={refetch} />);
    const button = screen.getByRole('button', { name: /delete doc.txt/i });
    fireEvent.click(button);
    expect(button).toBeDisabled();
    resolve!();
    await waitFor(() => expect(refetch).toHaveBeenCalled());
    await waitFor(() => expect(button).not.toBeDisabled());
    expect(toast.success).toHaveBeenCalled();
  });

  it('does not delete when confirmation is cancelled', () => {
    const refetch = vi.fn();
    vi.spyOn(window, 'confirm').mockReturnValue(false);
    render(<DocumentList documents={docs} refetch={refetch} />);
    fireEvent.click(screen.getByRole('button', { name: /delete doc.txt/i }));
    expect(deleteDocument).not.toHaveBeenCalled();
    expect(refetch).not.toHaveBeenCalled();
  });

  it('shows error toast on failure', async () => {
    const refetch = vi.fn();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    deleteDocument.mockRejectedValue(new Error('fail'));
    render(<DocumentList documents={docs} refetch={refetch} />);
    fireEvent.click(screen.getByRole('button', { name: /delete doc.txt/i }));
    await waitFor(() => expect(deleteDocument).toHaveBeenCalled());
    await waitFor(() => expect(refetch).not.toHaveBeenCalled());
    expect(toast.error).toHaveBeenCalled();
  });

  it('starts analysis and refreshes on success', async () => {
    const refetch = vi.fn();
    let resolve: () => void;
    runAgent.mockImplementation(() => new Promise(r => { resolve = r; }));

    render(<DocumentList documents={docs} refetch={refetch} />);
    const button = screen.getByRole('button', { name: /analyze doc.txt/i });
    fireEvent.click(button);
    expect(button).toBeDisabled();
    resolve!();
    await waitFor(() => expect(runAgent).toHaveBeenCalled());
    await waitFor(() => expect(refetch).toHaveBeenCalled());
    expect(toast.success).toHaveBeenCalled();
    await waitFor(() => expect(button).not.toBeDisabled());
  });

  it('shows error toast when analysis fails', async () => {
    const refetch = vi.fn();
    runAgent.mockRejectedValue(new Error('fail'));

    render(<DocumentList documents={docs} refetch={refetch} />);
    const button = screen.getByRole('button', { name: /analyze doc.txt/i });
    fireEvent.click(button);
    await waitFor(() => expect(runAgent).toHaveBeenCalled());
    await waitFor(() => expect(refetch).not.toHaveBeenCalled());
    expect(toast.error).toHaveBeenCalled();
    await waitFor(() => expect(button).not.toBeDisabled());
  });
});
