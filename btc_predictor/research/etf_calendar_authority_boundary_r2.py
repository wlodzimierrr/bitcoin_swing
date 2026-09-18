"""Universal replay-route closure proof for the ETF calendar authority boundary.

This architecture-decision builder supersedes the failed R1 proof artifact.  It
does not install runtime guards or modify the production calendar.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from btc_predictor.research import etf_calendar_authority_boundary_r1 as r1


DECISION_VERSION = r1.DECISION_VERSION
PROGRAM_TICKET = "POSTP1-001V2A-AD1-R2"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_in_process_authority_boundary_v1_r2"
DEFINITION_FILENAME = r1.DEFINITION_FILENAME
REPORT_FILENAME = r1.REPORT_FILENAME
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_XHIGH_ARCHITECTURE_REVIEW"
FINAL_CLASSIFICATION = (
    "ETF_CALENDAR_IN_PROCESS_AUTHORITY_BOUNDARY_V1_READY_FOR_FINAL_XHIGH_ARCHITECTURE_REVIEW"
)
CALENDAR_MODULE = r1.CALENDAR_MODULE
CALENDAR_SOURCE = r1.CALENDAR_SOURCE
CERTIFIED_DEPENDENCY_VERSION = r1.CERTIFIED_DEPENDENCY_VERSION
CERTIFIED_DEPENDENCY_SHA256 = r1.CERTIFIED_DEPENDENCY_SHA256
FAILED_ARCHITECTURE_SHA256 = r1.FAILED_ARCHITECTURE_SHA256
FAILED_R1_ARCHITECTURE_SHA256 = (
    "a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0"
)
FAILED_CALENDAR_LINEAGE = r1.FAILED_CALENDAR_LINEAGE
FROZEN_AUTHORITATIVE_INTERNALS = r1.FROZEN_AUTHORITATIVE_INTERNALS
FROZEN_REPLAY_OWNERS = r1.FROZEN_REPLAY_OWNERS
REQUIRED_DIRECT_BODIES = r1.REQUIRED_DIRECT_BODIES
STORE_APIS = r1.STORE_APIS

AuthorityBoundaryError = r1.AuthorityBoundaryError
_canonical_json = r1._canonical_json
_digest = r1._digest
_definition = r1._definition
_verify_definition_digest = r1._verify_definition_digest
_annotation_names_calendar_store = r1._annotation_names_calendar_store
_top_level_functions = r1._top_level_functions
_literal_string = r1._literal_string
audit_private_state_access = r1.audit_private_state_access
_required_body_nodes = r1._required_body_nodes
_direct_calls_in_body = r1._direct_calls_in_body


EdgeKind = Literal[
    "DOCUMENTED_STORE_API_TERMINAL",
    "ENUMERATED_REPLAY_OWNER_EDGE",
    "FORBIDDEN_UNDOCUMENTED_STORE_METHOD",
    "FORBIDDEN_UNENUMERATED_STORE_FORWARD",
    "FORBIDDEN_PRIVATE_STATE_ROUTE",
]


@dataclass(frozen=True, order=True)
class ReplayRouteEdge:
    """One deterministically identified syntactic store-dependent route."""

    owner: str
    lineno: int
    col_offset: int
    kind: EdgeKind
    target: str


@dataclass(frozen=True)
class StoreBearingExpressions:
    """Mechanical store roots and propagated references for one function."""

    references: frozenset[str]
    vararg_containers: frozenset[str]
    kwarg_containers: frozenset[str]

    def is_store(self, expression: ast.expr) -> bool:
        if isinstance(expression, ast.Name):
            return expression.id in self.references
        if isinstance(expression, ast.Subscript) and isinstance(expression.value, ast.Name):
            return expression.value.id in (
                self.vararg_containers | self.kwarg_containers
            )
        return False

    def forwards_store(self, expression: ast.expr, *, keyword_star: bool = False) -> bool:
        if self.is_store(expression):
            return True
        if isinstance(expression, ast.Starred) and isinstance(expression.value, ast.Name):
            return expression.value.id in self.vararg_containers
        if keyword_star and isinstance(expression, ast.Name):
            return expression.id in self.kwarg_containers
        return False


def _parameter_rows(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[tuple[ast.arg, ...], ast.arg | None, ast.arg | None]:
    ordinary = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    return ordinary, node.args.vararg, node.args.kwarg


def _assigned_names(target: ast.expr) -> set[str]:
    if isinstance(target, ast.Name):
        return {target.id}
    if isinstance(target, (ast.Tuple, ast.List)):
        return {name for child in target.elts for name in _assigned_names(child)}
    return set()


def _iterates_store_values(
    expression: ast.expr,
    varargs: set[str],
    kwargs: set[str],
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in varargs
    return (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr == "values"
        and isinstance(expression.func.value, ast.Name)
        and expression.func.value.id in kwargs
    )


def store_bearing_expressions(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> StoreBearingExpressions:
    """Build the one authoritative reference model used by every route audit."""

    ordinary, vararg, kwarg = _parameter_rows(node)
    references = {
        parameter.arg
        for parameter in ordinary
        if _annotation_names_calendar_store(parameter.annotation)
        or parameter.arg == "store"
        or parameter.arg.endswith("_store")
    }
    varargs = {
        vararg.arg
        for vararg in (vararg,)
        if vararg is not None and _annotation_names_calendar_store(vararg.annotation)
    }
    kwargs = {
        kwarg.arg
        for kwarg in (kwarg,)
        if kwarg is not None and _annotation_names_calendar_store(kwarg.annotation)
    }
    changed = True
    while changed:
        changed = False
        model = StoreBearingExpressions(
            frozenset(references), frozenset(varargs), frozenset(kwargs)
        )
        for candidate in ast.walk(node):
            targets: Sequence[ast.expr] = ()
            value: ast.expr | None = None
            if isinstance(candidate, ast.Assign):
                targets, value = candidate.targets, candidate.value
            elif isinstance(candidate, ast.AnnAssign) and candidate.value is not None:
                targets, value = (candidate.target,), candidate.value
            if value is not None and model.is_store(value):
                for target in targets:
                    for name in _assigned_names(target):
                        if name not in references:
                            references.add(name)
                            changed = True
            if isinstance(candidate, (ast.For, ast.AsyncFor)) and _iterates_store_values(
                candidate.iter, varargs, kwargs
            ):
                for name in _assigned_names(candidate.target):
                    if name not in references:
                        references.add(name)
                        changed = True
    return StoreBearingExpressions(
        frozenset(references), frozenset(varargs), frozenset(kwargs)
    )


def _call_forwards_store(call: ast.Call, model: StoreBearingExpressions) -> bool:
    return any(model.forwards_store(value) for value in call.args) or any(
        model.forwards_store(keyword.value, keyword_star=keyword.arg is None)
        for keyword in call.keywords
    )


def extract_replay_route_edges(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
) -> tuple[ReplayRouteEdge, ...]:
    """Classify every mechanically known store-dependent call/access edge."""

    tree = ast.parse(source)
    functions = _top_level_functions(tree)
    frozen = set(frozen_owners)
    edges: list[ReplayRouteEdge] = []
    for owner, node in functions.items():
        model = store_bearing_expressions(node)
        for candidate in ast.walk(node):
            if (
                isinstance(candidate, ast.Attribute)
                and model.is_store(candidate.value)
                and candidate.attr in FROZEN_AUTHORITATIVE_INTERNALS
            ):
                edges.append(
                    ReplayRouteEdge(
                        owner,
                        candidate.lineno,
                        candidate.col_offset,
                        "FORBIDDEN_PRIVATE_STATE_ROUTE",
                        candidate.attr,
                    )
                )
            if not isinstance(candidate, ast.Call):
                continue
            if isinstance(candidate.func, ast.Attribute) and model.is_store(
                candidate.func.value
            ):
                method = candidate.func.attr
                if method in STORE_APIS:
                    kind: EdgeKind = "DOCUMENTED_STORE_API_TERMINAL"
                elif method in FROZEN_AUTHORITATIVE_INTERNALS:
                    kind = "FORBIDDEN_PRIVATE_STATE_ROUTE"
                else:
                    kind = "FORBIDDEN_UNDOCUMENTED_STORE_METHOD"
                edges.append(
                    ReplayRouteEdge(
                        owner, candidate.lineno, candidate.col_offset, kind, method
                    )
                )
                continue
            if (
                isinstance(candidate.func, ast.Name)
                and candidate.func.id in {"getattr", "setattr", "vars"}
                and candidate.args
                and model.is_store(candidate.args[0])
            ):
                edges.append(
                    ReplayRouteEdge(
                        owner,
                        candidate.lineno,
                        candidate.col_offset,
                        "FORBIDDEN_PRIVATE_STATE_ROUTE",
                        candidate.func.id,
                    )
                )
                continue
            if not _call_forwards_store(candidate, model):
                continue
            called = candidate.func.id if isinstance(candidate.func, ast.Name) else None
            edges.append(
                ReplayRouteEdge(
                    owner,
                    candidate.lineno,
                    candidate.col_offset,
                    "ENUMERATED_REPLAY_OWNER_EDGE"
                    if called in frozen
                    else "FORBIDDEN_UNENUMERATED_STORE_FORWARD",
                    called or ast.unparse(candidate.func),
                )
            )
    return tuple(sorted(set(edges)))


def discover_replay_owners(source: str) -> tuple[str, ...]:
    """Discover consumers using the same reference and edge model as validation."""

    tree = ast.parse(source)
    functions = _top_level_functions(tree)
    all_names = tuple(functions)
    all_edges = extract_replay_route_edges(source, all_names)
    edge_owners = {edge.owner for edge in all_edges}
    discovered: set[str] = set()
    for name, node in functions.items():
        ordinary, vararg, kwarg = _parameter_rows(node)
        annotated = any(
            _annotation_names_calendar_store(parameter.annotation)
            for parameter in (*ordinary, *((vararg,) if vararg else ()), *((kwarg,) if kwarg else ()))
        )
        if annotated or name in edge_owners or r1._private_access_findings(node):
            discovered.add(name)
    return tuple(name for name in functions if name in discovered)


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


def _reject_owner_cycles(graph: Mapping[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(owner: str, path: tuple[str, ...]) -> None:
        if owner in visiting:
            start = path.index(owner)
            cycle = path[start:]
            raise AuthorityBoundaryError(f"replay-owner cycle forbidden: {' -> '.join(cycle)}")
        if owner in visited:
            return
        visiting.add(owner)
        for target in sorted(graph[owner]):
            visit(target, (*path, target))
        visiting.remove(owner)
        visited.add(owner)

    for owner in sorted(graph):
        visit(owner, (owner,))


def audit_replay_owner_api_routes(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
) -> tuple[ReplayRouteEdge, ...]:
    """Prove universal permitted-edge, acyclic, terminal route closure."""

    functions = _top_level_functions(ast.parse(source))
    missing = set(frozen_owners) - set(functions)
    if missing:
        raise AuthorityBoundaryError(f"stale replay-owner registry: {sorted(missing)!r}")
    frozen = set(frozen_owners)
    edges = tuple(edge for edge in extract_replay_route_edges(source, frozen_owners) if edge.owner in frozen)
    forbidden = [edge for edge in edges if edge.kind.startswith("FORBIDDEN_")]
    if forbidden:
        rendered = ", ".join(
            f"{edge.owner}:{edge.lineno}:{edge.kind}:{edge.target}" for edge in forbidden
        )
        raise AuthorityBoundaryError(f"forbidden store-dependent replay route: {rendered}")
    by_owner = {owner: [edge for edge in edges if edge.owner == owner] for owner in frozen}
    empty = sorted(owner for owner, owner_edges in by_owner.items() if not owner_edges)
    if empty:
        raise AuthorityBoundaryError(f"replay owner has no store-dependent edge: {empty!r}")
    graph = {
        owner: {
            edge.target
            for edge in owner_edges
            if edge.kind == "ENUMERATED_REPLAY_OWNER_EDGE"
        }
        for owner, owner_edges in by_owner.items()
    }
    if any(target not in frozen for targets in graph.values() for target in targets):
        raise AuthorityBoundaryError("owner edge targets an unenumerated replay owner")
    _reject_owner_cycles(graph)

    terminates: dict[str, bool] = {}

    def prove(owner: str) -> bool:
        if owner in terminates:
            return terminates[owner]
        owner_edges = by_owner[owner]
        has_terminal = any(
            edge.kind == "DOCUMENTED_STORE_API_TERMINAL" for edge in owner_edges
        )
        owner_targets = [
            edge.target
            for edge in owner_edges
            if edge.kind == "ENUMERATED_REPLAY_OWNER_EDGE"
        ]
        result = has_terminal or bool(owner_targets)
        result = result and all(prove(target) for target in owner_targets)
        terminates[owner] = result
        return result

    unresolved = sorted(owner for owner in frozen if not prove(owner))
    if unresolved:
        raise AuthorityBoundaryError(
            "replay owner path does not terminate at a documented store API: "
            f"{unresolved!r}"
        )
    return edges


def audit_static_production_surface(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
) -> None:
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
        if isinstance(candidate, ast.Call) and (
            (isinstance(candidate.func, ast.Name) and candidate.func.id == "wraps")
            or (isinstance(candidate.func, ast.Attribute) and candidate.func.attr == "wraps")
        ):
            raise AuthorityBoundaryError("functools.wraps authority guard forbidden")
        if isinstance(candidate, (ast.Assign, ast.AnnAssign)):
            targets = candidate.targets if isinstance(candidate, ast.Assign) else [candidate.target]
            if any(
                isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "CalendarEvidenceStore"
                and target.attr in STORE_APIS
                for target in targets
            ):
                raise AuthorityBoundaryError("runtime store-method guard rebinding forbidden")


# Accepted R1 architecture children are reused byte-for-byte.
trusted_computing_boundary = r1.trusted_computing_boundary
private_state_boundary = r1.private_state_boundary
direct_body_enforcement = r1.direct_body_enforcement
project_owned_bypass_prohibition = r1.project_owned_bypass_prohibition
runtime_mutation_threat_model = r1.runtime_mutation_threat_model


def replay_owner_registry() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_OWNER_REGISTRY_V1_R2",
            "production_module": CALENDAR_MODULE,
            "owners": list(FROZEN_REPLAY_OWNERS),
            "placeholder_category_permitted": False,
            "discovery_rules": [
                "ORDINARY_POSITIONAL_OR_KEYWORD_ANNOTATED_CalendarEvidenceStore",
                "ANNOTATED_VARARG_ELEMENTS_ARE_STORE_BEARING",
                "ANNOTATED_KWARG_VALUES_ARE_STORE_BEARING",
                "INDEX_ALIAS_AND_ITERATION_PROPAGATION",
                "SHARED_STORE_BEARING_EXPRESSION_MODEL_FOR_DISCOVERY_AND_ROUTES",
            ],
            "required_relation": "MECHANICALLY_DISCOVERED_OWNERS_EQUALS_FROZEN_REGISTRY",
        }
    )


def replay_route_model() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_ROUTE_MODEL_V1",
            "edge_kinds": [
                "DOCUMENTED_STORE_API_TERMINAL",
                "ENUMERATED_REPLAY_OWNER_EDGE",
                "FORBIDDEN_UNDOCUMENTED_STORE_METHOD",
                "FORBIDDEN_UNENUMERATED_STORE_FORWARD",
                "FORBIDDEN_PRIVATE_STATE_ROUTE",
            ],
            "documented_terminal_store_apis": list(STORE_APIS),
            "all_store_dependent_edges_classified": True,
            "undocumented_store_methods_permitted": False,
            "store_bearing_expressions": [
                "DIRECT_STORE_PARAMETERS",
                "ORDINARY_ALIASES",
                "ANNOTATED_VARARG_SUBSCRIPTS_AND_STARRED_ELEMENTS",
                "ANNOTATED_KWARG_SUBSCRIPTS_AND_STARRED_VALUES",
                "VARIADIC_ELEMENT_OR_VALUE_LOOP_TARGETS",
            ],
            "stable_edge_identity": "OWNER_LINE_COLUMN_KIND_TARGET",
        }
    )


def transitive_replay_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_TRANSITIVE_REPLAY_RULE_V1_R2",
            "rules": [
                "ALL_STORE_DEPENDENT_EDGES_MUST_BE_PERMITTED",
                "ALL_OWNER_PATHS_MUST_TERMINATE_AT_DOCUMENTED_STORE_API",
                "ANY_OWNER_CYCLE_IS_FORBIDDEN",
                "ANY_UNDOCUMENTED_STORE_METHOD_IS_FORBIDDEN",
                "ANY_STORE_FORWARD_TO_UNENUMERATED_OWNER_IS_FORBIDDEN",
            ],
            "owner_compliance_quantifier": "UNIVERSAL",
            "existential_compliance_permitted": False,
            "owner_graph_must_be_acyclic": True,
            "branch_feasibility_reasoning": "NOT_PERFORMED_ALL_SYNTACTIC_EDGES_COUNT",
        }
    )


def static_surface_audit() -> dict[str, Any]:
    child = dict(r1.static_surface_audit())
    child.pop("definition_sha256")
    child.update(
        {
            "contract_version": "ETF_CALENDAR_STATIC_SURFACE_AUDIT_V1_R2",
            "universal_route_edge_classification": True,
            "undocumented_store_methods_permitted": False,
            "store_forwarding_to_unenumerated_owner_permitted": False,
            "replay_owner_graph_acyclic": True,
            "all_owner_paths_terminate_at_documented_store_api": True,
            "annotated_variadic_parameter_discovery": True,
            "variadic_element_and_value_propagation": True,
        }
    )
    return _definition(child)


def drift_science_and_safety() -> dict[str, Any]:
    child = dict(r1.drift_science_and_safety())
    child.pop("definition_sha256")
    child["contract_version"] = "ETF_CALENDAR_DRIFT_SCIENCE_AND_SAFETY_V1_R2"
    child["failed_architectures"] = [
        {
            "definition_sha256": FAILED_ARCHITECTURE_SHA256,
            "failed": True,
            "certified": False,
            "used": False,
            "prospective_observations": 0,
        },
        {
            "definition_sha256": FAILED_R1_ARCHITECTURE_SHA256,
            "failed": True,
            "certified": False,
            "used": False,
            "prospective_observations": 0,
        },
    ]
    return _definition(child)


_CHILD_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("trusted_computing_boundary.json", "trusted_computing_boundary"),
    ("private_state_boundary.json", "private_state_boundary"),
    ("replay_owner_registry.json", "replay_owner_registry"),
    ("replay_route_model.json", "replay_route_model"),
    ("transitive_replay_rule.json", "transitive_replay_rule"),
    ("direct_body_enforcement.json", "direct_body_enforcement"),
    ("project_owned_bypass_prohibition.json", "project_owned_bypass_prohibition"),
    ("runtime_mutation_threat_model.json", "runtime_mutation_threat_model"),
    ("static_surface_audit.json", "static_surface_audit"),
    ("drift_science_and_safety.json", "drift_science_and_safety"),
)


def _children(
    child_artifacts: Sequence[tuple[str, str]] | None = None,
) -> dict[str, dict[str, Any]]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    return {
        filename.removesuffix(".json"): globals()[builder]()
        for filename, builder in registry
    }


def authority_boundary_definition(
    child_artifacts: Sequence[tuple[str, str]] | None = None,
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
            "required_review": "INDEPENDENT_EXACT_HASH_XHIGH_FINAL_ARCHITECTURE_REVIEW",
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
                "all_store_dependent_edges_classified": True,
                "owner_route_compliance_is_universal": True,
                "owner_cycles_permitted": False,
                "annotated_variadic_store_consumers_discovered": True,
                "direct_entrypoint_body_enforcement_required": True,
                "dynamic_wrapper_installation_permitted": False,
                "functools_wraps_authority_guards_permitted": False,
                "exposed_unguarded_production_owners_permitted": False,
                "process_isolation_required_if_hostile_same_process_mutation_enters_scope": True,
            },
            "authorization": {
                "independent_architecture_xhigh_final_review_may_begin": True,
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

## Universal replay-route proof

Every syntactic store-dependent edge is classified as a documented terminal,
an enumerated owner edge, or a forbidden undocumented method, unenumerated
forward, or private-state route. Forbidden edges refuse the audit. The owner
graph must be acyclic, every owner must have a store-dependent edge, and every
owner path must terminate at `put`, `get`, `records`, or `envelopes`. One valid
route never excuses another invalid route.

Annotated `*args: CalendarEvidenceStore` elements and
`**kwargs: CalendarEvidenceStore` values are store-bearing. Indexed references,
ordinary aliases, iteration targets, and resolvable starred forwarding share
the same mechanical model used by discovery and validation.

## Frozen replay-owner census

{owners}

The discovered production set equals the eleven-owner registry. No production
calendar code changed.

## Preserved boundary and safety

The production Python process remains trusted. Arbitrary caller mutation stays
out of scope; repository-owned access to `_records` or `_envelopes` remains
forbidden. If hostile same-process mutation enters scope, process isolation is
required. The five direct-body dependency assertions, wrapper prohibitions,
and startup self-check remain required.

Failed architectures `{FAILED_ARCHITECTURE_SHA256}` and
`{FAILED_R1_ARCHITECTURE_SHA256}` remain immutable, non-certified, unused, and
at zero observations. Trusted persistence `{CERTIFIED_DEPENDENCY_SHA256}` is
closed and unchanged. Source/parser, PIT/common-session, ETF, Stage-B, risk,
stop, and threshold semantics are unchanged.

No observation was collected and no Stage-B evaluation ran. Calendar
implementation, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004, and collection remain
blocked. BTC-019 is untouched and Epic T is unchanged. This correction
authorizes only independent exact-hash xHigh final architecture review.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Sequence[tuple[str, str]] | None = None,
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
        if decision["child_definition_sha256"].get(filename.removesuffix(".json")) != expected[
            "definition_sha256"
        ]:
            raise AuthorityBoundaryError(f"authority boundary does not bind {filename}")
    if (output_dir / REPORT_FILENAME).read_text(encoding="utf-8") != _report_markdown(decision):
        raise AuthorityBoundaryError("persisted report does not reproduce")
    return decision


def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[2]
    output_dir = args.output_dir or root / OUTPUT_NAMESPACE
    print(write_artifacts(output_dir)["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
