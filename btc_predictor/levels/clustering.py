"""Cluster nearby price levels into support and resistance zones."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from hashlib import sha1
from typing import Any

from btc_predictor.data import require_utc_datetime
from btc_predictor.quant.distances import atr_normalized_distance


LEVEL_CLUSTER_RESULT_FEATURE_ID = "LEVEL_CLUSTERS"
LEVEL_CLUSTER_FEATURE_ID = "LEVEL_CLUSTER"
LEVEL_CLUSTER_SUPPORT = "support"
LEVEL_CLUSTER_RESISTANCE = "resistance"
LEVEL_CLUSTER_ZONE_TYPES = (
    LEVEL_CLUSTER_SUPPORT,
    LEVEL_CLUSTER_RESISTANCE,
)
LEVEL_CLUSTER_REASON_CODES = (
    "LEVEL_CLUSTER_INPUT_MISSING",
    "LEVEL_CLUSTER_SOURCE_NOT_READY",
    "LEVEL_CLUSTER_INCOMPLETE_SOURCE_SKIPPED",
    "LEVEL_CLUSTER_DUPLICATE_MEMBER_SKIPPED",
    "LEVEL_CLUSTER_COMPLETE",
)
DEFAULT_LEVEL_CLUSTER_DISTANCE_FRACTION = Decimal("0.025")
DEFAULT_LEVEL_CLUSTER_ATR_DISTANCE_THRESHOLD = Decimal("0.50")
DEFAULT_LEVEL_CLUSTER_MINIMUM_STRENGTH = Decimal("60")
LEVEL_CLUSTER_TOUCH_BONUS_MAX = Decimal("10")


@dataclass(frozen=True)
class LevelClusterMember:
    member_id: str
    feature_id: str
    level_type: str
    price: Decimal
    detected_at: datetime
    exchange: str
    symbol: str
    provider: str
    source_timestamp: datetime | None = None
    source_timeframe: str | None = None
    source_record: dict[str, Any] | None = None

    def as_record(self) -> dict[str, Any]:
        detected_at = require_utc_datetime(self.detected_at, "detected_at")
        if not self.member_id.strip():
            raise ValueError("member_id must be non-empty")
        if not self.feature_id.strip():
            raise ValueError("feature_id must be non-empty")
        if not self.level_type.strip():
            raise ValueError("level_type must be non-empty")
        if self.price <= 0:
            raise ValueError("price must be > 0")
        source_timestamp = (
            require_utc_datetime(self.source_timestamp, "source_timestamp")
            if self.source_timestamp is not None
            else None
        )
        return {
            "member_id": self.member_id,
            "feature_id": self.feature_id,
            "level_type": self.level_type,
            "price": str(self.price),
            "detected_at": detected_at.isoformat(),
            "exchange": self.exchange,
            "symbol": self.symbol,
            "provider": self.provider,
            "source_timestamp": (
                source_timestamp.isoformat() if source_timestamp is not None else None
            ),
            "source_timeframe": self.source_timeframe,
            "source_record": dict(self.source_record or {}),
        }


@dataclass(frozen=True)
class LevelCluster:
    feature_id: str
    cluster_id: str
    zone_type: str
    lower_bound: Decimal
    upper_bound: Decimal
    center_price: Decimal
    reference_price: Decimal
    detected_at: datetime
    cluster_distance_fraction: Decimal
    minimum_level_strength: Decimal
    confluence_score: Decimal
    member_count: int
    unique_source_count: int
    unique_timeframe_count: int
    members: tuple[LevelClusterMember, ...]
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        detected_at = require_utc_datetime(self.detected_at, "detected_at")
        if self.feature_id != LEVEL_CLUSTER_FEATURE_ID:
            raise ValueError("feature_id must be LEVEL_CLUSTER")
        if not self.cluster_id.strip():
            raise ValueError("cluster_id must be non-empty")
        if self.zone_type not in LEVEL_CLUSTER_ZONE_TYPES:
            raise ValueError(f"zone_type must be one of {LEVEL_CLUSTER_ZONE_TYPES}")
        if self.lower_bound <= 0:
            raise ValueError("lower_bound must be > 0")
        if self.upper_bound < self.lower_bound:
            raise ValueError("upper_bound must be >= lower_bound")
        if self.center_price <= 0:
            raise ValueError("center_price must be > 0")
        if self.reference_price <= 0:
            raise ValueError("reference_price must be > 0")
        _positive_fraction(
            self.cluster_distance_fraction,
            "cluster_distance_fraction",
        )
        _score(self.minimum_level_strength, "minimum_level_strength")
        _score(self.confluence_score, "confluence_score")
        if self.member_count != len(self.members):
            raise ValueError("member_count must match members")
        if self.member_count < 1:
            raise ValueError("member_count must be >= 1")
        if self.unique_source_count < 1:
            raise ValueError("unique_source_count must be >= 1")
        if self.unique_timeframe_count < 0:
            raise ValueError("unique_timeframe_count must be >= 0")
        return {
            "feature_id": self.feature_id,
            "cluster_id": self.cluster_id,
            "zone_type": self.zone_type,
            "lower_bound": str(self.lower_bound),
            "upper_bound": str(self.upper_bound),
            "center_price": str(self.center_price),
            "reference_price": str(self.reference_price),
            "detected_at": detected_at.isoformat(),
            "cluster_distance_fraction": str(self.cluster_distance_fraction),
            "minimum_level_strength": str(self.minimum_level_strength),
            "confluence_score": str(self.confluence_score),
            "member_count": self.member_count,
            "unique_source_count": self.unique_source_count,
            "unique_timeframe_count": self.unique_timeframe_count,
            "members": [member.as_record() for member in self.members],
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class LevelClusterResult:
    feature_id: str
    as_of: datetime
    reference_price: Decimal
    cluster_distance_fraction: Decimal
    minimum_level_strength: Decimal
    clusters: tuple[LevelCluster, ...]
    source_level_count: int
    accepted_member_count: int
    skipped_future_count: int
    skipped_incomplete_count: int
    skipped_duplicate_count: int
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        as_of = require_utc_datetime(self.as_of, "as_of")
        if self.feature_id != LEVEL_CLUSTER_RESULT_FEATURE_ID:
            raise ValueError("feature_id must be LEVEL_CLUSTERS")
        if self.reference_price <= 0:
            raise ValueError("reference_price must be > 0")
        _positive_fraction(
            self.cluster_distance_fraction,
            "cluster_distance_fraction",
        )
        _score(self.minimum_level_strength, "minimum_level_strength")
        if self.source_level_count < 0:
            raise ValueError("source_level_count must be >= 0")
        if self.accepted_member_count < 0:
            raise ValueError("accepted_member_count must be >= 0")
        if self.skipped_future_count < 0:
            raise ValueError("skipped_future_count must be >= 0")
        if self.skipped_incomplete_count < 0:
            raise ValueError("skipped_incomplete_count must be >= 0")
        if self.skipped_duplicate_count < 0:
            raise ValueError("skipped_duplicate_count must be >= 0")
        if self.complete and not self.clusters:
            raise ValueError("complete level clustering requires clusters")
        return {
            "feature_id": self.feature_id,
            "as_of": as_of.isoformat(),
            "reference_price": str(self.reference_price),
            "cluster_distance_fraction": str(self.cluster_distance_fraction),
            "minimum_level_strength": str(self.minimum_level_strength),
            "clusters": [cluster.as_record() for cluster in self.clusters],
            "source_level_count": self.source_level_count,
            "accepted_member_count": self.accepted_member_count,
            "skipped_future_count": self.skipped_future_count,
            "skipped_incomplete_count": self.skipped_incomplete_count,
            "skipped_duplicate_count": self.skipped_duplicate_count,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class _PreparedMembers:
    source_level_count: int
    members: tuple[LevelClusterMember, ...]
    skipped_future_count: int
    skipped_incomplete_count: int
    skipped_duplicate_count: int


def cluster_price_levels(
    levels: Sequence[Any],
    *,
    as_of: datetime,
    reference_price: Any,
    cluster_distance_fraction: Any = DEFAULT_LEVEL_CLUSTER_DISTANCE_FRACTION,
    cluster_atr: Any | None = None,
    cluster_atr_distance_threshold: Any = DEFAULT_LEVEL_CLUSTER_ATR_DISTANCE_THRESHOLD,
    minimum_level_strength: Any = DEFAULT_LEVEL_CLUSTER_MINIMUM_STRENGTH,
) -> LevelClusterResult:
    """Cluster point-in-time known levels into support/resistance zones."""

    signal_time = require_utc_datetime(as_of, "as_of")
    reference = _positive_decimal(reference_price, "reference_price")
    distance_fraction = _positive_decimal_fraction(
        cluster_distance_fraction,
        "cluster_distance_fraction",
    )
    atr = (
        _positive_decimal(cluster_atr, "cluster_atr")
        if cluster_atr is not None
        else None
    )
    atr_distance_threshold = _positive_decimal(
        cluster_atr_distance_threshold,
        "cluster_atr_distance_threshold",
    )
    minimum_strength = _score(
        Decimal(str(minimum_level_strength)),
        "minimum_level_strength",
    )
    prepared = _prepare_members(levels, signal_time=signal_time)
    reason_codes = _result_reason_codes(prepared)
    if not prepared.members:
        if prepared.source_level_count == 0:
            reason_codes = (*reason_codes, "LEVEL_CLUSTER_INPUT_MISSING")
        return LevelClusterResult(
            feature_id=LEVEL_CLUSTER_RESULT_FEATURE_ID,
            as_of=signal_time,
            reference_price=reference,
            cluster_distance_fraction=distance_fraction,
            minimum_level_strength=minimum_strength,
            clusters=(),
            source_level_count=prepared.source_level_count,
            accepted_member_count=0,
            skipped_future_count=prepared.skipped_future_count,
            skipped_incomplete_count=prepared.skipped_incomplete_count,
            skipped_duplicate_count=prepared.skipped_duplicate_count,
            complete=False,
            reason_codes=reason_codes,
        )

    _single_market_identity(prepared.members)
    raw_clusters = _cluster_members(
        prepared.members,
        cluster_distance_fraction=distance_fraction,
        cluster_atr=atr,
        cluster_atr_distance_threshold=atr_distance_threshold,
    )
    clusters = tuple(
        sorted(
            (
                _build_cluster(
                    raw_cluster,
                    as_of=signal_time,
                    reference_price=reference,
                    cluster_distance_fraction=distance_fraction,
                    minimum_level_strength=minimum_strength,
                )
                for raw_cluster in raw_clusters
            ),
            key=lambda cluster: (cluster.zone_type, cluster.center_price),
        )
    )
    return LevelClusterResult(
        feature_id=LEVEL_CLUSTER_RESULT_FEATURE_ID,
        as_of=signal_time,
        reference_price=reference,
        cluster_distance_fraction=distance_fraction,
        minimum_level_strength=minimum_strength,
        clusters=clusters,
        source_level_count=prepared.source_level_count,
        accepted_member_count=len(prepared.members),
        skipped_future_count=prepared.skipped_future_count,
        skipped_incomplete_count=prepared.skipped_incomplete_count,
        skipped_duplicate_count=prepared.skipped_duplicate_count,
        complete=True,
        reason_codes=(*reason_codes, "LEVEL_CLUSTER_COMPLETE"),
    )


def _prepare_members(
    levels: Sequence[Any],
    *,
    signal_time: datetime,
) -> _PreparedMembers:
    source_records = tuple(_iter_source_records(levels))
    members: list[LevelClusterMember] = []
    seen_member_ids: set[str] = set()
    skipped_future_count = 0
    skipped_incomplete_count = 0
    skipped_duplicate_count = 0
    for source_record in source_records:
        if source_record.get("complete") is False:
            skipped_incomplete_count += 1
            continue
        member = _member_from_record(source_record)
        if member is None:
            skipped_incomplete_count += 1
            continue
        if member.detected_at > signal_time:
            skipped_future_count += 1
            continue
        if member.member_id in seen_member_ids:
            skipped_duplicate_count += 1
            continue
        seen_member_ids.add(member.member_id)
        members.append(member)
    return _PreparedMembers(
        source_level_count=len(source_records),
        members=tuple(sorted(members, key=lambda member: (member.price, member.member_id))),
        skipped_future_count=skipped_future_count,
        skipped_incomplete_count=skipped_incomplete_count,
        skipped_duplicate_count=skipped_duplicate_count,
    )


def _iter_source_records(levels: Sequence[Any]) -> tuple[dict[str, Any], ...]:
    records = []
    for level in levels:
        record = _source_record(level)
        if record.get("feature_id") == "VOLUME_PROFILE_LEVELS":
            records.extend(dict(item) for item in record.get("levels", ()))
        else:
            records.append(record)
    return tuple(records)


def _source_record(level: Any) -> dict[str, Any]:
    if isinstance(level, Mapping):
        return dict(level)
    if hasattr(level, "as_record"):
        return dict(level.as_record())
    raise TypeError("level sources must be mappings or expose as_record()")


def _member_from_record(record: Mapping[str, Any]) -> LevelClusterMember | None:
    feature_id = _required_string(record, "feature_id")
    if feature_id == "ANCHORED_VWAP":
        return _anchored_vwap_member(record)
    price = _record_decimal(record, "price")
    if price is None:
        return None
    detected_at = _record_datetime(record, "detected_at")
    source_timestamp = _optional_source_timestamp(record)
    source_timeframe = _optional_string(
        record,
        ("timeframe", "source_timeframe", "confirmation_timeframe"),
    )
    level_type = _level_type(record)
    exchange = _required_string(record, "exchange")
    symbol = _required_string(record, "symbol")
    provider = _required_string(record, "provider")
    member_id = record.get("member_id")
    return LevelClusterMember(
        member_id=(
            _required_string(record, "member_id")
            if member_id is not None
            else _member_id(
                feature_id=feature_id,
                level_type=level_type,
                price=price,
                exchange=exchange,
                symbol=symbol,
                provider=provider,
                source_timestamp=source_timestamp,
            )
        ),
        feature_id=feature_id,
        level_type=level_type,
        price=price,
        detected_at=detected_at,
        exchange=exchange,
        symbol=symbol,
        provider=provider,
        source_timestamp=source_timestamp,
        source_timeframe=source_timeframe,
        source_record=dict(record),
    )


def _anchored_vwap_member(record: Mapping[str, Any]) -> LevelClusterMember | None:
    price = _record_decimal(record, "vwap")
    if price is None:
        return None
    detected_at = _record_datetime(record, "as_of")
    source_timestamp = _record_datetime(record, "anchor_timestamp")
    level_type = _required_string(record, "anchor_type")
    exchange = _required_string(record, "exchange")
    symbol = _required_string(record, "symbol")
    provider = _required_string(record, "provider")
    feature_id = _required_string(record, "feature_id")
    return LevelClusterMember(
        member_id=_member_id(
            feature_id=feature_id,
            level_type=level_type,
            price=price,
            exchange=exchange,
            symbol=symbol,
            provider=provider,
            source_timestamp=source_timestamp,
        ),
        feature_id=feature_id,
        level_type=level_type,
        price=price,
        detected_at=detected_at,
        exchange=exchange,
        symbol=symbol,
        provider=provider,
        source_timestamp=source_timestamp,
        source_timeframe=_optional_string(record, ("source_timeframe",)),
        source_record=dict(record),
    )


def _cluster_members(
    members: Sequence[LevelClusterMember],
    *,
    cluster_distance_fraction: Decimal,
    cluster_atr: Decimal | None,
    cluster_atr_distance_threshold: Decimal,
) -> tuple[tuple[LevelClusterMember, ...], ...]:
    clusters: list[list[LevelClusterMember]] = []
    for member in sorted(members, key=lambda item: (item.price, item.member_id)):
        if not clusters:
            clusters.append([member])
            continue
        previous_price = clusters[-1][-1].price
        if cluster_atr is None:
            distance = (member.price - previous_price) / previous_price
            threshold = cluster_distance_fraction
        else:
            distance = Decimal(
                str(
                    atr_normalized_distance(
                        float(member.price),
                        float(previous_price),
                        float(cluster_atr),
                    )
                )
            )
            threshold = cluster_atr_distance_threshold
        if distance <= threshold:
            clusters[-1].append(member)
        else:
            clusters.append([member])
    return tuple(tuple(cluster) for cluster in clusters)


def _build_cluster(
    members: Sequence[LevelClusterMember],
    *,
    as_of: datetime,
    reference_price: Decimal,
    cluster_distance_fraction: Decimal,
    minimum_level_strength: Decimal,
) -> LevelCluster:
    lower_bound = min(member.price for member in members)
    upper_bound = max(member.price for member in members)
    center_price = _weighted_center(members)
    unique_sources = {member.feature_id for member in members}
    unique_timeframes = {
        member.source_timeframe
        for member in members
        if member.source_timeframe is not None
    }
    zone_type = (
        LEVEL_CLUSTER_SUPPORT
        if center_price <= reference_price
        else LEVEL_CLUSTER_RESISTANCE
    )
    confluence_score = _confluence_score(
        minimum_level_strength=minimum_level_strength,
        member_count=len(members),
        unique_source_count=len(unique_sources),
        unique_timeframe_count=len(unique_timeframes),
    )
    return LevelCluster(
        feature_id=LEVEL_CLUSTER_FEATURE_ID,
        cluster_id=_cluster_id(zone_type, members),
        zone_type=zone_type,
        lower_bound=lower_bound,
        upper_bound=upper_bound,
        center_price=center_price,
        reference_price=reference_price,
        detected_at=as_of,
        cluster_distance_fraction=cluster_distance_fraction,
        minimum_level_strength=minimum_level_strength,
        confluence_score=confluence_score,
        member_count=len(members),
        unique_source_count=len(unique_sources),
        unique_timeframe_count=len(unique_timeframes),
        members=tuple(sorted(members, key=lambda member: member.member_id)),
        reason_codes=("LEVEL_CLUSTER_COMPLETE",),
    )


def _weighted_center(members: Sequence[LevelClusterMember]) -> Decimal:
    weighted_sum = Decimal("0")
    weight_sum = Decimal("0")
    for member in members:
        weight = _source_weight(member)
        weighted_sum += member.price * weight
        weight_sum += weight
    return weighted_sum / weight_sum


def _source_weight(member: LevelClusterMember) -> Decimal:
    if member.feature_id == "MONTHLY_SWING_LEVEL":
        return Decimal("1.30")
    if member.feature_id == "WEEKLY_SWING_LEVEL":
        return Decimal("1.20")
    if member.feature_id == "BREAKOUT_RECLAIM_LEVEL":
        return Decimal("1.10")
    if member.feature_id == "VOLUME_PROFILE_LEVEL":
        return Decimal("1.00")
    if member.feature_id == "ANCHORED_VWAP":
        return Decimal("1.00")
    return Decimal("1.00")


def _confluence_score(
    *,
    minimum_level_strength: Decimal,
    member_count: int,
    unique_source_count: int,
    unique_timeframe_count: int,
) -> Decimal:
    source_bonus = Decimal(max(0, unique_source_count - 1)) * Decimal("10")
    timeframe_bonus = Decimal(max(0, unique_timeframe_count - 1)) * Decimal("5")
    touch_bonus = min(
        LEVEL_CLUSTER_TOUCH_BONUS_MAX,
        Decimal(max(0, member_count - unique_source_count)) * Decimal("2"),
    )
    return min(
        Decimal("100"),
        minimum_level_strength + source_bonus + timeframe_bonus + touch_bonus,
    )


def _cluster_id(zone_type: str, members: Sequence[LevelClusterMember]) -> str:
    payload = "|".join(
        (
            zone_type,
            *(member.member_id for member in sorted(members, key=lambda item: item.member_id)),
        )
    )
    return f"LEVEL_CLUSTER:{zone_type}:{sha1(payload.encode('utf-8')).hexdigest()[:12]}"


def _result_reason_codes(prepared: _PreparedMembers) -> tuple[str, ...]:
    reason_codes = []
    if prepared.skipped_future_count:
        reason_codes.append("LEVEL_CLUSTER_SOURCE_NOT_READY")
    if prepared.skipped_incomplete_count:
        reason_codes.append("LEVEL_CLUSTER_INCOMPLETE_SOURCE_SKIPPED")
    if prepared.skipped_duplicate_count:
        reason_codes.append("LEVEL_CLUSTER_DUPLICATE_MEMBER_SKIPPED")
    return tuple(reason_codes)


def _member_id(
    *,
    feature_id: str,
    level_type: str,
    price: Decimal,
    exchange: str,
    symbol: str,
    provider: str,
    source_timestamp: datetime | None,
) -> str:
    source_time = source_timestamp.isoformat() if source_timestamp else "none"
    return "|".join(
        (
            feature_id,
            level_type,
            source_time,
            str(price),
            exchange,
            symbol,
            provider,
        )
    )


def _level_type(record: Mapping[str, Any]) -> str:
    for key in ("level_type", "anchor_type", "source_type"):
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    raise ValueError("level_type must be available for clustering")


def _optional_source_timestamp(record: Mapping[str, Any]) -> datetime | None:
    for key in (
        "level_timestamp",
        "source_timestamp",
        "anchor_timestamp",
        "confirmation_timestamp",
        "profile_start",
    ):
        value = record.get(key)
        if value is not None:
            return _datetime(value, key)
    return None


def _optional_string(record: Mapping[str, Any], keys: tuple[str, ...]) -> str | None:
    for key in keys:
        value = record.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return None


def _record_decimal(record: Mapping[str, Any], key: str) -> Decimal | None:
    value = record.get(key)
    if value is None:
        return None
    return _positive_decimal(value, key)


def _record_datetime(record: Mapping[str, Any], key: str) -> datetime:
    value = record.get(key)
    if value is None:
        raise ValueError(f"{key} must be present")
    return _datetime(value, key)


def _datetime(value: Any, key: str) -> datetime:
    if isinstance(value, datetime):
        return require_utc_datetime(value, key)
    if isinstance(value, str):
        return require_utc_datetime(datetime.fromisoformat(value), key)
    raise ValueError(f"{key} must be a datetime or ISO datetime string")


def _required_string(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _single_market_identity(members: Sequence[LevelClusterMember]) -> tuple[str, str, str]:
    identities = {(member.exchange, member.symbol, member.provider) for member in members}
    if len(identities) != 1:
        raise ValueError("level clustering requires one exchange/symbol/provider series")
    return next(iter(identities))


def _positive_decimal_fraction(value: Any, name: str) -> Decimal:
    return _positive_fraction(Decimal(str(value)), name)


def _positive_fraction(value: Decimal, name: str) -> Decimal:
    if value <= 0 or value > 1:
        raise ValueError(f"{name} must be > 0 and <= 1")
    return value


def _positive_decimal(value: Any, name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value <= 0:
        raise ValueError(f"{name} must be > 0")
    return decimal_value


def _score(value: Decimal, name: str) -> Decimal:
    if value < 0 or value > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return value
