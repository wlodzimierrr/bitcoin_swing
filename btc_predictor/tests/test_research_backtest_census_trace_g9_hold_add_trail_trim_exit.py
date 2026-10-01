"""Deterministic synthetic fixtures for the RBT-002 runtime census cross-check.

Group 9: lifecycle roots for Hold Score (Rulebook 20), Add Score and its
risk-improvement component (Rulebook 21), add requirements (Rulebook 18.1),
trailing stop calculation and application (Rulebook 22/26), trim rules
(Rulebook 23) and exit rules (Rulebook 26/31).

Every thunk is zero-argument, builds its own synthetic inputs from
``btc_predictor`` owner types and the standard library only (Decimal and
timezone-aware UTC datetimes fixed inside 2021-01-01..2024-12-31), calls the
root, and returns the root's result. No randomness, no wall clock, no network,
no database. The champion configuration is read with
``btc_predictor.config.strategy.load_strategy_config()`` inside each thunk that
needs a ``StrategyConfig`` or config metadata (it reads the versioned strategy
TOML that ships with the repository; that is the only file touched).

Upstream results are produced by calling other decision-path owners (all of
them are themselves census roots): ``start_position_lifecycle``,
``apply_position_event``, ``calculate_hold_score``, ``calculate_add_score``,
``risk_improvement_component_score``, ``calculate_risk_at_stop``,
``volatility_buffer_for_invalidation``, ``trail_stop_for_position``,
``calculate_flow_score``, ``calculate_euphoria_flag`` and
``calculate_crowding_flag``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.features.add import (
    AddScoreInput,
    AddScoreResult,
    RiskImprovementComponent,
    calculate_add_score,
    risk_improvement_component_score,
)
from btc_predictor.features.flow import FlowScoreInput, FlowScoreResult, calculate_flow_score
from btc_predictor.features.hold import HoldScoreInput, HoldScoreResult, calculate_hold_score
from btc_predictor.features.positioning import (
    CrowdingFlagInput,
    CrowdingFlagResult,
    calculate_crowding_flag,
)
from btc_predictor.features.volatility import (
    EuphoriaFlagInput,
    EuphoriaFlagResult,
    calculate_euphoria_flag,
)
from btc_predictor.portfolio.state_machine import (
    ENTER,
    PENDING_ENTRY,
    PositionLifecycle,
    apply_position_event,
    start_position_lifecycle,
)
from btc_predictor.risk.buffer import (
    VolatilityBufferResult,
    volatility_buffer_for_invalidation,
)
from btc_predictor.risk.exposure import RiskAtStopResult, calculate_risk_at_stop
from btc_predictor.risk.trailing import (
    HIGHER_LOW,
    ConfirmedTrailingStructure,
    TrailingStopResult,
    apply_trailing_stop,
    trail_stop_for_position,
)
from btc_predictor.signals.add_requirements import (
    AddRequirementsResult,
    add_requirements_from_results,
)
from btc_predictor.signals.exit_rules import ExitSignalResult, exit_rules_for_position
from btc_predictor.signals.trim import TrimSignalResult, trim_rules_from_results


SYMBOL = "BTC-USD"
# Fixed synthetic clock inside the 2021-01-01..2024-12-31 window.
START = datetime(2024, 5, 1, tzinfo=UTC)
ENTRY_PRICE = "60000"
ENTRY_STOP = "54000"
ENTRY_QUANTITY = "1"
NAV = "1000000"


def _at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def _config() -> StrategyConfig:
    return load_strategy_config()


# --- shared upstream builders (each calls owners; none is a test module) -------------


def _open_lifecycle(config: StrategyConfig) -> PositionLifecycle:
    """A long position entered at 60000 with a 54000 structural stop at _at(1)."""

    lifecycle = start_position_lifecycle(
        symbol=SYMBOL,
        state=PENDING_ENTRY,
        config_metadata=config.run_metadata(),
    )
    return apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=_at(1),
        quantity=ENTRY_QUANTITY,
        price=ENTRY_PRICE,
        stop_price=ENTRY_STOP,
        reason_codes=("ENTRY_TRIGGER_RECLAIM_CONFIRMED",),
    )


def _watch_lifecycle(config: StrategyConfig) -> PositionLifecycle:
    """A pre-position lifecycle (WATCH): no open position, no stop."""

    return start_position_lifecycle(
        symbol=SYMBOL,
        config_metadata=config.run_metadata(),
    )


def _hold_result(config: StrategyConfig, *, flow: str | None = "78") -> HoldScoreResult:
    """Hold Score from direct components; ``flow=None`` makes it incomplete."""

    return calculate_hold_score(
        HoldScoreInput(
            trend_score=Decimal("80"),
            flow_score=None if flow is None else Decimal(flow),
            positioning_score=Decimal("70"),
            structure_score=Decimal("85"),
            momentum_persistence_score=Decimal("75"),
        ),
        strategy_config=config,
    )


def _add_score_result(config: StrategyConfig, *, complete: bool = True) -> AddScoreResult:
    return calculate_add_score(
        AddScoreInput(
            new_structure_score=Decimal("92"),
            flow_score=Decimal("88"),
            positioning_score=Decimal("86"),
            momentum_score=Decimal("90"),
            risk_improvement_score=Decimal("90") if complete else None,
        ),
        strategy_config=config,
    )


def _current_book_risk(config: StrategyConfig) -> RiskAtStopResult:
    """Risk of the open book (1 BTC at 60000) at the standing 54000 stop."""

    return calculate_risk_at_stop(
        [{"tranche_id": "t1", "quantity": ENTRY_QUANTITY, "entry_price": ENTRY_PRICE}],
        stop_price=ENTRY_STOP,
        nav=NAV,
        config=config,
    )


def _proposed_book_risk(config: StrategyConfig, *, nav: str = NAV) -> RiskAtStopResult:
    """Projected post-add book (1 BTC at 60000 + 0.5 BTC at 66000) at a 62000 stop."""

    return calculate_risk_at_stop(
        [
            {"tranche_id": "t1", "quantity": ENTRY_QUANTITY, "entry_price": ENTRY_PRICE},
            {"tranche_id": "t2", "quantity": "0.5", "entry_price": "66000"},
        ],
        stop_price="62000",
        nav=nav,
        config=config,
    )


def _risk_improvement(config: StrategyConfig) -> RiskImprovementComponent:
    current = _current_book_risk(config)
    proposed = calculate_risk_at_stop(
        [{"tranche_id": "t1", "quantity": ENTRY_QUANTITY, "entry_price": ENTRY_PRICE}],
        stop_price="57000",
        nav=NAV,
        config=config,
    )
    return risk_improvement_component_score(
        current_risk=current.risk_at_stop,
        proposed_risk=proposed.risk_at_stop,
    )


def _complete_buffer(config: StrategyConfig, metadata: dict[str, str]) -> VolatilityBufferResult:
    """A complete BTC-141 buffer derived from a bounded selected zone."""

    return volatility_buffer_for_invalidation(
        {
            "complete": True,
            "selected_zone_lower_bound": Decimal("61800"),
            "selected_zone_upper_bound": Decimal("62400"),
        },
        atr=Decimal("2500"),
        atr_multiplier=Decimal(str(config.stop_buffers.atr_multiplier)),
        atr_window=config.stop_buffers.atr_period,
        config_metadata=metadata,
    )


def _refused_buffer(config: StrategyConfig, metadata: dict[str, str]) -> VolatilityBufferResult:
    """BTC-140 refused the selection, so the buffer is incomplete."""

    return volatility_buffer_for_invalidation(
        {"complete": False},
        atr=Decimal("2500"),
        atr_multiplier=Decimal(str(config.stop_buffers.atr_multiplier)),
        atr_window=config.stop_buffers.atr_period,
        config_metadata=metadata,
    )


def _higher_low(metadata: dict[str, str], *, structure_id: str = "higher-low-2024-05-02") -> ConfirmedTrailingStructure:
    return ConfirmedTrailingStructure(
        structure_id=structure_id,
        source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
        direction="long",
        structure_type=HIGHER_LOW,
        price=Decimal("62000"),
        level_timestamp=_at(20),
        detected_at=_at(26),
        config_metadata=metadata,
        reason_codes=("HIGHER_LOW_CONFIRMED",),
    )


def _flow_result(config: StrategyConfig, zscore: str) -> FlowScoreResult:
    value = Decimal(zscore)
    return calculate_flow_score(
        FlowScoreInput(
            etf_norm_5_zscore=value,
            etf_norm_20_zscore=value,
            flow_accel_zscore=value,
        ),
        core_weights=config.scoring_weights.core_flow,
        full_weights=config.scoring_weights.full_flow,
        config_metadata=config.run_metadata(),
    )


def _euphoria_result(config: StrategyConfig, *, complete: bool = True) -> EuphoriaFlagResult:
    thresholds = config.volatility_flags.euphoria
    return calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=Decimal("55"),
            upside_return=Decimal("0.02") if complete else None,
            funding_zscore=Decimal("0.5"),
            basis_zscore=Decimal("0.4"),
            oi_intensity_percentile=Decimal("50"),
            volatility_percentile=Decimal("45") if complete else None,
            systemic_euphoria=False,
        ),
        range_percentile_min=thresholds.range_percentile_min,
        upside_return_min=thresholds.upside_return_min,
        funding_zscore_min=thresholds.funding_zscore_min,
        basis_zscore_min=thresholds.basis_zscore_min,
        oi_intensity_percentile_min=thresholds.oi_intensity_percentile_min,
        volatility_percentile_min=thresholds.volatility_percentile_min,
        config_metadata=config.run_metadata(),
    )


def _crowding_result(config: StrategyConfig) -> CrowdingFlagResult:
    thresholds = config.positioning_flags.crowding
    return calculate_crowding_flag(
        CrowdingFlagInput(
            funding_zscore=Decimal("0.5"),
            basis_zscore=Decimal("0.4"),
            oi_intensity_percentile=Decimal("50"),
        ),
        funding_zscore_min=thresholds.funding_zscore_min,
        basis_zscore_min=thresholds.basis_zscore_min,
        oi_intensity_percentile_min=thresholds.oi_intensity_percentile_min,
        entry_quality_penalty=thresholds.entry_quality_penalty,
        config_metadata=config.run_metadata(),
    )


# --- btc_predictor.features.hold.calculate_hold_score ---------------------------------


def hold_score_complete() -> HoldScoreResult:
    """Main path: all five v1.2 components present -> HOLD_SCORE_COMPLETE."""

    config = _config()
    return calculate_hold_score(
        HoldScoreInput(
            trend_score=Decimal("80"),
            flow_score=Decimal("70"),
            positioning_score=Decimal("60"),
            structure_score=Decimal("90"),
            momentum_persistence_score=Decimal("50"),
        ),
        strategy_config=config,
    )


def hold_score_input_missing() -> HoldScoreResult:
    """Missing-input branch: flow unavailable -> HOLD_SCORE_INPUT_MISSING, score None."""

    config = _config()
    return calculate_hold_score(
        HoldScoreInput(
            trend_score=Decimal("80"),
            flow_score=None,
            positioning_score=Decimal("60"),
            structure_score=Decimal("90"),
            momentum_persistence_score=Decimal("50"),
        ),
        strategy_config=config,
    )


# --- btc_predictor.features.add.calculate_add_score -----------------------------------


def add_score_complete() -> AddScoreResult:
    """Main path: all five Add Score components present -> ADD_SCORE_COMPLETE."""

    config = _config()
    component = _risk_improvement(config)
    return calculate_add_score(
        AddScoreInput(
            new_structure_score=Decimal("92"),
            flow_score=Decimal("88"),
            positioning_score=Decimal("86"),
            momentum_score=Decimal("90"),
            risk_improvement_score=component.score,
        ),
        strategy_config=config,
    )


def add_score_input_missing() -> AddScoreResult:
    """Missing-input branch: undefined risk-improvement component -> incomplete."""

    config = _config()
    # No current risk to remove: the BTC-153 bridge reports score=None.
    component = risk_improvement_component_score(current_risk="0", proposed_risk="0")
    return calculate_add_score(
        AddScoreInput(
            new_structure_score=Decimal("92"),
            flow_score=Decimal("88"),
            positioning_score=Decimal("86"),
            momentum_score=Decimal("90"),
            risk_improvement_score=component.score,
        ),
        strategy_config=config,
    )


# --- btc_predictor.features.add.risk_improvement_component_score ----------------------


def risk_improvement_improved() -> RiskImprovementComponent:
    """Main path: a tighter stop removes half the risk -> score 50, not worsened."""

    config = _config()
    current = _current_book_risk(config)
    proposed = calculate_risk_at_stop(
        [{"tranche_id": "t1", "quantity": ENTRY_QUANTITY, "entry_price": ENTRY_PRICE}],
        stop_price="57000",
        nav=NAV,
        config=config,
    )
    return risk_improvement_component_score(
        current_risk=current.risk_at_stop,
        proposed_risk=proposed.risk_at_stop,
    )


def risk_improvement_undefined() -> RiskImprovementComponent:
    """Refusal branch: zero current risk -> proportion undefined, score None."""

    return risk_improvement_component_score(
        current_risk=Decimal("0"),
        proposed_risk=Decimal("1500"),
    )


def risk_improvement_worsened() -> RiskImprovementComponent:
    """Worsened branch: the proposed book risks more -> signed negative, score 0."""

    return risk_improvement_component_score(
        current_risk=Decimal("6000"),
        proposed_risk=Decimal("9000"),
    )


# --- btc_predictor.signals.add_requirements.add_requirements_from_results -------------


def _add_requirements(
    *,
    lifecycle_builder: Callable[[StrategyConfig], PositionLifecycle],
    add_complete: bool = True,
) -> AddRequirementsResult:
    config = _config()
    return add_requirements_from_results(
        lifecycle=lifecycle_builder(config),
        current_price="67000",
        add_score=_add_score_result(config, complete=add_complete),
        risk_improvement=_risk_improvement(config),
        projected_risk_at_stop=_proposed_book_risk(config),
        new_structural_confirmation=True,
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        strategy_config=config,
        source_reason_codes={"new_structure": ("HIGHER_LOW_CONFIRMED",)},
    )


def add_requirements_satisfied() -> AddRequirementsResult:
    """Main path: profitable open position and every gate met -> ADD_REQUIREMENTS_SATISFIED."""

    return _add_requirements(lifecycle_builder=_open_lifecycle)


def add_requirements_no_open_position() -> AddRequirementsResult:
    """Missing-input branch: WATCH lifecycle -> profitability unresolved, add blocked."""

    return _add_requirements(lifecycle_builder=_watch_lifecycle)


def add_requirements_add_score_incomplete() -> AddRequirementsResult:
    """Missing-input branch: incomplete Add Score resolves to None and blocks."""

    return _add_requirements(lifecycle_builder=_open_lifecycle, add_complete=False)


# --- btc_predictor.risk.trailing.trail_stop_for_position ------------------------------


def trail_stop_advanced() -> TrailingStopResult:
    """Main path: confirmed higher low less a complete buffer advances the stop."""

    config = _config()
    lifecycle = _open_lifecycle(config)
    metadata = config.run_metadata()
    return trail_stop_for_position(
        lifecycle,
        structure=_higher_low(metadata),
        buffer=_complete_buffer(config, metadata),
        current_price=Decimal("66500"),
        as_of=_at(30),
    )


def trail_stop_buffer_incomplete() -> TrailingStopResult:
    """Incomplete branch: a refused invalidation yields no buffer -> held, incomplete."""

    config = _config()
    lifecycle = _open_lifecycle(config)
    metadata = config.run_metadata()
    return trail_stop_for_position(
        lifecycle,
        structure=_higher_low(metadata),
        buffer=_refused_buffer(config, metadata),
        current_price=Decimal("66500"),
        as_of=_at(30),
    )


def trail_stop_no_structure() -> TrailingStopResult:
    """Missing-input branch: no newly confirmed structure -> TRAILING_STOP_NO_NEW_STRUCTURE."""

    config = _config()
    lifecycle = _open_lifecycle(config)
    return trail_stop_for_position(
        lifecycle,
        structure=None,
        buffer=None,
        current_price=Decimal("66500"),
        as_of=_at(30),
    )


# --- btc_predictor.risk.trailing.apply_trailing_stop ----------------------------------


def apply_trailing_stop_advanced() -> PositionLifecycle:
    """Main path: an advanced result is recorded as an accepted STOP_MOVE."""

    config = _config()
    lifecycle = _open_lifecycle(config)
    metadata = config.run_metadata()
    result = trail_stop_for_position(
        lifecycle,
        structure=_higher_low(metadata),
        buffer=_complete_buffer(config, metadata),
        current_price=Decimal("66500"),
        as_of=_at(30),
    )
    return apply_trailing_stop(lifecycle, result, event_time=_at(31))


def apply_trailing_stop_held() -> PositionLifecycle:
    """No-op branch: a held (buffer-incomplete) result leaves the lifecycle unchanged."""

    config = _config()
    lifecycle = _open_lifecycle(config)
    metadata = config.run_metadata()
    result = trail_stop_for_position(
        lifecycle,
        structure=_higher_low(metadata),
        buffer=_refused_buffer(config, metadata),
        current_price=Decimal("66500"),
        as_of=_at(30),
    )
    return apply_trailing_stop(lifecycle, result, event_time=_at(31))


def apply_trailing_stop_structure_reused() -> PositionLifecycle:
    """Replay branch: the same structure cannot advance the stop twice."""

    config = _config()
    lifecycle = _open_lifecycle(config)
    metadata = config.run_metadata()
    structure = _higher_low(metadata)
    first = trail_stop_for_position(
        lifecycle,
        structure=structure,
        buffer=_complete_buffer(config, metadata),
        current_price=Decimal("66500"),
        as_of=_at(30),
    )
    advanced = apply_trailing_stop(lifecycle, first, event_time=_at(31))
    again = trail_stop_for_position(
        advanced,
        structure=structure,
        buffer=_complete_buffer(config, metadata),
        current_price=Decimal("66500"),
        as_of=_at(32),
    )
    return apply_trailing_stop(advanced, again, event_time=_at(33))


# --- btc_predictor.signals.trim.trim_rules_from_results -------------------------------


def trim_flow_deterioration() -> TrimSignalResult:
    """Main path: open position, Hold in the hold band, flow fell -> TRIM signal."""

    config = _config()
    return trim_rules_from_results(
        lifecycle=_open_lifecycle(config),
        hold_score=_hold_result(config, flow="78"),
        euphoria=_euphoria_result(config),
        crowding=_crowding_result(config),
        current_flow=_flow_result(config, "-0.5"),
        prior_flow=_flow_result(config, "0.5"),
        strategy_config=config,
    )


def trim_euphoria_incomplete() -> TrimSignalResult:
    """Missing-input branch: an incomplete Euphoria flag -> TRIM_INPUT_MISSING."""

    config = _config()
    return trim_rules_from_results(
        lifecycle=_open_lifecycle(config),
        hold_score=_hold_result(config, flow="78"),
        euphoria=_euphoria_result(config, complete=False),
        crowding=_crowding_result(config),
        current_flow=_flow_result(config, "0.5"),
        prior_flow=_flow_result(config, "0.5"),
        strategy_config=config,
    )


def trim_no_open_position() -> TrimSignalResult:
    """Suppression branch: WATCH lifecycle -> TRIM_NO_OPEN_POSITION."""

    config = _config()
    return trim_rules_from_results(
        lifecycle=_watch_lifecycle(config),
        hold_score=_hold_result(config, flow="78"),
        euphoria=_euphoria_result(config),
        crowding=_crowding_result(config),
        current_flow=_flow_result(config, "-0.5"),
        prior_flow=_flow_result(config, "0.5"),
        strategy_config=config,
    )


# --- btc_predictor.signals.exit_rules.exit_rules_for_position -------------------------


def exit_structural_stop() -> ExitSignalResult:
    """Main path: price touched the standing stop -> complete EXIT (STRUCTURAL_STOP)."""

    config = _config()
    return exit_rules_for_position(
        lifecycle=_open_lifecycle(config),
        current_price=Decimal("53900"),
        hold_score=_hold_result(config, flow="78"),
        regime_invalidated=False,
        data_risk_exit_required=False,
        manual_research_override=False,
        manual_override_reason=None,
        strategy_config=config,
        evaluated_at=_at(40),
        source_reason_codes={"regime": ("REGIME_SUPPORTIVE",)},
    )


def exit_inputs_missing() -> ExitSignalResult:
    """Missing-input branch: no observed price and an incomplete Hold Score."""

    config = _config()
    return exit_rules_for_position(
        lifecycle=_open_lifecycle(config),
        current_price=None,
        hold_score=_hold_result(config, flow=None),
        regime_invalidated=None,
        data_risk_exit_required=False,
        manual_research_override=False,
        manual_override_reason=None,
        strategy_config=config,
        evaluated_at=_at(40),
    )


def exit_not_triggered() -> ExitSignalResult:
    """Complete, not triggered: price above stop and Hold above exit_below."""

    config = _config()
    return exit_rules_for_position(
        lifecycle=_open_lifecycle(config),
        current_price=Decimal("64000"),
        hold_score=_hold_result(config, flow="78"),
        regime_invalidated=False,
        data_risk_exit_required=False,
        manual_research_override=False,
        manual_override_reason=None,
        strategy_config=config,
        evaluated_at=_at(40),
    )


FIXTURES: dict[str, tuple[Callable[[], object], ...]] = {
    "btc_predictor.features.hold.calculate_hold_score": (
        hold_score_complete,
        hold_score_input_missing,
    ),
    "btc_predictor.features.add.calculate_add_score": (
        add_score_complete,
        add_score_input_missing,
    ),
    "btc_predictor.features.add.risk_improvement_component_score": (
        risk_improvement_improved,
        risk_improvement_undefined,
        risk_improvement_worsened,
    ),
    "btc_predictor.signals.add_requirements.add_requirements_from_results": (
        add_requirements_satisfied,
        add_requirements_no_open_position,
        add_requirements_add_score_incomplete,
    ),
    "btc_predictor.risk.trailing.trail_stop_for_position": (
        trail_stop_advanced,
        trail_stop_buffer_incomplete,
        trail_stop_no_structure,
    ),
    "btc_predictor.risk.trailing.apply_trailing_stop": (
        apply_trailing_stop_advanced,
        apply_trailing_stop_held,
        apply_trailing_stop_structure_reused,
    ),
    "btc_predictor.signals.trim.trim_rules_from_results": (
        trim_flow_deterioration,
        trim_euphoria_incomplete,
        trim_no_open_position,
    ),
    "btc_predictor.signals.exit_rules.exit_rules_for_position": (
        exit_structural_stop,
        exit_inputs_missing,
        exit_not_triggered,
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
