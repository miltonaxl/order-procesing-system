import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import AsyncEngine

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.database import Base
target_metadata = Base.metadata

def get_database_url():
    """Get database URL from environment or alembic.ini"""
    # 1. Try environment variable first
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        return database_url
    
    # 2. Fall back to alembic.ini
    url = config.get_main_option("sqlalchemy.url")
    if url:
        return url
    
    # 3. If neither exists, raise error
    raise ValueError(
        "No DATABASE_URL environment variable or sqlalchemy.url in alembic.ini"
    )

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection):
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Get the URL
    database_url = get_database_url()
    
    # Create configuration dict for engine_from_config
    configuration = config.get_section(config.config_ini_section) or {}
    configuration['sqlalchemy.url'] = database_url
    
    connectable = AsyncEngine(
        engine_from_config(
            configuration,
            prefix="sqlalchemy.",
            poolclass=pool.NullPool,
            future=True,
        )
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())