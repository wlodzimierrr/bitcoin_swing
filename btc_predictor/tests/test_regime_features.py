from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features import (
    CORE_REGIME_SCORE_COMPONENT_IDS,
    DEFAULT_CORE_REGIME_SCORE_WEIGHTS,
    DEFAULT_FULL_REGIME_SCORE_WEIGHTS,
    DEFAULT_REGIME_SMOOTHING_NEW_WEIGHT,
    DEFAULT_REGIME_SMOOTHING_PREVIOUS_WEIGHT,
    FULL_REGIME_SCORE_COMPONENT_IDS,
    REGIME_MODEL_CORE_MARKET_ONLY,
    REGIME_MODEL_FULL_MACRO_ONCHAIN_LIQUIDITY,
    REGIME_SCORE_FEATURE_ID,
    REGIME_SCORE_REASON_CODES,
    REGIME_SMOOTHED_SCORE_FEATURE_ID,
    REGIME_SMOOTHING_REASON_CODES,
    RegimeScoreInput,
    RegimeSmoothingInput,
    calculate_regime_score,
    calculate_regime_smoothing,
)


def test_regime_score_metadata_is_stable() -> None:
    assert REGIME_SCORE_FEATURE_ID == "REGIME_SCORE"
    assert REGIME_SMOOTHED_SCORE_FEATURE_ID == "REGIME_SMOOTHED_SCORE"
    assert REGIME_MODEL_CORE_MARKET_ONLY == "CORE_MARKET_ONLY"
    assert REGIME_MODEL_FULL_MACRO_ONCHAIN_LIQUIDITY == (
        "FULL_MACRO_ONCHAIN_LIQUIDITY"
    )
    assert CORE_REGIME_SCORE_COMPONENT_IDS == (
        "trend",
        "flow",
        "volatility",
        "positioning",
    )
    assert FULL_REGIME_SCORE_COMPONENT_IDS == (
        "trend",
        "flow",
        "macro",
        "onchain",
        "volatility",
        "liquidity",
    )
    assert DEFAULT_CORE_REGIME_SCORE_WEIGHTS == {
        "trend": Decimal("0.45"),
        "flow": Decimal("0.25"),
        "volatility": Decimal("0.15"),
        "positioning": Decimal("0.15"),
    }
    assert DEFAULT_FULL_REGIME_SCORE_WEIGHTS == {
        "trend": Decimal("0.35"),
        "flow": Decimal("0.20"),
        "macro": Decimal("0.15"),
        "onchain": Decimal("0.10"),
        "volatility": Decimal("0.10"),
        "liquidity": Decimal("0.10"),
    }
    assert REGIME_SCORE_REASON_CODES == (
        "REGIME_SCORE_CORE_INPUT_MISSING",
        "REGIME_SCORE_P1_INPUT_MISSING",
    )
    assert DEFAULT_REGIME_SMOOTHING_PREVIOUS_WEIGHT == Decimal("0.70")
    assert DEFAULT_REGIME_SMOOTHING_NEW_WEIGHT == Decimal("0.30")
    assert REGIME_SMOOTHING_REASON_CODES == (
        "REGIME_SMOOTHING_NEW_SCORE_MISSING",
        "REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING",
    )


def test_calculate_regime_score_uses_full_model_when_p1_inputs_are_available() -> None:
    result = calculate_regime_score(
        RegimeScoreInput(
            trend_score=Decimal("80"),
            flow_score=Decimal("70"),
            volatility_score=Decimal("60"),
            positioning_score=Decimal("65"),
            macro_score=Decimal("50"),
            onchain_score=Decimal("55"),
            liquidity_score=Decimal("45"),
        )
    )

    assert result.complete is True
    assert result.regime_model == "FULL_MACRO_ONCHAIN_LIQUIDITY"
    assert result.score == Decimal("65.50")
    assert result.interpretation == "bull"
    assert result.reason_code == "REGIME_SCORE_bull"
    assert result.contributions == {
        "trend": Decimal("28.00"),
        "flow": Decimal("14.00"),
        "macro": Decimal("7.50"),
        "onchain": Decimal("5.50"),
        "volatility": Decimal("6.00"),
        "liquidity": Decimal("4.50"),
    }
    assert result.reason_codes == ()


