from pathlib import Path

from btc_predictor.db import (
    current_database_revision,
    downgrade_database,
    schema_fingerprint,
    upgrade_database,
)


HEAD_REVISION = "0001_bootstrap_migration_framework"


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
