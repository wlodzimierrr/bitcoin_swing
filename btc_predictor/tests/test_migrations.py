from pathlib import Path

from btc_predictor.db import (
    CORE_SCHEMAS,
    current_database_revision,
    downgrade_database,
    render_upgrade_sql,
    schema_fingerprint,
    upgrade_database,
    verify_research_connection,
    verify_runtime_connection,
)


HEAD_REVISION = "0014_create_raw_generic_series"


def sqlite_url(path: Path) -> str:
    return f"sqlite:///{path}"


def test_fresh_database_can_be_built_from_migrations(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "fresh.db")

    upgrade_database(database_url)

    assert current_database_revision(database_url) == HEAD_REVISION
    assert "table:alembic_version|columns:version_num:VARCHAR(32):False" in (
        schema_fingerprint(database_url)
    )


def test_upgrade_and_downgrade_are_reversible(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "round_trip.db")

    upgrade_database(database_url)
    assert current_database_revision(database_url) == HEAD_REVISION

    downgrade_database(database_url)
    assert current_database_revision(database_url) is None


def test_schema_state_is_reproducible(tmp_path: Path) -> None:
    first_database_url = sqlite_url(tmp_path / "first.db")
    second_database_url = sqlite_url(tmp_path / "second.db")

    upgrade_database(first_database_url)
    upgrade_database(second_database_url)

    assert schema_fingerprint(first_database_url) == schema_fingerprint(second_database_url)


def test_core_schema_migration_renders_postgresql_sql() -> None:
    sql = render_upgrade_sql(
        "postgresql+psycopg://example.invalid/btc_predictor",
        x_arguments={
            "runtime_role": "btc_predictor_runtime",
            "research_role": "btc_predictor_research",
        },
    )

    for schema_name in CORE_SCHEMAS:
        assert f"CREATE SCHEMA IF NOT EXISTS {schema_name}" in sql

    assert "GRANT USAGE ON SCHEMA raw TO btc_predictor_runtime" in sql
    assert "GRANT USAGE ON SCHEMA research TO btc_predictor_research" in sql
    assert "GRANT CREATE ON SCHEMA research TO btc_predictor_research" in sql


def test_raw_btc_ohlcv_migration_renders_postgresql_sql() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "CREATE TABLE raw.btc_ohlcv" in sql
    assert "timestamp TIMESTAMP WITH TIME ZONE NOT NULL" in sql
    assert "exchange VARCHAR(64) NOT NULL" in sql
    assert "symbol VARCHAR(32) NOT NULL" in sql
    assert "timeframe VARCHAR(16) NOT NULL" in sql
    assert "open NUMERIC(38, 18) NOT NULL" in sql
    assert "ingested_at TIMESTAMP WITH TIME ZONE NOT NULL" in sql
    assert "CONSTRAINT pk_raw_btc_ohlcv PRIMARY KEY" in sql


def test_derivatives_raw_migration_renders_postgresql_sql() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    for table_name in (
        "funding_rates",
        "open_interest",
        "futures_basis",
        "liquidations",
        "perp_volume",
    ):
        assert f"CREATE TABLE raw.{table_name}" in sql
        assert "exchange VARCHAR(64) NOT NULL" in sql
        assert "provider VARCHAR(64) NOT NULL" in sql
        assert "source VARCHAR(255) NOT NULL" in sql
        assert "available_at TIMESTAMP WITH TIME ZONE NOT NULL" in sql
        assert "ingested_at TIMESTAMP WITH TIME ZONE NOT NULL" in sql

    assert "funding_rate NUMERIC(38, 18) NOT NULL" in sql
    assert "open_interest NUMERIC(38, 18) NOT NULL" in sql
    assert "basis_rate NUMERIC(38, 18) NOT NULL" in sql
    assert "side VARCHAR(8) NOT NULL" in sql
    assert "volume_unit VARCHAR(32) NOT NULL" in sql
    assert "CONSTRAINT pk_raw_funding_rates PRIMARY KEY" in sql
    assert "CONSTRAINT pk_raw_open_interest PRIMARY KEY" in sql
    assert "CONSTRAINT pk_raw_futures_basis PRIMARY KEY" in sql
    assert "CONSTRAINT pk_raw_liquidations PRIMARY KEY" in sql
    assert "CONSTRAINT pk_raw_perp_volume PRIMARY KEY" in sql


