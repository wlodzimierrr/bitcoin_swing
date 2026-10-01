"""RBT-002 ``INVENTORY_HISTORICAL_INPUT_COVERAGE_V1`` (EPIC Y, non-certifying).

These tests pin:

- the policy V3 section 5A enumeration: every owner input type field and every
  owner call-site parameter is classified, and an owner that gains an input,
  or a classification that outlives its field, fails;
- classification semantics on fixture owners (shape, family, OWNERLESS,
  DISCRETIONARY detection) and the owner-less findings on the real surface;
- read-only coverage collection: every statement is a single SELECT, run
  through a read-only check, and rows outside the data window are only counted
  through COUNT/MIN/MAX of time columns;
- coverage summaries on synthetic rows: gaps, first and last observation and
  timestamp semantics;
- minimum-history rules read from the owners, and earliest dates that match
  the real owners' own completeness at, and just before, the derived instant;
- the blocker list and the RBT-003 plan;
- the persisted inventory: rebuilt byte for byte from its own snapshot, and
  byte-identical under hash seeds, another cwd and a fresh process.

Every fixture is synthetic and offline. Nothing before 2020 or inside the
holdout is read; no database or network is touched.
"""

from __future__ import annotations

import dataclasses
import functools
import inspect
import json
import os
import socket
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from btc_predictor.data import EtfFlow, FundingRate, OhlcvBar
from btc_predictor.features import flow as flow_owner
from btc_predictor.features import momentum as momentum_owner
from btc_predictor.features import positioning as positioning_owner
from btc_predictor.features import trend as trend_owner
from btc_predictor.features import volatility as volatility_owner
from btc_predictor.research import prospective_integration_corpus as epic_x_corpus
from btc_predictor.research.us_equity_market_closures import load_closures
from btc_predictor.research_backtest import coverage
from btc_predictor.research_backtest.coverage import (
    CoverageError,
    InputClassification,
    InputSurfaceError,
)


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT = ROOT / coverage.ARTIFACT_DIRECTORY / coverage.INVENTORY_FILENAME
DIGEST = ROOT / coverage.ARTIFACT_DIRECTORY / coverage.INVENTORY_DIGEST_FILENAME
REPORT = ROOT / coverage.ARTIFACT_DIRECTORY / coverage.INVENTORY_REPORT_FILENAME
DATA_START = datetime(2020, 1, 1, tzinfo=UTC)
HOLDOUT_START = datetime(2026, 1, 1, tzinfo=UTC)
HOUR = timedelta(hours=1)
DAY = timedelta(days=1)

# Every column the coverage SQL names is double-quoted, so a quoted value
# column appearing anywhere would mean a value is selected or filtered on.
VALUE_COLUMNS = tuple(
    f'"{name}"'
    for name in (
        "open",
        "high",
        "low",
        "close",
        "volume",
        "flow_usd",
        "aum_usd",
        "funding_rate",
        "funding_interval_hours",
        "open_interest",
        "basis_rate",
        "annualized_basis_rate",
        "quantity",
        "notional_usd",
        "value",
    )
)


# --- section 5A enumeration ----------------------------------------------------------


def test_every_owner_input_field_and_call_site_parameter_is_classified() -> None:
    rows = coverage.enumerate_input_surface()
    expected = sum(len(dataclasses.fields(owner)) for owner in coverage.OWNER_INPUT_TYPES) + sum(
        len(inspect.signature(function).parameters) for function, _ in coverage.CALL_SITE_CLASSIFICATIONS
    )
    assert len(rows) == expected
    assert len({row.key for row in rows}) == len(rows)
    for owner in coverage.OWNER_INPUT_TYPES:
        names = {row.name for row in rows if row.owner == coverage._owner_path(owner)}
        assert names == {item.name for item in dataclasses.fields(owner)}
    assert all(isinstance(row.classification, InputClassification) for row in rows)


def test_the_enumeration_covers_every_required_owner_area() -> None:
    owners = {row.owner for row in coverage.enumerate_input_surface()}
    required = {
        "btc_predictor.features.entry.EntryConvictionInput",
        "btc_predictor.features.trend.TrendScoreInput",
        "btc_predictor.features.flow.FlowScoreInput",
        "btc_predictor.features.positioning.PositioningScoreInput",
        "btc_predictor.features.volatility.OrderlinessScoreInput",
        "btc_predictor.features.volatility.VolatilityScoreInput",
        "btc_predictor.features.structure.StructureScoreInput",
        "btc_predictor.features.regime.RegimeScoreInput",
        "btc_predictor.features.volatility.StressFlagInput",
        "btc_predictor.features.volatility.CapitulationFlagInput",
        "btc_predictor.features.volatility.EuphoriaFlagInput",
        "btc_predictor.features.positioning.CrowdingFlagInput",
        "btc_predictor.signals.hard_veto.HardVetoInput",
        "btc_predictor.signals.data_quality.apply_data_quality_gate",
        "btc_predictor.data.quality.validate_derivatives_quality",
        "btc_predictor.risk.stop.initial_stop_for_setup",
        "btc_predictor.risk.sizing.initial_position_size_for_trade",
        "btc_predictor.risk.budget.calculate_risk_budget",
        "btc_predictor.risk.trailing.trail_stop_for_position",
        "btc_predictor.features.hold.HoldScoreInput",
        "btc_predictor.features.add.AddScoreInput",
        "btc_predictor.signals.add_requirements.AddRequirementsInput",
        "btc_predictor.signals.trim.TrimRuleInput",
        "btc_predictor.signals.exit_rules.ExitRuleInput",
    }
    assert required <= owners


def _with_extra_field(owner: type) -> type:
    fields = [(item.name, item.type, item) for item in dataclasses.fields(owner)]
    return dataclasses.make_dataclass(
        owner.__name__,
        [*fields, ("new_owner_input", "Decimal | None", dataclasses.field(default=None))],
        frozen=True,
    )


def test_an_owner_type_that_gains_a_field_fails_the_enumeration() -> None:
    owner = positioning_owner.PositioningScoreInput
    grown = _with_extra_field(owner)
    classifications = {grown: coverage.FIELD_CLASSIFICATIONS[owner]}
    with pytest.raises(InputSurfaceError) as raised:
        coverage.enumerate_input_surface(classifications, ())
    assert raised.value.code == "UNCLASSIFIED_FIELD"
    assert "new_owner_input" in str(raised.value)


