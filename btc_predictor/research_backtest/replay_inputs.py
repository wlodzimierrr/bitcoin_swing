"""Historical replay inputs for the EPIC Y research backtest (RBT-001).

``HISTORICAL_REPLAY_AVAILABILITY_V1`` is section 4 of
``RESEARCH_BACKTEST_POLICY_V2``. A backfill stamps every row it writes with one
bulk ingestion time, and the frozen BTC-180 engine reads ``OhlcvBar.ingested_at``
as live availability, so a dataset built the repository's own way replays with
no executable decision (the EPIC S audit). Nothing here rewrites a raw row. The
builder returns *derived replay inputs* -- copies of the raw owner records whose
availability field carries the modelled availability -- and a content-addressed
manifest that keeps every record's raw timestamps beside the modelled one.

Modelled availability, never earlier than the observation's close or end:

======================================  =========================================
input                                   modelled availability
======================================  =========================================
``1h`` price bar, one venue             its close boundary, ``timestamp + 1h``
derived daily/weekly/monthly bar        the close boundary of its last constituent
                                        hour, derived by BTC-040 at the decision
                                        instant (:func:`replay_market_bars_at`)
ETF flow and AUM, US trading date T     ``00:00`` UTC on calendar day ``T+2``, or
                                        the source's own later publication or
                                        revision time when it supplies one
funding rate settled at S               ``S``
open-interest snapshot at t             ``t``: the owner defines a snapshot and
                                        no interval, so the snapshot instant is
                                        its own end
perpetual volume interval               its end ``E = next_bar_timestamp(
                                        observation_time, timeframe)``
======================================  =========================================

``PerpVolume.observation_time`` is read as the interval *start*. That is an
assumption this module surfaces, not an owner fact: the schema allows "bar
timestamp or period end". It is the reading ``spot_perp_participation`` needs,
because it joins perp ``observation_time`` to the start-stamped
``OhlcvBar.timestamp`` by equality, and it can only delay an end-stamped row,
never advance it. RBT-003 must therefore persist perpetual volume stamped at
the interval start.

The modelled value goes into exactly the field each owner's point-in-time
predicate reads, and every other field keeps its raw value:

- ``OhlcvBar.ingested_at`` -- the BTC-180 engine (``max(close, ingested_at)``),
  BTC-040 ``build_canonical_market_bars``, BTC-161/162 execution and the
  spot side of ``spot_perp_participation_from_rows``;
- ``EtfFlow.available_at`` -- ``features.flow`` and
  ``data.etf_flows.latest_etf_flows_available_at``;
- ``FundingRate`` / ``OpenInterest`` / ``PerpVolume`` ``available_at`` --
  ``features.positioning``, ``data.derivatives``, ``data.quality`` and the perp
  side of ``spot_perp_participation``; those predicates also require
  ``observation_time <= signal time``, which modelled availability implies.

No owner reads ``ingested_at`` on an ETF or derivative record, so the replay
copy keeps the raw value there. The manifest records every raw time field
beside the modelled availability.

The replay window is one member of the closed policy section 3 enumeration.
Every record is admitted only if its whole observation interval lies inside
the requested window's admitted windows; anything else is refused, never
dropped. Records before ``2020-01-01 00:00`` UTC protect the sealed BTC-019
sample, the holdout stays shut behind :data:`HOLDOUT_OPENING_AUTHORIZED` until
RBT-008 lifts it in its own reviewed commit, and the reserve is never replayed.

One venue per price series and no splicing or fallback: the reference ``1h``
series belongs to exactly one ``PRICE_SOURCE_POLICY_V1`` required venue, gaps
are preserved and counted, and every non-price input -- including the retained
Bitstamp raw OHLCV that feeds volume and spot participation -- forms one shared
snapshot whose manifest digest is identical across the three venue runs.

Everything produced here is ``RESEARCH_BACKTEST_NON_CERTIFYING`` evidence with
the canonical reference ``UNRESOLVED``.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from btc_predictor.backtest.engine import validate_backtest_bars
from btc_predictor.data import (
    BITFINEX_BTC_USD_API_SYMBOL,
    BITFINEX_BTC_USD_SYMBOL,
    BITFINEX_EXCHANGE,
    BITFINEX_PROVIDER_ID,
    BITSTAMP_BTC_USD_API_SYMBOL,
    BITSTAMP_BTC_USD_SYMBOL,
    BITSTAMP_EXCHANGE,
    BITSTAMP_PROVIDER_ID,
    CANONICAL_MARKET_BAR_TIMEFRAMES,
    COINBASE_BTC_USD_API_SYMBOL,
    COINBASE_BTC_USD_SYMBOL,
    COINBASE_EXCHANGE,
    COINBASE_PROVIDER_ID,
    DerivativesQualityConfig,
    EtfFlow,
    FundingRate,
    OhlcvBar,
    OpenInterest,
    PerpVolume,
    build_canonical_market_bars,
    expected_bar_timestamps,
    expected_etf_publication_dates,
    missing_bar_timestamps,
    missing_etf_publication_dates,
    next_bar_timestamp,
    require_utc_datetime,
    validate_derivatives_quality,
)
from btc_predictor.features.flow import _latest_available_flows_by_fund_date


REPLAY_INPUTS_BUILDER_VERSION = "BUILD_HISTORICAL_REPLAY_INPUTS_V1"
RESEARCH_BACKTEST_POLICY_VERSION = "RESEARCH_BACKTEST_POLICY_V2"
REPLAY_AVAILABILITY_POLICY_VERSION = "HISTORICAL_REPLAY_AVAILABILITY_V1"
REPLAY_DATASET_MANIFEST_VERSION = "HISTORICAL_REPLAY_DATASET_MANIFEST_V1"
SHARED_SNAPSHOT_MANIFEST_VERSION = "HISTORICAL_REPLAY_SHARED_SNAPSHOT_MANIFEST_V1"
RESEARCH_EVIDENCE_CLASS = "RESEARCH_BACKTEST_NON_CERTIFYING"
CANONICAL_REFERENCE_UNRESOLVED = "UNRESOLVED"
REVISION_HISTORY_UNAVAILABLE = "REVISION_HISTORY_UNAVAILABLE"
REPLAY_SOURCE_TIMEFRAME = "1h"

# Only RBT-008 may set this to True, in its own reviewed commit, after the
# RBT-007 review passes. Until then a holdout replay is refused outright and
# every record dated in the holdout is refused from any replay.
HOLDOUT_OPENING_AUTHORIZED = False

REPLAY_REFUSAL_REASON_CODES = (
    "UNKNOWN_REPLAY_WINDOW",
    "PROHIBITED_WINDOW_REFUSED",
    "HOLDOUT_WINDOW_NOT_AUTHORIZED",
    "RESERVE_WINDOW_REFUSED",
    "PRE_2020_RECORD_REFUSED",
    "HOLDOUT_RECORD_REFUSED",
    "RESERVE_RECORD_REFUSED",
    "UNKNOWN_REPLAY_VENUE",
    "RECORD_TYPE_REFUSED",
    "OWNER_RECORD_REFUSED",
    "NON_UTC_TIMESTAMP_REFUSED",
    "SOURCE_TIMEFRAME_REFUSED",
    "MIXED_VENUE_SERIES_REFUSED",
    "SHARED_VOLUME_SOURCE_REFUSED",
    "DUPLICATE_RECORD_REFUSED",
    "EMPTY_PRICE_SERIES_REFUSED",
    "ENGINE_BAR_CONTRACT_REFUSED",
    "UNSUPPORTED_OBSERVATION_INTERVAL",
    "ETF_REVISION_ORDER_UNAVAILABLE",
    "DUPLICATE_SOURCE_PUBLICATION_TIME",
    "UNMATCHED_SOURCE_PUBLICATION_TIME",
    "SHARED_SNAPSHOT_WINDOW_MISMATCH",
    "NOT_A_REPLAY_BAR",
    "SOURCE_PUBLICATION_BEFORE_OBSERVATION",
)

REFERENCE_PRICE_FAMILY = "REFERENCE_PRICE_1H"
SHARED_VOLUME_FAMILY = "SHARED_RAW_VOLUME_1H"
ETF_FLOW_FAMILY = "ETF_FLOW_AND_AUM"
FUNDING_RATE_FAMILY = "FUNDING_RATE"
OPEN_INTEREST_FAMILY = "OPEN_INTEREST"
PERP_VOLUME_FAMILY = "PERP_VOLUME"
SHARED_SNAPSHOT_FAMILIES = (
    SHARED_VOLUME_FAMILY,
    ETF_FLOW_FAMILY,
    FUNDING_RATE_FAMILY,
    OPEN_INTEREST_FAMILY,
    PERP_VOLUME_FAMILY,
)

_ONE_MICROSECOND = timedelta(microseconds=1)
_DERIVATIVES_QUALITY_CONFIG = DerivativesQualityConfig()
_ONE_DAY = timedelta(days=1)


class ReplayInputRefused(ValueError):
    """An input cannot enter a replay. The build fails; nothing is dropped."""

    def __init__(self, reason_code: str, message: str) -> None:
        if reason_code not in REPLAY_REFUSAL_REASON_CODES:
            raise ValueError(f"undeclared replay refusal reason code: {reason_code}")
        super().__init__(f"{reason_code}: {message}")
        self.reason_code = reason_code


# --- the closed policy section 3 window enumeration -------------------------


@dataclass(frozen=True)
class ReplayWindow:
    """One member of the closed ``RESEARCH_BACKTEST_POLICY_V2`` section 3 enumeration.

    ``start`` is inclusive and ``end`` exclusive, so every UTC instant belongs to
    exactly one window. The policy's inclusive labels (for the data window,
    ``2020-01-01 00:00 .. 2025-12-31 23:00``) are the first and last ``1h`` bar a
    window admits.
    """

    window_id: str
    start: datetime | None
    end: datetime | None

    def contains(self, instant: datetime) -> bool:
        moment = _utc(instant, "instant")
        return (self.start is None or self.start <= moment) and (
            self.end is None or moment < self.end
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "window_id": self.window_id,
            "start": _iso(self.start),
            "end_exclusive": _iso(self.end),
            "first_hour": _iso(self.start),
            "last_hour": _iso(self.end - timedelta(hours=1) if self.end else None),
        }


_DATA_START = datetime(2020, 1, 1, tzinfo=UTC)
_HOLDOUT_START = datetime(2026, 1, 1, tzinfo=UTC)
_RESERVE_START = datetime(2026, 7, 1, tzinfo=UTC)

PROHIBITED_WINDOW = ReplayWindow("PROHIBITED", None, _DATA_START)
DATA_WINDOW = ReplayWindow("DATA", _DATA_START, _HOLDOUT_START)
HOLDOUT_WINDOW = ReplayWindow("HOLDOUT", _HOLDOUT_START, _RESERVE_START)
RESERVE_WINDOW = ReplayWindow("RESERVE", _RESERVE_START, None)
REPLAY_WINDOWS = (PROHIBITED_WINDOW, DATA_WINDOW, HOLDOUT_WINDOW, RESERVE_WINDOW)

# Which observation windows a replay of each window may read. A holdout replay
# (RBT-008) takes its warm-up only from the data window.
_ADMITTED_OBSERVATION_WINDOWS = {
    DATA_WINDOW.window_id: (DATA_WINDOW,),
    HOLDOUT_WINDOW.window_id: (DATA_WINDOW, HOLDOUT_WINDOW),
}


def replay_window_of(instant: datetime) -> ReplayWindow:
    """Return the one enumerated window that contains ``instant``."""

    matches = [window for window in REPLAY_WINDOWS if window.contains(instant)]
    if len(matches) != 1:
        raise RuntimeError("the replay window enumeration must partition time")
    return matches[0]


def require_replay_window(window: ReplayWindow) -> ReplayWindow:
    """Refuse every window a replay may not be built for."""

    if not isinstance(window, ReplayWindow) or window not in REPLAY_WINDOWS:
        raise ReplayInputRefused(
            "UNKNOWN_REPLAY_WINDOW",
            "the replay window must be one of the enumerated policy section 3 windows",
        )
    if window == PROHIBITED_WINDOW:
        raise ReplayInputRefused(
            "PROHIBITED_WINDOW_REFUSED",
            "nothing before 2020-01-01 00:00 UTC may be replayed (sealed BTC-019 sample)",
        )
    if window == RESERVE_WINDOW:
        raise ReplayInputRefused(
            "RESERVE_WINDOW_REFUSED",
            "the reserve window is not used by EPIC Y",
        )
    if window == HOLDOUT_WINDOW and not HOLDOUT_OPENING_AUTHORIZED:
        raise ReplayInputRefused(
            "HOLDOUT_WINDOW_NOT_AUTHORIZED",
            "the holdout is shut until RBT-008 lifts HOLDOUT_OPENING_AUTHORIZED "
            "in its own reviewed commit",
        )
    return window


def _require_admitted(
    window: ReplayWindow,
    first_instant: datetime,
    last_instant: datetime,
    *,
    what: str,
) -> None:
    admitted = _ADMITTED_OBSERVATION_WINDOWS[window.window_id]
    for instant in (first_instant, last_instant):
        observed = replay_window_of(instant)
        if observed in admitted and (
            observed != HOLDOUT_WINDOW or HOLDOUT_OPENING_AUTHORIZED
        ):
            continue
        if observed == PROHIBITED_WINDOW:
            raise ReplayInputRefused(
                "PRE_2020_RECORD_REFUSED",
                f"{what} observes {instant.isoformat()}, before 2020-01-01 00:00 UTC",
            )
        if observed == RESERVE_WINDOW:
            raise ReplayInputRefused(
                "RESERVE_RECORD_REFUSED",
                f"{what} observes {instant.isoformat()}, inside the reserve window",
            )
        raise ReplayInputRefused(
            "HOLDOUT_RECORD_REFUSED",
            f"{what} observes {instant.isoformat()}, inside the holdout window",
        )


# --- the three PRICE_SOURCE_POLICY_V1 required venues -----------------------


@dataclass(frozen=True)
class ReplayVenue:
    """One ``PRICE_SOURCE_POLICY_V1`` required venue. None is canonical."""

    venue_id: str
    exchange: str
    symbol: str
    provider: str
    api_instrument: str

    def owns(self, bar: OhlcvBar) -> bool:
        return (bar.exchange, bar.symbol, bar.provider) == (
            self.exchange,
            self.symbol,
            self.provider,
        )

    def as_record(self) -> dict[str, str]:
        return {
            "venue_id": self.venue_id,
            "exchange": self.exchange,
            "symbol": self.symbol,
            "provider": self.provider,
            "api_instrument": self.api_instrument,
        }


BITSTAMP_REPLAY_VENUE = ReplayVenue(
    "BITSTAMP",
    BITSTAMP_EXCHANGE,
    BITSTAMP_BTC_USD_SYMBOL,
    BITSTAMP_PROVIDER_ID,
    BITSTAMP_BTC_USD_API_SYMBOL,
)
COINBASE_REPLAY_VENUE = ReplayVenue(
    "COINBASE",
    COINBASE_EXCHANGE,
    COINBASE_BTC_USD_SYMBOL,
    COINBASE_PROVIDER_ID,
    COINBASE_BTC_USD_API_SYMBOL,
)
BITFINEX_REPLAY_VENUE = ReplayVenue(
    "BITFINEX",
    BITFINEX_EXCHANGE,
    BITFINEX_BTC_USD_SYMBOL,
    BITFINEX_PROVIDER_ID,
    BITFINEX_BTC_USD_API_SYMBOL,
)
REPLAY_VENUES = (BITSTAMP_REPLAY_VENUE, COINBASE_REPLAY_VENUE, BITFINEX_REPLAY_VENUE)
# Policy section 2: volume and spot participation use the retained primary raw
# OHLCV source in all three runs.
SHARED_VOLUME_VENUE = BITSTAMP_REPLAY_VENUE


# --- the policy section 4 availability table --------------------------------


@dataclass(frozen=True)
class ReplayAvailabilityRule:
    """How one input family's availability is modelled and where it is placed."""

    family: str
    owner_record: str
    observation_convention: str
    observation_convention_basis: str
    modelled_availability: str
    availability_field: str
    raw_time_fields: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "family": self.family,
            "owner_record": self.owner_record,
            "observation_convention": self.observation_convention,
            "observation_convention_basis": self.observation_convention_basis,
            "modelled_availability": self.modelled_availability,
            "availability_field": self.availability_field,
            "raw_time_fields": list(self.raw_time_fields),
        }


