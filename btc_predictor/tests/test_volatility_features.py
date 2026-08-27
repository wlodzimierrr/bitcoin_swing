from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.features import (
    DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS,
    REALIZED_VOLATILITY_FEATURE_IDS,
    REALIZED_VOLATILITY_REASON_CODES,
    REALIZED_VOLATILITY_WINDOWS,
    RV_7_FEATURE_ID,
    RV_20_FEATURE_ID,
    RV_60_FEATURE_ID,
    realized_volatility_from_daily_bars,
    rv_7_20_60_from_daily_bars,
)


def daily_bar(
    timestamp: datetime,
    *,
    close: str,
    ingested_at: datetime | None = None,
    timeframe: str = "1d",
) -> OhlcvBar:
    close_value = Decimal(close)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC/USD",
        timeframe=timeframe,
        open=close_value,
        high=close_value,
        low=close_value,
        close=close_value,
        volume=Decimal("100"),
        provider="coinbase",
        ingested_at=ingested_at or timestamp + timedelta(minutes=5),
    )


def daily_bars(closes: tuple[str, ...]) -> tuple[OhlcvBar, ...]:
    start = datetime(2026, 1, 1, tzinfo=UTC)
    return tuple(
        daily_bar(start + timedelta(days=index), close=close)
        for index, close in enumerate(closes)
    )


def compounding_daily_bars(
    *,
    count: int,
    returns: tuple[Decimal, ...] = (
        Decimal("0.01"),
        Decimal("-0.005"),
        Decimal("0.007"),
        Decimal("0"),
    ),
) -> tuple[OhlcvBar, ...]:
    closes = [Decimal("100")]
    for index in range(count - 1):
        closes.append(closes[-1] * (Decimal("1") + returns[index % len(returns)]))
    return daily_bars(tuple(str(close) for close in closes))


def test_realized_volatility_metadata_is_stable() -> None:
    assert RV_7_FEATURE_ID == "RV_7"
    assert RV_20_FEATURE_ID == "RV_20"
    assert RV_60_FEATURE_ID == "RV_60"
    assert REALIZED_VOLATILITY_WINDOWS == (7, 20, 60)
    assert REALIZED_VOLATILITY_FEATURE_IDS == {
        7: "RV_7",
        20: "RV_20",
        60: "RV_60",
    }
    assert DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS == 365
    assert REALIZED_VOLATILITY_REASON_CODES == (
        "REALIZED_VOLATILITY_INPUT_MISSING",
        "REALIZED_VOLATILITY_INSUFFICIENT_HISTORY",
        "REALIZED_VOLATILITY_NON_POSITIVE_CLOSE",
    )


def test_realized_volatility_uses_close_to_close_returns() -> None:
    rows = daily_bars(("100", "110", "99", "108.9"))

    result = realized_volatility_from_daily_bars(
        tuple(reversed(rows)),
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        window_days=3,
        annualization_periods=1,
    )

    assert result.complete is True
    assert result.feature_id == "RV_3"
    assert result.observation_time == datetime(2026, 1, 4, tzinfo=UTC)
    assert result.window_days == 3
    assert result.annualization_periods == 1
    assert result.realized_volatility is not None
    assert result.realized_volatility.quantize(Decimal("0.000001")) == Decimal("0.094281")
    assert result.return_count == 3
    assert result.source_bar_count == 4
    assert result.reason_codes == ()


def test_rv_7_20_60_from_daily_bars_returns_default_windows() -> None:
    rows = compounding_daily_bars(count=62)

    results = rv_7_20_60_from_daily_bars(
        tuple(reversed(rows)),
        as_of=datetime(2026, 3, 3, 1, tzinfo=UTC),
    )

    assert tuple(result.feature_id for result in results) == ("RV_7", "RV_20", "RV_60")
    assert tuple(result.window_days for result in results) == (7, 20, 60)
    assert tuple(result.return_count for result in results) == (7, 20, 60)
    assert all(result.complete for result in results)
    assert all(result.realized_volatility is not None for result in results)


