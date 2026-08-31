from dataclasses import replace

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.signals import (
    HARD_VETO_EFFECTS,
    HARD_VETO_FEATURE_ID,
    HARD_VETO_INPUT_IDS,
    HARD_VETO_POLICY_VERSION,
    HARD_VETO_REASON_CODES,
    HardVetoInput,
    HardVetoResult,
    evaluate_hard_veto,
)


def _clear_inputs(**changes: object) -> HardVetoInput:
    values: dict[str, object] = {
        "data_quality_fail": False,
        "valid_structural_stop": True,
        "reward_risk_passes": True,
        "stress_flagged": False,
        "severe_crowding_flagged": False,
        "no_chase_blocked": False,
        "setup": "BULL_TREND_CONTINUATION",
    }
    values.update(changes)
    return HardVetoInput(**values)  # type: ignore[arg-type]


def test_hard_veto_contract_is_stable() -> None:
    assert HARD_VETO_FEATURE_ID == "HARD_VETO"
    assert HARD_VETO_POLICY_VERSION == "HARD_VETO_V1"
    assert HARD_VETO_EFFECTS == ("NO_TRADE",)
    assert HARD_VETO_INPUT_IDS == (
        "data_quality_fail",
        "valid_structural_stop",
        "reward_risk_passes",
        "stress_flagged",
        "severe_crowding_flagged",
        "no_chase_blocked",
        "setup",
    )
    assert HARD_VETO_REASON_CODES == (
        "HARD_VETO_INPUT_MISSING",
        "HARD_VETO_DATA_QUALITY_FAIL",
        "HARD_VETO_NO_VALID_STRUCTURAL_STOP",
        "HARD_VETO_POOR_REWARD_RISK",
        "HARD_VETO_STRESS",
        "HARD_VETO_SEVERE_CROWDING",
        "HARD_VETO_NO_CHASE_VIOLATION",
        "HARD_VETO_UNSUPPORTED_SETUP",
        "HARD_VETO_CLEAR",
    )


def test_clear_result_is_complete_and_reconstructable() -> None:
    result = evaluate_hard_veto(
        _clear_inputs(
            source_reason_codes={
                "reward_risk_passes": ("REWARD_RISK_PASS",),
                "valid_structural_stop": ("INITIAL_STOP_COMPLETE",),
            },
        ),
        strategy_config=load_strategy_config(),
    )

    assert isinstance(result, HardVetoResult)
    assert result.blocked is False
    assert result.effects == ()
    assert result.missing_inputs == ()
    assert result.complete is True
    assert result.reason_codes == ("HARD_VETO_CLEAR",)
    assert result.as_record() == {
        "feature_id": "HARD_VETO",
        "policy_version": "HARD_VETO_V1",
        "inputs": {
            "data_quality_fail": False,
            "valid_structural_stop": True,
            "reward_risk_passes": True,
            "stress_flagged": False,
            "severe_crowding_flagged": False,
            "no_chase_blocked": False,
            "setup": "BULL_TREND_CONTINUATION",
            "source_reason_codes": {
                "reward_risk_passes": ["REWARD_RISK_PASS"],
                "valid_structural_stop": ["INITIAL_STOP_COMPLETE"],
            },
        },
        "supported_setups": [
            "bull_trend_continuation",
            "bullish_reset",
            "capitulation_reversal",
            "bearish_distribution",
        ],
        "stress_blocks_new_trades": False,
        "blocked": False,
        "effects": [],
        "missing_inputs": [],
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": ["HARD_VETO_CLEAR"],
    }


@pytest.mark.parametrize(
    ("changes", "reason_code"),
    [
        ({"data_quality_fail": True}, "HARD_VETO_DATA_QUALITY_FAIL"),
        (
            {"valid_structural_stop": False},
            "HARD_VETO_NO_VALID_STRUCTURAL_STOP",
        ),
        ({"reward_risk_passes": False}, "HARD_VETO_POOR_REWARD_RISK"),
        (
            {"severe_crowding_flagged": True},
            "HARD_VETO_SEVERE_CROWDING",
        ),
        ({"no_chase_blocked": True}, "HARD_VETO_NO_CHASE_VIOLATION"),
        ({"setup": "unknown_setup"}, "HARD_VETO_UNSUPPORTED_SETUP"),
    ],
)
def test_each_unconditional_veto_blocks_new_trade(
    changes: dict[str, object],
    reason_code: str,
) -> None:
    result = evaluate_hard_veto(
        _clear_inputs(**changes),
        strategy_config=load_strategy_config(),
    )

    assert result.blocked is True
    assert result.effects == ("NO_TRADE",)
    assert result.complete is True
    assert result.reason_codes == (reason_code,)