_BAR_RULE_FIELDS = {
    "owner_record": "OhlcvBar",
    "observation_convention": "BAR_START_1H",
    "observation_convention_basis": (
        "OHLCV owner: the close is next_bar_timestamp(timestamp, timeframe)"
    ),
    "modelled_availability": "BAR_CLOSE_BOUNDARY",
    "availability_field": "ingested_at",
    "raw_time_fields": ("ingested_at",),
}
REPLAY_AVAILABILITY_RULES = {
    REFERENCE_PRICE_FAMILY: ReplayAvailabilityRule(REFERENCE_PRICE_FAMILY, **_BAR_RULE_FIELDS),
    SHARED_VOLUME_FAMILY: ReplayAvailabilityRule(SHARED_VOLUME_FAMILY, **_BAR_RULE_FIELDS),
    ETF_FLOW_FAMILY: ReplayAvailabilityRule(
        ETF_FLOW_FAMILY,
        owner_record="EtfFlow",
        observation_convention="US_TRADING_DATE",
        observation_convention_basis="EtfFlow.observation_date is the US trading date",
        modelled_availability="T_PLUS_2_0000_UTC_OR_LATER_SOURCE_PUBLICATION",
        availability_field="available_at",
        raw_time_fields=("available_at", "ingested_at"),
    ),
    FUNDING_RATE_FAMILY: ReplayAvailabilityRule(
        FUNDING_RATE_FAMILY,
        owner_record="FundingRate",
        observation_convention="SETTLEMENT_INSTANT",
        observation_convention_basis=(
            "raw schema: funding timestamp or period end reported by the exchange"
        ),
        modelled_availability="SETTLEMENT_INSTANT",
        availability_field="available_at",
        raw_time_fields=("available_at", "ingested_at"),
    ),
    OPEN_INTEREST_FAMILY: ReplayAvailabilityRule(
        OPEN_INTEREST_FAMILY,
        owner_record="OpenInterest",
        observation_convention="SNAPSHOT_INSTANT",
        observation_convention_basis=(
            "raw schema: market timestamp of the open-interest snapshot; the record "
            "has no interval field"
        ),
        modelled_availability="SNAPSHOT_INSTANT",
        availability_field="available_at",
        raw_time_fields=("available_at", "ingested_at"),
    ),
    PERP_VOLUME_FAMILY: ReplayAvailabilityRule(
        PERP_VOLUME_FAMILY,
        owner_record="PerpVolume",
        observation_convention="INTERVAL_START",
        observation_convention_basis=(
            "ASSUMED: the raw schema allows bar timestamp or period end; "
            "features.flow joins perp observation_time to the start-stamped "
            "OhlcvBar.timestamp, and RBT-003 must stamp interval starts"
        ),
        modelled_availability="INTERVAL_END",
        availability_field="available_at",
        raw_time_fields=("available_at", "ingested_at"),
    ),
}
DERIVED_MARKET_BAR_DERIVATION = (
    "BTC-040 build_canonical_market_bars(data_available_at=decision instant)"
)
DERIVED_MARKET_BAR_AVAILABILITY = "LAST_CONSTITUENT_HOUR_CLOSE_BOUNDARY"


