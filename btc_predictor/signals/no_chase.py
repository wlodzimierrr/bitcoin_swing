"""Directional no-chase hard veto for intended entry zones."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from btc_predictor.data import require_utc_datetime
from btc_predictor.levels import (
    LEVEL_CLUSTER_RESISTANCE,
    LEVEL_CLUSTER_SUPPORT,
    LevelCluster,
)
from btc_predictor.quant.comparisons import decision_greater
from btc_predictor.quant.distances import (
    atr_normalized_distance,
    pairwise_price_distance,
)


NO_CHASE_FEATURE_ID = "NO_CHASE_FILTER"
NO_CHASE_DIRECTIONS = ("long", "short")
NO_CHASE_DISTANCE_MODES = ("atr", "fractional")
NO_CHASE_EFFECTS = ("NO_TRADE",)
NO_CHASE_REASON_CODES = (
    "NO_CHASE_ATR_MISSING",
    "NO_CHASE_WITHIN_ENTRY_ZONE",
    "NO_CHASE_DISTANCE_ACCEPTABLE",
    "NO_CHASE_VIOLATION",
)
DEFAULT_NO_CHASE_DISTANCE_MODE = "atr"
DEFAULT_NO_CHASE_MAX_DISTANCE_ATR = Decimal("0.50")
DEFAULT_NO_CHASE_MAX_DISTANCE_FRACTION = Decimal("0.02")


@dataclass(frozen=True)
class NoChaseResult:
    feature_id: str
    evaluated_at: datetime
    direction: str
    entry_zone: LevelCluster
    current_price: Decimal
    current_price_available_at: datetime
    distance_mode: str
    max_distance_atr: Decimal
    max_distance_fraction: Decimal
    chase_boundary: Decimal
    chase_distance_price: Decimal
    normalized_distance: Decimal | None
    atr: Decimal | None
    atr_available_at: datetime | None
    violated: bool
    blocked: bool
    effects: tuple[str, ...]
    complete: bool
    config_metadata: dict[str, str]
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        return self.reason_codes[0] if self.reason_codes else None

    def as_record(self) -> dict[str, Any]:
        evaluated_at = require_utc_datetime(self.evaluated_at, "evaluated_at")
        price_time = require_utc_datetime(
            self.current_price_available_at,
            "current_price_available_at",
        )
        _validate_cluster(self.entry_zone, direction=self.direction)
        zone_record = self.entry_zone.as_record()
        atr_time = _optional_utc(self.atr_available_at, "atr_available_at")
        _validate_result(
            self,
            evaluated_at=evaluated_at,
            price_time=price_time,
            atr_time=atr_time,
        )
        return {
            "feature_id": self.feature_id,
            "evaluated_at": evaluated_at.isoformat(),
            "direction": self.direction,
            "entry_zone": zone_record,
            "current_price": str(self.current_price),
            "current_price_available_at": price_time.isoformat(),
            "distance_mode": self.distance_mode,
            "max_distance_atr": str(self.max_distance_atr),
            "max_distance_fraction": str(self.max_distance_fraction),
            "chase_boundary": str(self.chase_boundary),
            "chase_distance_price": str(self.chase_distance_price),
            "normalized_distance": _decimal_record(self.normalized_distance),
            "atr": _decimal_record(self.atr),
            "atr_available_at": _datetime_record(atr_time),
            "violated": self.violated,
            "blocked": self.blocked,
            "effects": list(self.effects),
            "complete": self.complete,
            "config_metadata": _config_metadata(self.config_metadata),
            "reason_codes": list(self.reason_codes),
        }


def apply_no_chase_filter(
    entry_zone: LevelCluster,
    *,
    current_price: Any,
    current_price_available_at: datetime,
    as_of: datetime,
    direction: str = "long",
    distance_mode: str = DEFAULT_NO_CHASE_DISTANCE_MODE,
    max_distance_atr: Any = DEFAULT_NO_CHASE_MAX_DISTANCE_ATR,
    max_distance_fraction: Any = DEFAULT_NO_CHASE_MAX_DISTANCE_FRACTION,
    atr: Any | None = None,
    atr_available_at: datetime | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> NoChaseResult:
    """Block entries chased materially beyond a BTC-095 cluster boundary."""

    evaluated_at = require_utc_datetime(as_of, "as_of")
    _validate_direction(direction)
    _validate_cluster(entry_zone, direction=direction)
    if entry_zone.detected_at > evaluated_at:
        raise ValueError("entry_zone must be available by as_of")
    price = _positive_decimal(current_price, "current_price")
    price_time = require_utc_datetime(
        current_price_available_at,
        "current_price_available_at",
    )
    if not entry_zone.detected_at <= price_time <= evaluated_at:
        raise ValueError(
            "current_price_available_at must be between zone detection and as_of"
        )
    mode = _distance_mode(distance_mode)
    atr_limit = _positive_decimal(max_distance_atr, "max_distance_atr")
    fraction_limit = _positive_fraction(
        max_distance_fraction,
        "max_distance_fraction",
    )
    boundary = (
        entry_zone.upper_bound if direction == "long" else entry_zone.lower_bound
    )
    chased = (
        decision_greater(price, boundary)
        if direction == "long"
        else decision_greater(boundary, price)
    )
    distance_price = (
        _quant_distance(price, boundary) if chased else Decimal("0")
    )
    metadata = dict(config_metadata or {})

    if mode == "fractional":
        if atr is not None or atr_available_at is not None:
            raise ValueError("ATR inputs are only valid in atr distance mode")
        normalized = _fractional_distance(distance_price, price)
        return _result(
            entry_zone,
            evaluated_at=evaluated_at,
            direction=direction,
            current_price=price,
            price_time=price_time,
            mode=mode,
            atr_limit=atr_limit,
            fraction_limit=fraction_limit,
            boundary=boundary,
            distance_price=distance_price,
            normalized=normalized,
            atr=None,
            atr_time=None,
            config_metadata=metadata,
        )

    if atr is None and atr_available_at is None:
        return _result(
            entry_zone,
            evaluated_at=evaluated_at,
            direction=direction,
            current_price=price,
            price_time=price_time,
            mode=mode,
            atr_limit=atr_limit,
            fraction_limit=fraction_limit,
            boundary=boundary,
            distance_price=distance_price,
            normalized=Decimal("0") if not chased else None,
            atr=None,
            atr_time=None,
            config_metadata=metadata,
        )
    if atr is None or atr_available_at is None:
        raise ValueError("atr and atr_available_at must be supplied together")
    atr_value = _positive_decimal(atr, "atr")
    atr_time = require_utc_datetime(atr_available_at, "atr_available_at")
    if atr_time > price_time:
        raise ValueError("atr must be available by current price time")
    normalized = (
        _atr_distance(price, boundary, atr_value) if chased else Decimal("0")
    )
    return _result(
        entry_zone,
        evaluated_at=evaluated_at,
        direction=direction,
        current_price=price,
        price_time=price_time,
        mode=mode,
        atr_limit=atr_limit,
        fraction_limit=fraction_limit,
        boundary=boundary,
        distance_price=distance_price,
        normalized=normalized,
        atr=atr_value,
        atr_time=atr_time,
        config_metadata=metadata,
    )


def _result(
    entry_zone: LevelCluster,
    *,
    evaluated_at: datetime,
    direction: str,
    current_price: Decimal,
    price_time: datetime,
    mode: str,
    atr_limit: Decimal,
    fraction_limit: Decimal,
    boundary: Decimal,
    distance_price: Decimal,
    normalized: Decimal | None,
    atr: Decimal | None,
    atr_time: datetime | None,
    config_metadata: dict[str, str],
) -> NoChaseResult:
    if normalized is None:
        reason_code = "NO_CHASE_ATR_MISSING"
        complete = False
        violated = False
        blocked = True
    else:
        active_limit = atr_limit if mode == "atr" else fraction_limit
        violated = decision_greater(normalized, active_limit)
        complete = True
        blocked = violated
        if violated:
            reason_code = "NO_CHASE_VIOLATION"
        elif distance_price == 0:
            reason_code = "NO_CHASE_WITHIN_ENTRY_ZONE"
        else:
            reason_code = "NO_CHASE_DISTANCE_ACCEPTABLE"
    result = NoChaseResult(
        feature_id=NO_CHASE_FEATURE_ID,
        evaluated_at=evaluated_at,
        direction=direction,
        entry_zone=entry_zone,
        current_price=current_price,
        current_price_available_at=price_time,
        distance_mode=mode,
        max_distance_atr=atr_limit,
        max_distance_fraction=fraction_limit,
        chase_boundary=boundary,
        chase_distance_price=distance_price,
        normalized_distance=normalized,
        atr=atr,
        atr_available_at=atr_time,
        violated=violated,
        blocked=blocked,
        effects=NO_CHASE_EFFECTS if blocked else (),
        complete=complete,
        config_metadata=config_metadata,
        reason_codes=(reason_code,),
    )
    result.as_record()
    return result


def _validate_result(
    result: NoChaseResult,
    *,
    evaluated_at: datetime,
    price_time: datetime,
    atr_time: datetime | None,
) -> None:
    if result.feature_id != NO_CHASE_FEATURE_ID:
        raise ValueError("feature_id must be NO_CHASE_FILTER")
    _validate_direction(result.direction)
    mode = _distance_mode(result.distance_mode)
    atr_limit = _positive_decimal(result.max_distance_atr, "max_distance_atr")
    fraction_limit = _positive_fraction(
        result.max_distance_fraction,
        "max_distance_fraction",
    )
    price = _positive_decimal(result.current_price, "current_price")
    expected_boundary = (
        result.entry_zone.upper_bound
        if result.direction == "long"
        else result.entry_zone.lower_bound
    )
    if result.chase_boundary != expected_boundary:
        raise ValueError("chase_boundary must match directional entry-zone boundary")
    if not result.entry_zone.detected_at <= price_time <= evaluated_at:
        raise ValueError("current price time must respect zone and evaluation times")
    chased = (
        decision_greater(price, expected_boundary)
        if result.direction == "long"
        else decision_greater(expected_boundary, price)
    )
    expected_price_distance = (
        _quant_distance(price, expected_boundary) if chased else Decimal("0")
    )
    if result.chase_distance_price != expected_price_distance:
        raise ValueError("chase_distance_price must match BTC-045 distance")
    if not result.reason_codes or len(result.reason_codes) != 1:
        raise ValueError("exactly one no-chase reason code is required")
    if result.reason_code not in NO_CHASE_REASON_CODES:
        raise ValueError("unsupported no-chase reason code")

    if mode == "fractional":
        if any(value is not None for value in (result.atr, atr_time)):
            raise ValueError("fractional mode cannot contain ATR provenance")
        expected_normalized = _fractional_distance(
            expected_price_distance,
            price,
        )
    elif result.atr is None:
        if atr_time is not None:
            raise ValueError("missing ATR result cannot contain ATR provenance")
        expected_normalized = Decimal("0") if not chased else None
    else:
        atr = _positive_decimal(result.atr, "atr")
        if atr_time is None or atr_time > price_time:
            raise ValueError("ATR provenance must be available by current price")
        expected_normalized = (
            _atr_distance(price, expected_boundary, atr)
            if chased
            else Decimal("0")
        )
    if result.normalized_distance != expected_normalized:
        raise ValueError("normalized_distance must match configured distance mode")

    missing = expected_normalized is None
    active_limit = atr_limit if mode == "atr" else fraction_limit
    expected_violation = (
        False if missing else decision_greater(expected_normalized, active_limit)
    )
    expected_blocked = missing or expected_violation
    expected_reason = (
        "NO_CHASE_ATR_MISSING"
        if missing
        else "NO_CHASE_VIOLATION"
        if expected_violation
        else "NO_CHASE_WITHIN_ENTRY_ZONE"
        if expected_price_distance == 0
        else "NO_CHASE_DISTANCE_ACCEPTABLE"
    )
    if result.violated != expected_violation:
        raise ValueError("violated must match normalized distance and threshold")
    if result.blocked != expected_blocked:
        raise ValueError("blocked must match missing-input or violation state")
    if result.complete == missing:
        raise ValueError("complete must be false only when ATR is missing")
    if result.effects != (NO_CHASE_EFFECTS if expected_blocked else ()):
        raise ValueError("effects must match blocked state")
    if result.reason_code != expected_reason:
        raise ValueError("reason code must match no-chase state")


def _validate_cluster(cluster: LevelCluster, *, direction: str) -> None:
    if not isinstance(cluster, LevelCluster):
        raise ValueError("entry_zone must be a BTC-095 LevelCluster")
    cluster.as_record()
    expected_zone_type = (
        LEVEL_CLUSTER_SUPPORT if direction == "long" else LEVEL_CLUSTER_RESISTANCE
    )
    if cluster.zone_type != expected_zone_type:
        raise ValueError(
            f"{direction} no-chase filter requires {expected_zone_type} entry zone"
        )


def _validate_direction(direction: str) -> None:
    if direction not in NO_CHASE_DIRECTIONS:
        raise ValueError(f"direction must be one of {NO_CHASE_DIRECTIONS}")


def _distance_mode(mode: str) -> str:
    if mode not in NO_CHASE_DISTANCE_MODES:
        raise ValueError(f"distance_mode must be one of {NO_CHASE_DISTANCE_MODES}")
    return mode


def _quant_distance(first: Decimal, second: Decimal) -> Decimal:
    return Decimal(str(pairwise_price_distance(float(first), float(second))))


def _atr_distance(first: Decimal, second: Decimal, atr: Decimal) -> Decimal:
    return Decimal(
        str(
            atr_normalized_distance(
                float(first),
                float(second),
                float(atr),
            )
        )
    )


def _fractional_distance(distance: Decimal, current_price: Decimal) -> Decimal:
    return Decimal(str(float(distance) / float(current_price)))


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if result <= 0:
        raise ValueError(f"{name} must be > 0")
    return result


def _positive_fraction(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if not Decimal("0") < result <= Decimal("1"):
        raise ValueError(f"{name} must be > 0 and <= 1")
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
