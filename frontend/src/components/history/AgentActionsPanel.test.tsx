import { render, screen, fireEvent } from '@testing-library/react';
import { AgentActionsPanel } from './AgentActionsPanel';
import { useAgentActionsStore } from '@/hooks/useAgentActions';

describe('AgentActionsPanel', () => {
  const runId = 'r1';
  beforeEach(() => {
    useAgentActionsStore.getState().clear();
  });

  it('shows actions and expands payload', () => {
    useAgentActionsStore.getState().addFromMessage({
      run_id: runId,
      node: 'tool:test:request',
      args: { foo: 'bar' },
    });
    render(<AgentActionsPanel runId={runId} />);
    expect(screen.getByText('Agent actions (1)')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText(/foo/)).toBeInTheDocument();
  });
});
