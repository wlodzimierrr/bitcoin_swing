"""Deterministic synthetic fixtures for the RBT-002 runtime tracer: flow roots.

Group G2 (Rulebook 6.1 / 6.2 flow component of Entry Conviction). Every thunk
builds its own synthetic inputs from ``btc_predictor`` owner types and the
standard library only, then calls exactly one decision-path root and returns
its result. Nothing here reads data files, a database, the network, the wall
clock or a random source. All dates sit inside 2024 (inside the
2021-01-01..2024-12-31 envelope) and are UTC.

Roots covered (all in ``btc_predictor.features.flow``):

- ``five_day_etf_flow``            complete / missing row / missing AUM
- ``twenty_day_etf_flow``          complete (Good Friday holiday) / missing AUM / empty
- ``etf_flow_acceleration``        complete / five-day AUM missing
- ``spot_perp_participation_from_rows`` complete (champion defaults) / no perp notional / short history
- ``spot_perp_cvd_spread``         complete (champion defaults) / no CVD at all / short history
- ``calculate_flow_score``         full model (champion weights) / ETF_CORE fallback / core input missing
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal

from btc_predictor.config.strategy import load_strategy_config
from btc_predictor.data import EtfFlow, OhlcvBar, PerpVolume
from btc_predictor.features.flow import (
    CvdObservation,
    FlowScoreInput,
    calculate_flow_score,
    etf_flow_acceleration,
    five_day_etf_flow,
    spot_perp_cvd_spread,
    spot_perp_participation_from_rows,
    twenty_day_etf_flow,
)

ROOT_FIVE_DAY = "btc_predictor.features.flow.five_day_etf_flow"
ROOT_TWENTY_DAY = "btc_predictor.features.flow.twenty_day_etf_flow"
ROOT_ACCEL = "btc_predictor.features.flow.etf_flow_acceleration"
ROOT_PARTICIPATION = "btc_predictor.features.flow.spot_perp_participation_from_rows"
ROOT_CVD = "btc_predictor.features.flow.spot_perp_cvd_spread"
ROOT_FLOW_SCORE = "btc_predictor.features.flow.calculate_flow_score"

FUNDS = ("IBIT", "FBTC")
GOOD_FRIDAY_2024 = date(2024, 3, 29)


# --- synthetic builders (called inside the thunks) --------------------------------


def _publication_dates_ending(end: date, count: int, holidays: frozenset[date] = frozenset()) -> tuple[date, ...]:
    dates: list[date] = []
    current = end
    while len(dates) < count:
        if current.weekday() < 5 and current not in holidays:
            dates.append(current)
        current -= timedelta(days=1)
    return tuple(reversed(dates))


def _etf_flow(
    fund: str,
    observation_date: date,
    flow_usd: str,
    *,
    aum_usd: str | None,
    revision: str = "initial",
    available_at: datetime | None = None,
):
    published = available_at or datetime(
        observation_date.year, observation_date.month, observation_date.day, 13, 30, tzinfo=UTC
    ) + timedelta(days=1)
    return EtfFlow(
        fund=fund,
        observation_date=observation_date,
        flow_usd=Decimal(flow_usd),
        aum_usd=Decimal(aum_usd) if aum_usd is not None else None,
        provider="synthetic",
        source="synthetic-etf-flow-fixture",
        revision=revision,
        available_at=published,
        ingested_at=published + timedelta(minutes=5),
    )


def _flow_rows(dates: tuple[date, ...], *, fbtc_aum: str | None = "5000000000") -> list:
    """Two funds, every publication date, deterministic flows that vary by day."""

    rows = []
    for index, observation_date in enumerate(dates):
        ibit_flow = Decimal(150_000_000) + Decimal(index * 12_500_000) - Decimal((index % 3) * 40_000_000)
        fbtc_flow = Decimal(-30_000_000) + Decimal((index % 4) * 25_000_000)
        rows.append(
            _etf_flow(
                "IBIT",
                observation_date,
                str(ibit_flow),
                aum_usd=str(Decimal(15_000_000_000) + Decimal(index * 100_000_000)),
            )
        )
        rows.append(
            _etf_flow(
                "FBTC",
                observation_date,
                str(fbtc_flow),
                aum_usd=(
                    str(Decimal(fbtc_aum) + Decimal(index * 20_000_000))
                    if fbtc_aum is not None
                    else None
                ),
            )
        )
    return rows


def _flow_rows_with_revisions(dates: tuple[date, ...], as_of: datetime) -> tuple:
    """Rows plus a later visible revision and an invisible (post-as_of) revision."""

    rows = _flow_rows(dates)
    revised_date = dates[-2]
    first_publication = datetime(
        revised_date.year, revised_date.month, revised_date.day, 13, 30, tzinfo=UTC
    ) + timedelta(days=1)
    # Visible revision: supersedes the initial IBIT print for dates[-2].
    rows.append(
        _etf_flow(
            "IBIT",
            revised_date,
            "210000000",
            aum_usd="17100000000",
            revision="revised-1",
            available_at=first_publication + timedelta(hours=6),
        )
    )
    # Invisible revision: published after the signal time, must be ignored.
    rows.append(
        _etf_flow(
            "IBIT",
            revised_date,
            "999000000",
            aum_usd="99900000000",
            revision="revised-2",
            available_at=as_of + timedelta(days=2),
        )
    )
    # A next-day print that is not yet available at as_of (look-ahead row).
    rows.append(
        _etf_flow(
            "FBTC",
            dates[-1] + timedelta(days=3),
            "55000000",
            aum_usd="5500000000",
            available_at=as_of + timedelta(days=3),
        )
    )
    # Deterministic but unsorted input order.
    return tuple(reversed(rows))


def _hour(start: datetime, offset: int) -> datetime:
    return start + timedelta(hours=offset)


def _spot_bar(timestamp: datetime, *, close: Decimal, volume: Decimal):
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1h",
        open=close - Decimal("25"),
        high=close + Decimal("60"),
        low=close - Decimal("80"),
        close=close,
        volume=volume,
        provider="coinbase",
        # Bar timestamp is the bar open; the bar is ingested just after it closes.
        ingested_at=timestamp + timedelta(hours=1, minutes=1),
    )


def _perp_volume(timestamp: datetime, *, notional_usd: Decimal | None):
    return PerpVolume(
        observation_time=timestamp,
        exchange="binance",
        symbol="BTCUSDT",
        timeframe="1h",
        volume=Decimal("1000") if notional_usd is None else (notional_usd / Decimal("65000")).quantize(Decimal("0.001")),
        volume_unit="BTC",
        notional_usd=notional_usd,
        provider="binance",
        source="binance-futures-api",
        available_at=timestamp + timedelta(hours=1, minutes=1),
        ingested_at=timestamp + timedelta(hours=1, minutes=2),
    )


def _spot_close(index: int) -> Decimal:
    return Decimal(65000) + Decimal(index * 37) - Decimal((index % 5) * 90)


def _spot_volume(index: int) -> Decimal:
    return Decimal(120) + Decimal((index * 7) % 11) * Decimal("4.5") + Decimal(index) * Decimal("0.8")


def _perp_notional(index: int) -> Decimal:
    return Decimal(30_000_000) + Decimal((index * 5) % 13) * Decimal(900_000) + Decimal(index) * Decimal(150_000)


def _participation_rows(start: datetime, periods: int, *, perp_notional: bool = True) -> tuple[tuple, tuple]:
    spot_bars = [
        _spot_bar(_hour(start, index), close=_spot_close(index), volume=_spot_volume(index))
        for index in range(periods)
    ]
    perp_rows = [
        _perp_volume(_hour(start, index), notional_usd=_perp_notional(index) if perp_notional else None)
        for index in range(periods)
    ]
    # A perp row whose notional is unknown: the owner must skip it, not zero-fill it.
    perp_rows.append(_perp_volume(_hour(start, -1), notional_usd=None))
    # A spot bar that closes after the signal time: must be filtered.
    spot_bars.append(_spot_bar(_hour(start, periods), close=_spot_close(periods), volume=Decimal("9999")))
    return tuple(spot_bars), tuple(perp_rows)


def _cvd(timestamp: datetime, market_type: str, value: Decimal):
    return CvdObservation(
        observation_time=timestamp,
        market_type=market_type,
        cvd_usd=value,
        provider="synthetic",
        available_at=timestamp + timedelta(hours=1, minutes=1),
    )


def _cvd_series(start: datetime, periods: int) -> tuple:
    observations = []
    for index in range(periods):
        moment = _hour(start, index)
        spot = Decimal(1_000_000) + Decimal(index * 85_000) - Decimal((index % 4) * 120_000)
        perp = Decimal(-500_000) + Decimal(index * 40_000) + Decimal((index % 3) * 90_000)
        observations.append(_cvd(moment, "spot", spot))
        observations.append(_cvd(moment, "perp", perp))
    # A post-signal observation that must be ignored.
    observations.append(_cvd(_hour(start, periods), "spot", Decimal("99999999")))
    return tuple(observations)


# --- five_day_etf_flow --------------------------------------------------------------


def five_day_complete():
    as_of = datetime(2024, 4, 27, 14, 0, tzinfo=UTC)
    dates = _publication_dates_ending(date(2024, 4, 26), 7)
    return five_day_etf_flow(_flow_rows_with_revisions(dates, as_of), as_of=as_of, funds=FUNDS)


def five_day_missing_row():
    as_of = datetime(2024, 4, 27, 14, 0, tzinfo=UTC)
    dates = _publication_dates_ending(date(2024, 4, 26), 5)
    rows = [row for row in _flow_rows(dates) if not (row.fund == "FBTC" and row.observation_date == dates[2])]
    return five_day_etf_flow(tuple(rows), as_of=as_of, funds=FUNDS, end_date=date(2024, 4, 26))


def five_day_missing_aum():
    as_of = datetime(2024, 4, 27, 14, 0, tzinfo=UTC)
    dates = _publication_dates_ending(date(2024, 4, 26), 5)
    return five_day_etf_flow(tuple(_flow_rows(dates, fbtc_aum=None)), as_of=as_of, funds=FUNDS)


# --- twenty_day_etf_flow ------------------------------------------------------------


def twenty_day_complete_with_holiday():
    holidays = frozenset({GOOD_FRIDAY_2024})
    as_of = datetime(2024, 4, 13, 14, 0, tzinfo=UTC)
    dates = _publication_dates_ending(date(2024, 4, 12), 22, holidays)
    assert GOOD_FRIDAY_2024 not in dates
    return twenty_day_etf_flow(
        _flow_rows_with_revisions(dates, as_of),
        as_of=as_of,
        funds=FUNDS,
        market_holidays=(GOOD_FRIDAY_2024,),
    )


def twenty_day_missing_aum():
    holidays = frozenset({GOOD_FRIDAY_2024})
    as_of = datetime(2024, 4, 13, 14, 0, tzinfo=UTC)
    dates = _publication_dates_ending(date(2024, 4, 12), 20, holidays)
    return twenty_day_etf_flow(
        tuple(_flow_rows(dates, fbtc_aum=None)),
        as_of=as_of,
        funds=FUNDS,
        market_holidays=(GOOD_FRIDAY_2024,),
    )


def twenty_day_no_visible_rows():
    # Every row is published after the signal time: no fund universe, nothing visible.
    as_of = datetime(2024, 4, 13, 14, 0, tzinfo=UTC)
    dates = _publication_dates_ending(date(2024, 4, 12), 20)
    rows = tuple(
        _etf_flow(row.fund, row.observation_date, str(row.flow_usd), aum_usd=str(row.aum_usd), available_at=as_of + timedelta(days=30))
        for row in _flow_rows(dates)
    )
    return twenty_day_etf_flow(rows, as_of=as_of)


# --- etf_flow_acceleration ----------------------------------------------------------


def acceleration_complete():
    as_of = datetime(2024, 4, 27, 14, 0, tzinfo=UTC)
    dates = _publication_dates_ending(date(2024, 4, 26), 20)
    rows = _flow_rows_with_revisions(dates, as_of)
    five_day = five_day_etf_flow(rows, as_of=as_of, funds=FUNDS)
    twenty_day = twenty_day_etf_flow(rows, as_of=as_of, funds=FUNDS)
    return etf_flow_acceleration(five_day, twenty_day)


def acceleration_five_day_aum_missing():
    as_of = datetime(2024, 4, 27, 14, 0, tzinfo=UTC)
    dates = _publication_dates_ending(date(2024, 4, 26), 20)
    five_day = five_day_etf_flow(tuple(_flow_rows(dates[15:], fbtc_aum=None)), as_of=as_of, funds=FUNDS)
    twenty_day = twenty_day_etf_flow(tuple(_flow_rows(dates)), as_of=as_of, funds=FUNDS)
    return etf_flow_acceleration(five_day, twenty_day)


# --- spot_perp_participation_from_rows ----------------------------------------------


def participation_complete_champion_defaults():
    # Champion defaults: growth_window_periods=5, zscore_window_periods=20,
    # min_zscore_periods=None (-> 20). First growth value at index 9, so the
    # latest z-score needs 9 + 20 + 1 = 30 aligned hours; 36 are supplied.
    start = datetime(2024, 4, 1, 0, 0, tzinfo=UTC)
    periods = 36
    spot_bars, perp_rows = _participation_rows(start, periods)
    as_of = _hour(start, periods - 1) + timedelta(hours=1, minutes=2)
    return spot_perp_participation_from_rows(spot_bars, perp_rows, as_of=as_of)


def participation_perp_notional_missing():
    start = datetime(2024, 4, 1, 0, 0, tzinfo=UTC)
    periods = 36
    spot_bars, perp_rows = _participation_rows(start, periods, perp_notional=False)
    as_of = _hour(start, periods - 1) + timedelta(hours=1, minutes=2)
    return spot_perp_participation_from_rows(spot_bars, perp_rows, as_of=as_of)


def participation_short_history():
    start = datetime(2024, 4, 1, 0, 0, tzinfo=UTC)
    periods = 20
    spot_bars, perp_rows = _participation_rows(start, periods)
    as_of = _hour(start, periods - 1) + timedelta(hours=1, minutes=2)
    return spot_perp_participation_from_rows(spot_bars, perp_rows, as_of=as_of)


# --- spot_perp_cvd_spread ------------------------------------------------------------


def cvd_complete_champion_defaults():
    # Champion defaults: zscore_window_periods=20, min_zscore_periods=None (-> 20);
    # the latest z-score needs 21 aligned hours; 24 are supplied.
    start = datetime(2024, 4, 1, 0, 0, tzinfo=UTC)
    periods = 24
    as_of = _hour(start, periods - 1) + timedelta(hours=1, minutes=2)
    return spot_perp_cvd_spread(_cvd_series(start, periods), as_of=as_of)


def cvd_absent():
    # The champion has no CVD source: no observations at all.
    return spot_perp_cvd_spread((), as_of=datetime(2024, 4, 2, 0, 2, tzinfo=UTC))


def cvd_short_history():
    start = datetime(2024, 4, 1, 0, 0, tzinfo=UTC)
    periods = 12
    as_of = _hour(start, periods - 1) + timedelta(hours=1, minutes=2)
    return spot_perp_cvd_spread(_cvd_series(start, periods), as_of=as_of)


# --- calculate_flow_score -----------------------------------------------------------


def flow_score_full_model_champion():
    config = load_strategy_config()
    return calculate_flow_score(
        FlowScoreInput(
            etf_norm_5_zscore=Decimal("1.25"),
            etf_norm_20_zscore=Decimal("0.6"),
            flow_accel_zscore=Decimal("0.35"),
            cvd_spread_zscore=Decimal("0.9"),
            spot_dominance_zscore=Decimal("-0.4"),
        ),
        core_weights=config.scoring_weights.core_flow,
        full_weights=config.scoring_weights.full_flow,
        config_metadata=config.run_metadata(),
    )


def flow_score_etf_core_fallback_champion():
    # P1 inputs (CVD spread, spot dominance) missing -> ETF_CORE model, still complete.
    config = load_strategy_config()
    return calculate_flow_score(
        FlowScoreInput(
            etf_norm_5_zscore=Decimal("-0.8"),
            etf_norm_20_zscore=Decimal("-1.1"),
            flow_accel_zscore=Decimal("0.2"),
        ),
        core_weights=config.scoring_weights.core_flow,
        full_weights=config.scoring_weights.full_flow,
        config_metadata=config.run_metadata(),
    )


def flow_score_core_input_missing_champion():
    # A missing core component is never zero-filled: incomplete, no score.
    config = load_strategy_config()
    return calculate_flow_score(
        FlowScoreInput(
            etf_norm_5_zscore=Decimal("0.5"),
            etf_norm_20_zscore=None,
            flow_accel_zscore=Decimal("0.1"),
        ),
        core_weights=config.scoring_weights.core_flow,
        full_weights=config.scoring_weights.full_flow,
        config_metadata=config.run_metadata(),
    )


FIXTURES: dict[str, tuple[Callable[[], object], ...]] = {
    ROOT_FLOW_SCORE: (
        flow_score_full_model_champion,
        flow_score_etf_core_fallback_champion,
        flow_score_core_input_missing_champion,
    ),
    ROOT_FIVE_DAY: (five_day_complete, five_day_missing_row, five_day_missing_aum),
    ROOT_TWENTY_DAY: (twenty_day_complete_with_holiday, twenty_day_missing_aum, twenty_day_no_visible_rows),
    ROOT_ACCEL: (acceleration_complete, acceleration_five_day_aum_missing),
    ROOT_PARTICIPATION: (
        participation_complete_champion_defaults,
        participation_perp_notional_missing,
        participation_short_history,
    ),
    ROOT_CVD: (cvd_complete_champion_defaults, cvd_absent, cvd_short_history),
}


# --- RBT-002 R1 runtime cross-check -------------------------------------------------------

import functools as _functools  # noqa: E402

import pytest as _pytest  # noqa: E402

from btc_predictor.research_backtest import input_census as _input_census  # noqa: E402


@_functools.cache
def _census() -> _input_census.DecisionPathCensus:
    return _input_census.discover_decision_path()


@_pytest.mark.parametrize(
    "root, index",
    [(root, index) for root, thunks in sorted(FIXTURES.items()) for index in range(len(thunks))],
)
def test_the_static_census_contains_everything_this_root_traces(root: str, index: int) -> None:
    """Run the root on its synthetic fixture under sys.setprofile: every
    btc_predictor function entered and dataclass constructed must be in the
    static census, and the root itself must have run."""

    result, traced = _input_census.trace_owner_calls(FIXTURES[root][index])
    assert root in traced.functions
    assert _input_census.uncovered_traced(_census(), traced) == {"functions": [], "dataclasses": []}
    if index == 0 and hasattr(result, "complete"):
        assert result.complete is True
