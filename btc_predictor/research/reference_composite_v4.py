"""Stage-corrected successor to ``BTC_REFERENCE_COMPOSITE_V3``.

V4 changes one decision semantic only: the unchanged ``live_shadow_days >= 90``
gate belongs to post-certification promotion, not to the one-shot historical
verdict that makes a candidate eligible to start live shadow.  The module also
publishes the complete inherited-gate ownership census requested before V4 may
be executed.  Missing implementation ownership is recorded as such; it is
never relabelled as prospective evidence and never filled with a favourable
default.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from btc_predictor.research import reference_composite_v2 as _v2
from btc_predictor.research import reference_composite_v3_convergence as _v3


V4_PROTOCOL_VERSION = "BTC_REFERENCE_COMPOSITE_V4"
V4_PROTOCOL_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V4_PROTOCOL_DEFINITION_V1"
V4_STATUS = "FROZEN_STAGE_OWNERSHIP_CORRECTION"
PARENT_PROTOCOL_VERSION = "BTC_REFERENCE_COMPOSITE_V3"
PARENT_PROTOCOL_DEFINITION_SHA256 = (
    "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
)
CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256 = (
    "8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7"
)
FROZEN_V2_DEFINITION_SHA256 = (
    "bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a"
)

STAGE_HISTORICAL = "SEALED_HISTORICAL_VALIDATION"
STAGE_PROMOTION = "POST_CERTIFICATION_PROMOTION"
V4_STAGES = (STAGE_HISTORICAL, STAGE_PROMOTION)
LIVE_SHADOW_METRIC = "live_shadow_days"
LIVE_SHADOW_THRESHOLD = 90

OUTPUT_NAMESPACE = "research_artifacts/btc019_v4_stage_correction"
PROTOCOL_FILENAME = "reference_composite_v4_protocol.json"
OWNERSHIP_FILENAME = "inherited_gate_ownership.json"
SEMANTIC_DIFF_FILENAME = "v3_to_v4_semantic_diff.json"
REPORT_FILENAME = "V4_STAGE_CORRECTION_REPORT.md"

NO_EXECUTABLE_OWNER = "UNRESOLVED_NO_EXECUTABLE_MEASUREMENT_OWNER"


class V4StageCorrectionError(ValueError):
    """Raised when V4 cannot be reconstructed from its frozen authorities."""


def _canonical_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(payload: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("ascii")).hexdigest()


# These are measurement owners, not merely modules whose output is later
# compared with a gate.  The empty entries are deliberate repository findings:
# the frozen V2 artifact names a rate and threshold but no executable universe,
# denominator, or owner that produces the measurement from the sealed inputs.
_EVIDENCE_OWNERS: dict[str, tuple[str, ...]] = {
    "atr_median_absolute_fractional_difference": (
        "btc_predictor.research.reference_composite_empirical._atr_comparison",
    ),
    "atr_p95_absolute_fractional_difference": (
        "btc_predictor.research.reference_composite_empirical._atr_comparison",
    ),
    "cross_market_confirmed_stop_preservation_rate": (),
    "daily_bucket_usable_rate": (
        "btc_predictor.research.reference_composite_v2.aggregate_v2_reference_bucket",
    ),
    "deterministic_rerun_hash_match": (),
    "gap_through_stop_consensus_agreement_rate": (),
    "historical_fallback_splice_count": (
        "btc_predictor.research.price_source_policy.compare_price_sources",
    ),
    "isolated_venue_stop_suppression_rate": (),
    "live_shadow_days": (),
    "mae_max_absolute_difference": (
        "btc_predictor.research.reference_composite_empirical._trade_path_comparison",
    ),
    "mae_median_absolute_difference": (
        "btc_predictor.research.reference_composite_empirical._trade_path_comparison",
    ),
    "mae_p95_absolute_difference": (
        "btc_predictor.research.reference_composite_empirical._trade_path_comparison",
    ),
    "mfe_max_absolute_difference": (
        "btc_predictor.research.reference_composite_empirical._trade_path_comparison",
    ),
    "mfe_median_absolute_difference": (
        "btc_predictor.research.reference_composite_empirical._trade_path_comparison",
    ),
    "mfe_p95_absolute_difference": (
        "btc_predictor.research.reference_composite_empirical._trade_path_comparison",
    ),
    "point_in_time_violation_count": (
        "btc_predictor.research.reference_composite_v2.build_v2_reference_observation",
    ),
    "provenance_complete_rate": (),
    "raw_observation_mutation_count": (
        "btc_predictor.research.reference_composite_v3_sealed_executor.verify_collected_file_digests",
    ),
    "reference_degraded_rate": (
        "btc_predictor.research.reference_composite_v2.build_v2_reference_observation",
    ),
    "reference_unavailable_rate": (
        "btc_predictor.research.reference_composite_v2.build_v2_reference_observation",
    ),
    "reference_usable_rate": (
        "btc_predictor.research.reference_composite_v2.build_v2_reference_observation",
    ),
    "regime_classification_disagreement_rate": (),
    "risk_size_p95_relative_difference": (),
    "setup_classification_disagreement_rate": (),
    "silent_incomplete_bucket_omission_count": (
        "btc_predictor.research.reference_composite_v2.aggregate_v2_reference_bucket",
    ),
    "stop_touch_disagreement_rate": (
        "btc_predictor.research.reference_composite_empirical._trade_path_comparison",
    ),
    "swing_level_disagreement_rate_above_0_50_atr": (
        "btc_predictor.research.btc019b_diagnostics._swing_metric_summary",
    ),
    "trade_action_disagreement_rate": (),
    "trade_eligibility_disagreement_rate": (),
    "unrecorded_quality_state_count": (
        "btc_predictor.research.reference_composite_v2.build_v2_reference_observation",
    ),
    "validation_period_days": (
        "btc_predictor.research.reference_composite_v3_sealed_executor.validate_sealed_sample_manifest",
    ),
    "venue_disagreement_rate": (
        "btc_predictor.research.reference_composite_v2.build_v2_reference_observation",
    ),
    "weekly_bucket_usable_rate": (
        "btc_predictor.research.reference_composite_v2.aggregate_v2_reference_bucket",
    ),
}

# A related implementation is not automatically an evidence owner.  These
# components are persisted for the ownership audit because they explain why a
# tempting shortcut is non-conforming.  In particular, a hardcoded favourable
# value and an engine without a frozen comparison universe are not owners.
_UNRESOLVED_EXISTING_COMPONENTS: dict[str, tuple[str, ...]] = {
    "cross_market_confirmed_stop_preservation_rate": (
        "btc_predictor.research.reference_composite_empirical._known_event_analysis "
        "(development-event census only; no frozen sealed event universe)",
    ),
    "deterministic_rerun_hash_match": (
        "btc_predictor.research.reference_composite_v3_sealed_executor "
        "(single evidence build; no rerun comparison owner)",
    ),
    "gap_through_stop_consensus_agreement_rate": (
        "btc_predictor.research.reference_composite_empirical._trade_path_comparison "
        "(generic stop probes; no frozen gap-through event classifier)",
    ),
    "isolated_venue_stop_suppression_rate": (
        "btc_predictor.research.reference_composite_empirical._known_event_analysis "
        "(development-event census only; no frozen sealed event universe)",
    ),
    "provenance_complete_rate": (
        "btc_predictor.research.reference_composite_v3_sealed_evidence._inherited_measurements "
        "(hardcoded favourable value; non-conforming)",
    ),
    "regime_classification_disagreement_rate": (
        "Phase-1 regime owners exist; no frozen candidate/reference comparison universe",
    ),
    "risk_size_p95_relative_difference": (
        "Phase-1 risk owners exist; no frozen eligible-trade comparison universe",
    ),
    "setup_classification_disagreement_rate": (
        "Phase-1 setup owners exist; no frozen candidate/reference comparison universe",
    ),
    "trade_action_disagreement_rate": (
        "Phase-1 lifecycle/execution owners exist; no frozen decision comparison universe",
    ),
    "trade_eligibility_disagreement_rate": (
        "Phase-1 setup/veto/entry owners exist; no frozen decision comparison universe",
    ),
}

_OWNER_BLOCKING_REASONS: dict[str, str] = {
    "cross_market_confirmed_stop_preservation_rate": (
        "The frozen gate defines the rate's meaning and threshold but not the sealed "
        "cross-market event census or denominator."
    ),
    "deterministic_rerun_hash_match": (
        "The failed V2 executor builds evidence once and has no measurement owner that "
        "repeats processing over the same VerifiedRawCollection."
    ),
    "gap_through_stop_consensus_agreement_rate": (
        "No frozen owner classifies the sealed gap-through event universe or its "
        "deterministic venue-consensus denominator."
    ),
    "isolated_venue_stop_suppression_rate": (
        "The frozen gate does not define the sealed isolated-wick event census or "
        "candidate suppression denominator."
    ),
    "provenance_complete_rate": (
        "The failed builder hardcodes 1 instead of mechanically evaluating complete "
        "owner/version/input/config/definition provenance for every measurement."
    ),
    "regime_classification_disagreement_rate": (
        "No authority freezes the decision instants, non-price inputs, comparison "
        "reference, or denominator for this reserved Phase-1 consequence gate."
    ),
    "risk_size_p95_relative_difference": (
        "No authority freezes the eligible-trade universe, non-price risk inputs, "
        "comparison reference, or denominator for this reserved gate."
    ),
    "setup_classification_disagreement_rate": (
        "No authority freezes the decision instants, complete setup inputs, comparison "
        "reference, or denominator for this reserved Phase-1 consequence gate."
    ),
    "trade_action_disagreement_rate": (
        "No authority freezes the replay schedule, portfolio state, comparison "
        "reference, or denominator for this reserved Phase-1 consequence gate."
    ),
    "trade_eligibility_disagreement_rate": (
        "No authority freezes the replay schedule, full eligibility inputs, comparison "
        "reference, or denominator for this reserved Phase-1 consequence gate."
    ),
}

_REQUIRED_EVIDENCE: dict[str, str] = {
    "atr_median_absolute_fractional_difference": "candidate daily ATR versus the per-day raw-provider median; median absolute fractional difference",
    "atr_p95_absolute_fractional_difference": "the same daily ATR differences at nearest-rank p95",
    "cross_market_confirmed_stop_preservation_rate": "a declared census of cross-market-confirmed stop events and candidate preservation outcomes",
    "daily_bucket_usable_rate": "the complete V2 daily-bucket census, including unusable incomplete buckets",
    "deterministic_rerun_hash_match": "two processing digests over the same immutable VerifiedRawCollection and identical semantic identities",
    "gap_through_stop_consensus_agreement_rate": "a declared gap-through stop-event universe and deterministic venue-consensus comparison",
    "historical_fallback_splice_count": "fallback_used provenance on every raw/candidate observation",
    "isolated_venue_stop_suppression_rate": "a declared isolated-venue stop-event universe and candidate suppression outcomes",
    "live_shadow_days": "prospective post-certification shadow observations counted in elapsed qualifying days",
    "mae_max_absolute_difference": "candidate-versus-provider-consensus adverse-excursion differences over frozen PIT trade-path probes",
    "mae_median_absolute_difference": "candidate-versus-provider-consensus adverse-excursion differences over frozen PIT trade-path probes",
    "mae_p95_absolute_difference": "candidate-versus-provider-consensus adverse-excursion differences over frozen PIT trade-path probes",
    "mfe_max_absolute_difference": "candidate-versus-provider-consensus favourable-excursion differences over frozen PIT trade-path probes",
    "mfe_median_absolute_difference": "candidate-versus-provider-consensus favourable-excursion differences over frozen PIT trade-path probes",
    "mfe_p95_absolute_difference": "candidate-versus-provider-consensus favourable-excursion differences over frozen PIT trade-path probes",
    "point_in_time_violation_count": "a census of observations whose availability exceeds the decision instant",
    "provenance_complete_rate": "mechanical completeness over every scientific measurement's owner, version, input, config, and definition identity",
    "raw_observation_mutation_count": "manifest-bound raw mutation counts verified against immutable bytes",
    "reference_degraded_rate": "V2 hourly quality-state census",
    "reference_unavailable_rate": "V2 hourly quality-state census",
    "reference_usable_rate": "V2 hourly availability census",
    "regime_classification_disagreement_rate": "a PIT decision universe plus complete Phase-1 regime inputs replayed for candidate and comparison references",
    "risk_size_p95_relative_difference": "a PIT eligible-trade universe plus owner-produced Phase-1 risk sizes for candidate and comparison references",
    "setup_classification_disagreement_rate": "a PIT decision universe plus complete Phase-1 setup inputs replayed for candidate and comparison references",
    "silent_incomplete_bucket_omission_count": "expected V2 daily/weekly buckets reconciled one-for-one to persisted bucket records",
    "stop_touch_disagreement_rate": "candidate-versus-provider-consensus stop outcomes over frozen PIT trade-path probes",
    "swing_level_disagreement_rate_above_0_50_atr": "candidate/raw swing-level pairs and prior ATR under the frozen 0.50-ATR comparison",
    "trade_action_disagreement_rate": "a PIT strategy-decision universe replayed through the Phase-1 strategy, lifecycle, and execution owners",
    "trade_eligibility_disagreement_rate": "a PIT strategy-decision universe replayed through the Phase-1 setup, veto, R/R, and entry owners",
    "unrecorded_quality_state_count": "all V2 hourly quality states reconciled to the frozen vocabulary",
    "validation_period_days": "the authority-bound sealed window duration",
    "venue_disagreement_rate": "V2 hourly quality-state census",
    "weekly_bucket_usable_rate": "the complete V2 weekly-bucket census, including unusable incomplete buckets",
}

_NOT_DERIVABLE_FROM_CURRENT_SEALED_INPUT_CONTRACT = {
    "regime_classification_disagreement_rate",
    "risk_size_p95_relative_difference",
    "setup_classification_disagreement_rate",
    "trade_action_disagreement_rate",
    "trade_eligibility_disagreement_rate",
}


def _authorities(repository_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    parent = _v3.restore_v3_protocol(
        repository_root / _v3.CONVERGENCE_OUTPUT_NAMESPACE
    )
    if parent["definition_sha256"] != PARENT_PROTOCOL_DEFINITION_SHA256:
        raise V4StageCorrectionError("frozen V3 parent hash moved")
    v2 = _v2.frozen_v2_protocol_definition()
    if v2["definition_sha256"] != FROZEN_V2_DEFINITION_SHA256:
        raise V4StageCorrectionError("frozen V2 definition hash moved")
    return parent, v2


def inherited_gate_ownership_table(repository_root: Path) -> list[dict[str, Any]]:
    """Return all 33 inherited gates with their evidence and stage ownership."""

    parent, v2 = _authorities(repository_root)
    source_by_metric = {gate["metric"]: gate for gate in v2["approval_gates"]}
    rows = []
    for gate in sorted(parent["inherited_approval_gates"], key=lambda row: row["metric"]):
        metric = gate["metric"]
        source = source_by_metric.get(metric)
        if source is None:
            raise V4StageCorrectionError(f"{metric} has no frozen V2 source gate")
        expected = {
            "direction": source["direction"],
            "hard": source["hard"],
            "threshold": source["threshold"],
        }
        if any(gate[key] != value for key, value in expected.items()):
            raise V4StageCorrectionError(f"{metric} drifted from its frozen definition")
        frozen_stage = source["validation_stage"]
        stage = STAGE_PROMOTION if metric == LIVE_SHADOW_METRIC else STAGE_HISTORICAL
        if (frozen_stage == "promotion") != (metric == LIVE_SHADOW_METRIC):
            raise V4StageCorrectionError(
                f"additional frozen promotion-stage gate discovered: {metric}"
            )
        owners = _EVIDENCE_OWNERS.get(metric)
        if owners is None:
            raise V4StageCorrectionError(f"{metric} is absent from the ownership census")
        rows.append(
            {
                "authoritative_evidence_owner": list(owners),
                "authoritative_owner_count": len(owners),
                "authoritative_owner_status": (
                    "RESOLVED_EXACTLY_ONE"
                    if len(owners) == 1
                    else NO_EXECUTABLE_OWNER
                ),
                "blocking_reason": _OWNER_BLOCKING_REASONS.get(metric),
                "direction": gate["direction"],
                "existing_repository_owner": (
                    list(owners)
                    if owners
                    else list(_UNRESOLVED_EXISTING_COMPONENTS.get(metric, ()))
                ),
                "hard": gate["hard"],
                "historical_sealed_data_derivable": metric not in (
                    _NOT_DERIVABLE_FROM_CURRENT_SEALED_INPUT_CONTRACT | {LIVE_SHADOW_METRIC}
                ),
                "metric": metric,
                "owner_count": len(owners),
                "pre_existing_nonsealed_evidence": False,
                "prospective_only": metric == LIVE_SHADOW_METRIC,
                "required_evidence": _REQUIRED_EVIDENCE[metric],
                "threshold": gate["threshold"],
                "v3_role": "INHERITED_HARD_APPROVAL_GATE" if gate["hard"] else "INHERITED_SOFT_GATE",
                "v4_stage": stage,
            }
        )
    if len(rows) != 33 or len({row["metric"] for row in rows}) != 33:
        raise V4StageCorrectionError("the inherited ownership table is not exactly 33 gates")
    prospective = [row["metric"] for row in rows if row["prospective_only"]]
    if prospective != [LIVE_SHADOW_METRIC]:
        raise V4StageCorrectionError(
            "V4_STAGE_CORRECTION_BLOCKED_BY_ADDITIONAL_PROSPECTIVE_GATE"
        )
    return rows


def unresolved_stage_a_hard_gate_owners(repository_root: Path) -> tuple[str, ...]:
    return tuple(
        row["metric"]
        for row in inherited_gate_ownership_table(repository_root)
        if row["v4_stage"] == STAGE_HISTORICAL and row["hard"] and row["owner_count"] != 1
    )


def assert_stage_a_hard_gate_owner_completeness(repository_root: Path) -> None:
    unresolved = unresolved_stage_a_hard_gate_owners(repository_root)
    if unresolved:
        raise V4StageCorrectionError(
            "V4_EVIDENCE_PIPELINE_INCOMPLETE: every Stage-A hard gate must have "
            f"exactly one executable evidence owner; unresolved={list(unresolved)}"
        )


def semantic_diff(repository_root: Path) -> dict[str, Any]:
    table = inherited_gate_ownership_table(repository_root)
    payload: dict[str, Any] = {
        "implementation_completeness_changes_are_not_decision_semantics": True,
        "other_gate_definition_changes": [],
        "parent_protocol": PARENT_PROTOCOL_VERSION,
        "parent_protocol_hash": PARENT_PROTOCOL_DEFINITION_SHA256,
        "schema_version": "BTC_REFERENCE_COMPOSITE_V3_TO_V4_SEMANTIC_DIFF_V1",
        "stage_relocations": [
            {
                "direction": "minimum",
                "from": STAGE_HISTORICAL,
                "hard": True,
                "metric": LIVE_SHADOW_METRIC,
                "threshold": LIVE_SHADOW_THRESHOLD,
                "to": STAGE_PROMOTION,
            }
        ],
        "threshold_changes": [],
        "v4_protocol": V4_PROTOCOL_VERSION,
        "verified_gate_count": len(table),
    }
    payload["semantic_diff_sha256"] = _digest(payload)
    return payload


def v4_protocol_definition(repository_root: Path) -> dict[str, Any]:
    parent, _ = _authorities(repository_root)
    table = inherited_gate_ownership_table(repository_root)
    historical = [row["metric"] for row in table if row["v4_stage"] == STAGE_HISTORICAL]
    promotion = [row["metric"] for row in table if row["v4_stage"] == STAGE_PROMOTION]
    inherited = []
    by_metric = {row["metric"]: row for row in table}
    for gate in parent["inherited_approval_gates"]:
        inherited.append({**gate, "v4_stage": by_metric[gate["metric"]]["v4_stage"]})
    payload: dict[str, Any] = {
        "decision_contract": {
            "stage_a": {
                "consequence": "HISTORICAL_CANDIDATE_APPROVED_FOR_LIVE_SHADOW",
                "does_not_claim_live_shadow_occurred": True,
                "hard_gate_count": sum(
                    row["hard"] and row["v4_stage"] == STAGE_HISTORICAL for row in table
                ),
                "inherited_metrics": historical,
                "name": STAGE_HISTORICAL,
                "terminal_historical_result": True,
                "verdicts": ["PASS", "FAIL", "UNDEFINED_INSUFFICIENT_EVIDENCE"],
            },
            "stage_b": {
                "final_production_promotion_requires_pass": True,
                "hard_gate_count": 1,
                "inherited_metrics": promotion,
                "live_shadow_days_already_occurred": False,
                "name": STAGE_PROMOTION,
                "verdicts": ["PASS", "FAIL", "UNDEFINED_INSUFFICIENT_EVIDENCE"],
            },
        },
        "definition_parent_snapshot_sha256": parent["definition_sha256"],
        "inherited_approval_gates": inherited,
        "inherited_gate_ownership": table,
        "parent_protocol": PARENT_PROTOCOL_VERSION,
        "parent_protocol_hash": PARENT_PROTOCOL_DEFINITION_SHA256,
        "production_promotion_authorized": False,
        "reference_policy_version": V4_PROTOCOL_VERSION,
        "research_only": True,
        "sample_governance": parent["sample_governance"],
        "schema_version": V4_PROTOCOL_SCHEMA_VERSION,
        "semantic_diff": semantic_diff(repository_root),
        "stage_architecture": {
            "live_shadow_days_threshold": LIVE_SHADOW_THRESHOLD,
            "post_certification_promotion": promotion,
            "sealed_historical_validation": historical,
            "stages": list(V4_STAGES),
        },
        "status": V4_STATUS,
        "unchanged_parent_semantics": {
            key: parent[key]
            for key in sorted(parent)
            if key not in {
                "definition_sha256",
                "inherited_approval_gates",
                "parent_definition_sha256",
                "parent_protocol_version",
                "reference_policy_version",
                "schema_version",
                "status",
            }
        },
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def verify_v4_definition(repository_root: Path, payload: Mapping[str, Any]) -> None:
    expected = v4_protocol_definition(repository_root)
    if dict(payload) != expected:
        raise V4StageCorrectionError("persisted V4 definition does not reproduce")
    if payload["parent_protocol_hash"] != PARENT_PROTOCOL_DEFINITION_SHA256:
        raise V4StageCorrectionError("V4 names another parent")
    if payload["stage_architecture"]["post_certification_promotion"] != [
        LIVE_SHADOW_METRIC
    ]:
        raise V4StageCorrectionError("V4 moved another gate to promotion")


def write_v4_artifacts(repository_root: Path, output_dir: Path) -> dict[str, Any]:
    protocol = v4_protocol_definition(repository_root)
    ownership = {
        "gate_count": 33,
        "rows": inherited_gate_ownership_table(repository_root),
        "schema_version": "BTC_REFERENCE_COMPOSITE_V4_GATE_OWNERSHIP_V1",
        "unresolved_stage_a_hard_gate_owners": list(
            unresolved_stage_a_hard_gate_owners(repository_root)
        ),
    }
    ownership["ownership_table_sha256"] = _digest(ownership)
    diff = semantic_diff(repository_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / PROTOCOL_FILENAME).write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    (output_dir / OWNERSHIP_FILENAME).write_text(
        json.dumps(ownership, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    (output_dir / SEMANTIC_DIFF_FILENAME).write_text(
        json.dumps(diff, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    (output_dir / REPORT_FILENAME).write_text(
        _report_markdown(protocol, ownership), encoding="ascii"
    )
    return protocol


def _report_markdown(protocol: Mapping[str, Any], ownership: Mapping[str, Any]) -> str:
    lines = [
        "# BTC_REFERENCE_COMPOSITE_V4 Stage Correction",
        "",
        f"- Parent: `{PARENT_PROTOCOL_VERSION}` (`{PARENT_PROTOCOL_DEFINITION_SHA256}`)",
        f"- V4 hash: `{protocol['definition_sha256']}`",
        "- Threshold changes: none",
        "- Stage relocation: `live_shadow_days` only",
        "- `live_shadow_days` threshold: `>= 90` (unchanged)",
        "- Sealed sample collected/opened: no / no",
        "",
        "## Gate ownership",
        "",
        "| metric | role | threshold | direction | authoritative owner count | derivable | prospective | V4 stage |",
        "| --- | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for row in ownership["rows"]:
        lines.append(
            f"| `{row['metric']}` | {'hard' if row['hard'] else 'soft'} | "
            f"`{row['threshold']}` | `{row['direction']}` | {row['owner_count']} | "
            f"{str(row['historical_sealed_data_derivable']).lower()} | "
            f"{str(row['prospective_only']).lower()} | `{row['v4_stage']}` |"
        )
    unresolved = ownership["unresolved_stage_a_hard_gate_owners"]
    lines += [
        "",
        "## Certification disposition",
        "",
        "The stage correction is deterministic and `live_shadow_days` is the sole "
        "prospective-only inherited gate. Executor certification remains fail-closed "
        "because the following Stage-A hard metrics have no executable measurement "
        "owner with a frozen input universe and denominator:",
        "",
    ]
    lines += [f"- `{metric}`" for metric in unresolved]
    lines += ["", "Classification: `V4_EVIDENCE_PIPELINE_INCOMPLETE`", ""]
    return "\n".join(lines)


def restore_v4_artifacts(repository_root: Path, output_dir: Path) -> dict[str, Any]:
    protocol = json.loads((output_dir / PROTOCOL_FILENAME).read_text(encoding="ascii"))
    verify_v4_definition(repository_root, protocol)
    ownership = json.loads((output_dir / OWNERSHIP_FILENAME).read_text(encoding="ascii"))
    digest = ownership.pop("ownership_table_sha256", None)
    if digest != _digest(ownership):
        raise V4StageCorrectionError("persisted ownership table was tampered with")
    ownership["ownership_table_sha256"] = digest
    if ownership["rows"] != inherited_gate_ownership_table(repository_root):
        raise V4StageCorrectionError("persisted ownership table does not reproduce")
    diff = json.loads((output_dir / SEMANTIC_DIFF_FILENAME).read_text(encoding="ascii"))
    if diff != semantic_diff(repository_root):
        raise V4StageCorrectionError("persisted V3-to-V4 diff does not reproduce")
    return protocol


def main() -> None:  # pragma: no cover - operational artifact writer
    root = Path(__file__).resolve().parents[2]
    protocol = write_v4_artifacts(root, root / OUTPUT_NAMESPACE)
    print(protocol["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
