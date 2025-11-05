"""Align SQLite schema with CRUD expectations"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0006_align_sqlite_schema"
down_revision = "0005_create_document_chunks_table"
branch_labels = None
depends_on = None


def _has_table(insp: sa.Inspector, table: str) -> bool:
    return table in insp.get_table_names()


def _column_names(insp: sa.Inspector, table: str) -> set[str]:
    return {col["name"] for col in insp.get_columns(table)}


def _index_names(insp: sa.Inspector, table: str) -> set[str]:
    return {idx["name"] for idx in insp.get_indexes(table)}


def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    # --- backlog extras -------------------------------------------------
    if _has_table(insp, "backlog"):
        cols = _column_names(insp, "backlog")
        if "ia_fields" not in cols:
            op.add_column("backlog", sa.Column("ia_fields", sa.Text(), nullable=True))

    # --- diagram layout --------------------------------------------------
    if not _has_table(insp, "diagram_layout"):
        op.create_table(
            "diagram_layout",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("project_id", sa.Integer, nullable=False),
            sa.Column("item_id", sa.Integer, nullable=False),
            sa.Column("x", sa.Float, nullable=False),
            sa.Column("y", sa.Float, nullable=False),
            sa.Column("pinned", sa.Boolean, nullable=False, server_default="0"),
            sa.UniqueConstraint("project_id", "item_id", name="uq_diagram_layout_project_item"),
        )
        op.create_index(
            "idx_diagram_layout_project",
            "diagram_layout",
            ["project_id"],
            unique=False,
        )
        op.execute("UPDATE diagram_layout SET pinned=0")

    # --- document chunks -------------------------------------------------
    if _has_table(insp, "document_chunks"):
        cols = _column_names(insp, "document_chunks")

        if "text" not in cols and "content" in cols:
            op.execute("ALTER TABLE document_chunks RENAME COLUMN content TO text")
            cols.remove("content")
            cols.add("text")

        additions: list[tuple[str, sa.Column]] = [
            ("start_char", sa.Column("start_char", sa.Integer, nullable=True)),
            ("end_char", sa.Column("end_char", sa.Integer, nullable=True)),
            ("token_count", sa.Column("token_count", sa.Integer, nullable=True)),
            ("embedding_model", sa.Column("embedding_model", sa.Text(), nullable=True)),
            (
                "created_at",
                sa.Column(
                    "created_at",
                    sa.DateTime(),
                    nullable=False,
                    server_default=sa.text("CURRENT_TIMESTAMP"),
                ),
            ),
        ]

        for name, column in additions:
            if name not in cols:
                op.add_column("document_chunks", column)
                cols.add(name)
                if name == "created_at":
                    op.execute(
                        "UPDATE document_chunks SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
                    )

        idx = _index_names(insp, "document_chunks")
        if "idx_document_chunks_doc" not in idx:
            op.create_index(
                "idx_document_chunks_doc",
                "document_chunks",
                ["doc_id"],
                unique=False,
            )
        if "idx_document_chunks_doc_chunk" not in idx:
            op.create_index(
                "idx_document_chunks_doc_chunk",
                "document_chunks",
                ["doc_id", "chunk_index"],
                unique=False,
            )
        if "embedding_model" in cols and "idx_document_chunks_model" not in idx:
            op.create_index(
                "idx_document_chunks_model",
                "document_chunks",
                ["embedding_model"],
                unique=False,
            )

    # --- runs metadata ---------------------------------------------------
    if not _has_table(insp, "runs"):
        op.create_table(
            "runs",
            sa.Column("run_id", sa.Text, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=True),
            sa.Column("objective", sa.Text, nullable=False),
            sa.Column("status", sa.Text, nullable=False, server_default="running"),
            sa.Column("html", sa.Text, nullable=True),
            sa.Column("summary", sa.Text, nullable=True),
            sa.Column("artifacts", sa.Text, nullable=True),
            sa.Column(
                "created_at",
                sa.Text,
                nullable=False,
                server_default=sa.text("datetime('now')"),
            ),
            sa.Column("completed_at", sa.Text, nullable=True),
            sa.Column("request_id", sa.Text, nullable=True),
            sa.Column("tool_phase", sa.Integer, nullable=False, server_default="0"),
            sa.Column("meta", sa.Text, nullable=True),
            sa.Column("user_uid", sa.Text, nullable=True),
        )
        op.create_index("idx_runs_project", "runs", ["project_id"], unique=False)
        op.create_index("idx_runs_request", "runs", ["request_id"], unique=False)
        op.create_index("idx_runs_user", "runs", ["user_uid"], unique=False)

    else:
        cols = _column_names(insp, "runs")
        if "objective" not in cols:
            op.add_column("runs", sa.Column("objective", sa.Text, nullable=True))
        if "html" not in cols:
            op.add_column("runs", sa.Column("html", sa.Text, nullable=True))
        if "summary" not in cols:
            op.add_column("runs", sa.Column("summary", sa.Text, nullable=True))
        if "artifacts" not in cols:
            op.add_column("runs", sa.Column("artifacts", sa.Text, nullable=True))
        if "created_at" not in cols:
            op.add_column(
                "runs",
                sa.Column(
                    "created_at", sa.Text, nullable=False, server_default=sa.text("datetime('now')")
                ),
            )
        if "completed_at" not in cols:
            op.add_column("runs", sa.Column("completed_at", sa.Text, nullable=True))
        if "request_id" not in cols:
            op.add_column("runs", sa.Column("request_id", sa.Text, nullable=True))
        if "tool_phase" not in cols:
            op.add_column("runs", sa.Column("tool_phase", sa.Integer, nullable=False, server_default="0"))
        if "meta" not in cols:
            op.add_column("runs", sa.Column("meta", sa.Text, nullable=True))
        if "user_uid" not in cols:
            op.add_column("runs", sa.Column("user_uid", sa.Text, nullable=True))
        if "status" in cols:
            op.execute("UPDATE runs SET status = COALESCE(status, 'running')")

    if not _has_table(insp, "run_steps"):
        op.create_table(
            "run_steps",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.Text, nullable=False),
            sa.Column("node", sa.Text, nullable=False),
            sa.Column("content", sa.Text, nullable=True),
            sa.Column(
                "ts",
                sa.Text,
                nullable=False,
                server_default=sa.text("datetime('now')"),
            ),
        )
        op.create_index("idx_run_steps_run", "run_steps", ["run_id", "ts"], unique=False)

    if not _has_table(insp, "run_events"):
        op.create_table(
            "run_events",
            sa.Column("id", sa.Text, primary_key=True),
            sa.Column("run_id", sa.Text, nullable=False),
            sa.Column("seq", sa.Integer, nullable=False),
            sa.Column("event_type", sa.Text, nullable=False),
            sa.Column(
                "ts",
                sa.Text,
                nullable=False,
                server_default=sa.text("datetime('now')"),
            ),
            sa.Column("elapsed_ms", sa.Integer, nullable=True),
            sa.Column("model", sa.Text, nullable=True),
            sa.Column("prompt_tokens", sa.Integer, nullable=True),
            sa.Column("completion_tokens", sa.Integer, nullable=True),
            sa.Column("total_tokens", sa.Integer, nullable=True),
            sa.Column("cost_eur", sa.Float, nullable=True),
            sa.Column("tool_call_id", sa.Text, nullable=True),
            sa.Column("data", sa.Text, nullable=True),
        )
        op.create_index(
            "idx_run_events_seq", "run_events", ["run_id", "seq"], unique=False
        )

    # Timeline helper tables ------------------------------------------------
    if not _has_table(insp, "agent_spans"):
        op.create_table(
            "agent_spans",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.Text, nullable=False),
            sa.Column("agent_name", sa.Text, nullable=True),
            sa.Column("label", sa.Text, nullable=False),
            sa.Column("start_ts", sa.Text, nullable=False),
            sa.Column("end_ts", sa.Text, nullable=False),
            sa.Column("ref", sa.Text, nullable=True),
            sa.Column("meta", sa.Text, nullable=True),
        )
        op.create_index("idx_agent_spans_run", "agent_spans", ["run_id"], unique=False)

    if not _has_table(insp, "messages"):
        op.create_table(
            "messages",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.Text, nullable=False),
            sa.Column("agent_name", sa.Text, nullable=True),
            sa.Column("label", sa.Text, nullable=False),
            sa.Column("ts", sa.Text, nullable=False),
            sa.Column("ref", sa.Text, nullable=True),
            sa.Column("meta", sa.Text, nullable=True),
            sa.Column("token_count", sa.Integer, nullable=False, server_default="0"),
            sa.Column("cost_eur", sa.Float, nullable=False, server_default="0"),
        )
        op.create_index("idx_messages_run", "messages", ["run_id", "ts"], unique=False)

    if not _has_table(insp, "tool_calls"):
        op.create_table(
            "tool_calls",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.Text, nullable=False),
            sa.Column("agent_name", sa.Text, nullable=True),
            sa.Column("label", sa.Text, nullable=False),
            sa.Column("ts", sa.Text, nullable=False),
            sa.Column("ref", sa.Text, nullable=True),
            sa.Column("meta", sa.Text, nullable=True),
        )
        op.create_index("idx_tool_calls_run", "tool_calls", ["run_id", "ts"], unique=False)

    if not _has_table(insp, "tool_results"):
        op.create_table(
            "tool_results",
            sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
            sa.Column("run_id", sa.Text, nullable=False),
            sa.Column("agent_name", sa.Text, nullable=True),
            sa.Column("label", sa.Text, nullable=False),
            sa.Column("ts", sa.Text, nullable=False),
            sa.Column("ref", sa.Text, nullable=True),
            sa.Column("meta", sa.Text, nullable=True),
        )
        op.create_index("idx_tool_results_run", "tool_results", ["run_id", "ts"], unique=False)


def downgrade() -> None:
    raise RuntimeError("downgrade not supported for alignment migration")
