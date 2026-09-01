"""Walk-forward validation over the event-driven backtest (BTC-182).

One static train/test split answers exactly one question: how a rule behaved on
the single stretch of history somebody chose to hold out. Look at that stretch
while tuning and the answer stops meaning anything at all.
``WALK_FORWARD_VALIDATION_V1`` replaces it with an ordered sequence of folds.
Each fold has an in-sample window, an optional embargo, and an out-of-sample
window that begins strictly after both:

```text
rolling     [train][embargo][test]
                   [train][embargo][test]
                          [train][embargo][test]

expanding   [train][embargo][test]
            [train........][embargo][test]
            [train...............][embargo][test]
```

The leakage barrier is structural rather than advisory. The strategy that runs
a fold is produced by a factory handed the in-sample bars **only**, and BTC-180
then replays it over the out-of-sample bars **only**. The persisted fold proves
the second half: the engine result inside a fold starts on ``test_start`` and
ends on ``test_end``. What this module cannot police is a factory that reaches
for data it was never handed, so a calibrating factory should fit from its
``TrainingWindow`` and nothing else.

Three deliberate policies:

- ``INDEPENDENT_FOLD_CAPITAL_V1``. Every fold starts from the same NAV with a
  pristine account. Compounding folds would make fold *k* a function of folds
  *1..k-1*, which lets one lucky early fold carry a strategy that stopped
  working years ago.
- Out-of-sample windows never overlap. ``step_periods`` below ``test_periods``
  is rejected rather than aggregated, because pooling overlapping windows
  counts the same market twice and flatters everything computed from it.
- A tail too short for a full out-of-sample window is reported as untested
  periods, never tested as a short fold.

The engine sees a fold's out-of-sample bars alone, so a strategy needing price
history must seed it from the in-sample window the factory receives. That is
the honest arrangement: warm-up data is in-sample data.

``walk_forward_windows()`` splits any ordered UTC schedule, so BTC-048 decision
timestamps fold exactly like bar timestamps for research consumers.

A validation whose factory returns the same strategy for every fold measures
one fixed rule across time. It is evidence about that rule, not about a fitting
procedure; a fold that actually calibrated on its in-sample window says so by
declaring what it fitted.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import ROUND_HALF_EVEN, Decimal
from typing import Any

from btc_predictor.backtest.costs import CostProfile
from btc_predictor.backtest.engine import (
    BACKTEST_ENGINE_POLICY_VERSION,
    BacktestContext,
    BacktestIntent,
    BacktestResult,
    restore_backtest_result,
    run_backtest,
    validate_backtest_bars,
)
from btc_predictor.config.strategy import StrategyConfig, load_strategy_config
from btc_predictor.data import OhlcvBar, require_utc_datetime
from btc_predictor.portfolio.account import ExecutionCosts


WALK_FORWARD_FEATURE_ID = "WALK_FORWARD_VALIDATION"
WALK_FORWARD_POLICY_VERSION = "WALK_FORWARD_VALIDATION_V1"
WALK_FORWARD_SPLIT_POLICY_VERSION = "TRAIN_STRICTLY_BEFORE_TEST_V1"
WALK_FORWARD_CAPITAL_POLICY_VERSION = "INDEPENDENT_FOLD_CAPITAL_V1"
WALK_FORWARD_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"

ROLLING_SCHEME = "rolling"
EXPANDING_SCHEME = "expanding"
WALK_FORWARD_SCHEMES = (ROLLING_SCHEME, EXPANDING_SCHEME)

# Fold returns are quantized so a persisted aggregate replays exactly instead
# of depending on how many digits a consumer's decimal context happens to keep.
WALK_FORWARD_RETURN_EXPONENT = Decimal("1E-12")

WALK_FORWARD_REASON_CODES = (
    "WALK_FORWARD_ROLLING_WINDOWS",
    "WALK_FORWARD_EXPANDING_WINDOWS",
    "WALK_FORWARD_EMBARGO_APPLIED",
    "WALK_FORWARD_NO_EMBARGO",
    "WALK_FORWARD_OUT_OF_SAMPLE_CONTIGUOUS",
    "WALK_FORWARD_OUT_OF_SAMPLE_GAPS",
    "WALK_FORWARD_INDEPENDENT_FOLD_CAPITAL",
    "WALK_FORWARD_COST_PROFILE_APPLIED",
    "WALK_FORWARD_STRATEGY_CONSTANT",
    "WALK_FORWARD_STRATEGY_RECALIBRATED",
    "WALK_FORWARD_FOLD_CALIBRATED",
    "WALK_FORWARD_FOLD_UNCALIBRATED",
    "WALK_FORWARD_FOLD_NO_TRADES",
    "WALK_FORWARD_FOLD_POSITION_OPEN_AT_END",
    "WALK_FORWARD_TRAILING_PERIODS_UNTESTED",
    "WALK_FORWARD_NO_TRADES",
    "WALK_FORWARD_COMPLETE",
)

Strategy = Callable[[BacktestContext], BacktestIntent | None]


@dataclass(frozen=True)
class WalkForwardPlan:
    """The versioned split every fold of one validation is cut from."""

    feature_id: str
    policy_version: str
    split_policy_version: str
    parameter_status: str
    scheme: str
    train_periods: int
    test_periods: int
    step_periods: int
    embargo_periods: int
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...] = ()

    @property
    def minimum_periods(self) -> int:
        """Scheduled periods required before a single fold exists."""

        return self.train_periods + self.embargo_periods + self.test_periods

    def fold_count(self, periods: int) -> int:
        """Return how many complete folds ``periods`` scheduled points allow."""

        count = _non_negative_integer(periods, "periods")
        if count < self.minimum_periods:
            return 0
        return (count - self.minimum_periods) // self.step_periods + 1

    def as_record(self) -> dict[str, Any]:
        _validate_plan(self)
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "split_policy_version": self.split_policy_version,
            "parameter_status": self.parameter_status,
            "scheme": self.scheme,
            "train_periods": self.train_periods,
            "test_periods": self.test_periods,
            "step_periods": self.step_periods,
            "embargo_periods": self.embargo_periods,
            "minimum_periods": self.minimum_periods,
            "config_metadata": dict(self.config_metadata),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class WalkForwardWindow:
    """One fold's in-sample and out-of-sample boundaries."""

    fold_number: int
    scheme: str
    train_start_index: int
    train_stop_index: int
    test_start_index: int
    test_stop_index: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    embargo_periods: int
    embargo_start: datetime | None
    embargo_end: datetime | None

    @property
    def train_periods(self) -> int:
        return self.train_stop_index - self.train_start_index

    @property
    def test_periods(self) -> int:
        return self.test_stop_index - self.test_start_index

    def as_record(self) -> dict[str, Any]:
        _validate_window(self)
        return {
            "fold_number": self.fold_number,
            "scheme": self.scheme,
            "split_policy_version": WALK_FORWARD_SPLIT_POLICY_VERSION,
            "train_start_index": self.train_start_index,
            "train_stop_index": self.train_stop_index,
            "test_start_index": self.test_start_index,
            "test_stop_index": self.test_stop_index,
            "train_start": self.train_start.isoformat(),
            "train_end": self.train_end.isoformat(),
            "test_start": self.test_start.isoformat(),
            "test_end": self.test_end.isoformat(),
            "train_periods": self.train_periods,
            "test_periods": self.test_periods,
            "embargo_periods": self.embargo_periods,
            "embargo_start": _optional_time(self.embargo_start),
            "embargo_end": _optional_time(self.embargo_end),
        }


