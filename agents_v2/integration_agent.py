"""Integration agent - Handles external API calls and webhooks (future)."""
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from .state import AgentState
import logging

logger = logging.getLogger(__name__)

async def integration_agent_node(state: AgentState) -> AgentState:
    """Specialized agent for external integrations.
    
    Future capabilities (Phase 3+):
    - Jira API integration (create issues, sync status)
    - Confluence API (create/update documentation)
    - Slack notifications (progress updates, alerts)
    - Generic HTTP API calls (POST/GET to external services)
    - Webhook receivers (GitHub, GitLab, etc.)
    - Microsoft Teams integration
    - Asana/Monday.com sync
    - Email notifications
    
    Phase 2A: Stub only, returns placeholder message
    """
    logger.info(f"IntegrationAgent called with objective: {state['objective']}")
    logger.warning("IntegrationAgent is not yet implemented - returning stub response")
    
    try:
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
        
        # Analyze if this is an integration request
        objective = state["objective"].lower()
        integration_keywords = ["jira", "slack", "confluence", "teams", "webhook", "api", "export", "sync"]
        is_integration_request = any(keyword in objective for keyword in integration_keywords)
        
        if is_integration_request:
            message = f"""
🔧 **IntegrationAgent** détecté

L'objectif "{state['objective']}" semble nécessiter des intégrations externes.

**Capacités futures** (Phase 3+):
- 🔗 Jira API (création tickets, sync status)
- 💬 Slack/Teams notifications
- 📝 Confluence documentation
- 🔀 Generic HTTP APIs
- 📨 Email notifications
- ⚡ Webhooks (GitHub, GitLab)

**Status actuel**: Stub - Implementation prévue Phase 3

**Suggestion**: Pour l'instant, utilise les autres agents pour les tâches internes au système.
"""
        else:
            message = f"""
⚠️ **IntegrationAgent** appelé incorrectement

L'objectif "{state['objective']}" ne semble pas nécessiter d'intégrations externes.

**Suggestion**: Retourne au RouterAgent pour redirection vers l'agent approprié:
- **BacklogAgent**: Gestion items backlog
- **DocumentAgent**: Recherche et analyse documents  
- **WriterAgent**: Formatage et synthèse
- **PlannerAgent**: Décomposition tâches complexes
"""
        
        messages = [
            SystemMessage(content="Integration agent - Phase 2A stub implementation"),
            HumanMessage(content=state["objective"])
        ]
        
        # Create a mock response for now
        from langchain_core.messages import AIMessage
        response = AIMessage(content=message)
        
        return {
            **state,
            "messages": state["messages"] + [response],
            "current_agent": "integration",
            "next_agent": "end",
            "iteration": state["iteration"] + 1,
            "status_message": "⚠️ IntegrationAgent (stub - Phase 3)",
            "error": "Integration capabilities not yet implemented",
            "is_stub": True
        }
        
    except Exception as e:
        logger.error(f"IntegrationAgent stub failed: {e}")
        return {
            **state,
            "iteration": state["iteration"] + 1,
            "error": f"IntegrationAgent stub error: {str(e)}",
            "current_agent": "integration",
            "next_agent": "end"
        }

# TODO Phase 3: Real implementation with tools
# @tool
# async def create_jira_issue(summary: str, description: str, project_key: str) -> dict:
#     """Create a Jira issue from backlog item."""
#     pass
#
# @tool 
# async def send_slack_notification(channel: str, message: str) -> dict:
#     """Send notification to Slack channel."""
#     pass
#
# @tool
# async def sync_to_confluence(page_id: str, content: str) -> dict:
#     """Update Confluence page with generated content."""
#     pass