"""BTC-221 look-ahead bias suite.

Rulebook v1.2 section 3A.2 requires ``available_at <= decision_time`` for every
input reaching a decision, naming price observations, ETF flows, confirmed swing
levels, AVWAP anchors, and all derived features.

The owner suites already prove that each engine filters its own inputs. This
suite proves the stronger replay property those filters exist for:

- a result computed at a decision time from the full universe is identical to
  the same result computed from a universe physically truncated to what was
  available at that decision time, and
- appending future observations never rewrites an earlier decision.

Both halves are needed. Truncation equivalence alone cannot see an engine that
ignores its cutoff, and append invariance alone is satisfied vacuously by an
engine that ignores its inputs.
"""

from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

import numpy as np
import pytest

from btc_predictor.data import (
    EtfFlow,
    OhlcvBar,
    build_canonical_market_bars,
    next_bar_timestamp,
)
from btc_predictor.features import (
    RealizedVolatilityResult,
    etf_flow_acceleration,
    five_day_etf_flow,
    realized_volatility_from_daily_bars,
    twenty_day_etf_flow,
    volatility_percentile,
)
from btc_predictor.features import rolling as domain_rolling
from btc_predictor.levels import (
    ANCHOR_MAJOR_SWING_HIGH,
    ANCHOR_MAJOR_SWING_LOW,
    AnchoredVwapAnchor,
    anchored_vwap_anchor_from_swing_level,
    calculate_anchored_vwap,
    detect_monthly_swing_levels,
    detect_weekly_swing_levels,
)
from btc_predictor.quant.rolling import (
    average_true_range,
    historical_normalize,
    realized_volatility,
    rolling_mean,
    rolling_percentile,
    rolling_volatility,
    rolling_zscore,
)


EXCHANGE = "coinbase"
SYMBOL = "BTC-USD"
PROVIDER = "coinbase"
INGESTION_LAG = timedelta(minutes=5)

# 2026-01-05 is a Monday, so hourly bars from this instant fill whole canonical
# daily and weekly sessions.
SERIES_START = datetime(2026, 1, 5, tzinfo=UTC)

# Weekly levels chosen so the confirmed pivots are unambiguous: a strict swing
# low at index 3 and a strict swing high at index 6 under the default 3/3
# confirmation window, and no other index qualifies.
WEEKLY_LEVELS = (130, 122, 114, 100, 118, 126, 140, 124, 116, 108, 104)

# Monthly levels with a strict swing low at index 2 and a strict swing high at
# index 4 under the default 2/2 confirmation window.
MONTHLY_START = datetime(2026, 1, 1, tzinfo=UTC)
MONTHLY_LEVELS = (140, 130, 100, 120, 132, 118, 110)

ETF_FUNDS = ("AAA", "BBB")
ETF_FIRST_OBSERVATION_DATE = date(2026, 2, 2)
ETF_BUSINESS_DAY_COUNT = 40
ETF_PUBLICATION_LAG = timedelta(days=1, hours=16)


def _bar(
    timestamp: datetime,
    *,
    timeframe: str,
    open_price: Decimal,
    high: Decimal,
    low: Decimal,
    close: Decimal,
    volume: Decimal,
    ingested_at: datetime,
) -> OhlcvBar:
    return OhlcvBar(
        timestamp=timestamp,
        exchange=EXCHANGE,
        symbol=SYMBOL,
        timeframe=timeframe,
        open=open_price,
        high=high,
        low=low,
        close=close,
        volume=volume,
        provider=PROVIDER,
        ingested_at=ingested_at,
    )


def hourly_universe(weeks: int = len(WEEKLY_LEVELS)) -> tuple[OhlcvBar, ...]:
    """Raw 1h bars whose ingestion time trails each hour's close."""

    bars = []
    for week_index in range(weeks):
        level = Decimal(WEEKLY_LEVELS[week_index])
        for hour in range(7 * 24):
            timestamp = SERIES_START + timedelta(weeks=week_index, hours=hour)
            bars.append(
                _bar(
                    timestamp,
                    timeframe="1h",
                    open_price=level,
                    high=level + Decimal("20"),
                    low=level - Decimal("20"),
                    close=level + Decimal(hour) * Decimal("0.05"),
                    volume=Decimal("10"),
                    ingested_at=timestamp + timedelta(hours=1) + INGESTION_LAG,
                )
            )
    return tuple(bars)


def canonical_weekly_bars() -> tuple[OhlcvBar, ...]:
    """Persisted canonical 1w bars carrying their true first-availability time."""

    return tuple(
        _bar(
            SERIES_START + timedelta(weeks=index),
            timeframe="1w",
            open_price=Decimal(level),
            high=Decimal(level) + Decimal("20"),
            low=Decimal(level) - Decimal("20"),
            close=Decimal(level),
            volume=Decimal("1680"),
            ingested_at=SERIES_START + timedelta(weeks=index + 1) + INGESTION_LAG,
        )
        for index, level in enumerate(WEEKLY_LEVELS)
    )


def canonical_monthly_bars() -> tuple[OhlcvBar, ...]:
    """Persisted canonical 1mo bars carrying their true first-availability time."""

    bars = []
    timestamp = MONTHLY_START
    for level in MONTHLY_LEVELS:
        closed_at = next_bar_timestamp(timestamp, "1mo")
        bars.append(
            _bar(
                timestamp,
                timeframe="1mo",
                open_price=Decimal(level),
                high=Decimal(level) + Decimal("20"),
                low=Decimal(level) - Decimal("20"),
                close=Decimal(level),
                volume=Decimal("7200"),
                ingested_at=closed_at + INGESTION_LAG,
            )
        )
        timestamp = closed_at
    return tuple(bars)


