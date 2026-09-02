"""BTC-220 focused unit tests for the Decimal/float64 domain-wrapper boundary.

``features._scoring`` is the single seam every v1.2 domain score wrapper
(Entry Conviction, Hold, Add, Structure, Trend, Flow, Positioning, Volatility,
Regime) uses to delegate weighted-score arithmetic to the authoritative
``quant.scoring`` owner while keeping persisted values in ``Decimal``. The
delegation, the missing-component contract, and the weight-sum policy are
pinned here so the wrappers cannot quietly grow their own score arithmetic.
"""

from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.features._scoring import (
    DECIMAL_BOUNDED_LINEAR_POLICY_VERSION,
    DecimalWeightedScore,
    decimal_bounded_linear,
    decimal_weighted_score,
)
from btc_predictor.features.scoring_contracts import (
    ADD_SCORE_WEIGHTS_V1_2,
    ENTRY_CONVICTION_WEIGHTS_V1_2,
    HOLD_SCORE_WEIGHTS_V1_2,
    STRUCTURE_WEIGHTS_V1_2,
)
from btc_predictor.quant import NumericInputError
from btc_predictor.quant.scoring import weighted_score
from btc_predictor.quant.transforms import bounded_linear


COMPONENT_IDS = ("trend", "flow", "structure")
WEIGHTS = {
    "trend": Decimal("0.5"),
    "flow": Decimal("0.3"),
    "structure": Decimal("0.2"),
}
VALUES = {
    "trend": Decimal("70.00"),
    "flow": Decimal("55.00"),
    "structure": Decimal("40.00"),
}

V1_2_CONTRACTS = {
    "entry_conviction": ENTRY_CONVICTION_WEIGHTS_V1_2,
    "hold_score": HOLD_SCORE_WEIGHTS_V1_2,
    "add_score": ADD_SCORE_WEIGHTS_V1_2,
    "structure": STRUCTURE_WEIGHTS_V1_2,
}


def test_complete_score_is_the_exact_decimal_weighted_sum() -> None:
    result = decimal_weighted_score(VALUES, WEIGHTS, component_ids=COMPONENT_IDS)

    assert isinstance(result, DecimalWeightedScore)
    assert result.score == Decimal("59.500")
    assert result.contributions == {
        "trend": Decimal("35.000"),
        "flow": Decimal("16.500"),
        "structure": Decimal("8.000"),
    }
    assert result.missing_components == ()


def test_boundary_delegates_to_the_authoritative_quant_owner() -> None:
    result = decimal_weighted_score(VALUES, WEIGHTS, component_ids=COMPONENT_IDS)
    owner = weighted_score(
        [float(VALUES[name]) for name in COMPONENT_IDS],
        {name: float(WEIGHTS[name]) for name in COMPONENT_IDS},
        component_names=COMPONENT_IDS,
    )

    assert float(result.score) == pytest.approx(owner.scores, abs=1e-12)
    for index, name in enumerate(COMPONENT_IDS):
        assert float(result.contributions[name]) == pytest.approx(
            owner.contributions[index],
            abs=1e-12,
        )


def test_contribution_scale_follows_the_exact_decimal_template() -> None:
    # weight scale 4 + value scale 2 -> contribution and score keep 6 places.
    result = decimal_weighted_score(
        {"trend": Decimal("70.00"), "flow": Decimal("55.00")},
        {"trend": Decimal("0.6667"), "flow": Decimal("0.3333")},
        component_ids=("trend", "flow"),
    )

    assert result.contributions["trend"] == Decimal("46.669000")
    assert result.contributions["flow"] == Decimal("18.331500")
    assert result.score == Decimal("65.000500")
    assert result.score.as_tuple().exponent == -6


def test_component_ids_control_the_evaluation_and_output_order() -> None:
    reversed_ids = tuple(reversed(COMPONENT_IDS))

    canonical = decimal_weighted_score(VALUES, WEIGHTS, component_ids=COMPONENT_IDS)
    permuted = decimal_weighted_score(VALUES, WEIGHTS, component_ids=reversed_ids)

    assert tuple(permuted.contributions) == reversed_ids
    assert permuted.contributions == canonical.contributions
    assert permuted.score == canonical.score


def test_missing_component_is_surfaced_and_never_zero_filled() -> None:
    values = dict(VALUES) | {"flow": None}

    result = decimal_weighted_score(values, WEIGHTS, component_ids=COMPONENT_IDS)

    assert result.score is None
    assert result.contributions["flow"] is None
    assert result.missing_components == ("flow",)
    # Present components still report their own exact contributions.
    assert result.contributions["trend"] == Decimal("35.000")
    assert result.contributions["structure"] == Decimal("8.000")


def test_missing_components_are_reported_in_component_id_order() -> None:
    values = {"trend": None, "flow": Decimal("55.00"), "structure": None}

    result = decimal_weighted_score(values, WEIGHTS, component_ids=COMPONENT_IDS)

    assert result.missing_components == ("trend", "structure")
    assert result.score is None


def test_all_missing_inputs_produce_a_fully_missing_result() -> None:
    values = dict.fromkeys(COMPONENT_IDS)

    result = decimal_weighted_score(values, WEIGHTS, component_ids=COMPONENT_IDS)

    assert result.score is None
    assert result.missing_components == COMPONENT_IDS
    assert set(result.contributions) == set(COMPONENT_IDS)
    assert all(value is None for value in result.contributions.values())