def modelled_bar_available_at(bar: OhlcvBar) -> datetime:
    """A ``1h`` price bar is available at its close boundary."""

    _require_type(bar, OhlcvBar, "bar")
    if bar.timeframe != REPLAY_SOURCE_TIMEFRAME:
        raise ReplayInputRefused(
            "SOURCE_TIMEFRAME_REFUSED",
            f"the replay stream is the persisted 1h series, not {bar.timeframe!r}",
        )
    return next_bar_timestamp(_utc(bar.timestamp, "bar.timestamp"), REPLAY_SOURCE_TIMEFRAME)


def etf_trading_day_start(observation_date: date) -> datetime:
    """``00:00`` UTC on US trading date ``T``: no source can publish ``T`` earlier."""

    if type(observation_date) is not date:
        raise ReplayInputRefused(
            "RECORD_TYPE_REFUSED",
            "an ETF observation_date must be a datetime.date",
        )
    return datetime.combine(observation_date, time(0), tzinfo=UTC)


def etf_trading_day_end(observation_date: date) -> datetime:
    """The end of US trading date ``T`` as a UTC day: ``00:00`` UTC on ``T+1``.

    The US session of ``T`` closes inside that UTC day, so this is the latest
    instant the flow's observation can end.
    """

    if type(observation_date) is not date:
        raise ReplayInputRefused(
            "RECORD_TYPE_REFUSED",
            "an ETF observation_date must be a datetime.date",
        )
    return datetime.combine(observation_date + _ONE_DAY, time(0), tzinfo=UTC)


def etf_flow_scheduled_available_at(observation_date: date) -> datetime:
    """``00:00`` UTC on calendar day ``T+2`` for US trading date ``T``."""

    return etf_trading_day_end(observation_date) + _ONE_DAY


def modelled_etf_flow_available_at(
    flow: EtfFlow,
    *,
    source_published_at: datetime | None = None,
) -> datetime:
    """ETF flow and AUM: ``T+2 00:00`` UTC, or the source's own later time."""

    _require_type(flow, EtfFlow, "flow")
    scheduled = etf_flow_scheduled_available_at(flow.observation_date)
    if source_published_at is None:
        return scheduled
    return max(scheduled, _utc(source_published_at, "source_published_at"))


def modelled_funding_rate_available_at(rate: FundingRate) -> datetime:
    """Funding settled at ``S`` is available at ``S``."""

    _require_type(rate, FundingRate, "funding rate")
    return _utc(rate.observation_time, "funding_rate.observation_time")


def modelled_open_interest_available_at(snapshot: OpenInterest) -> datetime:
    """An open-interest snapshot at ``t`` is available at ``t``."""

    _require_type(snapshot, OpenInterest, "open interest")
    return _utc(snapshot.observation_time, "open_interest.observation_time")


def perp_volume_interval_end(volume: PerpVolume) -> datetime:
    """The end of the interval a start-stamped perpetual volume row aggregates."""

    _require_type(volume, PerpVolume, "perp volume")
    start = _utc(volume.observation_time, "perp_volume.observation_time")
    try:
        return next_bar_timestamp(start, volume.timeframe)
    except (ValueError, OverflowError) as exc:
        raise ReplayInputRefused(
            "UNSUPPORTED_OBSERVATION_INTERVAL",
            f"perp volume timeframe {volume.timeframe!r} has no owner interval: {exc}",
        ) from exc


def modelled_perp_volume_available_at(volume: PerpVolume) -> datetime:
    """A perpetual-volume interval ending at ``E`` is available at ``E``."""

    return perp_volume_interval_end(volume)


def funding_interval(rate: FundingRate) -> timedelta:
    """The funding period a settlement declares through ``funding_interval_hours``."""

    _require_type(rate, FundingRate, "funding rate")
    hours = rate.funding_interval_hours
    if not isinstance(hours, Decimal) or not hours.is_finite() or hours <= 0:
        raise ReplayInputRefused(
            "UNSUPPORTED_OBSERVATION_INTERVAL",
            "funding_interval_hours must be a positive finite Decimal",
        )
    seconds = hours * Decimal(3600)
    if seconds != seconds.to_integral_value():
        raise ReplayInputRefused(
            "UNSUPPORTED_OBSERVATION_INTERVAL",
            "funding_interval_hours must be a whole number of seconds",
        )
    try:
        return timedelta(seconds=int(seconds))
    except OverflowError as exc:
        raise ReplayInputRefused(
            "UNSUPPORTED_OBSERVATION_INTERVAL",
            f"funding_interval_hours {hours} is not a representable interval",
        ) from exc


# --- decision-instant market bars ------------------------------------------


