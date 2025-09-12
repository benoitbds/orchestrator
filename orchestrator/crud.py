# orchestrator/crud.py
import json
import sqlite3
from datetime import datetime
from typing import List, Optional
from .models import (
    Project,
    ProjectCreate,
    Document,
    BacklogItem,
    BacklogItemCreate,
    BacklogItemUpdate,
    EpicOut,
    CapabilityOut,
    FeatureOut,
    USOut,
    UCOut,
    User,
)

DATABASE_URL = "orchestrator.db"

def create_item_from_row(row_dict: dict) -> BacklogItem:
    """Create the appropriate item type based on the 'type' field"""
    item_type = row_dict.get('type')

    # Clean up None values and set defaults based on type
    cleaned_dict = {k: v for k, v in row_dict.items() if v is not None}
    cleaned_dict['is_deleted'] = bool(row_dict.get('is_deleted', 0))
    
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

def get_conn():
    return get_db_connection()

def init_db():
    conn = get_conn()
    conn.execute(
        "CREATE TABLE IF NOT EXISTS users ("
        "uid TEXT PRIMARY KEY,"
        "email TEXT,"
        "is_admin BOOLEAN DEFAULT 0"
        ")"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS projects ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT NOT NULL,"
        "description TEXT,"
        "user_uid TEXT,"
        "FOREIGN KEY(user_uid) REFERENCES users(uid)"
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
        "is_deleted BOOLEAN DEFAULT 0," 
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
        ("status", "TEXT"),
        ("is_deleted", "BOOLEAN DEFAULT 0"),
    ]
    
    for column_name, column_type in new_columns:
        try:
            conn.execute(f"ALTER TABLE backlog ADD COLUMN {column_name} {column_type}")
        except sqlite3.OperationalError:
            pass

    # Table for storing diagram layout positions
    conn.execute(
        "CREATE TABLE IF NOT EXISTS diagram_layout ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "project_id INTEGER NOT NULL,"
        "item_id INTEGER NOT NULL,"
        "x REAL NOT NULL,"
        "y REAL NOT NULL,"
        "pinned INTEGER NOT NULL DEFAULT 0,"
        "UNIQUE(project_id, item_id)"
        ")"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_diagram_layout_project ON diagram_layout(project_id)"
    )

    # Table for project documents
    conn.execute(
        "CREATE TABLE IF NOT EXISTS documents ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "project_id INTEGER,"
        "filename TEXT,"
        "content TEXT,"
        "embedding TEXT,"
        "filepath TEXT,"
        "FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE"
        ")"
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_project ON documents(project_id)")
    # Add filepath column if missing for backward compatibility
    cur = conn.execute("PRAGMA table_info(documents)")
    cols = [row[1] for row in cur.fetchall()]
    if "filepath" not in cols:
        conn.execute("ALTER TABLE documents ADD COLUMN filepath TEXT")
    
    # Add user_uid column to projects table for backward compatibility
    cur = conn.execute("PRAGMA table_info(projects)")
    cols = [row[1] for row in cur.fetchall()]
    if "user_uid" not in cols:
        conn.execute("ALTER TABLE projects ADD COLUMN user_uid TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_uid)")
    
    # Table for document chunks with embeddings
    conn.execute(
        "CREATE TABLE IF NOT EXISTS document_chunks ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "doc_id INTEGER,"
        "chunk_index INTEGER,"
        "text TEXT NOT NULL,"
        "start_char INTEGER,"
        "end_char INTEGER,"
        "token_count INTEGER,"
        "embedding TEXT,"
        "embedding_model TEXT,"
        "created_at DATETIME DEFAULT CURRENT_TIMESTAMP,"
        "FOREIGN KEY(doc_id) REFERENCES documents(id) ON DELETE CASCADE"
        ")"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_doc ON document_chunks(doc_id)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_doc_chunk ON document_chunks(doc_id, chunk_index)"
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_chunks_model ON document_chunks(embedding_model)"
    )
    
    # ---- Runs & steps ----
    # Runs are referenced throughout the agent workflow.  Earlier revisions used an
    # auto-increment integer id which made it awkward to coordinate with the
    # frontend that generates UUIDs.  We now store the UUID directly as the
    # primary key.
    cur = conn.execute("PRAGMA table_info(runs)")
    cols = [row[1] for row in cur.fetchall()]
    if cols and "run_id" not in cols:
        conn.execute("DROP TABLE runs")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS runs (
            run_id TEXT PRIMARY KEY,
            project_id INTEGER,
            objective TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'running',
            html TEXT,
            summary TEXT,
            artifacts TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            completed_at TEXT,
            request_id TEXT,
            tool_phase INTEGER DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project_id)"
    )
    # Add new columns to existing runs table if they don't exist
    try:
        conn.execute("ALTER TABLE runs ADD COLUMN request_id TEXT")
    except sqlite3.OperationalError:
        pass
    try:
        conn.execute("ALTER TABLE runs ADD COLUMN tool_phase INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
        
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_runs_request ON runs(request_id)"
    )

    # Run steps keep a simple ordered log of what happened during the run.  Each
    # step is stored with an auto-increment id so ordering can be reconstructed.
    cur = conn.execute("PRAGMA table_info(run_steps)")
    cols = [row[1] for row in cur.fetchall()]
    if cols and "node" not in cols:
        conn.execute("DROP TABLE run_steps")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            node TEXT NOT NULL,
            content TEXT,
            ts TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_run_steps_run ON run_steps(run_id, ts)"
    )
    
    # Run events for structured event tracking
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_events (
            id TEXT PRIMARY KEY,
            run_id TEXT NOT NULL,
            seq INTEGER NOT NULL,
            event_type TEXT NOT NULL,
            ts TEXT NOT NULL DEFAULT (datetime('now')),
            elapsed_ms INTEGER,
            model TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            total_tokens INTEGER,
            cost_eur REAL,
            tool_call_id TEXT,
            data TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_run_events_seq ON run_events(run_id, seq)"
    )

    # Tables for detailed timeline and cost tracking
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_spans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_name TEXT,
            label TEXT NOT NULL,
            start_ts TEXT NOT NULL,
            end_ts TEXT NOT NULL,
            ref TEXT,
            meta TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_agent_spans_run ON agent_spans(run_id)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_name TEXT,
            label TEXT NOT NULL,
            ts TEXT NOT NULL,
            ref TEXT,
            meta TEXT,
            token_count INTEGER DEFAULT 0,
            cost_eur REAL DEFAULT 0
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_messages_run ON messages(run_id, ts)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_name TEXT,
            label TEXT NOT NULL,
            ts TEXT NOT NULL,
            ref TEXT,
            meta TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tool_calls_run ON tool_calls(run_id, ts)"
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tool_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id TEXT NOT NULL,
            agent_name TEXT,
            label TEXT NOT NULL,
            ts TEXT NOT NULL,
            ref TEXT,
            meta TEXT
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_tool_results_run ON tool_results(run_id, ts)"
    )
    conn.close()


