"""Level-strength scoring for clustered price levels."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any


LEVEL_STRENGTH_FEATURE_ID = "LEVEL_STRENGTH"
LEVEL_STRENGTH_COMPONENT_IDS = (
    "timeframe",
    "touch_count",
    "reaction_magnitude",
    "volume",
    "confluence",
)
LEVEL_STRENGTH_REASON_CODES = (
    "LEVEL_STRENGTH_INPUT_MISSING",
    "LEVEL_STRENGTH_TOUCH_COUNT_CAPPED",
    "LEVEL_STRENGTH_REACTION_CAPPED",
    "LEVEL_STRENGTH_COMPLETE",
)
DEFAULT_LEVEL_STRENGTH_WEIGHTS = {
    "timeframe": Decimal("0.20"),
    "touch_count": Decimal("0.20"),
    "reaction_magnitude": Decimal("0.20"),
    "volume": Decimal("0.20"),
    "confluence": Decimal("0.20"),
}
DEFAULT_LEVEL_STRENGTH_TIMEFRAME_SCORES = {
    "1h": Decimal("40"),
    "1d": Decimal("65"),
    "1w": Decimal("85"),
    "1mo": Decimal("100"),
    "unknown": Decimal("50"),
}
DEFAULT_LEVEL_STRENGTH_TOUCH_COUNT_FULL = 4
DEFAULT_LEVEL_STRENGTH_REACTION_FULL_FRACTION = Decimal("0.10")


@dataclass(frozen=True)
class LevelStrengthInput:
    timeframes: tuple[str, ...]
    touch_count: int | None
    reaction_magnitude_fraction: Decimal | None
    volume_percentile: Decimal | None
    confluence_score: Decimal | None

    def as_record(self) -> dict[str, Any]:
        if not all(isinstance(timeframe, str) and timeframe.strip() for timeframe in self.timeframes):
            raise ValueError("timeframes must contain only non-empty strings")
        if self.touch_count is not None and self.touch_count < 0:
            raise ValueError("touch_count must be >= 0")
        if (
            self.reaction_magnitude_fraction is not None
            and self.reaction_magnitude_fraction < 0
        ):
            raise ValueError("reaction_magnitude_fraction must be >= 0")
        if self.volume_percentile is not None:
            _score(self.volume_percentile, "volume_percentile")
        if self.confluence_score is not None:
            _score(self.confluence_score, "confluence_score")
        return {
            "timeframes": list(self.timeframes),
            "touch_count": self.touch_count,
            "reaction_magnitude_fraction": (
                str(self.reaction_magnitude_fraction)
                if self.reaction_magnitude_fraction is not None
                else None
            ),
            "volume_percentile": (
                str(self.volume_percentile)
                if self.volume_percentile is not None
                else None
            ),
            "confluence_score": (
                str(self.confluence_score)
                if self.confluence_score is not None
                else None
            ),
        }


@dataclass(frozen=True)
class LevelStrengthResult:
    feature_id: str
    level_id: str
    zone_type: str | None
    score: Decimal | None
    interpretation: str | None
    inputs: LevelStrengthInput
    component_scores: dict[str, Decimal | None]
    weights: dict[str, Decimal]
    timeframe_scores: dict[str, Decimal]
    touch_count_full: int
    reaction_full_fraction: Decimal
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != LEVEL_STRENGTH_FEATURE_ID:
            raise ValueError("feature_id must be LEVEL_STRENGTH")
        if not self.level_id.strip():
            raise ValueError("level_id must be non-empty")
        if self.score is not None:
            _score(self.score, "score")
        if self.complete and self.score is None:
            raise ValueError("complete level-strength result requires score")
        _validate_weights(self.weights)
        _validate_timeframe_scores(self.timeframe_scores)
        if self.touch_count_full < 1:
            raise ValueError("touch_count_full must be >= 1")
        if self.reaction_full_fraction <= 0:
            raise ValueError("reaction_full_fraction must be > 0")
        for component_id in LEVEL_STRENGTH_COMPONENT_IDS:
            if component_id not in self.component_scores:
                raise ValueError(f"component_scores missing {component_id}")
            component_score = self.component_scores[component_id]
            if component_score is not None:
                _score(component_score, component_id)
        return {
            "feature_id": self.feature_id,
            "level_id": self.level_id,
            "zone_type": self.zone_type,
            "score": str(self.score) if self.score is not None else None,
            "interpretation": self.interpretation,
            "inputs": self.inputs.as_record(),
            "component_scores": {
                key: str(value) if value is not None else None
                for key, value in self.component_scores.items()
            },
            "weights": {key: str(value) for key, value in self.weights.items()},
            "timeframe_scores": {
                key: str(value) for key, value in self.timeframe_scores.items()
            },
            "touch_count_full": self.touch_count_full,
            "reaction_full_fraction": str(self.reaction_full_fraction),
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def calculate_level_strength(
    inputs: LevelStrengthInput,
    *,
    level_id: str,
    zone_type: str | None = None,
    weights: Mapping[str, Any] | None = None,
    timeframe_scores: Mapping[str, Any] | None = None,
    touch_count_full: int = DEFAULT_LEVEL_STRENGTH_TOUCH_COUNT_FULL,
    reaction_full_fraction: Any = DEFAULT_LEVEL_STRENGTH_REACTION_FULL_FRACTION,
    config_metadata: Mapping[str, str] | None = None,
) -> LevelStrengthResult:
    """Score a level's strength from timeframe, touch, reaction, volume, and confluence inputs."""

    if not level_id.strip():
        raise ValueError("level_id must be non-empty")
    normalized_weights = _normalize_weights(weights or DEFAULT_LEVEL_STRENGTH_WEIGHTS)
    normalized_timeframe_scores = _normalize_timeframe_scores(
        timeframe_scores or DEFAULT_LEVEL_STRENGTH_TIMEFRAME_SCORES,
    )
    if touch_count_full < 1:
        raise ValueError("touch_count_full must be >= 1")
    reaction_full = _positive_decimal(
        reaction_full_fraction,
        "reaction_full_fraction",
    )
    inputs.as_record()

    component_scores = {
        "timeframe": _timeframe_score(inputs.timeframes, normalized_timeframe_scores),
        "touch_count": _touch_count_score(inputs.touch_count, touch_count_full),
        "reaction_magnitude": _reaction_score(
            inputs.reaction_magnitude_fraction,
            reaction_full,
        ),
        "volume": inputs.volume_percentile,
        "confluence": inputs.confluence_score,
    }
    missing_components = [
        component_id
        for component_id, component_score in component_scores.items()
        if component_score is None
    ]
    reason_codes = _cap_reason_codes(
        inputs,
        touch_count_full=touch_count_full,
        reaction_full_fraction=reaction_full,
    )
    if missing_components:
        return LevelStrengthResult(
            feature_id=LEVEL_STRENGTH_FEATURE_ID,
            level_id=level_id,
            zone_type=zone_type,
            score=None,
            interpretation=None,
            inputs=inputs,
            component_scores=component_scores,
            weights=normalized_weights,
            timeframe_scores=normalized_timeframe_scores,
            touch_count_full=touch_count_full,
            reaction_full_fraction=reaction_full,
            config_metadata=dict(config_metadata or {}),
            complete=False,
            reason_codes=("LEVEL_STRENGTH_INPUT_MISSING", *reason_codes),
        )

    score = sum(
        component_scores[component_id] * normalized_weights[component_id]
        for component_id in LEVEL_STRENGTH_COMPONENT_IDS
    )
    return LevelStrengthResult(
        feature_id=LEVEL_STRENGTH_FEATURE_ID,
        level_id=level_id,
        zone_type=zone_type,
        score=score,
        interpretation=_interpret_score(score),
        inputs=inputs,
        component_scores=component_scores,
        weights=normalized_weights,
        timeframe_scores=normalized_timeframe_scores,
        touch_count_full=touch_count_full,
        reaction_full_fraction=reaction_full,
        config_metadata=dict(config_metadata or {}),
        complete=True,
        reason_codes=(*reason_codes, "LEVEL_STRENGTH_COMPLETE"),
    )


