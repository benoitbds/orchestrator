from __future__ import annotations

from logging.config import fileConfig
import os

from sqlalchemy import engine_from_config, pool
from alembic import context
from sqlmodel import SQLModel

from orchestrator.storage import models  # noqa: F401

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

def get_url() -> str:
    return os.getenv("AGENTIC_DB_URL", "sqlite:///orchestrator.db")

target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=get_url(),
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
