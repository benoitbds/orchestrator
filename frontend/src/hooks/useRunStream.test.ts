import { describe, it, expect, beforeEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { useRunStream, parseNode } from './useRunStream';

class MockWebSocket {
  url: string;
  onopen: (() => void) | null = null;
  sent: string[] = [];
  static last?: MockWebSocket;
  constructor(url: string) {
    this.url = url;
    MockWebSocket.last = this;
    setTimeout(() => this.onopen && this.onopen(), 0);
  }
  send(data: string) {
    this.sent.push(data);
  }
  close() {}
}

global.WebSocket = MockWebSocket as any;

describe('parseNode', () => {
  it('parses tool nodes', () => {
    expect(parseNode('tool:foo:request')).toEqual({ kind: 'tool', tool: 'foo', phase: 'request' });
  });
  it('parses write nodes', () => {
    expect(parseNode('write')).toEqual({ kind: 'write' });
  });
  it('throws on unknown node', () => {
    expect(() => parseNode('x')).toThrow();
  });
});

describe('useRunStream', () => {
  beforeEach(() => {
    MockWebSocket.last = undefined;
  });

  it('starts idle and opens websocket on start', () => {
    const { result } = renderHook(() => useRunStream({ projectId: 1, autoStart: false }));
    expect(result.current.status).toBe('idle');
    act(() => result.current.start());
    expect(MockWebSocket.last).toBeDefined();
  });
});
