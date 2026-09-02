from dataclasses import replace
from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features.entry import (
    ENTRY_CONVICTION_COMPONENT_IDS,
    ENTRY_CONVICTION_FEATURE_ID,
    ENTRY_CONVICTION_REASON_CODES,
    ENTRY_CONVICTION_SCORE_VERSION,
    ENTRY_CONVICTION_WEIGHT_SUM_TOLERANCE,
    EntryConvictionBatchResult,
    EntryConvictionInput,
    EntryConvictionResult,
    calculate_entry_conviction,
    calculate_entry_conviction_batch,
)
from btc_predictor.features.scoring_contracts import SCORING_PARAMETER_STATUS
from btc_predictor.quant import NumericInputError


def complete_input() -> EntryConvictionInput:
    return EntryConvictionInput(
        trend_score=Decimal("80"),
        flow_score=Decimal("70"),
        positioning_score=Decimal("60"),
        volatility_score=Decimal("50"),
        structure_score=Decimal("90"),
    )


def test_entry_conviction_contract_is_v1_2_and_excludes_regime() -> None:
    assert ENTRY_CONVICTION_FEATURE_ID == "ENTRY_CONVICTION"
    assert ENTRY_CONVICTION_SCORE_VERSION == "ENTRY_CONVICTION_V1_2"
    assert ENTRY_CONVICTION_COMPONENT_IDS == (
        "trend",
        "flow",
        "positioning",
        "volatility",
        "structure",
    )
    assert "regime" not in ENTRY_CONVICTION_COMPONENT_IDS
    assert "regime" not in complete_input().as_record()
    assert ENTRY_CONVICTION_REASON_CODES == (
        "ENTRY_CONVICTION_INPUT_MISSING",
        "ENTRY_CONVICTION_COMPLETE",
    )


def test_calculates_exact_v1_2_score_and_contributions_from_config() -> None:
    config = load_strategy_config()

    result = calculate_entry_conviction(complete_input(), strategy_config=config)

    assert isinstance(result, EntryConvictionResult)
    assert result.score == Decimal("71.8750")
    assert result.weights == {
        "trend": Decimal("0.25"),
        "flow": Decimal("0.25"),
        "positioning": Decimal("0.1875"),
        "volatility": Decimal("0.125"),
        "structure": Decimal("0.1875"),
    }
    assert result.contributions == {
        "trend": Decimal("20.00"),
        "flow": Decimal("17.50"),
        "positioning": Decimal("11.2500"),
        "volatility": Decimal("6.250"),
        "structure": Decimal("16.8750"),
    }
    assert sum(result.contributions.values(), Decimal("0")) == result.score
    assert result.complete is True
    assert result.missing_components == ()
    assert result.reason_codes == ("ENTRY_CONVICTION_COMPLETE",)


def test_persisted_record_is_reconstructable_and_versioned() -> None:
    config = load_strategy_config()
    record = calculate_entry_conviction(
        complete_input(),
        strategy_config=config,
    ).as_record()

    assert record == {
        "feature_id": "ENTRY_CONVICTION",
        "score_version": "ENTRY_CONVICTION_V1_2",
        "parameter_status": "PROVISIONAL_PENDING_BTC_185",
        "score": "71.8750",
        "inputs": {
            "trend": "80",
            "flow": "70",
            "positioning": "60",
            "volatility": "50",
            "structure": "90",
        },
        "weights": {
            "trend": "0.25",
            "flow": "0.25",
            "positioning": "0.1875",
            "volatility": "0.125",
            "structure": "0.1875",
        },
        "contributions": {
            "trend": "20.00",
            "flow": "17.50",
            "positioning": "11.2500",
            "volatility": "6.250",
            "structure": "16.8750",
        },
        "missing_components": [],
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": ["ENTRY_CONVICTION_COMPLETE"],
    }


