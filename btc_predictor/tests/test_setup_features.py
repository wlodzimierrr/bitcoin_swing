from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features import (
    BEARISH_DISTRIBUTION_FEATURE_ID,
    BEARISH_DISTRIBUTION_REASON_CODES,
    BEARISH_DISTRIBUTION_REQUIREMENT_KEYS,
    BEARISH_DISTRIBUTION_SETUP,
    BULLISH_RESET_FEATURE_ID,
    BULLISH_RESET_REASON_CODES,
    BULLISH_RESET_REQUIREMENT_KEYS,
    BULLISH_RESET_SETUP,
    BULL_TREND_CONTINUATION_FEATURE_ID,
    BULL_TREND_CONTINUATION_REASON_CODES,
    BULL_TREND_CONTINUATION_REQUIREMENT_KEYS,
    BULL_TREND_CONTINUATION_SETUP,
    CAPITULATION_REVERSAL_FEATURE_ID,
    CAPITULATION_REVERSAL_REASON_CODES,
    CAPITULATION_REVERSAL_REQUIREMENT_KEYS,
    CAPITULATION_REVERSAL_SETUP,
    DEFAULT_BEARISH_DISTRIBUTION_REQUIREMENTS,
    DEFAULT_BULLISH_RESET_REQUIREMENTS,
    DEFAULT_BULL_TREND_CONTINUATION_REQUIREMENTS,
    DEFAULT_CAPITULATION_REVERSAL_REQUIREMENTS,
    BearishDistributionInput,
    BullishResetInput,
    BullTrendContinuationInput,
    CapitulationReversalInput,
    detect_bearish_distribution,
    detect_bullish_reset,
    detect_bull_trend_continuation,
    detect_capitulation_reversal,
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


def test_bullish_reset_metadata_is_stable() -> None:
    assert BULLISH_RESET_SETUP == "BULLISH_RESET"
    assert BULLISH_RESET_FEATURE_ID == "SETUP_BULLISH_RESET"
    assert BULLISH_RESET_REQUIREMENT_KEYS == (
        "regime_min",
        "trend_min",
        "correction_min_fraction",
        "correction_max_fraction",
        "funding_health_improving_days",
        "oi_health_stable_days",
        "flow_accel_improving_days",
        "structure_min",
        "entry_trigger_required",
        "entry_conviction_min",
        "minimum_rr",
    )
    assert DEFAULT_BULLISH_RESET_REQUIREMENTS == {
        "regime_min": Decimal("55"),
        "trend_min": Decimal("55"),
        "correction_min_fraction": Decimal("0.08"),
        "correction_max_fraction": Decimal("0.25"),
        "funding_health_improving_days": 7,
        "oi_health_stable_days": 7,
        "flow_accel_improving_days": 5,
        "structure_min": Decimal("70"),
        "entry_trigger_required": True,
        "entry_conviction_min": Decimal("80"),
        "minimum_rr": Decimal("2"),
    }
    assert BULLISH_RESET_REASON_CODES == (
        "BULLISH_RESET_INPUT_MISSING",
        "BULLISH_RESET_REGIME_TOO_LOW",
        "BULLISH_RESET_TREND_TOO_LOW",
        "BULLISH_RESET_CORRECTION_TOO_SHALLOW",
        "BULLISH_RESET_CORRECTION_TOO_DEEP",
        "BULLISH_RESET_FUNDING_HEALTH_HISTORY_INSUFFICIENT",
        "BULLISH_RESET_FUNDING_HEALTH_NOT_IMPROVING",
        "BULLISH_RESET_OI_HEALTH_HISTORY_INSUFFICIENT",
        "BULLISH_RESET_OI_HEALTH_DETERIORATING",
        "BULLISH_RESET_FLOW_ACCEL_HISTORY_INSUFFICIENT",
        "BULLISH_RESET_FLOW_ACCEL_NOT_IMPROVING",
        "BULLISH_RESET_STRUCTURE_TOO_LOW",
        "BULLISH_RESET_ENTRY_TRIGGER_NOT_CONFIRMED",
        "BULLISH_RESET_ENTRY_CONVICTION_TOO_LOW",
        "BULLISH_RESET_RR_TOO_LOW",
    )


def test_capitulation_reversal_metadata_is_stable() -> None:
    assert CAPITULATION_REVERSAL_SETUP == "CAPITULATION_REVERSAL"
    assert CAPITULATION_REVERSAL_FEATURE_ID == "SETUP_CAPITULATION_REVERSAL"
    assert CAPITULATION_REVERSAL_REQUIREMENT_KEYS == (
        "capitulation_required",
        "confirmation_required",
        "confirmation_must_follow_capitulation",
        "max_confirmation_lag_days",
        "structure_min",
        "entry_conviction_min",
        "minimum_rr",
    )
    assert DEFAULT_CAPITULATION_REVERSAL_REQUIREMENTS == {
        "capitulation_required": True,
        "confirmation_required": True,
        "confirmation_must_follow_capitulation": True,
        "max_confirmation_lag_days": 14,
        "structure_min": Decimal("60"),
        "entry_conviction_min": Decimal("80"),
        "minimum_rr": Decimal("2"),
    }
    assert CAPITULATION_REVERSAL_REASON_CODES == (
        "CAPITULATION_REVERSAL_INPUT_MISSING",
        "CAPITULATION_REVERSAL_CAPITULATION_NOT_ACTIVE",
        "CAPITULATION_REVERSAL_CONFIRMATION_MISSING",
        "CAPITULATION_REVERSAL_CONFIRMATION_BEFORE_CAPITULATION",
        "CAPITULATION_REVERSAL_CONFIRMATION_TOO_STALE",
        "CAPITULATION_REVERSAL_STRUCTURE_TOO_LOW",
        "CAPITULATION_REVERSAL_ENTRY_CONVICTION_TOO_LOW",
        "CAPITULATION_REVERSAL_RR_TOO_LOW",
    )


def test_bearish_distribution_metadata_is_stable() -> None:
    assert BEARISH_DISTRIBUTION_SETUP == "BEARISH_DISTRIBUTION"
    assert BEARISH_DISTRIBUTION_FEATURE_ID == "SETUP_BEARISH_DISTRIBUTION"
    assert BEARISH_DISTRIBUTION_REQUIREMENT_KEYS == (
        "regime_max",
        "trend_max",
        "flow_max",
        "positioning_max",
        "structure_max",
        "entry_conviction_min",
        "minimum_rr",
        "distribution_required",
        "short_trigger_required",
        "require_no_stress",
    )
    assert DEFAULT_BEARISH_DISTRIBUTION_REQUIREMENTS == {
        "regime_max": Decimal("45"),
        "trend_max": Decimal("45"),
        "flow_max": Decimal("45"),
        "positioning_max": Decimal("45"),
        "structure_max": Decimal("50"),
        "entry_conviction_min": Decimal("85"),
        "minimum_rr": Decimal("2.5"),
        "distribution_required": True,
        "short_trigger_required": True,
        "require_no_stress": True,
    }
    assert BEARISH_DISTRIBUTION_REASON_CODES == (
        "BEARISH_DISTRIBUTION_INPUT_MISSING",
        "BEARISH_DISTRIBUTION_REGIME_TOO_HIGH",
        "BEARISH_DISTRIBUTION_TREND_TOO_HIGH",
        "BEARISH_DISTRIBUTION_FLOW_TOO_HIGH",
        "BEARISH_DISTRIBUTION_POSITIONING_TOO_HIGH",
        "BEARISH_DISTRIBUTION_STRUCTURE_TOO_HIGH",
        "BEARISH_DISTRIBUTION_ENTRY_CONVICTION_TOO_LOW",
        "BEARISH_DISTRIBUTION_RR_TOO_LOW",
        "BEARISH_DISTRIBUTION_NOT_ACTIVE",
        "BEARISH_DISTRIBUTION_SHORT_TRIGGER_NOT_CONFIRMED",
        "BEARISH_DISTRIBUTION_STRESS_ACTIVE",
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
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
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


def test_detect_bullish_reset_passes_on_hard_filter_boundaries() -> None:
    result = detect_bullish_reset(
        BullishResetInput(
            regime_score=Decimal("55"),
            trend_score=Decimal("55"),
            correction_from_local_high_fraction=Decimal("0.08"),
            funding_health_history=(
                Decimal("55"),
                Decimal("56"),
                Decimal("57"),
                Decimal("58"),
                Decimal("59"),
                Decimal("60"),
                Decimal("61"),
                Decimal("62"),
            ),
            oi_health_history=(
                Decimal("50"),
                Decimal("49"),
                Decimal("48"),
                Decimal("47"),
                Decimal("46"),
                Decimal("45"),
                Decimal("44"),
                Decimal("50"),
            ),
            flow_accel_history=(
                Decimal("-2"),
                Decimal("-1"),
                Decimal("0"),
                Decimal("1"),
                Decimal("2"),
                Decimal("3"),
            ),
            structure_score=Decimal("70"),
            entry_trigger_confirmed=True,
            entry_conviction_score=Decimal("80"),
            risk_reward=Decimal("2"),
        ),
    )

    assert result.complete is True
    assert result.detected is True
    assert result.setup == "BULLISH_RESET"
    assert result.reason_code == "SETUP_BULLISH_RESET_VALID"
    assert result.comparisons == {
        "funding_health": "7",
        "oi_health": "0",
        "flow_accel": "5",
    }
    assert result.reason_codes == ()


def test_detect_bullish_reset_accepts_correction_upper_boundary() -> None:
    result = detect_bullish_reset(
        BullishResetInput(
            regime_score=Decimal("70"),
            trend_score=Decimal("70"),
            correction_from_local_high_fraction=Decimal("0.25"),
            funding_health_history=(Decimal("40"), Decimal("48")),
            oi_health_history=(Decimal("50"), Decimal("50")),
            flow_accel_history=(Decimal("-1"), Decimal("1")),
            structure_score=Decimal("80"),
            entry_trigger_confirmed=True,
            entry_conviction_score=Decimal("90"),
            risk_reward=Decimal("3"),
        ),
        requirements={
            **DEFAULT_BULLISH_RESET_REQUIREMENTS,
            "funding_health_improving_days": 1,
            "oi_health_stable_days": 1,
            "flow_accel_improving_days": 1,
        },
    )

    assert result.detected is True
    assert result.reason_codes == ()


def test_detect_bullish_reset_reports_all_failed_hard_filters() -> None:
    result = detect_bullish_reset(
        BullishResetInput(
            regime_score=Decimal("54.99"),
            trend_score=Decimal("54.99"),
            correction_from_local_high_fraction=Decimal("0.26"),
            funding_health_history=(
                Decimal("62"),
                Decimal("62"),
                Decimal("61"),
                Decimal("60"),
                Decimal("59"),
                Decimal("58"),
                Decimal("57"),
                Decimal("55"),
            ),
            oi_health_history=(
                Decimal("60"),
                Decimal("59"),
                Decimal("58"),
                Decimal("57"),
                Decimal("56"),
                Decimal("55"),
                Decimal("54"),
                Decimal("50"),
            ),
            flow_accel_history=(
                Decimal("3"),
                Decimal("2"),
                Decimal("1"),
                Decimal("0"),
                Decimal("-1"),
                Decimal("-2"),
            ),
            structure_score=Decimal("69.99"),
            entry_trigger_confirmed=False,
            entry_conviction_score=Decimal("79.99"),
            risk_reward=Decimal("1.99"),
        ),
    )

    assert result.complete is True
    assert result.detected is False
    assert result.reason_code == "BULLISH_RESET_REGIME_TOO_LOW"
    assert result.reason_codes == (
        "BULLISH_RESET_REGIME_TOO_LOW",
        "BULLISH_RESET_TREND_TOO_LOW",
        "BULLISH_RESET_CORRECTION_TOO_DEEP",
        "BULLISH_RESET_FUNDING_HEALTH_NOT_IMPROVING",
        "BULLISH_RESET_OI_HEALTH_DETERIORATING",
        "BULLISH_RESET_FLOW_ACCEL_NOT_IMPROVING",
        "BULLISH_RESET_STRUCTURE_TOO_LOW",
        "BULLISH_RESET_ENTRY_TRIGGER_NOT_CONFIRMED",
        "BULLISH_RESET_ENTRY_CONVICTION_TOO_LOW",
        "BULLISH_RESET_RR_TOO_LOW",
    )


def test_detect_bullish_reset_reports_shallow_correction() -> None:
    result = detect_bullish_reset(
        BullishResetInput(
            regime_score=Decimal("70"),
            trend_score=Decimal("70"),
            correction_from_local_high_fraction=Decimal("0.079"),
            funding_health_history=(Decimal("40"), Decimal("50")),
            oi_health_history=(Decimal("50"), Decimal("50")),
            flow_accel_history=(Decimal("0"), Decimal("1")),
            structure_score=Decimal("80"),
            entry_trigger_confirmed=True,
            entry_conviction_score=Decimal("85"),
            risk_reward=Decimal("2.5"),
        ),
        requirements={
            **DEFAULT_BULLISH_RESET_REQUIREMENTS,
            "funding_health_improving_days": 1,
            "oi_health_stable_days": 1,
            "flow_accel_improving_days": 1,
        },
    )

    assert result.detected is False
    assert result.reason_codes == ("BULLISH_RESET_CORRECTION_TOO_SHALLOW",)


def test_detect_bullish_reset_reports_missing_inputs_and_insufficient_history() -> None:
    result = detect_bullish_reset(
        BullishResetInput(
            regime_score=None,
            trend_score=Decimal("60"),
            correction_from_local_high_fraction=None,
            funding_health_history=(Decimal("50"),),
            oi_health_history=None,
            flow_accel_history=(Decimal("1"), Decimal("2"), None),
            structure_score=Decimal("80"),
            entry_trigger_confirmed=None,
            entry_conviction_score=Decimal("85"),
            risk_reward=Decimal("2.5"),
        ),
    )

    assert result.complete is False
    assert result.detected is False
    assert result.reason_code == "BULLISH_RESET_INPUT_MISSING"
    assert result.comparisons == {
        "funding_health": None,
        "oi_health": None,
        "flow_accel": None,
    }
    assert result.reason_codes == (
        "BULLISH_RESET_INPUT_MISSING",
        "BULLISH_RESET_FUNDING_HEALTH_HISTORY_INSUFFICIENT",
        "BULLISH_RESET_OI_HEALTH_HISTORY_INSUFFICIENT",
        "BULLISH_RESET_FLOW_ACCEL_HISTORY_INSUFFICIENT",
    )


def test_detect_bullish_reset_uses_versioned_strategy_config() -> None:
    config = load_strategy_config()

    result = detect_bullish_reset(
        BullishResetInput(
            regime_score=Decimal("65"),
            trend_score=Decimal("62"),
            correction_from_local_high_fraction=Decimal("0.12"),
            funding_health_history=(
                Decimal("40"),
                Decimal("41"),
                Decimal("42"),
                Decimal("43"),
                Decimal("44"),
                Decimal("45"),
                Decimal("46"),
                Decimal("52"),
            ),
            oi_health_history=(
                Decimal("60"),
                Decimal("59"),
                Decimal("58"),
                Decimal("57"),
                Decimal("56"),
                Decimal("55"),
                Decimal("54"),
                Decimal("60"),
            ),
            flow_accel_history=(
                Decimal("-3"),
                Decimal("-2"),
                Decimal("-1"),
                Decimal("0"),
                Decimal("1"),
                Decimal("3"),
            ),
            structure_score=Decimal("74"),
            entry_trigger_confirmed=True,
            entry_conviction_score=Decimal("82"),
            risk_reward=Decimal("2.3"),
        ),
        requirements=config.setup_requirements.bullish_reset,
        config_metadata=config.run_metadata(),
    )

    assert result.as_record() == {
        "feature_id": "SETUP_BULLISH_RESET",
        "setup": "BULLISH_RESET",
        "detected": True,
        "reason_code": "SETUP_BULLISH_RESET_VALID",
        "inputs": {
            "regime_score": "65",
            "trend_score": "62",
            "correction_from_local_high_fraction": "0.12",
            "funding_health_history": [
                "40",
                "41",
                "42",
                "43",
                "44",
                "45",
                "46",
                "52",
            ],
            "oi_health_history": [
                "60",
                "59",
                "58",
                "57",
                "56",
                "55",
                "54",
                "60",
            ],
            "flow_accel_history": ["-3", "-2", "-1", "0", "1", "3"],
            "structure_score": "74",
            "entry_trigger_confirmed": True,
            "entry_conviction_score": "82",
            "risk_reward": "2.3",
        },
        "requirements": {
            "regime_min": "55.0",
            "trend_min": "55.0",
            "correction_min_fraction": "0.08",
            "correction_max_fraction": "0.25",
            "funding_health_improving_days": 7,
            "oi_health_stable_days": 7,
            "flow_accel_improving_days": 5,
            "structure_min": "70.0",
            "entry_trigger_required": True,
            "entry_conviction_min": "80.0",
            "minimum_rr": "2.0",
        },
        "comparisons": {
            "funding_health": "12",
            "oi_health": "0",
            "flow_accel": "6",
        },
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": [],
    }


def test_detect_bullish_reset_allows_optional_entry_trigger() -> None:
    requirements = dict(DEFAULT_BULLISH_RESET_REQUIREMENTS)
    requirements["entry_trigger_required"] = False

    result = detect_bullish_reset(
        BullishResetInput(
            regime_score=Decimal("65"),
            trend_score=Decimal("62"),
            correction_from_local_high_fraction=Decimal("0.12"),
            funding_health_history=(Decimal("40"), Decimal("50")),
            oi_health_history=(Decimal("50"), Decimal("50")),
            flow_accel_history=(Decimal("-1"), Decimal("1")),
            structure_score=Decimal("74"),
            entry_trigger_confirmed=False,
            entry_conviction_score=Decimal("82"),
            risk_reward=Decimal("2.3"),
        ),
        requirements={
            **requirements,
            "funding_health_improving_days": 1,
            "oi_health_stable_days": 1,
            "flow_accel_improving_days": 1,
        },
    )

    assert result.detected is True
    assert result.reason_codes == ()


def test_detect_bullish_reset_rejects_invalid_inputs_and_config() -> None:
    with pytest.raises(ValueError, match="entry_conviction_score"):
        detect_bullish_reset(
            BullishResetInput(
                regime_score=Decimal("65"),
                trend_score=Decimal("62"),
                correction_from_local_high_fraction=Decimal("0.12"),
                funding_health_history=(Decimal("40"), Decimal("50")),
                oi_health_history=(Decimal("50"), Decimal("50")),
                flow_accel_history=(Decimal("-1"), Decimal("1")),
                structure_score=Decimal("74"),
                entry_trigger_confirmed=True,
                entry_conviction_score=Decimal("101"),
                risk_reward=Decimal("2.3"),
            ),
            requirements={
                **DEFAULT_BULLISH_RESET_REQUIREMENTS,
                "funding_health_improving_days": 1,
                "oi_health_stable_days": 1,
                "flow_accel_improving_days": 1,
            },
        )

    with pytest.raises(ValueError, match="bullish reset requirements missing"):
        detect_bullish_reset(
            BullishResetInput(
                regime_score=Decimal("65"),
                trend_score=Decimal("62"),
                correction_from_local_high_fraction=Decimal("0.12"),
                funding_health_history=(Decimal("40"), Decimal("50")),
                oi_health_history=(Decimal("50"), Decimal("50")),
                flow_accel_history=(Decimal("-1"), Decimal("1")),
                structure_score=Decimal("74"),
                entry_trigger_confirmed=True,
                entry_conviction_score=Decimal("80"),
                risk_reward=Decimal("2.3"),
            ),
            requirements={"regime_min": Decimal("55")},
        )

    requirements = dict(DEFAULT_BULLISH_RESET_REQUIREMENTS)
    requirements["correction_max_fraction"] = Decimal("0.08")
    with pytest.raises(ValueError, match="correction_max_fraction"):
        detect_bullish_reset(
            BullishResetInput(
                regime_score=Decimal("65"),
                trend_score=Decimal("62"),
                correction_from_local_high_fraction=Decimal("0.12"),
                funding_health_history=(Decimal("40"), Decimal("50")),
                oi_health_history=(Decimal("50"), Decimal("50")),
                flow_accel_history=(Decimal("-1"), Decimal("1")),
                structure_score=Decimal("74"),
                entry_trigger_confirmed=True,
                entry_conviction_score=Decimal("80"),
                risk_reward=Decimal("2.3"),
            ),
            requirements=requirements,
        )


def test_detect_capitulation_reversal_passes_after_confirmed_capitulation() -> None:
    capitulation_at = datetime(2026, 8, 1, tzinfo=UTC)
    confirmation_at = capitulation_at + timedelta(days=2)

    result = detect_capitulation_reversal(
        CapitulationReversalInput(
            capitulation_flagged=True,
            capitulation_detected_at=capitulation_at,
            confirmation_triggered=True,
            confirmation_at=confirmation_at,
            structure_score=Decimal("60"),
            entry_conviction_score=Decimal("80"),
            risk_reward=Decimal("2"),
        ),
    )

    assert result.complete is True
    assert result.detected is True
    assert result.setup == "CAPITULATION_REVERSAL"
    assert result.reason_code == "SETUP_CAPITULATION_REVERSAL_VALID"
    assert result.confirmation_lag_days == Decimal("2")
    assert result.reason_codes == ()


def test_detect_capitulation_reversal_reports_all_failed_filters() -> None:
    capitulation_at = datetime(2026, 8, 10, tzinfo=UTC)
    confirmation_at = capitulation_at - timedelta(days=1)

    result = detect_capitulation_reversal(
        CapitulationReversalInput(
            capitulation_flagged=False,
            capitulation_detected_at=capitulation_at,
            confirmation_triggered=False,
            confirmation_at=confirmation_at,
            structure_score=Decimal("59.99"),
            entry_conviction_score=Decimal("79.99"),
            risk_reward=Decimal("1.99"),
        ),
    )

    assert result.complete is True
    assert result.detected is False
    assert result.reason_code == "CAPITULATION_REVERSAL_CAPITULATION_NOT_ACTIVE"
    assert result.confirmation_lag_days == Decimal("-1")
    assert result.reason_codes == (
        "CAPITULATION_REVERSAL_CAPITULATION_NOT_ACTIVE",
        "CAPITULATION_REVERSAL_CONFIRMATION_MISSING",
        "CAPITULATION_REVERSAL_CONFIRMATION_BEFORE_CAPITULATION",
        "CAPITULATION_REVERSAL_STRUCTURE_TOO_LOW",
        "CAPITULATION_REVERSAL_ENTRY_CONVICTION_TOO_LOW",
        "CAPITULATION_REVERSAL_RR_TOO_LOW",
    )


def test_detect_capitulation_reversal_rejects_stale_confirmation() -> None:
    capitulation_at = datetime(2026, 8, 1, tzinfo=UTC)
    confirmation_at = capitulation_at + timedelta(days=15)

    result = detect_capitulation_reversal(
        CapitulationReversalInput(
            capitulation_flagged=True,
            capitulation_detected_at=capitulation_at,
            confirmation_triggered=True,
            confirmation_at=confirmation_at,
            structure_score=Decimal("70"),
            entry_conviction_score=Decimal("90"),
            risk_reward=Decimal("3"),
        ),
    )

    assert result.complete is True
    assert result.detected is False
    assert result.confirmation_lag_days == Decimal("15")
    assert result.reason_codes == ("CAPITULATION_REVERSAL_CONFIRMATION_TOO_STALE",)


def test_detect_capitulation_reversal_reports_missing_inputs() -> None:
    result = detect_capitulation_reversal(
        CapitulationReversalInput(
            capitulation_flagged=None,
            capitulation_detected_at=None,
            confirmation_triggered=True,
            confirmation_at=datetime(2026, 8, 3, tzinfo=UTC),
            structure_score=Decimal("70"),
            entry_conviction_score=Decimal("90"),
            risk_reward=Decimal("3"),
        ),
    )

    assert result.complete is False
    assert result.detected is False
    assert result.reason_code == "CAPITULATION_REVERSAL_INPUT_MISSING"
    assert result.confirmation_lag_days is None
    assert result.reason_codes == ("CAPITULATION_REVERSAL_INPUT_MISSING",)


def test_detect_capitulation_reversal_uses_versioned_strategy_config() -> None:
    config = load_strategy_config()
    capitulation_at = datetime(2026, 8, 1, 12, tzinfo=UTC)
    confirmation_at = datetime(2026, 8, 4, 12, tzinfo=UTC)

    result = detect_capitulation_reversal(
        CapitulationReversalInput(
            capitulation_flagged=True,
            capitulation_detected_at=capitulation_at,
            confirmation_triggered=True,
            confirmation_at=confirmation_at,
            structure_score=Decimal("72"),
            entry_conviction_score=Decimal("84"),
            risk_reward=Decimal("2.5"),
        ),
        requirements=config.setup_requirements.capitulation_reversal,
        config_metadata=config.run_metadata(),
    )

    assert result.as_record() == {
        "feature_id": "SETUP_CAPITULATION_REVERSAL",
        "setup": "CAPITULATION_REVERSAL",
        "detected": True,
        "reason_code": "SETUP_CAPITULATION_REVERSAL_VALID",
        "inputs": {
            "capitulation_flagged": True,
            "capitulation_detected_at": "2026-08-01T12:00:00+00:00",
            "confirmation_triggered": True,
            "confirmation_at": "2026-08-04T12:00:00+00:00",
            "structure_score": "72",
            "entry_conviction_score": "84",
            "risk_reward": "2.5",
        },
        "requirements": {
            "capitulation_required": True,
            "confirmation_required": True,
            "confirmation_must_follow_capitulation": True,
            "max_confirmation_lag_days": 14,
            "structure_min": "60.0",
            "entry_conviction_min": "80.0",
            "minimum_rr": "2.0",
        },
        "confirmation_lag_days": "3",
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": [],
    }


def test_detect_capitulation_reversal_allows_disabled_capitulation_and_confirmation() -> None:
    requirements = dict(DEFAULT_CAPITULATION_REVERSAL_REQUIREMENTS)
    requirements["capitulation_required"] = False
    requirements["confirmation_required"] = False
    requirements["confirmation_must_follow_capitulation"] = False

    result = detect_capitulation_reversal(
        CapitulationReversalInput(
            capitulation_flagged=False,
            capitulation_detected_at=datetime(2026, 8, 10, tzinfo=UTC),
            confirmation_triggered=False,
            confirmation_at=datetime(2026, 8, 9, tzinfo=UTC),
            structure_score=Decimal("70"),
            entry_conviction_score=Decimal("90"),
            risk_reward=Decimal("3"),
        ),
        requirements=requirements,
    )

    assert result.detected is True
    assert result.confirmation_lag_days == Decimal("-1")
    assert result.reason_codes == ()


def test_detect_capitulation_reversal_rejects_invalid_inputs_and_config() -> None:
    with pytest.raises(ValueError, match="confirmation_at"):
        detect_capitulation_reversal(
            CapitulationReversalInput(
                capitulation_flagged=True,
                capitulation_detected_at=datetime(2026, 8, 1, tzinfo=UTC),
                confirmation_triggered=True,
                confirmation_at=datetime(2026, 8, 3),
                structure_score=Decimal("70"),
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
            ),
        )

    with pytest.raises(ValueError, match="structure_score"):
        detect_capitulation_reversal(
            CapitulationReversalInput(
                capitulation_flagged=True,
                capitulation_detected_at=datetime(2026, 8, 1, tzinfo=UTC),
                confirmation_triggered=True,
                confirmation_at=datetime(2026, 8, 3, tzinfo=UTC),
                structure_score=Decimal("101"),
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
            ),
        )

    with pytest.raises(ValueError, match="capitulation reversal requirements missing"):
        detect_capitulation_reversal(
            CapitulationReversalInput(
                capitulation_flagged=True,
                capitulation_detected_at=datetime(2026, 8, 1, tzinfo=UTC),
                confirmation_triggered=True,
                confirmation_at=datetime(2026, 8, 3, tzinfo=UTC),
                structure_score=Decimal("70"),
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
            ),
            requirements={"capitulation_required": True},
        )

    requirements = dict(DEFAULT_CAPITULATION_REVERSAL_REQUIREMENTS)
    requirements["max_confirmation_lag_days"] = 0
    with pytest.raises(ValueError, match="max_confirmation_lag_days"):
        detect_capitulation_reversal(
            CapitulationReversalInput(
                capitulation_flagged=True,
                capitulation_detected_at=datetime(2026, 8, 1, tzinfo=UTC),
                confirmation_triggered=True,
                confirmation_at=datetime(2026, 8, 3, tzinfo=UTC),
                structure_score=Decimal("70"),
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
            ),
            requirements=requirements,
        )


def test_detect_bearish_distribution_passes_on_strict_boundaries() -> None:
    result = detect_bearish_distribution(
        BearishDistributionInput(
            regime_score=Decimal("45"),
            trend_score=Decimal("45"),
            flow_score=Decimal("45"),
            positioning_score=Decimal("45"),
            structure_score=Decimal("50"),
            entry_conviction_score=Decimal("85"),
            risk_reward=Decimal("2.5"),
            distribution_flagged=True,
            short_trigger_confirmed=True,
            stress_flagged=False,
        ),
    )

    assert result.detected is True
    assert result.complete is True
    assert result.reason_code == "SETUP_BEARISH_DISTRIBUTION_VALID"
    assert result.reason_codes == ()
    assert result.as_record()["inputs"] == {
        "regime_score": "45",
        "trend_score": "45",
        "flow_score": "45",
        "positioning_score": "45",
        "structure_score": "50",
        "entry_conviction_score": "85",
        "risk_reward": "2.5",
        "distribution_flagged": True,
        "short_trigger_confirmed": True,
        "stress_flagged": False,
    }


def test_detect_bearish_distribution_reports_all_failed_filters() -> None:
    result = detect_bearish_distribution(
        BearishDistributionInput(
            regime_score=Decimal("46"),
            trend_score=Decimal("50"),
            flow_score=Decimal("60"),
            positioning_score=Decimal("70"),
            structure_score=Decimal("65"),
            entry_conviction_score=Decimal("84"),
            risk_reward=Decimal("2.49"),
            distribution_flagged=False,
            short_trigger_confirmed=False,
            stress_flagged=True,
        ),
    )

    assert result.detected is False
    assert result.complete is True
    assert result.reason_code == "BEARISH_DISTRIBUTION_REGIME_TOO_HIGH"
    assert result.reason_codes == (
        "BEARISH_DISTRIBUTION_REGIME_TOO_HIGH",
        "BEARISH_DISTRIBUTION_TREND_TOO_HIGH",
        "BEARISH_DISTRIBUTION_FLOW_TOO_HIGH",
        "BEARISH_DISTRIBUTION_POSITIONING_TOO_HIGH",
        "BEARISH_DISTRIBUTION_STRUCTURE_TOO_HIGH",
        "BEARISH_DISTRIBUTION_ENTRY_CONVICTION_TOO_LOW",
        "BEARISH_DISTRIBUTION_RR_TOO_LOW",
        "BEARISH_DISTRIBUTION_NOT_ACTIVE",
        "BEARISH_DISTRIBUTION_SHORT_TRIGGER_NOT_CONFIRMED",
        "BEARISH_DISTRIBUTION_STRESS_ACTIVE",
    )


def test_detect_bearish_distribution_reports_missing_inputs() -> None:
    result = detect_bearish_distribution(
        BearishDistributionInput(
            regime_score=None,
            trend_score=Decimal("40"),
            flow_score=Decimal("40"),
            positioning_score=Decimal("40"),
            structure_score=Decimal("45"),
            entry_conviction_score=Decimal("90"),
            risk_reward=Decimal("3"),
            distribution_flagged=True,
            short_trigger_confirmed=True,
            stress_flagged=False,
        ),
    )

    assert result.detected is False
    assert result.complete is False
    assert result.reason_code == "BEARISH_DISTRIBUTION_INPUT_MISSING"
    assert result.reason_codes == ("BEARISH_DISTRIBUTION_INPUT_MISSING",)


def test_detect_bearish_distribution_uses_versioned_strategy_config() -> None:
    config = load_strategy_config()

    result = detect_bearish_distribution(
        BearishDistributionInput(
            regime_score=Decimal("35"),
            trend_score=Decimal("30"),
            flow_score=Decimal("25"),
            positioning_score=Decimal("35"),
            structure_score=Decimal("45"),
            entry_conviction_score=Decimal("90"),
            risk_reward=Decimal("3"),
            distribution_flagged=True,
            short_trigger_confirmed=True,
            stress_flagged=False,
        ),
        requirements=config.setup_requirements.bearish_distribution,
        config_metadata=config.run_metadata(),
    )

    assert result.detected is True
    assert result.as_record() == {
        "feature_id": "SETUP_BEARISH_DISTRIBUTION",
        "setup": "BEARISH_DISTRIBUTION",
        "detected": True,
        "reason_code": "SETUP_BEARISH_DISTRIBUTION_VALID",
        "inputs": {
            "regime_score": "35",
            "trend_score": "30",
            "flow_score": "25",
            "positioning_score": "35",
            "structure_score": "45",
            "entry_conviction_score": "90",
            "risk_reward": "3",
            "distribution_flagged": True,
            "short_trigger_confirmed": True,
            "stress_flagged": False,
        },
        "requirements": {
            "regime_max": "45.0",
            "trend_max": "45.0",
            "flow_max": "45.0",
            "positioning_max": "45.0",
            "structure_max": "50.0",
            "entry_conviction_min": "85.0",
            "minimum_rr": "2.5",
            "distribution_required": True,
            "short_trigger_required": True,
            "require_no_stress": True,
        },
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": [],
    }


def test_detect_bearish_distribution_allows_disabled_flag_filters() -> None:
    requirements = dict(DEFAULT_BEARISH_DISTRIBUTION_REQUIREMENTS)
    requirements["distribution_required"] = False
    requirements["short_trigger_required"] = False
    requirements["require_no_stress"] = False

    result = detect_bearish_distribution(
        BearishDistributionInput(
            regime_score=Decimal("40"),
            trend_score=Decimal("40"),
            flow_score=Decimal("40"),
            positioning_score=Decimal("40"),
            structure_score=Decimal("40"),
            entry_conviction_score=Decimal("90"),
            risk_reward=Decimal("3"),
            distribution_flagged=False,
            short_trigger_confirmed=False,
            stress_flagged=True,
        ),
        requirements=requirements,
    )

    assert result.detected is True
    assert result.reason_codes == ()


def test_detect_bearish_distribution_rejects_invalid_inputs_and_config() -> None:
    with pytest.raises(ValueError, match="trend_score"):
        detect_bearish_distribution(
            BearishDistributionInput(
                regime_score=Decimal("40"),
                trend_score=Decimal("101"),
                flow_score=Decimal("40"),
                positioning_score=Decimal("40"),
                structure_score=Decimal("40"),
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
                distribution_flagged=True,
                short_trigger_confirmed=True,
                stress_flagged=False,
            ),
        )

    with pytest.raises(ValueError, match="distribution_flagged"):
        detect_bearish_distribution(
            BearishDistributionInput(
                regime_score=Decimal("40"),
                trend_score=Decimal("40"),
                flow_score=Decimal("40"),
                positioning_score=Decimal("40"),
                structure_score=Decimal("40"),
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
                distribution_flagged="true",  # type: ignore[arg-type]
                short_trigger_confirmed=True,
                stress_flagged=False,
            ),
        )

    with pytest.raises(ValueError, match="bearish distribution requirements missing"):
        detect_bearish_distribution(
            BearishDistributionInput(
                regime_score=Decimal("40"),
                trend_score=Decimal("40"),
                flow_score=Decimal("40"),
                positioning_score=Decimal("40"),
                structure_score=Decimal("40"),
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
                distribution_flagged=True,
                short_trigger_confirmed=True,
                stress_flagged=False,
            ),
            requirements={"regime_max": Decimal("45")},
        )

    requirements = dict(DEFAULT_BEARISH_DISTRIBUTION_REQUIREMENTS)
    requirements["minimum_rr"] = Decimal("0")
    with pytest.raises(ValueError, match="minimum_rr"):
        detect_bearish_distribution(
            BearishDistributionInput(
                regime_score=Decimal("40"),
                trend_score=Decimal("40"),
                flow_score=Decimal("40"),
                positioning_score=Decimal("40"),
                structure_score=Decimal("40"),
                entry_conviction_score=Decimal("90"),
                risk_reward=Decimal("3"),
                distribution_flagged=True,
                short_trigger_confirmed=True,
                stress_flagged=False,
            ),
            requirements=requirements,
        )
