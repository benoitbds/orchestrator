import { getApiBaseUrl } from './api';

function getWsBaseUrl(): string {
  const api = getApiBaseUrl();
  if (api.startsWith('http')) {
    return api.replace(/^http/, 'ws');
  }
  
  // En développement, utiliser directement l'adresse du backend
  if (process.env.NODE_ENV === 'development' && api === '/api') {
    return 'ws://192.168.1.93:8000';
  }
  
  const { protocol, host } = window.location;
  const wsProto = protocol === 'https:' ? 'wss:' : 'ws:';
  const base = api ? api : '';
  return `${wsProto}//${host}${base}`;
}

export function connectWS(path: string): WebSocket {
  const base = getWsBaseUrl().replace(/\/+$/, '');
  const url = `${base}${path.startsWith('/') ? path : '/' + path}`;
  return new WebSocket(url);
}
