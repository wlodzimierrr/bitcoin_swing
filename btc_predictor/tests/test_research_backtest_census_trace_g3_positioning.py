"""Deterministic synthetic fixtures for the positioning decision-path roots.

Group G3 (Rulebook 7.5 positioning composite and Rulebook 24 CROWDING) of the
RBT-002 correction R1 runtime cross-check. Every thunk is zero-argument, builds
its own synthetic inputs from ``btc_predictor`` owner types and the stdlib only,
and returns the root's result.

Determinism: no randomness, no wall clock, no network, no database. Every
timestamp is a fixed UTC instant inside 2023-03-01 .. 2023-05-31. The only file
touched is the pinned champion strategy config, read by the owner loader
``btc_predictor.config.load_strategy_config()`` where a root takes config
weights, thresholds or run metadata (as the champion composer does).

Window/min-observation parameters are left at the owner defaults, which are the
values the champion composer pins (see the ``_positioning.DEFAULT_*`` mapping in
``btc_predictor.research.prospective_integration_corpus_v2``): 7-day funding
average, 180-day z-score / percentile windows, 30 minimum observations, 7-day OI
growth window. The OI unit is the RBT-002 pinned unit, ``USD``.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btc_predictor.config import load_strategy_config
from btc_predictor.data import FundingRate, FuturesBasis, OpenInterest
from btc_predictor.features.positioning import (
    CrowdingFlagInput,
    MarketCapObservation,
    PositioningScoreInput,
    calculate_crowding_flag,
    calculate_positioning_score,
    funding_health,
    futures_basis_health,
    open_interest_growth_health,
    open_interest_intensity,
)

_ROOT = "btc_predictor.features.positioning."

# Fixed synthetic calendar: 60 daily observations from 2023-03-01 00:00 UTC.
_START = datetime(2023, 3, 1, tzinfo=UTC)
_DAYS = 60
_LAST = _START + timedelta(days=_DAYS - 1)  # 2023-04-29 00:00 UTC
_AS_OF = _LAST + timedelta(hours=1)  # signal instant just after the last close
_OI_UNIT = "USD"  # RBT-002 pinned open-interest unit


def _day(index: int) -> datetime:
    return _START + timedelta(days=index)


def _wave(index: int, multiplier: int, modulus: int) -> int:
    """Deterministic integer oscillation in ``0 .. modulus-1``."""

    return (index * multiplier) % modulus


# --- synthetic raw rows -----------------------------------------------------------------


def _funding_row(observation_time: datetime, rate: Decimal, *, delay_minutes: int = 1) -> FundingRate:
    return FundingRate(
        observation_time=observation_time,
        exchange="binance",
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        funding_rate=rate,
        funding_interval_hours=Decimal("8"),
        provider="binance",
        source="binance-api",
        available_at=observation_time + timedelta(minutes=delay_minutes),
        ingested_at=observation_time + timedelta(minutes=delay_minutes + 1),
    )


def _funding_rows(*, spike: bool = False, days: int = _DAYS) -> tuple[FundingRate, ...]:
    """Daily funding settlements; ``spike`` lifts the last three settlements."""

    rows = []
    for index in range(days):
        rate = Decimal("0.0001") * Decimal(_wave(index, 7, 11) - 3)
        if spike and index >= days - 3:
            rate = Decimal("0.0030")
        rows.append(_funding_row(_day(index), rate))
    return tuple(rows)


def _basis_row(observation_time: datetime, basis_rate: Decimal) -> FuturesBasis:
    return FuturesBasis(
        observation_time=observation_time,
        exchange="deribit",
        symbol="BTC",
        instrument="BTC-QUARTERLY",
        expiry=observation_time + timedelta(days=73),
        basis_rate=basis_rate,
        # 365 / 73 days to expiry = 5 exactly, so the annualized rate is a
        # terminating Decimal (keeps the zero-variance fixture exactly constant).
        annualized_basis_rate=basis_rate * Decimal("365") / Decimal("73"),
        provider="deribit",
        source="deribit-api",
        available_at=observation_time + timedelta(minutes=1),
        ingested_at=observation_time + timedelta(minutes=2),
    )


def _basis_rows(*, spike: bool = False, constant: bool = False, days: int = _DAYS) -> tuple[FuturesBasis, ...]:
    rows = []
    for index in range(days):
        if constant:
            basis_rate = Decimal("0.0150")
        else:
            basis_rate = Decimal("0.0100") + Decimal("0.0005") * Decimal(_wave(index, 5, 9))
        if spike and index == days - 1:
            basis_rate = Decimal("0.0400")
        rows.append(_basis_row(_day(index), basis_rate))
    return tuple(rows)


def _oi_row(observation_time: datetime, value: Decimal, *, unit: str = _OI_UNIT, exchange: str = "binance") -> OpenInterest:
    return OpenInterest(
        observation_time=observation_time,
        exchange=exchange,
        symbol="BTCUSDT",
        instrument="BTCUSDT-PERP",
        open_interest=value,
        open_interest_unit=unit,
        provider=exchange,
        source=f"{exchange}-api",
        available_at=observation_time + timedelta(minutes=1),
        ingested_at=observation_time + timedelta(minutes=2),
    )


def _oi_rows(*, spike: bool = False, unit: str = _OI_UNIT, days: int = _DAYS) -> tuple[OpenInterest, ...]:
    """Two exchanges per instant (aggregated by the owner), trend plus oscillation."""

    rows = []
    for index in range(days):
        base = (
            Decimal("6000000000")
            + Decimal("5000000") * Decimal(index)
            + Decimal("150000000") * Decimal(_wave(index, 7, 11))
        )
        if spike and index == days - 1:
            base = base * Decimal("1.6")
        rows.append(_oi_row(_day(index), base, unit=unit, exchange="binance"))
        rows.append(_oi_row(_day(index), base / Decimal("2"), unit=unit, exchange="bybit"))
    return tuple(rows)


def _market_cap_rows(days: int = _DAYS) -> tuple[MarketCapObservation, ...]:
    return tuple(
        MarketCapObservation(
            observation_time=_day(index),
            market_cap_usd=Decimal("450000000000") + Decimal("2000000000") * Decimal(_wave(index, 3, 7)),
            provider="coinmetrics",
            available_at=_day(index) + timedelta(hours=1),
        )
        for index in range(days)
    )


# --- funding_health -------------------------------------------------------------------


def funding_health_complete():
    """Main path: 60 settlements, 59 prior 7-day averages >= 30 -> complete."""

    return funding_health(_funding_rows(), as_of=_AS_OF)


def funding_health_input_missing():
    """Every row arrives after ``as_of`` -> point-in-time filter leaves nothing ->
    FUNDING_RATE_INPUT_MISSING (no zero fill)."""

    rows = tuple(_funding_row(_day(index), Decimal("0.0001"), delay_minutes=24 * 60 * 90) for index in range(_DAYS))
    return funding_health(rows, as_of=_AS_OF)


def funding_health_insufficient_history():
    """Only 10 settlements -> 9 prior averages < 30 -> FUNDING_HEALTH_INSUFFICIENT_HISTORY."""

    return funding_health(_funding_rows(days=10), as_of=_day(9) + timedelta(hours=1))


# --- futures_basis_health ---------------------------------------------------------------


def futures_basis_health_complete():
    return futures_basis_health(_basis_rows(), as_of=_AS_OF)


def futures_basis_health_input_missing():
    """No basis rows at all -> FUTURES_BASIS_INPUT_MISSING."""

    return futures_basis_health((), as_of=_AS_OF)


def futures_basis_health_zero_variance():
    """Constant annualized basis -> FUTURES_BASIS_ZERO_VARIANCE."""

    return futures_basis_health(_basis_rows(constant=True), as_of=_AS_OF)


# --- open_interest_growth_health ------------------------------------------------------


def open_interest_growth_health_complete():
    """60 instants x 2 exchanges; 7-day growth defined from day 7 -> 52 prior
    growth observations >= 30 -> complete."""

    return open_interest_growth_health(_oi_rows(), as_of=_AS_OF, open_interest_unit=_OI_UNIT)


def open_interest_growth_health_prior_missing():
    """Only 5 days of OI -> no observation 7 days earlier -> OI_GROWTH_PRIOR_INPUT_MISSING."""

    return open_interest_growth_health(
        _oi_rows(days=5),
        as_of=_day(4) + timedelta(hours=1),
        open_interest_unit=_OI_UNIT,
    )


def open_interest_growth_health_unit_mismatch():
    """Rows are BTC-denominated while the pinned unit is USD -> filtered out ->
    OI_GROWTH_INPUT_MISSING."""

    return open_interest_growth_health(_oi_rows(unit="BTC"), as_of=_AS_OF, open_interest_unit=_OI_UNIT)


# --- open_interest_intensity ----------------------------------------------------------


def open_interest_intensity_complete():
    return open_interest_intensity(
        _oi_rows(),
        _market_cap_rows(),
        as_of=_AS_OF,
        open_interest_unit=_OI_UNIT,
    )


def open_interest_intensity_market_cap_missing():
    """OI present but no market-cap observation -> OI_INTENSITY_MARKET_CAP_INPUT_MISSING."""

    return open_interest_intensity(_oi_rows(), (), as_of=_AS_OF, open_interest_unit=_OI_UNIT)


def open_interest_intensity_insufficient_history():
    """10 joint instants -> 9 prior intensities < 30 -> OI_INTENSITY_INSUFFICIENT_HISTORY."""

    return open_interest_intensity(
        _oi_rows(days=10),
        _market_cap_rows(days=10),
        as_of=_day(9) + timedelta(hours=1),
        open_interest_unit=_OI_UNIT,
    )


# --- calculate_positioning_score -------------------------------------------------------


def calculate_positioning_score_complete():
    """Main path: the four health components come from their owners on the same
    synthetic market (leverage_health = OI-intensity health, as the coverage
    classification maps it); weights and run metadata from the champion config."""

    config = load_strategy_config()
    funding = funding_health(_funding_rows(), as_of=_AS_OF)
    oi_growth = open_interest_growth_health(_oi_rows(), as_of=_AS_OF, open_interest_unit=_OI_UNIT)
    basis = futures_basis_health(_basis_rows(), as_of=_AS_OF)
    intensity = open_interest_intensity(_oi_rows(), _market_cap_rows(), as_of=_AS_OF, open_interest_unit=_OI_UNIT)
    inputs = PositioningScoreInput(
        funding_health=funding.health_score,
        oi_health=oi_growth.health_score,
        basis_health=basis.health_score,
        leverage_health=intensity.health_score,
    )
    return calculate_positioning_score(
        inputs,
        weights=config.scoring_weights.positioning,
        config_metadata=config.run_metadata(),
    )


def calculate_positioning_score_input_missing():
    """Leverage component unavailable (no market cap) -> score None,
    POSITIONING_SCORE_INPUT_MISSING (Rulebook 7.5 has no fallback)."""

    config = load_strategy_config()
    funding = funding_health(_funding_rows(), as_of=_AS_OF)
    oi_growth = open_interest_growth_health(_oi_rows(), as_of=_AS_OF, open_interest_unit=_OI_UNIT)
    basis = futures_basis_health(_basis_rows(), as_of=_AS_OF)
    intensity = open_interest_intensity(_oi_rows(), (), as_of=_AS_OF, open_interest_unit=_OI_UNIT)
    inputs = PositioningScoreInput(
        funding_health=funding.health_score,
        oi_health=oi_growth.health_score,
        basis_health=basis.health_score,
        leverage_health=intensity.health_score,
    )
    return calculate_positioning_score(
        inputs,
        weights=config.scoring_weights.positioning,
        config_metadata=config.run_metadata(),
    )


# --- calculate_crowding_flag ---------------------------------------------------------


def _crowding(inputs: CrowdingFlagInput):
    config = load_strategy_config()
    crowding = config.positioning_flags.crowding
    return calculate_crowding_flag(
        inputs,
        funding_zscore_min=crowding.funding_zscore_min,
        basis_zscore_min=crowding.basis_zscore_min,
        oi_intensity_percentile_min=crowding.oi_intensity_percentile_min,
        entry_quality_penalty=crowding.entry_quality_penalty,
        config_metadata=config.run_metadata(),
    )


def calculate_crowding_flag_detected():
    """Main path: complete inputs from the owners on a crowded synthetic market
    (funding spike, basis spike, OI spike) -> complete and flagged."""

    funding = funding_health(_funding_rows(spike=True), as_of=_AS_OF)
    basis = futures_basis_health(_basis_rows(spike=True), as_of=_AS_OF)
    intensity = open_interest_intensity(
        _oi_rows(spike=True),
        _market_cap_rows(),
        as_of=_AS_OF,
        open_interest_unit=_OI_UNIT,
    )
    return _crowding(
        CrowdingFlagInput(
            funding_zscore=funding.funding_zscore,
            basis_zscore=basis.annualized_basis_zscore,
            oi_intensity_percentile=intensity.oi_intensity_percentile,
        )
    )


def calculate_crowding_flag_input_missing():
    """Funding history too short -> funding z-score None -> CROWDING_INPUT_MISSING
    (complete False; never silently cleared)."""

    funding = funding_health(_funding_rows(days=10), as_of=_day(9) + timedelta(hours=1))
    basis = futures_basis_health(_basis_rows(), as_of=_AS_OF)
    intensity = open_interest_intensity(_oi_rows(), _market_cap_rows(), as_of=_AS_OF, open_interest_unit=_OI_UNIT)
    return _crowding(
        CrowdingFlagInput(
            funding_zscore=funding.funding_zscore,
            basis_zscore=basis.annualized_basis_zscore,
            oi_intensity_percentile=intensity.oi_intensity_percentile,
        )
    )


def calculate_crowding_flag_clear():
    """Complete inputs on the calm synthetic market -> complete and not flagged."""

    funding = funding_health(_funding_rows(), as_of=_AS_OF)
    basis = futures_basis_health(_basis_rows(), as_of=_AS_OF)
    intensity = open_interest_intensity(_oi_rows(), _market_cap_rows(), as_of=_AS_OF, open_interest_unit=_OI_UNIT)
    return _crowding(
        CrowdingFlagInput(
            funding_zscore=funding.funding_zscore,
            basis_zscore=basis.annualized_basis_zscore,
            oi_intensity_percentile=intensity.oi_intensity_percentile,
        )
    )


FIXTURES: dict[str, tuple[Callable[[], object], ...]] = {
    _ROOT + "calculate_positioning_score": (
        calculate_positioning_score_complete,
        calculate_positioning_score_input_missing,
    ),
    _ROOT + "funding_health": (
        funding_health_complete,
        funding_health_input_missing,
        funding_health_insufficient_history,
    ),
    _ROOT + "open_interest_growth_health": (
        open_interest_growth_health_complete,
        open_interest_growth_health_prior_missing,
        open_interest_growth_health_unit_mismatch,
    ),
    _ROOT + "open_interest_intensity": (
        open_interest_intensity_complete,
        open_interest_intensity_market_cap_missing,
        open_interest_intensity_insufficient_history,
    ),
    _ROOT + "futures_basis_health": (
        futures_basis_health_complete,
        futures_basis_health_input_missing,
        futures_basis_health_zero_variance,
    ),
    _ROOT + "calculate_crowding_flag": (
        calculate_crowding_flag_detected,
        calculate_crowding_flag_input_missing,
        calculate_crowding_flag_clear,
    ),
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