def create_run(run_id: str, objective: str, project_id: int | None, request_id: str | None = None) -> None:
    """Create a new run entry.

    The caller provides the run_id so that it can be shared with the frontend
    immediately (e.g. for WebSocket subscriptions).
    """
    conn = get_conn()
    conn.execute(
        "INSERT INTO runs (run_id, project_id, objective, status, request_id) VALUES (?, ?, ?, 'running', ?)",
        (run_id, project_id, objective, request_id),
    )
    conn.commit()
    conn.close()


def finish_run(run_id: str, html: str, summary: str, artifacts: dict | None = None) -> None:
    conn = get_conn()
    conn.execute(
        "UPDATE runs SET status='done', html=?, summary=?, artifacts=?, completed_at=datetime('now') WHERE run_id=?",
        (html, summary, json.dumps(artifacts or {}), run_id),
    )
    conn.commit()
    conn.close()


def find_run_by_request_id(request_id: str) -> dict | None:
    """Find an existing run by request_id."""
    if not request_id:
        return None
    
    conn = get_conn()
    row = conn.execute(
        "SELECT run_id, project_id, objective, status, tool_phase, created_at FROM runs WHERE request_id=? ORDER BY created_at DESC LIMIT 1",
        (request_id,),
    ).fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None


def update_run_tool_phase(run_id: str, tool_phase: bool) -> None:
    """Update the tool_phase flag for a run."""
    conn = get_conn()
    conn.execute(
        "UPDATE runs SET tool_phase=? WHERE run_id=?",
        (1 if tool_phase else 0, run_id),
    )
    conn.commit()
    conn.close()


