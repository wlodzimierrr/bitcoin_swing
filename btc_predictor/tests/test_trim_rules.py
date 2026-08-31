"""BTC-157 partial-reduction policy tests."""

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features import (
    CrowdingFlagInput,
    EuphoriaFlagInput,
    FlowScoreInput,
    HoldScoreInput,
    calculate_crowding_flag,
    calculate_euphoria_flag,
    calculate_flow_score,
    calculate_hold_score,
)
from btc_predictor.portfolio import (
    ENTER,
    PENDING_ENTRY,
    apply_position_event,
    start_position_lifecycle,
)
from btc_predictor.signals.trim import (
    TRIM_ACTION,
    TRIM_EFFECTS,
    TRIM_REASON_CODES,
    TRIM_RULE_INPUT_IDS,
    TRIM_RULES_PARAMETER_STATUS,
    TRIM_RULES_POLICY_VERSION,
    TRIM_SIGNAL_FEATURE_ID,
    TrimRuleInput,
    TrimSignalResult,
    evaluate_trim_rules,
    flow_score_is_deteriorating,
    trim_rules_from_results,
)


NOW = datetime(2026, 8, 31, tzinfo=timezone.utc)


def neutral_input(**overrides) -> TrimRuleInput:
    base = TrimRuleInput(
        position_open=True,
        hold_score=Decimal("70"),
        euphoria_active=False,
        crowding_active=False,
        current_flow_score=Decimal("60"),
        prior_flow_score=Decimal("60"),
    )
    return replace(base, **overrides) if overrides else base


def test_contract_is_stable_and_partial_only() -> None:
    assert TRIM_SIGNAL_FEATURE_ID == "TRIM_SIGNAL"
    assert TRIM_RULES_POLICY_VERSION == "TRIM_RULES_V1"
    assert TRIM_RULES_PARAMETER_STATUS == "PROVISIONAL_PENDING_BTC_185"
    assert TRIM_ACTION == "TRIM"
    assert TRIM_EFFECTS == ("PARTIAL_REDUCTION",)
    assert TRIM_RULE_INPUT_IDS == (
        "position_open",
        "hold_score",
        "euphoria_active",
        "crowding_active",
        "current_flow_score",
        "prior_flow_score",
    )
    assert "EXIT" not in TRIM_EFFECTS
    assert TRIM_REASON_CODES == (
        "TRIM_INPUT_MISSING",
        "TRIM_NO_OPEN_POSITION",
        "TRIM_SUPPRESSED_EXIT_BAND",
        "TRIM_HOLD_SCORE_BAND",
        "TRIM_EUPHORIA_ACTIVE",
        "TRIM_CROWDING_ACTIVE",
        "TRIM_FLOW_DETERIORATION",
        "TRIM_NOT_TRIGGERED",
    )


@pytest.mark.parametrize(
    ("score", "expected_signal", "expected_reason"),
    [
        ("39.99", False, "TRIM_SUPPRESSED_EXIT_BAND"),
        ("40", True, "TRIM_HOLD_SCORE_BAND"),
        ("49.99", True, "TRIM_HOLD_SCORE_BAND"),
        ("50", False, "TRIM_NOT_TRIGGERED"),
        ("70", False, "TRIM_NOT_TRIGGERED"),
    ],
)
def test_hold_score_bands_follow_versioned_config(
    score: str,
    expected_signal: bool,
    expected_reason: str,
) -> None:
    result = evaluate_trim_rules(
        neutral_input(hold_score=Decimal(score)),
        strategy_config=load_strategy_config(),
    )

    assert result.signal is expected_signal
    assert result.reason_codes == (expected_reason,)
    assert result.action == ("TRIM" if expected_signal else None)
    assert result.partial_reduction is expected_signal


@pytest.mark.parametrize(
    ("override", "reason"),
    [
        ({"euphoria_active": True}, "TRIM_EUPHORIA_ACTIVE"),
        ({"crowding_active": True}, "TRIM_CROWDING_ACTIVE"),
        (
            {"current_flow_score": Decimal("59"), "prior_flow_score": Decimal("60")},
            "TRIM_FLOW_DETERIORATION",
        ),
    ],
)
def test_each_context_trigger_can_emit_trim_independently(
    override: dict,
    reason: str,
) -> None:
    result = evaluate_trim_rules(
        neutral_input(**override),
        strategy_config=load_strategy_config(),
    )

    assert result.signal is True
    assert result.action == "TRIM"
    assert result.effects == ("PARTIAL_REDUCTION",)
    assert result.reason_codes == (reason,)


