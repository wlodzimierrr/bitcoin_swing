"""Three-stage BTC_REFERENCE_COMPOSITE_V5 certification protocol.

V5 classifies inherited gates by the evidence they require.  It does not move
or optimise a threshold.  The repository does not contain the deterministic
full-system integration corpus required by Stage B, so this module persists the
terminal BTC-019 conclusion and deliberately does not issue a validator,
builder, or executor definition.

The two Stage-A integrity measurements that do not require a Stage-B corpus are
real executable owners here: deterministic rerun invokes the supplied Stage-A
transformation twice over one already-verified in-memory collection, and
provenance completeness is calculated from a record-by-record census.
"""

from __future__ import annotations

import hashlib
import importlib
import inspect
import json
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from datetime import datetime
from decimal import Context, Decimal
from pathlib import Path
from typing import Any

from btc_predictor.research import reference_composite_v2 as _v2
from btc_predictor.research import reference_composite_v3_validator as _v1
from btc_predictor.research import reference_composite_v4 as _v4
from btc_predictor.research import reference_composite_v4_validator as _v4_validator


V5_PROTOCOL_VERSION = "BTC_REFERENCE_COMPOSITE_V5"
V5_PROTOCOL_SCHEMA_VERSION = "BTC_REFERENCE_COMPOSITE_V5_PROTOCOL_DEFINITION_V1"
V5_STATUS = "TERMINALLY_BLOCKED_MISSING_INTEGRATION_EVIDENCE"
FINAL_CLASSIFICATION = "BTC019_TERMINALLY_BLOCKED_BY_MISSING_INTEGRATION_EVIDENCE"

PARENT_PROTOCOL_VERSION = _v4.V4_PROTOCOL_VERSION
PARENT_PROTOCOL_DEFINITION_SHA256 = (
    "670ff12dd3d63615e9ddb3be05d65505bab16b50e50c1fd9ad077a4923a3f501"
)
PARENT_VALIDATOR_DEFINITION_SHA256 = (
    "8cf091fb8c0374f876dc54237d0226cea3f11a3d7554f6abae5ba5c1df498c28"
)
FROZEN_V3_DEFINITION_SHA256 = (
    "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
)
CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256 = (
    "8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7"
)

STAGE_A = "SEALED_REFERENCE_VALIDATION"
STAGE_B = "DETERMINISTIC_INTEGRATION_VALIDATION"
STAGE_C = "POST_CERTIFICATION_LIVE_SHADOW"
V5_STAGES = (STAGE_A, STAGE_B, STAGE_C)

STAGE_A_PASS_MEANING = "REFERENCE_CANDIDATE_PASSES_SEALED_SOURCE_VALIDATION"
STAGE_B_PASS_MEANING = (
    "REFERENCE_CANDIDATE_PASSES_DETERMINISTIC_INTEGRATION_VALIDATION"
)
STAGE_C_PASS_MEANING = "REFERENCE_CANDIDATE_SATISFIES_90_DAY_LIVE_SHADOW"

LIVE_SHADOW_METRIC = _v4.LIVE_SHADOW_METRIC
LIVE_SHADOW_THRESHOLD = _v4.LIVE_SHADOW_THRESHOLD

MECHANICAL_STAGE_A_METRICS = (
    "deterministic_rerun_hash_match",
    "provenance_complete_rate",
)
DEVELOPMENT_EVENT_STOP_METRICS = (
    "cross_market_confirmed_stop_preservation_rate",
    "gap_through_stop_consensus_agreement_rate",
    "isolated_venue_stop_suppression_rate",
)
PHASE1_CONSEQUENCE_METRICS = (
    "regime_classification_disagreement_rate",
    "risk_size_p95_relative_difference",
    "setup_classification_disagreement_rate",
    "trade_action_disagreement_rate",
    "trade_eligibility_disagreement_rate",
)
STAGE_B_METRICS = DEVELOPMENT_EVENT_STOP_METRICS + PHASE1_CONSEQUENCE_METRICS

OUTPUT_NAMESPACE = "research_artifacts/btc019_v5_certification_pipeline"
PROTOCOL_FILENAME = "reference_composite_v5_protocol.json"
OWNERSHIP_FILENAME = "stage_ownership.json"
SEMANTIC_DIFF_FILENAME = "v4_to_v5_semantic_diff.json"
CORPUS_ASSESSMENT_FILENAME = "integration_corpus_assessment.json"
REPORT_FILENAME = "V5_TERMINAL_BLOCKER_REPORT.md"

DETERMINISTIC_RERUN_OWNER = (
    "btc_predictor.research.reference_composite_v5."
    "measure_deterministic_rerun_hash_match"
)
PROVENANCE_COMPLETE_OWNER = (
    "btc_predictor.research.reference_composite_v5."
    "measure_provenance_complete_rate"
)
OWNER_VERSION = "BTC_REFERENCE_COMPOSITE_V5_MECHANICAL_STAGE_A_OWNERS_V1"

INTEGRATION_CORPUS_REQUIRED_FIELDS = (
    "evaluation_period",
    "decision_timestamps",
    "eligible_timestamps",
    "non_price_inputs",
    "candidate_reference",
    "comparison_reference",
    "strategy_version",
    "risk_version",
    "lifecycle_version",
    "execution_version",
    "portfolio_initial_state",
    "cost_slippage_configuration",
    "exclusion_rules",
    "denominators",
)

_RATE_CONTEXT = Context(prec=80)
_SHA256_HEX_LENGTH = 64


class V5CertificationError(ValueError):
    """Raised when V5 authority, evidence, or artifact integrity is invalid."""


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )


def _digest(payload: Any) -> str:
    return hashlib.sha256(_canonical_json(payload).encode("ascii")).hexdigest()


def _is_sha256(value: Any) -> bool:
    if not isinstance(value, str) or len(value) != _SHA256_HEX_LENGTH:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True


