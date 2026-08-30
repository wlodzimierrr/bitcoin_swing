from datetime import UTC, datetime
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.levels import (
    LEVEL_CLUSTER_FEATURE_ID,
    LevelCluster,
    LevelClusterMember,
    cluster_price_levels,
)
from btc_predictor.signals import (
    DEFAULT_NO_CHASE_DISTANCE_MODE,
    DEFAULT_NO_CHASE_MAX_DISTANCE_ATR,
    DEFAULT_NO_CHASE_MAX_DISTANCE_FRACTION,
    NO_CHASE_DIRECTIONS,
    NO_CHASE_DISTANCE_MODES,
    NO_CHASE_EFFECTS,
    NO_CHASE_FEATURE_ID,
    NO_CHASE_REASON_CODES,
    apply_no_chase_filter,
)


ZONE_DETECTED_AT = datetime(2026, 1, 10, tzinfo=UTC)
PRICE_TIME = datetime(2026, 1, 11, tzinfo=UTC)


def entry_zone(
    *,
    zone_type: str = "support",
    lower: str = "95",
    upper: str = "100",
    detected_at: datetime = ZONE_DETECTED_AT,
) -> LevelCluster:
    level_type = "swing_low" if zone_type == "support" else "swing_high"
    member = LevelClusterMember(
        member_id=f"weekly:{level_type}",
        feature_id="WEEKLY_SWING_LEVEL",
        level_type=level_type,
        price=Decimal(lower if zone_type == "support" else upper),
        detected_at=detected_at,
        exchange="coinbase",
        symbol="BTC-USD",
        provider="coinbase",
        source_timestamp=datetime(2026, 1, 1, tzinfo=UTC),
        source_timeframe="1w",
    )
    return LevelCluster(
        feature_id=LEVEL_CLUSTER_FEATURE_ID,
        cluster_id=f"{zone_type}-zone",
        zone_type=zone_type,
        lower_bound=Decimal(lower),
        upper_bound=Decimal(upper),
        center_price=(Decimal(lower) + Decimal(upper)) / Decimal("2"),
        reference_price=Decimal("105"),
        detected_at=detected_at,
        cluster_distance_fraction=Decimal("0.025"),
        minimum_level_strength=Decimal("60"),
        confluence_score=Decimal("70"),
        member_count=1,
        unique_source_count=1,
        unique_timeframe_count=1,
        members=(member,),
        reason_codes=("LEVEL_CLUSTER_COMPLETE",),
    )


def test_no_chase_metadata_is_stable() -> None:
    assert NO_CHASE_FEATURE_ID == "NO_CHASE_FILTER"
    assert NO_CHASE_DIRECTIONS == ("long", "short")
    assert NO_CHASE_DISTANCE_MODES == ("atr", "fractional")
    assert NO_CHASE_EFFECTS == ("NO_TRADE",)
    assert DEFAULT_NO_CHASE_DISTANCE_MODE == "atr"
    assert DEFAULT_NO_CHASE_MAX_DISTANCE_ATR == Decimal("0.50")
    assert DEFAULT_NO_CHASE_MAX_DISTANCE_FRACTION == Decimal("0.02")
    assert NO_CHASE_REASON_CODES == (
        "NO_CHASE_ATR_MISSING",
        "NO_CHASE_WITHIN_ENTRY_ZONE",
        "NO_CHASE_DISTANCE_ACCEPTABLE",
        "NO_CHASE_VIOLATION",
    )


def test_no_chase_passes_price_inside_long_entry_zone_without_atr() -> None:
    result = apply_no_chase_filter(
        entry_zone(),
        current_price="99",
        current_price_available_at=PRICE_TIME,
        as_of=PRICE_TIME,
    )

    assert result.complete is True
    assert result.violated is False
    assert result.blocked is False
    assert result.effects == ()
    assert result.chase_boundary == Decimal("100")
    assert result.chase_distance_price == Decimal("0")
    assert result.normalized_distance == Decimal("0")
    assert result.reason_codes == ("NO_CHASE_WITHIN_ENTRY_ZONE",)


