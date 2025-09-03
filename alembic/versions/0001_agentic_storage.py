"""Create agentic orchestration tables"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0001_agentic_storage"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "run",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_table(
        "agentspan",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("start_ts", sa.DateTime(), nullable=False),
        sa.Column("end_ts", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("input_ref", sa.String(), nullable=True),
        sa.Column("output_ref", sa.String(), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
    )
    op.create_index("idx_agent_span_run_start", "agentspan", ["run_id", "start_ts"], unique=False)
    op.create_table(
        "message",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=True),
        sa.Column("role", sa.String(), nullable=False),
        sa.Column("content_ref", sa.String(), nullable=True),
        sa.Column("model", sa.String(), nullable=True),
        sa.Column("prompt_tokens", sa.Integer(), nullable=True),
        sa.Column("completion_tokens", sa.Integer(), nullable=True),
        sa.Column("total_tokens", sa.Integer(), nullable=True),
        sa.Column("cost_eur", sa.Float(), nullable=True),
        sa.Column("ts", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_message_run_ts", "message", ["run_id", "ts"], unique=False)
    op.create_table(
        "toolcall",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("agent_name", sa.String(), nullable=False),
        sa.Column("tool_name", sa.String(), nullable=False),
        sa.Column("input_ref", sa.String(), nullable=True),
        sa.Column("ts", sa.DateTime(), nullable=False),
        sa.Column("span_id", sa.String(), sa.ForeignKey("agentspan.id"), nullable=True),
    )
    op.create_index("idx_tool_call_run_ts", "toolcall", ["run_id", "ts"], unique=False)
    op.create_table(
        "toolresult",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("run_id", sa.String(), sa.ForeignKey("run.id"), nullable=False),
        sa.Column("tool_call_id", sa.String(), sa.ForeignKey("toolcall.id"), nullable=False),
        sa.Column("output_ref", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=False),
    )
    op.create_table(
        "blobref",
        sa.Column("id", sa.String(), primary_key=True),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("data", sa.JSON(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("blobref")
    op.drop_table("toolresult")
    op.drop_index("idx_tool_call_run_ts", table_name="toolcall")
    op.drop_table("toolcall")
    op.drop_index("idx_message_run_ts", table_name="message")
    op.drop_table("message")
    op.drop_index("idx_agent_span_run_start", table_name="agentspan")
    op.drop_table("agentspan")
    op.drop_table("run")
