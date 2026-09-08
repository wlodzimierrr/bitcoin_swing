"""Two-stage validator for ``BTC_REFERENCE_COMPOSITE_V4``.

The certified V3 validator remains untouched.  This successor delegates every
unchanged scientific calculation to that validator and changes only inherited
gate composition: Stage A evaluates the 32 historical gates, while Stage B
evaluates the unchanged ``live_shadow_days >= 90`` promotion requirement after
a Stage-A pass.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from btc_predictor.research import reference_composite_v3_validator as _v1
from btc_predictor.research import reference_composite_v4 as _v4


VALIDATOR_VERSION = "BTC_REFERENCE_COMPOSITE_V4_VALIDATOR_V1"
VALIDATOR_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V4_VALIDATOR_DEFINITION_V1"
STAGE_A_RECORD_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V4_STAGE_A_RECORD_V1"
STAGE_B_RECORD_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V4_STAGE_B_RECORD_V1"
PARENT_VALIDATOR_VERSION = "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1"
PARENT_VALIDATOR_DEFINITION_SHA256 = (
    "8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7"
)
BOUND_PROTOCOL_VERSION = _v4.V4_PROTOCOL_VERSION

OUTPUT_NAMESPACE = "research_artifacts/btc019_v4_validator"
DEFINITION_FILENAME = "validator_definition.json"
REPORT_FILENAME = "V4_VALIDATOR_REPORT.md"

STAGE_A_PASS_CONSEQUENCE = "HISTORICAL_CANDIDATE_APPROVED_FOR_LIVE_SHADOW"
STAGE_A_NON_APPROVAL_CONSEQUENCE = "HISTORICAL_CANDIDATE_NOT_APPROVED"
STAGE_B_PASS_CONSEQUENCE = "CANDIDATE_ELIGIBLE_FOR_MANUAL_PRODUCTION_PROMOTION"
STAGE_B_BLOCKED_CONSEQUENCE = "CANDIDATE_NOT_ELIGIBLE_FOR_PRODUCTION_PROMOTION"


class V4ValidatorError(ValueError):
    """Raised when the stage contract or one of its authorities is invalid."""


@dataclass(frozen=True)
class V4ValidationRecord:
    payload: dict[str, Any]

    @property
    def verdict(self) -> str:
        return self.payload["verdict"]

    def as_record(self) -> dict[str, Any]:
        return json.loads(_canonical_json(self.payload))


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


def bind_v4(repository_root: Path) -> dict[str, Any]:
    protocol = _v4.v4_protocol_definition(repository_root)
    if protocol["parent_protocol_hash"] != _v4.PARENT_PROTOCOL_DEFINITION_SHA256:
        raise V4ValidatorError("V4 protocol binds another parent")
    return protocol


def bind_certified_parent_validator(repository_root: Path) -> dict[str, Any]:
    parent = _v1.restore_validator_definition(
        repository_root / _v1.VALIDATOR_OUTPUT_NAMESPACE
    )
    if parent["validator_definition_sha256"] != PARENT_VALIDATOR_DEFINITION_SHA256:
        raise V4ValidatorError("certified V1 validator hash moved")
    return parent


def stage_a_inherited_gate_definitions(
    protocol: Mapping[str, Any],
) -> tuple[dict[str, Any], ...]:
    gates = []
    for gate in protocol["inherited_approval_gates"]:
        if gate["v4_stage"] != _v4.STAGE_HISTORICAL:
            continue
        gates.append(
            {
                "direction": gate["direction"],
                "hard": gate["hard"],
                "metric": gate["metric"],
                "threshold": gate["threshold"],
            }
        )
    gates.sort(key=lambda row: row["metric"])
    if len(gates) != 32:
        raise V4ValidatorError("Stage A must contain exactly 32 inherited gates")
    if sum(row["hard"] for row in gates) != 28:
        raise V4ValidatorError("Stage A must contain 28 inherited hard gates")
    if sum(not row["hard"] for row in gates) != 4:
        raise V4ValidatorError("Stage A must contain 4 inherited soft gates")
    if any(row["metric"] == _v4.LIVE_SHADOW_METRIC for row in gates):
        raise V4ValidatorError("live shadow leaked into Stage A")
    return tuple(gates)


def validator_definition(repository_root: Path) -> dict[str, Any]:
    protocol = bind_v4(repository_root)
    parent = bind_certified_parent_validator(repository_root)
    stage_a_gates = stage_a_inherited_gate_definitions(protocol)
    unresolved = list(_v4.unresolved_stage_a_hard_gate_owners(repository_root))
    payload: dict[str, Any] = {
        "binding": {
            "bound_protocol": BOUND_PROTOCOL_VERSION,
            "bound_protocol_definition_sha256": protocol["definition_sha256"],
            "certified_parent_validator": PARENT_VALIDATOR_VERSION,
            "certified_parent_validator_definition_sha256": parent[
                "validator_definition_sha256"
            ],
        },
        "execution_readiness": {
            "every_stage_a_hard_gate_has_exactly_one_owner": not unresolved,
            "sealed_execution_authorized": False,
            "unresolved_stage_a_hard_gate_owners": unresolved,
        },
        "parent_scientific_contract_reused": {
            "diagnostics": True,
            "hard_requirement_composition": True,
            "pair_certification": True,
            "pair_universes": True,
            "soft_structural_gate": True,
            "transfer_guard": True,
            "wilson_rule": True,
        },
        "schema_version": VALIDATOR_SCHEMA_VERSION,
        "stage_a": {
            "consequence_on_pass": STAGE_A_PASS_CONSEQUENCE,
            "hard_gate_count": 28,
            "inherited_gate_metrics": [row["metric"] for row in stage_a_gates],
            "live_shadow_days_consulted": False,
            "name": _v4.STAGE_HISTORICAL,
            "soft_gate_count": 4,
            "terminal_historical_result": True,
            "verdict_vocabulary": list(_v1.VERDICT_VOCABULARY),
        },
        "stage_b": {
            "consequence_on_pass": STAGE_B_PASS_CONSEQUENCE,
            "direction": "minimum",
            "hard": True,
            "metric": _v4.LIVE_SHADOW_METRIC,
            "name": _v4.STAGE_PROMOTION,
            "requires_stage_a_pass": True,
            "threshold": _v4.LIVE_SHADOW_THRESHOLD,
            "verdict_vocabulary": list(_v1.VERDICT_VOCABULARY),
        },
        "stage_relocation": protocol["semantic_diff"]["stage_relocations"],
        "validator_version": VALIDATOR_VERSION,
    }
    payload["validator_definition_sha256"] = _digest(payload)
    return payload


def validator_definition_sha256(repository_root: Path) -> str:
    return validator_definition(repository_root)["validator_definition_sha256"]


def validate_stage_a_candidate(
    evidence_bundle: Mapping[str, Any], *, repository_root: Path
) -> V4ValidationRecord:
    """Evaluate historical evidence without consulting ``live_shadow_days``."""

    protocol = bind_v4(repository_root)
    contract = validator_definition(repository_root)
    bundle = _v1._require_mapping(evidence_bundle, "the evidence bundle")
    _v1._require_exact_keys(bundle, _v1.BUNDLE_REQUIRED_KEYS, (), "the evidence bundle")
    if bundle["schema_version"] != _v1.EVIDENCE_BUNDLE_SCHEMA_VERSION:
        raise _v1.ValidatorInputError("the evidence bundle carries another schema")

    sample = _v1._require_mapping(bundle["sample"], "the sample block")
    _v1._require_exact_keys(sample, _v1.SAMPLE_REQUIRED_KEYS, (), "the sample block")
    start = _v1._parse_instant(sample["start"], "sample start")
    end = _v1._parse_instant(sample["end"], "sample end")
    if end < start:
        raise _v1.ValidatorInputError("the sample ends before it starts")
    _v1.guard_untouched_validation_sample(
        start=start, end=end, purpose=f"{VALIDATOR_VERSION} DRY_RUN_SYNTHETIC"
    )

    identities = _v1._require_mapping(bundle["identities"], "the identities block")
    _v1._require_exact_keys(
        identities, _v1.IDENTITY_REQUIRED_KEYS, (), "the identities block"
    )
    for field, expected in _v1.BOUND_MEASUREMENT_IDENTITIES.items():
        declared = identities[field]
        actual = tuple(sorted(declared)) if isinstance(declared, list) else declared
        if actual != expected:
            raise _v1.ValidatorInputError(
                f"the bundle declares {field}={declared!r}, expected {expected!r}"
            )

    provenance = _v1._require_mapping(bundle["provenance"], "the provenance block")
    _v1._require_exact_keys(
        provenance, _v1.PROVENANCE_REQUIRED_KEYS, (), "the provenance block"
    )
    for field in ("measurement_record_digest", "sample_manifest_digest"):
        _v1._require_hex_digest(provenance[field], field)

    gate_ids = _v1.required_gate_pair_ids(protocol["unchanged_parent_semantics"])
    guard_ids = _v1.required_transfer_guard_pair_ids(
        protocol["unchanged_parent_semantics"]
    )
    parent = protocol["unchanged_parent_semantics"]
    limit = _v1.operative_structural_limit(parent)
    floor = _v1.operative_comparability_floor(parent)
    quantile = _v1.operative_normal_quantile(parent)
    gates = stage_a_inherited_gate_definitions(protocol)

    gate_measurements = _v1._validate_pair_universe(
        bundle["gate_pair_measurements"],
        required_ids=gate_ids,
        expected_role=_v1.ROLE_APPROVAL_GATE_PAIR,
        metric=_v1.STRUCTURAL_METRIC,
        floor=floor,
        what="gate_pair_measurements",
    )
    guard_measurements = _v1._validate_pair_universe(
        bundle["transfer_guard_pair_measurements"],
        required_ids=guard_ids,
        expected_role=_v1.ROLE_SOURCE_DISPERSION_GUARD_PAIR,
        metric=_v1.STRUCTURAL_METRIC,
        floor=floor,
        what="transfer_guard_pair_measurements",
    )
    soft_measurements = _v1._validate_pair_universe(
        bundle["soft_gate_pair_measurements"],
        required_ids=gate_ids,
        expected_role=_v1.ROLE_APPROVAL_GATE_PAIR,
        metric=_v1.EXACT_TIMESTAMP_METRIC,
        floor=floor,
        what="soft_gate_pair_measurements",
    )
    structural = _v1._structural_gate_requirement(
        gate_measurements,
        required_ids=gate_ids,
        limit=limit,
        quantile=quantile,
        floor=floor,
    )
    guard = _v1._transfer_guard_requirement(
        guard_measurements,
        required_ids=guard_ids,
        limit=limit,
        quantile=quantile,
        floor=floor,
    )
    comparability = _v1._comparability_requirement(
        gate_measurements, required_ids=gate_ids, floor=floor
    )
    completeness = _v1._pair_completeness_requirement(
        gate_measurements,
        required_ids=gate_ids,
        guard_measurements=guard_measurements,
        guard_required_ids=guard_ids,
    )
    not_comparable = _v1._not_comparable_requirement(
        bundle["not_comparable_accounting"]
    )
    derived_level = _v1._derived_level_review_requirement(
        bundle["derived_level_review"],
        required_ids=gate_ids,
        diagnostics=bundle["diagnostics"],
    )
    inherited = _v1._inherited_gate_requirement(
        bundle["inherited_gate_measurements"], gates=gates
    )
    hard = {
        _v1.REQUIREMENT_STRUCTURAL_GATE: structural,
        _v1.REQUIREMENT_TRANSFER_GUARD: guard,
        _v1.REQUIREMENT_COMPARABILITY: comparability,
        _v1.REQUIREMENT_PAIR_COMPLETENESS: completeness,
        _v1.REQUIREMENT_NOT_COMPARABLE: not_comparable,
        _v1.REQUIREMENT_DERIVED_LEVEL_REVIEW: derived_level,
        _v1.REQUIREMENT_INHERITED_GATES: inherited,
    }
    composition = _v1.compose_verdict(
        {name: block["outcome"] for name, block in hard.items()}
    )
    soft = _v1.evaluate_soft_gate(
        {name: soft_measurements.get(name) for name in gate_ids},
        required_pairs=gate_ids,
        limit=limit,
        comparability_floor=floor,
    )
    diagnostics = _v1._validate_diagnostics(bundle["diagnostics"])
    payload: dict[str, Any] = {
        "bound_protocol_definition_sha256": protocol["definition_sha256"],
        "composition": composition,
        "consequence": (
            STAGE_A_PASS_CONSEQUENCE
            if composition["verdict"] == _v1.VERDICT_PASS
            else STAGE_A_NON_APPROVAL_CONSEQUENCE
        ),
        "diagnostics": {
            **diagnostics,
            "can_veto_approval": False,
            "enter_the_hard_composition": False,
        },
        "hard_requirement_outcomes": {
            name: hard[name]["outcome"] for name in sorted(hard)
        },
        "hard_requirements": {name: hard[name] for name in sorted(hard)},
        "input_evidence_digest": _v1.evidence_bundle_digest(bundle),
        "live_shadow_days_consulted": False,
        "primary_reason": composition["primary_reason"],
        "reason_codes": composition["reason_codes"],
        "schema_version": STAGE_A_RECORD_SCHEMA_VERSION,
        "soft_gate": {
            **soft,
            "can_veto_approval": False,
            "enters_the_hard_composition": False,
        },
        "stage": _v4.STAGE_HISTORICAL,
        "terminal_historical_result": True,
        "validator_definition_sha256": contract["validator_definition_sha256"],
        "validator_version": VALIDATOR_VERSION,
        "verdict": composition["verdict"],
    }
    payload["validation_record_digest"] = _digest(payload)
    return V4ValidationRecord(payload)


def evaluate_stage_b_promotion(
    stage_a_record: Mapping[str, Any], *, live_shadow_days: int | None
) -> V4ValidationRecord:
    """Evaluate the unchanged promotion gate after a verified Stage-A result."""

    record = dict(stage_a_record)
    declared_digest = record.pop("validation_record_digest", None)
    if declared_digest != _digest(record):
        raise V4ValidatorError("Stage-A record digest does not reproduce")
    record["validation_record_digest"] = declared_digest
    if record.get("schema_version") != STAGE_A_RECORD_SCHEMA_VERSION:
        raise V4ValidatorError("Stage B requires a V4 Stage-A record")
    if record.get("stage") != _v4.STAGE_HISTORICAL:
        raise V4ValidatorError("Stage B received another stage")
    if live_shadow_days is not None and (
        isinstance(live_shadow_days, bool) or not isinstance(live_shadow_days, int)
    ):
        raise V4ValidatorError("live_shadow_days must be a whole-day count")
    if live_shadow_days is not None and live_shadow_days < 0:
        raise V4ValidatorError("live_shadow_days must be non-negative")

    if record["verdict"] != _v1.VERDICT_PASS:
        verdict = _v1.VERDICT_INSUFFICIENT
        reason = "HISTORICAL_CANDIDATE_NOT_APPROVED"
    elif live_shadow_days is None:
        verdict = _v1.VERDICT_INSUFFICIENT
        reason = "LIVE_SHADOW_EVIDENCE_MISSING"
    elif live_shadow_days < _v4.LIVE_SHADOW_THRESHOLD:
        verdict = _v1.VERDICT_FAIL
        reason = "LIVE_SHADOW_MINIMUM_NOT_MET"
    else:
        verdict = _v1.VERDICT_PASS
        reason = "POST_CERTIFICATION_PROMOTION_REQUIREMENTS_MET"
    payload: dict[str, Any] = {
        "consequence": (
            STAGE_B_PASS_CONSEQUENCE
            if verdict == _v1.VERDICT_PASS
            else STAGE_B_BLOCKED_CONSEQUENCE
        ),
        "direction": "minimum",
        "historical_stage_record_digest": declared_digest,
        "live_shadow_days": live_shadow_days,
        "metric": _v4.LIVE_SHADOW_METRIC,
        "primary_reason": reason,
        "schema_version": STAGE_B_RECORD_SCHEMA_VERSION,
        "stage": _v4.STAGE_PROMOTION,
        "threshold": _v4.LIVE_SHADOW_THRESHOLD,
        "verdict": verdict,
    }
    payload["validation_record_digest"] = _digest(payload)
    return V4ValidationRecord(payload)


def write_validator_artifacts(repository_root: Path, output_dir: Path) -> dict[str, Any]:
    definition = validator_definition(repository_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / DEFINITION_FILENAME).write_text(
        json.dumps(definition, indent=2, sort_keys=True) + "\n", encoding="ascii"
    )
    unresolved = definition["execution_readiness"][
        "unresolved_stage_a_hard_gate_owners"
    ]
    report = "\n".join(
        [
            "# BTC_REFERENCE_COMPOSITE_V4 Validator",
            "",
            f"- Definition hash: `{definition['validator_definition_sha256']}`",
            f"- Bound V4 hash: `{definition['binding']['bound_protocol_definition_sha256']}`",
            f"- Certified parent validator: `{PARENT_VALIDATOR_DEFINITION_SHA256}`",
            "- Stage A consequence on PASS: `HISTORICAL_CANDIDATE_APPROVED_FOR_LIVE_SHADOW`",
            "- Stage B gate: `live_shadow_days >= 90`",
            "- Sealed execution authorized: no",
            "",
            "## Unresolved Stage-A evidence owners",
            "",
            *[f"- `{metric}`" for metric in unresolved],
            "",
            "Classification: `V4_EVIDENCE_PIPELINE_INCOMPLETE`",
            "",
        ]
    )
    (output_dir / REPORT_FILENAME).write_text(report, encoding="ascii")
    return definition


def verify_validator_artifacts(repository_root: Path, output_dir: Path) -> dict[str, Any]:
    persisted = json.loads((output_dir / DEFINITION_FILENAME).read_text(encoding="ascii"))
    expected = validator_definition(repository_root)
    if persisted != expected:
        raise V4ValidatorError("persisted V4 validator definition does not reproduce")
    return persisted


def main() -> None:  # pragma: no cover
    root = Path(__file__).resolve().parents[2]
    definition = write_validator_artifacts(root, root / OUTPUT_NAMESPACE)
    print(definition["validator_definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