def test_missing_input_is_surfaced_without_zero_fill() -> None:
    config = load_strategy_config()
    inputs = replace(complete_input(), flow_score=None)

    result = calculate_entry_conviction(inputs, strategy_config=config)
    record = result.as_record()

    assert result.score is None
    assert result.complete is False
    assert result.missing_components == ("flow",)
    assert result.contributions == {
        "trend": Decimal("20.00"),
        "flow": None,
        "positioning": Decimal("11.2500"),
        "volatility": Decimal("6.250"),
        "structure": Decimal("16.8750"),
    }
    assert result.reason_codes == ("ENTRY_CONVICTION_INPUT_MISSING",)
    assert record["inputs"]["flow"] is None
    assert record["contributions"]["flow"] is None


def test_batch_and_single_row_scores_and_contributions_agree() -> None:
    config = load_strategy_config()
    generator = np.random.Generator(np.random.PCG64(130))
    values = generator.uniform(0, 100, size=(64, 5))

    batch = calculate_entry_conviction_batch(values, strategy_config=config)
    singles = [
        calculate_entry_conviction(
            EntryConvictionInput(
                trend_score=Decimal(str(row[0])),
                flow_score=Decimal(str(row[1])),
                positioning_score=Decimal(str(row[2])),
                volatility_score=Decimal(str(row[3])),
                structure_score=Decimal(str(row[4])),
            ),
            strategy_config=config,
        )
        for row in values
    ]

    assert isinstance(batch, EntryConvictionBatchResult)
    np.testing.assert_allclose(
        batch.scores,
        [float(result.score) for result in singles],
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        batch.contributions,
        [
            [float(result.contributions[name]) for name in ENTRY_CONVICTION_COMPONENT_IDS]
            for result in singles
        ],
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_array_equal(batch.complete_mask, np.ones(64, dtype=np.bool_))
    assert batch.single_row is False


def test_batch_single_row_uses_the_same_contract_and_metadata() -> None:
    config = load_strategy_config()

    result = calculate_entry_conviction_batch(
        [80, 70, 60, 50, 90],
        strategy_config=config,
    )

    assert result.scores == 71.875
    np.testing.assert_array_equal(
        result.contributions,
        [20, 17.5, 11.25, 6.25, 16.875],
    )
    assert result.score_version == "ENTRY_CONVICTION_V1_2"
    assert result.parameter_status == SCORING_PARAMETER_STATUS
    assert result.component_ids == ENTRY_CONVICTION_COMPONENT_IDS
    assert result.config_metadata == config.run_metadata()
    assert result.single_row is True


def test_batch_missing_inputs_retain_nan_masks() -> None:
    config = load_strategy_config()
    result = calculate_entry_conviction_batch(
        [[80, np.nan, 60, 50, 90], [80, 70, 60, 50, 90]],
        strategy_config=config,
    )

    assert np.isnan(result.scores[0])
    assert result.scores[1] == 71.875
    assert np.isnan(result.contributions[0, 1])
    np.testing.assert_array_equal(
        result.missing_mask,
        [
            [False, True, False, False, False],
            [False, False, False, False, False],
        ],
    )
    np.testing.assert_array_equal(result.complete_mask, [False, True])


@pytest.mark.parametrize(
    "field,value",
    [
        ("trend_score", Decimal("-0.01")),
        ("flow_score", Decimal("100.01")),
        ("positioning_score", Decimal("NaN")),
        ("volatility_score", Decimal("Infinity")),
        ("structure_score", True),
    ],
)
def test_single_score_inputs_fail_fast(field: str, value) -> None:
    config = load_strategy_config()

    with pytest.raises(ValueError, match=field.removesuffix("_score")):
        calculate_entry_conviction(
            replace(complete_input(), **{field: value}),
            strategy_config=config,
        )


@pytest.mark.parametrize(
    "values,match",
    [
        ([[80, 70, 60, 50, 101]], "between 0 and 100"),
        ([[80, 70, 60, -1, 90]], "between 0 and 100"),
        ([[80, 70, np.inf, 50, 90]], "infinite"),
        ([[80, 70, 60, 50]], "component count"),
    ],
)
def test_batch_inputs_fail_fast(values, match: str) -> None:
    config = load_strategy_config()

    with pytest.raises(NumericInputError, match=match):
        calculate_entry_conviction_batch(values, strategy_config=config)


def test_result_validation_rejects_contribution_drift() -> None:
    config = load_strategy_config()
    result = calculate_entry_conviction(complete_input(), strategy_config=config)
    broken = replace(
        result,
        contributions={**result.contributions, "trend": Decimal("19")},
    )

    with pytest.raises(ValueError, match="sum to score"):
        broken.as_record()


def test_result_validation_rejects_contribution_missingness_drift() -> None:
    config = load_strategy_config()
    result = calculate_entry_conviction(complete_input(), strategy_config=config)
    broken = replace(
        result,
        contributions={**result.contributions, "flow": None},
    )

    with pytest.raises(ValueError, match="contributions do not match"):
        broken.as_record()


def test_result_validation_rejects_reason_code_drift() -> None:
    config = load_strategy_config()
    result = calculate_entry_conviction(complete_input(), strategy_config=config)

    with pytest.raises(ValueError, match="reason_codes do not match"):
        replace(result, reason_codes=()).as_record()


# --- BTC-220: persisted-record and weight-contract validation -------------


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("feature_id", "ENTRY", "feature_id must be ENTRY_CONVICTION"),
        ("score_version", "ENTRY_CONVICTION_V1_1", "score_version must be"),
        ("parameter_status", "VALIDATED", "parameter_status must be"),
    ],
)
def test_record_rejects_identity_or_version_drift(field, value, match) -> None:
    result = calculate_entry_conviction(
        complete_input(),
        strategy_config=load_strategy_config(),
    )

    with pytest.raises(ValueError, match=match):
        replace(result, **{field: value}).as_record()


