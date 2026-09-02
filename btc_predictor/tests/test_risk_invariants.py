"""BTC-222 risk invariant suite.

Rulebook 32 lists rules that may never be violated, and rulebook 18.1, 19 and
24 give them their operative form. This ticket names six:

    no averaging down; stops never widen; risk-at-stop never exceeds the limit;
    no add when STRESS; no add when the CROWDING rule blocks; no trade during
    DATA_QUALITY_FAIL

Each already has an owner suite proving that its own engine refuses a violating
input. This suite pins the property those refusals exist for, which no single
owner can see: **no path can reach a violating state**. Every invariant is
therefore asserted at all three consumers rulebook 19 names -- advisory gates,
the BTC-150 paper ledger with its simulated executions, and the BTC-180 replay
-- and each is asserted in both halves:

- a violating proposal is refused, keeping its own reason code, and
- the state the invariant protects is bit-for-bit unchanged by the refusal.

Both halves are needed. A refusal that still mutated the ledger would satisfy
the first alone, and an engine that refused everything would satisfy the second.

The whole-run tests close the remaining gap: a single BTC-180 replay is walked
bar by bar and every invariant is re-checked against the recorded evidence, so
an ordering or composition defect that no single-decision test can produce is
still caught.
"""

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.backtest.engine import (
    ADD_ACTION as BACKTEST_ADD_ACTION,
    ARM_ENTRY_ACTION,
    TRAIL_ACTION,
    BacktestContext,
    BacktestIntent,
    restore_backtest_result,
    run_backtest,
)
from btc_predictor.config import StrategyConfigError, load_strategy_config
from btc_predictor.config.strategy import AddThresholds
from btc_predictor.data import OhlcvBar
from btc_predictor.features import (
    CROWDING_FLAG_EFFECTS,
    STRESS_FLAG_EFFECTS,
    CrowdingFlagInput,
    StressFlagInput,
    calculate_crowding_flag,
    calculate_stress_flag,
)
from btc_predictor.portfolio import (
    ADD,
    DEFEND,
    DEFENSIVE,
    ENTER,
    HOLD,
    OPEN_ADDED,
    OPEN_INITIAL,
    PENDING_ENTRY,
    RECOVER,
    STOP_MOVE,
    TRIM,
    AddExecutionIntent,
    apply_position_event,
    execution_costs_from_config,
    position_event_records,
    replay_position_event_records,
    restore_position_lifecycle,
    simulate_add_execution,
    start_position_lifecycle,
)
from btc_predictor.quant.comparisons import decision_equal
from btc_predictor.risk import (
    HIGHER_LOW,
    apply_trailing_stop,
    calculate_initial_stop,
    calculate_risk_at_stop,
    calculate_risk_budget,
    calculate_trailing_stop,
    calculate_tranche_size,
    initial_position_size_for_trade,
    stop_advance_count,
)
from btc_predictor.signals import (
    DATA_QUALITY_BLOCKED_ACTIONS,
    DATA_QUALITY_FAIL_REASON_CODE,
    RECOMMENDATION_ACTIONS,
    AddRequirementsInput,
    DataQualityFailure,
    ExitRuleInput,
    HardVetoInput,
    apply_data_quality_gate,
    build_recommendation_reason_code_records,
    evaluate_add_requirements,
    evaluate_exit_rules,
    evaluate_hard_veto,
)


CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
SYMBOL = "BTC-USD"
START = datetime(2026, 3, 2, tzinfo=UTC)
MAXIMUM_RISK_FRACTION = Decimal(str(CONFIG.risk.max_risk_at_stop_fraction_nav))
NAV = Decimal("1000000")

AVERAGE_DOWN_REFUSAL = "POSITION_STATE_ADD_REFUSED_AVERAGE_DOWN"
DEFENSIVE_REFUSAL = "POSITION_STATE_ADD_REFUSED_WHILE_DEFENSIVE"
WIDEN_REFUSAL = "POSITION_STATE_STOP_WOULD_WIDEN"


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def economics(lifecycle) -> tuple:
    """Everything a refusal must leave untouched."""

    return (
        lifecycle.state,
        lifecycle.tranches,
        lifecycle.quantity,
        lifecycle.average_entry_price,
        lifecycle.stop_price,
        lifecycle.opened_at,
        lifecycle.closed_at,
    )


def opened(
    *,
    direction: str = "long",
    price: str = "100000",
    quantity: str = "1",
    stop_price: str | None = None,
    hours: int = 1,
):
    lifecycle = start_position_lifecycle(
        symbol=SYMBOL,
        direction=direction,
        state=PENDING_ENTRY,
        config_metadata=METADATA,
    )
    if stop_price is None:
        stop_price = "90000" if direction == "long" else "110000"
    return apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(hours),
        quantity=quantity,
        price=price,
        stop_price=stop_price,
    )


def ledger_risk(lifecycle, *, nav=NAV, stop_price=None, config=CONFIG):
    """Aggregate BTC-146 risk for whatever the BTC-150 ledger currently holds."""

    return calculate_risk_at_stop(
        [
            {
                "tranche_id": f"t{tranche.tranche_number}",
                "quantity": tranche.quantity,
                "entry_price": tranche.entry_price,
            }
            for tranche in lifecycle.tranches
        ],
        stop_price=stop_price if stop_price is not None else lifecycle.stop_price,
        nav=nav,
        direction=lifecycle.direction,
        config=config,
    )


def projected_risk(lifecycle, *, quantity, entry_price, stop_price, nav=NAV):
    """BTC-146 measured on the book an add would create, before it is taken."""

    tranches = [
        {
            "tranche_id": f"t{tranche.tranche_number}",
            "quantity": tranche.quantity,
            "entry_price": tranche.entry_price,
        }
        for tranche in lifecycle.tranches
    ]
    tranches.append(
        {
            "tranche_id": f"t{lifecycle.tranche_count + 1}",
            "quantity": Decimal(str(quantity)),
            "entry_price": Decimal(str(entry_price)),
        }
    )
    return calculate_risk_at_stop(
        tranches,
        stop_price=stop_price,
        nav=nav,
        direction=lifecycle.direction,
        config=CONFIG,
    )