def test_a_classification_that_outlives_its_field_is_stale() -> None:
    owner = positioning_owner.PositioningScoreInput
    classified = dict(coverage.FIELD_CLASSIFICATIONS[owner])
    classified["removed_field"] = classified["funding_health"]
    with pytest.raises(InputSurfaceError) as raised:
        coverage.enumerate_input_surface({owner: classified}, ())
    assert raised.value.code == "STALE_CLASSIFICATION"


def test_a_call_site_that_gains_a_parameter_fails_the_enumeration() -> None:
    function, classified = next(
        item for item in coverage.CALL_SITE_CLASSIFICATIONS if item[0] is positioning_owner.funding_health
    )

    def grown(funding_rates, *, as_of, average_window_days=7, zscore_window_days=180, min_zscore_observations=30,
              preferred_zscore=None, zscore_width=None, new_window=None):  # noqa: ANN001, ANN202
        return None

    grown.__module__ = function.__module__
    grown.__qualname__ = function.__qualname__
    with pytest.raises(InputSurfaceError) as raised:
        coverage.enumerate_input_surface({}, ((grown, classified),))
    assert raised.value.code == "UNCLASSIFIED_PARAMETER"


def test_a_non_dataclass_owner_is_refused() -> None:
    with pytest.raises(InputSurfaceError) as raised:
        coverage.enumerate_input_surface({dict: {}}, ())
    assert raised.value.code == "NOT_A_DATACLASS"


# --- classification semantics ----------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class _FixtureOwnerInput:
    observed_price: Decimal
    snapshot_oi: Decimal | None
    owned_score: Decimal | None
    missing_owner_value: Decimal | None
    certified_value: Decimal | None
    manual_flag: bool | None
    engine_state: bool | None
    weights: dict


def _fixture_classifications() -> dict[str, InputClassification]:
    return {
        "observed_price": coverage._raw(
            (coverage.REFERENCE_PRICE_FAMILY,), coverage.SHAPE_INTERVAL, coverage.ROLE_VALUE, "raw.fixture via fixture", "gap", ("trend",)
        ),
        "snapshot_oi": coverage._raw(
            (coverage.OPEN_INTEREST_FAMILY,), coverage.SHAPE_SNAPSHOT, coverage.ROLE_VALUE, "raw.fixture_oi via fixture", "missing", ("positioning",)
        ),
        "owned_score": coverage._derived(trend_owner.calculate_trend_score, "None", (coverage.REFERENCE_PRICE_FAMILY,), ("trend",)),
        "missing_owner_value": coverage._ownerless("FIXTURE_OWNERLESS", "None", (coverage.REFERENCE_PRICE_FAMILY,), ("volatility",)),
        "certified_value": coverage._ownerless(
            "FIXTURE_CERTIFIED", "None", (coverage.LIQUIDATION_FAMILY,), ("volatility",), certified="CERTIFIED_FIXTURE_V1"
        ),
        "manual_flag": coverage._discretionary("FIXTURE_MANUAL", "None -> not asserted"),
        "engine_state": coverage._state("fixture lifecycle", "required"),
        "weights": coverage._config(),
    }


def test_fixture_owner_classification_reports_shape_family_and_ownerless_inputs() -> None:
    rows = coverage.enumerate_input_surface({_FixtureOwnerInput: _fixture_classifications()}, ())
    summary = coverage.input_surface_summary(rows)
    by_name = {row.name: row.classification for row in rows}
    assert by_name["observed_price"].shape == coverage.SHAPE_INTERVAL
    assert by_name["snapshot_oi"].shape == coverage.SHAPE_SNAPSHOT
    assert by_name["owned_score"].producing_owner == "btc_predictor.features.trend.calculate_trend_score"
    assert by_name["missing_owner_value"].producing_owner == coverage.OWNERLESS
    assert summary["ownerless_inputs"] == {
        "FIXTURE_CERTIFIED": {
            "kind": coverage.KIND_OWNERLESS_CERTIFIED,
            "certified_definition": "CERTIFIED_FIXTURE_V1",
            "entry_components": ["volatility"],
            "occurrences": [f"{__name__}._FixtureOwnerInput.certified_value"],
        },
        "FIXTURE_OWNERLESS": {
            "kind": coverage.KIND_OWNERLESS_UNDEFINED,
            "certified_definition": None,
            "entry_components": ["volatility"],
            "occurrences": [f"{__name__}._FixtureOwnerInput.missing_owner_value"],
        },
    }
    assert summary["discretionary_inputs"] == {"FIXTURE_MANUAL": [f"{__name__}._FixtureOwnerInput.manual_flag"]}
    assert summary["count_by_family_raw_leaves"] == {coverage.OPEN_INTEREST_FAMILY: 1, coverage.REFERENCE_PRICE_FAMILY: 1}
    assert by_name["owned_score"].core_regime_components == ("trend",)


@pytest.mark.parametrize(
    "kwargs, message",
    [
        ({"kind": coverage.KIND_RAW, "shape": coverage.SHAPE_DERIVED}, "section 4 shape"),
        ({"kind": coverage.KIND_OWNERLESS_UNDEFINED, "producing_owner": "owner.f"}, "OWNERLESS"),
        ({"kind": coverage.KIND_OWNERLESS_UNDEFINED, "producing_owner": coverage.OWNERLESS, "input_id": None}, "input_id"),
        ({"kind": coverage.KIND_DISCRETIONARY, "shape": coverage.SHAPE_NOT_APPLICABLE}, "DISCRETIONARY"),
        ({"families": ("NOT_A_FAMILY",)}, "families"),
        ({"entry_components": ("macro",)}, "Entry Conviction"),
        ({"missing_behaviour": " "}, "required"),
    ],
)
def test_invalid_classifications_are_refused(kwargs: dict[str, Any], message: str) -> None:
    base = {
        "kind": coverage.KIND_DERIVED,
        "shape": coverage.SHAPE_DERIVED,
        "families": (coverage.REFERENCE_PRICE_FAMILY,),
        "producing_owner": "owner.f",
        "historical_source": "upstream",
        "missing_behaviour": "None",
        "input_id": "X",
    }
    with pytest.raises(ValueError, match=message):
        InputClassification(**{**base, **kwargs})


