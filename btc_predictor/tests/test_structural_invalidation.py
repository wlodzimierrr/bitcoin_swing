"""BTC-140: structural invalidation level selection."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.risk import (
    BEARISH_DISTRIBUTION_SETUP,
    BULL_TREND_CONTINUATION_SETUP,
    BULLISH_RESET_SETUP,
    CAPITULATION_REVERSAL_SETUP,
    DEFAULT_MAX_INVALIDATION_DISTANCE_FRACTION,
    DEFAULT_MIN_CLUSTER_CONFLUENCE,
    DEFAULT_MIN_CLUSTER_MEMBER_COUNT,
    INVALIDATION_PARAMETER_STATUS,
    SELECTION_FARTHEST,
    SELECTION_NEAREST,
    SETUP_INVALIDATION_POLICY,
    STRUCTURAL_INVALIDATION_FEATURE_ID,
    STRUCTURAL_INVALIDATION_POLICY_VERSION,
    STRUCTURAL_INVALIDATION_REASON_CODES,
    StructuralInvalidationResult,
    select_structural_invalidation,
)

AS_OF = datetime(2026, 6, 1, tzinfo=UTC)
DETECTED = datetime(2026, 1, 1, tzinfo=UTC)


def cluster(
    cluster_id: str,
    lower: str,
    upper: str,
    *,
    zone_type: str = "support",
    confluence: str = "75",
    member_count: int = 3,
    detected_at: datetime = DETECTED,
) -> dict[str, object]:
    return {
        "feature_id": "LEVEL_CLUSTER",
        "cluster_id": cluster_id,
        "zone_type": zone_type,
        "lower_bound": lower,
        "upper_bound": upper,
        "center_price": str((Decimal(lower) + Decimal(upper)) / 2),
        "confluence_score": confluence,
        "member_count": member_count,
        "detected_at": detected_at,
    }


def long_clusters() -> list[dict[str, object]]:
    return [
        cluster("near", "95", "97"),
        cluster("mid", "91", "93"),
        cluster("far", "88", "90"),
        cluster("above", "105", "107", zone_type="resistance"),
    ]


def select(clusters, setup, **kwargs):
    return select_structural_invalidation(
        clusters,
        setup=setup,
        entry_price=kwargs.pop("entry_price", "100"),
        as_of=kwargs.pop("as_of", AS_OF),
        **kwargs,
    )


def test_metadata_is_stable() -> None:
    assert STRUCTURAL_INVALIDATION_FEATURE_ID == "STRUCTURAL_INVALIDATION"
    assert STRUCTURAL_INVALIDATION_POLICY_VERSION == "STRUCTURAL_INVALIDATION_V1"
    assert INVALIDATION_PARAMETER_STATUS == "PROVISIONAL_RESEARCH_CALIBRATABLE"
    assert DEFAULT_MAX_INVALIDATION_DISTANCE_FRACTION == Decimal("0.15")
    assert DEFAULT_MIN_CLUSTER_CONFLUENCE == Decimal("50")
    assert DEFAULT_MIN_CLUSTER_MEMBER_COUNT == 2
    assert SETUP_INVALIDATION_POLICY == {
        BULL_TREND_CONTINUATION_SETUP: ("long", SELECTION_NEAREST),
        BULLISH_RESET_SETUP: ("long", SELECTION_NEAREST),
        CAPITULATION_REVERSAL_SETUP: ("long", SELECTION_FARTHEST),
        BEARISH_DISTRIBUTION_SETUP: ("short", SELECTION_NEAREST),
    }


# --- setup-specific selection -------------------------------------------


@pytest.mark.parametrize(
    "setup", [BULL_TREND_CONTINUATION_SETUP, BULLISH_RESET_SETUP]
)
def test_trend_setups_take_the_nearest_qualifying_support(setup: str) -> None:
    result = select(long_clusters(), setup)

    assert result.complete is True
    assert result.direction == "long"
    assert result.selected_cluster_id == "near"
    # Zone-based: the invalidation sits at the far edge, not the centre.
    assert result.invalidation_price == Decimal("95")
    assert result.distance_fraction == Decimal("0.05")
    assert result.reason_codes == ("STRUCTURAL_INVALIDATION_SELECTED",)


def test_capitulation_reversal_takes_a_wide_thesis_stop() -> None:
    result = select(long_clusters(), CAPITULATION_REVERSAL_SETUP)

    # A washout buy expects nearby structure to be probed, so the thesis stop
    # is the farthest still-qualifying zone rather than the tightest.
    assert result.selection_mode == SELECTION_FARTHEST
    assert result.selected_cluster_id == "far"
    assert result.invalidation_price == Decimal("88")
    assert result.distance_fraction == Decimal("0.12")


def test_bearish_distribution_selects_resistance_above_entry() -> None:
    clusters = [
        cluster("res_near", "103", "105", zone_type="resistance"),
        cluster("res_far", "110", "112", zone_type="resistance"),
        cluster("sup", "95", "97"),
    ]

    result = select(clusters, BEARISH_DISTRIBUTION_SETUP)

    assert result.direction == "short"
    assert result.selected_cluster_id == "res_near"
    # Short invalidation is the upper edge of the resistance zone.
    assert result.invalidation_price == Decimal("105")
    assert result.distance_fraction == Decimal("0.05")


def test_long_and_short_use_opposite_zone_edges() -> None:
    long_result = select([cluster("s", "95", "97")], BULL_TREND_CONTINUATION_SETUP)
    short_result = select(
        [cluster("r", "103", "105", zone_type="resistance")],
        BEARISH_DISTRIBUTION_SETUP,
    )

    assert long_result.invalidation_price == long_result.selected_zone_lower_bound
    assert short_result.invalidation_price == short_result.selected_zone_upper_bound


# --- eligibility filters -------------------------------------------------


def test_zones_on_the_wrong_side_of_entry_are_rejected() -> None:
    # A "support" zone straddling or above entry cannot invalidate a long.
    result = select([cluster("straddle", "99", "101")], BULL_TREND_CONTINUATION_SETUP)

    assert result.complete is False
    assert result.invalidation_price is None
    assert "STRUCTURAL_INVALIDATION_NO_CANDIDATE" in result.reason_codes
    assert "STRUCTURAL_INVALIDATION_WRONG_SIDE" in result.reason_codes


def test_zones_beyond_the_max_distance_are_rejected() -> None:
    result = select([cluster("distant", "70", "72")], BULL_TREND_CONTINUATION_SETUP)

    assert result.complete is False
    assert "STRUCTURAL_INVALIDATION_BEYOND_MAX_DISTANCE" in result.reason_codes
    assert result.candidates[0].eligible is False


def test_low_confluence_or_thin_zones_are_rejected() -> None:
    thin = select(
        [cluster("thin", "95", "97", confluence="20")],
        BULL_TREND_CONTINUATION_SETUP,
    )
    lonely = select(
        [cluster("lonely", "95", "97", member_count=1)],
        BULL_TREND_CONTINUATION_SETUP,
    )

    for result in (thin, lonely):
        assert result.complete is False
        assert "STRUCTURAL_INVALIDATION_BELOW_MIN_CONFLUENCE" in result.reason_codes


def test_a_weak_near_zone_defers_to_a_stronger_farther_zone() -> None:
    clusters = [
        cluster("weak_near", "96", "98", confluence="10"),
        cluster("strong_mid", "92", "94"),
    ]

    result = select(clusters, BULL_TREND_CONTINUATION_SETUP)

    # Proximity alone must not win; the thesis stop needs real structure.
    assert result.selected_cluster_id == "strong_mid"
    assert result.invalidation_price == Decimal("92")
    rejected = {item.cluster_id: item for item in result.candidates}
    assert rejected["weak_near"].eligible is False


# --- point-in-time -------------------------------------------------------


def test_levels_detected_after_as_of_are_not_usable() -> None:
    clusters = [
        cluster("future", "95", "97", detected_at=AS_OF + timedelta(hours=1)),
        cluster("known", "92", "94"),
    ]

    result = select(clusters, BULL_TREND_CONTINUATION_SETUP)

    assert result.selected_cluster_id == "known"
    future = {item.cluster_id: item for item in result.candidates}["future"]
    assert future.eligible is False
    assert future.rejection_reason == "STRUCTURAL_INVALIDATION_NOT_YET_DETECTED"


def test_a_level_detected_exactly_at_as_of_is_usable() -> None:
    result = select(
        [cluster("boundary", "95", "97", detected_at=AS_OF)],
        BULL_TREND_CONTINUATION_SETUP,
    )

    assert result.complete is True
    assert result.selected_cluster_id == "boundary"


# --- missing inputs and unsupported setups -------------------------------


@pytest.mark.parametrize("clusters", [[], None, {"clusters": []}])
def test_missing_structure_is_reported_not_guessed(clusters) -> None:
    result = select(clusters, BULL_TREND_CONTINUATION_SETUP)

    assert result.complete is False
    assert result.invalidation_price is None
    assert "STRUCTURAL_INVALIDATION_INPUT_MISSING" in result.reason_codes


def test_unsupported_setup_is_rejected_without_a_level() -> None:
    result = select(long_clusters(), "MEAN_REVERSION_SCALP")

    assert result.complete is False
    assert result.invalidation_price is None
    assert result.reason_codes == ("STRUCTURAL_INVALIDATION_UNSUPPORTED_SETUP",)


def test_no_support_below_entry_yields_no_invalidation() -> None:
    result = select(
        [cluster("res", "105", "107", zone_type="resistance")],
        BULL_TREND_CONTINUATION_SETUP,
    )

    assert result.complete is False
    assert result.reason_codes == ("STRUCTURAL_INVALIDATION_NO_CANDIDATE",)


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"entry_price": "0"}, "entry_price must be positive"),
        ({"max_distance_fraction": "0"}, "max_distance_fraction must be positive"),
        ({"min_confluence": "150"}, "min_confluence must be between"),
        ({"min_member_count": 0}, "min_member_count must be >= 1"),
    ],
)
def test_invalid_parameters_fail_fast(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        select(long_clusters(), BULL_TREND_CONTINUATION_SETUP, **kwargs)


# --- determinism and persistence ----------------------------------------


def test_selection_is_independent_of_input_ordering() -> None:
    clusters = long_clusters()
    forward = select(clusters, BULL_TREND_CONTINUATION_SETUP)
    reversed_ = select(list(reversed(clusters)), BULL_TREND_CONTINUATION_SETUP)

    assert forward.as_record() == reversed_.as_record()


def test_ties_are_broken_deterministically_by_cluster_id() -> None:
    clusters = [cluster("b_zone", "95", "97"), cluster("a_zone", "95", "97")]

    result = select(clusters, BULL_TREND_CONTINUATION_SETUP)

    assert result.selected_cluster_id == "a_zone"
    assert [item.cluster_id for item in result.candidates] == ["a_zone", "b_zone"]


def test_recomputation_is_deterministic() -> None:
    first = select(long_clusters(), BULL_TREND_CONTINUATION_SETUP)
    second = select(long_clusters(), BULL_TREND_CONTINUATION_SETUP)

    assert first.as_record() == second.as_record()


def test_record_persists_every_candidate_and_its_verdict() -> None:
    result = select(
        long_clusters(),
        BULL_TREND_CONTINUATION_SETUP,
        atr="4",
        config_metadata={"config_version": "strategy_config_v2"},
    )
    record = result.as_record()

    assert isinstance(result, StructuralInvalidationResult)
    assert record["feature_id"] == "STRUCTURAL_INVALIDATION"
    assert record["policy_version"] == "STRUCTURAL_INVALIDATION_V1"
    assert record["setup"] == BULL_TREND_CONTINUATION_SETUP
    assert record["invalidation_price"] == "95"
    assert record["selected_cluster_id"] == "near"
    assert record["config_metadata"] == {"config_version": "strategy_config_v2"}
    assert record["thresholds"]["max_distance_fraction"] == "0.15"
    # Every considered zone is reconstructable, including the rejected ones.
    considered = {item["cluster_id"] for item in record["candidates"]}
    assert considered == {"near", "mid", "far"}
    assert all(item["rejection_reason"] is None for item in record["candidates"])
    assert record["atr_distance"] == "1.25"
    assert all(item["atr_distance"] is not None for item in record["candidates"])


def test_atr_distance_is_diagnostic_only_and_optional() -> None:
    without_atr = select(long_clusters(), BULL_TREND_CONTINUATION_SETUP)
    with_atr = select(long_clusters(), BULL_TREND_CONTINUATION_SETUP, atr="4")

    # BTC-140 selects a level only; the ATR reading never moves the selection.
    # Converting it into a buffer or a stop is BTC-141/BTC-142.
    assert without_atr.atr_distance is None
    assert with_atr.atr_distance == Decimal("1.25")
    assert without_atr.invalidation_price == with_atr.invalidation_price
    assert without_atr.selected_cluster_id == with_atr.selected_cluster_id


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        select(long_clusters(), BULL_TREND_CONTINUATION_SETUP),
        select([], BULL_TREND_CONTINUATION_SETUP),
        select(long_clusters(), "UNKNOWN"),
        select([cluster("straddle", "99", "101")], BULL_TREND_CONTINUATION_SETUP),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in STRUCTURAL_INVALIDATION_REASON_CODES


def test_accepts_cluster_objects_exposing_as_record() -> None:
    class Cluster:
        def __init__(self, payload: dict[str, object]) -> None:
            self._payload = payload

        def as_record(self) -> dict[str, object]:
            return self._payload

    result = select(
        [Cluster(cluster("obj", "95", "97"))],
        BULL_TREND_CONTINUATION_SETUP,
    )

    assert result.selected_cluster_id == "obj"
    assert result.invalidation_price == Decimal("95")
