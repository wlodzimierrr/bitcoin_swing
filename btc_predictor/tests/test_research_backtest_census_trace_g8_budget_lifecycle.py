"""Synthetic runtime-trace fixtures for the RBT-002 census cross-check (group 8).

Roots driven here (DECISION_PATH_ROOTS, areas RISK_BUDGET_SIZING_AND_RISK_AT_STOP
and LIFECYCLE_HOLD_ADD_TRANCHES_TRAIL_TRIM_EXIT):

- btc_predictor.risk.budget.calculate_risk_budget
- btc_predictor.risk.sizing.initial_position_size_for_trade
- btc_predictor.risk.exposure.calculate_risk_at_stop
- btc_predictor.portfolio.state_machine.start_position_lifecycle
- btc_predictor.portfolio.state_machine.apply_position_event
- btc_predictor.risk.tranches.next_tranche_for_position

Every thunk is zero-argument and deterministic: fixed synthetic UTC dates in
2024, exact Decimal inputs, the champion StrategyConfig from
``load_strategy_config()`` (the only file read, performed by the owner), no
randomness, no wall clock, no network, no database. Inputs are built only from
btc_predictor owner types and stdlib values; upstream results (structural
invalidation -> volatility buffer -> initial stop -> risk budget -> position
size, and the BTC-150 lifecycle) are produced by calling the owners inside the
thunk, the way the BTC-180 engine composes them.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.levels.clustering import (
    LEVEL_CLUSTER_FEATURE_ID,
    LEVEL_CLUSTER_SUPPORT,
    LevelCluster,
    LevelClusterMember,
)
from btc_predictor.portfolio.state_machine import (
    ADD,
    ARM_ENTRY,
    DEFEND,
    DISARM_ENTRY,
    ENTER,
    EXIT,
    HOLD,
    MISS,
    OBSERVE,
    PENDING_ENTRY,
    RECOVER,
    STOP_MOVE,
    TRIM,
    WATCH,
    PositionLifecycle,
    apply_position_event,
    start_position_lifecycle,
)
from btc_predictor.risk.budget import RiskBudgetResult, calculate_risk_budget
from btc_predictor.risk.buffer import volatility_buffer_for_invalidation
from btc_predictor.risk.exposure import (
    ABSOLUTE_DISTANCE,
    RiskAtStopResult,
    calculate_risk_at_stop,
)
from btc_predictor.risk.invalidation import (
    BULL_TREND_CONTINUATION_SETUP,
    LONG_DIRECTION,
    select_structural_invalidation,
)
from btc_predictor.risk.sizing import (
    InitialPositionSizeResult,
    initial_position_size_for_trade,
)
from btc_predictor.risk.stop import InitialStopResult, initial_stop_for_setup
from btc_predictor.risk.tranches import TrancheSizingResult, next_tranche_for_position


SYMBOL = "BTC-USD"
EXCHANGE = "coinbase"
PROVIDER = "synthetic"
# Fixed synthetic clock, all inside 2021-01-01..2024-12-31.
LEVEL_DETECTED_AT = datetime(2024, 5, 6, tzinfo=UTC)
DECISION_AT = datetime(2024, 6, 3, tzinfo=UTC)
NAV = Decimal("1000000")
ENTRY_PRICE = Decimal("60000")
ATR_20 = Decimal("1500")
SUPPORT_LOWER = Decimal("56000")
SUPPORT_UPPER = Decimal("56400")


def _at(hours: int) -> datetime:
    return DECISION_AT + timedelta(hours=hours)


def _champion() -> tuple[StrategyConfig, dict[str, str]]:
    config = load_strategy_config()
    return config, config.run_metadata()


# --- upstream owner results -------------------------------------------------------------


def _support_cluster(lower: Decimal, upper: Decimal) -> LevelCluster:
    """A BTC-097 support zone with two point-in-time members below entry."""

    members = (
        LevelClusterMember(
            member_id="weekly-swing-low-2024-05-06",
            feature_id="WEEKLY_SWING_LEVELS",
            level_type="swing_low",
            price=lower,
            detected_at=LEVEL_DETECTED_AT,
            exchange=EXCHANGE,
            symbol=SYMBOL,
            provider=PROVIDER,
            source_timestamp=LEVEL_DETECTED_AT - timedelta(days=7),
            source_timeframe="1w",
        ),
        LevelClusterMember(
            member_id="volume-profile-hvn-2024-05-06",
            feature_id="VOLUME_PROFILE_LEVELS",
            level_type="hvn",
            price=upper,
            detected_at=LEVEL_DETECTED_AT,
            exchange=EXCHANGE,
            symbol=SYMBOL,
            provider=PROVIDER,
            source_timestamp=LEVEL_DETECTED_AT - timedelta(days=1),
            source_timeframe="1d",
        ),
    )
    return LevelCluster(
        feature_id=LEVEL_CLUSTER_FEATURE_ID,
        cluster_id="support-56000-56400",
        zone_type=LEVEL_CLUSTER_SUPPORT,
        lower_bound=lower,
        upper_bound=upper,
        center_price=(lower + upper) / 2,
        reference_price=ENTRY_PRICE,
        detected_at=LEVEL_DETECTED_AT,
        cluster_distance_fraction=Decimal("0.025"),
        minimum_level_strength=Decimal("60"),
        confluence_score=Decimal("74"),
        member_count=len(members),
        unique_source_count=2,
        unique_timeframe_count=2,
        members=members,
        reason_codes=("LEVEL_CLUSTER_COMPLETE",),
    )


def _initial_stop(
    config: StrategyConfig,
    metadata: dict[str, str],
    *,
    with_structure: bool = True,
) -> InitialStopResult:
    """BTC-140 -> BTC-141 -> BTC-142 for a Setup A long at ENTRY_PRICE."""

    clusters = [_support_cluster(SUPPORT_LOWER, SUPPORT_UPPER)] if with_structure else []
    invalidation = select_structural_invalidation(
        clusters,
        setup=BULL_TREND_CONTINUATION_SETUP,
        entry_price=ENTRY_PRICE,
        as_of=DECISION_AT,
        atr=ATR_20,
        config_metadata=metadata,
    )
    buffer = volatility_buffer_for_invalidation(
        invalidation,
        atr=ATR_20,
        atr_multiplier=Decimal(str(config.stop_buffers.atr_multiplier)),
        atr_window=config.stop_buffers.atr_period,
        config_metadata=metadata,
    )
    return initial_stop_for_setup(invalidation, buffer, config_metadata=metadata)


def _budget(
    config: StrategyConfig,
    metadata: dict[str, str],
    conviction: Decimal | None,
) -> RiskBudgetResult:
    return calculate_risk_budget(
        entry_conviction=conviction,
        nav=NAV,
        config=config,
        config_metadata=metadata,
    )


def _position_size(
    config: StrategyConfig,
    metadata: dict[str, str],
    *,
    conviction: Decimal = Decimal("86.5"),
    with_structure: bool = True,
) -> tuple[InitialStopResult, InitialPositionSizeResult]:
    stop = _initial_stop(config, metadata, with_structure=with_structure)
    budget = _budget(config, metadata, conviction)
    size = initial_position_size_for_trade(budget, stop, config_metadata=metadata)
    return stop, size


def _entered(
    config: StrategyConfig,
    metadata: dict[str, str],
) -> tuple[InitialStopResult, InitialPositionSizeResult, PositionLifecycle]:
    """An OPEN_INITIAL lifecycle filled with the first scheduled tranche."""

    stop, size = _position_size(config, metadata)
    first = next_tranche_for_position(
        start_position_lifecycle(symbol=SYMBOL, state=PENDING_ENTRY, config_metadata=metadata),
        size,
        config=config,
        config_metadata=metadata,
    )
    lifecycle = start_position_lifecycle(
        symbol=SYMBOL,
        direction=LONG_DIRECTION,
        state=PENDING_ENTRY,
        config_metadata=metadata,
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=_at(1),
        quantity=first.allocation.quantity,
        price=stop.entry_price,
        stop_price=stop.stop_price,
        reason_codes=stop.reason_codes,
        source_feature_id="ENTRY_EXECUTION",
        source_record_id="entry-2024-06-03",
    )
    return stop, size, lifecycle


# --- btc_predictor.risk.budget.calculate_risk_budget --------------------------------------


def budget_assigned() -> RiskBudgetResult:
    """Conviction 86.5 under the champion schedule: the 85-90 band, 0.50% NAV."""

    config, metadata = _champion()
    return _budget(config, metadata, Decimal("86.5"))


def budget_below_minimum_conviction() -> RiskBudgetResult:
    """Conviction 74 is WATCH territory: no budget, never a reduced one."""

    config, metadata = _champion()
    return _budget(config, metadata, Decimal("74"))


def budget_input_missing() -> RiskBudgetResult:
    """A missing Entry Conviction yields RISK_BUDGET_INPUT_MISSING."""

    config, metadata = _champion()
    return _budget(config, metadata, None)


# --- btc_predictor.risk.sizing.initial_position_size_for_trade ---------------------------


def size_assigned() -> InitialPositionSizeResult:
    """Budget (86.5 -> 0.50% NAV) over the BTC-142 stop distance."""

    config, metadata = _champion()
    stop = _initial_stop(config, metadata)
    budget = _budget(config, metadata, Decimal("86.5"))
    return initial_position_size_for_trade(budget, stop, config_metadata=metadata)


def size_no_risk_budget() -> InitialPositionSizeResult:
    """A sub-80 conviction leaves no budget, so no position is sized."""

    config, metadata = _champion()
    stop = _initial_stop(config, metadata)
    budget = _budget(config, metadata, Decimal("74"))
    return initial_position_size_for_trade(budget, stop, config_metadata=metadata)


def size_stop_incomplete() -> InitialPositionSizeResult:
    """No structure -> incomplete invalidation, buffer and stop -> no size."""

    config, metadata = _champion()
    stop = _initial_stop(config, metadata, with_structure=False)
    budget = _budget(config, metadata, Decimal("86.5"))
    return initial_position_size_for_trade(budget, stop, config_metadata=metadata)


# --- btc_predictor.risk.exposure.calculate_risk_at_stop ----------------------------------


def _added(config: StrategyConfig, metadata: dict[str, str]) -> PositionLifecycle:
    """OPEN_ADDED: initial tranche plus the scheduled add at a higher price."""

    _, size, lifecycle = _entered(config, metadata)
    add_price = Decimal("63000")
    second = next_tranche_for_position(
        lifecycle,
        size,
        entry_price=add_price,
        config=config,
        config_metadata=metadata,
    )
    return apply_position_event(
        lifecycle,
        event=ADD,
        event_time=_at(49),
        quantity=second.allocation.quantity,
        price=add_price,
        source_feature_id="ADD_EXECUTION",
        source_record_id="add-2024-06-05",
    )


def risk_at_stop_complete() -> RiskAtStopResult:
    """Engine-shaped aggregate risk over the lifecycle's tranches at its stop."""

    config, metadata = _champion()
    lifecycle = _added(config, metadata)
    return calculate_risk_at_stop(
        [
            {
                "tranche_id": f"t{tranche.tranche_number}",
                "quantity": tranche.quantity,
                "entry_price": tranche.entry_price,
            }
            for tranche in lifecycle.tranches
        ],
        stop_price=lifecycle.stop_price,
        nav=NAV,
        direction=lifecycle.direction,
        config=config,
    )