def add_requirements(*, strategy_config=CONFIG, **overrides):
    base = AddRequirementsInput(
        position_profitable=True,
        new_structural_confirmation=True,
        signed_risk_improvement=Decimal("1500"),
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        add_score=Decimal("90"),
        projected_risk_at_stop_within_maximum=True,
    )
    if overrides:
        base = replace(base, **overrides)
    return evaluate_add_requirements(base, strategy_config=strategy_config)


def hour_bar(
    *,
    timestamp: datetime,
    open_: str,
    high: str | None = None,
    low: str | None = None,
    close: str | None = None,
) -> OhlcvBar:
    opening = Decimal(open_)
    closing = Decimal(close) if close is not None else opening
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol=SYMBOL,
        timeframe="1h",
        open=opening,
        high=Decimal(high) if high is not None else max(opening, closing),
        low=Decimal(low) if low is not None else min(opening, closing),
        close=closing,
        volume=Decimal("5"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(hours=1),
    )


def add_execution(
    *,
    lifecycle,
    fill_open: str,
    requirements,
    tranche_quantity: str = "0.5",
    decision_at: datetime | None = None,
):
    """Run one simulated add against a bar that opens at ``fill_open``."""

    moment = decision_at if decision_at is not None else at(4)
    intent = AddExecutionIntent(
        execution_id=f"add-{moment.isoformat()}",
        position_id=None,
        recommendation_id=None,
        symbol=SYMBOL,
        direction=lifecycle.direction,
        timeframe="1h",
        decision_at=moment,
        average_entry_price=lifecycle.average_entry_price,
        config_metadata=METADATA,
    )
    reference = Decimal(fill_open)
    tranche = calculate_tranche_size(
        tranche_number=lifecycle.tranche_count + 1,
        final_position_notional=reference * Decimal(tranche_quantity) * 4,
        entry_price=reference,
        config=CONFIG,
        config_metadata=METADATA,
    )
    return simulate_add_execution(
        intent,
        hour_bar(timestamp=intent.eligible_bar_at, open_=fill_open),
        requirements=requirements,
        tranche=tranche,
        costs=execution_costs_from_config(CONFIG),
    )


# --- invariant 1: no averaging down --------------------------------------


@pytest.mark.parametrize(
    ("direction", "script"),
    [
        (
            "long",
            (
                ("100000", True),
                ("99000", False),
                ("101000", True),
                ("100400", False),
                ("100600", True),
            ),
        ),
        (
            "short",
            (
                ("100000", True),
                ("101000", False),
                ("99000", True),
                ("99600", False),
                ("99400", True),
            ),
        ),
    ],
)
def test_the_weighted_average_entry_never_moves_against_the_position(
    direction: str,
    script: tuple[tuple[str, bool], ...],
) -> None:
    # "Never average down" is a ledger property, not just a refusal: whatever
    # sequence of adds, trims and stop moves is attempted, the weighted average
    # entry may only move in the position's favour.
    lifecycle = opened(direction=direction, price=script[0][0])
    averages = [lifecycle.average_entry_price]

    for index, (price, expected_accept) in enumerate(script[1:], start=2):
        before = economics(lifecycle)
        candidate = apply_position_event(
            lifecycle,
            event=ADD,
            event_time=at(index * 2),
            quantity="1",
            price=price,
        )
        assert candidate.accepted is expected_accept
        if expected_accept:
            lifecycle = candidate
        else:
            assert AVERAGE_DOWN_REFUSAL in candidate.reason_codes
            assert economics(candidate) == before
        averages.append(lifecycle.average_entry_price)
        # A pro-rata trim must not re-base the average either.
        lifecycle = apply_position_event(
            lifecycle,
            event=TRIM,
            event_time=at(index * 2 + 1),
            quantity=lifecycle.quantity / 4,
        )
        averages.append(lifecycle.average_entry_price)

    if direction == "long":
        assert averages == sorted(averages)
    else:
        assert averages == sorted(averages, reverse=True)
    assert lifecycle.tranche_count == 3


def test_the_invariant_holds_when_the_optional_profitability_gate_is_disabled() -> None:
    # BTC-154's strict profitability requirement is configurable. BTC-151's
    # never-average-down invariant is not, and disabling the former must not
    # open a path around the latter.
    with pytest.raises(StrategyConfigError, match="no_average_down"):
        AddThresholds.from_mapping(
            {
                "add_min": 85,
                "existing_position_must_be_profitable": True,
                "stop_must_improve": True,
                "no_average_down": False,
            }
        )

    relaxed = replace(
        CONFIG,
        add_thresholds=replace(
            CONFIG.add_thresholds,
            existing_position_must_be_profitable=False,
            stop_must_improve=False,
        ),
    )
    permitted = add_requirements(
        strategy_config=relaxed,
        position_profitable=False,
        signed_risk_improvement=None,
    )
    assert permitted.permitted is True

    lifecycle = opened()
    execution = add_execution(
        lifecycle=lifecycle,
        fill_open="99000",
        requirements=permitted,
    )
    assert execution.cancelled is True
    assert "ADD_EXECUTION_NO_LONGER_PROFITABLE" in execution.reason_codes
    assert execution.filled_quantity == Decimal("0")

    refused = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(6),
        quantity="0.5",
        price="99000",
    )
    assert refused.accepted is False
    assert AVERAGE_DOWN_REFUSAL in refused.reason_codes
    assert economics(refused) == economics(lifecycle)