def replay_market_bars_at(
    replay_bars: Sequence[OhlcvBar],
    *,
    decision_at: datetime,
    window: ReplayWindow,
    timeframes: Sequence[str] = CANONICAL_MARKET_BAR_TIMEFRAMES,
) -> tuple[OhlcvBar, ...]:
    """Derive the daily, weekly and monthly replay bars visible at ``decision_at``.

    BTC-040 ``build_canonical_market_bars`` does the derivation with the
    decision instant as its point-in-time cutoff, so only complete buckets whose
    every hour is available by then exist. It stamps the cutoff into
    ``ingested_at``; the replay copy instead carries the close boundary of the
    bucket's last constituent hour, read from that hour's replay bar.

    The source bars are held to the same rules as a venue replay stream: ``1h``
    bars of one required venue, each carrying its modelled availability, all
    admitted by ``window``, valid owner records, no duplicate hour, and the
    BTC-180 bar contract.
    """

    replay_window = require_replay_window(window)
    cutoff = _utc(decision_at, "decision_at")
    ordered = tuple(replay_bars)
    availability_by_hour: dict[datetime, datetime] = {}
    venues = set()
    for bar in ordered:
        _require_type(bar, OhlcvBar, "replay bar")
        if bar.timeframe != REPLAY_SOURCE_TIMEFRAME or bar.ingested_at != modelled_bar_available_at(bar):
            raise ReplayInputRefused(
                "NOT_A_REPLAY_BAR",
                "decision-instant bars derive only from 1h replay bars carrying "
                f"{REPLAY_AVAILABILITY_POLICY_VERSION} availability",
            )
        owners = [venue for venue in REPLAY_VENUES if venue.owns(bar)]
        if not owners:
            raise ReplayInputRefused(
                "UNKNOWN_REPLAY_VENUE",
                f"a {bar.exchange}/{bar.symbol}/{bar.provider} bar belongs to no "
                "PRICE_SOURCE_POLICY_V1 required venue",
            )
        venues.add(owners[0])
        if len(venues) > 1:
            raise ReplayInputRefused(
                "MIXED_VENUE_SERIES_REFUSED",
                "decision-instant bars derive from one venue's series; no splicing or fallback",
            )
        _require_admitted(
            replay_window,
            bar.timestamp,
            bar.ingested_at - _ONE_MICROSECOND,
            what=f"{REFERENCE_PRICE_FAMILY} bar",
        )
        _require_owner_record(bar, "OHLCV bar")
        _require_decimal_fields(bar, ("open", "high", "low", "close", "volume"), ())
        if bar.timestamp in availability_by_hour:
            raise ReplayInputRefused(
                "DUPLICATE_RECORD_REFUSED",
                f"decision-instant bars carry two bars at {bar.timestamp.isoformat()}",
            )
        availability_by_hour[bar.timestamp] = bar.ingested_at
    ordered = tuple(sorted(ordered, key=lambda bar: bar.timestamp))
    if venues:
        try:
            validate_backtest_bars(ordered, symbol=next(iter(venues)).symbol)
        except (TypeError, ValueError) as exc:
            raise ReplayInputRefused(
                "ENGINE_BAR_CONTRACT_REFUSED",
                f"decision-instant source bars fail the BTC-180 bar contract: {exc}",
            ) from exc
    derived = build_canonical_market_bars(
        ordered,
        data_available_at=cutoff,
        timeframes=timeframes,
    )
    replayed = []
    for bar in derived:
        last_hour = next_bar_timestamp(bar.timestamp, bar.timeframe) - timedelta(hours=1)
        available_at = availability_by_hour[last_hour]
        if available_at > cutoff:
            raise RuntimeError("BTC-040 derived a bucket that is not yet available")
        replayed.append(replace(bar, ingested_at=available_at))
    return tuple(replayed)


# --- manifest records --------------------------------------------------------


@dataclass(frozen=True)
class EtfSourcePublicationTime:
    """A publication or revision time the ETF flow source itself supplied.

    It names one raw revision by the owner's identity. ``T+2 00:00`` UTC remains
    the floor: a supplied time earlier than that does not advance availability,
    and a time before the trading date itself is refused as impossible.

    Publication timing alone says nothing about revision-history coverage.
    ``revision_history_available`` may be asserted only when the source also
    supplies the historical values for this revision's fund and trading date.
    RBT-003 must persist that source evidence; a final-only export leaves it
    false, even when the final revision has a publication timestamp.
    """

    fund: str
    observation_date: date
    provider: str
    revision: str
    published_at: datetime
    revision_history_available: bool = False

    def key(self) -> tuple[str, date, str, str]:
        return (self.fund, self.observation_date, self.provider, self.revision)


@dataclass(frozen=True)
class ReplayInputAvailability:
    """One input's raw timestamps beside its modelled availability."""

    family: str
    identity: tuple[tuple[str, str], ...]
    content_sha256: str
    observation_end: datetime
    raw_times: tuple[tuple[str, datetime], ...]
    source_published_at: datetime | None
    modelled_available_at: datetime
    labels: tuple[str, ...]

    @property
    def raw_ingested_at(self) -> datetime:
        return dict(self.raw_times)["ingested_at"]

    @property
    def raw_available_at(self) -> datetime | None:
        return dict(self.raw_times).get("available_at")

    def as_record(self) -> dict[str, Any]:
        return {
            "identity": dict(self.identity),
            "content_sha256": self.content_sha256,
            "observation_end": _iso(self.observation_end),
            "raw": {name: _iso(value) for name, value in self.raw_times},
            "source_published_at": _iso(self.source_published_at),
            "modelled_available_at": _iso(self.modelled_available_at),
            "labels": list(self.labels),
        }


@dataclass(frozen=True)
class SharedReplaySnapshot:
    """Every non-price replay input, shared unchanged by all three venue runs."""

    window: ReplayWindow
    volume_bars: tuple[OhlcvBar, ...]
    etf_flows: tuple[EtfFlow, ...]
    funding_rates: tuple[FundingRate, ...]
    open_interest: tuple[OpenInterest, ...]
    perp_volumes: tuple[PerpVolume, ...]
    availability: tuple[ReplayInputAvailability, ...]
    manifest_bytes: bytes
    manifest_sha256: str

    @property
    def manifest(self) -> dict[str, Any]:
        """A fresh decoded copy; the canonical bytes stay authoritative."""

        return json.loads(self.manifest_bytes)


@dataclass(frozen=True)
class VenueReplayDataset:
    """One venue's replay price stream bound to the shared non-price snapshot."""

    venue: ReplayVenue
    window: ReplayWindow
    price_bars: tuple[OhlcvBar, ...]
    price_availability: tuple[ReplayInputAvailability, ...]
    shared_snapshot: SharedReplaySnapshot
    manifest_bytes: bytes
    manifest_sha256: str

    @property
    def manifest(self) -> dict[str, Any]:
        """A fresh decoded copy; the canonical bytes stay authoritative."""

        return json.loads(self.manifest_bytes)

    def market_bars_at(
        self,
        decision_at: datetime,
        *,
        timeframes: Sequence[str] = CANONICAL_MARKET_BAR_TIMEFRAMES,
    ) -> tuple[OhlcvBar, ...]:
        return replay_market_bars_at(
            self.price_bars,
            decision_at=decision_at,
            window=self.window,
            timeframes=timeframes,
        )


# --- builders ----------------------------------------------------------------


def build_shared_replay_snapshot(
    *,
    window: ReplayWindow,
    volume_bars: Sequence[OhlcvBar] = (),
    etf_flows: Sequence[EtfFlow] = (),
    etf_source_publication_times: Sequence[EtfSourcePublicationTime] = (),
    funding_rates: Sequence[FundingRate] = (),
    open_interest: Sequence[OpenInterest] = (),
    perp_volumes: Sequence[PerpVolume] = (),
    etf_market_holidays: Iterable[date] | None = None,
) -> SharedReplaySnapshot:
    """Build the one non-price snapshot every venue run replays.

    ``etf_source_publication_times`` carries the source's own publication or
    revision times. A raw ``EtfFlow.available_at`` is never read as one, because
    a backfill stamps it with collection time. Several rows for one fund and
    date replay only when every row is dated and the flow owner's own choice is
    the latest publication at every instant. Each supplied time separately
    declares whether source-backed revision history is available; timestamps
    alone never clear the missing-history label.

    ``etf_market_holidays`` is used only to count ETF publication gaps with the
    owner's calendar; EPIC Y passes ``US_EQUITY_MARKET_CLOSURE_TABLE_V1``. When
    it is omitted the ETF gap count is recorded as not evaluated, never as zero.
    """

    replay_window = require_replay_window(window)
    holidays = _market_holidays(etf_market_holidays)

    volume_replay, volume_entries = _replay_bar_series(
        volume_bars,
        family=SHARED_VOLUME_FAMILY,
        venue=SHARED_VOLUME_VENUE,
        window=replay_window,
        mixed_reason="SHARED_VOLUME_SOURCE_REFUSED",
        allow_empty=True,
    )
    etf_replay, etf_entries = _replay_etf_flows(
        etf_flows,
        etf_source_publication_times,
        window=replay_window,
    )
    funding_replay, funding_entries = _replay_funding_rates(funding_rates, window=replay_window)
    oi_replay, oi_entries = _replay_open_interest(open_interest, window=replay_window)
    perp_replay, perp_entries = _replay_perp_volumes(perp_volumes, window=replay_window)

    families = {
        SHARED_VOLUME_FAMILY: _family_section(
            SHARED_VOLUME_FAMILY,
            volume_entries,
            (_bar_series_summary(volume_replay),) if volume_replay else (),
        ),
        ETF_FLOW_FAMILY: _family_section(
            ETF_FLOW_FAMILY,
            etf_entries,
            _etf_series_summaries(etf_replay, holidays),
        ),
        FUNDING_RATE_FAMILY: _family_section(
            FUNDING_RATE_FAMILY,
            funding_entries,
            _discontinuity_series_summaries(funding_replay),
        ),
        OPEN_INTEREST_FAMILY: _family_section(
            OPEN_INTEREST_FAMILY,
            oi_entries,
            _discontinuity_series_summaries(oi_replay),
        ),
        PERP_VOLUME_FAMILY: _family_section(
            PERP_VOLUME_FAMILY,
            perp_entries,
            _perp_volume_series_summaries(perp_replay),
        ),
    }
    availability = (*volume_entries, *etf_entries, *funding_entries, *oi_entries, *perp_entries)
    manifest = {
        **_evidence_header(SHARED_SNAPSHOT_MANIFEST_VERSION, replay_window),
        "shared_volume_venue": SHARED_VOLUME_VENUE.as_record(),
        "etf_market_holidays": (
            None if holidays is None else [day.isoformat() for day in sorted(holidays)]
        ),
        "families": families,
        "revision_history_unavailable_count": _revision_count(availability),
    }
    manifest_bytes = canonical_json_bytes(manifest)
    return SharedReplaySnapshot(
        window=replay_window,
        volume_bars=volume_replay,
        etf_flows=etf_replay,
        funding_rates=funding_replay,
        open_interest=oi_replay,
        perp_volumes=perp_replay,
        availability=availability,
        manifest_bytes=manifest_bytes,
        manifest_sha256=sha256_hex(manifest_bytes),
    )


