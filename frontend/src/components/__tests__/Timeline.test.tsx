import { render, screen, fireEvent, within } from '@testing-library/react';
import Timeline, { TimelineStep } from '../Timeline';

describe('Timeline', () => {
  const steps: TimelineStep[] = [
    { order: 1, node: 'Plan', timestamp: new Date().toISOString(), content: 'Plan content' },
  ];

  it('renders steps and opens modal on click', async () => {
    render(<Timeline steps={steps} />);
    fireEvent.click(screen.getByText('Plan'));
    const dialog = await screen.findByRole('dialog');
    expect(within(dialog).getByText('Plan content')).toBeInTheDocument();
  });

  it('renders empty state when no steps', () => {
    render(<Timeline steps={[]} />);
    expect(screen.getByText('No steps yet')).toBeInTheDocument();
  });
});
