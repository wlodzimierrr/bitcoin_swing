"""Narrow corrected store-capability proof architecture for the ETF calendar.

The certified candidate grammar is intentionally production-minimal: an
ordinary parameter explicitly annotated ``CalendarEvidenceStore`` is the only
store-bearing root, that parameter is immutable, and its only permitted uses
are direct documented API calls or non-starred forwarding to an exact frozen
replay owner.  This module does not modify or certify calendar production.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from btc_predictor.research import etf_calendar_store_capability_normal_form as failed


DECISION_VERSION = "ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1"
PROGRAM_TICKET = "POSTP1-001V2A-PAD1-R1"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_store_capability_normal_form_v1_r1"
DEFINITION_FILENAME = "store_capability_normal_form_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
FINAL_CLASSIFICATION = (
    "ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_READY_FOR_FINAL_XHIGH_REVIEW"
)
REQUIRED_REVIEW = (
    "POSTP1-002V2A-PAD1-R1_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW"
)
FAILED_PARENT_SHA256 = "9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295"

CALENDAR_SOURCE = failed.CALENDAR_SOURCE
CERTIFIED_DEPENDENCY_VERSION = failed.CERTIFIED_DEPENDENCY_VERSION
CERTIFIED_DEPENDENCY_SHA256 = failed.CERTIFIED_DEPENDENCY_SHA256
FAILED_ARCHITECTURE_LINEAGE = (*failed.FAILED_ARCHITECTURE_LINEAGE, FAILED_PARENT_SHA256)
FAILED_CALENDAR_LINEAGE = failed.FAILED_CALENDAR_LINEAGE
FROZEN_REPLAY_OWNERS = failed.FROZEN_REPLAY_OWNERS
REQUIRED_DIRECT_BODIES = failed.REQUIRED_DIRECT_BODIES
STORE_APIS = failed.STORE_APIS

NormalFormError = failed.NormalFormError
_definition = failed._definition
_verify_definition_digest = failed._verify_definition_digest
_annotation_names_calendar_store = failed._annotation_names_calendar_store
_top_level_functions = failed._top_level_functions


UseKind = Literal[
    "PERMITTED_DIRECT_STORE_API_CALL",
    "PERMITTED_ENUMERATED_OWNER_FORWARD",
    "FORBIDDEN_STORE_ATTRIBUTE_EXTRACTION",
    "FORBIDDEN_UNKNOWN_FORWARD",
    "FORBIDDEN_STARRED_FORWARD",
    "FORBIDDEN_CONTAINER_ESCAPE",
    "FORBIDDEN_RETURN_OR_YIELD",
    "FORBIDDEN_OBJECT_OR_SUBSCRIPT_STORAGE",
    "FORBIDDEN_NESTED_SCOPE_CAPTURE",
    "FORBIDDEN_DYNAMIC_ACCESS",
    "FORBIDDEN_OTHER_STORE_USE",
    "FORBIDDEN_STORE_ROOT_REBIND_OR_UNBIND",
]


@dataclass(frozen=True, order=True)
class StoreUse:
    """One stable classification of a root occurrence or binding event."""

    owner: str
    lineno: int
    col_offset: int
    kind: UseKind
    detail: str


@dataclass(frozen=True, order=True)
class OwnerEdge:
    owner: str
    lineno: int
    col_offset: int
    kind: Literal["DOCUMENTED_STORE_API_TERMINAL", "ENUMERATED_REPLAY_OWNER_EDGE"]
    target: str


def _parameters(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[tuple[ast.arg, ...], ast.arg | None, ast.arg | None]:
    ordinary = (*node.args.posonlyargs, *node.args.args, *node.args.kwonlyargs)
    return ordinary, node.args.vararg, node.args.kwarg


def _annotated_ordinary_roots(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> frozenset[str]:
    ordinary, _, _ = _parameters(node)
    return frozenset(
        parameter.arg
        for parameter in ordinary
        if _annotation_names_calendar_store(parameter.annotation)
    )


def _annotated_variadics(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[ast.arg, ...]:
    _, vararg, kwarg = _parameters(node)
    return tuple(
        parameter
        for parameter in (vararg, kwarg)
        if parameter is not None
        and _annotation_names_calendar_store(parameter.annotation)
    )


def _all_function_nodes(tree: ast.AST) -> tuple[ast.FunctionDef | ast.AsyncFunctionDef, ...]:
    return tuple(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )


def _call_constructs_calendar_store(node: ast.Call) -> bool:
    called = node.func
    if isinstance(called, ast.Name):
        return called.id == "CalendarEvidenceStore"
    return isinstance(called, ast.Attribute) and called.attr == "CalendarEvidenceStore"


def _module_wide_structural_refusals(tree: ast.Module) -> tuple[StoreUse, ...]:
    """Reject unsupported owners, variadics, and local construction first."""

    top_level = {
        node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    refusals: list[StoreUse] = []
    for node in _all_function_nodes(tree):
        annotated = bool(_annotated_ordinary_roots(node) or _annotated_variadics(node))
        if node not in top_level and annotated:
            refusals.append(
                StoreUse(
                    node.name,
                    node.lineno,
                    node.col_offset,
                    "FORBIDDEN_NESTED_SCOPE_CAPTURE",
                    "nested_annotated_store_owner",
                )
            )
        for parameter in _annotated_variadics(node):
            refusals.append(
                StoreUse(
                    node.name,
                    parameter.lineno,
                    parameter.col_offset,
                    "FORBIDDEN_OTHER_STORE_USE",
                    "annotated_store_variadic_parameter",
                )
            )
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and _annotation_names_calendar_store(
            node.annotation
        ):
            refusals.append(
                StoreUse(
                    "<module-structural-scan>",
                    node.lineno,
                    node.col_offset,
                    "FORBIDDEN_OTHER_STORE_USE",
                    "annotated_local_store_binding",
                )
            )
        elif isinstance(node, ast.Call) and _call_constructs_calendar_store(node):
            refusals.append(
                StoreUse(
                    "<module-structural-scan>",
                    node.lineno,
                    node.col_offset,
                    "FORBIDDEN_OTHER_STORE_USE",
                    "local_store_construction",
                )
            )
    return tuple(sorted(set(refusals)))


def _bound_names(target: ast.AST) -> tuple[tuple[str, ast.AST], ...]:
    if isinstance(target, ast.Name):
        return ((target.id, target),)
    if isinstance(target, (ast.Tuple, ast.List)):
        return tuple(item for element in target.elts for item in _bound_names(element))
    if isinstance(target, ast.Starred):
        return _bound_names(target.value)
    return ()


def _pattern_bound_names(pattern: ast.pattern) -> tuple[tuple[str, ast.AST], ...]:
    found: list[tuple[str, ast.AST]] = []
    for node in ast.walk(pattern):
        if isinstance(node, ast.MatchAs) and node.name is not None:
            found.append((node.name, node))
        elif isinstance(node, ast.MatchStar) and node.name is not None:
            found.append((node.name, node))
        elif isinstance(node, ast.MatchMapping) and node.rest is not None:
            found.append((node.rest, node))
    return tuple(found)


def _same_scope_bindings(
    owner: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[tuple[str, ast.AST, str], ...]:
    """Enumerate Python 3.12 same-function binding and unbinding forms."""

    found: list[tuple[str, ast.AST, str]] = []

    def add_target(target: ast.AST, detail: str) -> None:
        found.extend((name, node, detail) for name, node in _bound_names(target))

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node is owner:
                for statement in node.body:
                    self.visit(statement)
            else:
                found.append((node.name, node, "FunctionDef"))

        def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
            if node is owner:
                for statement in node.body:
                    self.visit(statement)
            else:
                found.append((node.name, node, "AsyncFunctionDef"))

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            found.append((node.name, node, "ClassDef"))

        def visit_Lambda(self, node: ast.Lambda) -> None:
            return

        def visit_Assign(self, node: ast.Assign) -> None:
            for target in node.targets:
                add_target(target, "Assign")
            self.visit(node.value)

        def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
            add_target(node.target, "AnnAssign")
            if node.value is not None:
                self.visit(node.value)

        def visit_AugAssign(self, node: ast.AugAssign) -> None:
            add_target(node.target, "AugAssign")
            self.visit(node.value)

        def visit_NamedExpr(self, node: ast.NamedExpr) -> None:
            add_target(node.target, "NamedExpr")
            self.visit(node.value)

        def visit_For(self, node: ast.For) -> None:
            add_target(node.target, "For")
            self.visit(node.iter)
            for statement in (*node.body, *node.orelse):
                self.visit(statement)

        def visit_AsyncFor(self, node: ast.AsyncFor) -> None:
            add_target(node.target, "AsyncFor")
            self.visit(node.iter)
            for statement in (*node.body, *node.orelse):
                self.visit(statement)

        def visit_With(self, node: ast.With) -> None:
            for item in node.items:
                self.visit(item.context_expr)
                if item.optional_vars is not None:
                    add_target(item.optional_vars, "With")
            for statement in node.body:
                self.visit(statement)

        def visit_AsyncWith(self, node: ast.AsyncWith) -> None:
            for item in node.items:
                self.visit(item.context_expr)
                if item.optional_vars is not None:
                    add_target(item.optional_vars, "AsyncWith")
            for statement in node.body:
                self.visit(statement)

        def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
            if node.name is not None:
                found.append((node.name, node, "ExceptHandler"))
            if node.type is not None:
                self.visit(node.type)
            for statement in node.body:
                self.visit(statement)

        def visit_match_case(self, node: ast.match_case) -> None:
            found.extend(
                (name, bound, "MatchCapture")
                for name, bound in _pattern_bound_names(node.pattern)
            )
            if node.guard is not None:
                self.visit(node.guard)
            for statement in node.body:
                self.visit(statement)

        def visit_Import(self, node: ast.Import) -> None:
            for alias in node.names:
                found.append((alias.asname or alias.name.split(".")[0], node, "Import"))

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
            for alias in node.names:
                if alias.name != "*":
                    found.append((alias.asname or alias.name, node, "ImportFrom"))

        def visit_Delete(self, node: ast.Delete) -> None:
            for target in node.targets:
                add_target(target, "Del")

    Visitor().visit(owner)
    return tuple(found)


def _binding_refusals(
    owner: ast.FunctionDef | ast.AsyncFunctionDef, roots: frozenset[str]
) -> tuple[StoreUse, ...]:
    return tuple(
        sorted(
            StoreUse(
                owner.name,
                getattr(node, "lineno", owner.lineno),
                getattr(node, "col_offset", owner.col_offset),
                "FORBIDDEN_STORE_ROOT_REBIND_OR_UNBIND",
                detail,
            )
            for name, node, detail in _same_scope_bindings(owner)
            if name in roots
        )
    )


def _parent_map(root: ast.AST) -> dict[ast.AST, ast.AST]:
    return {
        child: parent
        for parent in ast.walk(root)
        for child in ast.iter_child_nodes(parent)
    }


def _nested_scope_between(
    expression: ast.AST,
    owner: ast.FunctionDef | ast.AsyncFunctionDef,
    parents: Mapping[ast.AST, ast.AST],
) -> bool:
    current = parents.get(expression)
    boundaries = (
        ast.FunctionDef,
        ast.AsyncFunctionDef,
        ast.Lambda,
        ast.ClassDef,
        ast.GeneratorExp,
        ast.ListComp,
        ast.SetComp,
        ast.DictComp,
    )
    while current is not None and current is not owner:
        if isinstance(current, boundaries):
            return True
        current = parents.get(current)
    return False


def _inside_container(
    expression: ast.AST,
    owner: ast.FunctionDef | ast.AsyncFunctionDef,
    parents: Mapping[ast.AST, ast.AST],
) -> bool:
    current = parents.get(expression)
    while current is not None and current is not owner:
        if isinstance(current, (ast.List, ast.Tuple, ast.Dict, ast.Set)):
            return True
        if isinstance(current, (ast.stmt, ast.Lambda, ast.comprehension)):
            return False
        current = parents.get(current)
    return False


def _call_containing_argument(
    expression: ast.AST, parents: Mapping[ast.AST, ast.AST]
) -> tuple[ast.Call, ast.AST] | None:
    parent = parents.get(expression)
    argument: ast.AST = expression
    if isinstance(parent, ast.Starred) and parent.value is expression:
        argument = parent
        parent = parents.get(parent)
    if isinstance(parent, ast.keyword) and parent.value is expression:
        argument = parent
        parent = parents.get(parent)
    if isinstance(parent, ast.Call):
        return parent, argument
    return None


def _call_name(call: ast.Call) -> str | None:
    return call.func.id if isinstance(call.func, ast.Name) else None


def _assignment_targets(parent: ast.Assign | ast.AnnAssign) -> tuple[ast.AST, ...]:
    return tuple(parent.targets) if isinstance(parent, ast.Assign) else (parent.target,)


def _classify_root_load(
    expression: ast.Name,
    owner: ast.FunctionDef | ast.AsyncFunctionDef,
    parents: Mapping[ast.AST, ast.AST],
    frozen: frozenset[str],
) -> tuple[UseKind, str]:
    if _nested_scope_between(expression, owner, parents):
        return "FORBIDDEN_NESTED_SCOPE_CAPTURE", "nested_scope"

    parent = parents.get(expression)
    if isinstance(parent, ast.Attribute) and parent.value is expression:
        grandparent = parents.get(parent)
        if (
            isinstance(grandparent, ast.Call)
            and grandparent.func is parent
            and parent.attr in STORE_APIS
        ):
            return "PERMITTED_DIRECT_STORE_API_CALL", parent.attr
        if parent.attr == "__dict__":
            return "FORBIDDEN_DYNAMIC_ACCESS", parent.attr
        return "FORBIDDEN_STORE_ATTRIBUTE_EXTRACTION", parent.attr

    call_argument = _call_containing_argument(expression, parents)
    if call_argument is not None:
        call, argument = call_argument
        called = _call_name(call)
        if called in {"getattr", "setattr", "vars"}:
            return "FORBIDDEN_DYNAMIC_ACCESS", called
        if isinstance(argument, ast.Starred) or (
            isinstance(argument, ast.keyword) and argument.arg is None
        ):
            return "FORBIDDEN_STARRED_FORWARD", called or ast.unparse(call.func)
        if called in frozen:
            return "PERMITTED_ENUMERATED_OWNER_FORWARD", called
        return "FORBIDDEN_UNKNOWN_FORWARD", called or ast.unparse(call.func)

    if isinstance(parent, (ast.Assign, ast.AnnAssign)):
        targets = _assignment_targets(parent)
        if any(isinstance(target, (ast.Attribute, ast.Subscript)) for target in targets):
            return "FORBIDDEN_OBJECT_OR_SUBSCRIPT_STORAGE", "assignment_target"
        return "FORBIDDEN_OTHER_STORE_USE", "store_alias_or_assignment"
    if _inside_container(expression, owner, parents):
        return "FORBIDDEN_CONTAINER_ESCAPE", "new_container"
    if isinstance(parent, (ast.Return, ast.Yield, ast.YieldFrom)):
        return "FORBIDDEN_RETURN_OR_YIELD", type(parent).__name__
    return "FORBIDDEN_OTHER_STORE_USE", type(parent).__name__ if parent else "root"


def classify_store_uses(
    source: str, frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS
) -> tuple[StoreUse, ...]:
    """Classify structural refusals, all binding events, and every root load."""

    tree = ast.parse(source)
    uses: list[StoreUse] = list(_module_wide_structural_refusals(tree))
    frozen = frozenset(frozen_owners)
    for owner_name, owner in _top_level_functions(tree).items():
        roots = _annotated_ordinary_roots(owner)
        if not roots:
            continue
        uses.extend(_binding_refusals(owner, roots))
        parents = _parent_map(owner)
        for candidate in ast.walk(owner):
            if (
                isinstance(candidate, ast.Name)
                and isinstance(candidate.ctx, ast.Load)
                and candidate.id in roots
            ):
                kind, detail = _classify_root_load(candidate, owner, parents, frozen)
                uses.append(
                    StoreUse(
                        owner_name,
                        candidate.lineno,
                        candidate.col_offset,
                        kind,
                        detail,
                    )
                )
    return tuple(sorted(set(uses)))


def audit_store_capability_normal_form(
    source: str, frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS
) -> tuple[StoreUse, ...]:
    uses = classify_store_uses(source, frozen_owners)
    forbidden = [use for use in uses if use.kind.startswith("FORBIDDEN_")]
    if forbidden:
        rendered = ", ".join(
            f"{use.owner}:{use.lineno}:{use.kind}:{use.detail}" for use in forbidden
        )
        raise NormalFormError(f"forbidden store-capability use: {rendered}")
    return uses


def discover_replay_owners(source: str) -> tuple[str, ...]:
    functions = _top_level_functions(ast.parse(source))
    return tuple(
        name for name, node in functions.items() if _annotated_ordinary_roots(node)
    )


def verify_replay_owner_census(
    source: str, frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS
) -> tuple[str, ...]:
    tree = ast.parse(source)
    structural = _module_wide_structural_refusals(tree)
    if structural:
        rendered = ", ".join(f"{use.owner}:{use.detail}" for use in structural)
        raise NormalFormError(f"unsupported store owner syntax: {rendered}")
    discovered = discover_replay_owners(source)
    if set(discovered) != set(frozen_owners) or len(discovered) != len(frozen_owners):
        raise NormalFormError(
            "replay-owner registry/source census mismatch: "
            f"frozen={sorted(frozen_owners)!r}, discovered={sorted(discovered)!r}"
        )
    return discovered


def extract_owner_edges(
    source: str, frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS
) -> tuple[OwnerEdge, ...]:
    """Extract graph edges only after binding and use audits pass."""

    uses = audit_store_capability_normal_form(source, frozen_owners)
    frozen = frozenset(frozen_owners)
    edges: list[OwnerEdge] = []
    for use in uses:
        if use.owner not in frozen:
            continue
        if use.kind == "PERMITTED_DIRECT_STORE_API_CALL":
            edges.append(
                OwnerEdge(
                    use.owner,
                    use.lineno,
                    use.col_offset,
                    "DOCUMENTED_STORE_API_TERMINAL",
                    use.detail,
                )
            )
        elif use.kind == "PERMITTED_ENUMERATED_OWNER_FORWARD":
            edges.append(
                OwnerEdge(
                    use.owner,
                    use.lineno,
                    use.col_offset,
                    "ENUMERATED_REPLAY_OWNER_EDGE",
                    use.detail,
                )
            )
    return tuple(sorted(set(edges)))


def _reject_cycles(graph: Mapping[str, set[str]]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(owner: str, path: tuple[str, ...]) -> None:
        if owner in visiting:
            start = path.index(owner)
            raise NormalFormError(f"replay-owner cycle forbidden: {' -> '.join(path[start:])}")
        if owner in visited:
            return
        visiting.add(owner)
        for target in sorted(graph[owner]):
            visit(target, (*path, target))
        visiting.remove(owner)
        visited.add(owner)

    for owner in sorted(graph):
        visit(owner, (owner,))


def audit_replay_owner_graph(
    source: str, frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS
) -> tuple[OwnerEdge, ...]:
    verify_replay_owner_census(source, frozen_owners)
    edges = extract_owner_edges(source, frozen_owners)
    by_owner = {
        owner: [edge for edge in edges if edge.owner == owner] for owner in frozen_owners
    }
    empty = sorted(owner for owner, owner_edges in by_owner.items() if not owner_edges)
    if empty:
        raise NormalFormError(f"replay owner has no permitted edge: {empty!r}")
    graph = {
        owner: {
            edge.target
            for edge in owner_edges
            if edge.kind == "ENUMERATED_REPLAY_OWNER_EDGE"
        }
        for owner, owner_edges in by_owner.items()
    }
    _reject_cycles(graph)
    terminal: dict[str, bool] = {}

    def prove(owner: str) -> bool:
        if owner in terminal:
            return terminal[owner]
        owner_edges = by_owner[owner]
        targets = [
            edge.target
            for edge in owner_edges
            if edge.kind == "ENUMERATED_REPLAY_OWNER_EDGE"
        ]
        result = any(
            edge.kind == "DOCUMENTED_STORE_API_TERMINAL" for edge in owner_edges
        ) or bool(targets)
        result = result and all(prove(target) for target in targets)
        terminal[owner] = result
        return result

    unresolved = sorted(owner for owner in frozen_owners if not prove(owner))
    if unresolved:
        raise NormalFormError(
            "replay owner path does not terminate at documented API: " f"{unresolved!r}"
        )
    return edges


def trusted_process_boundary_reference() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_TRUSTED_PROCESS_BOUNDARY_REFERENCE_V1_R1",
            "production_python_process_trusted": True,
            "hostile_same_process_mutation_resistance_required": False,
            "project_owned_scientific_bypasses_in_scope": True,
            "arbitrary_hostile_in_process_manipulation_in_scope": False,
            "hostile_same_process_resistance_if_later_required": "PROCESS_ISOLATION",
            "wrapper_metaclass_or_source_hash_substitutes_for_isolation": False,
            "failed_boundary_lineage": list(FAILED_ARCHITECTURE_LINEAGE),
        }
    )


def store_root_grammar() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_STORE_ROOT_GRAMMAR_V1_R1",
            "normal_form": "DIRECT_IMMUTABLE_STORE_PARAMETER_NORMAL_FORM",
            "supported_root": "ORDINARY_PARAMETER_EXPLICITLY_ANNOTATED_CalendarEvidenceStore",
            "ordinary_parameter_kinds": ["POSITIONAL_ONLY", "POSITIONAL_OR_KEYWORD", "KEYWORD_ONLY"],
            "naming_heuristics_permitted": False,
            "local_store_construction_permitted": False,
            "transparent_aliases_permitted": False,
            "annotated_store_varargs_permitted": False,
            "annotated_store_kwargs_permitted": False,
            "container_derived_stores_permitted": False,
            "nested_annotated_owners_permitted": False,
            "other_roots_or_derivations": "FAIL_UNTIL_EXPLICIT_REVIEWED_AUTHORITY_CHANGE",
        }
    )


def store_binding_discipline() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_STORE_BINDING_DISCIPLINE_V1",
            "root_binding": "FUNCTION_PARAMETER_DECLARATION_ONLY",
            "root_is_immutable": True,
            "forbidden_same_scope_binding_or_unbinding_forms": [
                "Assign", "AnnAssign", "AugAssign", "NamedExpr", "For", "AsyncFor",
                "With", "AsyncWith", "ExceptHandler", "MatchCapture", "Import",
                "ImportFrom", "FunctionDef", "AsyncFunctionDef", "ClassDef", "Del",
            ],
            "binding_audit_precedes_use_and_graph_audits": True,
            "value_flow_after_rebinding_analyzed": False,
        }
    )


def permitted_direct_store_use() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PERMITTED_DIRECT_STORE_USE_V1_R1",
            "permitted_categories": [
                "PERMITTED_DIRECT_STORE_API_CALL",
                "PERMITTED_ENUMERATED_OWNER_FORWARD",
            ],
            "direct_call_ast_shape": "ast.Call(func=ast.Attribute(value=EXACT_IMMUTABLE_ROOT, attr=DOCUMENTED_API))",
            "documented_apis": list(STORE_APIS),
            "forward_target": "EXACT_FROZEN_REPLAY_OWNER_REGISTRY",
            "ordinary_positional_forwarding": True,
            "ordinary_named_keyword_forwarding": True,
            "starred_forwarding": False,
            "replay_owners": list(FROZEN_REPLAY_OWNERS),
        }
    )


def forbidden_capability_escape_rules() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_FORBIDDEN_CAPABILITY_ESCAPE_RULES_V1_R1",
            "forbidden_categories": [kind for kind in UseKind.__args__ if kind.startswith("FORBIDDEN_")],
            "bare_documented_or_undocumented_method_extraction_permitted": False,
            "aliases_permitted": False,
            "starred_store_forwarding_permitted": False,
            "return_yield_or_container_escape_permitted": False,
            "object_or_subscript_storage_permitted": False,
            "closure_generator_or_comprehension_capture_permitted": False,
            "dynamic_attribute_authority_permitted": False,
            "unsupported_use_may_be_masked_by_valid_route": False,
            "implementation_private_authoritative_state": ["_records", "_envelopes"],
            "repository_owned_access_outside_CalendarEvidenceStore_permitted": False,
        }
    )


def nested_owner_prohibition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_NESTED_OWNER_PROHIBITION_V1",
            "scan_scope": "MODULE_WIDE_INDEPENDENT_OF_OUTER_STORE_ROOTS",
            "nested_FunctionDef_with_annotated_store_parameter": "FORBIDDEN",
            "nested_AsyncFunctionDef_with_annotated_store_parameter": "FORBIDDEN",
            "nested_store_capture": "FORBIDDEN",
            "rootless_outer_can_hide_nested_owner": False,
        }
    )


def replay_owner_graph_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_OWNER_GRAPH_RULE_V1_PAD1_R1",
            "binding_and_use_audits_must_pass_before_graph_extraction": True,
            "owner_discovery": "TOP_LEVEL_ORDINARY_EXPLICITLY_ANNOTATED_PARAMETERS_ONLY",
            "owner_count": len(FROZEN_REPLAY_OWNERS),
            "owners": list(FROZEN_REPLAY_OWNERS),
            "edge_kinds": ["DOCUMENTED_STORE_API_TERMINAL", "ENUMERATED_REPLAY_OWNER_EDGE"],
            "cycles_permitted": False,
            "every_owner_path_terminates_at_documented_store_api": True,
            "owner_census_relation": "DISCOVERED_EQUALS_FROZEN_REGISTRY_AND_COUNT_EQUALS_11",
        }
    )


def direct_body_dependency_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_DIRECT_BODY_DEPENDENCY_RULE_V1_PAD1_R1",
            "required_direct_bodies": list(REQUIRED_DIRECT_BODIES),
            "exact_dependency_assertion": "assert_trusted_persistence_dependency",
            "proof": "DIRECT_EXECUTABLE_AST_CALL_IN_EACH_REQUIRED_BODY",
            "wrapper_installed_guards_permitted": False,
            "startup_self_check": [
                "CALENDAR_AUTHORITY_PARENT",
                "TRUSTED_PERSISTENCE_DEPENDENCY_CHILD",
                "EXACT_CERTIFIED_TRUSTED_PERSISTENCE_IDENTITY",
                "CERTIFIED_PRODUCTION_SURFACE_PROOF_IDENTITY",
            ],
            "startup_check_replaces_five_direct_checks": False,
        }
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PROOF_ORDER_AND_COMPLETENESS_V1_R1",
            "proof_order": [
                "REJECT_ALL_NESTED_ANNOTATED_STORE_OWNERS_MODULE_WIDE",
                "DISCOVER_TOP_LEVEL_ORDINARY_ANNOTATED_STORE_ROOTS",
                "REJECT_ANNOTATED_STORE_VARIADICS",
                "AUDIT_IMMUTABLE_ROOT_BINDING_DISCIPLINE",
                "CLASSIFY_EVERY_ROOT_USE",
                "REJECT_EVERY_FORBIDDEN_USE",
                "RECONCILE_DISCOVERED_AND_FROZEN_OWNER_REGISTRY",
                "EXTRACT_DIRECT_API_AND_ENUMERATED_OWNER_EDGES",
                "REJECT_OWNER_CYCLES",
                "PROVE_EVERY_OWNER_PATH_TERMINATES_AT_DOCUMENTED_API",
                "VERIFY_DIRECT_DEPENDENCY_BODY_AND_STARTUP_CONTRACTS",
            ],
            "models_all_possible_python_programs": False,
            "reaching_definition_analysis": False,
            "ssa_construction": False,
            "arbitrary_control_flow_graph_proof": False,
            "alias_propagation": False,
            "completeness": "ONE_IMMUTABLE_ANNOTATED_ROOT_BINDING_PLUS_CLOSED_DIRECT_USE_SYNTAX",
            "future_unsupported_syntax": "FAIL_UNTIL_EXPLICIT_REVIEWED_AUTHORITY_CHANGE",
            "decision_certifies_grammar": True,
            "decision_certifies_current_production_conformance": False,
            "known_future_implementation_delta": (
                "COMMON_ETF_SESSION_STATUS_GENERATOR_CAPTURE_OF_EVIDENCE_STORE_"
                "MUST_BE_REWRITTEN_WITHOUT_SEMANTIC_PIT_ORDER_OR_EXCEPTION_DRIFT"
            ),
        }
    )


def science_lineage_and_safety() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_NORMAL_FORM_SCIENCE_LINEAGE_AND_SAFETY_V1_R1",
            "certified_dependency": {
                "authority_version": CERTIFIED_DEPENDENCY_VERSION,
                "definition_sha256": CERTIFIED_DEPENDENCY_SHA256,
                "status": "CLOSED_CERTIFIED_FOR_BOUNDED_ETF_CALENDAR_INTEGRATION",
                "changed": False,
            },
            "failed_architecture_lineage": [
                {
                    "definition_sha256": digest,
                    "failed": True,
                    "certified": False,
                    "used": False,
                    "prospective_observations": 0,
                    "superseded_before_use": True,
                }
                for digest in FAILED_ARCHITECTURE_LINEAGE
            ],
            "failed_calendar_lineage": list(FAILED_CALENDAR_LINEAGE),
            "preserved_hashes": {
                "certified_prospective_v1": "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7",
                "failed_prospective_v2": "488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d",
            },
            "preserved_science": {
                "source_urls_profiles_tls_redirects_parsers_coverage_early_closes": "UNCHANGED",
                "pit_common_session_etf_formulas_revision_semantics": "UNCHANGED",
                "stage_b_metrics_risk_stops_thresholds": "UNCHANGED",
            },
            "safety": {
                "prospective_observations": 0,
                "real_stage_b_evaluation": False,
                "collection_authorized": False,
                "calendar_certified": False,
                "calendar_implementation": "BLOCKED_PENDING_REVIEW_PASS",
                "postp1_001v2r1": "BLOCKED",
                "postp1_003r3": "BLOCKED",
                "postp1_004": "BLOCKED",
                "btc019": "UNTOUCHED",
                "epic_t": "UNCHANGED",
            },
        }
    )


_CHILD_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("trusted_process_boundary_reference.json", "trusted_process_boundary_reference"),
    ("store_root_grammar.json", "store_root_grammar"),
    ("store_binding_discipline.json", "store_binding_discipline"),
    ("permitted_direct_store_use.json", "permitted_direct_store_use"),
    ("forbidden_capability_escape_rules.json", "forbidden_capability_escape_rules"),
    ("nested_owner_prohibition.json", "nested_owner_prohibition"),
    ("replay_owner_graph_rule.json", "replay_owner_graph_rule"),
    ("direct_body_dependency_rule.json", "direct_body_dependency_rule"),
    ("proof_order_and_completeness_definition.json", "proof_order_and_completeness_definition"),
    ("science_lineage_and_safety.json", "science_lineage_and_safety"),
)


def _children(
    child_artifacts: Sequence[tuple[str, str]] | None = None,
) -> dict[str, dict[str, Any]]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    return {
        filename.removesuffix(".json"): globals()[builder]()
        for filename, builder in registry
    }


def store_capability_normal_form_definition(
    child_artifacts: Sequence[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    source = CALENDAR_SOURCE.read_text(encoding="utf-8")
    verify_replay_owner_census(source)
    children = _children(child_artifacts)
    return _definition(
        {
            "decision_version": DECISION_VERSION,
            "program_ticket": PROGRAM_TICKET,
            "workstream": "EPIC X — PROSPECTIVE INTEGRATION EVIDENCE",
            "status": STATUS,
            "final_classification": FINAL_CLASSIFICATION,
            "proof_strategy": "DIRECT_IMMUTABLE_STORE_PARAMETER_NORMAL_FORM",
            "pre_data": True,
            "required_review": REQUIRED_REVIEW,
            "failed_parent_sha256": FAILED_PARENT_SHA256,
            "certified_dependency_sha256": CERTIFIED_DEPENDENCY_SHA256,
            "material_child_count": len(children),
            "material_child_enumeration": "MECHANICALLY_ENUMERATED_FROM_ONE_REGISTRY",
            "child_definition_sha256": {
                name: child["definition_sha256"] for name, child in children.items()
            },
            "central_decisions": {
                "ordinary_explicitly_annotated_immutable_roots_only": True,
                "store_aliases_permitted": False,
                "store_variadics_permitted": False,
                "starred_store_forwarding_permitted": False,
                "nested_annotated_owner_can_be_hidden_by_rootless_outer": False,
                "root_rebinding_or_unbinding_permitted": False,
                "models_arbitrary_python_dataflow": False,
                "calendar_science_changed": False,
            },
            "authorization": {
                "independent_final_proof_architecture_xhigh_review_may_begin": True,
                "calendar_implementation_may_begin": False,
                "postp1_001v2r1_may_begin": False,
                "prospective_collection_may_begin": False,
            },
        }
    )


def verify_definition(persisted: Mapping[str, Any]) -> None:
    if dict(persisted) != store_capability_normal_form_definition():
        raise NormalFormError("persisted corrected store-capability normal form does not reproduce")
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    owners = "\n".join(f"- `{owner}`" for owner in FROZEN_REPLAY_OWNERS)
    return f"""# {DECISION_VERSION} — corrected candidate

