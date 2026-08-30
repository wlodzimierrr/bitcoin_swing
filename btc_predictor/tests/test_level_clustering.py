from datetime import UTC, datetime
from decimal import Decimal

import pytest

from btc_predictor.levels import (
    DEFAULT_LEVEL_CLUSTER_ATR_DISTANCE_THRESHOLD,
    DEFAULT_LEVEL_CLUSTER_DISTANCE_FRACTION,
    DEFAULT_LEVEL_CLUSTER_MINIMUM_STRENGTH,
    LEVEL_CLUSTER_FEATURE_ID,
    LEVEL_CLUSTER_REASON_CODES,
    LEVEL_CLUSTER_RESISTANCE,
    LEVEL_CLUSTER_RESULT_FEATURE_ID,
    LEVEL_CLUSTER_SUPPORT,
    LEVEL_CLUSTER_TOUCH_BONUS_MAX,
    LEVEL_CLUSTER_ZONE_TYPES,
    LevelClusterMember,
    cluster_price_levels,
)


def level_record(
    *,
    feature_id: str,
    level_type: str,
    price: str,
    detected_at: datetime = datetime(2026, 1, 10, tzinfo=UTC),
    level_timestamp: datetime = datetime(2026, 1, 1, tzinfo=UTC),
    timeframe: str = "1d",
    provider: str = "coinbase",
) -> dict[str, str]:
    return {
        "feature_id": feature_id,
        "level_type": level_type,
        "price": price,
        "detected_at": detected_at.isoformat(),
        "level_timestamp": level_timestamp.isoformat(),
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "timeframe": timeframe,
        "provider": provider,
    }


def anchored_vwap_record(
    *,
    vwap: str | None = "95",
    complete: bool = True,
) -> dict[str, str | bool | None]:
    return {
        "feature_id": "ANCHORED_VWAP",
        "anchor_type": "major_swing_low",
        "anchor_timestamp": "2026-01-01T00:00:00+00:00",
        "as_of": "2026-01-10T00:00:00+00:00",
        "vwap": vwap,
        "complete": complete,
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "provider": "coinbase",
        "source_timeframe": "1w",
    }


def test_level_cluster_metadata_is_stable() -> None:
    assert LEVEL_CLUSTER_RESULT_FEATURE_ID == "LEVEL_CLUSTERS"
    assert LEVEL_CLUSTER_FEATURE_ID == "LEVEL_CLUSTER"
    assert LEVEL_CLUSTER_SUPPORT == "support"
    assert LEVEL_CLUSTER_RESISTANCE == "resistance"
    assert LEVEL_CLUSTER_ZONE_TYPES == ("support", "resistance")
    assert DEFAULT_LEVEL_CLUSTER_DISTANCE_FRACTION == Decimal("0.025")
    assert DEFAULT_LEVEL_CLUSTER_ATR_DISTANCE_THRESHOLD == Decimal("0.50")
    assert DEFAULT_LEVEL_CLUSTER_MINIMUM_STRENGTH == Decimal("60")
    assert LEVEL_CLUSTER_TOUCH_BONUS_MAX == Decimal("10")
    assert LEVEL_CLUSTER_REASON_CODES == (
        "LEVEL_CLUSTER_INPUT_MISSING",
        "LEVEL_CLUSTER_SOURCE_NOT_READY",
        "LEVEL_CLUSTER_INCOMPLETE_SOURCE_SKIPPED",
        "LEVEL_CLUSTER_DUPLICATE_MEMBER_SKIPPED",
        "LEVEL_CLUSTER_COMPLETE",
    )


def test_optional_atr_clustering_preserves_persistence_api() -> None:
    levels = (
        level_record(
            feature_id="WEEKLY_SWING_LEVEL",
            level_type="swing_low",
            price="100",
        ),
        level_record(
            feature_id="MONTHLY_SWING_LEVEL",
            level_type="swing_low",
            price="104",
        ),
    )
    fractional = cluster_price_levels(
        levels,
        as_of=datetime(2026, 1, 11, tzinfo=UTC),
        reference_price="110",
    )
    atr_normalized = cluster_price_levels(
        levels,
        as_of=datetime(2026, 1, 11, tzinfo=UTC),
        reference_price="110",
        cluster_atr="10",
        cluster_atr_distance_threshold="0.5",
    )

    assert len(fractional.clusters) == 2
    assert len(atr_normalized.clusters) == 1
    assert atr_normalized.clusters[0].member_count == 2
    assert atr_normalized.as_record().keys() == fractional.as_record().keys()


