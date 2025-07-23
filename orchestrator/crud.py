# orchestrator/crud.py
import sqlite3
from typing import List, Optional
from .models import Project, ProjectCreate, Item, ItemCreate, ItemUpdate

DATABASE_URL = "orchestrator.db"

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
        "CREATE TABLE IF NOT EXISTS items ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "project_id INTEGER NOT NULL,"
        "title TEXT NOT NULL,"
        "type TEXT NOT NULL,"
        "parent_id INTEGER,"
        "FOREIGN KEY(project_id) REFERENCES projects(id),"
        "FOREIGN KEY(parent_id) REFERENCES items(id)"
        ")"
    )
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


# -------------------- Items --------------------

def create_item(item: ItemCreate) -> Item:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (project_id, title, type, parent_id) VALUES (?, ?, ?, ?)",
        (item.project_id, item.title, item.type, item.parent_id),
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    return Item(id=item_id, **item.model_dump())


def get_item(item_id: int) -> Optional[Item]:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cur.fetchone()
    conn.close()
    return Item(**dict(row)) if row else None


def get_items(project_id: int, type: str | None = None, limit: int = 50, offset: int = 0) -> List[Item]:
    conn = get_db_connection()
    cur = conn.cursor()
    if type:
        cur.execute(
            "SELECT * FROM items WHERE project_id = ? AND type = ? ORDER BY id LIMIT ? OFFSET ?",
            (project_id, type, limit, offset),
        )
    else:
        cur.execute(
            "SELECT * FROM items WHERE project_id = ? ORDER BY id LIMIT ? OFFSET ?",
            (project_id, limit, offset),
        )
    rows = cur.fetchall()
    conn.close()
    return [Item(**dict(r)) for r in rows]


def update_item(item_id: int, data: ItemUpdate) -> Optional[Item]:
    fields = []
    values = []
    for field, value in data.model_dump(exclude_none=True).items():
        fields.append(f"{field} = ?")
        values.append(value)
    if not fields:
        return get_item(item_id)
    values.append(item_id)
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(f"UPDATE items SET {', '.join(fields)} WHERE id = ?", values)
    conn.commit()
    conn.close()
    return get_item(item_id)


def delete_item(item_id: int) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM items WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


def item_has_children(item_id: int) -> bool:
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT 1 FROM items WHERE parent_id = ? LIMIT 1", (item_id,))
    has = cur.fetchone() is not None
    conn.close()
    return has