def test_calculate_regime_score_uses_core_model_when_p1_inputs_are_missing() -> None:
    result = calculate_regime_score(
        RegimeScoreInput(
            trend_score=Decimal("80"),
            flow_score=Decimal("70"),
            volatility_score=Decimal("60"),
            positioning_score=Decimal("65"),
        )
    )

    assert result.complete is True
    assert result.regime_model == "CORE_MARKET_ONLY"
    assert result.score == Decimal("72.25")
    assert result.interpretation == "bull"
    assert set(result.contributions) == {
        "trend",
        "flow",
        "volatility",
        "positioning",
    }
    assert result.reason_codes == ("REGIME_SCORE_P1_INPUT_MISSING",)


def test_calculate_regime_score_does_not_fill_missing_core_inputs() -> None:
    result = calculate_regime_score(
        RegimeScoreInput(
            trend_score=Decimal("80"),
            flow_score=None,
            volatility_score=Decimal("60"),
            positioning_score=Decimal("65"),
        )
    )

    assert result.complete is False
    assert result.regime_model == "CORE_MARKET_ONLY"
    assert result.score is None
    assert result.interpretation is None
    assert result.contributions["flow"] is None
    assert result.reason_codes == (
        "REGIME_SCORE_CORE_INPUT_MISSING",
        "REGIME_SCORE_P1_INPUT_MISSING",
    )


