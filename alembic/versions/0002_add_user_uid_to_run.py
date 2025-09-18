"""add user_uid column to run table"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_user_uid_to_run"
down_revision = "0001_agentic_storage"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add nullable user_uid column to run table."""
    op.add_column("run", sa.Column("user_uid", sa.String(), nullable=True))


def downgrade() -> None:
    """Remove user_uid column from run table."""
    op.drop_column("run", "user_uid")
