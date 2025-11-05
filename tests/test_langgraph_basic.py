import pytest
from unittest.mock import Mock, AsyncMock, patch
from agents_v2.graph import build_agent_graph
from agents_v2.state import AgentState
from agents_v2.router import router_node
from agents_v2.backlog_agent import backlog_agent_node

class TestLangGraphBasic:
    """Tests basiques pour infrastructure LangGraph Phase 1."""
    
    @pytest.mark.asyncio
    async def test_build_graph_without_checkpointer(self):
        """Test que le graph se compile sans checkpointer."""
        graph = build_agent_graph(checkpointer=None)
        assert graph is not None
        # Basic structure validation
        assert hasattr(graph, 'ainvoke')
    
    @pytest.mark.asyncio 
    async def test_router_routes_to_backlog(self):
        """Test que le router route correctement vers backlog."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "créer un Epic pour mon projet",
            "next_agent": "",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            # Mock LLM response to route to backlog
            mock_response = Mock()
            mock_response.content = "backlog"
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router_node(initial_state)
            
            assert result["next_agent"] == "backlog"
            assert "messages" in result
    
    @pytest.mark.asyncio
    async def test_router_handles_invalid_routing(self):
        """Test fallback when router returns invalid agent."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user", 
            "objective": "test invalid routing",
            "next_agent": "",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            mock_response = Mock()
            mock_response.content = "invalid_agent_name"
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router_node(initial_state)
            
            # Should fallback to backlog
            assert result["next_agent"] == "backlog"
    
    @pytest.mark.asyncio
    async def test_backlog_agent_basic_execution(self):
        """Test que BacklogAgent s'exécute sans erreur."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "créer un Epic test",
            "next_agent": "backlog",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            # Mock LLM without tool calls
            mock_response = Mock()
            mock_response.content = "J'ai créé un Epic de test."
            mock_response.tool_calls = []  # No tools called
            mock_llm.return_value.bind_tools = Mock(return_value=mock_llm.return_value)
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await backlog_agent_node(initial_state)
            
            assert result["iteration"] == 1
            assert "error" not in result or result["error"] is None
            assert len(result["messages"]) >= 1
    
    @pytest.mark.asyncio
    async def test_graph_end_to_end_mock(self):
        """Test exécution complète du graph avec mocks."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "créer un Epic pour e-commerce",
            "next_agent": "",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            # Mock router response
            router_response = Mock()
            router_response.content = "backlog"
            
            # Mock backlog agent response  
            backlog_response = Mock()
            backlog_response.content = "Epic créé avec succès"
            backlog_response.tool_calls = []
            
            mock_llm.return_value.ainvoke = AsyncMock(side_effect=[
                router_response,  # Router call
                backlog_response  # Backlog agent call
            ])
            mock_llm.return_value.bind_tools = Mock(return_value=mock_llm.return_value)
            
            graph = build_agent_graph(checkpointer=None)
            result = await graph.ainvoke(initial_state)
            
            assert result is not None
            assert result["iteration"] >= 1
            assert result["next_agent"] == "backlog"

# TODO: Phase 2 tests
# - Test avec vrai Redis checkpointer
# - Test tool calls execution
# - Test error handling
# - Test avec plusieurs agents