EXPECTED_OWNERLESS = {
    "ADD_MOMENTUM_SCORE",
    "CORRECTION_FROM_LOCAL_HIGH",
    "DATA_RISK_EXIT_PREDICATE",
    "DISTRIBUTION_STATE",
    "DOWNSIDE_RETURN",
    "FLOW_SUPPORTIVE_PREDICATE",
    "FLOW_Z_ETF_NORM_20D",
    "FLOW_Z_ETF_NORM_5D",
    "FLOW_Z_FLOW_ACCEL",
    "LEVEL_REACTION_MAGNITUDE",
    "LEVEL_VOLUME_PERCENTILE",
    "LIQUIDATION_PERCENTILE",
    "MOMENTUM_PERSISTENCE_SCORE",
    "NEW_STRUCTURAL_CONFIRMATION",
    "NEW_STRUCTURE_SCORE",
    "RANGE_PERCENTILE",
    "REGIME_INVALIDATION_PREDICATE",
    "REGIME_SUPPORTIVE_PREDICATE",
    "SEVERE_CROWDING_STATE",
    "SHORT_TRIGGER",
    "TREND_Z_20W",
    "TREND_Z_52H",
    "TREND_Z_M12",
    "TREND_Z_M4",
    "UPSIDE_RETURN",
}


def test_the_real_surface_reports_these_owner_less_inputs() -> None:
    summary = coverage.input_surface_summary(coverage.enumerate_input_surface())
    assert set(summary["ownerless_inputs"]) == EXPECTED_OWNERLESS
    certified = {name for name, entry in summary["ownerless_inputs"].items() if entry["kind"] == coverage.KIND_OWNERLESS_CERTIFIED}
    assert certified == {"LIQUIDATION_PERCENTILE"}
    assert set(summary["discretionary_inputs"]) == {"MANUAL_RESEARCH_OVERRIDE", "SYSTEMIC_EUPHORIA", "SYSTEMIC_SHOCK"}


def test_no_production_code_produces_the_owner_less_entry_inputs() -> None:
    # The trend and flow owners take pre-normalised z-scores; nothing in
    # production constructs those inputs or computes the level/orderliness ones.
    production = [
        path
        for path in (ROOT / "btc_predictor").rglob("*.py")
        if "tests" not in path.parts and path.name != "coverage.py"
    ]
    # The level-strength owner forwards its own caller's value; no caller supplies one.
    patterns = {
        "TrendScoreInput(": set(),
        "FlowScoreInput(": set(),
        "OrderlinessScoreInput(": set(),
        "reaction_magnitude_fraction=": {"strength.py"},
    }
    for pattern, owners in patterns.items():
        offenders = [str(path) for path in production if path.name not in owners and pattern in path.read_text(encoding="utf-8")]
        assert offenders == [], pattern


def test_the_trend_owner_has_no_none_handling_for_its_z_scores() -> None:
    fields = {item.name: item.type for item in dataclasses.fields(trend_owner.TrendScoreInput)}
    assert all("None" not in str(annotation) for annotation in fields.values())
    with pytest.raises(RuntimeError):
        trend_owner.calculate_trend_score(
            trend_owner.TrendScoreInput(None, Decimal("0"), Decimal("0"), Decimal("0"), Decimal("0"))  # type: ignore[arg-type]
        )


def test_the_crowding_owner_has_no_severity_grade() -> None:
    names = {item.name for item in dataclasses.fields(positioning_owner.CrowdingFlagResult)}
    assert not any("sever" in name for name in names)


def test_liquidation_percentile_reuses_the_certified_epic_x_definition_by_reference() -> None:
    rows = coverage.enumerate_input_surface()
    liquidation = [row.classification for row in rows if row.classification.input_id == "LIQUIDATION_PERCENTILE"]
    assert liquidation and all(item.kind == coverage.KIND_OWNERLESS_CERTIFIED for item in liquidation)
    assert all(epic_x_corpus.PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION in item.historical_source for item in liquidation)
    requirement = _requirement("LIQUIDATION_PERCENTILE")
    assert requirement.parameter("window_days") == epic_x_corpus.LIQUIDATION_PERCENTILE_WINDOW_DAYS
    assert requirement.parameter("min_prior_observations") == epic_x_corpus.LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS
    assert coverage.LIQUIDATION_REQUIRED_DEPTH_DATE == date(2023, 1, 11)


# --- read-only SQL ---------------------------------------------------------------------


def _all_statements() -> list[str]:
    statements = [coverage.SERVER_FACTS_SQL, coverage.SCHEMAS_SQL, coverage.etf_revision_sql()]
    statements.append(coverage.OTHER_TIME_COLUMNS_SQL.replace(":schemas", coverage._in_list(coverage._OTHER_SCHEMAS)))
    for spec in coverage.RAW_TABLE_SPECS:
        statements += [
            coverage._total_rows_sql(spec.qualified),
            coverage.window_count_sql(spec),
            coverage.data_window_times_sql(spec),
            coverage.availability_lag_sql(spec),
        ]
    statements.append(coverage._other_column_sql("derived", "btc_reference_composite", "observation_time", is_date=False))
    return statements


def test_every_coverage_statement_is_a_single_select() -> None:
    for statement in _all_statements():
        assert coverage.require_select_only(statement) == statement
        assert coverage._LEADING_TAG.sub("", statement, count=1).lstrip().upper().startswith("SELECT")


@pytest.mark.parametrize(
    "statement",
    [
        "INSERT INTO raw.btc_ohlcv VALUES (1)",
        "UPDATE raw.btc_ohlcv SET close = 1",
        "DELETE FROM raw.btc_ohlcv",
        "SELECT 1; DROP TABLE raw.btc_ohlcv",
        "SELECT * INTO copy FROM raw.btc_ohlcv",
        "SET default_transaction_read_only = off",
        "WITH gone AS (DELETE FROM raw.btc_ohlcv RETURNING *) SELECT * FROM gone",
        "SELECT * FROM raw.btc_ohlcv FOR UPDATE",
        "/* rbt002:x */ TRUNCATE raw.btc_ohlcv",
    ],
)
def test_require_select_only_refuses_anything_else(statement: str) -> None:
    with pytest.raises(CoverageError) as raised:
        coverage.require_select_only(statement)
    assert raised.value.code == "NON_SELECT_SQL_REFUSED"