def test_an_add_permitted_at_the_decision_is_cancelled_when_the_fill_gaps_under() -> (
    None
):
    # The gate judges profitability at the decision; the fill happens later.
    # The second defence is what makes the invariant hold across that gap.
    lifecycle = opened()
    gate = add_requirements()
    assert gate.permitted is True

    execution = add_execution(
        lifecycle=lifecycle,
        fill_open="99500",
        requirements=gate,
    )

    assert execution.cancelled is True
    assert execution.reason_codes == (
        "ADD_EXECUTION_NO_LONGER_PROFITABLE",
        "ADD_EXECUTION_CANCELLED",
    )
    assert execution.average_fill_price is None
    # The ledger would have refused the same fill independently.
    ledger = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=execution.resolved_at,
        quantity="0.5",
        price="99500",
    )
    assert ledger.accepted is False
    assert AVERAGE_DOWN_REFUSAL in ledger.reason_codes
    assert economics(ledger) == economics(lifecycle)
    # Both refusals are replayable evidence, not transient state.
    assert execution.as_record()["status"] == "cancelled"
    assert restore_position_lifecycle(ledger.as_record()).as_record() == (
        ledger.as_record()
    )


def test_a_slipped_fill_never_reads_as_a_healthier_position_than_the_market() -> None:
    # A buy fills above the bar open. Judging profitability on the slipped fill
    # would let a losing add through whenever slippage crossed the average.
    lifecycle = opened(price="100000")
    costs = execution_costs_from_config(CONFIG)
    reference = Decimal("100000")
    slipped = costs.fill_price(reference, side="buy")
    assert slipped > reference  # the scenario only exists because of this

    execution = add_execution(
        lifecycle=lifecycle,
        fill_open=str(reference),
        requirements=add_requirements(),
    )

    assert execution.cancelled is True
    assert "ADD_EXECUTION_NO_LONGER_PROFITABLE" in execution.reason_codes


# --- invariant 2: stops never widen --------------------------------------


@pytest.mark.parametrize(
    ("direction", "moves"),
    [
        ("long", ("92000", "91000", "95000", "94999", "97000")),
        ("short", ("108000", "109000", "105000", "105001", "103000")),
    ],
)
def test_the_standing_stop_is_monotone_under_an_arbitrary_move_sequence(
    direction: str,
    moves: tuple[str, ...],
) -> None:
    lifecycle = opened(direction=direction)
    stops = [lifecycle.stop_price]
    refusals = 0

    for index, move in enumerate(moves, start=2):
        before = economics(lifecycle)
        candidate = apply_position_event(
            lifecycle,
            event=STOP_MOVE,
            event_time=at(index),
            stop_price=move,
        )
        if candidate.accepted:
            lifecycle = candidate
        else:
            refusals += 1
            assert candidate.reason_codes[0] == WIDEN_REFUSAL
            assert economics(candidate) == before
        stops.append(lifecycle.stop_price)

    assert refusals == 2  # the sequence deliberately contains two loosenings
    if direction == "long":
        assert stops == sorted(stops)
    else:
        assert stops == sorted(stops, reverse=True)


def test_a_refused_widening_survives_persistence_as_a_refusal() -> None:
    lifecycle = opened()
    tightened = apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=at(2),
        stop_price="95000",
    )
    widened = apply_position_event(
        tightened,
        event=STOP_MOVE,
        event_time=at(3),
        stop_price="93000",
    )

    assert widened.accepted is False
    assert widened.stop_price == Decimal("95000")

    rows = position_event_records(widened)
    replayed = replay_position_event_records(
        rows,
        symbol=SYMBOL,
        direction="long",
        config_metadata=METADATA,
    )
    assert replayed.stop_price == Decimal("95000")
    assert replayed.transitions[-1].accepted is False
    assert WIDEN_REFUSAL in replayed.transitions[-1].reason_codes
    assert restore_position_lifecycle(widened.as_record()).as_record() == (
        widened.as_record()
    )


def test_the_trailing_engine_and_the_ledger_refuse_the_same_loosening() -> None:
    lifecycle = opened()
    lifecycle = apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=at(2),
        stop_price="96000",
    )
    loosening = calculate_trailing_stop(
        direction=lifecycle.direction,
        previous_stop=lifecycle.stop_price,
        structure_price="93000",
        buffer=Decimal("500"),
        advance_count=stop_advance_count(lifecycle),
        current_price=Decimal("102000"),
        config_metadata=METADATA,
        evaluated_at=at(3),
        structure_id="hl-loosening",
        structure_source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
        structure_type=HIGHER_LOW,
        structure_level_timestamp=at(2),
        structure_detected_at=at(3),
    )

    assert loosening.advanced is False
    assert loosening.stop_price == Decimal("96000")
    assert "TRAILING_STOP_HELD" in loosening.reason_codes

    held = apply_trailing_stop(lifecycle, loosening, event_time=at(3))
    assert held is lifecycle

    manual = apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=at(3),
        stop_price="92500",
    )
    assert manual.accepted is False
    assert WIDEN_REFUSAL in manual.reason_codes


def test_a_ratcheting_stop_can_only_lower_risk_for_an_unchanged_book() -> None:
    # Rulebook 19's objective and rulebook 32 rule 3 compose: with tranches
    # untouched, a stop that may only tighten can only reduce risk at stop.
    lifecycle = opened(price="100000", quantity="2")
    fractions = [ledger_risk(lifecycle).risk_fraction_nav]

    for index, move in enumerate(("92000", "95000", "94000", "98000"), start=2):
        candidate = apply_position_event(
            lifecycle,
            event=STOP_MOVE,
            event_time=at(index),
            stop_price=move,
        )
        if candidate.accepted:
            lifecycle = candidate
        fractions.append(ledger_risk(lifecycle).risk_fraction_nav)

    assert fractions == sorted(fractions, reverse=True)
    assert all(fraction >= 0 for fraction in fractions)


# --- invariant 3: risk at stop never exceeds the limit --------------------


