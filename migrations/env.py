"""
Alembic migration environment.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root))

from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy.pool import NullPool

# Import config and create Flask app for SQLAlchemy
from flask import Flask
from src.config import DATABASE_URL

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Override sqlalchemy.url with our config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

# Create minimal Flask app and init db for metadata
app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

from src.models.models import db
db.init_app(app)

# Import models so they're registered with db.metadata
from src.models import (  # noqa: F401
    User,
    UserStrava,
    Activity,
    Gear,
    GearInstallation,
    GearService,
    GearServiceLog,
    ActivityGearUsage,
)

target_metadata = db.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
