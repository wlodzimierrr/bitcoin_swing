"""Frozen in-process trust boundary for the ETF calendar authority.

This module builds a pre-data architecture-decision artifact.  It deliberately
does not install guards or modify the calendar implementation.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any


DECISION_VERSION = "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1"
PROGRAM_TICKET = "POSTP1-001V2A-AD1"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_in_process_authority_boundary_v1"
DEFINITION_FILENAME = "authority_boundary_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_XHIGH_ARCHITECTURE_REVIEW"
FINAL_CLASSIFICATION = "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_XHIGH_REVIEW"

CERTIFIED_DEPENDENCY_VERSION = "TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1"
CERTIFIED_DEPENDENCY_SHA256 = (
    "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
)
FAILED_CALENDAR_LINEAGE = (
    "a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9",
    "b81c1702c65e1e042b7a2f948216305618fd21fabe2e629edc46376882b357af",
    "0524334396e529afbd057db25721b92c3074dd10205dd08be0946e512f99c855",
    "b499c6a4d1a8a6c25c6b108279831f26508742de97bdbcd57c7bee58e584e076",
    "901f572e03781030906cd6fe72a73ec5804f9ffbdefe6a8a944c067f7fd9853f",
)


class AuthorityBoundaryError(ValueError):
    """Raised when the frozen architecture decision does not reproduce."""


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


def _definition(payload: Mapping[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["definition_sha256"] = _digest(result)
    return result


def _verify_definition_digest(payload: Mapping[str, Any]) -> None:
    row = dict(payload)
    declared = row.pop("definition_sha256", None)
    if not isinstance(declared, str) or len(declared) != 64 or _digest(row) != declared:
        raise AuthorityBoundaryError("definition_sha256 does not recompute")


def trusted_computing_boundary() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_TRUSTED_COMPUTING_BOUNDARY_V1",
            "boundary": "PRODUCTION_PYTHON_INTERPRETER_AND_PROCESS_ARE_TRUSTED",
            "authority_kind": "SCIENTIFIC_CORRECTNESS_NOT_HOSTILE_INTERPRETER_ISOLATION",
            "in_scope": [
                "PROJECT_OWNED_SUPPORTED_BYPASS_PATHS",
                "MISCONFIGURATION",
                "PERSISTED_ARTIFACT_DRIFT",
                "DEPENDENCY_DRIFT",
                "UNSUPPORTED_PUBLIC_OR_TEST_APIS_ACCEPTED_AS_AUTHORITY",
                "ORDINARY_IMPLEMENTATION_OR_REFACTOR_ERRORS",
            ],
            "arbitrary_same_process_mutation_resistance_required": False,
            "bounded_convergence_rule": (
                "A future review must not fail the calendar solely because arbitrary "
                "trusted-process Python code could monkeypatch or privately mutate objects, "
                "when the repository ships no supported bypass, reviewed direct production "
                "bodies enforce the invariant, persisted/dependency drift refuses, and "
                "test-only APIs remain non-authoritative."
            ),
        }
    )


def supported_production_api() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_SUPPORTED_PRODUCTION_API_V1",
            "rule": "ONLY_DOCUMENTED_PRODUCTION_ENTRYPOINTS_ARE_AUTHORITATIVE_CALLABLE_SURFACES",
            "authoritative_entrypoints": [
                "CalendarEvidenceStore.put",
                "CalendarEvidenceStore.get",
                "CalendarEvidenceStore.records",
                "CalendarEvidenceStore.envelopes",
                "collect_official_calendar",
                "SCIENTIFIC_CALENDAR_AND_REPLAY_OWNERS_CONSUMING_CalendarEvidenceStore",
            ],
            "test_only_and_private_helpers_authoritative": False,
            "test_only_requirements": [
                "UNMISTAKABLE_NON_AUTHORITATIVE_TEST_ONLY_CLASSIFICATION",
                "NOT_ACCEPTED_BY_PRODUCTION_STORE_OR_PERSISTENCE",
                "NOT_REFERENCED_AS_A_PRODUCTION_ALIAS",
            ],
        }
    )


def direct_body_enforcement() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_DIRECT_BODY_ENFORCEMENT_V1",
            "exact_dependency_assertion": "assert_trusted_persistence_dependency",
            "rule": "ASSERTION_WRITTEN_DIRECTLY_IN_EACH_AUTHORITATIVE_PRODUCTION_ENTRYPOINT_BODY",
            "required_direct_bodies": [
                "CalendarEvidenceStore.put",
                "CalendarEvidenceStore.get",
                "CalendarEvidenceStore.records",
                "CalendarEvidenceStore.envelopes",
                "collect_official_calendar",
            ],
            "authoritative_replay_rule": (
                "EXISTING_ADMITTED_EVIDENCE_IS_NOT_SCIENTIFICALLY_USABLE_UNLESS_THE_EXACT_"
                "CALENDAR_DEPENDENCY_IS_VALID_AT_REPLAY_TIME"
            ),
            "production_collection_order": [
                "ASSERT_EXACT_CALENDAR_DEPENDENCY",
                "THEN_HTTPS",
                "THEN_PRIVATE_KEY_LOADING",
                "THEN_SIGNING",
                "THEN_PERSISTENCE",
            ],
            "startup_self_check_required": True,
            "startup_self_check": [
                "CALENDAR_FROZEN_PARENT_VALID",
                "DEPENDENCY_CHILD_VALID",
                "EXACT_TRUSTED_PERSISTENCE_DEPENDENCY_VALID",
                "EXECUTABLE_MANIFEST_VALID",
            ],
            "startup_self_check_replaces_per_entrypoint_checks": False,
        }
    )


def project_owned_bypass_prohibition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PROJECT_OWNED_BYPASS_PROHIBITION_V1",
            "project_owned_production_bypasses_permitted": False,
            "forbidden": [
                "__wrapped__",
                "PUBLIC_RAW_OR_ORIGINAL_OWNER_ATTRIBUTES",
                "UNGUARDED_CORE_METHODS_EXPOSED_FROM_PRODUCTION_MODULE",
                "ALTERNATE_PRODUCTION_ALIASES",
                "ALTERNATE_CONSTRUCTORS",
                "TEST_HELPERS_ACCEPTED_AS_PRODUCTION_AUTHORITY",
                "CALLER_SELECTED_VERIFICATION_OR_PERSISTENCE_CAPABILITIES",
                "RUNTIME_DECORATOR_OR_WRAPPER_INSTALLATION",
                "FUNCTOOLS_WRAPS_AUTHORITY_GUARDS",
                "MODULE_IMPORT_TIME_GUARD_REBINDING",
            ],
            "unguarded_core_extraction_permitted": False,
            "factoring_constraint": (
                "A factored helper must not independently establish or return authoritative "
                "scientific behavior without an already-proven authority context."
            ),
            "priority": "CORRECTNESS_OVER_DRY_AT_PRODUCTION_AUTHORITY_BOUNDARIES",
        }
    )


def runtime_mutation_threat_model() -> dict[str, Any]:
    mutations = [
        "CALLER_REASSIGNS_CalendarEvidenceStore.put",
        "CALLER_CHANGES_MODULE_GLOBALS_WITH_MONKEYPATCH_OR_SETATTR",
        "CALLER_MODIFIES_CLASS_DICTIONARY",
        "CALLER_INVOKES_OBJECT_INTERNALS_OR_PRIVATE_FIELDS_DIRECTLY",
        "CALLER_REPLACES_assert_trusted_persistence_dependency",
        "CALLER_USES_DEBUGGER_EXEC_OR_ARBITRARY_PYTHON_CODE_IN_PRODUCTION_PROCESS",
    ]
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_RUNTIME_MUTATION_THREAT_MODEL_V1",
            "mutations": {item: "OUTSIDE_SCIENTIFIC_AUTHORITY_THREAT_MODEL" for item in mutations},
            "reason": "EQUIVALENT_TO_CODE_EXECUTION_INSIDE_THE_TRUSTED_PRODUCTION_PROCESS",
            "repository_runtime_identity_rule": (
                "CONTROLLED_STARTUP_REPOSITORY_AND_RUNTIME_IMPLEMENTATION_IDENTITY_IS_DISTINCT_"
                "FROM_HOSTILE_POST_LOAD_MUTATION_RESISTANCE"
            ),
            "escalation": {
                "condition": "A_HIGHER_AUTHORITY_REQUIRES_ARBITRARY_SAME_PROCESS_MUTATION_RESISTANCE",
                "classification": "ETF_CALENDAR_AUTHORITY_REQUIRES_PROCESS_ISOLATION_ARCHITECTURE",
                "required_boundary": "SEPARATE_TRUSTED_PROCESS_OR_SERVICE_WITH_NARROW_IPC_AND_INDEPENDENT_STATE",
                "wrapper_metaclass_or_hash_workaround_permitted": False,
                "implemented_by_this_ticket": False,
            },
        }
    )


def static_surface_audit() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_STATIC_PRODUCTION_SURFACE_AUDIT_V1",
            "mechanical_ast_audit_required": True,
            "requirements": [
                "NO_FUNCTOOLS_WRAPS_OR_DECORATOR_INSTALLATION_FOR_AUTHORITY_GUARD",
                "NO___WRAPPED___PRODUCTION_BYPASS",
                "NO_PRODUCTION_ALIAS_TO_UNGUARDED_OWNER",
                "NO_EXPOSED_UNGUARDED_CORE_PERFORMING_AUTHORITATIVE_STORE_OR_COLLECTION_BEHAVIOR",
                "ALL_DOCUMENTED_AUTHORITATIVE_ENTRYPOINT_BODIES_CONTAIN_EXACT_DEPENDENCY_ASSERTION",
            ],
            "direct_call_regressions": [
                "CalendarEvidenceStore.put",
                "CalendarEvidenceStore.get",
                "CalendarEvidenceStore.records",
                "CalendarEvidenceStore.envelopes",
                "collect_official_calendar",
                "SCIENTIFIC_REPLAY_OWNERS",
            ],
            "regression_expectation": "SUPPORTED_CALLS_REFUSE_EXACT_DEPENDENCY_MISMATCH",
            "arbitrary_monkeypatch_generated_FUNCTIONS_PROVED_IMPOSSIBLE": False,
        }
    )


def drift_science_and_safety() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_DRIFT_SCIENCE_AND_SAFETY_V1",
            "hard_refusal": {
                "calendar_parent_mismatch": True,
                "dependency_child_mismatch": True,
                "expected_dependency_hash_mismatch": True,
                "expected_dependency_version_mismatch": True,
                "trusted_persistence_authority_mismatch": True,
                "supported_production_api_bypass": True,
            },
            "certified_dependency": {
                "authority_version": CERTIFIED_DEPENDENCY_VERSION,
                "definition_sha256": CERTIFIED_DEPENDENCY_SHA256,
                "status": "CLOSED_CERTIFIED_FOR_BOUNDED_ETF_CALENDAR_INTEGRATION",
                "changed": False,
            },
            "preserved_science": {
                "source_profiles_urls_tls_redirects_parsers_coverage_early_closes": "UNCHANGED",
                "pit_and_common_session_semantics": "UNCHANGED",
                "etf_formulas_and_revision_semantics": "UNCHANGED",
                "stage_b_metrics_risk_stops_thresholds": "UNCHANGED",
            },
            "failed_calendar_lineage": [
                {
                    "definition_sha256": digest,
                    "authoritative": False,
                    "certified": False,
                    "prospective_observations": 0,
                    "superseded_before_use": True,
                }
                for digest in FAILED_CALENDAR_LINEAGE
            ],
            "safety": {
                "prospective_observations": 0,
                "real_stage_b_evaluation": False,
                "calendar_certified": False,
                "collection_authorized": False,
                "postp1_001v2r1": "BLOCKED",
                "postp1_003r3": "BLOCKED",
                "postp1_004": "BLOCKED",
                "btc019": "UNTOUCHED",
                "epic_t": "UNCHANGED",
            },
        }
    )


_CHILD_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("trusted_computing_boundary.json", "trusted_computing_boundary"),
    ("supported_production_api.json", "supported_production_api"),
    ("direct_body_enforcement.json", "direct_body_enforcement"),
    ("project_owned_bypass_prohibition.json", "project_owned_bypass_prohibition"),
    ("runtime_mutation_threat_model.json", "runtime_mutation_threat_model"),
    ("static_surface_audit.json", "static_surface_audit"),
    ("drift_science_and_safety.json", "drift_science_and_safety"),
)


def _children() -> dict[str, dict[str, Any]]:
    return {
        filename.removesuffix(".json"): globals()[builder]()
        for filename, builder in _CHILD_ARTIFACTS
    }


def authority_boundary_definition() -> dict[str, Any]:
    children = _children()
    return _definition(
        {
            "decision_version": DECISION_VERSION,
            "program_ticket": PROGRAM_TICKET,
            "workstream": "EPIC X — PROSPECTIVE INTEGRATION EVIDENCE",
            "status": STATUS,
            "final_classification": FINAL_CLASSIFICATION,
            "pre_data": True,
            "required_review": "INDEPENDENT_XHIGH_ARCHITECTURE_REVIEW",
            "material_child_count": len(children),
            "material_child_enumeration": "MECHANICALLY_ENUMERATED_FROM_ONE_ARTIFACT_BUILDER_REGISTRY",
            "child_definition_sha256": {
                name: child["definition_sha256"] for name, child in children.items()
            },
            "central_decisions": {
                "trusted_production_python_process": True,
                "arbitrary_in_process_monkeypatch_resistance_required": False,
                "project_owned_production_bypasses_permitted": False,
                "direct_entrypoint_body_enforcement_required": True,
                "dynamic_wrapper_installation_permitted": False,
                "functools_wraps_authority_guards_permitted": False,
                "exposed_unguarded_production_owners_permitted": False,
                "process_isolation_required_if_arbitrary_same_process_mutation_enters_scope": True,
            },
            "authorization": {
                "independent_architecture_xhigh_review_may_begin": True,
                "another_calendar_implementation_may_begin": False,
                "calendar_implementation_requires_architecture_review_pass": True,
                "postp1_001v2r1_may_begin": False,
                "prospective_collection_may_begin": False,
            },
        }
    )


def verify_authority_boundary_definition(persisted: Mapping[str, Any]) -> None:
    if dict(persisted) != authority_boundary_definition():
        raise AuthorityBoundaryError("persisted authority boundary does not reproduce")
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    return f"""# {DECISION_VERSION}