@dataclass(frozen=True)
class TrainingWindow:
    """Everything a fold's factory may see: its in-sample bars, and no more."""

    window: WalkForwardWindow
    symbol: str
    bars: tuple[OhlcvBar, ...]
    config: StrategyConfig

    def __post_init__(self) -> None:
        if not isinstance(self.window, WalkForwardWindow):
            raise TypeError("window must be a WalkForwardWindow")
        if not isinstance(self.bars, tuple):
            raise TypeError("training bars must be a tuple")
        if len(self.bars) != self.window.train_periods:
            raise ValueError("training bars must fill the in-sample window")
        if (
            self.bars[0].timestamp != self.window.train_start
            or self.bars[-1].timestamp != self.window.train_end
        ):
            raise ValueError("training bars must span the in-sample window exactly")


@dataclass(frozen=True)
class FoldStrategy:
    """The strategy a factory selected for one fold, with its identity."""

    strategy: Strategy
    strategy_id: str
    calibration: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not callable(self.strategy):
            raise TypeError("strategy must be callable")
        if not isinstance(self.strategy_id, str) or not self.strategy_id.strip():
            raise ValueError("strategy_id must not be empty")
        if self.calibration is None:
            return
        if not isinstance(self.calibration, Mapping):
            raise TypeError("calibration must be a mapping")
        if not self.calibration:
            # An empty mapping cannot say what was fitted, and a fold that
            # fitted nothing is uncalibrated rather than calibrated on nothing.
            raise ValueError("calibration must not be empty; use None when uncalibrated")


@dataclass(frozen=True)
class WalkForwardFold:
    """One out-of-sample run and the window it was cut for."""

    window: WalkForwardWindow
    strategy_id: str
    calibration: dict[str, Any] | None
    result: BacktestResult
    reason_codes: tuple[str, ...]

    @property
    def fold_number(self) -> int:
        return self.window.fold_number

    @property
    def starting_nav(self) -> Decimal:
        return self.result.starting_nav

    @property
    def ending_nav(self) -> Decimal:
        return self.result.ending_nav

    @property
    def total_pnl(self) -> Decimal:
        """NAV change over the fold, including any open position's mark."""

        return self.result.total_pnl

    @property
    def net_pnl(self) -> Decimal:
        """Realized net P&L; an open position's mark is not realized."""

        return self.result.net_pnl

    @property
    def return_fraction(self) -> Decimal:
        return _return_fraction(self.total_pnl, self.starting_nav)

    @property
    def trade_count(self) -> int:
        return len(self.result.trades)

    @property
    def closed_trade_count(self) -> int:
        return sum(1 for trade in self.result.trades if trade.closed)

    @property
    def missed_entries(self) -> int:
        return self.result.missed_entries

    @property
    def stopped_out(self) -> int:
        return self.result.stopped_out

    @property
    def position_open_at_end(self) -> bool:
        return self.result.final_lifecycle.quantity > 0

    def as_record(self) -> dict[str, Any]:
        _validate_fold(self)
        return {
            "fold_number": self.fold_number,
            "window": self.window.as_record(),
            "strategy_id": self.strategy_id,
            "calibration": (
                _json_copy(dict(self.calibration))
                if self.calibration is not None
                else None
            ),
            "starting_nav": str(self.starting_nav),
            "ending_nav": str(self.ending_nav),
            "total_pnl": str(self.total_pnl),
            "net_pnl": str(self.net_pnl),
            "return_fraction": str(self.return_fraction),
            "trade_count": self.trade_count,
            "closed_trade_count": self.closed_trade_count,
            "missed_entries": self.missed_entries,
            "stopped_out": self.stopped_out,
            "position_open_at_end": self.position_open_at_end,
            "result": self.result.as_record(),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class WalkForwardValidation:
    """Every fold of one walk-forward, with the split that produced them."""

    feature_id: str
    policy_version: str
    split_policy_version: str
    capital_policy_version: str
    engine_policy_version: str
    validation_id: str
    evidence_digest: str
    schedule_digest: str
    symbol: str
    plan: WalkForwardPlan
    starting_nav: Decimal
    effective_costs: ExecutionCosts
    cost_profile: CostProfile | None
    scheduled_periods: int
    tested_periods: int
    untested_leading_periods: int
    untested_trailing_periods: int
    folds: tuple[WalkForwardFold, ...]
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...]

    @property
    def fold_count(self) -> int:
        return len(self.folds)

    @property
    def untested_gap_periods(self) -> int:
        """Periods skipped between folds when the split steps over history."""

        return sum(
            current.window.test_start_index - previous.window.test_stop_index
            for previous, current in zip(self.folds, self.folds[1:])
        )

    @property
    def trade_count(self) -> int:
        return sum(fold.trade_count for fold in self.folds)

    @property
    def profitable_folds(self) -> int:
        return sum(1 for fold in self.folds if fold.total_pnl > 0)

    @property
    def losing_folds(self) -> int:
        return sum(1 for fold in self.folds if fold.total_pnl < 0)

    @property
    def summed_net_pnl(self) -> Decimal:
        """Arithmetic sum of independent folds, not a compounded equity path."""

        return sum((fold.net_pnl for fold in self.folds), Decimal("0"))

    @property
    def mean_return_fraction(self) -> Decimal:
        """Unweighted mean of fold returns; folds are equal-length by policy."""

        total = sum((fold.return_fraction for fold in self.folds), Decimal("0"))
        return (total / self.fold_count).quantize(
            WALK_FORWARD_RETURN_EXPONENT,
            rounding=ROUND_HALF_EVEN,
        )

    @property
    def worst_fold(self) -> WalkForwardFold:
        return min(self.folds, key=lambda fold: (fold.return_fraction, fold.fold_number))

    @property
    def best_fold(self) -> WalkForwardFold:
        return max(self.folds, key=lambda fold: (fold.return_fraction, -fold.fold_number))

    def as_record(self) -> dict[str, Any]:
        _validate_validation(self)
        payload = _validation_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise ValueError("walk-forward evidence does not match evidence_digest")
        return {**payload, "evidence_digest": self.evidence_digest}