def test_no_statement_selects_a_value_column() -> None:
    for statement in _all_statements():
        for column in VALUE_COLUMNS:
            assert column not in statement, (column, statement)


def test_rows_outside_the_data_window_are_only_aggregated_over_time_columns() -> None:
    for spec in coverage.RAW_TABLE_SPECS:
        statement = coverage.window_count_sql(spec)
        select_list = statement.split(" SELECT ", 1)[1].split(" FROM ", 1)[0]
        keys = {f'"{column}"' for column in spec.series_columns}
        allowed_time = {f'"{column}"' for column in (spec.time_column, *spec.extra_time_columns)}
        for item in [part.strip() for part in select_list.split(", ")]:
            if item in keys:
                continue
            assert item.startswith(("COUNT(*) FILTER", "MIN(", "MAX(")), item
            if item.startswith(("MIN(", "MAX(")):
                assert item[4 : item.index(")")] in allowed_time, item
        for selected in (coverage.data_window_times_sql(spec), coverage.availability_lag_sql(spec)):
            assert ":holdout_start" in selected and ":data_start" in selected


class _RecordingConnection:
    """Answers the coverage queries from canned rows and records every SQL."""

    def __init__(self, *, read_only: str = "on", ohlcv_times: list[tuple[Any, ...]] | None = None) -> None:
        self.statements: list[str] = []
        self.read_only = read_only
        self.ohlcv_times = ohlcv_times or []

    def execute(self, clause: Any, params: dict[str, Any]) -> Any:
        sql = str(clause)
        self.statements.append(sql)
        tag = sql.split("*/", 1)[0]
        if "server_facts" in tag:
            rows = [("17.9", "fixture", self.read_only, self.read_only)]
        elif "schemas" in tag:
            rows = [("raw",), ("derived",)]
        elif "total_rows:raw.btc_ohlcv" in tag:
            rows = [(len(self.ohlcv_times) + 2,)]
        elif "total_rows" in tag:
            rows = [(0,)]
        elif "window_counts:raw.btc_ohlcv" in tag:
            first, last = self.ohlcv_times[0][-1], self.ohlcv_times[-1][-1]
            pre = datetime(2019, 12, 31, 22, tzinfo=UTC)
            rows = [
                (
                    "bitstamp", "BTC/USD", "1h", "bitstamp",
                    2, pre, pre + HOUR, pre, pre,
                    len(self.ohlcv_times), first, last, first, last,
                    0, None, None, None, None,
                    0, None, None, None, None,
                )
            ]
        elif "data_window_times:raw.btc_ohlcv" in tag:
            rows = self.ohlcv_times
        elif "other_time_columns" in tag:
            rows = [("derived", "fixture_table", "observation_time", "timestamp with time zone"), ("research", "trusted_acquisition_x", "t", "date")]
        elif "other_column" in tag:
            rows = [(5, 0, 5, 0, 0, DATA_START, DATA_START + DAY)]
        else:
            rows = []
        return _Result(rows)


class _Result:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def all(self) -> list[tuple[Any, ...]]:
        return list(self._rows)


def _bitstamp_times(hours: int, *, skip: set[int] = frozenset()) -> list[tuple[Any, ...]]:
    return [
        ("bitstamp", "BTC/USD", "1h", "bitstamp", DATA_START + index * HOUR)
        for index in range(hours)
        if index not in skip
    ]


def test_collection_runs_only_select_statements_and_counts_outside_rows() -> None:
    connection = _RecordingConnection(ohlcv_times=_bitstamp_times(48, skip={5, 6}))
    snapshot = coverage.collect_database_coverage(connection, collected_at=datetime(2026, 10, 1, tzinfo=UTC))
    assert connection.statements
    for statement in connection.statements:
        coverage.require_select_only(statement)
    table = snapshot["raw_tables"]["raw.btc_ohlcv"]
    assert table["window_rows"] == {"PROHIBITED": 2, "DATA": 46, "HOLDOUT": 0, "RESERVE": 0}
    series = table["series"][0]
    assert series["windows"]["PROHIBITED"]["timestamp"] == {"min": "2019-12-31T22:00:00+00:00", "max": "2019-12-31T23:00:00+00:00"}
    assert series["data_window"]["first"] == "2020-01-01T00:00:00+00:00"
    assert series["data_window"]["missing_runs"][0] == ["2020-01-01T05:00:00+00:00", "2020-01-01T06:00:00+00:00", 2]
    assert snapshot["server"]["engine_execution_options"] == {"postgresql_readonly": True}
    skipped = [column for column in snapshot["other_time_columns"] if "skipped" in column]
    assert [column["table"] for column in skipped] == ["research.trusted_acquisition_x"]
    assert not any("trusted_acquisition_x" in statement and "other_column" in statement for statement in connection.statements)


def test_collection_refuses_a_database_that_is_not_read_only() -> None:
    connection = _RecordingConnection(read_only="off", ohlcv_times=_bitstamp_times(2))
    with pytest.raises(CoverageError) as raised:
        coverage.collect_database_coverage(connection, collected_at=datetime(2026, 10, 1, tzinfo=UTC))
    assert raised.value.code == "DATABASE_NOT_READ_ONLY"
    assert len(connection.statements) == 1


def test_the_research_engine_is_created_read_only(monkeypatch: pytest.MonkeyPatch) -> None:
    from btc_predictor.research import btc019_empirical

    monkeypatch.setattr(btc019_empirical, "_database_url_from_environment", lambda: "sqlite://")
    engine = coverage.open_research_engine()
    try:
        assert engine.get_execution_options()["postgresql_readonly"] is True
    finally:
        engine.dispose()


# --- coverage summaries on synthetic rows ------------------------------------------------


def _ohlcv_window_row(times: list[datetime], *, prohibited: int = 0, holdout: int = 0) -> tuple[Any, ...]:
    def window(count: int, first: Any, last: Any) -> tuple[Any, ...]:
        return (count, first, last, first, last)

    return (
        "bitstamp", "BTC/USD", "1h", "bitstamp",
        *window(prohibited, None, None),
        *window(len(times), times[0] if times else None, times[-1] if times else None),
        *window(holdout, None, None),
        *window(0, None, None),
    )