def risk_at_stop_input_missing() -> RiskAtStopResult:
    """No stop price: RISK_AT_STOP_INPUT_MISSING, with no derived amounts."""

    config, metadata = _champion()
    _, _, lifecycle = _entered(config, metadata)
    return calculate_risk_at_stop(
        lifecycle.tranches,
        stop_price=None,
        nav=NAV,
        direction=lifecycle.direction,
        config=config,
        config_metadata=metadata,
    )


def risk_at_stop_ledger_tranches_after_trail() -> RiskAtStopResult:
    """Tranche objects straight from the ledger after a stop raise.

    The stop is raised above the first fill, so that tranche is profitable at
    the stop; the explicit ABSOLUTE_DISTANCE convention still charges it.
    """

    config, metadata = _champion()
    lifecycle = _added(config, metadata)
    trailed = apply_position_event(
        lifecycle,
        event=STOP_MOVE,
        event_time=_at(73),
        stop_price=Decimal("61000"),
        source_feature_id="TRAILING_STOP",
        source_record_id="trail-2024-06-06",
    )
    return calculate_risk_at_stop(
        trailed.tranches,
        stop_price=trailed.stop_price,
        nav=NAV,
        direction=trailed.direction,
        convention=ABSOLUTE_DISTANCE,
        config=config,
        config_metadata=metadata,
    )


