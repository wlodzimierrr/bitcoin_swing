"""EPIC E cross-ticket integration: BTC-040 canonical bars into BTC-041 rolling math.

BTC-040 emits only complete buckets, so a source outage removes a whole session
from the canonical series. BTC-041/BTC-043 read the preceding element as the
preceding period. These tests pin the composition of the two tickets rather
than either one alone.
"""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar, build_canonical_market_bars
from btc_predictor.features import average_true_range, true_ranges


CUTOFF = datetime(2024, 4, 1, tzinfo=UTC)


def hourly_bars(
    day_start: datetime,
    *,
    base: str,
    hours: int = 24,
) -> tuple[OhlcvBar, ...]:
    base_price = Decimal(base)
    return tuple(
        OhlcvBar(
            timestamp=day_start + timedelta(hours=hour),
            exchange="coinbase",
            symbol="BTC-USD",
            timeframe="1h",
            open=base_price + Decimal(hour),
            high=base_price + Decimal(hour) + Decimal("5"),
            low=base_price + Decimal(hour) - Decimal("5"),
            close=base_price + Decimal(hour),
            volume=Decimal("1"),
            provider="coinbase",
            ingested_at=day_start + timedelta(hours=hour + 1),
        )
        for hour in range(hours)
    )


def source_history(
    start: datetime,
    bases: tuple[str, ...],
    *,
    incomplete_days: frozenset[int] = frozenset(),
) -> tuple[OhlcvBar, ...]:
    bars: list[OhlcvBar] = []
    for offset, base in enumerate(bases):
        hours = 23 if offset in incomplete_days else 24
        bars.extend(hourly_bars(start + timedelta(days=offset), base=base, hours=hours))
    return tuple(bars)


def daily_bars(
    source: tuple[OhlcvBar, ...],
    *,
    data_available_at: datetime = CUTOFF,
) -> tuple[OhlcvBar, ...]:
    return build_canonical_market_bars(
        source,
        data_available_at=data_available_at,
        timeframes=("1d",),
    )


def expected_true_ranges(bars: tuple[OhlcvBar, ...]) -> tuple[Decimal, ...]:
    values = [bars[0].high - bars[0].low]
    for previous, current in zip(bars, bars[1:]):
        values.append(
            max(
                current.high - current.low,
                abs(current.high - previous.close),
                abs(current.low - previous.close),
            )
        )
    return tuple(values)


def test_complete_canonical_daily_series_composes_into_true_range_and_atr() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars = daily_bars(source_history(start, ("100", "200", "300", "400")))

    assert tuple(bar.timestamp for bar in bars) == tuple(
        start + timedelta(days=offset) for offset in range(4)
    )
    expected = expected_true_ranges(bars)
    assert true_ranges(bars) == expected
    assert average_true_range(bars, window=2) == (
        None,
        (expected[0] + expected[1]) / 2,
        (expected[1] + expected[2]) / 2,
        (expected[2] + expected[3]) / 2,
    )


def test_a_session_dropped_as_incomplete_stays_missing_instead_of_being_spanned() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    complete = daily_bars(source_history(start, ("100", "200", "300", "400")))
    gapped = daily_bars(
        source_history(
            start,
            ("100", "200", "300", "400"),
            incomplete_days=frozenset({1}),
        )
    )

    # BTC-040 legitimately omits the incomplete session, leaving a gap.
    assert tuple(bar.timestamp for bar in gapped) == (
        start,
        start + timedelta(days=2),
        start + timedelta(days=3),
    )

    ranges = true_ranges(gapped)
    assert ranges[0] == gapped[0].high - gapped[0].low
    assert ranges[1] is None
    assert ranges[2] == max(
        gapped[2].high - gapped[2].low,
        abs(gapped[2].high - gapped[1].close),
        abs(gapped[2].low - gapped[1].close),
    )

    # The absent session must not be absorbed into a plausible ATR either.
    assert average_true_range(gapped, window=2) == (None, None, None)
    assert average_true_range(gapped, window=1) == (
        ranges[0],
        None,
        ranges[2],
    )

    # A gap-spanning range would otherwise be reported as an ordinary one.
    spanning = max(
        gapped[1].high - gapped[1].low,
        abs(gapped[1].high - gapped[0].close),
        abs(gapped[1].low - gapped[0].close),
    )
    assert spanning not in {value for value in ranges if value is not None}
    assert true_ranges(complete)[1] != spanning


def test_canonical_weekly_and_monthly_series_compose_across_calendar_boundaries() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bases = tuple(str(100 + 100 * offset) for offset in range(70))
    source = source_history(start, bases)
    weekly = build_canonical_market_bars(
        source,
        data_available_at=CUTOFF,
        timeframes=("1w",),
    )
    monthly = build_canonical_market_bars(
        source,
        data_available_at=CUTOFF,
        timeframes=("1mo",),
    )

    assert len(weekly) == 10
    assert tuple(bar.timestamp for bar in monthly) == (
        datetime(2024, 1, 1, tzinfo=UTC),
        datetime(2024, 2, 1, tzinfo=UTC),
    )
    assert true_ranges(weekly) == expected_true_ranges(weekly)
    assert true_ranges(monthly) == expected_true_ranges(monthly)
    assert average_true_range(monthly, window=2)[-1] is not None


def test_a_dropped_calendar_month_is_reported_as_missing_not_spanned() -> None:
    december = OhlcvBar(
        timestamp=datetime(2023, 12, 1, tzinfo=UTC),
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1mo",
        open=Decimal("50"),
        high=Decimal("60"),
        low=Decimal("40"),
        close=Decimal("55"),
        volume=Decimal("1"),
        provider="coinbase",
        ingested_at=CUTOFF,
    )
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bases = tuple(str(100 + 100 * offset) for offset in range(70))
    february = build_canonical_market_bars(
        source_history(start, bases, incomplete_days=frozenset({10})),
        data_available_at=CUTOFF,
        timeframes=("1mo",),
    )

    assert tuple(bar.timestamp for bar in february) == (
        datetime(2024, 2, 1, tzinfo=UTC),
    )
    assert true_ranges((december, *february)) == (
        december.high - december.low,
        None,
    )


def test_future_source_bars_never_change_earlier_composed_atr() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bases = tuple(str(100 + 100 * offset) for offset in range(8))
    source = source_history(start, bases)
    early_cutoff = start + timedelta(days=4)

    early = daily_bars(source, data_available_at=early_cutoff)
    late = daily_bars(source)

    assert tuple(bar.timestamp for bar in late)[: len(early)] == tuple(
        bar.timestamp for bar in early
    )
    assert average_true_range(late, window=3)[: len(early)] == average_true_range(
        early,
        window=3,
    )
    assert true_ranges(late)[: len(early)] == true_ranges(early)


def test_mixed_timeframes_and_repeated_sessions_are_refused() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bases = tuple(str(100 + 100 * offset) for offset in range(14))
    derived = build_canonical_market_bars(
        source_history(start, bases),
        data_available_at=CUTOFF,
        timeframes=("1d", "1w"),
    )

    with pytest.raises(ValueError, match="one bar timeframe"):
        average_true_range(derived, window=2)

    daily = tuple(bar for bar in derived if bar.timeframe == "1d")
    with pytest.raises(ValueError, match="regularly spaced"):
        true_ranges((*daily, daily[-1]))