def test_derivatives_raw_migration_documents_units_and_timestamp_semantics() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "COMMENT ON TABLE raw.funding_rates" in sql
    assert "COMMENT ON COLUMN raw.funding_rates.observation_time" in sql
    assert "COMMENT ON COLUMN raw.funding_rates.funding_rate" in sql
    assert "COMMENT ON COLUMN raw.open_interest.open_interest_unit" in sql
    assert "COMMENT ON COLUMN raw.futures_basis.expiry" in sql
    assert "COMMENT ON COLUMN raw.liquidations.quantity_unit" in sql
    assert "COMMENT ON COLUMN raw.perp_volume.volume_unit" in sql


def test_raw_etf_flows_migration_renders_postgresql_sql() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "CREATE TABLE raw.etf_flows" in sql
    assert "fund VARCHAR(64) NOT NULL" in sql
    assert "observation_date DATE NOT NULL" in sql
    assert "flow_usd NUMERIC(38, 18) NOT NULL" in sql
    assert "aum_usd NUMERIC(38, 18)" in sql
    assert "source VARCHAR(255) NOT NULL" in sql
    assert "revision VARCHAR(64) NOT NULL" in sql
    assert "available_at TIMESTAMP WITH TIME ZONE NOT NULL" in sql
    assert "CONSTRAINT pk_raw_etf_flows PRIMARY KEY" in sql
    assert "CREATE INDEX ix_raw_etf_flows_available_at" in sql
    assert "CREATE INDEX ix_raw_etf_flows_observation_date" in sql


def test_raw_etf_flows_migration_documents_revision_and_timestamp_semantics() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "COMMENT ON TABLE raw.etf_flows" in sql
    assert "historical revisions preserved" in sql
    assert "COMMENT ON COLUMN raw.etf_flows.observation_date" in sql
    assert "COMMENT ON COLUMN raw.etf_flows.flow_usd" in sql
    assert "COMMENT ON COLUMN raw.etf_flows.aum_usd" in sql
    assert "COMMENT ON COLUMN raw.etf_flows.revision" in sql
    assert "COMMENT ON COLUMN raw.etf_flows.available_at" in sql


def test_raw_generic_series_migration_renders_postgresql_sql() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "CREATE TABLE raw.generic_series" in sql
    assert "series_id VARCHAR(128) NOT NULL" in sql
    assert "series_type VARCHAR(32) NOT NULL" in sql
    assert "observation_time TIMESTAMP WITH TIME ZONE NOT NULL" in sql
    assert "value NUMERIC(38, 18) NOT NULL" in sql
    assert "unit VARCHAR(64) NOT NULL" in sql
    assert "provider VARCHAR(64) NOT NULL" in sql
    assert "source VARCHAR(255) NOT NULL" in sql
    assert "revision VARCHAR(64) NOT NULL" in sql
    assert "available_at TIMESTAMP WITH TIME ZONE NOT NULL" in sql
    assert "CONSTRAINT pk_raw_generic_series PRIMARY KEY" in sql
    assert "CREATE INDEX ix_raw_generic_series_available_at" in sql
    assert "CREATE INDEX ix_raw_generic_series_observation_time" in sql


def test_raw_generic_series_migration_documents_scope_and_revisions() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "COMMENT ON TABLE raw.generic_series" in sql
    assert "macro, liquidity, market-proxy, and on-chain" in sql
    assert "COMMENT ON COLUMN raw.generic_series.series_id" in sql
    assert "COMMENT ON COLUMN raw.generic_series.series_type" in sql
    assert "COMMENT ON COLUMN raw.generic_series.observation_time" in sql
    assert "COMMENT ON COLUMN raw.generic_series.unit" in sql
    assert "COMMENT ON COLUMN raw.generic_series.revision" in sql
    assert "COMMENT ON COLUMN raw.generic_series.available_at" in sql


def test_runtime_and_research_connections_can_be_verified(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "connections.db")
    upgrade_database(database_url)

    runtime_report = verify_runtime_connection(database_url)
    research_report = verify_research_connection(database_url)

    assert runtime_report.is_valid
    assert research_report.is_valid
