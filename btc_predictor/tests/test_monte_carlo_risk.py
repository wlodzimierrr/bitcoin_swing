"""BTC-187: Monte Carlo portfolio risk analysis over resampled trade outcomes."""

import decimal
import sys
from datetime import UTC, datetime
from decimal import Context, Decimal, localcontext
from pathlib import Path

import pytest

from btc_predictor.portfolio.accounting import (
    PAPER_TRADE_ACCOUNTING_POLICY_VERSION,
    R_MULTIPLE_CONVENTION,
)
from btc_predictor.quant.simulation import (
    PERMUTATION_INDEX_POLICY_VERSION,
    UNIFORM_INDEX_POLICY_VERSION,
)
from btc_predictor.research import (
    CALMAR_METRIC,
    CALMAR_UNDEFINED_NO_DRAWDOWN,
    DEFAULT_DRAWDOWN_THRESHOLDS,
    DEFAULT_PERCENTILES,
    ENDING_NAV_FRACTION_METRIC,
    ENDING_NAV_METRIC,
    IID_BOOTSTRAP,
    LONGEST_LOSING_STREAK_METRIC,
    MAX_DRAWDOWN_METRIC,
    MONTE_CARLO_CALMAR_POLICY_VERSION,
    MONTE_CARLO_COMMON_PATHS_POLICY_VERSION,
    MONTE_CARLO_DRAWDOWN_POLICY_VERSION,
    MONTE_CARLO_FEATURE_ID,
    MONTE_CARLO_METRIC_NAMES,
    MONTE_CARLO_MISSING_VALUE_POLICY_VERSION,
    MONTE_CARLO_OUTCOME_BASES,
    MONTE_CARLO_PATH_POLICY_VERSION,
    MONTE_CARLO_PERCENTILE_POLICY_VERSION,
    MONTE_CARLO_POLICY_VERSION,
    MONTE_CARLO_PRODUCTION_STATUS,
    MONTE_CARLO_PROMOTION_TICKET,
    MONTE_CARLO_REASON_CODES,
    MONTE_CARLO_RESAMPLING_METHODS,
    MONTE_CARLO_RISK_BUDGET_STATUS,
    MONTE_CARLO_RUIN_POLICY_VERSION,
    MONTE_CARLO_SAMPLE_POLICY_VERSION,
    NET_RETURN_BASIS,
    NET_RETURN_CONVENTION,
    NET_RETURN_UNDEFINED_REASON,
    NOTIONAL_FRACTION_SCALING,
    OPEN_TRADE_REASON,
    ORDER_PERMUTATION,
    R_MULTIPLE_BASIS,
    R_UNDEFINED_REASON,
    RISK_FRACTION_SCALING,
    SAMPLE_AVAILABLE,
    SAMPLE_NOT_MEASURED,
    SCHEDULE_SOURCE_CALLER,
    SCHEDULE_SOURCE_CONFIG_BAND,
    SCHEDULE_SOURCE_CONFIG_MAXIMUM,
    TOTAL_RETURN_METRIC,
    TRADES_TAKEN_METRIC,
    MonteCarloRiskError,
    TradeOutcomeSample,
    TradeOutcomeSampleSet,
    config_risk_per_trade_schedules,
    monte_carlo_risk_spec,
    nearest_rank,
    restore_monte_carlo_risk_report,
    restore_trade_outcome_samples,
    risk_per_trade_schedule,
    run_monte_carlo_risk_analysis,
    trade_outcome_samples_from_backtest,
    trade_outcome_samples_from_dataset,
)
from btc_predictor.research.monte_carlo_risk import MONTE_CARLO_DECIMAL_PRECISION

sys.path.insert(0, str(Path(__file__).resolve().parent))

import test_backtest_engine as backtest_fixtures  # noqa: E402
import test_paper_trade_outcomes as outcome_fixtures  # noqa: E402


EXTRACTION = datetime(2024, 3, 1, tzinfo=UTC)
CONFIG = {
    "config_version": "strategy_config_v2",
    "strategy_version": "swing_v1.2",
    "parameter_set_id": "default_phase1",
}
# One realized run: three winners and five losers, none of which can drive NAV
# to zero under the compared budgets, so ruin never truncates a path here.
OBSERVED_R = ("2.5", "-1", "0.8", "-1", "1.4", "-0.6", "3.1", "-1")
SCHEDULE_FRACTIONS = ("0.005", "0.01", "0.02")


