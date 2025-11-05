import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { DocumentList } from '../project/DocumentList';
import { toast } from 'sonner';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() }
}));

const deleteDocument = vi.fn();
const analyzeDocument = vi.fn();
vi.mock('@/lib/documents', () => ({
  deleteDocument: (...args: any[]) => deleteDocument(...args),
  analyzeDocument: (...args: any[]) => analyzeDocument(...args)
}));

vi.mock('@/lib/firebase', () => ({
  auth: {
    currentUser: {
      getIdToken: vi.fn().mockResolvedValue('test-token')
    }
  }
}));


const docs = [{ id: 1, project_id: 1, filename: 'doc.txt', status: 'UPLOADED' as const }];

describe('DocumentList', () => {
  beforeEach(() => {
    deleteDocument.mockReset();
    analyzeDocument.mockReset();
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

  it('shows error toast on delete failure', async () => {
    const refetch = vi.fn();
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    deleteDocument.mockRejectedValue(new Error('fail'));
    render(<DocumentList documents={docs} refetch={refetch} />);
    fireEvent.click(screen.getByRole('button', { name: /delete doc.txt/i }));
    await waitFor(() => expect(deleteDocument).toHaveBeenCalled());
    await waitFor(() => expect(refetch).not.toHaveBeenCalled());
    expect(toast.error).toHaveBeenCalled();
  });

  it('starts analysis with LangGraph multi-agent', async () => {
    const refetch = vi.fn();
    const onAnalyze = vi.fn().mockResolvedValue(undefined);
    analyzeDocument.mockResolvedValue(undefined);

    render(<DocumentList documents={docs} refetch={refetch} onAnalyze={onAnalyze} />);
    const button = screen.getByRole('button', { name: /analyze doc.txt/i });
    fireEvent.click(button);
    
    await waitFor(() => expect(analyzeDocument).toHaveBeenCalledWith(1));
    await waitFor(() => expect(refetch).toHaveBeenCalled());
    
    expect(onAnalyze).toHaveBeenCalledWith(
      expect.stringContaining('doc.txt')
    );
    expect(toast.success).toHaveBeenCalled();
  });

  it('shows error toast when analyze fails', async () => {
    const refetch = vi.fn();
    analyzeDocument.mockRejectedValue(new Error('fail'));

    render(<DocumentList documents={docs} refetch={refetch} />);
    const button = screen.getByRole('button', { name: /analyze doc.txt/i });
    fireEvent.click(button);
    
    await waitFor(() => expect(analyzeDocument).toHaveBeenCalled());
    expect(toast.error).toHaveBeenCalled();
  });
});
