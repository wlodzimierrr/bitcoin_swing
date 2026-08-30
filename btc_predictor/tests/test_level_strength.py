from decimal import Decimal

import pytest

from btc_predictor.levels import (
    DEFAULT_LEVEL_STRENGTH_REACTION_FULL_FRACTION,
    DEFAULT_LEVEL_STRENGTH_TIMEFRAME_SCORES,
    DEFAULT_LEVEL_STRENGTH_TOUCH_COUNT_FULL,
    DEFAULT_LEVEL_STRENGTH_WEIGHTS,
    LEVEL_STRENGTH_COMPONENT_IDS,
    LEVEL_STRENGTH_FEATURE_ID,
    LEVEL_STRENGTH_REASON_CODES,
    LevelStrengthInput,
    calculate_level_strength,
    calculate_level_strength_from_cluster,
)


def cluster_record() -> dict[str, object]:
    return {
        "feature_id": "LEVEL_CLUSTER",
        "cluster_id": "LEVEL_CLUSTER:support:test",
        "zone_type": "support",
        "confluence_score": "75",
        "member_count": 2,
        "members": [
            {"source_timeframe": "1w"},
            {"source_timeframe": "1d"},
        ],
    }


def test_level_strength_metadata_is_stable() -> None:
    assert LEVEL_STRENGTH_FEATURE_ID == "LEVEL_STRENGTH"
    assert LEVEL_STRENGTH_COMPONENT_IDS == (
        "timeframe",
        "touch_count",
        "reaction_magnitude",
        "volume",
        "confluence",
    )
    assert DEFAULT_LEVEL_STRENGTH_WEIGHTS == {
        "timeframe": Decimal("0.20"),
        "touch_count": Decimal("0.20"),
        "reaction_magnitude": Decimal("0.20"),
        "volume": Decimal("0.20"),
        "confluence": Decimal("0.20"),
    }
    assert DEFAULT_LEVEL_STRENGTH_TIMEFRAME_SCORES == {
        "1h": Decimal("40"),
        "1d": Decimal("65"),
        "1w": Decimal("85"),
        "1mo": Decimal("100"),
        "unknown": Decimal("50"),
    }
    assert DEFAULT_LEVEL_STRENGTH_TOUCH_COUNT_FULL == 4
    assert DEFAULT_LEVEL_STRENGTH_REACTION_FULL_FRACTION == Decimal("0.10")
    assert LEVEL_STRENGTH_REASON_CODES == (
        "LEVEL_STRENGTH_INPUT_MISSING",
        "LEVEL_STRENGTH_TOUCH_COUNT_CAPPED",
        "LEVEL_STRENGTH_REACTION_CAPPED",
        "LEVEL_STRENGTH_COMPLETE",
    )


def test_calculates_level_strength_from_explicit_inputs() -> None:
    result = calculate_level_strength(
        LevelStrengthInput(
            timeframes=("1d", "1w"),
            touch_count=3,
            reaction_magnitude_fraction=Decimal("0.05"),
            volume_percentile=Decimal("80"),
            confluence_score=Decimal("75"),
        ),
        level_id="level-1",
        zone_type="support",
        config_metadata={"parameter_set_id": "default_phase1"},
    )

    assert result.complete is True
    assert result.score == Decimal("73.00")
    assert result.interpretation == "watch"
    assert result.component_scores == {
        "timeframe": Decimal("85"),
        "touch_count": Decimal("75.00"),
        "reaction_magnitude": Decimal("50.0"),
        "volume": Decimal("80"),
        "confluence": Decimal("75"),
    }
    assert result.reason_codes == ("LEVEL_STRENGTH_COMPLETE",)


def test_calculates_level_strength_from_cluster_record() -> None:
    result = calculate_level_strength_from_cluster(
        cluster_record(),
        touch_count=4,
        reaction_magnitude_fraction="0.08",
        volume_percentile="90",
    )

    assert result.complete is True
    assert result.level_id == "LEVEL_CLUSTER:support:test"
    assert result.zone_type == "support"
    assert result.inputs.timeframes == ("1d", "1w")
    assert result.component_scores["timeframe"] == Decimal("85")
    assert result.component_scores["touch_count"] == Decimal("100")
    assert result.component_scores["reaction_magnitude"] == Decimal("80.0")
    assert result.score == Decimal("86.00")
    assert result.interpretation == "strong"


def test_missing_inputs_return_incomplete_result() -> None:
    result = calculate_level_strength(
        LevelStrengthInput(
            timeframes=("1w",),
            touch_count=2,
            reaction_magnitude_fraction=None,
            volume_percentile=Decimal("50"),
            confluence_score=Decimal("70"),
        ),
        level_id="level-1",
    )

    assert result.complete is False
    assert result.score is None
    assert result.interpretation is None
    assert result.component_scores["reaction_magnitude"] is None
    assert result.reason_codes == ("LEVEL_STRENGTH_INPUT_MISSING",)


