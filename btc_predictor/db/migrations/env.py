"""Alembic environment configuration."""

from __future__ import annotations

from logging.config import fileConfig
import os

from alembic import context
from sqlalchemy import engine_from_config, pool

from btc_predictor.db.base import target_metadata


config = context.config
DATABASE_URL_ENV_VAR = "BTC_PREDICTOR_DATABASE_URL"

if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def database_url() -> str:
    cli_url = context.get_x_argument(as_dictionary=True).get("database_url")
    env_url = os.getenv(DATABASE_URL_ENV_VAR)
    configured_url = config.get_main_option("sqlalchemy.url")
    return cli_url or env_url or configured_url


def run_migrations_offline() -> None:
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
            include_schemas=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
