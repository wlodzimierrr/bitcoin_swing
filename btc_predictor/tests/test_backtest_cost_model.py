"""BTC-181: realistic backtest cost profiles."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.backtest.costs import (
    BASE_PROFILE,
    COST_PROFILES,
    COST_PROFILE_FEATURE_ID,
    COST_PROFILE_PARAMETER_STATUS,
    COST_PROFILE_POLICY_VERSION,
    COST_PROFILE_REASON_CODES,
    OPTIMISTIC_PROFILE,
    STRESS_PROFILE,
    cost_profile,
    cost_profiles,
    restore_cost_profile,
)
from btc_predictor.backtest.engine import (
    ARM_ENTRY_ACTION,
    BACKTEST_REASON_CODES,
    BacktestContext,
    BacktestIntent,
    restore_backtest_result,
    run_backtest,
)
from btc_predictor.config import StrategyConfigError, load_strategy_config
from btc_predictor.config.strategy import DEFAULT_STRATEGY_CONFIG_PATH
from btc_predictor.data import OhlcvBar
from btc_predictor.portfolio.account import (
    EXECUTION_COST_POLICY_VERSION,
    execution_costs_from_config,
    open_paper_account,
)
from btc_predictor.risk.stop import calculate_initial_stop


UTC = timezone.utc
START = datetime(2024, 1, 1, tzinfo=UTC)
CONFIG = load_strategy_config()
NAV = "1000000"
ZONE_LOWER = Decimal("99000")
ZONE_UPPER = Decimal("101000")
STOP = Decimal("95000")
COMPONENTS = ("fee_bps", "slippage_bps", "funding_cost_bps_per_day")


def bar(day: int, open_: str, high: str, low: str, close: str) -> OhlcvBar:
    timestamp = START + timedelta(days=day)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=Decimal(open_),
        high=Decimal(high),
        low=Decimal(low),
        close=Decimal(close),
        volume=Decimal("100"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(days=1),
    )


RISING = (
    bar(0, "100000", "101000", "99000", "100500"),
    bar(1, "100500", "102000", "99500", "101500"),
    bar(2, "101500", "108000", "101000", "107000"),
    bar(3, "107000", "112000", "106000", "111000"),
    bar(4, "111000", "115000", "110000", "114000"),
)


def enter_on_the_first_bar(context: BacktestContext) -> BacktestIntent | None:
    if context.bar.timestamp != RISING[0].timestamp:
        return None
    return BacktestIntent(
        action=ARM_ENTRY_ACTION,
        entry_zone_lower=ZONE_LOWER,
        entry_zone_upper=ZONE_UPPER,
        initial_stop=calculate_initial_stop(
            invalidation_price=STOP,
            buffer=Decimal("0"),
            direction="long",
            entry_price=ZONE_UPPER,
            config_metadata=CONFIG.run_metadata(),
        ),
        entry_conviction=Decimal("90"),
    )


def run(bars=RISING, **kwargs):
    return run_backtest(
        bars,
        strategy=enter_on_the_first_bar,
        starting_nav=NAV,
        strategy_config=CONFIG,
        strategy_id="btc181-test-strategy",
        **kwargs,
    )


def config_with(*, base=None, **profile_overrides):
    """Return CONFIG with individual cost rungs replaced.

    ``base`` edits the ``[backtest]`` triple the base rung is derived from.
    """

    declared = CONFIG.backtest.cost_profiles
    return replace(
        CONFIG,
        backtest=replace(
            CONFIG.backtest,
            cost_profiles=replace(
                declared,
                **{
                    name: replace(getattr(declared, name), **values)
                    for name, values in profile_overrides.items()
                },
            ),
            **(base or {}),
        ),
    )


def config_file(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "strategy.toml"
    path.write_text(text, encoding="utf-8")
    return path


# --- the ladder -----------------------------------------------------------


def test_metadata_and_profile_vocabulary_are_stable() -> None:
    assert COST_PROFILE_FEATURE_ID == "BACKTEST_COST_PROFILE"
    assert COST_PROFILE_POLICY_VERSION == "REALISTIC_COST_MODEL_V1"
    assert COST_PROFILE_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"
    assert COST_PROFILES == ("optimistic", "base", "stress")
    assert (OPTIMISTIC_PROFILE, BASE_PROFILE, STRESS_PROFILE) == COST_PROFILES


def test_the_ladder_is_returned_cheapest_first() -> None:
    assert tuple(rung.profile for rung in cost_profiles(CONFIG)) == COST_PROFILES


def test_the_base_rung_is_the_shared_configured_assumption() -> None:
    base = cost_profile(BASE_PROFILE, config=CONFIG)

    # Not a copy of the configured numbers: the same object value advisory and
    # paper trading price against, so the two cannot silently diverge.
    assert base.costs == execution_costs_from_config(CONFIG)
    assert "COST_PROFILE_SHARED_CONFIG_COSTS" in base.reason_codes


def test_only_the_base_rung_claims_the_shared_assumption() -> None:
    for rung in cost_profiles(CONFIG):
        shared = "COST_PROFILE_SHARED_CONFIG_COSTS" in rung.reason_codes
        assert shared is (rung.profile == BASE_PROFILE)


def test_a_more_pessimistic_rung_is_never_cheaper() -> None:
    ladder = cost_profiles(CONFIG)

    for cheaper, dearer in zip(ladder, ladder[1:]):
        for component in COMPONENTS:
            assert getattr(dearer.costs, component) >= getattr(
                cheaper.costs, component
            )
        assert dearer.round_trip_cost("100000") >= cheaper.round_trip_cost("100000")


def test_the_configured_ladder_actually_spans_a_range() -> None:
    optimistic, _, stress = cost_profiles(CONFIG)

    assert stress.round_trip_cost("100000") > optimistic.round_trip_cost("100000")


def test_every_rung_prices_costs_the_execution_owners_accept() -> None:
    # BTC-162/163 reject any ExecutionCosts that is not the shared policy.
    for rung in cost_profiles(CONFIG):
        assert rung.costs.policy_version == EXECUTION_COST_POLICY_VERSION


def test_round_trip_cost_delegates_to_the_shared_owner() -> None:
    for rung in cost_profiles(CONFIG):
        assert rung.round_trip_cost("250000") == rung.costs.round_trip_cost("250000")


def test_a_rung_that_prices_no_carry_says_so() -> None:
    for rung in cost_profiles(CONFIG):
        unpriced = "COST_PROFILE_FUNDING_UNPRICED" in rung.reason_codes
        assert unpriced is (rung.costs.funding_cost_bps_per_day == 0)


def test_every_reason_code_is_declared() -> None:
    for rung in cost_profiles(CONFIG):
        for code in rung.reason_codes:
            assert code in COST_PROFILE_REASON_CODES


def test_the_profile_carries_the_config_identity() -> None:
    assert cost_profile(STRESS_PROFILE, config=CONFIG).config_metadata == (
        CONFIG.run_metadata()
    )


# --- ladders that must fail closed ---------------------------------------


@pytest.mark.parametrize("component", COMPONENTS)
def test_an_optimistic_rung_dearer_than_base_is_rejected(component: str) -> None:
    crossed = config_with(optimistic={component: 999.0})

    with pytest.raises(ValueError, match=f"must not price {component} below"):
        cost_profiles(crossed)


@pytest.mark.parametrize("component", COMPONENTS)
def test_a_stress_rung_cheaper_than_base_is_rejected(component: str) -> None:
    # The base rung is lifted so every component is a real crossing: base
    # prices no carry today, and a tie is not what this rejects.
    crossed = config_with(
        base={component: 5.0},
        optimistic={component: 0.0},
        stress={component: 0.0},
    )

    with pytest.raises(ValueError, match=f"must not price {component} below"):
        cost_profiles(crossed)


def test_an_unknown_profile_name_is_rejected() -> None:
    with pytest.raises(ValueError, match="profile must be one of"):
        cost_profile("pessimistic", config=CONFIG)


def test_a_non_config_object_is_rejected() -> None:
    with pytest.raises(TypeError, match="StrategyConfig"):
        cost_profiles({"backtest": {}})


# --- persistence ----------------------------------------------------------


def test_profile_records_round_trip() -> None:
    for rung in cost_profiles(CONFIG):
        assert restore_cost_profile(rung.as_record()) == rung


def test_a_record_states_the_priced_round_trip_cost() -> None:
    stress = cost_profile(STRESS_PROFILE, config=CONFIG)

    assert stress.as_record()["round_trip_cost_fraction"] == str(
        stress.round_trip_cost(Decimal("1"))
    )


def test_tampered_profile_costs_are_rejected() -> None:
    record = cost_profile(STRESS_PROFILE, config=CONFIG).as_record()
    record["costs"]["fee_bps"] = "1"

    with pytest.raises(ValueError, match="does not match reconstructed"):
        restore_cost_profile(record)


def test_an_undeclared_profile_reason_code_is_rejected() -> None:
    stress = cost_profile(STRESS_PROFILE, config=CONFIG)

    with pytest.raises(ValueError, match="undeclared cost profile reason code"):
        replace(stress, reason_codes=("COST_PROFILE_INVENTED",)).as_record()


# --- configuration --------------------------------------------------------


def test_configuration_rejects_a_redeclared_base_rung(tmp_path: Path) -> None:
    text = DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8")
    path = config_file(
        tmp_path,
        f"{text}\n[backtest.cost_profiles.base]\nfee_bps = 1\n"
        "slippage_bps = 1\nfunding_cost_bps_per_day = 1\n",
    )

    with pytest.raises(StrategyConfigError, match="accepts only"):
        load_strategy_config(path)


def test_configuration_rejects_a_negative_rung(tmp_path: Path) -> None:
    text = DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8").replace(
        "[backtest.cost_profiles.optimistic]\nfee_bps = 5",
        "[backtest.cost_profiles.optimistic]\nfee_bps = -5",
    )

    with pytest.raises(StrategyConfigError, match="optimistic: fee_bps"):
        load_strategy_config(config_file(tmp_path, text))


def test_configuration_requires_the_cost_ladder(tmp_path: Path) -> None:
    text = DEFAULT_STRATEGY_CONFIG_PATH.read_text(encoding="utf-8")
    trimmed = text.split("[backtest.cost_profiles.optimistic]")[0]

    with pytest.raises(StrategyConfigError, match="cost_profiles must be a table"):
        load_strategy_config(config_file(tmp_path, trimmed))


# --- engine integration ---------------------------------------------------


def test_a_named_profile_prices_the_whole_run() -> None:
    stress = cost_profile(STRESS_PROFILE, config=CONFIG)

    result = run(cost_profile=STRESS_PROFILE)

    assert result.cost_profile == stress
    assert result.effective_costs == stress.costs
    # The account prices its own fees, so it must execute under the same rung.
    assert result.account.costs == stress.costs
    assert "BACKTEST_COST_PROFILE_APPLIED" in result.reason_codes
    assert "BACKTEST_COST_PROFILE_APPLIED" in BACKTEST_REASON_CODES


def test_an_unprofiled_run_records_no_profile() -> None:
    result = run()

    assert result.cost_profile is None
    assert "BACKTEST_COST_PROFILE_APPLIED" not in result.reason_codes
    assert result.effective_costs == execution_costs_from_config(CONFIG)


def test_the_base_profile_reproduces_an_unprofiled_run() -> None:
    unprofiled = run()
    based = run(cost_profile=BASE_PROFILE)

    assert based.effective_costs == unprofiled.effective_costs
    assert based.ending_nav == unprofiled.ending_nav
    assert [point.as_record() for point in based.equity_curve] == [
        point.as_record() for point in unprofiled.equity_curve
    ]
    # Same economics, different declared run: selecting a rung is a run input.
    assert based.run_id != unprofiled.run_id


def test_a_more_expensive_rung_never_ends_richer() -> None:
    results = [run(cost_profile=name) for name in COST_PROFILES]

    for cheaper, dearer in zip(results, results[1:]):
        assert dearer.ending_nav <= cheaper.ending_nav
        assert dearer.account.fees_paid >= cheaper.account.fees_paid
        assert dearer.account.funding_paid >= cheaper.account.funding_paid


def test_the_stress_rung_charges_fees_slippage_and_carry() -> None:
    optimistic = run(cost_profile=OPTIMISTIC_PROFILE)
    stress = run(cost_profile=STRESS_PROFILE)

    assert stress.account.fees_paid > optimistic.account.fees_paid
    assert stress.account.funding_paid > optimistic.account.funding_paid
    # A buy slips adversely, so the same intent fills higher under stress.
    assert stress.trades[0].fills[0].price > optimistic.trades[0].fills[0].price
    assert stress.ending_nav < optimistic.ending_nav


def test_costs_and_a_profile_cannot_both_be_supplied() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        run(
            cost_profile=BASE_PROFILE,
            costs=execution_costs_from_config(CONFIG),
        )


def test_an_account_priced_off_the_profile_is_rejected() -> None:
    account = open_paper_account(
        account_name="backtest-BTC-USD",
        created_at=RISING[0].timestamp,
        starting_nav=NAV,
        costs=cost_profile(OPTIMISTIC_PROFILE, config=CONFIG).costs,
        config=CONFIG,
    )

    with pytest.raises(ValueError, match="execution costs must be identical"):
        run_backtest(
            RISING,
            strategy=enter_on_the_first_bar,
            strategy_config=CONFIG,
            strategy_id="btc181-test-strategy",
            cost_profile=STRESS_PROFILE,
            account=account,
        )


def test_an_unknown_engine_profile_is_rejected() -> None:
    with pytest.raises(ValueError, match="cost_profile must be one of"):
        run(cost_profile="cheap")


def test_a_run_without_bars_still_records_its_profile() -> None:
    unprofiled = run(bars=())
    profiled = run(bars=(), cost_profile=STRESS_PROFILE)

    assert unprofiled.cost_profile is None
    assert unprofiled.reason_codes == ("BACKTEST_NO_BARS",)
    assert profiled.cost_profile == cost_profile(STRESS_PROFILE, config=CONFIG)
    assert profiled.reason_codes == (
        "BACKTEST_COST_PROFILE_APPLIED",
        "BACKTEST_NO_BARS",
    )
    assert restore_backtest_result(profiled.as_record()) == profiled


def test_a_profiled_result_persists_and_restores() -> None:
    result = run(cost_profile=STRESS_PROFILE)
    record = result.as_record()

    assert record["cost_profile"]["profile"] == "stress"
    assert record["cost_profile"]["policy_version"] == COST_PROFILE_POLICY_VERSION
    assert record["effective_costs"] == record["cost_profile"]["costs"]
    assert restore_backtest_result(record) == result


def test_an_unprofiled_result_persists_and_restores() -> None:
    result = run()
    record = result.as_record()

    assert record["cost_profile"] is None
    assert restore_backtest_result(record) == result


def test_a_swapped_profile_name_is_rejected() -> None:
    record = run(cost_profile=STRESS_PROFILE).as_record()
    record["cost_profile"]["profile"] = OPTIMISTIC_PROFILE

    # The rung is part of run identity, so relabelling it cannot pass replay.
    with pytest.raises(ValueError, match="run inputs do not match run_id"):
        restore_backtest_result(record)


def test_replaying_a_profiled_run_is_deterministic() -> None:
    first = run(cost_profile=STRESS_PROFILE)
    second = run(cost_profile=STRESS_PROFILE)

    assert first.as_record() == second.as_record()


def test_different_rungs_are_different_runs() -> None:
    run_ids = {run(cost_profile=name).run_id for name in COST_PROFILES}

    assert len(run_ids) == len(COST_PROFILES)