def test_record_rejects_a_contribution_component_set_that_is_not_the_contract() -> None:
    result = calculate_entry_conviction(
        complete_input(),
        strategy_config=load_strategy_config(),
    )
    contributions = dict(result.contributions)
    contributions["regime"] = Decimal("10")

    with pytest.raises(
        ValueError,
        match="contributions must exactly match Entry Conviction components",
    ):
        replace(result, contributions=contributions).as_record()


def test_record_rejects_config_metadata_that_is_missing_or_blank() -> None:
    result = calculate_entry_conviction(
        complete_input(),
        strategy_config=load_strategy_config(),
    )

    incomplete = dict(result.config_metadata)
    del incomplete["parameter_set_id"]
    with pytest.raises(ValueError, match="config_metadata missing"):
        replace(result, config_metadata=incomplete).as_record()

    blank = dict(result.config_metadata) | {"strategy_version": "   "}
    with pytest.raises(
        ValueError,
        match="config_metadata.strategy_version must be a non-empty string",
    ):
        replace(result, config_metadata=blank).as_record()


def test_record_rejects_missingness_or_completeness_drift() -> None:
    config = load_strategy_config()
    complete = calculate_entry_conviction(complete_input(), strategy_config=config)
    incomplete = calculate_entry_conviction(
        replace(complete_input(), flow_score=None),
        strategy_config=config,
    )

    with pytest.raises(ValueError, match="missing_components do not match"):
        replace(complete, missing_components=("flow",)).as_record()
    with pytest.raises(ValueError, match="contributions do not match"):
        replace(
            incomplete,
            contributions={**incomplete.contributions, "flow": Decimal("0")},
        ).as_record()
    with pytest.raises(ValueError, match="complete state does not match"):
        replace(incomplete, complete=True).as_record()


def _config_with_entry_weights(weights: dict[str, Decimal]):
    default = load_strategy_config()
    return replace(
        default,
        scoring_weights=replace(default.scoring_weights, entry_conviction=weights),
    )


