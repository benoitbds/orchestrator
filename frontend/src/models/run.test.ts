import { describe, it, expect } from 'vitest';
import { normalizeStep } from './run';

describe('normalizeStep', () => {
  it('parses JSON payload', () => {
    const step = normalizeStep({ node: 'plan', payload: '{"a":1}' });
    expect(step.content).toEqual({ a: 1 });
  });

  it('keeps string when JSON invalid', () => {
    const step = normalizeStep({ node: 'plan', payload: '{invalid}' });
    expect(step.content).toBe('{invalid}');
  });

  it('handles missing fields', () => {
    const step = normalizeStep({});
    expect(step.node).toBe('unknown');
  });
});
