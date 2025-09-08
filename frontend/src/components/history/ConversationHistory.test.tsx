import { render, screen } from '@testing-library/react';
import ConversationHistory from './ConversationHistory';
import { useHistory } from '@/store/useHistory';
import type { ConversationTurn } from '@/types/history';

describe('ConversationHistory', () => {
  beforeEach(async () => {
    await useHistory.persist.clearStorage();
    useHistory.setState({ turns: {}, orderDesc: [], promoted: {} });
  });

  it('shows placeholder when empty', () => {
    render(<ConversationHistory />);
    expect(screen.getByText('No conversation yet')).toBeInTheDocument();
  });

  it('renders turns in newest first order', () => {
    const turnA: ConversationTurn = {
      turnId: 'a',
      createdAt: 1,
      userText: 'Old',
      actions: [],
      agentText: 'A',
      phase: 'completed',
    };
    const turnB: ConversationTurn = {
      turnId: 'b',
      createdAt: 2,
      userText: 'New',
      actions: [],
      agentText: 'B',
      phase: 'completed',
    };
    useHistory.setState({
      turns: { a: turnA, b: turnB },
      orderDesc: ['b', 'a'],
      promoted: {},
    });
    render(<ConversationHistory />);
    const cards = screen.getAllByTestId('turn-card');
    expect(cards[0]).toHaveTextContent('New');
    expect(cards[1]).toHaveTextContent('Old');
  });
});
