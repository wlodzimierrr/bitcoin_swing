"""Controlled, manual strategy promotion workflow (BTC-193).

The promotion boundary composes evidence owned by BTC-182, BTC-185, BTC-189,
and BTC-192.  It does not reinterpret their metrics and it deliberately does
not define an automatic pass/fail threshold: the Rulebook does not provide
one.  Instead, it proves that a complete evidence chain belongs to the exact
current-production and candidate configuration identities, then waits for an
explicit manual decision.

An approved decision creates an immutable production-release record.  Nothing
in this module reads, writes, replaces, or reloads live strategy configuration;
deployment remains a separate operational action.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from typing import Any

from btc_predictor.backtest.threshold_sweeps import (
    ThresholdSweepReport,
    restore_threshold_sweep_report,
)
from btc_predictor.backtest.walk_forward import (
    WalkForwardValidation,
    restore_walk_forward_validation,
)
from btc_predictor.config.strategy import ConfigIdentity
from btc_predictor.research.component_ablation import (
    ComponentAblationReport,
    restore_component_ablation_report,
)
from btc_predictor.research.predictor_diagnostics import (
    PredictorDiagnosticsReport,
    restore_predictor_diagnostics_report,
)
from btc_predictor.research.strategy_comparison import (
    HISTORICAL_BACKTEST,
    PAPER_TRADE,
    StrategyComparisonReport,
    StrategyVariant,
    restore_strategy_comparison_report,
)


STRATEGY_PROMOTION_FEATURE_ID = "CONTROLLED_STRATEGY_PROMOTION"
STRATEGY_PROMOTION_POLICY_VERSION = "CONTROLLED_STRATEGY_PROMOTION_V1"
STRATEGY_PROMOTION_EVIDENCE_POLICY_VERSION = (
    "EXACT_IDENTITY_REPLAYABLE_EVIDENCE_CHAIN_V1"
)
STRATEGY_PROMOTION_APPROVAL_POLICY_VERSION = "EXPLICIT_MANUAL_HUMAN_DECISION_V1"
STRATEGY_PROMOTION_DEPLOYMENT_POLICY_VERSION = "RECORD_ONLY_NO_CONFIG_MUTATION_V1"

AWAITING_MANUAL_APPROVAL = "AWAITING_MANUAL_APPROVAL"
PROMOTION_APPROVE = "APPROVE"
PROMOTION_REJECT = "REJECT"
PROMOTION_DECISIONS = (PROMOTION_APPROVE, PROMOTION_REJECT)
PROMOTED = "PROMOTED"
PROMOTION_REJECTED = "REJECTED"
PROMOTION_STATUSES = (PROMOTED, PROMOTION_REJECTED)
MANUAL_HUMAN_APPROVAL = "MANUAL_HUMAN_APPROVAL"

STRATEGY_PROMOTION_PACKET_REASON_CODES = (
    "STRATEGY_PROMOTION_CURRENT_PRODUCTION_BOUND",
    "STRATEGY_PROMOTION_CANDIDATE_VERSIONED",
    "STRATEGY_PROMOTION_PAPER_TRADE_EVIDENCE_BOUND",
    "STRATEGY_PROMOTION_RESEARCH_EVIDENCE_BOUND",
    "STRATEGY_PROMOTION_HISTORICAL_BACKTEST_BOUND",
    "STRATEGY_PROMOTION_WALK_FORWARD_BOUND",
    "STRATEGY_PROMOTION_ROBUSTNESS_EVIDENCE_BOUND",
    "STRATEGY_PROMOTION_EVIDENCE_CHAIN_COMPLETE",
    "STRATEGY_PROMOTION_AWAITING_MANUAL_APPROVAL",
    "STRATEGY_PROMOTION_NO_AUTOMATIC_CONFIG_MUTATION",
)


class StrategyPromotionError(ValueError):
    """Raised when a BTC-193 evidence chain or decision fails closed."""


@dataclass(frozen=True)
class StrategyPromotionPacket:
    """Replayable evidence awaiting a human promotion decision."""

    feature_id: str
    policy_version: str
    evidence_policy_version: str
    approval_policy_version: str
    deployment_policy_version: str
    packet_id: str
    evidence_digest: str
    current_production: ConfigIdentity
    candidate: ConfigIdentity
    paper_trade_comparison: StrategyComparisonReport
    predictor_diagnostics: PredictorDiagnosticsReport
    component_ablation: ComponentAblationReport
    historical_backtest_comparison: StrategyComparisonReport
    walk_forward_validation: WalkForwardValidation
    robustness_sweeps: tuple[ThresholdSweepReport, ...]
    status: str
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        _validate_packet(self)
        payload = _packet_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise StrategyPromotionError(
                "strategy promotion packet does not match evidence_digest"
            )
        return {**payload, "evidence_digest": self.evidence_digest}


@dataclass(frozen=True)
class ManualPromotionDecision:
    """An explicit human decision over one immutable promotion packet."""

    policy_version: str
    decision_id: str
    packet_id: str
    decision: str
    approval_method: str
    approver_id: str
    decided_at: datetime
    rationale: str
    reason_codes: tuple[str, ...]

    @property
    def approved(self) -> bool:
        return self.decision == PROMOTION_APPROVE

    def as_record(self) -> dict[str, Any]:
        _validate_decision(self)
        payload = _decision_payload(self)
        if _digest(payload) != self.decision_id:
            raise StrategyPromotionError(
                "manual promotion decision does not match decision_id"
            )
        return {**payload, "decision_id": self.decision_id}


@dataclass(frozen=True)
class StrategyPromotionRecord:
    """Final immutable decision and resulting production identity."""

    feature_id: str
    policy_version: str
    deployment_policy_version: str
    record_id: str
    evidence_digest: str
    packet: StrategyPromotionPacket
    manual_decision: ManualPromotionDecision
    status: str
    previous_production: ConfigIdentity
    candidate: ConfigIdentity
    resulting_production: ConfigIdentity
    effective_at: datetime | None
    config_mutation_performed: bool
    reason_codes: tuple[str, ...]

    def as_record(self) -> dict[str, Any]:
        _validate_promotion_record(self)
        payload = _promotion_record_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise StrategyPromotionError(
                "strategy promotion record does not match evidence_digest"
            )
        return {**payload, "evidence_digest": self.evidence_digest}


def prepare_strategy_promotion(
    *,
    current_production: ConfigIdentity,
    candidate: ConfigIdentity,
    paper_trade_comparison: StrategyComparisonReport,
    predictor_diagnostics: PredictorDiagnosticsReport,
    component_ablation: ComponentAblationReport,
    historical_backtest_comparison: StrategyComparisonReport,
    walk_forward_validation: WalkForwardValidation,
    robustness_sweeps: Sequence[ThresholdSweepReport],
) -> StrategyPromotionPacket:
    """Bind the complete evidence chain and stop for manual approval.

    The source reports remain the authoritative metric owners.  This function
    verifies completeness, replayability, evidence mode, and exact strategy /
    parameter / configuration identity only; it does not invent a statistical
    promotion threshold.
    """

    _validate_identity(current_production, "current_production")
    _validate_identity(candidate, "candidate")
    if _identity_record(current_production) == _identity_record(candidate):
        raise StrategyPromotionError(
            "candidate must have a new versioned configuration identity"
        )
    sweeps = tuple(robustness_sweeps)
    if not sweeps:
        raise StrategyPromotionError(
            "at least one BTC-185 robustness sweep is required"
        )
    if any(not isinstance(item, ThresholdSweepReport) for item in sweeps):
        raise TypeError("robustness_sweeps must contain ThresholdSweepReport values")
    ordered_sweeps = tuple(
        sorted(sweeps, key=lambda item: (item.parameter, item.report_id))
    )
    if len({item.report_id for item in ordered_sweeps}) != len(ordered_sweeps):
        raise StrategyPromotionError("robustness sweep report IDs must be unique")
    if len({item.parameter for item in ordered_sweeps}) != len(ordered_sweeps):
        raise StrategyPromotionError(
            "only one robustness sweep may represent each parameter"
        )

    packet = StrategyPromotionPacket(
        feature_id=STRATEGY_PROMOTION_FEATURE_ID,
        policy_version=STRATEGY_PROMOTION_POLICY_VERSION,
        evidence_policy_version=STRATEGY_PROMOTION_EVIDENCE_POLICY_VERSION,
        approval_policy_version=STRATEGY_PROMOTION_APPROVAL_POLICY_VERSION,
        deployment_policy_version=STRATEGY_PROMOTION_DEPLOYMENT_POLICY_VERSION,
        packet_id="",
        evidence_digest="",
        current_production=current_production,
        candidate=candidate,
        paper_trade_comparison=paper_trade_comparison,
        predictor_diagnostics=predictor_diagnostics,
        component_ablation=component_ablation,
        historical_backtest_comparison=historical_backtest_comparison,
        walk_forward_validation=walk_forward_validation,
        robustness_sweeps=ordered_sweeps,
        status=AWAITING_MANUAL_APPROVAL,
        reason_codes=STRATEGY_PROMOTION_PACKET_REASON_CODES,
    )
    packet = replace(packet, packet_id=_packet_id(packet))
    _validate_packet(packet, allow_empty_digest=True)
    return replace(packet, evidence_digest=_digest(_packet_payload(packet)))


def record_manual_promotion_decision(
    packet: StrategyPromotionPacket,
    *,
    decision: str,
    approver_id: str,
    decided_at: datetime,
    rationale: str,
) -> ManualPromotionDecision:
    """Create the explicit manual decision required before finalization."""

    if not isinstance(packet, StrategyPromotionPacket):
        raise TypeError("packet must be a StrategyPromotionPacket")
    packet.as_record()
    resolved_decision = _member(decision, PROMOTION_DECISIONS, "decision")
    codes = (
        "STRATEGY_PROMOTION_MANUAL_APPROVAL_RECORDED",
        (
            "STRATEGY_PROMOTION_MANUALLY_APPROVED"
            if resolved_decision == PROMOTION_APPROVE
            else "STRATEGY_PROMOTION_MANUALLY_REJECTED"
        ),
    )
    result = ManualPromotionDecision(
        policy_version=STRATEGY_PROMOTION_APPROVAL_POLICY_VERSION,
        decision_id="",
        packet_id=packet.packet_id,
        decision=resolved_decision,
        approval_method=MANUAL_HUMAN_APPROVAL,
        approver_id=_non_empty(approver_id, "approver_id"),
        decided_at=_utc_datetime(decided_at, "decided_at"),
        rationale=_non_empty(rationale, "rationale"),
        reason_codes=codes,
    )
    result = replace(result, decision_id=_digest(_decision_payload(result)))
    _validate_decision(result)
    return result


def finalize_strategy_promotion(
    packet: StrategyPromotionPacket,
    manual_decision: ManualPromotionDecision,
) -> StrategyPromotionRecord:
    """Record the human outcome without mutating live configuration."""

    if not isinstance(packet, StrategyPromotionPacket):
        raise TypeError("packet must be a StrategyPromotionPacket")
    if not isinstance(manual_decision, ManualPromotionDecision):
        raise TypeError("manual_decision must be a ManualPromotionDecision")
    packet.as_record()
    manual_decision.as_record()
    if manual_decision.packet_id != packet.packet_id:
        raise StrategyPromotionError(
            "manual decision must reference the exact promotion packet"
        )
    approved = manual_decision.approved
    status = PROMOTED if approved else PROMOTION_REJECTED
    resulting = packet.candidate if approved else packet.current_production
    reason_codes = (
        "STRATEGY_PROMOTION_MANUAL_DECISION_ENFORCED",
        (
            "STRATEGY_PROMOTION_NEW_PRODUCTION_VERSION_RECORDED"
            if approved
            else "STRATEGY_PROMOTION_CURRENT_PRODUCTION_RETAINED"
        ),
        "STRATEGY_PROMOTION_CONFIG_MUTATION_NOT_PERFORMED",
        "STRATEGY_PROMOTION_COMPLETE",
    )
    record = StrategyPromotionRecord(
        feature_id=STRATEGY_PROMOTION_FEATURE_ID,
        policy_version=STRATEGY_PROMOTION_POLICY_VERSION,
        deployment_policy_version=STRATEGY_PROMOTION_DEPLOYMENT_POLICY_VERSION,
        record_id="",
        evidence_digest="",
        packet=packet,
        manual_decision=manual_decision,
        status=status,
        previous_production=packet.current_production,
        candidate=packet.candidate,
        resulting_production=resulting,
        effective_at=manual_decision.decided_at if approved else None,
        config_mutation_performed=False,
        reason_codes=reason_codes,
    )
    record = replace(record, record_id=_promotion_record_id(record))
    _validate_promotion_record(record, allow_empty_digest=True)
    return replace(record, evidence_digest=_digest(_promotion_record_payload(record)))


def restore_strategy_promotion_packet(
    record: Mapping[str, Any],
) -> StrategyPromotionPacket:
    """Restore a packet and reject missing, substituted, or edited evidence."""

    source = _mapping(record, "record")
    packet = prepare_strategy_promotion(
        current_production=_identity_from_record(
            _mapping(source.get("current_production"), "current_production")
        ),
        candidate=_identity_from_record(
            _mapping(source.get("candidate"), "candidate")
        ),
        paper_trade_comparison=restore_strategy_comparison_report(
            _mapping(source.get("paper_trade_comparison"), "paper_trade_comparison")
        ),
        predictor_diagnostics=restore_predictor_diagnostics_report(
            _mapping(source.get("predictor_diagnostics"), "predictor_diagnostics")
        ),
        component_ablation=restore_component_ablation_report(
            _mapping(source.get("component_ablation"), "component_ablation")
        ),
        historical_backtest_comparison=restore_strategy_comparison_report(
            _mapping(
                source.get("historical_backtest_comparison"),
                "historical_backtest_comparison",
            )
        ),
        walk_forward_validation=restore_walk_forward_validation(
            _mapping(source.get("walk_forward_validation"), "walk_forward_validation")
        ),
        robustness_sweeps=tuple(
            restore_threshold_sweep_report(_mapping(item, "robustness_sweep"))
            for item in _sequence(source.get("robustness_sweeps"), "robustness_sweeps")
        ),
    )
    if packet.as_record() != dict(source):
        raise StrategyPromotionError(
            "record does not match reconstructed strategy promotion packet"
        )
    return packet


def restore_manual_promotion_decision(
    record: Mapping[str, Any],
) -> ManualPromotionDecision:
    """Restore a manual decision and verify its content-addressed identity."""

    source = _mapping(record, "record")
    result = ManualPromotionDecision(
        policy_version=_string(source.get("policy_version"), "policy_version"),
        decision_id=_string(source.get("decision_id"), "decision_id"),
        packet_id=_string(source.get("packet_id"), "packet_id"),
        decision=_string(source.get("decision"), "decision"),
        approval_method=_string(source.get("approval_method"), "approval_method"),
        approver_id=_string(source.get("approver_id"), "approver_id"),
        decided_at=_datetime_from_record(source.get("decided_at"), "decided_at"),
        rationale=_string(source.get("rationale"), "rationale"),
        reason_codes=_string_tuple(source.get("reason_codes"), "reason_codes"),
    )
    if result.as_record() != dict(source):
        raise StrategyPromotionError(
            "record does not match reconstructed manual promotion decision"
        )
    return result


def restore_strategy_promotion_record(
    record: Mapping[str, Any],
) -> StrategyPromotionRecord:
    """Restore the complete decision and reject packet or outcome tampering."""

    source = _mapping(record, "record")
    packet = restore_strategy_promotion_packet(
        _mapping(source.get("packet"), "packet")
    )
    decision = restore_manual_promotion_decision(
        _mapping(source.get("manual_decision"), "manual_decision")
    )
    rebuilt = finalize_strategy_promotion(packet, decision)
    if rebuilt.as_record() != dict(source):
        raise StrategyPromotionError(
            "record does not match reconstructed strategy promotion record"
        )
    return rebuilt


def _validate_packet(
    packet: StrategyPromotionPacket, *, allow_empty_digest: bool = False
) -> None:
    expected = {
        "feature_id": STRATEGY_PROMOTION_FEATURE_ID,
        "policy_version": STRATEGY_PROMOTION_POLICY_VERSION,
        "evidence_policy_version": STRATEGY_PROMOTION_EVIDENCE_POLICY_VERSION,
        "approval_policy_version": STRATEGY_PROMOTION_APPROVAL_POLICY_VERSION,
        "deployment_policy_version": STRATEGY_PROMOTION_DEPLOYMENT_POLICY_VERSION,
        "status": AWAITING_MANUAL_APPROVAL,
        "reason_codes": STRATEGY_PROMOTION_PACKET_REASON_CODES,
    }
    for name, value in expected.items():
        if getattr(packet, name) != value:
            raise StrategyPromotionError(f"{name} must be {value!r}")
    _validate_identity(packet.current_production, "current_production")
    _validate_identity(packet.candidate, "candidate")
    if _identity_record(packet.current_production) == _identity_record(
        packet.candidate
    ):
        raise StrategyPromotionError(
            "candidate must have a new versioned configuration identity"
        )
    current = _identity_record(packet.current_production)
    candidate = _identity_record(packet.candidate)
    _validate_comparison(
        packet.paper_trade_comparison,
        evidence_mode=PAPER_TRADE,
        current=current,
        candidate=candidate,
        name="paper_trade_comparison",
    )
    _validate_comparison(
        packet.historical_backtest_comparison,
        evidence_mode=HISTORICAL_BACKTEST,
        current=current,
        candidate=candidate,
        name="historical_backtest_comparison",
    )
    if not isinstance(packet.walk_forward_validation, WalkForwardValidation):
        raise TypeError("walk_forward_validation must be a WalkForwardValidation")
    packet.walk_forward_validation.as_record()
    if packet.walk_forward_validation.config_metadata != candidate:
        raise StrategyPromotionError(
            "walk-forward evidence must match the exact candidate identity"
        )
    _validate_diagnostics(packet.predictor_diagnostics, candidate)
    _validate_ablation(packet.component_ablation, candidate)
    if not packet.robustness_sweeps:
        raise StrategyPromotionError(
            "at least one BTC-185 robustness sweep is required"
        )
    sweep_keys: list[tuple[str, str]] = []
    for sweep in packet.robustness_sweeps:
        if not isinstance(sweep, ThresholdSweepReport):
            raise TypeError(
                "robustness_sweeps must contain ThresholdSweepReport values"
            )
        sweep.as_record()
        if sweep.config_metadata != candidate:
            raise StrategyPromotionError(
                "robustness evidence must match the exact candidate identity"
            )
        sweep_keys.append((sweep.parameter, sweep.report_id))
    if tuple(sweep_keys) != tuple(sorted(sweep_keys)):
        raise StrategyPromotionError("robustness sweeps must use deterministic order")
    if len({item[1] for item in sweep_keys}) != len(sweep_keys):
        raise StrategyPromotionError("robustness sweep report IDs must be unique")
    if len({item[0] for item in sweep_keys}) != len(sweep_keys):
        raise StrategyPromotionError(
            "only one robustness sweep may represent each parameter"
        )
    if packet.packet_id != _packet_id(packet):
        raise StrategyPromotionError("promotion evidence does not match packet_id")
    if not allow_empty_digest:
        _non_empty(packet.evidence_digest, "evidence_digest")


def _validate_comparison(
    report: StrategyComparisonReport,
    *,
    evidence_mode: str,
    current: dict[str, str],
    candidate: dict[str, str],
    name: str,
) -> None:
    if not isinstance(report, StrategyComparisonReport):
        raise TypeError(f"{name} must be a StrategyComparisonReport")
    report.as_record()
    if report.evidence_mode != evidence_mode:
        raise StrategyPromotionError(f"{name} must use {evidence_mode} evidence")
    current_variant = StrategyVariant(
        current["strategy_version"], current["parameter_set_id"]
    )
    candidate_variant = StrategyVariant(
        candidate["strategy_version"], candidate["parameter_set_id"]
    )
    if report.baseline != current_variant:
        raise StrategyPromotionError(f"{name} baseline must be current production")
    try:
        current_arm = report.arm(
            current_variant.strategy_version, current_variant.parameter_set_id
        )
        candidate_arm = report.arm(
            candidate_variant.strategy_version, candidate_variant.parameter_set_id
        )
    except KeyError as error:
        raise StrategyPromotionError(
            f"{name} must contain the exact candidate"
        ) from error
    if _config_identity(current_arm.config_metadata, f"{name} baseline") != current:
        raise StrategyPromotionError(
            f"{name} baseline config must match current production"
        )
    if (
        _config_identity(candidate_arm.config_metadata, f"{name} candidate")
        != candidate
    ):
        raise StrategyPromotionError(
            f"{name} candidate config must match the exact candidate identity"
        )


def _validate_diagnostics(
    report: PredictorDiagnosticsReport, candidate: dict[str, str]
) -> None:
    if not isinstance(report, PredictorDiagnosticsReport):
        raise TypeError("predictor_diagnostics must be a PredictorDiagnosticsReport")
    report.as_record()
    definition = _mapping(report.feature_definition, "feature_definition")
    provenance = _mapping(definition.get("provenance"), "feature_definition.provenance")
    observed = {
        key: _string(provenance.get(key), f"feature_definition.provenance.{key}")
        for key in candidate
    }
    if observed != candidate:
        raise StrategyPromotionError(
            "predictor diagnostics must match the exact candidate identity"
        )


def _validate_ablation(
    report: ComponentAblationReport, candidate: dict[str, str]
) -> None:
    if not isinstance(report, ComponentAblationReport):
        raise TypeError("component_ablation must be a ComponentAblationReport")
    report.as_record()
    if report.config_metadata != candidate:
        raise StrategyPromotionError(
            "component ablation must match the exact candidate identity"
        )


def _config_identity(value: Mapping[str, Any], name: str) -> dict[str, str]:
    """Select the configuration identity from richer provenance metadata."""

    return {
        key: _string(value.get(key), f"{name}.{key}")
        for key in ("config_version", "strategy_version", "parameter_set_id")
    }


def _validate_decision(decision: ManualPromotionDecision) -> None:
    if decision.policy_version != STRATEGY_PROMOTION_APPROVAL_POLICY_VERSION:
        raise StrategyPromotionError(
            "manual decision carries the wrong approval policy"
        )
    _non_empty(decision.decision_id, "decision_id")
    _non_empty(decision.packet_id, "packet_id")
    _member(decision.decision, PROMOTION_DECISIONS, "decision")
    if decision.approval_method != MANUAL_HUMAN_APPROVAL:
        raise StrategyPromotionError(
            f"approval_method must be {MANUAL_HUMAN_APPROVAL}"
        )
    _non_empty(decision.approver_id, "approver_id")
    _utc_datetime(decision.decided_at, "decided_at")
    _non_empty(decision.rationale, "rationale")
    expected_codes = (
        "STRATEGY_PROMOTION_MANUAL_APPROVAL_RECORDED",
        (
            "STRATEGY_PROMOTION_MANUALLY_APPROVED"
            if decision.approved
            else "STRATEGY_PROMOTION_MANUALLY_REJECTED"
        ),
    )
    if decision.reason_codes != expected_codes:
        raise StrategyPromotionError(
            "manual decision reason_codes do not match outcome"
        )


def _validate_promotion_record(
    record: StrategyPromotionRecord, *, allow_empty_digest: bool = False
) -> None:
    if record.feature_id != STRATEGY_PROMOTION_FEATURE_ID:
        raise StrategyPromotionError(
            f"feature_id must be {STRATEGY_PROMOTION_FEATURE_ID}"
        )
    if record.policy_version != STRATEGY_PROMOTION_POLICY_VERSION:
        raise StrategyPromotionError(
            f"policy_version must be {STRATEGY_PROMOTION_POLICY_VERSION}"
        )
    if record.deployment_policy_version != STRATEGY_PROMOTION_DEPLOYMENT_POLICY_VERSION:
        raise StrategyPromotionError(
            "promotion record carries the wrong deployment policy"
        )
    record.packet.as_record()
    record.manual_decision.as_record()
    if record.manual_decision.packet_id != record.packet.packet_id:
        raise StrategyPromotionError(
            "manual decision must reference the exact promotion packet"
        )
    approved = record.manual_decision.approved
    expected_status = PROMOTED if approved else PROMOTION_REJECTED
    expected_result = (
        record.packet.candidate if approved else record.packet.current_production
    )
    expected_effective = record.manual_decision.decided_at if approved else None
    expected_codes = (
        "STRATEGY_PROMOTION_MANUAL_DECISION_ENFORCED",
        (
            "STRATEGY_PROMOTION_NEW_PRODUCTION_VERSION_RECORDED"
            if approved
            else "STRATEGY_PROMOTION_CURRENT_PRODUCTION_RETAINED"
        ),
        "STRATEGY_PROMOTION_CONFIG_MUTATION_NOT_PERFORMED",
        "STRATEGY_PROMOTION_COMPLETE",
    )
    if record.status != expected_status:
        raise StrategyPromotionError("promotion status does not match manual decision")
    if record.previous_production != record.packet.current_production:
        raise StrategyPromotionError("previous production does not match packet")
    if record.candidate != record.packet.candidate:
        raise StrategyPromotionError("candidate does not match packet")
    if record.resulting_production != expected_result:
        raise StrategyPromotionError(
            "resulting production does not match manual decision"
        )
    if record.effective_at != expected_effective:
        raise StrategyPromotionError("effective_at does not match manual decision")
    if record.config_mutation_performed:
        raise StrategyPromotionError("BTC-193 must not mutate live configuration")
    if record.reason_codes != expected_codes:
        raise StrategyPromotionError(
            "promotion record reason_codes do not match outcome"
        )
    if record.record_id != _promotion_record_id(record):
        raise StrategyPromotionError("promotion outcome does not match record_id")
    if not allow_empty_digest:
        _non_empty(record.evidence_digest, "evidence_digest")


def _packet_id(packet: StrategyPromotionPacket) -> str:
    return _digest(
        {
            "policy_version": packet.policy_version,
            "current_production": _identity_record(packet.current_production),
            "candidate": _identity_record(packet.candidate),
            "paper_comparison_id": packet.paper_trade_comparison.comparison_id,
            "predictor_diagnostics_id": packet.predictor_diagnostics.report_id,
            "component_ablation_id": packet.component_ablation.report_id,
            "historical_comparison_id": (
                packet.historical_backtest_comparison.comparison_id
            ),
            "walk_forward_validation_id": (
                packet.walk_forward_validation.validation_id
            ),
            "robustness_report_ids": [
                item.report_id for item in packet.robustness_sweeps
            ],
        }
    )


def _packet_payload(packet: StrategyPromotionPacket) -> dict[str, Any]:
    return {
        "feature_id": packet.feature_id,
        "policy_version": packet.policy_version,
        "evidence_policy_version": packet.evidence_policy_version,
        "approval_policy_version": packet.approval_policy_version,
        "deployment_policy_version": packet.deployment_policy_version,
        "packet_id": packet.packet_id,
        "current_production": _identity_record(packet.current_production),
        "candidate": _identity_record(packet.candidate),
        "paper_trade_comparison": packet.paper_trade_comparison.as_record(),
        "predictor_diagnostics": packet.predictor_diagnostics.as_record(),
        "component_ablation": packet.component_ablation.as_record(),
        "historical_backtest_comparison": (
            packet.historical_backtest_comparison.as_record()
        ),
        "walk_forward_validation": packet.walk_forward_validation.as_record(),
        "robustness_sweeps": [item.as_record() for item in packet.robustness_sweeps],
        "status": packet.status,
        "reason_codes": list(packet.reason_codes),
    }


def _decision_payload(decision: ManualPromotionDecision) -> dict[str, Any]:
    return {
        "policy_version": decision.policy_version,
        "packet_id": decision.packet_id,
        "decision": decision.decision,
        "approval_method": decision.approval_method,
        "approver_id": decision.approver_id,
        "decided_at": decision.decided_at.isoformat(),
        "rationale": decision.rationale,
        "reason_codes": list(decision.reason_codes),
    }


def _promotion_record_id(record: StrategyPromotionRecord) -> str:
    return _digest(
        {
            "policy_version": record.policy_version,
            "packet_id": record.packet.packet_id,
            "decision_id": record.manual_decision.decision_id,
            "status": record.status,
            "resulting_production": _identity_record(record.resulting_production),
        }
    )


def _promotion_record_payload(record: StrategyPromotionRecord) -> dict[str, Any]:
    return {
        "feature_id": record.feature_id,
        "policy_version": record.policy_version,
        "deployment_policy_version": record.deployment_policy_version,
        "record_id": record.record_id,
        "packet": record.packet.as_record(),
        "manual_decision": record.manual_decision.as_record(),
        "status": record.status,
        "previous_production": _identity_record(record.previous_production),
        "candidate": _identity_record(record.candidate),
        "resulting_production": _identity_record(record.resulting_production),
        "effective_at": (
            None if record.effective_at is None else record.effective_at.isoformat()
        ),
        "config_mutation_performed": record.config_mutation_performed,
        "reason_codes": list(record.reason_codes),
    }


def _validate_identity(identity: ConfigIdentity, name: str) -> None:
    if not isinstance(identity, ConfigIdentity):
        raise TypeError(f"{name} must be a ConfigIdentity")
    for field_name, value in _identity_record(identity).items():
        _non_empty(value, f"{name}.{field_name}")


def _identity_record(identity: ConfigIdentity) -> dict[str, str]:
    return {
        "config_version": identity.config_version,
        "strategy_version": identity.strategy_version,
        "parameter_set_id": identity.parameter_set_id,
    }


def _identity_from_record(record: Mapping[str, Any]) -> ConfigIdentity:
    return ConfigIdentity(
        config_version=_string(record.get("config_version"), "config_version"),
        strategy_version=_string(record.get("strategy_version"), "strategy_version"),
        parameter_set_id=_string(record.get("parameter_set_id"), "parameter_set_id"),
    )


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _mapping(value: Any, name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise StrategyPromotionError(f"{name} must be a mapping")
    return value


def _sequence(value: Any, name: str) -> tuple[Any, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise StrategyPromotionError(f"{name} must be a sequence")
    return tuple(value)


def _string_tuple(value: Any, name: str) -> tuple[str, ...]:
    return tuple(_string(item, name) for item in _sequence(value, name))


def _string(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StrategyPromotionError(f"{name} must be a non-empty string")
    return value


def _non_empty(value: str, name: str) -> str:
    return _string(value, name)


def _member(value: str, choices: tuple[str, ...], name: str) -> str:
    resolved = _non_empty(value, name)
    if resolved not in choices:
        raise StrategyPromotionError(f"{name} must be one of {choices}")
    return resolved


def _utc_datetime(value: datetime, name: str) -> datetime:
    if not isinstance(value, datetime):
        raise StrategyPromotionError(f"{name} must be a datetime")
    if value.tzinfo is None or value.utcoffset() is None:
        raise StrategyPromotionError(f"{name} must be timezone-aware UTC")
    if value.utcoffset() != UTC.utcoffset(value):
        raise StrategyPromotionError(f"{name} must use UTC")
    return value


def _datetime_from_record(value: Any, name: str) -> datetime:
    text = _string(value, name)
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as error:
        raise StrategyPromotionError(f"{name} must be an ISO-8601 datetime") from error
    return _utc_datetime(parsed, name)