def build_venue_replay_dataset(
    *,
    venue: ReplayVenue,
    window: ReplayWindow,
    price_bars: Sequence[OhlcvBar],
    shared_snapshot: SharedReplaySnapshot,
) -> VenueReplayDataset:
    """Build one venue's replay stream for the unchanged BTC-180 engine."""

    if not isinstance(venue, ReplayVenue) or venue not in REPLAY_VENUES:
        raise ReplayInputRefused(
            "UNKNOWN_REPLAY_VENUE",
            "the venue must be one of the three PRICE_SOURCE_POLICY_V1 required venues",
        )
    replay_window = require_replay_window(window)
    _require_type(shared_snapshot, SharedReplaySnapshot, "shared snapshot")
    if shared_snapshot.window != replay_window:
        raise ReplayInputRefused(
            "SHARED_SNAPSHOT_WINDOW_MISMATCH",
            "the shared snapshot was built for another window",
        )
    replay_bars, entries = _replay_bar_series(
        price_bars,
        family=REFERENCE_PRICE_FAMILY,
        venue=venue,
        window=replay_window,
        mixed_reason="MIXED_VENUE_SERIES_REFUSED",
        allow_empty=False,
    )
    shared = shared_snapshot.manifest
    manifest = {
        **_evidence_header(REPLAY_DATASET_MANIFEST_VERSION, replay_window),
        "venue": venue.as_record(),
        "derived_market_bars": {
            "timeframes": list(CANONICAL_MARKET_BAR_TIMEFRAMES),
            "derivation": DERIVED_MARKET_BAR_DERIVATION,
            "modelled_availability": DERIVED_MARKET_BAR_AVAILABILITY,
            "availability_field": "ingested_at",
        },
        "price_series": _family_section(
            REFERENCE_PRICE_FAMILY,
            entries,
            (_bar_series_summary(replay_bars),),
        ),
        "shared_snapshot": {
            "manifest_version": shared["manifest_version"],
            "manifest_sha256": shared_snapshot.manifest_sha256,
            "families": {
                family: {
                    key: section[key]
                    for key in (
                        "record_count",
                        "records_sha256",
                        "revision_history_unavailable_count",
                        "gap_count",
                        "missing_slot_count",
                        "gap_not_evaluated_reasons",
                    )
                }
                for family, section in shared["families"].items()
            },
            "revision_history_unavailable_count": shared["revision_history_unavailable_count"],
        },
        "revision_history_unavailable_count": (
            _revision_count(entries) + shared["revision_history_unavailable_count"]
        ),
    }
    manifest_bytes = canonical_json_bytes(manifest)
    return VenueReplayDataset(
        venue=venue,
        window=replay_window,
        price_bars=replay_bars,
        price_availability=entries,
        shared_snapshot=shared_snapshot,
        manifest_bytes=manifest_bytes,
        manifest_sha256=sha256_hex(manifest_bytes),
    )


# --- per-family replay copies ------------------------------------------------


def _replay_bar_series(
    bars: Sequence[OhlcvBar],
    *,
    family: str,
    venue: ReplayVenue,
    window: ReplayWindow,
    mixed_reason: str,
    allow_empty: bool,
) -> tuple[tuple[OhlcvBar, ...], tuple[ReplayInputAvailability, ...]]:
    source = tuple(bars)
    if not source and not allow_empty:
        raise ReplayInputRefused(
            "EMPTY_PRICE_SERIES_REFUSED",
            f"a {venue.venue_id} replay needs its 1h price series",
        )
    by_timestamp: dict[datetime, OhlcvBar] = {}
    for bar in source:
        _require_type(bar, OhlcvBar, "bar")
        timestamp = _utc(bar.timestamp, "bar.timestamp")
        _require_admitted(window, timestamp, timestamp, what=f"{family} bar")
        close = modelled_bar_available_at(bar)
        _require_admitted(window, timestamp, close - _ONE_MICROSECOND, what=f"{family} bar")
        _require_owner_record(bar, "OHLCV bar")
        _require_decimal_fields(bar, ("open", "high", "low", "close", "volume"), ())
        if not venue.owns(bar):
            raise ReplayInputRefused(
                mixed_reason,
                f"a {venue.venue_id} series cannot carry a "
                f"{bar.exchange}/{bar.symbol}/{bar.provider} bar; no splicing or fallback",
            )
        if timestamp in by_timestamp:
            raise ReplayInputRefused(
                "DUPLICATE_RECORD_REFUSED",
                f"{family} has two bars at {timestamp.isoformat()}",
            )
        by_timestamp[timestamp] = bar

    replayed: list[OhlcvBar] = []
    entries: list[ReplayInputAvailability] = []
    for timestamp in sorted(by_timestamp):
        bar = by_timestamp[timestamp]
        modelled = modelled_bar_available_at(bar)
        replayed.append(replace(bar, ingested_at=modelled))
        entries.append(
            _availability(
                family,
                identity=(("timestamp", timestamp.isoformat()),),
                record=bar.as_record(),
                observation_end=modelled,
                raw_times=(("ingested_at", bar.ingested_at),),
                source_published_at=None,
                modelled_available_at=modelled,
            )
        )
    try:
        validated = validate_backtest_bars(replayed, symbol=venue.symbol)
    except (TypeError, ValueError) as exc:
        raise ReplayInputRefused(
            "ENGINE_BAR_CONTRACT_REFUSED",
            f"{family} fails the BTC-180 bar contract: {exc}",
        ) from exc
    return validated, tuple(entries)


