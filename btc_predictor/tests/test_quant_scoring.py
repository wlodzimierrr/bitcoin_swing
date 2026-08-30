import numpy as np
import pytest

from btc_predictor.quant import NumericInputError, WeightedScoreResult, weighted_score


COMPONENTS = ("trend", "flow", "volatility")
WEIGHTS = {"trend": 0.5, "flow": 0.3, "volatility": 0.2}


def test_single_row_returns_named_score_contributions_and_masks() -> None:
    result = weighted_score([80, 60, 40], WEIGHTS, component_names=COMPONENTS)

    assert isinstance(result, WeightedScoreResult)
    assert result.component_names == COMPONENTS
    assert result.single_row is True
    assert result.scores == 66.0
    assert result.complete_mask is True
    np.testing.assert_array_equal(result.weights, [0.5, 0.3, 0.2])
    np.testing.assert_array_equal(result.contributions, [40, 18, 8])
    np.testing.assert_array_equal(result.missing_mask, [False, False, False])


def test_mapping_weights_are_reordered_to_explicit_component_names() -> None:
    result = weighted_score(
        [40, 80, 60],
        {"trend": 0.5, "flow": 0.3, "volatility": 0.2},
        component_names=("volatility", "trend", "flow"),
    )

    np.testing.assert_array_equal(result.weights, [0.2, 0.5, 0.3])
    np.testing.assert_array_equal(result.contributions, [8, 40, 18])
    assert result.scores == 66


def test_matrix_scores_and_contributions_have_stable_shapes() -> None:
    values = np.asarray([[80, 60, 40], [20, 40, 100]], dtype=np.float64)

    result = weighted_score(values, WEIGHTS, component_names=COMPONENTS)

    assert result.single_row is False
    np.testing.assert_array_equal(result.scores, [66, 42])
    np.testing.assert_array_equal(result.contributions, [[40, 18, 8], [10, 12, 20]])
    np.testing.assert_array_equal(result.complete_mask, [True, True])
    assert result.contributions.shape == values.shape
    assert result.missing_mask.shape == values.shape
    assert result.contributions.dtype == np.float64
    assert result.missing_mask.dtype == np.bool_


def test_batch_and_single_row_calculations_are_numerically_identical() -> None:
    generator = np.random.Generator(np.random.PCG64(46))
    values = generator.normal(loc=50, scale=20, size=(128, 3))
    batch = weighted_score(values, WEIGHTS, component_names=COMPONENTS)

    singles = [
        weighted_score(row, WEIGHTS, component_names=COMPONENTS)
        for row in values
    ]

    np.testing.assert_array_equal(batch.scores, [result.scores for result in singles])
    np.testing.assert_array_equal(
        batch.contributions,
        [result.contributions for result in singles],
    )


def test_missing_inputs_are_masked_and_never_zero_filled() -> None:
    result = weighted_score(
        [[80, np.nan, 40], [20, 40, 100]],
        WEIGHTS,
        component_names=COMPONENTS,
    )

    assert np.isnan(result.scores[0])
    assert result.scores[1] == 42
    assert np.isnan(result.contributions[0, 1])
    np.testing.assert_array_equal(
        result.missing_mask,
        [[False, True, False], [False, False, False]],
    )
    np.testing.assert_array_equal(result.complete_mask, [False, True])


def test_all_missing_row_remains_nan_with_complete_contribution_mask() -> None:
    result = weighted_score(
        [np.nan, np.nan, np.nan],
        WEIGHTS,
        component_names=COMPONENTS,
    )

    assert np.isnan(result.scores)
    assert np.all(np.isnan(result.contributions))
    assert np.all(result.missing_mask)
    assert result.complete_mask is False


def test_array_weights_require_names_and_produce_same_output_as_mapping() -> None:
    mapping = weighted_score([80, 60, 40], WEIGHTS, component_names=COMPONENTS)
    array = weighted_score(
        [80, 60, 40],
        [0.5, 0.3, 0.2],
        component_names=COMPONENTS,
    )

    assert array.scores == mapping.scores
    np.testing.assert_array_equal(array.contributions, mapping.contributions)
    with pytest.raises(NumericInputError, match="component_names"):
        weighted_score([80, 60, 40], [0.5, 0.3, 0.2])