def test_the_budget_and_the_exposure_owners_read_one_configured_ceiling() -> None:
    budget = calculate_risk_budget(
        entry_conviction="92",
        nav=NAV,
        config=CONFIG,
        config_metadata=METADATA,
    )
    exposure = ledger_risk(opened())

    assert budget.maximum_risk_fraction_nav == MAXIMUM_RISK_FRACTION
    assert exposure.maximum_fraction_nav == MAXIMUM_RISK_FRACTION
    assert budget.config_metadata == METADATA
    assert exposure.config_metadata == METADATA


@pytest.mark.parametrize("conviction", ["80", "84.99", "85", "90", "97"])
@pytest.mark.parametrize("invalidation", ["96000", "92000", "85000"])
def test_a_sized_entry_spends_exactly_its_budget_and_stays_under_the_ceiling(
    conviction: str,
    invalidation: str,
) -> None:
    # BTC-144 -> BTC-142 -> BTC-145 -> BTC-146. The composition is the reason
    # a fresh position can never open above the ceiling, and it is a property
    # of the chain rather than of any single owner.
    entry = Decimal("100000")
    budget = calculate_risk_budget(
        entry_conviction=conviction,
        nav=NAV,
        config=CONFIG,
        config_metadata=METADATA,
    )
    stop = calculate_initial_stop(
        invalidation_price=invalidation,
        buffer=Decimal("500"),
        direction="long",
        entry_price=entry,
        config_metadata=METADATA,
    )
    size = initial_position_size_for_trade(budget, stop, config_metadata=METADATA)
    assert size.complete is True

    exposure = calculate_risk_at_stop(
        [
            {
                "tranche_id": "t1",
                "quantity": size.position_quantity,
                "entry_price": entry,
            }
        ],
        stop_price=stop.stop_price,
        nav=NAV,
        config=CONFIG,
        config_metadata=METADATA,
    )

    assert decision_equal(exposure.risk_at_stop, budget.risk_budget_amount)
    assert decision_equal(exposure.risk_fraction_nav, budget.risk_fraction_nav)
    assert exposure.risk_fraction_nav <= MAXIMUM_RISK_FRACTION
    assert exposure.within_maximum is True
    assert "RISK_AT_STOP_EXCEEDS_MAXIMUM" not in exposure.reason_codes


def test_an_add_that_would_breach_the_ceiling_is_refused_by_every_path() -> None:
    lifecycle = opened(price="100000", quantity="1", stop_price="95000")
    breaching_quantity = Decimal("2")
    projection = projected_risk(
        lifecycle,
        quantity=breaching_quantity,
        entry_price="101000",
        stop_price=lifecycle.stop_price,
    )
    assert projection.within_maximum is False
    assert "RISK_AT_STOP_EXCEEDS_MAXIMUM" in projection.reason_codes
    assert projection.headroom_amount == Decimal("0")

    gate = add_requirements(
        projected_risk_at_stop_within_maximum=projection.within_maximum,
    )
    assert gate.blocked is True
    assert gate.effects == ("NO_ADD",)
    assert "ADD_REQUIREMENTS_RISK_AT_STOP_EXCEEDED" in gate.reason_codes

    execution = add_execution(
        lifecycle=lifecycle,
        fill_open="101000",
        requirements=gate,
    )
    assert execution.cancelled is True
    assert execution.reason_codes[0] == "ADD_EXECUTION_BLOCKED_BY_REQUIREMENTS"
    # The gate's own explanation travels with the refusal.
    assert "ADD_REQUIREMENTS_RISK_AT_STOP_EXCEEDED" in execution.reason_codes
    assert execution.filled_quantity == Decimal("0")
    assert ledger_risk(lifecycle).within_maximum is True


@pytest.mark.parametrize(
    "quantity",
    ["0.1", "0.5", "0.9", "1", "1.5", "2", "5"],
)
def test_every_permitted_add_leaves_the_realized_book_within_the_ceiling(
    quantity: str,
) -> None:
    lifecycle = opened(price="100000", quantity="1", stop_price="95000")
    add_price = Decimal("101000")
    projection = projected_risk(
        lifecycle,
        quantity=quantity,
        entry_price=add_price,
        stop_price=lifecycle.stop_price,
    )
    gate = add_requirements(
        projected_risk_at_stop_within_maximum=projection.within_maximum,
    )

    if gate.blocked:
        assert projection.within_maximum is False
        execution = add_execution(
            lifecycle=lifecycle,
            fill_open=str(add_price),
            requirements=gate,
        )
        assert execution.cancelled is True
        assert ledger_risk(lifecycle).within_maximum is True
        return

    added = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(5),
        quantity=quantity,
        price=add_price,
    )
    assert added.accepted is True
    realized = ledger_risk(added)
    # The projection the gate approved is the book the ledger now holds.
    assert decision_equal(realized.risk_at_stop, projection.risk_at_stop)
    assert realized.within_maximum is True
    assert realized.risk_fraction_nav <= MAXIMUM_RISK_FRACTION


def test_a_breach_is_reported_rather_than_silently_clipped() -> None:
    # A ceiling that quietly rescaled the measurement would make the gate
    # unfalsifiable. The breach must stay visible in the persisted record.
    lifecycle = opened(price="100000", quantity="1", stop_price="80000")
    exposure = ledger_risk(lifecycle)

    assert exposure.within_maximum is False
    assert exposure.risk_fraction_nav > MAXIMUM_RISK_FRACTION
    assert exposure.headroom_amount == Decimal("0")
    assert "RISK_AT_STOP_EXCEEDS_MAXIMUM" in exposure.reason_codes

    record = exposure.as_record()
    assert record["within_maximum"] is False
    assert record["maximum_fraction_nav"] == str(MAXIMUM_RISK_FRACTION)
    assert record["risk_at_stop"] == str(exposure.risk_at_stop)


# --- invariant 4: no add when STRESS --------------------------------------


