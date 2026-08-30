"""Point-in-time higher-low entry confirmation anchored to BTC-090."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Literal

from btc_predictor.data import OhlcvBar, next_bar_timestamp, require_utc_datetime
from btc_predictor.levels import (
    WEEKLY_SWING_LEVEL_FEATURE_ID,
    WEEKLY_SWING_LOW,
    WeeklySwingLevel,
)
from btc_predictor.quant.comparisons import (
    decision_equal,
    decision_greater,
    decision_less,
)


HIGHER_LOW_TRIGGER_FEATURE_ID = "ENTRY_TRIGGER_HIGHER_LOW"
HIGHER_LOW_TRIGGER_TYPE = "HIGHER_LOW"
HIGHER_LOW_TRIGGER_REASON_CODES = (
    "HIGHER_LOW_SOURCE_BAR_MISSING",
    "HIGHER_LOW_PIVOT_PENDING",
    "HIGHER_LOW_PIVOT_NOT_FOUND",
    "HIGHER_LOW_PULLBACK_PENDING",
    "HIGHER_LOW_PULLBACK_NOT_FOUND",
    "HIGHER_LOW_NOT_ABOVE_SOURCE",
    "HIGHER_LOW_BREAK_PENDING",
    "HIGHER_LOW_INVALIDATED",
    "HIGHER_LOW_BREAK_NOT_CONFIRMED",
    "HIGHER_LOW_CONFIRMED",
)
DEFAULT_HIGHER_LOW_PIVOT_LEFT_BARS = 2
DEFAULT_HIGHER_LOW_PIVOT_RIGHT_BARS = 2
DEFAULT_HIGHER_LOW_LEFT_BARS = 2
DEFAULT_HIGHER_LOW_RIGHT_BARS = 2
DEFAULT_HIGHER_LOW_MAX_PATTERN_BARS = 30
DEFAULT_HIGHER_LOW_MAX_BREAKOUT_BARS = 10
DEFAULT_HIGHER_LOW_BUFFER_FRACTION = Decimal("0")
DEFAULT_HIGHER_LOW_PIVOT_BREAK_BUFFER_FRACTION = Decimal("0")


@dataclass(frozen=True)
class HigherLowTriggerResult:
    feature_id: str
    trigger_type: str
    evaluated_at: datetime
    triggered: bool
    complete: bool
    source_swing_low: WeeklySwingLevel
    pivot_left_bars: int
    pivot_right_bars: int
    higher_low_left_bars: int
    higher_low_right_bars: int
    max_pattern_bars: int
    max_breakout_bars: int
    higher_low_buffer_fraction: Decimal
    pivot_break_buffer_fraction: Decimal
    source_low_bar_timestamp: datetime | None
    source_low_bar_detected_at: datetime | None
    source_low_price: Decimal
    higher_low_threshold: Decimal
    pivot_timestamp: datetime | None
    pivot_detected_at: datetime | None
    pivot_high: Decimal | None
    pivot_break_threshold: Decimal | None
    higher_low_timestamp: datetime | None
    higher_low_detected_at: datetime | None
    higher_low_price: Decimal | None
    evaluated_bar_timestamps: tuple[datetime, ...]
    evaluated_highs: tuple[Decimal, ...]
    evaluated_lows: tuple[Decimal, ...]
    evaluated_closes: tuple[Decimal, ...]
    confirmation_timestamp: datetime | None
    confirmation_close: Decimal | None
    detected_at: datetime | None
    source_bar_count: int
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        return self.reason_codes[0] if self.reason_codes else None

    def as_record(self) -> dict[str, Any]:
        evaluated_at = require_utc_datetime(self.evaluated_at, "evaluated_at")
        _validate_source_level(self.source_swing_low)
        source_record = self.source_swing_low.as_record()
        _validate_result(self)
        timestamps = tuple(
            require_utc_datetime(value, "evaluated_bar_timestamp")
            for value in self.evaluated_bar_timestamps
        )
        if not (
            len(timestamps)
            == len(self.evaluated_highs)
            == len(self.evaluated_lows)
            == len(self.evaluated_closes)
        ):
            raise ValueError("evaluated bar provenance must have matching lengths")
        if timestamps != tuple(sorted(timestamps)) or len(set(timestamps)) != len(
            timestamps
        ):
            raise ValueError("evaluated bar timestamps must be unique and ordered")
        prices = (*self.evaluated_highs, *self.evaluated_lows, *self.evaluated_closes)
        if any(value <= 0 for value in prices):
            raise ValueError("evaluated bar prices must be > 0")
        _validate_nonnegative_int(self.source_bar_count, "source_bar_count")
        if self.source_bar_count < len(timestamps):
            raise ValueError("source_bar_count must include evaluated bars")

        source_timestamp = _optional_utc(
            self.source_low_bar_timestamp,
            "source_low_bar_timestamp",
        )
        source_detected_at = _optional_utc(
            self.source_low_bar_detected_at,
            "source_low_bar_detected_at",
        )
        pivot_timestamp = _optional_utc(self.pivot_timestamp, "pivot_timestamp")
        pivot_detected_at = _optional_utc(
            self.pivot_detected_at,
            "pivot_detected_at",
        )
        higher_low_timestamp = _optional_utc(
            self.higher_low_timestamp,
            "higher_low_timestamp",
        )
        higher_low_detected_at = _optional_utc(
            self.higher_low_detected_at,
            "higher_low_detected_at",
        )
        confirmation_timestamp = _optional_utc(
            self.confirmation_timestamp,
            "confirmation_timestamp",
        )
        detected_at = _optional_utc(self.detected_at, "detected_at")
        _validate_stage_provenance(
            self,
            timestamps=timestamps,
            evaluated_at=evaluated_at,
            source_timestamp=source_timestamp,
            source_detected_at=source_detected_at,
            pivot_timestamp=pivot_timestamp,
            pivot_detected_at=pivot_detected_at,
            higher_low_timestamp=higher_low_timestamp,
            higher_low_detected_at=higher_low_detected_at,
            confirmation_timestamp=confirmation_timestamp,
            detected_at=detected_at,
        )
        return {
            "feature_id": self.feature_id,
            "trigger_type": self.trigger_type,
            "evaluated_at": evaluated_at.isoformat(),
            "triggered": self.triggered,
            "complete": self.complete,
            "reason_code": self.reason_code,
            "source_swing_low": source_record,
            "pivot_left_bars": self.pivot_left_bars,
            "pivot_right_bars": self.pivot_right_bars,
            "higher_low_left_bars": self.higher_low_left_bars,
            "higher_low_right_bars": self.higher_low_right_bars,
            "max_pattern_bars": self.max_pattern_bars,
            "max_breakout_bars": self.max_breakout_bars,
            "higher_low_buffer_fraction": str(self.higher_low_buffer_fraction),
            "pivot_break_buffer_fraction": str(
                self.pivot_break_buffer_fraction
            ),
            "source_low_bar_timestamp": _datetime_record(source_timestamp),
            "source_low_bar_detected_at": _datetime_record(source_detected_at),
            "source_low_price": str(self.source_low_price),
            "higher_low_threshold": str(self.higher_low_threshold),
            "pivot_timestamp": _datetime_record(pivot_timestamp),
            "pivot_detected_at": _datetime_record(pivot_detected_at),
            "pivot_high": _decimal_record(self.pivot_high),
            "pivot_break_threshold": _decimal_record(self.pivot_break_threshold),
            "higher_low_timestamp": _datetime_record(higher_low_timestamp),
            "higher_low_detected_at": _datetime_record(higher_low_detected_at),
            "higher_low_price": _decimal_record(self.higher_low_price),
            "evaluated_bar_timestamps": [value.isoformat() for value in timestamps],
            "evaluated_highs": [str(value) for value in self.evaluated_highs],
            "evaluated_lows": [str(value) for value in self.evaluated_lows],
            "evaluated_closes": [str(value) for value in self.evaluated_closes],
            "confirmation_timestamp": _datetime_record(confirmation_timestamp),
            "confirmation_close": _decimal_record(self.confirmation_close),
            "detected_at": _datetime_record(detected_at),
            "source_bar_count": self.source_bar_count,
            "config_metadata": _config_metadata(self.config_metadata),
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class _ConfirmedExtreme:
    bar: OhlcvBar
    index: int
    confirmation_index: int
    detected_at: datetime


def evaluate_higher_low_trigger(
    source_swing_low: WeeklySwingLevel,
    daily_bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    pivot_left_bars: int = DEFAULT_HIGHER_LOW_PIVOT_LEFT_BARS,
    pivot_right_bars: int = DEFAULT_HIGHER_LOW_PIVOT_RIGHT_BARS,
    higher_low_left_bars: int = DEFAULT_HIGHER_LOW_LEFT_BARS,
    higher_low_right_bars: int = DEFAULT_HIGHER_LOW_RIGHT_BARS,
    max_pattern_bars: int = DEFAULT_HIGHER_LOW_MAX_PATTERN_BARS,
    max_breakout_bars: int = DEFAULT_HIGHER_LOW_MAX_BREAKOUT_BARS,
    higher_low_buffer_fraction: Any = DEFAULT_HIGHER_LOW_BUFFER_FRACTION,
    pivot_break_buffer_fraction: Any = (
        DEFAULT_HIGHER_LOW_PIVOT_BREAK_BUFFER_FRACTION
    ),
    config_metadata: Mapping[str, str] | None = None,
) -> HigherLowTriggerResult:
    """Confirm selloff, bounce, higher low, and subsequent pivot break."""

    evaluated_at = require_utc_datetime(as_of, "as_of")
    _validate_source_level(source_swing_low)
    if source_swing_low.detected_at > evaluated_at:
        raise ValueError("source_swing_low must be available by as_of")
    pivot_left = _positive_int(pivot_left_bars, "pivot_left_bars")
    pivot_right = _positive_int(pivot_right_bars, "pivot_right_bars")
    low_left = _positive_int(higher_low_left_bars, "higher_low_left_bars")
    low_right = _positive_int(higher_low_right_bars, "higher_low_right_bars")
    pattern_limit = _positive_int(max_pattern_bars, "max_pattern_bars")
    breakout_limit = _positive_int(max_breakout_bars, "max_breakout_bars")
    minimum_pattern = pivot_left + max(pivot_right, low_left + low_right) + 1
    if pattern_limit < minimum_pattern:
        raise ValueError("max_pattern_bars must accommodate both confirmation windows")
    low_buffer = _fraction(
        higher_low_buffer_fraction,
        "higher_low_buffer_fraction",
    )
    break_buffer = _fraction(
        pivot_break_buffer_fraction,
        "pivot_break_buffer_fraction",
    )
    _validate_daily_bars(daily_bars)
    available = _available_daily_bars(
        source_swing_low,
        daily_bars,
        evaluated_at=evaluated_at,
    )
    metadata = dict(config_metadata or {})
    higher_low_threshold = source_swing_low.price * (Decimal("1") + low_buffer)
    parameters = {
        "pivot_left": pivot_left,
        "pivot_right": pivot_right,
        "low_left": low_left,
        "low_right": low_right,
        "pattern_limit": pattern_limit,
        "breakout_limit": breakout_limit,
        "low_buffer": low_buffer,
        "break_buffer": break_buffer,
        "higher_low_threshold": higher_low_threshold,
        "metadata": metadata,
    }

    anchor = _source_low_bar(source_swing_low, available)
    if anchor is None:
        return _build_result(
            source_swing_low,
            evaluated_at=evaluated_at,
            available=available,
            evaluated=(),
            parameters=parameters,
            complete=False,
            reason_code="HIGHER_LOW_SOURCE_BAR_MISSING",
        )

    pattern = tuple(bar for bar in available if bar.timestamp > anchor.timestamp)
    pattern_window = pattern[:pattern_limit]
    pivot = _first_confirmed_extreme(
        pattern_window,
        kind="high",
        left_bars=pivot_left,
        right_bars=pivot_right,
    )
    if pivot is None:
        complete = len(pattern) >= pattern_limit
        return _build_result(
            source_swing_low,
            evaluated_at=evaluated_at,
            available=available,
            evaluated=(anchor, *pattern_window),
            parameters=parameters,
            complete=complete,
            reason_code=(
                "HIGHER_LOW_PIVOT_NOT_FOUND"
                if complete
                else "HIGHER_LOW_PIVOT_PENDING"
            ),
            anchor=anchor,
        )

    pullback_series = pattern_window[pivot.index :]
    higher_low = _first_confirmed_extreme(
        pullback_series,
        kind="low",
        left_bars=low_left,
        right_bars=low_right,
        offset=pivot.index,
    )
    if higher_low is None:
        complete = len(pattern) >= pattern_limit
        return _build_result(
            source_swing_low,
            evaluated_at=evaluated_at,
            available=available,
            evaluated=(anchor, *pattern_window),
            parameters=parameters,
            complete=complete,
            reason_code=(
                "HIGHER_LOW_PULLBACK_NOT_FOUND"
                if complete
                else "HIGHER_LOW_PULLBACK_PENDING"
            ),
            anchor=anchor,
            pivot=pivot,
        )

    evaluated_pattern = pattern_window[: higher_low.confirmation_index + 1]
    if not decision_greater(higher_low.bar.low, higher_low_threshold):
        return _build_result(
            source_swing_low,
            evaluated_at=evaluated_at,
            available=available,
            evaluated=(anchor, *evaluated_pattern),
            parameters=parameters,
            complete=True,
            reason_code="HIGHER_LOW_NOT_ABOVE_SOURCE",
            anchor=anchor,
            pivot=pivot,
            higher_low=higher_low,
        )

    pivot_break_threshold = pivot.bar.high * (Decimal("1") + break_buffer)
    confirmation_boundary = pattern_window[higher_low.confirmation_index].timestamp
    breakout_bars = tuple(
        bar for bar in available if bar.timestamp > confirmation_boundary
    )[:breakout_limit]
    evaluated_breakout: list[OhlcvBar] = []
    for bar in breakout_bars:
        evaluated_breakout.append(bar)
        if decision_less(bar.low, higher_low.bar.low):
            return _build_result(
                source_swing_low,
                evaluated_at=evaluated_at,
                available=available,
                evaluated=(anchor, *evaluated_pattern, *evaluated_breakout),
                parameters=parameters,
                complete=True,
                reason_code="HIGHER_LOW_INVALIDATED",
                anchor=anchor,
                pivot=pivot,
                higher_low=higher_low,
            )
        if decision_greater(bar.close, pivot_break_threshold):
            return _build_result(
                source_swing_low,
                evaluated_at=evaluated_at,
                available=available,
                evaluated=(anchor, *evaluated_pattern, *evaluated_breakout),
                parameters=parameters,
                complete=True,
                reason_code="HIGHER_LOW_CONFIRMED",
                anchor=anchor,
                pivot=pivot,
                higher_low=higher_low,
                confirmation_bar=bar,
            )

    complete = len(breakout_bars) == breakout_limit
    return _build_result(
        source_swing_low,
        evaluated_at=evaluated_at,
        available=available,
        evaluated=(anchor, *evaluated_pattern, *evaluated_breakout),
        parameters=parameters,
        complete=complete,
        reason_code=(
            "HIGHER_LOW_BREAK_NOT_CONFIRMED"
            if complete
            else "HIGHER_LOW_BREAK_PENDING"
        ),
        anchor=anchor,
        pivot=pivot,
        higher_low=higher_low,
    )


def _build_result(
    source: WeeklySwingLevel,
    *,
    evaluated_at: datetime,
    available: Sequence[OhlcvBar],
    evaluated: Sequence[OhlcvBar],
    parameters: dict[str, Any],
    complete: bool,
    reason_code: str,
    anchor: OhlcvBar | None = None,
    pivot: _ConfirmedExtreme | None = None,
    higher_low: _ConfirmedExtreme | None = None,
    confirmation_bar: OhlcvBar | None = None,
) -> HigherLowTriggerResult:
    break_threshold = (
        None
        if pivot is None
        else pivot.bar.high
        * (Decimal("1") + parameters["break_buffer"])
    )
    triggered = reason_code == "HIGHER_LOW_CONFIRMED"
    result = HigherLowTriggerResult(
        feature_id=HIGHER_LOW_TRIGGER_FEATURE_ID,
        trigger_type=HIGHER_LOW_TRIGGER_TYPE,
        evaluated_at=evaluated_at,
        triggered=triggered,
        complete=complete,
        source_swing_low=source,
        pivot_left_bars=parameters["pivot_left"],
        pivot_right_bars=parameters["pivot_right"],
        higher_low_left_bars=parameters["low_left"],
        higher_low_right_bars=parameters["low_right"],
        max_pattern_bars=parameters["pattern_limit"],
        max_breakout_bars=parameters["breakout_limit"],
        higher_low_buffer_fraction=parameters["low_buffer"],
        pivot_break_buffer_fraction=parameters["break_buffer"],
        source_low_bar_timestamp=None if anchor is None else anchor.timestamp,
        source_low_bar_detected_at=None if anchor is None else _bar_detected_at(anchor),
        source_low_price=source.price,
        higher_low_threshold=parameters["higher_low_threshold"],
        pivot_timestamp=None if pivot is None else pivot.bar.timestamp,
        pivot_detected_at=None if pivot is None else pivot.detected_at,
        pivot_high=None if pivot is None else pivot.bar.high,
        pivot_break_threshold=break_threshold,
        higher_low_timestamp=(
            None if higher_low is None else higher_low.bar.timestamp
        ),
        higher_low_detected_at=(
            None if higher_low is None else higher_low.detected_at
        ),
        higher_low_price=None if higher_low is None else higher_low.bar.low,
        evaluated_bar_timestamps=tuple(bar.timestamp for bar in evaluated),
        evaluated_highs=tuple(bar.high for bar in evaluated),
        evaluated_lows=tuple(bar.low for bar in evaluated),
        evaluated_closes=tuple(bar.close for bar in evaluated),
        confirmation_timestamp=(
            None if confirmation_bar is None else confirmation_bar.timestamp
        ),
        confirmation_close=(
            None if confirmation_bar is None else confirmation_bar.close
        ),
        detected_at=(
            None
            if confirmation_bar is None
            else max(source.detected_at, _bar_detected_at(confirmation_bar))
        ),
        source_bar_count=len(available),
        config_metadata=parameters["metadata"],
        reason_codes=(reason_code,),
    )
    result.as_record()
    return result


def _source_low_bar(
    source: WeeklySwingLevel,
    bars: Sequence[OhlcvBar],
) -> OhlcvBar | None:
    week_end = next_bar_timestamp(source.level_timestamp, "1w")
    candidates = [
        bar
        for bar in bars
        if source.level_timestamp <= bar.timestamp < week_end
        and decision_equal(bar.low, source.price)
    ]
    return None if not candidates else candidates[-1]


def _first_confirmed_extreme(
    bars: Sequence[OhlcvBar],
    *,
    kind: Literal["high", "low"],
    left_bars: int,
    right_bars: int,
    offset: int = 0,
) -> _ConfirmedExtreme | None:
    for index in range(left_bars, len(bars) - right_bars):
        candidate = bars[index]
        comparisons = (
            *bars[index - left_bars : index],
            *bars[index + 1 : index + right_bars + 1],
        )
        value = candidate.high if kind == "high" else candidate.low
        qualifies = all(
            decision_greater(value, bar.high)
            if kind == "high"
            else decision_less(value, bar.low)
            for bar in comparisons
        )
        if qualifies:
            confirmation_index = index + right_bars
            return _ConfirmedExtreme(
                bar=candidate,
                index=index + offset,
                confirmation_index=confirmation_index + offset,
                detected_at=_bar_detected_at(bars[confirmation_index]),
            )
    return None


def _available_daily_bars(
    source: WeeklySwingLevel,
    bars: Sequence[OhlcvBar],
    *,
    evaluated_at: datetime,
) -> tuple[OhlcvBar, ...]:
    available = []
    for bar in bars:
        if _bar_identity(bar) != _level_identity(source):
            continue
        record = bar.as_record()
        if (
            next_bar_timestamp(bar.timestamp, "1d") <= evaluated_at
            and record["ingested_at"] <= evaluated_at
        ):
            available.append(bar)
    return tuple(sorted(available, key=lambda bar: bar.timestamp))


def _validate_source_level(source: WeeklySwingLevel) -> None:
    if not isinstance(source, WeeklySwingLevel):
        raise ValueError("source_swing_low must be a WeeklySwingLevel")
    source.as_record()
    if source.feature_id != WEEKLY_SWING_LEVEL_FEATURE_ID:
        raise ValueError("source_swing_low must use BTC-090 feature identity")
    if source.level_type != WEEKLY_SWING_LOW:
        raise ValueError("source_swing_low must have level_type swing_low")


def _validate_daily_bars(bars: Sequence[OhlcvBar]) -> None:
    identities: set[tuple[str, str, str, datetime]] = set()
    for bar in bars:
        if not isinstance(bar, OhlcvBar):
            raise ValueError("daily_bars must contain OhlcvBar values")
        record = bar.as_record()
        if bar.timeframe != "1d":
            raise ValueError("higher-low trigger requires canonical 1d bars")
        identity = (*_bar_identity(bar), record["timestamp"])
        if identity in identities:
            raise ValueError("higher-low bars must not contain duplicates")
        identities.add(identity)


def _validate_result(result: HigherLowTriggerResult) -> None:
    if result.feature_id != HIGHER_LOW_TRIGGER_FEATURE_ID:
        raise ValueError("feature_id must be ENTRY_TRIGGER_HIGHER_LOW")
    if result.trigger_type != HIGHER_LOW_TRIGGER_TYPE:
        raise ValueError("trigger_type must be HIGHER_LOW")
    pivot_left = _positive_int(result.pivot_left_bars, "pivot_left_bars")
    pivot_right = _positive_int(result.pivot_right_bars, "pivot_right_bars")
    low_left = _positive_int(result.higher_low_left_bars, "higher_low_left_bars")
    low_right = _positive_int(
        result.higher_low_right_bars,
        "higher_low_right_bars",
    )
    pattern_limit = _positive_int(result.max_pattern_bars, "max_pattern_bars")
    _positive_int(result.max_breakout_bars, "max_breakout_bars")
    minimum_pattern = pivot_left + max(pivot_right, low_left + low_right) + 1
    if pattern_limit < minimum_pattern:
        raise ValueError("max_pattern_bars must accommodate confirmation windows")
    low_buffer = _fraction(
        result.higher_low_buffer_fraction,
        "higher_low_buffer_fraction",
    )
    break_buffer = _fraction(
        result.pivot_break_buffer_fraction,
        "pivot_break_buffer_fraction",
    )
    if result.source_low_price != result.source_swing_low.price:
        raise ValueError("source_low_price must match BTC-090 source")
    if result.higher_low_threshold != result.source_low_price * (
        Decimal("1") + low_buffer
    ):
        raise ValueError("higher_low_threshold must match source price and buffer")
    if not result.reason_codes or len(result.reason_codes) != 1:
        raise ValueError("exactly one higher-low reason code is required")
    if result.reason_code not in HIGHER_LOW_TRIGGER_REASON_CODES:
        raise ValueError("unsupported higher-low reason code")
    if result.triggered != (result.reason_code == "HIGHER_LOW_CONFIRMED"):
        raise ValueError("triggered must match confirmed reason code")
    pending = {
        "HIGHER_LOW_SOURCE_BAR_MISSING",
        "HIGHER_LOW_PIVOT_PENDING",
        "HIGHER_LOW_PULLBACK_PENDING",
        "HIGHER_LOW_BREAK_PENDING",
    }
    if result.complete == (result.reason_code in pending):
        raise ValueError("complete must match higher-low reason code")
    if result.pivot_high is None:
        if result.pivot_break_threshold is not None:
            raise ValueError("pivot break threshold requires pivot high")
    elif result.pivot_break_threshold != result.pivot_high * (
        Decimal("1") + break_buffer
    ):
        raise ValueError("pivot_break_threshold must match pivot and buffer")

    source_present = result.source_low_bar_timestamp is not None
    pivot_present = result.pivot_timestamp is not None
    low_present = result.higher_low_timestamp is not None
    no_source_reasons = {"HIGHER_LOW_SOURCE_BAR_MISSING"}
    source_only_reasons = {
        "HIGHER_LOW_PIVOT_PENDING",
        "HIGHER_LOW_PIVOT_NOT_FOUND",
    }
    pivot_reasons = {
        "HIGHER_LOW_PULLBACK_PENDING",
        "HIGHER_LOW_PULLBACK_NOT_FOUND",
    }
    low_reasons = {
        "HIGHER_LOW_NOT_ABOVE_SOURCE",
        "HIGHER_LOW_BREAK_PENDING",
        "HIGHER_LOW_INVALIDATED",
        "HIGHER_LOW_BREAK_NOT_CONFIRMED",
        "HIGHER_LOW_CONFIRMED",
    }
    if result.reason_code in no_source_reasons and any(
        (source_present, pivot_present, low_present)
    ):
        raise ValueError("missing-source result cannot contain pattern stages")
    if result.reason_code in source_only_reasons and not (
        source_present and not pivot_present and not low_present
    ):
        raise ValueError("pivot-search result requires only source provenance")
    if result.reason_code in pivot_reasons and not (
        source_present and pivot_present and not low_present
    ):
        raise ValueError("pullback-search result requires source and pivot")
    if result.reason_code in low_reasons and not (
        source_present and pivot_present and low_present
    ):
        raise ValueError("post-pullback result requires all pattern stages")
    if result.higher_low_price is not None:
        is_above = decision_greater(
            result.higher_low_price,
            result.higher_low_threshold,
        )
        if result.reason_code == "HIGHER_LOW_NOT_ABOVE_SOURCE" and is_above:
            raise ValueError("not-above-source reason requires a failed higher low")
        if result.reason_code in low_reasons - {"HIGHER_LOW_NOT_ABOVE_SOURCE"}:
            if not is_above:
                raise ValueError("post-pullback stage requires a valid higher low")


def _validate_stage_provenance(
    result: HigherLowTriggerResult,
    *,
    timestamps: tuple[datetime, ...],
    evaluated_at: datetime,
    source_timestamp: datetime | None,
    source_detected_at: datetime | None,
    pivot_timestamp: datetime | None,
    pivot_detected_at: datetime | None,
    higher_low_timestamp: datetime | None,
    higher_low_detected_at: datetime | None,
    confirmation_timestamp: datetime | None,
    detected_at: datetime | None,
) -> None:
    source_fields = (source_timestamp, source_detected_at)
    pivot_fields = (pivot_timestamp, pivot_detected_at, result.pivot_high)
    low_fields = (
        higher_low_timestamp,
        higher_low_detected_at,
        result.higher_low_price,
    )
    if any(value is not None for value in source_fields) != all(
        value is not None for value in source_fields
    ):
        raise ValueError("source daily bar provenance must be all present or absent")
    if any(value is not None for value in pivot_fields) != all(
        value is not None for value in pivot_fields
    ):
        raise ValueError("pivot provenance must be all present or absent")
    if any(value is not None for value in low_fields) != all(
        value is not None for value in low_fields
    ):
        raise ValueError("higher-low provenance must be all present or absent")
    for label, timestamp in (
        ("source_low_bar_timestamp", source_timestamp),
        ("pivot_timestamp", pivot_timestamp),
        ("higher_low_timestamp", higher_low_timestamp),
    ):
        if timestamp is not None and timestamp not in timestamps:
            raise ValueError(f"{label} must identify an evaluated bar")
    if source_timestamp is not None:
        week_end = next_bar_timestamp(result.source_swing_low.level_timestamp, "1w")
        if not result.source_swing_low.level_timestamp <= source_timestamp < week_end:
            raise ValueError("source daily low must belong to the BTC-090 source week")
        source_index = timestamps.index(source_timestamp)
        if not decision_equal(
            result.evaluated_lows[source_index],
            result.source_low_price,
        ):
            raise ValueError("source daily low must match BTC-090 price")
    if pivot_timestamp is not None:
        pivot_index = timestamps.index(pivot_timestamp)
        if result.evaluated_highs[pivot_index] != result.pivot_high:
            raise ValueError("pivot high must match evaluated bar provenance")
        _validate_confirmed_extreme(
            result,
            index=pivot_index,
            kind="high",
            left_bars=result.pivot_left_bars,
            right_bars=result.pivot_right_bars,
            detected_at=pivot_detected_at,
        )
    if higher_low_timestamp is not None:
        low_index = timestamps.index(higher_low_timestamp)
        if result.evaluated_lows[low_index] != result.higher_low_price:
            raise ValueError("higher low must match evaluated bar provenance")
        _validate_confirmed_extreme(
            result,
            index=low_index,
            kind="low",
            left_bars=result.higher_low_left_bars,
            right_bars=result.higher_low_right_bars,
            detected_at=higher_low_detected_at,
        )
    if (
        source_timestamp is not None
        and pivot_timestamp is not None
        and not source_timestamp < pivot_timestamp
    ):
        raise ValueError("pivot must follow source low")
    if (
        pivot_timestamp is not None
        and higher_low_timestamp is not None
        and not pivot_timestamp < higher_low_timestamp
    ):
        raise ValueError("higher low must follow pivot")
    for label, value in (
        ("source_low_bar_detected_at", source_detected_at),
        ("pivot_detected_at", pivot_detected_at),
        ("higher_low_detected_at", higher_low_detected_at),
    ):
        if value is not None and value > evaluated_at:
            raise ValueError(f"{label} must be <= evaluated_at")
    confirmation_fields = (
        confirmation_timestamp,
        result.confirmation_close,
        detected_at,
    )
    if result.triggered:
        if not all(value is not None for value in confirmation_fields):
            raise ValueError("confirmed result requires confirmation provenance")
        if confirmation_timestamp not in timestamps:
            raise ValueError("confirmation_timestamp must identify an evaluated bar")
        if higher_low_timestamp is None or confirmation_timestamp <= higher_low_timestamp:
            raise ValueError("confirmation must follow higher low")
        confirmation_index = timestamps.index(confirmation_timestamp)
        if result.evaluated_closes[confirmation_index] != result.confirmation_close:
            raise ValueError("confirmation close must match evaluated provenance")
        if not decision_greater(
            result.confirmation_close,
            result.pivot_break_threshold,
        ):
            raise ValueError("confirmation close must exceed pivot threshold")
        if detected_at is None or not (
            result.source_swing_low.detected_at <= detected_at <= evaluated_at
        ):
            raise ValueError("detected_at must respect source and evaluation times")
        if detected_at < next_bar_timestamp(confirmation_timestamp, "1d"):
            raise ValueError("detected_at must follow confirmation bar close")
    elif any(value is not None for value in confirmation_fields):
        raise ValueError("untriggered result cannot contain confirmation provenance")


def _validate_confirmed_extreme(
    result: HigherLowTriggerResult,
    *,
    index: int,
    kind: Literal["high", "low"],
    left_bars: int,
    right_bars: int,
    detected_at: datetime | None,
) -> None:
    if index < left_bars or index + right_bars >= len(
        result.evaluated_bar_timestamps
    ):
        raise ValueError(f"{kind} provenance must include its confirmation window")
    values = result.evaluated_highs if kind == "high" else result.evaluated_lows
    candidate = values[index]
    comparison_values = (
        *values[index - left_bars : index],
        *values[index + 1 : index + right_bars + 1],
    )
    qualifies = all(
        decision_greater(candidate, value)
        if kind == "high"
        else decision_less(candidate, value)
        for value in comparison_values
    )
    if not qualifies:
        raise ValueError(f"persisted {kind} does not satisfy confirmation window")
    confirmation_timestamp = result.evaluated_bar_timestamps[index + right_bars]
    if detected_at is None or detected_at < next_bar_timestamp(
        confirmation_timestamp,
        "1d",
    ):
        raise ValueError(f"{kind}_detected_at must follow confirmation bar close")


def _bar_detected_at(bar: OhlcvBar) -> datetime:
    record = bar.as_record()
    return max(
        next_bar_timestamp(record["timestamp"], bar.timeframe),
        record["ingested_at"],
    )


def _level_identity(level: WeeklySwingLevel) -> tuple[str, str, str]:
    return level.exchange, level.symbol, level.provider


def _bar_identity(bar: OhlcvBar) -> tuple[str, str, str]:
    return bar.exchange, bar.symbol, bar.provider


def _positive_int(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _validate_nonnegative_int(value: Any, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{name} must be a non-negative integer")


def _fraction(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be a numeric fraction")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a numeric fraction") from error
    if not result.is_finite() or not Decimal("0") <= result <= Decimal("1"):
        raise ValueError(f"{name} must be between 0 and 1")
    return result


def _optional_utc(value: datetime | None, name: str) -> datetime | None:
    return None if value is None else require_utc_datetime(value, name)


def _decimal_record(value: Decimal | None) -> str | None:
    return None if value is None else str(value)


def _datetime_record(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _config_metadata(values: Mapping[str, str]) -> dict[str, str]:
    output = dict(values)
    for key, value in output.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("config_metadata keys must be non-empty strings")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("config_metadata values must be non-empty strings")
    return output
