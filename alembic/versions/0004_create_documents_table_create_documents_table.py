"""create documents table"""

from alembic import op
import sqlalchemy as sa

revision = "0004_create_documents_table"
down_revision = "0003_add_item_review_fields"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "documents" not in insp.get_table_names():
        op.create_table(
            "documents",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("project_id", sa.Integer, nullable=False),
            sa.Column("filename", sa.String, nullable=False),
            sa.Column("content", sa.Text),
            sa.Column("embedding", sa.LargeBinary),
            sa.Column("filepath", sa.String),
            sa.Column("status", sa.String),
            sa.Column("meta", sa.JSON),
        )
        op.create_index("ix_documents_project_id", "documents", ["project_id"])
        op.create_index("ix_documents_status", "documents", ["status"])

def downgrade() -> None:
    op.drop_index("ix_documents_status", table_name="documents")
    op.drop_index("ix_documents_project_id", table_name="documents")
    op.drop_table("documents")
