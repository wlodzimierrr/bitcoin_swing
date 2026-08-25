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


HEAD_REVISION = "0010_create_core_postgresql_schemas"


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


def test_runtime_and_research_connections_can_be_verified(tmp_path: Path) -> None:
    database_url = sqlite_url(tmp_path / "connections.db")
    upgrade_database(database_url)

    runtime_report = verify_runtime_connection(database_url)
    research_report = verify_research_connection(database_url)

    assert runtime_report.is_valid
    assert research_report.is_valid