def sample(
    reference: str,
    *,
    r_multiple: str | None = None,
    net_return: str | None = None,
    r_reason: str = R_UNDEFINED_REASON,
    net_reason: str = NET_RETURN_UNDEFINED_REASON,
) -> TradeOutcomeSample:
    return TradeOutcomeSample(
        trade_reference=reference,
        r_multiple=None if r_multiple is None else Decimal(r_multiple),
        r_multiple_status=(
            SAMPLE_NOT_MEASURED if r_multiple is None else SAMPLE_AVAILABLE
        ),
        r_multiple_reason_code=None if r_multiple is not None else r_reason,
        net_return_fraction=None if net_return is None else Decimal(net_return),
        net_return_status=(
            SAMPLE_NOT_MEASURED if net_return is None else SAMPLE_AVAILABLE
        ),
        net_return_reason_code=None if net_return is not None else net_reason,
    )


def sample_set(*samples: TradeOutcomeSample, **overrides) -> TradeOutcomeSampleSet:
    values = {
        "feature_id": MONTE_CARLO_FEATURE_ID,
        "policy_version": MONTE_CARLO_SAMPLE_POLICY_VERSION,
        "source_feature_id": "PAPER_TRADE_OUTCOME_DATASET",
        "source_policy_version": "PAPER_TRADE_OUTCOME_DATASET_V1",
        "source_id": "dataset-btc187",
        "accounting_policy_version": PAPER_TRADE_ACCOUNTING_POLICY_VERSION,
        "r_multiple_convention": R_MULTIPLE_CONVENTION,
        "net_return_convention": NET_RETURN_CONVENTION,
        "extraction_time": EXTRACTION,
        "config_metadata": dict(CONFIG),
        "samples": samples,
        **overrides,
    }
    return TradeOutcomeSampleSet(**values)


def observed_samples(values: tuple[str, ...] = OBSERVED_R) -> TradeOutcomeSampleSet:
    return sample_set(
        *(
            sample(
                f"trade-{index:04d}",
                r_multiple=value,
                # An arbitrary but distinct second basis, so a basis swap is a
                # visibly different question rather than the same numbers twice.
                net_return=str(Decimal(value) / Decimal("20")),
            )
            for index, value in enumerate(values)
        )
    )


def schedules(fractions: tuple[str, ...] = SCHEDULE_FRACTIONS):
    return [
        risk_per_trade_schedule(schedule_id=f"risk_{fraction}", fraction_of_nav=fraction)
        for fraction in fractions
    ]


def spec_for(samples: TradeOutcomeSampleSet, **overrides):
    values = {
        "samples": samples,
        "schedules": schedules(),
        "seed": 20260902,
        "simulation_count": 250,
        "path_length": 24,
        **overrides,
    }
    return monte_carlo_risk_spec(**values)


def analysis(**overrides):
    samples = overrides.pop("samples", observed_samples())
    spec = spec_for(samples, **overrides)
    return spec, samples, run_monte_carlo_risk_analysis(spec, samples)


# --- the frozen contract --------------------------------------------------


def test_metadata_and_vocabulary_are_stable() -> None:
    assert MONTE_CARLO_FEATURE_ID == "MONTE_CARLO_PORTFOLIO_RISK"
    assert MONTE_CARLO_POLICY_VERSION == "MONTE_CARLO_PORTFOLIO_RISK_V1"
    assert MONTE_CARLO_OUTCOME_BASES == (R_MULTIPLE_BASIS, NET_RETURN_BASIS)
    assert MONTE_CARLO_RESAMPLING_METHODS == (IID_BOOTSTRAP, ORDER_PERMUTATION)
    assert MONTE_CARLO_METRIC_NAMES == (
        ENDING_NAV_METRIC,
        ENDING_NAV_FRACTION_METRIC,
        TOTAL_RETURN_METRIC,
        MAX_DRAWDOWN_METRIC,
        LONGEST_LOSING_STREAK_METRIC,
        CALMAR_METRIC,
        TRADES_TAKEN_METRIC,
    )
    assert DEFAULT_DRAWDOWN_THRESHOLDS == (Decimal("0.10"), Decimal("0.15"))