def test_calculate_regime_score_exposes_persistable_payload() -> None:
    result = calculate_regime_score(
        RegimeScoreInput(
            trend_score=Decimal("80"),
            flow_score=Decimal("70"),
            volatility_score=Decimal("60"),
            positioning_score=Decimal("65"),
        ),
        config_metadata={
            "config_version": "strategy_config_v1",
            "strategy_version": "swing_v1.0",
            "parameter_set_id": "default_phase1",
        },
    )

    assert result.as_record() == {
        "feature_id": "REGIME_SCORE",
        "regime_model": "CORE_MARKET_ONLY",
        "score": "72.25",
        "interpretation": "bull",
        "reason_code": "REGIME_SCORE_bull",
        "inputs": {
            "trend": "80",
            "flow": "70",
            "volatility": "60",
            "positioning": "65",
            "macro": None,
            "onchain": None,
            "liquidity": None,
        },
        "weights": {
            "trend": "0.45",
            "flow": "0.25",
            "volatility": "0.15",
            "positioning": "0.15",
        },
        "contributions": {
            "trend": "36.00",
            "flow": "17.50",
            "volatility": "9.00",
            "positioning": "9.75",
        },
        "config_metadata": {
            "config_version": "strategy_config_v1",
            "strategy_version": "swing_v1.0",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": ["REGIME_SCORE_P1_INPUT_MISSING"],
    }


def test_calculate_regime_score_uses_weights_from_versioned_strategy_config() -> None:
    config = load_strategy_config()

    result = calculate_regime_score(
        RegimeScoreInput(
            trend_score=Decimal("80"),
            flow_score=Decimal("70"),
            volatility_score=Decimal("60"),
            positioning_score=Decimal("65"),
        ),
        core_weights=config.scoring_weights.core_regime,
        full_weights=config.scoring_weights.full_regime,
        config_metadata=config.run_metadata(),
    )

    assert result.score == Decimal("72.25")
    assert result.weights == DEFAULT_CORE_REGIME_SCORE_WEIGHTS
    assert result.config_metadata == {
        "config_version": "strategy_config_v1",
        "strategy_version": "swing_v1.0",
        "parameter_set_id": "default_phase1",
    }


def test_calculate_regime_score_rejects_invalid_inputs_and_weights() -> None:
    with pytest.raises(ValueError, match="trend"):
        calculate_regime_score(
            RegimeScoreInput(
                trend_score=Decimal("101"),
                flow_score=Decimal("70"),
                volatility_score=Decimal("60"),
                positioning_score=Decimal("65"),
            )
        )

    with pytest.raises(ValueError, match="core_regime"):
        calculate_regime_score(
            RegimeScoreInput(
                trend_score=Decimal("80"),
                flow_score=Decimal("70"),
                volatility_score=Decimal("60"),
                positioning_score=Decimal("65"),
            ),
            core_weights={"trend": Decimal("1")},
        )

    with pytest.raises(ValueError, match="full_regime"):
        calculate_regime_score(
            RegimeScoreInput(
                trend_score=Decimal("80"),
                flow_score=Decimal("70"),
                volatility_score=Decimal("60"),
                positioning_score=Decimal("65"),
                macro_score=Decimal("50"),
                onchain_score=Decimal("55"),
                liquidity_score=Decimal("45"),
            ),
            full_weights={
                "trend": Decimal("0.35"),
                "flow": Decimal("0.20"),
                "macro": Decimal("0.15"),
                "onchain": Decimal("0.10"),
                "volatility": Decimal("0.10"),
                "liquidity": Decimal("0.05"),
            },
        )


def test_calculate_regime_smoothing_applies_weighted_formula() -> None:
    result = calculate_regime_smoothing(
        RegimeSmoothingInput(
            previous_smoothed_score=Decimal("60"),
            new_regime_score=Decimal("80"),
        ),
    )

    assert result.complete is True
    assert result.score == Decimal("66.00")
    assert result.interpretation == "bull"
    assert result.reason_code == "REGIME_SMOOTHED_SCORE_bull"
    assert result.weights == {
        "previous_smoothed_score": Decimal("0.70"),
        "new_regime_score": Decimal("0.30"),
    }
    assert result.contributions == {
        "previous_smoothed_score": Decimal("42.00"),
        "new_regime_score": Decimal("24.00"),
    }
    assert result.reason_codes == ()


def test_calculate_regime_smoothing_bootstraps_without_previous_score() -> None:
    result = calculate_regime_smoothing(
        RegimeSmoothingInput(
            previous_smoothed_score=None,
            new_regime_score=Decimal("72.25"),
        ),
    )

    assert result.complete is True
    assert result.score == Decimal("72.25")
    assert result.interpretation == "bull"
    assert result.contributions == {
        "previous_smoothed_score": None,
        "new_regime_score": Decimal("72.25"),
    }
    assert result.reason_codes == ("REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING",)


def test_calculate_regime_smoothing_reports_missing_new_score() -> None:
    result = calculate_regime_smoothing(
        RegimeSmoothingInput(
            previous_smoothed_score=Decimal("60"),
            new_regime_score=None,
        ),
    )

    assert result.complete is False
    assert result.score is None
    assert result.interpretation is None
    assert result.reason_code is None
    assert result.contributions == {
        "previous_smoothed_score": None,
        "new_regime_score": None,
    }
    assert result.reason_codes == ("REGIME_SMOOTHING_NEW_SCORE_MISSING",)


def test_calculate_regime_smoothing_exposes_persistable_payload() -> None:
    config = load_strategy_config()

    result = calculate_regime_smoothing(
        RegimeSmoothingInput(
            previous_smoothed_score=Decimal("70"),
            new_regime_score=Decimal("60"),
        ),
        previous_weight=config.regime_smoothing.previous_weight,
        new_weight=config.regime_smoothing.new_weight,
        config_metadata=config.run_metadata(),
    )

    assert result.as_record() == {
        "feature_id": "REGIME_SMOOTHED_SCORE",
        "score": "67.0",
        "interpretation": "bull",
        "reason_code": "REGIME_SMOOTHED_SCORE_bull",
        "inputs": {
            "previous_smoothed_score": "70",
            "new_regime_score": "60",
        },
        "weights": {
            "previous_smoothed_score": "0.7",
            "new_regime_score": "0.3",
        },
        "contributions": {
            "previous_smoothed_score": "49.0",
            "new_regime_score": "18.0",
        },
        "config_metadata": {
            "config_version": "strategy_config_v1",
            "strategy_version": "swing_v1.0",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": [],
    }


def test_calculate_regime_smoothing_rejects_invalid_inputs_and_weights() -> None:
    with pytest.raises(ValueError, match="new_regime_score"):
        calculate_regime_smoothing(
            RegimeSmoothingInput(
                previous_smoothed_score=Decimal("60"),
                new_regime_score=Decimal("101"),
            ),
        )

    with pytest.raises(ValueError, match="previous_smoothed_score"):
        calculate_regime_smoothing(
            RegimeSmoothingInput(
                previous_smoothed_score=Decimal("-1"),
                new_regime_score=Decimal("60"),
            ),
        )

    with pytest.raises(ValueError, match="regime_smoothing"):
        calculate_regime_smoothing(
            RegimeSmoothingInput(
                previous_smoothed_score=Decimal("60"),
                new_regime_score=Decimal("70"),
            ),
            previous_weight=Decimal("0.50"),
            new_weight=Decimal("0.30"),
        )
