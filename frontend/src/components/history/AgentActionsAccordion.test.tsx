import { render, screen, fireEvent } from '@testing-library/react';
import { AgentActionsAccordion } from './actions/AgentActionsAccordion';
import type { AgentAction } from '@/types/history';

describe('AgentActionsAccordion', () => {
  const baseAction: AgentAction = {
    id: 'a1',
    label: 'Test Action',
    status: 'running',
  } as AgentAction;

  it('is closed by default and shows running in header', () => {
    render(<AgentActionsAccordion actions={[baseAction]} phase="running" />);
    expect(screen.queryByText('Test Action')).not.toBeInTheDocument();
    expect(screen.getByText(/Running: Test Action/)).toBeInTheDocument();
  });

  it('removes running indicator when action completes', () => {
    const { rerender } = render(<AgentActionsAccordion actions={[baseAction]} phase="running" />);
    rerender(
      <AgentActionsAccordion
        actions={[{ ...baseAction, status: 'succeeded' }]}
        phase="completed"
      />,
    );
    expect(screen.queryByText(/Running:/)).not.toBeInTheDocument();
  });

  it('toggles details JSON', () => {
    const action: AgentAction = {
      ...baseAction,
      status: 'succeeded',
      debug: { input: { foo: 'bar' } },
    };
    render(<AgentActionsAccordion actions={[action]} phase="completed" />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.queryByText('foo')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Details'));
    expect(screen.getByText('foo')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Details'));
    expect(screen.queryByText('foo')).not.toBeInTheDocument();
  });
});