def test_clusters_nearby_levels_into_support_and_resistance_zones() -> None:
    support_swing = level_record(
        feature_id="WEEKLY_SWING_LEVEL",
        level_type="swing_low",
        price="95",
        timeframe="1w",
    )
    support_volume = level_record(
        feature_id="VOLUME_PROFILE_LEVEL",
        level_type="val",
        price="95",
    )
    resistance_monthly = level_record(
        feature_id="MONTHLY_SWING_LEVEL",
        level_type="swing_high",
        price="120",
        timeframe="1mo",
    )
    resistance_breakout = level_record(
        feature_id="BREAKOUT_RECLAIM_LEVEL",
        level_type="breakout",
        price="122",
    )

    result = cluster_price_levels(
        (
            support_swing,
            support_volume,
            support_volume,
            resistance_breakout,
            resistance_monthly,
        ),
        as_of=datetime(2026, 1, 11, tzinfo=UTC),
        reference_price=Decimal("100"),
        cluster_distance_fraction=Decimal("0.025"),
        minimum_level_strength=Decimal("60"),
    )

    assert result.complete is True
    assert result.source_level_count == 5
    assert result.accepted_member_count == 4
    assert result.skipped_duplicate_count == 1
    assert result.reason_codes == (
        "LEVEL_CLUSTER_DUPLICATE_MEMBER_SKIPPED",
        "LEVEL_CLUSTER_COMPLETE",
    )
    zones = {cluster.zone_type: cluster for cluster in result.clusters}
    support = zones["support"]
    resistance = zones["resistance"]
    assert support.lower_bound == Decimal("95")
    assert support.upper_bound == Decimal("95")
    assert support.center_price == Decimal("95")
    assert support.confluence_score == Decimal("75")
    assert support.member_count == 2
    assert support.unique_source_count == 2
    assert support.unique_timeframe_count == 2
    assert [member.feature_id for member in support.members] == [
        "VOLUME_PROFILE_LEVEL",
        "WEEKLY_SWING_LEVEL",
    ]
    assert resistance.lower_bound == Decimal("120")
    assert resistance.upper_bound == Decimal("122")
    assert resistance.center_price.quantize(Decimal("0.0001")) == Decimal("120.9167")
    assert resistance.confluence_score == Decimal("75")
    assert resistance.member_count == 2


def test_clusters_anchored_vwap_result_as_level_member() -> None:
    result = cluster_price_levels(
        (
            anchored_vwap_record(),
            level_record(
                feature_id="VOLUME_PROFILE_LEVEL",
                level_type="poc",
                price="96",
            ),
        ),
        as_of=datetime(2026, 1, 11, tzinfo=UTC),
        reference_price="100",
    )

    assert result.complete is True
    assert len(result.clusters) == 1
    cluster = result.clusters[0]
    assert cluster.zone_type == "support"
    assert cluster.lower_bound == Decimal("95")
    assert cluster.upper_bound == Decimal("96")
    assert cluster.unique_source_count == 2
    assert [member.level_type for member in cluster.members] == [
        "major_swing_low",
        "poc",
    ]


def test_volume_profile_result_members_are_expanded() -> None:
    result = cluster_price_levels(
        (
            {
                "feature_id": "VOLUME_PROFILE_LEVELS",
                "complete": True,
                "levels": [
                    level_record(
                        feature_id="VOLUME_PROFILE_LEVEL",
                        level_type="poc",
                        price="95",
                    ),
                    level_record(
                        feature_id="VOLUME_PROFILE_LEVEL",
                        level_type="vah",
                        price="121",
                    ),
                ],
            },
        ),
        as_of=datetime(2026, 1, 11, tzinfo=UTC),
        reference_price="100",
    )

    assert result.complete is True
    assert result.source_level_count == 2
    assert result.accepted_member_count == 2
    assert [cluster.zone_type for cluster in result.clusters] == [
        "resistance",
        "support",
    ]


def test_skips_future_incomplete_and_empty_sources_explicitly() -> None:
    future_level = level_record(
        feature_id="WEEKLY_SWING_LEVEL",
        level_type="swing_low",
        price="95",
        detected_at=datetime(2026, 1, 12, tzinfo=UTC),
    )

    skipped = cluster_price_levels(
        (
            future_level,
            anchored_vwap_record(vwap=None, complete=False),
        ),
        as_of=datetime(2026, 1, 11, tzinfo=UTC),
        reference_price="100",
    )
    empty = cluster_price_levels(
        (),
        as_of=datetime(2026, 1, 11, tzinfo=UTC),
        reference_price="100",
    )

    assert skipped.complete is False
    assert skipped.source_level_count == 2
    assert skipped.skipped_future_count == 1
    assert skipped.skipped_incomplete_count == 1
    assert skipped.reason_codes == (
        "LEVEL_CLUSTER_SOURCE_NOT_READY",
        "LEVEL_CLUSTER_INCOMPLETE_SOURCE_SKIPPED",
    )
    assert empty.complete is False
    assert empty.reason_codes == ("LEVEL_CLUSTER_INPUT_MISSING",)