def test_summary_reports_gaps_first_last_and_a_partial_series_as_not_confirmable() -> None:
    times = [DATA_START + index * HOUR for index in range(30) if index not in {3, 10, 11, 12}]
    spec = coverage.RAW_TABLE_SPECS[0]
    summary = coverage.summarize_raw_table(
        spec,
        total_rows=len(times),
        window_rows=[_ohlcv_window_row(times)],
        data_window_times=[("bitstamp", "BTC/USD", "1h", "bitstamp", value) for value in times],
    )
    window = summary["series"][0]["data_window"]
    assert window["first"] == "2020-01-01T00:00:00+00:00"
    assert window["last"] == "2020-01-02T05:00:00+00:00"
    assert window["missing_runs"][:2] == [
        ["2020-01-01T03:00:00+00:00", "2020-01-01T03:00:00+00:00", 1],
        ["2020-01-01T10:00:00+00:00", "2020-01-01T12:00:00+00:00", 3],
    ]
    # Every later data-window hour is missing too: the grid spans the whole window.
    assert window["missing"] == 52608 - len(times)
    assert summary["timestamp_semantics"]["from_data"].startswith(coverage.STAMPS_NOT_CONFIRMABLE)


def test_a_full_window_series_is_only_consistent_with_interval_start() -> None:
    table = synthetic_snapshot()["raw_tables"]["raw.btc_ohlcv"]
    verdict = table["timestamp_semantics"]["from_data"]
    assert verdict.startswith(coverage.STAMPS_CONSISTENT_WITH_START)
    assert "cannot exclude end stamping" in verdict


def test_an_off_grid_series_is_inconsistent() -> None:
    times = [DATA_START + index * HOUR + timedelta(minutes=30) for index in range(24)]
    summary = coverage.summarize_raw_table(
        coverage.RAW_TABLE_SPECS[0],
        total_rows=len(times),
        window_rows=[_ohlcv_window_row(times)],
        data_window_times=[("bitstamp", "BTC/USD", "1h", "bitstamp", value) for value in times],
    )
    assert summary["timestamp_semantics"]["from_data"].startswith(coverage.STAMPS_INCONSISTENT)


def test_an_end_stamped_series_is_not_confirmed_as_interval_start() -> None:
    times = [DATA_START + (index + 1) * HOUR for index in range(24)]
    summary = coverage.summarize_raw_table(
        coverage.RAW_TABLE_SPECS[0],
        total_rows=len(times),
        window_rows=[_ohlcv_window_row(times)],
        data_window_times=[("bitstamp", "BTC/USD", "1h", "bitstamp", value) for value in times],
    )
    assert not summary["timestamp_semantics"]["from_data"].startswith(coverage.STAMPS_CONSISTENT_WITH_START)


def test_empty_tables_report_no_persisted_rows_and_the_whole_window_missing() -> None:
    snapshot = synthetic_snapshot()
    for table in ("raw.funding_rates", "raw.liquidations", "raw.futures_basis", "raw.perp_volume"):
        assert snapshot["raw_tables"][table]["timestamp_semantics"]["from_data"].startswith("NO_PERSISTED_ROWS")
    records = {(r["family"], r["venue"]): r for r in coverage.family_coverage(snapshot)}
    assert records[(coverage.LIQUIDATION_FAMILY, "SHARED")]["status"] == "EMPTY"
    assert records[(coverage.LIQUIDATION_FAMILY, "SHARED")]["missing_span"]["first_hour"] == "2020-01-01T00:00:00+00:00"
    assert records[(coverage.REFERENCE_PRICE_FAMILY, "COINBASE")]["missing_hours"] == 2


def test_missing_hours_round_trip_through_the_snapshot() -> None:
    snapshot = synthetic_snapshot()
    missing = coverage.rebuild_missing_hours(snapshot, exchange="coinbase", symbol="BTC-USD", provider="coinbase")
    assert missing == (datetime(2021, 3, 1, 5, tzinfo=UTC), datetime(2021, 3, 1, 6, tzinfo=UTC))


# --- minimum history read from the owners ----------------------------------------------


def _requirement(input_id: str) -> coverage.HistoryRequirement:
    return next(item for item in coverage.minimum_history_requirements() if item.input_id == input_id)


def test_minimum_history_parameters_are_the_owners_own_numbers() -> None:
    expected = {
        ("MOMENTUM_4W", "lookback_rows"): momentum_owner.FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS,
        ("MOMENTUM_12W", "lookback_rows"): momentum_owner.TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS,
        ("MA_DISTANCE_20W", "window_rows"): trend_owner.TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS,
        ("HIGH_DISTANCE_52W", "window_rows"): trend_owner.FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS,
        ("ETF_NORM_5D", "publication_days"): flow_owner.FIVE_DAY_ETF_FLOW_WINDOW_DAYS,
        ("ETF_NORM_20D", "publication_days"): flow_owner.TWENTY_DAY_ETF_FLOW_WINDOW_DAYS,
        ("FUNDING_HEALTH", "window_days"): positioning_owner.DEFAULT_FUNDING_ZSCORE_WINDOW_DAYS,
        ("FUNDING_HEALTH", "min_prior_observations"): positioning_owner.DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS,
        ("OI_GROWTH_HEALTH", "growth_window_days"): positioning_owner.DEFAULT_OI_GROWTH_WINDOW_DAYS,
        ("FUTURES_BASIS_HEALTH", "window_days"): positioning_owner.DEFAULT_FUTURES_BASIS_ZSCORE_WINDOW_DAYS,
        ("OI_INTENSITY_PERCENTILE", "min_prior_observations"): positioning_owner.DEFAULT_OI_INTENSITY_MIN_PERCENTILE_OBSERVATIONS,
        ("VOL_PERCENTILE_2Y", "window_days"): volatility_owner.volatility_percentile.__kwdefaults__["percentile_window_days"],
        ("VOL_PERCENTILE_2Y", "min_prior_observations"): volatility_owner.volatility_percentile.__kwdefaults__["min_percentile_observations"],
        ("RV_60", "lookback_rows"): 60,
    }
    for (input_id, name), value in expected.items():
        assert _requirement(input_id).parameter(name) == value
    undefined = {item.input_id for item in coverage.minimum_history_requirements() if item.rule == coverage.RULE_UNDEFINED}
    assert undefined == {
        "TREND_Z_M4", "TREND_Z_M12", "TREND_Z_20W", "TREND_Z_52H",
        "FLOW_Z_ETF_NORM_5D", "FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL",
        "RANGE_PERCENTILE", "DOWNSIDE_RETURN", "LEVEL_REACTION_MAGNITUDE", "LEVEL_VOLUME_PERCENTILE",
    }


