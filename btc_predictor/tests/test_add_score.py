"""BTC-153 v1.2 Add Score tests."""

from dataclasses import replace
from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features.add import (
    ADD_SCORE_COMPONENT_IDS,
    ADD_SCORE_FEATURE_ID,
    ADD_SCORE_REASON_CODES,
    ADD_SCORE_VERSION,
    RISK_IMPROVEMENT_NORMALIZATION_VERSION,
    AddScoreBatchResult,
    AddScoreInput,
    AddScoreResult,
    RiskImprovementComponent,
    calculate_add_score,
    calculate_add_score_batch,
    risk_improvement_component_score,
)
from btc_predictor.features.hold import HOLD_SCORE_COMPONENT_IDS
from btc_predictor.features.scoring_contracts import SCORING_PARAMETER_STATUS
from btc_predictor.quant import NumericInputError


def complete_input() -> AddScoreInput:
    return AddScoreInput(
        new_structure_score=Decimal("90"),
        flow_score=Decimal("80"),
        positioning_score=Decimal("70"),
        momentum_score=Decimal("60"),
        risk_improvement_score=Decimal("50"),
    )


def test_add_score_contract_is_v1_2_and_excludes_hold_score() -> None:
    assert ADD_SCORE_FEATURE_ID == "ADD_SCORE"
    assert ADD_SCORE_VERSION == "ADD_SCORE_V1_2"
    assert ADD_SCORE_COMPONENT_IDS == (
        "new_structure",
        "flow",
        "positioning",
        "momentum",
        "risk_improvement",
    )
    # Rulebook 21: Hold Score is not nested inside Add Score, and neither is
    # Regime. Neither has a component, a field, or a weight route.
    assert "hold_score" not in ADD_SCORE_COMPONENT_IDS
    assert "regime" not in ADD_SCORE_COMPONENT_IDS
    record = complete_input().as_record()
    assert "hold_score" not in record
    assert "regime" not in record
    assert ADD_SCORE_REASON_CODES == (
        "ADD_SCORE_INPUT_MISSING",
        "ADD_SCORE_COMPLETE",
    )


def test_add_score_is_not_a_reweighting_of_hold_score() -> None:
    # Adding is a different judgement, not Hold with different numbers: Add
    # replaces Structure with NewStructure and drops Trend entirely.
    assert set(ADD_SCORE_COMPONENT_IDS) != set(HOLD_SCORE_COMPONENT_IDS)
    assert "trend" not in ADD_SCORE_COMPONENT_IDS
    assert "structure" not in ADD_SCORE_COMPONENT_IDS
    assert "new_structure" not in HOLD_SCORE_COMPONENT_IDS
    assert "risk_improvement" not in HOLD_SCORE_COMPONENT_IDS


def test_calculates_exact_v1_2_score_and_contributions_from_config() -> None:
    config = load_strategy_config()

    result = calculate_add_score(complete_input(), strategy_config=config)

    # 0.3125*90 + 0.25*80 + 0.1875*70 + 0.125*60 + 0.125*50
    assert isinstance(result, AddScoreResult)
    assert result.score == Decimal("75.0000")
    assert result.weights == {
        "new_structure": Decimal("0.3125"),
        "flow": Decimal("0.25"),
        "positioning": Decimal("0.1875"),
        "momentum": Decimal("0.125"),
        "risk_improvement": Decimal("0.125"),
    }
    assert sum(result.weights.values()) == Decimal("1.0000")
    assert result.contributions == {
        "new_structure": Decimal("28.1250"),
        "flow": Decimal("20.00"),
        "positioning": Decimal("13.1250"),
        "momentum": Decimal("7.500"),
        "risk_improvement": Decimal("6.250"),
    }
    assert result.complete is True
    assert result.reason_codes == ("ADD_SCORE_COMPLETE",)


def test_new_structure_is_the_heaviest_component() -> None:
    config = load_strategy_config()
    weights = calculate_add_score(
        complete_input(),
        strategy_config=config,
    ).weights

    # Rulebook 21: adding should be harder than holding, and new confirmed
    # structure is what earns it.
    assert max(weights, key=lambda key: weights[key]) == "new_structure"