def test_weights_must_be_exactly_the_v1_2_component_set() -> None:
    with pytest.raises(ValueError, match="must exactly match"):
        calculate_entry_conviction(
            complete_input(),
            strategy_config=_config_with_entry_weights({"trend": Decimal("1")}),
        )


def test_weights_must_sum_to_one_within_the_declared_tolerance() -> None:
    default = load_strategy_config()
    inflated = dict(default.scoring_weights.entry_conviction) | {
        "trend": Decimal("0.5"),
    }

    with pytest.raises(
        ValueError,
        match="Entry Conviction weights must sum to 1",
    ):
        calculate_entry_conviction(
            complete_input(),
            strategy_config=_config_with_entry_weights(inflated),
        )


def test_weight_sum_tolerance_admits_only_negligible_rounding() -> None:
    default = load_strategy_config()
    inside = dict(default.scoring_weights.entry_conviction)
    inside["trend"] = (
        Decimal(str(inside["trend"])) + ENTRY_CONVICTION_WEIGHT_SUM_TOLERANCE
    )
    outside = dict(default.scoring_weights.entry_conviction)
    outside["trend"] = (
        Decimal(str(outside["trend"])) + ENTRY_CONVICTION_WEIGHT_SUM_TOLERANCE * 10
    )

    accepted = calculate_entry_conviction(
        complete_input(),
        strategy_config=_config_with_entry_weights(inside),
    )
    assert accepted.score is not None

    with pytest.raises(ValueError, match="must sum to 1"):
        calculate_entry_conviction(
            complete_input(),
            strategy_config=_config_with_entry_weights(outside),
        )


def test_negative_weights_are_rejected() -> None:
    default = load_strategy_config()
    signed = dict(default.scoring_weights.entry_conviction)
    signed["trend"] = Decimal("-0.25")
    signed["flow"] = Decimal("0.75")

    with pytest.raises(ValueError, match="trend must be non-negative"):
        calculate_entry_conviction(
            complete_input(),
            strategy_config=_config_with_entry_weights(signed),
        )


@pytest.mark.parametrize(
    ("weight", "match"),
    [
        (True, "trend must be numeric"),
        ("abc", "trend must be numeric"),
        (Decimal("NaN"), "trend must be finite"),
    ],
)
def test_non_numeric_or_non_finite_weights_are_rejected(weight, match) -> None:
    default = load_strategy_config()
    broken = dict(default.scoring_weights.entry_conviction) | {"trend": weight}

    with pytest.raises(ValueError, match=match):
        calculate_entry_conviction(
            complete_input(),
            strategy_config=_config_with_entry_weights(broken),
        )


def test_calculation_requires_the_declared_input_and_config_types() -> None:
    with pytest.raises(TypeError, match="inputs must be an EntryConvictionInput"):
        calculate_entry_conviction(
            {"trend_score": Decimal("50")},
            strategy_config=load_strategy_config(),
        )
    with pytest.raises(TypeError, match="strategy_config must be a StrategyConfig"):
        calculate_entry_conviction(complete_input(), strategy_config=object())


def test_repeated_single_and_batch_calculation_is_deterministic() -> None:
    config = load_strategy_config()
    first = calculate_entry_conviction(complete_input(), strategy_config=config)
    second = calculate_entry_conviction(complete_input(), strategy_config=config)
    first_batch = calculate_entry_conviction_batch(
        [[80, 70, 60, 50, 90]],
        strategy_config=config,
    )
    second_batch = calculate_entry_conviction_batch(
        [[80, 70, 60, 50, 90]],
        strategy_config=config,
    )

    assert first.as_record() == second.as_record()
    np.testing.assert_array_equal(first_batch.scores, second_batch.scores)
    np.testing.assert_array_equal(
        first_batch.contributions,
        second_batch.contributions,
    )