# --- btc_predictor.portfolio.state_machine.start_position_lifecycle ---------------------


def lifecycle_started_pending_entry() -> PositionLifecycle:
    """Conviction >= 80 goes straight to PENDING_ENTRY under champion metadata."""

    _, metadata = _champion()
    return start_position_lifecycle(
        symbol=SYMBOL,
        direction=LONG_DIRECTION,
        state=PENDING_ENTRY,
        config_metadata=metadata,
    )


def lifecycle_started_watch_defaults() -> PositionLifecycle:
    """The owner's defaults: a long lifecycle in WATCH with no metadata.

    start_position_lifecycle has no refusal or incomplete branch: malformed
    input raises, so the second fixture exercises its defaulted parameters.
    """

    return start_position_lifecycle(symbol=SYMBOL)


# --- btc_predictor.portfolio.state_machine.apply_position_event --------------------------


def lifecycle_full_accepted_path() -> PositionLifecycle:
    """WATCH -> ... -> CLOSED, every event accepted (ENTER, ADD, TRIM, EXIT...)."""

    config, metadata = _champion()
    stop, size = _position_size(config, metadata)
    first = next_tranche_for_position(
        start_position_lifecycle(symbol=SYMBOL, config_metadata=metadata),
        size,
        config=config,
        config_metadata=metadata,
    )
    lifecycle = start_position_lifecycle(symbol=SYMBOL, state=WATCH, config_metadata=metadata)
    lifecycle = apply_position_event(lifecycle, event=OBSERVE, event_time=_at(0))
    lifecycle = apply_position_event(
        lifecycle, event=ARM_ENTRY, event_time=_at(0), reason_codes=("ENTRY_CONVICTION_ENTER",)
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=_at(1),
        quantity=first.allocation.quantity,
        price=stop.entry_price,
        stop_price=stop.stop_price,
        reason_codes=stop.reason_codes,
        source_feature_id="ENTRY_EXECUTION",
        source_record_id="entry-2024-06-03",
    )
    lifecycle = apply_position_event(lifecycle, event=HOLD, event_time=_at(25))
    add_price = Decimal("63000")
    second = next_tranche_for_position(
        lifecycle, size, entry_price=add_price, config=config, config_metadata=metadata
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ADD,
        event_time=_at(49),
        quantity=second.allocation.quantity,
        price=add_price,
        source_feature_id="ADD_EXECUTION",
        source_record_id="add-2024-06-05",
    )
    lifecycle = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=_at(73), stop_price=Decimal("59000")
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=TRIM,
        event_time=_at(97),
        quantity=lifecycle.quantity / 3,
        price=Decimal("66000"),
        reason_codes=("TRIM_EXTENSION",),
    )
    lifecycle = apply_position_event(
        lifecycle, event=DEFEND, event_time=_at(121), reason_codes=("HOLD_SCORE_DEFENSIVE",)
    )
    lifecycle = apply_position_event(lifecycle, event=RECOVER, event_time=_at(145))
    return apply_position_event(
        lifecycle,
        event=EXIT,
        event_time=_at(169),
        quantity=lifecycle.quantity,
        price=Decimal("64000"),
        reason_codes=("EXIT_RULE",),
        source_feature_id="EXIT_EXECUTION",
        source_record_id="exit-2024-06-10",
    )


