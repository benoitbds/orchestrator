from langchain_core.tools import tool
from orchestrator import crud
from orchestrator.models import USCreate, FeatureCreate, EpicCreate, UCCreate
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
import logging
import re
import json

logger = logging.getLogger(__name__)

GENERIC_RX = re.compile(r"^generated\s+(us|feature|epic)\s+#\d+$", re.I)

@tool
async def create_backlog_item_tool(
    project_id: int,
    item_type: str,
    title: str,
    description: str,
    parent_id: int | None = None
) -> dict:
    """Créer un nouvel item backlog (Epic/Feature/US).
    
    Args:
        project_id: ID du projet
        item_type: Type d'item (Epic, Feature, US)
        title: Titre de l'item
        description: Description détaillée
        parent_id: ID du parent si hiérarchie
        
    Returns:
        dict avec id, title, type de l'item créé
    """
    try:
        logger.info(f"Creating {item_type} item: {title} in project {project_id}")
        
        item_type_normalized = item_type.upper()
        if item_type_normalized not in ['EPIC', 'FEATURE', 'US', 'UC', 'CAPABILITY']:
            return {"error": f"Invalid item type: {item_type}", "success": False}
        
        if GENERIC_RX.match(title):
            logger.warning(f"Rejecting generic title: {title}")
            return {"error": f"Generic titles not allowed: {title}", "success": False}
        
        if item_type_normalized == "US":
            item_create = USCreate(
                project_id=project_id,
                title=title,
                description=description,
                parent_id=parent_id,
                ia_review_status="pending",
                status="Todo"
            )
        elif item_type_normalized == "FEATURE":
            item_create = FeatureCreate(
                project_id=project_id,
                title=title,
                description=description,
                parent_id=parent_id,
                ia_review_status="pending"
            )
        elif item_type_normalized == "EPIC":
            item_create = EpicCreate(
                project_id=project_id,
                title=title,
                description=description,
                parent_id=parent_id,
                ia_review_status="pending",
                state="Funnel"
            )
        else:
            return {"error": f"Unsupported item type: {item_type_normalized}", "success": False}
        
        new_item = crud.create_item(item_create)
        
        result = {
            "id": new_item.id,
            "title": new_item.title,
            "type": new_item.type,
            "project_id": new_item.project_id,
            "parent_id": new_item.parent_id,
            "success": True
        }
        
        logger.info(f"Created item: {result}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to create item: {e}")
        return {"error": str(e), "success": False}

