"""Closed store-capability proof architecture for the ETF calendar authority.

This pre-data decision defines a finite supported Python syntax for scientific
``CalendarEvidenceStore`` use.  It does not modify the production calendar or
attempt to model arbitrary Python dataflow.
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping, Sequence

from btc_predictor.research import etf_calendar_authority_boundary_r2 as r2


DECISION_VERSION = "ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1"
PROGRAM_TICKET = "POSTP1-001V2A-PAD1"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_store_capability_normal_form_v1"
DEFINITION_FILENAME = "store_capability_normal_form_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
FINAL_CLASSIFICATION = (
    "ETF_CALENDAR_STORE_CAPABILITY_NORMAL_FORM_V1_READY_FOR_XHIGH_REVIEW"
)
CALENDAR_MODULE = r2.CALENDAR_MODULE
CALENDAR_SOURCE = r2.CALENDAR_SOURCE
CERTIFIED_DEPENDENCY_VERSION = r2.CERTIFIED_DEPENDENCY_VERSION
CERTIFIED_DEPENDENCY_SHA256 = r2.CERTIFIED_DEPENDENCY_SHA256
FAILED_ARCHITECTURE_LINEAGE = (
    r2.FAILED_ARCHITECTURE_SHA256,
    r2.FAILED_R1_ARCHITECTURE_SHA256,
    "dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e",
)
FAILED_CALENDAR_LINEAGE = r2.FAILED_CALENDAR_LINEAGE
FROZEN_REPLAY_OWNERS = r2.FROZEN_REPLAY_OWNERS
REQUIRED_DIRECT_BODIES = r2.REQUIRED_DIRECT_BODIES
STORE_APIS = r2.STORE_APIS

NormalFormError = r2.AuthorityBoundaryError
_definition = r2._definition
_verify_definition_digest = r2._verify_definition_digest
_annotation_names_calendar_store = r2._annotation_names_calendar_store
_top_level_functions = r2._top_level_functions


UseKind = Literal[
    "PERMITTED_DIRECT_STORE_API_CALL",
    "PERMITTED_ENUMERATED_OWNER_FORWARD",
    "PERMITTED_TRANSPARENT_ALIAS",
    "PERMITTED_VARIADIC_DERIVATION",
    "FORBIDDEN_STORE_ATTRIBUTE_EXTRACTION",
    "FORBIDDEN_UNKNOWN_FORWARD",
    "FORBIDDEN_CONTAINER_ESCAPE",
    "FORBIDDEN_RETURN_OR_YIELD",
    "FORBIDDEN_OBJECT_OR_SUBSCRIPT_STORAGE",
    "FORBIDDEN_NESTED_SCOPE_CAPTURE",
    "FORBIDDEN_DYNAMIC_ACCESS",
    "FORBIDDEN_OTHER_STORE_USE",
]


@dataclass(frozen=True, order=True)
class StoreUse:
    """One stable classification of one store-bearing expression use."""

    owner: str
    lineno: int
    col_offset: int
    kind: UseKind
    detail: str


@dataclass(frozen=True)
class StoreGrammar:
    """Mechanically derived names and frozen variadic boundary containers."""

    references: frozenset[str]
    vararg_containers: frozenset[str]
    kwarg_containers: frozenset[str]

    def is_reference(self, expression: ast.AST) -> bool:
        return isinstance(expression, ast.Name) and expression.id in self.references

    def is_variadic_element(self, expression: ast.AST) -> bool:
        return (
            isinstance(expression, ast.Subscript)
            and isinstance(expression.value, ast.Name)
            and expression.value.id
            in (self.vararg_containers | self.kwarg_containers)
        )

    def is_store(self, expression: ast.AST) -> bool:
        return self.is_reference(expression) or self.is_variadic_element(expression)


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


def _same_scope_nodes(
    owner: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[ast.AST, ...]:
    """Walk one function body without entering nested callable scopes."""

    nodes: list[ast.AST] = []

    class Visitor(ast.NodeVisitor):
        def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
            if node is owner:
                for statement in node.body:
                    self.visit(statement)
            else:
                nodes.append(node)

        visit_AsyncFunctionDef = visit_FunctionDef

        def visit_Lambda(self, node: ast.Lambda) -> None:
            nodes.append(node)

        def visit_ClassDef(self, node: ast.ClassDef) -> None:
            nodes.append(node)

        def generic_visit(self, node: ast.AST) -> None:
            nodes.append(node)
            super().generic_visit(node)

    Visitor().visit(owner)
    return tuple(nodes)


def _simple_alias_target(node: ast.AST) -> ast.Name | None:
    if isinstance(node, ast.Assign) and len(node.targets) == 1:
        return node.targets[0] if isinstance(node.targets[0], ast.Name) else None
    if isinstance(node, ast.AnnAssign):
        return node.target if isinstance(node.target, ast.Name) else None
    return None


def _assignment_value(node: ast.AST) -> ast.expr | None:
    if isinstance(node, ast.Assign):
        return node.value
    if isinstance(node, ast.AnnAssign):
        return node.value
    return None


def _variadic_iteration(
    expression: ast.AST, varargs: set[str], kwargs: set[str]
) -> bool:
    if isinstance(expression, ast.Name):
        return expression.id in varargs
    return (
        isinstance(expression, ast.Call)
        and isinstance(expression.func, ast.Attribute)
        and expression.func.attr == "values"
        and isinstance(expression.func.value, ast.Name)
        and expression.func.value.id in kwargs
        and not expression.args
        and not expression.keywords
    )


def derive_store_grammar(
    owner: ast.FunctionDef | ast.AsyncFunctionDef,
) -> StoreGrammar:
    """Derive only roots and aliases admitted by the closed grammar."""

    ordinary, vararg, kwarg = _parameters(owner)
    references = {
        parameter.arg
        for parameter in ordinary
        if _annotation_names_calendar_store(parameter.annotation)
    }
    varargs = {
        parameter.arg
        for parameter in (vararg,)
        if parameter is not None
        and _annotation_names_calendar_store(parameter.annotation)
    }
    kwargs = {
        parameter.arg
        for parameter in (kwarg,)
        if parameter is not None
        and _annotation_names_calendar_store(parameter.annotation)
    }
    nodes = _same_scope_nodes(owner)
    changed = True
    while changed:
        changed = False
        grammar = StoreGrammar(
            frozenset(references), frozenset(varargs), frozenset(kwargs)
        )
        for node in nodes:
            target = _simple_alias_target(node)
            value = _assignment_value(node)
            if target is not None and value is not None and grammar.is_store(value):
                if target.id not in references:
                    references.add(target.id)
                    changed = True
            if isinstance(node, (ast.For, ast.AsyncFor)) and isinstance(
                node.target, ast.Name
            ):
                if _variadic_iteration(node.iter, varargs, kwargs):
                    if node.target.id not in references:
                        references.add(node.target.id)
                        changed = True
    return StoreGrammar(
        frozenset(references), frozenset(varargs), frozenset(kwargs)
    )


def _parent_map(root: ast.AST) -> dict[ast.AST, ast.AST]:
    return {child: parent for parent in ast.walk(root) for child in ast.iter_child_nodes(parent)}


def _nested_scope_between(
    expression: ast.AST,
    owner: ast.FunctionDef | ast.AsyncFunctionDef,
    parents: Mapping[ast.AST, ast.AST],
) -> bool:
    current = parents.get(expression)
    nested = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef)
    closures = (ast.GeneratorExp, ast.ListComp, ast.SetComp, ast.DictComp)
    while current is not None and current is not owner:
        if isinstance(current, nested + closures):
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


def _classify_store_use(
    expression: ast.expr,
    owner: ast.FunctionDef | ast.AsyncFunctionDef,
    grammar: StoreGrammar,
    parents: Mapping[ast.AST, ast.AST],
    frozen_owners: frozenset[str],
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
        call, _ = call_argument
        called = _call_name(call)
        if called in {"getattr", "setattr", "vars"}:
            return "FORBIDDEN_DYNAMIC_ACCESS", called
        if called in frozen_owners:
            return "PERMITTED_ENUMERATED_OWNER_FORWARD", called
        return "FORBIDDEN_UNKNOWN_FORWARD", called or ast.unparse(call.func)

    if isinstance(parent, (ast.Assign, ast.AnnAssign)):
        value = _assignment_value(parent)
        if value is expression:
            target = _simple_alias_target(parent)
            if target is not None:
                return "PERMITTED_TRANSPARENT_ALIAS", target.id
            targets = parent.targets if isinstance(parent, ast.Assign) else [parent.target]
            if any(isinstance(target, (ast.Attribute, ast.Subscript)) for target in targets):
                return "FORBIDDEN_OBJECT_OR_SUBSCRIPT_STORAGE", "assignment_target"
            return "FORBIDDEN_OTHER_STORE_USE", "non_simple_assignment"

    if _inside_container(expression, owner, parents):
        return "FORBIDDEN_CONTAINER_ESCAPE", "new_container"
    if isinstance(parent, (ast.Return, ast.Yield, ast.YieldFrom)):
        return "FORBIDDEN_RETURN_OR_YIELD", type(parent).__name__
    return "FORBIDDEN_OTHER_STORE_USE", type(parent).__name__ if parent else "root"


def _classify_variadic_container_use(
    expression: ast.Name,
    owner: ast.FunctionDef | ast.AsyncFunctionDef,
    grammar: StoreGrammar,
    parents: Mapping[ast.AST, ast.AST],
    frozen_owners: frozenset[str],
) -> tuple[UseKind, str] | None:
    """Classify the container occurrence that derives/forwards frozen elements."""

    if expression.id not in grammar.vararg_containers | grammar.kwarg_containers:
        return None
    if _nested_scope_between(expression, owner, parents):
        return "FORBIDDEN_NESTED_SCOPE_CAPTURE", "nested_variadic_container"
    parent = parents.get(expression)
    if isinstance(parent, ast.Subscript) and parent.value is expression:
        return "PERMITTED_VARIADIC_DERIVATION", "indexed_element"
    if isinstance(parent, (ast.For, ast.AsyncFor)) and parent.iter is expression:
        return "PERMITTED_VARIADIC_DERIVATION", "iteration"
    if (
        isinstance(parent, ast.Attribute)
        and parent.value is expression
        and parent.attr == "values"
        and expression.id in grammar.kwarg_containers
    ):
        call = parents.get(parent)
        loop = parents.get(call) if isinstance(call, ast.Call) else None
        if (
            isinstance(call, ast.Call)
            and not call.args
            and not call.keywords
            and isinstance(loop, (ast.For, ast.AsyncFor))
            and loop.iter is call
        ):
            return "PERMITTED_VARIADIC_DERIVATION", "mapping_value_iteration"
    call_argument = _call_containing_argument(expression, parents)
    if call_argument is not None:
        call, argument = call_argument
        called = _call_name(call)
        starred_ok = (
            expression.id in grammar.vararg_containers
            and isinstance(argument, ast.Starred)
        ) or (
            expression.id in grammar.kwarg_containers
            and isinstance(argument, ast.keyword)
            and argument.arg is None
        )
        if starred_ok and called in frozen_owners:
            return "PERMITTED_ENUMERATED_OWNER_FORWARD", called
        return "FORBIDDEN_UNKNOWN_FORWARD", called or ast.unparse(call.func)
    return "FORBIDDEN_OTHER_STORE_USE", "variadic_container"


def classify_store_uses(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
) -> tuple[StoreUse, ...]:
    """Classify every recognized store-bearing occurrence into one category."""

    tree = ast.parse(source)
    functions = _top_level_functions(tree)
    frozen = frozenset(frozen_owners)
    uses: list[StoreUse] = []
    for owner_name, owner in functions.items():
        grammar = derive_store_grammar(owner)
        if not (
            grammar.references
            or grammar.vararg_containers
            or grammar.kwarg_containers
        ):
            continue
        parents = _parent_map(owner)
        for candidate in ast.walk(owner):
            if isinstance(candidate, (ast.FunctionDef, ast.AsyncFunctionDef)) and candidate is not owner:
                ordinary, vararg, kwarg = _parameters(candidate)
                parameters = (
                    *ordinary,
                    *((vararg,) if vararg else ()),
                    *((kwarg,) if kwarg else ()),
                )
                if any(
                    _annotation_names_calendar_store(parameter.annotation)
                    for parameter in parameters
                ):
                    uses.append(
                        StoreUse(
                            owner_name,
                            candidate.lineno,
                            candidate.col_offset,
                            "FORBIDDEN_NESTED_SCOPE_CAPTURE",
                            "nested_store_parameter",
                        )
                    )
            if isinstance(candidate, ast.Name) and isinstance(candidate.ctx, ast.Load):
                variadic = _classify_variadic_container_use(
                    candidate, owner, grammar, parents, frozen
                )
                if variadic is not None:
                    kind, detail = variadic
                elif grammar.is_reference(candidate):
                    kind, detail = _classify_store_use(
                        candidate, owner, grammar, parents, frozen
                    )
                else:
                    continue
            elif grammar.is_variadic_element(candidate):
                kind, detail = _classify_store_use(
                    candidate, owner, grammar, parents, frozen
                )
            else:
                continue
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
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
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
    discovered: list[str] = []
    for name, node in functions.items():
        ordinary, vararg, kwarg = _parameters(node)
        parameters = (*ordinary, *((vararg,) if vararg else ()), *((kwarg,) if kwarg else ()))
        if any(
            _annotation_names_calendar_store(parameter.annotation)
            for parameter in parameters
        ):
            discovered.append(name)
    return tuple(discovered)


def verify_replay_owner_census(
    source: str, frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS
) -> tuple[str, ...]:
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
    """Extract graph edges only after the closed normal-form audit passes."""

    uses = audit_store_capability_normal_form(source, frozen_owners)
    edges: list[OwnerEdge] = []
    for use in uses:
        if use.owner not in set(frozen_owners):
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
            raise NormalFormError(
                f"replay-owner cycle forbidden: {' -> '.join(path[start:])}"
            )
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
    functions = _top_level_functions(ast.parse(source))
    missing = set(frozen_owners) - set(functions)
    if missing:
        raise NormalFormError(f"stale replay-owner registry: {sorted(missing)!r}")
    edges = extract_owner_edges(source, frozen_owners)
    by_owner = {
        owner: [edge for edge in edges if edge.owner == owner]
        for owner in frozen_owners
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
            "replay owner path does not terminate at documented API: "
            f"{unresolved!r}"
        )
    return edges


def trusted_process_boundary_reference() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_TRUSTED_PROCESS_BOUNDARY_REFERENCE_V1",
            "production_python_process_trusted": True,
            "hostile_same_process_mutation_resistance_required": False,
            "project_owned_scientific_bypasses_in_scope": True,
            "arbitrary_caller_monkeypatch_debugger_private_mutation_in_scope": False,
            "hostile_same_process_resistance_if_later_required": "PROCESS_ISOLATION",
            "wrapper_metaclass_or_source_hash_substitutes_for_isolation": False,
            "failed_boundary_parent_sha256": FAILED_ARCHITECTURE_LINEAGE[-1],
        }
    )


def store_bearing_value_grammar() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_STORE_BEARING_VALUE_GRAMMAR_V1",
            "supported_roots_and_derivations": [
                "DIRECT_PARAMETERS_ANNOTATED_CalendarEvidenceStore",
                "SIMPLE_LOCAL_NAME_ALIAS_OF_STORE_BEARING_VALUE",
                "ELEMENT_OF_ANNOTATED_VARARG_CalendarEvidenceStore",
                "VALUE_OF_ANNOTATED_KWARG_CalendarEvidenceStore",
                "DIRECT_INDEXED_VARIADIC_EXTRACTION",
                "DIRECT_VARIADIC_ITERATION_TARGET",
                "SIMPLE_LOCAL_ALIAS_OF_EXTRACTED_OR_ITERATED_VALUE",
            ],
            "simple_alias_target": "LOCAL_ast.Name_ONLY",
            "generic_container_dataflow": "NOT_SUPPORTED",
            "other_derivations": "FORBIDDEN_UNLESS_EXPLICITLY_FROZEN",
        }
    )


def permitted_store_use_normal_form() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PERMITTED_STORE_USE_NORMAL_FORM_V1",
            "permitted_categories": [
                "PERMITTED_DIRECT_STORE_API_CALL",
                "PERMITTED_ENUMERATED_OWNER_FORWARD",
                "PERMITTED_TRANSPARENT_ALIAS",
                "PERMITTED_VARIADIC_DERIVATION",
            ],
            "direct_call_ast_shape": "ast.Call(func=ast.Attribute(value=STORE_BEARING_VALUE, attr=DOCUMENTED_API))",
            "documented_apis": list(STORE_APIS),
            "first_class_bound_method_capability_supported": False,
            "forward_target": "EXACT_FROZEN_REPLAY_OWNER_REGISTRY",
            "replay_owners": list(FROZEN_REPLAY_OWNERS),
        }
    )


def forbidden_capability_escape_rules() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_FORBIDDEN_CAPABILITY_ESCAPE_RULES_V1",
            "forbidden_categories": [
                "FORBIDDEN_STORE_ATTRIBUTE_EXTRACTION",
                "FORBIDDEN_UNKNOWN_FORWARD",
                "FORBIDDEN_CONTAINER_ESCAPE",
                "FORBIDDEN_RETURN_OR_YIELD",
                "FORBIDDEN_OBJECT_OR_SUBSCRIPT_STORAGE",
                "FORBIDDEN_NESTED_SCOPE_CAPTURE",
                "FORBIDDEN_DYNAMIC_ACCESS",
                "FORBIDDEN_OTHER_STORE_USE",
            ],
            "bare_documented_method_extraction_permitted": False,
            "bare_undocumented_method_extraction_permitted": False,
            "new_list_tuple_dict_set_packing_permitted": False,
            "closure_or_local_callable_capture_permitted": False,
            "dynamic_attribute_authority_permitted": False,
            "unsupported_use_may_be_masked_by_valid_route": False,
            "implementation_private_authoritative_state": ["_records", "_envelopes"],
            "repository_owned_access_outside_CalendarEvidenceStore_permitted": False,
        }
    )


def replay_owner_graph_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_OWNER_GRAPH_RULE_V1_PAD1",
            "normal_form_audit_must_pass_before_graph_extraction": True,
            "owner_count": len(FROZEN_REPLAY_OWNERS),
            "owners": list(FROZEN_REPLAY_OWNERS),
            "edge_kinds": [
                "DOCUMENTED_STORE_API_TERMINAL",
                "ENUMERATED_REPLAY_OWNER_EDGE",
            ],
            "cycles_permitted": False,
            "every_owner_path_terminates_at_documented_store_api": True,
            "owner_census_relation": "DISCOVERED_EQUALS_FROZEN_REGISTRY",
        }
    )


def variadic_store_reference_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_VARIADIC_STORE_REFERENCE_RULE_V1",
            "annotated_vararg_elements_supported": True,
            "annotated_kwarg_values_supported": True,
            "supported_operations": [
                "DIRECT_INDEXED_EXTRACTION",
                "SIMPLE_LOCAL_ALIAS",
                "DIRECT_ITERATION",
                "DIRECT_DOCUMENTED_API_CALL",
                "DIRECT_ENUMERATED_OWNER_FORWARD",
                "MECHANICALLY_RESOLVABLE_STARRED_ENUMERATED_OWNER_FORWARD",
            ],
            "resulting_elements_subject_to_same_normal_form": True,
            "bound_method_extraction_permitted": False,
            "container_escape_permitted": False,
        }
    )


def direct_body_dependency_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_DIRECT_BODY_DEPENDENCY_RULE_V1_PAD1",
            "required_direct_bodies": list(REQUIRED_DIRECT_BODIES),
            "exact_dependency_assertion": "assert_trusted_persistence_dependency",
            "proof": "DIRECT_EXECUTABLE_AST_CALL_IN_EACH_REQUIRED_BODY",
            "wrapper_installed_guards_permitted": False,
            "startup_self_check": [
                "CALENDAR_AUTHORITY_PARENT",
                "TRUSTED_PERSISTENCE_DEPENDENCY_CHILD",
                "EXACT_CERTIFIED_TRUSTED_PERSISTENCE_IDENTITY",
                "EXECUTABLE_STATIC_PRODUCTION_SURFACE_AUTHORITY",
            ],
            "startup_check_replaces_per_entrypoint_check": False,
        }
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PROOF_ORDER_AND_COMPLETENESS_V1",
            "proof_order": [
                "DISCOVER_STORE_BEARING_ROOTS",
                "DERIVE_ONLY_FROZEN_ALIASES_AND_VARIADIC_REFERENCES",
                "AUDIT_EVERY_STORE_BEARING_USE",
                "REJECT_CAPABILITY_ESCAPE_OR_UNSUPPORTED_USE",
                "RECONCILE_DISCOVERED_AND_FROZEN_OWNER_REGISTRY",
                "EXTRACT_DOCUMENTED_TERMINALS_AND_ENUMERATED_OWNER_EDGES",
                "REJECT_UNENUMERATED_FORWARDING",
                "REJECT_OWNER_CYCLES",
                "PROVE_EVERY_OWNER_PATH_TERMINATES_AT_DOCUMENTED_API",
                "VERIFY_DIRECT_DEPENDENCY_AND_PRODUCTION_SURFACE_CONSTRAINTS",
            ],
            "models_all_possible_python_programs": False,
            "models_every_certified_allowed_store_use": True,
            "rejects_every_non_certified_store_use": True,
            "completeness": "EVERY_STORE_BEARING_EXPRESSION_USE_CONFORMS_TO_FROZEN_SUPPORTED_GRAMMAR",
            "future_unsupported_syntax": "FAIL_UNTIL_EXPLICIT_REVIEWED_AUTHORITY_CHANGE",
            "automatic_analyzer_expansion_obligation": False,
            "decision_certifies_current_production_conformance": False,
            "known_future_implementation_delta": (
                "COMMON_ETF_SESSION_STATUS_GENERATOR_CAPTURE_OF_EVIDENCE_STORE_"
                "MUST_BE_REWRITTEN_IN_CERTIFIED_IMPLEMENTATION_WITHOUT_SEMANTIC_DRIFT"
            ),
        }
    )


def science_lineage_and_safety() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_NORMAL_FORM_SCIENCE_LINEAGE_AND_SAFETY_V1",
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
                "calendar_implementation": "BLOCKED_PENDING_PROOF_ARCHITECTURE_REVIEW_PASS",
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
    ("store_bearing_value_grammar.json", "store_bearing_value_grammar"),
    ("permitted_store_use_normal_form.json", "permitted_store_use_normal_form"),
    ("forbidden_capability_escape_rules.json", "forbidden_capability_escape_rules"),
    ("replay_owner_graph_rule.json", "replay_owner_graph_rule"),
    ("variadic_store_reference_rule.json", "variadic_store_reference_rule"),
    ("direct_body_dependency_rule.json", "direct_body_dependency_rule"),
    (
        "proof_order_and_completeness_definition.json",
        "proof_order_and_completeness_definition",
    ),
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
            "proof_strategy": "CLOSED_SUPPORTED_STORE_CAPABILITY_GRAMMAR",
            "pre_data": True,
            "required_review": "POSTP1-002V2A-PAD1_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW",
            "failed_parent_sha256": FAILED_ARCHITECTURE_LINEAGE[-1],
            "certified_dependency_sha256": CERTIFIED_DEPENDENCY_SHA256,
            "material_child_count": len(children),
            "material_child_enumeration": "MECHANICALLY_ENUMERATED_FROM_ONE_REGISTRY",
            "child_definition_sha256": {
                name: child["definition_sha256"] for name, child in children.items()
            },
            "central_decisions": {
                "closed_supported_scientific_store_use_grammar": True,
                "models_arbitrary_python_dataflow": False,
                "every_certified_allowed_store_use_modeled": True,
                "every_non_certified_store_use_rejected": True,
                "bare_bound_method_extraction_permitted": False,
                "unsupported_use_masked_by_valid_route_permitted": False,
                "future_new_syntax_automatically_supported": False,
                "trusted_process_boundary_changed": False,
                "calendar_science_changed": False,
            },
            "authorization": {
                "independent_proof_architecture_xhigh_review_may_begin": True,
                "calendar_implementation_may_begin": False,
                "postp1_001v2r1_may_begin": False,
                "prospective_collection_may_begin": False,
            },
        }
    )


def verify_definition(persisted: Mapping[str, Any]) -> None:
    if dict(persisted) != store_capability_normal_form_definition():
        raise NormalFormError("persisted store-capability normal form does not reproduce")
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    owners = "\n".join(f"- `{owner}`" for owner in FROZEN_REPLAY_OWNERS)
    return f"""# {DECISION_VERSION}