def test_the_specification_persists_every_policy_it_depends_on() -> None:
    spec, _, report = analysis()

    assert spec.policy_version == MONTE_CARLO_POLICY_VERSION
    assert spec.sample_policy_version == MONTE_CARLO_SAMPLE_POLICY_VERSION
    assert spec.resampling_policy_version == "IID_BOOTSTRAP_WITH_REPLACEMENT_V1"
    assert spec.random_stream_policy_version == UNIFORM_INDEX_POLICY_VERSION
    assert spec.path_policy_version == MONTE_CARLO_PATH_POLICY_VERSION
    assert spec.schedule_scaling_policy_version == RISK_FRACTION_SCALING
    assert spec.drawdown_policy_version == MONTE_CARLO_DRAWDOWN_POLICY_VERSION
    assert spec.calmar_policy_version == MONTE_CARLO_CALMAR_POLICY_VERSION
    assert spec.percentile_policy_version == MONTE_CARLO_PERCENTILE_POLICY_VERSION
    assert spec.ruin_policy_version == MONTE_CARLO_RUIN_POLICY_VERSION
    assert spec.common_paths_policy_version == MONTE_CARLO_COMMON_PATHS_POLICY_VERSION
    assert spec.config_metadata == CONFIG
    assert report.missing_value_policy_version == MONTE_CARLO_MISSING_VALUE_POLICY_VERSION
    assert set(report.reason_codes) <= set(MONTE_CARLO_REASON_CODES)


def test_permutation_resampling_declares_its_own_stream_and_policy() -> None:
    samples = observed_samples()
    spec = spec_for(
        samples, resampling_method=ORDER_PERMUTATION, path_length=None, simulation_count=60
    )

    assert spec.resampling_policy_version == "PERMUTATION_WITHOUT_REPLACEMENT_V1"
    assert spec.random_stream_policy_version == PERMUTATION_INDEX_POLICY_VERSION
    assert spec.path_length == spec.usable_sample_count
    report = run_monte_carlo_risk_analysis(spec, samples)
    assert "MONTE_CARLO_TRADE_MULTISET_PRESERVED" in report.reason_codes
    assert "MONTE_CARLO_SERIAL_DEPENDENCE_NOT_PRESERVED" not in report.reason_codes


# --- the observed universe ------------------------------------------------


def test_samples_are_read_from_a_paper_trade_outcome_dataset() -> None:
    dataset = outcome_fixtures._dataset()

    samples = trade_outcome_samples_from_dataset(dataset)

    assert samples.source_feature_id == dataset.feature_id
    assert samples.source_id == dataset.dataset_id
    assert samples.accounting_policy_version == dataset.accounting_policy_version
    assert samples.r_multiple_convention == dataset.r_multiple_convention
    assert samples.extraction_time == dataset.extraction_time
    assert samples.config_metadata == dataset.config_metadata
    for row in dataset.rows:
        drawn = next(
            item
            for item in samples.samples
            if item.trade_reference == row.trade_reference
        )
        # BTC-165 owns the R multiple; BTC-187 never recomputes it.
        assert drawn.r_multiple == row.outcome(R_MULTIPLE_BASIS).value
        # The net return is normalized inside the module's declared context,
        # so replay never depends on the caller's ambient decimal precision.
        with localcontext(Context(prec=MONTE_CARLO_DECIMAL_PRECISION)):
            expected = (
                row.outcome("net_pnl").value / row.outcome("entry_notional").value
            )
        assert drawn.net_return_fraction == expected


def test_samples_are_read_from_a_backtest_run_and_open_trades_are_excluded() -> None:
    result = backtest_fixtures.run()
    open_trades = tuple(trade for trade in result.trades if not trade.closed)
    assert open_trades, "the fixture run is expected to end holding a position"

    samples = trade_outcome_samples_from_backtest(result)

    assert samples.source_id == result.run_id
    assert samples.sample_count == len(result.trades)
    excluded = samples.excluded(R_MULTIPLE_BASIS)
    assert len(excluded) == len(open_trades)
    for item in excluded:
        assert item.r_multiple is None
        assert item.r_multiple_reason_code == OPEN_TRADE_REASON
        assert item.net_return_fraction is None
        assert item.net_return_reason_code == OPEN_TRADE_REASON


def test_the_sample_set_replays_from_its_record() -> None:
    samples = observed_samples()

    record = samples.as_record()

    assert restore_trade_outcome_samples(record).as_record() == record
    tampered = {**record, "samples": [*record["samples"]]}
    tampered["samples"][0] = {**tampered["samples"][0], "r_multiple": "9.9"}
    # A universe is bound to an analysis by digest, so an edited outcome can no
    # longer answer the question that was asked of the recorded one.
    assert (
        restore_trade_outcome_samples(tampered).input_digest != samples.input_digest
    )
    with pytest.raises(MonteCarloRiskError, match="do not match the specification"):
        run_monte_carlo_risk_analysis(
            spec_for(samples), restore_trade_outcome_samples(tampered)
        )
    contradictory = {**record, "samples": [*record["samples"]]}
    contradictory["samples"][0] = {
        **contradictory["samples"][0],
        "r_multiple": None,
    }
    with pytest.raises(MonteCarloRiskError, match="must be a Decimal"):
        restore_trade_outcome_samples(contradictory)


