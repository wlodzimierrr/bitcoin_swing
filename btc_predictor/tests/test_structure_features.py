from decimal import Decimal

import pytest

from btc_predictor.features import (
    DEFAULT_ENTRY_LOCATION_FULL_SCORE_DISTANCE_FRACTION,
    DEFAULT_ENTRY_LOCATION_ZERO_SCORE_DISTANCE_FRACTION,
    DEFAULT_RR_MINIMUM,
    DEFAULT_RR_PREFERRED_MAX,
    DEFAULT_RR_PREFERRED_MIN,
    DEFAULT_STRUCTURE_SCORE_WEIGHTS,
    STRUCTURE_SCORE_COMPONENT_IDS,
    STRUCTURE_SCORE_FEATURE_ID,
    STRUCTURE_SCORE_REASON_CODES,
    StructureScoreInput,
    calculate_structure_score,
    calculate_structure_score_from_clusters,
)


def support_cluster() -> dict[str, object]:
    return {
        "feature_id": "LEVEL_CLUSTER",
        "cluster_id": "LEVEL_CLUSTER:support:phase1",
        "zone_type": "support",
        "lower_bound": "95",
        "upper_bound": "99",
        "center_price": "97",
        "confluence_score": "75",
        "member_count": 3,
        "members": [
            {"feature_id": "WEEKLY_SWING_LEVEL", "source_timeframe": "1w"},
            {"feature_id": "MONTHLY_SWING_LEVEL", "source_timeframe": "1mo"},
            {"feature_id": "BREAKOUT_RECLAIM_LEVEL", "source_timeframe": "1d"},
        ],
    }


def target_cluster() -> dict[str, object]:
    return {
        "feature_id": "LEVEL_CLUSTER",
        "cluster_id": "LEVEL_CLUSTER:resistance:phase1",
        "zone_type": "resistance",
        "lower_bound": "124",
        "upper_bound": "126",
        "center_price": "125",
        "confluence_score": "70",
        "member_count": 2,
        "members": [
            {"feature_id": "WEEKLY_SWING_LEVEL", "source_timeframe": "1w"},
            {"feature_id": "MONTHLY_SWING_LEVEL", "source_timeframe": "1mo"},
        ],
    }


def cluster_result() -> dict[str, object]:
    return {
        "feature_id": "LEVEL_CLUSTERS",
        "complete": True,
        "clusters": [target_cluster(), support_cluster()],
    }


def test_structure_score_metadata_is_stable() -> None:
    assert STRUCTURE_SCORE_FEATURE_ID == "STRUCTURE_SCORE"
    assert STRUCTURE_SCORE_COMPONENT_IDS == (
        "level_strength",
        "entry_location",
        "rr_quality",
        "confluence",
    )
    assert DEFAULT_STRUCTURE_SCORE_WEIGHTS == {
        "level_strength": Decimal("0.45"),
        "entry_location": Decimal("0.25"),
        "rr_quality": Decimal("0.20"),
        "confluence": Decimal("0.10"),
    }
    assert DEFAULT_ENTRY_LOCATION_FULL_SCORE_DISTANCE_FRACTION == Decimal("0.01")
    assert DEFAULT_ENTRY_LOCATION_ZERO_SCORE_DISTANCE_FRACTION == Decimal("0.08")
    assert DEFAULT_RR_MINIMUM == Decimal("2.0")
    assert DEFAULT_RR_PREFERRED_MIN == Decimal("2.5")
    assert DEFAULT_RR_PREFERRED_MAX == Decimal("3.0")
    assert STRUCTURE_SCORE_REASON_CODES == (
        "STRUCTURE_SCORE_INPUT_MISSING",
        "STRUCTURE_SCORE_SUPPORT_MISSING",
        "STRUCTURE_SCORE_TARGET_MISSING",
        "STRUCTURE_SCORE_INVALID_RISK",
        "STRUCTURE_SCORE_COMPLETE",
    )


