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


HEAD_REVISION = "0018_create_ingestion_audit_log"


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


def test_predictor_recommendation_migration_renders_postgresql_sql() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "CREATE TABLE signals.predictor_runs" in sql
    assert "CREATE TABLE signals.recommendations" in sql
    assert "CREATE TABLE signals.recommendation_reason_codes" in sql
    assert "config_version VARCHAR(64) NOT NULL" in sql
    assert "strategy_version VARCHAR(64) NOT NULL" in sql
    assert "feature_version VARCHAR(64) NOT NULL" in sql
    assert "parameter_set_id VARCHAR(128) NOT NULL" in sql
    assert "code_commit VARCHAR(64) NOT NULL" in sql
    assert "regime VARCHAR(32) NOT NULL" in sql
    assert "setup VARCHAR(64)" in sql
    assert "direction VARCHAR(16) NOT NULL" in sql
    assert "entry_conviction NUMERIC(6, 3) NOT NULL" in sql
    assert "hold_score NUMERIC(6, 3)" in sql
    assert "add_score NUMERIC(6, 3)" in sql
    assert "entry_zone_lower NUMERIC(38, 18)" in sql
    assert "invalidation_level NUMERIC(38, 18)" in sql
    assert "initial_stop NUMERIC(38, 18)" in sql
    assert "rr_ratio NUMERIC(12, 6)" in sql
    assert "risk_fraction_nav NUMERIC(12, 8)" in sql
    assert "suggested_notional NUMERIC(38, 18)" in sql
    assert "action VARCHAR(32) NOT NULL" in sql
    assert "CONSTRAINT pk_signals_predictor_runs PRIMARY KEY" in sql
    assert "CONSTRAINT pk_signals_recommendations PRIMARY KEY" in sql
    assert "CONSTRAINT pk_signals_recommendation_reason_codes PRIMARY KEY" in sql


def test_predictor_recommendation_migration_documents_reconstructability() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "COMMENT ON TABLE signals.predictor_runs" in sql
    assert "reconstructing recommendations" in sql
    assert "COMMENT ON COLUMN signals.predictor_runs.data_available_at" in sql
    assert "point-in-time reconstruction" in sql
    assert "COMMENT ON TABLE signals.recommendations" in sql
    assert "full score and risk payload" in sql
    assert "COMMENT ON TABLE signals.recommendation_reason_codes" in sql
    assert "Ordered reason codes explaining each persisted recommendation" in sql


def test_paper_portfolio_migration_renders_postgresql_sql() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    for table_name in (
        "paper_accounts",
        "positions",
        "tranches",
        "paper_orders",
        "stops",
        "position_events",
        "completed_trades",
    ):
        assert f"CREATE TABLE portfolio.{table_name}" in sql

    assert "account_name VARCHAR(128) NOT NULL" in sql
    assert "opening_recommendation_id BIGINT" in sql
    assert "tranche_number BIGINT NOT NULL" in sql
    assert "order_type VARCHAR(16) NOT NULL" in sql
    assert "stop_price NUMERIC(38, 18) NOT NULL" in sql
    assert "event_time TIMESTAMP WITH TIME ZONE NOT NULL" in sql
    assert "realized_pnl NUMERIC(38, 18) NOT NULL" in sql
    assert "CONSTRAINT pk_portfolio_paper_accounts PRIMARY KEY" in sql
    assert "CONSTRAINT pk_portfolio_positions PRIMARY KEY" in sql
    assert "CONSTRAINT pk_portfolio_tranches PRIMARY KEY" in sql
    assert "CONSTRAINT pk_portfolio_paper_orders PRIMARY KEY" in sql
    assert "CONSTRAINT pk_portfolio_stops PRIMARY KEY" in sql
    assert "CONSTRAINT pk_portfolio_position_events PRIMARY KEY" in sql
    assert "CONSTRAINT pk_portfolio_completed_trades PRIMARY KEY" in sql