def test_stress_respects_versioned_block_new_trades_policy() -> None:
    default = load_strategy_config()
    blocking = replace(
        default,
        volatility_flags=replace(
            default.volatility_flags,
            stress=replace(
                default.volatility_flags.stress,
                block_new_trades=True,
            ),
        ),
    )

    default_result = evaluate_hard_veto(
        _clear_inputs(stress_flagged=True),
        strategy_config=default,
    )
    blocking_result = evaluate_hard_veto(
        _clear_inputs(stress_flagged=True),
        strategy_config=blocking,
    )

    assert default_result.blocked is False
    assert default_result.reason_codes == ("HARD_VETO_CLEAR",)
    assert default_result.stress_blocks_new_trades is False
    assert blocking_result.blocked is True
    assert blocking_result.reason_codes == ("HARD_VETO_STRESS",)
    assert blocking_result.as_record()["stress_blocks_new_trades"] is True


@pytest.mark.parametrize("input_id", HARD_VETO_INPUT_IDS)
def test_missing_required_inputs_fail_closed(input_id: str) -> None:
    result = evaluate_hard_veto(
        _clear_inputs(**{input_id: None}),
        strategy_config=load_strategy_config(),
    )

    assert result.blocked is True
    assert result.effects == ("NO_TRADE",)
    assert result.complete is False
    assert result.missing_inputs == (input_id,)
    assert result.reason_codes[0] == "HARD_VETO_INPUT_MISSING"
    if input_id == "valid_structural_stop":
        assert "HARD_VETO_NO_VALID_STRUCTURAL_STOP" in result.reason_codes
    if input_id == "reward_risk_passes":
        assert "HARD_VETO_POOR_REWARD_RISK" in result.reason_codes
    if input_id == "setup":
        assert "HARD_VETO_UNSUPPORTED_SETUP" in result.reason_codes


def test_all_veto_reasons_have_deterministic_policy_order() -> None:
    config = load_strategy_config()
    config = replace(
        config,
        volatility_flags=replace(
            config.volatility_flags,
            stress=replace(config.volatility_flags.stress, block_new_trades=True),
        ),
    )
    inputs = _clear_inputs(
        data_quality_fail=True,
        valid_structural_stop=False,
        reward_risk_passes=False,
        stress_flagged=True,
        severe_crowding_flagged=True,
        no_chase_blocked=True,
        setup="not_supported",
    )

    first = evaluate_hard_veto(inputs, strategy_config=config)
    second = evaluate_hard_veto(inputs, strategy_config=config)

    assert first.reason_codes == (
        "HARD_VETO_DATA_QUALITY_FAIL",
        "HARD_VETO_NO_VALID_STRUCTURAL_STOP",
        "HARD_VETO_POOR_REWARD_RISK",
        "HARD_VETO_STRESS",
        "HARD_VETO_SEVERE_CROWDING",
        "HARD_VETO_NO_CHASE_VIOLATION",
        "HARD_VETO_UNSUPPORTED_SETUP",
    )
    assert first.as_record() == second.as_record()


def test_supported_setup_policy_is_loaded_from_strategy_config() -> None:
    default = load_strategy_config()
    custom = replace(
        default,
        setup_requirements=replace(
            default.setup_requirements,
            supported_setups=("custom_setup",),
        ),
    )

    result = evaluate_hard_veto(
        _clear_inputs(setup="CUSTOM_SETUP"),
        strategy_config=custom,
    )

    assert result.blocked is False
    assert result.supported_setups == ("custom_setup",)


def test_result_record_rejects_derived_state_drift() -> None:
    result = evaluate_hard_veto(
        _clear_inputs(),
        strategy_config=load_strategy_config(),
    )

    with pytest.raises(ValueError, match="blocked does not match"):
        replace(result, blocked=True).as_record()
    with pytest.raises(ValueError, match="reason_codes do not match"):
        replace(result, reason_codes=("HARD_VETO_STRESS",)).as_record()
    with pytest.raises(ValueError, match="config_metadata must exactly match"):
        replace(result, config_metadata={}).as_record()


def test_invalid_input_and_source_reason_types_fail_fast() -> None:
    with pytest.raises(TypeError, match="data_quality_fail"):
        evaluate_hard_veto(
            _clear_inputs(data_quality_fail=1),
            strategy_config=load_strategy_config(),
        )
    with pytest.raises(ValueError, match="unsupported source"):
        evaluate_hard_veto(
            _clear_inputs(source_reason_codes={"other": ("CODE",)}),
            strategy_config=load_strategy_config(),
        )


def test_entry_score_cannot_override_a_hard_veto() -> None:
    assert "entry_conviction" not in HARD_VETO_INPUT_IDS
    result = evaluate_hard_veto(
        _clear_inputs(data_quality_fail=True),
        strategy_config=load_strategy_config(),
    )

    assert result.blocked is True
    assert result.effects == ("NO_TRADE",)
