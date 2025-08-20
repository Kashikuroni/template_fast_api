import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context
import sys
from os.path import dirname, abspath

sys.path.insert(0, dirname(dirname(abspath(__file__))))

from src.database import DATABASE_URL, Base
from src.auth.models import User, Workspace, WorkspaceUser


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

config.set_main_option("sqlalchemy.url", DATABASE_URL)
target_metadata = [Base.metadata]

def do_run_migrations(sync_conn: Connection) -> None:
    """Синхронная часть: конфигурируем контекст и запускаем миграции."""
    context.configure(
        connection=sync_conn,
        target_metadata=target_metadata,
        include_schemas=True,
        compare_type=True,
        render_as_batch=True,
        version_table_schema='public',
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Запуск миграций в offline‑режиме."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        include_schemas=True,
        compare_type=True,
        render_as_batch=True,
        version_table_schema='public',
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Запуск миграций в online‑режиме с асинхронным движком."""
    connectable = async_engine_from_config(
        dict(config.get_section(config.config_ini_section) or {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async def _migrate() -> None:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)

    asyncio.run(_migrate())

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