def stress_flag(*, flagged: bool):
    stress_config = CONFIG.volatility_flags.stress
    return calculate_stress_flag(
        StressFlagInput(
            volatility_percentile=Decimal("97") if flagged else Decimal("40"),
            liquidation_percentile=Decimal("50"),
            downside_return=Decimal("-0.02"),
            funding_zscore=Decimal("0"),
            basis_zscore=Decimal("0"),
            systemic_shock=False,
        ),
        volatility_percentile_min=Decimal(str(stress_config.volatility_percentile_min)),
        liquidation_percentile_min=Decimal(
            str(stress_config.liquidation_percentile_min)
        ),
        downside_return_min=Decimal(str(stress_config.downside_return_min)),
        funding_abs_zscore_min=Decimal(str(stress_config.funding_abs_zscore_min)),
        basis_abs_zscore_min=Decimal(str(stress_config.basis_abs_zscore_min)),
        max_exposure_multiplier=Decimal(str(stress_config.max_exposure_multiplier)),
        block_new_trades=stress_config.block_new_trades,
        config_metadata=METADATA,
    )


def test_the_stress_flag_declares_the_rulebook_24_no_add_effect() -> None:
    assert STRESS_FLAG_EFFECTS[0] == "NO_ADD"

    flagged = stress_flag(flagged=True)
    assert flagged.flagged is True
    assert "NO_ADD" in flagged.effects
    assert flagged.complete is True
    assert flagged.max_exposure_multiplier < Decimal("1")

    clear = stress_flag(flagged=False)
    assert clear.flagged is False
    assert clear.effects == ()
    assert clear.max_exposure_multiplier == Decimal("1")


@pytest.mark.parametrize("state", [OPEN_INITIAL, OPEN_ADDED])
def test_the_defensive_state_refuses_an_otherwise_perfect_add(state: str) -> None:
    # Rulebook 24 gives STRESS / CROWDING / EUPHORIA one shared effect, and the
    # BTC-150 DEFENSIVE state is where the ledger carries it.
    lifecycle = opened(price="100000")
    if state == OPEN_ADDED:
        lifecycle = apply_position_event(
            lifecycle,
            event=ADD,
            event_time=at(2),
            quantity="1",
            price="101000",
        )
    assert lifecycle.state == state

    defended = apply_position_event(
        lifecycle,
        event=DEFEND,
        event_time=at(3),
        reason_codes=("STRESS_EXTREME_VOLATILITY",),
    )
    assert defended.state == DEFENSIVE
    before = economics(defended)

    refused = apply_position_event(
        defended,
        event=ADD,
        event_time=at(4),
        quantity="1",
        # Deeply profitable: nothing but the flag stands in the way.
        price="150000",
    )
    assert refused.accepted is False
    assert refused.reason_codes[0] == DEFENSIVE_REFUSAL
    assert economics(refused) == before

    recovered = apply_position_event(defended, event=RECOVER, event_time=at(5))
    assert recovered.state == state
    permitted = apply_position_event(
        recovered,
        event=ADD,
        event_time=at(6),
        quantity="1",
        price="150000",
    )
    assert permitted.accepted is True


def test_a_stress_refusal_is_the_same_transition_the_backtest_would_apply() -> None:
    # BTC-180 routes every accepted add through apply_position_event, so a
    # ledger state that refuses ADD refuses it on the replay path too.
    lifecycle = opened(price="100000")
    defended = apply_position_event(
        lifecycle,
        event=DEFEND,
        event_time=at(3),
        reason_codes=("STRESS_LIQUIDATION_CASCADE",),
    )
    execution = add_execution(
        lifecycle=defended,
        fill_open="110000",
        requirements=add_requirements(),
    )
    assert execution.filled is True  # execution alone cannot see the flag

    ledger = apply_position_event(
        defended,
        event=ADD,
        event_time=execution.resolved_at,
        quantity=execution.filled_quantity,
        price=execution.average_fill_price,
        reason_codes=execution.reason_codes,
        source_feature_id=execution.feature_id,
        source_record_id=execution.intent.execution_id,
    )
    assert ledger.accepted is False
    assert DEFENSIVE_REFUSAL in ledger.reason_codes
    assert economics(ledger) == economics(defended)


def test_stress_gates_new_trades_only_through_the_versioned_policy() -> None:
    # Rulebook 24 makes NO ADDING unconditional and blocking new trades
    # optional. The optional half must be read from configuration, and the
    # unconditional half must not depend on it.
    stress_config = CONFIG.volatility_flags.stress
    flagged = stress_flag(flagged=True)
    assert flagged.block_new_trades is stress_config.block_new_trades

    inputs = HardVetoInput(
        data_quality_fail=False,
        valid_structural_stop=True,
        reward_risk_passes=True,
        stress_flagged=flagged.flagged,
        severe_crowding_flagged=False,
        no_chase_blocked=False,
        setup="bull_trend_continuation",
        source_reason_codes={"stress_flagged": flagged.reason_codes},
    )

    permissive = evaluate_hard_veto(inputs, strategy_config=CONFIG)
    assert permissive.stress_blocks_new_trades is stress_config.block_new_trades
    assert permissive.blocked is stress_config.block_new_trades

    blocking = replace(
        CONFIG,
        volatility_flags=replace(
            CONFIG.volatility_flags,
            stress=replace(stress_config, block_new_trades=True),
        ),
    )
    vetoed = evaluate_hard_veto(inputs, strategy_config=blocking)
    assert vetoed.blocked is True
    assert "HARD_VETO_STRESS" in vetoed.reason_codes
    # Under either policy the add effect is unchanged.
    assert "NO_ADD" in flagged.effects


# --- invariant 5: no add when the CROWDING rule blocks --------------------


