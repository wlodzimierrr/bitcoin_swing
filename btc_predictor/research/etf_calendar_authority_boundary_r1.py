"""Corrected frozen in-process authority boundary for the ETF calendar.

This is an architecture-decision builder and static-audit specification.  It
does not install guards or modify the production calendar implementation.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any


DECISION_VERSION = "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1"
PROGRAM_TICKET = "POSTP1-001V2A-AD1-R1"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_in_process_authority_boundary_v1_r1"
DEFINITION_FILENAME = "authority_boundary_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_XHIGH_ARCHITECTURE_REVIEW"
FINAL_CLASSIFICATION = (
    "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_REPEAT_XHIGH_REVIEW"
)
CALENDAR_MODULE = "btc_predictor.research.etf_publication_calendar"
CALENDAR_SOURCE = Path(__file__).with_name("etf_publication_calendar.py")

CERTIFIED_DEPENDENCY_VERSION = "TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY_V1"
CERTIFIED_DEPENDENCY_SHA256 = (
    "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
)
FAILED_ARCHITECTURE_SHA256 = (
    "0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d"
)
FAILED_CALENDAR_LINEAGE = (
    "a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9",
    "b81c1702c65e1e042b7a2f948216305618fd21fabe2e629edc46376882b357af",
    "0524334396e529afbd057db25721b92c3074dd10205dd08be0946e512f99c855",
    "b499c6a4d1a8a6c25c6b108279831f26508742de97bdbcd57c7bee58e584e076",
    "901f572e03781030906cd6fe72a73ec5804f9ffbdefe6a8a944c067f7fd9853f",
)
FROZEN_AUTHORITATIVE_INTERNALS = ("_records", "_envelopes")
FROZEN_REPLAY_OWNERS = (
    "derive_normalized_schedule_from_official_source",
    "venue_session_calendar_record",
    "_verify_schedule",
    "_verify_schedule_record",
    "validate_normalized_schedule_against_source",
    "_verify_venue_row",
    "venue_session_status",
    "common_etf_session_status",
    "expected_etf_publication_dates",
    "derive_etf_window_calendar",
    "scientific_etf_flow_window",
)
REQUIRED_DIRECT_BODIES = (
    "CalendarEvidenceStore.put",
    "CalendarEvidenceStore.get",
    "CalendarEvidenceStore.records",
    "CalendarEvidenceStore.envelopes",
    "collect_official_calendar",
)
STORE_APIS = ("put", "get", "records", "envelopes")


class AuthorityBoundaryError(ValueError):
    """Raised when the frozen decision or production-surface audit fails."""


def _canonical_json(payload: Any) -> str:
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True, allow_nan=False
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


def _annotation_names_calendar_store(annotation: ast.expr | None) -> bool:
    return annotation is not None and "CalendarEvidenceStore" in ast.unparse(annotation)


def _function_store_parameters(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    parameters = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    return {
        parameter.arg
        for parameter in parameters
        if _annotation_names_calendar_store(parameter.annotation)
        or parameter.arg == "store"
        or parameter.arg.endswith("_store")
    }


def _function_store_references(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    """Return annotated/conventional store parameters plus ordinary local aliases."""

    references = _function_store_parameters(node)
    changed = True
    while changed:
        changed = False
        for candidate in ast.walk(node):
            value: ast.expr | None = None
            targets: Sequence[ast.expr] = ()
            if isinstance(candidate, ast.Assign):
                value, targets = candidate.value, candidate.targets
            elif isinstance(candidate, ast.AnnAssign):
                value, targets = candidate.value, (candidate.target,)
            if not isinstance(value, ast.Name) or value.id not in references:
                continue
            for target in targets:
                if isinstance(target, ast.Name) and target.id not in references:
                    references.add(target.id)
                    changed = True
    return references


def _top_level_functions(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    return {
        node.name: node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }


def _literal_string(node: ast.expr) -> str | None:
    return node.value if isinstance(node, ast.Constant) and isinstance(node.value, str) else None


def _function_direct_store_use(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    store_parameters: set[str],
) -> bool:
    for candidate in ast.walk(node):
        if isinstance(candidate, ast.Attribute) and candidate.attr in FROZEN_AUTHORITATIVE_INTERNALS:
            return True
        if not isinstance(candidate, ast.Call):
            continue
        if (
            isinstance(candidate.func, ast.Attribute)
            and candidate.func.attr in STORE_APIS
            and isinstance(candidate.func.value, ast.Name)
            and candidate.func.value.id in store_parameters
        ):
            return True
        if (
            isinstance(candidate.func, ast.Name)
            and candidate.func.id in {"getattr", "setattr"}
            and len(candidate.args) >= 2
            and _literal_string(candidate.args[1]) in FROZEN_AUTHORITATIVE_INTERNALS
        ):
            return True
    return False


def _forwards_store_to_owner(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    store_parameters: set[str],
    owners: set[str],
) -> bool:
    for candidate in ast.walk(node):
        if not isinstance(candidate, ast.Call):
            continue
        called = candidate.func.id if isinstance(candidate.func, ast.Name) else None
        if called not in owners:
            continue
        values = [*candidate.args, *(keyword.value for keyword in candidate.keywords)]
        if any(isinstance(value, ast.Name) and value.id in store_parameters for value in values):
            return True
    return False


def discover_replay_owners(source: str) -> tuple[str, ...]:
    """Discover top-level scientific store consumers by frozen AST rules."""

    tree = ast.parse(source)
    functions = _top_level_functions(tree)
    store_parameters = {
        name: _function_store_references(node) for name, node in functions.items()
    }
    owners = {
        name
        for name, node in functions.items()
        if any(
            _annotation_names_calendar_store(parameter.annotation)
            for parameter in (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
        )
        or _function_direct_store_use(node, store_parameters[name])
    }
    changed = True
    while changed:
        changed = False
        for name, node in functions.items():
            if name not in owners and _forwards_store_to_owner(
                node, store_parameters[name], owners
            ):
                owners.add(name)
                changed = True
    return tuple(name for name in functions if name in owners)


def verify_replay_owner_census(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
) -> tuple[str, ...]:
    discovered = discover_replay_owners(source)
    if set(discovered) != set(frozen_owners) or len(discovered) != len(frozen_owners):
        raise AuthorityBoundaryError(
            "replay-owner registry/source census mismatch: "
            f"frozen={sorted(frozen_owners)!r}, discovered={sorted(discovered)!r}"
        )
    return discovered


def _is_self(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == "self"


def _mapping_private_base(node: ast.expr) -> tuple[bool, str] | None:
    if isinstance(node, ast.Attribute) and node.attr == "__dict__":
        return _is_self(node.value), "__dict__"
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "vars"
        and len(node.args) == 1
    ):
        return _is_self(node.args[0]), "vars"
    return None


def _private_access_findings(node: ast.AST, *, allow_self: bool = False) -> list[str]:
    findings: list[str] = []
    for candidate in ast.walk(node):
        if (
            isinstance(candidate, ast.Attribute)
            and candidate.attr in FROZEN_AUTHORITATIVE_INTERNALS
        ):
            if not (allow_self and _is_self(candidate.value)):
                findings.append(f"attribute:{candidate.attr}")
        if (
            isinstance(candidate, ast.Call)
            and isinstance(candidate.func, ast.Name)
            and candidate.func.id in {"getattr", "setattr"}
            and len(candidate.args) >= 2
            and _literal_string(candidate.args[1]) in FROZEN_AUTHORITATIVE_INTERNALS
        ):
            if not (allow_self and _is_self(candidate.args[0])):
                findings.append(f"{candidate.func.id}:{_literal_string(candidate.args[1])}")
        if isinstance(candidate, ast.Subscript):
            field = _literal_string(candidate.slice)
            if field not in FROZEN_AUTHORITATIVE_INTERNALS:
                continue
            base = _mapping_private_base(candidate.value)
            if base is not None and not (allow_self and base[0]):
                findings.append(f"{base[1]}:{field}")
        if (
            isinstance(candidate, ast.Call)
            and isinstance(candidate.func, ast.Attribute)
            and candidate.func.attr in {"get", "setdefault", "pop"}
            and candidate.args
            and _literal_string(candidate.args[0]) in FROZEN_AUTHORITATIVE_INTERNALS
        ):
            base = _mapping_private_base(candidate.func.value)
            if base is not None and not (allow_self and base[0]):
                findings.append(
                    f"{base[1]}.{candidate.func.attr}:{_literal_string(candidate.args[0])}"
                )
    return findings


def audit_private_state_access(source: str) -> None:
    """Reject reserved internal-state access outside store method bodies."""

    tree = ast.parse(source)
    findings: list[str] = []
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "CalendarEvidenceStore":
            for member in node.body:
                # Store methods may access their own ``self`` state, not another
                # store object's authoritative internals.
                findings.extend(
                    _private_access_findings(
                        member,
                        allow_self=isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)),
                    )
                )
            continue
        findings.extend(_private_access_findings(node))
    if findings:
        raise AuthorityBoundaryError(
            "reserved authoritative store-internal access outside CalendarEvidenceStore: "
            + ", ".join(sorted(findings))
        )


def _direct_calls_in_body(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    calls: set[str] = set()

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, child: ast.FunctionDef) -> None:
            if child is node:
                for statement in child.body:
                    self.visit(statement)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, child: ast.Lambda) -> None:
            del child

        def visit_Call(self, child: ast.Call) -> None:
            if isinstance(child.func, ast.Name):
                calls.add(child.func.id)
            self.generic_visit(child)

    Visitor().visit(node)
    return calls


def _required_body_nodes(tree: ast.Module) -> dict[str, ast.FunctionDef | ast.AsyncFunctionDef]:
    found: dict[str, ast.FunctionDef | ast.AsyncFunctionDef] = {}
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == "CalendarEvidenceStore":
            for member in node.body:
                if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    key = f"CalendarEvidenceStore.{member.name}"
                    if key in REQUIRED_DIRECT_BODIES:
                        found[key] = member
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name in REQUIRED_DIRECT_BODIES:
                found[node.name] = node
    return found


def _owner_reaches_documented_store_api(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    store_parameters: set[str],
    compliant_owners: set[str],
) -> bool:
    for candidate in ast.walk(node):
        if not isinstance(candidate, ast.Call):
            continue
        if (
            isinstance(candidate.func, ast.Attribute)
            and candidate.func.attr in STORE_APIS
            and isinstance(candidate.func.value, ast.Name)
            and candidate.func.value.id in store_parameters
        ):
            return True
        called = candidate.func.id if isinstance(candidate.func, ast.Name) else None
        if called in compliant_owners:
            values = [*candidate.args, *(keyword.value for keyword in candidate.keywords)]
            if any(isinstance(value, ast.Name) and value.id in store_parameters for value in values):
                return True
    return False


def audit_replay_owner_api_routes(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
) -> None:
    tree = ast.parse(source)
    functions = _top_level_functions(tree)
    missing = set(frozen_owners) - set(functions)
    if missing:
        raise AuthorityBoundaryError(f"stale replay-owner registry: {sorted(missing)!r}")
    compliant: set[str] = set()
    changed = True
    while changed:
        changed = False
        for name in frozen_owners:
            if name in compliant:
                continue
            node = functions[name]
            if _owner_reaches_documented_store_api(
                node, _function_store_references(node), compliant
            ):
                compliant.add(name)
                changed = True
    unresolved = set(frozen_owners) - compliant
    if unresolved:
        raise AuthorityBoundaryError(
            f"replay owner has no route to a documented store API: {sorted(unresolved)!r}"
        )


def audit_static_production_surface(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
) -> None:
    """Apply the complete structural AST architecture audit to a module."""

    tree = ast.parse(source)
    verify_replay_owner_census(source, frozen_owners)
    audit_private_state_access(source)
    audit_replay_owner_api_routes(source, frozen_owners)
    required = _required_body_nodes(tree)
    if set(required) != set(REQUIRED_DIRECT_BODIES):
        raise AuthorityBoundaryError("required authoritative direct body is missing")
    for name, node in required.items():
        if node.decorator_list:
            raise AuthorityBoundaryError(f"runtime decorator/wrapper forbidden on {name}")
        if "assert_trusted_persistence_dependency" not in _direct_calls_in_body(node):
            raise AuthorityBoundaryError(f"exact dependency ast.Call missing from {name}")
    for candidate in ast.walk(tree):
        if isinstance(candidate, ast.Attribute) and candidate.attr == "__wrapped__":
            raise AuthorityBoundaryError("__wrapped__ production bypass forbidden")
        if (
            isinstance(candidate, ast.Call)
            and (
                (isinstance(candidate.func, ast.Name) and candidate.func.id == "wraps")
                or (isinstance(candidate.func, ast.Attribute) and candidate.func.attr == "wraps")
            )
        ):
            raise AuthorityBoundaryError("functools.wraps authority guard forbidden")
        if isinstance(candidate, (ast.Assign, ast.AnnAssign)):
            targets = candidate.targets if isinstance(candidate, ast.Assign) else [candidate.target]
            for target in targets:
                if (
                    isinstance(target, ast.Attribute)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == "CalendarEvidenceStore"
                    and target.attr in STORE_APIS
                ):
                    raise AuthorityBoundaryError("runtime store-method guard rebinding forbidden")


def trusted_computing_boundary() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_TRUSTED_COMPUTING_BOUNDARY_V1_R1",
            "boundary": "PRODUCTION_PYTHON_INTERPRETER_AND_PROCESS_ARE_TRUSTED",
            "authority_kind": "SCIENTIFIC_CORRECTNESS_NOT_HOSTILE_INTERPRETER_ISOLATION",
            "arbitrary_same_process_mutation_resistance_required": False,
            "project_owned_production_scientific_bypasses_in_scope": True,
            "bounded_convergence_rule": (
                "Arbitrary caller execution that mutates interpreter internals is outside scope; "
                "repository-owned production/scientific bypasses remain in scope and forbidden."
            ),
        }
    )


def private_state_boundary() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PRIVATE_STATE_BOUNDARY_V1",
            "external_caller_private_state_mutation": "OUTSIDE_SCIENTIFIC_AUTHORITY_THREAT_MODEL",
            "project_owned_private_state_access": "IN_SCOPE_AND_FORBIDDEN",
            "authoritative_internal_state": list(FROZEN_AUTHORITATIVE_INTERNALS),
            "classification": "IMPLEMENTATION_PRIVATE_AUTHORITATIVE_STATE",
            "allowed_implementation_boundary": "CalendarEvidenceStore_METHOD_BODIES",
            "documented_authoritative_store_api": list(STORE_APIS),
            "direct_reads_outside_implementation": "FORBIDDEN",
            "direct_writes_outside_implementation": "FORBIDDEN",
            "ordinary_forms_mechanically_refused": [
                "ATTRIBUTE",
                "LITERAL_GETATTR_SETATTR",
                "LITERAL___DICT___SUBSCRIPT",
                "LITERAL_VARS_SUBSCRIPT",
            ],
            "arbitrarily_obfuscated_hostile_code_proved_impossible": False,
            "future_extension_rule": (
                "ANY_NEW_FIELD_STORING_AUTHORITATIVE_SCIENTIFIC_EVIDENCE_OR_ENVELOPE_"
                "IDENTITY_REQUIRES_REGISTRY_UPDATE_REVIEW_AND_PARENT_HASH_CHANGE"
            ),
            "underscore_naming_alone_is_the_boundary": False,
        }
    )


def replay_owner_registry() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_OWNER_REGISTRY_V1",
            "production_module": CALENDAR_MODULE,
            "owners": list(FROZEN_REPLAY_OWNERS),
            "placeholder_category_permitted": False,
            "discovery_rules": [
                "TOP_LEVEL_FUNCTION_PARAMETER_ANNOTATED_CalendarEvidenceStore",
                "DOCUMENTED_STORE_API_CALL_ON_STORE_LIKE_PARAMETER_OR_REFERENCE",
                "RESERVED_AUTHORITATIVE_INTERNAL_ACCESS",
                "ENUMERATED_OWNER_CALL_FORWARDING_EVIDENCE_STORE_ARGUMENT",
            ],
            "required_relation": "MECHANICALLY_DISCOVERED_OWNERS_EQUALS_FROZEN_REGISTRY",
        }
    )


def transitive_replay_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_TRANSITIVE_REPLAY_RULE_V1",
            "rule": (
                "EVERY_AUTHORITATIVE_EVIDENCE_ROUTE_TERMINATES_IN_DOCUMENTED_STORE_READ_"
                "SURFACE_PERFORMING_EXACT_DEPENDENCY_ASSERTION"
            ),
            "permitted_routes": ["DOCUMENTED_STORE_API", "COMPLIANT_ENUMERATED_OWNER"],
            "forbidden_routes": [
                "PRIVATE_STATE",
                "TEST_ONLY_STATE",
                "RAW_PRODUCTION_ALIAS",
                "UNGUARDED_CORE",
                "ALTERNATE_STORE_IMPLEMENTATION",
            ],
            "higher_level_owner_duplicates_dependency_assertion": False,
            "direct_internal_state_access_breaks_invariant": True,
        }
    )


def direct_body_enforcement() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_DIRECT_BODY_ENFORCEMENT_V1_R1",
            "exact_dependency_assertion": "assert_trusted_persistence_dependency",
            "proof": "EXECUTABLE_AST_CALL_IN_EACH_REQUIRED_FUNCTION_BODY",
            "required_direct_bodies": list(REQUIRED_DIRECT_BODIES),
            "higher_level_replay_owner_duplication_required": False,
            "runtime_wrapper_installation_permitted": False,
            "functools_wraps_authority_guards_permitted": False,
            "exposed_unguarded_production_owner_permitted": False,
            "startup_self_check": [
                "CALENDAR_FROZEN_PARENT_VALID",
                "DEPENDENCY_CHILD_VALID",
                "EXACT_TRUSTED_PERSISTENCE_DEPENDENCY_VALID",
                "EXECUTABLE_MANIFEST_VALID",
            ],
            "startup_self_check_replaces_direct_body_checks": False,
        }
    )


def project_owned_bypass_prohibition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PROJECT_OWNED_BYPASS_PROHIBITION_V1_R1",
            "project_owned_production_bypasses_permitted": False,
            "forbidden": [
                "DIRECT_AUTHORITATIVE_INTERNAL_STATE_READ_OR_WRITE",
                "__wrapped__",
                "PUBLIC_RAW_OR_ORIGINAL_OWNER_ATTRIBUTES",
                "UNGUARDED_CORE_METHODS_EXPOSED_FROM_PRODUCTION_MODULE",
                "ALTERNATE_PRODUCTION_ALIASES_OR_STORE_IMPLEMENTATIONS",
                "TEST_HELPERS_ACCEPTED_AS_PRODUCTION_AUTHORITY",
                "CALLER_SELECTED_VERIFICATION_OR_PERSISTENCE_CAPABILITIES",
                "RUNTIME_DECORATOR_OR_WRAPPER_INSTALLATION",
                "FUNCTOOLS_WRAPS_AUTHORITY_GUARDS",
                "MODULE_IMPORT_TIME_GUARD_REBINDING",
            ],
            "production_mutation_enters_through_documented_store_surfaces": True,
            "test_modules_fixtures_and_explicit_test_only_helpers_excluded": True,
        }
    )


def runtime_mutation_threat_model() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_RUNTIME_MUTATION_THREAT_MODEL_V1_R1",
            "external_caller_mutations": {
                key: "OUTSIDE_SCIENTIFIC_AUTHORITY_THREAT_MODEL"
                for key in (
                    "CALLER_MUTATES_STORE_PRIVATE_FIELDS",
                    "CALLER_CHANGES_MODULE_GLOBALS_OR_CLASS_DICTIONARY",
                    "CALLER_USES_DEBUGGER_EXEC_OR_ARBITRARY_PYTHON",
                )
            },
            "repository_owned_private_state_access": "IN_SCOPE_AND_FORBIDDEN",
            "escalation": {
                "condition": "ARBITRARY_SAME_PROCESS_HOSTILE_MUTATION_RESISTANCE_ENTERS_SCOPE",
                "classification": "ETF_CALENDAR_AUTHORITY_REQUIRES_PROCESS_ISOLATION_ARCHITECTURE",
                "required_boundary": "SEPARATE_TRUSTED_PROCESS_OR_SERVICE_WITH_NARROW_IPC",
                "wrapper_metaclass_descriptor_frozen_object_or_hash_workaround_permitted": False,
            },
        }
    )


def static_surface_audit() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_STATIC_PRODUCTION_SURFACE_AUDIT_V1_R1",
            "production_module": CALENDAR_MODULE,
            "proof_form": "PYTHON_AST_STRUCTURE_NOT_TEXT_SEARCH",
            "entire_production_module_private_state_audit": True,
            "store_implementation_method_bodies_excluded_from_private_state_prohibition": True,
            "requirements": [
                "NO_RUNTIME_DECORATOR_OR_WRAPPER_AUTHORITY_GUARD",
                "NO___WRAPPED___PROJECT_OWNED_BYPASS",
                "NO_UNGUARDED_PRODUCTION_ALIAS_OR_CORE",
                "DIRECT_EXACT_DEPENDENCY_AST_CALL_IN_ALL_FIVE_BOUNDARY_BODIES",
                "NO_RESERVED_PRIVATE_STATE_ACCESS_OUTSIDE_STORE_IMPLEMENTATION",
                "FROZEN_OWNER_REGISTRY_EQUALS_MECHANICALLY_DISCOVERED_CENSUS",
                "EVERY_REPLAY_OWNER_REACHES_ONLY_DOCUMENTED_STORE_API_OR_COMPLIANT_OWNER",
            ],
            "non_structural_evidence_does_not_satisfy": [
                "STRING", "COMMENT", "DOCSTRING", "CONSTANT", "DEAD_NAME", "UNRELATED_CALL"
            ],
            "test_code_scope": "EXCLUDED_FROM_PRODUCTION_MODULE_AUDIT",
        }
    )


def drift_science_and_safety() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_DRIFT_SCIENCE_AND_SAFETY_V1_R1",
            "failed_architecture": {
                "definition_sha256": FAILED_ARCHITECTURE_SHA256,
                "certified": False,
                "failed_independent_review": True,
                "superseded_before_use": True,
                "prospective_observations": 0,
            },
            "certified_dependency": {
                "authority_version": CERTIFIED_DEPENDENCY_VERSION,
                "definition_sha256": CERTIFIED_DEPENDENCY_SHA256,
                "status": "CLOSED_CERTIFIED_FOR_BOUNDED_ETF_CALENDAR_INTEGRATION",
                "changed": False,
            },
            "preserved_hashes": {
                "certified_prospective_v1": "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7",
                "failed_prospective_v2": "488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d",
            },
            "failed_calendar_lineage": list(FAILED_CALENDAR_LINEAGE),
            "preserved_science": {
                "source_profiles_urls_tls_redirects_parsers_coverage_early_closes": "UNCHANGED",
                "pit_and_common_session_semantics": "UNCHANGED",
                "etf_formulas_and_revision_semantics": "UNCHANGED",
                "stage_b_metrics_risk_stops_thresholds": "UNCHANGED",
            },
            "safety": {
                "prospective_observations": 0,
                "real_stage_b_evaluation": False,
                "calendar_certified": False,
                "calendar_implementation": "BLOCKED_PENDING_REVIEW_PASS",
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
    ("private_state_boundary.json", "private_state_boundary"),
    ("replay_owner_registry.json", "replay_owner_registry"),
    ("transitive_replay_rule.json", "transitive_replay_rule"),
    ("direct_body_enforcement.json", "direct_body_enforcement"),
    ("project_owned_bypass_prohibition.json", "project_owned_bypass_prohibition"),
    ("runtime_mutation_threat_model.json", "runtime_mutation_threat_model"),
    ("static_surface_audit.json", "static_surface_audit"),
    ("drift_science_and_safety.json", "drift_science_and_safety"),
)


def _children(
    child_artifacts: Iterable[tuple[str, str]] | None = None,
) -> dict[str, dict[str, Any]]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    return {
        filename.removesuffix(".json"): globals()[builder]()
        for filename, builder in registry
    }


def authority_boundary_definition(
    child_artifacts: Iterable[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    source = CALENDAR_SOURCE.read_text(encoding="utf-8")
    verify_replay_owner_census(source)
    audit_private_state_access(source)
    audit_replay_owner_api_routes(source)
    children = _children(child_artifacts)
    return _definition(
        {
            "decision_version": DECISION_VERSION,
            "program_ticket": PROGRAM_TICKET,
            "workstream": "EPIC X — PROSPECTIVE INTEGRATION EVIDENCE",
            "status": STATUS,
            "final_classification": FINAL_CLASSIFICATION,
            "pre_data": True,
            "required_review": "INDEPENDENT_EXACT_HASH_XHIGH_ARCHITECTURE_REREVIEW",
            "material_child_count": len(children),
            "material_child_enumeration": "MECHANICALLY_ENUMERATED_FROM_ONE_REGISTRY",
            "child_definition_sha256": {
                name: child["definition_sha256"] for name, child in children.items()
            },
            "central_decisions": {
                "trusted_production_python_process": True,
                "arbitrary_caller_private_state_mutation_in_scope": False,
                "project_owned_private_state_access_in_scope": True,
                "project_owned_private_state_access_permitted": False,
                "direct_entrypoint_body_enforcement_required": True,
                "dynamic_wrapper_installation_permitted": False,
                "functools_wraps_authority_guards_permitted": False,
                "exposed_unguarded_production_owners_permitted": False,
                "process_isolation_required_if_hostile_same_process_mutation_enters_scope": True,
            },
            "authorization": {
                "independent_architecture_xhigh_rereview_may_begin": True,
                "calendar_implementation_may_begin": False,
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
    owners = "\n".join(f"- `{owner}`" for owner in FROZEN_REPLAY_OWNERS)
    return f"""# {DECISION_VERSION}