def test_calculates_structure_score_from_explicit_components() -> None:
    result = calculate_structure_score(
        StructureScoreInput(
            level_strength=Decimal("80"),
            entry_location=Decimal("70"),
            rr_quality=Decimal("90"),
            confluence=Decimal("75"),
        ),
        config_metadata={"parameter_set_id": "default_phase1"},
    )

    assert result.complete is True
    assert result.score == Decimal("79.00")
    assert result.interpretation == "constructive"
    assert result.reason_code == "STRUCTURE_SCORE_constructive"
    assert result.contributions == {
        "level_strength": Decimal("36.00"),
        "entry_location": Decimal("17.50"),
        "rr_quality": Decimal("18.00"),
        "confluence": Decimal("7.50"),
    }
    assert result.reason_codes == ("STRUCTURE_SCORE_COMPLETE",)


def test_calculates_phase1_structure_score_from_clusters_without_p1_level_evidence() -> None:
    result = calculate_structure_score_from_clusters(
        cluster_result(),
        entry_price="100",
        stop_price="90",
        level_strength_score="80",
    )

    assert result.complete is True
    assert result.score == Decimal("85.50")
    assert result.interpretation == "strong"
    assert result.inputs.as_record() == {
        "level_strength": "80",
        "entry_location": "100",
        "rr_quality": "85",
        "confluence": "75",
    }
    assert result.selection.support_cluster_id == "LEVEL_CLUSTER:support:phase1"
    assert result.selection.target_cluster_id == "LEVEL_CLUSTER:resistance:phase1"
    assert result.selection.reward_risk == Decimal("2.5")


def test_selects_nearest_support_and_nearest_resistance_target() -> None:
    lower_support = dict(support_cluster(), center_price="80", upper_bound="82")
    farther_target = dict(target_cluster(), cluster_id="farther", center_price="150")

    result = calculate_structure_score_from_clusters(
        (farther_target, target_cluster(), lower_support, support_cluster()),
        entry_price="100",
        stop_price="90",
        level_strength_score="80",
    )

    assert result.selection.support_cluster_id == "LEVEL_CLUSTER:support:phase1"
    assert result.selection.target_cluster_id == "LEVEL_CLUSTER:resistance:phase1"


def test_uses_complete_level_strength_result_input() -> None:
    result = calculate_structure_score_from_clusters(
        cluster_result(),
        entry_price="100",
        stop_price="90",
        level_strength_result={
            "feature_id": "LEVEL_STRENGTH",
            "score": "82",
            "complete": True,
        },
    )

    assert result.complete is True
    assert result.inputs.level_strength == Decimal("82")
    assert result.score == Decimal("86.400")


def test_missing_required_inputs_are_reported_explicitly() -> None:
    missing_strength = calculate_structure_score_from_clusters(
        cluster_result(),
        entry_price="100",
        stop_price="90",
    )
    missing_support = calculate_structure_score_from_clusters(
        (target_cluster(),),
        entry_price="100",
        stop_price="90",
        level_strength_score="80",
    )
    missing_target = calculate_structure_score_from_clusters(
        (support_cluster(),),
        entry_price="100",
        stop_price="90",
        level_strength_score="80",
    )

    assert missing_strength.complete is False
    assert missing_strength.reason_codes == ("STRUCTURE_SCORE_INPUT_MISSING",)
    assert missing_support.complete is False
    assert missing_support.reason_codes == (
        "STRUCTURE_SCORE_SUPPORT_MISSING",
        "STRUCTURE_SCORE_INPUT_MISSING",
    )
    assert missing_target.complete is False
    assert missing_target.inputs.entry_location == Decimal("100")
    assert missing_target.reason_codes == (
        "STRUCTURE_SCORE_TARGET_MISSING",
        "STRUCTURE_SCORE_INPUT_MISSING",
    )


