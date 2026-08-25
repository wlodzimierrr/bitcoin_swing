"""create core postgresql schemas

Revision ID: 0010_create_core_postgresql_schemas
Revises: 0001_bootstrap_migration_framework
Create Date: 2026-08-25 00:00:00.000000
"""

from __future__ import annotations

import os

from alembic import context, op
from sqlalchemy.schema import CreateSchema, DropSchema


revision = "0010_create_core_postgresql_schemas"
down_revision = "0001_bootstrap_migration_framework"
branch_labels = None
depends_on = None

CORE_SCHEMAS = ("raw", "derived", "signals", "portfolio", "research", "system")
RUNTIME_SCHEMAS = ("raw", "derived", "signals", "portfolio", "system")
RESEARCH_SCHEMAS = CORE_SCHEMAS
RUNTIME_ROLE_ENV_VAR = "BTC_PREDICTOR_RUNTIME_DB_ROLE"
RESEARCH_ROLE_ENV_VAR = "BTC_PREDICTOR_RESEARCH_DB_ROLE"


def upgrade() -> None:
    if _dialect_name() != "postgresql":
        return

    for schema_name in CORE_SCHEMAS:
        op.execute(CreateSchema(schema_name, if_not_exists=True))

    runtime_role = _role_name("runtime_role", RUNTIME_ROLE_ENV_VAR)
    if runtime_role:
        _grant_schema_usage(runtime_role, RUNTIME_SCHEMAS)

    research_role = _role_name("research_role", RESEARCH_ROLE_ENV_VAR)
    if research_role:
        _grant_schema_usage(research_role, RESEARCH_SCHEMAS)
        _grant_schema_create(research_role, ("research",))


def downgrade() -> None:
    if _dialect_name() != "postgresql":
        return

    for schema_name in reversed(CORE_SCHEMAS):
        op.execute(DropSchema(schema_name, if_exists=True))


def _dialect_name() -> str:
    return op.get_context().dialect.name


def _role_name(x_argument_name: str, env_var_name: str) -> str | None:
    x_arguments = context.get_x_argument(as_dictionary=True)
    return x_arguments.get(x_argument_name) or os.getenv(env_var_name)


def _grant_schema_usage(role_name: str, schema_names: tuple[str, ...]) -> None:
    quoted_role = _quote_identifier(role_name)
    for schema_name in schema_names:
        op.execute(f"GRANT USAGE ON SCHEMA {_quote_identifier(schema_name)} TO {quoted_role}")


def _grant_schema_create(role_name: str, schema_names: tuple[str, ...]) -> None:
    quoted_role = _quote_identifier(role_name)
    for schema_name in schema_names:
        op.execute(f"GRANT CREATE ON SCHEMA {_quote_identifier(schema_name)} TO {quoted_role}")


def _quote_identifier(identifier: str) -> str:
    return op.get_context().dialect.identifier_preparer.quote(identifier)
