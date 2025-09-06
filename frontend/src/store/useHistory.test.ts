import { describe, it, expect, beforeEach } from 'vitest';
import { useHistory } from './useHistory';

describe('useHistory store', () => {
  beforeEach(() => {
    useHistory.setState({ turns: {}, orderDesc: [], promoted: {} });
  });

  it('promotes temp id to real id', () => {
    useHistory.getState().createTurn('temp', 'hi');
    useHistory.getState().promoteTurn('temp', 'real');
    const state = useHistory.getState();
    expect(state.turns.real).toBeDefined();
    expect(state.orderDesc[0]).toBe('real');
  });

  it('dedupes agent text using hash', () => {
    useHistory.getState().createTurn('t', 'hi');
    useHistory.getState().setAgentTextOnce('t', 'summary');
    const firstHash = useHistory.getState().turns.t.lastSummaryHash;
    useHistory.getState().setAgentTextOnce('t', 'summary');
    expect(useHistory.getState().turns.t.lastSummaryHash).toBe(firstHash);
  });

  it('patches actions', () => {
    useHistory.getState().createTurn('t', 'hi');
    useHistory.getState().appendAction('t', { id: 'a', label: 'A', status: 'running' });
    useHistory.getState().patchAction('t', 'a', { status: 'succeeded', durationMs: 10 });
    const action = useHistory.getState().turns.t.actions[0];
    expect(action.status).toBe('succeeded');
    expect(action.durationMs).toBe(10);
  });
});
