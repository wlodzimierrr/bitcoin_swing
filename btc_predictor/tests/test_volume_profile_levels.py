from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.levels import (
    DEFAULT_VOLUME_PROFILE_BIN_SIZE_FRACTION,
    DEFAULT_VOLUME_PROFILE_HVN_VOLUME_FRACTION,
    DEFAULT_VOLUME_PROFILE_MIN_BARS,
    DEFAULT_VOLUME_PROFILE_PRICE_SOURCE,
    DEFAULT_VOLUME_PROFILE_VALUE_AREA_FRACTION,
    VOLUME_PROFILE_HVN,
    VOLUME_PROFILE_LEVEL_FEATURE_ID,
    VOLUME_PROFILE_LEVEL_TYPES,
    VOLUME_PROFILE_POC,
    VOLUME_PROFILE_PRICE_SOURCE_CLOSE,
    VOLUME_PROFILE_PRICE_SOURCE_HLC3,
    VOLUME_PROFILE_PRICE_SOURCES,
    VOLUME_PROFILE_REASON_CODES,
    VOLUME_PROFILE_RESULT_FEATURE_ID,
    VOLUME_PROFILE_VAH,
    VOLUME_PROFILE_VAL,
    VolumeProfileBin,
    calculate_volume_profile_levels,
)


def daily_bar(
    timestamp: datetime,
    *,
    close: str,
    volume: str,
    ingested_at: datetime | None = None,
    provider: str = "coinbase",
    timeframe: str = "1d",
) -> OhlcvBar:
    close_value = Decimal(close)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe=timeframe,
        open=close_value,
        high=close_value,
        low=close_value,
        close=close_value,
        volume=Decimal(volume),
        provider=provider,
        ingested_at=ingested_at or timestamp + timedelta(days=1),
    )


