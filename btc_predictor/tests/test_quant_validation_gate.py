import json
import warnings
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from math import fsum, sqrt

import numpy as np
import pytest

from btc_predictor.features.flow import (
    FULL_FLOW_SCORE_COMPONENT_IDS,
    FlowScoreInput,
    calculate_flow_score,
)
from btc_predictor.features.positioning import (
    POSITIONING_SCORE_COMPONENT_IDS,
    PositioningScoreInput,
    calculate_positioning_score,
)
from btc_predictor.features.structure import (
    STRUCTURE_SCORE_COMPONENT_IDS,
    StructureScoreInput,
    calculate_structure_score,
)
from btc_predictor.features.trend import (
    TREND_SCORE_COMPONENT_IDS,
    TrendScoreInput,
    calculate_trend_score,
)
from btc_predictor.quant import (
    DEFAULT_TOLERANCE,
    PARITY_ABSOLUTE_TOLERANCE,
    PARITY_RELATIVE_TOLERANCE,
    PARITY_TOLERANCE,
    NumericInputError,
    as_float64_array,
    normal_cdf_score,
    position_notional,
    risk_at_stop,
    rolling_mean,
    rolling_volatility,
    rolling_zscore,
    weighted_score,
)
from btc_predictor.research.feature_matrix import (
    FeatureMatrixDefinition,
    FeatureObservation,
    build_point_in_time_feature_matrix,
)
from btc_predictor.research.quant_benchmarks import (
    QUANT_BENCHMARK_NAMES,
    QUANT_BENCHMARK_VERSION,
    run_basic_quant_benchmarks,
)


def test_parity_tolerance_is_owned_by_the_central_numeric_policy() -> None:
    assert PARITY_TOLERANCE is DEFAULT_TOLERANCE
    assert PARITY_ABSOLUTE_TOLERANCE == DEFAULT_TOLERANCE.absolute == 1e-12
    assert PARITY_RELATIVE_TOLERANCE == DEFAULT_TOLERANCE.relative == 1e-12


def test_python_oracles_match_numpy_rolling_mean_volatility_and_zscore() -> None:
    generator = np.random.Generator(np.random.PCG64(49))
    values = generator.normal(0, 2, size=257).tolist()
    window = 20

    expected_mean = []
    expected_volatility = []
    expected_zscore = []
    for index, value in enumerate(values):
        inclusive = values[max(0, index - window + 1) : index + 1]
        prior = values[max(0, index - window) : index]
        if len(inclusive) < window:
            expected_mean.append(np.nan)
            expected_volatility.append(np.nan)
        else:
            average = fsum(inclusive) / len(inclusive)
            variance = fsum((item - average) ** 2 for item in inclusive) / len(
                inclusive
            )
            expected_mean.append(average)
            expected_volatility.append(sqrt(variance))
        if len(prior) < window:
            expected_zscore.append(np.nan)
        else:
            prior_average = fsum(prior) / len(prior)
            prior_variance = fsum((item - prior_average) ** 2 for item in prior) / len(
                prior
            )
            expected_zscore.append((value - prior_average) / sqrt(prior_variance))

    np.testing.assert_allclose(
        rolling_mean(values, window=window),
        expected_mean,
        atol=PARITY_ABSOLUTE_TOLERANCE,
        rtol=PARITY_RELATIVE_TOLERANCE,
        equal_nan=True,
    )
    np.testing.assert_allclose(
        rolling_volatility(values, window=window),
        expected_volatility,
        atol=PARITY_ABSOLUTE_TOLERANCE,
        rtol=PARITY_RELATIVE_TOLERANCE,
        equal_nan=True,
    )
    np.testing.assert_allclose(
        rolling_zscore(values, window=window),
        expected_zscore,
        atol=PARITY_ABSOLUTE_TOLERANCE,
        rtol=PARITY_RELATIVE_TOLERANCE,
        equal_nan=True,
    )