def test_unmeasured_outcomes_are_excluded_by_name_and_never_zero_filled() -> None:
    samples = sample_set(
        sample("trade-a", r_multiple="1.5", net_return="0.075"),
        sample("trade-b", r_multiple="-1", net_return="-0.05"),
        sample("trade-c", r_multiple=None, net_return="0.01"),
    )

    _, _, report = analysis(samples=samples, path_length=6, simulation_count=40)

    assert report.included_trade_references == ("trade-a", "trade-b")
    assert len(report.excluded_samples) == 1
    excluded = report.excluded_samples[0]
    assert excluded.trade_reference == "trade-c"
    assert excluded.status == SAMPLE_NOT_MEASURED
    assert excluded.reason_code == R_UNDEFINED_REASON
    assert "MONTE_CARLO_EXCLUDED_UNMEASURED_OUTCOMES" in report.reason_codes
    # The unmeasured trade never enters the resampled universe as a zero.
    assert report.spec.usable_sample_count == 2
    assert report.spec.sample_count == 3


def test_a_zero_entry_notional_makes_the_net_return_undefined_not_zero() -> None:
    dataset = outcome_fixtures._dataset()
    samples = trade_outcome_samples_from_dataset(dataset)
    assert all(
        item.net_return_status == SAMPLE_AVAILABLE for item in samples.samples
    )

    undefined = sample("trade-flat", r_multiple="0.5")

    assert undefined.net_return_fraction is None
    assert undefined.net_return_reason_code == NET_RETURN_UNDEFINED_REASON


def test_included_and_excluded_trades_account_for_every_sample() -> None:
    samples = sample_set(
        sample("trade-a", r_multiple="1.5", net_return="0.075"),
        sample("trade-b", r_multiple="-1", net_return="-0.05"),
        sample("trade-c", r_multiple=None, net_return="0.01"),
    )

    _, _, report = analysis(samples=samples, path_length=6, simulation_count=40)

    accounted = {*report.included_trade_references} | {
        item.trade_reference for item in report.excluded_samples
    }
    assert accounted == {item.trade_reference for item in samples.samples}


def test_a_small_observed_universe_is_declared_rather_than_smoothed_over() -> None:
    _, _, report = analysis()

    assert report.spec.usable_sample_count == len(OBSERVED_R)
    assert "MONTE_CARLO_SMALL_SAMPLE_UNIVERSE" in report.reason_codes


# --- reproducibility ------------------------------------------------------


def test_a_fixed_seed_and_configuration_reproduce_identical_evidence() -> None:
    _, _, first = analysis()
    _, _, second = analysis()

    assert first.evidence_digest == second.evidence_digest
    assert first.as_record() == second.as_record()


def test_a_different_seed_produces_a_different_analysis_and_evidence() -> None:
    _, _, first = analysis()
    _, _, second = analysis(seed=20260903)

    assert first.spec.seed != second.spec.seed
    assert first.spec.analysis_id != second.spec.analysis_id
    assert first.evidence_digest != second.evidence_digest


def test_the_report_replays_from_its_record_and_refuses_a_tampered_one() -> None:
    _, _, report = analysis()

    record = report.as_record()

    assert restore_monte_carlo_risk_report(record).as_record() == record
    tampered = {**record, "profiles": [*record["profiles"]]}
    tampered["profiles"][0] = {
        **tampered["profiles"][0],
        "probability_of_ruin": "0.500000000000",
    }
    with pytest.raises(MonteCarloRiskError, match="does not match"):
        restore_monte_carlo_risk_report(tampered)


def test_schedule_order_is_canonical_so_one_question_has_one_identity() -> None:
    samples = observed_samples()
    declared = schedules()

    forward = spec_for(samples, schedules=declared)
    reversed_order = spec_for(samples, schedules=list(reversed(declared)))

    assert forward.analysis_id == reversed_order.analysis_id
    assert forward.schedules == reversed_order.schedules
    assert run_monte_carlo_risk_analysis(
        forward, samples
    ).evidence_digest == run_monte_carlo_risk_analysis(
        reversed_order, samples
    ).evidence_digest


