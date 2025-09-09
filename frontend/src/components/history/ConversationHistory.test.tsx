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
    render(<ConversationHistory projectId={1} />);
    expect(screen.getByText('No conversation yet')).toBeInTheDocument();
  });

  it('renders turns in newest first order', () => {
    const turnA: ConversationTurn = {
      turnId: 'a',
      createdAt: 1,
      userText: 'Old',
      projectId: 1,
      actions: [],
      agentText: 'A',
      phase: 'completed',
    };
    const turnB: ConversationTurn = {
      turnId: 'b',
      createdAt: 2,
      userText: 'New',
      projectId: 1,
      actions: [],
      agentText: 'B',
      phase: 'completed',
    };
    useHistory.setState({
      turns: { a: turnA, b: turnB },
      orderDesc: ['b', 'a'],
      promoted: {},
    });
    render(<ConversationHistory projectId={1} />);
    const cards = screen.getAllByTestId('turn-card');
    expect(cards[0]).toHaveTextContent('New');
    expect(cards[1]).toHaveTextContent('Old');
  });

  it('filters turns by project', () => {
    const turnA: ConversationTurn = {
      turnId: 'a',
      createdAt: 1,
      userText: 'Project1',
      projectId: 1,
      actions: [],
      phase: 'completed',
    };
    const turnB: ConversationTurn = {
      turnId: 'b',
      createdAt: 2,
      userText: 'Project2',
      projectId: 2,
      actions: [],
      phase: 'completed',
    };
    useHistory.setState({
      turns: { a: turnA, b: turnB },
      orderDesc: ['b', 'a'],
      promoted: {},
    });
    render(<ConversationHistory projectId={1} />);
    expect(screen.getByText('Project1')).toBeInTheDocument();
    expect(screen.queryByText('Project2')).toBeNull();
  });
});