- Ticket: `{PROGRAM_TICKET}`
- Decision hash: `{decision['definition_sha256']}`
- Status: `{STATUS}`
- Classification: `{FINAL_CLASSIFICATION}`
- Material children: {decision['material_child_count']}

## Closed proof architecture

Scientific authority is proven by restricting repository-owned production code
to a closed, mechanically auditable store-capability grammar. Every recognized
store-bearing use must be a direct documented API call, direct enumerated-owner
forward, transparent local alias, or frozen variadic derivation. Every other
use is refused. Completeness does not mean understanding every Python program.

Bare extraction of documented or undocumented bound methods is forbidden.
Return/yield, arbitrary container packing, object/subscript storage, unknown
forwarding, nested capture, and dynamic access are forbidden. A future syntax
outside this normal form fails until an explicit reviewed authority change.
This architecture decision does not certify current production conformance;
the later implementation must rewrite the existing generator-expression store
capture in `common_etf_session_status` without changing calendar semantics.

## Proof order and replay graph

The capability normal-form audit runs before owner reconciliation or graph
extraction. The accepted graph retains these eleven frozen owners:

{owners}

Only direct documented store terminals and direct enumerated-owner edges enter
the graph. Cycles are forbidden and every owner path must terminate at `put`,
`get`, `records`, or `envelopes`.

## Preserved boundary and safety

The production Python process remains trusted; hostile same-process arbitrary
mutation remains out of scope, and process isolation remains required if that
threat enters scope. Project-owned scientific bypasses remain forbidden. The
failed architecture parent `{FAILED_ARCHITECTURE_LINEAGE[-1]}` and its two
predecessors remain failed, non-certified, unused, and at zero observations.
Trusted persistence `{CERTIFIED_DEPENDENCY_SHA256}` remains closed and
unchanged. Calendar science and failed calendar lineage are unchanged.

No observation was collected and no Stage-B evaluation ran. Calendar
implementation, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004, and collection remain
blocked. BTC-019 is untouched and Epic T is unchanged. This decision authorizes
only POSTP1-002V2A-PAD1 independent exact-hash xHigh proof-architecture review.
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
            raise NormalFormError(f"normal-form parent does not bind {filename}")
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise NormalFormError("persisted normal-form report does not reproduce")
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