def test_touch_count_and_reaction_scores_are_capped() -> None:
    result = calculate_level_strength(
        LevelStrengthInput(
            timeframes=("1mo",),
            touch_count=8,
            reaction_magnitude_fraction=Decimal("0.25"),
            volume_percentile=Decimal("100"),
            confluence_score=Decimal("100"),
        ),
        level_id="level-1",
    )

    assert result.complete is True
    assert result.score == Decimal("100.00")
    assert result.interpretation == "major"
    assert result.component_scores["touch_count"] == Decimal("100")
    assert result.component_scores["reaction_magnitude"] == Decimal("100")
    assert result.reason_codes == (
        "LEVEL_STRENGTH_TOUCH_COUNT_CAPPED",
        "LEVEL_STRENGTH_REACTION_CAPPED",
        "LEVEL_STRENGTH_COMPLETE",
    )


def test_level_strength_record_is_reconstructable() -> None:
    result = calculate_level_strength_from_cluster(
        cluster_record(),
        reaction_magnitude_fraction="0.08",
        volume_percentile="90",
        config_metadata={
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
    )

    assert result.as_record() == {
        "feature_id": "LEVEL_STRENGTH",
        "level_id": "LEVEL_CLUSTER:support:test",
        "zone_type": "support",
        "score": "76.000",
        "interpretation": "strong",
        "inputs": {
            "timeframes": ["1d", "1w"],
            "touch_count": 2,
            "reaction_magnitude_fraction": "0.08",
            "volume_percentile": "90",
            "confluence_score": "75",
        },
        "component_scores": {
            "timeframe": "85",
            "touch_count": "50.0",
            "reaction_magnitude": "80.0",
            "volume": "90",
            "confluence": "75",
        },
        "weights": {
            "timeframe": "0.20",
            "touch_count": "0.20",
            "reaction_magnitude": "0.20",
            "volume": "0.20",
            "confluence": "0.20",
        },
        "timeframe_scores": {
            "1h": "40",
            "1d": "65",
            "1w": "85",
            "1mo": "100",
            "unknown": "50",
        },
        "touch_count_full": 4,
        "reaction_full_fraction": "0.10",
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": ["LEVEL_STRENGTH_COMPLETE"],
    }


def test_invalid_inputs_fail_fast() -> None:
    with pytest.raises(ValueError, match="level_id"):
        calculate_level_strength(
            LevelStrengthInput(
                timeframes=("1w",),
                touch_count=1,
                reaction_magnitude_fraction=Decimal("0.05"),
                volume_percentile=Decimal("50"),
                confluence_score=Decimal("50"),
            ),
            level_id="",
        )

    with pytest.raises(ValueError, match="timeframes"):
        calculate_level_strength(
            LevelStrengthInput(
                timeframes=("",),
                touch_count=1,
                reaction_magnitude_fraction=Decimal("0.05"),
                volume_percentile=Decimal("50"),
                confluence_score=Decimal("50"),
            ),
            level_id="level-1",
        )

    with pytest.raises(ValueError, match="volume_percentile"):
        calculate_level_strength(
            LevelStrengthInput(
                timeframes=("1w",),
                touch_count=1,
                reaction_magnitude_fraction=Decimal("0.05"),
                volume_percentile=Decimal("101"),
                confluence_score=Decimal("50"),
            ),
            level_id="level-1",
        )

    with pytest.raises(ValueError, match="weights"):
        calculate_level_strength(
            LevelStrengthInput(
                timeframes=("1w",),
                touch_count=1,
                reaction_magnitude_fraction=Decimal("0.05"),
                volume_percentile=Decimal("50"),
                confluence_score=Decimal("50"),
            ),
            level_id="level-1",
            weights={"timeframe": Decimal("1")},
        )

    with pytest.raises(ValueError, match="timeframe_scores"):
        calculate_level_strength(
            LevelStrengthInput(
                timeframes=("1w",),
                touch_count=1,
                reaction_magnitude_fraction=Decimal("0.05"),
                volume_percentile=Decimal("50"),
                confluence_score=Decimal("50"),
            ),
            level_id="level-1",
            timeframe_scores={"1w": Decimal("85")},
        )

    with pytest.raises(ValueError, match="member_count"):
        calculate_level_strength_from_cluster(
            {
                "cluster_id": "bad",
                "confluence_score": "75",
                "member_count": -1,
                "members": [],
            },
            reaction_magnitude_fraction="0.08",
            volume_percentile="90",
        )
