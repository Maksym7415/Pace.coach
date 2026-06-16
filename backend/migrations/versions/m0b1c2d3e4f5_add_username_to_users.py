"""add username to users

Revision ID: m0b1c2d3e4f5
Revises: l9a0b1c2d3e4
Create Date: 2026-06-11

"""
import re

import sqlalchemy as sa
from alembic import op

revision = "m0b1c2d3e4f5"
down_revision = "l9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("username", sa.String(30), nullable=True))

    connection = op.get_bind()
    rows = connection.execute(sa.text("SELECT id, email FROM users ORDER BY id")).fetchall()
    used: set[str] = set()

    for user_id, email in rows:
        local = email.split("@")[0]
        base = re.sub(r"[^a-zA-Z0-9_]", "_", local)[:27].strip("_")
        if len(base) < 3:
            base = f"user_{user_id}"
        candidate = base
        counter = 1
        while candidate in used:
            candidate = f"{base}_{counter}"
            counter += 1
        used.add(candidate)
        connection.execute(
            sa.text("UPDATE users SET username = :u WHERE id = :id"),
            {"u": candidate[:30], "id": user_id},
        )

    op.alter_column("users", "username", nullable=False)
    op.create_index("ix_users_username", "users", ["username"], unique=True)
    op.execute(
        "ALTER TABLE users ADD CONSTRAINT ck_users_username_format "
        "CHECK (username ~ '^[a-zA-Z0-9_]{3,30}$')"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE users DROP CONSTRAINT ck_users_username_format")
    op.drop_index("ix_users_username", table_name="users")
    op.drop_column("users", "username")