def get_run(run_id: str) -> dict | None:
    conn = get_conn()
    row = conn.execute(
        "SELECT run_id, project_id, objective, status, html, summary, artifacts, created_at, completed_at, request_id, tool_phase FROM runs WHERE run_id=?",
        (run_id,),
    ).fetchone()
    if not row:
        conn.close()
        return None

    step_rows = conn.execute(
        "SELECT node, content, ts FROM run_steps WHERE run_id=? ORDER BY id",
        (run_id,),
    ).fetchall()
    conn.close()

    steps = [
        {
            "order": idx + 1,
            "node": r[0],
            "timestamp": r[2],
            "content": r[1],
        }
        for idx, r in enumerate(step_rows)
    ]
    result = dict(row)
    result.setdefault("html", "")
    result.setdefault("summary", "")
    result.setdefault("artifacts", None)
    result["steps"] = steps
    return result


def get_runs(project_id: int | None = None) -> list[dict]:
    conn = get_conn()
    if project_id is None:
        rows = conn.execute(
            "SELECT run_id, project_id, objective, status, created_at, completed_at FROM runs ORDER BY created_at",
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT run_id, project_id, objective, status, created_at, completed_at FROM runs WHERE project_id=? ORDER BY created_at",
            (project_id,),
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def record_run_step(run_id: str, node: str, content: str, broadcast: bool = False) -> None:
    """Persist a run step for tracing.

    The ``broadcast`` flag is accepted for backward compatibility with older
    callers but is currently ignored.  Streaming to clients is handled at a
    higher level.
    """
    conn = get_conn()
    try:
        if content and len(content) > 1_000_000:
            content = content[:1_000_000] + "...[truncated]"
        conn.execute(
            "INSERT INTO run_steps (run_id, node, content) VALUES (?, ?, ?)",
            (run_id, node, content),
        )
        conn.commit()
    finally:
        conn.close()


def get_run_steps(run_id: str, limit: int = 200) -> list[dict]:
    conn = get_conn()
    rows = conn.execute(
        "SELECT node, content, ts FROM run_steps WHERE run_id=? ORDER BY id LIMIT ?",
        (run_id, limit),
    ).fetchall()
    conn.close()
    return [
        {"order": idx + 1, "node": r[0], "content": r[1], "timestamp": r[2]}
        for idx, r in enumerate(rows)
    ]


def get_run_timeline(
    run_id: str, limit: int = 1000, cursor: str | None = None
) -> list[dict]:
    """Return unified timeline events for a run."""
    conn = get_conn()
    try:
        events: list[dict] = []

        rows = conn.execute(
            "SELECT agent_name, label, start_ts, end_ts, ref, meta FROM agent_spans WHERE run_id=?",
            (run_id,),
        ).fetchall()
        for r in rows:
            ref = json.loads(r[4]) if r[4] else {}
            meta = json.loads(r[5]) if r[5] else {}
            start = {
                "type": "agent.span.start",
                "ts": datetime.fromisoformat(r[2]),
                "run_id": run_id,
                "agent": r[0],
                "label": r[1],
                "ref": ref,
                "meta": meta,
            }
            end = start.copy()
            end["type"] = "agent.span.end"
            end["ts"] = datetime.fromisoformat(r[3])
            events.extend([start, end])

        def _load(table: str, ev_type: str):
            rows = conn.execute(
                f"SELECT agent_name, label, ts, ref, meta FROM {table} WHERE run_id=?",
                (run_id,),
            ).fetchall()
            for r in rows:
                events.append(
                    {
                        "type": ev_type,
                        "ts": datetime.fromisoformat(r[2]),
                        "run_id": run_id,
                        "agent": r[0],
                        "label": r[1],
                        "ref": json.loads(r[3]) if r[3] else {},
                        "meta": json.loads(r[4]) if r[4] else {},
                    }
                )

        _load("messages", "message")
        _load("tool_calls", "tool.call")
        _load("tool_results", "tool.result")

        events.sort(key=lambda e: e["ts"])
        return events[:limit]
    finally:
        conn.close()


def get_run_cost(run_id: str) -> dict:
    """Aggregate token and cost information for a run."""
    conn = get_conn()
    try:
        rows = conn.execute(
            """
            SELECT agent_name, SUM(token_count) AS tokens, SUM(cost_eur) AS cost
            FROM messages WHERE run_id=? GROUP BY agent_name
            """,
            (run_id,),
        ).fetchall()
        by_agent: list[dict] = []
        total_tokens = 0
        total_cost = 0.0
        for r in rows:
            tokens = r[1] or 0
            cost = r[2] or 0.0
            by_agent.append(
                {"agent": r[0], "tokens": int(tokens), "cost_eur": float(cost)}
            )
            total_tokens += int(tokens)
            total_cost += float(cost)
        return {
            "by_agent": by_agent,
            "total": {"agent": None, "tokens": total_tokens, "cost_eur": total_cost},
        }
    finally:
        conn.close()



def get_user_by_uid(uid: str) -> Optional[User]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT uid, email, is_admin FROM users WHERE uid = ?",
        (uid,),
    )
    row = cursor.fetchone()
    conn.close()
    if row:
        return User(uid=row["uid"], email=row["email"], is_admin=bool(row["is_admin"]))
    return None