def test_the_simulation_count_is_configurable_and_honoured() -> None:
    _, _, small = analysis(simulation_count=37)

    for profile in small.profiles:
        assert profile.simulation_count == 37
        for distribution in profile.distributions:
            assert distribution.defined_count + distribution.undefined_count == 37


# --- comparing risk-per-trade schedules -----------------------------------


def test_every_schedule_is_simulated_on_the_same_resampled_paths() -> None:
    _, _, report = analysis()

    assert report.schedule_ids == tuple(
        f"risk_{fraction}" for fraction in SCHEDULE_FRACTIONS
    )
    assert "MONTE_CARLO_COMMON_PATHS_ACROSS_SCHEDULES" in report.reason_codes
    reference = report.profiles[0]
    for profile in report.profiles[1:]:
        # The win/loss pattern of a path does not depend on the budget, so
        # common random numbers force these two metrics to agree exactly.
        for metric in (LONGEST_LOSING_STREAK_METRIC, TRADES_TAKEN_METRIC):
            assert profile.distribution(metric).as_record() == reference.distribution(
                metric
            ).as_record()
    # The budget still has to matter for the metrics it scales.
    assert (
        report.profiles[-1].distribution(MAX_DRAWDOWN_METRIC).mean
        != reference.distribution(MAX_DRAWDOWN_METRIC).mean
    )


def test_a_larger_budget_is_never_safer_on_the_same_paths() -> None:
    _, _, report = analysis()

    ordered = sorted(report.profiles, key=lambda item: item.schedule.fraction_of_nav)
    for lower, higher in zip(ordered, ordered[1:], strict=False):
        low = lower.distribution(MAX_DRAWDOWN_METRIC)
        high = higher.distribution(MAX_DRAWDOWN_METRIC)
        for percentile in DEFAULT_PERCENTILES:
            assert high.percentile(percentile) >= low.percentile(percentile)
        for threshold in DEFAULT_DRAWDOWN_THRESHOLDS:
            assert (
                higher.exceedance(threshold).path_count
                >= lower.exceedance(threshold).path_count
            )


def test_risk_budgets_are_read_from_the_versioned_strategy_configuration() -> None:
    declared = config_risk_per_trade_schedules()

    assert len(declared) >= 2
    fractions = [item.fraction_of_nav for item in declared]
    assert fractions == sorted(fractions)
    assert len(set(fractions)) == len(fractions)
    sources = {item.source for item in declared}
    assert sources <= {SCHEDULE_SOURCE_CONFIG_BAND, SCHEDULE_SOURCE_CONFIG_MAXIMUM}
    assert SCHEDULE_SOURCE_CONFIG_BAND in sources
    samples = observed_samples()
    spec = spec_for(samples, schedules=list(declared), simulation_count=40, path_length=8)
    report = run_monte_carlo_risk_analysis(spec, samples)
    assert report.schedule_ids == tuple(item.schedule_id for item in declared)


def test_a_caller_declared_schedule_records_its_source() -> None:
    declared = risk_per_trade_schedule(schedule_id="stress", fraction_of_nav="0.03")

    assert declared.source == SCHEDULE_SOURCE_CALLER
    assert declared.fraction_of_nav == Decimal("0.03")


# --- the simulated portfolio path -----------------------------------------


def test_path_arithmetic_is_hand_checkable() -> None:
    # One winner and one loser, reordered without replacement, so every path is
    # a permutation of (+1R, -1R) and the whole distribution is closed form.
    samples = sample_set(
        sample("winner", r_multiple="1", net_return="0.05"),
        sample("loser", r_multiple="-1", net_return="-0.05"),
    )
    spec = spec_for(
        samples,
        schedules=schedules(("0.5", "0.25")),
        resampling_method=ORDER_PERMUTATION,
        path_length=None,
        simulation_count=32,
    )

    report = run_monte_carlo_risk_analysis(spec, samples)

    half = report.profile("risk_0.5")
    # NAV multiplies by 1.5 and by 0.5 in some order: 0.75 either way.
    assert half.distribution(ENDING_NAV_METRIC).minimum == Decimal("0.75")
    assert half.distribution(ENDING_NAV_METRIC).maximum == Decimal("0.75")
    assert half.distribution(TOTAL_RETURN_METRIC).mean == Decimal("-0.25")
    # Peak 1.5 to trough 0.75, or peak 1 to trough 0.5: one half either way.
    assert half.distribution(MAX_DRAWDOWN_METRIC).minimum == Decimal("0.5")
    assert half.distribution(MAX_DRAWDOWN_METRIC).maximum == Decimal("0.5")
    assert half.distribution(CALMAR_METRIC).mean == Decimal("-0.5")
    assert half.distribution(LONGEST_LOSING_STREAK_METRIC).maximum == Decimal("1")
    assert half.distribution(TRADES_TAKEN_METRIC).minimum == Decimal("2")
    assert half.probability_of_loss == Decimal("1")
    assert half.probability_of_ruin == Decimal("0")
    quarter = report.profile("risk_0.25")
    # 1.25 * 0.75 = 0.9375, and the drawdown is 0.25 whichever order is drawn.
    assert quarter.distribution(ENDING_NAV_METRIC).mean == Decimal("0.9375")
    assert quarter.distribution(MAX_DRAWDOWN_METRIC).mean == Decimal("0.25")


