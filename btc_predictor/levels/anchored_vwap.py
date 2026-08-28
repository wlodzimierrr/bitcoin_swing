"""Anchored VWAP support for confirmed price levels and market events."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from btc_predictor.data import OhlcvBar, next_bar_timestamp, require_utc_datetime
from btc_predictor.levels.breakout import (
    BREAKOUT_LEVEL_TYPE,
    BREAKOUT_RECLAIM_LEVEL_FEATURE_ID,
    BreakoutReclaimLevel,
)
from btc_predictor.levels.swing import (
    MONTHLY_SWING_HIGH,
    MONTHLY_SWING_LEVEL_FEATURE_ID,
    MONTHLY_SWING_LOW,
    WEEKLY_SWING_HIGH,
    WEEKLY_SWING_LEVEL_FEATURE_ID,
    WEEKLY_SWING_LOW,
    MonthlySwingLevel,
    WeeklySwingLevel,
)


ANCHORED_VWAP_FEATURE_ID = "ANCHORED_VWAP"
ANCHOR_MAJOR_SWING_LOW = "major_swing_low"
ANCHOR_MAJOR_SWING_HIGH = "major_swing_high"
ANCHOR_BREAKOUT = "breakout"
ANCHOR_CAPITULATION_EVENT = "capitulation_event"
ANCHORED_VWAP_ANCHOR_TYPES = (
    ANCHOR_MAJOR_SWING_LOW,
    ANCHOR_MAJOR_SWING_HIGH,
    ANCHOR_BREAKOUT,
    ANCHOR_CAPITULATION_EVENT,
)
ANCHORED_VWAP_REASON_CODES = (
    "ANCHORED_VWAP_ANCHOR_NOT_DETECTED",
    "ANCHORED_VWAP_INSUFFICIENT_BARS",
    "ANCHORED_VWAP_ZERO_VOLUME",
    "ANCHORED_VWAP_COMPLETE",
)
ANCHORED_VWAP_PRICE_SOURCE_HLC3 = "hlc3"
ANCHORED_VWAP_PRICE_SOURCE_CLOSE = "close"
ANCHORED_VWAP_PRICE_SOURCES = (
    ANCHORED_VWAP_PRICE_SOURCE_HLC3,
    ANCHORED_VWAP_PRICE_SOURCE_CLOSE,
)
DEFAULT_ANCHORED_VWAP_PRICE_SOURCE = ANCHORED_VWAP_PRICE_SOURCE_HLC3


@dataclass(frozen=True)
class CapitulationEvent:
    event_timestamp: datetime
    detected_at: datetime
    price: Decimal
    exchange: str
    symbol: str
    provider: str
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        event_timestamp = require_utc_datetime(
            self.event_timestamp,
            "event_timestamp",
        )
        detected_at = require_utc_datetime(self.detected_at, "detected_at")
        if detected_at < event_timestamp:
            raise ValueError("detected_at must be >= event_timestamp")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        return {
            "event_timestamp": event_timestamp.isoformat(),
            "detected_at": detected_at.isoformat(),
            "price": str(self.price),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "provider": self.provider,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class AnchoredVwapAnchor:
    anchor_type: str
    anchor_timestamp: datetime
    detected_at: datetime
    price: Decimal
    exchange: str
    symbol: str
    provider: str
    source_feature_id: str
    source_type: str
    source_timestamp: datetime
    source_detected_at: datetime
    source_timeframe: str | None = None
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        anchor_timestamp = require_utc_datetime(
            self.anchor_timestamp,
            "anchor_timestamp",
        )
        detected_at = require_utc_datetime(self.detected_at, "detected_at")
        source_timestamp = require_utc_datetime(
            self.source_timestamp,
            "source_timestamp",
        )
        source_detected_at = require_utc_datetime(
            self.source_detected_at,
            "source_detected_at",
        )
        if self.anchor_type not in ANCHORED_VWAP_ANCHOR_TYPES:
            raise ValueError(f"anchor_type must be one of {ANCHORED_VWAP_ANCHOR_TYPES}")
        if detected_at < anchor_timestamp:
            raise ValueError("detected_at must be >= anchor_timestamp")
        if source_detected_at > detected_at:
            raise ValueError("source_detected_at must be <= detected_at")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        if not self.source_feature_id.strip():
            raise ValueError("source_feature_id must be non-empty")
        if not self.source_type.strip():
            raise ValueError("source_type must be non-empty")
        return {
            "anchor_type": self.anchor_type,
            "anchor_timestamp": anchor_timestamp.isoformat(),
            "detected_at": detected_at.isoformat(),
            "price": str(self.price),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "provider": self.provider,
            "source_feature_id": self.source_feature_id,
            "source_type": self.source_type,
            "source_timestamp": source_timestamp.isoformat(),
            "source_detected_at": source_detected_at.isoformat(),
            "source_timeframe": self.source_timeframe,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class AnchoredVwapResult:
    feature_id: str
    anchor: AnchoredVwapAnchor
    as_of: datetime
    price_source: str
    source_timeframe: str | None
    vwap: Decimal | None
    bar_count: int
    volume_sum: Decimal
    price_volume_sum: Decimal
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        as_of = require_utc_datetime(self.as_of, "as_of")
        if self.feature_id != ANCHORED_VWAP_FEATURE_ID:
            raise ValueError("feature_id must be ANCHORED_VWAP")
        _validate_price_source(self.price_source)
        anchor_record = self.anchor.as_record()
        if self.bar_count < 0:
            raise ValueError("bar_count must be >= 0")
        if self.volume_sum < 0:
            raise ValueError("volume_sum must be >= 0")
        if self.price_volume_sum < 0:
            raise ValueError("price_volume_sum must be >= 0")
        if self.complete and self.vwap is None:
            raise ValueError("complete VWAP result requires vwap")
        if self.vwap is not None and self.vwap <= 0:
            raise ValueError("vwap must be > 0")
        return {
            "feature_id": self.feature_id,
            "anchor": anchor_record,
            "anchor_type": self.anchor.anchor_type,
            "anchor_timestamp": anchor_record["anchor_timestamp"],
            "anchor_detected_at": anchor_record["detected_at"],
            "anchor_price": anchor_record["price"],
            "source_feature_id": anchor_record["source_feature_id"],
            "source_type": anchor_record["source_type"],
            "source_timestamp": anchor_record["source_timestamp"],
            "source_detected_at": anchor_record["source_detected_at"],
            "source_timeframe": self.source_timeframe,
            "exchange": self.anchor.exchange,
            "symbol": self.anchor.symbol,
            "provider": self.anchor.provider,
            "as_of": as_of.isoformat(),
            "price_source": self.price_source,
            "vwap": str(self.vwap) if self.vwap is not None else None,
            "bar_count": self.bar_count,
            "volume_sum": str(self.volume_sum),
            "price_volume_sum": str(self.price_volume_sum),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def anchored_vwap_anchor_from_swing_level(
    level: WeeklySwingLevel | MonthlySwingLevel,
) -> AnchoredVwapAnchor:
    """Create a VWAP anchor from a confirmed weekly/monthly swing level."""

    record = level.as_record()
    if record["feature_id"] not in (
        WEEKLY_SWING_LEVEL_FEATURE_ID,
        MONTHLY_SWING_LEVEL_FEATURE_ID,
    ):
        raise ValueError("swing anchor requires a weekly or monthly swing level")
    if record["level_type"] in (WEEKLY_SWING_LOW, MONTHLY_SWING_LOW):
        anchor_type = ANCHOR_MAJOR_SWING_LOW
    elif record["level_type"] in (WEEKLY_SWING_HIGH, MONTHLY_SWING_HIGH):
        anchor_type = ANCHOR_MAJOR_SWING_HIGH
    else:
        raise ValueError("swing anchor requires a swing high or swing low")
    return AnchoredVwapAnchor(
        anchor_type=anchor_type,
        anchor_timestamp=level.level_timestamp,
        detected_at=level.detected_at,
        price=level.price,
        exchange=level.exchange,
        symbol=level.symbol,
        provider=level.provider,
        source_feature_id=level.feature_id,
        source_type=level.level_type,
        source_timestamp=level.level_timestamp,
        source_detected_at=level.detected_at,
        source_timeframe=level.timeframe,
    )


def anchored_vwap_anchor_from_breakout_level(
    level: BreakoutReclaimLevel,
) -> AnchoredVwapAnchor:
    """Create a VWAP anchor from a confirmed breakout level."""

    record = level.as_record()
    if record["feature_id"] != BREAKOUT_RECLAIM_LEVEL_FEATURE_ID:
        raise ValueError("breakout anchor requires a breakout/reclaim level")
    if record["level_type"] != BREAKOUT_LEVEL_TYPE:
        raise ValueError("anchored VWAP breakout anchors require a breakout level")
    return AnchoredVwapAnchor(
        anchor_type=ANCHOR_BREAKOUT,
        anchor_timestamp=level.confirmation_timestamp,
        detected_at=level.detected_at,
        price=level.price,
        exchange=level.exchange,
        symbol=level.symbol,
        provider=level.provider,
        source_feature_id=level.feature_id,
        source_type=level.level_type,
        source_timestamp=level.confirmation_timestamp,
        source_detected_at=level.detected_at,
        source_timeframe=level.confirmation_timeframe,
        reason_codes=level.reason_codes,
    )


def anchored_vwap_anchor_from_capitulation_event(
    event: CapitulationEvent,
) -> AnchoredVwapAnchor:
    """Create a VWAP anchor from a detected capitulation event."""

    event.as_record()
    return AnchoredVwapAnchor(
        anchor_type=ANCHOR_CAPITULATION_EVENT,
        anchor_timestamp=event.event_timestamp,
        detected_at=event.detected_at,
        price=event.price,
        exchange=event.exchange,
        symbol=event.symbol,
        provider=event.provider,
        source_feature_id="CAPITULATION_EVENT",
        source_type=ANCHOR_CAPITULATION_EVENT,
        source_timestamp=event.event_timestamp,
        source_detected_at=event.detected_at,
        reason_codes=event.reason_codes,
    )


def calculate_anchored_vwap(
    anchor: AnchoredVwapAnchor,
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    price_source: str = DEFAULT_ANCHORED_VWAP_PRICE_SOURCE,
) -> AnchoredVwapResult:
    """Calculate anchored VWAP from bars known at signal time."""

    signal_time = require_utc_datetime(as_of, "as_of")
    price_source = _validate_price_source(price_source)
    anchor.as_record()
    if signal_time < anchor.detected_at:
        return _incomplete_result(
            anchor,
            as_of=signal_time,
            price_source=price_source,
            reason_codes=("ANCHORED_VWAP_ANCHOR_NOT_DETECTED",),
        )

    matched_bars = _available_anchor_bars(anchor, bars, signal_time=signal_time)
    if not matched_bars:
        return _incomplete_result(
            anchor,
            as_of=signal_time,
            price_source=price_source,
            reason_codes=("ANCHORED_VWAP_INSUFFICIENT_BARS",),
        )

    source_timeframe = _single_timeframe(matched_bars)
    volume_sum = sum((bar.volume for bar in matched_bars), Decimal("0"))
    if volume_sum == 0:
        return _incomplete_result(
            anchor,
            as_of=signal_time,
            price_source=price_source,
            source_timeframe=source_timeframe,
            bar_count=len(matched_bars),
            reason_codes=("ANCHORED_VWAP_ZERO_VOLUME",),
        )

    price_volume_sum = sum(
        (_bar_price(bar, price_source) * bar.volume for bar in matched_bars),
        Decimal("0"),
    )
    return AnchoredVwapResult(
        feature_id=ANCHORED_VWAP_FEATURE_ID,
        anchor=anchor,
        as_of=signal_time,
        price_source=price_source,
        source_timeframe=source_timeframe,
        vwap=price_volume_sum / volume_sum,
        bar_count=len(matched_bars),
        volume_sum=volume_sum,
        price_volume_sum=price_volume_sum,
        complete=True,
        reason_codes=("ANCHORED_VWAP_COMPLETE",),
    )


def calculate_anchored_vwaps(
    anchors: Sequence[AnchoredVwapAnchor],
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    price_source: str = DEFAULT_ANCHORED_VWAP_PRICE_SOURCE,
) -> tuple[AnchoredVwapResult, ...]:
    """Calculate deterministic anchored VWAP records for many anchors."""

    results = (
        calculate_anchored_vwap(
            anchor,
            bars,
            as_of=as_of,
            price_source=price_source,
        )
        for anchor in anchors
    )
    return tuple(
        sorted(
            results,
            key=lambda result: (
                result.anchor.detected_at,
                result.anchor.anchor_timestamp,
                result.anchor.anchor_type,
                result.anchor.price,
            ),
        )
    )


def _available_anchor_bars(
    anchor: AnchoredVwapAnchor,
    bars: Sequence[OhlcvBar],
    *,
    signal_time: datetime,
) -> tuple[OhlcvBar, ...]:
    available = []
    for bar in bars:
        _validate_ohlcv_bar(bar)
        if _bar_identity(bar) != _anchor_identity(anchor):
            continue
        if bar.timestamp < anchor.anchor_timestamp:
            continue
        if next_bar_timestamp(bar.timestamp, bar.timeframe) > signal_time:
            continue
        if require_utc_datetime(bar.ingested_at, "ingested_at") > signal_time:
            continue
        available.append(bar)
    return tuple(sorted(available, key=lambda bar: bar.timestamp))


def _validate_ohlcv_bar(bar: OhlcvBar) -> None:
    record = bar.as_record()
    if record["open"] <= 0:
        raise ValueError("bar open must be > 0")
    if record["high"] <= 0:
        raise ValueError("bar high must be > 0")
    if record["low"] <= 0:
        raise ValueError("bar low must be > 0")
    if record["close"] <= 0:
        raise ValueError("bar close must be > 0")
    if record["volume"] < 0:
        raise ValueError("bar volume must be >= 0")
    next_bar_timestamp(record["timestamp"], record["timeframe"])


def _bar_price(bar: OhlcvBar, price_source: str) -> Decimal:
    if price_source == ANCHORED_VWAP_PRICE_SOURCE_HLC3:
        return (bar.high + bar.low + bar.close) / Decimal("3")
    if price_source == ANCHORED_VWAP_PRICE_SOURCE_CLOSE:
        return bar.close
    raise ValueError(f"price_source must be one of {ANCHORED_VWAP_PRICE_SOURCES}")


def _incomplete_result(
    anchor: AnchoredVwapAnchor,
    *,
    as_of: datetime,
    price_source: str,
    reason_codes: tuple[str, ...],
    source_timeframe: str | None = None,
    bar_count: int = 0,
) -> AnchoredVwapResult:
    return AnchoredVwapResult(
        feature_id=ANCHORED_VWAP_FEATURE_ID,
        anchor=anchor,
        as_of=as_of,
        price_source=price_source,
        source_timeframe=source_timeframe,
        vwap=None,
        bar_count=bar_count,
        volume_sum=Decimal("0"),
        price_volume_sum=Decimal("0"),
        complete=False,
        reason_codes=reason_codes,
    )


def _single_timeframe(bars: Sequence[OhlcvBar]) -> str:
    timeframes = {bar.timeframe for bar in bars}
    if len(timeframes) != 1:
        raise ValueError("anchored VWAP requires bars from a single timeframe")
    return next(iter(timeframes))


def _anchor_identity(anchor: AnchoredVwapAnchor) -> tuple[str, str, str]:
    return (anchor.exchange, anchor.symbol, anchor.provider)


def _bar_identity(bar: OhlcvBar) -> tuple[str, str, str]:
    return (bar.exchange, bar.symbol, bar.provider)


def _validate_price_source(price_source: str) -> str:
    if price_source not in ANCHORED_VWAP_PRICE_SOURCES:
        raise ValueError(f"price_source must be one of {ANCHORED_VWAP_PRICE_SOURCES}")
    return price_source
