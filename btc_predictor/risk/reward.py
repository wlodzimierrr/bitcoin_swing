"""Reward reference selection and the R/R filter (BTC-143).

Rulebook 15:

    RR = PotentialReward / RiskToInvalidation

``PotentialReward`` is measured to the nearest credible structural reference,
selected in strict priority order:

1. nearest major weekly/monthly resistance cluster
2. prior local swing high
3. prior range high
4. conservative measured move from the active setup

If no credible reference exists the filter fails. It never falls back to an
arbitrary target, and it never invents one from the stop distance.

The R/R produced here is a hard asymmetry filter. BTC-098 removed R/R from
Structure Score arithmetic precisely so it could stay independent, so this
module gates entry rather than contributing to any score.
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
from btc_predictor.risk.invalidation import (
    INVALIDATION_DIRECTIONS,
    LONG_DIRECTION,
    SHORT_DIRECTION,
)


REWARD_RISK_FEATURE_ID = "REWARD_RISK_FILTER"
REWARD_RISK_POLICY_VERSION = "REWARD_RISK_FILTER_V1"

# Rulebook 15 minimum, with the preferred band recorded for reporting.
DEFAULT_MINIMUM_REWARD_RISK = Decimal("2")
PREFERRED_REWARD_RISK_MIN = Decimal("2.5")
PREFERRED_REWARD_RISK_MAX = Decimal("3.0")
REWARD_RISK_PARAMETER_STATUS = "PROVISIONAL_RESEARCH_CALIBRATABLE"

# Timeframes that make a resistance cluster "major" for priority 1.
MAJOR_REWARD_TIMEFRAMES = ("1w", "1mo")

MAJOR_RESISTANCE_CLUSTER = "MAJOR_RESISTANCE_CLUSTER"
PRIOR_LOCAL_SWING_HIGH = "PRIOR_LOCAL_SWING_HIGH"
PRIOR_RANGE_HIGH = "PRIOR_RANGE_HIGH"
CONSERVATIVE_MEASURED_MOVE = "CONSERVATIVE_MEASURED_MOVE"
# Strict rulebook order. The first tier that yields a credible reference wins;
# a nearer reference from a lower tier never overrides a higher one.
REWARD_REFERENCE_PRIORITY = (
    MAJOR_RESISTANCE_CLUSTER,
    PRIOR_LOCAL_SWING_HIGH,
    PRIOR_RANGE_HIGH,
    CONSERVATIVE_MEASURED_MOVE,
)

REWARD_RISK_REASON_CODES = (
    "REWARD_RISK_PASS",
    "REWARD_RISK_BELOW_MINIMUM",
    "REWARD_RISK_NO_REWARD_REFERENCE",
    "REWARD_RISK_INPUT_MISSING",
    "REWARD_RISK_INVALID_RISK",
    "REWARD_RISK_PREFERRED_BAND",
)


@dataclass(frozen=True)
class RewardReference:
    """The structural level potential reward is measured to."""

    reference_type: str
    priority: int
    price: Decimal
    source_id: str | None = None
    timeframe: str | None = None
    detected_at: datetime | None = None

    def as_record(self) -> dict[str, Any]:
        return {
            "reference_type": self.reference_type,
            "priority": self.priority,
            "price": str(self.price),
            "source_id": self.source_id,
            "timeframe": self.timeframe,
            "detected_at": (
                require_utc_datetime(self.detected_at, "detected_at").isoformat()
                if self.detected_at is not None
                else None
            ),
        }


@dataclass(frozen=True)
class RewardRiskResult:
    feature_id: str
    policy_version: str
    direction: str
    entry_price: Decimal | None
    stop_price: Decimal | None
    reward_reference: RewardReference | None
    reward: Decimal | None
    risk: Decimal | None
    reward_risk: Decimal | None
    minimum_reward_risk: Decimal
    passes: bool
    considered_references: tuple[RewardReference, ...]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        if self.passes and self.reward_risk is None:
            raise ValueError("a passing R/R filter requires a ratio")
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "direction": self.direction,
            "entry_price": _optional(self.entry_price),
            "stop_price": _optional(self.stop_price),
            "reward_reference": (
                self.reward_reference.as_record()
                if self.reward_reference is not None
                else None
            ),
            "reward": _optional(self.reward),
            "risk": _optional(self.risk),
            "reward_risk": _optional(self.reward_risk),
            "minimum_reward_risk": str(self.minimum_reward_risk),
            "passes": self.passes,
            "considered_references": [
                item.as_record() for item in self.considered_references
            ],
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def select_reward_reference(
    *,
    entry_price: Any,
    direction: str = LONG_DIRECTION,
    resistance_clusters: Sequence[Any] = (),
    swing_highs: Sequence[Any] = (),
    range_highs: Sequence[Any] = (),
    measured_move: Any | None = None,
    as_of: datetime | None = None,
    major_timeframes: Sequence[str] = MAJOR_REWARD_TIMEFRAMES,
) -> tuple[RewardReference | None, tuple[RewardReference, ...]]:
    """Return the highest-priority credible reference and everything considered.

    A reference is credible only if it lies beyond entry in the reward
    direction. Within a tier the nearest such reference is taken; across tiers
    the rulebook order is strict.
    """

    if direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    entry = _positive_decimal(entry_price, "entry_price")
    signal_time = (
        require_utc_datetime(as_of, "as_of") if as_of is not None else None
    )

    tiers: dict[str, list[RewardReference]] = {
        MAJOR_RESISTANCE_CLUSTER: _cluster_references(
            resistance_clusters,
            direction=direction,
            major_timeframes=tuple(major_timeframes),
            signal_time=signal_time,
        ),
        PRIOR_LOCAL_SWING_HIGH: _level_references(
            swing_highs,
            reference_type=PRIOR_LOCAL_SWING_HIGH,
            priority=2,
            signal_time=signal_time,
        ),
        PRIOR_RANGE_HIGH: _level_references(
            range_highs,
            reference_type=PRIOR_RANGE_HIGH,
            priority=3,
            signal_time=signal_time,
        ),
        CONSERVATIVE_MEASURED_MOVE: (
            _level_references(
                [measured_move],
                reference_type=CONSERVATIVE_MEASURED_MOVE,
                priority=4,
                signal_time=signal_time,
            )
            if measured_move is not None
            else []
        ),
    }

    considered: list[RewardReference] = []
    selected: RewardReference | None = None
    for reference_type in REWARD_REFERENCE_PRIORITY:
        credible = sorted(
            (
                item
                for item in tiers[reference_type]
                if _is_beyond_entry(item.price, entry, direction)
            ),
            key=lambda item: (
                abs(item.price - entry),
                item.source_id or "",
            ),
        )
        considered.extend(tiers[reference_type])
        if selected is None and credible:
            selected = credible[0]
    return selected, tuple(considered)


def evaluate_reward_risk(
    *,
    entry_price: Any | None,
    stop_price: Any | None,
    direction: str = LONG_DIRECTION,
    reward_reference: RewardReference | None = None,
    considered_references: Sequence[RewardReference] = (),
    minimum_reward_risk: Any = DEFAULT_MINIMUM_REWARD_RISK,
    config_metadata: Mapping[str, str] | None = None,
) -> RewardRiskResult:
    """Apply the hard ``RR >= minimum`` asymmetry filter.

    Missing structure is a filter failure, not a pass and not a neutral
    outcome: without a credible reward reference there is no evidence of
    asymmetry, so the trade is not permitted.
    """

    if direction not in INVALIDATION_DIRECTIONS:
        raise ValueError(f"direction must be one of {INVALIDATION_DIRECTIONS}")
    minimum = _positive_decimal(minimum_reward_risk, "minimum_reward_risk")
    metadata = dict(config_metadata or {})
    considered = tuple(considered_references)
    entry = (
        _positive_decimal(entry_price, "entry_price")
        if entry_price is not None
        else None
    )
    stop = (
        _positive_decimal(stop_price, "stop_price")
        if stop_price is not None
        else None
    )

    if entry is None or stop is None:
        return _failed(
            direction=direction,
            entry=entry,
            stop=stop,
            reference=reward_reference,
            considered=considered,
            minimum=minimum,
            metadata=metadata,
            reason_codes=("REWARD_RISK_INPUT_MISSING",),
            complete=False,
        )

    if reward_reference is None:
        return _failed(
            direction=direction,
            entry=entry,
            stop=stop,
            reference=None,
            considered=considered,
            minimum=minimum,
            metadata=metadata,
            reason_codes=("REWARD_RISK_NO_REWARD_REFERENCE",),
            complete=True,
        )

    risk = entry - stop if direction == LONG_DIRECTION else stop - entry
    reward = (
        reward_reference.price - entry
        if direction == LONG_DIRECTION
        else entry - reward_reference.price
    )
    if decision_less_equal(risk, 0) or decision_less_equal(reward, 0):
        return _failed(
            direction=direction,
            entry=entry,
            stop=stop,
            reference=reward_reference,
            considered=considered,
            minimum=minimum,
            metadata=metadata,
            reason_codes=("REWARD_RISK_INVALID_RISK",),
            complete=True,
            reward=reward,
            risk=risk,
        )

    ratio = reward / risk
    passes = decision_greater_equal(ratio, minimum)
    reason_codes = ["REWARD_RISK_PASS" if passes else "REWARD_RISK_BELOW_MINIMUM"]
    if passes and decision_greater_equal(
        ratio, PREFERRED_REWARD_RISK_MIN
    ) and decision_less_equal(ratio, PREFERRED_REWARD_RISK_MAX):
        reason_codes.append("REWARD_RISK_PREFERRED_BAND")

    return RewardRiskResult(
        feature_id=REWARD_RISK_FEATURE_ID,
        policy_version=REWARD_RISK_POLICY_VERSION,
        direction=direction,
        entry_price=entry,
        stop_price=stop,
        reward_reference=reward_reference,
        reward=reward,
        risk=risk,
        reward_risk=ratio,
        minimum_reward_risk=minimum,
        passes=passes,
        considered_references=considered,
        config_metadata=metadata,
        complete=True,
        reason_codes=tuple(reason_codes),
    )


def reward_risk_for_stop(
    stop: Any,
    *,
    resistance_clusters: Sequence[Any] = (),
    swing_highs: Sequence[Any] = (),
    range_highs: Sequence[Any] = (),
    measured_move: Any | None = None,
    as_of: datetime | None = None,
    minimum_reward_risk: Any = DEFAULT_MINIMUM_REWARD_RISK,
    config_metadata: Mapping[str, str] | None = None,
) -> RewardRiskResult:
    """Canonical path: filter a BTC-142 stop against structural reward.

    Entry, stop and direction all come from the BTC-142 result so the trade
    geometry cannot be restated inconsistently.
    """

    record = _as_record(stop, "stop")
    direction = record.get("direction") or LONG_DIRECTION
    entry = record.get("entry_price")
    stop_price = record.get("stop_price")
    metadata = dict(config_metadata or {})

    if not record.get("complete") or entry is None or stop_price is None:
        return _failed(
            direction=direction if direction in INVALIDATION_DIRECTIONS else "",
            entry=None,
            stop=None,
            reference=None,
            considered=(),
            minimum=_positive_decimal(minimum_reward_risk, "minimum_reward_risk"),
            metadata=metadata,
            reason_codes=("REWARD_RISK_INPUT_MISSING",),
            complete=False,
        )

    reference, considered = select_reward_reference(
        entry_price=entry,
        direction=direction,
        resistance_clusters=resistance_clusters,
        swing_highs=swing_highs,
        range_highs=range_highs,
        measured_move=measured_move,
        as_of=as_of,
    )
    return evaluate_reward_risk(
        entry_price=entry,
        stop_price=stop_price,
        direction=direction,
        reward_reference=reference,
        considered_references=considered,
        minimum_reward_risk=minimum_reward_risk,
        config_metadata=metadata,
    )


def _cluster_references(
    clusters: Sequence[Any],
    *,
    direction: str,
    major_timeframes: tuple[str, ...],
    signal_time: datetime | None,
) -> list[RewardReference]:
    required_zone = "resistance" if direction == LONG_DIRECTION else "support"
    references = []
    for cluster in clusters:
        record = _as_record(cluster, "resistance_cluster")
        if record.get("zone_type") != required_zone:
            continue
        detected_at = _optional_utc(record.get("detected_at"))
        if signal_time is not None and detected_at is not None and (
            detected_at > signal_time
        ):
            continue
        timeframes = _cluster_timeframes(record)
        if major_timeframes and not (set(timeframes) & set(major_timeframes)):
            continue
        # Reward is measured to the near edge of the zone, the first price at
        # which the level begins to matter.
        price = _positive_decimal(
            record["lower_bound"]
            if direction == LONG_DIRECTION
            else record["upper_bound"],
            "cluster_bound",
        )
        references.append(
            RewardReference(
                reference_type=MAJOR_RESISTANCE_CLUSTER,
                priority=1,
                price=price,
                source_id=record.get("cluster_id"),
                timeframe=",".join(sorted(set(timeframes))) or None,
                detected_at=detected_at,
            )
        )
    return references


def _level_references(
    levels: Sequence[Any],
    *,
    reference_type: str,
    priority: int,
    signal_time: datetime | None,
) -> list[RewardReference]:
    references = []
    for level in levels:
        if level is None:
            continue
        if isinstance(level, Mapping) or hasattr(level, "as_record"):
            record = _as_record(level, reference_type)
            price = _positive_decimal(
                record.get("price", record.get("level_price")),
                reference_type,
            )
            detected_at = _optional_utc(record.get("detected_at"))
            source_id = record.get("source_id") or record.get("level_id")
            timeframe = record.get("timeframe") or record.get("source_timeframe")
        else:
            price = _positive_decimal(level, reference_type)
            detected_at = None
            source_id = None
            timeframe = None
        if signal_time is not None and detected_at is not None and (
            detected_at > signal_time
        ):
            continue
        references.append(
            RewardReference(
                reference_type=reference_type,
                priority=priority,
                price=price,
                source_id=source_id,
                timeframe=timeframe,
                detected_at=detected_at,
            )
        )
    return references


def _cluster_timeframes(record: Mapping[str, Any]) -> tuple[str, ...]:
    members = record.get("members") or ()
    timeframes = []
    for member in members:
        member_record = member if isinstance(member, Mapping) else _as_record(
            member,
            "cluster_member",
        )
        timeframe = member_record.get("source_timeframe")
        if timeframe:
            timeframes.append(str(timeframe))
    return tuple(timeframes)


def _is_beyond_entry(price: Decimal, entry: Decimal, direction: str) -> bool:
    if direction == LONG_DIRECTION:
        return decision_greater(price, entry)
    return decision_less(price, entry)


def _failed(
    *,
    direction: str,
    entry: Decimal | None,
    stop: Decimal | None,
    reference: RewardReference | None,
    considered: tuple[RewardReference, ...],
    minimum: Decimal,
    metadata: dict[str, str],
    reason_codes: tuple[str, ...],
    complete: bool,
    reward: Decimal | None = None,
    risk: Decimal | None = None,
) -> RewardRiskResult:
    return RewardRiskResult(
        feature_id=REWARD_RISK_FEATURE_ID,
        policy_version=REWARD_RISK_POLICY_VERSION,
        direction=direction,
        entry_price=entry,
        stop_price=stop,
        reward_reference=reference,
        reward=reward,
        risk=risk,
        reward_risk=None,
        minimum_reward_risk=minimum,
        passes=False,
        considered_references=considered,
        config_metadata=metadata,
        complete=complete,
        reason_codes=reason_codes,
    )


def _as_record(source: Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    as_record = getattr(source, "as_record", None)
    if callable(as_record):
        return as_record()
    raise TypeError(f"{name} must be a mapping or expose as_record()")


def _optional_utc(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return require_utc_datetime(value, "detected_at")
    parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    return require_utc_datetime(parsed, "detected_at")


def _optional(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _positive_decimal(value: Any, name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except Exception as error:  # noqa: BLE001 - surfaced as a domain error
        raise ValueError(f"{name} must be numeric") from error
    if decision_less_equal(result, 0):
        raise ValueError(f"{name} must be positive")
    return result


__all__ = [
    "CONSERVATIVE_MEASURED_MOVE",
    "DEFAULT_MINIMUM_REWARD_RISK",
    "MAJOR_RESISTANCE_CLUSTER",
    "MAJOR_REWARD_TIMEFRAMES",
    "PREFERRED_REWARD_RISK_MAX",
    "PREFERRED_REWARD_RISK_MIN",
    "PRIOR_LOCAL_SWING_HIGH",
    "PRIOR_RANGE_HIGH",
    "REWARD_REFERENCE_PRIORITY",
    "REWARD_RISK_FEATURE_ID",
    "REWARD_RISK_PARAMETER_STATUS",
    "REWARD_RISK_POLICY_VERSION",
    "REWARD_RISK_REASON_CODES",
    "RewardReference",
    "RewardRiskResult",
    "evaluate_reward_risk",
    "reward_risk_for_stop",
    "select_reward_reference",
]
