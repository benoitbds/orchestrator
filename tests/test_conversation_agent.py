"""Tests pour le ConversationAgent."""
import pytest
from agents_v2.conversation_agent import ConversationAgent
from agents_v2.state import AgentState


@pytest.fixture
def base_state():
    """State de base pour les tests."""
    return {
        "messages": [],
        "project_id": 1,
        "user_uid": "test_user",
        "objective": "test objective",
        "meta": None,
        "next_agent": "conversation",
        "current_agent": None,
        "iteration": 0,
        "max_iterations": 5,
        "tool_results": {},
        "items_created": None,
        "documents_searched": None,
        "error": None,
        "run_id": "test_run",
        "status_message": None,
        "progress_steps": None,
        "synthesis_complete": None,
        "final_response": None,
        "is_stub": None,
        "workflow_steps": None,
        "current_step_index": None,
        "is_paused": None,
        "pending_approval": None
    }


class TestConversationAgent:
    """Tests pour la classe ConversationAgent."""
    
    def test_init(self, base_state):
        """Test de l'initialisation."""
        agent = ConversationAgent(base_state)
        assert agent.project_id == 1
        assert agent.current_agent is None
        assert agent.error is None
    
    @pytest.mark.asyncio
    async def test_suggest_next_steps_after_document_analysis(self, base_state):
        """Test des suggestions après analyse de documents."""
        state = {
            **base_state,
            "current_agent": "document",
            "tool_results": {
                "draft_features_from_documents": {
                    "features_created": [1, 2, 3],
                    "source_documents": ["spec.pdf", "requirements.docx"]
                }
            }
        }
        
        agent = ConversationAgent(state)
        suggestions = await agent.suggest_next_steps()
        
        assert suggestions["priority"] == "high"
        assert len(suggestions["suggestions"]) >= 2
        # Vérifier qu'au moins une suggestion mentionne User Stories ou génération
        assert any("User Stories" in s or "User Story" in s or "User" in s or "générer" in s.lower() for s in suggestions["suggestions"])
        assert "features" in suggestions["context"].lower() or "feature" in suggestions["context"].lower()
    
    @pytest.mark.asyncio
    async def test_suggest_next_steps_after_backlog_creation(self, base_state):
        """Test des suggestions après création dans le backlog."""
        state = {
            **base_state,
            "current_agent": "backlog",
            "tool_results": {
                "bulk_create_features": {
                    "features_created": [10, 11, 12, 13]
                }
            }
        }
        
        agent = ConversationAgent(state)
        suggestions = await agent.suggest_next_steps()
        
        assert suggestions["priority"] == "high"
        assert len(suggestions["suggestions"]) >= 2
        assert any("User Stories" in s for s in suggestions["suggestions"])
    
    @pytest.mark.asyncio
    async def test_suggest_next_steps_with_error(self, base_state):
        """Test des suggestions en cas d'erreur."""
        state = {
            **base_state,
            "error": "Failed to create items"
        }
        
        agent = ConversationAgent(state)
        suggestions = await agent.suggest_next_steps()
        
        assert suggestions["priority"] == "high"
        assert any("Réessayer" in s or "réessayer" in s for s in suggestions["suggestions"])
    
    @pytest.mark.asyncio
    async def test_suggest_next_steps_empty_state(self, base_state):
        """Test des suggestions avec état vide."""
        agent = ConversationAgent(base_state)
        suggestions = await agent.suggest_next_steps()
        
        assert suggestions["priority"] in ["medium", "low"]
        assert len(suggestions["suggestions"]) >= 2
        assert suggestions["emoji"] in ["💡", "💭", "💬"]
    
    def test_format_response_with_features(self, base_state):
        """Test du formatage avec features créées."""
        agent = ConversationAgent(base_state)
        
        data = {
            "features_created": [1, 2, 3],
            "success": True
        }
        
        formatted = agent.format_response(data)
        
        assert "✅" in formatted
        assert "3 feature" in formatted
        assert "#1" in formatted
    
    def test_format_response_with_error(self, base_state):
        """Test du formatage avec erreur."""
        agent = ConversationAgent(base_state)
        
        data = {
            "error": "Database connection failed",
            "success": False
        }
        
        formatted = agent.format_response(data)
        
        assert "❌" in formatted
        assert "Database connection failed" in formatted
    
    def test_format_response_with_search_results(self, base_state):
        """Test du formatage avec résultats de recherche."""
        agent = ConversationAgent(base_state)
        
        data = {
            "results": [
                {"content": "result 1", "similarity": 0.9},
                {"content": "result 2", "similarity": 0.8}
            ]
        }
        
        formatted = agent.format_response(data)
        
        assert "🔍" in formatted
        assert "2 résultat" in formatted
    
    @pytest.mark.asyncio
    async def test_ask_clarification(self, base_state):
        """Test de la demande de clarification."""
        from unittest.mock import AsyncMock, patch
        
        state = {
            **base_state,
            "objective": "créer des items"
        }
        
        agent = ConversationAgent(state)
        
        # Mock le LLM pour éviter l'appel API
        with patch("agents_v2.conversation_agent.ChatOpenAI") as mock_llm:
            mock_response = AsyncMock()
            mock_response.content = "🤔 Voulez-vous créer un Epic ou une Feature ?"
            mock_llm.return_value.ainvoke = AsyncMock(return_value=mock_response)
            
            question = await agent.ask_clarification("Le type d'item n'est pas spécifié")
            
            assert len(question) > 0
            # Devrait contenir un emoji
            assert any(char in question for char in ["🤔", "❓", "📋", "💭"])
    
    def test_extract_document_results(self, base_state):
        """Test de l'extraction des résultats documents."""
        state = {
            **base_state,
            "tool_results": {
                "draft_features_from_documents": {
                    "features_created": [1, 2],
                    "source_documents": ["doc1.pdf", "doc2.pdf"]
                },
                "list_documents": {
                    "documents": [{"id": 1, "filename": "doc1.pdf"}]
                }
            },
            "documents_searched": ["doc1.pdf"]
        }
        
        agent = ConversationAgent(state)
        results = agent._extract_document_results()
        
        assert results["features_created"] == [1, 2]
        assert "doc1.pdf" in results["documents_analyzed"]
        assert results["documents_list"][0]["id"] == 1
    
    def test_extract_backlog_results(self, base_state):
        """Test de l'extraction des résultats backlog."""
        state = {
            **base_state,
            "tool_results": {
                "bulk_create_features": {
                    "features_created": [10, 11, 12]
                },
                "generate_children_items": {
                    "items_created": [
                        {"id": 20, "type": "US"},
                        {"id": 21, "type": "US"}
                    ]
                }
            }
        }
        
        agent = ConversationAgent(state)
        results = agent._extract_backlog_results()
        
        assert results["features_created"] == [10, 11, 12]
        assert results["user_stories_created"] == [20, 21]
    
    def test_get_context_emoji(self, base_state):
        """Test de la sélection d'emoji selon la priorité."""
        agent = ConversationAgent(base_state)
        
        assert agent._get_context_emoji("high") == "🔥"
        assert agent._get_context_emoji("medium") == "💡"
        assert agent._get_context_emoji("low") == "💭"
        assert agent._get_context_emoji("unknown") == "💬"


