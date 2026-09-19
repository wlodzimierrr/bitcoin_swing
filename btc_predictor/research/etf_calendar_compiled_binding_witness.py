"""Compiled binding-witness proof architecture for the ETF calendar authority.

The narrow POSTP1-001V2A-PAD1-R1 source grammar is retained, but root
immutability is no longer claimed from a hand-maintained census of Python
binding AST nodes.  It is proven against the exact compiled code object of each
frozen replay owner under one frozen CPython compiler identity.  This module is
a pre-data decision builder and static audit specification: it never imports,
executes, collects or certifies the production calendar.
"""

from __future__ import annotations

import argparse
import ast
import dis
import hashlib
import importlib.util
import json
import opcode as _opcode
import sys
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Literal, Mapping, Sequence

from btc_predictor.research import etf_calendar_store_capability_normal_form as _base
from btc_predictor.research import etf_calendar_store_capability_normal_form_r1 as narrow


DECISION_VERSION = "ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1"
PROGRAM_TICKET = "POSTP1-001V2A-PAD2"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_compiled_binding_witness_v1"
DEFINITION_FILENAME = "etf_calendar_compiled_binding_witness_v1_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
FINAL_CLASSIFICATION = "ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1_READY_FOR_XHIGH_REVIEW"
PROOF_STRATEGY = "CLOSED_AST_USE_GRAMMAR_PLUS_FROZEN_CPYTHON_BINDING_WITNESS"
REQUIRED_REVIEW = (
    "POSTP1-002V2A-PAD2_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW"
)
FAILED_PARENT_SHA256 = (
    "7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b"
)

CALENDAR_MODULE = _base.CALENDAR_MODULE
CALENDAR_SOURCE = narrow.CALENDAR_SOURCE
CERTIFIED_DEPENDENCY_VERSION = narrow.CERTIFIED_DEPENDENCY_VERSION
CERTIFIED_DEPENDENCY_SHA256 = narrow.CERTIFIED_DEPENDENCY_SHA256
FAILED_ARCHITECTURE_LINEAGE = (*narrow.FAILED_ARCHITECTURE_LINEAGE, FAILED_PARENT_SHA256)
FAILED_CALENDAR_LINEAGE = narrow.FAILED_CALENDAR_LINEAGE
FROZEN_REPLAY_OWNERS = narrow.FROZEN_REPLAY_OWNERS
REQUIRED_DIRECT_BODIES = narrow.REQUIRED_DIRECT_BODIES
STORE_APIS = narrow.STORE_APIS

_definition = narrow._definition
_verify_definition_digest = narrow._verify_definition_digest
_annotated_ordinary_roots = narrow._annotated_ordinary_roots
_top_level_functions = narrow._top_level_functions


class CompiledBindingWitnessError(narrow.NormalFormError):
    """Raised when the frozen compiled binding witness refuses scientific authority."""


# ---------------------------------------------------------------------------
# Frozen proof interpreter
# ---------------------------------------------------------------------------

PROOF_INTERPRETER_IDENTITY: Mapping[str, Any] = {
    "implementation_name": "cpython",
    "version_major": 3,
    "version_minor": 12,
    "version_micro": 14,
    "version_releaselevel": "final",
    "version_serial": 0,
    "hexversion": 0x030C0EF0,
    "cache_tag": "cpython-312",
    "magic_number_hex": "cb0d0d0a",
}

COMPILE_MODE = "exec"
COMPILE_DONT_INHERIT = True
COMPILE_OPTIMIZE = 0
COMPILE_FLAGS = 0


def current_interpreter_identity() -> dict[str, Any]:
    """Read the live interpreter/compiler identity used as scientific proof material."""

    return {
        "implementation_name": sys.implementation.name,
        "version_major": sys.version_info.major,
        "version_minor": sys.version_info.minor,
        "version_micro": sys.version_info.micro,
        "version_releaselevel": sys.version_info.releaselevel,
        "version_serial": sys.version_info.serial,
        "hexversion": sys.hexversion,
        "cache_tag": sys.implementation.cache_tag,
        "magic_number_hex": importlib.util.MAGIC_NUMBER.hex(),
    }