def test_realized_volatility_filters_unavailable_future_bars() -> None:
    rows = daily_bars(("100", "110", "99", "108.9"))
    future_revision = daily_bar(
        datetime(2026, 1, 4, tzinfo=UTC),
        close="999",
        ingested_at=datetime(2026, 1, 5, tzinfo=UTC),
    )

    baseline = realized_volatility_from_daily_bars(
        rows,
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        window_days=3,
        annualization_periods=1,
    ).as_record()
    with_future = realized_volatility_from_daily_bars(
        (*rows, future_revision),
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        window_days=3,
        annualization_periods=1,
    ).as_record()

    assert with_future == baseline


def test_realized_volatility_reports_missing_input_without_zero_fill() -> None:
    result = realized_volatility_from_daily_bars(
        (),
        as_of=datetime(2026, 1, 4, tzinfo=UTC),
        window_days=3,
    )

    assert result.complete is False
    assert result.realized_volatility is None
    assert result.return_count == 0
    assert result.source_bar_count == 0
    assert result.reason_codes == ("REALIZED_VOLATILITY_INPUT_MISSING",)


def test_realized_volatility_reports_insufficient_history() -> None:
    result = realized_volatility_from_daily_bars(
        daily_bars(("100", "110", "99")),
        as_of=datetime(2026, 1, 3, 1, tzinfo=UTC),
        window_days=3,
    )

    assert result.complete is False
    assert result.realized_volatility is None
    assert result.return_count == 0
    assert result.source_bar_count == 3
    assert result.reason_codes == ("REALIZED_VOLATILITY_INSUFFICIENT_HISTORY",)


def test_realized_volatility_reports_non_positive_close() -> None:
    result = realized_volatility_from_daily_bars(
        daily_bars(("100", "110", "0", "108.9")),
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        window_days=3,
    )

    assert result.complete is False
    assert result.realized_volatility is None
    assert result.return_count == 0
    assert result.reason_codes == ("REALIZED_VOLATILITY_NON_POSITIVE_CLOSE",)


def test_realized_volatility_exposes_persistable_payload() -> None:
    result = realized_volatility_from_daily_bars(
        daily_bars(("100", "110", "99", "108.9")),
        as_of=datetime(2026, 1, 4, 1, tzinfo=UTC),
        window_days=3,
        annualization_periods=1,
    )

    record = result.as_record()
    assert record["feature_id"] == "RV_3"
    assert record["observation_time"] == "2026-01-04T00:00:00+00:00"
    assert record["window_days"] == 3
    assert record["annualization_periods"] == 1
    assert record["realized_volatility"] == str(result.realized_volatility)
    assert record["return_count"] == 3
    assert record["source_bar_count"] == 4
    assert record["complete"] is True
    assert record["reason_codes"] == []


def test_realized_volatility_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="as_of must be timezone-aware UTC"):
        realized_volatility_from_daily_bars((), as_of=datetime(2026, 1, 4), window_days=3)

    with pytest.raises(ValueError, match="window_days"):
        realized_volatility_from_daily_bars(
            (),
            as_of=datetime(2026, 1, 4, tzinfo=UTC),
            window_days=0,
        )

    with pytest.raises(ValueError, match="annualization_periods"):
        realized_volatility_from_daily_bars(
            (),
            as_of=datetime(2026, 1, 4, tzinfo=UTC),
            window_days=3,
            annualization_periods=0,
        )

    with pytest.raises(ValueError, match="canonical 1d bars"):
        realized_volatility_from_daily_bars(
            (daily_bar(datetime(2026, 1, 1, tzinfo=UTC), close="100", timeframe="1h"),),
            as_of=datetime(2026, 1, 4, tzinfo=UTC),
            window_days=3,
        )