def _replay_etf_flows(
    flows: Sequence[EtfFlow],
    publication_times: Sequence[EtfSourcePublicationTime],
    *,
    window: ReplayWindow,
) -> tuple[tuple[EtfFlow, ...], tuple[ReplayInputAvailability, ...]]:
    by_key: dict[tuple[str, date, str, str], EtfFlow] = {}
    for flow in tuple(flows):
        _require_type(flow, EtfFlow, "ETF flow")
        trading_day_start = etf_trading_day_start(flow.observation_date)
        _require_admitted(window, trading_day_start, trading_day_start, what=f"{ETF_FLOW_FAMILY} {flow.fund}")
        trading_day_end = etf_trading_day_end(flow.observation_date)
        _require_admitted(
            window,
            trading_day_start,
            trading_day_end - _ONE_MICROSECOND,
            what=f"{ETF_FLOW_FAMILY} {flow.fund}",
        )
        _require_owner_record(flow, "ETF flow")
        _require_decimal_fields(flow, ("flow_usd",), ("aum_usd",))
        key = (flow.fund, flow.observation_date, flow.provider, flow.revision)
        if key in by_key:
            raise ReplayInputRefused(
                "DUPLICATE_RECORD_REFUSED",
                f"ETF revision {_etf_key_text(key)} appears twice; one revision has one "
                "first-available time",
            )
        by_key[key] = flow

    published: dict[tuple[str, date, str, str], datetime] = {}
    history_available: dict[tuple[str, date, str, str], bool] = {}
    for supplied in tuple(publication_times):
        _require_type(supplied, EtfSourcePublicationTime, "ETF source publication time")
        if type(supplied.revision_history_available) is not bool:
            raise ReplayInputRefused(
                "RECORD_TYPE_REFUSED",
                "ETF revision_history_available must be an explicit bool",
            )
        key = supplied.key()
        if key in published:
            raise ReplayInputRefused(
                "DUPLICATE_SOURCE_PUBLICATION_TIME",
                f"ETF revision {_etf_key_text(key)} has two supplied publication times",
            )
        if key not in by_key:
            raise ReplayInputRefused(
                "UNMATCHED_SOURCE_PUBLICATION_TIME",
                f"no ETF revision {_etf_key_text(key)} matches a supplied publication time",
            )
        published_at = _utc(supplied.published_at, "published_at")
        if published_at < etf_trading_day_start(supplied.observation_date):
            raise ReplayInputRefused(
                "SOURCE_PUBLICATION_BEFORE_OBSERVATION",
                f"ETF revision {_etf_key_text(key)} is dated {published_at.isoformat()}, "
                "before its own trading date began",
            )
        published[key] = published_at
        history_available[key] = supplied.revision_history_available

    modelled_by_key = {
        key: modelled_etf_flow_available_at(by_key[key], source_published_at=published.get(key))
        for key in by_key
    }
    rows_by_owner_key: dict[tuple[str, date], list[tuple[str, date, str, str]]] = {}
    for key in by_key:
        rows_by_owner_key.setdefault(key[:2], []).append(key)
    for owner_key, keys in sorted(rows_by_owner_key.items()):
        if len(keys) > 1:
            _require_replayable_revision_order(owner_key, keys, by_key, published, modelled_by_key)

    replayed: list[EtfFlow] = []
    entries: list[ReplayInputAvailability] = []
    for key in sorted(by_key):
        flow = by_key[key]
        supplied_at = published.get(key)
        modelled = modelled_by_key[key]
        replayed.append(replace(flow, available_at=modelled))
        entries.append(
            _availability(
                ETF_FLOW_FAMILY,
                identity=(
                    ("fund", flow.fund),
                    ("observation_date", flow.observation_date.isoformat()),
                    ("provider", flow.provider),
                    ("revision", flow.revision),
                ),
                record=flow.as_record(),
                observation_end=etf_trading_day_end(flow.observation_date),
                raw_times=(("available_at", flow.available_at), ("ingested_at", flow.ingested_at)),
                source_published_at=supplied_at,
                modelled_available_at=modelled,
                revision_history_available=history_available.get(key, False),
            )
        )
    return tuple(replayed), tuple(entries)


def _require_replayable_revision_order(
    owner_key: tuple[str, date],
    keys: Sequence[tuple[str, date, str, str]],
    flows: Mapping[tuple[str, date, str, str], EtfFlow],
    published: Mapping[tuple[str, date, str, str], datetime],
    modelled: Mapping[tuple[str, date, str, str], datetime],
) -> None:
    """Refuse rows for one fund and date that cannot replay in publication order.

    The flow owner keeps one row per fund and date, across revisions and
    providers: the greatest ``(available_at, revision, provider)``. Rows the
    ``T+2`` floor gives the same availability are therefore ordered by their
    labels, which carry no time. Several rows replay point in time only if the
    source dated every one of them, and the owner's own choice at each modelled
    instant is the latest-published row available then.
    """

    fund, observation_date = owner_key
    label = f"ETF {fund} {observation_date.isoformat()}"
    if any(key not in published for key in keys):
        raise ReplayInputRefused(
            "ETF_REVISION_ORDER_UNAVAILABLE",
            f"{label} has {len(keys)} rows across revisions or providers, but not every "
            "one carries a source publication time, so their point-in-time order is unknown",
        )
    if len({published[key] for key in keys}) != len(keys):
        raise ReplayInputRefused(
            "ETF_REVISION_ORDER_UNAVAILABLE",
            f"{label} has two rows published at the same instant, so neither is the later one",
        )
    copies = {key: replace(flows[key], available_at=modelled[key]) for key in keys}
    for instant in sorted({modelled[key] for key in keys}):
        visible = [key for key in keys if modelled[key] <= instant]
        latest = copies[max(visible, key=lambda key: published[key])]
        chosen = _latest_available_flows_by_fund_date(
            [copies[key] for key in keys],
            as_of=instant,
            funds=(),
            end_date=None,
        )[owner_key]
        if chosen is not latest:
            raise ReplayInputRefused(
                "ETF_REVISION_ORDER_UNAVAILABLE",
                f"{label}: at {instant.isoformat()} the flow owner would keep revision "
                f"{chosen.revision!r} from {chosen.provider}, not the latest published "
                f"{latest.revision!r} from {latest.provider}, because the T+2 floor gives "
                "them one availability and the owner breaks that tie by label",
            )


def _replay_funding_rates(
    rates: Sequence[FundingRate],
    *,
    window: ReplayWindow,
) -> tuple[tuple[FundingRate, ...], tuple[ReplayInputAvailability, ...]]:
    by_key: dict[tuple[Any, ...], FundingRate] = {}
    for rate in tuple(rates):
        _require_type(rate, FundingRate, "funding rate")
        settled_at = modelled_funding_rate_available_at(rate)
        what = f"{FUNDING_RATE_FAMILY} settled {settled_at.isoformat()}"
        _require_admitted(window, settled_at, settled_at, what=what)
        # The rate settled at S prices the period (S - interval, S], so that
        # whole period must lie inside the admitted windows.
        interval = funding_interval(rate)
        try:
            accrual_first = settled_at - interval + _ONE_MICROSECOND
        except OverflowError as exc:
            raise ReplayInputRefused(
                "PRE_2020_RECORD_REFUSED",
                f"{what} prices a period that begins before 2020-01-01 00:00 UTC",
            ) from exc
        _require_admitted(window, accrual_first, settled_at, what=what)
        _require_owner_record(rate, "funding rate")
        _require_decimal_fields(rate, ("funding_rate", "funding_interval_hours"), ())
        key = (settled_at, rate.exchange, rate.symbol, rate.instrument, rate.provider)
        _put_unique(by_key, key, rate, FUNDING_RATE_FAMILY)

    replayed: list[FundingRate] = []
    entries: list[ReplayInputAvailability] = []
    for key in sorted(by_key):
        rate = by_key[key]
        modelled = modelled_funding_rate_available_at(rate)
        replayed.append(replace(rate, available_at=modelled))
        entries.append(
            _availability(
                FUNDING_RATE_FAMILY,
                identity=_derivative_identity(rate, "instrument"),
                record=rate.as_record(),
                observation_end=modelled,
                raw_times=(("available_at", rate.available_at), ("ingested_at", rate.ingested_at)),
                source_published_at=None,
                modelled_available_at=modelled,
            )
        )
    return tuple(replayed), tuple(entries)


def _replay_open_interest(
    snapshots: Sequence[OpenInterest],
    *,
    window: ReplayWindow,
) -> tuple[tuple[OpenInterest, ...], tuple[ReplayInputAvailability, ...]]:
    by_key: dict[tuple[Any, ...], OpenInterest] = {}
    for snapshot in tuple(snapshots):
        _require_type(snapshot, OpenInterest, "open interest")
        observed_at = modelled_open_interest_available_at(snapshot)
        _require_admitted(
            window,
            observed_at,
            observed_at,
            what=f"{OPEN_INTEREST_FAMILY} {observed_at.isoformat()}",
        )
        _require_owner_record(snapshot, "open interest")
        _require_decimal_fields(snapshot, ("open_interest",), ())
        key = (observed_at, snapshot.exchange, snapshot.symbol, snapshot.instrument, snapshot.provider)
        _put_unique(by_key, key, snapshot, OPEN_INTEREST_FAMILY)

    replayed: list[OpenInterest] = []
    entries: list[ReplayInputAvailability] = []
    for key in sorted(by_key):
        snapshot = by_key[key]
        modelled = modelled_open_interest_available_at(snapshot)
        replayed.append(replace(snapshot, available_at=modelled))
        entries.append(
            _availability(
                OPEN_INTEREST_FAMILY,
                identity=_derivative_identity(snapshot, "instrument"),
                record=snapshot.as_record(),
                observation_end=modelled,
                raw_times=(
                    ("available_at", snapshot.available_at),
                    ("ingested_at", snapshot.ingested_at),
                ),
                source_published_at=None,
                modelled_available_at=modelled,
            )
        )
    return tuple(replayed), tuple(entries)


