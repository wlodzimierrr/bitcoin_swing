from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features import (
    BULL_TREND_CONTINUATION_FEATURE_ID,
    BULL_TREND_CONTINUATION_REASON_CODES,
    BULL_TREND_CONTINUATION_REQUIREMENT_KEYS,
    BULL_TREND_CONTINUATION_SETUP,
    DEFAULT_BULL_TREND_CONTINUATION_REQUIREMENTS,
    BullTrendContinuationInput,
    detect_bull_trend_continuation,
)


def test_bull_trend_continuation_metadata_is_stable() -> None:
    assert BULL_TREND_CONTINUATION_SETUP == "BULL_TREND_CONTINUATION"
    assert BULL_TREND_CONTINUATION_FEATURE_ID == "SETUP_BULL_TREND_CONTINUATION"
    assert BULL_TREND_CONTINUATION_REQUIREMENT_KEYS == (
        "regime_min",
        "trend_min",
        "flow_min",
        "positioning_min",
        "structure_min",
        "minimum_rr",
        "require_no_stress",
        "require_no_severe_crowding",
    )
    assert DEFAULT_BULL_TREND_CONTINUATION_REQUIREMENTS == {
        "regime_min": Decimal("65"),
        "trend_min": Decimal("70"),
        "flow_min": Decimal("55"),
        "positioning_min": Decimal("60"),
        "structure_min": Decimal("70"),
        "minimum_rr": Decimal("2"),
        "require_no_stress": True,
        "require_no_severe_crowding": True,
    }
    assert BULL_TREND_CONTINUATION_REASON_CODES == (
        "BULL_TREND_CONTINUATION_INPUT_MISSING",
        "BULL_TREND_CONTINUATION_REGIME_TOO_LOW",
        "BULL_TREND_CONTINUATION_TREND_TOO_LOW",
        "BULL_TREND_CONTINUATION_FLOW_TOO_LOW",
        "BULL_TREND_CONTINUATION_POSITIONING_TOO_LOW",
        "BULL_TREND_CONTINUATION_STRUCTURE_TOO_LOW",
        "BULL_TREND_CONTINUATION_STRESS_ACTIVE",
        "BULL_TREND_CONTINUATION_SEVERE_CROWDING_ACTIVE",
        "BULL_TREND_CONTINUATION_RR_TOO_LOW",
    )


def test_detect_bull_trend_continuation_passes_on_hard_filter_boundaries() -> None:
    result = detect_bull_trend_continuation(
        BullTrendContinuationInput(
            regime_score=Decimal("65"),
            trend_score=Decimal("70"),
            flow_score=Decimal("55"),
            positioning_score=Decimal("60"),
            structure_score=Decimal("70"),
            stress_flagged=False,
            severe_crowding_flagged=False,
            risk_reward=Decimal("2"),
        ),
    )

    assert result.complete is True
    assert result.detected is True
    assert result.setup == "BULL_TREND_CONTINUATION"
    assert result.reason_code == "SETUP_BULL_TREND_CONTINUATION_VALID"
    assert result.reason_codes == ()


def test_detect_bull_trend_continuation_reports_all_failed_hard_filters() -> None:
    result = detect_bull_trend_continuation(
        BullTrendContinuationInput(
            regime_score=Decimal("64.99"),
            trend_score=Decimal("69.99"),
            flow_score=Decimal("54.99"),
            positioning_score=Decimal("59.99"),
            structure_score=Decimal("69.99"),
            stress_flagged=True,
            severe_crowding_flagged=True,
            risk_reward=Decimal("1.99"),
        ),
    )

    assert result.complete is True
    assert result.detected is False
    assert result.reason_code == "BULL_TREND_CONTINUATION_REGIME_TOO_LOW"
    assert result.reason_codes == (
        "BULL_TREND_CONTINUATION_REGIME_TOO_LOW",
        "BULL_TREND_CONTINUATION_TREND_TOO_LOW",
        "BULL_TREND_CONTINUATION_FLOW_TOO_LOW",
        "BULL_TREND_CONTINUATION_POSITIONING_TOO_LOW",
        "BULL_TREND_CONTINUATION_STRUCTURE_TOO_LOW",
        "BULL_TREND_CONTINUATION_STRESS_ACTIVE",
        "BULL_TREND_CONTINUATION_SEVERE_CROWDING_ACTIVE",
        "BULL_TREND_CONTINUATION_RR_TOO_LOW",
    )


def test_detect_bull_trend_continuation_reports_missing_inputs() -> None:
    result = detect_bull_trend_continuation(
        BullTrendContinuationInput(
            regime_score=None,
            trend_score=Decimal("72"),
            flow_score=Decimal("60"),
            positioning_score=Decimal("65"),
            structure_score=Decimal("75"),
            stress_flagged=None,
            severe_crowding_flagged=False,
            risk_reward=Decimal("2.5"),
        ),
    )

    assert result.complete is False
    assert result.detected is False
    assert result.reason_code == "BULL_TREND_CONTINUATION_INPUT_MISSING"
    assert result.reason_codes == ("BULL_TREND_CONTINUATION_INPUT_MISSING",)


