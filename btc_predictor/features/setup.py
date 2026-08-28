"""Setup detector helpers."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any


BULL_TREND_CONTINUATION_SETUP = "BULL_TREND_CONTINUATION"
BULL_TREND_CONTINUATION_FEATURE_ID = "SETUP_BULL_TREND_CONTINUATION"
BULL_TREND_CONTINUATION_REQUIREMENT_KEYS = (
    "regime_min",
    "trend_min",
    "flow_min",
    "positioning_min",
    "structure_min",
    "minimum_rr",
    "require_no_stress",
    "require_no_severe_crowding",
)
BULL_TREND_CONTINUATION_REASON_CODES = (
    "BULL_TREND_CONTINUATION_INPUT_MISSING",
    "BULL_TREND_CONTINUATION_REGIME_TOO_LOW",
    "BULL_TREND_CONTINUATION_TREND_TOO_LOW",
    "BULL_TREND_CONTINUATION_FLOW_TOO_LOW",
    "BULL_TREND_CONTINUATION_POSITIONING_TOO_LOW",
    "BULL_TREND_CONTINUATION_STRUCTURE_TOO_LOW",
    "BULL_TREND_CONTINUATION_STRESS_ACTIVE",
    "BULL_TREND_CONTINUATION_SEVERE_CROWDING_ACTIVE",
    "BULL_TREND_CONTINUATION_RR_TOO_LOW",
)
DEFAULT_BULL_TREND_CONTINUATION_REQUIREMENTS = {
    "regime_min": Decimal("65"),
    "trend_min": Decimal("70"),
    "flow_min": Decimal("55"),
    "positioning_min": Decimal("60"),
    "structure_min": Decimal("70"),
    "minimum_rr": Decimal("2"),
    "require_no_stress": True,
    "require_no_severe_crowding": True,
}


@dataclass(frozen=True)
class BullTrendContinuationInput:
    regime_score: Decimal | None
    trend_score: Decimal | None
    flow_score: Decimal | None
    positioning_score: Decimal | None
    structure_score: Decimal | None
    stress_flagged: bool | None
    severe_crowding_flagged: bool | None
    risk_reward: Decimal | None

    def as_record(self) -> dict[str, str | bool | None]:
        return {
            "regime_score": _optional_score_record(self.regime_score, "regime_score"),
            "trend_score": _optional_score_record(self.trend_score, "trend_score"),
            "flow_score": _optional_score_record(self.flow_score, "flow_score"),
            "positioning_score": _optional_score_record(
                self.positioning_score,
                "positioning_score",
            ),
            "structure_score": _optional_score_record(
                self.structure_score,
                "structure_score",
            ),
            "stress_flagged": _optional_bool_record(
                self.stress_flagged,
                "stress_flagged",
            ),
            "severe_crowding_flagged": _optional_bool_record(
                self.severe_crowding_flagged,
                "severe_crowding_flagged",
            ),
            "risk_reward": (
                str(_non_negative_decimal(self.risk_reward, "risk_reward"))
                if self.risk_reward is not None
                else None
            ),
        }


@dataclass(frozen=True)
class BullTrendContinuationResult:
    feature_id: str
    setup: str
    detected: bool
    inputs: BullTrendContinuationInput
    requirements: dict[str, Decimal | bool]
    config_metadata: dict[str, str]
    complete: bool
    reason_codes: tuple[str, ...] = ()

    @property
    def reason_code(self) -> str | None:
        if self.detected:
            return f"{self.feature_id}_VALID"
        if self.reason_codes:
            return self.reason_codes[0]
        return None

    def as_record(self) -> dict[str, Any]:
        if self.feature_id != BULL_TREND_CONTINUATION_FEATURE_ID:
            raise ValueError("feature_id must be SETUP_BULL_TREND_CONTINUATION")
        if self.setup != BULL_TREND_CONTINUATION_SETUP:
            raise ValueError("setup must be BULL_TREND_CONTINUATION")
        normalized_requirements = _normalize_bull_trend_requirements(self.requirements)
        self.inputs.as_record()
        return {
            "feature_id": self.feature_id,
            "setup": self.setup,
            "detected": self.detected,
            "reason_code": self.reason_code,
            "inputs": self.inputs.as_record(),
            "requirements": {
                key: str(value) if isinstance(value, Decimal) else value
                for key, value in normalized_requirements.items()
            },
            "config_metadata": dict(self.config_metadata),
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def detect_bull_trend_continuation(
    inputs: BullTrendContinuationInput,
    *,
    requirements: Mapping[str, Any] | None = None,
    config_metadata: Mapping[str, str] | None = None,
) -> BullTrendContinuationResult:
    """Evaluate the Bull Trend Continuation hard filters."""

    normalized_requirements = _normalize_bull_trend_requirements(
        requirements or DEFAULT_BULL_TREND_CONTINUATION_REQUIREMENTS,
    )
    input_values = _bull_trend_input_values(inputs)
    reason_codes = []

    if any(value is None for value in input_values.values()):
        reason_codes.append("BULL_TREND_CONTINUATION_INPUT_MISSING")
    _append_score_failure(
        reason_codes,
        value=inputs.regime_score,
        minimum=normalized_requirements["regime_min"],
        reason_code="BULL_TREND_CONTINUATION_REGIME_TOO_LOW",
    )
    _append_score_failure(
        reason_codes,
        value=inputs.trend_score,
        minimum=normalized_requirements["trend_min"],
        reason_code="BULL_TREND_CONTINUATION_TREND_TOO_LOW",
    )
    _append_score_failure(
        reason_codes,
        value=inputs.flow_score,
        minimum=normalized_requirements["flow_min"],
        reason_code="BULL_TREND_CONTINUATION_FLOW_TOO_LOW",
    )
    _append_score_failure(
        reason_codes,
        value=inputs.positioning_score,
        minimum=normalized_requirements["positioning_min"],
        reason_code="BULL_TREND_CONTINUATION_POSITIONING_TOO_LOW",
    )
    _append_score_failure(
        reason_codes,
        value=inputs.structure_score,
        minimum=normalized_requirements["structure_min"],
        reason_code="BULL_TREND_CONTINUATION_STRUCTURE_TOO_LOW",
    )
    if normalized_requirements["require_no_stress"] and inputs.stress_flagged is True:
        reason_codes.append("BULL_TREND_CONTINUATION_STRESS_ACTIVE")
    if (
        normalized_requirements["require_no_severe_crowding"]
        and inputs.severe_crowding_flagged is True
    ):
        reason_codes.append("BULL_TREND_CONTINUATION_SEVERE_CROWDING_ACTIVE")
    if (
        inputs.risk_reward is not None
        and inputs.risk_reward < normalized_requirements["minimum_rr"]
    ):
        reason_codes.append("BULL_TREND_CONTINUATION_RR_TOO_LOW")

    reason_codes = _dedupe_reason_codes(reason_codes)
    return BullTrendContinuationResult(
        feature_id=BULL_TREND_CONTINUATION_FEATURE_ID,
        setup=BULL_TREND_CONTINUATION_SETUP,
        detected=not reason_codes,
        inputs=inputs,
        requirements=normalized_requirements,
        config_metadata=dict(config_metadata or {}),
        complete="BULL_TREND_CONTINUATION_INPUT_MISSING" not in reason_codes,
        reason_codes=reason_codes,
    )


def _normalize_bull_trend_requirements(
    requirements: Mapping[str, Any],
) -> dict[str, Decimal | bool]:
    missing = set(BULL_TREND_CONTINUATION_REQUIREMENT_KEYS) - set(requirements)
    if missing:
        raise ValueError(
            "bull trend continuation requirements missing "
            f"{sorted(missing)}",
        )
    normalized: dict[str, Decimal | bool] = {
        "regime_min": _score(requirements["regime_min"], "regime_min"),
        "trend_min": _score(requirements["trend_min"], "trend_min"),
        "flow_min": _score(requirements["flow_min"], "flow_min"),
        "positioning_min": _score(
            requirements["positioning_min"],
            "positioning_min",
        ),
        "structure_min": _score(requirements["structure_min"], "structure_min"),
        "minimum_rr": _positive_decimal(requirements["minimum_rr"], "minimum_rr"),
        "require_no_stress": _bool(
            requirements["require_no_stress"],
            "require_no_stress",
        ),
        "require_no_severe_crowding": _bool(
            requirements["require_no_severe_crowding"],
            "require_no_severe_crowding",
        ),
    }
    return normalized


def _bull_trend_input_values(
    inputs: BullTrendContinuationInput,
) -> dict[str, Decimal | bool | None]:
    inputs.as_record()
    return {
        "regime_score": inputs.regime_score,
        "trend_score": inputs.trend_score,
        "flow_score": inputs.flow_score,
        "positioning_score": inputs.positioning_score,
        "structure_score": inputs.structure_score,
        "stress_flagged": inputs.stress_flagged,
        "severe_crowding_flagged": inputs.severe_crowding_flagged,
        "risk_reward": inputs.risk_reward,
    }


def _append_score_failure(
    reason_codes: list[str],
    *,
    value: Decimal | None,
    minimum: Decimal | bool,
    reason_code: str,
) -> None:
    if not isinstance(minimum, Decimal):
        raise ValueError("minimum must be decimal")
    if value is not None and value < minimum:
        reason_codes.append(reason_code)


def _optional_score_record(value: Decimal | None, name: str) -> str | None:
    if value is None:
        return None
    return str(_score(value, name))


def _optional_bool_record(value: bool | None, name: str) -> bool | None:
    if value is not None and not isinstance(value, bool):
        raise ValueError(f"{name} must be bool when provided")
    return value


def _score(value: Any, name: str) -> Decimal:
    score = _decimal(value, name)
    if score < 0 or score > 100:
        raise ValueError(f"{name} must be between 0 and 100")
    return score


def _positive_decimal(value: Any, name: str) -> Decimal:
    number = _decimal(value, name)
    if number <= 0:
        raise ValueError(f"{name} must be positive")
    return number


def _non_negative_decimal(value: Any, name: str) -> Decimal:
    number = _decimal(value, name)
    if number < 0:
        raise ValueError(f"{name} must be non-negative")
    return number


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(f"{name} must be bool")
    return value


def _decimal(value: Any, name: str) -> Decimal:
    if value is None or isinstance(value, bool):
        raise ValueError(f"{name} must be numeric")
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"{name} must be numeric") from exc


def _dedupe_reason_codes(reason_codes: list[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(reason_codes))