def walk_forward_plan(
    config: StrategyConfig | None = None,
    *,
    scheme: str | None = None,
    train_periods: int | None = None,
    test_periods: int | None = None,
    step_periods: int | None = None,
    embargo_periods: int | None = None,
) -> WalkForwardPlan:
    """Resolve the configured split, with explicit research overrides."""

    resolved = config if config is not None else load_strategy_config()
    if not isinstance(resolved, StrategyConfig):
        raise TypeError("config must be a StrategyConfig")
    declared = resolved.backtest.walk_forward
    selected_scheme = scheme if scheme is not None else declared.scheme
    if selected_scheme not in WALK_FORWARD_SCHEMES:
        raise ValueError(f"scheme must be one of {WALK_FORWARD_SCHEMES}")
    train = (
        _positive_integer(train_periods, "train_periods")
        if train_periods is not None
        else declared.train_periods
    )
    test = (
        _positive_integer(test_periods, "test_periods")
        if test_periods is not None
        else declared.test_periods
    )
    step = (
        _positive_integer(step_periods, "step_periods")
        if step_periods is not None
        else declared.step_periods
    )
    embargo = (
        _non_negative_integer(embargo_periods, "embargo_periods")
        if embargo_periods is not None
        else declared.embargo_periods
    )
    plan = WalkForwardPlan(
        feature_id=WALK_FORWARD_FEATURE_ID,
        policy_version=WALK_FORWARD_POLICY_VERSION,
        split_policy_version=WALK_FORWARD_SPLIT_POLICY_VERSION,
        parameter_status=WALK_FORWARD_PARAMETER_STATUS,
        scheme=selected_scheme,
        train_periods=train,
        test_periods=test,
        step_periods=step,
        embargo_periods=embargo,
        config_metadata=resolved.run_metadata(),
        reason_codes=_plan_reason_codes(
            scheme=selected_scheme,
            test_periods=test,
            step_periods=step,
            embargo_periods=embargo,
        ),
    )
    plan.as_record()
    return plan


def restore_walk_forward_plan(record: Mapping[str, Any]) -> WalkForwardPlan:
    """Restore a persisted split and reject drift or tampering."""

    source = _mapping(record, "plan")
    plan = WalkForwardPlan(
        feature_id=_string(source.get("feature_id"), "plan.feature_id"),
        policy_version=_string(source.get("policy_version"), "plan.policy_version"),
        split_policy_version=_string(
            source.get("split_policy_version"), "plan.split_policy_version"
        ),
        parameter_status=_string(
            source.get("parameter_status"), "plan.parameter_status"
        ),
        scheme=_string(source.get("scheme"), "plan.scheme"),
        train_periods=_positive_integer(
            source.get("train_periods"), "plan.train_periods"
        ),
        test_periods=_positive_integer(source.get("test_periods"), "plan.test_periods"),
        step_periods=_positive_integer(source.get("step_periods"), "plan.step_periods"),
        embargo_periods=_non_negative_integer(
            source.get("embargo_periods"), "plan.embargo_periods"
        ),
        config_metadata=_string_mapping(
            source.get("config_metadata"), "plan.config_metadata"
        ),
        reason_codes=_string_tuple(source.get("reason_codes"), "plan.reason_codes"),
    )
    if plan.as_record() != dict(source):
        raise ValueError("record does not match reconstructed walk-forward plan")
    return plan


def walk_forward_windows(
    schedule: Sequence[datetime],
    *,
    plan: WalkForwardPlan | None = None,
) -> tuple[WalkForwardWindow, ...]:
    """Cut an ordered UTC schedule into complete walk-forward folds."""

    resolved = plan if plan is not None else walk_forward_plan()
    if not isinstance(resolved, WalkForwardPlan):
        raise TypeError("plan must be a WalkForwardPlan")
    resolved.as_record()
    timestamps = _validate_schedule(schedule)
    folds = resolved.fold_count(len(timestamps))
    if folds < 2:
        # One fold is still the static train/test split this ticket replaces.
        # A walk-forward needs at least one subsequent step before it can say
        # how the rule behaved across changing in-sample windows.
        minimum = resolved.minimum_periods + resolved.step_periods
        raise ValueError(
            "walk-forward validation requires at least two complete folds; "
            f"a {resolved.scheme} split of {resolved.train_periods} train, "
            f"{resolved.embargo_periods} embargo and {resolved.test_periods} test "
            f"periods stepped by {resolved.step_periods} needs at least {minimum} "
            "scheduled periods; "
            f"{len(timestamps)} were supplied"
        )
    windows = tuple(
        _window(resolved, fold_number, timestamps)
        for fold_number in range(1, folds + 1)
    )
    _validate_window_sequence(windows, plan=resolved)
    return windows


