import { describe, it, expect, beforeEach } from 'vitest';
import { useAgentActionsStore } from './useAgentActions';

const runId = 'run1';

function add(msg: any) {
  useAgentActionsStore.getState().addFromMessage({ run_id: runId, ...msg });
}

describe('useAgentActions store', () => {
  beforeEach(() => {
    useAgentActionsStore.getState().clear();
  });

  it('adds request and response actions and dedupes', () => {
    add({ node: 'tool:list:request', args: { a: 1 } });
    add({ node: 'tool:list:request', args: { a: 1 } });
    let actions = Object.values(useAgentActionsStore.getState().actions[runId]);
    expect(actions).toHaveLength(1);
    add({ node: 'tool:list:response', data: { ok: true }, ok: true });
    actions = Object.values(useAgentActionsStore.getState().actions[runId]);
    expect(actions).toHaveLength(2);
    const response = actions.find(a => a.phase === 'response');
    expect(response?.ok).toBe(true);
  });

  it('handles error responses', () => {
    add({ node: 'tool:fail:response', ok: false, data: { err: 'x' } });
    const actions = Object.values(useAgentActionsStore.getState().actions[runId]);
    expect(actions[0].ok).toBe(false);
  });

  it('clears actions by run', () => {
    add({ node: 'tool:list:request' });
    expect(Object.keys(useAgentActionsStore.getState().actions)).toHaveLength(1);
    useAgentActionsStore.getState().clear(runId);
    expect(Object.keys(useAgentActionsStore.getState().actions)).toHaveLength(0);
  });
});