@tool 
async def update_backlog_item_tool(
    item_id: int,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None
) -> dict:
    """Mettre à jour un item backlog existant.
    
    Args:
        item_id: ID de l'item à modifier
        title: Nouveau titre (optionnel)
        description: Nouvelle description (optionnelle)  
        status: Nouveau statut (optionnel)
        
    Returns:
        dict avec les informations de l'item mis à jour
    """
    try:
        logger.info(f"Updating item {item_id}")
        
        # Mock implementation 
        result = {
            "id": item_id,
            "title": title or "Updated Item",
            "description": description,
            "status": status,
            "updated": True
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to update item {item_id}: {e}")
        return {"error": str(e), "success": False}

@tool
async def get_backlog_item_tool(
    item_id: int
) -> dict:
    """Récupérer un item backlog par son ID.
    
    Args:
        item_id: ID de l'item à récupérer
        
    Returns:
        dict avec les informations de l'item
    """
    try:
        logger.info(f"Getting item {item_id}")
        
        item = crud.get_item(item_id)
        if not item:
            return {"error": f"Item {item_id} not found", "success": False}
        
        result = {
            "id": item.id,
            "title": item.title,
            "type": item.type,
            "description": item.description or "",
            "project_id": item.project_id,
            "parent_id": item.parent_id
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to get item {item_id}: {e}")
        return {"error": str(e), "success": False}

@tool
async def list_backlog_items(
    project_id: int,
    item_type: str | None = None,
    limit: int = 50
) -> dict:
    """Lister items backlog d'un projet avec filtres.
    
    Args:
        project_id: ID du projet
        item_type: Type d'item optionnel (Epic, Feature, US)
        limit: Nombre max d'items à retourner
        
    Returns:
        Dict avec items (list) et metadata
    """
    try:
        logger.info(f"Listing backlog items for project {project_id}, type: {item_type}")
        
        # Mock implementation
        items = [
            {
                "id": 1,
                "title": "User Authentication Epic",
                "type": "Epic",
                "project_id": project_id,
                "parent_id": None
            },
            {
                "id": 2,
                "title": "Login Feature",
                "type": "Feature", 
                "project_id": project_id,
                "parent_id": 1
            }
        ]
        
        # Filter by type if specified
        if item_type:
            items = [item for item in items if item["type"] == item_type]
        
        return {
            "project_id": project_id,
            "items": items[:limit],
            "total_count": len(items),
            "filter_type": item_type
        }
        
    except Exception as e:
        logger.error(f"Failed to list items: {e}")
        return {"error": str(e), "items": []}

@tool
async def delete_backlog_item(item_id: int, explicit_confirm: bool = False) -> dict:
    """Supprimer un item backlog et ses descendants.
    
    ATTENTION: Suppression cascade des items enfants !
    
    Args:
        item_id: ID de l'item à supprimer
        explicit_confirm: Confirmation explicite requise
        
    Returns:
        Dict avec items_deleted (count) et confirmation
    """
    try:
        logger.info(f"Deleting item {item_id}, confirmed: {explicit_confirm}")
        
        if not explicit_confirm:
            return {
                "error": "Confirmation required for delete operation",
                "item_id": item_id,
                "deleted": False,
                "required_param": "explicit_confirm=True"
            }
        
        # Mock implementation
        result = {
            "item_id": item_id,
            "deleted": True,
            "deleted_count": 3,  # Item + 2 descendants
            "message": f"Item {item_id} and 2 descendants deleted"
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to delete item {item_id}: {e}")
        return {"error": str(e), "deleted": False}

@tool
async def move_backlog_item(
    item_id: int,
    new_parent_id: int | None
) -> dict:
    """Déplacer un item vers un nouveau parent (re-parenting).
    
    Args:
        item_id: ID de l'item à déplacer
        new_parent_id: Nouveau parent (None = racine)
        
    Returns:
        Dict avec confirmation et nouvelle hiérarchie
    """
    try:
        logger.info(f"Moving item {item_id} to parent {new_parent_id}")
        
        # Mock implementation
        result = {
            "item_id": item_id,
            "old_parent_id": 5,
            "new_parent_id": new_parent_id,
            "moved": True,
            "hierarchy_valid": True
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to move item {item_id}: {e}")
        return {"error": str(e), "moved": False}

@tool
async def summarize_project_backlog(project_id: int) -> dict:
    """Résumer l'arbre backlog complet d'un projet.
    
    Args:
        project_id: ID du projet
        
    Returns:
        Dict avec compteurs (epics, features, US) et arbre hiérarchique
    """
    try:
        logger.info(f"Summarizing backlog for project {project_id}")
        
        # Mock implementation
        result = {
            "project_id": project_id,
            "summary": "Backlog contains 2 Epics, 5 Features, 12 User Stories",
            "counts": {
                "epics": 2,
                "features": 5,
                "user_stories": 12,
                "total": 19
            },
            "tree_depth": 3,
            "completion_rate": 0.35  # 35% done
        }
        
        return result
        
    except Exception as e:
        logger.error(f"Failed to summarize project {project_id}: {e}")
        return {"error": str(e), "counts": {}}

@tool
async def bulk_create_features(
    project_id: int,
    epic_id: int,
    feature_titles: list[str]
) -> dict:
    """Créer plusieurs Features en masse sous un Epic.
    
    Args:
        project_id: ID du projet
        epic_id: Epic parent
        feature_titles: Liste de titres de Features
        
    Returns:
        Dict avec features_created (IDs)
    """
    try:
        logger.info(f"Bulk creating {len(feature_titles)} features under epic {epic_id}")
        
        # Mock implementation
        created_ids = []
        for i, title in enumerate(feature_titles):
            feature_id = 200 + i  # Mock IDs
            created_ids.append(feature_id)
            logger.info(f"Created Feature '{title}' with ID {feature_id}")
        
        return {
            "project_id": project_id,
            "epic_id": epic_id,
            "features_created": created_ids,
            "count": len(created_ids),
            "titles": feature_titles
        }
        
    except Exception as e:
        logger.error(f"Failed to bulk create features: {e}")
        return {"error": str(e), "features_created": []}

@tool
async def generate_children_items(
    project_id: int,
    parent_id: int,
    target_type: str,
    count: int = 5
) -> dict:
    """Générer items enfants sous un parent (Epic→Features, Features→US, US→UC).
    
    Args:
        project_id: ID du projet
        parent_id: ID de l'item parent
        target_type: Type d'items à créer (Feature, US, UC)
        count: Nombre d'items à générer
        
    Returns:
        Dict avec children_created (IDs) et descriptions
    """
    try:
        logger.info(f"Generating {count} {target_type} items under parent {parent_id}")
        
        parent = crud.get_item(parent_id)
        if not parent:
            return {"error": f"Parent item {parent_id} not found", "children_created": []}
        
        parent_title = parent.title
        parent_type = parent.type
        parent_description = parent.description or ""
        
        # Validate parent-child compatibility
        if target_type.upper() == "UC":
            if parent_type != "US":
                return {
                    "error": f"Use Cases must be created under a US, not {parent_type}",
                    "children_created": [],
                    "validation_failed": True
                }
        elif target_type.upper() == "US":
            if parent_type not in ["Feature", "Capability"]:
                return {
                    "error": f"User Stories must be created under a Feature or Capability, not {parent_type}",
                    "children_created": [],
                    "validation_failed": True
                }
        elif target_type.upper() == "FEATURE":
            if parent_type not in ["Epic", "Capability"]:
                return {
                    "error": f"Features must be created under an Epic or Capability, not {parent_type}",
                    "children_created": [],
                    "validation_failed": True
                }
        
        logger.info(f"Parent context: {parent_type} '{parent_title}'")
        
        target_type_normalized = target_type.upper()
        if target_type_normalized not in ['US', 'FEATURE', 'EPIC', 'UC', 'CAPABILITY']:
            target_type_normalized = 'US'
        
        # Generate UC-specific prompt with steps/flows/conditions
        if target_type_normalized == 'UC':
            prompt = f"""You are creating Use Cases (UC) under the parent User Story:
- User Story ID: {parent_id}
- User Story Title: "{parent_title}"
- User Story Description: {parent_description}

Return {count} Use Cases as strict JSON array:
[
  {{
    "title": "<concise, domain-specific use case name>",
    "description": "<detailed description of the use case>",
    "preconditions": "<what must be true before this use case starts>",
    "postconditions": "<what will be true after successful completion>",
    "main_flow": [
      "1. Actor does X",
      "2. System responds with Y",
      "3. ..."
    ],
    "alternative_flows": [
      "If condition A: do B",
      "..."
    ],
    "acceptance_criteria": [
      "Given ... When ... Then ...",
      "..."
    ],
    "priority": "Must",
    "story_points": 3
  }}
]

IMPORTANT:
- Avoid generic titles like "Generated UC #1"
- Use the User Story title as context
- Include detailed step-by-step flows
- Define clear pre/post-conditions
- Return ONLY valid JSON array, no markdown"""
        else:
            prompt = f"""You are creating {target_type_normalized} items under the parent {parent_type}:
- Parent ID: {parent_id}
- Parent Title: "{parent_title}"
- Parent Description: {parent_description}

Return {count} {target_type_normalized} items as strict JSON array:
[
  {{
    "title": "<concise, domain-specific title>",
    "description": "<what/why>",
    "acceptance_criteria": [
      "Given ... When ... Then ...",
      "..."
    ],
    "priority": "Must",
    "story_points": 3
  }}
]

IMPORTANT:
- Avoid generic titles like "Generated {target_type_normalized} #1"
- Use the parent title as context for domain-specific names
- Each item should be distinct and focused
- Return ONLY valid JSON array, no markdown"""
        
        llm = ChatOpenAI(model="gpt-4o", temperature=0.7)
        messages = [
            SystemMessage(content="You are a product backlog expert. Generate high-quality, domain-specific backlog items."),
            HumanMessage(content=prompt)
        ]
        
        response = await llm.ainvoke(messages)
        content = response.content.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()
        
        try:
            items_data = json.loads(content)
        except json.JSONDecodeError as je:
            logger.error(f"Failed to parse LLM response as JSON: {je}")
            return {"error": "Failed to parse generated items", "children_created": []}
        
        if not isinstance(items_data, list):
            items_data = [items_data]
        
        children_created = []
        for i, item_data in enumerate(items_data[:count]):
            title = item_data.get("title", f"Generated {target_type_normalized} #{i+1}")
            
            if GENERIC_RX.match(title):
                logger.warning(f"Rejecting generic title: {title}")
                title = f"{parent_title} - {target_type_normalized} #{i+1}"
            
            description = item_data.get("description", "")
            acceptance_criteria = item_data.get("acceptance_criteria", [])
            priority = item_data.get("priority", "Should")
            story_points = item_data.get("story_points", 3)
            
            # Handle UC-specific fields
            if target_type_normalized == "UC":
                preconditions = item_data.get("preconditions", "")
                postconditions = item_data.get("postconditions", "")
                main_flow = item_data.get("main_flow", [])
                alternative_flows = item_data.get("alternative_flows", [])
                
                main_flow_text = "\n".join(main_flow)
                alt_flow_text = "\n".join(alternative_flows) if alternative_flows else "None"
                acceptance_text = "\n".join([f"- {criterion}" for criterion in acceptance_criteria])
                
                full_description = f"{description}\n\nPreconditions:\n{preconditions}\n\nMain Flow:\n{main_flow_text}\n\nAlternative Flows:\n{alt_flow_text}\n\nPostconditions:\n{postconditions}\n\nAcceptance Criteria:\n{acceptance_text}"
            else:
                acceptance_text = "\n".join([f"- {criterion}" for criterion in acceptance_criteria])
                full_description = f"{description}\n\nAcceptance Criteria:\n{acceptance_text}"
            
            try:
                if target_type_normalized == "US":
                    item_create = USCreate(
                        project_id=project_id,
                        title=title,
                        description=full_description,
                        parent_id=parent_id,
                        ia_review_status="pending",
                        story_points=story_points,
                        status="Todo"
                    )
                elif target_type_normalized == "FEATURE":
                    item_create = FeatureCreate(
                        project_id=project_id,
                        title=title,
                        description=full_description,
                        parent_id=parent_id,
                        ia_review_status="pending"
                    )
                elif target_type_normalized == "EPIC":
                    item_create = EpicCreate(
                        project_id=project_id,
                        title=title,
                        description=full_description,
                        parent_id=parent_id,
                        ia_review_status="pending",
                        state="Funnel"
                    )
                elif target_type_normalized == "UC":
                    item_create = UCCreate(
                        project_id=project_id,
                        title=title,
                        description=full_description,
                        parent_id=parent_id,
                        ia_review_status="pending",
                        story_points=story_points,
                        status="Todo"
                    )
                else:
                    logger.error(f"Unsupported type: {target_type_normalized}")
                    continue
                
                new_item = crud.create_item(item_create)
                
                children_created.append({
                    "id": new_item.id,
                    "title": new_item.title,
                    "type": new_item.type,
                    "parent_id": new_item.parent_id,
                    "description": new_item.description,
                    "priority": priority,
                    "story_points": story_points
                })
                
                logger.info(f"Created {target_type_normalized}: {title} (ID: {new_item.id})")
                
            except Exception as create_error:
                logger.error(f"Failed to create item '{title}': {create_error}")
                continue
        
        return {
            "project_id": project_id,
            "parent_id": parent_id,
            "parent_title": parent_title,
            "target_type": target_type_normalized,
            "children_created": children_created,
            "count": len(children_created),
            "generation_method": "AI-assisted"
        }
        
    except Exception as e:
        logger.error(f"Failed to generate children items: {e}")
        return {"error": str(e), "children_created": []}