"""Database integration."""

from btc_predictor.db.alembic import (
    alembic_config,
    current_database_revision,
    downgrade_database,
    render_downgrade_sql,
    render_upgrade_sql,
    schema_fingerprint,
    upgrade_database,
)
from btc_predictor.db.base import Base, target_metadata
from btc_predictor.db.connections import (
    CORE_SCHEMAS,
    RESEARCH_SCHEMAS,
    RUNTIME_SCHEMAS,
    ConnectionVerification,
    verify_connection,
    verify_research_connection,
    verify_runtime_connection,
)

__all__ = [
    "Base",
    "CORE_SCHEMAS",
    "ConnectionVerification",
    "RESEARCH_SCHEMAS",
    "RUNTIME_SCHEMAS",
    "alembic_config",
    "current_database_revision",
    "downgrade_database",
    "render_downgrade_sql",
    "render_upgrade_sql",
    "schema_fingerprint",
    "target_metadata",
    "upgrade_database",
    "verify_connection",
    "verify_research_connection",
    "verify_runtime_connection",
]