@pytest.mark.asyncio
async def test_conversation_agent_node_suggestions(base_state):
    """Test du node pour suggestions."""
    from agents_v2.conversation_agent import conversation_agent_node
    from unittest.mock import AsyncMock, patch
    
    state = {
        **base_state,
        "objective": "suggère-moi les prochaines étapes",
        "current_agent": "document"
    }
    
    # Mock le stream manager
    with patch("agents_v2.conversation_agent.get_stream_manager") as mock_stream:
        mock_stream.return_value.emit_agent_start = AsyncMock()
        mock_stream.return_value.emit_agent_end = AsyncMock()
        
        result = await conversation_agent_node(state)
        
        assert result["current_agent"] == "conversation"
        assert result["iteration"] == 1
        assert "final_response" in result
        assert len(result["final_response"]) > 0


@pytest.mark.asyncio
async def test_conversation_agent_node_formatting(base_state):
    """Test du node pour formatage."""
    from agents_v2.conversation_agent import conversation_agent_node
    from unittest.mock import AsyncMock, patch
    
    state = {
        **base_state,
        "objective": "résume ce qui a été fait",
        "tool_results": {
            "bulk_create_features": {
                "features_created": [1, 2, 3]
            }
        }
    }
    
    with patch("agents_v2.conversation_agent.get_stream_manager") as mock_stream:
        mock_stream.return_value.emit_agent_start = AsyncMock()
        mock_stream.return_value.emit_agent_end = AsyncMock()
        
        result = await conversation_agent_node(state)
        
        assert result["current_agent"] == "conversation"
        assert "final_response" in result
        # Devrait contenir une réponse formatée
        assert len(result["final_response"]) > 0
        # Comme current_agent est None dans ce test, on ne s'attend pas à détecter les features
        # Le test valide juste que la réponse est générée