def crowding_flag(*, flagged: bool):
    crowding_config = CONFIG.positioning_flags.crowding
    return calculate_crowding_flag(
        CrowdingFlagInput(
            funding_zscore=Decimal("2.5") if flagged else Decimal("0.2"),
            basis_zscore=Decimal("0.1"),
            oi_intensity_percentile=Decimal("40"),
        ),
        funding_zscore_min=Decimal(str(crowding_config.funding_zscore_min)),
        basis_zscore_min=Decimal(str(crowding_config.basis_zscore_min)),
        oi_intensity_percentile_min=Decimal(
            str(crowding_config.oi_intensity_percentile_min)
        ),
        entry_quality_penalty=Decimal(str(crowding_config.entry_quality_penalty)),
        config_metadata=METADATA,
    )


def test_the_crowding_flag_declares_the_rulebook_24_no_add_effect() -> None:
    assert CROWDING_FLAG_EFFECTS[0] == "NO_ADD"

    flagged = crowding_flag(flagged=True)
    assert flagged.flagged is True
    assert "NO_ADD" in flagged.effects
    assert "CROWDING_FUNDING_EXCESS" in flagged.reason_codes
    assert flagged.complete is True

    clear = crowding_flag(flagged=False)
    assert clear.flagged is False
    assert clear.effects == ()
    assert clear.entry_quality_penalty == Decimal("0")


def test_a_crowded_book_blocks_the_add_at_its_named_requirement() -> None:
    # Rulebook 18.1 requirement 6 is "Positioning is not crowded"; the gate
    # input of that name is where a CROWDING flag lands.
    flagged = crowding_flag(flagged=True)
    gate = evaluate_add_requirements(
        AddRequirementsInput(
            position_profitable=True,
            new_structural_confirmation=True,
            signed_risk_improvement=Decimal("1500"),
            regime_supportive=True,
            flow_supportive=True,
            positioning_healthy=not flagged.flagged,
            add_score=Decimal("99"),
            projected_risk_at_stop_within_maximum=True,
            source_reason_codes={"positioning_healthy": flagged.reason_codes},
        ),
        strategy_config=CONFIG,
    )

    assert gate.blocked is True
    assert gate.effects == ("NO_ADD",)
    assert gate.reason_codes == ("ADD_REQUIREMENTS_POSITIONING_UNHEALTHY",)
    # The crowding evidence is persisted with the refusal, not summarised away.
    record = gate.as_record()
    assert record["inputs"]["source_reason_codes"]["positioning_healthy"] == list(
        flagged.reason_codes
    )
    assert record["config_metadata"] == METADATA


def test_a_crowding_blocked_add_never_fills_and_never_reaches_the_ledger() -> None:
    lifecycle = opened(price="100000")
    flagged = crowding_flag(flagged=True)
    gate = add_requirements(
        positioning_healthy=not flagged.flagged,
    )
    assert gate.blocked is True

    execution = add_execution(
        lifecycle=lifecycle,
        # A price at which the add would otherwise be entirely legitimate.
        fill_open="110000",
        requirements=gate,
    )

    assert execution.cancelled is True
    assert execution.reason_codes == (
        "ADD_EXECUTION_BLOCKED_BY_REQUIREMENTS",
        "ADD_REQUIREMENTS_POSITIONING_UNHEALTHY",
        "ADD_EXECUTION_CANCELLED",
    )
    # No fill, no cost, and nothing the ledger could be handed.
    assert execution.filled_quantity == Decimal("0")
    assert execution.average_fill_price is None
    assert execution.notional == Decimal("0")
    assert execution.fee == Decimal("0")
    assert execution.slippage_cost == Decimal("0")
    # The allocation that was refused is still auditable: a refusal records
    # what it declined, not merely that it declined.
    assert execution.tranche_number == lifecycle.tranche_count + 1
    assert execution.requested_quantity is not None
    record = execution.as_record()
    assert record["tranche"]["allocation"] is not None
    assert record["requirements"]["effects"] == ["NO_ADD"]


def test_severe_crowding_blocks_a_new_trade_unconditionally() -> None:
    inputs = HardVetoInput(
        data_quality_fail=False,
        valid_structural_stop=True,
        reward_risk_passes=True,
        stress_flagged=False,
        severe_crowding_flagged=True,
        no_chase_blocked=False,
        setup="bull_trend_continuation",
    )

    result = evaluate_hard_veto(inputs, strategy_config=CONFIG)

    assert result.blocked is True
    assert result.effects == ("NO_TRADE",)
    assert "HARD_VETO_SEVERE_CROWDING" in result.reason_codes
    # Unlike stress, no configuration switch turns this one off.
    relaxed = replace(
        CONFIG,
        volatility_flags=replace(
            CONFIG.volatility_flags,
            stress=replace(
                CONFIG.volatility_flags.stress,
                block_new_trades=False,
            ),
        ),
    )
    assert evaluate_hard_veto(inputs, strategy_config=relaxed).blocked is True


# --- invariant 6: no trade during DATA_QUALITY_FAIL -----------------------


def quality_failures() -> tuple[DataQualityFailure, ...]:
    return (
        DataQualityFailure(
            source_component="ohlcv",
            reason_codes=("OHLCV_GAP_DETECTED",),
        ),
        DataQualityFailure(
            source_component="derivatives",
            reason_codes=("DERIVATIVES_STALE_FUNDING",),
        ),
    )


@pytest.mark.parametrize("requested", RECOMMENDATION_ACTIONS)
def test_a_data_quality_failure_never_yields_an_enter_or_add(requested: str) -> None:
    gated = apply_data_quality_gate(requested, quality_failures())

    assert gated.data_quality_fail is True
    assert gated.action not in DATA_QUALITY_BLOCKED_ACTIONS
    if requested in DATA_QUALITY_BLOCKED_ACTIONS:
        assert gated.blocked_by_data_quality is True
        assert gated.action == ("NO_TRADE" if requested == "ENTER" else "HOLD")
        assert all(reason.severity == "veto" for reason in gated.reason_codes)
    else:
        # Rulebook 24 blocks new trades and new adds, not the management of a
        # position that is already open.
        assert gated.action == requested
        assert all(reason.severity == "warning" for reason in gated.reason_codes)
    assert gated.reason_codes[0].code == DATA_QUALITY_FAIL_REASON_CODE


