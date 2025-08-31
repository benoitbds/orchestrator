import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { vi } from 'vitest';
import { ProjectPanel } from '../project/ProjectPanel';

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() }
}));

vi.mock('@/context/ProjectContext', () => ({
  useProjects: () => ({
    projects: [{ id: 1, name: 'P', description: '' }],
    currentProject: { id: 1, name: 'P', description: '' },
    setCurrentProject: vi.fn(),
    refreshProjects: vi.fn(),
  })
}));

const listDocuments = vi.fn();
const uploadDocument = vi.fn();

vi.mock('@/lib/documents', () => ({
  listDocuments: (...args: any[]) => listDocuments(...args),
  uploadDocument: (...args: any[]) => uploadDocument(...args),
}));

describe('ProjectPanel document upload', () => {
  it('uploads file and refreshes list', async () => {
    listDocuments.mockResolvedValueOnce([]);
    const uploaded = { id: 1, project_id: 1, filename: 'test.txt' };
    listDocuments.mockResolvedValue([uploaded]);
    uploadDocument.mockResolvedValue(uploaded);

    render(<ProjectPanel />);

    const file = new File(['hello'], 'test.txt', { type: 'text/plain' });
    const input = screen.getByLabelText(/upload file/i);
    fireEvent.change(input, { target: { files: [file] } });

    fireEvent.click(screen.getByRole('button', { name: /upload/i }));

    await waitFor(() => expect(uploadDocument).toHaveBeenCalled());
    await waitFor(() => expect(screen.getByText('test.txt')).toBeInTheDocument());
  });
});