def test_persisted_record_is_reconstructable_and_versioned() -> None:
    config = load_strategy_config()
    record = calculate_add_score(
        complete_input(),
        strategy_config=config,
    ).as_record()

    assert record == {
        "feature_id": "ADD_SCORE",
        "score_version": "ADD_SCORE_V1_2",
        "parameter_status": "PROVISIONAL_PENDING_BTC_185",
        "score": "75.0000",
        "inputs": {
            "new_structure": "90",
            "flow": "80",
            "positioning": "70",
            "momentum": "60",
            "risk_improvement": "50",
        },
        "weights": {
            "new_structure": "0.3125",
            "flow": "0.25",
            "positioning": "0.1875",
            "momentum": "0.125",
            "risk_improvement": "0.125",
        },
        "contributions": {
            "new_structure": "28.1250",
            "flow": "20.00",
            "positioning": "13.1250",
            "momentum": "7.500",
            "risk_improvement": "6.250",
        },
        "missing_components": [],
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": ["ADD_SCORE_COMPLETE"],
    }


@pytest.mark.parametrize(
    "field,component",
    [
        ("new_structure_score", "new_structure"),
        ("flow_score", "flow"),
        ("positioning_score", "positioning"),
        ("momentum_score", "momentum"),
        ("risk_improvement_score", "risk_improvement"),
    ],
)
def test_missing_input_is_surfaced_without_zero_fill(
    field: str,
    component: str,
) -> None:
    config = load_strategy_config()
    result = calculate_add_score(
        replace(complete_input(), **{field: None}),
        strategy_config=config,
    )
    record = result.as_record()

    # A missing component must never read as a zero-scoring one; that would
    # make an add look worse rather than unevaluable.
    assert result.score is None
    assert result.complete is False
    assert result.missing_components == (component,)
    assert result.contributions[component] is None
    assert result.reason_codes == ("ADD_SCORE_INPUT_MISSING",)
    assert record["inputs"][component] is None
    assert record["contributions"][component] is None


# --- risk improvement normalization --------------------------------------


def test_risk_improvement_component_is_the_share_of_risk_removed() -> None:
    component = risk_improvement_component_score(
        current_risk="10000",
        proposed_risk="6000",
    )

    assert isinstance(component, RiskImprovementComponent)
    assert component.normalization_version == "RISK_IMPROVEMENT_PROPORTIONAL_V1"
    assert component.improvement_fraction == Decimal("0.4")
    assert component.score == Decimal("40.0")
    assert component.worsened is False


@pytest.mark.parametrize(
    ("current", "proposed", "score"),
    [
        ("10000", "10000", Decimal("0")),
        ("10000", "0", Decimal("100")),
        ("10000", "2500", Decimal("75.00")),
    ],
)
def test_risk_improvement_spans_the_full_component_range(
    current: str,
    proposed: str,
    score: Decimal,
) -> None:
    component = risk_improvement_component_score(
        current_risk=current,
        proposed_risk=proposed,
    )

    assert component.score == score


def test_a_worsened_stop_scores_zero_but_reports_a_signed_delta() -> None:
    worsened = risk_improvement_component_score(
        current_risk="10000",
        proposed_risk="14000",
    )
    unchanged = risk_improvement_component_score(
        current_risk="10000",
        proposed_risk="10000",
    )

    # Both score zero, but only the signed value distinguishes them, which is
    # what rulebook 18's "stop can improve" requirement needs from BTC-154.
    assert worsened.score == Decimal("0")
    assert unchanged.score == Decimal("0")
    assert worsened.signed_improvement == Decimal("-4000.0")
    assert unchanged.signed_improvement == Decimal("0.0")
    assert worsened.worsened is True
    assert unchanged.worsened is False


def test_risk_improvement_matches_the_btc047_kernel() -> None:
    from btc_predictor.quant.risk import risk_improvement

    for current, proposed in (("10000", "6000"), ("8000", "8000"), ("5000", "9000")):
        component = risk_improvement_component_score(
            current_risk=current,
            proposed_risk=proposed,
        )
        expected = risk_improvement(
            float(current),
            float(proposed),
            floor_at_zero=False,
        )
        assert float(component.signed_improvement) == pytest.approx(expected)


def test_zero_current_risk_has_no_defined_proportion() -> None:
    component = risk_improvement_component_score(
        current_risk="0",
        proposed_risk="0",
    )

    # Nothing to remove is not a perfect improvement; the component is absent
    # and the Add Score becomes incomplete rather than silently maximal.
    assert component.improvement_fraction is None
    assert component.score is None


def test_an_absent_risk_improvement_component_makes_the_score_incomplete() -> None:
    config = load_strategy_config()
    component = risk_improvement_component_score(current_risk="0", proposed_risk="0")

    result = calculate_add_score(
        replace(complete_input(), risk_improvement_score=component.score),
        strategy_config=config,
    )

    assert result.complete is False
    assert result.missing_components == ("risk_improvement",)


