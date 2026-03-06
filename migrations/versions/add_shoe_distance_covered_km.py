"""add shoe distance_covered_km

Revision ID: a1b2c3d4e5f6
Revises: c658052fa63a
Create Date: 2026-02-28

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'c658052fa63a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('shoes', sa.Column('distance_covered_km', sa.Float(), nullable=False, server_default='0'))
    # Backfill from activity_shoes so existing shoes show correct total
    op.execute("""
        UPDATE shoes s
        SET distance_covered_km = COALESCE(
            (SELECT SUM(distance_km) FROM activity_shoes WHERE shoe_id = s.id), 0
        )
    """)


def downgrade() -> None:
    op.drop_column('shoes', 'distance_covered_km')
