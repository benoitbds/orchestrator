import { describe, it, expect, beforeEach, vi } from 'vitest';
import { listDocuments, uploadDocument } from './documents';

// Mock fetch globally
const globalAny: any = global;

describe('documents api', () => {
  beforeEach(() => {
    globalAny.fetch = vi.fn();
  });

  describe('listDocuments', () => {
    it('returns documents when request succeeds', async () => {
      const docs = [{ id: 1, project_id: 1, filename: 'doc.txt' }];
      globalAny.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(docs) });
      const result = await listDocuments(1);
      expect(globalAny.fetch).toHaveBeenCalledWith('/api/projects/1/documents', undefined);
      expect(result).toEqual(docs);
    });

    it('throws on error response', async () => {
      globalAny.fetch.mockResolvedValue({ ok: false });
      await expect(listDocuments(1)).rejects.toThrow('Failed to list documents');
    });
  });

  describe('uploadDocument', () => {
    it('posts file and returns document', async () => {
      const doc = { id: 1, project_id: 1, filename: 'test.txt' };
      globalAny.fetch.mockResolvedValue({ ok: true, json: () => Promise.resolve(doc) });
      const file = new File(['hello'], 'test.txt');
      const result = await uploadDocument(1, file);
      const [url, options] = globalAny.fetch.mock.calls[0];
      expect(url).toBe('/api/projects/1/documents');
      expect(options.method).toBe('POST');
      expect(options.body).toBeInstanceOf(FormData);
      expect(result).toEqual(doc);
    });

    it('throws on upload failure', async () => {
      globalAny.fetch.mockResolvedValue({ ok: false });
      const file = new File(['hello'], 'test.txt');
      await expect(uploadDocument(1, file)).rejects.toThrow('Failed to upload document');
    });
  });
});