def run_walk_forward(
    bars: Sequence[OhlcvBar],
    *,
    strategy_factory: Callable[[TrainingWindow], FoldStrategy],
    plan: WalkForwardPlan | None = None,
    symbol: str = "BTC-USD",
    starting_nav: Any | None = None,
    strategy_config: StrategyConfig | None = None,
    costs: ExecutionCosts | None = None,
    cost_profile: str | None = None,
) -> WalkForwardValidation:
    """Replay one strategy per fold over out-of-sample bars only.

    ``strategy_factory`` receives a :class:`TrainingWindow` holding that fold's
    in-sample bars and returns the :class:`FoldStrategy` to evaluate. It never
    sees an out-of-sample bar, and the strategy it returns never sees an
    in-sample one, so the split cannot be crossed by accident.
    """

    config = strategy_config if strategy_config is not None else load_strategy_config()
    if not isinstance(config, StrategyConfig):
        raise TypeError("strategy_config must be a StrategyConfig")
    if not callable(strategy_factory):
        raise TypeError("strategy_factory must be callable")
    metadata = config.run_metadata()
    resolved_plan = plan if plan is not None else walk_forward_plan(config)
    if not isinstance(resolved_plan, WalkForwardPlan):
        raise TypeError("plan must be a WalkForwardPlan")
    if resolved_plan.config_metadata != metadata:
        raise ValueError("plan config_metadata must match the run")
    ordered = validate_backtest_bars(bars, symbol=symbol)
    windows = walk_forward_windows(
        [bar.timestamp for bar in ordered],
        plan=resolved_plan,
    )

    folds: list[WalkForwardFold] = []
    declared_calibrations: dict[str, dict[str, Any] | None] = {}
    for window in windows:
        selected = strategy_factory(
            TrainingWindow(
                window=window,
                symbol=symbol,
                bars=ordered[window.train_start_index : window.train_stop_index],
                config=config,
            )
        )
        if not isinstance(selected, FoldStrategy):
            raise TypeError("strategy_factory must return a FoldStrategy")
        calibration = (
            _json_copy(dict(selected.calibration))
            if selected.calibration is not None
            else None
        )
        if (
            selected.strategy_id in declared_calibrations
            and declared_calibrations[selected.strategy_id] != calibration
        ):
            # One identity must mean one calibrated strategy, or a comparison
            # across folds is comparing two different things under one name.
            raise ValueError(
                f"strategy_id {selected.strategy_id!r} declares two different "
                "calibrations"
            )
        declared_calibrations[selected.strategy_id] = calibration
        result = run_backtest(
            ordered[window.test_start_index : window.test_stop_index],
            strategy=selected.strategy,
            symbol=symbol,
            starting_nav=starting_nav,
            strategy_config=config,
            costs=costs,
            cost_profile=cost_profile,
            strategy_id=selected.strategy_id,
        )
        folds.append(
            WalkForwardFold(
                window=window,
                strategy_id=selected.strategy_id,
                calibration=calibration,
                result=result,
                reason_codes=_fold_reason_codes(result, calibration),
            )
        )

    resolved_folds = tuple(folds)
    first = resolved_folds[0].result
    trailing = len(ordered) - resolved_folds[-1].window.test_stop_index
    validation = WalkForwardValidation(
        feature_id=WALK_FORWARD_FEATURE_ID,
        policy_version=WALK_FORWARD_POLICY_VERSION,
        split_policy_version=WALK_FORWARD_SPLIT_POLICY_VERSION,
        capital_policy_version=WALK_FORWARD_CAPITAL_POLICY_VERSION,
        engine_policy_version=BACKTEST_ENGINE_POLICY_VERSION,
        validation_id="",
        evidence_digest="",
        schedule_digest=_schedule_digest(bar.timestamp for bar in ordered),
        symbol=symbol,
        plan=resolved_plan,
        starting_nav=first.starting_nav,
        effective_costs=first.effective_costs,
        cost_profile=first.cost_profile,
        scheduled_periods=len(ordered),
        tested_periods=sum(fold.window.test_periods for fold in resolved_folds),
        untested_leading_periods=(
            resolved_plan.train_periods + resolved_plan.embargo_periods
        ),
        untested_trailing_periods=trailing,
        folds=resolved_folds,
        config_metadata=dict(metadata),
        reason_codes=_validation_reason_codes(
            folds=resolved_folds,
            cost_profile=first.cost_profile,
            untested_trailing_periods=trailing,
        ),
    )
    validation = replace(validation, validation_id=_validation_id(validation))
    _validate_validation(validation)
    return replace(
        validation,
        evidence_digest=_digest(_validation_payload(validation)),
    )


