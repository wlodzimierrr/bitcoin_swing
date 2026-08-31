"""BTC-152 v1.2 Hold Score tests."""

from dataclasses import replace
from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features.hold import (
    HOLD_SCORE_COMPONENT_IDS,
    HOLD_SCORE_FEATURE_ID,
    HOLD_SCORE_REASON_CODES,
    HOLD_SCORE_VERSION,
    HoldScoreBatchResult,
    HoldScoreInput,
    HoldScoreResult,
    calculate_hold_score,
    calculate_hold_score_batch,
)
from btc_predictor.features.scoring_contracts import SCORING_PARAMETER_STATUS
from btc_predictor.quant import NumericInputError


def complete_input() -> HoldScoreInput:
    return HoldScoreInput(
        trend_score=Decimal("80"),
        flow_score=Decimal("70"),
        positioning_score=Decimal("60"),
        structure_score=Decimal("90"),
        momentum_persistence_score=Decimal("50"),
    )


def test_hold_score_contract_is_v1_2_and_excludes_regime() -> None:
    assert HOLD_SCORE_FEATURE_ID == "HOLD_SCORE"
    assert HOLD_SCORE_VERSION == "HOLD_SCORE_V1_2"
    assert HOLD_SCORE_COMPONENT_IDS == (
        "trend",
        "flow",
        "positioning",
        "structure",
        "momentum_persistence",
    )
    assert "regime" not in HOLD_SCORE_COMPONENT_IDS
    assert "regime" not in complete_input().as_record()
    assert HOLD_SCORE_REASON_CODES == (
        "HOLD_SCORE_INPUT_MISSING",
        "HOLD_SCORE_COMPLETE",
    )


def test_calculates_exact_v1_2_score_and_contributions_from_config() -> None:
    config = load_strategy_config()

    result = calculate_hold_score(complete_input(), strategy_config=config)

    assert isinstance(result, HoldScoreResult)
    assert result.score == Decimal("70.6666670")
    assert result.weights == {
        "trend": Decimal("0.2666667"),
        "flow": Decimal("0.2666667"),
        "positioning": Decimal("0.2"),
        "structure": Decimal("0.1333333"),
        "momentum_persistence": Decimal("0.1333333"),
    }
    assert result.contributions == {
        "trend": Decimal("21.3333360"),
        "flow": Decimal("18.6666690"),
        "positioning": Decimal("12.0"),
        "structure": Decimal("11.9999970"),
        "momentum_persistence": Decimal("6.6666650"),
    }
    assert sum(result.contributions.values(), Decimal("0")) == result.score
    assert result.complete is True
    assert result.missing_components == ()
    assert result.reason_codes == ("HOLD_SCORE_COMPLETE",)


def test_persisted_record_is_reconstructable_and_versioned() -> None:
    config = load_strategy_config()
    record = calculate_hold_score(
        complete_input(),
        strategy_config=config,
    ).as_record()

    assert record == {
        "feature_id": "HOLD_SCORE",
        "score_version": "HOLD_SCORE_V1_2",
        "parameter_status": "PROVISIONAL_PENDING_BTC_185",
        "score": "70.6666670",
        "inputs": {
            "trend": "80",
            "flow": "70",
            "positioning": "60",
            "structure": "90",
            "momentum_persistence": "50",
        },
        "weights": {
            "trend": "0.2666667",
            "flow": "0.2666667",
            "positioning": "0.2",
            "structure": "0.1333333",
            "momentum_persistence": "0.1333333",
        },
        "contributions": {
            "trend": "21.3333360",
            "flow": "18.6666690",
            "positioning": "12.0",
            "structure": "11.9999970",
            "momentum_persistence": "6.6666650",
        },
        "missing_components": [],
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": ["HOLD_SCORE_COMPLETE"],
    }


@pytest.mark.parametrize(
    "field,component",
    [
        ("trend_score", "trend"),
        ("flow_score", "flow"),
        ("positioning_score", "positioning"),
        ("structure_score", "structure"),
        ("momentum_persistence_score", "momentum_persistence"),
    ],
)
def test_missing_input_is_surfaced_without_zero_fill(
    field: str,
    component: str,
) -> None:
    config = load_strategy_config()
    result = calculate_hold_score(
        replace(complete_input(), **{field: None}),
        strategy_config=config,
    )
    record = result.as_record()

    assert result.score is None
    assert result.complete is False
    assert result.missing_components == (component,)
    assert result.contributions[component] is None
    assert result.reason_codes == ("HOLD_SCORE_INPUT_MISSING",)
    assert record["inputs"][component] is None
    assert record["contributions"][component] is None


