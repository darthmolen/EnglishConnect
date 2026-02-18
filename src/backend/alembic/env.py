"""Alembic migration environment configuration."""

import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Import settings for database URL
from app.config import get_settings

# Import Base and all models to register them with metadata
from app.database import Base
from app.models import content, progress, user  # noqa: F401

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Override sqlalchemy.url from settings
settings = get_settings()
# Convert async URL to sync for alembic (asyncpg -> psycopg2)
sync_url = settings.database_url.replace("postgresql+asyncpg", "postgresql+psycopg2")
# psycopg2 uses 'sslmode' not 'ssl' (Azure Postgres uses ?ssl=require)
import re
sync_url = re.sub(r'\bssl=', 'sslmode=', sync_url)
config.set_main_option("sqlalchemy.url", sync_url)

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
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
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    from sqlalchemy import engine_from_config

    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