def restore_walk_forward_validation(
    record: Mapping[str, Any],
) -> WalkForwardValidation:
    """Restore persisted BTC-182 evidence and reject drift or tampering."""

    source = _mapping(record, "record")
    plan = restore_walk_forward_plan(_mapping(source.get("plan"), "plan"))
    folds = tuple(
        _fold_from_record(_mapping(item, "fold"))
        for item in _record_sequence(source.get("folds"), "folds")
    )
    if not folds:
        raise ValueError("a walk-forward validation must persist at least one fold")
    # Costs, the priced rung and the starting NAV are taken from the restored
    # engine evidence rather than parsed twice; the record's own copies are then
    # checked against them by the round-trip comparison below.
    first = folds[0].result
    validation = WalkForwardValidation(
        feature_id=_string(source.get("feature_id"), "feature_id"),
        policy_version=_string(source.get("policy_version"), "policy_version"),
        split_policy_version=_string(
            source.get("split_policy_version"), "split_policy_version"
        ),
        capital_policy_version=_string(
            source.get("capital_policy_version"), "capital_policy_version"
        ),
        engine_policy_version=_string(
            source.get("engine_policy_version"), "engine_policy_version"
        ),
        validation_id=_string(source.get("validation_id"), "validation_id"),
        evidence_digest=_string(source.get("evidence_digest"), "evidence_digest"),
        schedule_digest=_string(source.get("schedule_digest"), "schedule_digest"),
        symbol=_string(source.get("symbol"), "symbol"),
        plan=plan,
        starting_nav=first.starting_nav,
        effective_costs=first.effective_costs,
        cost_profile=first.cost_profile,
        scheduled_periods=_non_negative_integer(
            source.get("scheduled_periods"), "scheduled_periods"
        ),
        tested_periods=_non_negative_integer(
            source.get("tested_periods"), "tested_periods"
        ),
        untested_leading_periods=_non_negative_integer(
            source.get("untested_leading_periods"), "untested_leading_periods"
        ),
        untested_trailing_periods=_non_negative_integer(
            source.get("untested_trailing_periods"), "untested_trailing_periods"
        ),
        folds=folds,
        config_metadata=_string_mapping(
            source.get("config_metadata"), "config_metadata"
        ),
        reason_codes=_string_tuple(source.get("reason_codes"), "reason_codes"),
    )
    if validation.as_record() != dict(source):
        raise ValueError("record does not match reconstructed walk-forward evidence")
    return validation


def _window(
    plan: WalkForwardPlan,
    fold_number: int,
    timestamps: tuple[datetime, ...],
) -> WalkForwardWindow:
    train_start, train_stop, test_start, test_stop = _window_indices(plan, fold_number)
    embargoed = timestamps[train_stop:test_start]
    window = WalkForwardWindow(
        fold_number=fold_number,
        scheme=plan.scheme,
        train_start_index=train_start,
        train_stop_index=train_stop,
        test_start_index=test_start,
        test_stop_index=test_stop,
        train_start=timestamps[train_start],
        train_end=timestamps[train_stop - 1],
        test_start=timestamps[test_start],
        test_end=timestamps[test_stop - 1],
        embargo_periods=plan.embargo_periods,
        embargo_start=embargoed[0] if embargoed else None,
        embargo_end=embargoed[-1] if embargoed else None,
    )
    window.as_record()
    return window


def _window_indices(plan: WalkForwardPlan, fold_number: int) -> tuple[int, int, int, int]:
    """Return the index bounds of one fold; a pure function of the plan."""

    number = _positive_integer(fold_number, "fold_number")
    offset = (number - 1) * plan.step_periods
    train_stop = offset + plan.train_periods
    train_start = 0 if plan.scheme == EXPANDING_SCHEME else offset
    test_start = train_stop + plan.embargo_periods
    return train_start, train_stop, test_start, test_start + plan.test_periods


def _plan_reason_codes(
    *,
    scheme: str,
    test_periods: int,
    step_periods: int,
    embargo_periods: int,
) -> tuple[str, ...]:
    codes = [
        "WALK_FORWARD_ROLLING_WINDOWS"
        if scheme == ROLLING_SCHEME
        else "WALK_FORWARD_EXPANDING_WINDOWS",
        "WALK_FORWARD_EMBARGO_APPLIED"
        if embargo_periods > 0
        else "WALK_FORWARD_NO_EMBARGO",
        "WALK_FORWARD_OUT_OF_SAMPLE_GAPS"
        if step_periods > test_periods
        else "WALK_FORWARD_OUT_OF_SAMPLE_CONTIGUOUS",
    ]
    return tuple(codes)


def _fold_reason_codes(
    result: BacktestResult,
    calibration: Mapping[str, Any] | None,
) -> tuple[str, ...]:
    codes = [
        "WALK_FORWARD_FOLD_CALIBRATED"
        if calibration is not None
        else "WALK_FORWARD_FOLD_UNCALIBRATED"
    ]
    if not result.trades:
        codes.append("WALK_FORWARD_FOLD_NO_TRADES")
    if result.final_lifecycle.quantity > 0:
        # Its NAV includes a mark, not a realized exit; BTC-180 never forces
        # a liquidation at the end of a dataset.
        codes.append("WALK_FORWARD_FOLD_POSITION_OPEN_AT_END")
    return tuple(codes)


def _validation_reason_codes(
    *,
    folds: tuple[WalkForwardFold, ...],
    cost_profile: CostProfile | None,
    untested_trailing_periods: int,
) -> tuple[str, ...]:
    codes = ["WALK_FORWARD_INDEPENDENT_FOLD_CAPITAL"]
    if cost_profile is not None:
        codes.append("WALK_FORWARD_COST_PROFILE_APPLIED")
    identities = {fold.strategy_id for fold in folds}
    calibrated = any(fold.calibration is not None for fold in folds)
    codes.append(
        "WALK_FORWARD_STRATEGY_RECALIBRATED"
        if len(identities) > 1 or calibrated
        else "WALK_FORWARD_STRATEGY_CONSTANT"
    )
    if untested_trailing_periods > 0:
        codes.append("WALK_FORWARD_TRAILING_PERIODS_UNTESTED")
    if all(not fold.result.trades for fold in folds):
        # No trade anywhere is not a passed validation; it is no evidence.
        codes.append("WALK_FORWARD_NO_TRADES")
    codes.append("WALK_FORWARD_COMPLETE")
    return tuple(codes)