- Ticket: `{PROGRAM_TICKET}`
- Decision hash: `{decision['definition_sha256']}`
- Status: `{STATUS}`
- Classification: `{FINAL_CLASSIFICATION}`
- Material children: {decision['material_child_count']}

## Threat boundary and project-owned bypasses

The production Python interpreter/process remains trusted. Arbitrary external
caller manipulation of private fields, class dictionaries, module globals,
debugger state, or equivalent interpreter internals is outside the scientific-
authority threat model. Repository-owned production/scientific code that reads
or writes authoritative store internals outside `CalendarEvidenceStore` is in
scope and forbidden. If hostile same-process mutation later enters scope, work
must stop for process isolation; no wrapper, metaclass, descriptor, frozen-
object, or source-hash workaround may substitute for that boundary.

The implementation-private authoritative fields are exactly `_records` and
`_envelopes`. Store methods may access their own state. Every other production
owner must use `put`, `get`, `records`, or `envelopes`. A future authoritative
state field requires registry review and a new child and parent hash.

## Frozen replay-owner census

{owners}

The production module is mechanically parsed with Python AST. The discovered
owner set must equal this registry with no missing or stale names. The entire
production module, excluding `CalendarEvidenceStore` method bodies, is audited
for dotted, literal `getattr`/`setattr`, `__dict__`, and `vars` access to the
reserved internals. Each owner must reach a documented store surface directly
or through another compliant enumerated owner.