def test_weight_total_policy_supports_tolerance_and_unconstrained_positive_totals() -> None:
    tolerant = weighted_score(
        [10, 20],
        {"a": 0.5000002, "b": 0.5000002},
        weight_tolerance=1e-6,
    )
    unconstrained = weighted_score(
        [10, 20],
        {"a": 2, "b": 1},
        expected_weight_total=None,
    )

    assert tolerant.complete_mask is True
    assert unconstrained.scores == 40
    with pytest.raises(NumericInputError, match="sum to"):
        weighted_score(
            [10, 20],
            {"a": 0.6, "b": 0.5},
            weight_tolerance=1e-6,
        )


def test_empty_historical_matrix_is_supported_with_known_components() -> None:
    result = weighted_score(
        np.empty((0, 3), dtype=np.float64),
        WEIGHTS,
        component_names=COMPONENTS,
    )

    assert result.scores.shape == (0,)
    assert result.contributions.shape == (0, 3)
    assert result.missing_mask.shape == (0, 3)
    assert result.complete_mask.shape == (0,)


def test_inputs_and_weights_are_not_mutated_or_aliased() -> None:
    values = np.asarray([80.0, 60.0, 40.0])
    weights = np.asarray([0.5, 0.3, 0.2])

    result = weighted_score(values, weights, component_names=COMPONENTS)
    result.contributions[0] = -1
    result.weights[0] = -1

    np.testing.assert_array_equal(values, [80, 60, 40])
    np.testing.assert_array_equal(weights, [0.5, 0.3, 0.2])


@pytest.mark.parametrize(
    "weights,names,match",
    [
        ({"trend": 0.5, "flow": 0.5}, COMPONENTS, "exactly match"),
        ({"trend": 0.5, "flow": 0.3, "other": 0.2}, COMPONENTS, "exactly match"),
        ([0.5, 0.5], COMPONENTS, "count"),
        ([0.5, 0.3, 0.2], ("trend", "trend", "flow"), "unique"),
        ([1.0], ("",), "non-empty strings"),
    ],
)
def test_weight_names_and_shapes_fail_fast(weights, names, match) -> None:
    with pytest.raises(NumericInputError, match=match):
        weighted_score([1, 2, 3], weights, component_names=names)


@pytest.mark.parametrize(
    "call,match",
    [
        (lambda: weighted_score(1, {"a": 1}), "one-dimensional row or matrix"),
        (lambda: weighted_score([], {"a": 1}), "at least one component"),
        (lambda: weighted_score([[[1]]], {"a": 1}), "one-dimensional row or matrix"),
        (lambda: weighted_score([1, 2], {"a": 1}), "component count"),
        (lambda: weighted_score([1], {"a": -1}), "non-negative"),
        (lambda: weighted_score([1], {"a": 0}), "positive total"),
        (lambda: weighted_score([1], {"a": np.nan}), "NaN"),
        (lambda: weighted_score([np.inf], {"a": 1}), "infinite"),
        (lambda: weighted_score([1], {"a": 1}, weight_tolerance=-1), "non-negative"),
    ],
)
def test_invalid_score_inputs_and_weight_policy_fail_fast(call, match) -> None:
    with pytest.raises(NumericInputError, match=match):
        call()


def test_repeated_calculation_is_deterministic() -> None:
    first = weighted_score([[80, 60, 40]], WEIGHTS, component_names=COMPONENTS)
    second = weighted_score([[80, 60, 40]], WEIGHTS, component_names=COMPONENTS)

    np.testing.assert_array_equal(first.scores, second.scores)
    np.testing.assert_array_equal(first.contributions, second.contributions)
    np.testing.assert_array_equal(first.missing_mask, second.missing_mask)