def _validate_plan(plan: WalkForwardPlan) -> None:
    if plan.feature_id != WALK_FORWARD_FEATURE_ID:
        raise ValueError(f"feature_id must be {WALK_FORWARD_FEATURE_ID}")
    if plan.policy_version != WALK_FORWARD_POLICY_VERSION:
        raise ValueError(f"policy_version must be {WALK_FORWARD_POLICY_VERSION}")
    if plan.split_policy_version != WALK_FORWARD_SPLIT_POLICY_VERSION:
        raise ValueError(
            f"split_policy_version must be {WALK_FORWARD_SPLIT_POLICY_VERSION}"
        )
    if plan.parameter_status != WALK_FORWARD_PARAMETER_STATUS:
        raise ValueError(f"parameter_status must be {WALK_FORWARD_PARAMETER_STATUS}")
    if plan.scheme not in WALK_FORWARD_SCHEMES:
        raise ValueError(f"scheme must be one of {WALK_FORWARD_SCHEMES}")
    _positive_integer(plan.train_periods, "train_periods")
    _positive_integer(plan.test_periods, "test_periods")
    _positive_integer(plan.step_periods, "step_periods")
    _non_negative_integer(plan.embargo_periods, "embargo_periods")
    if plan.step_periods < plan.test_periods:
        # Overlapping out-of-sample windows would count the same market twice
        # in every aggregate computed from the folds.
        raise ValueError(
            "step_periods must be at least test_periods so out-of-sample "
            "windows never overlap"
        )
    _string_mapping(plan.config_metadata, "plan.config_metadata")
    expected = _plan_reason_codes(
        scheme=plan.scheme,
        test_periods=plan.test_periods,
        step_periods=plan.step_periods,
        embargo_periods=plan.embargo_periods,
    )
    if plan.reason_codes != expected:
        raise ValueError("plan reason codes do not describe the plan")
    _validate_reason_codes(plan.reason_codes)


def _validate_window(window: WalkForwardWindow) -> None:
    _positive_integer(window.fold_number, "fold_number")
    if window.scheme not in WALK_FORWARD_SCHEMES:
        raise ValueError(f"scheme must be one of {WALK_FORWARD_SCHEMES}")
    _non_negative_integer(window.train_start_index, "train_start_index")
    _non_negative_integer(window.embargo_periods, "embargo_periods")
    if window.train_stop_index <= window.train_start_index:
        raise ValueError("an in-sample window must contain at least one period")
    if window.test_stop_index <= window.test_start_index:
        raise ValueError("an out-of-sample window must contain at least one period")
    if window.test_start_index != window.train_stop_index + window.embargo_periods:
        raise ValueError("an out-of-sample window must begin after the embargo")
    if window.train_end >= window.test_start:
        raise ValueError("in-sample data must end strictly before out-of-sample data")
    for name in ("train_start", "train_end", "test_start", "test_end"):
        require_utc_datetime(getattr(window, name), f"window.{name}")
    if window.train_start > window.train_end or window.test_start > window.test_end:
        raise ValueError("window boundaries must be in time order")
    embargoed = (window.embargo_start, window.embargo_end)
    if window.embargo_periods == 0:
        if any(value is not None for value in embargoed):
            raise ValueError("a window without an embargo cannot embargo periods")
    else:
        if any(value is None for value in embargoed):
            raise ValueError("an embargoed window must record its embargoed periods")
        require_utc_datetime(window.embargo_start, "window.embargo_start")
        require_utc_datetime(window.embargo_end, "window.embargo_end")
        if not window.train_end < window.embargo_start <= window.embargo_end:
            raise ValueError("embargoed periods must lie between train and test")
        if window.embargo_end >= window.test_start:
            raise ValueError("embargoed periods must end before out-of-sample data")


def _validate_window_sequence(
    windows: tuple[WalkForwardWindow, ...],
    *,
    plan: WalkForwardPlan,
) -> None:
    if not windows:
        raise ValueError("a walk-forward split must produce at least one fold")
    for position, window in enumerate(windows, start=1):
        if window.fold_number != position:
            raise ValueError("fold numbers must be contiguous from one")
        if window.scheme != plan.scheme:
            raise ValueError("every window must share the plan's scheme")
        if window.embargo_periods != plan.embargo_periods:
            raise ValueError("every window must share the plan's embargo")
        if window.test_periods != plan.test_periods:
            raise ValueError("every out-of-sample window must be the planned length")
        if (
            window.train_start_index,
            window.train_stop_index,
            window.test_start_index,
            window.test_stop_index,
        ) != _window_indices(plan, position):
            raise ValueError("window indices do not match the plan")
    for previous, current in zip(windows, windows[1:]):
        if current.test_start_index < previous.test_stop_index:
            raise ValueError("out-of-sample windows must not overlap")
        if current.test_start <= previous.test_end:
            raise ValueError("out-of-sample windows must advance in time")


def _validate_fold(fold: WalkForwardFold) -> None:
    if not isinstance(fold.window, WalkForwardWindow):
        raise TypeError("fold.window must be a WalkForwardWindow")
    if not isinstance(fold.result, BacktestResult):
        raise TypeError("fold.result must be a BacktestResult")
    _string(fold.strategy_id, "fold.strategy_id")
    if fold.calibration is not None:
        if not isinstance(fold.calibration, Mapping) or not fold.calibration:
            raise ValueError("fold.calibration must be a non-empty mapping or None")
    if fold.result.strategy_id != fold.strategy_id:
        raise ValueError("fold strategy_id must match the run it produced")
    # The whole leakage barrier, restated as evidence: the engine replayed the
    # out-of-sample window and nothing else.
    if fold.result.bar_count != fold.window.test_periods:
        raise ValueError("a fold must replay exactly its out-of-sample window")
    if (
        fold.result.started_at != fold.window.test_start
        or fold.result.ended_at != fold.window.test_end
    ):
        raise ValueError("a fold's run must span its out-of-sample window")
    expected = _fold_reason_codes(fold.result, fold.calibration)
    if fold.reason_codes != expected:
        raise ValueError("fold reason codes do not describe the fold")
    _validate_reason_codes(fold.reason_codes)


