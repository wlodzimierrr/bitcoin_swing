"""Database connection and schema-access checks."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import create_engine, inspect, text


CORE_SCHEMAS = ("raw", "derived", "signals", "portfolio", "research", "system")
RUNTIME_SCHEMAS = ("raw", "derived", "signals", "portfolio", "system")
RESEARCH_SCHEMAS = CORE_SCHEMAS


@dataclass(frozen=True)
class ConnectionVerification:
    name: str
    can_connect: bool
    required_schemas: tuple[str, ...]
    available_schemas: tuple[str, ...]

    @property
    def has_required_schemas(self) -> bool:
        return set(self.required_schemas).issubset(self.available_schemas)

    @property
    def is_valid(self) -> bool:
        return self.can_connect and self.has_required_schemas


def verify_runtime_connection(database_url: str) -> ConnectionVerification:
    return verify_connection(
        name="runtime",
        database_url=database_url,
        required_schemas=RUNTIME_SCHEMAS,
    )


def verify_research_connection(database_url: str) -> ConnectionVerification:
    return verify_connection(
        name="research",
        database_url=database_url,
        required_schemas=RESEARCH_SCHEMAS,
    )


def verify_connection(
    name: str,
    database_url: str,
    required_schemas: tuple[str, ...],
) -> ConnectionVerification:
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            connection.execute(text("select 1"))
            inspector = inspect(connection)
            if connection.dialect.name == "postgresql":
                available_schemas = tuple(sorted(inspector.get_schema_names()))
            else:
                available_schemas = required_schemas
            return ConnectionVerification(
                name=name,
                can_connect=True,
                required_schemas=required_schemas,
                available_schemas=available_schemas,
            )
    finally:
        engine.dispose()
