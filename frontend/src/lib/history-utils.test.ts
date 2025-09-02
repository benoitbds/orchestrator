import { describe, expect, it } from 'vitest';
import { formatTime, ms } from './history-utils';

// Given/When/Then style comments

describe('ms', () => {
  it('formats numbers', () => {
    expect(ms(123)).toBe('123ms');
  });
  it('handles undefined', () => {
    expect(ms()).toBe('');
  });
});

describe('formatTime', () => {
  it('formats ISO strings', () => {
    const date = new Date('2024-01-01T12:34:56Z');
    expect(formatTime(date.toISOString())).toMatch(/12:34/);
  });
  it('handles invalid strings', () => {
    expect(formatTime('invalid')).toBe('Invalid Date');
  });
});