def _validate_validation(validation: WalkForwardValidation) -> None:
    if validation.feature_id != WALK_FORWARD_FEATURE_ID:
        raise ValueError(f"feature_id must be {WALK_FORWARD_FEATURE_ID}")
    if validation.policy_version != WALK_FORWARD_POLICY_VERSION:
        raise ValueError(f"policy_version must be {WALK_FORWARD_POLICY_VERSION}")
    if validation.split_policy_version != WALK_FORWARD_SPLIT_POLICY_VERSION:
        raise ValueError(
            f"split_policy_version must be {WALK_FORWARD_SPLIT_POLICY_VERSION}"
        )
    if validation.capital_policy_version != WALK_FORWARD_CAPITAL_POLICY_VERSION:
        raise ValueError(
            f"capital_policy_version must be {WALK_FORWARD_CAPITAL_POLICY_VERSION}"
        )
    if validation.engine_policy_version != BACKTEST_ENGINE_POLICY_VERSION:
        raise ValueError(
            f"engine_policy_version must be {BACKTEST_ENGINE_POLICY_VERSION}"
        )
    plan = validation.plan
    plan.as_record()
    if not validation.folds:
        raise ValueError("a walk-forward validation must contain at least one fold")
    _string(validation.symbol, "symbol")
    _string_mapping(validation.config_metadata, "config_metadata")
    validation.effective_costs.as_record()
    _validate_window_sequence(
        tuple(fold.window for fold in validation.folds),
        plan=plan,
    )
    for fold in validation.folds:
        fold.as_record()
        result = fold.result
        if result.symbol != validation.symbol:
            raise ValueError("every fold must replay the validated symbol")
        if result.config_metadata != validation.config_metadata:
            raise ValueError("every fold must share the run's config identity")
        if result.starting_nav != validation.starting_nav:
            # INDEPENDENT_FOLD_CAPITAL_V1: folds are independent experiments,
            # so a later fold cannot inherit an earlier fold's winnings.
            raise ValueError("every fold must start from the same capital")
        if result.effective_costs != validation.effective_costs:
            raise ValueError("every fold must price the same execution costs")
        if result.cost_profile != validation.cost_profile:
            raise ValueError("every fold must execute under the same cost profile")
    if validation.cost_profile is not None:
        validation.cost_profile.as_record()
        if validation.cost_profile.costs != validation.effective_costs:
            raise ValueError("cost_profile costs must equal effective_costs")
    if plan.config_metadata != validation.config_metadata:
        raise ValueError("plan config identity must match the validation")
    if validation.tested_periods != validation.fold_count * plan.test_periods:
        raise ValueError("tested periods must equal the folded out-of-sample length")
    if validation.untested_leading_periods != plan.train_periods + plan.embargo_periods:
        raise ValueError("untested leading periods must equal train plus embargo")
    last = validation.folds[-1].window.test_stop_index
    if validation.scheduled_periods != last + validation.untested_trailing_periods:
        raise ValueError("scheduled periods must account for every untested period")
    accounted = (
        validation.untested_leading_periods
        + validation.tested_periods
        + validation.untested_gap_periods
        + validation.untested_trailing_periods
    )
    if accounted != validation.scheduled_periods:
        # Coverage has to add up, or "tested out of sample" is a claim about an
        # unknown share of the history.
        raise ValueError("tested and untested periods must cover the schedule")
    if plan.fold_count(validation.scheduled_periods) != validation.fold_count:
        raise ValueError("the schedule and plan do not produce the recorded folds")
    expected = _validation_reason_codes(
        folds=validation.folds,
        cost_profile=validation.cost_profile,
        untested_trailing_periods=validation.untested_trailing_periods,
    )
    if validation.reason_codes != expected:
        raise ValueError("validation reason codes do not describe the validation")
    _validate_reason_codes(validation.reason_codes)
    if validation.validation_id != _validation_id(validation):
        raise ValueError("validation inputs do not match validation_id")


def _validate_reason_codes(codes: tuple[str, ...]) -> None:
    for code in codes:
        if code not in WALK_FORWARD_REASON_CODES:
            raise ValueError(f"undeclared walk-forward reason code: {code}")
    if len(set(codes)) != len(codes):
        raise ValueError("reason codes must not repeat")


def _validation_id(validation: WalkForwardValidation) -> str:
    return _digest(
        {
            "policy": WALK_FORWARD_POLICY_VERSION,
            "split_policy": WALK_FORWARD_SPLIT_POLICY_VERSION,
            "capital_policy": WALK_FORWARD_CAPITAL_POLICY_VERSION,
            "engine_policy": validation.engine_policy_version,
            "plan": validation.plan.as_record(),
            "schedule_digest": validation.schedule_digest,
            "scheduled_periods": validation.scheduled_periods,
            "symbol": validation.symbol,
            "starting_nav": str(validation.starting_nav),
            "costs": validation.effective_costs.as_record(),
            "cost_profile": (
                validation.cost_profile.profile
                if validation.cost_profile is not None
                else None
            ),
            "folds": [
                {
                    "fold_number": fold.fold_number,
                    "strategy_id": fold.strategy_id,
                    "calibration": (
                        _json_copy(dict(fold.calibration))
                        if fold.calibration is not None
                        else None
                    ),
                    "run_id": fold.result.run_id,
                }
                for fold in validation.folds
            ],
        }
    )


def _validation_payload(validation: WalkForwardValidation) -> dict[str, Any]:
    return {
        "feature_id": validation.feature_id,
        "policy_version": validation.policy_version,
        "split_policy_version": validation.split_policy_version,
        "capital_policy_version": validation.capital_policy_version,
        "engine_policy_version": validation.engine_policy_version,
        "validation_id": validation.validation_id,
        "schedule_digest": validation.schedule_digest,
        "symbol": validation.symbol,
        "plan": validation.plan.as_record(),
        "starting_nav": str(validation.starting_nav),
        "effective_costs": validation.effective_costs.as_record(),
        "cost_profile": (
            validation.cost_profile.as_record()
            if validation.cost_profile is not None
            else None
        ),
        "scheduled_periods": validation.scheduled_periods,
        "tested_periods": validation.tested_periods,
        "untested_leading_periods": validation.untested_leading_periods,
        "untested_gap_periods": validation.untested_gap_periods,
        "untested_trailing_periods": validation.untested_trailing_periods,
        "fold_count": validation.fold_count,
        "trade_count": validation.trade_count,
        "profitable_folds": validation.profitable_folds,
        "losing_folds": validation.losing_folds,
        "summed_net_pnl": str(validation.summed_net_pnl),
        "mean_return_fraction": str(validation.mean_return_fraction),
        "best_fold_number": validation.best_fold.fold_number,
        "best_fold_return_fraction": str(validation.best_fold.return_fraction),
        "worst_fold_number": validation.worst_fold.fold_number,
        "worst_fold_return_fraction": str(validation.worst_fold.return_fraction),
        "folds": [fold.as_record() for fold in validation.folds],
        "config_metadata": dict(validation.config_metadata),
        "reason_codes": list(validation.reason_codes),
    }


