import { describe, it, expect, beforeEach } from 'vitest';
import { getApiBaseUrl } from './api';

describe('getApiBaseUrl', () => {
  beforeEach(() => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
  });

  it('returns env value without trailing slash', () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = 'http://example.com/';
    expect(getApiBaseUrl()).toBe('http://example.com');
  });

  it('falls back to /api when env missing', () => {
    expect(getApiBaseUrl()).toBe('/api');
  });

  it('handles relative base', () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = '/backend/';
    expect(getApiBaseUrl()).toBe('/backend');
  });
});