def lifecycle_refusals() -> PositionLifecycle:
    """Refused events are recorded, not raised: out of order, average-down,
    widening stop, ADD while DEFENSIVE, partial EXIT, events after CLOSED."""

    config, metadata = _champion()
    stop, _, lifecycle = _entered(config, metadata)
    # Out of order: earlier than the accepted ENTER watermark.
    lifecycle = apply_position_event(lifecycle, event=HOLD, event_time=_at(0))
    # Average down: ADD below the weighted average entry.
    lifecycle = apply_position_event(
        lifecycle, event=ADD, event_time=_at(25), quantity=Decimal("0.1"), price=Decimal("58000")
    )
    # Never widen a stop after entry, and ENTER is not permitted while open.
    lifecycle = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=_at(26), stop_price=stop.stop_price - 1000
    )
    lifecycle = apply_position_event(
        lifecycle, event=ENTER, event_time=_at(27), quantity=Decimal("0.1"), price=Decimal("60500")
    )
    # A whole-position TRIM is refused; a TRIM carrying a stop is refused.
    lifecycle = apply_position_event(
        lifecycle, event=TRIM, event_time=_at(28), quantity=lifecycle.quantity,
        stop_price=stop.stop_price,
    )
    lifecycle = apply_position_event(lifecycle, event=DEFEND, event_time=_at(29))
    lifecycle = apply_position_event(
        lifecycle, event=ADD, event_time=_at(30), quantity=Decimal("0.1"), price=Decimal("62000")
    )
    lifecycle = apply_position_event(
        lifecycle, event=EXIT, event_time=_at(31), quantity=lifecycle.quantity / 2,
        price=Decimal("61000"),
    )
    lifecycle = apply_position_event(lifecycle, event=EXIT, event_time=_at(32), price=Decimal("61000"))
    return apply_position_event(lifecycle, event=HOLD, event_time=_at(33))