def test_invalid_risk_is_reported_without_silent_rr_score() -> None:
    result = calculate_structure_score_from_clusters(
        cluster_result(),
        entry_price="100",
        stop_price="101",
        level_strength_score="80",
    )

    assert result.complete is False
    assert result.inputs.rr_quality is None
    assert result.selection.reward_risk is None
    assert result.reason_codes == (
        "STRUCTURE_SCORE_INVALID_RISK",
        "STRUCTURE_SCORE_INPUT_MISSING",
    )


def test_structure_score_record_is_reconstructable() -> None:
    result = calculate_structure_score_from_clusters(
        cluster_result(),
        entry_price="100",
        stop_price="90",
        level_strength_score="80",
        config_metadata={
            "config_version": "strategy_config_v1",
            "strategy_version": "swing_v1.0",
            "parameter_set_id": "default_phase1",
        },
    )

    assert result.as_record() == {
        "feature_id": "STRUCTURE_SCORE",
        "score": "85.50",
        "interpretation": "strong",
        "reason_code": "STRUCTURE_SCORE_strong",
        "inputs": {
            "level_strength": "80",
            "entry_location": "100",
            "rr_quality": "85",
            "confluence": "75",
        },
        "weights": {
            "level_strength": "0.45",
            "entry_location": "0.25",
            "rr_quality": "0.20",
            "confluence": "0.10",
        },
        "contributions": {
            "level_strength": "36.00",
            "entry_location": "25.00",
            "rr_quality": "17.00",
            "confluence": "7.50",
        },
        "selection": {
            "support_cluster_id": "LEVEL_CLUSTER:support:phase1",
            "support_center_price": "97",
            "support_lower_bound": "95",
            "support_upper_bound": "99",
            "target_cluster_id": "LEVEL_CLUSTER:resistance:phase1",
            "target_center_price": "125",
            "target_lower_bound": "124",
            "target_upper_bound": "126",
            "entry_price": "100",
            "stop_price": "90",
            "reward_risk": "2.5",
        },
        "entry_location_parameters": {
            "full_score_distance_fraction": "0.01",
            "zero_score_distance_fraction": "0.08",
        },
        "rr_parameters": {
            "rr_minimum": "2.0",
            "rr_preferred_min": "2.5",
            "rr_preferred_max": "3.0",
        },
        "config_metadata": {
            "config_version": "strategy_config_v1",
            "strategy_version": "swing_v1.0",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": ["STRUCTURE_SCORE_COMPLETE"],
    }


def test_invalid_inputs_fail_fast() -> None:
    with pytest.raises(ValueError, match="level_strength"):
        calculate_structure_score(
            StructureScoreInput(
                level_strength=Decimal("101"),
                entry_location=Decimal("70"),
                rr_quality=Decimal("90"),
                confluence=Decimal("75"),
            ),
        )

    with pytest.raises(ValueError, match="structure score weights"):
        calculate_structure_score(
            StructureScoreInput(
                level_strength=Decimal("80"),
                entry_location=Decimal("70"),
                rr_quality=Decimal("90"),
                confluence=Decimal("75"),
            ),
            weights={"level_strength": Decimal("1")},
        )

    with pytest.raises(ValueError, match="zero_score_distance_fraction"):
        calculate_structure_score_from_clusters(
            cluster_result(),
            entry_price="100",
            stop_price="90",
            level_strength_score="80",
            entry_location_zero_score_distance_fraction="0.01",
        )

    with pytest.raises(ValueError, match="rr_preferred_max"):
        calculate_structure_score_from_clusters(
            cluster_result(),
            entry_price="100",
            stop_price="90",
            level_strength_score="80",
            rr_preferred_max="2.0",
        )

    with pytest.raises(ValueError, match="entry_price"):
        calculate_structure_score_from_clusters(
            cluster_result(),
            entry_price="0",
            stop_price="90",
            level_strength_score="80",
        )