def test_existing_domain_score_fixtures_are_reproduced_by_quant_engine() -> None:
    trend_inputs = TrendScoreInput(
        z_m4=Decimal("1"),
        z_m12=Decimal("0.5"),
        z_20w=Decimal("-0.25"),
        structure_score=Decimal("1"),
        z_52h=Decimal("-0.5"),
    )
    trend = calculate_trend_score(trend_inputs)
    _assert_domain_score_parity(
        values=[1, 0.5, -0.25, 1, -0.5],
        weights=[0.30, 0.30, 0.20, 0.15, 0.05],
        names=TREND_SCORE_COMPONENT_IDS,
        domain_score=trend.raw_score,
        domain_contributions=trend.contributions,
        expected_weight_total=None,
    )
    assert trend.score == Decimal(
        str(normal_cdf_score(float(trend.raw_score), minimum=0, maximum=100))
    )

    flow_inputs = FlowScoreInput(
        etf_norm_5_zscore=Decimal("1"),
        etf_norm_20_zscore=Decimal("0.5"),
        flow_accel_zscore=Decimal("0.2"),
        cvd_spread_zscore=Decimal("1.5"),
        spot_dominance_zscore=Decimal("-0.5"),
    )
    flow = calculate_flow_score(flow_inputs)
    _assert_domain_score_parity(
        values=[1, 0.5, 0.2, 1.5, -0.5],
        weights=[0.30, 0.25, 0.20, 0.15, 0.10],
        names=FULL_FLOW_SCORE_COMPONENT_IDS,
        domain_score=flow.raw_score,
        domain_contributions=flow.contributions,
    )
    assert flow.score == Decimal(
        str(normal_cdf_score(float(flow.raw_score), minimum=0, maximum=100))
    )

    positioning = calculate_positioning_score(
        PositioningScoreInput(
            funding_health=Decimal("80"),
            oi_health=Decimal("70"),
            basis_health=Decimal("60"),
            leverage_health=Decimal("40"),
        )
    )
    _assert_domain_score_parity(
        values=[80, 70, 60, 40],
        weights=[0.35, 0.30, 0.20, 0.15],
        names=POSITIONING_SCORE_COMPONENT_IDS,
        domain_score=positioning.score,
        domain_contributions=positioning.contributions,
    )

    structure = calculate_structure_score(
        StructureScoreInput(
            level_strength=Decimal("80"),
            entry_location=Decimal("70"),
            rr_quality=Decimal("90"),
            confluence=Decimal("75"),
        )
    )
    _assert_domain_score_parity(
        values=[80, 70, 90, 75],
        weights=[0.45, 0.25, 0.20, 0.10],
        names=STRUCTURE_SCORE_COMPONENT_IDS,
        domain_score=structure.score,
        domain_contributions=structure.contributions,
    )


def test_single_date_and_batch_history_paths_match_across_matrix_scoring_and_risk() -> (
    None
):
    start = datetime(2026, 1, 1, tzinfo=UTC)
    decisions = tuple(start + timedelta(days=index) for index in range(1, 5))
    definition = FeatureMatrixDefinition(
        feature_names=("TREND_SCORE", "FLOW_SCORE"),
        version="QUANT_GATE_FEATURES_V1",
    )
    observations = []
    for index in range(4):
        observation_time = start + timedelta(days=index)
        observations.extend(
            (
                FeatureObservation(
                    "TREND_SCORE",
                    60 + index,
                    observation_time,
                    observation_time + timedelta(hours=1),
                    f"trend-{index}",
                ),
                FeatureObservation(
                    "FLOW_SCORE",
                    50 + index,
                    observation_time,
                    observation_time + timedelta(hours=1),
                    f"flow-{index}",
                ),
            )
        )
    matrix = build_point_in_time_feature_matrix(
        observations,
        decisions,
        definition=definition,
    )
    batch_score = weighted_score(
        matrix.values,
        [0.6, 0.4],
        component_names=definition.feature_names,
    )
    single_scores = [
        weighted_score(
            row,
            [0.6, 0.4],
            component_names=definition.feature_names,
        ).scores
        for row in matrix.values
    ]
    np.testing.assert_array_equal(batch_score.scores, single_scores)

    entries = np.asarray([[100, 110], [120, 130], [140, 150], [160, 170]])
    quantities = np.asarray([[1, 2], [2, 3], [3, 4], [4, 5]])
    notionals = position_notional(quantities, entries)
    batch_risk = risk_at_stop(notionals, entries, 90, side="long")
    single_risk = [
        risk_at_stop(row_notionals, row_entries, 90, side="long")
        for row_notionals, row_entries in zip(notionals, entries)
    ]
    np.testing.assert_array_equal(batch_risk, single_risk)


