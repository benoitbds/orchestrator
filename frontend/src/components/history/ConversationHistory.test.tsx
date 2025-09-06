import { render, screen } from '@testing-library/react';
import { ConversationHistory } from './ConversationHistory';
import type { ConversationTurn } from '@/types/conversation';

describe('ConversationHistory', () => {
  it('sorts turns in descending order', () => {
    const turns: ConversationTurn[] = [
      {
        id: '1',
        createdAt: '2024-01-01T00:00:00Z',
        userText: 'Old',
        actions: [],
        agentText: 'A',
        status: 'completed',
      },
      {
        id: '2',
        createdAt: '2024-01-02T00:00:00Z',
        userText: 'New',
        actions: [],
        agentText: 'B',
        status: 'completed',
      },
    ];

    render(<ConversationHistory turns={turns} />);
    const cards = screen.getAllByTestId('turn-card');
    expect(cards[0]).toHaveTextContent('New');
    expect(cards[1]).toHaveTextContent('Old');
  });
});