def _fold_from_record(source: Mapping[str, Any]) -> WalkForwardFold:
    calibration = source.get("calibration")
    return WalkForwardFold(
        window=_window_from_record(_mapping(source.get("window"), "fold.window")),
        strategy_id=_string(source.get("strategy_id"), "fold.strategy_id"),
        calibration=(
            _mapping(calibration, "fold.calibration") if calibration is not None else None
        ),
        result=restore_backtest_result(_mapping(source.get("result"), "fold.result")),
        reason_codes=_string_tuple(source.get("reason_codes"), "fold.reason_codes"),
    )


def _window_from_record(source: Mapping[str, Any]) -> WalkForwardWindow:
    if source.get("split_policy_version") != WALK_FORWARD_SPLIT_POLICY_VERSION:
        raise ValueError(
            f"split_policy_version must be {WALK_FORWARD_SPLIT_POLICY_VERSION}"
        )
    return WalkForwardWindow(
        fold_number=_positive_integer(source.get("fold_number"), "window.fold_number"),
        scheme=_string(source.get("scheme"), "window.scheme"),
        train_start_index=_non_negative_integer(
            source.get("train_start_index"), "window.train_start_index"
        ),
        train_stop_index=_non_negative_integer(
            source.get("train_stop_index"), "window.train_stop_index"
        ),
        test_start_index=_non_negative_integer(
            source.get("test_start_index"), "window.test_start_index"
        ),
        test_stop_index=_non_negative_integer(
            source.get("test_stop_index"), "window.test_stop_index"
        ),
        train_start=_utc(source.get("train_start"), "window.train_start"),
        train_end=_utc(source.get("train_end"), "window.train_end"),
        test_start=_utc(source.get("test_start"), "window.test_start"),
        test_end=_utc(source.get("test_end"), "window.test_end"),
        embargo_periods=_non_negative_integer(
            source.get("embargo_periods"), "window.embargo_periods"
        ),
        embargo_start=_optional_utc(
            source.get("embargo_start"), "window.embargo_start"
        ),
        embargo_end=_optional_utc(source.get("embargo_end"), "window.embargo_end"),
    )


def _validate_schedule(schedule: Sequence[datetime]) -> tuple[datetime, ...]:
    if isinstance(schedule, (str, bytes)) or not isinstance(schedule, Sequence):
        raise TypeError("schedule must be a sequence of UTC datetimes")
    timestamps = tuple(
        require_utc_datetime(value, "schedule entry") for value in schedule
    )
    for previous, current in zip(timestamps, timestamps[1:]):
        if current <= previous:
            raise ValueError("schedule must be in strictly increasing time order")
    return timestamps


def _return_fraction(total_pnl: Decimal, starting_nav: Decimal) -> Decimal:
    if starting_nav <= 0:
        raise ValueError("starting_nav must be positive to express a return")
    return (total_pnl / starting_nav).quantize(
        WALK_FORWARD_RETURN_EXPONENT,
        rounding=ROUND_HALF_EVEN,
    )


def _schedule_digest(timestamps: Any) -> str:
    return _digest([value.isoformat() for value in timestamps])


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{name} must be a mapping")
    return dict(value)


def _record_sequence(value: Any, name: str) -> tuple[Any, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be a sequence")
    return tuple(value)


def _string_mapping(value: Any, name: str) -> dict[str, str]:
    source = _mapping(value, name)
    if any(
        not isinstance(key, str) or not isinstance(item, str)
        for key, item in source.items()
    ):
        raise TypeError(f"{name} keys and values must be strings")
    return source


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    values = _record_sequence(value, name)
    if any(not isinstance(item, str) or not item for item in values):
        raise TypeError(f"{name} must contain non-empty strings")
    return tuple(values)


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must not be empty")
    return value


def _utc(value: Any, name: str) -> datetime:
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError(f"{name} must be an ISO-8601 datetime") from error
    return require_utc_datetime(value, name)


def _optional_utc(value: Any, name: str) -> datetime | None:
    return None if value is None else _utc(value, name)


def _positive_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _non_negative_integer(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")
    return value


def _optional_time(value: datetime | None) -> str | None:
    return value.isoformat() if value is not None else None


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


def _json_copy(value: Any) -> Any:
    return json.loads(
        json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    )


__all__ = [
    "EXPANDING_SCHEME",
    "ROLLING_SCHEME",
    "WALK_FORWARD_CAPITAL_POLICY_VERSION",
    "WALK_FORWARD_FEATURE_ID",
    "WALK_FORWARD_PARAMETER_STATUS",
    "WALK_FORWARD_POLICY_VERSION",
    "WALK_FORWARD_REASON_CODES",
    "WALK_FORWARD_RETURN_EXPONENT",
    "WALK_FORWARD_SCHEMES",
    "WALK_FORWARD_SPLIT_POLICY_VERSION",
    "FoldStrategy",
    "TrainingWindow",
    "WalkForwardFold",
    "WalkForwardPlan",
    "WalkForwardValidation",
    "WalkForwardWindow",
    "restore_walk_forward_plan",
    "restore_walk_forward_validation",
    "run_walk_forward",
    "walk_forward_plan",
    "walk_forward_windows",
]