def verify_proof_interpreter_identity(
    identity: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Refuse scientific authority on any runtime/compiler identity mismatch."""

    observed = dict(current_interpreter_identity() if identity is None else identity)
    if set(observed) != set(PROOF_INTERPRETER_IDENTITY):
        raise CompiledBindingWitnessError(
            "proof interpreter identity shape mismatch: REFUSE_SCIENTIFIC_AUTHORITY"
        )
    mismatched = sorted(
        field
        for field, expected in PROOF_INTERPRETER_IDENTITY.items()
        if observed[field] != expected
    )
    if mismatched:
        raise CompiledBindingWitnessError(
            "frozen proof interpreter mismatch on "
            f"{mismatched!r}: REFUSE_SCIENTIFIC_AUTHORITY"
        )
    return observed


# ---------------------------------------------------------------------------
# Frozen root-binding opcode policy for the exact proof interpreter
# ---------------------------------------------------------------------------

OpcodeClass = Literal[
    "ROOT_WRITE",
    "ROOT_DELETE",
    "ROOT_CLEAR",
    "FRAME_ENTRY_CELL_ESTABLISHMENT",
    "ROOT_READ",
    "ATTRIBUTE_NAMESPACE",
]

ROOT_BINDING_OPCODE_POLICY: Mapping[str, OpcodeClass] = {
    "STORE_FAST": "ROOT_WRITE",
    "STORE_FAST_MAYBE_NULL": "ROOT_WRITE",
    "STORE_DEREF": "ROOT_WRITE",
    "STORE_NAME": "ROOT_WRITE",
    "STORE_GLOBAL": "ROOT_WRITE",
    "DELETE_FAST": "ROOT_DELETE",
    "DELETE_DEREF": "ROOT_DELETE",
    "DELETE_NAME": "ROOT_DELETE",
    "DELETE_GLOBAL": "ROOT_DELETE",
    "LOAD_FAST_AND_CLEAR": "ROOT_CLEAR",
    "MAKE_CELL": "FRAME_ENTRY_CELL_ESTABLISHMENT",
    "LOAD_FAST": "ROOT_READ",
    "LOAD_FAST_CHECK": "ROOT_READ",
    "LOAD_CLOSURE": "ROOT_READ",
    "LOAD_DEREF": "ROOT_READ",
    "LOAD_FROM_DICT_OR_DEREF": "ROOT_READ",
    "LOAD_FROM_DICT_OR_GLOBALS": "ROOT_READ",
    "LOAD_NAME": "ROOT_READ",
    "LOAD_GLOBAL": "ROOT_READ",
    "IMPORT_NAME": "ROOT_READ",
    "IMPORT_FROM": "ROOT_READ",
    "STORE_ATTR": "ATTRIBUTE_NAMESPACE",
    "DELETE_ATTR": "ATTRIBUTE_NAMESPACE",
    "LOAD_ATTR": "ATTRIBUTE_NAMESPACE",
    "LOAD_METHOD": "ATTRIBUTE_NAMESPACE",
    "LOAD_SUPER_ATTR": "ATTRIBUTE_NAMESPACE",
    "LOAD_SUPER_METHOD": "ATTRIBUTE_NAMESPACE",
    "LOAD_ZERO_SUPER_ATTR": "ATTRIBUTE_NAMESPACE",
    "LOAD_ZERO_SUPER_METHOD": "ATTRIBUTE_NAMESPACE",
}

FROZEN_OPCODE_NUMBERS: Mapping[str, int] = {
    "DELETE_ATTR": 96,
    "DELETE_DEREF": 139,
    "DELETE_FAST": 126,
    "DELETE_GLOBAL": 98,
    "DELETE_NAME": 91,
    "IMPORT_FROM": 109,
    "IMPORT_NAME": 108,
    "LOAD_ATTR": 106,
    "LOAD_CLOSURE": 136,
    "LOAD_DEREF": 137,
    "LOAD_FAST": 124,
    "LOAD_FAST_AND_CLEAR": 143,
    "LOAD_FAST_CHECK": 127,
    "LOAD_FROM_DICT_OR_DEREF": 176,
    "LOAD_FROM_DICT_OR_GLOBALS": 175,
    "LOAD_GLOBAL": 116,
    "LOAD_METHOD": 262,
    "LOAD_NAME": 101,
    "LOAD_SUPER_ATTR": 141,
    "LOAD_SUPER_METHOD": 263,
    "LOAD_ZERO_SUPER_ATTR": 265,
    "LOAD_ZERO_SUPER_METHOD": 264,
    "MAKE_CELL": 135,
    "STORE_ATTR": 95,
    "STORE_DEREF": 138,
    "STORE_FAST": 125,
    "STORE_FAST_MAYBE_NULL": 266,
    "STORE_GLOBAL": 97,
    "STORE_NAME": 90,
}

#: Reserved, unnamed members of the frozen interpreter's name-referencing opcode
#: groups.  CPython 3.12.14 appends opcode 148 to ``hasfree`` without a matching
#: ``def_op``; it is the specialized ``STORE_ATTR_SLOT`` slot, is absent from
#: ``opcode.opmap`` and can never be emitted by ``compile``.  The witness still
#: refuses if that set moves.
FROZEN_UNNAMED_NAME_GROUP_OPCODES: tuple[int, ...] = (148,)

#: CPython 3.12.14 defines 64 specialized instructions.  None of them is in
#: ``opcode.opmap``, and ``dis.get_instructions(..., adaptive=False)`` reports the
#: deoptimized base instruction, so a specialized (quickened) opcode can never
#: hide a root write from this scan.  Both facts are checked mechanically.
FROZEN_SPECIALIZED_INSTRUCTION_COUNT = 64

ROOT_MUTATION_CLASSES: frozenset[str] = frozenset(
    {"ROOT_WRITE", "ROOT_DELETE", "ROOT_CLEAR"}
)
#: Every named opcode of the frozen interpreter's ``haslocal | hasfree | hasname``
#: groups is classified above, so an instruction whose opcode belongs to those
#: groups but whose name is absent from the policy is impossible after the
#: integrity check and is treated as a fail-closed refusal if it ever appears.
_NAME_REFERENCING_OPNAMES: frozenset[str] = frozenset(ROOT_BINDING_OPCODE_POLICY)
FRAME_ENTRY_TERMINATOR = "RESUME"


def _name_group_opcodes(
    opcode_module: Any,
) -> tuple[dict[str, int], tuple[int, ...]]:
    numbers = sorted(
        {
            *opcode_module.haslocal,
            *opcode_module.hasfree,
            *opcode_module.hasname,
        }
    )
    named: dict[str, int] = {}
    unnamed: list[int] = []
    for number in numbers:
        name = opcode_module.opname[number]
        if name.startswith("<"):
            unnamed.append(number)
        else:
            named[name] = number
    return named, tuple(unnamed)


def verify_opcode_policy_integrity(opcode_module: Any | None = None) -> dict[str, Any]:
    """Mechanically prove the frozen policy matches the exact interpreter table."""

    module = _opcode if opcode_module is None else opcode_module
    named, unnamed = _name_group_opcodes(module)
    emittable = set(getattr(module, "opmap", {}).values())
    leaked = sorted(number for number in unnamed if number in emittable)
    if leaked:
        raise CompiledBindingWitnessError(
            f"reserved unnamed name-group opcode became emittable {leaked!r}: "
            "REQUIRE_NEW_PROOF_ARCHITECTURE"
        )
    specialized = tuple(getattr(module, "_specialized_instructions", ()))
    if specialized:
        if len(specialized) != FROZEN_SPECIALIZED_INSTRUCTION_COUNT:
            raise CompiledBindingWitnessError(
                f"specialized instruction table moved ({len(specialized)} != "
                f"{FROZEN_SPECIALIZED_INSTRUCTION_COUNT}): REQUIRE_NEW_PROOF_ARCHITECTURE"
            )
        emitted = sorted(name for name in specialized if name in getattr(module, "opmap", {}))
        if emitted:
            raise CompiledBindingWitnessError(
                f"specialized instruction entered the compiler opmap {emitted!r}: "
                "REQUIRE_NEW_PROOF_ARCHITECTURE"
            )
    unexpected = sorted(set(named) - set(ROOT_BINDING_OPCODE_POLICY))
    missing = sorted(set(ROOT_BINDING_OPCODE_POLICY) - set(named))
    if unexpected or missing:
        raise CompiledBindingWitnessError(
            "frozen root-binding opcode policy is incompatible with the interpreter "
            f"(unclassified={unexpected!r}, absent={missing!r}): "
            "REQUIRE_NEW_PROOF_ARCHITECTURE"
        )
    moved = sorted(
        name for name, number in named.items() if FROZEN_OPCODE_NUMBERS[name] != number
    )
    if moved:
        raise CompiledBindingWitnessError(
            f"frozen opcode numbers moved for {moved!r}: REQUIRE_NEW_PROOF_ARCHITECTURE"
        )
    if unnamed != FROZEN_UNNAMED_NAME_GROUP_OPCODES:
        raise CompiledBindingWitnessError(
            "reserved unnamed name-group opcodes changed "
            f"({unnamed!r} != {FROZEN_UNNAMED_NAME_GROUP_OPCODES!r}): "
            "REQUIRE_NEW_PROOF_ARCHITECTURE"
        )
    return {
        "named": dict(sorted(named.items())),
        "unnamed": list(unnamed),
        "name_group_opcodes": frozenset({*named.values(), *unnamed}),
    }


def _opcodes_of_class(wanted: str) -> tuple[str, ...]:
    return tuple(
        sorted(name for name, kind in ROOT_BINDING_OPCODE_POLICY.items() if kind == wanted)
    )


# ---------------------------------------------------------------------------
# Compile without executing
# ---------------------------------------------------------------------------


def source_sha256(source: str) -> str:
    return hashlib.sha256(source.encode("utf-8")).hexdigest()


def compile_reviewed_source(source: str, filename: str) -> types.CodeType:
    """Compile the reviewed source under the frozen deterministic settings.

    No import, execution, HTTPS, signing, persistence or calendar collection is
    performed, and no cached ``.pyc`` artifact is read or trusted.
    """

    verify_proof_interpreter_identity()
    return compile(
        source,
        filename,
        COMPILE_MODE,
        COMPILE_FLAGS,
        dont_inherit=COMPILE_DONT_INHERIT,
        optimize=COMPILE_OPTIMIZE,
    )


def _nested_code_objects(code: types.CodeType) -> Iterator[types.CodeType]:
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            yield constant


def _all_code_objects(code: types.CodeType) -> Iterator[types.CodeType]:
    for child in _nested_code_objects(code):
        yield child
        yield from _all_code_objects(child)


# ---------------------------------------------------------------------------
# Exact owner code-object identification
# ---------------------------------------------------------------------------

OWNER_IDENTITY_COMPONENTS: tuple[str, ...] = (
    "TOP_LEVEL_OWNER_NAME",
    "CO_QUALNAME_EQUALS_TOP_LEVEL_OWNER_NAME",
    "CO_FIRSTLINENO_EQUALS_AST_DECORATOR_OR_DEF_DEFINITION_LINE",
    "ROOT_IS_A_DECLARED_PARAMETER_OF_THAT_CODE_OBJECT",
    "EXACTLY_ONE_MATCHING_CODE_OBJECT",
)


def owner_definition_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """The line CPython 3.12 records as ``co_firstlineno`` for a top-level owner.

    A decorated definition reports the first decorator's line, not the ``def``
    line, so the source-side identity component must agree with the compiler.
    """

    if node.decorator_list:
        return min(decorator.lineno for decorator in node.decorator_list)
    return node.lineno


@dataclass(frozen=True, order=True)
class OwnerCodeObject:
    """One mechanically identified top-level replay-owner code object."""

    owner: str
    qualname: str
    first_line: int
    parameters: tuple[str, ...]
    roots: tuple[str, ...]
    cell_roots: tuple[str, ...]


def _declared_parameters(code: types.CodeType) -> tuple[str, ...]:
    count = code.co_argcount + code.co_kwonlyargcount
    total = count + bool(code.co_flags & 0x04) + bool(code.co_flags & 0x08)
    return tuple(code.co_varnames[:total])


def _identify_owner_code_object(
    module_code: types.CodeType,
    owner: str,
    first_line: int,
    roots: Sequence[str],
) -> tuple[OwnerCodeObject, types.CodeType]:
    """Identify the exact top-level owner code object, never a same-named nested one."""

    qualified = [
        code for code in _all_code_objects(module_code) if code.co_qualname == owner
    ]
    if len(qualified) != 1:
        raise CompiledBindingWitnessError(
            f"owner code-object identity is not exact for {owner!r}: "
            f"{len(qualified)} code objects carry that qualified name"
        )
    code = qualified[0]
    if code.co_firstlineno != first_line:
        raise CompiledBindingWitnessError(
            f"owner code-object identity mismatch for {owner!r}: "
            f"co_firstlineno={code.co_firstlineno} ast_lineno={first_line}"
        )
    parameters = _declared_parameters(code)
    unknown = sorted(root for root in roots if root not in parameters)
    if unknown:
        raise CompiledBindingWitnessError(
            f"scientific root {unknown!r} is not a declared parameter of {owner!r}"
        )
    identity = OwnerCodeObject(
        owner=owner,
        qualname=code.co_qualname,
        first_line=code.co_firstlineno,
        parameters=parameters,
        roots=tuple(sorted(roots)),
        cell_roots=tuple(sorted(root for root in roots if root in code.co_cellvars)),
    )
    return identity, code


def identify_owner_code_object(
    module_code: types.CodeType,
    owner: str,
    first_line: int,
    roots: Sequence[str],
) -> OwnerCodeObject:
    """Public exact owner code-object identity for one frozen replay owner."""

    return _identify_owner_code_object(module_code, owner, first_line, roots)[0]


MODULE_SCOPE = "<module>"
MODULE_OWNER_NAME_BINDING_OPNAMES: tuple[str, ...] = (
    "STORE_NAME",
    "STORE_GLOBAL",
    "DELETE_NAME",
    "DELETE_GLOBAL",
)

#: Names that hand the reviewed module its own namespace as a first-class
#: mutable mapping, or that define/replace a binding dynamically.  Once any of
#: them is reachable, module-level name substitution is unbounded, so they are
#: refused anywhere in the reviewed module's code-object tree.
MODULE_NAMESPACE_REACH_NAMES: tuple[str, ...] = (
    "__import__",
    "compile",
    "delattr",
    "eval",
    "exec",
    "execfile",
    "globals",
    "locals",
    "setattr",
    "vars",
)

#: Attributes that replace what a already-bound function object executes.
FUNCTION_OBJECT_MUTATION_ATTRIBUTES: tuple[str, ...] = (
    "__closure__",
    "__code__",
    "__defaults__",
    "__dict__",
    "__func__",
    "__globals__",
    "__kwdefaults__",
    "__name__",
    "__qualname__",
    "__wrapped__",
)
_MODULE_NAMESPACE_LOAD_OPNAMES: frozenset[str] = frozenset(
    {"LOAD_NAME", "LOAD_GLOBAL", "LOAD_FROM_DICT_OR_GLOBALS", "LOAD_DEREF"}
)


def owner_name_identity_findings(
    module_code: types.CodeType,
    owners: Mapping[str, ast.FunctionDef | ast.AsyncFunctionDef],
) -> tuple[RootBindingFinding, ...]:
    """Prove the module-level owner NAME still denotes the reviewed definition.

    A decorator, a later rebinding, a write to the live function object or any
    reach into the module namespace as a mutable mapping would leave the
    reviewed code object intact while the callable actually invoked at replay
    time became something else.
    """

    findings: list[RootBindingFinding] = []
    for name, node in sorted(owners.items()):
        if node.decorator_list:
            findings.append(
                RootBindingFinding(
                    name,
                    MODULE_SCOPE,
                    name,
                    owner_definition_line(node),
                    "MAKE_FUNCTION",
                    "MODULE_OWNER_DECORATED",
                )
            )
    bindings: dict[str, int] = {name: 0 for name in owners}
    for instruction in _instructions(module_code):
        if instruction.opname == "STORE_NAME" and instruction.argval in bindings:
            bindings[str(instruction.argval)] += 1
    for name, count in sorted(bindings.items()):
        if count != 1:
            findings.append(
                RootBindingFinding(
                    name,
                    MODULE_SCOPE,
                    name,
                    count,
                    "STORE_NAME",
                    "MODULE_OWNER_NAME_NOT_UNIQUELY_BOUND",
                )
            )
    for scope in (module_code, *_all_code_objects(module_code)):
        for instruction in _instructions(scope):
            argval = instruction.argval
            if (
                instruction.opname in {"STORE_GLOBAL", "DELETE_GLOBAL", "DELETE_NAME"}
                and argval in bindings
            ):
                findings.append(
                    RootBindingFinding(
                        str(argval),
                        f"{MODULE_SCOPE}:{scope.co_qualname}",
                        str(argval),
                        instruction.offset,
                        instruction.opname,
                        "MODULE_OWNER_NAME_REBOUND",
                    )
                )
            elif instruction.opname in {"STORE_ATTR", "DELETE_ATTR"}:
                if argval in bindings:
                    findings.append(
                        RootBindingFinding(
                            str(argval),
                            f"{MODULE_SCOPE}:{scope.co_qualname}",
                            str(argval),
                            instruction.offset,
                            instruction.opname,
                            "MODULE_OWNER_NAME_REBOUND",
                        )
                    )
                elif argval in FUNCTION_OBJECT_MUTATION_ATTRIBUTES:
                    findings.append(
                        RootBindingFinding(
                            MODULE_SCOPE,
                            f"{MODULE_SCOPE}:{scope.co_qualname}",
                            str(argval),
                            instruction.offset,
                            instruction.opname,
                            "MODULE_FUNCTION_OBJECT_MUTATION",
                        )
                    )
            elif (
                instruction.opname in _MODULE_NAMESPACE_LOAD_OPNAMES
                and argval in MODULE_NAMESPACE_REACH_NAMES
            ) or (
                instruction.opname in {"IMPORT_NAME", "IMPORT_FROM"}
                and str(argval).split(".")[0] in MODULE_NAMESPACE_REACH_NAMES
            ):
                findings.append(
                    RootBindingFinding(
                        MODULE_SCOPE,
                        f"{MODULE_SCOPE}:{scope.co_qualname}",
                        str(argval),
                        instruction.offset,
                        instruction.opname,
                        "MODULE_NAMESPACE_REACH",
                    )
                )
    return tuple(sorted(set(findings)))


# ---------------------------------------------------------------------------
# Root immutability witness
# ---------------------------------------------------------------------------

FindingKind = Literal[
    "OWNER_SCOPE_ROOT_WRITE",
    "OWNER_SCOPE_ROOT_DELETE",
    "OWNER_SCOPE_ROOT_CLEAR",
    "OWNER_SCOPE_LATE_FRAME_CELL",
    "OWNER_ROOT_IS_CELL_VARIABLE",
    "OWNER_CELL_ROOT_WRITE",
    "OWNER_CELL_ROOT_DELETE",
    "UNCLASSIFIED_ROOT_BINDING_INSTRUCTION",
    "MODULE_OWNER_DECORATED",
    "MODULE_OWNER_NAME_NOT_UNIQUELY_BOUND",
    "MODULE_OWNER_NAME_REBOUND",
    "MODULE_FUNCTION_OBJECT_MUTATION",
    "MODULE_NAMESPACE_REACH",
]

MODULE_IDENTITY_KINDS: frozenset[str] = frozenset(
    {
        "MODULE_OWNER_DECORATED",
        "MODULE_OWNER_NAME_NOT_UNIQUELY_BOUND",
        "MODULE_OWNER_NAME_REBOUND",
        "MODULE_FUNCTION_OBJECT_MUTATION",
        "MODULE_NAMESPACE_REACH",
    }
)

_OWNER_SCOPE_KIND: Mapping[str, FindingKind] = {
    "ROOT_WRITE": "OWNER_SCOPE_ROOT_WRITE",
    "ROOT_DELETE": "OWNER_SCOPE_ROOT_DELETE",
    "ROOT_CLEAR": "OWNER_SCOPE_ROOT_CLEAR",
}
#: Only ``STORE_DEREF``/``DELETE_DEREF`` can write a free variable's cell.  A
#: class body nested in the owner keeps the root in ``co_freevars`` while binding
#: its own ``co_names`` entry of the same name through ``STORE_NAME``, which is a
#: different namespace and is never an owner-root write.
OWNER_CELL_MUTATION_OPNAMES: Mapping[str, FindingKind] = {
    "STORE_DEREF": "OWNER_CELL_ROOT_WRITE",
    "DELETE_DEREF": "OWNER_CELL_ROOT_DELETE",
}


@dataclass(frozen=True, order=True)
class RootBindingFinding:
    """One compiled instruction that writes, clears or deletes a scientific root."""

    owner: str
    scope: str
    root: str
    offset: int
    opname: str
    kind: FindingKind


def _instructions(code: types.CodeType) -> tuple[dis.Instruction, ...]:
    return tuple(dis.get_instructions(code, adaptive=False))


def _frame_entry_boundary(instructions: Sequence[dis.Instruction]) -> int:
    for index, instruction in enumerate(instructions):
        if instruction.opname == FRAME_ENTRY_TERMINATOR:
            return index
    return 0


def _scan_owner_scope(
    owner: str,
    code: types.CodeType,
    roots: Sequence[str],
    name_group_opcodes: frozenset[int],
) -> tuple[RootBindingFinding, ...]:
    instructions = _instructions(code)
    boundary = _frame_entry_boundary(instructions)
    findings: list[RootBindingFinding] = []
    for root in sorted(roots):
        if root in code.co_cellvars:
            findings.append(
                RootBindingFinding(
                    owner,
                    "OWNER_CODE_OBJECT",
                    root,
                    0,
                    "MAKE_CELL",
                    "OWNER_ROOT_IS_CELL_VARIABLE",
                )
            )
    for index, instruction in enumerate(instructions):
        if instruction.argval not in roots:
            continue
        policy = ROOT_BINDING_OPCODE_POLICY.get(instruction.opname)
        if policy is None:
            if instruction.opcode in name_group_opcodes:
                findings.append(
                    RootBindingFinding(
                        owner,
                        "OWNER_CODE_OBJECT",
                        str(instruction.argval),
                        instruction.offset,
                        instruction.opname,
                        "UNCLASSIFIED_ROOT_BINDING_INSTRUCTION",
                    )
                )
            continue
        if policy in ROOT_MUTATION_CLASSES:
            findings.append(
                RootBindingFinding(
                    owner,
                    "OWNER_CODE_OBJECT",
                    str(instruction.argval),
                    instruction.offset,
                    instruction.opname,
                    _OWNER_SCOPE_KIND[policy],
                )
            )
        elif policy == "FRAME_ENTRY_CELL_ESTABLISHMENT" and index >= boundary:
            findings.append(
                RootBindingFinding(
                    owner,
                    "OWNER_CODE_OBJECT",
                    str(instruction.argval),
                    instruction.offset,
                    instruction.opname,
                    "OWNER_SCOPE_LATE_FRAME_CELL",
                )
            )
    return tuple(findings)


def _scan_owner_cell_closure(
    owner: str, code: types.CodeType, roots: Sequence[str]
) -> tuple[RootBindingFinding, ...]:
    """Secondary witness over the owner's own cell, if the root ever becomes one.

    ``co_freevars`` is disjoint from ``co_varnames`` and ``co_cellvars``, so a
    nested scope that rebinds the name as its own local or cell terminates the
    chain and its writes are not owner-root writes.  A captured *parameter*
    appears in both ``co_varnames`` and ``co_cellvars`` of the owner, which the
    primary structural rule already refuses, so every finding produced here
    belongs to an owner that is refused anyway; this scan is defence in depth
    and is deliberately conservative within such an owner.
    """

    findings: list[RootBindingFinding] = []

    def descend(parent: types.CodeType) -> None:
        for child in _nested_code_objects(parent):
            visible = tuple(root for root in roots if root in child.co_freevars)
            if not visible:
                continue
            for instruction in _instructions(child):
                if instruction.argval not in visible:
                    continue
                kind = OWNER_CELL_MUTATION_OPNAMES.get(instruction.opname)
                if kind is None:
                    continue
                findings.append(
                    RootBindingFinding(
                        owner,
                        f"OWNER_CELL_CLOSURE:{child.co_qualname}",
                        str(instruction.argval),
                        instruction.offset,
                        instruction.opname,
                        kind,
                    )
                )
            descend(child)

    descend(code)
    return tuple(findings)


@dataclass(frozen=True)
class CompiledBindingWitness:
    """One compiled root-immutability witness bound to one exact reviewed source."""

    decision_version: str
    source_sha256: str
    filename: str
    interpreter_identity: tuple[tuple[str, Any], ...]
    owners: tuple[OwnerCodeObject, ...]
    findings: tuple[RootBindingFinding, ...]

    @property
    def root_immutable(self) -> bool:
        return not self.findings

    @property
    def root_rebinding_findings(self) -> tuple[RootBindingFinding, ...]:
        """Findings that are an actual root write, clear or delete."""

        return tuple(
            row
            for row in self.findings
            if row.kind != "OWNER_ROOT_IS_CELL_VARIABLE"
            and row.kind not in MODULE_IDENTITY_KINDS
        )

    @property
    def module_identity_findings(self) -> tuple[RootBindingFinding, ...]:
        """Findings about the module-level owner name and namespace reach."""

        return tuple(row for row in self.findings if row.kind in MODULE_IDENTITY_KINDS)

    @property
    def root_capture_findings(self) -> tuple[RootBindingFinding, ...]:
        """Findings that expose a root as a first-class closure cell."""

        return tuple(
            row for row in self.findings if row.kind == "OWNER_ROOT_IS_CELL_VARIABLE"
        )


def _discovered_annotated_owners(tree: ast.Module) -> tuple[str, ...]:
    return tuple(
        name
        for name, node in _top_level_functions(tree).items()
        if _annotated_ordinary_roots(node)
    )


def compiled_binding_witness(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
    filename: str | None = None,
) -> CompiledBindingWitness:
    """Prove that no frozen owner rebinds, clears or deletes its scientific root."""

    identity = verify_proof_interpreter_identity()
    opcode_table = verify_opcode_policy_integrity()
    tree = ast.parse(source)
    top_level = _top_level_functions(tree)
    audited = sorted({*frozen_owners, *_discovered_annotated_owners(tree)})
    missing = sorted(name for name in frozen_owners if name not in top_level)
    if missing:
        raise CompiledBindingWitnessError(
            f"frozen replay owner is absent from the reviewed source: {missing!r}"
        )
    module_code = compile_reviewed_source(
        source, CALENDAR_MODULE if filename is None else filename
    )
    name_group_opcodes = opcode_table["name_group_opcodes"]
    owners: list[OwnerCodeObject] = []
    findings: list[RootBindingFinding] = list(
        owner_name_identity_findings(
            module_code, {name: top_level[name] for name in audited}
        )
    )
    for name in audited:
        node = top_level[name]
        roots = tuple(sorted(_annotated_ordinary_roots(node)))
        if not roots:
            raise CompiledBindingWitnessError(
                f"frozen replay owner {name!r} declares no explicitly annotated "
                "CalendarEvidenceStore root"
            )
        identified, code = _identify_owner_code_object(
            module_code, name, owner_definition_line(node), roots
        )
        owners.append(identified)
        findings.extend(_scan_owner_scope(name, code, roots, name_group_opcodes))
        findings.extend(_scan_owner_cell_closure(name, code, roots))
    return CompiledBindingWitness(
        decision_version=DECISION_VERSION,
        source_sha256=source_sha256(source),
        filename=CALENDAR_MODULE if filename is None else filename,
        interpreter_identity=tuple(sorted(identity.items())),
        owners=tuple(sorted(owners)),
        findings=tuple(sorted(set(findings))),
    )


def audit_compiled_binding_witness(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
    filename: str | None = None,
) -> CompiledBindingWitness:
    """Refuse before graph authority when any owner root is written or deleted."""

    witness = compiled_binding_witness(source, frozen_owners, filename)
    if witness.findings:
        rendered = ", ".join(
            f"{row.owner}:{row.scope}:{row.root}:{row.opname}:{row.kind}"
            for row in witness.findings
        )
        raise CompiledBindingWitnessError(f"compiled root binding forbidden: {rendered}")
    return witness


def verify_witness_binds_source(witness: CompiledBindingWitness, source: str) -> None:
    """Refuse a detached witness generated from a different source."""

    if witness.decision_version != DECISION_VERSION:
        raise CompiledBindingWitnessError("compiled witness decision version mismatch")
    if witness.source_sha256 != source_sha256(source):
        raise CompiledBindingWitnessError(
            "compiled binding witness does not certify this source: "
            f"witness={witness.source_sha256} source={source_sha256(source)}"
        )
    if dict(witness.interpreter_identity) != dict(PROOF_INTERPRETER_IDENTITY):
        raise CompiledBindingWitnessError(
            "compiled binding witness was not produced by the frozen proof interpreter"
        )


# ---------------------------------------------------------------------------
# Dynamic execution prohibition
# ---------------------------------------------------------------------------

FORBIDDEN_DYNAMIC_EXECUTION_NAMES: tuple[str, ...] = (
    "__import__",
    "compile",
    "delattr",
    "eval",
    "exec",
    "execfile",
    "getattr",
    "globals",
    "locals",
    "setattr",
    "vars",
)

#: Conservative production prohibition, not a completeness claim.  Reaching a
#: frame or a closure cell as a first-class object is the only project-owned way
#: left to mutate a scientific root without a root-binding instruction, so the
#: names and attributes that reach them are refused inside replay owners.
#: Arbitrary hostile reflection stays outside the trusted-process threat model.
FORBIDDEN_REFLECTIVE_AUTHORITY_NAMES: tuple[str, ...] = (
    "ctypes",
    "gc",
    "inspect",
    "sys",
)
FORBIDDEN_REFLECTIVE_AUTHORITY_ATTRIBUTES: tuple[str, ...] = (
    "__closure__",
    "__code__",
    "__defaults__",
    "__dict__",
    "__func__",
    "__globals__",
    "__kwdefaults__",
    "__wrapped__",
    "ag_frame",
    "cell_contents",
    "cr_frame",
    "f_back",
    "f_globals",
    "f_locals",
    "f_trace",
    "gi_frame",
)
_DYNAMIC_LOAD_OPNAMES: frozenset[str] = frozenset(
    {"LOAD_GLOBAL", "LOAD_NAME", "LOAD_FROM_DICT_OR_GLOBALS", "LOAD_DEREF"}
)
_IMPORT_OPNAMES: frozenset[str] = frozenset({"IMPORT_NAME", "IMPORT_FROM"})
_ATTRIBUTE_OPNAMES: frozenset[str] = frozenset(
    {
        "LOAD_ATTR",
        "LOAD_METHOD",
        "LOAD_SUPER_ATTR",
        "LOAD_SUPER_METHOD",
        "STORE_ATTR",
        "DELETE_ATTR",
    }
)


def audit_dynamic_execution_prohibition(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
    filename: str | None = None,
) -> tuple[str, ...]:
    """Forbid project-supported dynamic execution inside authoritative replay owners."""

    verify_proof_interpreter_identity()
    tree = ast.parse(source)
    top_level = _top_level_functions(tree)
    module_code = compile_reviewed_source(
        source, CALENDAR_MODULE if filename is None else filename
    )
    forbidden: set[str] = set()
    for name in frozen_owners:
        if name not in top_level:
            continue
        code = next(
            (child for child in _all_code_objects(module_code) if child.co_qualname == name),
            None,
        )
        if code is None:
            continue
        for scope in (code, *_all_code_objects(code)):
            for instruction in _instructions(scope):
                if instruction.opname in _DYNAMIC_LOAD_OPNAMES and instruction.argval in (
                    *FORBIDDEN_DYNAMIC_EXECUTION_NAMES,
                    *FORBIDDEN_REFLECTIVE_AUTHORITY_NAMES,
                ):
                    forbidden.add(f"{name}:{instruction.argval}")
                elif instruction.opname in _IMPORT_OPNAMES and str(
                    instruction.argval
                ).split(".")[0] in FORBIDDEN_REFLECTIVE_AUTHORITY_NAMES:
                    forbidden.add(f"{name}:{instruction.argval}")
                elif (
                    instruction.opname in _ATTRIBUTE_OPNAMES
                    and instruction.argval in FORBIDDEN_REFLECTIVE_AUTHORITY_ATTRIBUTES
                ):
                    forbidden.add(f"{name}:{instruction.argval}")
    if forbidden:
        raise CompiledBindingWitnessError(
            "dynamic code execution or reflective authority escape forbidden in "
            f"replay owners: {sorted(forbidden)!r}"
        )
    return (
        *FORBIDDEN_DYNAMIC_EXECUTION_NAMES,
        *FORBIDDEN_REFLECTIVE_AUTHORITY_NAMES,
        *FORBIDDEN_REFLECTIVE_AUTHORITY_ATTRIBUTES,
    )


# ---------------------------------------------------------------------------
# Layer reconciliation and frozen proof order
# ---------------------------------------------------------------------------

PROOF_ORDER: tuple[str, ...] = (
    "VERIFY_FROZEN_CPYTHON_COMPILER_IDENTITY",
    "COMPILE_REVIEWED_SOURCE_WITHOUT_EXECUTION",
    "IDENTIFY_EXACT_TOP_LEVEL_REPLAY_OWNER_CODE_OBJECTS",
    "DISCOVER_ORDINARY_EXPLICITLY_ANNOTATED_STORE_ROOTS",
    "RUN_COMPILED_BINDING_WITNESS_FOR_EVERY_ROOT",
    "REJECT_ANY_ROOT_WRITE_CLEAR_OR_DELETE",
    "RUN_CLOSED_AST_STORE_USE_GRAMMAR",
    "REJECT_NESTED_ANNOTATED_OWNERS_AND_CAPABILITY_ESCAPES",
    "RECONCILE_EXACT_ELEVEN_OWNER_CENSUS",
    "EXTRACT_DIRECT_API_AND_ENUMERATED_OWNER_EDGES",
    "REJECT_OWNER_CYCLES",
    "PROVE_EVERY_OWNER_PATH_TERMINATES_AT_DOCUMENTED_STORE_API",
    "VERIFY_DIRECT_DEPENDENCY_BODY_AND_STARTUP_CONTRACTS",
)


def ast_binding_diagnostics(
    source: str, frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS
) -> tuple[narrow.StoreUse, ...]:
    """Non-authoritative source diagnostics for human-readable binding reasons."""

    return tuple(
        use
        for use in narrow.classify_store_uses(source, frozen_owners)
        if use.kind == "FORBIDDEN_STORE_ROOT_REBIND_OR_UNBIND"
    )


def reconcile_binding_layers(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
    filename: str | None = None,
) -> dict[str, Any]:
    """Never choose the permissive result when the two layers disagree."""

    witness = compiled_binding_witness(source, frozen_owners, filename)
    diagnostics = ast_binding_diagnostics(source, frozen_owners)
    witnessed = {(row.owner, row.root) for row in witness.findings}
    diagnosed = {(use.owner, use.detail) for use in diagnostics}
    if witness.findings:
        raise CompiledBindingWitnessError(
            "compiled binding witness refuses regardless of the AST diagnostic layer: "
            f"compiled={sorted(witnessed)!r} ast_diagnostics={sorted(diagnosed)!r}"
        )
    return {
        "compiled_root_mutations": 0,
        "ast_binding_diagnostics": len(diagnostics),
        "authoritative_layer": "COMPILED_BINDING_WITNESS",
        "disagreement_resolution": "FAIL_CLOSED",
    }


def audit_compiled_binding_witness_architecture(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
    filename: str | None = None,
) -> dict[str, Any]:
    """Run the frozen proof order; no graph authority before the binding witness."""

    identity = verify_proof_interpreter_identity()
    opcode_table = verify_opcode_policy_integrity()
    witness = audit_compiled_binding_witness(source, frozen_owners, filename)
    verify_witness_binds_source(witness, source)
    audit_dynamic_execution_prohibition(source, frozen_owners, filename)
    reconciliation = reconcile_binding_layers(source, frozen_owners, filename)
    uses = narrow.audit_store_capability_normal_form(source, frozen_owners)
    census = narrow.verify_replay_owner_census(source, frozen_owners)
    edges = narrow.audit_replay_owner_graph(source, frozen_owners)
    return {
        "proof_order": list(PROOF_ORDER),
        "interpreter_identity": identity,
        "named_binding_opcodes": len(opcode_table["named"]),
        "source_sha256": witness.source_sha256,
        "owners": [row.owner for row in witness.owners],
        "census": list(census),
        "root_mutations": 0,
        "permitted_uses": len(uses),
        "edges": len(edges),
        "layer_reconciliation": reconciliation,
    }


# ---------------------------------------------------------------------------
# Material children
# ---------------------------------------------------------------------------


def trusted_process_boundary_reference() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_TRUSTED_PROCESS_BOUNDARY_REFERENCE_V1_PAD2",
            "production_python_process_trusted": True,
            "hostile_same_process_mutation_resistance_required": False,
            "project_owned_scientific_bypasses_in_scope": True,
            "arbitrary_hostile_in_process_manipulation_in_scope": False,
            "hostile_same_process_resistance_if_later_required": "PROCESS_ISOLATION",
            "wrapper_metaclass_or_source_hash_substitutes_for_isolation": False,
            "arbitrary_dynamic_python_mutation_proved": False,
            "failed_boundary_lineage": list(FAILED_ARCHITECTURE_LINEAGE),
        }
    )


def proof_interpreter_identity() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PROOF_INTERPRETER_IDENTITY_V1_PAD2",
            "frozen_identity": dict(PROOF_INTERPRETER_IDENTITY),
            "identity_fields": sorted(PROOF_INTERPRETER_IDENTITY),
            "compiler_identity_is_scientific_proof_material": True,
            "runtime_or_compiler_identity_mismatch": "REFUSE_SCIENTIFIC_AUTHORITY",
            "different_python_compiler_may_reuse_this_authority": False,
            "future_python_upgrade": "REQUIRES_EXPLICIT_REVIEW_AND_REFREEZE",
            "cached_pyc_is_scientific_authority": False,
            "compile_settings": {
                "mode": COMPILE_MODE,
                "flags": COMPILE_FLAGS,
                "dont_inherit": COMPILE_DONT_INHERIT,
                "optimize": COMPILE_OPTIMIZE,
                "executes_reviewed_source": False,
                "imports_reviewed_source": False,
                "performs_https_signing_persistence_or_collection": False,
            },
        }
    )


def store_root_and_direct_use_grammar() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_STORE_ROOT_AND_DIRECT_USE_GRAMMAR_V1_PAD2",
            "normal_form": "DIRECT_IMMUTABLE_STORE_PARAMETER_NORMAL_FORM",
            "supported_root": "ORDINARY_PARAMETER_EXPLICITLY_ANNOTATED_CalendarEvidenceStore",
            "ordinary_parameter_kinds": [
                "POSITIONAL_ONLY",
                "POSITIONAL_OR_KEYWORD",
                "KEYWORD_ONLY",
            ],
            "naming_heuristics_permitted": False,
            "transparent_aliases_permitted": False,
            "annotated_store_varargs_permitted": False,
            "annotated_store_kwargs_permitted": False,
            "starred_store_forwarding_permitted": False,
            "local_store_construction_permitted": False,
            "container_derived_stores_permitted": False,
            "nested_annotated_owners_permitted": False,
            "permitted_categories": [
                "PERMITTED_DIRECT_STORE_API_CALL",
                "PERMITTED_ENUMERATED_OWNER_FORWARD",
            ],
            "direct_call_ast_shape": (
                "ast.Call(func=ast.Attribute(value=EXACT_IMMUTABLE_ROOT, attr=DOCUMENTED_API))"
            ),
            "documented_apis": list(STORE_APIS),
            "forward_target": "EXACT_FROZEN_REPLAY_OWNER_REGISTRY",
            "ordinary_positional_forwarding": True,
            "ordinary_named_keyword_forwarding": True,
            "other_roots_or_derivations": "FAIL_UNTIL_EXPLICIT_REVIEWED_AUTHORITY_CHANGE",
        }
    )


def compiled_binding_witness_definition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_COMPILED_BINDING_WITNESS_DEFINITION_V1_PAD2",
            "proof_strategy": PROOF_STRATEGY,
            "proves": (
                "THE_FROZEN_ANNOTATED_STORE_ROOT_IS_NOT_REBOUND_CLEARED_OR_DELETED_BY_"
                "EXECUTABLE_CODE_IN_THE_OWNING_FUNCTION_COMPILED_SCOPE_UNDER_THE_FROZEN_"
                "CPYTHON_COMPILER"
            ),
            "does_not_prove_arbitrary_python_semantics": True,
            "hand_maintained_ast_binder_census_is_the_proof": False,
            "ast_binding_visitor_role": [
                "DIAGNOSTICS",
                "EARLY_FAILURE",
                "HUMAN_READABLE_REASON_CODES",
                "REGRESSION_LOCALIZATION",
            ],
            "missing_ast_diagnostic_can_accept_a_compiled_root_write": False,
            "root_target_rule": "INSTRUCTION_EFFECTIVE_TARGET_IDENTITY_EQUALS_ROOT_NAME",
            "root_write_opcodes": list(_opcodes_of_class("ROOT_WRITE")),
            "root_delete_opcodes": list(_opcodes_of_class("ROOT_DELETE")),
            "root_clear_opcodes": list(_opcodes_of_class("ROOT_CLEAR")),
            "frame_entry_cell_opcodes": list(
                _opcodes_of_class("FRAME_ENTRY_CELL_ESTABLISHMENT")
            ),
            "root_read_opcodes": list(_opcodes_of_class("ROOT_READ")),
            "attribute_namespace_opcodes": list(_opcodes_of_class("ATTRIBUTE_NAMESPACE")),
            "frozen_opcode_numbers": dict(sorted(FROZEN_OPCODE_NUMBERS.items())),
            "reserved_unnamed_name_group_opcodes": list(
                FROZEN_UNNAMED_NAME_GROUP_OPCODES
            ),
            "opcode_policy_integrity_checked_against_interpreter_table": True,
            "unexpected_or_unclassified_root_binding_opcode": (
                "REFUSE_REQUIRE_NEW_PROOF_ARCHITECTURE"
            ),
            "frame_entry_parameter_establishment_exemption": (
                "MAKE_CELL_ON_A_ROOT_IS_PERMITTED_ONLY_BEFORE_THE_FIRST_RESUME"
            ),
            "owner_scope_rule": (
                "NO_ROOT_WRITE_CLEAR_OR_DELETE_INSTRUCTION_IN_THE_OWNER_OWN_CODE_OBJECT"
            ),
            "root_may_be_a_cell_variable_of_the_owner": False,
            "structural_root_cell_prohibition": (
                "A_CONFORMING_ROOT_IS_AN_UNCAPTURED_FAST_LOCAL_SO_NO_FIRST_CLASS_CELL_"
                "OBJECT_FOR_THE_ROOT_EVER_EXISTS"
            ),
            "structural_root_cell_prohibition_rationale": (
                "A_CELL_IS_A_FIRST_CLASS_OBJECT_REACHABLE_THROUGH_A_CAPTURING_FUNCTION_"
                "__closure___SO_cell_contents_COULD_REBIND_THE_ROOT_WITHOUT_ANY_ROOT_"
                "BINDING_INSTRUCTION"
            ),
            "structural_rule_is_at_least_as_strict_as_the_source_nested_capture_prohibition": True,
            "structural_rule_may_refuse_sources_the_source_grammar_accepts": True,
            "structural_rule_over_refusal_is_fail_closed_and_deliberate": True,
            "known_structural_over_refusal_families": [
                "BARE_NONLOCAL_DECLARATION_NAMING_THE_ROOT",
                "PEP_695_LAZY_TYPE_ALIAS_OR_TYPE_PARAM_SCOPE_READING_THE_ROOT",
                "STATICALLY_DEAD_NESTED_SCOPE_THAT_STILL_CELLS_THE_ROOT",
            ],
            "owner_cell_closure_rule": (
                "NO_STORE_DEREF_OR_DELETE_DEREF_ON_THE_ROOT_IN_A_NESTED_CODE_OBJECT_THAT_"
                "HOLDS_THE_ROOT_AS_A_FREE_VARIABLE_OF_THE_OWNER_CELL"
            ),
            "owner_cell_closure_rule_is_defence_in_depth": True,
            "class_body_store_name_is_an_owner_root_write": False,
            "nested_body_local_assignment_is_an_outer_root_write": False,
            "recursively_treats_all_nested_writes_as_outer_writes": False,
            "module_level_owner_name_identity_rule": (
                "EXACTLY_ONE_MODULE_STORE_NAME_PER_OWNER_NO_DECORATOR_NO_LATER_REBIND_"
                "NO_FUNCTION_OBJECT_MUTATION_AND_NO_MODULE_NAMESPACE_REACH_ANYWHERE_IN_"
                "THE_REVIEWED_MODULE_CODE_OBJECT_TREE"
            ),
            "module_identity_finding_kinds": sorted(MODULE_IDENTITY_KINDS),
            "specialized_or_instrumented_opcode_may_hide_a_root_write": False,
            "instruction_scan_deoptimizes_specialized_instructions": True,
            "source_identity_binding": [
                "SOURCE_SHA256",
                "COMPILED_ARTIFACT",
                "OWNER_CODE_OBJECT_IDENTITY",
                "BINDING_WITNESS_RESULT",
            ],
            "detached_witness_may_certify_another_source": False,
            "ast_and_compiled_disagreement": "FAIL_CLOSED_NEVER_PERMISSIVE",
            "binding_witness_precedes_graph_authority": True,
        }
    )


def owner_code_object_identity_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_OWNER_CODE_OBJECT_IDENTITY_RULE_V1_PAD2",
            "identity_components": list(OWNER_IDENTITY_COMPONENTS),
            "co_name_alone_is_sufficient": False,
            "nested_function_with_the_same_simple_name_may_be_substituted": False,
            "ambiguous_or_absent_code_object": "REFUSE",
            "duplicate_or_conditional_module_level_definition": "REFUSE",
            "decorated_replay_owner_definition": "REFUSE",
            "module_level_owner_name_rebinding_or_deletion": "REFUSE",
            "module_namespace_reach_anywhere_in_the_module_tree": "REFUSE",
            "function_object_mutation_anywhere_in_the_module_tree": "REFUSE",
            "owner_name_module_binding_count": 1,
            "owner_discovery": "TOP_LEVEL_ORDINARY_EXPLICITLY_ANNOTATED_PARAMETERS_ONLY",
            "owners": list(FROZEN_REPLAY_OWNERS),
            "owner_count": len(FROZEN_REPLAY_OWNERS),
        }
    )


def dynamic_execution_prohibition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_DYNAMIC_EXECUTION_PROHIBITION_V1_PAD2",
            "forbidden_names_in_replay_owners": list(FORBIDDEN_DYNAMIC_EXECUTION_NAMES),
            "forbidden_reflective_names_in_replay_owners": list(
                FORBIDDEN_REFLECTIVE_AUTHORITY_NAMES
            ),
            "forbidden_reflective_attributes_in_replay_owners": list(
                FORBIDDEN_REFLECTIVE_AUTHORITY_ATTRIBUTES
            ),
            "forbidden_module_namespace_reach_names": list(MODULE_NAMESPACE_REACH_NAMES),
            "forbidden_function_object_mutation_attributes": list(
                FUNCTION_OBJECT_MUTATION_ATTRIBUTES
            ),
            "module_namespace_reach_scope": "WHOLE_REVIEWED_MODULE_CODE_OBJECT_TREE",
            "prohibition_is_a_conservative_production_rule_not_a_completeness_proof": True,
            "project_supported_dynamic_store_authority_synthesis": "FORBIDDEN",
            "arbitrary_hostile_same_process_mutation_in_threat_model": False,
            "out_of_scope": [
                "EXEC_OR_EVAL_INJECTED_BY_A_HOSTILE_SAME_PROCESS_ACTOR",
                "FRAME_LOCAL_MUTATION",
                "DEBUGGER_MUTATION",
                "ARBITRARY_REFLECTIVE_NAMESPACE_MANIPULATION",
            ],
            "attempts_to_prove_arbitrary_dynamic_python_mutation": False,
            "escalation_if_hostile_resistance_becomes_required": "PROCESS_ISOLATION",
        }
    )


def nested_owner_and_capability_escape_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_NESTED_OWNER_AND_CAPABILITY_ESCAPE_RULE_V1_PAD2",
            "scan_scope": "MODULE_WIDE_INDEPENDENT_OF_OUTER_STORE_ROOTS",
            "nested_FunctionDef_with_annotated_store_parameter": "FORBIDDEN",
            "nested_AsyncFunctionDef_with_annotated_store_parameter": "FORBIDDEN",
            "rootless_outer_can_hide_nested_owner": False,
            "forbidden_categories": [
                kind for kind in narrow.UseKind.__args__ if kind.startswith("FORBIDDEN_")
            ],
            "bound_method_extraction_permitted": False,
            "unknown_forwarding_permitted": False,
            "starred_store_forwarding_permitted": False,
            "return_yield_or_container_escape_permitted": False,
            "object_or_subscript_storage_permitted": False,
            "closure_generator_or_comprehension_capture_permitted": False,
            "dynamic_attribute_authority_permitted": False,
            "aliases_or_variadics_reintroduced_by_this_decision": False,
            "unsupported_use_may_be_masked_by_valid_route": False,
            "implementation_private_authoritative_state": ["_records", "_envelopes"],
            "repository_owned_access_outside_CalendarEvidenceStore_permitted": False,
        }
    )


def replay_owner_graph_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_OWNER_GRAPH_RULE_V1_PAD2",
            "compiled_binding_witness_must_pass_before_graph_extraction": True,
            "ast_use_audit_must_pass_before_graph_extraction": True,
            "owner_count": len(FROZEN_REPLAY_OWNERS),
            "owners": list(FROZEN_REPLAY_OWNERS),
            "edge_kinds": [
                "DOCUMENTED_STORE_API_TERMINAL",
                "ENUMERATED_REPLAY_OWNER_EDGE",
            ],
            "cycles_permitted": False,
            "every_owner_has_an_evidence_edge": True,
            "every_owner_path_terminates_at_documented_store_api": True,
            "unknown_forwarding_permitted": False,
            "owner_census_relation": "DISCOVERED_EQUALS_FROZEN_REGISTRY_AND_COUNT_EQUALS_11",
        }
    )


def direct_body_dependency_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_DIRECT_BODY_DEPENDENCY_RULE_V1_PAD2",
            "required_direct_bodies": list(REQUIRED_DIRECT_BODIES),
            "exact_dependency_assertion": "assert_trusted_persistence_dependency",
            "proof": "DIRECT_EXECUTABLE_AST_CALL_IN_EACH_REQUIRED_BODY",
            "wrapper_installed_guards_permitted": False,
            "startup_self_check": [
                "CALENDAR_AUTHORITY_PARENT",
                "TRUSTED_PERSISTENCE_DEPENDENCY_CHILD",
                "EXACT_CERTIFIED_TRUSTED_PERSISTENCE_IDENTITY",
                "CERTIFIED_PROOF_ARCHITECTURE_IDENTITY",
                "REVIEWED_PRODUCTION_SOURCE_AND_EXECUTABLE_IDENTITY",
                "FROZEN_PROOF_INTERPRETER_IDENTITY",
            ],
            "startup_check_replaces_five_direct_checks": False,
        }
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PROOF_ORDER_AND_COMPLETENESS_V1_PAD2",
            "proof_order": list(PROOF_ORDER),
            "separate_guarantees": {
                "compiled_binding_witness": "FROZEN_ROOT_IS_NOT_REBOUND_OR_DELETED",
                "ast_normal_form": "PERMITTED_STORE_USES_ONLY",
                "replay_owner_graph": "REPLAY_ROUTE_CLOSURE",
            },
            "bytecode_proves_all_program_semantics": False,
            "source_ast_binding_visitor_is_the_scientific_proof_of_root_immutability": False,
            "manually_maintained_ast_node_list_frozen_as_complete_python_312_binding_set": False,
            "models_all_possible_python_programs": False,
            "reaching_definition_analysis": False,
            "ssa_construction": False,
            "arbitrary_control_flow_graph_proof": False,
            "alias_propagation": False,
            "completeness": (
                "FROZEN_CPYTHON_COMPILED_ROOT_BINDING_WITNESS_PLUS_CLOSED_DIRECT_USE_SYNTAX"
            ),
            "future_unsupported_syntax": "FAIL_UNTIL_EXPLICIT_REVIEWED_AUTHORITY_CHANGE",
            "decision_certifies_grammar": True,
            "decision_certifies_current_production_conformance": False,
            "current_production_expected_result": {
                "compiled_binding_witness": "BINDING_PROOF_COMPATIBLE",
                "unexpected_root_rebinding": "NONE",
                "root_write_clear_or_delete_findings": 0,
                "ast_direct_use_grammar": "NON_CONFORMING",
                "blocking_use": (
                    "COMMON_ETF_SESSION_STATUS_GENERATOR_EXPRESSION_CAPTURE_OF_EVIDENCE_STORE"
                ),
                "both_layers_refuse_the_same_single_construct": True,
                "module_namespace_reach_sites": list(
                    KNOWN_PRODUCTION_MODULE_NAMESPACE_SITES
                ),
                "calendar_implementation": "BLOCKED",
            },
            "known_future_implementation_delta": (
                "COMMON_ETF_SESSION_STATUS_GENERATOR_CAPTURE_OF_EVIDENCE_STORE_"
                "MUST_BE_REWRITTEN_WITHOUT_SEMANTIC_PIT_ORDER_OR_EXCEPTION_DRIFT"
            ),
        }
    )


def science_lineage_and_safety() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_COMPILED_WITNESS_SCIENCE_LINEAGE_AND_SAFETY_V1_PAD2",
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
                "certified_prospective_v1": (
                    "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7"
                ),
                "failed_prospective_v2": (
                    "488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d"
                ),
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
                "trusted_persistence": "CLOSED_UNCHANGED",
            },
        }
    )


_CHILD_ARTIFACTS: tuple[tuple[str, str], ...] = (
    ("trusted_process_boundary_reference.json", "trusted_process_boundary_reference"),
    ("proof_interpreter_identity.json", "proof_interpreter_identity"),
    ("store_root_and_direct_use_grammar.json", "store_root_and_direct_use_grammar"),
    ("compiled_binding_witness_definition.json", "compiled_binding_witness_definition"),
    ("owner_code_object_identity_rule.json", "owner_code_object_identity_rule"),
    ("dynamic_execution_prohibition.json", "dynamic_execution_prohibition"),
    (
        "nested_owner_and_capability_escape_rule.json",
        "nested_owner_and_capability_escape_rule",
    ),
    ("replay_owner_graph_rule.json", "replay_owner_graph_rule"),
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


KNOWN_PRODUCTION_BLOCKER_OWNER = "common_etf_session_status"
KNOWN_PRODUCTION_BLOCKER_ROOT = "evidence_store"

#: Current production reaches its own module namespace through ``globals()`` in
#: exactly these scopes.  One of them installs the wrapper guard that the frozen
#: direct-body dependency rule already forbids; the others dispatch artifact
#: builders by name and must become an explicit registry.  The calendar
#: implementation ticket removes all five.
KNOWN_PRODUCTION_MODULE_NAMESPACE_SITES: tuple[str, ...] = (
    "<module>:_children:globals",
    "<module>:_install_exact_dependency_guards:globals",
    "<module>:_semantic_ast_sha256:globals",
    "<module>:restore_artifacts:globals",
    "<module>:write_artifacts:globals",
)


def verify_current_production_expected_result(source: str) -> dict[str, Any]:
    """Bind the frozen production claim to the reviewed source mechanically.

    Current production contains no root write, clear or delete at all.  Its only
    compiled-layer finding is the very ``common_etf_session_status``
    generator-expression capture that the closed AST grammar already refuses:
    the capture makes the root a first-class closure cell, and both layers
    therefore refuse the same single known construct.
    """

    produced = compiled_binding_witness(source)
    verify_witness_binds_source(produced, source)
    audit_dynamic_execution_prohibition(source)
    if len(produced.owners) != len(FROZEN_REPLAY_OWNERS):
        raise CompiledBindingWitnessError(
            "compiled witness owner census is not the exact frozen eleven"
        )
    if produced.root_rebinding_findings:
        raise CompiledBindingWitnessError(
            "unexpected current-production root rebinding: "
            f"{produced.root_rebinding_findings!r}"
        )
    expected_capture = (
        RootBindingFinding(
            KNOWN_PRODUCTION_BLOCKER_OWNER,
            "OWNER_CODE_OBJECT",
            KNOWN_PRODUCTION_BLOCKER_ROOT,
            0,
            "MAKE_CELL",
            "OWNER_ROOT_IS_CELL_VARIABLE",
        ),
    )
    if produced.root_capture_findings != expected_capture:
        raise CompiledBindingWitnessError(
            "current-production capture findings are not the single known "
            f"generator blocker: {produced.root_capture_findings!r}"
        )
    observed_sites = tuple(
        f"{row.scope}:{row.root}" for row in produced.module_identity_findings
    )
    if observed_sites != KNOWN_PRODUCTION_MODULE_NAMESPACE_SITES:
        raise CompiledBindingWitnessError(
            "current-production module-namespace findings are not the frozen known "
            f"set: {observed_sites!r}"
        )
    try:
        narrow.audit_store_capability_normal_form(source)
    except narrow.NormalFormError as error:
        if "FORBIDDEN_NESTED_SCOPE_CAPTURE" not in str(error):
            raise CompiledBindingWitnessError(
                f"unexpected current-production AST refusal: {error}"
            ) from error
    else:
        raise CompiledBindingWitnessError(
            "current production unexpectedly conforms to the closed AST use grammar"
        )
    return {
        "compiled_binding_witness": "BINDING_PROOF_COMPATIBLE",
        "unexpected_root_rebinding": "NONE",
        "root_write_clear_or_delete_findings": 0,
        "ast_direct_use_grammar": "REFUSED",
        "expected_generator_blocker": True,
        "blocking_owner": KNOWN_PRODUCTION_BLOCKER_OWNER,
        "blocking_root": KNOWN_PRODUCTION_BLOCKER_ROOT,
        "both_layers_refuse_the_same_single_construct": True,
        "module_namespace_reach_sites": list(KNOWN_PRODUCTION_MODULE_NAMESPACE_SITES),
    }


def compiled_binding_witness_v1_definition(
    child_artifacts: Sequence[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    source = CALENDAR_SOURCE.read_text(encoding="utf-8")
    narrow.verify_replay_owner_census(source)
    production = verify_current_production_expected_result(source)
    children = _children(child_artifacts)
    return _definition(
        {
            "decision_version": DECISION_VERSION,
            "program_ticket": PROGRAM_TICKET,
            "workstream": "EPIC X — PROSPECTIVE INTEGRATION EVIDENCE",
            "status": STATUS,
            "final_classification": FINAL_CLASSIFICATION,
            "proof_strategy": PROOF_STRATEGY,
            "pre_data": True,
            "required_review": REQUIRED_REVIEW,
            "failed_parent_sha256": FAILED_PARENT_SHA256,
            "certified_dependency_sha256": CERTIFIED_DEPENDENCY_SHA256,
            "proof_interpreter": dict(PROOF_INTERPRETER_IDENTITY),
            "material_child_count": len(children),
            "material_child_enumeration": "MECHANICALLY_ENUMERATED_FROM_ONE_REGISTRY",
            "child_definition_sha256": {
                name: child["definition_sha256"] for name, child in children.items()
            },
            "central_decisions": {
                "hand_maintained_ast_binder_census_is_the_completeness_proof": False,
                "root_immutability_proven_against_exact_compiled_owner_code_object": True,
                "compiler_identity_is_scientific_proof_material": True,
                "type_statement_root_replacement_refused_before_graph_authority": True,
                "root_may_be_a_cell_variable_of_a_conforming_owner": False,
                "closure_cell_or_frame_reflection_permitted_in_replay_owners": False,
                "module_level_owner_name_substitution_permitted": False,
                "definition_time_named_expressions_refused_in_the_outer_owner": True,
                "nested_body_local_assignment_misclassified_as_outer_write": False,
                "store_aliases_permitted": False,
                "store_variadics_permitted": False,
                "starred_store_forwarding_permitted": False,
                "dynamic_execution_in_replay_owners_permitted": False,
                "proves_arbitrary_python_semantics": False,
                "calendar_science_changed": False,
            },
            "current_production_expected_result": production,
            "authorization": {
                "independent_proof_architecture_xhigh_review_may_begin": True,
                "calendar_implementation_may_begin": False,
                "postp1_001v2r1_may_begin": False,
                "prospective_collection_may_begin": False,
            },
        }
    )


def verify_definition(persisted: Mapping[str, Any]) -> None:
    if dict(persisted) != compiled_binding_witness_v1_definition():
        raise CompiledBindingWitnessError(
            "persisted compiled binding witness decision does not reproduce"
        )
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    owners = "\n".join(f"- `{owner}`" for owner in FROZEN_REPLAY_OWNERS)
    lineage = ", ".join(FAILED_ARCHITECTURE_LINEAGE)
    interpreter = PROOF_INTERPRETER_IDENTITY
    return f"""# {DECISION_VERSION} — compiled binding witness

- Ticket: `{PROGRAM_TICKET}`
- Decision hash: `{decision['definition_sha256']}`
- Failed parent: `{FAILED_PARENT_SHA256}`
- Status: `{STATUS}`
- Classification: `{FINAL_CLASSIFICATION}`
- Strategy: `{PROOF_STRATEGY}`
- Material children: {decision['material_child_count']}

## Why the binder census was replaced

`POSTP1-002V2A-PAD1-R1` failed with `PYTHON 3.12 BINDING CENSUS INCOMPLETE`.
Manually enumerating AST binding constructs is not a bounded completeness
strategy, so this decision stops claiming it. The source AST binding visitor is
retained only for diagnostics, early failure, reason codes and regression
localization; a missing AST diagnostic can never make an actual compiled root
write scientifically acceptable.

## Two independent layers

The source layer keeps the narrow `DIRECT_IMMUTABLE_STORE_PARAMETER_NORMAL_FORM`
grammar: the only scientific root is an ordinary positional-only,
positional-or-keyword or keyword-only parameter explicitly annotated
`CalendarEvidenceStore`, usable only as the receiver of a direct `put`, `get`,
`records` or `envelopes` call or as a non-starred argument to an exact frozen
replay owner. Aliases, annotated store variadics, starred forwarding, local
construction, container derivation and nested annotated owners remain forbidden.

The compiled layer proves root immutability against the exact top-level code
object of each owner under frozen `{interpreter['implementation_name']}`
`{interpreter['version_major']}.{interpreter['version_minor']}.{interpreter['version_micro']}`
(magic `{interpreter['magic_number_hex']}`, cache tag `{interpreter['cache_tag']}`).
The reviewed source is compiled, never executed and never imported, with
`dont_inherit={COMPILE_DONT_INHERIT}` and `optimize={COMPILE_OPTIMIZE}`; cached
bytecode is not scientific authority. A runtime or compiler identity mismatch
refuses scientific authority instead of silently certifying another compiler.

## What the witness proves

A conforming root is an ordinary, uncaptured fast local. Structurally, the root
may never be a cell variable of its owner, because a cell is a first-class
object that any capturing function exposes through `__closure__`, and writing
`cell_contents` would rebind the root without emitting a single root-binding
instruction. The rule removes the entire cell-escape class by construction
rather than by enumerating escape attributes.

It is at least as strict as the source layer's unconditional nested-capture
prohibition, and in a few families it is strictly stricter: a bare `nonlocal`
declaration naming the root, a PEP 695 lazy type-alias or type-parameter scope
that reads the root, and a statically dead nested scope that still cells the
root are all accepted by the source grammar and refused here. That over-refusal
is deliberate and fail closed; the decision never claims the two layers accept
exactly the same sources.

On top of it, no instruction in an owner's own code object may write, clear or
delete the root after frame-entry parameter establishment, and, as defence in
depth, no nested code object holding the root as a free variable of the owner's
cell may `STORE_DEREF` or `DELETE_DEREF` it. A class body keeps the root in its
free variables while binding its own same-named `co_names` entry through
`STORE_NAME`; that is a different namespace and is never an owner-root write.
An ordinary assignment inside a nested function body binds that nested scope's
own local and is likewise not an outer-root write.

The module-level owner name must still denote the reviewed definition. Owners
may not be decorated, each owner name is bound exactly once in the module code
object, and anywhere in the reviewed module's whole code-object tree a later
rebinding or deletion of an owner name, a write to a live function object's
`__code__`, `__defaults__`, `__closure__`, `__globals__` or `__dict__`, and any
reach into the module namespace as a mutable mapping through `globals`, `vars`,
`locals`, `setattr`, `delattr`, `exec`, `eval`, `compile` or `__import__` all
refuse. Those checks run over every nested code object, so a substitution hidden
one call frame deep is refused too.

The frozen write/delete/clear opcode policy is checked mechanically against the
exact interpreter's opcode table, including its reserved unnamed slots and its
specialization table; an unclassified, moved or newly emittable root-binding
opcode refuses and requires a new proof architecture. Instructions are read
deoptimized, so a specialized opcode cannot hide a root write.

The witness proves exactly that, and nothing more. It does not claim to prove
arbitrary Python semantics, and frame-local mutation, debugger mutation and
arbitrary reflective namespace manipulation remain outside the trusted-process
threat model; the reflective-name and attribute prohibitions inside replay
owners are a conservative production rule, not a completeness claim. The AST
normal form proves permitted uses and the replay graph proves route closure.

## Frozen replay owners

{owners}

The production census is exactly eleven. Compiled binding, dynamic-execution and
AST use audits all precede graph extraction; cycles are forbidden and every
owner path must terminate at a documented API.

## Current production

All eleven owners are binding-proof compatible: there is no root write, clear or
delete anywhere, and no dynamic or reflective authority escape. The single
compiled-layer root finding is the `common_etf_session_status`
generator-expression capture of `evidence_store`, which exposes that root as a
closure cell; the closed AST grammar refuses the same construct. Both layers
therefore refuse one and the same known use.

Separately, current production reaches its own module namespace through
`globals()` in five scopes. One of them installs the wrapper guard that the
frozen direct-body dependency rule already forbids; the other four dispatch
artifact builders by name and must become an explicit registry. The calendar
implementation ticket removes all five, and the implementation therefore remains
blocked.

## Preserved authority and safety

Failed proof-architecture lineage `{lineage}`
remains immutable, non-certified, unused and at zero observations. Trusted
persistence `{CERTIFIED_DEPENDENCY_SHA256}` is closed and unchanged. The
trusted-process boundary, direct dependency-body rule, startup identity checks,
calendar science, failed calendar lineage, BTC-019 and Epic T are unchanged.

No observation was collected and no real Stage-B evaluation ran. Calendar
implementation, POSTP1-001V2R1, POSTP1-003R3, POSTP1-004 and collection remain
blocked. This candidate authorizes only `{REQUIRED_REVIEW}`.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Sequence[tuple[str, str]] | None = None,
) -> dict[str, Any]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    decision = compiled_binding_witness_v1_definition(registry)
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
            raise CompiledBindingWitnessError(f"persisted {filename} does not reproduce")
        _verify_definition_digest(persisted)
        if decision["child_definition_sha256"].get(
            filename.removesuffix(".json")
        ) != expected["definition_sha256"]:
            raise CompiledBindingWitnessError(
                f"compiled binding witness parent does not bind {filename}"
            )
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise CompiledBindingWitnessError(
            "persisted compiled binding witness report does not reproduce"
        )
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