def test_a_zero_component_score_is_not_treated_as_missing() -> None:
    values = dict(VALUES) | {"flow": Decimal("0.00")}

    result = decimal_weighted_score(values, WEIGHTS, component_ids=COMPONENT_IDS)

    assert result.missing_components == ()
    assert result.contributions["flow"] == Decimal("0.000")
    assert result.score == Decimal("43.000")


@pytest.mark.parametrize(("composite", "weights"), sorted(V1_2_CONTRACTS.items()))
def test_every_v1_2_contract_satisfies_the_default_weight_sum_policy(
    composite: str,
    weights: dict[str, Decimal],
) -> None:
    component_ids = tuple(weights)
    values = {name: Decimal("50.00") for name in component_ids}

    result = decimal_weighted_score(values, weights, component_ids=component_ids)

    assert result.score is not None
    assert result.score == pytest.approx(Decimal("50"), abs=Decimal("0.001"))
    assert result.missing_components == ()


def test_weights_that_do_not_sum_to_one_are_rejected_by_default() -> None:
    broken = dict(WEIGHTS) | {"structure": Decimal("0.3")}

    with pytest.raises(NumericInputError, match="weights must sum to 1.0"):
        decimal_weighted_score(VALUES, broken, component_ids=COMPONENT_IDS)


def test_unconstrained_weight_totals_are_opt_in() -> None:
    unnormalized = {
        "trend": Decimal("2"),
        "flow": Decimal("1"),
        "structure": Decimal("1"),
    }

    result = decimal_weighted_score(
        VALUES,
        unnormalized,
        component_ids=COMPONENT_IDS,
        expected_weight_total=None,
    )

    assert result.score == Decimal("235")


def test_negative_weights_are_rejected_by_the_quant_owner() -> None:
    signed = {
        "trend": Decimal("1.2"),
        "flow": Decimal("-0.2"),
        "structure": Decimal("0"),
    }

    with pytest.raises(NumericInputError, match="weights must be non-negative"):
        decimal_weighted_score(VALUES, signed, component_ids=COMPONENT_IDS)


def test_unknown_component_id_fails_fast_instead_of_defaulting() -> None:
    with pytest.raises(KeyError):
        decimal_weighted_score(
            VALUES,
            WEIGHTS,
            component_ids=(*COMPONENT_IDS, "regime"),
        )


def test_empty_component_ids_are_rejected() -> None:
    with pytest.raises(NumericInputError):
        decimal_weighted_score({}, {}, component_ids=())


def test_repeated_calculation_is_deterministic() -> None:
    values = dict(VALUES) | {"structure": None}

    first = decimal_weighted_score(values, WEIGHTS, component_ids=COMPONENT_IDS)

    for _ in range(3):
        repeat = decimal_weighted_score(values, WEIGHTS, component_ids=COMPONENT_IDS)
        assert repeat == first


def test_inputs_and_weights_are_not_mutated() -> None:
    values = dict(VALUES)
    weights = dict(WEIGHTS)

    decimal_weighted_score(values, weights, component_ids=COMPONENT_IDS)

    assert values == VALUES
    assert weights == WEIGHTS


def test_decimal_bounded_linear_policy_version_is_frozen() -> None:
    assert DECIMAL_BOUNDED_LINEAR_POLICY_VERSION == "DECIMAL_BOUNDED_LINEAR_V1"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (Decimal("-1"), Decimal("0")),
        (Decimal("0"), Decimal("0")),
        (Decimal("1"), Decimal("50")),
        (Decimal("2"), Decimal("100")),
        (Decimal("3"), Decimal("100")),
    ],
)
def test_decimal_bounded_linear_clamps_and_interpolates_exactly(
    value: Decimal,
    expected: Decimal,
) -> None:
    result = decimal_bounded_linear(
        value,
        input_minimum=Decimal("0"),
        input_maximum=Decimal("2"),
        output_at_minimum=Decimal("0"),
        output_at_maximum=Decimal("100"),
    )

    assert result == expected
    assert float(result) == pytest.approx(
        bounded_linear(
            float(value),
            input_minimum=0.0,
            input_maximum=2.0,
            output_minimum=0.0,
            output_maximum=100.0,
        ),
        abs=1e-12,
    )


@pytest.mark.parametrize(
    ("minimum", "maximum"),
    [(Decimal("1"), Decimal("1")), (Decimal("2"), Decimal("1"))],
)
def test_decimal_bounded_linear_rejects_a_degenerate_interval(
    minimum: Decimal,
    maximum: Decimal,
) -> None:
    with pytest.raises(ValueError, match="input_minimum must be less than"):
        decimal_bounded_linear(
            Decimal("1"),
            input_minimum=minimum,
            input_maximum=maximum,
            output_at_minimum=Decimal("0"),
            output_at_maximum=Decimal("100"),
        )


@pytest.mark.parametrize("nan_value", [Decimal("NaN"), np.float64("nan")])
def test_nan_component_values_are_surfaced_as_missing_not_zero_filled(
    nan_value,
) -> None:
    # ``None`` is the wrappers' missing marker, but a NaN reaching the boundary
    # must degrade to the same explicit missing contract rather than
    # contributing zero to a persisted score.
    values = dict(VALUES) | {"flow": nan_value}

    result = decimal_weighted_score(values, WEIGHTS, component_ids=COMPONENT_IDS)

    assert result.score is None
    assert result.contributions["flow"] is None
    assert result.missing_components == ("flow",)