- Ticket: `{PROGRAM_TICKET}`
- Decision hash: `{decision['definition_sha256']}`
- Failed parent: `{FAILED_PARENT_SHA256}`
- Status: `{STATUS}`
- Classification: `{FINAL_CLASSIFICATION}`
- Material children: {decision['material_child_count']}

## Direct immutable parameter normal form

The only scientific store root is an ordinary function parameter explicitly
annotated `CalendarEvidenceStore`. It has one binding: its parameter binding.
Aliases, annotated store variadics, local construction, nested annotated owners,
rebindings, deletion, and starred forwarding are forbidden. No naming heuristic,
reaching-definition analysis, SSA construction, generic capability propagation,
or arbitrary Python dataflow proof is used.

An immutable root may only receive a direct `put`, `get`, `records`, or
`envelopes` call, or be passed as an ordinary positional or named keyword
argument to one of the exact frozen replay owners. Every other root occurrence
and every later same-scope binding event fails closed.

## Frozen replay owners

{owners}

The production census is exactly eleven. Binding and use audits precede graph
extraction; cycles are forbidden and every owner path must terminate at a
documented API. Current production is not certified: the known
`common_etf_session_status` generator-expression capture remains refused and is
reserved for the later calendar implementation ticket after review PASS.

## Preserved authority and safety

Failed parent `{FAILED_PARENT_SHA256}` remains immutable, non-certified, unused,
and at zero observations. Trusted persistence `{CERTIFIED_DEPENDENCY_SHA256}` is
closed and unchanged. The trusted-process boundary, direct dependency-body rule,
startup identity checks, calendar science, failed calendar lineage, BTC-019 and
Epic T are unchanged.

No observation was collected and no real Stage-B evaluation ran. Calendar
implementation, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and collection remain
blocked. This candidate authorizes only `{REQUIRED_REVIEW}`.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Sequence[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    decision = store_capability_normal_form_definition(registry)
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
    verify_definition(decision)
    for filename, builder in _CHILD_ARTIFACTS:
        persisted = json.loads((output_dir / filename).read_text(encoding="ascii"))
        expected = globals()[builder]()
        if persisted != expected:
            raise NormalFormError(f"persisted {filename} does not reproduce")
        _verify_definition_digest(persisted)
        if decision["child_definition_sha256"].get(filename.removesuffix(".json")) != expected[
            "definition_sha256"
        ]:
            raise NormalFormError(f"corrected normal-form parent does not bind {filename}")
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise NormalFormError("persisted corrected normal-form report does not reproduce")
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
