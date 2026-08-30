"""Point-in-time breakout, retest, and continuation confirmation."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from btc_predictor.data import OhlcvBar, next_bar_timestamp, require_utc_datetime
from btc_predictor.levels import (
    BREAKOUT_LEVEL_TYPE,
    BREAKOUT_SUPPORT_ROLE,
    BreakoutReclaimLevel,
)
from btc_predictor.quant.comparisons import (
    decision_greater,
    decision_greater_equal,
    decision_less_equal,
)
from btc_predictor.quant.distances import atr_normalized_distance


BREAKOUT_RETEST_TRIGGER_FEATURE_ID = "ENTRY_TRIGGER_BREAKOUT_RETEST"
BREAKOUT_RETEST_TRIGGER_TYPE = "BREAKOUT_RETEST"
BREAKOUT_RETEST_TRIGGER_REASON_CODES = (
    "BREAKOUT_RETEST_ATR_MISSING",
    "BREAKOUT_RETEST_PENDING",
    "BREAKOUT_RETEST_NOT_FOUND",
    "BREAKOUT_RETEST_SUPPORT_FAILED",
    "BREAKOUT_RETEST_CONTINUATION_PENDING",
    "BREAKOUT_RETEST_CONTINUATION_NOT_CONFIRMED",
    "BREAKOUT_RETEST_CONFIRMED",
)
DEFAULT_BREAKOUT_RETEST_MAX_RETEST_BARS = 5
DEFAULT_BREAKOUT_RETEST_MAX_CONTINUATION_BARS = 3
DEFAULT_BREAKOUT_RETEST_DISTANCE_ATR_MAX = Decimal("0.50")
DEFAULT_BREAKOUT_RETEST_SUPPORT_BREACH_ATR_MAX = Decimal("0.25")
DEFAULT_BREAKOUT_RETEST_CONTINUATION_BUFFER_ATR = Decimal("0")
CONFIRMATION_TIMEFRAMES = ("1d", "1w", "1mo")


@dataclass(frozen=True)
class BreakoutRetestTriggerResult:
    feature_id: str
    trigger_type: str
    evaluated_at: datetime
    triggered: bool
    complete: bool
    source_breakout_level: BreakoutReclaimLevel
    atr: Decimal | None
    atr_available_at: datetime | None
    max_retest_bars: int
    max_continuation_bars: int
    retest_distance_atr_max: Decimal
    support_breach_atr_max: Decimal
    continuation_buffer_atr: Decimal
    retest_zone_upper: Decimal | None
    support_floor: Decimal | None
    retest_timestamp: datetime | None
    retest_detected_at: datetime | None
    retest_low: Decimal | None
    retest_high: Decimal | None
    retest_close: Decimal | None
    retest_distance_atr: Decimal | None
    continuation_threshold: Decimal | None
    evaluated_bar_timestamps: tuple[datetime, ...]
    evaluated_lows: tuple[Decimal, ...]
    evaluated_highs: tuple[Decimal, ...]
    evaluated_closes: tuple[Decimal, ...]
    confirmation_timestamp: datetime | None
    detected_at: datetime | None
    source_bar_count: int
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        return self.reason_codes[0] if self.reason_codes else None

    def as_record(self) -> dict[str, Any]:
        evaluated_at = require_utc_datetime(self.evaluated_at, "evaluated_at")
        _validate_breakout_level(self.source_breakout_level)
        source_record = self.source_breakout_level.as_record()
        _validate_result(self)
        atr_available_at = _optional_utc(self.atr_available_at, "atr_available_at")
        retest_timestamp = _optional_utc(self.retest_timestamp, "retest_timestamp")
        retest_detected_at = _optional_utc(
            self.retest_detected_at,
            "retest_detected_at",
        )
        confirmation_timestamp = _optional_utc(
            self.confirmation_timestamp,
            "confirmation_timestamp",
        )
        detected_at = _optional_utc(self.detected_at, "detected_at")
        timestamps = tuple(
            require_utc_datetime(value, "evaluated_bar_timestamp")
            for value in self.evaluated_bar_timestamps
        )
        if not (
            len(timestamps)
            == len(self.evaluated_lows)
            == len(self.evaluated_highs)
            == len(self.evaluated_closes)
        ):
            raise ValueError("evaluated bar provenance must have matching lengths")
        prices = (*self.evaluated_lows, *self.evaluated_highs, *self.evaluated_closes)
        if any(value <= 0 for value in prices):
            raise ValueError("evaluated bar prices must be > 0")
        _validate_nonnegative_int(self.source_bar_count, "source_bar_count")
        if self.source_bar_count < len(timestamps):
            raise ValueError("source_bar_count must include evaluated bars")
        if timestamps != tuple(sorted(timestamps)) or len(set(timestamps)) != len(
            timestamps
        ):
            raise ValueError("evaluated bar timestamps must be unique and ordered")
        if any(
            value <= self.source_breakout_level.confirmation_timestamp
            for value in timestamps
        ):
            raise ValueError("evaluated bars must follow the breakout bar")
        if retest_timestamp is not None and retest_timestamp not in timestamps:
            raise ValueError("retest_timestamp must identify an evaluated bar")
        if retest_timestamp is not None:
            retest_index = timestamps.index(retest_timestamp)
            if (
                self.evaluated_lows[retest_index] != self.retest_low
                or self.evaluated_highs[retest_index] != self.retest_high
                or self.evaluated_closes[retest_index] != self.retest_close
            ):
                raise ValueError("retest prices must match evaluated bar provenance")
            if retest_detected_at is None or not (
                next_bar_timestamp(
                    retest_timestamp,
                    self.source_breakout_level.confirmation_timeframe,
                )
                <= retest_detected_at
                <= evaluated_at
            ):
                raise ValueError("retest_detected_at must follow bar close by evaluated_at")
        if self.triggered:
            if not self.complete:
                raise ValueError("triggered breakout-retest result must be complete")
            if confirmation_timestamp not in timestamps:
                raise ValueError("confirmation_timestamp must identify an evaluated bar")
            if detected_at is None or detected_at > evaluated_at:
                raise ValueError("detected_at must be present and <= evaluated_at")
            confirmation_index = timestamps.index(confirmation_timestamp)
            if not decision_greater_equal(
                self.evaluated_lows[confirmation_index],
                self.support_floor,
            ) or not decision_greater_equal(
                self.evaluated_closes[confirmation_index],
                self.source_breakout_level.price,
            ):
                raise ValueError("confirmation bar must preserve breakout support")
            if not decision_greater(
                self.evaluated_closes[confirmation_index],
                self.continuation_threshold,
            ):
                raise ValueError("confirmation close must exceed continuation threshold")
        elif confirmation_timestamp is not None or detected_at is not None:
            raise ValueError("untriggered result cannot have confirmation times")
        return {
            "feature_id": self.feature_id,
            "trigger_type": self.trigger_type,
            "evaluated_at": evaluated_at.isoformat(),
            "triggered": self.triggered,
            "complete": self.complete,
            "reason_code": self.reason_code,
            "source_breakout_level": source_record,
            "atr": _decimal_record(self.atr),
            "atr_available_at": _datetime_record(atr_available_at),
            "max_retest_bars": self.max_retest_bars,
            "max_continuation_bars": self.max_continuation_bars,
            "retest_distance_atr_max": str(self.retest_distance_atr_max),
            "support_breach_atr_max": str(self.support_breach_atr_max),
            "continuation_buffer_atr": str(self.continuation_buffer_atr),
            "retest_zone_upper": _decimal_record(self.retest_zone_upper),
            "support_floor": _decimal_record(self.support_floor),
            "retest_timestamp": _datetime_record(retest_timestamp),
            "retest_detected_at": _datetime_record(retest_detected_at),
            "retest_low": _decimal_record(self.retest_low),
            "retest_high": _decimal_record(self.retest_high),
            "retest_close": _decimal_record(self.retest_close),
            "retest_distance_atr": _decimal_record(self.retest_distance_atr),
            "continuation_threshold": _decimal_record(
                self.continuation_threshold,
            ),
            "evaluated_bar_timestamps": [value.isoformat() for value in timestamps],
            "evaluated_lows": [str(value) for value in self.evaluated_lows],
            "evaluated_highs": [str(value) for value in self.evaluated_highs],
            "evaluated_closes": [str(value) for value in self.evaluated_closes],
            "confirmation_timestamp": _datetime_record(confirmation_timestamp),
            "detected_at": _datetime_record(detected_at),
            "source_bar_count": self.source_bar_count,
            "config_metadata": _config_metadata(self.config_metadata),
            "reason_codes": list(self.reason_codes),
        }


def evaluate_breakout_retest_trigger(
    breakout_level: BreakoutReclaimLevel,
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    atr: Any | None = None,
    atr_available_at: datetime | None = None,
    max_retest_bars: int = DEFAULT_BREAKOUT_RETEST_MAX_RETEST_BARS,
    max_continuation_bars: int = DEFAULT_BREAKOUT_RETEST_MAX_CONTINUATION_BARS,
    retest_distance_atr_max: Any = DEFAULT_BREAKOUT_RETEST_DISTANCE_ATR_MAX,
    support_breach_atr_max: Any = DEFAULT_BREAKOUT_RETEST_SUPPORT_BREACH_ATR_MAX,
    continuation_buffer_atr: Any = DEFAULT_BREAKOUT_RETEST_CONTINUATION_BUFFER_ATR,
    config_metadata: Mapping[str, str] | None = None,
) -> BreakoutRetestTriggerResult:
    """Confirm a pullback, support hold, and continuation after BTC-092 breakout."""

    evaluated_at = require_utc_datetime(as_of, "as_of")
    _validate_breakout_level(breakout_level)
    if breakout_level.detected_at > evaluated_at:
        raise ValueError("breakout_level must be available by as_of")
    retest_limit = _positive_int(max_retest_bars, "max_retest_bars")
    continuation_limit = _positive_int(
        max_continuation_bars,
        "max_continuation_bars",
    )
    distance_limit = _positive_decimal(
        retest_distance_atr_max,
        "retest_distance_atr_max",
    )
    breach_limit = _nonnegative_decimal(
        support_breach_atr_max,
        "support_breach_atr_max",
    )
    continuation_buffer = _nonnegative_decimal(
        continuation_buffer_atr,
        "continuation_buffer_atr",
    )
    if breach_limit > distance_limit:
        raise ValueError(
            "support_breach_atr_max must be <= retest_distance_atr_max"
        )
    _validate_bars(bars)
    available = _available_follow_up_bars(
        breakout_level,
        bars,
        evaluated_at=evaluated_at,
    )
    metadata = dict(config_metadata or {})

    if atr is None and atr_available_at is None:
        return _build_result(
            breakout_level,
            evaluated_at=evaluated_at,
            available=available,
            evaluated=(),
            atr=None,
            atr_available_at=None,
            retest_limit=retest_limit,
            continuation_limit=continuation_limit,
            distance_limit=distance_limit,
            breach_limit=breach_limit,
            continuation_buffer=continuation_buffer,
            complete=False,
            reason_code="BREAKOUT_RETEST_ATR_MISSING",
            config_metadata=metadata,
        )
    if atr is None or atr_available_at is None:
        raise ValueError("atr and atr_available_at must be supplied together")
    atr_value = _positive_decimal(atr, "atr")
    atr_time = require_utc_datetime(atr_available_at, "atr_available_at")
    if atr_time > breakout_level.detected_at:
        raise ValueError("atr must be available by breakout detection time")

    retest_zone_upper = breakout_level.price + distance_limit * atr_value
    support_floor = breakout_level.price - breach_limit * atr_value
    if support_floor <= 0:
        raise ValueError("support floor must remain > 0")
    retest_bar: OhlcvBar | None = None
    evaluated: list[OhlcvBar] = []

    for bar in available[:retest_limit]:
        evaluated.append(bar)
        if not decision_less_equal(bar.low, retest_zone_upper):
            continue
        if not decision_greater_equal(
            bar.low,
            support_floor,
        ) or not decision_greater_equal(bar.close, breakout_level.price):
            return _build_result(
                breakout_level,
                evaluated_at=evaluated_at,
                available=available,
                evaluated=tuple(evaluated),
                atr=atr_value,
                atr_available_at=atr_time,
                retest_limit=retest_limit,
                continuation_limit=continuation_limit,
                distance_limit=distance_limit,
                breach_limit=breach_limit,
                continuation_buffer=continuation_buffer,
                complete=True,
                reason_code="BREAKOUT_RETEST_SUPPORT_FAILED",
                config_metadata=metadata,
            )
        retest_bar = bar
        break

    if retest_bar is None:
        complete = len(available) >= retest_limit
        return _build_result(
            breakout_level,
            evaluated_at=evaluated_at,
            available=available,
            evaluated=tuple(evaluated),
            atr=atr_value,
            atr_available_at=atr_time,
            retest_limit=retest_limit,
            continuation_limit=continuation_limit,
            distance_limit=distance_limit,
            breach_limit=breach_limit,
            continuation_buffer=continuation_buffer,
            complete=complete,
            reason_code=(
                "BREAKOUT_RETEST_NOT_FOUND"
                if complete
                else "BREAKOUT_RETEST_PENDING"
            ),
            config_metadata=metadata,
        )

    retest_index = available.index(retest_bar)
    continuation_threshold = retest_bar.high + continuation_buffer * atr_value
    continuation_bars = available[
        retest_index + 1 : retest_index + 1 + continuation_limit
    ]
    for bar in continuation_bars:
        evaluated.append(bar)
        if not decision_greater_equal(
            bar.low,
            support_floor,
        ) or not decision_greater_equal(bar.close, breakout_level.price):
            return _build_result(
                breakout_level,
                evaluated_at=evaluated_at,
                available=available,
                evaluated=tuple(evaluated),
                atr=atr_value,
                atr_available_at=atr_time,
                retest_limit=retest_limit,
                continuation_limit=continuation_limit,
                distance_limit=distance_limit,
                breach_limit=breach_limit,
                continuation_buffer=continuation_buffer,
                complete=True,
                reason_code="BREAKOUT_RETEST_SUPPORT_FAILED",
                config_metadata=metadata,
                retest_bar=retest_bar,
            )
        if decision_greater(bar.close, continuation_threshold):
            return _build_result(
                breakout_level,
                evaluated_at=evaluated_at,
                available=available,
                evaluated=tuple(evaluated),
                atr=atr_value,
                atr_available_at=atr_time,
                retest_limit=retest_limit,
                continuation_limit=continuation_limit,
                distance_limit=distance_limit,
                breach_limit=breach_limit,
                continuation_buffer=continuation_buffer,
                complete=True,
                reason_code="BREAKOUT_RETEST_CONFIRMED",
                config_metadata=metadata,
                retest_bar=retest_bar,
                confirmation_bar=bar,
            )

    complete = len(continuation_bars) == continuation_limit
    return _build_result(
        breakout_level,
        evaluated_at=evaluated_at,
        available=available,
        evaluated=tuple(evaluated),
        atr=atr_value,
        atr_available_at=atr_time,
        retest_limit=retest_limit,
        continuation_limit=continuation_limit,
        distance_limit=distance_limit,
        breach_limit=breach_limit,
        continuation_buffer=continuation_buffer,
        complete=complete,
        reason_code=(
            "BREAKOUT_RETEST_CONTINUATION_NOT_CONFIRMED"
            if complete
            else "BREAKOUT_RETEST_CONTINUATION_PENDING"
        ),
        config_metadata=metadata,
        retest_bar=retest_bar,
    )


def _build_result(
    breakout_level: BreakoutReclaimLevel,
    *,
    evaluated_at: datetime,
    available: Sequence[OhlcvBar],
    evaluated: Sequence[OhlcvBar],
    atr: Decimal | None,
    atr_available_at: datetime | None,
    retest_limit: int,
    continuation_limit: int,
    distance_limit: Decimal,
    breach_limit: Decimal,
    continuation_buffer: Decimal,
    complete: bool,
    reason_code: str,
    config_metadata: dict[str, str],
    retest_bar: OhlcvBar | None = None,
    confirmation_bar: OhlcvBar | None = None,
) -> BreakoutRetestTriggerResult:
    retest_distance = None
    support_floor = None
    retest_zone_upper = None
    continuation_threshold = None
    if atr is not None:
        support_floor = breakout_level.price - breach_limit * atr
        retest_zone_upper = breakout_level.price + distance_limit * atr
    if atr is not None and retest_bar is not None:
        retest_distance = Decimal(
            str(
                atr_normalized_distance(
                    float(retest_bar.low),
                    float(breakout_level.price),
                    float(atr),
                )
            )
        )
        continuation_threshold = retest_bar.high + continuation_buffer * atr
    triggered = reason_code == "BREAKOUT_RETEST_CONFIRMED"
    result = BreakoutRetestTriggerResult(
        feature_id=BREAKOUT_RETEST_TRIGGER_FEATURE_ID,
        trigger_type=BREAKOUT_RETEST_TRIGGER_TYPE,
        evaluated_at=evaluated_at,
        triggered=triggered,
        complete=complete,
        source_breakout_level=breakout_level,
        atr=atr,
        atr_available_at=atr_available_at,
        max_retest_bars=retest_limit,
        max_continuation_bars=continuation_limit,
        retest_distance_atr_max=distance_limit,
        support_breach_atr_max=breach_limit,
        continuation_buffer_atr=continuation_buffer,
        retest_zone_upper=retest_zone_upper,
        support_floor=support_floor,
        retest_timestamp=None if retest_bar is None else retest_bar.timestamp,
        retest_detected_at=(
            None if retest_bar is None else _bar_detected_at(retest_bar)
        ),
        retest_low=None if retest_bar is None else retest_bar.low,
        retest_high=None if retest_bar is None else retest_bar.high,
        retest_close=None if retest_bar is None else retest_bar.close,
        retest_distance_atr=retest_distance,
        continuation_threshold=continuation_threshold,
        evaluated_bar_timestamps=tuple(bar.timestamp for bar in evaluated),
        evaluated_lows=tuple(bar.low for bar in evaluated),
        evaluated_highs=tuple(bar.high for bar in evaluated),
        evaluated_closes=tuple(bar.close for bar in evaluated),
        confirmation_timestamp=(
            None if confirmation_bar is None else confirmation_bar.timestamp
        ),
        detected_at=(
            None if confirmation_bar is None else _bar_detected_at(confirmation_bar)
        ),
        source_bar_count=len(available),
        config_metadata=config_metadata,
        reason_codes=(reason_code,),
    )
    result.as_record()
    return result


def _available_follow_up_bars(
    breakout_level: BreakoutReclaimLevel,
    bars: Sequence[OhlcvBar],
    *,
    evaluated_at: datetime,
) -> tuple[OhlcvBar, ...]:
    available = []
    for bar in bars:
        if _bar_identity(bar) != _level_identity(breakout_level):
            continue
        if bar.timeframe != breakout_level.confirmation_timeframe:
            continue
        if bar.timestamp <= breakout_level.confirmation_timestamp:
            continue
        record = bar.as_record()
        if (
            next_bar_timestamp(bar.timestamp, bar.timeframe) <= evaluated_at
            and record["ingested_at"] <= evaluated_at
        ):
            available.append(bar)
    return tuple(sorted(available, key=lambda bar: bar.timestamp))


def _validate_breakout_level(breakout_level: BreakoutReclaimLevel) -> None:
    if not isinstance(breakout_level, BreakoutReclaimLevel):
        raise ValueError("breakout_level must be a BreakoutReclaimLevel")
    breakout_level.as_record()
    if breakout_level.level_type != BREAKOUT_LEVEL_TYPE:
        raise ValueError("breakout_level must have level_type breakout")
    if breakout_level.level_role != BREAKOUT_SUPPORT_ROLE:
        raise ValueError("breakout_level must have support_after_breakout role")
    if breakout_level.confirmation_timeframe not in CONFIRMATION_TIMEFRAMES:
        raise ValueError("breakout_level must use a canonical confirmation timeframe")


def _validate_bars(bars: Sequence[OhlcvBar]) -> None:
    identities: set[tuple[str, str, str, str, datetime]] = set()
    for bar in bars:
        if not isinstance(bar, OhlcvBar):
            raise ValueError("bars must contain OhlcvBar values")
        record = bar.as_record()
        if bar.timeframe not in CONFIRMATION_TIMEFRAMES:
            raise ValueError("breakout-retest trigger requires canonical bars")
        identity = (*_bar_identity(bar), bar.timeframe, record["timestamp"])
        if identity in identities:
            raise ValueError("breakout-retest bars must not contain duplicates")
        identities.add(identity)


def _validate_result(result: BreakoutRetestTriggerResult) -> None:
    if result.feature_id != BREAKOUT_RETEST_TRIGGER_FEATURE_ID:
        raise ValueError("feature_id must be ENTRY_TRIGGER_BREAKOUT_RETEST")
    if result.trigger_type != BREAKOUT_RETEST_TRIGGER_TYPE:
        raise ValueError("trigger_type must be BREAKOUT_RETEST")
    _positive_int(result.max_retest_bars, "max_retest_bars")
    _positive_int(result.max_continuation_bars, "max_continuation_bars")
    distance_limit = _positive_decimal(
        result.retest_distance_atr_max,
        "retest_distance_atr_max",
    )
    breach_limit = _nonnegative_decimal(
        result.support_breach_atr_max,
        "support_breach_atr_max",
    )
    continuation_buffer = _nonnegative_decimal(
        result.continuation_buffer_atr,
        "continuation_buffer_atr",
    )
    if breach_limit > distance_limit:
        raise ValueError(
            "support_breach_atr_max must be <= retest_distance_atr_max"
        )
    if not result.reason_codes or len(result.reason_codes) != 1:
        raise ValueError("exactly one breakout-retest reason code is required")
    if result.reason_code not in BREAKOUT_RETEST_TRIGGER_REASON_CODES:
        raise ValueError("unsupported breakout-retest reason code")
    if result.triggered != (result.reason_code == "BREAKOUT_RETEST_CONFIRMED"):
        raise ValueError("triggered must match confirmed reason code")
    pending_reasons = {
        "BREAKOUT_RETEST_ATR_MISSING",
        "BREAKOUT_RETEST_PENDING",
        "BREAKOUT_RETEST_CONTINUATION_PENDING",
    }
    if result.complete == (result.reason_code in pending_reasons):
        raise ValueError("complete must match breakout-retest reason code")

    atr_fields = (
        result.atr,
        result.atr_available_at,
        result.retest_zone_upper,
        result.support_floor,
    )
    if result.atr is None:
        if any(value is not None for value in atr_fields):
            raise ValueError("missing ATR result cannot contain ATR thresholds")
    else:
        atr = _positive_decimal(result.atr, "atr")
        if result.atr_available_at is None:
            raise ValueError("atr_available_at is required with atr")
        atr_available_at = require_utc_datetime(
            result.atr_available_at,
            "atr_available_at",
        )
        if atr_available_at > result.source_breakout_level.detected_at:
            raise ValueError("atr must be available by breakout detection time")
        expected_upper = result.source_breakout_level.price + distance_limit * atr
        expected_floor = result.source_breakout_level.price - breach_limit * atr
        if expected_floor <= 0:
            raise ValueError("support floor must remain > 0")
        if (
            result.retest_zone_upper != expected_upper
            or result.support_floor != expected_floor
        ):
            raise ValueError("ATR thresholds must match source price and configuration")

    retest_fields = (
        result.retest_timestamp,
        result.retest_detected_at,
        result.retest_low,
        result.retest_high,
        result.retest_close,
        result.retest_distance_atr,
        result.continuation_threshold,
    )
    present = tuple(value is not None for value in retest_fields)
    if any(present) and not all(present):
        raise ValueError("retest provenance must be entirely present or absent")
    if all(present):
        if (
            result.atr is None
            or result.retest_low is None
            or result.retest_high is None
            or result.retest_close is None
            or result.retest_distance_atr is None
            or result.retest_zone_upper is None
            or result.support_floor is None
        ):
            raise ValueError("retest provenance requires ATR and retest prices")
        expected_distance = Decimal(
            str(
                atr_normalized_distance(
                    float(result.retest_low),
                    float(result.source_breakout_level.price),
                    float(result.atr),
                )
            )
        )
        if result.retest_distance_atr != expected_distance:
            raise ValueError("retest distance must match BTC-045 calculation")
        if (
            not decision_less_equal(result.retest_low, result.retest_zone_upper)
            or not decision_greater_equal(result.retest_low, result.support_floor)
            or not decision_greater_equal(
                result.retest_close,
                result.source_breakout_level.price,
            )
        ):
            raise ValueError("retest bar must enter the zone and preserve support")
        expected_continuation = (
            result.retest_high + continuation_buffer * result.atr
        )
        if result.continuation_threshold != expected_continuation:
            raise ValueError("continuation threshold must match retest high and buffer")
    retest_required_reasons = {
        "BREAKOUT_RETEST_CONTINUATION_PENDING",
        "BREAKOUT_RETEST_CONTINUATION_NOT_CONFIRMED",
        "BREAKOUT_RETEST_CONFIRMED",
    }
    if result.reason_code in retest_required_reasons and not all(present):
        raise ValueError("continuation result requires retest provenance")
    no_retest_reasons = {
        "BREAKOUT_RETEST_ATR_MISSING",
        "BREAKOUT_RETEST_PENDING",
        "BREAKOUT_RETEST_NOT_FOUND",
    }
    if result.reason_code in no_retest_reasons and any(present):
        raise ValueError("pre-retest result cannot contain retest provenance")


def _bar_detected_at(bar: OhlcvBar) -> datetime:
    record = bar.as_record()
    return max(
        next_bar_timestamp(record["timestamp"], bar.timeframe),
        record["ingested_at"],
    )


def _level_identity(level: BreakoutReclaimLevel) -> tuple[str, str, str]:
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


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be > 0")
    return result


def _nonnegative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be >= 0")
    return result


def _decimal(value: Any, name: str) -> Decimal:
    if isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as error:
        raise ValueError(f"{name} must be numeric") from error
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
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