def create_user(uid: str, email: str | None, is_admin: bool = False) -> User:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO users (uid, email, is_admin) VALUES (?, ?, ?)",
        (uid, email, int(is_admin)),
    )
    conn.commit()
    conn.close()
    return User(uid=uid, email=email, is_admin=is_admin)


def create_project(project: ProjectCreate | str, description: str | None = None, user_uid: str | None = None) -> Project:
    if isinstance(project, ProjectCreate):
        data = project
        if user_uid and not data.user_uid:
            data.user_uid = user_uid
    else:
        data = ProjectCreate(name=project, description=description, user_uid=user_uid)

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO projects (name, description, user_uid) VALUES (?, ?, ?)",
        (data.name, data.description, data.user_uid)
    )
    conn.commit()
    project_id = cursor.lastrowid
    conn.close()
    return Project(id=project_id, **data.model_dump())

def get_project(project_id: int) -> Optional[Project]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return Project(**dict(row))
    return None

def get_project_for_user(project_id: int, user_uid: str) -> Optional[Project]:
    """Get a project if it belongs to the specified user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM projects WHERE id = ? AND user_uid = ?", (project_id, user_uid))
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

def get_projects_for_user(user_uid: str) -> List[Project]:
    """Get all projects for a specific user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM projects WHERE user_uid = ? ORDER BY name",
        (user_uid,)
    )
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


def get_layout(project_id: int) -> List[dict]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT item_id, x, y, pinned FROM diagram_layout WHERE project_id = ?",
        (project_id,),
    )
    rows = cursor.fetchall()
    conn.close()
    return [
        {
            "item_id": row["item_id"],
            "x": row["x"],
            "y": row["y"],
            "pinned": bool(row["pinned"]),
        }
        for row in rows
    ]


def upsert_layout(project_id: int, nodes: List[dict]) -> None:
    conn = get_db_connection()
    cursor = conn.cursor()
    for node in nodes:
        cursor.execute(
            "INSERT OR REPLACE INTO diagram_layout (project_id, item_id, x, y, pinned) VALUES (?, ?, ?, ?, ?)",
            (
                project_id,
                node["item_id"],
                node["x"],
                node["y"],
                1 if node.get("pinned") else 0,
            ),
        )
    conn.commit()
    conn.close()


def create_document(
    project_id: int,
    filename: str,
    content: str | None = None,
    embedding: List[float] | None = None,
    filepath: str | None = None,
) -> Document:
    """Store a document linked to a project."""
    if project_id is None or not filename:
        raise ValueError("project_id and filename are required")
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO documents (project_id, filename, content, embedding, filepath) VALUES (?, ?, ?, ?, ?)",
        (
            project_id,
            filename,
            content,
            json.dumps(embedding) if embedding is not None else None,
            filepath,
        ),
    )
    doc_id = cursor.lastrowid
    conn.commit()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    return Document(
        id=row["id"],
        project_id=row["project_id"],
        filename=row["filename"],
        content=row["content"],
        embedding=json.loads(row["embedding"]) if row["embedding"] else None,
        filepath=row["filepath"],
    )


