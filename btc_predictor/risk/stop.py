"""Initial structural stop (BTC-142).

Rulebook 16.1:

    long:  Stop = StructuralInvalidation - VolatilityBuffer
    short: Stop = StructuralInvalidation + VolatilityBuffer

This module composes the BTC-140 invalidation level with the BTC-141 buffer.
It owns the stop price and the stop's own geometry (its distance from entry).
It does not own reward/risk (BTC-143), the risk budget (BTC-144), position
sizing (BTC-145), or any trailing behaviour.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.quant.comparisons import (
    decision_greater_equal,
    decision_less_equal,
)
from btc_predictor.risk.invalidation import (
    INVALIDATION_DIRECTIONS,
    LONG_DIRECTION,
    SHORT_DIRECTION,
)


INITIAL_STOP_FEATURE_ID = "INITIAL_STOP"
INITIAL_STOP_POLICY_VERSION = "INITIAL_STOP_V1"

INITIAL_STOP_REASON_CODES = (
    "INITIAL_STOP_COMPLETE",
    "INITIAL_STOP_INPUT_MISSING",
    "INITIAL_STOP_INVALIDATION_INCOMPLETE",
    "INITIAL_STOP_BUFFER_INCOMPLETE",
    "INITIAL_STOP_NON_POSITIVE",
    "INITIAL_STOP_WRONG_SIDE_OF_ENTRY",
)


@dataclass(frozen=True)
class InitialStopResult:
    feature_id: str
    policy_version: str
    direction: str
    invalidation_price: Decimal | None
    buffer: Decimal | None
    stop_price: Decimal | None
    entry_price: Decimal | None
    stop_distance: Decimal | None
    stop_distance_fraction: Decimal | None
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        if self.complete and self.stop_price is None:
            raise ValueError("complete initial stop requires a stop price")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "direction": self.direction,
            "invalidation_price": _optional(self.invalidation_price),
            "buffer": _optional(self.buffer),
            "stop_price": _optional(self.stop_price),
            "entry_price": _optional(self.entry_price),
            "stop_distance": _optional(self.stop_distance),
            "stop_distance_fraction": _optional(self.stop_distance_fraction),
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def calculate_initial_stop(
    *,
    invalidation_price: Any | None,
    buffer: Any | None,
    direction: str,
    entry_price: Any | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> InitialStopResult:
    """Place the stop a buffer beyond the structural invalidation level.

    ``entry_price`` is optional. When supplied it enables the side check -- a
    long stop must sit below entry and a short stop above it -- and yields the
    stop's distance from entry, which BTC-145 consumes as ``StopDistance%``.
    """

    if direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    metadata = dict(config_metadata or {})
    entry = (
        _positive_decimal(entry_price, "entry_price")
        if entry_price is not None
        else None
    )

    if invalidation_price is None or buffer is None:
        return _incomplete(
            direction=direction,
            invalidation_price=(
                _positive_decimal(invalidation_price, "invalidation_price")
                if invalidation_price is not None
                else None
            ),
            buffer=(
                _non_negative_decimal(buffer, "buffer")
                if buffer is not None
                else None
            ),
            entry=entry,
            metadata=metadata,
            reason_codes=("INITIAL_STOP_INPUT_MISSING",),
        )

    level = _positive_decimal(invalidation_price, "invalidation_price")
    distance = _non_negative_decimal(buffer, "buffer")
    stop_price = (
        level - distance if direction == LONG_DIRECTION else level + distance
    )

    # A buffer wide enough to drive the stop to or below zero is not a stop.
    if decision_less_equal(stop_price, 0):
        return _incomplete(
            direction=direction,
            invalidation_price=level,
            buffer=distance,
            entry=entry,
            metadata=metadata,
            reason_codes=("INITIAL_STOP_NON_POSITIVE",),
        )

    if entry is not None and _is_wrong_side(stop_price, entry, direction):
        return _incomplete(
            direction=direction,
            invalidation_price=level,
            buffer=distance,
            entry=entry,
            metadata=metadata,
            reason_codes=("INITIAL_STOP_WRONG_SIDE_OF_ENTRY",),
        )

    stop_distance = None if entry is None else abs(entry - stop_price)
    return InitialStopResult(
        feature_id=INITIAL_STOP_FEATURE_ID,
        policy_version=INITIAL_STOP_POLICY_VERSION,
        direction=direction,
        invalidation_price=level,
        buffer=distance,
        stop_price=stop_price,
        entry_price=entry,
        stop_distance=stop_distance,
        stop_distance_fraction=(
            None if stop_distance is None else stop_distance / entry
        ),
        config_metadata=metadata,
        complete=True,
        reason_codes=("INITIAL_STOP_COMPLETE",),
    )


def initial_stop_for_setup(
    invalidation: Any,
    buffer: Any,
    *,
    config_metadata: Mapping[str, str] | None = None,
) -> InitialStopResult:
    """Canonical path: compose a BTC-140 selection with a BTC-141 buffer.

    Direction, invalidation level and entry price are all taken from the
    BTC-140 result so the trade side cannot be restated inconsistently.
    Incompleteness upstream propagates rather than producing a stop from
    partial inputs.
    """

    invalidation_record = _as_record(invalidation, "invalidation")
    buffer_record = _as_record(buffer, "buffer")
    direction = invalidation_record.get("direction") or LONG_DIRECTION
    metadata = dict(config_metadata or {})
    entry = invalidation_record.get("entry_price")

    reason_codes = []
    if not invalidation_record.get("complete"):
        reason_codes.append("INITIAL_STOP_INVALIDATION_INCOMPLETE")
    if not buffer_record.get("complete"):
        reason_codes.append("INITIAL_STOP_BUFFER_INCOMPLETE")
    if reason_codes:
        return _incomplete(
            direction=direction if direction in INVALIDATION_DIRECTIONS else "",
            invalidation_price=None,
            buffer=None,
            entry=(
                _positive_decimal(entry, "entry_price")
                if entry is not None
                else None
            ),
            metadata=metadata,
            reason_codes=tuple(reason_codes),
        )

    return calculate_initial_stop(
        invalidation_price=invalidation_record.get("invalidation_price"),
        buffer=buffer_record.get("buffer"),
        direction=direction,
        entry_price=entry,
        config_metadata=metadata,
    )


def _is_wrong_side(stop_price: Decimal, entry: Decimal, direction: str) -> bool:
    if direction == LONG_DIRECTION:
        return decision_greater_equal(stop_price, entry)
    return decision_less_equal(stop_price, entry)


def _incomplete(
    *,
    direction: str,
    invalidation_price: Decimal | None,
    buffer: Decimal | None,
    entry: Decimal | None,
    metadata: dict[str, str],
    reason_codes: tuple[str, ...],
) -> InitialStopResult:
    return InitialStopResult(
        feature_id=INITIAL_STOP_FEATURE_ID,
        policy_version=INITIAL_STOP_POLICY_VERSION,
        direction=direction,
        invalidation_price=invalidation_price,
        buffer=buffer,
        stop_price=None,
        entry_price=entry,
        stop_distance=None,
        stop_distance_fraction=None,
        config_metadata=metadata,
        complete=False,
        reason_codes=reason_codes,
    )


def _as_record(source: Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    as_record = getattr(source, "as_record", None)
    if callable(as_record):
        return as_record()
    raise TypeError(f"{name} must be a mapping or expose as_record()")


def _optional(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _decimal(value: Any, name: str) -> Decimal:
    try:
        return Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result < 0:
        raise ValueError(f"{name} must be non-negative")
    return result


__all__ = [
    "INITIAL_STOP_FEATURE_ID",
    "INITIAL_STOP_POLICY_VERSION",
    "INITIAL_STOP_REASON_CODES",
    "InitialStopResult",
    "calculate_initial_stop",
    "initial_stop_for_setup",
]
