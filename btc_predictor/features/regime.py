"""Base regime score helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from btc_predictor.features._scoring import decimal_weighted_score
from btc_predictor.quant.comparisons import decision_greater_equal


REGIME_SCORE_FEATURE_ID = "REGIME_SCORE"
REGIME_SMOOTHED_SCORE_FEATURE_ID = "REGIME_SMOOTHED_SCORE"
REGIME_CLASSIFICATION_FEATURE_ID = "REGIME_CLASSIFICATION"
REGIME_MODEL_CORE_MARKET_ONLY = "CORE_MARKET_ONLY"
REGIME_MODEL_FULL_MACRO_ONCHAIN_LIQUIDITY = "FULL_MACRO_ONCHAIN_LIQUIDITY"
CORE_REGIME_SCORE_COMPONENT_IDS = (
    "trend",
    "flow",
    "volatility",
    "positioning",
)
FULL_REGIME_SCORE_COMPONENT_IDS = (
    "trend",
    "flow",
    "macro",
    "onchain",
    "volatility",
    "liquidity",
)
DEFAULT_CORE_REGIME_SCORE_WEIGHTS = {
    "trend": Decimal("0.45"),
    "flow": Decimal("0.25"),
    "volatility": Decimal("0.15"),
    "positioning": Decimal("0.15"),
}
DEFAULT_FULL_REGIME_SCORE_WEIGHTS = {
    "trend": Decimal("0.35"),
    "flow": Decimal("0.20"),
    "macro": Decimal("0.15"),
    "onchain": Decimal("0.10"),
    "volatility": Decimal("0.10"),
    "liquidity": Decimal("0.10"),
}
DEFAULT_REGIME_SMOOTHING_PREVIOUS_WEIGHT = Decimal("0.70")
DEFAULT_REGIME_SMOOTHING_NEW_WEIGHT = Decimal("0.30")
REGIME_CLASSIFICATION_THRESHOLD_IDS = (
    "strong_bull",
    "bull",
    "mild_bull",
    "neutral",
    "mild_bear",
    "bear",
)
DEFAULT_REGIME_CLASSIFICATION_THRESHOLDS = {
    "strong_bull": Decimal("80"),
    "bull": Decimal("65"),
    "mild_bull": Decimal("55"),
    "neutral": Decimal("45"),
    "mild_bear": Decimal("35"),
    "bear": Decimal("20"),
}
REGIME_CLASSIFICATION_LABELS = (
    "STRONG_BULL",
    "BULL",
    "MILD_BULL",
    "NEUTRAL",
    "MILD_BEAR",
    "BEAR",
    "STRONG_BEAR",
)
REGIME_SCORE_REASON_CODES = (
    "REGIME_SCORE_CORE_INPUT_MISSING",
    "REGIME_SCORE_P1_INPUT_MISSING",
)
REGIME_SMOOTHING_REASON_CODES = (
    "REGIME_SMOOTHING_NEW_SCORE_MISSING",
    "REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING",
)
REGIME_CLASSIFICATION_REASON_CODES = (
    "REGIME_CLASSIFICATION_SCORE_MISSING",
)


@dataclass(frozen=True)
class RegimeScoreInput:
    trend_score: Decimal | None
    flow_score: Decimal | None
    volatility_score: Decimal | None
    positioning_score: Decimal | None
    macro_score: Decimal | None = None
    onchain_score: Decimal | None = None
    liquidity_score: Decimal | None = None

    def as_record(self) -> dict[str, str | None]:
        return {
            "trend": _optional_score_record(self.trend_score, "trend"),
            "flow": _optional_score_record(self.flow_score, "flow"),
            "volatility": _optional_score_record(
                self.volatility_score,
                "volatility",
            ),
            "positioning": _optional_score_record(
                self.positioning_score,
                "positioning",
            ),
            "macro": _optional_score_record(self.macro_score, "macro"),
            "onchain": _optional_score_record(self.onchain_score, "onchain"),
            "liquidity": _optional_score_record(
                self.liquidity_score,
                "liquidity",
            ),
        }


@dataclass(frozen=True)
class RegimeScoreResult:
    feature_id: str
    regime_model: str
    score: Decimal | None
    interpretation: str | None
    inputs: RegimeScoreInput
    weights: dict[str, Decimal]
    contributions: dict[str, Decimal | None]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        if self.interpretation is None:
            return None
        return f"{self.feature_id}_{self.interpretation}"

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != REGIME_SCORE_FEATURE_ID:
            raise ValueError("feature_id must be REGIME_SCORE")
        if self.regime_model not in (
            REGIME_MODEL_CORE_MARKET_ONLY,
            REGIME_MODEL_FULL_MACRO_ONCHAIN_LIQUIDITY,
        ):
            raise ValueError("regime_model is not supported")
        if self.score is not None:
            _score(self.score, "score")
        if self.complete and self.score is None:
            raise ValueError("complete regime score requires score")
        component_ids = (
            FULL_REGIME_SCORE_COMPONENT_IDS
            if self.regime_model == REGIME_MODEL_FULL_MACRO_ONCHAIN_LIQUIDITY
            else CORE_REGIME_SCORE_COMPONENT_IDS
        )
        _validate_weights(self.weights, component_ids=component_ids, name="regime")
        for component_id in component_ids:
            if component_id not in self.contributions:
                raise ValueError(f"contributions missing {component_id}")
            contribution = self.contributions[component_id]
            if contribution is not None and contribution < 0:
                raise ValueError(f"{component_id} contribution must be >= 0")
        return {
            "feature_id": self.feature_id,
            "regime_model": self.regime_model,
            "score": str(self.score) if self.score is not None else None,
            "interpretation": self.interpretation,
            "reason_code": self.reason_code,
            "inputs": self.inputs.as_record(),
            "weights": {key: str(value) for key, value in self.weights.items()},
            "contributions": {
                key: str(value) if value is not None else None
                for key, value in self.contributions.items()
            },
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class RegimeSmoothingInput:
    previous_smoothed_score: Decimal | None
    new_regime_score: Decimal | None

    def as_record(self) -> dict[str, str | None]:
        return {
            "previous_smoothed_score": _optional_score_record(
                self.previous_smoothed_score,
                "previous_smoothed_score",
            ),
            "new_regime_score": _optional_score_record(
                self.new_regime_score,
                "new_regime_score",
            ),
        }


@dataclass(frozen=True)
class RegimeSmoothingResult:
    feature_id: str
    score: Decimal | None
    interpretation: str | None
    inputs: RegimeSmoothingInput
    weights: dict[str, Decimal]
    contributions: dict[str, Decimal | None]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        if self.interpretation is None:
            return None
        return f"{self.feature_id}_{self.interpretation}"

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != REGIME_SMOOTHED_SCORE_FEATURE_ID:
            raise ValueError("feature_id must be REGIME_SMOOTHED_SCORE")
        if self.score is not None:
            _score(self.score, "score")
        if self.complete and self.score is None:
            raise ValueError("complete regime smoothing requires score")
        _validate_weights(
            self.weights,
            component_ids=("previous_smoothed_score", "new_regime_score"),
            name="regime_smoothing",
        )
        for component_id in self.weights:
            if component_id not in self.contributions:
                raise ValueError(f"contributions missing {component_id}")
        for component_id, contribution in self.contributions.items():
            if component_id not in self.weights:
                raise ValueError(f"contributions includes unsupported {component_id}")
            if contribution is not None and contribution < 0:
                raise ValueError(f"{component_id} contribution must be >= 0")
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
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


@dataclass(frozen=True)
class RegimeClassificationResult:
    feature_id: str
    score: Decimal | None
    regime: str | None
    thresholds: dict[str, Decimal]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        if self.regime is None:
            return None
        return f"{self.feature_id}_{self.regime}"

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != REGIME_CLASSIFICATION_FEATURE_ID:
            raise ValueError("feature_id must be REGIME_CLASSIFICATION")
        if self.score is not None:
            _score(self.score, "score")
        if self.complete and self.regime is None:
            raise ValueError("complete regime classification requires regime")
        _validate_regime_thresholds(self.thresholds)
        if self.regime is not None and self.regime not in REGIME_CLASSIFICATION_LABELS:
            raise ValueError("regime is not supported")
        return {
            "feature_id": self.feature_id,
            "score": str(self.score) if self.score is not None else None,
            "regime": self.regime,
            "reason_code": self.reason_code,
            "thresholds": {
                key: str(value) for key, value in self.thresholds.items()
            },
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def calculate_regime_score(
    inputs: RegimeScoreInput,
    *,
    core_weights: Mapping[str, Any] | None = None,
    full_weights: Mapping[str, Any] | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> RegimeScoreResult:
    """Calculate base regime score and record selected regime model."""

    core_score_weights = _normalize_weights(
        core_weights or DEFAULT_CORE_REGIME_SCORE_WEIGHTS,
        component_ids=CORE_REGIME_SCORE_COMPONENT_IDS,
        name="core_regime",
    )
    full_score_weights = _normalize_weights(
        full_weights or DEFAULT_FULL_REGIME_SCORE_WEIGHTS,
        component_ids=FULL_REGIME_SCORE_COMPONENT_IDS,
        name="full_regime",
    )
    input_values = _input_values(inputs)
    core_missing = [
        component_id
        for component_id in CORE_REGIME_SCORE_COMPONENT_IDS
        if input_values[component_id] is None
    ]
    p1_missing = [
        component_id
        for component_id in ("macro", "onchain", "liquidity")
        if input_values[component_id] is None
    ]
    reason_codes = []
    if core_missing:
        reason_codes.append("REGIME_SCORE_CORE_INPUT_MISSING")
    if p1_missing:
        reason_codes.append("REGIME_SCORE_P1_INPUT_MISSING")

    regime_model = (
        REGIME_MODEL_CORE_MARKET_ONLY
        if p1_missing
        else REGIME_MODEL_FULL_MACRO_ONCHAIN_LIQUIDITY
    )
    selected_component_ids = (
        FULL_REGIME_SCORE_COMPONENT_IDS
        if regime_model == REGIME_MODEL_FULL_MACRO_ONCHAIN_LIQUIDITY
        else CORE_REGIME_SCORE_COMPONENT_IDS
    )
    selected_weights = (
        full_score_weights
        if regime_model == REGIME_MODEL_FULL_MACRO_ONCHAIN_LIQUIDITY
        else core_score_weights
    )
    weighted = decimal_weighted_score(
        input_values,
        selected_weights,
        component_ids=selected_component_ids,
    )
    contributions = weighted.contributions
    score = weighted.score
    return RegimeScoreResult(
        feature_id=REGIME_SCORE_FEATURE_ID,
        regime_model=regime_model,
        score=score,
        interpretation=_interpret_score(score),
        inputs=inputs,
        weights=selected_weights,
        contributions=contributions,
        config_metadata=dict(config_metadata or {}),
        complete=score is not None,
        reason_codes=tuple(reason_codes),
    )


def calculate_regime_classification(
    score: Decimal | None,
    *,
    thresholds: Any | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> RegimeClassificationResult:
    """Classify a raw or smoothed regime score into the rulebook regime bucket."""

    normalized_thresholds = _normalize_regime_thresholds(thresholds)
    if score is None:
        return RegimeClassificationResult(
            feature_id=REGIME_CLASSIFICATION_FEATURE_ID,
            score=None,
            regime=None,
            thresholds=normalized_thresholds,
            config_metadata=dict(config_metadata or {}),
            complete=False,
            reason_codes=("REGIME_CLASSIFICATION_SCORE_MISSING",),
        )

    regime_score = _score(score, "score")
    return RegimeClassificationResult(
        feature_id=REGIME_CLASSIFICATION_FEATURE_ID,
        score=regime_score,
        regime=_classify_regime(regime_score, normalized_thresholds),
        thresholds=normalized_thresholds,
        config_metadata=dict(config_metadata or {}),
        complete=True,
        reason_codes=(),
    )


def calculate_regime_smoothing(
    inputs: RegimeSmoothingInput,
    *,
    previous_weight: Any = DEFAULT_REGIME_SMOOTHING_PREVIOUS_WEIGHT,
    new_weight: Any = DEFAULT_REGIME_SMOOTHING_NEW_WEIGHT,
    config_metadata: Mapping[str, str] | None = None,
) -> RegimeSmoothingResult:
    """Smooth the latest regime score against the prior smoothed regime score."""

    weights = _normalize_weights(
        {
            "previous_smoothed_score": previous_weight,
            "new_regime_score": new_weight,
        },
        component_ids=("previous_smoothed_score", "new_regime_score"),
        name="regime_smoothing",
    )
    inputs.as_record()
    reason_codes = []

    if inputs.new_regime_score is None:
        reason_codes.append("REGIME_SMOOTHING_NEW_SCORE_MISSING")
        return RegimeSmoothingResult(
            feature_id=REGIME_SMOOTHED_SCORE_FEATURE_ID,
            score=None,
            interpretation=None,
            inputs=inputs,
            weights=weights,
            contributions={
                "previous_smoothed_score": None,
                "new_regime_score": None,
            },
            config_metadata=dict(config_metadata or {}),
            complete=False,
            reason_codes=tuple(reason_codes),
        )

    new_score = _score(inputs.new_regime_score, "new_regime_score")
    if inputs.previous_smoothed_score is None:
        reason_codes.append("REGIME_SMOOTHING_PREVIOUS_SCORE_MISSING")
        contributions = {
            "previous_smoothed_score": None,
            "new_regime_score": new_score,
        }
        score = new_score
    else:
        previous_score = _score(
            inputs.previous_smoothed_score,
            "previous_smoothed_score",
        )
        contributions = {
            "previous_smoothed_score": (
                weights["previous_smoothed_score"] * previous_score
            ),
            "new_regime_score": weights["new_regime_score"] * new_score,
        }
        score = sum(contributions.values(), Decimal("0"))

    return RegimeSmoothingResult(
        feature_id=REGIME_SMOOTHED_SCORE_FEATURE_ID,
        score=score,
        interpretation=_interpret_score(score),
        inputs=inputs,
        weights=weights,
        contributions=contributions,
        config_metadata=dict(config_metadata or {}),
        complete=True,
        reason_codes=tuple(reason_codes),
    )


def _input_values(inputs: RegimeScoreInput) -> dict[str, Decimal | None]:
    inputs.as_record()
    return {
        "trend": inputs.trend_score,
        "flow": inputs.flow_score,
        "volatility": inputs.volatility_score,
        "positioning": inputs.positioning_score,
        "macro": inputs.macro_score,
        "onchain": inputs.onchain_score,
        "liquidity": inputs.liquidity_score,
    }


def _interpret_score(score: Decimal | None) -> str | None:
    if score is None:
        return None
    return _classify_regime(score, DEFAULT_REGIME_CLASSIFICATION_THRESHOLDS).lower()


def _classify_regime(score: Decimal, thresholds: Mapping[str, Decimal]) -> str:
    if decision_greater_equal(score, thresholds["strong_bull"]):
        return "STRONG_BULL"
    if decision_greater_equal(score, thresholds["bull"]):
        return "BULL"
    if decision_greater_equal(score, thresholds["mild_bull"]):
        return "MILD_BULL"
    if decision_greater_equal(score, thresholds["neutral"]):
        return "NEUTRAL"
    if decision_greater_equal(score, thresholds["mild_bear"]):
        return "MILD_BEAR"
    if decision_greater_equal(score, thresholds["bear"]):
        return "BEAR"
    return "STRONG_BEAR"


def _normalize_regime_thresholds(
    thresholds: Any | None,
) -> dict[str, Decimal]:
    if thresholds is None:
        normalized = dict(DEFAULT_REGIME_CLASSIFICATION_THRESHOLDS)
    elif isinstance(thresholds, Mapping):
        missing = set(REGIME_CLASSIFICATION_THRESHOLD_IDS) - set(thresholds)
        extra = set(thresholds) - set(REGIME_CLASSIFICATION_THRESHOLD_IDS)
        if missing or extra:
            raise ValueError(
                "regime classification thresholds must exactly match "
                f"{REGIME_CLASSIFICATION_THRESHOLD_IDS}; "
                f"missing={sorted(missing)}, extra={sorted(extra)}",
            )
        normalized = {
            threshold_id: Decimal(str(thresholds[threshold_id]))
            for threshold_id in REGIME_CLASSIFICATION_THRESHOLD_IDS
        }
    else:
        try:
            normalized = {
                threshold_id: Decimal(str(getattr(thresholds, f"{threshold_id}_min")))
                for threshold_id in REGIME_CLASSIFICATION_THRESHOLD_IDS
            }
        except AttributeError as exc:
            raise ValueError(
                "regime classification thresholds must expose *_min attributes",
            ) from exc
    _validate_regime_thresholds(normalized)
    return normalized


def _validate_regime_thresholds(thresholds: Mapping[str, Decimal]) -> None:
    missing = set(REGIME_CLASSIFICATION_THRESHOLD_IDS) - set(thresholds)
    extra = set(thresholds) - set(REGIME_CLASSIFICATION_THRESHOLD_IDS)
    if missing or extra:
        raise ValueError(
            "regime classification thresholds must exactly match "
            f"{REGIME_CLASSIFICATION_THRESHOLD_IDS}; "
            f"missing={sorted(missing)}, extra={sorted(extra)}",
        )
    previous: Decimal | None = None
    for threshold_id in REGIME_CLASSIFICATION_THRESHOLD_IDS:
        threshold = _score(thresholds[threshold_id], threshold_id)
        if previous is not None and threshold >= previous:
            raise ValueError("regime classification thresholds must decrease")
        previous = threshold


def _normalize_weights(
    weights: Mapping[str, Any],
    *,
    component_ids: tuple[str, ...],
    name: str,
) -> dict[str, Decimal]:
    normalized = {key: Decimal(str(value)) for key, value in weights.items()}
    _validate_weights(normalized, component_ids=component_ids, name=name)
    return normalized


def _validate_weights(
    weights: Mapping[str, Decimal],
    *,
    component_ids: tuple[str, ...],
    name: str,
) -> None:
    missing = set(component_ids) - set(weights)
    extra = set(weights) - set(component_ids)
    if missing or extra:
        raise ValueError(
            f"{name} weights must exactly match {component_ids}; "
            f"missing={sorted(missing)}, extra={sorted(extra)}",
        )
    for component_id, weight in weights.items():
        if weight < 0 or weight > 1:
            raise ValueError(f"{component_id} weight must be between 0 and 1")
    if abs(sum(weights.values()) - Decimal("1")) > Decimal("0.000001"):
        raise ValueError(f"{name} weights must sum to 1.0")


def _optional_score_record(value: Decimal | None, name: str) -> str | None:
    if value is None:
        return None
    _score(value, name)
    return str(value)


def _score(value: Decimal, name: str) -> Decimal:
    if value < 0 or value > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return value