def get_document(doc_id: int) -> Optional[dict]:
    """Return document row as a dict or None."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE id = ?", (doc_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "filename": row["filename"],
        "content": row["content"],
        "embedding": json.loads(row["embedding"]) if row["embedding"] else None,
        "filepath": row["filepath"],
    }


def get_documents(project_id: int) -> List[Document]:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM documents WHERE project_id = ? ORDER BY id", (project_id,))
    rows = cursor.fetchall()
    conn.close()
    documents = []
    for row in rows:
        documents.append(
            Document(
                id=row["id"],
                project_id=row["project_id"],
                filename=row["filename"],
                content=row["content"],
                embedding=json.loads(row["embedding"]) if row["embedding"] else None,
                filepath=row["filepath"],
            )
        )
    return documents


# Document chunks CRUD operations

def upsert_document_chunks(doc_id: int, chunks: list[tuple[int, str, list[float]]]) -> int:
    """Upsert chunk records for a document.

    Each chunk tuple is (chunk_index, text, embedding_list).
    Embeddings are stored as JSON strings. Returns number of processed chunks.
    """
    if not chunks:
        return 0
    conn = get_db_connection()
    cursor = conn.cursor()
    count = 0
    try:
        for idx, text, emb in chunks:
            cursor.execute(
                """
                INSERT OR REPLACE INTO document_chunks (id, doc_id, chunk_index, text, embedding)
                VALUES (
                    COALESCE((SELECT id FROM document_chunks WHERE doc_id=? AND chunk_index=?), NULL),
                    ?, ?, ?, ?
                )
                """,
                (doc_id, idx, doc_id, idx, text, json.dumps(emb)),
            )
            count += 1
        conn.commit()
    finally:
        conn.close()
    return count

def create_document_chunks(doc_id: int, chunks_data: List[dict]) -> List[int]:
    """
    Create multiple document chunks for a document.
    
    Args:
        doc_id: ID of the parent document
        chunks_data: List of chunk dictionaries with embedding data
        
    Returns:
        List of chunk IDs that were created
    """
    if not chunks_data:
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    chunk_ids = []
    
    try:
        for chunk in chunks_data:
            cursor.execute(
                "INSERT INTO document_chunks "
                "(doc_id, chunk_index, text, start_char, end_char, token_count, embedding, embedding_model) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    doc_id,
                    chunk.get("chunk_index"),
                    chunk.get("text"),
                    chunk.get("start_char"),
                    chunk.get("end_char"),
                    chunk.get("token_count"),
                    json.dumps(chunk.get("embedding")) if chunk.get("embedding") else None,
                    chunk.get("embedding_model"),
                ),
            )
            chunk_ids.append(cursor.lastrowid)
        
        conn.commit()
    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
    
    return chunk_ids

def get_document_chunks(doc_id: int) -> List[dict]:
    """
    Get all chunks for a document.
    
    Args:
        doc_id: ID of the parent document
        
    Returns:
        List of chunk dictionaries
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM document_chunks WHERE doc_id = ? ORDER BY chunk_index",
        (doc_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    chunks = []
    for row in rows:
        chunks.append({
            "id": row["id"],
            "doc_id": row["doc_id"],
            "chunk_index": row["chunk_index"],
            "text": row["text"],
            "start_char": row["start_char"],
            "end_char": row["end_char"],
            "token_count": row["token_count"],
            "embedding": json.loads(row["embedding"]) if row["embedding"] else None,
            "embedding_model": row["embedding_model"],
            "created_at": row["created_at"]
        })
    
    return chunks

def get_all_chunks_for_project(project_id: int) -> List[dict]:
    """
    Get all document chunks for a project.
    
    Args:
        project_id: ID of the project
        
    Returns:
        List of chunk dictionaries with document info
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT dc.*, d.filename, d.project_id
        FROM document_chunks dc
        JOIN documents d ON dc.doc_id = d.id
        WHERE d.project_id = ?
        ORDER BY d.id, dc.chunk_index
        """,
        (project_id,)
    )
    rows = cursor.fetchall()
    conn.close()
    
    chunks = []
    for row in rows:
        chunks.append({
            "id": row["id"],
            "doc_id": row["doc_id"],
            "chunk_index": row["chunk_index"],
            "text": row["text"],
            "start_char": row["start_char"],
            "end_char": row["end_char"],
            "token_count": row["token_count"],
            "embedding": json.loads(row["embedding"]) if row["embedding"] else None,
            "embedding_model": row["embedding_model"],
            "created_at": row["created_at"],
            "filename": row["filename"],
            "project_id": row["project_id"]
        })

    return chunks