def test_appending_future_data_cannot_change_historical_quant_outputs() -> None:
    values = [100, 102, 101, 105, 107, 106, 109, 111]
    future_values = [*values, 1_000_000]
    np.testing.assert_array_equal(
        rolling_mean(values, window=3),
        rolling_mean(future_values, window=3)[: len(values)],
    )
    np.testing.assert_array_equal(
        rolling_zscore(values, window=3),
        rolling_zscore(future_values, window=3)[: len(values)],
    )

    start = datetime(2026, 2, 1, tzinfo=UTC)
    decisions = (start + timedelta(days=1), start + timedelta(days=2))
    definition = FeatureMatrixDefinition(
        feature_names=("TREND_SCORE",),
        version="APPEND_GATE_V1",
    )
    history = [
        FeatureObservation(
            "TREND_SCORE",
            60,
            start,
            start + timedelta(hours=1),
            "history",
        )
    ]
    original = build_point_in_time_feature_matrix(
        history,
        decisions,
        definition=definition,
    )
    appended = build_point_in_time_feature_matrix(
        [
            *history,
            FeatureObservation(
                "TREND_SCORE",
                99,
                start + timedelta(days=3),
                start + timedelta(days=3, hours=1),
                "future",
            ),
        ],
        decisions,
        definition=definition,
    )
    np.testing.assert_array_equal(original.values, appended.values)
    assert original.available_ats == appended.available_ats


def test_nan_and_infinity_policy_is_enforced_at_inputs_and_arithmetic_outputs() -> None:
    incomplete = weighted_score(
        [80, np.nan],
        [0.5, 0.5],
        component_names=("trend", "flow"),
    )
    assert np.isnan(incomplete.scores)
    assert incomplete.complete_mask is False
    np.testing.assert_array_equal(incomplete.missing_mask, [False, True])

    with pytest.raises(NumericInputError, match="infinite"):
        as_float64_array([1, np.inf], nan_policy="propagate")
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        np.testing.assert_array_equal(
            rolling_mean([1e308, 1e308], window=2),
            [np.nan, 1e308],
        )
        with pytest.raises(NumericInputError, match="finite float64 range"):
            weighted_score(
                [1e308, 1e308],
                [1, 1],
                component_names=("a", "b"),
                expected_weight_total=2,
            )
        with pytest.raises(NumericInputError, match="finite float64 range"):
            position_notional(1e308, 1e308)


def test_basic_benchmarks_execute_without_becoming_a_speed_gate() -> None:
    first = run_basic_quant_benchmarks(observation_count=512, repeats=1, seed=49)
    second = run_basic_quant_benchmarks(observation_count=512, repeats=1, seed=49)

    assert tuple(result.name for result in first) == QUANT_BENCHMARK_NAMES
    assert all(result.benchmark_version == QUANT_BENCHMARK_VERSION for result in first)
    assert all(result.best_seconds > 0 for result in first)
    assert all(result.median_seconds > 0 for result in first)
    assert all(result.observations_per_second > 0 for result in first)
    np.testing.assert_allclose(
        [result.checksum for result in first],
        [result.checksum for result in second],
        atol=PARITY_ABSOLUTE_TOLERANCE,
        rtol=PARITY_RELATIVE_TOLERANCE,
    )
    json.dumps([result.as_record() for result in first], sort_keys=True)


def _assert_domain_score_parity(
    *,
    values: list[float],
    weights: list[float],
    names: tuple[str, ...],
    domain_score: Decimal | None,
    domain_contributions: dict[str, Decimal | None],
    expected_weight_total: float | None = 1.0,
) -> None:
    result = weighted_score(
        values,
        weights,
        component_names=names,
        expected_weight_total=expected_weight_total,
    )
    assert domain_score is not None
    np.testing.assert_allclose(
        result.scores,
        float(domain_score),
        atol=PARITY_ABSOLUTE_TOLERANCE,
        rtol=PARITY_RELATIVE_TOLERANCE,
    )
    np.testing.assert_allclose(
        result.contributions,
        [float(domain_contributions[name]) for name in names],
        atol=PARITY_ABSOLUTE_TOLERANCE,
        rtol=PARITY_RELATIVE_TOLERANCE,
    )