def profile_sample_bars() -> tuple[OhlcvBar, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return (
        daily_bar(start, close="15", volume="10"),
        daily_bar(start + timedelta(days=1), close="25", volume="70"),
        daily_bar(start + timedelta(days=2), close="35", volume="100"),
        daily_bar(start + timedelta(days=3), close="45", volume="80"),
        daily_bar(start + timedelta(days=4), close="55", volume="10"),
        daily_bar(start + timedelta(days=5), close="100", volume="1"),
    )


def test_volume_profile_metadata_is_stable() -> None:
    assert VOLUME_PROFILE_RESULT_FEATURE_ID == "VOLUME_PROFILE_LEVELS"
    assert VOLUME_PROFILE_LEVEL_FEATURE_ID == "VOLUME_PROFILE_LEVEL"
    assert VOLUME_PROFILE_POC == "poc"
    assert VOLUME_PROFILE_HVN == "hvn"
    assert VOLUME_PROFILE_VAH == "vah"
    assert VOLUME_PROFILE_VAL == "val"
    assert VOLUME_PROFILE_LEVEL_TYPES == ("poc", "hvn", "vah", "val")
    assert VOLUME_PROFILE_PRICE_SOURCE_HLC3 == "hlc3"
    assert VOLUME_PROFILE_PRICE_SOURCE_CLOSE == "close"
    assert VOLUME_PROFILE_PRICE_SOURCES == ("hlc3", "close")
    assert DEFAULT_VOLUME_PROFILE_PRICE_SOURCE == "hlc3"
    assert DEFAULT_VOLUME_PROFILE_BIN_SIZE_FRACTION == Decimal("0.01")
    assert DEFAULT_VOLUME_PROFILE_VALUE_AREA_FRACTION == Decimal("0.70")
    assert DEFAULT_VOLUME_PROFILE_HVN_VOLUME_FRACTION == Decimal("0.70")
    assert DEFAULT_VOLUME_PROFILE_MIN_BARS == 20
    assert VOLUME_PROFILE_REASON_CODES == (
        "VOLUME_PROFILE_INPUT_MISSING",
        "VOLUME_PROFILE_INSUFFICIENT_BARS",
        "VOLUME_PROFILE_ZERO_VOLUME",
        "VOLUME_PROFILE_POC",
        "VOLUME_PROFILE_HVN",
        "VOLUME_PROFILE_VALUE_AREA",
        "VOLUME_PROFILE_COMPLETE",
    )


def test_calculates_poc_hvn_vah_and_val_from_available_bars() -> None:
    result = calculate_volume_profile_levels(
        tuple(reversed(profile_sample_bars())),
        as_of=datetime(2026, 1, 7, tzinfo=UTC),
        bin_size_fraction=Decimal("0.10"),
        value_area_fraction=Decimal("0.70"),
        hvn_volume_fraction=Decimal("0.70"),
        min_bar_count=1,
    )

    assert result.complete is True
    assert result.source_bar_count == 6
    assert result.total_volume == Decimal("271")
    assert result.reason_codes == ("VOLUME_PROFILE_COMPLETE",)
    assert [(level.level_type, level.price, level.bin_volume) for level in result.levels] == [
        ("poc", Decimal("35.0"), Decimal("100")),
        ("hvn", Decimal("25.0"), Decimal("70")),
        ("hvn", Decimal("45.0"), Decimal("80")),
        ("vah", Decimal("50.0"), Decimal("80")),
        ("val", Decimal("20.0"), Decimal("70")),
    ]
    assert all(level.bin_size == Decimal("10.00") for level in result.levels)
    assert all(level.value_area_volume == Decimal("250") for level in result.levels)


def test_volume_profile_record_is_reconstructable() -> None:
    result = calculate_volume_profile_levels(
        profile_sample_bars(),
        as_of=datetime(2026, 1, 7, tzinfo=UTC),
        bin_size_fraction=Decimal("0.10"),
        min_bar_count=1,
    )
    record = result.as_record()
    poc = record["levels"][0]

    assert record["feature_id"] == "VOLUME_PROFILE_LEVELS"
    assert record["as_of"] == "2026-01-07T00:00:00+00:00"
    assert record["price_source"] == "hlc3"
    assert record["bin_size_fraction"] == "0.10"
    assert record["value_area_fraction"] == "0.70"
    assert record["hvn_volume_fraction"] == "0.70"
    assert record["min_bar_count"] == 1
    assert record["source_bar_count"] == 6
    assert record["total_volume"] == "271"
    assert record["complete"] is True
    assert record["reason_codes"] == ["VOLUME_PROFILE_COMPLETE"]
    assert poc == {
        "feature_id": "VOLUME_PROFILE_LEVEL",
        "level_type": "poc",
        "price": "35.00",
        "detected_at": "2026-01-07T00:00:00+00:00",
        "profile_start": "2026-01-01T00:00:00+00:00",
        "profile_end": "2026-01-06T00:00:00+00:00",
        "exchange": "coinbase",
        "symbol": "BTC-USD",
        "timeframe": "1d",
        "provider": "coinbase",
        "price_source": "hlc3",
        "bin_size": "10.00",
        "bin_size_fraction": "0.10",
        "bin_lower": "30.00",
        "bin_upper": "40.00",
        "bin_volume": "100",
        "total_volume": "271",
        "value_area_volume": "250",
        "value_area_fraction": "0.70",
        "hvn_volume_fraction": "0.70",
        "source_bar_count": 6,
        "reason_codes": ["VOLUME_PROFILE_POC"],
    }


def test_ignores_future_and_late_ingested_bars() -> None:
    result = calculate_volume_profile_levels(
        (
            daily_bar(datetime(2026, 1, 1, tzinfo=UTC), close="20", volume="100"),
            daily_bar(
                datetime(2026, 1, 2, tzinfo=UTC),
                close="40",
                volume="200",
                ingested_at=datetime(2026, 1, 4, tzinfo=UTC),
            ),
            daily_bar(datetime(2026, 1, 3, tzinfo=UTC), close="60", volume="500"),
        ),
        as_of=datetime(2026, 1, 3, tzinfo=UTC),
        bin_size_fraction=Decimal("0.50"),
        min_bar_count=1,
    )

    assert result.complete is True
    assert result.source_bar_count == 1
    assert [(level.level_type, level.price) for level in result.levels] == [
        ("poc", Decimal("25.0")),
        ("vah", Decimal("30.0")),
        ("val", Decimal("20.0")),
    ]


def test_can_use_close_price_source() -> None:
    result = calculate_volume_profile_levels(
        (
            OhlcvBar(
                timestamp=datetime(2026, 1, 1, tzinfo=UTC),
                exchange="coinbase",
                symbol="BTC-USD",
                timeframe="1d",
                open=Decimal("10"),
                high=Decimal("40"),
                low=Decimal("10"),
                close=Decimal("10"),
                volume=Decimal("100"),
                provider="coinbase",
                ingested_at=datetime(2026, 1, 2, tzinfo=UTC),
            ),
        ),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
        price_source="close",
        bin_size_fraction=Decimal("1"),
        min_bar_count=1,
    )

    assert result.levels[0].level_type == "poc"
    assert result.levels[0].price == Decimal("15")
    assert result.levels[0].price_source == "close"


def test_reports_missing_insufficient_and_zero_volume_inputs() -> None:
    missing = calculate_volume_profile_levels(
        (),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
        min_bar_count=1,
    )
    insufficient = calculate_volume_profile_levels(
        (
            daily_bar(datetime(2026, 1, 1, tzinfo=UTC), close="20", volume="100"),
        ),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
        min_bar_count=2,
    )
    zero_volume = calculate_volume_profile_levels(
        (
            daily_bar(datetime(2026, 1, 1, tzinfo=UTC), close="20", volume="0"),
        ),
        as_of=datetime(2026, 1, 2, tzinfo=UTC),
        min_bar_count=1,
    )

    assert missing.complete is False
    assert missing.reason_codes == ("VOLUME_PROFILE_INPUT_MISSING",)
    assert insufficient.complete is False
    assert insufficient.source_bar_count == 1
    assert insufficient.reason_codes == ("VOLUME_PROFILE_INSUFFICIENT_BARS",)
    assert zero_volume.complete is False
    assert zero_volume.source_bar_count == 1
    assert zero_volume.reason_codes == ("VOLUME_PROFILE_ZERO_VOLUME",)


def test_volume_profile_bin_record_validates_metadata() -> None:
    profile_bin = VolumeProfileBin(
        index=3,
        lower=Decimal("30"),
        upper=Decimal("40"),
        midpoint=Decimal("35"),
        volume=Decimal("100"),
        bar_count=2,
    )

    assert profile_bin.as_record() == {
        "index": 3,
        "lower": "30",
        "upper": "40",
        "midpoint": "35",
        "volume": "100",
        "bar_count": 2,
    }


def test_invalid_inputs_fail_fast() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        calculate_volume_profile_levels((), as_of=datetime(2026, 1, 2))

    with pytest.raises(ValueError, match="price_source"):
        calculate_volume_profile_levels(
            (),
            as_of=datetime(2026, 1, 2, tzinfo=UTC),
            price_source="ohlc4",
        )

    with pytest.raises(ValueError, match="bin_size_fraction"):
        calculate_volume_profile_levels(
            (),
            as_of=datetime(2026, 1, 2, tzinfo=UTC),
            bin_size_fraction=Decimal("0"),
        )

    with pytest.raises(ValueError, match="min_bar_count"):
        calculate_volume_profile_levels(
            (),
            as_of=datetime(2026, 1, 2, tzinfo=UTC),
            min_bar_count=0,
        )

    with pytest.raises(ValueError, match="bar volume"):
        calculate_volume_profile_levels(
            (
                daily_bar(
                    datetime(2026, 1, 1, tzinfo=UTC),
                    close="20",
                    volume="-1",
                ),
            ),
            as_of=datetime(2026, 1, 2, tzinfo=UTC),
            min_bar_count=1,
        )

    with pytest.raises(ValueError, match="single timeframe"):
        calculate_volume_profile_levels(
            (
                daily_bar(datetime(2026, 1, 1, tzinfo=UTC), close="20", volume="100"),
                daily_bar(
                    datetime(2026, 1, 1, tzinfo=UTC),
                    close="20",
                    volume="100",
                    timeframe="1h",
                ),
            ),
            as_of=datetime(2026, 1, 2, tzinfo=UTC),
            min_bar_count=1,
        )

    with pytest.raises(ValueError, match="single market series"):
        calculate_volume_profile_levels(
            (
                daily_bar(datetime(2026, 1, 1, tzinfo=UTC), close="20", volume="100"),
                daily_bar(
                    datetime(2026, 1, 1, tzinfo=UTC),
                    close="20",
                    volume="100",
                    provider="kraken",
                ),
            ),
            as_of=datetime(2026, 1, 2, tzinfo=UTC),
            min_bar_count=1,
        )