def _source_closure_sha256(function_names: Sequence[str]) -> str:
    """Hash the declared complete implementation closure for one small owner."""

    sources = []
    for name in function_names:
        owner = globals().get(name)
        if not callable(owner):
            raise V5CertificationError(f"mechanical owner dependency {name!r} moved")
        sources.append({"function": name, "source": inspect.getsource(owner)})
    return _digest(sources)


def _verified_collection_identity(collection: Any) -> str:
    """Fingerprint an already-verified collection without opening any raw path."""

    from btc_predictor.research.reference_composite_v3_sealed_executor import (
        VerifiedRawCollection,
    )

    if not isinstance(collection, VerifiedRawCollection):
        raise V5CertificationError(
            "deterministic rerun requires the executor's VerifiedRawCollection"
        )
    files = []
    for row in collection.files:
        actual_raw_sha256 = hashlib.sha256(row.raw_bytes).hexdigest()
        if actual_raw_sha256 != row.sha256:
            raise V5CertificationError(
                f"verified in-memory raw bytes moved for {row.provider_id}"
            )
        files.append(
            {
                "bars_sha256": hashlib.sha256(repr(row.bars).encode("utf-8")).hexdigest(),
                "provider_id": row.provider_id,
                "raw_sha256": actual_raw_sha256,
                "relative_path": row.relative_path,
            }
        )
    return _digest({"files": files, "manifest": dict(collection.manifest)})


def _transformation_digest(
    evidence: Mapping[str, Any],
    *,
    collection_identity: str,
    configuration_identity: str,
    semantic_dependency_identity: str,
) -> str:
    return _digest(
        {
            "collection_identity": collection_identity,
            "configuration_identity": configuration_identity,
            "evidence": dict(evidence),
            "semantic_dependency_identity": semantic_dependency_identity,
        }
    )


def measure_deterministic_rerun_hash_match(
    collection: Any,
    *,
    transform: Callable[[Any], Mapping[str, Any]],
    frozen_configuration: Mapping[str, Any],
    semantic_dependency_identities: Mapping[str, Any],
) -> dict[str, Any]:
    """Run one complete Stage-A transform twice on the same in-memory input.

    No path is accepted and no raw file is reopened.  Input mutation between
    invocations is a refusal, while two different evidence outputs are a valid
    measured ``False`` rather than an operational error.
    """

    if not callable(transform):
        raise V5CertificationError("the Stage-A transform must be callable")
    collection_identity = _verified_collection_identity(collection)
    configuration_identity = _digest(dict(frozen_configuration))
    dependency_identity = _digest(dict(semantic_dependency_identities))

    first = transform(collection)
    if not isinstance(first, Mapping):
        raise V5CertificationError("the first Stage-A transformation was not a mapping")
    if _verified_collection_identity(collection) != collection_identity:
        raise V5CertificationError("the first Stage-A transformation mutated its input")

    second = transform(collection)
    if not isinstance(second, Mapping):
        raise V5CertificationError("the second Stage-A transformation was not a mapping")
    if _verified_collection_identity(collection) != collection_identity:
        raise V5CertificationError("the second Stage-A transformation mutated its input")

    digest_1 = _transformation_digest(
        first,
        collection_identity=collection_identity,
        configuration_identity=configuration_identity,
        semantic_dependency_identity=dependency_identity,
    )
    digest_2 = _transformation_digest(
        second,
        collection_identity=collection_identity,
        configuration_identity=configuration_identity,
        semantic_dependency_identity=dependency_identity,
    )
    return {
        "authoritative_owner": DETERMINISTIC_RERUN_OWNER,
        "collection_identity": collection_identity,
        "configuration_identity": configuration_identity,
        "digest_1": digest_1,
        "digest_2": digest_2,
        "measurement_id": "deterministic_rerun_hash_match",
        "owner_version_identity": OWNER_VERSION,
        "same_verified_collection_object": True,
        "semantic_dependency_identity": dependency_identity,
        "transformation_invocation_count": 2,
        "value": digest_1 == digest_2,
    }


def _nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _valid_pit_window(value: Any) -> bool:
    if not isinstance(value, Mapping) or set(value) != {
        "available_at_rule",
        "end",
        "start",
    }:
        return False
    if not _nonempty_string(value["available_at_rule"]):
        return False
    try:
        start = datetime.fromisoformat(value["start"])
        end = datetime.fromisoformat(value["end"])
    except (TypeError, ValueError):
        return False
    return (
        start.tzinfo is not None
        and end.tzinfo is not None
        and end >= start
    )


def _validate_provenance_record(
    record: Mapping[str, Any],
    inventory_row: Mapping[str, Any],
    *,
    expected_configuration_identity: str,
    expected_input_identity: str,
    expected_manifest_execution_identity: str,
) -> tuple[bool, list[str]]:
    reasons = []
    expected = {
        "authoritative_owner": inventory_row["authoritative_owner"],
        "measurement_id": inventory_row["measurement_id"],
    }
    for field, value in expected.items():
        if record.get(field) != value:
            reasons.append(f"{field}_mismatch")
    if not _nonempty_string(record.get("owner_version_identity")):
        reasons.append("owner_version_identity_missing")
    elif record["owner_version_identity"] != inventory_row["owner_version_identity"]:
        reasons.append("owner_version_identity_mismatch")
    identity_expectations = {
        "configuration_identity": expected_configuration_identity,
        "input_identity": expected_input_identity,
        "manifest_execution_identity": expected_manifest_execution_identity,
        "semantic_definition_hash": inventory_row["semantic_definition_hash"],
    }
    for field, expected_identity in identity_expectations.items():
        if not _is_sha256(record.get(field)):
            reasons.append(f"{field}_invalid")
        elif record[field] != expected_identity:
            reasons.append(f"{field}_mismatch")
    if not _valid_pit_window(record.get("pit_evaluation_window")):
        reasons.append("pit_evaluation_window_invalid")

    numerator = record.get("numerator")
    denominator = record.get("denominator")
    undefined_reason = record.get("undefined_reason")
    if inventory_row["numerator_denominator_required"]:
        if undefined_reason is not None:
            if not _nonempty_string(undefined_reason):
                reasons.append("undefined_reason_invalid")
            if numerator is not None or denominator is not None:
                reasons.append("undefined_fraction_must_be_null")
        elif (
            isinstance(numerator, bool)
            or not isinstance(numerator, int)
            or isinstance(denominator, bool)
            or not isinstance(denominator, int)
            or denominator <= 0
            or numerator < 0
            or numerator > denominator
        ):
            reasons.append("numerator_denominator_invalid")
    elif numerator is not None or denominator is not None:
        reasons.append("numerator_denominator_not_applicable")
    elif undefined_reason is not None and not _nonempty_string(undefined_reason):
        reasons.append("undefined_reason_invalid")
    return not reasons, reasons