def test_all_trigger_reasons_are_retained_in_stable_order() -> None:
    result = evaluate_trim_rules(
        neutral_input(
            hold_score=Decimal("45"),
            euphoria_active=True,
            crowding_active=True,
            current_flow_score=Decimal("50"),
            prior_flow_score=Decimal("60"),
        ),
        strategy_config=load_strategy_config(),
    )

    assert result.reason_codes == (
        "TRIM_HOLD_SCORE_BAND",
        "TRIM_EUPHORIA_ACTIVE",
        "TRIM_CROWDING_ACTIVE",
        "TRIM_FLOW_DETERIORATION",
    )


def test_exit_band_suppresses_trim_even_when_every_context_trigger_is_active() -> None:
    result = evaluate_trim_rules(
        neutral_input(
            hold_score=Decimal("30"),
            euphoria_active=True,
            crowding_active=True,
            current_flow_score=Decimal("40"),
            prior_flow_score=Decimal("60"),
        ),
        strategy_config=load_strategy_config(),
    )

    assert result.signal is False
    assert result.action is None
    assert result.effects == ()
    assert result.exit_precedence is True
    assert result.reason_codes == ("TRIM_SUPPRESSED_EXIT_BAND",)


def test_no_open_position_suppresses_otherwise_valid_trim() -> None:
    result = evaluate_trim_rules(
        neutral_input(position_open=False, hold_score=Decimal("45")),
        strategy_config=load_strategy_config(),
    )

    assert result.signal is False
    assert result.action is None
    assert result.reason_codes == ("TRIM_NO_OPEN_POSITION",)


def test_missing_evidence_is_surfaced_without_erasing_known_risk_reduction() -> None:
    result = evaluate_trim_rules(
        neutral_input(
            euphoria_active=True,
            crowding_active=None,
            current_flow_score=None,
        ),
        strategy_config=load_strategy_config(),
    )

    assert result.signal is True
    assert result.complete is False
    assert result.missing_inputs == ("crowding_active", "current_flow_score")
    assert result.reason_codes == (
        "TRIM_INPUT_MISSING",
        "TRIM_EUPHORIA_ACTIVE",
    )


def test_missing_evidence_never_becomes_a_false_clear_signal() -> None:
    result = evaluate_trim_rules(
        neutral_input(euphoria_active=None),
        strategy_config=load_strategy_config(),
    )

    assert result.signal is False
    assert result.complete is False
    assert result.action is None
    assert result.reason_codes == ("TRIM_INPUT_MISSING",)


def test_flow_deterioration_uses_shared_decision_tolerance() -> None:
    assert flow_score_is_deteriorating(
        current_flow_score="59",
        prior_flow_score="60",
    ) is True
    assert flow_score_is_deteriorating(
        current_flow_score="60",
        prior_flow_score="60",
    ) is False
    assert flow_score_is_deteriorating(
        current_flow_score="59.999999999999",
        prior_flow_score="60",
    ) is False


def test_record_persists_decision_inputs_thresholds_reasons_and_config() -> None:
    inputs = neutral_input(
        hold_score=Decimal("45"),
        source_reason_codes={
            "hold_score": ("HOLD_SCORE_COMPLETE",),
            "euphoria": (),
        },
    )
    result = evaluate_trim_rules(inputs, strategy_config=load_strategy_config())

    assert result.as_record() == {
        "feature_id": "TRIM_SIGNAL",
        "policy_version": "TRIM_RULES_V1",
        "parameter_status": "PROVISIONAL_PENDING_BTC_185",
        "inputs": {
            "position_open": True,
            "hold_score": "45",
            "euphoria_active": False,
            "crowding_active": False,
            "current_flow_score": "60",
            "prior_flow_score": "60",
            "source_reason_codes": {
                "hold_score": ["HOLD_SCORE_COMPLETE"],
                "euphoria": [],
            },
        },
        "trim_minimum": "40.0",
        "defensive_minimum": "50.0",
        "exit_below": "40.0",
        "signal": True,
        "action": "TRIM",
        "partial_reduction": True,
        "effects": ["PARTIAL_REDUCTION"],
        "exit_precedence": False,
        "missing_inputs": [],
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": ["TRIM_HOLD_SCORE_BAND"],
    }


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("position_open", "yes", "position_open"),
        ("hold_score", Decimal("101"), "hold_score"),
        ("current_flow_score", Decimal("NaN"), "current_flow_score"),
        ("prior_flow_score", True, "prior_flow_score"),
    ],
)
def test_invalid_inputs_fail_fast(field: str, value, match: str) -> None:
    with pytest.raises((TypeError, ValueError), match=match):
        evaluate_trim_rules(
            neutral_input(**{field: value}),
            strategy_config=load_strategy_config(),
        )