- Ticket: `{PROGRAM_TICKET}`
- Decision hash: `{decision['definition_sha256']}`
- Status: `{STATUS}`
- Classification: `{FINAL_CLASSIFICATION}`
- Material children: {decision['material_child_count']}

## Decision

The production Python interpreter and process are part of the trusted computing
boundary. This is a scientific-correctness boundary, not a hostile-interpreter
isolation boundary. Arbitrary code execution, monkeypatching, module or class
mutation, private-state manipulation, debugger changes, and replacement of the
assertion inside that trusted process are outside this authority's threat model.

Every documented project-owned authoritative entrypoint must contain the exact
trusted-persistence dependency assertion directly in its reviewed body. The
repository may expose no wrapper original, raw/core owner, production alias,
alternate constructor, test helper, or caller-selected capability that bypasses
that assertion. Runtime decorator installation and `functools.wraps` authority
guards are forbidden. Store reads must assert at replay time, and production
collection must assert before HTTPS, private-key loading, signing, or persistence.

Controlled-startup implementation identity remains required to detect ordinary
repository/runtime drift. A startup self-check supplements, but never replaces,
the direct entrypoint checks. If a higher authority later requires resistance to
arbitrary mutation inside the trusted process, wrapper-level work must stop and
a separate process/service isolation architecture is required.

