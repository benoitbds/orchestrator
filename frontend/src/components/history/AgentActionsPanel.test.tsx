import { render, screen, fireEvent } from '@testing-library/react';
import { AgentActionsPanel } from './AgentActionsPanel';
import { AgentStep } from '@/hooks/useRunStream';

describe('AgentActionsPanel', () => {
  const baseStep: AgentStep = {
    id: 'list_items_1',
    tool: 'list_items',
    startedAt: Date.now(),
    request: { project_id: 1 },
    state: 'running',
  };

  it('renders steps and toggles details', () => {
    const steps: AgentStep[] = [
      { ...baseStep, state: 'success', ok: true, result: { ok: true }, finishedAt: Date.now() },
    ];
    render(<AgentActionsPanel steps={steps} status="done" />);
    expect(screen.getByText('Agent actions (1)')).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText(/"project_id": 1/)).toBeInTheDocument();
  });

  it('shows error badge when failed', () => {
    const steps: AgentStep[] = [
      { ...baseStep, state: 'failed', ok: false, error: 'boom', finishedAt: Date.now() },
    ];
    render(<AgentActionsPanel steps={steps} status="error" />);
    expect(screen.getByText(/Failed: boom/)).toBeInTheDocument();
  });

  it('renders safely when steps are missing', () => {
    render(<AgentActionsPanel status="idle" />);
    expect(screen.getByText('Agent actions (0)')).toBeInTheDocument();
    expect(screen.getByText('No actions yet')).toBeInTheDocument();
  });
});