def lifecycle_disarmed_then_missed() -> PositionLifecycle:
    """A pre-position lifecycle that never fills: ARM, DISARM, then MISS."""

    _, metadata = _champion()
    lifecycle = start_position_lifecycle(symbol=SYMBOL, config_metadata=metadata)
    lifecycle = apply_position_event(lifecycle, event=ARM_ENTRY, event_time=_at(0))
    lifecycle = apply_position_event(lifecycle, event=OBSERVE, event_time=_at(1))
    # ENTER without a stop is refused before a fill.
    lifecycle = apply_position_event(
        lifecycle, event=ENTER, event_time=_at(2), quantity=Decimal("1"), price=ENTRY_PRICE
    )
    lifecycle = apply_position_event(lifecycle, event=DISARM_ENTRY, event_time=_at(3))
    return apply_position_event(
        lifecycle, event=MISS, event_time=_at(4), reason_codes=("NO_CHASE",)
    )


# --- btc_predictor.risk.tranches.next_tranche_for_position -------------------------------


def tranche_add_allocated() -> TrancheSizingResult:
    """Add #1 (35% of the final BTC-145 notional) at its own fill price."""

    config, metadata = _champion()
    _, size, lifecycle = _entered(config, metadata)
    return next_tranche_for_position(
        lifecycle,
        size,
        entry_price=Decimal("63000"),
        config=config,
        config_metadata=metadata,
    )


def tranche_no_position_size() -> TrancheSizingResult:
    """An incomplete BTC-145 size (sub-80 conviction) allocates nothing."""

    config, metadata = _champion()
    _, unsized = _position_size(config, metadata, conviction=Decimal("74"))
    lifecycle = start_position_lifecycle(
        symbol=SYMBOL, state=PENDING_ENTRY, config_metadata=metadata
    )
    return next_tranche_for_position(lifecycle, unsized, config=config, config_metadata=metadata)


def tranche_add_without_price() -> TrancheSizingResult:
    """A later tranche without its own fill price: TRANCHE_SIZING_NO_ADD_PRICE."""

    config, metadata = _champion()
    _, size, lifecycle = _entered(config, metadata)
    return next_tranche_for_position(lifecycle, size, config=config, config_metadata=metadata)


FIXTURES: dict[str, tuple[Callable[[], object], ...]] = {
    "btc_predictor.risk.budget.calculate_risk_budget": (
        budget_assigned,
        budget_below_minimum_conviction,
        budget_input_missing,
    ),
    "btc_predictor.risk.sizing.initial_position_size_for_trade": (
        size_assigned,
        size_no_risk_budget,
        size_stop_incomplete,
    ),
    "btc_predictor.risk.exposure.calculate_risk_at_stop": (
        risk_at_stop_complete,
        risk_at_stop_input_missing,
        risk_at_stop_ledger_tranches_after_trail,
    ),
    "btc_predictor.portfolio.state_machine.start_position_lifecycle": (
        lifecycle_started_pending_entry,
        lifecycle_started_watch_defaults,
    ),
    "btc_predictor.portfolio.state_machine.apply_position_event": (
        lifecycle_full_accepted_path,
        lifecycle_refusals,
        lifecycle_disarmed_then_missed,
    ),
    "btc_predictor.risk.tranches.next_tranche_for_position": (
        tranche_add_allocated,
        tranche_no_position_size,
        tranche_add_without_price,
    ),
}


# --- RBT-002 R1 runtime cross-check -------------------------------------------------------

import functools as _functools  # noqa: E402

import pytest as _pytest  # noqa: E402

from btc_predictor.research_backtest import input_census as _input_census  # noqa: E402


@_functools.cache
def _census() -> _input_census.DecisionPathCensus:
    return _input_census.discover_decision_path()


@_pytest.mark.parametrize(
    "root, index",
    [(root, index) for root, thunks in sorted(FIXTURES.items()) for index in range(len(thunks))],
)
def test_the_static_census_contains_everything_this_root_traces(root: str, index: int) -> None:
    """Run the root on its synthetic fixture under sys.setprofile: every
    btc_predictor function entered and dataclass constructed must be in the
    static census, and the root itself must have run."""

    result, traced = _input_census.trace_owner_calls(FIXTURES[root][index])
    assert root in traced.functions
    assert _input_census.uncovered_traced(_census(), traced) == {"functions": [], "dataclasses": []}
    if index == 0 and hasattr(result, "complete"):
        assert result.complete is True
