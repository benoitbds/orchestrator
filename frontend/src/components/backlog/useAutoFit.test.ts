import { describe, it, expect } from 'vitest';
import { computeFit } from './useAutoFit';

describe('computeFit', () => {
  it('centers box inside container', () => {
    const res = computeFit({ width: 200, height: 100 }, { x: 0, y: 0, width: 100, height: 50 });
    expect(res.scale).toBe(2);
    expect(res.x).toBe(0);
    expect(res.y).toBe(0);
  });

  it('limits scale to 2.5', () => {
    const res = computeFit({ width: 1000, height: 1000 }, { x: 0, y: 0, width: 10, height: 10 });
    expect(res.scale).toBe(2.5);
  });
});
