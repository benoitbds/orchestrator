import { render, screen, fireEvent } from '@testing-library/react';
import { AgentActionsAccordion } from './AgentActionsAccordion';
import type { AgentAction } from '@/types/conversation';

describe('AgentActionsAccordion', () => {
  const baseAction: AgentAction = {
    id: 'a1',
    label: 'Test Action',
    status: 'running',
  } as AgentAction;

  it('is closed by default', () => {
    render(<AgentActionsAccordion actions={[baseAction]} />);
    expect(screen.queryByText('Test Action')).not.toBeInTheDocument();
  });

  it('updates running indicator when action succeeds', () => {
    const { rerender } = render(<AgentActionsAccordion actions={[baseAction]} />);
    expect(screen.getByText(/Running: Test Action/)).toBeInTheDocument();
    rerender(<AgentActionsAccordion actions={[{ ...baseAction, status: 'succeeded' }]} />);
    expect(screen.queryByText(/Running:/)).not.toBeInTheDocument();
  });

  it('toggles details JSON', () => {
    const action: AgentAction = {
      ...baseAction,
      status: 'succeeded',
      debug: { input: { foo: 'bar' } },
    };
    render(<AgentActionsAccordion actions={[action]} />);
    fireEvent.click(screen.getByText('Agent actions (1)'));
    expect(screen.queryByText('foo')).not.toBeInTheDocument();
    fireEvent.click(screen.getByText('Details'));
    expect(screen.getByText('foo')).toBeInTheDocument();
    fireEvent.click(screen.getByText('Details'));
    expect(screen.queryByText('foo')).not.toBeInTheDocument();
  });
});