def test_owner_constants_drive_the_derived_rules(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(positioning_owner, "DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS", 7)
    assert _requirement("FUNDING_HEALTH").parameter("min_prior_observations") == 7


def _daily_bars(count: int, start: datetime = DATA_START) -> list[OhlcvBar]:
    bars = []
    for index in range(count):
        close = Decimal(100 + (index * 37) % 23 + index) / Decimal("1")
        moment = start + index * DAY
        bars.append(
            OhlcvBar(moment, "fixture", "BTC/USD", "1d", close, close + 1, close - 1, close, Decimal("1"), "fixture", moment + DAY)
        )
    return bars


def test_lookback_rules_match_the_momentum_and_weekly_owners() -> None:
    closes = [Decimal(100 + index % 7 + index) for index in range(120)]
    for owner, input_id in (
        (momentum_owner.four_week_momentum, "MOMENTUM_4W"),
        (momentum_owner.twelve_week_momentum, "MOMENTUM_12W"),
    ):
        first = next(index for index, value in enumerate(owner(closes)) if value is not None)
        assert first == coverage.lookback_rows_index(closes, _requirement(input_id).parameter("lookback_rows"))
    ma = trend_owner.twenty_week_ma_distance(closes)
    assert next(i for i, v in enumerate(ma) if v is not None) == _requirement("MA_DISTANCE_20W").parameter("window_rows") - 1
    high = trend_owner.fifty_two_week_high_distance(closes)
    assert next(i for i, v in enumerate(high) if v is not None) == _requirement("HIGH_DISTANCE_52W").parameter("window_rows") - 1
    structure = trend_owner.classify_weekly_structure(closes, [value - 1 for value in closes])
    assert next(i for i, v in enumerate(structure) if v is not None) == _requirement("WEEKLY_STRUCTURE").parameter("lookback_rows")


def test_trailing_window_rule_matches_the_funding_owner_at_and_before_the_derived_instant() -> None:
    step = timedelta(hours=8)
    rates = [
        FundingRate(
            DATA_START + step * (index + 1), "fixture", "BTCUSDT", "BTC-PERP",
            Decimal(index % 5 - 2) / Decimal("10000"), Decimal("8"), "fixture", "fixture",
            DATA_START + step * (index + 1), DATA_START + step * (index + 1),
        )
        for index in range(60)
    ]
    requirement = _requirement("FUNDING_HEALTH")
    times = [rate.observation_time for rate in rates]
    index = coverage.trailing_window_index(
        times, timedelta(days=requirement.parameter("window_days")), requirement.parameter("min_prior_observations")
    )
    assert index is not None
    at = positioning_owner.funding_health(rates, as_of=times[index])
    before = positioning_owner.funding_health(rates, as_of=times[index - 1])
    assert at.funding_zscore is not None
    assert "FUNDING_HEALTH_INSUFFICIENT_HISTORY" in before.reason_codes


def test_volatility_percentile_rule_matches_the_owner_at_and_before_the_derived_instant() -> None:
    bars = _daily_bars(400)
    series = coverage.ObservationSeries(
        coverage.SERIES_RV_20,
        tuple((bar.timestamp, bar.timestamp + DAY) for bar in bars[20:]),
        coverage.BASIS_MEASURED,
        "fixture",
    )
    result = coverage.earliest_evaluable_inputs(
        [_requirement("VOL_PERCENTILE_2Y")], {coverage.SERIES_RV_20: series}
    )["VOL_PERCENTILE_2Y"]
    assert result.status == coverage.STATUS_EVALUABLE

    def percentile(as_of: datetime) -> volatility_owner.VolatilityPercentileResult:
        visible = [bar for bar in bars if bar.timestamp + DAY <= as_of]
        rv = [
            volatility_owner.realized_volatility_from_daily_bars(visible[: index + 1], as_of=as_of, window_days=20)
            for index in range(len(visible))
        ]
        return volatility_owner.volatility_percentile([item for item in rv if item.complete], as_of=as_of)

    assert percentile(result.available_at).complete
    assert "VOL_PERCENTILE_INSUFFICIENT_HISTORY" in percentile(result.available_at - DAY).reason_codes


def test_etf_window_rule_matches_the_flow_owner_at_and_before_the_derived_instant() -> None:
    holidays = load_closures(date(2023, 1, 1), date(2026, 12, 31))
    series = coverage.projected_shared_series()[coverage.SERIES_ETF_DAYS]
    dates = [observed.date() for observed, _ in series.observations[:30]]
    flows = [
        EtfFlow(fund, day, Decimal("10"), Decimal("1000"), "fixture", "fixture", "final",
                datetime.combine(day + timedelta(days=2), datetime.min.time(), tzinfo=UTC),
                datetime(2026, 9, 1, tzinfo=UTC))
        for fund in ("FUND_A", "FUND_B")
        for day in dates
    ]
    result = coverage.earliest_evaluable_inputs([_requirement("ETF_NORM_20D")], {coverage.SERIES_ETF_DAYS: series})["ETF_NORM_20D"]
    assert result.available_at == datetime(2024, 2, 10, tzinfo=UTC)
    at = flow_owner.twenty_day_etf_flow(flows, as_of=result.available_at, market_holidays=holidays)
    before = flow_owner.twenty_day_etf_flow(flows, as_of=result.available_at - timedelta(microseconds=1), market_holidays=holidays)
    assert at.complete
    assert not before.complete


def test_venue_bar_series_reuses_the_btc_040_census() -> None:
    missing = [datetime(2020, 1, 8, 5, tzinfo=UTC)]
    series = coverage.venue_bar_series(missing)
    daily = {observed for observed, _ in series[coverage.SERIES_DAILY].observations}
    weekly = {observed for observed, _ in series[coverage.SERIES_WEEKLY].observations}
    assert datetime(2020, 1, 8, tzinfo=UTC) not in daily
    assert datetime(2020, 1, 7, tzinfo=UTC) in daily
    assert datetime(2020, 1, 6, tzinfo=UTC) not in weekly  # Monday week containing the gap
    assert datetime(2020, 1, 13, tzinfo=UTC) in weekly
    assert datetime(2019, 12, 30, tzinfo=UTC) not in weekly  # straddles 2020-01-01: pre-2020 hours never read
    first_day, available = series[coverage.SERIES_DAILY].observations[0]
    assert (first_day, available) == (DATA_START, DATA_START + DAY)


def test_a_member_without_observations_is_reported_among_the_blockers() -> None:
    undefined = coverage.EarliestEvaluable("Z", coverage.STATUS_UNDEFINED, blocking_inputs=("Z",))
    empty = coverage.EarliestEvaluable("E", coverage.STATUS_NO_OBSERVATIONS)
    combined = coverage._all_of("C", [undefined, empty])
    assert combined.status == coverage.STATUS_UNDEFINED
    assert combined.blocking_inputs == ("E", "Z")
    assert coverage._all_of("D", [empty]).status == coverage.STATUS_NO_OBSERVATIONS


def test_an_owner_less_member_makes_a_composite_undefined_with_a_lower_bound() -> None:
    defined = coverage.EarliestEvaluable("A", coverage.STATUS_EVALUABLE, DATA_START, DATA_START + DAY, coverage.BASIS_MEASURED)
    undefined = coverage.EarliestEvaluable("Z", coverage.STATUS_UNDEFINED, blocking_inputs=("Z",))
    combined = coverage._all_of("C", [defined, undefined])
    assert combined.status == coverage.STATUS_UNDEFINED
    assert combined.blocking_inputs == ("Z",)
    assert combined.lower_bound_available_at == DATA_START + DAY
    assert combined.available_at is None


def test_projected_positioning_series_respect_the_data_window_and_joins() -> None:
    series = coverage.projected_shared_series()
    funding = series[coverage.SERIES_FUNDING].observations
    assert funding[0][0] == datetime(2020, 1, 1, 8, tzinfo=UTC)  # the 00:00 settlement prices 2019
    intensity = series[coverage.SERIES_OI_INTENSITY].observations
    assert intensity[0] == (datetime(2020, 9, 1, tzinfo=UTC), datetime(2020, 9, 2, tzinfo=UTC))
    for observations in (funding, intensity, series[coverage.SERIES_LIQUIDATION_DAYS].observations):
        assert all(DATA_START <= observed < HOLDOUT_START for observed, _ in observations)


# --- blockers and the plan ---------------------------------------------------------------


def test_every_owner_less_undefined_input_belongs_to_exactly_one_blocker() -> None:
    blockers = coverage.derive_blockers(coverage.enumerate_input_surface())
    members = [name for blocker in blockers for name in blocker["inputs"]]
    assert len(members) == len(set(members))
    assert set(members) == EXPECTED_OWNERLESS - {"LIQUIDATION_PERCENTILE"}


def test_an_unassigned_owner_less_input_is_refused() -> None:
    rows = coverage.enumerate_input_surface({_FixtureOwnerInput: _fixture_classifications()}, ())
    with pytest.raises(CoverageError) as raised:
        coverage.derive_blockers(rows)
    assert raised.value.code == "BLOCKER_MEMBERSHIP"


def test_the_entry_conviction_structural_blockers_need_owner_decisions() -> None:
    blockers = {item["blocker_id"]: item for item in coverage.derive_blockers(coverage.enumerate_input_surface())}
    structural = {key for key, item in blockers.items() if item["entry_conviction_structurally_incomplete_on_every_date"]}
    assert structural == {
        "BLK-TREND-ZSCORE-NORMALISATION",
        "BLK-FLOW-ZSCORE-NORMALISATION",
        "BLK-VOLATILITY-RANGE-AND-RETURN",
        "BLK-LEVEL-STRENGTH-INPUTS",
    }
    assert all(blockers[key]["decision_required"] == coverage.DECISION_OWNER for key in structural)
    assert all(blockers[key]["resolution_options"] for key in structural)
    vetoed = {key for key, item in blockers.items() if item["every_new_trade_blocked_on_every_date"]}
    assert vetoed == {"BLK-SEVERE-CROWDING-STATE", "BLK-STRESS-HARD-VETO-MAPPING"}
    v4 = {key for key, item in blockers.items() if item["decision_required"] == coverage.DECISION_POLICY_V4}
    assert v4 == {"BLK-LIQUIDATION-HISTORICAL-CENSUS", "BLK-FUTURES-BASIS-CONTRACT", "BLK-STRESS-HARD-VETO-MAPPING", "BLK-ETF-FUND-UNIVERSE"}


def test_policy_v4_source_blockers_follow_the_selected_sources() -> None:
    rows = coverage.enumerate_input_surface()
    without = tuple(
        dataclasses.replace(candidate, deviations=())
        if candidate.candidate_id == "binance_coinm_quarterly_basis"
        else candidate
        for candidate in coverage.SOURCE_CANDIDATES
    )
    ids = {item["blocker_id"] for item in coverage.derive_blockers(rows, without)}
    assert "BLK-FUTURES-BASIS-CONTRACT" not in ids
    assert "BLK-LIQUIDATION-HISTORICAL-CENSUS" in ids


def test_source_selection_ranks_consistency_then_cost_and_the_plan_totals_29_usd() -> None:
    selected = coverage.selected_sources()
    assert selected[coverage.LIQUIDATION_FAMILY].candidate_id == "kraken_futures_rest_executions"
    assert selected[coverage.MARKET_CAP_FAMILY].candidate_id == "coinmetrics_community_capmrktcurusd"
    assert selected[coverage.ETF_FLOW_FAMILY].cost_usd == Decimal("29")
    plan = coverage.acquisition_plan(synthetic_snapshot(), coverage.derive_blockers(coverage.enumerate_input_surface()))
    assert plan["total_cost_usd"] == "29"
    assert plan["purchases_made"] is False
    status = {item["family"]: item["status"] for item in plan["items"]}
    assert status[coverage.LIQUIDATION_FAMILY] == "BLOCKED_PENDING_POLICY_V4_DECISION"
    assert status[coverage.FUTURES_BASIS_FAMILY] == "BLOCKED_PENDING_POLICY_V4_DECISION"
    assert status[coverage.ETF_FLOW_FAMILY] == "READY_FOR_RBT_003_AFTER_RBT_001A"
    assert all(item["span_end"] == "2025-12-31T23:00:00+00:00" for item in plan["items"])
    starts = [item["span_start"] for item in plan["items"]]
    assert all(start >= "2020-01-01" for start in starts)


def test_probe_evidence_is_provenance_only() -> None:
    ids = [probe.probe_id for probe in coverage.PROBE_EVIDENCE]
    assert len(ids) == len(set(ids))
    referenced = {probe for candidate in coverage.SOURCE_CANDIDATES for probe in candidate.probes}
    assert referenced <= set(ids)
    for probe in coverage.PROBE_EVIDENCE:
        assert probe.response_sha256 is None or len(probe.response_sha256) == 64
        assert "api_key" not in probe.url
        assert all(isinstance(value, str) for _, value in probe.observed)


# --- the inventory artifact ----------------------------------------------------------------


@functools.cache
def synthetic_snapshot() -> dict[str, Any]:
    """A full coverage snapshot built from synthetic timestamp-only rows."""

    tables: dict[str, Any] = {}
    ohlcv = coverage.RAW_TABLE_SPECS[0]
    missing = {"coinbase": {datetime(2021, 3, 1, 5, tzinfo=UTC), datetime(2021, 3, 1, 6, tzinfo=UTC)}, "bitfinex": set(), "bitstamp": set()}
    symbols = {"bitstamp": "BTC/USD", "coinbase": "BTC-USD", "bitfinex": "BTC/USD"}
    window_rows, times = [], []
    total = 0
    for exchange in ("bitfinex", "bitstamp", "coinbase"):
        hours = []
        current = DATA_START
        while current < HOLDOUT_START:
            if current not in missing[exchange]:
                hours.append(current)
            current += HOUR
        key = (exchange, symbols[exchange], "1h", exchange)
        window_rows.append(
            (*key, 0, None, None, None, None, len(hours), hours[0], hours[-1], hours[0], hours[-1], 0, None, None, None, None, 0, None, None, None, None)
        )
        times.extend((*key, value) for value in hours)
        total += len(hours)
    tables[ohlcv.qualified] = coverage.summarize_raw_table(ohlcv, total_rows=total, window_rows=window_rows, data_window_times=times)
    for spec in coverage.RAW_TABLE_SPECS[1:]:
        tables[spec.qualified] = coverage.summarize_raw_table(spec, total_rows=0, window_rows=[], data_window_times=[])
    return {
        "snapshot_version": coverage.DATABASE_COVERAGE_SNAPSHOT_VERSION,
        "collected_at": "2026-10-01T00:00:00+00:00",
        "server": {"server_version": "fixture", "database": "fixture", "default_transaction_read_only": "on",
                   "transaction_read_only": "on", "engine_execution_options": {"postgresql_readonly": True}},
        "schemas": ["raw"],
        "raw_tables": tables,
        "other_time_columns": [],
    }


def determinism_bytes() -> bytes:
    return coverage.inventory_bytes(coverage.build_inventory(synthetic_snapshot()))


def test_the_inventory_build_opens_no_socket(monkeypatch: pytest.MonkeyPatch) -> None:
    def refuse(*args: Any, **kwargs: Any) -> Any:
        raise AssertionError("the inventory build must not open a network connection")

    monkeypatch.setattr(socket, "socket", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)
    inventory = coverage.build_inventory(synthetic_snapshot())
    assert inventory["verdict"]["epic_y_stops_for_owner_decision"] is True
    assert inventory["safety"]["holdout_values_read"] is False


def test_the_inventory_is_byte_identical_in_fresh_processes_hash_seeds_and_another_cwd(tmp_path: Path) -> None:
    expected = determinism_bytes()
    script = """
import sys
from pathlib import Path
from btc_predictor.tests.test_research_backtest_coverage import determinism_bytes
Path(sys.argv[1]).write_bytes(determinism_bytes())
"""
    for seed in ("0", "1", "8675309"):
        cwd = tmp_path / f"cwd-{seed}"
        cwd.mkdir()
        output = tmp_path / f"inventory-{seed}.json"
        subprocess.run(
            [sys.executable, "-c", script, str(output)],
            cwd=cwd,
            env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(ROOT)),
            check=True,
            capture_output=True,
            text=True,
        )
        assert output.read_bytes() == expected


