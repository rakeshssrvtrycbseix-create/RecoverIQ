import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

import app.models  # noqa: F401 (ensure all models register with Base.metadata)
from app.core.config import get_settings
from app.core.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata

# Determine sqlalchemy.url:
# 1. Respect explicit URL if set programmatically on config
# 2. Otherwise use DATABASE_URL from environment
# 3. Otherwise fallback to application settings
current_url = config.get_main_option("sqlalchemy.url")
env_url = os.environ.get("DATABASE_URL")

if not current_url or current_url.startswith("postgresql://localhost"):
    if env_url:
        config.set_main_option("sqlalchemy.url", env_url)
    else:
        try:
            settings = get_settings()
            if settings.database_url:
                config.set_main_option("sqlalchemy.url", settings.database_url)
        except Exception:
            pass


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
        poolclass=pool.NullPool,
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
