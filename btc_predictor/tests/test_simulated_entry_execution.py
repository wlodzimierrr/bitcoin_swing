"""BTC-161: deterministic simulated entry execution."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.db.portfolio import paper_orders
from btc_predictor.portfolio import (
    ENTER_ACTION,
    ENTRY_EXECUTION_FEATURE_ID,
    ENTRY_EXECUTION_POLICY_VERSION,
    ENTRY_EXECUTION_REASON_CODES,
    ENTRY_FILLED,
    ENTRY_MISSED,
    MARKET_ORDER,
    MISSED_ACTION,
    EntryExecutionIntent,
    ExecutionCosts,
    execution_costs_from_config,
    next_eligible_bar_timestamp,
    restore_simulated_entry_execution,
    simulate_next_bar_entry,
)


UTC = timezone.utc
DECISION_AT = datetime(2024, 8, 1, 12, tzinfo=UTC)
CONFIG_METADATA = load_strategy_config().run_metadata()


def intent(**kwargs) -> EntryExecutionIntent:
    base = {
        "execution_id": "entry-001",
        "recommendation_id": 41,
        "symbol": "BTC-USD",
        "direction": "long",
        "decision_at": DECISION_AT,
        "timeframe": "1h",
        "entry_zone_lower": Decimal("99000"),
        "entry_zone_upper": Decimal("101000"),
        "entry_zone_available_at": DECISION_AT - timedelta(minutes=1),
        "entry_zone_id": "cluster-17",
        "requested_quantity": Decimal("2"),
        "config_metadata": CONFIG_METADATA,
    }
    return EntryExecutionIntent(**{**base, **kwargs})


def bar(**kwargs) -> OhlcvBar:
    base = {
        "timestamp": DECISION_AT,
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "timeframe": "1h",
        "open": Decimal("100000"),
        "high": Decimal("102000"),
        "low": Decimal("98000"),
        "close": Decimal("100500"),
        "volume": Decimal("250"),
        "provider": "coinbase",
        "ingested_at": DECISION_AT + timedelta(hours=1, seconds=5),
    }
    return OhlcvBar(**{**base, **kwargs})


def costs() -> ExecutionCosts:
    return execution_costs_from_config()


def execute(**kwargs):
    return simulate_next_bar_entry(
        kwargs.pop("entry_intent", intent()),
        kwargs.pop("execution_bar", bar()),
        costs=kwargs.pop("execution_costs", costs()),
    )


def test_metadata_and_reason_code_catalog_are_stable() -> None:
    assert ENTRY_EXECUTION_FEATURE_ID == "SIMULATED_ENTRY_EXECUTION"
    assert ENTRY_EXECUTION_POLICY_VERSION == "SIMULATED_ENTRY_EXECUTION_V1"
    assert set(ENTRY_EXECUTION_REASON_CODES) == {
        "ENTRY_ZONE_TOUCHED",
        "ENTRY_ZONE_NOT_TOUCHED",
        "ENTRY_REFERENCE_BAR_OPEN",
        "ENTRY_REFERENCE_ZONE_LOWER",
        "ENTRY_REFERENCE_ZONE_UPPER",
        "ENTRY_EXECUTION_COSTS_APPLIED",
        "ENTRY_EXECUTION_FILLED",
        "ENTRY_EXECUTION_MISSED",
        "ENTRY_DO_NOT_CHASE",
    }


@pytest.mark.parametrize(
    ("decision_at", "timeframe", "expected"),
    [
        (DECISION_AT, "1h", DECISION_AT),
        (DECISION_AT + timedelta(seconds=1), "1h", DECISION_AT + timedelta(hours=1)),
        (
            datetime(2024, 8, 1, 12, tzinfo=UTC),
            "1d",
            datetime(2024, 8, 2, tzinfo=UTC),
        ),
        (
            datetime(2024, 8, 5, tzinfo=UTC),
            "1w",
            datetime(2024, 8, 5, tzinfo=UTC),
        ),
        (
            datetime(2024, 12, 20, tzinfo=UTC),
            "1mo",
            datetime(2025, 1, 1, tzinfo=UTC),
        ),
    ],
)
def test_first_full_bar_boundary_is_deterministic(
    decision_at: datetime,
    timeframe: str,
    expected: datetime,
) -> None:
    assert next_eligible_bar_timestamp(decision_at, timeframe) == expected


def test_long_fills_from_open_with_adverse_slippage_and_fee() -> None:
    result = execute()

    assert result.status == ENTRY_FILLED
    assert result.action == ENTER_ACTION
    assert result.filled is True and result.missed is False
    assert result.reference_price == Decimal("100000")
    assert result.average_fill_price == Decimal("100050.00000")
    assert result.average_fill_price > result.reference_price
    assert result.filled_quantity == Decimal("2")
    assert result.notional == Decimal("200100.0")
    assert result.slippage_cost == Decimal("100.0")
    assert result.fee == Decimal("200.10000")
    assert result.reason_codes == (
        "ENTRY_ZONE_TOUCHED",
        "ENTRY_REFERENCE_BAR_OPEN",
        "ENTRY_EXECUTION_COSTS_APPLIED",
        "ENTRY_EXECUTION_FILLED",
    )


def test_short_fill_is_adverse_and_uses_sell_side() -> None:
    result = execute(entry_intent=intent(direction="short"))

    assert result.intent.side == "sell"
    assert result.average_fill_price == Decimal("99950.00000")
    assert result.average_fill_price < result.reference_price


@pytest.mark.parametrize(
    ("execution_bar", "expected_reference", "reason"),
    [
        (
            bar(open=Decimal("103000"), high=Decimal("104000"), low=Decimal("100500")),
            Decimal("101000"),
            "ENTRY_REFERENCE_ZONE_UPPER",
        ),
        (
            bar(
                    open=Decimal("97000"),
                    high=Decimal("99500"),
                    low=Decimal("96000"),
                    close=Decimal("99200"),
                ),
            Decimal("99000"),
            "ENTRY_REFERENCE_ZONE_LOWER",
        ),
    ],
)
def test_gap_then_zone_touch_uses_first_reachable_boundary(
    execution_bar: OhlcvBar,
    expected_reference: Decimal,
    reason: str,
) -> None:
    result = execute(execution_bar=execution_bar)

    assert result.reference_price == expected_reference
    assert reason in result.reason_codes
    assert result.average_fill_price != expected_reference


@pytest.mark.parametrize(
    "execution_bar",
    [
        bar(
            open=Decimal("103000"),
            high=Decimal("104000"),
            low=Decimal("102000"),
            close=Decimal("103500"),
        ),
        bar(
            open=Decimal("97000"),
            high=Decimal("98000"),
            low=Decimal("96000"),
            close=Decimal("97500"),
        ),
    ],
)
def test_no_zone_overlap_is_terminally_missed(execution_bar: OhlcvBar) -> None:
    result = execute(execution_bar=execution_bar)

    assert result.status == ENTRY_MISSED
    assert result.action == MISSED_ACTION
    assert result.missed is True and result.filled is False
    assert result.reference_price is None
    assert result.average_fill_price is None
    assert result.filled_quantity == 0
    assert result.notional == result.fee == result.slippage_cost == 0
    assert result.reason_codes == (
        "ENTRY_ZONE_NOT_TOUCHED",
        "ENTRY_EXECUTION_MISSED",
        "ENTRY_DO_NOT_CHASE",
    )


@pytest.mark.parametrize(
    ("execution_bar", "expected_reference", "filled"),
    [
        (
            bar(
                open=Decimal("103000"),
                high=Decimal("104000"),
                low=Decimal("101000"),
                close=Decimal("103000"),
            ),
            Decimal("101000"),
            True,
        ),
        (
            bar(
                open=Decimal("103000"),
                high=Decimal("104000"),
                low=Decimal("101000.01"),
                close=Decimal("103000"),
            ),
            None,
            False,
        ),
        (
            bar(
                open=Decimal("97000"),
                high=Decimal("99000"),
                low=Decimal("96000"),
                close=Decimal("98000"),
            ),
            Decimal("99000"),
            True,
        ),
        (
            bar(
                open=Decimal("97000"),
                high=Decimal("98999.99"),
                low=Decimal("96000"),
                close=Decimal("98000"),
            ),
            None,
            False,
        ),
    ],
)
def test_the_zone_boundary_is_inclusive(
    execution_bar: OhlcvBar,
    expected_reference: Decimal | None,
    filled: bool,
) -> None:
    result = execute(execution_bar=execution_bar)

    # Touching a boundary exactly is inside the zone; missing it by a cent is
    # outside. This is the line the whole "respect entry zone" rule turns on.
    assert result.filled is filled
    assert result.reference_price == expected_reference


def test_later_bar_cannot_be_used_to_chase_a_missed_entry() -> None:
    later = replace(
        bar(),
        timestamp=DECISION_AT + timedelta(hours=1),
        ingested_at=DECISION_AT + timedelta(hours=2),
    )

    with pytest.raises(ValueError, match="first eligible full bar"):
        execute(execution_bar=later)


def test_a_decision_after_the_boundary_waits_for_the_next_full_bar() -> None:
    delayed = intent(decision_at=DECISION_AT + timedelta(seconds=5))
    next_bar = replace(
        bar(),
        timestamp=DECISION_AT + timedelta(hours=1),
        ingested_at=DECISION_AT + timedelta(hours=2, seconds=5),
    )

    result = execute(entry_intent=delayed, execution_bar=next_bar)

    assert result.intent.eligible_bar_at == DECISION_AT + timedelta(hours=1)


def test_monthly_execution_resolves_at_next_calendar_boundary() -> None:
    monthly_decision = datetime(2024, 12, 1, tzinfo=UTC)
    monthly_intent = intent(
        decision_at=monthly_decision,
        timeframe="1mo",
        entry_zone_available_at=monthly_decision,
    )
    monthly_bar = replace(
        bar(),
        timestamp=monthly_decision,
        timeframe="1mo",
        ingested_at=datetime(2025, 1, 1, 0, 1, tzinfo=UTC),
    )

    result = execute(entry_intent=monthly_intent, execution_bar=monthly_bar)

    assert result.resolved_at == datetime(2025, 1, 1, 0, 1, tzinfo=UTC)


def test_zone_must_have_been_available_at_decision_time() -> None:
    future_zone = intent(entry_zone_available_at=DECISION_AT + timedelta(seconds=1))

    with pytest.raises(ValueError, match="available by decision_at"):
        execute(entry_intent=future_zone)


@pytest.mark.parametrize(
    ("bad_intent", "match"),
    [
        (
            intent(entry_zone_lower=Decimal("102000")),
            "entry_zone_lower must be <= entry_zone_upper",
        ),
        (intent(requested_quantity=Decimal("0")), "requested_quantity must be positive"),
        (intent(direction="flat"), "direction must be one of"),
        (intent(config_metadata={}), "config_metadata must exactly contain"),
    ],
)
def test_invalid_intents_fail_fast(bad_intent: EntryExecutionIntent, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        execute(entry_intent=bad_intent)


@pytest.mark.parametrize(
    ("execution_bar", "match"),
    [
        (bar(symbol="ETH-USD"), "symbol must match"),
        (bar(high=Decimal("99000")), "impossible OHLC"),
        (bar(volume=Decimal("-1")), "volume must be non-negative"),
    ],
)
def test_invalid_execution_bars_fail_fast(execution_bar: OhlcvBar, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        execute(execution_bar=execution_bar)


def test_unknown_cost_policy_is_rejected() -> None:
    incompatible = replace(costs(), policy_version="EXECUTION_COST_V2")

    with pytest.raises(ValueError, match="costs.policy_version"):
        execute(execution_costs=incompatible)


def test_record_round_trip_retains_all_provenance() -> None:
    result = execute()
    record = result.as_record()

    restored = restore_simulated_entry_execution(record)

    assert restored == result
    assert record["intent"]["config_metadata"] == CONFIG_METADATA
    assert record["intent"]["entry_zone_id"] == "cluster-17"
    assert record["execution_bar"]["provider"] == "coinbase"
    assert record["costs"] == costs().as_record()


def test_tampered_record_is_rejected_by_replay() -> None:
    record = execute().as_record()
    record["average_fill_price"] = "1"

    with pytest.raises(ValueError, match="does not match reconstructed"):
        restore_simulated_entry_execution(record)


def test_order_record_matches_existing_schema_for_fill() -> None:
    order = execute().as_order_record(account_id=7)

    columns = {column.name for column in paper_orders.columns}
    assert set(order) <= columns
    # Execution knows the fill, not the run. BTC-166 stamps strategy identity
    # onto every row, so this module must not invent one.
    assert set(order) == columns - {
        "order_id",
        "strategy_version",
        "parameter_set_id",
    }
    assert order["action"] == "ENTER"
    assert order["side"] == "buy"
    assert order["order_type"] == MARKET_ORDER
    assert order["status"] == "filled"
    assert order["filled_at"] == DECISION_AT + timedelta(hours=1, seconds=5)
    assert order["limit_price"] is None


def test_order_record_marks_a_miss_without_a_fill_time_or_price() -> None:
    missed = execute(
        execution_bar=bar(
            open=Decimal("103000"),
            high=Decimal("104000"),
            low=Decimal("102000"),
            close=Decimal("103500"),
        )
    ).as_order_record(account_id=7)

    assert missed["action"] == "MISSED"
    assert missed["status"] == "missed"
    assert missed["filled_quantity"] == 0
    assert missed["filled_at"] is None
    assert missed["average_fill_price"] is None


def test_same_evidence_produces_the_same_result() -> None:
    first = execute()
    second = execute()

    assert first == second
    assert first.as_record() == second.as_record()