def _replay_perp_volumes(
    volumes: Sequence[PerpVolume],
    *,
    window: ReplayWindow,
) -> tuple[tuple[PerpVolume, ...], tuple[ReplayInputAvailability, ...]]:
    by_key: dict[tuple[Any, ...], PerpVolume] = {}
    for volume in tuple(volumes):
        _require_type(volume, PerpVolume, "perp volume")
        start = _utc(volume.observation_time, "perp_volume.observation_time")
        _require_admitted(window, start, start, what=f"{PERP_VOLUME_FAMILY} {volume.timeframe} {start.isoformat()}")
        end = perp_volume_interval_end(volume)
        _require_admitted(
            window,
            start,
            end - _ONE_MICROSECOND,
            what=f"{PERP_VOLUME_FAMILY} {volume.timeframe} {start.isoformat()}",
        )
        _require_owner_record(volume, "perp volume")
        _require_decimal_fields(volume, ("volume",), ("notional_usd",))
        key = (start, volume.exchange, volume.symbol, volume.timeframe, volume.provider)
        _put_unique(by_key, key, volume, PERP_VOLUME_FAMILY)

    replayed: list[PerpVolume] = []
    entries: list[ReplayInputAvailability] = []
    for key in sorted(by_key):
        volume = by_key[key]
        modelled = modelled_perp_volume_available_at(volume)
        replayed.append(replace(volume, available_at=modelled))
        entries.append(
            _availability(
                PERP_VOLUME_FAMILY,
                identity=_derivative_identity(volume, "timeframe"),
                record=volume.as_record(),
                observation_end=modelled,
                raw_times=(("available_at", volume.available_at), ("ingested_at", volume.ingested_at)),
                source_published_at=None,
                modelled_available_at=modelled,
            )
        )
    return tuple(replayed), tuple(entries)


def _availability(
    family: str,
    *,
    identity: tuple[tuple[str, str], ...],
    record: Mapping[str, Any],
    observation_end: datetime,
    raw_times: tuple[tuple[str, datetime], ...],
    source_published_at: datetime | None,
    modelled_available_at: datetime,
    revision_history_available: bool = False,
) -> ReplayInputAvailability:
    if modelled_available_at < observation_end:
        raise RuntimeError(
            f"{family} availability {modelled_available_at.isoformat()} precedes its "
            f"observation end {observation_end.isoformat()}"
        )
    # A timestamp can date a final-only value without supplying prior revisions.
    # Unknown coverage stays labelled, independently of modelled availability.
    labels = () if revision_history_available else (REVISION_HISTORY_UNAVAILABLE,)
    return ReplayInputAvailability(
        family=family,
        identity=identity,
        content_sha256=replay_record_content_sha256(family, record),
        observation_end=observation_end,
        raw_times=raw_times,
        source_published_at=source_published_at,
        modelled_available_at=modelled_available_at,
        labels=labels,
    )


def _derivative_identity(record: Any, series_field: str) -> tuple[tuple[str, str], ...]:
    return (
        ("observation_time", _iso(record.observation_time)),
        ("exchange", record.exchange),
        ("symbol", record.symbol),
        (series_field, getattr(record, series_field)),
        ("provider", record.provider),
    )


def _require_decimal_fields(
    record: Any,
    required: tuple[str, ...],
    optional: tuple[str, ...],
) -> None:
    """Owner numbers are finite Decimals; an optional one may be absent, never zero-filled."""

    for name in (*required, *optional):
        value = getattr(record, name)
        if value is None and name in optional:
            continue
        if not isinstance(value, Decimal) or not value.is_finite():
            raise ReplayInputRefused(
                "RECORD_TYPE_REFUSED",
                f"{type(record).__name__}.{name} must be a finite Decimal, not {value!r}",
            )


def _require_owner_record(record: Any, name: str) -> dict[str, Any]:
    """Hold a raw record to its owner's own ``as_record`` validation."""

    for field in ("available_at", "ingested_at"):
        if hasattr(record, field):
            _utc(getattr(record, field), f"{name}.{field}")
    try:
        return record.as_record()
    except (TypeError, ValueError) as exc:
        raise ReplayInputRefused(
            "OWNER_RECORD_REFUSED",
            f"the {name} owner refuses this raw record: {exc}",
        ) from exc


def _put_unique(store: dict[tuple[Any, ...], Any], key: tuple[Any, ...], record: Any, family: str) -> None:
    if key in store:
        raise ReplayInputRefused(
            "DUPLICATE_RECORD_REFUSED",
            f"{family} has two records for {key[0].isoformat()} "
            f"{'/'.join(str(part) for part in key[1:])}",
        )
    store[key] = record


def _etf_key_text(key: tuple[str, date, str, str]) -> str:
    fund, observation_date, provider, revision = key
    return f"{fund} {observation_date.isoformat()} {provider} {revision!r}"


# --- series summaries and gaps -----------------------------------------------