@pytest.mark.parametrize(
    ("price", "expected_distance"),
    [("104", Decimal("0.4")), ("105", Decimal("0.5"))],
)
def test_no_chase_allows_atr_distance_through_exact_threshold(
    price: str,
    expected_distance: Decimal,
) -> None:
    result = apply_no_chase_filter(
        entry_zone(),
        current_price=price,
        current_price_available_at=PRICE_TIME,
        as_of=PRICE_TIME,
        atr="10",
        atr_available_at=ZONE_DETECTED_AT,
    )

    assert result.complete is True
    assert result.violated is False
    assert result.blocked is False
    assert result.normalized_distance == expected_distance
    assert result.reason_codes == ("NO_CHASE_DISTANCE_ACCEPTABLE",)


def test_no_chase_blocks_long_price_above_atr_threshold() -> None:
    config = load_strategy_config()
    result = apply_no_chase_filter(
        entry_zone(),
        current_price="105.1",
        current_price_available_at=PRICE_TIME,
        as_of=PRICE_TIME,
        atr="10",
        atr_available_at=ZONE_DETECTED_AT,
        config_metadata=config.run_metadata(),
    )

    assert result.complete is True
    assert result.violated is True
    assert result.blocked is True
    assert result.effects == ("NO_TRADE",)
    assert result.chase_distance_price == pytest.approx(Decimal("5.1"))
    assert result.normalized_distance == pytest.approx(Decimal("0.51"))
    assert result.reason_codes == ("NO_CHASE_VIOLATION",)
    record = result.as_record()
    assert record["entry_zone"] == entry_zone().as_record()
    assert record["effects"] == ["NO_TRADE"]
    assert record["config_metadata"] == config.run_metadata()


def test_no_chase_fails_closed_when_chased_price_has_no_atr() -> None:
    result = apply_no_chase_filter(
        entry_zone(),
        current_price="103",
        current_price_available_at=PRICE_TIME,
        as_of=PRICE_TIME,
    )

    assert result.complete is False
    assert result.violated is False
    assert result.blocked is True
    assert result.effects == ("NO_TRADE",)
    assert result.normalized_distance is None
    assert result.reason_codes == ("NO_CHASE_ATR_MISSING",)


def test_no_chase_fractional_mode_has_strict_boundary() -> None:
    exact = apply_no_chase_filter(
        entry_zone(),
        current_price="102.0408163265306",
        current_price_available_at=PRICE_TIME,
        as_of=PRICE_TIME,
        distance_mode="fractional",
    )
    violation = apply_no_chase_filter(
        entry_zone(),
        current_price="102.1",
        current_price_available_at=PRICE_TIME,
        as_of=PRICE_TIME,
        distance_mode="fractional",
    )

    assert exact.normalized_distance == pytest.approx(Decimal("0.02"))
    assert exact.blocked is False
    assert violation.normalized_distance == Decimal("0.02056807051909887")
    assert violation.blocked is True
    assert violation.reason_codes == ("NO_CHASE_VIOLATION",)


@pytest.mark.parametrize(
    ("price", "expected_blocked", "expected_distance"),
    [
        ("101", False, Decimal("0")),
        ("96", False, Decimal("0.4")),
        ("94", True, Decimal("0.6")),
    ],
)
def test_no_chase_mirrors_distance_for_short_entries(
    price: str,
    expected_blocked: bool,
    expected_distance: Decimal,
) -> None:
    result = apply_no_chase_filter(
        entry_zone(zone_type="resistance", lower="100", upper="105"),
        current_price=price,
        current_price_available_at=PRICE_TIME,
        as_of=PRICE_TIME,
        direction="short",
        atr="10",
        atr_available_at=ZONE_DETECTED_AT,
    )

    assert result.blocked is expected_blocked
    assert result.normalized_distance == expected_distance
    assert result.effects == (("NO_TRADE",) if expected_blocked else ())


