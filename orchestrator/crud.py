# orchestrator/crud.py
import sqlite3
from typing import List, Optional
from .models import (
    Project,
    ProjectCreate,
    BacklogItem,
    BacklogItemCreate,
    BacklogItemUpdate,
    EpicOut,
    CapabilityOut,
    FeatureOut,
    USOut,
    UCOut,
)

DATABASE_URL = "orchestrator.db"

def create_item_from_row(row_dict: dict) -> BacklogItem:
    """Create the appropriate item type based on the 'type' field"""
    item_type = row_dict.get('type')
    
    # Clean up None values and set defaults based on type
    cleaned_dict = {k: v for k, v in row_dict.items() if v is not None}
    
    if item_type == 'Epic':
        # Set defaults for Epic-specific fields
        if 'state' not in cleaned_dict:
            cleaned_dict['state'] = 'Funnel'
        return EpicOut(**cleaned_dict)
    elif item_type == 'Capability':
        # Set defaults for Capability-specific fields  
        if 'state' not in cleaned_dict:
            cleaned_dict['state'] = 'Funnel'
        return CapabilityOut(**cleaned_dict)
    elif item_type == 'Feature':
        # Feature doesn't have state, so no special defaults needed
        return FeatureOut(**cleaned_dict)
    elif item_type == 'US':
        # Set defaults for US-specific fields
        if 'status' not in cleaned_dict:
            cleaned_dict['status'] = 'Todo'
        if 'invest_compliant' not in cleaned_dict:
            cleaned_dict['invest_compliant'] = False
        return USOut(**cleaned_dict)
    elif item_type == 'UC':
        # Set defaults for UC-specific fields
        if 'status' not in cleaned_dict:
            cleaned_dict['status'] = 'Todo'
        if 'invest_compliant' not in cleaned_dict:
            cleaned_dict['invest_compliant'] = False
        return UCOut(**cleaned_dict)
    else:
        # Fallback to Epic for unknown types
        if 'state' not in cleaned_dict:
            cleaned_dict['state'] = 'Funnel'
        return EpicOut(**cleaned_dict)

def get_db_connection():
    conn = sqlite3.connect(DATABASE_URL)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS projects ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT NOT NULL,"
        "description TEXT"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS backlog ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "project_id INTEGER,"
        "title TEXT NOT NULL,"
        "description TEXT,"
        "type TEXT CHECK(type IN ('Epic','Capability','Feature','US','UC')),"
        "parent_id INTEGER,"
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "updated_at DATETIME,"
        "FOREIGN KEY(parent_id) REFERENCES backlog(id) ON DELETE CASCADE,"
        "FOREIGN KEY(project_id) REFERENCES projects(id)"
        ")"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_backlog_parent ON backlog(parent_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_backlog_project ON backlog(project_id)")
    # Ensure updated_at column exists (for backward compatibility)
    try:
        conn.execute("ALTER TABLE backlog ADD COLUMN updated_at DATETIME")
    except sqlite3.OperationalError:
        pass
    
    # Add new columns for enhanced backlog items
    new_columns = [
        ("state", "TEXT"),
        ("benefit_hypothesis", "TEXT"),
        ("leading_indicators", "TEXT"),
        ("mvp_definition", "TEXT"),
        ("wsjf", "REAL"),
        ("acceptance_criteria", "TEXT"),
        ("story_points", "INTEGER"),
        ("program_increment", "TEXT"),
        ("iteration", "TEXT"),
        ("owner", "TEXT"),
        ("invest_compliant", "BOOLEAN DEFAULT 0"),
        ("status", "TEXT")
    ]
    
    for column_name, column_type in new_columns:
        try:
            conn.execute(f"ALTER TABLE backlog ADD COLUMN {column_name} {column_type}")
        except sqlite3.OperationalError:
            pass
    conn.close()

def create_project(project: ProjectCreate) -> Project:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (name, description) VALUES (?, ?)",
        (project.name, project.description)
    )
    conn.commit()
    project_id = cursor.lastrowid
    conn.close()
    return Project(id=project_id, **project.model_dump())

def get_project(project_id: int) -> Optional[Project]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Project(**dict(row))
    return None

def get_projects() -> List[Project]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects ORDER BY name")
    rows = cursor.fetchall()
    conn.close()
    return [Project(**dict(row)) for row in rows]

def update_project(project_id: int, project: ProjectCreate) -> Optional[Project]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE projects SET name = ?, description = ? WHERE id = ?",
        (project.name, project.description, project_id)
    )
    conn.commit()
    conn.close()
    if cursor.rowcount > 0:
        return Project(id=project_id, **project.model_dump())
    return None

def delete_project(project_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0


def create_item(item: BacklogItemCreate) -> BacklogItem:
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Prepare base fields
    fields = ["project_id", "parent_id", "title", "description", "type"]
    values = [item.project_id, item.parent_id, item.title, item.description, item.type]
    
    # Add type-specific fields
    item_dict = item.model_dump()
    optional_fields = [
        "state", "benefit_hypothesis", "leading_indicators", "mvp_definition", "wsjf",
        "acceptance_criteria", "story_points", "program_increment", "iteration",
        "owner", "invest_compliant", "status"
    ]
    
    for field in optional_fields:
        if field in item_dict and item_dict[field] is not None:
            fields.append(field)
            values.append(item_dict[field])
    
    placeholders = ", ".join(["?" for _ in fields])
    fields_str = ", ".join(fields)
    
    cursor.execute(
        f"INSERT INTO backlog ({fields_str}) VALUES ({placeholders})",
        values
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    return get_item(item_id)


def get_item(item_id: int) -> Optional[BacklogItem]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM backlog WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return create_item_from_row(dict(row))
    return None


def get_items(project_id: int, type: str | None = None, limit: int = 50, offset: int = 0) -> List[BacklogItem]:
    conn = get_db_connection()
    cursor = conn.cursor()
    if type:
        cursor.execute(
            "SELECT * FROM backlog WHERE project_id = ? AND type = ? ORDER BY id LIMIT ? OFFSET ?",
            (project_id, type, limit, offset),
        )
    else:
        cursor.execute(
            "SELECT * FROM backlog WHERE project_id = ? ORDER BY id LIMIT ? OFFSET ?",
            (project_id, limit, offset),
        )
    rows = cursor.fetchall()
    conn.close()
    return [create_item_from_row(dict(row)) for row in rows]


def update_item(item_id: int, data: BacklogItemUpdate) -> Optional[BacklogItem]:
    fields = []
    values = []
    for field, value in data.model_dump(exclude_none=True).items():
        fields.append(f"{field} = ?")
        values.append(value)
    if not fields:
        return get_item(item_id)
    
    fields.append("updated_at = CURRENT_TIMESTAMP")
    values.append(item_id)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(f"UPDATE backlog SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return get_item(item_id)


def delete_item(item_id: int) -> bool:
    """
    Delete an item and all its descendants in a single operation.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    # Recursively delete item and all children using a recursive CTE
    cursor.execute(
        """
        WITH RECURSIVE to_delete AS (
            SELECT id FROM backlog WHERE id = ?
            UNION ALL
            SELECT b.id FROM backlog b JOIN to_delete td ON b.parent_id = td.id
        )
        DELETE FROM backlog WHERE id IN (SELECT id FROM to_delete)
        """,
        (item_id,),
    )
    conn.commit()
    conn.close()
    return True


def item_has_children(item_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM backlog WHERE parent_id = ? LIMIT 1", (item_id,))
    has = cursor.fetchone() is not None
    conn.close()
    return has