def _family_section(
    family: str,
    entries: Sequence[ReplayInputAvailability],
    series: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    records = [entry.as_record() for entry in entries]
    evaluated = [item["gaps"] for item in series if item["gaps"]["gap_count"] is not None]
    # An absent family has no gaps to count, which is not the same as zero gaps.
    reasons = (
        sorted(
            {
                item["gaps"]["not_evaluated_reason"]
                for item in series
                if item["gaps"]["gap_count"] is None
            }
        )
        if series
        else ["FAMILY_HAS_NO_RECORDS"]
    )
    return {
        "rule": REPLAY_AVAILABILITY_RULES[family].as_record(),
        "record_count": len(records),
        "records_sha256": sha256_hex(canonical_json_bytes(records)),
        "revision_history_unavailable_count": _revision_count(entries),
        "series": list(series),
        "gap_count": None if reasons else sum(gaps["gap_count"] for gaps in evaluated),
        "missing_slot_count": (
            None
            if reasons or any(gaps["missing_slot_count"] is None for gaps in evaluated)
            else sum(gaps["missing_slot_count"] for gaps in evaluated)
        ),
        "gap_not_evaluated_reasons": reasons,
        "records": records,
    }


def _bar_series_summary(bars: Sequence[OhlcvBar]) -> dict[str, Any]:
    first = bars[0]
    return {
        "identity": {
            "exchange": first.exchange,
            "symbol": first.symbol,
            "provider": first.provider,
            "timeframe": first.timeframe,
        },
        "record_count": len(bars),
        "first_observation": _iso(bars[0].timestamp),
        "last_observation": _iso(bars[-1].timestamp),
        "gaps": _grid_gaps(
            [bar.timestamp for bar in bars],
            first.timeframe,
            method="OWNER_BAR_GRID",
        ),
    }


def _perp_volume_series_summaries(volumes: Sequence[PerpVolume]) -> tuple[dict[str, Any], ...]:
    grouped: dict[tuple[str, str, str, str], list[PerpVolume]] = {}
    for volume in volumes:
        grouped.setdefault(
            (volume.exchange, volume.symbol, volume.timeframe, volume.provider), []
        ).append(volume)
    summaries = []
    for (exchange, symbol, timeframe, provider), series in sorted(grouped.items()):
        times = [volume.observation_time for volume in series]
        summaries.append(
            {
                "identity": {
                    "exchange": exchange,
                    "symbol": symbol,
                    "timeframe": timeframe,
                    "provider": provider,
                },
                "record_count": len(series),
                "first_observation": _iso(min(times)),
                "last_observation": _iso(max(times)),
                "gaps": _grid_gaps(times, timeframe, method="OWNER_BAR_GRID"),
            }
        )
    return tuple(summaries)


def _grid_gaps(times: Sequence[datetime], timeframe: str, *, method: str) -> dict[str, Any]:
    observed = sorted(set(times))
    try:
        missing = missing_bar_timestamps(
            observed,
            start=observed[0],
            end=observed[-1],
            timeframe=timeframe,
        )
        grid = set(expected_bar_timestamps(start=observed[0], end=observed[-1], timeframe=timeframe))
    except (ValueError, OverflowError):
        # A monthly series anchored after the 28th has no owner grid across a
        # short month; its gaps are not evaluated rather than guessed.
        return _not_evaluated(method, "OWNER_GRID_UNDEFINED")
    spans = _consecutive_runs(
        missing,
        lambda previous, current: next_bar_timestamp(previous, timeframe) == current,
    )
    return {
        "method": method,
        "gap_count": len(spans),
        "missing_slot_count": len(missing),
        "off_grid_observation_count": sum(1 for moment in observed if moment not in grid),
        "not_evaluated_reason": None,
        "spans": [
            {
                "first_missing": _iso(span[0]),
                "last_missing": _iso(span[-1]),
                "missing_slots": len(span),
            }
            for span in spans
        ],
    }


def _etf_series_summaries(
    flows: Sequence[EtfFlow],
    holidays: frozenset[date] | None,
) -> tuple[dict[str, Any], ...]:
    grouped: dict[tuple[str, str], list[EtfFlow]] = {}
    for flow in flows:
        grouped.setdefault((flow.fund, flow.provider), []).append(flow)
    summaries = []
    for (fund, provider), series in sorted(grouped.items()):
        dates = sorted({flow.observation_date for flow in series})
        summaries.append(
            {
                "identity": {"fund": fund, "provider": provider},
                "record_count": len(series),
                "first_observation": dates[0].isoformat(),
                "last_observation": dates[-1].isoformat(),
                "gaps": _etf_publication_gaps(series, fund, dates, holidays),
            }
        )
    return tuple(summaries)


def _etf_publication_gaps(
    series: Sequence[EtfFlow],
    fund: str,
    dates: Sequence[date],
    holidays: frozenset[date] | None,
) -> dict[str, Any]:
    if holidays is None:
        return _not_evaluated(
            "OWNER_PUBLICATION_CALENDAR",
            "ETF_MARKET_HOLIDAYS_NOT_SUPPLIED",
        )
    missing = missing_etf_publication_dates(
        series,
        funds=(fund,),
        start=dates[0],
        end=dates[-1],
        market_holidays=holidays,
    )[fund]
    calendar = expected_etf_publication_dates(
        start=dates[0],
        end=dates[-1],
        market_holidays=holidays,
    )
    position = {day: index for index, day in enumerate(calendar)}
    spans = _consecutive_runs(
        missing,
        lambda previous, current: position[current] == position[previous] + 1,
    )
    return {
        "method": "OWNER_PUBLICATION_CALENDAR",
        "gap_count": len(spans),
        "missing_slot_count": len(missing),
        "off_grid_observation_count": len([day for day in dates if day not in position]),
        "not_evaluated_reason": None,
        "spans": [
            {
                "first_missing": span[0].isoformat(),
                "last_missing": span[-1].isoformat(),
                "missing_slots": len(span),
            }
            for span in spans
        ],
    }


def _discontinuity_series_summaries(
    records: Sequence[FundingRate | OpenInterest],
) -> tuple[dict[str, Any], ...]:
    grouped: dict[tuple[str, str, str, str], list[FundingRate | OpenInterest]] = {}
    for record in records:
        grouped.setdefault(
            (record.exchange, record.symbol, record.instrument, record.provider), []
        ).append(record)
    summaries = []
    for (exchange, symbol, instrument, provider), series in sorted(grouped.items()):
        ordered = sorted(series, key=lambda record: record.observation_time)
        summaries.append(
            {
                "identity": {
                    "exchange": exchange,
                    "symbol": symbol,
                    "instrument": instrument,
                    "provider": provider,
                },
                "record_count": len(ordered),
                "first_observation": _iso(ordered[0].observation_time),
                "last_observation": _iso(ordered[-1].observation_time),
                "gaps": _provider_discontinuities(ordered),
            }
        )
    return tuple(summaries)


def _provider_discontinuities(series: Sequence[FundingRate | OpenInterest]) -> dict[str, Any]:
    """Gaps exactly as the BTC-031 ``data.quality`` owner defines them.

    A funding series may arrive up to its declared interval plus the owner's
    buffer after the previous settlement; open interest up to the owner's
    provider-gap threshold. Longer jumps are ``PROVIDER_DISCONTINUITY``.
    """

    try:
        report = validate_derivatives_quality(
            series,
            as_of=series[-1].observation_time,
            config=_DERIVATIVES_QUALITY_CONFIG,
        )
    except (TypeError, ValueError) as exc:
        raise ReplayInputRefused(
            "OWNER_RECORD_REFUSED",
            f"the data.quality owner refuses this derivatives series: {exc}",
        ) from exc
    spans = [
        {
            "previous_observation": issue.details["previous_observation_time"],
            "next_observation": _iso(issue.timestamp),
            "gap_seconds": issue.details["gap_seconds"],
            "max_gap_seconds": issue.details["max_gap_seconds"],
        }
        for issue in report.issues
        if issue.reason_code == "PROVIDER_DISCONTINUITY"
    ]
    return {
        "method": "DATA_QUALITY_PROVIDER_DISCONTINUITY",
        "gap_count": len(spans),
        "missing_slot_count": None,
        "off_grid_observation_count": None,
        "not_evaluated_reason": None,
        "spans": spans,
    }


def _not_evaluated(method: str, reason: str) -> dict[str, Any]:
    return {
        "method": method,
        "gap_count": None,
        "missing_slot_count": None,
        "off_grid_observation_count": None,
        "not_evaluated_reason": reason,
        "spans": None,
    }


def _consecutive_runs(values: Sequence[Any], adjacent: Any) -> list[list[Any]]:
    runs: list[list[Any]] = []
    for value in values:
        if runs and adjacent(runs[-1][-1], value):
            runs[-1].append(value)
        else:
            runs.append([value])
    return runs


def _market_holidays(values: Iterable[date] | None) -> frozenset[date] | None:
    if values is None:
        return None
    try:
        holidays = frozenset(values)
    except TypeError as exc:
        raise ReplayInputRefused(
            "RECORD_TYPE_REFUSED",
            "etf_market_holidays must be an iterable of datetime.date values",
        ) from exc
    for day in holidays:
        if type(day) is not date:
            raise ReplayInputRefused(
                "RECORD_TYPE_REFUSED",
                "etf_market_holidays must contain datetime.date values",
            )
    return holidays


def _revision_count(entries: Iterable[ReplayInputAvailability]) -> int:
    return sum(1 for entry in entries if REVISION_HISTORY_UNAVAILABLE in entry.labels)


def _evidence_header(manifest_version: str, window: ReplayWindow) -> dict[str, Any]:
    # The holdout guard is deliberately absent: a DATA dataset's identity must
    # not change when RBT-008 flips the guard, and a HOLDOUT window id already
    # proves the guard was open.
    return {
        "manifest_version": manifest_version,
        "builder_version": REPLAY_INPUTS_BUILDER_VERSION,
        "policy": RESEARCH_BACKTEST_POLICY_VERSION,
        "availability_policy": REPLAY_AVAILABILITY_POLICY_VERSION,
        "evidence_class": RESEARCH_EVIDENCE_CLASS,
        "canonical_reference": CANONICAL_REFERENCE_UNRESOLVED,
        "window": window.as_record(),
    }


# --- canonical encoding --------------------------------------------------------


def canonical_json_bytes(value: Any) -> bytes:
    """Sorted-key, whitespace-free ASCII JSON: the manifest's hashed form."""

    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def replay_record_content_sha256(family: str, record: Mapping[str, Any]) -> str:
    """The content digest of one raw owner record, as its owner renders it.

    Numbers enter by value (:func:`canonical_decimal`), so collector output and
    the same rows read back from ``NUMERIC`` columns address identically.
    """

    return sha256_hex(canonical_json_bytes({"family": family, "record": _jsonable(record)}))


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime):
        return _iso(value)
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return canonical_decimal(value)
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    raise ReplayInputRefused(
        "RECORD_TYPE_REFUSED",
        f"record field of type {type(value).__name__} has no canonical form; "
        "owner records carry Decimal numbers",
    )


def canonical_decimal(value: Decimal) -> str:
    """A Decimal by value, not by scale: ``60000``, ``60000.0`` and a
    ``NUMERIC(38,18)`` read-back all render ``60000``.

    Positional, no exponent, no trailing zeros, and ``-0`` is ``0``. It uses the
    exact digits, never ``Decimal.normalize``, which rounds to the context
    precision and would merge distinct 38-digit values.
    """

    if not isinstance(value, Decimal) or not value.is_finite():
        raise ReplayInputRefused("RECORD_TYPE_REFUSED", "record numbers must be finite Decimals")
    sign, digits, exponent = value.as_tuple()
    coefficient = int("".join(str(digit) for digit in digits) or "0")
    if coefficient == 0:
        return "0"
    while coefficient % 10 == 0:
        coefficient //= 10
        exponent += 1
    text = str(coefficient)
    if exponent >= 0:
        text += "0" * exponent
    elif len(text) > -exponent:
        text = f"{text[:exponent]}.{text[exponent:]}"
    else:
        text = "0." + "0" * (-exponent - len(text)) + text
    return f"-{text}" if sign else text


def _iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    return _utc(value, "timestamp").isoformat()


def _utc(value: Any, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise ReplayInputRefused(
            "NON_UTC_TIMESTAMP_REFUSED",
            f"{name} must be a timezone-aware UTC datetime",
        )
    try:
        return require_utc_datetime(value, name)
    except ValueError as exc:
        raise ReplayInputRefused("NON_UTC_TIMESTAMP_REFUSED", str(exc)) from exc


def _require_type(value: Any, expected: type, name: str) -> None:
    if type(value) is not expected:
        raise ReplayInputRefused(
            "RECORD_TYPE_REFUSED",
            f"{name} must be a {expected.__name__}, not {type(value).__name__}",
        )