def test_level_cluster_record_is_reconstructable() -> None:
    result = cluster_price_levels(
        (
            level_record(
                feature_id="WEEKLY_SWING_LEVEL",
                level_type="swing_low",
                price="95",
                timeframe="1w",
            ),
            level_record(
                feature_id="VOLUME_PROFILE_LEVEL",
                level_type="val",
                price="95",
            ),
        ),
        as_of=datetime(2026, 1, 11, tzinfo=UTC),
        reference_price="100",
    )
    record = result.as_record()
    cluster = record["clusters"][0]

    assert record["feature_id"] == "LEVEL_CLUSTERS"
    assert record["as_of"] == "2026-01-11T00:00:00+00:00"
    assert record["reference_price"] == "100"
    assert record["cluster_distance_fraction"] == "0.025"
    assert record["minimum_level_strength"] == "60"
    assert record["source_level_count"] == 2
    assert record["accepted_member_count"] == 2
    assert record["complete"] is True
    assert record["reason_codes"] == ["LEVEL_CLUSTER_COMPLETE"]
    assert cluster["feature_id"] == "LEVEL_CLUSTER"
    assert cluster["cluster_id"].startswith("LEVEL_CLUSTER:support:")
    assert cluster["zone_type"] == "support"
    assert cluster["lower_bound"] == "95"
    assert cluster["upper_bound"] == "95"
    assert cluster["center_price"] == "95"
    assert cluster["reference_price"] == "100"
    assert cluster["confluence_score"] == "75"
    assert cluster["member_count"] == 2
    assert len(cluster["members"]) == 2
    assert {
        member["member_id"] for member in cluster["members"]
    } == {
        "WEEKLY_SWING_LEVEL|swing_low|2026-01-01T00:00:00+00:00|95|coinbase|BTC-USD|coinbase",
        "VOLUME_PROFILE_LEVEL|val|2026-01-01T00:00:00+00:00|95|coinbase|BTC-USD|coinbase",
    }


def test_direct_level_cluster_member_is_supported() -> None:
    member = LevelClusterMember(
        member_id="manual|1",
        feature_id="MANUAL_LEVEL",
        level_type="support",
        price=Decimal("95"),
        detected_at=datetime(2026, 1, 10, tzinfo=UTC),
        exchange="coinbase",
        symbol="BTC-USD",
        provider="coinbase",
        source_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        source_timeframe="1d",
    )

    result = cluster_price_levels(
        (member,),
        as_of=datetime(2026, 1, 11, tzinfo=UTC),
        reference_price="100",
    )

    assert result.complete is True
    assert result.clusters[0].members[0].member_id == "manual|1"


def test_invalid_inputs_fail_fast() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        cluster_price_levels((), as_of=datetime(2026, 1, 11), reference_price="100")

    with pytest.raises(ValueError, match="reference_price"):
        cluster_price_levels(
            (),
            as_of=datetime(2026, 1, 11, tzinfo=UTC),
            reference_price="0",
        )

    with pytest.raises(ValueError, match="cluster_distance_fraction"):
        cluster_price_levels(
            (),
            as_of=datetime(2026, 1, 11, tzinfo=UTC),
            reference_price="100",
            cluster_distance_fraction="0",
        )

    with pytest.raises(ValueError, match="minimum_level_strength"):
        cluster_price_levels(
            (),
            as_of=datetime(2026, 1, 11, tzinfo=UTC),
            reference_price="100",
            minimum_level_strength="101",
        )

    with pytest.raises(ValueError, match="one exchange/symbol/provider"):
        cluster_price_levels(
            (
                level_record(
                    feature_id="WEEKLY_SWING_LEVEL",
                    level_type="swing_low",
                    price="95",
                ),
                level_record(
                    feature_id="VOLUME_PROFILE_LEVEL",
                    level_type="val",
                    price="95",
                    provider="kraken",
                ),
            ),
            as_of=datetime(2026, 1, 11, tzinfo=UTC),
            reference_price="100",
        )