## Preserved scope and safety

Persisted calendar-parent, dependency-child, expected dependency hash/version,
and certified dependency mismatches still refuse. The certified dependency
`{CERTIFIED_DEPENDENCY_SHA256}` remains closed and unchanged. Source, parser,
PIT, common-session, ETF, Stage-B, risk, stop, and threshold semantics are
unchanged. All five failed calendar hashes remain non-authoritative,
non-certified, unused, and superseded before use.

No observation was collected and no real Stage-B evaluation ran. The calendar
is not certified. POSTP1-001V2R1, POSTP1-003R3, POSTP1-004, and collection stay
blocked; BTC-019 is untouched and Epic T is unchanged. This decision authorizes
only its independent xHigh architecture review.
"""


def write_artifacts(output_dir: Path) -> dict[str, Any]:
    decision = authority_boundary_definition()
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {DEFINITION_FILENAME: decision}
    payloads.update({filename: globals()[builder]() for filename, builder in _CHILD_ARTIFACTS})
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )
    (output_dir / REPORT_FILENAME).write_text(_report_markdown(decision), encoding="utf-8")
    return decision


def restore_artifacts(output_dir: Path) -> dict[str, Any]:
    decision = json.loads((output_dir / DEFINITION_FILENAME).read_text(encoding="ascii"))
    verify_authority_boundary_definition(decision)
    for filename, builder in _CHILD_ARTIFACTS:
        persisted = json.loads((output_dir / filename).read_text(encoding="ascii"))
        expected = globals()[builder]()
        if persisted != expected:
            raise AuthorityBoundaryError(f"persisted {filename} does not reproduce")
        _verify_definition_digest(persisted)
        if decision["child_definition_sha256"].get(filename.removesuffix(".json")) != expected["definition_sha256"]:
            raise AuthorityBoundaryError(f"authority boundary does not bind {filename}")
    if (output_dir / REPORT_FILENAME).read_text(encoding="utf-8") != _report_markdown(decision):
        raise AuthorityBoundaryError("persisted report does not reproduce")
    return decision


def main() -> None:  # pragma: no cover - artifact writer
    root = Path(__file__).resolve().parents[2]
    print(write_artifacts(root / OUTPUT_NAMESPACE)["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