def test_no_chase_consumes_btc_095_cluster_without_adapter() -> None:
    clustered = cluster_price_levels(
        (
            {
                "feature_id": "WEEKLY_SWING_LEVEL",
                "level_type": "swing_low",
                "price": "99",
                "detected_at": ZONE_DETECTED_AT.isoformat(),
                "level_timestamp": "2026-01-01T00:00:00+00:00",
                "exchange": "coinbase",
                "symbol": "BTC-USD",
                "timeframe": "1w",
                "provider": "coinbase",
            },
            {
                "feature_id": "MONTHLY_SWING_LEVEL",
                "level_type": "swing_low",
                "price": "100",
                "detected_at": ZONE_DETECTED_AT.isoformat(),
                "level_timestamp": "2025-12-01T00:00:00+00:00",
                "exchange": "coinbase",
                "symbol": "BTC-USD",
                "timeframe": "1mo",
                "provider": "coinbase",
            },
        ),
        as_of=PRICE_TIME,
        reference_price="105",
    )
    support = next(zone for zone in clustered.clusters if zone.zone_type == "support")

    result = apply_no_chase_filter(
        support,
        current_price="106",
        current_price_available_at=PRICE_TIME,
        as_of=PRICE_TIME,
        atr="10",
        atr_available_at=ZONE_DETECTED_AT,
    )

    assert result.entry_zone is support
    assert result.chase_boundary == Decimal("100")
    assert result.normalized_distance == Decimal("0.6")
    assert result.blocked is True


def test_no_chase_is_deterministic() -> None:
    kwargs = {
        "current_price": "104",
        "current_price_available_at": PRICE_TIME,
        "as_of": PRICE_TIME,
        "atr": "10",
        "atr_available_at": ZONE_DETECTED_AT,
    }

    first = apply_no_chase_filter(entry_zone(), **kwargs)
    second = apply_no_chase_filter(entry_zone(), **kwargs)

    assert first.as_record() == second.as_record()


def test_no_chase_rejects_invalid_inputs() -> None:
    zone = entry_zone()
    with pytest.raises(ValueError, match="direction"):
        apply_no_chase_filter(
            zone,
            current_price="100",
            current_price_available_at=PRICE_TIME,
            as_of=PRICE_TIME,
            direction="flat",
        )
    with pytest.raises(ValueError, match="requires resistance"):
        apply_no_chase_filter(
            zone,
            current_price="100",
            current_price_available_at=PRICE_TIME,
            as_of=PRICE_TIME,
            direction="short",
        )
    with pytest.raises(ValueError, match="distance_mode"):
        apply_no_chase_filter(
            zone,
            current_price="100",
            current_price_available_at=PRICE_TIME,
            as_of=PRICE_TIME,
            distance_mode="absolute",
        )
    with pytest.raises(ValueError, match="available by as_of"):
        apply_no_chase_filter(
            entry_zone(detected_at=datetime(2026, 1, 12, tzinfo=UTC)),
            current_price="100",
            current_price_available_at=PRICE_TIME,
            as_of=PRICE_TIME,
        )
    with pytest.raises(ValueError, match="between zone detection and as_of"):
        apply_no_chase_filter(
            zone,
            current_price="100",
            current_price_available_at=datetime(2026, 1, 9, tzinfo=UTC),
            as_of=PRICE_TIME,
        )
    with pytest.raises(ValueError, match="supplied together"):
        apply_no_chase_filter(
            zone,
            current_price="103",
            current_price_available_at=PRICE_TIME,
            as_of=PRICE_TIME,
            atr="10",
        )
    with pytest.raises(ValueError, match="current price time"):
        apply_no_chase_filter(
            zone,
            current_price="103",
            current_price_available_at=PRICE_TIME,
            as_of=PRICE_TIME,
            atr="10",
            atr_available_at=datetime(2026, 1, 12, tzinfo=UTC),
        )
    with pytest.raises(ValueError, match="only valid in atr"):
        apply_no_chase_filter(
            zone,
            current_price="103",
            current_price_available_at=PRICE_TIME,
            as_of=PRICE_TIME,
            distance_mode="fractional",
            atr="10",
            atr_available_at=ZONE_DETECTED_AT,
        )
