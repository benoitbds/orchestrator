import { describe, it, expect } from 'vitest';
import { connectWS } from './ws';

class MockWebSocket {
  url: string;
  constructor(url: string) {
    this.url = url;
  }
}

global.WebSocket = MockWebSocket as any;

describe('connectWS', () => {
  const base = `ws://${window.location.host}/api`;

  it('adds a leading slash when missing', () => {
    const ws = connectWS('chat');
    expect(ws.url).toBe(`${base}/chat`);
  });

  it('uses existing leading slash', () => {
    const ws = connectWS('/chat');
    expect(ws.url).toBe(`${base}/chat`);
  });
});