The five authoritative boundary bodies remain required to contain a direct
executable AST call to `assert_trusted_persistence_dependency`. Runtime guards,
`functools.wraps`, `__wrapped__`, unguarded production owners, and aliases remain
forbidden. Controlled startup checks the calendar parent, dependency child,
exact trusted-persistence dependency, and executable manifest, but never
replaces direct body checks.

## Preserved scope and safety

The failed architecture `{FAILED_ARCHITECTURE_SHA256}` remains non-certified,
failed, superseded before use, and at zero observations. The certified trusted-
persistence dependency `{CERTIFIED_DEPENDENCY_SHA256}` remains closed and
unchanged. Source/parser, PIT/common-session, ETF, Stage-B, risk, stop, and
threshold semantics are unchanged.

No observation was collected and no real Stage-B evaluation ran. The calendar
is not certified. Calendar implementation, POSTP1-001V2R1, POSTP1-003R3,
POSTP1-004, and collection remain blocked; BTC-019 is untouched and Epic T is
unchanged. This correction authorizes only independent exact-hash xHigh
architecture re-review.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Iterable[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    decision = authority_boundary_definition(registry)
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {DEFINITION_FILENAME: decision}
    payloads.update({filename: globals()[builder]() for filename, builder in registry})
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
        name = filename.removesuffix(".json")
        if decision["child_definition_sha256"].get(name) != expected["definition_sha256"]:
            raise AuthorityBoundaryError(f"authority boundary does not bind {filename}")
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise AuthorityBoundaryError("persisted report does not reproduce")
    return decision


def main() -> None:  # pragma: no cover - artifact writer
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output_dir = args.output_dir or root / OUTPUT_NAMESPACE
    print(write_artifacts(output_dir)["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