def test_risk_improvement_component_record_is_persistable() -> None:
    record = risk_improvement_component_score(
        current_risk="10000",
        proposed_risk="6000",
    ).as_record()

    assert record == {
        "normalization_version": RISK_IMPROVEMENT_NORMALIZATION_VERSION,
        "current_risk": "10000",
        "proposed_risk": "6000",
        "signed_improvement": "4000.0",
        "improvement_fraction": "0.4",
        "score": "40.0",
        "worsened": False,
    }


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"current_risk": "-1", "proposed_risk": "0"}, "current_risk"),
        ({"current_risk": "0", "proposed_risk": "-1"}, "proposed_risk"),
        ({"current_risk": "abc", "proposed_risk": "0"}, "current_risk"),
        ({"current_risk": Decimal("NaN"), "proposed_risk": "0"}, "current_risk"),
    ],
)
def test_risk_improvement_inputs_fail_fast(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        risk_improvement_component_score(**kwargs)


# --- batch ---------------------------------------------------------------


def test_batch_and_single_row_scores_and_contributions_agree() -> None:
    config = load_strategy_config()
    generator = np.random.Generator(np.random.PCG64(153))
    values = generator.uniform(0, 100, size=(64, 5))

    batch = calculate_add_score_batch(values, strategy_config=config)
    singles = [
        calculate_add_score(
            AddScoreInput(
                new_structure_score=Decimal(str(row[0])),
                flow_score=Decimal(str(row[1])),
                positioning_score=Decimal(str(row[2])),
                momentum_score=Decimal(str(row[3])),
                risk_improvement_score=Decimal(str(row[4])),
            ),
            strategy_config=config,
        )
        for row in values
    ]

    assert isinstance(batch, AddScoreBatchResult)
    np.testing.assert_allclose(
        batch.scores,
        [float(result.score) for result in singles],
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_allclose(
        batch.contributions,
        [
            [float(result.contributions[name]) for name in ADD_SCORE_COMPONENT_IDS]
            for result in singles
        ],
        rtol=1e-12,
        atol=1e-12,
    )
    np.testing.assert_array_equal(batch.complete_mask, np.ones(64, dtype=np.bool_))
    assert batch.single_row is False


def test_batch_single_row_uses_same_contract_and_metadata() -> None:
    config = load_strategy_config()

    result = calculate_add_score_batch([90, 80, 70, 60, 50], strategy_config=config)

    assert result.scores == pytest.approx(75.0)
    np.testing.assert_allclose(
        result.contributions,
        [28.125, 20.0, 13.125, 7.5, 6.25],
    )
    assert result.score_version == "ADD_SCORE_V1_2"
    assert result.parameter_status == SCORING_PARAMETER_STATUS
    assert result.component_ids == ADD_SCORE_COMPONENT_IDS
    assert result.config_metadata == config.run_metadata()
    assert result.single_row is True


def test_batch_missing_inputs_retain_nan_masks() -> None:
    config = load_strategy_config()

    result = calculate_add_score_batch(
        [[90, 80, 70, 60, np.nan], [90, 80, 70, 60, 50]],
        strategy_config=config,
    )

    assert np.isnan(result.scores[0])
    assert result.scores[1] == pytest.approx(75.0)
    assert np.isnan(result.contributions[0, 4])
    np.testing.assert_array_equal(
        result.missing_mask,
        [
            [False, False, False, False, True],
            [False, False, False, False, False],
        ],
    )
    np.testing.assert_array_equal(result.complete_mask, [False, True])


def test_batch_prefix_is_unchanged_when_future_rows_are_appended() -> None:
    config = load_strategy_config()
    history = np.array(
        [[90, 80, 70, 60, 50], [65, 55, 75, 60, 80]],
        dtype=np.float64,
    )
    future = np.array([[10, 20, 30, 40, 50]], dtype=np.float64)

    before = calculate_add_score_batch(history, strategy_config=config)
    after = calculate_add_score_batch(
        np.vstack((history, future)),
        strategy_config=config,
    )

    np.testing.assert_array_equal(after.scores[: len(history)], before.scores)
    np.testing.assert_array_equal(
        after.contributions[: len(history)],
        before.contributions,
    )


# --- validation ----------------------------------------------------------


@pytest.mark.parametrize(
    "field,value",
    [
        ("new_structure_score", Decimal("-0.01")),
        ("flow_score", Decimal("100.01")),
        ("positioning_score", Decimal("NaN")),
        ("momentum_score", Decimal("Infinity")),
        ("risk_improvement_score", True),
    ],
)
def test_single_score_inputs_fail_fast(field: str, value) -> None:
    config = load_strategy_config()

    with pytest.raises(ValueError, match=field.removesuffix("_score")):
        calculate_add_score(
            replace(complete_input(), **{field: value}),
            strategy_config=config,
        )


@pytest.mark.parametrize(
    "values,match",
    [
        ([[90, 80, 70, 60, 101]], "between 0 and 100"),
        ([[90, 80, 70, -1, 50]], "between 0 and 100"),
        ([[90, 80, np.inf, 60, 50]], "infinite"),
        ([[90, 80, 70, 60]], "component count"),
    ],
)
def test_batch_inputs_fail_fast(values, match: str) -> None:
    config = load_strategy_config()

    with pytest.raises(NumericInputError, match=match):
        calculate_add_score_batch(values, strategy_config=config)


def test_non_input_types_are_rejected() -> None:
    config = load_strategy_config()

    with pytest.raises(TypeError, match="AddScoreInput"):
        calculate_add_score({"flow": 80}, strategy_config=config)
    with pytest.raises(TypeError, match="StrategyConfig"):
        calculate_add_score(complete_input(), strategy_config={"add_score": {}})


def test_result_validation_rejects_persistence_drift() -> None:
    config = load_strategy_config()
    result = calculate_add_score(complete_input(), strategy_config=config)

    with pytest.raises(ValueError, match="sum to score"):
        replace(
            result,
            contributions={**result.contributions, "flow": Decimal("20.5")},
        ).as_record()
    with pytest.raises(ValueError, match="reason_codes do not match"):
        replace(result, reason_codes=()).as_record()
    with pytest.raises(ValueError, match="score_version"):
        replace(result, score_version="ADD_SCORE_V1_1").as_record()
    with pytest.raises(ValueError, match="feature_id"):
        replace(result, feature_id="HOLD_SCORE").as_record()


def test_config_contract_rejects_weight_membership_or_total_drift() -> None:
    config = load_strategy_config()
    missing = dict(config.scoring_weights.add_score)
    missing.pop("risk_improvement")
    nested = dict(config.scoring_weights.add_score)
    nested["hold_score"] = 0.0
    wrong_total = dict(config.scoring_weights.add_score)
    wrong_total["flow"] = 0.30

    for weights, match in (
        (missing, "exactly match"),
        (nested, "exactly match"),
        (wrong_total, "sum to 1"),
    ):
        with pytest.raises(ValueError, match=match):
            calculate_add_score(
                complete_input(),
                strategy_config=replace(
                    config,
                    scoring_weights=replace(
                        config.scoring_weights,
                        add_score=weights,
                    ),
                ),
            )


# --- BTC-220: record identity, missingness, and metadata validation -------


def test_add_record_rejects_parameter_status_drift() -> None:
    result = calculate_add_score(
        complete_input(),
        strategy_config=load_strategy_config(),
    )

    with pytest.raises(ValueError, match="parameter_status must be"):
        replace(result, parameter_status="VALIDATED").as_record()


def test_add_record_rejects_a_contribution_set_that_is_not_the_contract() -> None:
    result = calculate_add_score(
        complete_input(),
        strategy_config=load_strategy_config(),
    )
    contributions = dict(result.contributions) | {"hold_score": Decimal("10")}

    with pytest.raises(
        ValueError,
        match="contributions must exactly match Add Score components",
    ):
        replace(result, contributions=contributions).as_record()


def test_add_record_rejects_missingness_or_completeness_drift() -> None:
    config = load_strategy_config()
    complete = calculate_add_score(complete_input(), strategy_config=config)
    incomplete = calculate_add_score(
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


def test_add_record_rejects_config_metadata_that_is_missing_or_blank() -> None:
    result = calculate_add_score(
        complete_input(),
        strategy_config=load_strategy_config(),
    )

    incomplete = dict(result.config_metadata)
    del incomplete["strategy_version"]
    with pytest.raises(ValueError, match="config_metadata missing"):
        replace(result, config_metadata=incomplete).as_record()

    blank = dict(result.config_metadata) | {"strategy_version": "\t"}
    with pytest.raises(
        ValueError,
        match="config_metadata.strategy_version must be a non-empty string",
    ):
        replace(result, config_metadata=blank).as_record()


def test_repeated_single_and_batch_calculation_is_deterministic() -> None:
    config = load_strategy_config()
    first = calculate_add_score(complete_input(), strategy_config=config)
    second = calculate_add_score(complete_input(), strategy_config=config)
    first_batch = calculate_add_score_batch(
        [[90, 80, 70, 60, 50]],
        strategy_config=config,
    )
    second_batch = calculate_add_score_batch(
        [[90, 80, 70, 60, 50]],
        strategy_config=config,
    )

    assert first.as_record() == second.as_record()
    np.testing.assert_array_equal(first_batch.scores, second_batch.scores)
    np.testing.assert_array_equal(
        first_batch.contributions,
        second_batch.contributions,
    )
