"""Programmatic Alembic helpers."""

from __future__ import annotations

from io import StringIO
from pathlib import Path
from types import SimpleNamespace
from typing import TextIO

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text


MIGRATION_SCRIPT_LOCATION = Path(__file__).resolve().parent / "migrations"


def alembic_config(
    database_url: str,
    config_path: Path | None = None,
    output_buffer: TextIO | None = None,
    x_arguments: dict[str, str] | None = None,
) -> Config:
    """Build an Alembic config for a specific database URL."""

    config = (
        Config(str(config_path), output_buffer=output_buffer)
        if config_path is not None
        else Config(output_buffer=output_buffer)
    )
    if x_arguments:
        config.cmd_opts = SimpleNamespace(
            x=[f"{key}={value}" for key, value in x_arguments.items()],
        )
    config.set_main_option("script_location", str(MIGRATION_SCRIPT_LOCATION))
    config.set_main_option("sqlalchemy.url", database_url)
    return config


def upgrade_database(database_url: str, revision: str = "head") -> None:
    command.upgrade(alembic_config(database_url), revision)


def downgrade_database(database_url: str, revision: str = "base") -> None:
    command.downgrade(alembic_config(database_url), revision)


def render_upgrade_sql(
    database_url: str,
    revision: str = "head",
    x_arguments: dict[str, str] | None = None,
) -> str:
    output = StringIO()
    command.upgrade(
        alembic_config(
            database_url,
            output_buffer=output,
            x_arguments=x_arguments,
        ),
        revision,
        sql=True,
    )
    return output.getvalue()


def render_downgrade_sql(
    database_url: str,
    revision: str = "base",
    x_arguments: dict[str, str] | None = None,
) -> str:
    output = StringIO()
    command.downgrade(
        alembic_config(
            database_url,
            output_buffer=output,
            x_arguments=x_arguments,
        ),
        revision,
        sql=True,
    )
    return output.getvalue()


def schema_fingerprint(database_url: str) -> tuple[str, ...]:
    """Return a deterministic description of the current database objects."""

    engine = create_engine(database_url)
    try:
        inspector = inspect(engine)
        fingerprints: list[str] = []
        for table_name in sorted(inspector.get_table_names()):
            column_parts = []
            for column in inspector.get_columns(table_name):
                column_parts.append(
                    f"{column['name']}:{column['type']}:{column['nullable']}",
                )
            fingerprints.append(f"table:{table_name}|columns:{','.join(column_parts)}")
        return tuple(fingerprints)
    finally:
        engine.dispose()


def current_database_revision(database_url: str) -> str | None:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            if not inspect(connection).has_table("alembic_version"):
                return None
            result = connection.execute(text("select version_num from alembic_version"))
            row = result.first()
            if row is None:
                return None
            return str(row[0])
    finally:
        engine.dispose()