def test_detect_bull_trend_continuation_uses_versioned_strategy_config() -> None:
    config = load_strategy_config()

    result = detect_bull_trend_continuation(
        BullTrendContinuationInput(
            regime_score=Decimal("72.25"),
            trend_score=Decimal("74"),
            flow_score=Decimal("62"),
            positioning_score=Decimal("70"),
            structure_score=Decimal("80"),
            stress_flagged=False,
            severe_crowding_flagged=False,
            risk_reward=Decimal("2.4"),
        ),
        requirements=config.setup_requirements.bull_trend_continuation,
        config_metadata=config.run_metadata(),
    )

    assert result.as_record() == {
        "feature_id": "SETUP_BULL_TREND_CONTINUATION",
        "setup": "BULL_TREND_CONTINUATION",
        "detected": True,
        "reason_code": "SETUP_BULL_TREND_CONTINUATION_VALID",
        "inputs": {
            "regime_score": "72.25",
            "trend_score": "74",
            "flow_score": "62",
            "positioning_score": "70",
            "structure_score": "80",
            "stress_flagged": False,
            "severe_crowding_flagged": False,
            "risk_reward": "2.4",
        },
        "requirements": {
            "regime_min": "65.0",
            "trend_min": "70.0",
            "flow_min": "55.0",
            "positioning_min": "60.0",
            "structure_min": "70.0",
            "minimum_rr": "2.0",
            "require_no_stress": True,
            "require_no_severe_crowding": True,
        },
        "config_metadata": {
            "config_version": "strategy_config_v1",
            "strategy_version": "swing_v1.0",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": [],
    }


def test_detect_bull_trend_continuation_allows_disabled_flag_filters() -> None:
    requirements = dict(DEFAULT_BULL_TREND_CONTINUATION_REQUIREMENTS)
    requirements["require_no_stress"] = False
    requirements["require_no_severe_crowding"] = False

    result = detect_bull_trend_continuation(
        BullTrendContinuationInput(
            regime_score=Decimal("80"),
            trend_score=Decimal("80"),
            flow_score=Decimal("80"),
            positioning_score=Decimal("80"),
            structure_score=Decimal("80"),
            stress_flagged=True,
            severe_crowding_flagged=True,
            risk_reward=Decimal("3"),
        ),
        requirements=requirements,
    )

    assert result.detected is True
    assert result.reason_codes == ()


def test_detect_bull_trend_continuation_rejects_invalid_inputs_and_config() -> None:
    with pytest.raises(ValueError, match="regime_score"):
        detect_bull_trend_continuation(
            BullTrendContinuationInput(
                regime_score=Decimal("101"),
                trend_score=Decimal("70"),
                flow_score=Decimal("55"),
                positioning_score=Decimal("60"),
                structure_score=Decimal("70"),
                stress_flagged=False,
                severe_crowding_flagged=False,
                risk_reward=Decimal("2"),
            ),
        )

    with pytest.raises(ValueError, match="risk_reward"):
        detect_bull_trend_continuation(
            BullTrendContinuationInput(
                regime_score=Decimal("65"),
                trend_score=Decimal("70"),
                flow_score=Decimal("55"),
                positioning_score=Decimal("60"),
                structure_score=Decimal("70"),
                stress_flagged=False,
                severe_crowding_flagged=False,
                risk_reward=Decimal("-1"),
            ),
        )

    with pytest.raises(ValueError, match="requirements missing"):
        detect_bull_trend_continuation(
            BullTrendContinuationInput(
                regime_score=Decimal("65"),
                trend_score=Decimal("70"),
                flow_score=Decimal("55"),
                positioning_score=Decimal("60"),
                structure_score=Decimal("70"),
                stress_flagged=False,
                severe_crowding_flagged=False,
                risk_reward=Decimal("2"),
            ),
            requirements={"regime_min": Decimal("65")},
        )

    requirements = dict(DEFAULT_BULL_TREND_CONTINUATION_REQUIREMENTS)
    requirements["require_no_stress"] = "true"
    with pytest.raises(ValueError, match="require_no_stress"):
        detect_bull_trend_continuation(
            BullTrendContinuationInput(
                regime_score=Decimal("65"),
                trend_score=Decimal("70"),
                flow_score=Decimal("55"),
                positioning_score=Decimal("60"),
                structure_score=Decimal("70"),
                stress_flagged=False,
                severe_crowding_flagged=False,
                risk_reward=Decimal("2"),
            ),
            requirements=requirements,
        )