def test_ruin_stops_the_path_and_is_reported_as_a_tail_metric() -> None:
    samples = sample_set(
        sample("loss-a", r_multiple="-1", net_return="-0.05"),
        sample("loss-b", r_multiple="-1", net_return="-0.05"),
    )
    spec = spec_for(
        samples,
        schedules=schedules(("0.25", "0.5")),
        simulation_count=16,
        path_length=5,
        ruin_nav_fraction="0.5",
    )

    report = run_monte_carlo_risk_analysis(spec, samples)

    assert "MONTE_CARLO_RUIN_OBSERVED" in report.reason_codes
    gentle = report.profile("risk_0.25")
    # 0.75, 0.5625, 0.421875: the third loss breaches the declared ruin level.
    assert gentle.probability_of_ruin == Decimal("1")
    assert gentle.ruin_path_count == spec.simulation_count
    assert gentle.distribution(TRADES_TAKEN_METRIC).maximum == Decimal("3")
    assert gentle.distribution(ENDING_NAV_METRIC).mean == Decimal("0.421875")
    steep = report.profile("risk_0.5")
    # A halved NAV is already at the ruin level, so the path stops immediately.
    assert steep.probability_of_ruin == Decimal("1")
    assert steep.distribution(TRADES_TAKEN_METRIC).maximum == Decimal("1")
    assert steep.distribution(ENDING_NAV_METRIC).mean == Decimal("0.5")


def test_calmar_is_undefined_rather_than_infinite_without_a_drawdown() -> None:
    samples = sample_set(
        sample("winner-a", r_multiple="1", net_return="0.05"),
        sample("winner-b", r_multiple="2", net_return="0.1"),
    )

    _, _, report = analysis(samples=samples, simulation_count=24, path_length=6)

    for profile in report.profiles:
        calmar = profile.distribution(CALMAR_METRIC)
        assert calmar.defined_count == 0
        assert calmar.undefined_count == profile.simulation_count
        assert calmar.undefined_status == CALMAR_UNDEFINED_NO_DRAWDOWN
        assert calmar.percentiles == ()
        assert calmar.mean is None
        assert profile.distribution(MAX_DRAWDOWN_METRIC).maximum == Decimal("0")
    assert "MONTE_CARLO_UNDEFINED_CALMAR_PATHS" in report.reason_codes


# --- distributions rather than averages -----------------------------------


def test_every_metric_reports_a_percentile_distribution_beside_its_average() -> None:
    _, _, report = analysis()

    for profile in report.profiles:
        for distribution in profile.distributions:
            assert distribution.mean is not None
            assert tuple(
                item.percentile for item in distribution.percentiles
            ) == DEFAULT_PERCENTILES
            values = [item.value for item in distribution.percentiles]
            assert values == sorted(values)
            assert distribution.minimum <= values[0]
            assert values[-1] <= distribution.maximum


def test_the_percentile_grid_is_configurable_and_uses_nearest_rank() -> None:
    # 250 paths, so nearest rank puts the 0.4th percentile on the first path
    # and the 100th on the last: both percentiles are observed paths.
    grid = (Decimal("0.4"), Decimal("50"), Decimal("100"))

    _, _, report = analysis(percentiles=grid)

    for profile in report.profiles:
        distribution = profile.distribution(TOTAL_RETURN_METRIC)
        assert tuple(item.percentile for item in distribution.percentiles) == grid
        # Nearest rank reports an observed path, so the top rank is the maximum.
        assert distribution.percentile(100) == distribution.maximum
        assert distribution.percentile("0.4") == distribution.minimum


