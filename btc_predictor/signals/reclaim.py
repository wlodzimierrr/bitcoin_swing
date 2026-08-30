"""Point-in-time confirmation for long reclaim entry triggers."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from btc_predictor.data import OhlcvBar, next_bar_timestamp, require_utc_datetime
from btc_predictor.levels import (
    RECLAIM_LEVEL_TYPE,
    RECLAIM_SUPPORT_ROLE,
    BreakoutReclaimLevel,
)
from btc_predictor.quant.comparisons import decision_greater, decision_greater_equal


RECLAIM_TRIGGER_FEATURE_ID = "ENTRY_TRIGGER_RECLAIM"
RECLAIM_TRIGGER_TYPE = "RECLAIM"
RECLAIM_TRIGGER_REASON_CODES = (
    "RECLAIM_TRIGGER_CONFIRMATION_PENDING",
    "RECLAIM_TRIGGER_LEVEL_NOT_HELD",
    "RECLAIM_TRIGGER_CLOSE_NOT_CONFIRMED",
    "RECLAIM_TRIGGER_CONFIRMED",
)
DEFAULT_RECLAIM_CONFIRMATION_BARS = 1
DEFAULT_RECLAIM_HOLD_BUFFER_FRACTION = Decimal("0")
DEFAULT_RECLAIM_CLOSE_BUFFER_FRACTION = Decimal("0")
CONFIRMATION_TIMEFRAMES = ("1d", "1w", "1mo")


@dataclass(frozen=True)
class ReclaimTriggerResult:
    feature_id: str
    trigger_type: str
    evaluated_at: datetime
    triggered: bool
    complete: bool
    source_reclaim_level: BreakoutReclaimLevel
    confirmation_bars_required: int
    hold_buffer_fraction: Decimal
    close_buffer_fraction: Decimal
    hold_threshold: Decimal
    close_threshold: Decimal
    confirmation_bar_timestamps: tuple[datetime, ...]
    confirmation_lows: tuple[Decimal, ...]
    confirmation_closes: tuple[Decimal, ...]
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
        _validate_reclaim_level(self.source_reclaim_level)
        source_record = self.source_reclaim_level.as_record()
        _validate_result_identity(self)
        timestamps = tuple(
            require_utc_datetime(value, "confirmation_bar_timestamp")
            for value in self.confirmation_bar_timestamps
        )
        if not (
            len(timestamps)
            == len(self.confirmation_lows)
            == len(self.confirmation_closes)
        ):
            raise ValueError("confirmation bar provenance must have matching lengths")
        if any(value <= 0 for value in (*self.confirmation_lows, *self.confirmation_closes)):
            raise ValueError("confirmation prices must be > 0")
        complete_from_provenance = len(timestamps) == self.confirmation_bars_required
        if self.complete != complete_from_provenance:
            raise ValueError("complete must match confirmation bar provenance")
        _validate_nonnegative_int(self.source_bar_count, "source_bar_count")
        if self.source_bar_count < len(timestamps):
            raise ValueError("source_bar_count must include evaluated confirmation bars")
        confirmation_timestamp = _optional_utc(
            self.confirmation_timestamp,
            "confirmation_timestamp",
        )
        detected_at = _optional_utc(self.detected_at, "detected_at")
        if self.triggered:
            if not self.complete:
                raise ValueError("triggered reclaim result must be complete")
            if len(timestamps) != self.confirmation_bars_required:
                raise ValueError("triggered reclaim result requires all confirmation bars")
            if confirmation_timestamp != timestamps[-1]:
                raise ValueError("confirmation_timestamp must identify the final bar")
            if detected_at is None or detected_at > evaluated_at:
                raise ValueError("detected_at must be present and <= evaluated_at")
        elif confirmation_timestamp is not None or detected_at is not None:
            raise ValueError("untriggered reclaim result cannot have confirmation times")
        return {
            "feature_id": self.feature_id,
            "trigger_type": self.trigger_type,
            "evaluated_at": evaluated_at.isoformat(),
            "triggered": self.triggered,
            "complete": self.complete,
            "reason_code": self.reason_code,
            "source_reclaim_level": source_record,
            "confirmation_bars_required": self.confirmation_bars_required,
            "hold_buffer_fraction": str(self.hold_buffer_fraction),
            "close_buffer_fraction": str(self.close_buffer_fraction),
            "hold_threshold": str(self.hold_threshold),
            "close_threshold": str(self.close_threshold),
            "confirmation_bar_timestamps": [
                value.isoformat() for value in timestamps
            ],
            "confirmation_lows": [str(value) for value in self.confirmation_lows],
            "confirmation_closes": [
                str(value) for value in self.confirmation_closes
            ],
            "confirmation_timestamp": (
                None
                if confirmation_timestamp is None
                else confirmation_timestamp.isoformat()
            ),
            "detected_at": None if detected_at is None else detected_at.isoformat(),
            "source_bar_count": self.source_bar_count,
            "config_metadata": _config_metadata(self.config_metadata),
            "reason_codes": list(self.reason_codes),
        }


def evaluate_reclaim_trigger(
    reclaim_level: BreakoutReclaimLevel,
    bars: Sequence[OhlcvBar],
    *,
    as_of: datetime,
    confirmation_bars: int = DEFAULT_RECLAIM_CONFIRMATION_BARS,
    hold_buffer_fraction: Any = DEFAULT_RECLAIM_HOLD_BUFFER_FRACTION,
    close_buffer_fraction: Any = DEFAULT_RECLAIM_CLOSE_BUFFER_FRACTION,
    config_metadata: Mapping[str, str] | None = None,
) -> ReclaimTriggerResult:
    """Confirm that a BTC-092 reclaim level holds on subsequent closed bars."""

    evaluated_at = require_utc_datetime(as_of, "as_of")
    _validate_reclaim_level(reclaim_level)
    if reclaim_level.detected_at > evaluated_at:
        raise ValueError("reclaim_level must be available by as_of")
    required = _positive_int(confirmation_bars, "confirmation_bars")
    hold_buffer = _fraction(hold_buffer_fraction, "hold_buffer_fraction")
    close_buffer = _fraction(close_buffer_fraction, "close_buffer_fraction")
    _validate_bars(bars)

    available = _available_follow_up_bars(
        reclaim_level,
        bars,
        evaluated_at=evaluated_at,
    )
    selected = available[:required]
    hold_threshold = reclaim_level.price * (Decimal("1") - hold_buffer)
    close_threshold = reclaim_level.price * (Decimal("1") + close_buffer)
    reason_codes: list[str] = []
    complete = len(selected) == required
    triggered = False

    if not complete:
        reason_codes.append("RECLAIM_TRIGGER_CONFIRMATION_PENDING")
    else:
        if any(
            not decision_greater_equal(bar.low, hold_threshold) for bar in selected
        ):
            reason_codes.append("RECLAIM_TRIGGER_LEVEL_NOT_HELD")
        if any(not decision_greater(bar.close, close_threshold) for bar in selected):
            reason_codes.append("RECLAIM_TRIGGER_CLOSE_NOT_CONFIRMED")
        triggered = not reason_codes
        if triggered:
            reason_codes.append("RECLAIM_TRIGGER_CONFIRMED")

    final_bar = selected[-1] if triggered else None
    result = ReclaimTriggerResult(
        feature_id=RECLAIM_TRIGGER_FEATURE_ID,
        trigger_type=RECLAIM_TRIGGER_TYPE,
        evaluated_at=evaluated_at,
        triggered=triggered,
        complete=complete,
        source_reclaim_level=reclaim_level,
        confirmation_bars_required=required,
        hold_buffer_fraction=hold_buffer,
        close_buffer_fraction=close_buffer,
        hold_threshold=hold_threshold,
        close_threshold=close_threshold,
        confirmation_bar_timestamps=tuple(bar.timestamp for bar in selected),
        confirmation_lows=tuple(bar.low for bar in selected),
        confirmation_closes=tuple(bar.close for bar in selected),
        confirmation_timestamp=None if final_bar is None else final_bar.timestamp,
        detected_at=None if final_bar is None else _bar_detected_at(final_bar),
        source_bar_count=len(available),
        config_metadata=dict(config_metadata or {}),
        reason_codes=tuple(reason_codes),
    )
    result.as_record()
    return result


def _available_follow_up_bars(
    reclaim_level: BreakoutReclaimLevel,
    bars: Sequence[OhlcvBar],
    *,
    evaluated_at: datetime,
) -> tuple[OhlcvBar, ...]:
    available = []
    for bar in bars:
        if _bar_identity(bar) != _level_identity(reclaim_level):
            continue
        if bar.timeframe != reclaim_level.confirmation_timeframe:
            continue
        if bar.timestamp <= reclaim_level.confirmation_timestamp:
            continue
        record = bar.as_record()
        if (
            next_bar_timestamp(bar.timestamp, bar.timeframe) <= evaluated_at
            and record["ingested_at"] <= evaluated_at
        ):
            available.append(bar)
    return tuple(sorted(available, key=lambda bar: bar.timestamp))


def _validate_reclaim_level(reclaim_level: BreakoutReclaimLevel) -> None:
    if not isinstance(reclaim_level, BreakoutReclaimLevel):
        raise ValueError("reclaim_level must be a BreakoutReclaimLevel")
    reclaim_level.as_record()
    if reclaim_level.level_type != RECLAIM_LEVEL_TYPE:
        raise ValueError("reclaim_level must have level_type reclaim")
    if reclaim_level.level_role != RECLAIM_SUPPORT_ROLE:
        raise ValueError("reclaim_level must have reclaimed_support role")
    if reclaim_level.confirmation_timeframe not in CONFIRMATION_TIMEFRAMES:
        raise ValueError("reclaim_level must use a canonical confirmation timeframe")


def _validate_bars(bars: Sequence[OhlcvBar]) -> None:
    identities: set[tuple[str, str, str, str, datetime]] = set()
    for bar in bars:
        if not isinstance(bar, OhlcvBar):
            raise ValueError("bars must contain OhlcvBar values")
        record = bar.as_record()
        if bar.timeframe not in CONFIRMATION_TIMEFRAMES:
            raise ValueError("reclaim trigger requires canonical bars")
        identity = (*_bar_identity(bar), bar.timeframe, record["timestamp"])
        if identity in identities:
            raise ValueError("reclaim trigger bars must not contain duplicates")
        identities.add(identity)


def _validate_result_identity(result: ReclaimTriggerResult) -> None:
    if result.feature_id != RECLAIM_TRIGGER_FEATURE_ID:
        raise ValueError("feature_id must be ENTRY_TRIGGER_RECLAIM")
    if result.trigger_type != RECLAIM_TRIGGER_TYPE:
        raise ValueError("trigger_type must be RECLAIM")
    _positive_int(result.confirmation_bars_required, "confirmation_bars_required")
    _fraction(result.hold_buffer_fraction, "hold_buffer_fraction")
    _fraction(result.close_buffer_fraction, "close_buffer_fraction")
    expected_hold = result.source_reclaim_level.price * (
        Decimal("1") - result.hold_buffer_fraction
    )
    expected_close = result.source_reclaim_level.price * (
        Decimal("1") + result.close_buffer_fraction
    )
    if result.hold_threshold != expected_hold or result.close_threshold != expected_close:
        raise ValueError("reclaim trigger thresholds must match source price and buffers")
    if not result.reason_codes:
        raise ValueError("reason_codes must not be empty")
    if any(code not in RECLAIM_TRIGGER_REASON_CODES for code in result.reason_codes):
        raise ValueError("unsupported reclaim trigger reason code")
    expected_confirmed = ("RECLAIM_TRIGGER_CONFIRMED",)
    if result.triggered and result.reason_codes != expected_confirmed:
        raise ValueError("triggered reclaim result must use confirmed reason code")
    if not result.triggered and "RECLAIM_TRIGGER_CONFIRMED" in result.reason_codes:
        raise ValueError("untriggered reclaim result cannot be confirmed")


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


def _config_metadata(values: Mapping[str, str]) -> dict[str, str]:
    output = dict(values)
    for key, value in output.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("config_metadata keys must be non-empty strings")
        if not isinstance(value, str) or not value.strip():
            raise ValueError("config_metadata values must be non-empty strings")
    return output
