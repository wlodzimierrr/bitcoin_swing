"""BTC-166: complete paper trade lifecycle persistence."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.db.portfolio import (
    LIFECYCLE_EVENT_TABLES,
    LIFECYCLE_PROVENANCE_COLUMNS,
    completed_trades,
    paper_orders,
    position_events,
)
from btc_predictor.portfolio import (
    ENTER,
    EXIT,
    PENDING_ENTRY,
    EntryExecutionIntent,
    apply_position_event,
    execution_costs_from_config,
    simulate_next_bar_entry,
    start_position_lifecycle,
)
from btc_predictor.portfolio.accounting import TradeFill, calculate_trade_accounting
from btc_predictor.portfolio.lifecycle_persistence import (
    COMPLETED_TRADES_TABLE,
    EVENTS_TABLE,
    LIFECYCLE_PERSISTENCE_REASON_CODES,
    ORDERS_TABLE,
    PAPER_LIFECYCLE_PERSISTENCE_FEATURE_ID,
    PAPER_LIFECYCLE_PERSISTENCE_POLICY_VERSION,
    LifecycleProvenance,
    PaperTradeLifecycleRows,
    build_paper_trade_lifecycle_rows,
    verify_lifecycle_rows,
)


UTC = timezone.utc
DECISION_AT = datetime(2024, 12, 2, 12, tzinfo=UTC)
CLOSED_AT = DECISION_AT + timedelta(days=20)
CONFIG = load_strategy_config()
CONFIG_METADATA = CONFIG.run_metadata()
ACCOUNT_ID = 7
POSITION_ID = 3


def provenance(**kwargs) -> LifecycleProvenance:
    base = {
        "recommendation_id": 41,
        "strategy_version": "swing_v1.2",
        "parameter_set_id": "default_phase1",
    }
    return LifecycleProvenance(**{**base, **kwargs})


def closed_lifecycle():
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        state=PENDING_ENTRY,
        config_metadata=CONFIG_METADATA,
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=DECISION_AT,
        quantity="2",
        price="100000",
        stop_price="90000",
    )
    return apply_position_event(lifecycle, event=EXIT, event_time=CLOSED_AT)


def entry_execution():
    intent = EntryExecutionIntent(
        execution_id="entry-001",
        recommendation_id=41,
        symbol="BTC-USD",
        direction="long",
        decision_at=DECISION_AT,
        timeframe="1h",
        entry_zone_lower=Decimal("99000"),
        entry_zone_upper=Decimal("101000"),
        entry_zone_available_at=DECISION_AT - timedelta(minutes=1),
        entry_zone_id="cluster-17",
        requested_quantity=Decimal("2"),
        config_metadata=CONFIG_METADATA,
    )
    bar = OhlcvBar(
        timestamp=DECISION_AT,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1h",
        open=Decimal("100000"),
        high=Decimal("102000"),
        low=Decimal("98000"),
        close=Decimal("100500"),
        volume=Decimal("9"),
        provider="coinbase",
        ingested_at=DECISION_AT + timedelta(hours=1, seconds=5),
    )
    return simulate_next_bar_entry(intent, bar, costs=execution_costs_from_config())


def trade_accounting():
    return calculate_trade_accounting(
        (
            TradeFill(
                1,
                DECISION_AT,
                "ENTER",
                Decimal("2"),
                Decimal("100000"),
                Decimal("200"),
                "entry-accounting-1",
            ),
            TradeFill(
                2,
                CLOSED_AT,
                "EXIT",
                Decimal("2"),
                Decimal("120000"),
                Decimal("240"),
                "exit-accounting-1",
            ),
        ),
        symbol="BTC-USD",
        direction="long",
        initial_stop_price="90000",
        initial_stop_source_id="stop-1",
        exit_reason="HOLD_SCORE_COLLAPSE",
        exit_reason_source_id="exit-signal-1",
        config_metadata=CONFIG_METADATA,
    )


def build(**kwargs) -> PaperTradeLifecycleRows:
    base = {
        "provenance": provenance(),
        "account_id": ACCOUNT_ID,
        "position_id": POSITION_ID,
        "executions": [entry_execution()],
        "lifecycle": closed_lifecycle(),
        "accounting": trade_accounting(),
    }
    return build_paper_trade_lifecycle_rows(**{**base, **kwargs})


def test_metadata_is_stable() -> None:
    assert PAPER_LIFECYCLE_PERSISTENCE_FEATURE_ID == "PAPER_LIFECYCLE_PERSISTENCE"
    assert PAPER_LIFECYCLE_PERSISTENCE_POLICY_VERSION == (
        "PAPER_LIFECYCLE_PERSISTENCE_V1"
    )
    assert LIFECYCLE_PROVENANCE_COLUMNS == (
        "recommendation_id",
        "strategy_version",
        "parameter_set_id",
    )
    assert LIFECYCLE_EVENT_TABLES == (
        "paper_orders",
        "position_events",
        "completed_trades",
    )


# --- the schema now has somewhere to put the identity --------------------


@pytest.mark.parametrize(
    "table",
    [paper_orders, position_events, completed_trades],
)
def test_every_event_table_carries_the_full_provenance_triple(table) -> None:
    names = {column.name for column in table.columns}

    # Before BTC-166 only recommendation_id existed, and paper_orders had no
    # note column either, so an order row carried no strategy identity at all.
    assert set(LIFECYCLE_PROVENANCE_COLUMNS) <= names


@pytest.mark.parametrize("table", [paper_orders, position_events, completed_trades])
def test_strategy_identity_columns_are_not_nullable(table) -> None:
    for name in ("strategy_version", "parameter_set_id"):
        assert table.columns[name].nullable is False


def test_recommendation_id_stays_nullable_because_its_fk_sets_null() -> None:
    # A NOT NULL column would make deleting a recommendation fail rather than
    # sever the link, so the requirement is enforced by the writer instead.
    assert paper_orders.columns["recommendation_id"].nullable is True
    assert position_events.columns["recommendation_id"].nullable is True


# --- provenance -----------------------------------------------------------


def test_provenance_comes_from_the_strategy_config() -> None:
    resolved = LifecycleProvenance.from_config(CONFIG, recommendation_id=41)

    assert resolved.strategy_version == CONFIG_METADATA["strategy_version"]
    assert resolved.parameter_set_id == CONFIG_METADATA["parameter_set_id"]
    assert resolved.as_columns() == {
        "recommendation_id": 41,
        "strategy_version": "swing_v1.2",
        "parameter_set_id": "default_phase1",
    }


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"recommendation_id": 0}, "recommendation_id must be a positive integer"),
        ({"recommendation_id": None}, "recommendation_id must be a positive integer"),
        ({"recommendation_id": True}, "recommendation_id must be a positive integer"),
        ({"strategy_version": ""}, "strategy_version must be a non-empty string"),
        ({"parameter_set_id": "   "}, "parameter_set_id must be a non-empty string"),
    ],
)
def test_incomplete_provenance_is_refused(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        provenance(**kwargs).as_columns()


def test_an_unlinked_event_cannot_be_persisted() -> None:
    # "Every event linked to recommendation_id" is the whole requirement, so an
    # event without one is refused rather than written with a null.
    with pytest.raises(ValueError, match="recommendation_id"):
        build(provenance=provenance(recommendation_id=None))


def test_a_non_config_is_rejected() -> None:
    with pytest.raises(TypeError, match="StrategyConfig"):
        LifecycleProvenance.from_config({"identity": {}}, recommendation_id=41)


# --- assembly -------------------------------------------------------------


def test_a_complete_trade_produces_rows_for_every_table() -> None:
    rows = build()

    assert rows.complete is True
    assert rows.reason_codes == ("LIFECYCLE_PERSISTENCE_COMPLETE",)
    assert len(rows.orders) == 1
    assert len(rows.events) == 2
    assert rows.completed_trade is not None


def test_every_assembled_row_carries_the_same_identity() -> None:
    rows = build()

    assert rows.all_rows
    for table, row in rows.all_rows:
        assert table in LIFECYCLE_EVENT_TABLES
        for column in LIFECYCLE_PROVENANCE_COLUMNS:
            assert row[column] == provenance().as_columns()[column]


def test_every_assembled_row_belongs_to_the_same_account_and_position() -> None:
    rows = build()

    for _, row in rows.all_rows:
        assert row["account_id"] == ACCOUNT_ID
        assert row.get("position_id") in (None, POSITION_ID)


def test_provenance_overrides_an_executions_own_recommendation_id() -> None:
    # The execution carried recommendation 41; the lifecycle is being written
    # under a different one, and the assembled row must not disagree.
    rows = build(provenance=provenance(recommendation_id=99))

    assert entry_execution().intent.recommendation_id == 41
    for _, row in rows.all_rows:
        assert row["recommendation_id"] == 99


def test_accounting_strategy_identity_cannot_be_relabelled_at_persistence() -> None:
    mismatched = replace(
        trade_accounting(),
        config_metadata={**CONFIG_METADATA, "parameter_set_id": "experiment_b"},
    )

    with pytest.raises(ValueError, match="parameter_set_id"):
        build(accounting=mismatched)


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"executions": []}, "LIFECYCLE_PERSISTENCE_NO_ORDERS"),
        ({"lifecycle": None}, "LIFECYCLE_PERSISTENCE_NO_EVENTS"),
        ({"accounting": None}, "LIFECYCLE_PERSISTENCE_TRADE_NOT_CLOSED"),
    ],
)
def test_a_partial_lifecycle_is_reported_incomplete(kwargs, expected: str) -> None:
    rows = build(**kwargs)

    # An unfinished trade still persists what it has; it is simply not a
    # complete lifecycle yet.
    assert rows.complete is False
    assert expected in rows.reason_codes


def test_an_open_position_has_no_completed_trade_row() -> None:
    rows = build(accounting=None)

    assert rows.completed_trade is None
    assert all(table != COMPLETED_TRADES_TABLE for table, _ in rows.all_rows)


def test_row_counts_are_reported_per_table() -> None:
    record = build().as_record()

    assert record["row_counts"] == {
        ORDERS_TABLE: 1,
        EVENTS_TABLE: 2,
        COMPLETED_TRADES_TABLE: 1,
    }


# --- verification ---------------------------------------------------------


def test_verification_rejects_a_row_missing_its_identity() -> None:
    rows = build()
    stripped = {**rows.orders[0]}
    stripped.pop("strategy_version")

    with pytest.raises(ValueError, match="not attributed to strategy_version"):
        verify_lifecycle_rows(replace(rows, orders=(stripped,)))


def test_verification_rejects_a_row_attributed_to_another_run() -> None:
    rows = build()
    foreign = {**rows.orders[0], "parameter_set_id": "experiment_b"}

    with pytest.raises(ValueError, match="not attributed to parameter_set_id"):
        verify_lifecycle_rows(replace(rows, orders=(foreign,)))


def test_verification_rejects_a_row_from_another_account() -> None:
    rows = build()
    foreign = {**rows.orders[0], "account_id": 99}

    with pytest.raises(ValueError, match="does not belong to the account"):
        verify_lifecycle_rows(replace(rows, orders=(foreign,)))


def test_verification_rejects_a_row_from_another_position() -> None:
    rows = build()
    foreign = {**rows.events[0], "position_id": 99}

    with pytest.raises(ValueError, match="does not belong to the position"):
        verify_lifecycle_rows(replace(rows, events=(foreign,)))


def test_verification_rejects_a_column_the_table_does_not_have() -> None:
    rows = build()
    drifted = {**rows.orders[0], "invented_column": 1}

    # A builder that drifts from the schema fails here rather than at the first
    # INSERT.
    with pytest.raises(ValueError, match="columns the table does not have"):
        verify_lifecycle_rows(replace(rows, orders=(drifted,)))


def test_as_record_reverifies_before_persisting() -> None:
    rows = build()
    foreign = {**rows.orders[0], "strategy_version": "swing_v1.1"}

    with pytest.raises(ValueError, match="not attributed to strategy_version"):
        replace(rows, orders=(foreign,)).as_record()


def test_verification_requires_the_real_type() -> None:
    with pytest.raises(TypeError, match="PaperTradeLifecycleRows"):
        verify_lifecycle_rows({"orders": ()})


# --- input validation -----------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"account_id": 0}, "account_id must be a positive integer"),
        ({"position_id": 0}, "position_id must be a positive integer"),
        ({"account_id": True}, "account_id must be a positive integer"),
    ],
)
def test_invalid_identifiers_fail_fast(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        build(**kwargs)


def test_a_non_execution_is_rejected() -> None:
    with pytest.raises(TypeError, match="as_order_record"):
        build(executions=[object()])


def test_a_non_provenance_is_rejected() -> None:
    with pytest.raises(TypeError, match="LifecycleProvenance"):
        build(provenance={"recommendation_id": 41})


# --- determinism ----------------------------------------------------------


def test_assembly_is_deterministic() -> None:
    assert build().as_record() == build().as_record()
    assert build().all_rows == build().all_rows


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    for rows in (build(), build(executions=[]), build(accounting=None)):
        for code in rows.reason_codes:
            assert code in LIFECYCLE_PERSISTENCE_REASON_CODES
