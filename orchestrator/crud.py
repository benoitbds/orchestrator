# orchestrator/crud.py
import sqlite3
import json
from typing import List, Optional
from .models import (
    Project,
    ProjectCreate,
    Item,
    ItemCreate,
)

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
        "type TEXT NOT NULL,"
        "title TEXT NOT NULL,"
        "description TEXT,"
        "status TEXT NOT NULL,"
        "parent_id INTEGER,"
        "acceptance_criteria TEXT,"
        "created_at TEXT DEFAULT CURRENT_TIMESTAMP,"
        "updated_at TEXT DEFAULT CURRENT_TIMESTAMP,"
        "FOREIGN KEY(parent_id) REFERENCES items(id),"
        "FOREIGN KEY(project_id) REFERENCES projects(id)"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS test_cases ("
        "item_id INTEGER PRIMARY KEY,"
        "expected_result TEXT,"
        "FOREIGN KEY(item_id) REFERENCES items(id) ON DELETE CASCADE"
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


# ----- Item CRUD -----

HIERARCHY = {
    "Epic": None,
    "Feature": "Epic",
    "US": "Feature",
    "UC": "US",
    "TC": "UC",
}


def _get_item(cursor, item_id: int) -> Optional[Item]:
    cursor.execute("SELECT * FROM items WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    if not row:
        return None
    item = Item(**dict(row))
    cursor.execute(
        "SELECT expected_result FROM test_cases WHERE item_id = ?",
        (item_id,),
    )
    tc = cursor.fetchone()
    if tc:
        item.expected_result = tc["expected_result"]
    return item


def create_item(item: ItemCreate) -> Item:
    if item.type not in HIERARCHY:
        raise ValueError("invalid item type")
    if item.type != "Epic" and item.parent_id is None:
        raise ValueError("parent_id required for non-Epic items")

    conn = get_db_connection()
    cur = conn.cursor()

    if item.parent_id is not None:
        parent = _get_item(cur, item.parent_id)
        if not parent:
            conn.close()
            raise ValueError("parent not found")
        expected_parent_type = HIERARCHY[item.type]
        if parent.type != expected_parent_type:
            conn.close()
            raise ValueError("invalid parent type")

    cur.execute(
        """
        INSERT INTO items (project_id, type, title, description, status, parent_id, acceptance_criteria)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            item.project_id,
            item.type,
            item.title,
            item.description,
            item.status,
            item.parent_id,
            json.dumps(item.acceptance_criteria) if item.acceptance_criteria else None,
        ),
    )
    item_id = cur.lastrowid

    if item.type == "TC" and item.expected_result is not None:
        cur.execute(
            "INSERT INTO test_cases (item_id, expected_result) VALUES (?, ?)",
            (item_id, item.expected_result),
        )

    conn.commit()
    created = _get_item(cur, item_id)
    conn.close()
    return created


def get_item(item_id: int) -> Optional[Item]:
    conn = get_db_connection()
    cur = conn.cursor()
    item = _get_item(cur, item_id)
    conn.close()
    return item