def test_drawdown_exceedance_probabilities_follow_the_declared_thresholds() -> None:
    thresholds = (Decimal("0.05"), Decimal("0.10"), Decimal("0.15"))

    _, _, report = analysis(drawdown_thresholds=thresholds)

    for profile in report.profiles:
        assert tuple(
            item.threshold for item in profile.drawdown_exceedances
        ) == thresholds
        counts = [item.path_count for item in profile.drawdown_exceedances]
        # A deeper threshold can only be breached by fewer paths.
        assert counts == sorted(counts, reverse=True)
        for item in profile.drawdown_exceedances:
            assert item.probability == (
                Decimal(item.path_count) / Decimal(profile.simulation_count)
            ).quantize(Decimal("1E-12"))


# --- the two outcome bases ------------------------------------------------


def test_both_outcome_bases_are_supported_and_scale_differently() -> None:
    samples = observed_samples()

    risk = spec_for(samples, outcome_basis=R_MULTIPLE_BASIS)
    notional = spec_for(samples, outcome_basis=NET_RETURN_BASIS)

    assert risk.schedule_scaling_policy_version == RISK_FRACTION_SCALING
    assert notional.schedule_scaling_policy_version == NOTIONAL_FRACTION_SCALING
    assert risk.analysis_id != notional.analysis_id
    risk_report = run_monte_carlo_risk_analysis(risk, samples)
    notional_report = run_monte_carlo_risk_analysis(notional, samples)
    assert risk_report.outcome_basis == R_MULTIPLE_BASIS
    assert notional_report.outcome_basis == NET_RETURN_BASIS
    assert risk_report.evidence_digest != notional_report.evidence_digest


# --- research evidence, not a control surface -----------------------------


def test_the_analysis_challenges_a_risk_budget_and_never_changes_one() -> None:
    _, _, report = analysis()

    assert report.production_status == MONTE_CARLO_PRODUCTION_STATUS
    assert report.production_status == "RESEARCH_ONLY_NOT_PRODUCTION"
    assert report.promotion_ticket == MONTE_CARLO_PROMOTION_TICKET == "BTC-193"
    assert report.risk_budget_status == MONTE_CARLO_RISK_BUDGET_STATUS
    assert "MONTE_CARLO_RISK_BUDGET_CHALLENGE_ONLY" in report.reason_codes
    assert "MONTE_CARLO_RESEARCH_ONLY" in report.reason_codes
    assert "MONTE_CARLO_BTC_193_PROMOTION_REQUIRED" in report.reason_codes
    assert report.reason_codes[-1] == "MONTE_CARLO_COMPLETE"


def test_the_module_exposes_no_way_to_write_a_risk_budget() -> None:
    import btc_predictor.research.monte_carlo_risk as module

    forbidden = ("promote", "apply", "update_config", "write", "set_risk")
    exposed = [name for name in dir(module) if not name.startswith("_")]
    assert not [name for name in exposed if any(word in name for word in forbidden)]


# --- refused contracts ----------------------------------------------------


@pytest.mark.parametrize(
    "overrides,message",
    [
        ({"schedules": schedules(("0.01",))}, "at least 2 risk-per-trade schedules"),
        ({"simulation_count": 0}, "positive integer"),
        ({"seed": -1}, "non-negative integer"),
        ({"path_length": 0}, "positive integer"),
        ({"outcome_basis": "invented"}, "outcome_basis must be one of"),
        ({"resampling_method": "invented"}, "resampling_method must be one of"),
        ({"percentiles": (Decimal("50"), Decimal("10"))}, "percentiles must be ascending"),
        ({"percentiles": (Decimal("101"),)}, r"percentiles must fall in \(0, 100\]"),
        (
            {"drawdown_thresholds": (Decimal("0.15"), Decimal("0.10"))},
            "thresholds must be ascending",
        ),
        ({"drawdown_thresholds": (Decimal("0"),)}, "thresholds must be positive"),
        ({"ruin_nav_fraction": "1"}, "ruin_nav_fraction must be at least zero"),
        ({"starting_nav": "0"}, "starting_nav must be a positive decimal"),
        (
            {"resampling_method": ORDER_PERMUTATION, "path_length": 3},
            "order_permutation requires path_length",
        ),
    ],
)
def test_a_specification_that_breaks_the_contract_is_refused(overrides, message) -> None:
    with pytest.raises((MonteCarloRiskError, TypeError), match=message):
        spec_for(observed_samples(), **overrides)


