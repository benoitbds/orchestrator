import { render, screen } from '@testing-library/react';
import AgentTimeline, { AgentTimelineStep } from '../AgentTimeline';

describe('AgentTimeline', () => {
  it('renders steps grouped by run', () => {
    const steps: AgentTimelineStep[] = [
      {
        runId: 'run1',
        node: 'tool:create_item:request',
        content: { name: 'create_item', args: { title: 'foo' } },
        timestamp: new Date().toISOString(),
      },
      {
        runId: 'run1',
        node: 'tool:create_item:response',
        content: { ok: true, result: { id: 42 } },
        timestamp: new Date().toISOString(),
      },
    ];
    render(<AgentTimeline steps={steps} />);
    expect(screen.getByText(/create_item\(request\)/)).toBeInTheDocument();
    expect(screen.getByText(/ok=true/)).toBeInTheDocument();
  });

  it('shows placeholder when no steps', () => {
    render(<AgentTimeline steps={[]} />);
    expect(screen.getByText(/No steps yet/i)).toBeInTheDocument();
  });

  it('marks error responses', () => {
    const steps: AgentTimelineStep[] = [
      {
        runId: 'run1',
        node: 'tool:create_item:response',
        content: { ok: false, error: 'fail' },
        timestamp: new Date().toISOString(),
      },
    ];
    render(<AgentTimeline steps={steps} />);
    expect(screen.getByText('error')).toBeInTheDocument();
  });
});