def calculate_level_strength_from_cluster(
    cluster: Any,
    *,
    touch_count: int | None = None,
    reaction_magnitude_fraction: Any | None = None,
    volume_percentile: Any | None = None,
    weights: Mapping[str, Any] | None = None,
    timeframe_scores: Mapping[str, Any] | None = None,
    touch_count_full: int = DEFAULT_LEVEL_STRENGTH_TOUCH_COUNT_FULL,
    reaction_full_fraction: Any = DEFAULT_LEVEL_STRENGTH_REACTION_FULL_FRACTION,
    config_metadata: Mapping[str, str] | None = None,
) -> LevelStrengthResult:
    """Score a clustered support/resistance zone from cluster plus strength inputs."""

    record = _record(cluster)
    level_id = _required_string(record, "cluster_id")
    confluence_score = _required_score(record, "confluence_score")
    member_count = _required_non_negative_int(record, "member_count")
    inputs = LevelStrengthInput(
        timeframes=_member_timeframes(record),
        touch_count=member_count if touch_count is None else touch_count,
        reaction_magnitude_fraction=(
            Decimal(str(reaction_magnitude_fraction))
            if reaction_magnitude_fraction is not None
            else None
        ),
        volume_percentile=(
            Decimal(str(volume_percentile)) if volume_percentile is not None else None
        ),
        confluence_score=confluence_score,
    )
    return calculate_level_strength(
        inputs,
        level_id=level_id,
        zone_type=_optional_string(record, "zone_type"),
        weights=weights,
        timeframe_scores=timeframe_scores,
        touch_count_full=touch_count_full,
        reaction_full_fraction=reaction_full_fraction,
        config_metadata=config_metadata,
    )