def test_the_persisted_inventory_rebuilds_byte_for_byte_from_its_own_snapshot() -> None:
    data = ARTIFACT.read_bytes()
    persisted = json.loads(data)
    rebuilt = coverage.build_inventory(persisted["database_coverage"])
    assert coverage.inventory_bytes(rebuilt) == data
    digest = coverage.inventory_digest(rebuilt)
    assert DIGEST.read_text(encoding="ascii") == f"{digest}  {coverage.INVENTORY_FILENAME}\n"
    assert REPORT.read_text(encoding="utf-8") == coverage.render_report(rebuilt, digest)


def test_the_persisted_snapshot_records_the_exposure_and_no_holdout_rows() -> None:
    persisted = json.loads(ARTIFACT.read_bytes())
    snapshot = persisted["database_coverage"]
    assert snapshot["server"]["default_transaction_read_only"] == "on"
    exposures = persisted["exposures"]
    assert exposures["raw_holdout_window_rows"] == 0
    assert exposures["raw_prohibited_window_rows"] == sum(
        table["window_rows"]["PROHIBITED"] for table in snapshot["raw_tables"].values()
    )
    for table in snapshot["raw_tables"].values():
        for series in table["series"]:
            for window in ("PROHIBITED", "HOLDOUT", "RESERVE"):
                recorded = series["windows"][window]
                assert set(recorded) == {"rows", table["time_column"], *(c for c in ("available_at", "ingested_at") if c in recorded)}
