"""BTC-182: walk-forward validation."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.backtest.costs import STRESS_PROFILE, cost_profile
from btc_predictor.backtest.engine import (
    ARM_ENTRY_ACTION,
    BacktestContext,
    BacktestIntent,
)
from btc_predictor.backtest.walk_forward import (
    EXPANDING_SCHEME,
    ROLLING_SCHEME,
    WALK_FORWARD_CAPITAL_POLICY_VERSION,
    WALK_FORWARD_FEATURE_ID,
    WALK_FORWARD_PARAMETER_STATUS,
    WALK_FORWARD_POLICY_VERSION,
    WALK_FORWARD_REASON_CODES,
    WALK_FORWARD_SCHEMES,
    WALK_FORWARD_SPLIT_POLICY_VERSION,
    FoldStrategy,
    TrainingWindow,
    WalkForwardPlan,
    restore_walk_forward_plan,
    restore_walk_forward_validation,
    run_walk_forward,
    walk_forward_plan,
    walk_forward_windows,
)
from btc_predictor.config import StrategyConfigError, load_strategy_config
from btc_predictor.config.strategy import (
    DEFAULT_STRATEGY_CONFIG_PATH,
    WALK_FORWARD_SCHEME_KEYS,
)
from btc_predictor.data import OhlcvBar
from btc_predictor.risk.stop import calculate_initial_stop


UTC = timezone.utc
START = datetime(2024, 1, 1, tzinfo=UTC)
CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
NAV = "1000000"
STRATEGY_ID = "btc182-fixed-rule"


def bar(day: int) -> OhlcvBar:
    """One rising daily bar; the exact path only has to be replayable."""

    timestamp = START + timedelta(days=day)
    base = 100000 + day * 500
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=Decimal(str(base)),
        high=Decimal(str(base + 1500)),
        low=Decimal(str(base - 1000)),
        close=Decimal(str(base + 500)),
        volume=Decimal("100"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(days=1),
    )


BARS = tuple(bar(day) for day in range(12))
SCHEDULE = tuple(item.timestamp for item in BARS)


def plan(**overrides) -> WalkForwardPlan:
    """A small split: three train periods, two tested, stepped by two."""

    values = {"train_periods": 3, "test_periods": 2, "step_periods": 2, **overrides}
    return walk_forward_plan(CONFIG, **values)


def enter_immediately(context: BacktestContext) -> BacktestIntent | None:
    """Arm one entry on the first bar of whatever window it is given."""

    if context.bar.timestamp != context.bars[0].timestamp:
        return None
    close = context.bar.close
    return BacktestIntent(
        action=ARM_ENTRY_ACTION,
        entry_zone_lower=close * Decimal("0.97"),
        entry_zone_upper=close * Decimal("1.03"),
        initial_stop=calculate_initial_stop(
            invalidation_price=close * Decimal("0.9"),
            buffer=Decimal("0"),
            direction="long",
            entry_price=close,
            config_metadata=METADATA,
        ),
        entry_conviction=Decimal("90"),
    )


def stand_aside(context: BacktestContext) -> BacktestIntent | None:
    return None


def fixed_rule(window: TrainingWindow) -> FoldStrategy:
    return FoldStrategy(strategy=enter_immediately, strategy_id=STRATEGY_ID)


def run(bars=BARS, *, strategy_factory=fixed_rule, **kwargs):
    values = {
        "plan": plan(),
        "starting_nav": NAV,
        "strategy_config": CONFIG,
        **kwargs,
    }
    return run_walk_forward(bars, strategy_factory=strategy_factory, **values)


def config_file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "strategy.toml"
    path.write_text(text, encoding="utf-8")
    return path


# --- the split contract ---------------------------------------------------


def test_metadata_and_scheme_vocabulary_are_stable() -> None:
    assert WALK_FORWARD_FEATURE_ID == "WALK_FORWARD_VALIDATION"
    assert WALK_FORWARD_POLICY_VERSION == "WALK_FORWARD_VALIDATION_V1"
    assert WALK_FORWARD_SPLIT_POLICY_VERSION == "TRAIN_STRICTLY_BEFORE_TEST_V1"
    assert WALK_FORWARD_CAPITAL_POLICY_VERSION == "INDEPENDENT_FOLD_CAPITAL_V1"
    assert WALK_FORWARD_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"
    assert WALK_FORWARD_SCHEMES == (ROLLING_SCHEME, EXPANDING_SCHEME)
    # Configuration parses the same vocabulary the owner module validates.
    assert set(WALK_FORWARD_SCHEME_KEYS) == set(WALK_FORWARD_SCHEMES)


def test_the_configured_split_is_the_default_plan() -> None:
    declared = CONFIG.backtest.walk_forward
    resolved = walk_forward_plan(CONFIG)

    assert resolved.scheme == declared.scheme
    assert resolved.train_periods == declared.train_periods
    assert resolved.test_periods == declared.test_periods
    assert resolved.step_periods == declared.step_periods
    assert resolved.embargo_periods == declared.embargo_periods
    assert resolved.config_metadata == METADATA


def test_research_overrides_replace_only_what_they_name() -> None:
    resolved = plan(scheme=ROLLING_SCHEME, embargo_periods=1)

    assert resolved.scheme == ROLLING_SCHEME
    assert (resolved.train_periods, resolved.test_periods) == (3, 2)
    assert resolved.embargo_periods == 1


def test_overlapping_out_of_sample_windows_are_rejected() -> None:
    # Pooling overlapping windows counts the same market twice, which flatters
    # every aggregate computed from the folds.
    with pytest.raises(ValueError, match="never overlap"):
        plan(step_periods=1)


@pytest.mark.parametrize(
    ("override", "message"),
    [
        ({"scheme": "sliding"}, "scheme must be one of"),
        ({"train_periods": 0}, "train_periods must be a positive integer"),
        ({"test_periods": 0}, "test_periods must be a positive integer"),
        ({"step_periods": 0}, "step_periods must be a positive integer"),
        ({"embargo_periods": -1}, "embargo_periods must be a non-negative integer"),
    ],
)
def test_an_unusable_split_is_rejected(override: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        plan(**override)


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({}, "WALK_FORWARD_EXPANDING_WINDOWS"),
        ({"scheme": ROLLING_SCHEME}, "WALK_FORWARD_ROLLING_WINDOWS"),
        ({"embargo_periods": 0}, "WALK_FORWARD_NO_EMBARGO"),
        ({"embargo_periods": 2}, "WALK_FORWARD_EMBARGO_APPLIED"),
        ({"step_periods": 2}, "WALK_FORWARD_OUT_OF_SAMPLE_CONTIGUOUS"),
        ({"step_periods": 3}, "WALK_FORWARD_OUT_OF_SAMPLE_GAPS"),
    ],
)
def test_a_plan_states_what_it_does(override: dict, expected: str) -> None:
    assert expected in plan(**override).reason_codes
    assert expected in WALK_FORWARD_REASON_CODES


def test_fold_arithmetic_matches_the_windows_produced() -> None:
    resolved = plan()

    assert resolved.minimum_periods == 5
    assert resolved.fold_count(4) == 0
    assert resolved.fold_count(5) == 1
    assert resolved.fold_count(6) == 1
    assert resolved.fold_count(len(SCHEDULE)) == len(
        walk_forward_windows(SCHEDULE, plan=resolved)
    )


# --- windows --------------------------------------------------------------


def test_expanding_windows_keep_every_earlier_period() -> None:
    windows = walk_forward_windows(SCHEDULE, plan=plan(scheme=EXPANDING_SCHEME))

    assert [window.train_start_index for window in windows] == [0, 0, 0, 0]
    assert [window.train_periods for window in windows] == [3, 5, 7, 9]
    assert all(window.train_start == SCHEDULE[0] for window in windows)


def test_rolling_windows_slide_a_fixed_history() -> None:
    windows = walk_forward_windows(SCHEDULE, plan=plan(scheme=ROLLING_SCHEME))

    assert [window.train_start_index for window in windows] == [0, 2, 4, 6]
    assert {window.train_periods for window in windows} == {3}


def test_in_sample_data_ends_strictly_before_out_of_sample_data() -> None:
    for window in walk_forward_windows(SCHEDULE, plan=plan()):
        assert window.train_stop_index <= window.test_start_index
        assert window.train_end < window.test_start


def test_tested_windows_are_contiguous_and_never_repeat_a_period() -> None:
    windows = walk_forward_windows(SCHEDULE, plan=plan())
    tested = [
        index
        for window in windows
        for index in range(window.test_start_index, window.test_stop_index)
    ]

    assert tested == sorted(tested)
    assert len(tested) == len(set(tested))
    assert {window.test_periods for window in windows} == {2}


def test_an_embargo_removes_the_periods_between_train_and_test() -> None:
    embargoed = plan(embargo_periods=1)

    windows = walk_forward_windows(SCHEDULE, plan=embargoed)

    first = windows[0]
    assert first.train_stop_index == 3
    assert first.test_start_index == 4
    assert first.embargo_start == SCHEDULE[3] == first.embargo_end
    assert first.train_end < first.embargo_start < first.test_start
    # Every tested window moves one period later, and the embargoed period is
    # in neither side of the split.
    for embargoed_window, plain in zip(windows, walk_forward_windows(SCHEDULE, plan=plan())):
        assert embargoed_window.test_start_index == plain.test_start_index + 1
        assert embargoed_window.train_stop_index == plain.train_stop_index
        assert (
            embargoed_window.train_stop_index
            < embargoed_window.test_start_index
            == embargoed_window.train_stop_index + 1
        )


def test_a_short_tail_is_left_untested_rather_than_tested_short() -> None:
    windows = walk_forward_windows(SCHEDULE, plan=plan())

    # Twelve periods, folds tested through index 11 exclusive of nothing left
    # over would need an exact fit; the remainder is simply not folded.
    assert windows[-1].test_stop_index == 11
    assert windows[-1].test_periods == 2


def test_a_schedule_too_short_for_one_fold_is_rejected() -> None:
    with pytest.raises(ValueError, match="needs at least 5 scheduled periods"):
        walk_forward_windows(SCHEDULE[:4], plan=plan())


def test_a_schedule_must_be_ordered_utc_decision_times() -> None:
    with pytest.raises(ValueError, match="strictly increasing"):
        walk_forward_windows(tuple(reversed(SCHEDULE)), plan=plan())
    with pytest.raises(ValueError):
        walk_forward_windows(
            tuple(item.replace(tzinfo=None) for item in SCHEDULE),
            plan=plan(),
        )


def test_any_point_in_time_schedule_folds_the_same_way() -> None:
    # BTC-048 research rows fold exactly like bars: the splitter only sees an
    # ordered UTC schedule.
    decisions = tuple(START + timedelta(days=day) for day in range(12))

    assert walk_forward_windows(decisions, plan=plan()) == walk_forward_windows(
        SCHEDULE,
        plan=plan(),
    )


def test_plan_records_round_trip() -> None:
    resolved = plan(embargo_periods=1)

    assert restore_walk_forward_plan(resolved.as_record()) == resolved


def test_a_tampered_plan_is_rejected() -> None:
    record = plan().as_record()
    record["train_periods"] = 4

    # minimum_periods is derived, so a rewritten window length no longer
    # describes any plan this owner would produce.
    with pytest.raises(ValueError, match="does not match reconstructed"):
        restore_walk_forward_plan(record)


def test_a_relabelled_plan_scheme_is_rejected() -> None:
    record = plan(scheme=EXPANDING_SCHEME).as_record()
    record["scheme"] = ROLLING_SCHEME

    with pytest.raises(ValueError, match="reason codes do not describe the plan"):
        restore_walk_forward_plan(record)


# --- the leakage barrier --------------------------------------------------


def test_a_factory_sees_in_sample_bars_and_nothing_else() -> None:
    seen: list[TrainingWindow] = []

    def recording_factory(window: TrainingWindow) -> FoldStrategy:
        seen.append(window)
        return FoldStrategy(strategy=enter_immediately, strategy_id=STRATEGY_ID)

    validation = run(strategy_factory=recording_factory)

    assert len(seen) == validation.fold_count
    for training, fold in zip(seen, validation.folds):
        assert training.bars == BARS[
            fold.window.train_start_index : fold.window.train_stop_index
        ]
        assert max(item.timestamp for item in training.bars) < fold.window.test_start


def test_a_fold_strategy_is_replayed_over_its_tested_window_only() -> None:
    seen: dict[int, list[datetime]] = {}

    def recording_factory(window: TrainingWindow) -> FoldStrategy:
        fold_number = window.window.fold_number
        seen[fold_number] = []

        def strategy(context: BacktestContext) -> BacktestIntent | None:
            seen[fold_number].append(context.bar.timestamp)
            return enter_immediately(context)

        return FoldStrategy(strategy=strategy, strategy_id=STRATEGY_ID)

    validation = run(strategy_factory=recording_factory)

    for fold in validation.folds:
        window = fold.window
        tested = BARS[window.test_start_index : window.test_stop_index]
        # The engine received the out-of-sample window and nothing else, which
        # is the whole split restated as persisted evidence.
        assert fold.result.input_bars == tested
        assert fold.result.started_at == window.test_start
        assert fold.result.ended_at == window.test_end
        assert fold.result.bar_count == window.test_periods
        assert seen[fold.fold_number] == [item.timestamp for item in tested]


def test_every_fold_starts_from_the_same_capital() -> None:
    validation = run()

    assert {fold.starting_nav for fold in validation.folds} == {Decimal(NAV)}
    assert validation.starting_nav == Decimal(NAV)
    # A fold that made money does not hand its winnings to the next one.
    assert validation.folds[0].ending_nav != Decimal(NAV)
    assert validation.capital_policy_version == WALK_FORWARD_CAPITAL_POLICY_VERSION
    assert "WALK_FORWARD_INDEPENDENT_FOLD_CAPITAL" in validation.reason_codes


def test_folds_cover_the_schedule_without_double_counting() -> None:
    validation = run()

    tested = [
        index
        for fold in validation.folds
        for index in range(fold.window.test_start_index, fold.window.test_stop_index)
    ]
    assert len(tested) == len(set(tested)) == validation.tested_periods
    assert validation.scheduled_periods == len(BARS)
    assert validation.untested_leading_periods == 3
    assert validation.untested_gap_periods == 0
    assert validation.untested_trailing_periods == 1
    assert "WALK_FORWARD_TRAILING_PERIODS_UNTESTED" in validation.reason_codes


def test_a_stepped_split_reports_the_history_it_stepped_over() -> None:
    validation = run(plan=plan(step_periods=3))

    # Stepping further than the tested window leaves history neither trained
    # on nor tested, and a coverage claim has to admit that.
    assert "WALK_FORWARD_OUT_OF_SAMPLE_GAPS" in validation.plan.reason_codes
    assert validation.untested_gap_periods == validation.fold_count - 1
    assert (
        validation.untested_leading_periods
        + validation.tested_periods
        + validation.untested_gap_periods
        + validation.untested_trailing_periods
        == validation.scheduled_periods
    )


# --- fold and validation evidence -----------------------------------------


def test_a_constant_rule_is_reported_as_constant() -> None:
    validation = run()

    assert "WALK_FORWARD_STRATEGY_CONSTANT" in validation.reason_codes
    assert {fold.strategy_id for fold in validation.folds} == {STRATEGY_ID}
    assert all(fold.calibration is None for fold in validation.folds)
    assert all(
        "WALK_FORWARD_FOLD_UNCALIBRATED" in fold.reason_codes
        for fold in validation.folds
    )


def test_a_fold_that_fitted_its_window_says_what_it_fitted() -> None:
    def calibrating_factory(window: TrainingWindow) -> FoldStrategy:
        return FoldStrategy(
            strategy=enter_immediately,
            strategy_id=f"fitted-{window.window.fold_number}",
            calibration={
                "entry_conviction_min": "90",
                "fitted_through": window.window.train_end.isoformat(),
            },
        )

    validation = run(strategy_factory=calibrating_factory)

    assert "WALK_FORWARD_STRATEGY_RECALIBRATED" in validation.reason_codes
    for fold in validation.folds:
        assert fold.calibration["fitted_through"] == fold.window.train_end.isoformat()
        assert "WALK_FORWARD_FOLD_CALIBRATED" in fold.reason_codes
        assert fold.result.strategy_id == fold.strategy_id


def test_one_identity_cannot_describe_two_calibrations() -> None:
    def inconsistent_factory(window: TrainingWindow) -> FoldStrategy:
        return FoldStrategy(
            strategy=enter_immediately,
            strategy_id="ambiguous",
            calibration={"fold": str(window.window.fold_number)},
        )

    with pytest.raises(ValueError, match="two different calibrations"):
        run(strategy_factory=inconsistent_factory)


def test_a_validation_that_never_traded_says_so() -> None:
    validation = run(
        strategy_factory=lambda window: FoldStrategy(
            strategy=stand_aside,
            strategy_id="stand-aside",
        )
    )

    # No trade anywhere is not a passed validation; it is no evidence at all.
    assert "WALK_FORWARD_NO_TRADES" in validation.reason_codes
    assert validation.trade_count == 0
    assert all(
        "WALK_FORWARD_FOLD_NO_TRADES" in fold.reason_codes
        for fold in validation.folds
    )
    assert all(fold.total_pnl == 0 for fold in validation.folds)


def test_a_fold_holding_at_its_end_is_marked_not_liquidated() -> None:
    validation = run()

    for fold in validation.folds:
        assert fold.position_open_at_end
        assert "WALK_FORWARD_FOLD_POSITION_OPEN_AT_END" in fold.reason_codes
        # BTC-180 marks the open position rather than forcing an exit, so the
        # fold's marked NAV rose on paper while the only realized economics
        # were the costs of getting in.
        assert fold.closed_trade_count == 0
        assert fold.net_pnl < 0 < fold.total_pnl


def test_aggregates_are_recomputed_from_the_folds() -> None:
    validation = run()
    returns = [fold.return_fraction for fold in validation.folds]

    assert validation.fold_count == len(validation.folds)
    assert validation.profitable_folds == sum(
        1 for fold in validation.folds if fold.total_pnl > 0
    )
    assert validation.losing_folds == sum(
        1 for fold in validation.folds if fold.total_pnl < 0
    )
    assert validation.summed_net_pnl == sum(
        (fold.net_pnl for fold in validation.folds),
        Decimal("0"),
    )
    assert validation.best_fold.return_fraction == max(returns)
    assert validation.worst_fold.return_fraction == min(returns)
    assert validation.mean_return_fraction == (
        sum(returns, Decimal("0")) / len(returns)
    ).quantize(Decimal("1E-12"))


def test_a_fold_return_is_stated_against_its_own_starting_capital() -> None:
    fold = run().folds[0]

    assert fold.return_fraction == (fold.total_pnl / fold.starting_nav).quantize(
        Decimal("1E-12")
    )
    assert fold.total_pnl == fold.ending_nav - fold.starting_nav


def test_every_reason_code_is_declared() -> None:
    validation = run()

    for code in validation.reason_codes + validation.plan.reason_codes:
        assert code in WALK_FORWARD_REASON_CODES
    for fold in validation.folds:
        for code in fold.reason_codes:
            assert code in WALK_FORWARD_REASON_CODES


# --- run inputs -----------------------------------------------------------


def test_a_named_cost_rung_prices_every_fold() -> None:
    stress = cost_profile(STRESS_PROFILE, config=CONFIG)

    validation = run(cost_profile=STRESS_PROFILE)

    assert validation.cost_profile == stress
    assert validation.effective_costs == stress.costs
    assert all(fold.result.cost_profile == stress for fold in validation.folds)
    assert "WALK_FORWARD_COST_PROFILE_APPLIED" in validation.reason_codes


def test_an_unpriced_run_claims_no_rung() -> None:
    validation = run()

    assert validation.cost_profile is None
    assert "WALK_FORWARD_COST_PROFILE_APPLIED" not in validation.reason_codes


def test_a_plan_from_another_configuration_is_rejected() -> None:
    foreign = replace(plan(), config_metadata={"config_version": "other"})

    with pytest.raises(ValueError, match="plan config_metadata must match"):
        run(plan=foreign)


def test_the_engine_bar_contract_still_applies() -> None:
    with pytest.raises(ValueError, match="every bar must belong to the backtest symbol"):
        run(symbol="ETH-USD")


def test_a_factory_must_return_a_fold_strategy() -> None:
    with pytest.raises(TypeError, match="must return a FoldStrategy"):
        run(strategy_factory=lambda window: enter_immediately)


@pytest.mark.parametrize(
    ("kwargs", "error", "message"),
    [
        ({"strategy_id": ""}, ValueError, "strategy_id must not be empty"),
        ({"calibration": {}}, ValueError, "calibration must not be empty"),
        ({"calibration": "fitted"}, TypeError, "calibration must be a mapping"),
    ],
)
def test_a_fold_strategy_declares_a_usable_identity(kwargs, error, message) -> None:
    values = {"strategy": enter_immediately, "strategy_id": STRATEGY_ID, **kwargs}

    with pytest.raises(error, match=message):
        FoldStrategy(**values)


# --- determinism and persistence ------------------------------------------


def test_replaying_a_validation_is_deterministic() -> None:
    assert run().as_record() == run().as_record()


def test_a_different_split_is_a_different_validation() -> None:
    first = run()
    second = run(plan=plan(scheme=ROLLING_SCHEME))

    assert first.validation_id != second.validation_id


def test_validation_records_round_trip() -> None:
    validation = run(cost_profile=STRESS_PROFILE)
    record = validation.as_record()

    assert record["plan"]["scheme"] == EXPANDING_SCHEME
    assert record["fold_count"] == len(record["folds"])
    assert record["folds"][0]["result"]["bar_count"] == 2
    assert restore_walk_forward_validation(record) == validation


def test_a_tampered_fold_result_is_rejected() -> None:
    record = run().as_record()
    record["folds"][0]["result"]["ending_nav"] = "999999999"

    with pytest.raises(ValueError, match="does not match"):
        restore_walk_forward_validation(record)


def test_a_tampered_fold_summary_is_rejected() -> None:
    record = run().as_record()
    record["folds"][0]["return_fraction"] = "9.999999999999"

    # Summaries are recomputed from the engine evidence on restore, so an
    # edited headline number cannot survive replay.
    with pytest.raises(ValueError, match="does not match reconstructed"):
        restore_walk_forward_validation(record)


def test_a_tampered_coverage_count_is_rejected() -> None:
    record = run().as_record()
    record["tested_periods"] = 99

    with pytest.raises(ValueError, match="tested periods must equal"):
        restore_walk_forward_validation(record)


def test_a_reordered_fold_is_rejected() -> None:
    record = run().as_record()
    record["folds"] = list(reversed(record["folds"]))

    with pytest.raises(ValueError, match="fold numbers must be contiguous"):
        restore_walk_forward_validation(record)


def test_a_moved_window_boundary_is_rejected() -> None:
    record = run().as_record()
    record["folds"][0]["window"]["test_start_index"] = 4
    record["folds"][0]["window"]["test_stop_index"] = 6

    # Window bounds are a pure function of the plan, so a window cannot be
    # quietly slid onto a friendlier stretch of history.
    with pytest.raises(ValueError, match="window indices do not match the plan"):
        restore_walk_forward_validation(record)


def test_a_window_that_swallows_its_embargo_is_rejected() -> None:
    window = walk_forward_windows(SCHEDULE, plan=plan(embargo_periods=1))[0]

    swallowed = replace(
        window,
        test_start_index=window.test_start_index - 1,
        test_stop_index=window.test_stop_index - 1,
        test_start=SCHEDULE[window.test_start_index - 1],
        test_end=SCHEDULE[window.test_stop_index - 2],
    )

    with pytest.raises(ValueError, match="out-of-sample window must begin after"):
        swallowed.as_record()


def test_a_relabelled_validation_identity_is_rejected() -> None:
    record = run().as_record()
    record["validation_id"] = "0" * 64

    with pytest.raises(ValueError, match="do not match validation_id"):
        restore_walk_forward_validation(record)


def test_an_edited_untested_tail_is_rejected() -> None:
    record = run().as_record()
    record["untested_trailing_periods"] = 0

    # Dropping the tail alone leaves a scheduled period nothing accounts for.
    with pytest.raises(ValueError, match="must account for every untested period"):
        restore_walk_forward_validation(record)

    record["scheduled_periods"] = 11

    # Shrinking the dataset to match still claims a coverage the run's own
    # reason codes contradict.
    with pytest.raises(ValueError, match="reason codes do not describe"):
        restore_walk_forward_validation(record)


def test_a_dropped_fold_is_rejected() -> None:
    record = run().as_record()
    record["folds"] = record["folds"][:3]
    record["fold_count"] = 3
    record["tested_periods"] = 6

    # Deleting the fold that went badly cannot pass as a shorter validation.
    with pytest.raises(ValueError, match="must account for every untested period"):
        restore_walk_forward_validation(record)


def test_a_swapped_schedule_digest_is_rejected() -> None:
    record = run().as_record()
    record["schedule_digest"] = "0" * 64

    # The digest is part of run identity: the folds no longer claim to come
    # from the dataset the record names.
    with pytest.raises(ValueError, match="do not match validation_id"):
        restore_walk_forward_validation(record)


# --- configuration --------------------------------------------------------


def test_configuration_requires_the_walk_forward_split(tmp_path: Path) -> None:
    text = DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8")
    trimmed = text.split("[backtest.walk_forward]")[0]

    with pytest.raises(StrategyConfigError, match="walk_forward must be a table"):
        load_strategy_config(config_file(tmp_path, trimmed))


def test_configuration_rejects_an_unknown_scheme(tmp_path: Path) -> None:
    text = DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
        'scheme = "expanding"',
        'scheme = "sliding"',
    )

    with pytest.raises(StrategyConfigError, match="walk_forward: scheme must be one of"):
        load_strategy_config(config_file(tmp_path, text))


def test_configuration_rejects_a_negative_embargo(tmp_path: Path) -> None:
    text = DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
        "embargo_periods = 0",
        "embargo_periods = -1",
    )

    with pytest.raises(StrategyConfigError, match="embargo_periods must be a non-negative"):
        load_strategy_config(config_file(tmp_path, text))
