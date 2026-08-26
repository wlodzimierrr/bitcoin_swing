"""Data-quality gating for predictor recommendations."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

from btc_predictor.data import DerivativesQualityReport, OhlcvQualityReport


DATA_QUALITY_FAIL_REASON_CODE = "DATA_QUALITY_FAIL"
DATA_QUALITY_BLOCKED_ACTIONS = ("ENTER", "ADD")
RECOMMENDATION_ACTIONS = ("NO_TRADE", "WATCH", "ENTER", "HOLD", "ADD", "TRIM", "EXIT")
RECOMMENDATION_REASON_SEVERITIES = ("info", "warning", "veto")

QualityReport = OhlcvQualityReport | DerivativesQualityReport


@dataclass(frozen=True)
class DataQualityFailure:
    source_component: str
    reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        if not self.source_component.strip():
            raise ValueError("source_component must be a non-empty string")
        if not self.reason_codes:
            raise ValueError("reason_codes must contain at least one code")
        for reason_code in self.reason_codes:
            if not reason_code.strip():
                raise ValueError("reason_codes must contain non-empty codes")


@dataclass(frozen=True)
class RecommendationReasonCode:
    code: str
    source_component: str
    severity: str
    detail: str

    def __post_init__(self) -> None:
        if not self.code.strip():
            raise ValueError("code must be a non-empty string")
        if not self.source_component.strip():
            raise ValueError("source_component must be a non-empty string")
        if self.severity not in RECOMMENDATION_REASON_SEVERITIES:
            raise ValueError(f"Unsupported recommendation reason severity: {self.severity}")
        if not self.detail.strip():
            raise ValueError("detail must be a non-empty string")

    def as_record(self, *, recommendation_id: int, reason_rank: int) -> dict[str, Any]:
        if recommendation_id < 1:
            raise ValueError("recommendation_id must be positive")
        if reason_rank < 0:
            raise ValueError("reason_rank must be >= 0")
        return {
            "recommendation_id": recommendation_id,
            "reason_rank": reason_rank,
            "code": self.code,
            "source_component": self.source_component,
            "severity": self.severity,
            "detail": self.detail,
        }


@dataclass(frozen=True)
class DataQualityGatedRecommendation:
    requested_action: str
    action: str
    data_quality_fail: bool
    reason_codes: tuple[RecommendationReasonCode, ...]
    existing_position_state: Mapping[str, Any] = field(default_factory=dict)

    @property
    def blocked_by_data_quality(self) -> bool:
        return self.data_quality_fail and self.requested_action in DATA_QUALITY_BLOCKED_ACTIONS


def failures_from_quality_reports(
    reports: Mapping[str, QualityReport],
) -> tuple[DataQualityFailure, ...]:
    """Convert failed quality reports into stable predictor failure inputs."""

    failures = []
    for source_component in sorted(reports):
        report = reports[source_component]
        if not report.is_valid:
            failures.append(
                DataQualityFailure(
                    source_component=source_component,
                    reason_codes=report.reason_codes,
                )
            )
    return tuple(failures)


def apply_data_quality_gate(
    requested_action: str,
    failures: Sequence[DataQualityFailure],
    *,
    existing_position_state: Mapping[str, Any] | None = None,
) -> DataQualityGatedRecommendation:
    """Apply the DATA_QUALITY_FAIL veto to new trade and add recommendations."""

    _validate_action(requested_action)
    ordered_failures = tuple(sorted(failures, key=lambda failure: failure.source_component))
    data_quality_fail = bool(ordered_failures)
    action = _blocked_action(requested_action) if data_quality_fail else requested_action
    reason_codes = _data_quality_reason_codes(
        requested_action=requested_action,
        failures=ordered_failures,
    )
    return DataQualityGatedRecommendation(
        requested_action=requested_action,
        action=action,
        data_quality_fail=data_quality_fail,
        reason_codes=reason_codes,
        existing_position_state=dict(existing_position_state or {}),
    )


def build_recommendation_reason_code_records(
    recommendation_id: int,
    reason_codes: Sequence[RecommendationReasonCode],
) -> tuple[dict[str, Any], ...]:
    """Build ordered rows for signals.recommendation_reason_codes."""

    return tuple(
        reason_code.as_record(recommendation_id=recommendation_id, reason_rank=rank)
        for rank, reason_code in enumerate(reason_codes)
    )


def _data_quality_reason_codes(
    *,
    requested_action: str,
    failures: Sequence[DataQualityFailure],
) -> tuple[RecommendationReasonCode, ...]:
    if not failures:
        return ()

    reasons = [
        RecommendationReasonCode(
            code=DATA_QUALITY_FAIL_REASON_CODE,
            source_component="data_quality",
            severity="veto" if requested_action in DATA_QUALITY_BLOCKED_ACTIONS else "warning",
            detail=(
                "Critical data quality failure blocks new trade and add actions."
                if requested_action in DATA_QUALITY_BLOCKED_ACTIONS
                else "Critical data quality failure present while preserving existing-position action."
            ),
        )
    ]
    for failure in failures:
        for reason_code in failure.reason_codes:
            reasons.append(
                RecommendationReasonCode(
                    code=reason_code,
                    source_component=failure.source_component,
                    severity="veto" if requested_action in DATA_QUALITY_BLOCKED_ACTIONS else "warning",
                    detail=f"Data quality failure from {failure.source_component}: {reason_code}",
                )
            )
    return tuple(reasons)


def _blocked_action(requested_action: str) -> str:
    if requested_action == "ENTER":
        return "NO_TRADE"
    if requested_action == "ADD":
        return "HOLD"
    return requested_action


def _validate_action(action: str) -> None:
    if action not in RECOMMENDATION_ACTIONS:
        raise ValueError(f"Unsupported recommendation action: {action}")
