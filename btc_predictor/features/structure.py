"""Structure score helpers for entry location and structural R/R quality."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.features._scoring import decimal_weighted_score


STRUCTURE_SCORE_FEATURE_ID = "STRUCTURE_SCORE"
STRUCTURE_SCORE_COMPONENT_IDS = (
    "level_strength",
    "entry_location",
    "rr_quality",
    "confluence",
)
STRUCTURE_SCORE_REASON_CODES = (
    "STRUCTURE_SCORE_INPUT_MISSING",
    "STRUCTURE_SCORE_SUPPORT_MISSING",
    "STRUCTURE_SCORE_TARGET_MISSING",
    "STRUCTURE_SCORE_INVALID_RISK",
    "STRUCTURE_SCORE_COMPLETE",
)
DEFAULT_STRUCTURE_SCORE_WEIGHTS = {
    "level_strength": Decimal("0.45"),
    "entry_location": Decimal("0.25"),
    "rr_quality": Decimal("0.20"),
    "confluence": Decimal("0.10"),
}
DEFAULT_ENTRY_LOCATION_FULL_SCORE_DISTANCE_FRACTION = Decimal("0.01")
DEFAULT_ENTRY_LOCATION_ZERO_SCORE_DISTANCE_FRACTION = Decimal("0.08")
DEFAULT_RR_MINIMUM = Decimal("2.0")
DEFAULT_RR_PREFERRED_MIN = Decimal("2.5")
DEFAULT_RR_PREFERRED_MAX = Decimal("3.0")


@dataclass(frozen=True)
class StructureScoreInput:
    level_strength: Decimal | None
    entry_location: Decimal | None
    rr_quality: Decimal | None
    confluence: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "level_strength": _optional_score_record(
                self.level_strength,
                "level_strength",
            ),
            "entry_location": _optional_score_record(
                self.entry_location,
                "entry_location",
            ),
            "rr_quality": _optional_score_record(self.rr_quality, "rr_quality"),
            "confluence": _optional_score_record(self.confluence, "confluence"),
        }


@dataclass(frozen=True)
class StructureSelection:
    support_cluster_id: str | None
    support_center_price: Decimal | None
    support_lower_bound: Decimal | None
    support_upper_bound: Decimal | None
    target_cluster_id: str | None
    target_center_price: Decimal | None
    target_lower_bound: Decimal | None
    target_upper_bound: Decimal | None
    entry_price: Decimal | None
    stop_price: Decimal | None
    reward_risk: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "support_cluster_id": self.support_cluster_id,
            "support_center_price": _optional_decimal_record(
                self.support_center_price,
                "support_center_price",
            ),
            "support_lower_bound": _optional_decimal_record(
                self.support_lower_bound,
                "support_lower_bound",
            ),
            "support_upper_bound": _optional_decimal_record(
                self.support_upper_bound,
                "support_upper_bound",
            ),
            "target_cluster_id": self.target_cluster_id,
            "target_center_price": _optional_decimal_record(
                self.target_center_price,
                "target_center_price",
            ),
            "target_lower_bound": _optional_decimal_record(
                self.target_lower_bound,
                "target_lower_bound",
            ),
            "target_upper_bound": _optional_decimal_record(
                self.target_upper_bound,
                "target_upper_bound",
            ),
            "entry_price": _optional_decimal_record(self.entry_price, "entry_price"),
            "stop_price": _optional_decimal_record(self.stop_price, "stop_price"),
            "reward_risk": _optional_decimal_record(self.reward_risk, "reward_risk"),
        }


@dataclass(frozen=True)
class StructureScoreResult:
    feature_id: str
    score: Decimal | None
    interpretation: str | None
    inputs: StructureScoreInput
    weights: dict[str, Decimal]
    contributions: dict[str, Decimal | None]
    selection: StructureSelection
    entry_location_parameters: dict[str, Decimal]
    rr_parameters: dict[str, Decimal]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        if self.interpretation is None:
            return None
        return f"{self.feature_id}_{self.interpretation}"

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != STRUCTURE_SCORE_FEATURE_ID:
            raise ValueError("feature_id must be STRUCTURE_SCORE")
        if self.score is not None:
            _score(self.score, "score")
        if self.complete and self.score is None:
            raise ValueError("complete structure score requires score")
        _validate_weights(self.weights)
        for component_id in STRUCTURE_SCORE_COMPONENT_IDS:
            if component_id not in self.contributions:
                raise ValueError(f"contributions missing {component_id}")
            contribution = self.contributions[component_id]
            if contribution is not None:
                _non_negative_decimal(contribution, component_id)
        _validate_entry_location_parameters(self.entry_location_parameters)
        _validate_rr_parameters(self.rr_parameters)
        return {
            "feature_id": self.feature_id,
            "score": str(self.score) if self.score is not None else None,
            "interpretation": self.interpretation,
            "reason_code": self.reason_code,
            "inputs": self.inputs.as_record(),
            "weights": {key: str(value) for key, value in self.weights.items()},
            "contributions": {
                key: str(value) if value is not None else None
                for key, value in self.contributions.items()
            },
            "selection": self.selection.as_record(),
            "entry_location_parameters": {
                key: str(value) for key, value in self.entry_location_parameters.items()
            },
            "rr_parameters": {
                key: str(value) for key, value in self.rr_parameters.items()
            },
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def calculate_structure_score(
    inputs: StructureScoreInput,
    *,
    weights: Mapping[str, Any] | None = None,
    selection: StructureSelection | None = None,
    entry_location_parameters: Mapping[str, Any] | None = None,
    rr_parameters: Mapping[str, Any] | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> StructureScoreResult:
    """Calculate StructureScore from explicit component scores."""

    normalized_weights = _normalize_weights(weights or DEFAULT_STRUCTURE_SCORE_WEIGHTS)
    normalized_entry_parameters = _normalize_entry_location_parameters(
        entry_location_parameters,
    )
    normalized_rr_parameters = _normalize_rr_parameters(rr_parameters)
    inputs.as_record()
    components = {
        "level_strength": inputs.level_strength,
        "entry_location": inputs.entry_location,
        "rr_quality": inputs.rr_quality,
        "confluence": inputs.confluence,
    }
    weighted = decimal_weighted_score(
        components,
        normalized_weights,
        component_ids=STRUCTURE_SCORE_COMPONENT_IDS,
    )
    contributions = weighted.contributions
    if any(value is None for value in components.values()):
        return StructureScoreResult(
            feature_id=STRUCTURE_SCORE_FEATURE_ID,
            score=None,
            interpretation=None,
            inputs=inputs,
            weights=normalized_weights,
            contributions=contributions,
            selection=selection or _empty_selection(),
            entry_location_parameters=normalized_entry_parameters,
            rr_parameters=normalized_rr_parameters,
            config_metadata=dict(config_metadata or {}),
            complete=False,
            reason_codes=("STRUCTURE_SCORE_INPUT_MISSING",),
        )

    if weighted.score is None:
        raise RuntimeError("complete structure inputs unexpectedly produced an incomplete score")
    score = weighted.score
    return StructureScoreResult(
        feature_id=STRUCTURE_SCORE_FEATURE_ID,
        score=score,
        interpretation=_interpret_score(score),
        inputs=inputs,
        weights=normalized_weights,
        contributions=contributions,
        selection=selection or _empty_selection(),
        entry_location_parameters=normalized_entry_parameters,
        rr_parameters=normalized_rr_parameters,
        config_metadata=dict(config_metadata or {}),
        complete=True,
        reason_codes=("STRUCTURE_SCORE_COMPLETE",),
    )


def calculate_structure_score_from_clusters(
    clusters: Any,
    *,
    entry_price: Any,
    stop_price: Any,
    level_strength_score: Any | None = None,
    level_strength_result: Any | None = None,
    weights: Mapping[str, Any] | None = None,
    entry_location_full_score_distance_fraction: Any = (
        DEFAULT_ENTRY_LOCATION_FULL_SCORE_DISTANCE_FRACTION
    ),
    entry_location_zero_score_distance_fraction: Any = (
        DEFAULT_ENTRY_LOCATION_ZERO_SCORE_DISTANCE_FRACTION
    ),
    rr_minimum: Any = DEFAULT_RR_MINIMUM,
    rr_preferred_min: Any = DEFAULT_RR_PREFERRED_MIN,
    rr_preferred_max: Any = DEFAULT_RR_PREFERRED_MAX,
    config_metadata: Mapping[str, str] | None = None,
) -> StructureScoreResult:
    """Calculate Phase 1 structure score from support/resistance clusters."""

    entry = _positive_decimal(entry_price, "entry_price")
    stop = _positive_decimal(stop_price, "stop_price")
    level_strength = _level_strength_score(
        level_strength_score=level_strength_score,
        level_strength_result=level_strength_result,
    )
    entry_parameters = _normalize_entry_location_parameters(
        {
            "full_score_distance_fraction": (
                entry_location_full_score_distance_fraction
            ),
            "zero_score_distance_fraction": (
                entry_location_zero_score_distance_fraction
            ),
        }
    )
    rr_parameters = _normalize_rr_parameters(
        {
            "rr_minimum": rr_minimum,
            "rr_preferred_min": rr_preferred_min,
            "rr_preferred_max": rr_preferred_max,
        }
    )
    cluster_records = _cluster_records(clusters)
    support = _nearest_support(cluster_records, entry)
    target = _nearest_resistance(cluster_records, entry)
    selection = _selection(
        support=support,
        target=target,
        entry_price=entry,
        stop_price=stop,
        reward_risk=None,
    )
    if support is None:
        return _incomplete_from_components(
            level_strength=level_strength,
            entry_location=None,
            rr_quality=None,
            confluence=None,
            selection=selection,
            weights=weights,
            entry_location_parameters=entry_parameters,
            rr_parameters=rr_parameters,
            config_metadata=config_metadata,
            reason_codes=("STRUCTURE_SCORE_SUPPORT_MISSING",),
        )
    if target is None:
        return _incomplete_from_components(
            level_strength=level_strength,
            entry_location=_entry_location_score(support, entry, entry_parameters),
            rr_quality=None,
            confluence=_record_score(support, "confluence_score"),
            selection=selection,
            weights=weights,
            entry_location_parameters=entry_parameters,
            rr_parameters=rr_parameters,
            config_metadata=config_metadata,
            reason_codes=("STRUCTURE_SCORE_TARGET_MISSING",),
        )

    reward_risk = _reward_risk_ratio(entry=entry, stop=stop, target=target)
    selection = _selection(
        support=support,
        target=target,
        entry_price=entry,
        stop_price=stop,
        reward_risk=reward_risk,
    )
    if reward_risk is None:
        return _incomplete_from_components(
            level_strength=level_strength,
            entry_location=_entry_location_score(support, entry, entry_parameters),
            rr_quality=None,
            confluence=_record_score(support, "confluence_score"),
            selection=selection,
            weights=weights,
            entry_location_parameters=entry_parameters,
            rr_parameters=rr_parameters,
            config_metadata=config_metadata,
            reason_codes=("STRUCTURE_SCORE_INVALID_RISK",),
        )

    return calculate_structure_score(
        StructureScoreInput(
            level_strength=level_strength,
            entry_location=_entry_location_score(support, entry, entry_parameters),
            rr_quality=_rr_quality_score(reward_risk, rr_parameters),
            confluence=_record_score(support, "confluence_score"),
        ),
        weights=weights,
        selection=selection,
        entry_location_parameters=entry_parameters,
        rr_parameters=rr_parameters,
        config_metadata=config_metadata,
    )


def _incomplete_from_components(
    *,
    level_strength: Decimal | None,
    entry_location: Decimal | None,
    rr_quality: Decimal | None,
    confluence: Decimal | None,
    selection: StructureSelection,
    weights: Mapping[str, Any] | None,
    entry_location_parameters: Mapping[str, Decimal],
    rr_parameters: Mapping[str, Decimal],
    config_metadata: Mapping[str, str] | None,
    reason_codes: tuple[str, ...],
) -> StructureScoreResult:
    result = calculate_structure_score(
        StructureScoreInput(
            level_strength=level_strength,
            entry_location=entry_location,
            rr_quality=rr_quality,
            confluence=confluence,
        ),
        weights=weights,
        selection=selection,
        entry_location_parameters=entry_location_parameters,
        rr_parameters=rr_parameters,
        config_metadata=config_metadata,
    )
    return StructureScoreResult(
        feature_id=result.feature_id,
        score=result.score,
        interpretation=result.interpretation,
        inputs=result.inputs,
        weights=result.weights,
        contributions=result.contributions,
        selection=result.selection,
        entry_location_parameters=result.entry_location_parameters,
        rr_parameters=result.rr_parameters,
        config_metadata=result.config_metadata,
        complete=False,
        reason_codes=(*reason_codes, "STRUCTURE_SCORE_INPUT_MISSING"),
    )


def _cluster_records(clusters: Any) -> tuple[dict[str, Any], ...]:
    if isinstance(clusters, Sequence) and not isinstance(clusters, str | bytes):
        return tuple(_record(cluster) for cluster in clusters)
    record = _record(clusters)
    if record.get("feature_id") == "LEVEL_CLUSTERS":
        return tuple(dict(cluster) for cluster in record.get("clusters", ()))
    return (record,)


def _record(source: Any) -> dict[str, Any]:
    if isinstance(source, Mapping):
        return dict(source)
    if hasattr(source, "as_record"):
        return dict(source.as_record())
    raise TypeError("cluster sources must be mappings or expose as_record()")


def _nearest_support(
    clusters: Sequence[Mapping[str, Any]],
    entry_price: Decimal,
) -> dict[str, Any] | None:
    supports = [
        dict(cluster)
        for cluster in clusters
        if cluster.get("zone_type") == "support"
        and _record_decimal(cluster, "center_price") <= entry_price
    ]
    if not supports:
        return None
    return max(
        supports,
        key=lambda cluster: (
            _record_decimal(cluster, "center_price"),
            _record_score(cluster, "confluence_score"),
            _required_string(cluster, "cluster_id"),
        ),
    )


def _nearest_resistance(
    clusters: Sequence[Mapping[str, Any]],
    entry_price: Decimal,
) -> dict[str, Any] | None:
    resistances = [
        dict(cluster)
        for cluster in clusters
        if cluster.get("zone_type") == "resistance"
        and _record_decimal(cluster, "center_price") > entry_price
    ]
    if not resistances:
        return None
    return min(
        resistances,
        key=lambda cluster: (
            _record_decimal(cluster, "center_price"),
            -_record_score(cluster, "confluence_score"),
            _required_string(cluster, "cluster_id"),
        ),
    )


def _entry_location_score(
    support: Mapping[str, Any],
    entry_price: Decimal,
    parameters: Mapping[str, Decimal],
) -> Decimal:
    upper_bound = _record_decimal(support, "upper_bound")
    if entry_price <= upper_bound:
        return Decimal("100")
    distance_fraction = (entry_price - upper_bound) / entry_price
    full_distance = parameters["full_score_distance_fraction"]
    zero_distance = parameters["zero_score_distance_fraction"]
    if distance_fraction <= full_distance:
        return Decimal("100")
    if distance_fraction >= zero_distance:
        return Decimal("0")
    return (
        Decimal("100")
        * (zero_distance - distance_fraction)
        / (zero_distance - full_distance)
    )


def _reward_risk_ratio(
    *,
    entry: Decimal,
    stop: Decimal,
    target: Mapping[str, Any],
) -> Decimal | None:
    target_price = _record_decimal(target, "center_price")
    risk = entry - stop
    reward = target_price - entry
    if risk <= 0 or reward <= 0:
        return None
    return reward / risk


def _rr_quality_score(
    reward_risk: Decimal,
    parameters: Mapping[str, Decimal],
) -> Decimal:
    rr_minimum = parameters["rr_minimum"]
    rr_preferred_min = parameters["rr_preferred_min"]
    rr_preferred_max = parameters["rr_preferred_max"]
    if reward_risk < rr_minimum:
        return reward_risk / rr_minimum * Decimal("60")
    if reward_risk < rr_preferred_min:
        return Decimal("60") + (
            (reward_risk - rr_minimum)
            / (rr_preferred_min - rr_minimum)
            * Decimal("25")
        )
    if reward_risk <= rr_preferred_max:
        return Decimal("85") + (
            (reward_risk - rr_preferred_min)
            / (rr_preferred_max - rr_preferred_min)
            * Decimal("15")
        )
    return Decimal("100")


def _level_strength_score(
    *,
    level_strength_score: Any | None,
    level_strength_result: Any | None,
) -> Decimal | None:
    if level_strength_score is not None:
        return _score(Decimal(str(level_strength_score)), "level_strength_score")
    if level_strength_result is None:
        return None
    record = _record(level_strength_result)
    if record.get("complete") is False:
        return None
    score = record.get("score")
    if score is None:
        return None
    return _score(Decimal(str(score)), "level_strength_result.score")


def _selection(
    *,
    support: Mapping[str, Any] | None,
    target: Mapping[str, Any] | None,
    entry_price: Decimal,
    stop_price: Decimal,
    reward_risk: Decimal | None,
) -> StructureSelection:
    return StructureSelection(
        support_cluster_id=_optional_string(support, "cluster_id"),
        support_center_price=_optional_record_decimal(support, "center_price"),
        support_lower_bound=_optional_record_decimal(support, "lower_bound"),
        support_upper_bound=_optional_record_decimal(support, "upper_bound"),
        target_cluster_id=_optional_string(target, "cluster_id"),
        target_center_price=_optional_record_decimal(target, "center_price"),
        target_lower_bound=_optional_record_decimal(target, "lower_bound"),
        target_upper_bound=_optional_record_decimal(target, "upper_bound"),
        entry_price=entry_price,
        stop_price=stop_price,
        reward_risk=reward_risk,
    )


def _empty_selection() -> StructureSelection:
    return StructureSelection(
        support_cluster_id=None,
        support_center_price=None,
        support_lower_bound=None,
        support_upper_bound=None,
        target_cluster_id=None,
        target_center_price=None,
        target_lower_bound=None,
        target_upper_bound=None,
        entry_price=None,
        stop_price=None,
        reward_risk=None,
    )


def _normalize_weights(weights: Mapping[str, Any]) -> dict[str, Decimal]:
    normalized = {key: Decimal(str(value)) for key, value in weights.items()}
    _validate_weights(normalized)
    return normalized


def _validate_weights(weights: Mapping[str, Decimal]) -> None:
    missing = set(STRUCTURE_SCORE_COMPONENT_IDS) - set(weights)
    extra = set(weights) - set(STRUCTURE_SCORE_COMPONENT_IDS)
    if missing or extra:
        raise ValueError(
            "structure score weights must exactly match "
            f"{STRUCTURE_SCORE_COMPONENT_IDS}; missing={sorted(missing)}, "
            f"extra={sorted(extra)}",
        )
    for key, value in weights.items():
        if value < 0 or value > 1:
            raise ValueError(f"{key} weight must be between 0 and 1")
    if abs(sum(weights.values()) - Decimal("1")) > Decimal("0.000001"):
        raise ValueError("structure score weights must sum to 1.0")


def _normalize_entry_location_parameters(
    parameters: Mapping[str, Any] | None,
) -> dict[str, Decimal]:
    raw = {
        "full_score_distance_fraction": (
            DEFAULT_ENTRY_LOCATION_FULL_SCORE_DISTANCE_FRACTION
        ),
        "zero_score_distance_fraction": (
            DEFAULT_ENTRY_LOCATION_ZERO_SCORE_DISTANCE_FRACTION
        ),
    }
    raw.update(parameters or {})
    normalized = {key: Decimal(str(value)) for key, value in raw.items()}
    _validate_entry_location_parameters(normalized)
    return normalized


def _validate_entry_location_parameters(parameters: Mapping[str, Decimal]) -> None:
    full_distance = parameters["full_score_distance_fraction"]
    zero_distance = parameters["zero_score_distance_fraction"]
    _positive_fraction(full_distance, "full_score_distance_fraction")
    _positive_fraction(zero_distance, "zero_score_distance_fraction")
    if zero_distance <= full_distance:
        raise ValueError("zero_score_distance_fraction must be > full_score_distance_fraction")


def _normalize_rr_parameters(parameters: Mapping[str, Any] | None) -> dict[str, Decimal]:
    raw = {
        "rr_minimum": DEFAULT_RR_MINIMUM,
        "rr_preferred_min": DEFAULT_RR_PREFERRED_MIN,
        "rr_preferred_max": DEFAULT_RR_PREFERRED_MAX,
    }
    raw.update(parameters or {})
    normalized = {key: Decimal(str(value)) for key, value in raw.items()}
    _validate_rr_parameters(normalized)
    return normalized


def _validate_rr_parameters(parameters: Mapping[str, Decimal]) -> None:
    rr_minimum = parameters["rr_minimum"]
    rr_preferred_min = parameters["rr_preferred_min"]
    rr_preferred_max = parameters["rr_preferred_max"]
    _positive_decimal(rr_minimum, "rr_minimum")
    _positive_decimal(rr_preferred_min, "rr_preferred_min")
    _positive_decimal(rr_preferred_max, "rr_preferred_max")
    if rr_preferred_min < rr_minimum:
        raise ValueError("rr_preferred_min must be >= rr_minimum")
    if rr_preferred_max < rr_preferred_min:
        raise ValueError("rr_preferred_max must be >= rr_preferred_min")


def _interpret_score(score: Decimal) -> str:
    if score >= Decimal("85"):
        return "strong"
    if score >= Decimal("70"):
        return "constructive"
    if score >= Decimal("55"):
        return "mixed"
    return "weak"


def _required_string(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_string(record: Mapping[str, Any] | None, key: str) -> str | None:
    if record is None:
        return None
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _record_score(record: Mapping[str, Any], key: str) -> Decimal:
    return _score(_record_decimal(record, key), key)


def _record_decimal(record: Mapping[str, Any], key: str) -> Decimal:
    value = record.get(key)
    if value is None:
        raise ValueError(f"{key} must be present")
    return _positive_decimal(value, key)


def _optional_record_decimal(
    record: Mapping[str, Any] | None,
    key: str,
) -> Decimal | None:
    if record is None:
        return None
    value = record.get(key)
    if value is None:
        return None
    return _positive_decimal(value, key)


def _optional_score_record(value: Decimal | None, name: str) -> str | None:
    if value is None:
        return None
    _score(value, name)
    return str(value)


def _optional_decimal_record(value: Decimal | None, name: str) -> str | None:
    if value is None:
        return None
    _positive_decimal(value, name)
    return str(value)


def _positive_decimal(value: Any, name: str) -> Decimal:
    decimal_value = Decimal(str(value))
    if decimal_value <= 0:
        raise ValueError(f"{name} must be > 0")
    return decimal_value


def _non_negative_decimal(value: Decimal, name: str) -> Decimal:
    if value < 0:
        raise ValueError(f"{name} must be >= 0")
    return value


def _positive_fraction(value: Decimal, name: str) -> Decimal:
    if value <= 0 or value > 1:
        raise ValueError(f"{name} must be > 0 and <= 1")
    return value


def _score(value: Decimal, name: str) -> Decimal:
    if value < 0 or value > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return value
