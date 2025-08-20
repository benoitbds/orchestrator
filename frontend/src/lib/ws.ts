import { getApiBaseUrl } from './api';

function getWsBaseUrl(): string {
  const api = getApiBaseUrl();
  if (api.startsWith('http')) {
    return api.replace(/^http/, 'ws');
  }
  const { protocol, host } = window.location;
  const wsProto = protocol === 'https:' ? 'wss:' : 'ws:';
  const base = api ? api : '';
  return `${wsProto}//${host}${base}`;
}

export function connectWS(path: string): WebSocket {
  const base = getWsBaseUrl().replace(/\/+$, '');
  const url = `${base}${path.startsWith('/') ? path : '/' + path}`;
  return new WebSocket(url);
}
