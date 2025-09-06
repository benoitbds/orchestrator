import { describe, it, expect, vi } from 'vitest';

const UUID_V4_REGEX = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

describe('safeId', () => {
  it('uses crypto.randomUUID when available', async () => {
    const { safeId } = await import('./safeId');
    const spy = vi.spyOn(globalThis.crypto, 'randomUUID');
    const id = safeId();
    expect(spy).toHaveBeenCalled();
    expect(id).toMatch(UUID_V4_REGEX);
    spy.mockRestore();
  });

  it('generates a v4 UUID without crypto.randomUUID', async () => {
    const originalRandomUUID = globalThis.crypto.randomUUID;
    Object.defineProperty(globalThis.crypto, 'randomUUID', { value: undefined, configurable: true });

    const { safeId } = await import('./safeId');
    const id = safeId();

    expect(id).toMatch(UUID_V4_REGEX);

    Object.defineProperty(globalThis.crypto, 'randomUUID', { value: originalRandomUUID, configurable: true });
  });

  it('generates a v4 UUID without any crypto API', async () => {
    const originalDescriptor = Object.getOwnPropertyDescriptor(globalThis, 'crypto');
    Object.defineProperty(globalThis, 'crypto', { value: undefined, configurable: true });

    const { safeId } = await import('./safeId');
    const id = safeId();

    expect(id).toMatch(UUID_V4_REGEX);

    if (originalDescriptor) {
      Object.defineProperty(globalThis, 'crypto', originalDescriptor);
    }
  });
});
