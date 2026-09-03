"""Structural invalidation level selection (BTC-140).

Selects the price level whose breach would invalidate the active setup's
thesis. This is deliberately the *level only*: the volatility buffer is
BTC-141 and the resulting stop is BTC-142. Rulebook 16.1 composes them as
``Stop = StructuralInvalidation -/+ VolatilityBuffer``.

Selection principles, from rulebook 16.2:

- stops are based on **zones**, not exact lines, so the invalidation price is
  the far edge of the selected zone rather than its centre;
- the invalidation must represent **thesis** failure, so the candidate
  preference is setup-specific;
- the structural timeframe should match the trade timeframe, so candidate
  quality is filtered on cluster confluence rather than proximity alone.

Avoiding placement immediately beyond obvious public levels is the buffer's
job in BTC-141 and is not applied here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any

from btc_predictor.data import require_utc_datetime
from btc_predictor.quant.comparisons import (
    decision_greater,
    decision_greater_equal,
    decision_less,
    decision_less_equal,
)


STRUCTURAL_INVALIDATION_FEATURE_ID = "STRUCTURAL_INVALIDATION"
STRUCTURAL_INVALIDATION_POLICY_VERSION = "STRUCTURAL_INVALIDATION_V1"

LONG_DIRECTION = "long"
SHORT_DIRECTION = "short"
INVALIDATION_DIRECTIONS = (LONG_DIRECTION, SHORT_DIRECTION)

BULL_TREND_CONTINUATION_SETUP = "BULL_TREND_CONTINUATION"
BULLISH_RESET_SETUP = "BULLISH_RESET"
CAPITULATION_REVERSAL_SETUP = "CAPITULATION_REVERSAL"
BEARISH_DISTRIBUTION_SETUP = "BEARISH_DISTRIBUTION"

# How a setup's thesis fails determines which qualifying zone is selected.
# NEAREST: the tightest zone whose breach already refutes the thesis.
# FARTHEST: a wide "Stage 1 thesis stop" (rulebook 22), used where the setup is
# explicitly buying a washout and nearby structure is expected to be probed.
SELECTION_NEAREST = "NEAREST_QUALIFYING_ZONE"
SELECTION_FARTHEST = "FARTHEST_QUALIFYING_ZONE"
INVALIDATION_SELECTION_MODES = (SELECTION_NEAREST, SELECTION_FARTHEST)

SETUP_INVALIDATION_POLICY = {
    BULL_TREND_CONTINUATION_SETUP: (LONG_DIRECTION, SELECTION_NEAREST),
    BULLISH_RESET_SETUP: (LONG_DIRECTION, SELECTION_NEAREST),
    CAPITULATION_REVERSAL_SETUP: (LONG_DIRECTION, SELECTION_FARTHEST),
    BEARISH_DISTRIBUTION_SETUP: (SHORT_DIRECTION, SELECTION_NEAREST),
}

STRUCTURAL_INVALIDATION_REASON_CODES = (
    "STRUCTURAL_INVALIDATION_SELECTED",
    "STRUCTURAL_INVALIDATION_INPUT_MISSING",
    "STRUCTURAL_INVALIDATION_UNSUPPORTED_SETUP",
    "STRUCTURAL_INVALIDATION_NO_CANDIDATE",
    "STRUCTURAL_INVALIDATION_WRONG_SIDE",
    "STRUCTURAL_INVALIDATION_BEYOND_MAX_DISTANCE",
    "STRUCTURAL_INVALIDATION_BELOW_MIN_CONFLUENCE",
    "STRUCTURAL_INVALIDATION_NOT_YET_DETECTED",
)

# PROVISIONAL deterministic Phase-1 parameters, research-calibratable by
# BTC-185. They bound how far structure may sit from entry and how much
# confluence a zone needs before it can carry a thesis stop.
DEFAULT_MAX_INVALIDATION_DISTANCE_FRACTION = Decimal("0.15")
DEFAULT_MIN_CLUSTER_CONFLUENCE = Decimal("50")
DEFAULT_MIN_CLUSTER_MEMBER_COUNT = 2
INVALIDATION_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"


@dataclass(frozen=True)
class InvalidationCandidate:
    """One structural zone considered as an invalidation level."""

    cluster_id: str
    zone_type: str
    lower_bound: Decimal
    upper_bound: Decimal
    center_price: Decimal
    confluence_score: Decimal
    member_count: int
    detected_at: datetime
    invalidation_price: Decimal
    distance_fraction: Decimal
    eligible: bool
    rejection_reason: str | None
    atr_distance: Decimal | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "cluster_id": self.cluster_id,
            "zone_type": self.zone_type,
            "lower_bound": str(self.lower_bound),
            "upper_bound": str(self.upper_bound),
            "center_price": str(self.center_price),
            "confluence_score": str(self.confluence_score),
            "member_count": self.member_count,
            "detected_at": require_utc_datetime(
                self.detected_at,
                "detected_at",
            ).isoformat(),
            "invalidation_price": str(self.invalidation_price),
            "distance_fraction": str(self.distance_fraction),
            "atr_distance": (
                str(self.atr_distance) if self.atr_distance is not None else None
            ),
            "eligible": self.eligible,
            "rejection_reason": self.rejection_reason,
        }


@dataclass(frozen=True)
class StructuralInvalidationResult:
    feature_id: str
    policy_version: str
    setup: str
    direction: str
    selection_mode: str
    entry_price: Decimal
    invalidation_price: Decimal | None
    selected_cluster_id: str | None
    selected_zone_lower_bound: Decimal | None
    selected_zone_upper_bound: Decimal | None
    distance_fraction: Decimal | None
    atr_distance: Decimal | None
    thresholds: dict[str, Decimal]
    candidates: tuple[InvalidationCandidate, ...]
    config_metadata: dict[str, str]
    complete: bool
    as_of: datetime | None = None
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        if self.complete and self.invalidation_price is None:
            raise ValueError("complete invalidation requires a price")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "setup": self.setup,
            "direction": self.direction,
            "selection_mode": self.selection_mode,
            "entry_price": str(self.entry_price),
            "invalidation_price": (
                str(self.invalidation_price)
                if self.invalidation_price is not None
                else None
            ),
            "selected_cluster_id": self.selected_cluster_id,
            "selected_zone_lower_bound": (
                str(self.selected_zone_lower_bound)
                if self.selected_zone_lower_bound is not None
                else None
            ),
            "selected_zone_upper_bound": (
                str(self.selected_zone_upper_bound)
                if self.selected_zone_upper_bound is not None
                else None
            ),
            "distance_fraction": (
                str(self.distance_fraction)
                if self.distance_fraction is not None
                else None
            ),
            "atr_distance": (
                str(self.atr_distance) if self.atr_distance is not None else None
            ),
            "thresholds": {
                key: str(value) for key, value in self.thresholds.items()
            },
            "candidates": [item.as_record() for item in self.candidates],
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
            # The decision time every candidate's detected_at was filtered
            # against. A selection whose record omits it cannot later be
            # re-checked for point-in-time correctness.
            "as_of": (
                require_utc_datetime(self.as_of, "as_of").isoformat()
                if self.as_of is not None
                else None
            ),
        }


def select_structural_invalidation(
    clusters: Any,
    *,
    setup: str,
    entry_price: Any,
    as_of: datetime,
    atr: Any | None = None,
    max_distance_fraction: Any = DEFAULT_MAX_INVALIDATION_DISTANCE_FRACTION,
    min_confluence: Any = DEFAULT_MIN_CLUSTER_CONFLUENCE,
    min_member_count: int = DEFAULT_MIN_CLUSTER_MEMBER_COUNT,
    config_metadata: Mapping[str, str] | None = None,
) -> StructuralInvalidationResult:
    """Select the invalidation level for an active setup from nearby structure.

    Every zone on the trade's own side -- support for a long, resistance for a
    short -- is retained in ``candidates`` with an explicit eligibility
    verdict, so a selection is always reconstructable from the persisted
    record. A zone of the opposite type could never invalidate this thesis and
    is not a candidate at all.

    ``as_of`` is persisted alongside the candidates so a stored selection can
    later be re-checked against the availability rule it was made under.
    """

    signal_time = require_utc_datetime(as_of, "as_of")
    entry = _positive_decimal(entry_price, "entry_price")
    thresholds = _thresholds(
        max_distance_fraction=max_distance_fraction,
        min_confluence=min_confluence,
        min_member_count=min_member_count,
    )
    metadata = dict(config_metadata or {})

    if setup not in SETUP_INVALIDATION_POLICY:
        return _empty_result(
            setup=setup,
            direction="",
            selection_mode="",
            entry=entry,
            thresholds=thresholds,
            metadata=metadata,
            as_of=signal_time,
            reason_codes=("STRUCTURAL_INVALIDATION_UNSUPPORTED_SETUP",),
        )
    direction, selection_mode = SETUP_INVALIDATION_POLICY[setup]
    atr_value = _positive_decimal(atr, "atr") if atr is not None else None

    records = _cluster_records(clusters)
    if not records:
        return _empty_result(
            setup=setup,
            direction=direction,
            selection_mode=selection_mode,
            entry=entry,
            thresholds=thresholds,
            metadata=metadata,
            as_of=signal_time,
            reason_codes=("STRUCTURAL_INVALIDATION_INPUT_MISSING",),
        )

    required_zone = "support" if direction == LONG_DIRECTION else "resistance"
    candidates = []
    for record in records:
        candidate = _evaluate_candidate(
            record,
            direction=direction,
            required_zone=required_zone,
            entry=entry,
            signal_time=signal_time,
            atr_value=atr_value,
            thresholds=thresholds,
        )
        if candidate is not None:
            candidates.append(candidate)

    ordered = tuple(
        sorted(
            candidates,
            key=lambda item: (item.distance_fraction, item.cluster_id),
        )
    )
    eligible = [item for item in ordered if item.eligible]
    if not eligible:
        reasons = ["STRUCTURAL_INVALIDATION_NO_CANDIDATE"]
        # Surface why the closest rejected zones did not qualify.
        for item in ordered:
            if item.rejection_reason and item.rejection_reason not in reasons:
                reasons.append(item.rejection_reason)
        return _empty_result(
            setup=setup,
            direction=direction,
            selection_mode=selection_mode,
            entry=entry,
            thresholds=thresholds,
            metadata=metadata,
            as_of=signal_time,
            reason_codes=tuple(reasons),
            candidates=ordered,
        )

    selected = eligible[0] if selection_mode == SELECTION_NEAREST else eligible[-1]
    return StructuralInvalidationResult(
        feature_id=STRUCTURAL_INVALIDATION_FEATURE_ID,
        policy_version=STRUCTURAL_INVALIDATION_POLICY_VERSION,
        setup=setup,
        direction=direction,
        selection_mode=selection_mode,
        entry_price=entry,
        invalidation_price=selected.invalidation_price,
        selected_cluster_id=selected.cluster_id,
        selected_zone_lower_bound=selected.lower_bound,
        selected_zone_upper_bound=selected.upper_bound,
        distance_fraction=selected.distance_fraction,
        atr_distance=selected.atr_distance,
        thresholds=thresholds,
        candidates=ordered,
        config_metadata=metadata,
        complete=True,
        as_of=signal_time,
        reason_codes=("STRUCTURAL_INVALIDATION_SELECTED",),
    )


def _evaluate_candidate(
    record: Mapping[str, Any],
    *,
    direction: str,
    required_zone: str,
    entry: Decimal,
    signal_time: datetime,
    atr_value: Decimal | None,
    thresholds: Mapping[str, Decimal],
) -> InvalidationCandidate | None:
    zone_type = _required_string(record, "zone_type")
    if zone_type != required_zone:
        return None
    lower = _positive_decimal(record["lower_bound"], "lower_bound")
    upper = _positive_decimal(record["upper_bound"], "upper_bound")
    if decision_less(upper, lower):
        raise ValueError("cluster upper_bound must be >= lower_bound")
    center = _positive_decimal(record["center_price"], "center_price")
    confluence = _decimal(record.get("confluence_score", 0), "confluence_score")
    member_count = int(record.get("member_count", 0))
    detected_at = _parse_utc(record["detected_at"])

    # Zone-based stops sit beyond the zone, not at its centre.
    invalidation_price = lower if direction == LONG_DIRECTION else upper
    distance = (
        (entry - invalidation_price) / entry
        if direction == LONG_DIRECTION
        else (invalidation_price - entry) / entry
    )

    rejection: str | None = None
    if detected_at > signal_time:
        rejection = "STRUCTURAL_INVALIDATION_NOT_YET_DETECTED"
    elif direction == LONG_DIRECTION and decision_greater_equal(upper, entry):
        rejection = "STRUCTURAL_INVALIDATION_WRONG_SIDE"
    elif direction == SHORT_DIRECTION and decision_less_equal(lower, entry):
        rejection = "STRUCTURAL_INVALIDATION_WRONG_SIDE"
    elif decision_less_equal(distance, 0):
        rejection = "STRUCTURAL_INVALIDATION_WRONG_SIDE"
    elif decision_greater(distance, thresholds["max_distance_fraction"]):
        rejection = "STRUCTURAL_INVALIDATION_BEYOND_MAX_DISTANCE"
    elif decision_less(confluence, thresholds["min_confluence"]) or (
        member_count < int(thresholds["min_member_count"])
    ):
        rejection = "STRUCTURAL_INVALIDATION_BELOW_MIN_CONFLUENCE"

    return InvalidationCandidate(
        cluster_id=_required_string(record, "cluster_id"),
        zone_type=zone_type,
        lower_bound=lower,
        upper_bound=upper,
        center_price=center,
        confluence_score=confluence,
        member_count=member_count,
        detected_at=detected_at,
        invalidation_price=invalidation_price,
        distance_fraction=distance,
        atr_distance=(
            abs(entry - invalidation_price) / atr_value
            if atr_value is not None
            else None
        ),
        eligible=rejection is None,
        rejection_reason=rejection,
    )


def _empty_result(
    *,
    setup: str,
    direction: str,
    selection_mode: str,
    entry: Decimal,
    thresholds: dict[str, Decimal],
    metadata: dict[str, str],
    reason_codes: tuple[str, ...],
    as_of: datetime | None = None,
    candidates: tuple[InvalidationCandidate, ...] = (),
) -> StructuralInvalidationResult:
    return StructuralInvalidationResult(
        feature_id=STRUCTURAL_INVALIDATION_FEATURE_ID,
        policy_version=STRUCTURAL_INVALIDATION_POLICY_VERSION,
        setup=setup,
        direction=direction,
        selection_mode=selection_mode,
        entry_price=entry,
        invalidation_price=None,
        selected_cluster_id=None,
        selected_zone_lower_bound=None,
        selected_zone_upper_bound=None,
        distance_fraction=None,
        atr_distance=None,
        thresholds=thresholds,
        candidates=candidates,
        config_metadata=metadata,
        complete=False,
        as_of=as_of,
        reason_codes=reason_codes,
    )


def _thresholds(
    *,
    max_distance_fraction: Any,
    min_confluence: Any,
    min_member_count: int,
) -> dict[str, Decimal]:
    distance = _decimal(max_distance_fraction, "max_distance_fraction")
    if decision_less_equal(distance, 0):
        raise ValueError("max_distance_fraction must be positive")
    confluence = _decimal(min_confluence, "min_confluence")
    if decision_less(confluence, 0) or decision_greater(confluence, Decimal("100")):
        raise ValueError("min_confluence must be between 0 and 100")
    if int(min_member_count) < 1:
        raise ValueError("min_member_count must be >= 1")
    return {
        "max_distance_fraction": distance,
        "min_confluence": confluence,
        "min_member_count": Decimal(int(min_member_count)),
    }


def _cluster_records(clusters: Any) -> tuple[dict[str, Any], ...]:
    if clusters is None:
        return ()
    if isinstance(clusters, Mapping):
        if "clusters" in clusters:
            return _expand_cluster_container(clusters)
        return (_record(clusters),)
    if isinstance(clusters, Sequence) and not isinstance(clusters, str | bytes):
        return tuple(_record(item) for item in clusters)
    record = _record(clusters)
    if "clusters" in record:
        return _expand_cluster_container(record)
    return (record,)


def _record(source: Any) -> dict[str, Any]:
    if isinstance(source, Mapping):
        return dict(source)
    as_record = getattr(source, "as_record", None)
    if callable(as_record):
        return dict(as_record())
    raise TypeError("cluster must be a mapping or expose as_record()")


def _expand_cluster_container(record: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    """Unwrap a BTC-097 clustering *result* into its individual zones.

    The owner's ``LevelClusterResult`` is the natural thing to hand this
    function; only its ``as_record()`` mapping was previously understood, so
    passing the object itself failed on a missing ``zone_type``.
    """

    return tuple(_record(item) for item in record["clusters"])


def _required_string(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _decimal(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error
    # NaN and infinity are rejected here as named domain errors. Left to the
    # bare comparisons they surface as decimal.InvalidOperation, an
    # ArithmeticError carrying no field name, and NaN silently poisons every
    # downstream max/sum instead of refusing the input.
    if not result.is_finite():
        raise ValueError(f"{name} must be finite")
    return result


def _positive_decimal(value: Any, name: str) -> Decimal:
    result = _decimal(value, name)
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


def _parse_utc(value: Any) -> datetime:
    if isinstance(value, datetime):
        return require_utc_datetime(value, "detected_at")
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return require_utc_datetime(parsed, "detected_at")