def get_all_document_chunks_for_project(project_id: int) -> List[dict]:
    """Compatibility wrapper for older naming."""
    return get_all_chunks_for_project(project_id)

def delete_document_chunks(doc_id: int) -> None:
    """Delete all chunks for a document."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM document_chunks WHERE doc_id = ?", (doc_id,))
    conn.commit()
    conn.close()


def delete_document(doc_id: int) -> bool:
    """Delete a document row. Returns True if deleted."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM documents WHERE id = ?", (doc_id,))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted

def search_similar_chunks(
    project_id: int,
    query_embedding: List[float],
    limit: int = 10,
    embedding_model: str = None
) -> List[dict]:
    """
    Search for similar chunks in a project using embeddings.
    Note: This is a basic implementation. For production, consider using a vector database.
    
    Args:
        project_id: ID of the project to search in
        query_embedding: Query embedding vector
        limit: Maximum number of results to return
        embedding_model: Optional filter by embedding model
        
    Returns:
        List of similar chunks (similarity calculation done in application layer)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = """
        SELECT dc.*, d.filename, d.project_id
        FROM document_chunks dc
        JOIN documents d ON dc.doc_id = d.id
        WHERE d.project_id = ? AND dc.embedding IS NOT NULL
    """
    params = [project_id]
    
    if embedding_model:
        query += " AND dc.embedding_model = ?"
        params.append(embedding_model)
    
    query += " ORDER BY dc.created_at DESC"
    
    if limit:
        query += " LIMIT ?"
        params.append(limit * 5)  # Get more chunks for similarity calculation
    
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    
    chunks = []
    for row in rows:
        chunks.append({
            "id": row["id"],
            "doc_id": row["doc_id"],
            "chunk_index": row["chunk_index"],
            "text": row["text"],
            "start_char": row["start_char"],
            "end_char": row["end_char"],
            "token_count": row["token_count"],
            "embedding": json.loads(row["embedding"]) if row["embedding"] else None,
            "embedding_model": row["embedding_model"],
            "created_at": row["created_at"],
            "filename": row["filename"],
            "project_id": row["project_id"]
        })
    
    return chunks


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
            "SELECT * FROM backlog WHERE project_id = ? AND type = ? AND is_deleted = 0 ORDER BY id LIMIT ? OFFSET ?",
            (project_id, type, limit, offset),
        )
    else:
        cursor.execute(
            "SELECT * FROM backlog WHERE project_id = ? AND is_deleted = 0 ORDER BY id LIMIT ? OFFSET ?",
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


def delete_item(item_id: int) -> int:
    """Soft delete an item and all its descendants.

    Returns the number of rows updated. ``0`` indicates no matching item.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        WITH RECURSIVE to_delete AS (
            SELECT id FROM backlog WHERE id = ?
            UNION ALL
            SELECT b.id FROM backlog b JOIN to_delete td ON b.parent_id = td.id
        )
        UPDATE backlog SET is_deleted = 1 WHERE id IN (SELECT id FROM to_delete)
        """,
        (item_id,),
    )
    deleted = cursor.rowcount
    conn.commit()
    conn.close()
    return deleted


def item_has_children(item_id: int) -> bool:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM backlog WHERE parent_id = ? LIMIT 1", (item_id,))
    has = cursor.fetchone() is not None
    conn.close()
    return has
