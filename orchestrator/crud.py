# orchestrator/crud.py
import sqlite3
import json
from typing import List, Optional
from .models import (
    Project,
    ProjectCreate,
    BacklogItem,
    BacklogItemCreate,
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
        "CREATE TABLE IF NOT EXISTS backlog ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "project_id INTEGER NOT NULL,"
        "parent_id INTEGER,"
        "title TEXT NOT NULL,"
        "description TEXT,"
        "type TEXT NOT NULL,"
        "FOREIGN KEY(project_id) REFERENCES projects(id),"
        "FOREIGN KEY(parent_id) REFERENCES backlog(id)"
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



def create_item(item: BacklogItemCreate) -> BacklogItem:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO backlog (project_id, parent_id, title, description, type) VALUES (?, ?, ?, ?, ?)",
        (
            item.project_id,
            item.parent_id,
            item.title,
            item.description,
            item.type,
        ),
    )
    conn.commit()
    item_id = cursor.lastrowid
    conn.close()
    return BacklogItem(id=item_id, **item.model_dump())


def get_item(item_id: int) -> Optional[BacklogItem]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM backlog WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return BacklogItem(**dict(row))
    return None


def get_items(project_id: int) -> List[BacklogItem]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM backlog WHERE project_id = ? ORDER BY id",
        (project_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [BacklogItem(**dict(row)) for row in rows]


def update_item(item_id: int, item: BacklogItemCreate) -> Optional[BacklogItem]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE backlog SET project_id = ?, parent_id = ?, title = ?, description = ?, type = ? WHERE id = ?",
        (
            item.project_id,
            item.parent_id,
            item.title,
            item.description,
            item.type,
            item_id,
        ),
    )
    conn.commit()
    conn.close()
    if cursor.rowcount > 0:
        return BacklogItem(id=item_id, **item.model_dump())
    return None


def delete_item(item_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM backlog WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return cursor.rowcount > 0