def test_paper_portfolio_migration_supports_required_actions() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "action in ('ENTER', 'HOLD', 'ADD', 'STOP_MOVE', 'TRIM', 'EXIT', 'MISSED')" in sql
    assert "action in ('ENTER', 'ADD', 'TRIM', 'EXIT', 'MISSED')" in sql
    assert "Chronological paper position events supporting full lifecycle replay" in sql


def test_manual_trade_journal_migration_renders_postgresql_sql() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "CREATE TABLE portfolio.manual_trade_journal" in sql
    assert "recommendation_id BIGINT" in sql
    assert "actual_entry_time TIMESTAMP WITH TIME ZONE" in sql
    assert "actual_entry_price NUMERIC(38, 18)" in sql
    assert "actual_size NUMERIC(38, 18)" in sql
    assert "actual_size_unit VARCHAR(16)" in sql
    assert "actual_stop NUMERIC(38, 18)" in sql
    assert "actual_exit_time TIMESTAMP WITH TIME ZONE" in sql
    assert "actual_exit_price NUMERIC(38, 18)" in sql
    assert "manual_decision VARCHAR(32) NOT NULL" in sql
    assert "override_reason TEXT" in sql
    assert "notes TEXT" in sql
    assert "CONSTRAINT pk_portfolio_manual_trade_journal PRIMARY KEY" in sql
    assert "CONSTRAINT fk_portfolio_manual_trade_recommendation FOREIGN KEY" in sql
    assert "manual_decision in ('FOLLOWED', 'OVERRIDDEN', 'SKIPPED', 'MANUAL_ONLY')" in sql
    assert "manual_decision = 'MANUAL_ONLY' or recommendation_id is not null" in sql
    assert "manual_decision != 'OVERRIDDEN' or override_reason is not null" in sql
    assert "Manual execution journal linked to model recommendations" in sql


def test_ingestion_audit_log_migration_renders_postgresql_sql() -> None:
    sql = render_upgrade_sql("postgresql+psycopg://example.invalid/btc_predictor")

    assert "CREATE TABLE system.ingestion_audit_log" in sql
    assert "job_run_id VARCHAR(128) NOT NULL" in sql
    assert "job_name VARCHAR(128) NOT NULL" in sql
    assert "feed_name VARCHAR(64) NOT NULL" in sql
    assert "provider VARCHAR(64) NOT NULL" in sql
    assert "source VARCHAR(255) NOT NULL" in sql
    assert "started_at TIMESTAMP WITH TIME ZONE NOT NULL" in sql
    assert "ended_at TIMESTAMP WITH TIME ZONE" in sql
    assert "records_fetched BIGINT NOT NULL" in sql
    assert "records_inserted BIGINT NOT NULL" in sql
    assert "failure_count BIGINT NOT NULL" in sql
    assert "gap_count BIGINT NOT NULL" in sql
    assert "provider_response_metadata JSON NOT NULL" in sql
    assert "config_version VARCHAR(64)" in sql
    assert "reason_codes JSON NOT NULL" in sql
    assert "CONSTRAINT pk_system_ingestion_audit_log PRIMARY KEY" in sql
    assert "CONSTRAINT uq_system_ingestion_audit_log_job_run_id UNIQUE" in sql
    assert "status in ('started', 'succeeded', 'failed', 'partial')" in sql
    assert "ended_at is null or ended_at >= started_at" in sql
    assert "records_fetched >= 0" in sql
    assert "records_inserted >= 0" in sql
    assert "Ingestion job audit log with counters, gaps, failures, and provider metadata" in sql


def test_runtime_and_research_connections_can_be_verified(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "connections.db")
    upgrade_database(database_url)

    runtime_report = verify_runtime_connection(database_url)
    research_report = verify_research_connection(database_url)

    assert runtime_report.is_valid
    assert research_report.is_valid