def measure_provenance_complete_rate(
    records: Sequence[Mapping[str, Any]],
    *,
    required_inventory: Sequence[Mapping[str, Any]],
    expected_configuration_identity: str,
    expected_input_identity: str,
    expected_manifest_execution_identity: str,
) -> dict[str, Any]:
    """Measure provenance completeness from the entire frozen inventory census."""

    inventory = [dict(row) for row in required_inventory]
    required_ids = [row.get("measurement_id") for row in inventory]
    if not inventory or any(not _nonempty_string(item) for item in required_ids):
        raise V5CertificationError("the Stage-A measurement inventory is invalid")
    if len(set(required_ids)) != len(required_ids):
        raise V5CertificationError("the Stage-A measurement inventory has duplicates")
    if any(
        not _nonempty_string(row.get("authoritative_owner"))
        or not _nonempty_string(row.get("owner_version_identity"))
        or not _is_sha256(row.get("semantic_definition_hash"))
        or not isinstance(row.get("numerator_denominator_required"), bool)
        for row in inventory
    ):
        raise V5CertificationError("the Stage-A inventory lacks owner/count semantics")
    expected_identities = (
        expected_configuration_identity,
        expected_input_identity,
        expected_manifest_execution_identity,
    )
    if any(not _is_sha256(value) for value in expected_identities):
        raise V5CertificationError("the Stage-A execution identities are invalid")

    supplied = [dict(record) for record in records]
    counts = Counter(record.get("measurement_id") for record in supplied)
    by_id = {
        record.get("measurement_id"): record
        for record in supplied
        if counts[record.get("measurement_id")] == 1
    }
    census = []
    complete_count = 0
    for row in inventory:
        measurement_id = row["measurement_id"]
        if counts[measurement_id] == 0:
            valid, reasons = False, ["measurement_record_missing"]
        elif counts[measurement_id] > 1:
            valid, reasons = False, ["measurement_record_duplicated"]
        else:
            valid, reasons = _validate_provenance_record(
                by_id[measurement_id],
                row,
                expected_configuration_identity=expected_configuration_identity,
                expected_input_identity=expected_input_identity,
                expected_manifest_execution_identity=expected_manifest_execution_identity,
            )
        complete_count += int(valid)
        census.append(
            {
                "complete": valid,
                "measurement_id": measurement_id,
                "reasons": reasons,
            }
        )

    required_set = set(required_ids)
    unexpected = sorted(
        item for item in counts if isinstance(item, str) and item not in required_set
    )
    denominator = len(inventory)
    value = str(
        _RATE_CONTEXT.divide(Decimal(complete_count), Decimal(denominator))
    )
    return {
        "authoritative_owner": PROVENANCE_COMPLETE_OWNER,
        "census": census,
        "denominator": denominator,
        "inventory_identity": _digest(inventory),
        "manifest_execution_identity": expected_manifest_execution_identity,
        "measurement_id": "provenance_complete_rate",
        "numerator": complete_count,
        "owner_version_identity": OWNER_VERSION,
        "configuration_identity": expected_configuration_identity,
        "input_identity": expected_input_identity,
        "unexpected_measurement_ids": unexpected,
        "value": value,
    }


def mechanical_owner_definitions() -> dict[str, dict[str, Any]]:
    rerun_contract = {
        "input": "one already-verified immutable VerifiedRawCollection",
        "invocations": 2,
        "raw_reopen_allowed": False,
        "same_configuration_required": True,
        "same_semantic_dependency_identities_required": True,
        "verdict": "digest_1 == digest_2",
    }
    provenance_contract = {
        "complete_record_fields": [
            "measurement_id",
            "authoritative_owner",
            "owner_version_identity",
            "semantic_definition_hash",
            "input_identity",
            "configuration_identity",
            "manifest_execution_identity",
            "pit_evaluation_window",
            "numerator",
            "denominator",
            "undefined_reason",
        ],
        "derivation": "complete_valid_records / complete_frozen_inventory",
        "execution_identities": "validated against caller-supplied frozen identities",
        "favourable_constant_allowed": False,
    }
    return {
        "deterministic_rerun_hash_match": {
            "authoritative_owner": DETERMINISTIC_RERUN_OWNER,
            "implementation_closure_sha256": _source_closure_sha256(
                (
                    "_canonical_json",
                    "_digest",
                    "_verified_collection_identity",
                    "_transformation_digest",
                    "measure_deterministic_rerun_hash_match",
                )
            ),
            "owner_version_identity": OWNER_VERSION,
            "semantic_contract": rerun_contract,
            "semantic_definition_hash": _digest(rerun_contract),
        },
        "provenance_complete_rate": {
            "authoritative_owner": PROVENANCE_COMPLETE_OWNER,
            "implementation_closure_sha256": _source_closure_sha256(
                (
                    "_canonical_json",
                    "_digest",
                    "_is_sha256",
                    "_nonempty_string",
                    "_valid_pit_window",
                    "_validate_provenance_record",
                    "measure_provenance_complete_rate",
                )
            ),
            "owner_version_identity": OWNER_VERSION,
            "semantic_contract": provenance_contract,
            "semantic_definition_hash": _digest(provenance_contract),
        },
    }


