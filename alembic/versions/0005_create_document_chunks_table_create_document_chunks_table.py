"""create document_chunks table"""

from alembic import op
import sqlalchemy as sa

# IDs de révision
revision = "0005_create_document_chunks_table"
down_revision = "0004_create_documents_table"
branch_labels = None
depends_on = None

def upgrade() -> None:
    bind = op.get_bind()
    insp = sa.inspect(bind)

    if "document_chunks" not in insp.get_table_names():
        op.create_table(
            "document_chunks",
            sa.Column("id", sa.Integer, primary_key=True),
            sa.Column("doc_id", sa.Integer, sa.ForeignKey("documents.id", ondelete="CASCADE"), nullable=False),
            sa.Column("chunk_index", sa.Integer, nullable=False),
            sa.Column("content", sa.Text, nullable=False),
            sa.Column("embedding", sa.LargeBinary),  # vecteurs d'embedding (bytes)
            sa.Column("page", sa.Integer),
            sa.Column("section", sa.String),
            sa.Column("meta", sa.JSON),
            sa.UniqueConstraint("doc_id", "chunk_index", name="uq_document_chunks_doc_idx"),
        )
        op.create_index("ix_document_chunks_doc_id", "document_chunks", ["doc_id"])
        op.create_index("ix_document_chunks_page", "document_chunks", ["page"])

def downgrade() -> None:
    op.drop_index("ix_document_chunks_page", table_name="document_chunks")
    op.drop_index("ix_document_chunks_doc_id", table_name="document_chunks")
    op.drop_table("document_chunks")