def test_persistence_validation_rejects_decision_drift() -> None:
    result = evaluate_trim_rules(
        neutral_input(hold_score=Decimal("45")),
        strategy_config=load_strategy_config(),
    )

    with pytest.raises(ValueError, match="signal does not match"):
        replace(result, signal=False).as_record()
    with pytest.raises(ValueError, match="action does not match"):
        replace(result, action=None).as_record()
    with pytest.raises(ValueError, match="reason_codes do not match"):
        replace(result, reason_codes=()).as_record()


def open_lifecycle(config):
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        state=PENDING_ENTRY,
        config_metadata=config.run_metadata(),
    )
    return apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=NOW,
        quantity="1",
        price="100",
        stop_price="90",
    )


def hold_result(config, score: str = "80"):
    value = Decimal(score)
    return calculate_hold_score(
        HoldScoreInput(value, value, value, value, value),
        strategy_config=config,
    )


def euphoria_result(config, *, flagged: bool = False):
    inputs = EuphoriaFlagInput(
        range_percentile=Decimal("50"),
        upside_return=Decimal("0.20") if flagged else Decimal("0"),
        funding_zscore=Decimal("3") if flagged else Decimal("0"),
        basis_zscore=Decimal("0"),
        oi_intensity_percentile=Decimal("50"),
        volatility_percentile=Decimal("50"),
        systemic_euphoria=False,
    )
    return calculate_euphoria_flag(
        inputs,
        config_metadata=config.run_metadata(),
    )


def crowding_result(config, *, flagged: bool = False):
    return calculate_crowding_flag(
        CrowdingFlagInput(
            funding_zscore=Decimal("3") if flagged else Decimal("0"),
            basis_zscore=Decimal("0"),
            oi_intensity_percentile=Decimal("50"),
        ),
        config_metadata=config.run_metadata(),
    )


def flow_result(config, zscore: str):
    value = Decimal(zscore)
    return calculate_flow_score(
        FlowScoreInput(value, value, value),
        core_weights=config.scoring_weights.core_flow,
        full_weights=config.scoring_weights.full_flow,
        config_metadata=config.run_metadata(),
    )


def test_canonical_path_composes_real_upstream_results_and_evidence() -> None:
    config = load_strategy_config()
    result = trim_rules_from_results(
        lifecycle=open_lifecycle(config),
        hold_score=hold_result(config),
        euphoria=euphoria_result(config),
        crowding=crowding_result(config),
        current_flow=flow_result(config, "-0.5"),
        prior_flow=flow_result(config, "0.5"),
        strategy_config=config,
    )

    assert isinstance(result, TrimSignalResult)
    assert result.signal is True
    assert result.reason_codes == ("TRIM_FLOW_DETERIORATION",)
    assert result.inputs.current_flow_score < result.inputs.prior_flow_score
    assert result.inputs.source_reason_codes["hold_score"] == (
        "HOLD_SCORE_COMPLETE",
    )
    assert result.inputs.source_reason_codes["current_flow"] == (
        "FLOW_SCORE_P1_INPUT_MISSING",
    )
    assert result.as_record()["inputs"]["source_reason_codes"]["lifecycle"] == [
        "POSITION_STATE_ENTERED",
    ]


def test_canonical_path_rejects_cross_config_source_results() -> None:
    config = load_strategy_config()
    wrong_hold = replace(
        hold_result(config),
        config_metadata={**config.run_metadata(), "parameter_set_id": "other"},
    )

    with pytest.raises(ValueError, match="hold_score config_metadata"):
        trim_rules_from_results(
            lifecycle=open_lifecycle(config),
            hold_score=wrong_hold,
            euphoria=euphoria_result(config),
            crowding=crowding_result(config),
            current_flow=flow_result(config, "0"),
            prior_flow=flow_result(config, "0"),
            strategy_config=config,
        )


def test_repeated_evaluation_is_deterministic() -> None:
    config = load_strategy_config()
    inputs = neutral_input(
        euphoria_active=True,
        source_reason_codes={"euphoria": ("EUPHORIA_UPSIDE_EXTENSION",)},
    )

    first = evaluate_trim_rules(inputs, strategy_config=config)
    second = evaluate_trim_rules(inputs, strategy_config=config)

    assert first == second
    assert first.as_record() == second.as_record()