def test_duplicate_schedule_identities_and_fractions_are_refused() -> None:
    samples = observed_samples()
    duplicate_fraction = [
        risk_per_trade_schedule(schedule_id="a", fraction_of_nav="0.01"),
        risk_per_trade_schedule(schedule_id="b", fraction_of_nav="0.01"),
    ]

    with pytest.raises(MonteCarloRiskError, match="distinct NAV fractions"):
        spec_for(samples, schedules=duplicate_fraction)


def test_an_unresamplable_universe_is_refused_rather_than_padded() -> None:
    samples = sample_set(
        sample("trade-a", r_multiple="1.5", net_return="0.075"),
        sample("trade-b", r_multiple=None, net_return="-0.05"),
    )

    with pytest.raises(MonteCarloRiskError, match="measurable r_multiple outcomes"):
        spec_for(samples, path_length=4)


def test_a_report_cannot_be_built_from_a_different_observed_universe() -> None:
    samples = observed_samples()
    spec = spec_for(samples)
    other = observed_samples(("1.0", "-1", "0.5", "-1", "2.0", "-0.5", "1.1", "-1"))

    with pytest.raises(MonteCarloRiskError, match="do not match the specification"):
        run_monte_carlo_risk_analysis(spec, other)


def test_a_sample_set_refuses_a_value_without_provenance() -> None:
    with pytest.raises(MonteCarloRiskError, match="must not carry a value"):
        TradeOutcomeSample(
            trade_reference="trade-a",
            r_multiple=Decimal("1"),
            r_multiple_status=SAMPLE_NOT_MEASURED,
            r_multiple_reason_code=R_UNDEFINED_REASON,
            net_return_fraction=None,
            net_return_status=SAMPLE_NOT_MEASURED,
            net_return_reason_code=R_UNDEFINED_REASON,
        )
    with pytest.raises(MonteCarloRiskError, match="reason_code must not be empty"):
        sample("trade-a", r_reason=" ")


def test_a_sample_set_refuses_a_foreign_accounting_convention() -> None:
    with pytest.raises(MonteCarloRiskError, match="r_multiple_convention"):
        sample_set(
            sample("trade-a", r_multiple="1", net_return="0.05"),
            r_multiple_convention="SOME_OTHER_R_V9",
        )
    with pytest.raises(MonteCarloRiskError, match="config_metadata must include"):
        sample_set(
            sample("trade-a", r_multiple="1", net_return="0.05"),
            config_metadata={"config_version": "strategy_config_v2"},
        )


def test_a_sample_set_keeps_the_whole_recorded_strategy_identity() -> None:
    dataset = outcome_fixtures._dataset()

    samples = trade_outcome_samples_from_dataset(dataset)

    assert set(samples.config_metadata) > set(CONFIG)
    assert samples.config_metadata["point_in_time_policy_version"]


def test_a_duplicate_trade_reference_is_refused() -> None:
    with pytest.raises(MonteCarloRiskError, match="trade references must be unique"):
        sample_set(
            sample("trade-a", r_multiple="1", net_return="0.05"),
            sample("trade-a", r_multiple="-1", net_return="-0.05"),
        )


def test_an_end_to_end_dataset_analysis_replays(monkeypatch) -> None:
    dataset = outcome_fixtures._dataset()
    samples = trade_outcome_samples_from_dataset(dataset)
    spec = monte_carlo_risk_spec(
        samples=samples,
        schedules=list(config_risk_per_trade_schedules()),
        seed=99,
        simulation_count=50,
        path_length=12,
    )

    report = run_monte_carlo_risk_analysis(spec, samples)

    record = report.as_record()
    assert restore_monte_carlo_risk_report(record).as_record() == record
    assert report.spec.sample_set_digest == samples.input_digest
    assert report.samples.source_id == dataset.dataset_id


def test_the_shared_percentile_rank_ignores_the_ambient_decimal_context() -> None:
    # EPIC S2 integration review.  BTC-189 delegates to this public rank rather
    # than restating NEAREST_RANK_PERCENTILE_V1, and it calls it outside this
    # module's own pinned computations, so one declared convention must not
    # resolve to two ranks depending on the caller's decimal context.
    expected = [(nearest_rank("2.5", 937), nearest_rank("97.5", 937))]

    for precision in (14, 6, 3, 2, 1):
        with decimal.localcontext() as context:
            context.prec = precision
            assert [(nearest_rank("2.5", 937), nearest_rank("97.5", 937))] == expected