def test_batch_and_single_row_scores_and_contributions_agree() -> None:
    config = load_strategy_config()
    generator = np.random.Generator(np.random.PCG64(152))
    values = generator.uniform(0, 100, size=(64, 5))

    batch = calculate_hold_score_batch(values, strategy_config=config)
    singles = [
        calculate_hold_score(
            HoldScoreInput(
                trend_score=Decimal(str(row[0])),
                flow_score=Decimal(str(row[1])),
                positioning_score=Decimal(str(row[2])),
                structure_score=Decimal(str(row[3])),
                momentum_persistence_score=Decimal(str(row[4])),
            ),
            strategy_config=config,
        )
        for row in values
    ]

    assert isinstance(batch, HoldScoreBatchResult)
    np.testing.assert_allclose(
        batch.scores,
        [float(result.score) for result in singles],
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        batch.contributions,
        [
            [float(result.contributions[name]) for name in HOLD_SCORE_COMPONENT_IDS]
            for result in singles
        ],
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_array_equal(batch.complete_mask, np.ones(64, dtype=np.bool_))
    assert batch.single_row is False


def test_batch_single_row_uses_same_contract_and_metadata() -> None:
    config = load_strategy_config()

    result = calculate_hold_score_batch(
        [80, 70, 60, 90, 50],
        strategy_config=config,
    )

    assert result.scores == pytest.approx(70.666667)
    np.testing.assert_allclose(
        result.contributions,
        [21.333336, 18.666669, 12, 11.999997, 6.666665],
    )
    assert result.score_version == "HOLD_SCORE_V1_2"
    assert result.parameter_status == SCORING_PARAMETER_STATUS
    assert result.component_ids == HOLD_SCORE_COMPONENT_IDS
    assert result.config_metadata == config.run_metadata()
    assert result.single_row is True


def test_batch_missing_inputs_retain_nan_masks() -> None:
    config = load_strategy_config()
    result = calculate_hold_score_batch(
        [[80, 70, 60, 90, np.nan], [80, 70, 60, 90, 50]],
        strategy_config=config,
    )

    assert np.isnan(result.scores[0])
    assert result.scores[1] == pytest.approx(70.666667)
    assert np.isnan(result.contributions[0, 4])
    np.testing.assert_array_equal(
        result.missing_mask,
        [
            [False, False, False, False, True],
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
        ("structure_score", Decimal("Infinity")),
        ("momentum_persistence_score", True),
    ],
)
def test_single_score_inputs_fail_fast(field: str, value) -> None:
    config = load_strategy_config()

    with pytest.raises(ValueError, match=field.removesuffix("_score")):
        calculate_hold_score(
            replace(complete_input(), **{field: value}),
            strategy_config=config,
        )


@pytest.mark.parametrize(
    "values,match",
    [
        ([[80, 70, 60, 90, 101]], "between 0 and 100"),
        ([[80, 70, 60, -1, 50]], "between 0 and 100"),
        ([[80, 70, np.inf, 90, 50]], "infinite"),
        ([[80, 70, 60, 90]], "component count"),
    ],
)
def test_batch_inputs_fail_fast(values, match: str) -> None:
    config = load_strategy_config()

    with pytest.raises(NumericInputError, match=match):
        calculate_hold_score_batch(values, strategy_config=config)


def test_result_validation_rejects_persistence_drift() -> None:
    config = load_strategy_config()
    result = calculate_hold_score(complete_input(), strategy_config=config)

    with pytest.raises(ValueError, match="sum to score"):
        replace(
            result,
            contributions={**result.contributions, "trend": Decimal("20")},
        ).as_record()
    with pytest.raises(ValueError, match="reason_codes do not match"):
        replace(result, reason_codes=()).as_record()
    with pytest.raises(ValueError, match="score_version"):
        replace(result, score_version="HOLD_SCORE_V1_1").as_record()


def test_config_contract_rejects_weight_membership_or_total_drift() -> None:
    config = load_strategy_config()
    missing = dict(config.scoring_weights.hold_score)
    missing.pop("structure")
    wrong_total = dict(config.scoring_weights.hold_score)
    wrong_total["trend"] = 0.20

    with pytest.raises(ValueError, match="exactly match"):
        calculate_hold_score(
            complete_input(),
            strategy_config=replace(
                config,
                scoring_weights=replace(
                    config.scoring_weights,
                    hold_score=missing,
                ),
            ),
        )
    with pytest.raises(ValueError, match="sum to 1"):
        calculate_hold_score(
            complete_input(),
            strategy_config=replace(
                config,
                scoring_weights=replace(
                    config.scoring_weights,
                    hold_score=wrong_total,
                ),
            ),
        )


def test_batch_prefix_is_unchanged_when_future_rows_are_appended() -> None:
    config = load_strategy_config()
    history = np.array(
        [[80, 70, 60, 90, 50], [65, 55, 75, 60, 80]],
        dtype=np.float64,
    )
    future = np.array([[10, 20, 30, 40, 50]], dtype=np.float64)

    before = calculate_hold_score_batch(history, strategy_config=config)
    after = calculate_hold_score_batch(
        np.vstack((history, future)),
        strategy_config=config,
    )

    np.testing.assert_array_equal(after.scores[: len(history)], before.scores)
    np.testing.assert_array_equal(
        after.contributions[: len(history)],
        before.contributions,
    )


def test_repeated_single_and_batch_calculation_is_deterministic() -> None:
    config = load_strategy_config()
    first = calculate_hold_score(complete_input(), strategy_config=config)
    second = calculate_hold_score(complete_input(), strategy_config=config)
    first_batch = calculate_hold_score_batch(
        [[80, 70, 60, 90, 50]],
        strategy_config=config,
    )
    second_batch = calculate_hold_score_batch(
        [[80, 70, 60, 90, 50]],
        strategy_config=config,
    )

    assert first.as_record() == second.as_record()
    np.testing.assert_array_equal(first_batch.scores, second_batch.scores)
    np.testing.assert_array_equal(
        first_batch.contributions,
        second_batch.contributions,
    )