def _record(source: Any) -> dict[str, Any]:
    if isinstance(source, Mapping):
        return dict(source)
    if hasattr(source, "as_record"):
        return dict(source.as_record())
    raise TypeError("cluster must be a mapping or expose as_record()")


def _member_timeframes(record: Mapping[str, Any]) -> tuple[str, ...]:
    timeframes = []
    for member in record.get("members", ()):
        if not isinstance(member, Mapping):
            continue
        timeframe = member.get("source_timeframe")
        if isinstance(timeframe, str) and timeframe.strip():
            timeframes.append(timeframe)
    if not timeframes:
        timeframe = record.get("source_timeframe")
        if isinstance(timeframe, str) and timeframe.strip():
            timeframes.append(timeframe)
    return tuple(sorted(set(timeframes)))


def _timeframe_score(
    timeframes: tuple[str, ...],
    timeframe_scores: Mapping[str, Decimal],
) -> Decimal | None:
    if not timeframes:
        return None
    fallback = timeframe_scores["unknown"]
    return max(timeframe_scores.get(timeframe, fallback) for timeframe in timeframes)


def _touch_count_score(touch_count: int | None, touch_count_full: int) -> Decimal | None:
    if touch_count is None:
        return None
    return min(Decimal("100"), Decimal(touch_count) / Decimal(touch_count_full) * Decimal("100"))


def _reaction_score(
    reaction_magnitude_fraction: Decimal | None,
    reaction_full_fraction: Decimal,
) -> Decimal | None:
    if reaction_magnitude_fraction is None:
        return None
    return min(
        Decimal("100"),
        reaction_magnitude_fraction / reaction_full_fraction * Decimal("100"),
    )


def _cap_reason_codes(
    inputs: LevelStrengthInput,
    *,
    touch_count_full: int,
    reaction_full_fraction: Decimal,
) -> tuple[str, ...]:
    reason_codes = []
    if inputs.touch_count is not None and inputs.touch_count > touch_count_full:
        reason_codes.append("LEVEL_STRENGTH_TOUCH_COUNT_CAPPED")
    if (
        inputs.reaction_magnitude_fraction is not None
        and inputs.reaction_magnitude_fraction > reaction_full_fraction
    ):
        reason_codes.append("LEVEL_STRENGTH_REACTION_CAPPED")
    return tuple(reason_codes)


def _interpret_score(score: Decimal) -> str:
    if score >= Decimal("90"):
        return "major"
    if score >= Decimal("75"):
        return "strong"
    if score >= Decimal("60"):
        return "watch"
    return "weak"


def _normalize_weights(weights: Mapping[str, Any]) -> dict[str, Decimal]:
    normalized = {key: Decimal(str(value)) for key, value in weights.items()}
    _validate_weights(normalized)
    return normalized


def _validate_weights(weights: Mapping[str, Decimal]) -> None:
    missing = set(LEVEL_STRENGTH_COMPONENT_IDS) - set(weights)
    extra = set(weights) - set(LEVEL_STRENGTH_COMPONENT_IDS)
    if missing or extra:
        raise ValueError(
            "level-strength weights must exactly match "
            f"{LEVEL_STRENGTH_COMPONENT_IDS}; missing={sorted(missing)}, "
            f"extra={sorted(extra)}",
        )
    for key, value in weights.items():
        if value < 0 or value > 1:
            raise ValueError(f"{key} weight must be between 0 and 1")
    if abs(sum(weights.values()) - Decimal("1")) > Decimal("0.000001"):
        raise ValueError("level-strength weights must sum to 1.0")


def _normalize_timeframe_scores(scores: Mapping[str, Any]) -> dict[str, Decimal]:
    normalized = {key: Decimal(str(value)) for key, value in scores.items()}
    _validate_timeframe_scores(normalized)
    return normalized


def _validate_timeframe_scores(scores: Mapping[str, Decimal]) -> None:
    if "unknown" not in scores:
        raise ValueError("timeframe_scores must include unknown")
    for timeframe, score in scores.items():
        if not timeframe.strip():
            raise ValueError("timeframe score keys must be non-empty")
        _score(score, f"timeframe_scores.{timeframe}")


def _required_string(record: Mapping[str, Any], key: str) -> str:
    value = record.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _optional_string(record: Mapping[str, Any], key: str) -> str | None:
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{key} must be a non-empty string")
    return value


def _required_score(record: Mapping[str, Any], key: str) -> Decimal:
    value = record.get(key)
    if value is None:
        raise ValueError(f"{key} must be present")
    return _score(Decimal(str(value)), key)


def _required_non_negative_int(record: Mapping[str, Any], key: str) -> int:
    value = record.get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
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