def _owner_is_executable(owner_path: str) -> bool:
    module_name, separator, function_name = owner_path.rpartition(".")
    if not separator:
        return False
    try:
        module = importlib.import_module(module_name)
    except ImportError:
        return False
    return callable(getattr(module, function_name, None))


def _authorities(repository_root: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    v4 = _v4.restore_v4_artifacts(
        repository_root, repository_root / _v4.OUTPUT_NAMESPACE
    )
    if v4["definition_sha256"] != PARENT_PROTOCOL_DEFINITION_SHA256:
        raise V5CertificationError("immutable V4 parent hash moved")
    validator = _v4_validator.verify_validator_artifacts(
        repository_root,
        repository_root / "research_artifacts/btc019_v4_validator",
    )
    if (
        validator["validator_definition_sha256"]
        != PARENT_VALIDATOR_DEFINITION_SHA256
    ):
        raise V5CertificationError("immutable V4 validator hash moved")
    if _v4.PARENT_PROTOCOL_DEFINITION_SHA256 != FROZEN_V3_DEFINITION_SHA256:
        raise V5CertificationError("immutable V3 lineage binding moved")
    if (
        _v4.CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256
        != CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256
    ):
        raise V5CertificationError("certified V1 lineage binding moved")
    return v4, _v2.frozen_v2_protocol_definition()


def _stage_for_metric(metric: str) -> str:
    if metric == LIVE_SHADOW_METRIC:
        return STAGE_C
    if metric in STAGE_B_METRICS:
        return STAGE_B
    return STAGE_A


def inherited_gate_stage_table(repository_root: Path) -> list[dict[str, Any]]:
    """Return all 33 gates with V4 and evidence-dependent V5 ownership."""

    v4, v2 = _authorities(repository_root)
    v4_ownership = {
        row["metric"]: row for row in v4["inherited_gate_ownership"]
    }
    v2_gates = {row["metric"]: row for row in v2["approval_gates"]}
    mechanical = mechanical_owner_definitions()
    rows = []
    for gate in sorted(v4["inherited_approval_gates"], key=lambda item: item["metric"]):
        metric = gate["metric"]
        prior = v4_ownership[metric]
        source = v2_gates[metric]
        stage = _stage_for_metric(metric)
        if metric in mechanical:
            owners = [mechanical[metric]["authoritative_owner"]]
        elif stage == STAGE_A:
            owners = list(prior["authoritative_evidence_owner"])
        else:
            owners = []
        if stage == STAGE_A and (
            len(owners) != 1 or not _owner_is_executable(owners[0])
        ):
            raise V5CertificationError(
                f"Stage-A gate {metric} does not have one executable owner"
            )
        reason = None
        if metric in DEVELOPMENT_EVENT_STOP_METRICS:
            reason = (
                "No authority defines a unique sealed event universe; the only "
                "repository census is development-specific, so this requires a "
                "frozen deterministic integration corpus."
            )
        elif metric in PHASE1_CONSEQUENCE_METRICS:
            reason = (
                "The Phase-1 engines can produce individual consequences, but no "
                "authority freezes their decision universe, complete non-price "
                "inputs, comparison reference, state, or denominator."
            )
        elif metric == LIVE_SHADOW_METRIC:
            reason = "This metric requires genuinely prospective post-certification evidence."
        rows.append(
            {
                "authoritative_evidence_owner": owners,
                "authoritative_owner_count": len(owners),
                "authoritative_owner_executable": (
                    len(owners) == 1 and _owner_is_executable(owners[0])
                ),
                "definition": source["rationale"],
                "definition_source": source["source_of_rationale"],
                "direction": gate["direction"],
                "evidence_dependency_reason": reason,
                "hard": gate["hard"],
                "metric": metric,
                "old_stage": gate["v4_stage"],
                "required_evidence": prior["required_evidence"],
                "role": "HARD" if gate["hard"] else "SOFT",
                "stage_b_frozen_corpus_count": 0 if stage == STAGE_B else None,
                "threshold": gate["threshold"],
                "v5_stage": stage,
            }
        )
    if len(rows) != 33 or len({row["metric"] for row in rows}) != 33:
        raise V5CertificationError("V5 did not classify exactly 33 inherited gates")
    if tuple(row["metric"] for row in rows if row["v5_stage"] == STAGE_B) != tuple(
        sorted(STAGE_B_METRICS)
    ):
        raise V5CertificationError("Stage-B evidence classification moved")
    return rows


def stage_a_measurement_inventory(repository_root: Path) -> list[dict[str, Any]]:
    """Freeze every inherited Stage-A gate record plus V3 structured evidence rows."""

    v4, _ = _authorities(repository_root)
    protocol = _v1.bind_frozen_v3(repository_root)
    rows = []
    for gate in inherited_gate_stage_table(repository_root):
        if gate["v5_stage"] != STAGE_A:
            continue
        rows.append(
            {
                "authoritative_owner": gate["authoritative_evidence_owner"][0],
                "measurement_id": f"inherited_gate:{gate['metric']}",
                "numerator_denominator_required": gate["metric"].endswith("_rate"),
            }
        )

    gate_pairs = _v1.required_gate_pair_ids(protocol)
    guard_pairs = _v1.required_transfer_guard_pair_ids(protocol)
    pair_owner = (
        "btc_predictor.research.reference_composite_v3_sealed_evidence._pair_measurement"
    )
    for pair_id in gate_pairs:
        rows.extend(
            (
                {
                    "authoritative_owner": pair_owner,
                    "measurement_id": f"structural_hard_gate:{pair_id}",
                    "numerator_denominator_required": True,
                },
                {
                    "authoritative_owner": pair_owner,
                    "measurement_id": f"exact_timestamp_soft_gate:{pair_id}",
                    "numerator_denominator_required": True,
                },
                {
                    "authoritative_owner": (
                        "btc_predictor.research.reference_composite_v3_sealed_evidence."
                        "_derived_level_census"
                    ),
                    "measurement_id": f"derived_level_review:{pair_id}",
                    "numerator_denominator_required": False,
                },
            )
        )
        for diagnostic in _v1.DIAGNOSTIC_METRICS:
            rows.append(
                {
                    "authoritative_owner": (
                        "btc_predictor.research.reference_composite_v3_sealed_evidence."
                        "_diagnostic_row"
                    ),
                    "measurement_id": f"diagnostic:{diagnostic}:{pair_id}",
                    "numerator_denominator_required": True,
                }
            )
    for pair_id in guard_pairs:
        rows.append(
            {
                "authoritative_owner": pair_owner,
                "measurement_id": f"source_dispersion_guard:{pair_id}",
                "numerator_denominator_required": True,
            }
        )
    rows.append(
        {
            "authoritative_owner": (
                "btc_predictor.research.reference_composite_v3_sealed_evidence."
                "_comparison_records"
            ),
            "measurement_id": "not_comparable_accounting",
            "numerator_denominator_required": False,
        }
    )
    if len(rows) != len({row["measurement_id"] for row in rows}):
        raise V5CertificationError("Stage-A measurement inventory has duplicate IDs")
    if v4["definition_sha256"] != PARENT_PROTOCOL_DEFINITION_SHA256:
        raise V5CertificationError("Stage-A inventory is not V4-bound")
    gate_semantics = {
        f"inherited_gate:{row['metric']}": {
            "definition": row["definition"],
            "direction": row["direction"],
            "threshold": row["threshold"],
        }
        for row in inherited_gate_stage_table(repository_root)
        if row["v5_stage"] == STAGE_A
    }
    for row in rows:
        row["owner_version_identity"] = (
            OWNER_VERSION
            if row["authoritative_owner"]
            in (DETERMINISTIC_RERUN_OWNER, PROVENANCE_COMPLETE_OWNER)
            else f"V5_BOUND_EXISTING_OWNER::{row['authoritative_owner']}"
        )
        row["semantic_definition_hash"] = _digest(
            {
                "frozen_v3_definition_sha256": FROZEN_V3_DEFINITION_SHA256,
                "measurement_id": row["measurement_id"],
                "numerator_denominator_required": row[
                    "numerator_denominator_required"
                ],
                "owner": row["authoritative_owner"],
                "parent_v4_definition_sha256": PARENT_PROTOCOL_DEFINITION_SHA256,
                "semantic": gate_semantics.get(row["measurement_id"]),
            }
        )
    return sorted(rows, key=lambda row: row["measurement_id"])


def _walk_mappings(value: Any, pointer: str = "$") -> list[tuple[str, Mapping[str, Any]]]:
    found = []
    if isinstance(value, Mapping):
        found.append((pointer, value))
        for key in sorted(value, key=str):
            found.extend(_walk_mappings(value[key], f"{pointer}.{key}"))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            found.extend(_walk_mappings(item, f"{pointer}[{index}]"))
    return found


def _repository_json_inventory(repository_root: Path) -> tuple[list[dict[str, str]], list[dict[str, str]], dict[str, list[str]]]:
    inventory = []
    complete_candidates = []
    occurrences = {field: [] for field in INTEGRATION_CORPUS_REQUIRED_FIELDS}
    output_root = (repository_root / OUTPUT_NAMESPACE).resolve()
    paths = []
    for relative_root in ("data", "research_artifacts"):
        root = repository_root / relative_root
        if root.exists():
            paths.extend(root.rglob("*.json"))
    for path in sorted(paths):
        if output_root in path.resolve().parents:
            continue
        raw = path.read_bytes()
        relative = path.relative_to(repository_root).as_posix()
        inventory.append(
            {"path": relative, "sha256": hashlib.sha256(raw).hexdigest()}
        )
        try:
            payload = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise V5CertificationError(f"repository JSON artifact is invalid: {relative}") from error
        for pointer, mapping in _walk_mappings(payload):
            present = set(mapping) & set(INTEGRATION_CORPUS_REQUIRED_FIELDS)
            for field in sorted(present):
                occurrences[field].append(f"{relative}:{pointer}")
            if set(INTEGRATION_CORPUS_REQUIRED_FIELDS) <= set(mapping):
                complete_candidates.append({"path": relative, "pointer": pointer})
    for field in occurrences:
        occurrences[field] = sorted(set(occurrences[field]))
    return inventory, complete_candidates, occurrences


def integration_corpus_assessment(repository_root: Path) -> dict[str, Any]:
    """Determine whether existing persisted artifacts freeze one Stage-B corpus."""

    inventory, candidates, occurrences = _repository_json_inventory(repository_root)
    field_assessment = {
        field: {
            "exact_key_occurrences": occurrences[field],
            "frozen_by_complete_integration_corpus": bool(candidates),
            "status": (
                "FROZEN_IN_COMPLETE_CORPUS"
                if candidates
                else "MISSING_FROM_COMPLETE_REPRODUCIBLE_INTEGRATION_CORPUS"
            ),
        }
        for field in INTEGRATION_CORPUS_REQUIRED_FIELDS
    }
    payload: dict[str, Any] = {
        "candidate_reference_state": "MEDIAN_OHLC_V2_NOT_CONSTRUCTED_OR_EVALUATED",
        "complete_corpus_candidates": candidates,
        "corpus_definition_sha256": None,
        "field_assessment": field_assessment,
        "final_classification": FINAL_CLASSIFICATION,
        "json_artifact_inventory": inventory,
        "json_artifact_inventory_sha256": _digest(inventory),
        "new_market_evidence_collected": False,
        "required_fields": list(INTEGRATION_CORPUS_REQUIRED_FIELDS),
        "reproducible_integration_corpus_exists": bool(candidates),
        "schema_version": "BTC_REFERENCE_COMPOSITE_V5_INTEGRATION_CORPUS_ASSESSMENT_V1",
        "sealed_sample_opened": False,
        "terminal_reason": (
            "No persisted mapping under data/ or research_artifacts/ freezes all "
            "required Stage-B corpus fields. Existing Phase-1 implementations and "
            "synthetic tests cannot supply missing historical non-price inputs, a "
            "candidate/comparison replay pair, initial portfolio state, or frozen "
            "denominators without manufacturing evidence."
        ),
    }
    payload["assessment_sha256"] = _digest(payload)
    return payload


def v4_to_v5_semantic_diff(repository_root: Path) -> dict[str, Any]:
    """Diff V5 stage ownership against the parent V4 gate semantics.

    The three semantic-change counts are measured against the immutable parent
    gate table, never asserted, so a future edit that moved a threshold,
    direction, or hard/soft role would be counted and refused here.
    """

    v4, _ = _authorities(repository_root)
    parent = {row["metric"]: row for row in v4["inherited_approval_gates"]}
    rows = []
    threshold_changes = 0
    direction_changes = 0
    hard_soft_changes = 0
    for gate in inherited_gate_stage_table(repository_root):
        source = parent[gate["metric"]]
        threshold_changes += int(source["threshold"] != gate["threshold"])
        direction_changes += int(source["direction"] != gate["direction"])
        hard_soft_changes += int(
            bool(source["hard"]) is not (gate["role"] == "HARD")
        )
        rows.append(
            {
                "definition": gate["definition"],
                "direction": gate["direction"],
                "hard_soft_role": gate["role"],
                "metric": gate["metric"],
                "new_stage": gate["v5_stage"],
                "old_stage": gate["old_stage"],
                "old_stage_v5_equivalent": (
                    STAGE_C
                    if gate["old_stage"] == _v4.STAGE_PROMOTION
                    else STAGE_A
                ),
                "threshold": gate["threshold"],
            }
        )
    if threshold_changes or direction_changes or hard_soft_changes:
        raise V5CertificationError(
            "V5 may only change evidence-stage ownership: "
            f"threshold={threshold_changes} direction={direction_changes} "
            f"hard_soft={hard_soft_changes}"
        )
    payload: dict[str, Any] = {
        "direction_change_count": direction_changes,
        "gate_count": len(rows),
        "gate_semantic_diff": rows,
        "hard_soft_change_count": hard_soft_changes,
        "parent_protocol": PARENT_PROTOCOL_VERSION,
        "parent_protocol_definition_sha256": PARENT_PROTOCOL_DEFINITION_SHA256,
        "schema_version": "BTC_REFERENCE_COMPOSITE_V4_TO_V5_SEMANTIC_DIFF_V1",
        "evidence_stage_reassignment_count": sum(
            row["old_stage_v5_equivalent"] != row["new_stage"] for row in rows
        ),
        "stage_label_change_count": sum(
            row["old_stage"] != row["new_stage"] for row in rows
        ),
        "threshold_change_count": threshold_changes,
        "v5_protocol": V5_PROTOCOL_VERSION,
    }
    payload["semantic_diff_sha256"] = _digest(payload)
    return payload


def unresolved_stage_b_hard_gate_owners(repository_root: Path) -> tuple[str, ...]:
    return tuple(
        row["metric"]
        for row in inherited_gate_stage_table(repository_root)
        if row["v5_stage"] == STAGE_B
        and row["hard"]
        and (
            row["authoritative_owner_count"] != 1
            or row["stage_b_frozen_corpus_count"] != 1
        )
    )


def assert_stage_a_hard_gate_owner_completeness(repository_root: Path) -> None:
    unresolved = [
        row["metric"]
        for row in inherited_gate_stage_table(repository_root)
        if row["v5_stage"] == STAGE_A
        and row["hard"]
        and row["authoritative_owner_count"] != 1
    ]
    if unresolved:
        raise V5CertificationError(
            f"Stage-A hard-gate ownership is incomplete: {unresolved}"
        )


def assert_stage_b_issuance_ready(repository_root: Path) -> None:
    assessment = integration_corpus_assessment(repository_root)
    unresolved = unresolved_stage_b_hard_gate_owners(repository_root)
    if not assessment["reproducible_integration_corpus_exists"] or unresolved:
        raise V5CertificationError(
            f"{FINAL_CLASSIFICATION}: unresolved_stage_b={list(unresolved)}"
        )


def synthetic_stage_gate_verdict(
    repository_root: Path,
    *,
    stage: str,
    measurements: Mapping[str, Any],
) -> str:
    """Exercise inherited threshold composition without claiming real evidence."""

    if stage not in (STAGE_A, STAGE_B):
        raise V5CertificationError("synthetic gate composition supports Stage A or B")
    gates = [
        {
            "direction": row["direction"],
            "hard": row["hard"],
            "metric": row["metric"],
            "threshold": row["threshold"],
        }
        for row in inherited_gate_stage_table(repository_root)
        if row["v5_stage"] == stage
    ]
    return _v1._inherited_gate_requirement(measurements, gates=gates)["outcome"]


def synthetic_reachability(repository_root: Path) -> dict[str, Any]:
    """Demonstrate all scientific outcomes without representing them as evidence."""

    result = {}
    for stage in (STAGE_A, STAGE_B):
        gates = [
            row
            for row in inherited_gate_stage_table(repository_root)
            if row["v5_stage"] == stage
        ]
        passing = {row["metric"]: row["threshold"] for row in gates}
        hard = next(row for row in gates if row["hard"])
        failing = dict(passing)
        if hard["direction"] == "maximum":
            failing[hard["metric"]] = str(
                _RATE_CONTEXT.add(Decimal(str(hard["threshold"])), Decimal(1))
            )
        elif hard["direction"] == "minimum":
            failing[hard["metric"]] = str(
                _RATE_CONTEXT.subtract(Decimal(str(hard["threshold"])), Decimal(1))
            )
        elif isinstance(hard["threshold"], bool):
            failing[hard["metric"]] = not hard["threshold"]
        else:
            failing[hard["metric"]] = int(hard["threshold"]) + 1
        insufficient = dict(passing)
        insufficient.pop(hard["metric"])
        outcomes = {
            "fail": synthetic_stage_gate_verdict(
                repository_root, stage=stage, measurements=failing
            ),
            "pass": synthetic_stage_gate_verdict(
                repository_root, stage=stage, measurements=passing
            ),
            "undefined_insufficient_evidence": synthetic_stage_gate_verdict(
                repository_root, stage=stage, measurements=insufficient
            ),
        }
        expected = {
            "fail": _v1.VERDICT_FAIL,
            "pass": _v1.VERDICT_PASS,
            "undefined_insufficient_evidence": _v1.VERDICT_INSUFFICIENT,
        }
        if outcomes != expected:
            raise V5CertificationError(f"{stage} synthetic reachability moved")
        result[stage] = {
            "does_not_claim_real_evidence": True,
            "outcomes": outcomes,
        }
    return result


def v5_protocol_definition(repository_root: Path) -> dict[str, Any]:
    table = inherited_gate_stage_table(repository_root)
    assessment = integration_corpus_assessment(repository_root)
    assert_stage_a_hard_gate_owner_completeness(repository_root)
    if assessment["reproducible_integration_corpus_exists"]:
        raise V5CertificationError(
            "repository evidence changed: this terminal V5 disposition must be rebuilt"
        )
    stages = {
        stage: [row["metric"] for row in table if row["v5_stage"] == stage]
        for stage in V5_STAGES
    }
    payload: dict[str, Any] = {
        "decision_contract": {
            "complete_promotion_chain": [STAGE_A, STAGE_B, STAGE_C],
            "only_complete_chain_authorizes_production_promotion": True,
            "stage_a_pass_meaning": STAGE_A_PASS_MEANING,
            "stage_b_pass_meaning": STAGE_B_PASS_MEANING,
            "stage_c_pass_meaning": STAGE_C_PASS_MEANING,
        },
        "final_classification": FINAL_CLASSIFICATION,
        "inherited_approval_gates": table,
        "integration_corpus_assessment": assessment,
        "issuance": {
            "complete_certification_pipeline_definition_sha256": None,
            "sealed_execution_authorized": False,
            "stage_a_builder_definition_sha256": None,
            "v5_executor_definition_sha256": None,
            "v5_validator_definition_sha256": None,
        },
        "stage_a_readiness": {
            "every_hard_gate_has_exactly_one_executable_owner": True,
            "known_unfixed_live_builder_correctness_findings": [
                "ATR_P95_OWNER_PARITY_NOT_FIXED_BECAUSE_STAGE_B_IS_TERMINALLY_BLOCKED",
                "V2_INCOMPLETE_BUCKET_CENSUS_NOT_FIXED_BECAUSE_STAGE_B_IS_TERMINALLY_BLOCKED",
                "DECIMAL_CONTEXT_INVARIANCE_NOT_FIXED_BECAUSE_STAGE_B_IS_TERMINALLY_BLOCKED",
                "FULL_BUILDER_SEMANTIC_DEPENDENCY_CLOSURE_NOT_FIXED_BECAUSE_STAGE_B_IS_TERMINALLY_BLOCKED",
            ],
            "numerical_correctness_certified": False,
            "provenance_census_executed_on_real_stage_a_evidence": False,
        },
        "lineage": {
            "certified_v1_validator_definition_sha256": CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256,
            "frozen_v3_definition_sha256": FROZEN_V3_DEFINITION_SHA256,
            "parent_v4_definition_sha256": PARENT_PROTOCOL_DEFINITION_SHA256,
            "parent_v4_validator_definition_sha256": PARENT_VALIDATOR_DEFINITION_SHA256,
        },
        "mechanical_stage_a_owners": mechanical_owner_definitions(),
        "no_threshold_optimization": True,
        "parent_protocol": PARENT_PROTOCOL_VERSION,
        "parent_protocol_definition_sha256": PARENT_PROTOCOL_DEFINITION_SHA256,
        "production_promotion_authorized": False,
        "reference_policy_version": V5_PROTOCOL_VERSION,
        "research_only": True,
        "safety": {
            "actual_sealed_sample_collected": False,
            "actual_sealed_sample_opened": False,
            "candidate_evaluated": False,
            "new_market_evidence_collected": False,
        },
        "schema_version": V5_PROTOCOL_SCHEMA_VERSION,
        "stage_a_measurement_inventory": stage_a_measurement_inventory(repository_root),
        "stage_architecture": {
            "stage_a": {
                "hard_gate_count": sum(
                    row["hard"] and row["v5_stage"] == STAGE_A for row in table
                ),
                "metrics": stages[STAGE_A],
                "name": STAGE_A,
            },
            "stage_b": {
                "frozen_corpus_definition_sha256": None,
                "hard_gate_count": sum(
                    row["hard"] and row["v5_stage"] == STAGE_B for row in table
                ),
                "metrics": stages[STAGE_B],
                "name": STAGE_B,
            },
            "stage_c": {
                "direction": "minimum",
                "hard_gate_count": 1,
                "metrics": stages[STAGE_C],
                "name": STAGE_C,
                "requires_stage_a_and_stage_b_certification": True,
                "threshold": LIVE_SHADOW_THRESHOLD,
            },
            "stages": list(V5_STAGES),
        },
        "status": V5_STATUS,
        "synthetic_reachability": synthetic_reachability(repository_root),
        "v4_to_v5_semantic_diff": v4_to_v5_semantic_diff(repository_root),
    }
    payload["definition_sha256"] = _digest(payload)
    return payload


def verify_v5_definition(repository_root: Path, payload: Mapping[str, Any]) -> None:
    expected = v5_protocol_definition(repository_root)
    if dict(payload) != expected:
        raise V5CertificationError("persisted V5 terminal protocol does not reproduce")
    if payload["final_classification"] != FINAL_CLASSIFICATION:
        raise V5CertificationError("V5 terminal classification moved")
    if any(payload["issuance"].values()):
        raise V5CertificationError("a blocked V5 contract issued an execution hash")


def _ownership_artifact(repository_root: Path) -> dict[str, Any]:
    rows = inherited_gate_stage_table(repository_root)
    payload: dict[str, Any] = {
        "every_stage_a_hard_gate_has_exactly_one_owner": all(
            row["authoritative_owner_count"] == 1
            for row in rows
            if row["hard"] and row["v5_stage"] == STAGE_A
        ),
        "every_stage_b_hard_gate_has_exactly_one_owner_and_corpus": False,
        "gate_count": len(rows),
        "rows": rows,
        "schema_version": "BTC_REFERENCE_COMPOSITE_V5_STAGE_OWNERSHIP_V1",
        "unresolved_stage_b_hard_gates": list(
            unresolved_stage_b_hard_gate_owners(repository_root)
        ),
    }
    payload["ownership_sha256"] = _digest(payload)
    return payload


def _report_markdown(protocol: Mapping[str, Any]) -> str:
    stage = protocol["stage_architecture"]
    lines = [
        "# BTC_REFERENCE_COMPOSITE_V5 Terminal Certification-Pipeline Assessment",
        "",
        f"- Parent V4: `{PARENT_PROTOCOL_DEFINITION_SHA256}`",
        f"- V5 protocol hash: `{protocol['definition_sha256']}`",
        f"- Classification: `{FINAL_CLASSIFICATION}`",
        "- Threshold changes: `0`",
        "- Direction changes: `0`",
        "- Hard/soft changes: `0`",
        "- V5 validator / Stage-A builder / executor: not issued",
        "- Sealed sample collected/opened: no / no",
        "- Candidate evaluated: no",
        "- New market evidence collected: no",
        "",
        "## Stage ownership",
        "",
        f"- Stage A -- `{STAGE_A}` ({stage['stage_a']['hard_gate_count']} hard gates)",
        f"- Stage B -- `{STAGE_B}` ({stage['stage_b']['hard_gate_count']} hard gates)",
        f"- Stage C -- `{STAGE_C}` (`live_shadow_days >= 90`)",
        "",
        "The three development-event stop gates move to Stage B because repository "
        "authority specifies only a development-event list, not a unique sealed "
        "event universe. The five Phase-1 consequence gates also move to Stage B "
        "because their full-system non-price and portfolio inputs do not exist in "
        "the sealed-price contract.",
        "",
        "## Terminal corpus finding",
        "",
        protocol["integration_corpus_assessment"]["terminal_reason"],
        "",
        "Existing engines and synthetic fixtures are implementation evidence, not a "
        "historical decision corpus. Freezing them into one now would invent inputs "
        "and denominators after the gate thresholds were already known.",
        "",
        f"Final classification: `{FINAL_CLASSIFICATION}`",
        "",
    ]
    return "\n".join(lines)


def write_v5_artifacts(repository_root: Path, output_dir: Path) -> dict[str, Any]:
    protocol = v5_protocol_definition(repository_root)
    ownership = _ownership_artifact(repository_root)
    diff = v4_to_v5_semantic_diff(repository_root)
    assessment = integration_corpus_assessment(repository_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename, payload in (
        (PROTOCOL_FILENAME, protocol),
        (OWNERSHIP_FILENAME, ownership),
        (SEMANTIC_DIFF_FILENAME, diff),
        (CORPUS_ASSESSMENT_FILENAME, assessment),
    ):
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )
    (output_dir / REPORT_FILENAME).write_text(
        _report_markdown(protocol), encoding="ascii"
    )
    return protocol


def restore_v5_artifacts(repository_root: Path, output_dir: Path) -> dict[str, Any]:
    protocol = json.loads((output_dir / PROTOCOL_FILENAME).read_text(encoding="ascii"))
    verify_v5_definition(repository_root, protocol)
    expected = {
        OWNERSHIP_FILENAME: _ownership_artifact(repository_root),
        SEMANTIC_DIFF_FILENAME: v4_to_v5_semantic_diff(repository_root),
        CORPUS_ASSESSMENT_FILENAME: integration_corpus_assessment(repository_root),
    }
    for filename, value in expected.items():
        persisted = json.loads((output_dir / filename).read_text(encoding="ascii"))
        if persisted != value:
            raise V5CertificationError(f"persisted {filename} does not reproduce")
    if (output_dir / REPORT_FILENAME).read_text(encoding="ascii") != _report_markdown(
        protocol
    ):
        raise V5CertificationError("persisted V5 terminal report does not reproduce")
    return protocol


def main() -> None:  # pragma: no cover - operational artifact writer
    root = Path(__file__).resolve().parents[2]
    protocol = write_v5_artifacts(root, root / OUTPUT_NAMESPACE)
    print(protocol["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