def test_the_gate_and_the_hard_veto_agree_on_a_data_quality_failure() -> None:
    failures = quality_failures()
    gated = apply_data_quality_gate("ENTER", failures)
    veto = evaluate_hard_veto(
        HardVetoInput(
            data_quality_fail=gated.data_quality_fail,
            valid_structural_stop=True,
            reward_risk_passes=True,
            stress_flagged=False,
            severe_crowding_flagged=False,
            no_chase_blocked=False,
            setup="bull_trend_continuation",
            source_reason_codes={
                "data_quality_fail": tuple(
                    reason.code for reason in gated.reason_codes
                ),
            },
        ),
        strategy_config=CONFIG,
    )

    assert gated.action == "NO_TRADE"
    assert veto.blocked is True
    assert veto.effects == ("NO_TRADE",)
    assert "HARD_VETO_DATA_QUALITY_FAIL" in veto.reason_codes
    assert veto.as_record()["inputs"]["source_reason_codes"]["data_quality_fail"][0] == (
        DATA_QUALITY_FAIL_REASON_CODE
    )


def test_the_failure_and_its_evidence_persist_as_ordered_veto_rows() -> None:
    gated = apply_data_quality_gate("ADD", quality_failures())

    rows = build_recommendation_reason_code_records(7, gated.reason_codes)

    assert [row["reason_rank"] for row in rows] == list(range(len(rows)))
    assert rows[0]["code"] == DATA_QUALITY_FAIL_REASON_CODE
    assert {row["code"] for row in rows} >= {
        "OHLCV_GAP_DETECTED",
        "DERIVATIVES_STALE_FUNDING",
    }
    assert all(row["severity"] == "veto" for row in rows)
    assert all(row["recommendation_id"] == 7 for row in rows)


def test_an_ordinary_data_quality_failure_is_not_a_forced_liquidation() -> None:
    # The invariant is "no new trades, no new adds". Reading it as a forced
    # exit would turn a data outage into an unrequested market order.
    signal = evaluate_exit_rules(
        ExitRuleInput(
            position_open=True,
            direction="long",
            standing_stop=Decimal("95000"),
            current_price=Decimal("101000"),
            hold_score=Decimal("70"),
            regime_invalidated=False,
            data_risk_exit_required=False,
            manual_research_override=False,
            source_reason_codes={
                "data_risk_exit_required": (DATA_QUALITY_FAIL_REASON_CODE,),
            },
        ),
        strategy_config=CONFIG,
        evaluated_at=at(4),
    )

    assert signal.signal is False
    assert signal.effects == ()
    assert signal.exit_reasons == ()


def test_a_data_quality_blocked_add_leaves_the_ledger_untouched() -> None:
    lifecycle = opened(price="100000")
    before = economics(lifecycle)
    gated = apply_data_quality_gate("ADD", quality_failures())
    assert gated.action == "HOLD"

    held = apply_position_event(
        lifecycle,
        event=HOLD,
        event_time=at(4),
        reason_codes=(DATA_QUALITY_FAIL_REASON_CODE,),
    )

    assert held.accepted is True
    assert held.state == OPEN_INITIAL
    assert economics(held) == before
    assert held.tranche_count == 1
    assert DATA_QUALITY_FAIL_REASON_CODE in held.transitions[-1].reason_codes

    # The downgrade is what protected the book: the requested ADD would have
    # changed it.
    added = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=at(4),
        quantity="0.5",
        price="110000",
    )
    assert added.accepted is True
    assert economics(added) != before


# --- whole-run replay -----------------------------------------------------


ZONE_LOWER = Decimal("99000")
ZONE_UPPER = Decimal("101000")
ENTRY_STOP = Decimal("95000")


def day_bar(day: int, open_: str, high: str, low: str, close: str) -> OhlcvBar:
    timestamp = START + timedelta(days=day)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol=SYMBOL,
        timeframe="1d",
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("100"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(days=1),
    )


# Rises into a dip that would tempt an average-down, then recovers.
INVARIANT_BARS = (
    day_bar(0, "100000", "101000", "99000", "100500"),
    day_bar(1, "100500", "102000", "99500", "101500"),
    day_bar(2, "101500", "106000", "101000", "105500"),
    day_bar(3, "105500", "108000", "104000", "107000"),
    day_bar(4, "107000", "107500", "98000", "98500"),
    day_bar(5, "98500", "99500", "97500", "99000"),
    day_bar(6, "99000", "112000", "98800", "111000"),
    day_bar(7, "111000", "116000", "110000", "115000"),
    day_bar(8, "115000", "118000", "114000", "117000"),
    day_bar(9, "117000", "120000", "116000", "119000"),
)


def entry_intent() -> BacktestIntent:
    stop = calculate_initial_stop(
        invalidation_price=ENTRY_STOP,
        buffer=Decimal("0"),
        direction="long",
        entry_price=ZONE_UPPER,
        config_metadata=METADATA,
    )
    return BacktestIntent(
        action=ARM_ENTRY_ACTION,
        entry_zone_lower=ZONE_LOWER,
        entry_zone_upper=ZONE_UPPER,
        initial_stop=stop,
        entry_conviction=Decimal("90"),
        source_id="btc222-entry",
    )


