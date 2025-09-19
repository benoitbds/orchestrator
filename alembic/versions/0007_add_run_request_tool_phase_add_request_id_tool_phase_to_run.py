from alembic import op
import sqlalchemy as sa

revision = "0007_add_run_request_tool_phase"
down_revision = "0006_align_sqlite_schema"
branch_labels = None
depends_on = None


def _has_column(table: str, col: str) -> bool:
    bind = op.get_bind()
    insp = sa.inspect(bind)
    return any(c["name"] == col for c in insp.get_columns(table))


def upgrade() -> None:
    bind = op.get_bind()
    dialect = bind.dialect.name

    if not _has_column("run", "request_id"):
        op.add_column("run", sa.Column("request_id", sa.String(), nullable=True))

    if not _has_column("run", "tool_phase"):
        # SQLite: pas de bool natif → default à 0
        op.add_column(
            "run",
            sa.Column("tool_phase", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        )
        op.execute("UPDATE run SET tool_phase = 0 WHERE tool_phase IS NULL")

    # Ne pas tenter DROP DEFAULT sur SQLite (non supporté)
    if dialect != "sqlite":
        op.alter_column("run", "tool_phase", server_default=None, existing_type=sa.Boolean())


def downgrade() -> None:
    # Suffisant en dev
    with op.batch_alter_table("run") as batch:
        if _has_column("run", "tool_phase"):
            batch.drop_column("tool_phase")
        if _has_column("run", "request_id"):
            batch.drop_column("request_id")
