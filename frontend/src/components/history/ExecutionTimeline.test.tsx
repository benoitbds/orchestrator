import { render, fireEvent, screen } from '@testing-library/react';
import { ExecutionTimeline } from './ExecutionTimeline';
import type { Step } from '@/types/history';

describe('ExecutionTimeline', () => {
  const steps: Step[] = [
    {
      id: '1',
      t: new Date().toISOString(),
      kind: 'LLM',
      title: 'call',
      status: 'failed',
      details: {
        error: { code: '429', message: 'Too many requests', hint: 'wait', docUrl: 'https://docs' },
      },
    },
  ];

  it('shows error details when expanded', () => {
    render(<ExecutionTimeline steps={steps} />);
    fireEvent.click(screen.getByRole('button'));
    expect(screen.getByText('Too many requests')).toBeInTheDocument();
    expect(screen.getByText(/Hint: wait/)).toBeInTheDocument();
  });

  it('filters steps', () => {
    const filter = (s: Step) => s.status === 'completed';
    const { queryByText } = render(<ExecutionTimeline steps={steps} filter={filter} />);
    expect(queryByText('call')).toBeNull();
  });
});