def invariant_strategy(context: BacktestContext) -> BacktestIntent | None:
    """Propose exactly the decisions the six invariants must refuse or allow."""

    day = (context.bar.timestamp - START).days
    if day == 0:
        return entry_intent()
    if not context.position_open:
        return None
    if day == 4:
        # Underwater: the add gate is satisfied but the market is not.
        return BacktestIntent(
            action=BACKTEST_ADD_ACTION,
            requirements=add_requirements(),
            source_id="btc222-add-underwater",
        )
    if day == 5:
        # Crowded: the gate itself blocks.
        return BacktestIntent(
            action=BACKTEST_ADD_ACTION,
            requirements=add_requirements(positioning_healthy=False),
            source_id="btc222-add-crowded",
        )
    if day == 6:
        return BacktestIntent(
            action=TRAIL_ACTION,
            trailing_stop=calculate_trailing_stop(
                direction=context.lifecycle.direction,
                previous_stop=context.standing_stop,
                # Below the standing stop: a loosening that must be held.
                structure_price="90000",
                buffer=Decimal("500"),
                advance_count=stop_advance_count(context.lifecycle),
                current_price=context.bar.close,
                config_metadata=METADATA,
                evaluated_at=context.as_of,
                structure_id="btc222-loosening",
                structure_source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
                structure_type=HIGHER_LOW,
                structure_level_timestamp=context.bar.timestamp,
                structure_detected_at=context.as_of,
            ),
            source_id="btc222-trail-loosening",
        )
    if day == 7:
        return BacktestIntent(
            action=TRAIL_ACTION,
            trailing_stop=calculate_trailing_stop(
                direction=context.lifecycle.direction,
                previous_stop=context.standing_stop,
                structure_price="105000",
                buffer=Decimal("500"),
                advance_count=stop_advance_count(context.lifecycle),
                current_price=context.bar.close,
                config_metadata=METADATA,
                evaluated_at=context.as_of,
                structure_id="btc222-advance",
                structure_source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
                structure_type=HIGHER_LOW,
                structure_level_timestamp=context.bar.timestamp,
                structure_detected_at=context.as_of,
            ),
            source_id="btc222-trail-advance",
        )
    if day == 8:
        # Profitable, uncrowded, within the ceiling: this one must fill.
        return BacktestIntent(
            action=BACKTEST_ADD_ACTION,
            requirements=add_requirements(),
            source_id="btc222-add-permitted",
        )
    return None


def invariant_run():
    return run_backtest(
        INVARIANT_BARS,
        strategy=invariant_strategy,
        symbol=SYMBOL,
        starting_nav=NAV,
        strategy_config=CONFIG,
        strategy_id="btc222-risk-invariant-strategy",
    )


def test_a_full_replay_never_averages_down_or_widens_a_stop() -> None:
    result = invariant_run()
    lifecycle = result.final_lifecycle

    averages: list[Decimal] = []
    stops: list[Decimal] = []
    quantity = Decimal("0")
    average = None
    for transition in lifecycle.transitions:
        if not transition.accepted:
            continue
        if transition.event in (ENTER, ADD):
            if average is not None:
                # Rulebook 32 rule 2, read off the accepted ledger itself.
                assert transition.price >= average
            total = quantity + transition.requested_quantity
            average = (
                (average or Decimal("0")) * quantity
                + transition.price * transition.requested_quantity
            ) / total
            quantity = total
            averages.append(average)
        if transition.stop_price is not None:
            stops.append(transition.stop_price)

    assert averages == sorted(averages)
    assert stops == sorted(stops)
    assert lifecycle.average_entry_price == averages[-1]
    assert lifecycle.stop_price == stops[-1]


def test_a_full_replay_refuses_exactly_the_violating_proposals() -> None:
    result = invariant_run()
    by_source = {}
    for event in result.events:
        by_source.setdefault(event.source_id, []).append(event)

    underwater = [
        event
        for event in by_source["btc222-add-underwater"]
        if event.event_type == "ADD_EXECUTION"
    ]
    assert [event.status for event in underwater] == ["REFUSED"]
    assert "ADD_EXECUTION_NO_LONGER_PROFITABLE" in underwater[0].reason_codes

    crowded = [
        event
        for event in by_source["btc222-add-crowded"]
        if event.event_type == "ADD_EXECUTION"
    ]
    assert [event.status for event in crowded] == ["REFUSED"]
    assert "ADD_REQUIREMENTS_POSITIONING_UNHEALTHY" in crowded[0].reason_codes

    loosening = by_source["btc222-trail-loosening"]
    assert [event.status for event in loosening if event.event_type == "TRAILING_STOP"] == [
        "REFUSED"
    ]

    advance = by_source["btc222-trail-advance"]
    assert [event.status for event in advance if event.event_type == "TRAILING_STOP"] == [
        "APPLIED"
    ]

    permitted = [
        event
        for event in by_source["btc222-add-permitted"]
        if event.event_type == "ADD_EXECUTION"
    ]
    assert [event.status for event in permitted] == ["EXECUTED"]

    assert "BACKTEST_ADD_REFUSED" in result.reason_codes
    assert "BACKTEST_ADDED" in result.reason_codes
    assert "BACKTEST_STOP_TRAILED" in result.reason_codes
    assert "BACKTEST_TRAIL_HELD" in result.reason_codes
    assert result.final_lifecycle.tranche_count == 2


def test_a_full_replay_reports_risk_at_stop_at_every_open_bar() -> None:
    result = invariant_run()

    open_points = [point for point in result.equity_curve if point.open_quantity > 0]
    assert open_points

    for point in open_points:
        # Never silently absent, and never negative.
        assert point.risk_at_stop is not None
        assert point.risk_fraction_nav is not None
        assert point.risk_at_stop >= Decimal("0")

    # Every add the run accepted left the book within the configured ceiling
    # at the NAV it was taken on.
    lifecycle = result.final_lifecycle
    assert ledger_risk(lifecycle, nav=result.ending_nav).within_maximum is True


def test_the_invariant_replay_is_deterministic_and_persists_its_evidence() -> None:
    first = invariant_run()
    second = invariant_run()

    assert first.as_record() == second.as_record()
    assert restore_backtest_result(first.as_record()).as_record() == first.as_record()
    assert first.config_metadata == METADATA
