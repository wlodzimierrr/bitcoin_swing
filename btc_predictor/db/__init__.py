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
from btc_predictor.db.raw import BTC_OHLCV_PRIMARY_KEY, btc_ohlcv, raw_metadata
from btc_predictor.db.raw import (
    FUNDING_RATES_PRIMARY_KEY,
    FUTURES_BASIS_PRIMARY_KEY,
    LIQUIDATIONS_PRIMARY_KEY,
    OPEN_INTEREST_PRIMARY_KEY,
    PERP_VOLUME_PRIMARY_KEY,
    funding_rates,
    futures_basis,
    liquidations,
    open_interest,
    perp_volume,
)

__all__ = [
    "Base",
    "BTC_OHLCV_PRIMARY_KEY",
    "CORE_SCHEMAS",
    "ConnectionVerification",
    "FUNDING_RATES_PRIMARY_KEY",
    "FUTURES_BASIS_PRIMARY_KEY",
    "LIQUIDATIONS_PRIMARY_KEY",
    "OPEN_INTEREST_PRIMARY_KEY",
    "PERP_VOLUME_PRIMARY_KEY",
    "RESEARCH_SCHEMAS",
    "RUNTIME_SCHEMAS",
    "alembic_config",
    "current_database_revision",
    "downgrade_database",
    "render_downgrade_sql",
    "render_upgrade_sql",
    "btc_ohlcv",
    "funding_rates",
    "futures_basis",
    "liquidations",
    "open_interest",
    "perp_volume",
    "raw_metadata",
    "schema_fingerprint",
    "target_metadata",
    "upgrade_database",
    "verify_connection",
    "verify_research_connection",
    "verify_runtime_connection",
]