def canonical_daily_bars(days: int = len(WEEKLY_LEVELS) * 7) -> tuple[OhlcvBar, ...]:
    """Persisted canonical 1d bars with distinct closes and varying volume."""

    bars = []
    for day in range(days):
        timestamp = SERIES_START + timedelta(days=day)
        close = Decimal(WEEKLY_LEVELS[day // 7]) + Decimal(day % 7) * Decimal("1.25")
        bars.append(
            _bar(
                timestamp,
                timeframe="1d",
                open_price=close,
                high=close + Decimal("20"),
                low=close - Decimal("20"),
                close=close,
                volume=Decimal(10 + (day % 5) * 3),
                ingested_at=timestamp + timedelta(days=1) + INGESTION_LAG,
            )
        )
    return tuple(bars)


def etf_business_days(count: int = ETF_BUSINESS_DAY_COUNT) -> tuple[date, ...]:
    days = []
    current = ETF_FIRST_OBSERVATION_DATE
    while len(days) < count:
        if current.weekday() < 5:
            days.append(current)
        current += timedelta(days=1)
    return tuple(days)


def etf_flow_row(
    fund: str,
    observation_date: date,
    *,
    flow_usd: Decimal,
    aum_usd: Decimal,
    revision: str = "initial",
    available_at: datetime | None = None,
) -> EtfFlow:
    published_at = datetime(
        observation_date.year,
        observation_date.month,
        observation_date.day,
        tzinfo=UTC,
    )
    return EtfFlow(
        fund=fund,
        observation_date=observation_date,
        flow_usd=flow_usd,
        aum_usd=aum_usd,
        provider="farside",
        source="farside",
        revision=revision,
        available_at=available_at or published_at + ETF_PUBLICATION_LAG,
        ingested_at=available_at or published_at + ETF_PUBLICATION_LAG,
    )


def etf_universe() -> tuple[EtfFlow, ...]:
    flows = []
    for index, observation_date in enumerate(etf_business_days()):
        for fund_index, fund in enumerate(ETF_FUNDS):
            flows.append(
                etf_flow_row(
                    fund,
                    observation_date,
                    flow_usd=Decimal(100 + index * 7 + fund_index * 13),
                    aum_usd=Decimal(50_000 + index * 100 + fund_index * 500),
                )
            )
    return tuple(flows)


def available_bars(bars, as_of: datetime) -> tuple[OhlcvBar, ...]:
    """Bars whose session closed and whose ingestion completed by ``as_of``."""

    return tuple(
        bar
        for bar in bars
        if next_bar_timestamp(bar.timestamp, bar.timeframe) <= as_of
        and bar.ingested_at <= as_of
    )


def available_flows(flows, as_of: datetime) -> tuple[EtfFlow, ...]:
    return tuple(flow for flow in flows if flow.available_at <= as_of)


def weekly_decision_times() -> tuple[datetime, ...]:
    return tuple(
        SERIES_START + timedelta(weeks=index) + timedelta(hours=12)
        for index in range(1, len(WEEKLY_LEVELS) + 1)
    )


def far_future_hourly_bars(count: int = 24) -> tuple[OhlcvBar, ...]:
    """Hourly bars far beyond every decision time, at absurd prices."""

    start = SERIES_START + timedelta(weeks=len(WEEKLY_LEVELS))
    return tuple(
        _bar(
            start + timedelta(hours=hour),
            timeframe="1h",
            open_price=Decimal("900000"),
            high=Decimal("999999"),
            low=Decimal("800000"),
            close=Decimal("950000"),
            volume=Decimal("99999"),
            ingested_at=start + timedelta(hours=hour + 1) + INGESTION_LAG,
        )
        for hour in range(count)
    )


def records(items) -> list[dict]:
    return [item.as_record() for item in items]


# ---------------------------------------------------------------------------
# Future bars unavailable
# ---------------------------------------------------------------------------


def test_canonical_market_bars_only_expose_sessions_closed_and_ingested_by_the_cutoff() -> None:
    universe = hourly_universe(weeks=4)

    for cutoff in weekly_decision_times()[:4]:
        derived = build_canonical_market_bars(universe, data_available_at=cutoff)
        assert derived, "expected at least one canonical bar at this cutoff"
        for bar in derived:
            assert next_bar_timestamp(bar.timestamp, bar.timeframe) <= cutoff
            assert bar.ingested_at == cutoff


def test_canonical_market_bars_never_emit_a_partially_observed_session() -> None:
    universe = hourly_universe()
    february_close = datetime(2026, 3, 1, tzinfo=UTC)

    before_publication = build_canonical_market_bars(
        universe,
        data_available_at=february_close,
    )
    after_publication = build_canonical_market_bars(
        universe,
        data_available_at=february_close + INGESTION_LAG,
    )

    # The final February hour closes exactly at the month boundary but is only
    # ingested five minutes later, so the month is still incomplete at the
    # boundary itself.
    assert not [bar for bar in before_publication if bar.timeframe == "1mo"]
    monthly = [bar for bar in after_publication if bar.timeframe == "1mo"]
    assert [bar.timestamp for bar in monthly] == [datetime(2026, 2, 1, tzinfo=UTC)]
    # January and March are only partially covered by the hourly universe and
    # never become canonical monthly bars.
    assert monthly[0].volume == Decimal("10") * Decimal(28 * 24)


def test_canonical_market_bars_exclude_an_hour_published_before_it_closed() -> None:
    # A provider that publishes the running hour early would otherwise complete
    # the session's last bucket with a partial bar.
    universe = hourly_universe(weeks=1)
    final_hour = universe[-1]
    published_early = (
        *universe[:-1],
        _bar(
            final_hour.timestamp,
            timeframe="1h",
            open_price=final_hour.open,
            high=final_hour.high,
            low=final_hour.low,
            close=final_hour.close,
            volume=final_hour.volume,
            ingested_at=final_hour.timestamp + timedelta(minutes=30),
        ),
    )
    cutoff = final_hour.timestamp + timedelta(minutes=45)

    derived = build_canonical_market_bars(published_early, data_available_at=cutoff)

    assert [bar.timestamp for bar in derived if bar.timeframe == "1d"] == [
        SERIES_START + timedelta(days=day) for day in range(6)
    ]
    assert not [bar for bar in derived if bar.timeframe == "1w"]


def test_canonical_market_bars_grow_as_a_prefix_and_never_revise_earlier_sessions() -> None:
    universe = hourly_universe(weeks=5)
    previous: dict[str, list[dict]] = {"1d": [], "1w": [], "1mo": []}

    for cutoff in weekly_decision_times()[:5]:
        derived = build_canonical_market_bars(universe, data_available_at=cutoff)
        for timeframe, earlier in previous.items():
            current = [
                {
                    key: value
                    for key, value in bar.as_record().items()
                    if key != "ingested_at"
                }
                for bar in derived
                if bar.timeframe == timeframe
            ]
            assert current[: len(earlier)] == earlier
            previous[timeframe] = current

    assert len(previous["1d"]) == 5 * 7
    assert len(previous["1w"]) == 5


def test_appending_future_hourly_bars_never_changes_canonical_bars_at_a_cutoff() -> None:
    universe = hourly_universe(weeks=4)
    polluted = (*universe, *far_future_hourly_bars())

    for cutoff in weekly_decision_times()[:4]:
        assert records(
            build_canonical_market_bars(polluted, data_available_at=cutoff)
        ) == records(build_canonical_market_bars(universe, data_available_at=cutoff))


def test_canonical_market_bars_equal_the_bars_built_from_a_truncated_universe() -> None:
    universe = hourly_universe(weeks=4)

    for cutoff in weekly_decision_times()[:4]:
        truncated = available_bars(universe, cutoff)
        assert records(
            build_canonical_market_bars(universe, data_available_at=cutoff)
        ) == records(
            build_canonical_market_bars(truncated, data_available_at=cutoff)
        )


def test_realized_volatility_at_a_decision_ignores_bars_that_close_later() -> None:
    bars = canonical_daily_bars()
    polluted = (
        *bars,
        _bar(
            SERIES_START + timedelta(days=len(bars)),
            timeframe="1d",
            open_price=Decimal("900000"),
            high=Decimal("999999"),
            low=Decimal("800000"),
            close=Decimal("950000"),
            volume=Decimal("99999"),
            ingested_at=SERIES_START + timedelta(days=len(bars) + 1),
        ),
    )

    for day in range(10, 40, 5):
        as_of = SERIES_START + timedelta(days=day, hours=12)
        baseline = realized_volatility_from_daily_bars(
            bars,
            as_of=as_of,
            window_days=3,
            annualization_periods=1,
        ).as_record()

        assert (
            realized_volatility_from_daily_bars(
                polluted,
                as_of=as_of,
                window_days=3,
                annualization_periods=1,
            ).as_record()
            == baseline
        )
        assert (
            realized_volatility_from_daily_bars(
                available_bars(bars, as_of),
                as_of=as_of,
                window_days=3,
                annualization_periods=1,
            ).as_record()
            == baseline
        )


def test_realized_volatility_excludes_a_daily_session_that_has_not_closed() -> None:
    # A provider that publishes the running day early would otherwise let an
    # unfinished session's close into the return window.
    bars = list(canonical_daily_bars(days=12))
    live_index = 11
    live_day = bars[live_index]
    bars[live_index] = _bar(
        live_day.timestamp,
        timeframe="1d",
        open_price=live_day.open,
        high=live_day.high,
        low=live_day.low,
        close=live_day.close,
        volume=live_day.volume,
        ingested_at=live_day.timestamp + timedelta(hours=1),
    )
    universe = tuple(bars)
    as_of = live_day.timestamp + timedelta(hours=12)
    assert live_day.timestamp < as_of < next_bar_timestamp(live_day.timestamp, "1d")

    result = realized_volatility_from_daily_bars(
        universe,
        as_of=as_of,
        window_days=3,
        annualization_periods=1,
    )

    assert result.complete is True
    assert result.observation_time == bars[live_index - 1].timestamp
    assert (
        realized_volatility_from_daily_bars(
            available_bars(universe, as_of),
            as_of=as_of,
            window_days=3,
            annualization_periods=1,
        ).as_record()
        == result.as_record()
    )


# ---------------------------------------------------------------------------
# Future ETF flows unavailable
# ---------------------------------------------------------------------------


def etf_decision_times() -> tuple[datetime, ...]:
    business_days = etf_business_days()
    return tuple(
        datetime(day.year, day.month, day.day, tzinfo=UTC) + timedelta(hours=20)
        for day in business_days[22:28]
    )


def etf_window_records(flows, as_of: datetime) -> tuple[dict, dict, dict]:
    five_day = five_day_etf_flow(flows, as_of=as_of, funds=ETF_FUNDS)
    twenty_day = twenty_day_etf_flow(flows, as_of=as_of, funds=ETF_FUNDS)
    return (
        five_day.as_record(),
        twenty_day.as_record(),
        etf_flow_acceleration(five_day, twenty_day).as_record(),
    )


def test_etf_flow_windows_equal_the_windows_built_from_a_truncated_universe() -> None:
    flows = etf_universe()

    for as_of in etf_decision_times():
        assert etf_window_records(flows, as_of) == etf_window_records(
            available_flows(flows, as_of),
            as_of,
        )


def test_appending_unpublished_etf_flows_never_changes_an_earlier_decision() -> None:
    flows = etf_universe()
    business_days = etf_business_days()
    future_rows = tuple(
        etf_flow_row(
            fund,
            observation_date,
            flow_usd=Decimal("999999"),
            aum_usd=Decimal("1"),
        )
        for observation_date in business_days[28:]
        for fund in ETF_FUNDS
    )
    assert future_rows

    for as_of in etf_decision_times():
        assert etf_window_records((*flows, *future_rows), as_of) == etf_window_records(
            flows,
            as_of,
        )


def test_a_late_etf_revision_moves_only_decisions_made_after_it_is_published() -> None:
    flows = etf_universe()
    business_days = etf_business_days()
    revised_date = business_days[24]
    published_at = datetime(
        revised_date.year,
        revised_date.month,
        revised_date.day,
        tzinfo=UTC,
    ) + timedelta(days=4)
    revision = etf_flow_row(
        ETF_FUNDS[0],
        revised_date,
        flow_usd=Decimal("5000"),
        aum_usd=Decimal("50_000"),
        revision="restated",
        available_at=published_at,
    )

    before = published_at - timedelta(hours=1)
    after = published_at + timedelta(hours=1)

    assert etf_window_records((*flows, revision), before) == etf_window_records(
        flows,
        before,
    )
    assert etf_window_records((*flows, revision), after) != etf_window_records(
        flows,
        after,
    )


def test_an_etf_window_before_publication_is_reported_missing_and_never_zero_filled() -> None:
    flows = etf_universe()
    first_observation_date = etf_business_days()[0]
    as_of = datetime(
        first_observation_date.year,
        first_observation_date.month,
        first_observation_date.day,
        tzinfo=UTC,
    ) + timedelta(hours=20)

    result = five_day_etf_flow(flows, as_of=as_of, funds=ETF_FUNDS)

    assert available_flows(flows, as_of) == ()
    assert result.complete is False
    assert result.flow_sum_usd is None
    assert result.normalized_flow is None
    assert result.source_record_count == 0
    assert "ETF_FLOW_INPUT_MISSING" in result.reason_codes


def test_etf_windows_never_reach_past_the_decision_for_their_observation_date() -> None:
    flows = etf_universe()

    for as_of in etf_decision_times():
        five_day = five_day_etf_flow(flows, as_of=as_of, funds=ETF_FUNDS)
        latest_available = max(
            flow.observation_date for flow in available_flows(flows, as_of)
        )
        assert five_day.observation_date == latest_available
        assert max(five_day.included_observation_dates) == latest_available


# ---------------------------------------------------------------------------
# Future confirmed pivots unavailable
# ---------------------------------------------------------------------------


EXPECTED_WEEKLY_SWING_LOW_TIMESTAMP = SERIES_START + timedelta(weeks=3)
EXPECTED_WEEKLY_SWING_LOW_DETECTED_AT = SERIES_START + timedelta(weeks=7) + INGESTION_LAG
EXPECTED_WEEKLY_SWING_HIGH_TIMESTAMP = SERIES_START + timedelta(weeks=6)
EXPECTED_WEEKLY_SWING_HIGH_DETECTED_AT = (
    SERIES_START + timedelta(weeks=10) + INGESTION_LAG
)


def test_weekly_pivots_are_the_expected_confirmed_levels() -> None:
    bars = canonical_weekly_bars()
    levels = detect_weekly_swing_levels(
        bars,
        as_of=SERIES_START + timedelta(weeks=len(WEEKLY_LEVELS) + 1),
    )

    assert [
        (level.level_type, level.level_timestamp, level.price, level.detected_at)
        for level in levels
    ] == [
        (
            "swing_low",
            EXPECTED_WEEKLY_SWING_LOW_TIMESTAMP,
            Decimal("80"),
            EXPECTED_WEEKLY_SWING_LOW_DETECTED_AT,
        ),
        (
            "swing_high",
            EXPECTED_WEEKLY_SWING_HIGH_TIMESTAMP,
            Decimal("160"),
            EXPECTED_WEEKLY_SWING_HIGH_DETECTED_AT,
        ),
    ]


def test_a_weekly_pivot_is_unavailable_until_its_confirmation_window_closes() -> None:
    bars = canonical_weekly_bars()
    detected_at = EXPECTED_WEEKLY_SWING_LOW_DETECTED_AT

    assert detect_weekly_swing_levels(bars, as_of=detected_at - timedelta(seconds=1)) == ()
    confirmed = detect_weekly_swing_levels(bars, as_of=detected_at)
    assert [level.level_timestamp for level in confirmed] == [
        EXPECTED_WEEKLY_SWING_LOW_TIMESTAMP
    ]
    # The pivot bar itself closed four weeks before the level could be used.
    assert confirmed[0].level_timestamp < detected_at - timedelta(weeks=3)


def test_confirmed_pivots_never_precede_their_detection_time_at_any_decision() -> None:
    bars = canonical_weekly_bars()

    for as_of in weekly_decision_times():
        for level in detect_weekly_swing_levels(bars, as_of=as_of):
            assert level.detected_at <= as_of
            assert level.level_timestamp < level.detected_at


def test_confirmed_pivot_sets_grow_monotonically_and_are_never_restated() -> None:
    bars = canonical_weekly_bars()
    previous: list[dict] = []

    for as_of in weekly_decision_times():
        current = records(detect_weekly_swing_levels(bars, as_of=as_of))
        assert current[: len(previous)] == previous
        previous = current

    assert len(previous) == 2


def test_appending_future_weekly_bars_never_changes_earlier_confirmed_pivots() -> None:
    bars = canonical_weekly_bars()
    # A far lower low and far higher high than anything in the series; if the
    # detector reached forward, the confirmed set would change.
    future_bars = tuple(
        _bar(
            SERIES_START + timedelta(weeks=len(WEEKLY_LEVELS) + offset),
            timeframe="1w",
            open_price=Decimal("1000"),
            high=Decimal("9000"),
            low=Decimal("1"),
            close=Decimal("1000"),
            volume=Decimal("1680"),
            ingested_at=SERIES_START
            + timedelta(weeks=len(WEEKLY_LEVELS) + offset + 1)
            + INGESTION_LAG,
        )
        for offset in range(4)
    )

    for as_of in weekly_decision_times():
        assert records(detect_weekly_swing_levels((*bars, *future_bars), as_of=as_of)) == records(
            detect_weekly_swing_levels(bars, as_of=as_of)
        )
        assert records(
            detect_weekly_swing_levels(available_bars(bars, as_of), as_of=as_of)
        ) == records(detect_weekly_swing_levels(bars, as_of=as_of))


def test_a_pivot_confirmed_by_a_late_ingested_bar_waits_for_that_ingestion() -> None:
    # The confirming bar closed on schedule but only reached the repository two
    # weeks later, so the pivot was not knowable in between.
    bars = list(canonical_weekly_bars()[:7])
    confirming = bars[-1]
    backfilled_at = confirming.ingested_at + timedelta(weeks=2)
    bars[-1] = _bar(
        confirming.timestamp,
        timeframe="1w",
        open_price=confirming.open,
        high=confirming.high,
        low=confirming.low,
        close=confirming.close,
        volume=confirming.volume,
        ingested_at=backfilled_at,
    )
    delayed = tuple(bars)

    assert next_bar_timestamp(confirming.timestamp, "1w") < backfilled_at
    assert detect_weekly_swing_levels(
        delayed,
        as_of=backfilled_at - timedelta(seconds=1),
    ) == ()

    confirmed = detect_weekly_swing_levels(delayed, as_of=backfilled_at)
    assert [level.level_timestamp for level in confirmed] == [
        EXPECTED_WEEKLY_SWING_LOW_TIMESTAMP
    ]
    assert confirmed[0].detected_at == backfilled_at


def test_a_pivot_is_not_backdated_when_a_window_bar_is_backfilled_late() -> None:
    # The bar that closes the swing low's confirmation window arrived on time,
    # but a bar inside the same window was backfilled five weeks later. The
    # level could not be derived from its full window until that backfill, so
    # it must never claim the confirming bar's earlier availability, and a
    # decision already taken must never see its detection time move backwards.
    backfilled_index = 5
    bars = list(canonical_weekly_bars())
    delayed = bars[backfilled_index]
    backfilled_at = delayed.ingested_at + timedelta(weeks=5)
    bars[backfilled_index] = _bar(
        delayed.timestamp,
        timeframe="1w",
        open_price=delayed.open,
        high=delayed.high,
        low=delayed.low,
        close=delayed.close,
        volume=delayed.volume,
        ingested_at=backfilled_at,
    )
    universe = tuple(bars)
    assert EXPECTED_WEEKLY_SWING_LOW_DETECTED_AT < backfilled_at

    latest_detected_at: dict[tuple[str, datetime], datetime] = {}
    for as_of in weekly_decision_times():
        for level in detect_weekly_swing_levels(universe, as_of=as_of):
            key = (level.level_type, level.level_timestamp)
            assert level.detected_at <= as_of
            assert level.detected_at >= latest_detected_at.get(key, level.detected_at)
            latest_detected_at[key] = level.detected_at

    swing_low = detect_weekly_swing_levels(
        universe,
        as_of=SERIES_START + timedelta(weeks=len(WEEKLY_LEVELS) + 1),
    )[0]
    assert swing_low.level_type == "swing_low"
    assert swing_low.level_timestamp == EXPECTED_WEEKLY_SWING_LOW_TIMESTAMP
    assert swing_low.detected_at == backfilled_at
    assert detect_weekly_swing_levels(
        universe,
        as_of=backfilled_at - timedelta(seconds=1),
    ) == detect_weekly_swing_levels(
        available_bars(universe, backfilled_at - timedelta(seconds=1)),
        as_of=backfilled_at - timedelta(seconds=1),
    )


def test_a_monthly_pivot_waits_for_its_confirming_month_to_close() -> None:
    bars = canonical_monthly_bars()
    swing_low_detected_at = datetime(2026, 6, 1, tzinfo=UTC) + INGESTION_LAG
    swing_high_detected_at = datetime(2026, 8, 1, tzinfo=UTC) + INGESTION_LAG

    assert detect_monthly_swing_levels(
        bars,
        as_of=swing_low_detected_at - timedelta(seconds=1),
    ) == ()
    low_only = detect_monthly_swing_levels(bars, as_of=swing_low_detected_at)
    assert [(level.level_type, level.level_timestamp) for level in low_only] == [
        ("swing_low", datetime(2026, 3, 1, tzinfo=UTC))
    ]

    both = detect_monthly_swing_levels(bars, as_of=swing_high_detected_at)
    assert [(level.level_type, level.level_timestamp) for level in both] == [
        ("swing_low", datetime(2026, 3, 1, tzinfo=UTC)),
        ("swing_high", datetime(2026, 5, 1, tzinfo=UTC)),
    ]
    assert records(both)[:1] == records(low_only)


# ---------------------------------------------------------------------------
# Rolling normalization past-only
# ---------------------------------------------------------------------------


NORMALIZATION_VALUES = (
    10.0,
    12.0,
    9.0,
    15.0,
    11.0,
    18.0,
    14.0,
    13.0,
    16.0,
    12.5,
    17.5,
    11.5,
)
PRIOR_WINDOW_KERNELS = (
    ("rolling_zscore", lambda values: rolling_zscore(values, window=4)),
    ("rolling_percentile", lambda values: rolling_percentile(values, window=4)),
    ("historical_normalize", lambda values: historical_normalize(values, window=4)),
)
INCLUSIVE_WINDOW_KERNELS = (
    ("rolling_mean", lambda values: rolling_mean(values, window=4)),
    ("rolling_volatility", lambda values: rolling_volatility(values, window=4)),
    ("realized_volatility", lambda values: realized_volatility(values, window=4)),
)


def test_normalization_kernels_never_read_an_observation_that_arrives_later() -> None:
    mutated_index = 7
    mutated = list(NORMALIZATION_VALUES)
    mutated[mutated_index] = 10_000.0

    for name, kernel in (*PRIOR_WINDOW_KERNELS, *INCLUSIVE_WINDOW_KERNELS):
        baseline = kernel(NORMALIZATION_VALUES)
        perturbed = kernel(mutated)
        np.testing.assert_array_equal(
            perturbed[:mutated_index],
            baseline[:mutated_index],
            err_msg=f"{name} leaked a later observation into earlier outputs",
        )
        assert not np.array_equal(
            perturbed[mutated_index:],
            baseline[mutated_index:],
        ), f"{name} ignored the perturbed observation entirely"


def test_prior_window_normalizers_exclude_the_current_observation_from_its_window() -> None:
    # A value far outside its own prior window is normalized against that window
    # alone. A self-inclusive window would rescale to the extreme itself, capping
    # the percentile below 100 and the z-score at sqrt(window).
    values = (10.0, 12.0, 11.0, 13.0, 100.0)

    percentiles = rolling_percentile(values, window=4)
    normalized = historical_normalize(values, window=4)
    zscores = rolling_zscore(values, window=4)

    assert percentiles[-1] == 100.0
    assert normalized[-1] == 100.0
    assert zscores[-1] > np.sqrt(4.0)


def test_a_degenerate_prior_window_is_reported_missing_rather_than_zero() -> None:
    flat = (10.0, 10.0, 10.0, 10.0, 20.0)

    assert np.isnan(rolling_zscore(flat, window=4)[-1])
    assert np.isnan(historical_normalize(flat, window=4)[-1])
    # Percentile ranking stays defined against a flat prior window.
    assert rolling_percentile(flat, window=4)[-1] == 100.0


def test_streaming_prefixes_reproduce_batch_normalization_exactly() -> None:
    for name, kernel in (*PRIOR_WINDOW_KERNELS, *INCLUSIVE_WINDOW_KERNELS):
        batch = kernel(NORMALIZATION_VALUES)
        for length in range(1, len(NORMALIZATION_VALUES) + 1):
            prefix = kernel(NORMALIZATION_VALUES[:length])
            np.testing.assert_array_equal(
                prefix,
                batch[:length],
                err_msg=f"{name} prefix diverged from the batch calculation",
            )


def test_average_true_range_uses_only_bars_through_the_current_index() -> None:
    highs = [12.0, 14.0, 13.5, 16.0, 15.0, 18.0]
    lows = [9.0, 11.0, 10.5, 13.0, 12.5, 15.0]
    closes = [10.0, 13.0, 11.0, 15.0, 13.0, 17.0]
    batch = average_true_range(highs, lows, closes, window=3)

    for length in range(1, len(highs) + 1):
        np.testing.assert_array_equal(
            average_true_range(
                highs[:length],
                lows[:length],
                closes[:length],
                window=3,
            ),
            batch[:length],
        )


def test_domain_rolling_wrappers_report_warm_up_as_missing_not_zero() -> None:
    values = tuple(Decimal(str(value)) for value in NORMALIZATION_VALUES)

    for series in (
        domain_rolling.rolling_zscore(values, window=4),
        domain_rolling.rolling_percentile(values, window=4),
        domain_rolling.historical_normalize(values, window=4),
    ):
        assert series[0] is None
        assert len(series) == len(values)
        assert all(value is None or isinstance(value, Decimal) for value in series)

    for length in range(1, len(values) + 1):
        assert domain_rolling.historical_normalize(values[:length], window=4) == (
            domain_rolling.historical_normalize(values, window=4)[:length]
        )


def test_volatility_percentile_ranks_against_strictly_prior_history() -> None:
    bars = canonical_daily_bars(days=30)
    results = tuple(
        realized_volatility_from_daily_bars(
            bars,
            as_of=bar.timestamp + timedelta(days=1) + INGESTION_LAG,
            window_days=3,
            annualization_periods=1,
        )
        for bar in bars
    )
    complete_results = tuple(
        result for result in results if result.realized_volatility is not None
    )
    assert len(complete_results) >= 10

    as_of = complete_results[-1].observation_time + timedelta(hours=1)
    ranked = volatility_percentile(
        complete_results,
        as_of=as_of,
        source_feature_id="RV_3",
        percentile_window_days=365,
        min_percentile_observations=5,
    )

    assert ranked.observation_time == complete_results[-1].observation_time
    assert ranked.history_observation_count == len(complete_results) - 1
    assert ranked.source_result_count == len(complete_results)

    future_result = RealizedVolatilityResult(
        feature_id="RV_3",
        observation_time=as_of + timedelta(days=5),
        window_days=3,
        annualization_periods=1,
        realized_volatility=Decimal("9999"),
        return_count=3,
        source_bar_count=4,
        complete=True,
    )
    assert (
        volatility_percentile(
            (*complete_results, future_result),
            as_of=as_of,
            source_feature_id="RV_3",
            percentile_window_days=365,
            min_percentile_observations=5,
        ).as_record()
        == ranked.as_record()
    )


# ---------------------------------------------------------------------------
# AVWAP anchors point-in-time valid
# ---------------------------------------------------------------------------


def confirmed_weekly_swing_low_anchor() -> AnchoredVwapAnchor:
    levels = detect_weekly_swing_levels(
        canonical_weekly_bars(),
        as_of=EXPECTED_WEEKLY_SWING_LOW_DETECTED_AT,
    )
    return anchored_vwap_anchor_from_swing_level(levels[0])


def test_an_avwap_anchor_inherits_the_confirmed_pivots_detection_time() -> None:
    levels = detect_weekly_swing_levels(
        canonical_weekly_bars(),
        as_of=EXPECTED_WEEKLY_SWING_HIGH_DETECTED_AT,
    )
    low_anchor = anchored_vwap_anchor_from_swing_level(levels[0])
    high_anchor = anchored_vwap_anchor_from_swing_level(levels[1])

    assert low_anchor.anchor_type == ANCHOR_MAJOR_SWING_LOW
    assert high_anchor.anchor_type == ANCHOR_MAJOR_SWING_HIGH
    for anchor, level in ((low_anchor, levels[0]), (high_anchor, levels[1])):
        assert anchor.anchor_timestamp == level.level_timestamp
        assert anchor.detected_at == level.detected_at
        assert anchor.source_detected_at == level.detected_at
        assert anchor.detected_at > anchor.anchor_timestamp


def test_an_anchor_that_claims_earlier_detection_than_its_source_is_rejected() -> None:
    anchor = confirmed_weekly_swing_low_anchor()
    backdated = AnchoredVwapAnchor(
        anchor_type=anchor.anchor_type,
        anchor_timestamp=anchor.anchor_timestamp,
        detected_at=anchor.source_detected_at - timedelta(seconds=1),
        price=anchor.price,
        exchange=anchor.exchange,
        symbol=anchor.symbol,
        provider=anchor.provider,
        source_feature_id=anchor.source_feature_id,
        source_type=anchor.source_type,
        source_timestamp=anchor.source_timestamp,
        source_detected_at=anchor.source_detected_at,
        source_timeframe=anchor.source_timeframe,
    )

    with pytest.raises(ValueError, match="source_detected_at must be <= detected_at"):
        backdated.as_record()


def test_an_avwap_is_unusable_before_its_anchor_was_detected() -> None:
    anchor = confirmed_weekly_swing_low_anchor()
    bars = canonical_daily_bars()

    early = calculate_anchored_vwap(
        anchor,
        bars,
        as_of=anchor.detected_at - timedelta(seconds=1),
    )

    assert early.complete is False
    assert early.vwap is None
    assert early.bar_count == 0
    assert early.volume_sum == Decimal("0")
    assert early.reason_codes == ("ANCHORED_VWAP_ANCHOR_NOT_DETECTED",)


def test_avwap_accumulates_only_bars_closed_and_ingested_by_the_decision() -> None:
    anchor = confirmed_weekly_swing_low_anchor()
    bars = canonical_daily_bars()

    for offset in range(0, 21, 5):
        as_of = anchor.detected_at + timedelta(days=offset)
        result = calculate_anchored_vwap(anchor, bars, as_of=as_of)
        contributing = tuple(
            bar
            for bar in available_bars(bars, as_of)
            if bar.timestamp >= anchor.anchor_timestamp
        )

        assert contributing
        assert result.bar_count == len(contributing)
        assert result.volume_sum == sum(
            (bar.volume for bar in contributing), Decimal("0")
        )
        assert (
            calculate_anchored_vwap(
                anchor,
                available_bars(bars, as_of),
                as_of=as_of,
            ).as_record()
            == result.as_record()
        )


def test_avwap_excludes_a_bar_published_before_its_session_closed() -> None:
    anchor = confirmed_weekly_swing_low_anchor()
    bars = list(canonical_daily_bars())
    live_index = 60
    live_day = bars[live_index]
    bars[live_index] = _bar(
        live_day.timestamp,
        timeframe="1d",
        open_price=live_day.open,
        high=live_day.high,
        low=live_day.low,
        close=live_day.close,
        volume=live_day.volume,
        ingested_at=live_day.timestamp + timedelta(hours=6),
    )
    as_of = live_day.timestamp + timedelta(hours=12)
    assert live_day.timestamp < as_of < next_bar_timestamp(live_day.timestamp, "1d")

    with_live_session = calculate_anchored_vwap(anchor, tuple(bars), as_of=as_of)
    settled_only = calculate_anchored_vwap(anchor, tuple(bars[:live_index]), as_of=as_of)

    assert with_live_session.as_record() == settled_only.as_record()
    anchor_day = (anchor.anchor_timestamp - SERIES_START).days
    assert with_live_session.bar_count == live_index - anchor_day


def test_appending_future_bars_never_changes_an_earlier_avwap() -> None:
    anchor = confirmed_weekly_swing_low_anchor()
    bars = canonical_daily_bars()
    future_bars = tuple(
        _bar(
            SERIES_START + timedelta(days=len(bars) + offset),
            timeframe="1d",
            open_price=Decimal("900000"),
            high=Decimal("999999"),
            low=Decimal("800000"),
            close=Decimal("950000"),
            volume=Decimal("99999"),
            ingested_at=SERIES_START + timedelta(days=len(bars) + offset + 1),
        )
        for offset in range(5)
    )

    for offset in range(0, 21, 5):
        as_of = anchor.detected_at + timedelta(days=offset)
        assert (
            calculate_anchored_vwap(anchor, (*bars, *future_bars), as_of=as_of).as_record()
            == calculate_anchored_vwap(anchor, bars, as_of=as_of).as_record()
        )


def test_avwap_bar_coverage_grows_monotonically_across_decisions() -> None:
    anchor = confirmed_weekly_swing_low_anchor()
    bars = canonical_daily_bars()
    previous_bar_count = 0

    for offset in range(0, 25, 3):
        result = calculate_anchored_vwap(
            anchor,
            bars,
            as_of=anchor.detected_at + timedelta(days=offset),
        )
        assert result.complete is True
        assert result.bar_count >= previous_bar_count
        previous_bar_count = result.bar_count


# ---------------------------------------------------------------------------
# Cross-cutting point-in-time replay gate
# ---------------------------------------------------------------------------


def point_in_time_replay(
    *,
    weekly_bars,
    daily_bars,
    hourly_bars,
    flows,
    as_of: datetime,
) -> dict:
    """Every BTC-221 owner evaluated at one decision timestamp."""

    levels = detect_weekly_swing_levels(weekly_bars, as_of=as_of)
    anchors = tuple(anchored_vwap_anchor_from_swing_level(level) for level in levels)
    five_day = five_day_etf_flow(flows, as_of=as_of, funds=ETF_FUNDS)
    twenty_day = twenty_day_etf_flow(flows, as_of=as_of, funds=ETF_FUNDS)
    return {
        "canonical_bars": records(
            build_canonical_market_bars(hourly_bars, data_available_at=as_of)
        ),
        "confirmed_pivots": records(levels),
        "anchored_vwaps": records(
            calculate_anchored_vwap(anchor, daily_bars, as_of=as_of)
            for anchor in anchors
        ),
        "realized_volatility": realized_volatility_from_daily_bars(
            daily_bars,
            as_of=as_of,
            window_days=3,
            annualization_periods=1,
        ).as_record(),
        "etf_flow_5d": five_day.as_record(),
        "etf_flow_20d": twenty_day.as_record(),
        "etf_flow_acceleration": etf_flow_acceleration(
            five_day,
            twenty_day,
        ).as_record(),
    }


def replay_decision_times() -> tuple[datetime, ...]:
    """Decisions spanning the confirmation of both weekly pivots."""

    business_days = etf_business_days()
    return tuple(
        datetime(
            business_days[index].year,
            business_days[index].month,
            business_days[index].day,
            tzinfo=UTC,
        )
        + timedelta(hours=20)
        for index in (20, 24, 28, 30, 31, 34)
    )


def test_point_in_time_replay_is_identical_with_and_without_a_future_universe() -> None:
    weekly = canonical_weekly_bars()
    daily = canonical_daily_bars()
    hourly = hourly_universe()
    flows = etf_universe()

    future_weekly = tuple(
        _bar(
            SERIES_START + timedelta(weeks=len(WEEKLY_LEVELS) + offset),
            timeframe="1w",
            open_price=Decimal("1000"),
            high=Decimal("9000"),
            low=Decimal("1"),
            close=Decimal("1000"),
            volume=Decimal("1680"),
            ingested_at=SERIES_START
            + timedelta(weeks=len(WEEKLY_LEVELS) + offset + 1)
            + INGESTION_LAG,
        )
        for offset in range(3)
    )
    future_daily = tuple(
        _bar(
            SERIES_START + timedelta(days=len(daily) + offset),
            timeframe="1d",
            open_price=Decimal("900000"),
            high=Decimal("999999"),
            low=Decimal("800000"),
            close=Decimal("950000"),
            volume=Decimal("99999"),
            ingested_at=SERIES_START + timedelta(days=len(daily) + offset + 1),
        )
        for offset in range(3)
    )
    future_flows = tuple(
        etf_flow_row(
            fund,
            observation_date,
            flow_usd=Decimal("999999"),
            aum_usd=Decimal("1"),
        )
        for observation_date in etf_business_days()[28:]
        for fund in ETF_FUNDS
    )

    pivot_counts: list[int] = []
    for as_of in replay_decision_times():
        baseline = point_in_time_replay(
            weekly_bars=weekly,
            daily_bars=daily,
            hourly_bars=hourly,
            flows=flows,
            as_of=as_of,
        )
        with_future = point_in_time_replay(
            weekly_bars=(*weekly, *future_weekly),
            daily_bars=(*daily, *future_daily),
            hourly_bars=(*hourly, *far_future_hourly_bars()),
            flows=(*flows, *future_flows),
            as_of=as_of,
        )
        truncated = point_in_time_replay(
            weekly_bars=available_bars(weekly, as_of),
            daily_bars=available_bars(daily, as_of),
            hourly_bars=available_bars(hourly, as_of),
            flows=available_flows(flows, as_of),
            as_of=as_of,
        )

        assert with_future == baseline
        assert truncated == baseline
        assert baseline["canonical_bars"]
        assert baseline["etf_flow_5d"]["complete"] is True
        assert baseline["realized_volatility"]["complete"] is True
        assert len(baseline["confirmed_pivots"]) == len(baseline["anchored_vwaps"])
        pivot_counts.append(len(baseline["confirmed_pivots"]))

    # The replay window spans the confirmation of both weekly pivots, so the
    # comparison is never made against an empty pivot set.
    assert pivot_counts == sorted(pivot_counts)
    assert pivot_counts[0] == 1
    assert pivot_counts[-1] == 2


def test_point_in_time_replay_is_deterministic_for_shuffled_inputs() -> None:
    weekly = canonical_weekly_bars()
    daily = canonical_daily_bars()
    hourly = hourly_universe(weeks=6)
    flows = etf_universe()
    as_of = replay_decision_times()[0]

    baseline = point_in_time_replay(
        weekly_bars=weekly,
        daily_bars=daily,
        hourly_bars=hourly,
        flows=flows,
        as_of=as_of,
    )
    shuffled = point_in_time_replay(
        weekly_bars=tuple(reversed(weekly)),
        daily_bars=tuple(reversed(daily)),
        hourly_bars=tuple(reversed(hourly)),
        flows=tuple(reversed(flows)),
        as_of=as_of,
    )

    assert shuffled == baseline
