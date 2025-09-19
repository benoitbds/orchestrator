"""add AI review fields to backlog items"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_add_item_review_fields"
down_revision = "0002_add_user_uid_to_run"
branch_labels = None
depends_on = None

TBL = "backlog"  # <-- remplace par "items" si besoin


def _has_column(bind, table: str, col: str) -> bool:
    insp = sa.inspect(bind)
    try:
        cols = [c["name"] for c in insp.get_columns(table)]
    except Exception:
        cols = []
    return col in cols


def upgrade() -> None:
    bind = op.get_bind()

    # 1) Ajouter les colonnes uniquement si manquantes
    with op.batch_alter_table(TBL) as batch:
        if not _has_column(bind, TBL, "ia_review_status"):
            batch.add_column(sa.Column("ia_review_status", sa.String(), nullable=False, server_default="approved"))
        if not _has_column(bind, TBL, "last_modified_by"):
            batch.add_column(sa.Column("last_modified_by", sa.String(), nullable=False, server_default="user"))
        if not _has_column(bind, TBL, "ia_last_run_id"):
            batch.add_column(sa.Column("ia_last_run_id", sa.String(), nullable=True))
        if not _has_column(bind, TBL, "validated_at"):
            batch.add_column(sa.Column("validated_at", sa.DateTime(), nullable=True))
        if not _has_column(bind, TBL, "validated_by"):
            batch.add_column(sa.Column("validated_by", sa.String(), nullable=True))

    # 2) Initialiser les valeurs par défaut sur les lignes existantes (si NULL)
    op.execute(
        sa.text(
            f"""
            UPDATE {TBL}
            SET
              ia_review_status = COALESCE(ia_review_status, 'approved'),
              last_modified_by = COALESCE(last_modified_by, 'user')
            """
        )
    )

    # 3) Retirer les server_default (pour éviter des defaults DB permanents)
    #    Sous SQLite, ça peut nécessiter un recreate de table; on ignore si non supporté.
    try:
        with op.batch_alter_table(TBL) as batch:
            if _has_column(bind, TBL, "ia_review_status"):
                batch.alter_column("ia_review_status", server_default=None)
            if _has_column(bind, TBL, "last_modified_by"):
                batch.alter_column("last_modified_by", server_default=None)
    except Exception:
        pass


def downgrade() -> None:
    bind = op.get_bind()
    with op.batch_alter_table(TBL) as batch:
        for col in ["validated_by", "validated_at", "ia_last_run_id", "last_modified_by", "ia_review_status"]:
            if _has_column(bind, TBL, col):
                try:
                    batch.drop_column(col)
                except Exception:
                    pass
