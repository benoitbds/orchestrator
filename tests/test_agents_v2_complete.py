"""Tests for Phase 2A complete multi-agent system."""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from agents_v2.graph import build_agent_graph
from agents_v2.state import AgentState
from agents_v2.router import router_node
from agents_v2.backlog_agent import backlog_agent_node
from agents_v2.document_agent import document_agent_node
from agents_v2.planner_agent import planner_agent_node
from agents_v2.writer_agent import writer_agent_node
from agents_v2.integration_agent import integration_agent_node

class TestPhase2AAgents:
    """Test suite for complete 6-agent system."""
    
    @pytest.mark.asyncio
    async def test_graph_builds_with_6_agents(self):
        """Test that graph builds successfully with all 6 agents."""
        graph = build_agent_graph(checkpointer=None)
        assert graph is not None
        # Graph should be compiled and ready
        assert hasattr(graph, 'ainvoke')

    @pytest.mark.asyncio
    async def test_router_routes_to_backlog(self):
        """Test router routes backlog requests correctly."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "créer un Epic e-commerce",
            "next_agent": "",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            mock_response = Mock()
            mock_response.content = "backlog"
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router_node(initial_state)
            
            assert result["next_agent"] == "backlog"
            assert "messages" in result

    @pytest.mark.asyncio 
    async def test_router_routes_to_document(self):
        """Test router routes document requests correctly."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "analyser les documents et extraire des features",
            "next_agent": "",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            mock_response = Mock()
            mock_response.content = "document"
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router_node(initial_state)
            
            assert result["next_agent"] == "document"

    @pytest.mark.asyncio
    async def test_router_routes_to_planner(self):
        """Test router routes complex planning requests."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "planifier le développement complet d'une app mobile",
            "next_agent": "",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            mock_response = Mock()
            mock_response.content = "planner"
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router_node(initial_state)
            
            assert result["next_agent"] == "planner"

    @pytest.mark.asyncio
    async def test_backlog_agent_with_all_tools(self):
        """Test BacklogAgent with complete tool suite (9 tools)."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "lister tous les items Epic du projet",
            "next_agent": "backlog",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            # Mock LLM without tool calls for simple test
            mock_response = Mock()
            mock_response.content = "Voici les Epic items du projet."
            mock_response.tool_calls = []
            mock_llm.return_value.bind_tools = Mock(return_value=mock_llm.return_value)
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await backlog_agent_node(initial_state)
            
            assert result["iteration"] == 1
            assert result["current_agent"] == "backlog"
            assert len(result["messages"]) >= 1

    @pytest.mark.asyncio
    async def test_document_agent_with_5_tools(self):
        """Test DocumentAgent with complete tool suite."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "rechercher les spécifications d'authentification",
            "next_agent": "document",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            mock_response = Mock()
            mock_response.content = "Voici les spécifications d'authentification trouvées."
            mock_response.tool_calls = []
            mock_llm.return_value.bind_tools = Mock(return_value=mock_llm.return_value)
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await document_agent_node(initial_state)
            
            assert result["iteration"] == 1
            assert result["current_agent"] == "document"

    @pytest.mark.asyncio
    async def test_planner_agent_creates_steps(self):
        """Test PlannerAgent creates structured steps."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "créer un backlog complet pour app e-commerce",
            "next_agent": "planner",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            mock_response = Mock()
            mock_response.content = """Step 1: Créer Epic e-commerce → Agent: backlog
Step 2: Analyser documents → Agent: document
Step 3: Générer Features → Agent: backlog"""
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await planner_agent_node(initial_state)
            
            assert result["current_agent"] == "planner"
            assert "progress_steps" in result
            assert len(result["progress_steps"]) >= 3
            assert result["next_agent"] in ["backlog", "document", "writer"]

    @pytest.mark.asyncio
    async def test_writer_agent_synthesis(self):
        """Test WriterAgent formats and synthesizes results."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "synthétiser les résultats de la session",
            "next_agent": "writer",
            "iteration": 2,
            "max_iterations": 10,
            "tool_results": {
                "create_backlog_item": {"id": 123, "title": "Epic Test"},
                "search_documents": {"results": ["doc1.pdf", "doc2.docx"]}
            },
            "error": None
        }
        
        with patch('langchain_openai.ChatOpenAI') as mock_llm:
            mock_response = Mock()
            mock_response.content = """## ✅ Résumé d'exécution
Epic créé avec succès et documents analysés.

## 📊 Résultats détaillés
- Items créés: 1 Epic (#123)
- Documents consultés: 2 docs"""
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await writer_agent_node(initial_state)
            
            assert result["current_agent"] == "writer"
            assert result["next_agent"] == "end"
            assert result["synthesis_complete"] == True
            assert "final_response" in result

    @pytest.mark.asyncio
    async def test_integration_agent_stub(self):
        """Test IntegrationAgent returns stub response."""
        initial_state: AgentState = {
            "messages": [],
            "project_id": 1,
            "user_uid": "test_user",
            "objective": "synchroniser avec Jira",
            "next_agent": "integration",
            "iteration": 0,
            "max_iterations": 10,
            "tool_results": {},
            "error": None
        }
        
        result = await integration_agent_node(initial_state)
        
        assert result["current_agent"] == "integration"
        assert result["is_stub"] == True
        assert "error" in result
        assert "not yet implemented" in result["error"]

    @pytest.mark.asyncio
    async def test_router_handles_invalid_routing(self):
        """Test router fallback for invalid agent names."""
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
            mock_response.content = "nonexistent_agent"
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            result = await router_node(initial_state)
            
            # Should fallback to backlog
            assert result["next_agent"] == "backlog"

# TODO Phase 2B: Add integration tests with real Redis
# TODO Phase 2B: Add tool execution tests with real CRUD calls  
# TODO Phase 2C: Add multi-step workflow tests
# TODO Phase 2C: Add error recovery and retry tests

class TestToolIntegration:
    """Test tool execution and integration."""
    
    @pytest.mark.asyncio
    async def test_backlog_tools_importable(self):
        """Test all backlog tools can be imported."""
        from agents_v2.tools.backlog_tools import (
            create_backlog_item_tool,
            update_backlog_item_tool,
            get_backlog_item_tool,
            list_backlog_items,
            delete_backlog_item,
            move_backlog_item,
            summarize_project_backlog,
            bulk_create_features,
            generate_children_items
        )
        
        # All tools should be LangChain tools
        assert hasattr(create_backlog_item_tool, 'ainvoke')
        assert hasattr(list_backlog_items, 'ainvoke')
        assert hasattr(delete_backlog_item, 'ainvoke')

    @pytest.mark.asyncio
    async def test_document_tools_importable(self):
        """Test all document tools can be imported."""
        from agents_v2.tools.document_tools import (
            search_documents,
            list_documents,
            get_document_content,
            draft_features_from_documents,
            analyze_document_structure
        )
        
        # All tools should be LangChain tools
        assert hasattr(search_documents, 'ainvoke')
        assert hasattr(draft_features_from_documents, 'ainvoke')
        assert hasattr(analyze_document_structure, 'ainvoke')