"""Runtime owner-attestation proof architecture for the ETF calendar authority.

``POSTP1-002V2A-PAD2`` failed with ``MODULE OWNER IDENTITY MODEL INCOMPLETE``.
The compiled root-binding witness itself is coherent and is retained here, but
the separate claim that a static census of reflection and module-mutation syntax
proves *which callable a frozen owner name actually denotes* is abandoned: an
open-ended blacklist is not a bounded completeness argument.

This decision replaces ``STATIC_COMPLETE_MODULE_OWNER_IDENTITY_PROOF`` with
``CONTROLLED_RUNTIME_OWNER_ATTESTATION``.  The effective runtime binding of every
frozen replay owner is *measured* at the scientific execution boundary and
compared against identity material independently compiled from the certified
reviewed source under the frozen CPython interpreter.  The mutation syntax used
to substitute an owner is irrelevant to the proof, because the proof never looks
at the syntax: it looks at the object that is actually about to be executed.

This module is a pre-data decision builder, a static audit specification and a
reference attestation mechanism.  It never collects, persists, signs or certifies
anything, and it changes no ETF calendar production code.
"""

from __future__ import annotations

import argparse
import ast
import builtins
import dis
import hashlib
import json
import sys
import threading
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Iterator, Mapping, Sequence

from btc_predictor.research import etf_calendar_authority_boundary_r1 as _bodies
from btc_predictor.research import etf_calendar_compiled_binding_witness as witness
from btc_predictor.research import etf_calendar_store_capability_normal_form_r1 as narrow


DECISION_VERSION = "ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1"
PROGRAM_TICKET = "POSTP1-001V2A-PAD3"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_runtime_owner_attestation_v1"
DEFINITION_FILENAME = "etf_calendar_runtime_owner_attestation_v1_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
FINAL_CLASSIFICATION = "ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1_READY_FOR_XHIGH_REVIEW"
PROOF_STRATEGY = (
    "COMPILED_ROOT_WITNESS_PLUS_CLOSED_AST_STORE_USE_GRAMMAR_PLUS_"
    "RUNTIME_SCIENTIFIC_EXECUTION_EPOCH_ATTESTATION"
)
REQUIRED_REVIEW = (
    "POSTP1-002V2A-PAD3_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW"
)

#: The failed ``ETF_CALENDAR_COMPILED_BINDING_WITNESS_V1`` parent.  Its compiled
#: root-binding layer is re-adopted here under a new parent; the failed parent
#: hash itself is never certified.
FAILED_PARENT_SHA256 = (
    "b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9"
)

CALENDAR_MODULE = witness.CALENDAR_MODULE
CALENDAR_SOURCE = witness.CALENDAR_SOURCE
CALENDAR_MODULE_IMPORT_NAME = "btc_predictor.research.etf_publication_calendar"
CERTIFIED_DEPENDENCY_VERSION = witness.CERTIFIED_DEPENDENCY_VERSION
CERTIFIED_DEPENDENCY_SHA256 = witness.CERTIFIED_DEPENDENCY_SHA256
FAILED_ARCHITECTURE_LINEAGE = (
    *witness.FAILED_ARCHITECTURE_LINEAGE,
    FAILED_PARENT_SHA256,
)
FAILED_CALENDAR_LINEAGE = witness.FAILED_CALENDAR_LINEAGE
FROZEN_REPLAY_OWNERS = witness.FROZEN_REPLAY_OWNERS
REQUIRED_DIRECT_BODIES = witness.REQUIRED_DIRECT_BODIES
STORE_APIS = witness.STORE_APIS
PROOF_INTERPRETER_IDENTITY = witness.PROOF_INTERPRETER_IDENTITY

_definition = narrow._definition
_verify_definition_digest = narrow._verify_definition_digest
_annotated_ordinary_roots = narrow._annotated_ordinary_roots
_top_level_functions = narrow._top_level_functions


class RuntimeOwnerAttestationError(witness.CompiledBindingWitnessError):
    """Raised when runtime owner attestation refuses scientific authority."""

    def __init__(self, message: str, evidence: Mapping[str, Any] | None = None) -> None:
        super().__init__(message)
        self.evidence: dict[str, Any] = dict(evidence or {})


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


def source_sha256(source: str) -> str:
    return witness.source_sha256(source)


# ---------------------------------------------------------------------------
# Deterministic owner code-execution fingerprint
# ---------------------------------------------------------------------------

CODE_FINGERPRINT_VERSION = "ETF_CALENDAR_OWNER_CODE_FINGERPRINT_V1_CPYTHON_312"

#: Execution-relevant code-object material.  ``co_code`` alone is not identity:
#: the constant pool, the name/variable layout, the argument layout, the flags,
#: the exception table and every nested code object change what executes.
CODE_FINGERPRINT_FIELDS: tuple[str, ...] = (
    "co_argcount",
    "co_posonlyargcount",
    "co_kwonlyargcount",
    "co_nlocals",
    "co_stacksize",
    "co_flags",
    "co_firstlineno",
    "co_name",
    "co_qualname",
)

#: ``co_filename`` records where the compiler read the text, not what executes,
#: and an independently compiled expectation legitimately carries another path.
#: Reviewed-source identity is attested separately and exactly.
CODE_FINGERPRINT_EXCLUDED_FIELDS: tuple[str, ...] = ("co_filename",)

CODE_FINGERPRINT_BYTE_FIELDS: tuple[str, ...] = (
    "co_code",
    "co_exceptiontable",
    "co_linetable",
)

CODE_FINGERPRINT_NAME_TUPLE_FIELDS: tuple[str, ...] = (
    "co_names",
    "co_varnames",
    "co_freevars",
    "co_cellvars",
)

#: Constant kinds a reviewed replay owner may legitimately carry.  Anything else
#: refuses instead of being hashed through an unstable representation.
CODE_FINGERPRINT_CONSTANT_KINDS: tuple[str, ...] = (
    "NONE",
    "ELLIPSIS",
    "BOOL",
    "INT",
    "FLOAT",
    "COMPLEX",
    "STR",
    "BYTES",
    "TUPLE",
    "FROZENSET",
    "CODE",
)


def _encode_float(value: float) -> str:
    if value != value:
        return "nan"
    if value == 0.0:
        return "-0.0" if str(value)[0] == "-" else "0.0"
    return repr(value)


def _encode_constant(value: Any) -> Any:
    """Type-tagged canonical encoding of one code constant.

    The tag prefix keeps distinct types distinct (``True`` is not ``1``, ``1``
    is not ``1.0``, ``"a"`` is not ``b"a"``), ``frozenset`` members are ordered
    by their own canonical encoding so no hash-seed randomisation leaks in, and
    an unsupported constant kind refuses rather than being represented by an
    unstable ``repr``.
    """

    if value is None:
        return ["NONE"]
    if value is Ellipsis:
        return ["ELLIPSIS"]
    if isinstance(value, bool):
        return ["BOOL", value]
    if isinstance(value, int):
        return ["INT", str(value)]
    if isinstance(value, float):
        return ["FLOAT", _encode_float(value)]
    if isinstance(value, complex):
        return ["COMPLEX", _encode_float(value.real), _encode_float(value.imag)]
    if isinstance(value, str):
        return ["STR", value]
    if isinstance(value, bytes):
        return ["BYTES", value.hex()]
    if isinstance(value, tuple):
        return ["TUPLE", [_encode_constant(item) for item in value]]
    if isinstance(value, frozenset):
        return [
            "FROZENSET",
            sorted(_canonical_json(_encode_constant(item)) for item in value),
        ]
    if isinstance(value, types.CodeType):
        return ["CODE", owner_code_fingerprint(value)]
    raise RuntimeOwnerAttestationError(
        "unsupported code constant kind for a deterministic execution "
        f"fingerprint: {type(value).__name__}: REFUSE_SCIENTIFIC_AUTHORITY"
    )


def code_fingerprint_material(code: types.CodeType) -> dict[str, Any]:
    """Execution-relevant material of one code object, without any address."""

    material: dict[str, Any] = {
        "fingerprint_version": CODE_FINGERPRINT_VERSION,
    }
    for field in CODE_FINGERPRINT_FIELDS:
        material[field] = getattr(code, field)
    for field in CODE_FINGERPRINT_BYTE_FIELDS:
        material[field] = getattr(code, field).hex()
    for field in CODE_FINGERPRINT_NAME_TUPLE_FIELDS:
        material[field] = list(getattr(code, field))
    material["co_consts"] = [_encode_constant(const) for const in code.co_consts]
    return material


def owner_code_fingerprint(code: types.CodeType) -> str:
    """Deterministic recursive execution fingerprint of one code object.

    Two independently compiled code objects are different objects, so identity
    (``function.__code__ is expected_code``) can never be the rule.  The
    fingerprint is the rule, and it recurses into every nested code object held
    in the constant pool.
    """

    if not isinstance(code, types.CodeType):
        raise RuntimeOwnerAttestationError(
            "owner code fingerprint requires a code object: "
            "REFUSE_SCIENTIFIC_AUTHORITY"
        )
    return _digest(code_fingerprint_material(code))


# ---------------------------------------------------------------------------
# Deterministic runtime value fingerprint for defaults and kwdefaults
# ---------------------------------------------------------------------------

VALUE_FINGERPRINT_VERSION = "ETF_CALENDAR_OWNER_VALUE_FINGERPRINT_V1"

#: Runtime default values are ordinary mutable function-object state: replacing
#: them changes behaviour without touching ``__code__``.  Only stable, address
#: free value kinds may be fingerprinted; anything else refuses.
VALUE_FINGERPRINT_KINDS: tuple[str, ...] = (
    "NONE",
    "ELLIPSIS",
    "BOOL",
    "INT",
    "FLOAT",
    "COMPLEX",
    "STR",
    "BYTES",
    "TUPLE",
    "FROZENSET",
)

UNSTABLE_VALUE_FINGERPRINT = "UNSTABLE_RUNTIME_VALUE_IDENTITY"


def _encode_value(value: Any) -> Any:
    if isinstance(value, types.CodeType):
        raise RuntimeOwnerAttestationError(UNSTABLE_VALUE_FINGERPRINT)
    return _encode_constant(value)


def value_fingerprint(value: Any) -> str:
    """Stable fingerprint of a runtime default/kwdefault value.

    ``id()``, memory addresses and any ``repr`` that can embed an address are
    never scientific identity, so an object whose value identity is not stable
    yields the explicit ``UNSTABLE_RUNTIME_VALUE_IDENTITY`` marker and refuses
    the attestation instead of silently hashing an address.
    """

    try:
        encoded = _encode_value(value)
    except RuntimeOwnerAttestationError:
        return UNSTABLE_VALUE_FINGERPRINT
    return _digest({"fingerprint_version": VALUE_FINGERPRINT_VERSION, "value": encoded})


def _mapping_fingerprint(mapping: Mapping[str, Any] | None) -> str:
    if mapping is None:
        return value_fingerprint(None)
    if not isinstance(mapping, dict):
        return UNSTABLE_VALUE_FINGERPRINT
    items = []
    for key in sorted(mapping):
        if not isinstance(key, str):
            return UNSTABLE_VALUE_FINGERPRINT
        fingerprint = value_fingerprint(mapping[key])
        if fingerprint == UNSTABLE_VALUE_FINGERPRINT:
            return UNSTABLE_VALUE_FINGERPRINT
        items.append([key, fingerprint])
    return _digest(
        {"fingerprint_version": VALUE_FINGERPRINT_VERSION, "mapping": items}
    )


# ---------------------------------------------------------------------------
# Frozen runtime owner identity contract
# ---------------------------------------------------------------------------

FROZEN_CALLABLE_TYPE = "types.FunctionType"
FROZEN_CLOSURE_CONTRACT = "NO_CLOSURE_CELLS"
FROZEN_WRAPPER_CONTRACT = "UNDECORATED_PLAIN_FUNCTION"
NO_DEFAULTS_FINGERPRINT_SENTINEL = "NO_DECLARED_DEFAULTS"

RUNTIME_OWNER_ATTESTATION_FIELDS: tuple[str, ...] = (
    "binding_present",
    "callable_type",
    "name",
    "qualname",
    "module",
    "code_fingerprint",
    "globals_is_attested_module_namespace",
    "builtins_is_the_real_builtins_namespace",
    "closure_contract",
    "defaults_fingerprint",
    "kwdefaults_fingerprint",
    "wrapper_state",
)

RUNTIME_OWNER_REFUSAL_CODES: tuple[str, ...] = (
    "OWNER_BINDING_ABSENT",
    "OWNER_CALLABLE_TYPE_MISMATCH",
    "OWNER_NAME_MISMATCH",
    "OWNER_QUALNAME_MISMATCH",
    "OWNER_MODULE_MISMATCH",
    "OWNER_CODE_FINGERPRINT_MISMATCH",
    "OWNER_GLOBALS_NAMESPACE_MISMATCH",
    "OWNER_BUILTINS_NAMESPACE_MISMATCH",
    "OWNER_CLOSURE_CONTRACT_MISMATCH",
    "OWNER_DEFAULTS_FINGERPRINT_MISMATCH",
    "OWNER_KWDEFAULTS_FINGERPRINT_MISMATCH",
    "OWNER_WRAPPER_STATE_MISMATCH",
)

MODULE_NAMESPACE_REFUSAL_CODES: tuple[str, ...] = (
    "MODULE_IS_NOT_AN_EXACT_MODULE_OBJECT",
    "MODULE_NOT_BOUND_IN_SYS_MODULES",
    "MODULE_NOT_BOUND_AS_THE_PACKAGE_ATTRIBUTE",
    "DUPLICATE_CALENDAR_MODULE_INSTANCE",
    "MODULE_NAMESPACE_BUILTINS_MISMATCH",
    "MODULE_SOURCE_IDENTITY_MISMATCH",
    "CONSUMER_BINDING_DIVERGENCE",
)

SCIENTIFIC_EXECUTION_NOT_AUTHORIZED = "SCIENTIFIC_EXECUTION_NOT_AUTHORIZED"
RESULT_REJECTED = "RESULT_REJECTED"
DATA_QUALITY_FAIL = "DATA_QUALITY_FAIL"


@dataclass(frozen=True, order=True)
class OwnerIdentityExpectation:
    """Frozen runtime identity expectation for one replay owner.

    Every field is derived from the certified reviewed source under the frozen
    proof interpreter, never from the live process.
    """

    owner: str
    qualname: str
    module: str
    first_line: int
    parameters: tuple[str, ...]
    roots: tuple[str, ...]
    code_fingerprint: str
    callable_type: str = FROZEN_CALLABLE_TYPE
    closure_contract: str = FROZEN_CLOSURE_CONTRACT
    defaults_fingerprint: str = ""
    kwdefaults_fingerprint: str = ""
    wrapper_contract: str = FROZEN_WRAPPER_CONTRACT

    def as_material(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "qualname": self.qualname,
            "module": self.module,
            "first_line": self.first_line,
            "parameters": list(self.parameters),
            "roots": list(self.roots),
            "code_fingerprint": self.code_fingerprint,
            "callable_type": self.callable_type,
            "closure_contract": self.closure_contract,
            "defaults_fingerprint": self.defaults_fingerprint,
            "kwdefaults_fingerprint": self.kwdefaults_fingerprint,
            "wrapper_contract": self.wrapper_contract,
        }


def _literal_default(node: ast.expr, owner: str) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError) as error:
        raise RuntimeOwnerAttestationError(
            f"closure member {owner!r} declares a parameter default that is not a "
            "reviewable literal; the frozen runtime identity contract requires "
            "explicitly reviewed default value material: "
            "REFUSE_SCIENTIFIC_AUTHORITY"
        ) from error


def _declared_default_contract(
    node: ast.FunctionDef | ast.AsyncFunctionDef,
) -> tuple[str, str]:
    """Frozen default expectation structurally derived from the reviewed source.

    Runtime defaults are ordinary mutable function-object state, so they are
    attested against a fingerprint of the exact values the certified signature
    declares.  A default that is not a reviewable literal refuses here rather
    than silently attesting whatever the live process happens to hold.
    """

    positional = tuple(
        _literal_default(default, node.name) for default in node.args.defaults
    )
    keyword = {
        argument.arg: _literal_default(default, node.name)
        for argument, default in zip(node.args.kwonlyargs, node.args.kw_defaults)
        if default is not None
    }
    return (
        value_fingerprint(positional or None),
        _mapping_fingerprint(keyword or None),
    )


def expected_owner_identities(
    source: str,
    module_name: str = CALENDAR_MODULE_IMPORT_NAME,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
    filename: str | None = None,
) -> tuple[OwnerIdentityExpectation, ...]:
    """Compile the certified source and derive every frozen owner expectation.

    The reviewed source is compiled, never imported or executed, under the exact
    frozen interpreter; the resulting code objects are the independent identity
    authority that the effective runtime bindings are measured against.
    """

    witness.verify_proof_interpreter_identity()
    tree = ast.parse(source)
    top_level = _top_level_functions(tree)
    missing = sorted(name for name in frozen_owners if name not in top_level)
    if missing:
        raise RuntimeOwnerAttestationError(
            f"frozen replay owner is absent from the reviewed source: {missing!r}"
        )
    module_code = witness.compile_reviewed_source(
        source, CALENDAR_MODULE if filename is None else filename
    )
    expectations: list[OwnerIdentityExpectation] = []
    for name in sorted(frozen_owners):
        node = top_level[name]
        roots = tuple(sorted(_annotated_ordinary_roots(node)))
        if not roots:
            raise RuntimeOwnerAttestationError(
                f"frozen replay owner {name!r} declares no explicitly annotated "
                "CalendarEvidenceStore root"
            )
        if node.decorator_list:
            raise RuntimeOwnerAttestationError(
                f"frozen replay owner {name!r} is decorated; the frozen runtime "
                "owner contract requires an undecorated plain function"
            )
        identity, code = witness._identify_owner_code_object(
            module_code, name, witness.owner_definition_line(node), roots
        )
        defaults, kwdefaults = _declared_default_contract(node)
        expectations.append(
            OwnerIdentityExpectation(
                owner=name,
                qualname=identity.qualname,
                module=module_name,
                first_line=identity.first_line,
                parameters=identity.parameters,
                roots=identity.roots,
                code_fingerprint=owner_code_fingerprint(code),
                defaults_fingerprint=defaults,
                kwdefaults_fingerprint=kwdefaults,
            )
        )
    return tuple(expectations)


# ---------------------------------------------------------------------------
# Effective runtime owner attestation
# ---------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class OwnerAttestation:
    """One measured effective runtime owner binding."""

    owner: str
    conforms: bool
    reasons: tuple[str, ...]
    material: tuple[tuple[str, Any], ...]

    def as_material(self) -> dict[str, Any]:
        return {
            "owner": self.owner,
            "conforms": self.conforms,
            "reasons": list(self.reasons),
            "attested": dict(self.material),
        }


def _callable_type_name(value: Any) -> str:
    kind = type(value)
    module = getattr(kind, "__module__", "?")
    return f"{module}.{kind.__qualname__}"


def _closure_contract(value: Any) -> str:
    closure = getattr(value, "__closure__", None)
    if closure is None:
        return FROZEN_CLOSURE_CONTRACT
    return f"CLOSURE_CELLS:{len(closure)}"


def _wrapper_state(value: Any) -> str:
    states: list[str] = []
    if "__wrapped__" in getattr(value, "__dict__", {}) or hasattr(value, "__wrapped__"):
        states.append("WRAPPED_CALLABLE")
    function_dict = getattr(value, "__dict__", None)
    if function_dict:
        states.append(f"FUNCTION_DICT_KEYS:{sorted(function_dict)}")
    if not states:
        return FROZEN_WRAPPER_CONTRACT
    return "|".join(states)


def _resolved_builtins(namespace: Mapping[str, Any] | None) -> Any:
    if namespace is None:
        return None
    candidate = namespace.get("__builtins__")
    if isinstance(candidate, types.ModuleType):
        return candidate.__dict__
    return candidate


def _attest_function_binding(
    namespace: Mapping[str, Any],
    binding_name: str,
    expectation: OwnerIdentityExpectation,
) -> tuple[bool, tuple[str, ...], dict[str, Any]]:
    """Measure one effective function binding against a frozen identity contract.

    The binding is read from the namespace a call actually resolves through, so
    the mechanism that replaced it is irrelevant to the measurement.
    """

    reasons: list[str] = []
    material: dict[str, Any] = {
        field: None for field in RUNTIME_OWNER_ATTESTATION_FIELDS
    }
    if binding_name not in namespace:
        material["binding_present"] = False
        return False, ("OWNER_BINDING_ABSENT",), material
    effective = namespace[binding_name]
    material["binding_present"] = True
    material["callable_type"] = _callable_type_name(effective)
    if type(effective) is not types.FunctionType:
        material["globals_is_attested_module_namespace"] = False
        material["builtins_is_the_real_builtins_namespace"] = False
        material["closure_contract"] = _closure_contract(effective)
        material["wrapper_state"] = _wrapper_state(effective)
        return False, ("OWNER_CALLABLE_TYPE_MISMATCH",), material
    material["name"] = effective.__name__
    material["qualname"] = effective.__qualname__
    material["module"] = effective.__module__
    try:
        material["code_fingerprint"] = owner_code_fingerprint(effective.__code__)
    except RuntimeOwnerAttestationError:
        material["code_fingerprint"] = UNSTABLE_VALUE_FINGERPRINT
    material["globals_is_attested_module_namespace"] = effective.__globals__ is namespace
    bound_builtins = getattr(effective, "__builtins__", None)
    if isinstance(bound_builtins, types.ModuleType):
        bound_builtins = bound_builtins.__dict__
    material["builtins_is_the_real_builtins_namespace"] = (
        bound_builtins is builtins.__dict__
    )
    material["closure_contract"] = _closure_contract(effective)
    material["defaults_fingerprint"] = value_fingerprint(effective.__defaults__)
    material["kwdefaults_fingerprint"] = _mapping_fingerprint(effective.__kwdefaults__)
    material["wrapper_state"] = _wrapper_state(effective)

    if material["name"] != expectation.owner:
        reasons.append("OWNER_NAME_MISMATCH")
    if material["qualname"] != expectation.qualname:
        reasons.append("OWNER_QUALNAME_MISMATCH")
    if material["module"] != expectation.module:
        reasons.append("OWNER_MODULE_MISMATCH")
    if material["code_fingerprint"] != expectation.code_fingerprint:
        reasons.append("OWNER_CODE_FINGERPRINT_MISMATCH")
    if material["globals_is_attested_module_namespace"] is not True:
        reasons.append("OWNER_GLOBALS_NAMESPACE_MISMATCH")
    if material["builtins_is_the_real_builtins_namespace"] is not True:
        reasons.append("OWNER_BUILTINS_NAMESPACE_MISMATCH")
    if material["closure_contract"] != expectation.closure_contract:
        reasons.append("OWNER_CLOSURE_CONTRACT_MISMATCH")
    if material["defaults_fingerprint"] != expectation.defaults_fingerprint:
        reasons.append("OWNER_DEFAULTS_FINGERPRINT_MISMATCH")
    if material["kwdefaults_fingerprint"] != expectation.kwdefaults_fingerprint:
        reasons.append("OWNER_KWDEFAULTS_FINGERPRINT_MISMATCH")
    if material["wrapper_state"] != expectation.wrapper_contract:
        reasons.append("OWNER_WRAPPER_STATE_MISMATCH")
    return not reasons, tuple(reasons), material


def attest_owner(
    module: types.ModuleType, expectation: OwnerIdentityExpectation
) -> OwnerAttestation:
    """Measure one effective runtime replay-owner binding."""

    conforms, reasons, material = _attest_function_binding(
        module.__dict__, expectation.owner, expectation
    )
    return OwnerAttestation(
        expectation.owner, conforms, reasons, tuple(sorted(material.items()))
    )


# ---------------------------------------------------------------------------
# Transitive execution closure
# ---------------------------------------------------------------------------
#
# Attesting only the eleven entry bindings would measure who is called, not what
# executes.  An owner resolves other module-level names at call time, so a
# persistent replacement of any reachable helper, result class, frozen constant
# or imported dependency changes the scientific answer while every owner
# fingerprint still matches.  The closure is therefore derived mechanically from
# the certified compiled code — a fixpoint over the names the owner code objects
# can actually load — and never from a hand-maintained list.

CLOSURE_CONTRACT_VERSION = "CALENDAR_TRANSITIVE_EXECUTION_CLOSURE_V1"
PROJECT_PACKAGE_ROOT = "btc_predictor"
BASELINE_BOUND = "BASELINE_BOUND"

_GLOBAL_NAME_OPNAMES: frozenset[str] = frozenset(
    {
        "LOAD_GLOBAL",
        "LOAD_NAME",
        "LOAD_FROM_DICT_OR_GLOBALS",
        "STORE_GLOBAL",
        "DELETE_GLOBAL",
    }
)

CLOSURE_KINDS: tuple[str, ...] = (
    "CLOSURE_FUNCTION",
    "CLOSURE_CLASS",
    "CLOSURE_VALUE",
    "CLOSURE_IMPORT",
)

CLOSURE_REFUSAL_CODES: tuple[str, ...] = (
    "CLOSURE_BINDING_ABSENT",
    "CLOSURE_CLASS_TYPE_MISMATCH",
    "CLOSURE_CLASS_IDENTITY_MISMATCH",
    "CLOSURE_CLASS_MRO_MISMATCH",
    "CLOSURE_CLASS_CERTIFIED_METHOD_MISMATCH",
    "CLOSURE_CLASS_METHOD_WRAPPER_STATE_MISMATCH",
    "CLOSURE_CLASS_UNCERTIFIED_METHOD_PRESENT",
    "CLOSURE_VALUE_FINGERPRINT_MISMATCH",
    "CLOSURE_VALUE_NOT_STATICALLY_DERIVABLE",
    "CLOSURE_IMPORT_KIND_MISMATCH",
    "CLOSURE_IMPORT_NOT_BOUND_IN_SYS_MODULES",
    "CLOSURE_IMPORT_ORIGIN_MISMATCH",
    "CLOSURE_IMPORT_SOURCE_IDENTITY_MISMATCH",
    "CLOSURE_IMPORT_OBJECT_IDENTITY_MISMATCH",
    "CLOSURE_IMPORT_PROJECT_FUNCTION_MISMATCH",
)


def _code_subtree(code: types.CodeType) -> Iterator[types.CodeType]:
    yield code
    for constant in code.co_consts:
        if isinstance(constant, types.CodeType):
            yield from _code_subtree(constant)


def referenced_global_names(code: types.CodeType) -> frozenset[str]:
    """Every module-level name the given code object subtree can resolve.

    Instructions are read deoptimized so a specialized global load cannot hide a
    reachable name.
    """

    names: set[str] = set()
    for nested in _code_subtree(code):
        for instruction in dis.get_instructions(
            nested, show_caches=False, adaptive=False
        ):
            if instruction.opname in _GLOBAL_NAME_OPNAMES and isinstance(
                instruction.argval, str
            ):
                names.add(instruction.argval)
    return frozenset(names)


def _module_level_binding_kinds(tree: ast.Module) -> dict[str, str]:
    kinds: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            kinds[node.name] = "CLOSURE_FUNCTION"
        elif isinstance(node, ast.ClassDef):
            kinds[node.name] = "CLOSURE_CLASS"
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                kinds[alias.asname or alias.name.split(".")[0]] = "CLOSURE_IMPORT"
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    kinds[target.id] = "CLOSURE_VALUE"
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            kinds[node.target.id] = "CLOSURE_VALUE"
    return kinds


def _module_level_import_origins(tree: ast.Module) -> dict[str, tuple[str, str]]:
    """Map each imported local binding to its frozen ``(origin, attribute)``."""

    origins: dict[str, tuple[str, str]] = {}
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                local = alias.asname or alias.name.split(".")[0]
                origins[local] = (
                    alias.name if alias.asname else alias.name.split(".")[0],
                    "",
                )
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                raise RuntimeOwnerAttestationError(
                    "relative imports are not a frozen closure origin"
                )
            for alias in node.names:
                origins[alias.asname or alias.name] = (node.module or "", alias.name)
    return origins


def _module_level_value_nodes(tree: ast.Module) -> dict[str, ast.expr]:
    values: dict[str, ast.expr] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and node.value is not None:
            for target in node.targets:
                if isinstance(target, ast.Name):
                    values[target.id] = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.value is not None
        ):
            values[node.target.id] = node.value
    return values


def _root_annotation_type_names(
    tree: ast.Module, frozen_owners: Sequence[str]
) -> tuple[str, ...]:
    """The store type the owners declare, so the authoritative edges are closed."""

    top_level = _top_level_functions(tree)
    names: set[str] = set()
    for owner in frozen_owners:
        node = top_level.get(owner)
        if node is None:
            continue
        arguments = node.args
        for argument in (
            *arguments.posonlyargs,
            *arguments.args,
            *arguments.kwonlyargs,
        ):
            if isinstance(argument.annotation, ast.Name):
                names.add(argument.annotation.id)
    return tuple(sorted(names & set(_module_level_binding_kinds(tree))))


@dataclass(frozen=True)
class ExecutionClosure:
    """The mechanically derived transitive execution closure of the owners."""

    functions: tuple[str, ...]
    classes: tuple[str, ...]
    values: tuple[str, ...]
    imports: tuple[str, ...]
    unresolved_names: tuple[str, ...]

    def as_material(self) -> dict[str, Any]:
        return {
            "closure_contract_version": CLOSURE_CONTRACT_VERSION,
            "functions": list(self.functions),
            "classes": list(self.classes),
            "values": list(self.values),
            "imports": list(self.imports),
            "unresolved_names": list(self.unresolved_names),
        }


def execution_closure(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
    filename: str | None = None,
) -> ExecutionClosure:
    """Derive the transitive execution closure from the certified compiled code."""

    witness.verify_proof_interpreter_identity()
    tree = ast.parse(source)
    kinds = _module_level_binding_kinds(tree)
    module_code = witness.compile_reviewed_source(
        source, CALENDAR_MODULE if filename is None else filename
    )
    by_qualname: dict[str, types.CodeType] = {}
    for code in witness._all_code_objects(module_code):
        by_qualname.setdefault(code.co_qualname, code)

    seeds = [*frozen_owners, *_root_annotation_type_names(tree, frozen_owners)]
    reached: dict[str, str] = {}
    unresolved: set[str] = set()
    frontier = list(seeds)
    while frontier:
        name = frontier.pop()
        if name in reached:
            continue
        kind = kinds.get(name)
        if kind is None:
            unresolved.add(name)
            continue
        reached[name] = kind
        if kind not in {"CLOSURE_FUNCTION", "CLOSURE_CLASS"}:
            continue
        code = by_qualname.get(name)
        if code is None:
            raise RuntimeOwnerAttestationError(
                f"closure member {name!r} has no certified code object"
            )
        frontier.extend(sorted(referenced_global_names(code)))
    return ExecutionClosure(
        functions=tuple(
            sorted(n for n, kind in reached.items() if kind == "CLOSURE_FUNCTION")
        ),
        classes=tuple(
            sorted(n for n, kind in reached.items() if kind == "CLOSURE_CLASS")
        ),
        values=tuple(
            sorted(n for n, kind in reached.items() if kind == "CLOSURE_VALUE")
        ),
        imports=tuple(
            sorted(n for n, kind in reached.items() if kind == "CLOSURE_IMPORT")
        ),
        unresolved_names=tuple(sorted(unresolved)),
    )


def _deep_value_encoding(value: Any, depth: int = 0) -> Any:
    """Canonical encoding of a frozen module-level value, address free."""

    if depth > 32:
        raise RuntimeOwnerAttestationError(UNSTABLE_VALUE_FINGERPRINT)
    if isinstance(value, dict):
        items = []
        for key in value:
            if not isinstance(key, (str, int, bool, float, bytes)) or isinstance(
                key, bool
            ):
                if not isinstance(key, bool):
                    raise RuntimeOwnerAttestationError(UNSTABLE_VALUE_FINGERPRINT)
            items.append(
                [
                    _canonical_json(_deep_value_encoding(key, depth + 1)),
                    _deep_value_encoding(value[key], depth + 1),
                ]
            )
        return ["DICT", sorted(items, key=lambda row: row[0])]
    if isinstance(value, list):
        return ["LIST", [_deep_value_encoding(item, depth + 1) for item in value]]
    if isinstance(value, tuple):
        return ["TUPLE", [_deep_value_encoding(item, depth + 1) for item in value]]
    if isinstance(value, (set, frozenset)):
        tag = "FROZENSET" if isinstance(value, frozenset) else "SET"
        return [
            tag,
            sorted(
                _canonical_json(_deep_value_encoding(item, depth + 1)) for item in value
            ),
        ]
    if isinstance(value, types.CodeType):
        raise RuntimeOwnerAttestationError(UNSTABLE_VALUE_FINGERPRINT)
    return _encode_constant(value)


def deep_value_fingerprint(value: Any) -> str:
    """Stable deep fingerprint of a frozen module-level value."""

    try:
        encoded = _deep_value_encoding(value)
    except RuntimeOwnerAttestationError:
        return UNSTABLE_VALUE_FINGERPRINT
    return _digest(
        {"fingerprint_version": VALUE_FINGERPRINT_VERSION, "value": encoded}
    )


@dataclass(frozen=True, order=True)
class ClosureClassExpectation:
    """Frozen identity expectation for one reachable module-level class."""

    name: str
    qualname: str
    module: str
    metaclass: str
    bases: tuple[str, ...]
    certified_method_fingerprints: tuple[tuple[str, str, str], ...]

    def as_material(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "qualname": self.qualname,
            "module": self.module,
            "metaclass": self.metaclass,
            "bases": list(self.bases),
            "certified_method_fingerprints": [
                list(row) for row in self.certified_method_fingerprints
            ],
        }


@dataclass(frozen=True, order=True)
class ClosureValueExpectation:
    """Frozen identity expectation for one reachable module-level value."""

    name: str
    fingerprint: str
    statically_derived: bool

    def as_material(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "fingerprint": self.fingerprint,
            "statically_derived": self.statically_derived,
        }


@dataclass(frozen=True, order=True)
class ClosureImportExpectation:
    """Frozen identity expectation for one reachable imported binding."""

    name: str
    origin_module: str
    origin_attribute: str
    ownership: str
    certified_module: str
    source_sha256: str
    defining_module: str = ""
    function_expectations: tuple[OwnerIdentityExpectation, ...] = ()

    def as_material(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "origin_module": self.origin_module,
            "origin_attribute": self.origin_attribute,
            "ownership": self.ownership,
            "certified_module": self.certified_module,
            "source_sha256": self.source_sha256,
            "defining_module": self.defining_module,
            "function_expectations": [
                row.as_material() for row in self.function_expectations
            ],
        }


@dataclass(frozen=True)
class ExecutionClosureExpectation:
    """Every frozen expectation of one certified transitive execution closure."""

    closure: ExecutionClosure
    owners: tuple[OwnerIdentityExpectation, ...]
    functions: tuple[OwnerIdentityExpectation, ...]
    classes: tuple[ClosureClassExpectation, ...]
    values: tuple[ClosureValueExpectation, ...]
    imports: tuple[ClosureImportExpectation, ...]

    def as_material(self) -> dict[str, Any]:
        return {
            "closure": self.closure.as_material(),
            "owners": [row.as_material() for row in self.owners],
            "functions": [row.as_material() for row in self.functions],
            "classes": [row.as_material() for row in self.classes],
            "values": [row.as_material() for row in self.values],
            "imports": [row.as_material() for row in self.imports],
        }

    @property
    def digest(self) -> str:
        return _digest(self.as_material())


def _project_module_source(dotted: str) -> Path | None:
    """Resolve one project dotted name to its certified source file, if any."""

    root = Path(__file__).resolve().parents[2]
    base = root.joinpath(*dotted.split("."))
    module_path = base.with_suffix(".py")
    if module_path.is_file():
        return module_path
    package_path = base / "__init__.py"
    if package_path.is_file():
        return package_path
    return None


def _certified_project_module(origin_module: str, origin_attribute: str) -> tuple[str, str]:
    """The dotted name and certified digest of one project-owned closure import.

    ``from package import submodule`` names the package as the origin, so the
    submodule's own certified source is the one that governs what executes.
    """

    candidates = []
    if origin_attribute:
        candidates.append(f"{origin_module}.{origin_attribute}")
    candidates.append(origin_module)
    for dotted in candidates:
        path = _project_module_source(dotted)
        if path is not None:
            return dotted, source_sha256(path.read_text(encoding="utf-8"))
    raise RuntimeOwnerAttestationError(
        f"project closure import {origin_module}.{origin_attribute} has no "
        "certified source"
    )


#: CPython promotes these class-body functions to class methods implicitly, so
#: the certified expectation must record the descriptor the interpreter builds,
#: not only the ``def`` the source writes.
_IMPLICIT_CLASSMETHOD_NAMES: frozenset[str] = frozenset(
    {"__init_subclass__", "__class_getitem__"}
)


def _certified_method_kind(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    decorators = {
        decorator.id
        for decorator in node.decorator_list
        if isinstance(decorator, ast.Name)
    }
    if "classmethod" in decorators or node.name in _IMPLICIT_CLASSMETHOD_NAMES:
        return "CLASSMETHOD"
    if "staticmethod" in decorators:
        return "STATICMETHOD"
    if decorators or node.decorator_list:
        raise RuntimeOwnerAttestationError(
            f"closure class method {node.name!r} carries an unsupported decorator"
        )
    return "FUNCTION"


def _class_attribute_function(value: Any) -> tuple[str, types.FunctionType] | None:
    if type(value) is types.FunctionType:
        return "FUNCTION", value
    if isinstance(value, classmethod) and type(value.__func__) is types.FunctionType:
        return "CLASSMETHOD", value.__func__
    if isinstance(value, staticmethod) and type(value.__func__) is types.FunctionType:
        return "STATICMETHOD", value.__func__
    return None


def _project_module_function_expectations(
    dotted: str, only: frozenset[str] | None = None
) -> tuple[OwnerIdentityExpectation, ...]:
    """Frozen identity expectations for the functions of one project module.

    Attesting whole project-owned closure modules avoids attributing each
    reached attribute to its object by dataflow, and is strictly stricter than
    doing so.
    """

    path = _project_module_source(dotted)
    if path is None:
        raise RuntimeOwnerAttestationError(
            f"project closure module {dotted!r} has no certified source"
        )
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text)
    module_code = witness.compile_reviewed_source(text, str(path))
    by_qualname: dict[str, types.CodeType] = {}
    for code in witness._all_code_objects(module_code):
        by_qualname.setdefault(code.co_qualname, code)
    expectations: list[OwnerIdentityExpectation] = []
    for node in tree.body:
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if only is not None and node.name not in only:
            continue
        code = by_qualname.get(node.name)
        if code is None:
            raise RuntimeOwnerAttestationError(
                f"project closure function {dotted}.{node.name} has no certified "
                "code object"
            )
        expectations.append(
            _function_expectation_from_code(node.name, node.name, dotted, code, node)
        )
    return tuple(sorted(expectations))


def _resolve_project_definition(
    dotted: str, attribute: str, depth: int = 0
) -> tuple[str, str]:
    """Follow project re-exports to the module that actually defines a name."""

    if depth > 4:
        raise RuntimeOwnerAttestationError(
            f"project closure re-export chain for {dotted}.{attribute} is too deep"
        )
    path = _project_module_source(dotted)
    if path is None:
        raise RuntimeOwnerAttestationError(
            f"project closure module {dotted!r} has no certified source"
        )
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if (
            isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
            and node.name == attribute
        ):
            return dotted, attribute
        if isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                if (alias.asname or alias.name) == attribute:
                    return _resolve_project_definition(
                        node.module, alias.name, depth + 1
                    )
    raise RuntimeOwnerAttestationError(
        f"project closure import {dotted}.{attribute} has no certified definition"
    )


def _function_expectation_from_code(
    name: str,
    qualname: str,
    module_name: str,
    code: types.CodeType,
    node: ast.FunctionDef | ast.AsyncFunctionDef,
    roots: tuple[str, ...] = (),
) -> OwnerIdentityExpectation:
    if node.decorator_list:
        raise RuntimeOwnerAttestationError(
            f"closure function {name!r} is decorated; the frozen runtime identity "
            "contract requires an undecorated plain function"
        )
    defaults, kwdefaults = _declared_default_contract(node)
    return OwnerIdentityExpectation(
        owner=name,
        qualname=qualname,
        module=module_name,
        first_line=code.co_firstlineno,
        parameters=witness._declared_parameters(code),
        roots=roots,
        code_fingerprint=owner_code_fingerprint(code),
        defaults_fingerprint=defaults,
        kwdefaults_fingerprint=kwdefaults,
    )


def expected_execution_closure(
    source: str,
    module_name: str = CALENDAR_MODULE_IMPORT_NAME,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
    filename: str | None = None,
) -> ExecutionClosureExpectation:
    """Derive every closure expectation from the certified source, without import."""

    closure = execution_closure(source, frozen_owners, filename)
    tree = ast.parse(source)
    top_level = _top_level_functions(tree)
    class_nodes = {
        node.name: node for node in tree.body if isinstance(node, ast.ClassDef)
    }
    value_nodes = _module_level_value_nodes(tree)
    import_origins = _module_level_import_origins(tree)
    module_code = witness.compile_reviewed_source(
        source, CALENDAR_MODULE if filename is None else filename
    )
    by_qualname: dict[str, types.CodeType] = {}
    for code in witness._all_code_objects(module_code):
        by_qualname.setdefault(code.co_qualname, code)

    owners = expected_owner_identities(source, module_name, frozen_owners, filename)
    owner_names = {row.owner for row in owners}

    functions: list[OwnerIdentityExpectation] = []
    for name in closure.functions:
        if name in owner_names:
            continue
        functions.append(
            _function_expectation_from_code(
                name, name, module_name, by_qualname[name], top_level[name]
            )
        )

    classes: list[ClosureClassExpectation] = []
    for name in closure.classes:
        node = class_nodes[name]
        if node.decorator_list:
            decorators = tuple(ast.unparse(row) for row in node.decorator_list)
        else:
            decorators = ()
        certified: list[tuple[str, str, str]] = []
        for member in node.body:
            if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = f"{name}.{member.name}"
                code = by_qualname.get(qualname)
                if code is None:
                    raise RuntimeOwnerAttestationError(
                        f"closure class method {qualname!r} has no certified code object"
                    )
                certified.append(
                    (
                        member.name,
                        _certified_method_kind(member),
                        owner_code_fingerprint(code),
                    )
                )
        classes.append(
            ClosureClassExpectation(
                name=name,
                qualname=name,
                module=module_name,
                metaclass="builtins.type",
                bases=tuple(ast.unparse(base) for base in node.bases) + decorators,
                certified_method_fingerprints=tuple(sorted(certified)),
            )
        )

    values: list[ClosureValueExpectation] = []
    for name in closure.values:
        node_value = value_nodes.get(name)
        try:
            literal = ast.literal_eval(node_value) if node_value is not None else None
            statically_derived = node_value is not None
        except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
            literal = None
            statically_derived = False
        values.append(
            ClosureValueExpectation(
                name=name,
                fingerprint=(
                    deep_value_fingerprint(literal)
                    if statically_derived
                    else BASELINE_BOUND
                ),
                statically_derived=statically_derived,
            )
        )

    imports: list[ClosureImportExpectation] = []
    for name in closure.imports:
        origin_module, origin_attribute = import_origins[name]
        project = origin_module.split(".")[0] == PROJECT_PACKAGE_ROOT
        certified_module, certified_sha256 = (
            _certified_project_module(origin_module, origin_attribute)
            if project
            else ("", "")
        )
        defining_module = ""
        function_expectations: tuple[OwnerIdentityExpectation, ...] = ()
        if project:
            imports_a_module = certified_module != origin_module or not origin_attribute
            if imports_a_module:
                defining_module = certified_module
                function_expectations = _project_module_function_expectations(
                    certified_module
                )
            else:
                defining_module, defined_name = _resolve_project_definition(
                    origin_module, origin_attribute
                )
                function_expectations = _project_module_function_expectations(
                    defining_module, frozenset({defined_name})
                )
        imports.append(
            ClosureImportExpectation(
                name=name,
                origin_module=origin_module,
                origin_attribute=origin_attribute,
                ownership="PROJECT_OWNED" if project else "INTERPRETER_PROVIDED",
                certified_module=certified_module,
                source_sha256=certified_sha256,
                defining_module=defining_module,
                function_expectations=function_expectations,
            )
        )

    return ExecutionClosureExpectation(
        closure=closure,
        owners=owners,
        functions=tuple(sorted(functions)),
        classes=tuple(sorted(classes)),
        values=tuple(sorted(values)),
        imports=tuple(sorted(imports)),
    )


@dataclass(frozen=True, order=True)
class ClosureAttestation:
    """One measured closure member."""

    kind: str
    name: str
    conforms: bool
    reasons: tuple[str, ...]
    material: tuple[tuple[str, Any], ...]

    def as_material(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "conforms": self.conforms,
            "reasons": list(self.reasons),
            "attested": dict(self.material),
        }


def _attest_closure_class(
    module: types.ModuleType, expectation: ClosureClassExpectation
) -> ClosureAttestation:
    namespace = module.__dict__
    reasons: list[str] = []
    material: dict[str, Any] = {
        "binding_present": expectation.name in namespace,
        "metaclass": None,
        "qualname": None,
        "module": None,
        "mro": None,
        "certified_method_fingerprints": None,
        "uncertified_function_attributes": None,
        "method_wrapper_states": None,
    }
    if not material["binding_present"]:
        return ClosureAttestation(
            "CLOSURE_CLASS",
            expectation.name,
            False,
            ("CLOSURE_BINDING_ABSENT",),
            tuple(sorted(material.items())),
        )
    effective = namespace[expectation.name]
    material["metaclass"] = _callable_type_name(effective)
    if not isinstance(effective, type):
        return ClosureAttestation(
            "CLOSURE_CLASS",
            expectation.name,
            False,
            ("CLOSURE_CLASS_TYPE_MISMATCH",),
            tuple(sorted(material.items())),
        )
    material["qualname"] = effective.__qualname__
    material["module"] = effective.__module__
    material["mro"] = [f"{row.__module__}.{row.__qualname__}" for row in effective.__mro__]
    certified = {
        attribute: [kind, fingerprint]
        for attribute, kind, fingerprint in expectation.certified_method_fingerprints
    }
    measured: dict[str, list[str]] = {}
    uncertified: list[str] = []
    wrapper_states: dict[str, str] = {}
    for attribute, value in sorted(vars(effective).items()):
        resolved = _class_attribute_function(value)
        if resolved is None:
            continue
        kind, function = resolved
        wrapper_states[attribute] = _wrapper_state(function)
        try:
            fingerprint = owner_code_fingerprint(function.__code__)
        except RuntimeOwnerAttestationError:
            fingerprint = UNSTABLE_VALUE_FINGERPRINT
        if attribute in certified:
            measured[attribute] = [kind, fingerprint]
        else:
            uncertified.append(attribute)
    material["certified_method_fingerprints"] = dict(sorted(measured.items()))
    material["uncertified_function_attributes"] = sorted(uncertified)
    material["method_wrapper_states"] = dict(sorted(wrapper_states.items()))

    if material["metaclass"] != expectation.metaclass:
        reasons.append("CLOSURE_CLASS_TYPE_MISMATCH")
    if (
        material["qualname"] != expectation.qualname
        or material["module"] != expectation.module
    ):
        reasons.append("CLOSURE_CLASS_IDENTITY_MISMATCH")
    if measured != certified:
        reasons.append("CLOSURE_CLASS_CERTIFIED_METHOD_MISMATCH")
    drifted_wrappers = sorted(
        attribute
        for attribute, state in wrapper_states.items()
        if attribute in certified and state != FROZEN_WRAPPER_CONTRACT
    )
    if drifted_wrappers:
        reasons.append("CLOSURE_CLASS_METHOD_WRAPPER_STATE_MISMATCH")
    return ClosureAttestation(
        "CLOSURE_CLASS",
        expectation.name,
        not reasons,
        tuple(reasons),
        tuple(sorted(material.items())),
    )


def _attest_closure_value(
    module: types.ModuleType, expectation: ClosureValueExpectation
) -> ClosureAttestation:
    namespace = module.__dict__
    material: dict[str, Any] = {"binding_present": expectation.name in namespace}
    if not material["binding_present"]:
        material["fingerprint"] = None
        return ClosureAttestation(
            "CLOSURE_VALUE",
            expectation.name,
            False,
            ("CLOSURE_BINDING_ABSENT",),
            tuple(sorted(material.items())),
        )
    measured = deep_value_fingerprint(namespace[expectation.name])
    material["fingerprint"] = measured
    material["statically_derived"] = expectation.statically_derived
    reasons: list[str] = []
    if not expectation.statically_derived:
        reasons.append("CLOSURE_VALUE_NOT_STATICALLY_DERIVABLE")
    elif measured != expectation.fingerprint:
        reasons.append("CLOSURE_VALUE_FINGERPRINT_MISMATCH")
    return ClosureAttestation(
        "CLOSURE_VALUE",
        expectation.name,
        not reasons,
        tuple(reasons),
        tuple(sorted(material.items())),
    )


def _attest_closure_import(
    module: types.ModuleType, expectation: ClosureImportExpectation
) -> ClosureAttestation:
    namespace = module.__dict__
    reasons: list[str] = []
    material: dict[str, Any] = {
        "binding_present": expectation.name in namespace,
        "kind": None,
        "origin_module": expectation.origin_module,
        "origin_attribute": expectation.origin_attribute,
        "ownership": expectation.ownership,
        "bound_in_sys_modules": None,
        "resolves_to_the_origin_attribute": None,
        "source_sha256": None,
    }
    if not material["binding_present"]:
        return ClosureAttestation(
            "CLOSURE_IMPORT",
            expectation.name,
            False,
            ("CLOSURE_BINDING_ABSENT",),
            tuple(sorted(material.items())),
        )
    effective = namespace[expectation.name]
    origin = sys.modules.get(expectation.origin_module)
    if expectation.origin_attribute:
        material["kind"] = "IMPORTED_OBJECT"
        material["bound_in_sys_modules"] = origin is not None
        material["resolves_to_the_origin_attribute"] = (
            origin is not None
            and getattr(origin, expectation.origin_attribute, None) is effective
        )
        if origin is None:
            reasons.append("CLOSURE_IMPORT_NOT_BOUND_IN_SYS_MODULES")
        elif material["resolves_to_the_origin_attribute"] is not True:
            reasons.append("CLOSURE_IMPORT_OBJECT_IDENTITY_MISMATCH")
    else:
        material["kind"] = "IMPORTED_MODULE"
        if not isinstance(effective, types.ModuleType):
            reasons.append("CLOSURE_IMPORT_KIND_MISMATCH")
            return ClosureAttestation(
                "CLOSURE_IMPORT",
                expectation.name,
                False,
                tuple(reasons),
                tuple(sorted(material.items())),
            )
        material["bound_in_sys_modules"] = (
            sys.modules.get(effective.__name__) is effective
        )
        material["resolves_to_the_origin_attribute"] = (
            effective.__name__ == expectation.origin_module
        )
        if material["bound_in_sys_modules"] is not True:
            reasons.append("CLOSURE_IMPORT_NOT_BOUND_IN_SYS_MODULES")
        if material["resolves_to_the_origin_attribute"] is not True:
            reasons.append("CLOSURE_IMPORT_ORIGIN_MISMATCH")
    if expectation.ownership == "PROJECT_OWNED":
        target = sys.modules.get(expectation.certified_module)
        if target is None and isinstance(effective, types.ModuleType):
            target = effective
        module_file = getattr(target, "__file__", None)
        if module_file is None:
            reasons.append("CLOSURE_IMPORT_SOURCE_IDENTITY_MISMATCH")
        else:
            observed = source_sha256(
                Path(module_file).resolve().read_text(encoding="utf-8")
            )
            material["source_sha256"] = observed
            if observed != expectation.source_sha256:
                reasons.append("CLOSURE_IMPORT_SOURCE_IDENTITY_MISMATCH")
        defining = sys.modules.get(expectation.defining_module)
        function_material: dict[str, Any] = {}
        drifted: list[str] = []
        if expectation.function_expectations and defining is None:
            reasons.append("CLOSURE_IMPORT_NOT_BOUND_IN_SYS_MODULES")
        elif defining is not None:
            for function in expectation.function_expectations:
                conforms, function_reasons, _ = _attest_function_binding(
                    defining.__dict__, function.owner, function
                )
                function_material[function.owner] = list(function_reasons)
                if not conforms:
                    drifted.append(function.owner)
        material["project_function_reasons"] = dict(sorted(function_material.items()))
        material["project_function_count"] = len(expectation.function_expectations)
        if drifted:
            reasons.append("CLOSURE_IMPORT_PROJECT_FUNCTION_MISMATCH")
    return ClosureAttestation(
        "CLOSURE_IMPORT",
        expectation.name,
        not reasons,
        tuple(reasons),
        tuple(sorted(material.items())),
    )


def attest_execution_closure(
    module: types.ModuleType, expectation: ExecutionClosureExpectation
) -> tuple[ClosureAttestation, ...]:
    """Measure every reachable closure member effective in one loaded module."""

    rows: list[ClosureAttestation] = []
    for function in expectation.functions:
        conforms, reasons, material = _attest_function_binding(
            module.__dict__, function.owner, function
        )
        rows.append(
            ClosureAttestation(
                "CLOSURE_FUNCTION",
                function.owner,
                conforms,
                reasons,
                tuple(sorted(material.items())),
            )
        )
    for klass in expectation.classes:
        rows.append(_attest_closure_class(module, klass))
    for value in expectation.values:
        rows.append(_attest_closure_value(module, value))
    for imported in expectation.imports:
        rows.append(_attest_closure_import(module, imported))
    return tuple(sorted(rows))


@dataclass(frozen=True)
class RuntimeOwnerAttestation:
    """One complete measured attestation of the effective calendar surface."""

    decision_version: str
    module_name: str
    source_sha256: str
    interpreter_identity: tuple[tuple[str, Any], ...]
    namespace_reasons: tuple[str, ...]
    owners: tuple[OwnerAttestation, ...]
    closure: tuple[ClosureAttestation, ...] = ()
    closure_derivation: tuple[tuple[str, Any], ...] = ()

    @property
    def conforms(self) -> bool:
        return (
            not self.namespace_reasons
            and all(row.conforms for row in self.owners)
            and all(row.conforms for row in self.closure)
        )

    @property
    def reasons(self) -> tuple[str, ...]:
        rows = [
            f"{row.owner}:{reason}" for row in self.owners for reason in row.reasons
        ]
        rows.extend(
            f"{row.kind}:{row.name}:{reason}"
            for row in self.closure
            for reason in row.reasons
        )
        return tuple([*self.namespace_reasons, *rows])

    def as_material(self) -> dict[str, Any]:
        return {
            "decision_version": self.decision_version,
            "attestation_contract": RUNTIME_OWNER_ATTESTATION_FIELDS_MATERIAL,
            "closure_contract_version": CLOSURE_CONTRACT_VERSION,
            "module_name": self.module_name,
            "source_sha256": self.source_sha256,
            "interpreter_identity": dict(self.interpreter_identity),
            "namespace_reasons": list(self.namespace_reasons),
            "owner_count": len(self.owners),
            "owners": [row.as_material() for row in self.owners],
            "closure_member_count": len(self.closure),
            "closure_derivation": dict(self.closure_derivation),
            "closure": [row.as_material() for row in self.closure],
        }

    @property
    def digest(self) -> str:
        """Deterministic digest over stable reviewed execution identity only."""

        return _digest(self.as_material())


RUNTIME_OWNER_ATTESTATION_FIELDS_MATERIAL = list(RUNTIME_OWNER_ATTESTATION_FIELDS)


def _module_namespace_reasons(module: types.ModuleType) -> tuple[str, ...]:
    """Refuse every route by which the attested namespace could not be the live one."""

    reasons: list[str] = []
    if type(module) is not types.ModuleType:
        reasons.append("MODULE_IS_NOT_AN_EXACT_MODULE_OBJECT")
    if sys.modules.get(module.__name__) is not module:
        reasons.append("MODULE_NOT_BOUND_IN_SYS_MODULES")
    package, _, leaf = module.__name__.rpartition(".")
    if package:
        parent = sys.modules.get(package)
        if parent is not None and getattr(parent, leaf, module) is not module:
            reasons.append("MODULE_NOT_BOUND_AS_THE_PACKAGE_ATTRIBUTE")
    certified = CALENDAR_SOURCE.resolve()
    duplicates = sorted(
        name
        for name, loaded in list(sys.modules.items())
        if isinstance(loaded, types.ModuleType)
        and loaded is not module
        and getattr(loaded, "__file__", None) is not None
        and Path(loaded.__file__).resolve() == certified
    )
    if duplicates:
        reasons.append("DUPLICATE_CALENDAR_MODULE_INSTANCE")
    if _resolved_builtins(module.__dict__) is not builtins.__dict__:
        reasons.append("MODULE_NAMESPACE_BUILTINS_MISMATCH")
    return tuple(reasons)


def consumer_binding_divergence(
    module: types.ModuleType, frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS
) -> tuple[str, ...]:
    """Refuse a loaded consumer holding its own, different binding for an owner.

    ``from ... import owner`` copies the reference into the consumer namespace,
    so the attested definition site is not automatically the site a caller
    resolves through.
    """

    divergent: list[str] = []
    namespace = module.__dict__
    for name, loaded in sorted(
        (name, loaded)
        for name, loaded in list(sys.modules.items())
        if isinstance(loaded, types.ModuleType) and loaded is not module
    ):
        consumer = getattr(loaded, "__dict__", None)
        if not isinstance(consumer, dict):
            continue
        for owner in frozen_owners:
            if owner not in consumer or owner not in namespace:
                continue
            candidate = consumer[owner]
            if (
                getattr(candidate, "__module__", None) == module.__name__
                and candidate is not namespace[owner]
            ):
                divergent.append(f"{name}:{owner}")
    return tuple(sorted(divergent))


def attest_runtime_owners(
    module: types.ModuleType,
    expectations: Sequence[OwnerIdentityExpectation],
    source_sha256_value: str,
    closure_expectation: ExecutionClosureExpectation | None = None,
) -> RuntimeOwnerAttestation:
    """Measure the frozen owners, and the closure, effective in one loaded module."""

    identity = witness.verify_proof_interpreter_identity()
    namespace_reasons = list(_module_namespace_reasons(module))
    namespace_reasons.extend(
        f"CONSUMER_BINDING_DIVERGENCE:{row}"
        for row in consumer_binding_divergence(
            module, [row.owner for row in expectations]
        )
    )
    owners = tuple(
        sorted(attest_owner(module, expectation) for expectation in expectations)
    )
    closure: tuple[ClosureAttestation, ...] = ()
    derivation: dict[str, Any] = {}
    if closure_expectation is not None:
        closure = attest_execution_closure(module, closure_expectation)
        derivation = closure_expectation.closure.as_material()
    return RuntimeOwnerAttestation(
        decision_version=DECISION_VERSION,
        module_name=module.__name__,
        source_sha256=source_sha256_value,
        interpreter_identity=tuple(sorted(identity.items())),
        namespace_reasons=tuple(namespace_reasons),
        owners=owners,
        closure=closure,
        closure_derivation=tuple(sorted(derivation.items())),
    )


def verify_module_source_identity(
    module: types.ModuleType,
    source: str,
    expected_source_sha256: str | None = None,
) -> dict[str, Any]:
    """Bind the loaded module to the exact certified reviewed source file.

    When the reviewed parent artifact's recorded source digest is supplied, the
    chain stops being self-consistent: whatever happens to be on disk can no
    longer define both the expectation and the measurement.
    """

    module_file = getattr(module, "__file__", None)
    if module_file is None:
        raise RuntimeOwnerAttestationError(
            "attested module has no source file: MODULE_SOURCE_IDENTITY_MISMATCH"
        )
    resolved = Path(module_file).resolve()
    certified = CALENDAR_SOURCE.resolve()
    if resolved != certified:
        raise RuntimeOwnerAttestationError(
            "attested module is not the certified reviewed calendar source: "
            "MODULE_SOURCE_IDENTITY_MISMATCH"
        )
    spec = getattr(module, "__spec__", None)
    origin = getattr(spec, "origin", None)
    if origin is not None and Path(origin).resolve() != certified:
        raise RuntimeOwnerAttestationError(
            "attested module loader origin is not the certified reviewed source: "
            "MODULE_SOURCE_IDENTITY_MISMATCH"
        )
    observed = resolved.read_text(encoding="utf-8")
    digest = source_sha256(source)
    if source_sha256(observed) != digest:
        raise RuntimeOwnerAttestationError(
            "reviewed source identity drifted: MODULE_SOURCE_IDENTITY_MISMATCH"
        )
    if expected_source_sha256 is not None and digest != expected_source_sha256:
        raise RuntimeOwnerAttestationError(
            "reviewed source does not match the parent artifact's certified "
            "digest: MODULE_SOURCE_IDENTITY_MISMATCH"
        )
    return {
        "module_name": module.__name__,
        "source_path": str(resolved),
        "source_sha256": digest,
        "loader_origin_verified": origin is not None,
        "parent_artifact_digest_compared": expected_source_sha256 is not None,
    }


# ---------------------------------------------------------------------------
# Controlled scientific execution epoch
# ---------------------------------------------------------------------------

SCIENTIFIC_EXECUTION_EPOCH = "CALENDAR_SCIENTIFIC_EXECUTION_EPOCH"
EXECUTION_EPOCH_ORDER: tuple[str, ...] = (
    "ACQUIRE_SINGLE_CALENDAR_AUTHORITY_EXECUTION_EPOCH",
    "VERIFY_FROZEN_PROOF_INTERPRETER_IDENTITY",
    "VERIFY_REVIEWED_SOURCE_AND_MODULE_IDENTITY",
    "PRE_EXECUTION_OWNER_AND_CLOSURE_ATTESTATION",
    "REQUIRE_THE_PRE_ATTESTATION_TO_REPRODUCE_THE_STARTUP_BASELINE",
    "REFUSE_UNLESS_EVERY_OWNER_AND_CLOSURE_MEMBER_ATTESTS",
    "SYNCHRONOUS_SCIENTIFIC_COMPUTATION_IN_THE_ATTESTED_MODULE",
    "REFUSE_A_LAZY_OR_DEFERRED_RESULT",
    "POST_EXECUTION_OWNER_AND_CLOSURE_ATTESTATION",
    "REQUIRE_POST_ATTESTATION_EQUALS_PRE_ATTESTATION",
    "ADMIT_OR_PERSIST_THE_RESULT",
    "SWEEP_FOR_DRIFT_ON_EVERY_EXIT_PATH_INCLUDING_EXCEPTIONS",
    "RELEASE_THE_EXECUTION_EPOCH",
)

EXECUTION_SERIALIZATION = (
    "ONE_CALENDAR_SCIENTIFIC_EXECUTION_EPOCH_AT_A_TIME_PER_PROCESS"
)
NESTED_EPOCH_RULE = "REENTRANT_OR_NESTED_SCIENTIFIC_EXECUTION_EPOCH_REFUSES"

#: The operation must be pure with respect to durable state.  Everything that
#: admits, persists or publishes runs in ``admit``, which the executor calls
#: only after the post-execution attestation has reproduced the pre-execution
#: attestation, so no scientific evidence can be written and then discovered to
#: be unauthorised.
EPOCH_PERSISTENCE_ORDERING = (
    "THE_OPERATION_IS_PURE_WITH_RESPECT_TO_DURABLE_STATE_AND_ALL_ADMISSION_"
    "PERSISTENCE_AND_PUBLICATION_HAPPENS_IN_ADMIT_AFTER_POST_ATTESTATION"
)

#: A lazy result would run its body after the measured window closed.
EPOCH_RESULT_RULE = "THE_ADMITTED_RESULT_MUST_BE_FULLY_EVALUATED_INSIDE_THE_EPOCH"
LAZY_RESULT_REFUSAL = "EPOCH_RESULT_IS_NOT_EAGERLY_EVALUATED"
POST_EPOCH_DRIFT_REFUSAL = "SCIENTIFIC_EXECUTION_EPOCH_DRIFT_DETECTED_ON_EXIT"

_EPOCH_SERIALIZATION_LOCK = threading.Lock()
_EPOCH_STATE = threading.local()

ATTESTATION_EVIDENCE_FIELDS: tuple[str, ...] = (
    "execution_epoch_id",
    "calendar_authority_sha256",
    "proof_architecture_sha256",
    "reviewed_source_sha256",
    "proof_interpreter_identity",
    "module_identity",
    "pre_owner_attestation_digest",
    "post_owner_attestation_digest",
    "attestation_match",
    "result_admitted",
    "failure_reason",
    "decision_time",
)

FORBIDDEN_ATTESTATION_EVIDENCE_MATERIAL: tuple[str, ...] = (
    "OBJECT_ID",
    "MEMORY_ADDRESS",
    "REPR_CONTAINING_AN_ADDRESS",
    "PROCESS_RANDOMIZED_OBJECT_REPRESENTATION",
)

_EAGER_RESULT_EXEMPT_TYPES: tuple[type, ...] = (
    str,
    bytes,
    bytearray,
    dict,
    list,
    tuple,
    set,
    frozenset,
)


def lazy_result_kind(result: Any) -> str | None:
    """Name the deferred-evaluation kind of a result, or ``None`` when eager.

    A generator, coroutine or lazy iterator returned from the operation would
    execute its body after the measured window closed, reading whatever bindings
    existed at consumption time.
    """

    if isinstance(
        result,
        (types.GeneratorType, types.CoroutineType, types.AsyncGeneratorType),
    ):
        return f"{type(result).__module__}.{type(result).__qualname__}"
    if isinstance(result, _EAGER_RESULT_EXEMPT_TYPES):
        return None
    if hasattr(type(result), "__next__") or hasattr(type(result), "__await__"):
        return f"{type(result).__module__}.{type(result).__qualname__}"
    return None


@dataclass(frozen=True)
class ScientificExecutionEpoch:
    """One bounded, attested calendar/replay execution unit."""

    epoch_id: str
    module: types.ModuleType
    expectations: tuple[OwnerIdentityExpectation, ...]
    source: str
    calendar_authority_sha256: str
    proof_architecture_sha256: str
    decision_time: str
    closure_expectation: ExecutionClosureExpectation | None = None
    baseline_digest: str | None = None
    expected_source_sha256: str | None = None


@dataclass(frozen=True)
class EpochOutcome:
    """The admitted outcome of one attested scientific execution epoch."""

    epoch_id: str
    admitted: bool
    result: Any
    pre_attestation_digest: str
    post_attestation_digest: str
    attestation_match: bool
    evidence: Mapping[str, Any]


def _epoch_attestation(epoch: ScientificExecutionEpoch) -> RuntimeOwnerAttestation:
    return attest_runtime_owners(
        epoch.module,
        epoch.expectations,
        source_sha256(epoch.source),
        epoch.closure_expectation,
    )


def _epoch_evidence(
    epoch: ScientificExecutionEpoch,
    module_identity: Mapping[str, Any],
    pre_digest: str | None,
    post_digest: str | None,
    attestation_match: bool,
    result_admitted: bool,
    failure_reason: str | None,
) -> dict[str, Any]:
    return {
        "execution_epoch_id": epoch.epoch_id,
        "calendar_authority_sha256": epoch.calendar_authority_sha256,
        "proof_architecture_sha256": epoch.proof_architecture_sha256,
        "reviewed_source_sha256": source_sha256(epoch.source),
        "proof_interpreter_identity": dict(PROOF_INTERPRETER_IDENTITY),
        "module_identity": dict(module_identity),
        "pre_owner_attestation_digest": pre_digest,
        "post_owner_attestation_digest": post_digest,
        "attestation_match": attestation_match,
        "result_admitted": result_admitted,
        "failure_reason": failure_reason,
        "decision_time": epoch.decision_time,
    }


def run_scientific_execution_epoch(
    epoch: ScientificExecutionEpoch,
    operation: Callable[[types.ModuleType], Any],
    admit: Callable[[Any], Any] | None = None,
) -> EpochOutcome:
    """Run one authoritative calendar computation inside a bounded epoch.

    Pre-attestation authorises the call, the computation runs synchronously in
    the very module whose bindings were attested, post-attestation re-measures
    the same material, and only a post-attestation that reproduces the
    pre-attestation digest may admit or persist the result.  Every exit path,
    including an exception raised by the operation, sweeps for drift so a
    failing epoch can never leave a persistent substitution unrecorded.
    """

    if getattr(_EPOCH_STATE, "active", False):
        raise RuntimeOwnerAttestationError(
            f"{NESTED_EPOCH_RULE}: {SCIENTIFIC_EXECUTION_NOT_AUTHORIZED}"
        )
    with _EPOCH_SERIALIZATION_LOCK:
        _EPOCH_STATE.active = True
        pre: RuntimeOwnerAttestation | None = None
        settled = False
        module_identity: dict[str, Any] = {}
        try:
            witness.verify_proof_interpreter_identity()
            module_identity = verify_module_source_identity(
                epoch.module, epoch.source, epoch.expected_source_sha256
            )
            pre = _epoch_attestation(epoch)
            if not pre.conforms or (
                epoch.baseline_digest is not None
                and pre.digest != epoch.baseline_digest
            ):
                settled = True
                evidence = _epoch_evidence(
                    epoch,
                    module_identity,
                    pre.digest,
                    None,
                    False,
                    False,
                    f"{SCIENTIFIC_EXECUTION_NOT_AUTHORIZED}:{','.join(pre.reasons)}",
                )
                raise RuntimeOwnerAttestationError(
                    "pre-execution attestation refused: "
                    f"{SCIENTIFIC_EXECUTION_NOT_AUTHORIZED}: {pre.reasons!r}",
                    evidence,
                )
            result = operation(epoch.module)
            deferred = lazy_result_kind(result)
            post = _epoch_attestation(epoch)
            if deferred is not None or post.digest != pre.digest:
                settled = True
                evidence = _epoch_evidence(
                    epoch,
                    module_identity,
                    pre.digest,
                    post.digest,
                    post.digest == pre.digest,
                    False,
                    f"{RESULT_REJECTED}:{DATA_QUALITY_FAIL}:"
                    + (
                        f"{LAZY_RESULT_REFUSAL}:{deferred}"
                        if deferred is not None
                        else ",".join(post.reasons)
                    ),
                )
                raise RuntimeOwnerAttestationError(
                    "the epoch refused its result before admission: "
                    f"{RESULT_REJECTED}: {DATA_QUALITY_FAIL}: "
                    + (
                        f"{LAZY_RESULT_REFUSAL}: {deferred}"
                        if deferred is not None
                        else repr(post.reasons)
                    ),
                    evidence,
                )
            admitted = result if admit is None else admit(result)
            settled = True
            evidence = _epoch_evidence(
                epoch, module_identity, pre.digest, post.digest, True, True, None
            )
            return EpochOutcome(
                epoch_id=epoch.epoch_id,
                admitted=True,
                result=admitted,
                pre_attestation_digest=pre.digest,
                post_attestation_digest=post.digest,
                attestation_match=True,
                evidence=evidence,
            )
        finally:
            _EPOCH_STATE.active = False
            if pre is not None and not settled:
                sweep = _epoch_attestation(epoch)
                if sweep.digest != pre.digest:
                    raise RuntimeOwnerAttestationError(
                        "the failing epoch left persistent owner drift: "
                        f"{POST_EPOCH_DRIFT_REFUSAL}: {sweep.reasons!r}",
                        _epoch_evidence(
                            epoch,
                            module_identity,
                            pre.digest,
                            sweep.digest,
                            False,
                            False,
                            f"{POST_EPOCH_DRIFT_REFUSAL}:{','.join(sweep.reasons)}",
                        ),
                    )


def verify_result_admission_ordering() -> dict[str, Any]:
    """Mechanically prove post-attestation strictly precedes result admission.

    The proof is structural, over this module's own reviewed source: the epoch
    executor performs exactly two attestations on the admitting path and exactly
    one drift sweep on the exception path, the operation runs strictly between
    the two, and the admission call is unreachable unless the post-attestation
    refusal did not fire.
    """

    source = Path(__file__).resolve().read_text(encoding="utf-8")
    tree = ast.parse(source)
    executor = next(
        (
            node
            for node in tree.body
            if isinstance(node, ast.FunctionDef)
            and node.name == "run_scientific_execution_epoch"
        ),
        None,
    )
    if executor is None:
        raise RuntimeOwnerAttestationError("epoch executor is absent")
    try_node = next(
        (node for node in ast.walk(executor) if isinstance(node, ast.Try)), None
    )
    if try_node is None or not try_node.finalbody:
        raise RuntimeOwnerAttestationError(
            "the epoch executor does not sweep for drift on every exit path"
        )
    final_lines = {
        node.lineno
        for statement in try_node.finalbody
        for node in ast.walk(statement)
        if hasattr(node, "lineno")
    }

    def _calls(name: str) -> tuple[list[int], list[int]]:
        body: list[int] = []
        final: list[int] = []
        for node in ast.walk(executor):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == name
            ):
                (final if node.lineno in final_lines else body).append(node.lineno)
        return sorted(body), sorted(final)

    attestations, sweeps = _calls("_epoch_attestation")
    operations, _ = _calls("operation")
    lazy_guards, _ = _calls("lazy_result_kind")
    admissions, _ = _calls("admit")
    if len(attestations) != 2 or len(sweeps) != 1:
        raise RuntimeOwnerAttestationError(
            "the epoch executor does not perform exactly two attestations and one "
            "exception-path drift sweep"
        )
    if len(operations) != 1 or len(admissions) != 1 or len(lazy_guards) != 1:
        raise RuntimeOwnerAttestationError(
            "the epoch executor does not have exactly one operation, one lazy-result "
            "guard and one admission"
        )
    pre_line, post_line = attestations
    operation_line = operations[0]
    admit_line = admissions[0]
    refusals = sorted(
        node.lineno
        for node in ast.walk(executor)
        if isinstance(node, ast.Raise)
        and post_line < node.lineno < admit_line
        and node.lineno not in final_lines
    )
    if not (pre_line < operation_line < post_line < admit_line):
        raise RuntimeOwnerAttestationError(
            "result admission does not strictly follow post-execution attestation"
        )
    if not refusals:
        raise RuntimeOwnerAttestationError(
            "post-execution mismatch does not refuse before result admission"
        )
    return {
        "pre_attestation_line": pre_line,
        "operation_line": operation_line,
        "lazy_result_guard_line": lazy_guards[0],
        "post_attestation_line": post_line,
        "mismatch_refusal_line": refusals[0],
        "admission_line": admit_line,
        "exception_path_drift_sweep_line": sweeps[0],
        "post_attestation_precedes_admission": True,
        "exception_path_sweeps_for_drift": True,
        "persist_then_discover_mismatch": False,
    }


# ---------------------------------------------------------------------------
# Startup attestation
# ---------------------------------------------------------------------------

STARTUP_ATTESTATION_CHECKS: tuple[str, ...] = (
    "CERTIFIED_PROOF_ARCHITECTURE_AUTHORITY",
    "CERTIFIED_TRUSTED_PERSISTENCE_DEPENDENCY",
    "FROZEN_PROOF_INTERPRETER_IDENTITY",
    "REVIEWED_PRODUCTION_SOURCE_IDENTITY",
    "CERTIFIED_SOURCE_CLOSURE_IDENTITY",
    "ELEVEN_EFFECTIVE_RUNTIME_OWNER_BINDINGS",
    "TRANSITIVE_EXECUTION_CLOSURE_BINDINGS",
    "DIRECT_DEPENDENCY_BODY_AUTHORITY",
)

#: Import-time behaviour is fully determined by the certified sources, whose
#: exact digests are attested, and every post-startup mutation is measured
#: against the startup baseline.  The residual window is the interval between
#: the end of import and the startup attestation, which is closed by running
#: the startup attestation as the process's first action.
STARTUP_ORDERING_RULE = (
    "STARTUP_ATTESTATION_RUNS_AS_THE_FIRST_ACTION_AFTER_IMPORT_AND_BEFORE_ANY_"
    "SCIENTIFIC_EXECUTION_EPOCH"
)


def direct_dependency_body_findings(source: str) -> dict[str, Any]:
    """Report which required bodies execute the exact dependency assertion.

    Current production installs wrapper guards instead, so this reports findings
    rather than refusing; the strict audit below is the rule the final calendar
    implementation must satisfy.
    """

    tree = ast.parse(source)
    required = _bodies._required_body_nodes(tree)
    missing_bodies = sorted(set(REQUIRED_DIRECT_BODIES) - set(required))
    decorated: list[str] = []
    without_direct_call: list[str] = []
    for name, node in sorted(required.items()):
        if node.decorator_list:
            decorated.append(name)
        if "assert_trusted_persistence_dependency" not in _bodies._direct_calls_in_body(
            node
        ):
            without_direct_call.append(name)
    return {
        "required_direct_bodies": list(REQUIRED_DIRECT_BODIES),
        "bodies_present": sorted(required),
        "bodies_absent": missing_bodies,
        "decorated_bodies": decorated,
        "bodies_without_the_direct_dependency_assertion": without_direct_call,
        "conforms": not (missing_bodies or decorated or without_direct_call),
    }


def audit_direct_dependency_bodies(source: str) -> tuple[str, ...]:
    """Every required body must execute the exact dependency assertion itself."""

    findings = direct_dependency_body_findings(source)
    if findings["bodies_absent"]:
        raise RuntimeOwnerAttestationError(
            "required authoritative direct body is missing: "
            f"{findings['bodies_absent']!r}"
        )
    if findings["decorated_bodies"]:
        raise RuntimeOwnerAttestationError(
            f"runtime decorator/wrapper forbidden on {findings['decorated_bodies']!r}"
        )
    if findings["bodies_without_the_direct_dependency_assertion"]:
        raise RuntimeOwnerAttestationError(
            "exact dependency ast.Call missing from "
            f"{findings['bodies_without_the_direct_dependency_assertion']!r}"
        )
    return tuple(findings["bodies_present"])


def attest_scientific_process_startup(
    module: types.ModuleType,
    *,
    proof_architecture_sha256: str,
    trusted_persistence_sha256: str = CERTIFIED_DEPENDENCY_SHA256,
    source: str | None = None,
    expected_source_sha256: str | None = None,
) -> dict[str, Any]:
    """Refuse scientific readiness before the process may run any epoch.

    Startup attestation never replaces per-epoch pre/post attestation: it only
    refuses a process that is already wrong before the first epoch begins.
    """

    reviewed = CALENDAR_SOURCE.read_text(encoding="utf-8") if source is None else source
    identity = witness.verify_proof_interpreter_identity()
    if proof_architecture_sha256 != runtime_owner_attestation_v1_definition()[
        "definition_sha256"
    ]:
        raise RuntimeOwnerAttestationError(
            "startup proof-architecture authority mismatch: "
            f"{SCIENTIFIC_EXECUTION_NOT_AUTHORIZED}"
        )
    if trusted_persistence_sha256 != CERTIFIED_DEPENDENCY_SHA256:
        raise RuntimeOwnerAttestationError(
            "startup trusted-persistence dependency mismatch: "
            f"{SCIENTIFIC_EXECUTION_NOT_AUTHORIZED}"
        )
    module_identity = verify_module_source_identity(
        module, reviewed, expected_source_sha256
    )
    bodies = audit_direct_dependency_bodies(reviewed)
    expectations = expected_owner_identities(reviewed, module.__name__)
    closure = expected_execution_closure(reviewed, module.__name__)
    attestation = attest_runtime_owners(
        module, expectations, source_sha256(reviewed), closure
    )
    if not attestation.conforms:
        raise RuntimeOwnerAttestationError(
            "startup attestation refused: "
            f"{SCIENTIFIC_EXECUTION_NOT_AUTHORIZED}: {attestation.reasons!r}"
        )
    return {
        "checks": list(STARTUP_ATTESTATION_CHECKS),
        "startup_ordering_rule": STARTUP_ORDERING_RULE,
        "interpreter_identity": identity,
        "module_identity": module_identity,
        "direct_dependency_bodies": list(bodies),
        "owner_count": len(attestation.owners),
        "closure_member_count": len(attestation.closure),
        "closure_expectation_digest": closure.digest,
        "startup_baseline_digest": attestation.digest,
        "startup_replaces_per_epoch_attestation": False,
    }


# ---------------------------------------------------------------------------
# Static layers retained from the coherent compiled binding-witness design
# ---------------------------------------------------------------------------

REUSED_COMPILED_WITNESS_MECHANISM = witness.DECISION_VERSION

PROOF_ORDER: tuple[str, ...] = (
    "VERIFY_FROZEN_CPYTHON_COMPILER_IDENTITY",
    "COMPILE_REVIEWED_SOURCE_WITHOUT_EXECUTION",
    "IDENTIFY_EXACT_TOP_LEVEL_REPLAY_OWNER_CODE_OBJECTS",
    "DISCOVER_ORDINARY_EXPLICITLY_ANNOTATED_STORE_ROOTS",
    "RUN_COMPILED_ROOT_BINDING_WITNESS_FOR_EVERY_ROOT",
    "REJECT_ANY_ROOT_WRITE_CLEAR_OR_DELETE",
    "REJECT_ANY_ROOT_CELL_VARIABLE",
    "RUN_CLOSED_AST_STORE_USE_GRAMMAR",
    "REJECT_NESTED_ANNOTATED_OWNERS_AND_CAPABILITY_ESCAPES",
    "RECONCILE_EXACT_ELEVEN_OWNER_CENSUS",
    "EXTRACT_DIRECT_API_AND_ENUMERATED_OWNER_EDGES",
    "REJECT_OWNER_CYCLES",
    "PROVE_EVERY_OWNER_PATH_TERMINATES_AT_DOCUMENTED_STORE_API",
    "VERIFY_DIRECT_DEPENDENCY_BODY_AUTHORITY",
    "DERIVE_FROZEN_RUNTIME_OWNER_IDENTITY_EXPECTATIONS",
    "RUN_STARTUP_OWNER_ATTESTATION",
    "RUN_PER_EPOCH_PRE_EXECUTION_OWNER_ATTESTATION",
    "EXECUTE_THE_ATTESTED_SCIENTIFIC_OPERATION",
    "RUN_PER_EPOCH_POST_EXECUTION_OWNER_ATTESTATION",
    "ADMIT_THE_RESULT_ONLY_AFTER_BOTH_ATTESTATIONS_AGREE",
)


def compiled_root_binding_witness(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
    filename: str | None = None,
) -> witness.CompiledBindingWitness:
    """The re-adopted compiled root-binding witness, freshly parent-bound."""

    return witness.compiled_binding_witness(source, frozen_owners, filename)


def root_binding_findings(
    source: str,
    frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS,
    filename: str | None = None,
) -> dict[str, Any]:
    """Compiled root-binding result with the demoted module-identity layer split out."""

    produced = compiled_root_binding_witness(source, frozen_owners, filename)
    witness.verify_witness_binds_source(produced, source)
    return {
        "source_sha256": produced.source_sha256,
        "owners": [row.owner for row in produced.owners],
        "root_rebinding_findings": [
            f"{row.owner}:{row.scope}:{row.root}:{row.opname}:{row.kind}"
            for row in produced.root_rebinding_findings
        ],
        "root_cell_findings": [
            f"{row.owner}:{row.root}" for row in produced.root_capture_findings
        ],
        "demoted_static_module_identity_findings": [
            f"{row.scope}:{row.root}" for row in produced.module_identity_findings
        ],
    }


# ---------------------------------------------------------------------------
# Demoted static reflection policy and module-namespace reach classification
# ---------------------------------------------------------------------------

STATIC_REFLECTION_POLICY_ROLE: tuple[str, ...] = (
    "DIAGNOSTIC",
    "DEFENCE_IN_DEPTH",
    "CODING_POLICY_ENFORCEMENT",
)

KNOWN_PRODUCTION_BLOCKER_OWNER = witness.KNOWN_PRODUCTION_BLOCKER_OWNER
KNOWN_PRODUCTION_BLOCKER_ROOT = witness.KNOWN_PRODUCTION_BLOCKER_ROOT

#: The wrapper installer is already forbidden by the certified direct-body
#: architecture and must be removed by the calendar implementation ticket.  The
#: other four reach the module namespace only to look an artifact builder up by
#: name, and no runtime owner attestation requires them to change.
WRAPPER_INSTALLER_SITE = "_install_exact_dependency_guards"
ARTIFACT_BUILDER_DISPATCH_SITES: tuple[str, ...] = (
    "_children",
    "_semantic_ast_sha256",
    "restore_artifacts",
    "write_artifacts",
)
MODULE_NAMESPACE_REACH_SITES: tuple[str, ...] = tuple(
    sorted((WRAPPER_INSTALLER_SITE, *ARTIFACT_BUILDER_DISPATCH_SITES))
)


def _enclosing_function_names(tree: ast.Module) -> dict[ast.AST, str]:
    scopes: dict[ast.AST, str] = {}

    def walk(node: ast.AST, scope: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                scopes[child] = child.name
                walk(child, child.name)
            elif isinstance(child, ast.ClassDef):
                walk(child, scope)
            else:
                scopes[child] = scope
                walk(child, scope)

    walk(tree, "<module>")
    return scopes


def _namespace_reach_operations(
    tree: ast.Module,
) -> tuple[dict[str, Any], ...]:
    """Classify every ``globals()`` reach in the reviewed source mechanically."""

    scopes = _enclosing_function_names(tree)
    parents: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[child] = node
    operations: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        if not (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "globals"
        ):
            continue
        scope = scopes.get(node, "<module>")
        parent = parents.get(node)
        operation = "UNKNOWN_NAMESPACE_REACH"
        written_keys: list[str] = []
        if isinstance(parent, ast.Subscript):
            grandparent = parents.get(parent)
            if isinstance(grandparent, ast.Assign) and any(
                target is parent for target in grandparent.targets
            ):
                operation = "NAMESPACE_WRITE"
                if isinstance(parent.slice, ast.Constant) and isinstance(
                    parent.slice.value, str
                ):
                    written_keys.append(parent.slice.value)
                else:
                    operation = "UNKNOWN_NAMESPACE_WRITE"
            elif isinstance(grandparent, (ast.Delete, ast.AugAssign)):
                operation = "UNKNOWN_NAMESPACE_WRITE"
            else:
                operation = "NAMESPACE_READ_DISPATCH"
        elif isinstance(parent, ast.Attribute):
            operation = (
                "NAMESPACE_READ_DISPATCH"
                if parent.attr == "get"
                else "UNKNOWN_NAMESPACE_REACH"
            )
        operations.append(
            {
                "scope": scope,
                "operation": operation,
                "written_keys": sorted(written_keys),
            }
        )
    return tuple(
        sorted(operations, key=lambda row: (row["scope"], row["operation"]))
    )


def classify_module_namespace_reach_sites(
    source: str, frozen_owners: Sequence[str] = FROZEN_REPLAY_OWNERS
) -> dict[str, Any]:
    """Establish independently whether a reach site can replace a frozen owner.

    A read-only dispatch lookup cannot change any effective owner binding, so it
    is not required to change by this decision.  Only a namespace *write* can,
    and only when the written key is a frozen replay owner.
    """

    tree = ast.parse(source)
    operations = _namespace_reach_operations(tree)
    scopes = sorted({row["scope"] for row in operations})
    writes = tuple(row for row in operations if row["operation"] != "NAMESPACE_READ_DISPATCH")
    unknown = tuple(row for row in operations if row["operation"].startswith("UNKNOWN"))
    owner_writes = sorted(
        {
            key
            for row in writes
            for key in row["written_keys"]
            if key in set(frozen_owners)
        }
    )
    return {
        "reach_scopes": scopes,
        "reach_site_count": len(operations),
        "operations": [dict(row) for row in operations],
        "namespace_write_scopes": sorted({row["scope"] for row in writes}),
        "unclassified_reach_scopes": sorted({row["scope"] for row in unknown}),
        "written_keys": sorted({key for row in writes for key in row["written_keys"]}),
        "frozen_owner_bindings_written": owner_writes,
        "artifact_builder_dispatch_scopes": sorted(
            {
                row["scope"]
                for row in operations
                if row["operation"] == "NAMESPACE_READ_DISPATCH"
            }
        ),
        "rewrite_required_solely_by_owner_identity": sorted(
            {
                row["scope"]
                for row in operations
                if row["operation"].startswith("UNKNOWN")
                or any(key in set(frozen_owners) for key in row["written_keys"])
            }
        ),
    }


# ---------------------------------------------------------------------------
# Material children
# ---------------------------------------------------------------------------


def trusted_process_boundary_reference() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_TRUSTED_PROCESS_BOUNDARY_REFERENCE_V1_PAD3",
            "production_python_process_trusted": True,
            "hostile_same_process_mutation_resistance_required": False,
            "project_owned_scientific_bypasses_in_scope": True,
            "arbitrary_hostile_in_process_manipulation_in_scope": False,
            "arbitrary_debugger_memory_or_interpreter_mutation_in_scope": False,
            "hostile_same_process_resistance_if_later_required": "PROCESS_ISOLATION",
            "wrapper_metaclass_or_source_hash_substitutes_for_isolation": False,
            "arbitrary_dynamic_python_mutation_proved": False,
            "threat_model_changed_by_this_decision": False,
            "transient_mutate_and_restore_resistance_claimed": False,
            "transient_mutate_and_restore_classification": (
                "ARBITRARY_ADVERSARIAL_SAME_PROCESS_MUTATION_OUTSIDE_ACCEPTED_TRUST_MODEL"
            ),
            "transient_mutate_and_restore_limitation_is_explicit": True,
            "escalation_path_is_more_python_reflection_filters": False,
            "failed_boundary_lineage": list(FAILED_ARCHITECTURE_LINEAGE),
        }
    )


def proof_interpreter_identity() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PROOF_INTERPRETER_IDENTITY_V1_PAD3",
            "frozen_identity": dict(PROOF_INTERPRETER_IDENTITY),
            "identity_fields": sorted(PROOF_INTERPRETER_IDENTITY),
            "compiler_identity_is_scientific_proof_material": True,
            "runtime_or_compiler_identity_mismatch": "REFUSE_SCIENTIFIC_AUTHORITY",
            "different_python_compiler_may_reuse_this_authority": False,
            "future_python_upgrade": "REQUIRES_EXPLICIT_REVIEW_AND_REFREEZE",
            "cached_pyc_is_scientific_authority": False,
            "runtime_attestation_recompiles_the_certified_source_independently": True,
            "compile_settings": {
                "mode": witness.COMPILE_MODE,
                "flags": witness.COMPILE_FLAGS,
                "dont_inherit": witness.COMPILE_DONT_INHERIT,
                "optimize": witness.COMPILE_OPTIMIZE,
                "executes_reviewed_source": False,
                "imports_reviewed_source": False,
                "performs_https_signing_persistence_or_collection": False,
            },
        }
    )


def compiled_root_binding_witness_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_COMPILED_ROOT_BINDING_WITNESS_RULE_V1_PAD3",
            "reused_mechanism": REUSED_COMPILED_WITNESS_MECHANISM,
            "reused_mechanism_parent_certified_by_this_decision": False,
            "failed_reused_mechanism_parent_sha256": FAILED_PARENT_SHA256,
            "readopted_layers": [
                "FROZEN_CPYTHON_3_12_14_IDENTITY",
                "EXACT_ROOT_BINDING_OPCODE_POLICY",
                "DEOPTIMIZED_INSTRUCTION_SCAN",
                "TYPEALIAS_AND_DEFINITION_TIME_MUTATION_DETECTION",
                "EXACT_OWNER_CODE_OBJECT_IDENTIFICATION",
                "NESTED_BODY_SCOPING_CORRECTNESS",
                "ROOT_CELL_PROHIBITION",
            ],
            "proves": (
                "THE_FROZEN_ANNOTATED_STORE_ROOT_IS_NOT_REBOUND_CLEARED_OR_DELETED_BY_"
                "EXECUTABLE_CODE_IN_THE_OWNING_COMPILED_SCOPE_OF_THE_CERTIFIED_SOURCE"
            ),
            "proves_which_callable_the_owner_name_denotes_at_runtime": False,
            "root_write_opcodes": list(witness._opcodes_of_class("ROOT_WRITE")),
            "root_delete_opcodes": list(witness._opcodes_of_class("ROOT_DELETE")),
            "root_clear_opcodes": list(witness._opcodes_of_class("ROOT_CLEAR")),
            "frozen_opcode_numbers": dict(sorted(witness.FROZEN_OPCODE_NUMBERS.items())),
            "reserved_unnamed_name_group_opcodes": list(
                witness.FROZEN_UNNAMED_NAME_GROUP_OPCODES
            ),
            "opcode_policy_integrity_checked_against_interpreter_table": True,
            "instruction_scan_deoptimizes_specialized_instructions": True,
            "root_may_be_a_cell_variable_of_the_owner": False,
            "root_cell_prohibition_is_structural": True,
            "class_body_store_name_is_an_owner_root_write": False,
            "nested_body_local_assignment_is_an_outer_root_write": False,
            "detached_witness_may_certify_another_source": False,
            "compiled_witness_precedes_graph_authority": True,
            "ast_and_compiled_disagreement": "FAIL_CLOSED_NEVER_PERMISSIVE",
        }
    )


def store_root_and_direct_use_grammar() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_STORE_ROOT_AND_DIRECT_USE_GRAMMAR_V1_PAD3",
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
            "nested_store_capture_permitted": False,
            "bound_method_store_extraction_permitted": False,
            "unknown_store_forwarding_permitted": False,
            "capability_escape_permitted": False,
            "private_authoritative_state_access_permitted": False,
            "implementation_private_authoritative_state": ["_records", "_envelopes"],
            "permitted_categories": [
                "PERMITTED_DIRECT_STORE_API_CALL",
                "PERMITTED_ENUMERATED_OWNER_FORWARD",
            ],
            "direct_call_ast_shape": (
                "ast.Call(func=ast.Attribute(value=EXACT_IMMUTABLE_ROOT, attr=DOCUMENTED_API))"
            ),
            "documented_apis": list(STORE_APIS),
            "forward_target": "EXACT_FROZEN_REPLAY_OWNER_REGISTRY",
            "other_roots_or_derivations": "FAIL_UNTIL_EXPLICIT_REVIEWED_AUTHORITY_CHANGE",
        }
    )


def runtime_owner_identity_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_RUNTIME_OWNER_IDENTITY_CONTRACT_V1_PAD3",
            "replaces": "STATIC_COMPLETE_MODULE_OWNER_IDENTITY_PROOF",
            "replacement": "CONTROLLED_RUNTIME_OWNER_ATTESTATION",
            "module_or_function_reflection_syntax_statically_enumerated_as_completeness_proof": False,
            "effective_binding_source": "LOADED_CALENDAR_MODULE___dict___OWNER_NAME",
            "owners": list(FROZEN_REPLAY_OWNERS),
            "owner_count": len(FROZEN_REPLAY_OWNERS),
            "attested_fields": list(RUNTIME_OWNER_ATTESTATION_FIELDS),
            "refusal_codes": list(RUNTIME_OWNER_REFUSAL_CODES),
            "namespace_refusal_codes": list(MODULE_NAMESPACE_REFUSAL_CODES),
            "binding_must_exist": True,
            "exact_supported_callable_type": FROZEN_CALLABLE_TYPE,
            "callable_subclass_or_duck_typed_callable_accepted": False,
            "name_qualname_module_exact": True,
            "code_execution_fingerprint_exact": True,
            "code_object_identity_comparison_is_the_rule": False,
            "code_object_identity_comparison_rejected_reason": (
                "INDEPENDENTLY_COMPILED_EQUIVALENT_CODE_OBJECTS_ARE_NOT_THE_SAME_OBJECT"
            ),
            "globals_must_be_the_attested_module_namespace": True,
            "globals_identity_rule": "EFFECTIVE_OWNER___globals___IS_REVIEWED_MODULE___dict__",
            "same_code_foreign_globals_accepted": False,
            "closure_contract": FROZEN_CLOSURE_CONTRACT,
            "defaults_attested": True,
            "kwdefaults_attested": True,
            "defaults_attested_only_when_code_changes": False,
            "wrapper_state_contract": FROZEN_WRAPPER_CONTRACT,
            "wrapped_attribute_permitted": False,
            "wrapper_callable_permitted": False,
            "callable_object_substitution_permitted": False,
            "bound_method_substitution_permitted": False,
            "partial_substitution_permitted": False,
            "behavioural_equivalence_is_identity_authority": False,
            "owner_hot_reload_supported": False,
            "owner_monkeypatch_supported_as_a_feature": False,
            "dynamic_owner_replacement_supported": False,
            "reviewed_code_update_procedure": "VERSION_REFREEZE_AND_DEPLOYMENT",
            "source_authority_chain": [
                "CERTIFIED_REVIEWED_SOURCE_SHA256",
                "EXACT_FROZEN_PROOF_INTERPRETER",
                "INDEPENDENTLY_COMPILED_EXPECTED_OWNER_CODE_FINGERPRINTS",
                "EFFECTIVE_RUNTIME_OWNER_BINDINGS",
                "EXECUTION_EPOCH_ATTESTATION",
            ],
            "another_source_may_reuse_this_attestation_authority": False,
            "ambient_decimal_context_or_caller_state_affects_attestation_material": False,
            "mutation_syntax_must_be_recognized_for_detection": False,
            "builtins_namespace_attested": True,
            "attested_binding_is_only_the_entry_point": False,
            "transitive_execution_closure_attested": True,
            "module_route_identity_attested": [
                "EXACT_MODULE_OBJECT_TYPE",
                "SYS_MODULES_ENTRY",
                "PACKAGE_ATTRIBUTE",
                "NO_DUPLICATE_LOADED_INSTANCE_OF_THE_CERTIFIED_SOURCE",
            ],
            "consumer_held_owner_bindings_attested": True,
        }
    )


def owner_code_fingerprint_definition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_OWNER_CODE_FINGERPRINT_V1_PAD3",
            "fingerprint_version": CODE_FINGERPRINT_VERSION,
            "interpreter_bound": dict(PROOF_INTERPRETER_IDENTITY),
            "derivation": (
                "DETERMINISTIC_RECURSIVE_DIGEST_OF_THE_EFFECTIVE_RUNTIME_CODE_OBJECT_"
                "COMPARED_AGAINST_THE_CODE_OBJECT_INDEPENDENTLY_COMPILED_FROM_THE_"
                "CERTIFIED_REVIEWED_SOURCE"
            ),
            "scalar_fields": list(CODE_FINGERPRINT_FIELDS),
            "byte_fields": list(CODE_FINGERPRINT_BYTE_FIELDS),
            "name_tuple_fields": list(CODE_FINGERPRINT_NAME_TUPLE_FIELDS),
            "constant_pool_included": True,
            "nested_code_objects_recursed": True,
            "supported_constant_kinds": list(CODE_FINGERPRINT_CONSTANT_KINDS),
            "unsupported_constant_kind": "REFUSE_SCIENTIFIC_AUTHORITY",
            "excluded_fields": list(CODE_FINGERPRINT_EXCLUDED_FIELDS),
            "excluded_field_rationale": (
                "CO_FILENAME_RECORDS_WHERE_THE_TEXT_WAS_READ_NOT_WHAT_EXECUTES_AND_"
                "REVIEWED_SOURCE_IDENTITY_IS_ATTESTED_SEPARATELY_AND_EXACTLY"
            ),
            "type_tagged_constant_encoding": True,
            "bool_and_int_constants_distinguished": True,
            "int_and_float_constants_distinguished": True,
            "signed_zero_and_nan_distinguished": True,
            "str_and_bytes_constants_distinguished": True,
            "frozenset_constants_ordered_by_canonical_encoding": True,
            "hash_seed_dependent_material": False,
            "object_address_or_id_material": False,
            "execution_preconditions": [
                "SYS_FLAGS_OPTIMIZE_EQUALS_THE_FROZEN_COMPILE_OPTIMIZE_LEVEL",
                "EFFECTIVE_MODULE_LOADED_FROM_THE_CERTIFIED_REVIEWED_SOURCE_PATH",
                "CERTIFIED_REVIEWED_SOURCE_SHA256_UNCHANGED",
            ],
            "cached_pyc_trusted_without_recomparison": False,
        }
    )


def transitive_execution_closure_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_TRANSITIVE_EXECUTION_CLOSURE_RULE_V1_PAD3",
            "closure_contract_version": CLOSURE_CONTRACT_VERSION,
            "why": (
                "ATTESTING_ONLY_THE_ELEVEN_ENTRY_BINDINGS_MEASURES_WHO_IS_CALLED_NOT_"
                "WHAT_EXECUTES_SO_A_PERSISTENT_REPLACEMENT_OF_ANY_REACHABLE_CALLEE_"
                "VALUE_OR_DEPENDENCY_WOULD_CHANGE_THE_SCIENCE_WITH_EVERY_OWNER_"
                "FINGERPRINT_INTACT"
            ),
            "derivation": (
                "MECHANICAL_FIXPOINT_OVER_THE_MODULE_LEVEL_NAMES_THE_CERTIFIED_OWNER_"
                "CODE_OBJECTS_CAN_LOAD_PLUS_THE_DECLARED_STORE_ROOT_ANNOTATION_TYPE"
            ),
            "derivation_is_a_hand_maintained_list": False,
            "instruction_scan_deoptimizes_specialized_instructions": True,
            "recurses_into_nested_code_objects": True,
            "seeded_by": [
                "EXACT_FROZEN_REPLAY_OWNERS",
                "DECLARED_CalendarEvidenceStore_ROOT_ANNOTATION_TYPE",
            ],
            "closure_kinds": list(CLOSURE_KINDS),
            "closure_refusal_codes": list(CLOSURE_REFUSAL_CODES),
            "function_members_use_the_full_runtime_owner_identity_contract": True,
            "class_members_attested": [
                "EXACT_METACLASS",
                "QUALNAME_AND_MODULE",
                "CERTIFIED_METHOD_CODE_FINGERPRINTS",
                "CERTIFIED_METHOD_WRAPPER_STATE",
                "UNCERTIFIED_FUNCTION_ATTRIBUTE_CENSUS",
            ],
            "value_members_attested_by": "DETERMINISTIC_DEEP_TYPED_VALUE_FINGERPRINT",
            "value_expectation_source": "REVIEWED_SOURCE_LITERAL",
            "value_that_is_not_a_reviewable_literal": (
                "REFUSE_AS_CLOSURE_VALUE_NOT_STATICALLY_DERIVABLE"
            ),
            "project_owned_import_members_attested_by": [
                "SYS_MODULES_BINDING_IDENTITY",
                "ORIGIN_ATTRIBUTE_IDENTITY",
                "CERTIFIED_MODULE_SOURCE_SHA256",
                "EVERY_TOP_LEVEL_FUNCTION_UNDER_THE_RUNTIME_IDENTITY_CONTRACT",
            ],
            "project_owned_import_whole_module_function_attestation": True,
            "project_owned_reexport_chain_followed_to_the_defining_module": True,
            "interpreter_provided_import_members_attested_by": [
                "SYS_MODULES_BINDING_IDENTITY",
                "ORIGIN_ATTRIBUTE_IDENTITY",
            ],
            "interpreter_provided_module_internals_attested": False,
            "interpreter_provided_module_internals_rationale": (
                "THE_FROZEN_PROOF_INTERPRETER_IDENTITY_IS_ALREADY_AN_EXPLICIT_AXIOM_OF_"
                "THIS_ARCHITECTURE_AND_IS_NOT_RE_PROVED_FUNCTION_BY_FUNCTION"
            ),
            "certified_source_closure_identity_required": True,
            "unresolved_closure_name": "CLASSIFIED_AS_A_BUILTIN_AND_REPORTED",
            "closure_member_absent_from_the_frozen_expectation": "REFUSE",
        }
    )


def scientific_execution_epoch_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_SCIENTIFIC_EXECUTION_EPOCH_RULE_V1_PAD3",
            "epoch": SCIENTIFIC_EXECUTION_EPOCH,
            "epoch_order": list(EXECUTION_EPOCH_ORDER),
            "every_authoritative_calendar_or_replay_computation_is_enclosed": True,
            "computation_is_synchronous_inside_the_epoch": True,
            "execution_binds_to": [
                "ATTESTED_MODULE_OBJECT",
                "REVIEWED_SOURCE_IDENTITY",
                "FROZEN_PROOF_INTERPRETER_IDENTITY",
                "PRE_EXECUTION_OWNER_ATTESTATION_DIGEST",
            ],
            "attest_one_module_then_execute_another": False,
            "execution_serialization": EXECUTION_SERIALIZATION,
            "nested_or_reentrant_epoch": NESTED_EPOCH_RULE,
            "serialization_purpose": (
                "DETERMINISTIC_EXECUTION_AND_CONFIGURATION_INTEGRITY"
            ),
            "serialization_is_hostile_same_process_security": False,
            "startup_attestation_required": True,
            "startup_attestation_checks": list(STARTUP_ATTESTATION_CHECKS),
            "startup_attestation_replaces_per_epoch_attestation": False,
            "owner_hot_reload_within_a_process_authority_epoch": "UNSUPPORTED",
            "startup_ordering_rule": STARTUP_ORDERING_RULE,
            "operation_purity_rule": EPOCH_PERSISTENCE_ORDERING,
            "operation_may_persist_before_post_attestation": False,
            "result_rule": EPOCH_RESULT_RULE,
            "lazy_or_deferred_result_admitted": False,
            "lazy_result_refusal": LAZY_RESULT_REFUSAL,
            "exception_path_sweeps_for_persistent_drift": True,
            "exception_path_drift_refusal": POST_EPOCH_DRIFT_REFUSAL,
            "duplicate_loaded_calendar_module_instance": "REFUSE",
            "pre_attestation_must_reproduce_the_startup_baseline": True,
        }
    )


def pre_post_attestation_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PRE_POST_ATTESTATION_RULE_V1_PAD3",
            "pre_execution_attestation_required": True,
            "post_execution_attestation_required": True,
            "post_attestation_before_result_admission": True,
            "result_admitted_before_post_attestation": False,
            "persist_then_discover_mismatch": False,
            "admission_gated_on": "POST_ATTESTATION_DIGEST_EQUALS_PRE_ATTESTATION_DIGEST",
            "compared_material": list(RUNTIME_OWNER_ATTESTATION_FIELDS),
            "pre_attestation_detects": [
                "PERSISTENT_SUBSTITUTION_BEFORE_THE_OPERATION",
                "IMPORT_TIME_MUTATION",
                "STARTUP_CONFIGURATION_DRIFT",
            ],
            "post_attestation_detects": [
                "PERSISTENT_MUTATION_OCCURRING_DURING_THE_OPERATION",
            ],
            "process_startup_attestation_alone_is_sufficient": False,
            "pre_attestation_failure": SCIENTIFIC_EXECUTION_NOT_AUTHORIZED,
            "pre_attestation_failure_effects": [
                "NO_OWNER_CALL",
                "NO_PARTIAL_CALENDAR_RESULT",
                "NO_PERSISTENCE",
                "NO_STAGE_B_EVIDENCE",
            ],
            "post_attestation_failure": [RESULT_REJECTED, DATA_QUALITY_FAIL],
            "post_attestation_failure_effects": [
                "NO_SCIENTIFIC_EVIDENCE_ADMISSION",
                "NO_DOWNSTREAM_STAGE_B_CONSUMPTION",
            ],
            "failure_semantics": "FAIL_CLOSED",
            "fallback_to_an_unattested_owner": False,
            "best_effort_execution": False,
            "transient_mutate_and_restore_inside_one_epoch_detected": False,
            "transient_mutate_and_restore_is_cause_neutral": True,
            "transient_mutate_and_restore_statement": (
                "ANY_MUTATION_FULLY_REVERTED_BETWEEN_THE_PRE_AND_POST_ATTESTATION_"
                "INSTANTS_IS_NOT_DETECTED_WHATEVER_ITS_CAUSE_INCLUDING_BENIGN_"
                "CONCURRENT_PATCH_AND_RESTORE_BY_PROJECT_OWNED_CODE"
            ),
            "epoch_lock_serializes_epochs_against_non_epoch_threads": False,
            "transient_mutate_and_restore_escalation": "PROCESS_ISOLATION",
            "compared_surface": [
                "ELEVEN_FROZEN_REPLAY_OWNERS",
                "TRANSITIVE_EXECUTION_CLOSURE",
                "MODULE_ROUTE_AND_NAMESPACE_IDENTITY",
            ],
        }
    )


def attestation_evidence_schema() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_ATTESTATION_EVIDENCE_SCHEMA_V1_PAD3",
            "evidence_per_scientific_execution_epoch": True,
            "fields": list(ATTESTATION_EVIDENCE_FIELDS),
            "digest_material": (
                "STABLE_REVIEWED_EXECUTION_IDENTITY_ONLY"
            ),
            "forbidden_digest_material": list(FORBIDDEN_ATTESTATION_EVIDENCE_MATERIAL),
            "raw_python_object_addresses_persisted_as_scientific_identity": False,
            "attestation_digest_is_deterministic": True,
            "attestation_digest_reproduces_across_processes_and_hash_seeds": True,
            "refused_epoch_records_its_failure_reason": True,
            "decision_time_is_supplied_by_the_caller_not_read_from_a_clock": True,
        }
    )


def replay_owner_graph_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_OWNER_GRAPH_RULE_V1_PAD3",
            "compiled_root_witness_must_pass_before_graph_extraction": True,
            "ast_use_audit_must_pass_before_graph_extraction": True,
            "runtime_owner_attestation_required_at_execution": True,
            "static_graph_proves": "CERTIFIED_SOURCE_STRUCTURE",
            "runtime_attestation_proves": (
                "EFFECTIVE_RUNTIME_CALLABLE_BINDINGS_CORRESPOND_TO_THE_CERTIFIED_SOURCE"
            ),
            "either_layer_substitutes_for_the_other": False,
            "both_layers_required": True,
            "owner_count": len(FROZEN_REPLAY_OWNERS),
            "owners": list(FROZEN_REPLAY_OWNERS),
            "edge_kinds": [
                "DOCUMENTED_STORE_API_TERMINAL",
                "ENUMERATED_REPLAY_OWNER_EDGE",
            ],
            "cycles_permitted": False,
            "every_owner_has_an_evidence_edge": True,
            "every_owner_path_terminates_at_documented_store_api": True,
            "documented_terminals": list(STORE_APIS),
            "unknown_forwarding_permitted": False,
            "owner_census_relation": (
                "FROZEN_EQUALS_SOURCE_DISCOVERED_EQUALS_RUNTIME_ATTESTED_EQUALS_11"
            ),
        }
    )


def direct_body_dependency_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_DIRECT_BODY_DEPENDENCY_RULE_V1_PAD3",
            "required_direct_bodies": list(REQUIRED_DIRECT_BODIES),
            "exact_dependency_assertion": "assert_trusted_persistence_dependency",
            "proof": "DIRECT_EXECUTABLE_AST_CALL_IN_EACH_REQUIRED_BODY",
            "wrapper_installed_guards_permitted": False,
            "wrapper_installer_must_be_removed": WRAPPER_INSTALLER_SITE,
            "wrapper_removal_is_independent_of_module_owner_attestation": True,
            "startup_self_check": list(STARTUP_ATTESTATION_CHECKS),
            "startup_check_replaces_five_direct_checks": False,
            "startup_check_replaces_per_epoch_attestation": False,
        }
    )


def static_reflection_policy_demotion() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_STATIC_REFLECTION_POLICY_DEMOTION_V1_PAD3",
            "frozen_finding": "STATIC_REFLECTION_BLACKLIST_IS_NOT_OWNER_IDENTITY_PROOF",
            "reflection_blacklist_complete": False,
            "static_reflection_blacklist_is_scientific_completeness_authority": False,
            "retained_roles": list(STATIC_REFLECTION_POLICY_ROLE),
            "demoted_static_names": list(witness.MODULE_NAMESPACE_REACH_NAMES),
            "demoted_static_function_object_attributes": list(
                witness.FUNCTION_OBJECT_MUTATION_ATTRIBUTES
            ),
            "enumerating_more_reflection_names_is_a_valid_correction": False,
            "failed_static_owner_identity_claim": (
                "A_LIST_SUCH_AS_globals_locals_vars_setattr_delattr_sys_modules_"
                "object___setattr___type___setattr___ENUMERATES_EVERY_WAY_PYTHON_CAN_"
                "REPLACE_A_MODULE_BINDING_OR_FUNCTION_BEHAVIOUR"
            ),
            "substitution_forms_detected_behaviourally_not_syntactically": [
                "MODULE_DICTIONARY_OWNER_REPLACEMENT",
                "OWNER___setattr___CODE_MUTATION",
                "object___setattr___CODE_MUTATION",
                "type_OWNER___setattr___CODE_MUTATION",
                "SAME_CODE_FOREIGN_GLOBALS_RECONSTRUCTION",
                "DEFAULTS_OR_KWDEFAULTS_MUTATION",
                "WRAPPER_PARTIAL_BOUND_METHOD_OR_CALLABLE_OBJECT_SUBSTITUTION",
            ],
            "detection_requires_knowing_how_the_mutation_was_performed": False,
        }
    )


def module_namespace_reach_site_classification() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_MODULE_NAMESPACE_REACH_CLASSIFICATION_V1_PAD3",
            "known_reach_sites": list(MODULE_NAMESPACE_REACH_SITES),
            "known_reach_site_count": len(MODULE_NAMESPACE_REACH_SITES),
            "wrapper_installer_site": WRAPPER_INSTALLER_SITE,
            "wrapper_installer_removal_required": True,
            "wrapper_installer_removal_authority": (
                "CERTIFIED_DIRECT_BODY_ARCHITECTURE_FORBIDS_WRAPPER_INSTALLED_GUARDS"
            ),
            "artifact_builder_dispatch_sites": list(ARTIFACT_BUILDER_DISPATCH_SITES),
            "artifact_builder_dispatch_classification": (
                "NON_SCIENTIFIC_ARTIFACT_GENERATION_DISPATCH"
            ),
            "artifact_builder_dispatch_mutates_effective_replay_owner_bindings": False,
            "artifact_builder_dispatch_rewrite_required_solely_by_owner_identity": False,
            "artifact_builder_determinism_governed_by": "EXISTING_ARTIFACT_TESTS",
            "classification_method": (
                "MECHANICAL_AST_CLASSIFICATION_OF_EVERY_MODULE_NAMESPACE_REACH_PLUS_"
                "EFFECTIVE_RUNTIME_OWNER_ATTESTATION_BEFORE_AND_AFTER_ARTIFACT_GENERATION"
            ),
            "unclassified_namespace_reach": "REFUSE",
            "namespace_write_to_a_frozen_owner_name": "REFUSE",
        }
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PROOF_ORDER_AND_COMPLETENESS_V1_PAD3",
            "proof_order": list(PROOF_ORDER),
            "separate_guarantees": {
                "compiled_root_binding_witness": "FROZEN_ROOT_IS_NOT_REBOUND_OR_DELETED",
                "ast_normal_form": "PERMITTED_STORE_USES_ONLY",
                "replay_owner_graph": "REPLAY_ROUTE_CLOSURE",
                "runtime_owner_attestation": (
                    "THE_EFFECTIVE_RUNTIME_BINDINGS_ARE_THE_CERTIFIED_SOURCE_OWNERS"
                ),
            },
            "bytecode_proves_all_program_semantics": False,
            "models_all_possible_python_programs": False,
            "static_module_owner_identity_proof": False,
            "manually_maintained_reflection_or_binder_list_frozen_as_complete": False,
            "completeness": (
                "FROZEN_CPYTHON_COMPILED_ROOT_BINDING_WITNESS_PLUS_CLOSED_DIRECT_USE_"
                "SYNTAX_PLUS_MEASURED_PRE_AND_POST_EXECUTION_EFFECTIVE_OWNER_IDENTITY"
            ),
            "bounded_guarantee": (
                "WITHIN_ONE_SCIENTIFIC_EXECUTION_EPOCH_ANY_OWNER_SUBSTITUTION_OR_"
                "FUNCTION_OBJECT_MUTATION_THAT_IS_STILL_IN_EFFECT_AT_EITHER_"
                "ATTESTATION_POINT_REFUSES_BEFORE_ANY_RESULT_IS_ADMITTED"
            ),
            "guarantee_excludes": [
                "TRANSIENT_MUTATE_AND_PERFECTLY_RESTORE_INSIDE_ONE_EPOCH",
                "ARBITRARY_HOSTILE_SAME_PROCESS_ACTORS",
                "DEBUGGER_FRAME_OR_INTERPRETER_MEMORY_MUTATION",
            ],
            "future_unsupported_syntax": "FAIL_UNTIL_EXPLICIT_REVIEWED_AUTHORITY_CHANGE",
            "decision_certifies_grammar_and_attestation_mechanism": True,
            "decision_certifies_current_production_conformance": False,
            "known_future_implementation_delta": [
                "COMMON_ETF_SESSION_STATUS_GENERATOR_CAPTURE_OF_EVIDENCE_STORE_"
                "MUST_BE_REWRITTEN_WITHOUT_SEMANTIC_PIT_ORDER_OR_EXCEPTION_DRIFT",
                "WRAPPER_INSTALLED_DEPENDENCY_GUARDS_MUST_BE_REMOVED",
                "FIVE_DIRECT_DEPENDENCY_ASSERTIONS_MUST_BE_INSERTED",
                "STARTUP_AND_PER_EPOCH_PRE_POST_OWNER_ATTESTATION_MUST_BE_IMPLEMENTED",
                "EXECUTION_ATTESTATION_EVIDENCE_MUST_BE_PERSISTED",
            ],
        }
    )


def science_lineage_and_safety() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_RUNTIME_ATTESTATION_SCIENCE_LINEAGE_AND_SAFETY_V1_PAD3"
            ),
            "certified_dependency": {
                "authority_version": CERTIFIED_DEPENDENCY_VERSION,
                "definition_sha256": CERTIFIED_DEPENDENCY_SHA256,
                "status": "CLOSED_CERTIFIED_FOR_BOUNDED_ETF_CALENDAR_INTEGRATION",
                "changed": False,
                "rereviewed_wholesale_by_this_decision": False,
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
                "etf_calendar_production_code_changed_by_this_decision": False,
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


_CHILD_ARTIFACTS: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
    ("trusted_process_boundary_reference.json", trusted_process_boundary_reference),
    ("proof_interpreter_identity.json", proof_interpreter_identity),
    ("compiled_root_binding_witness_rule.json", compiled_root_binding_witness_rule),
    ("store_root_and_direct_use_grammar.json", store_root_and_direct_use_grammar),
    ("runtime_owner_identity_contract.json", runtime_owner_identity_contract),
    ("transitive_execution_closure_rule.json", transitive_execution_closure_rule),
    ("owner_code_fingerprint_definition.json", owner_code_fingerprint_definition),
    ("scientific_execution_epoch_rule.json", scientific_execution_epoch_rule),
    ("pre_post_attestation_rule.json", pre_post_attestation_rule),
    ("attestation_evidence_schema.json", attestation_evidence_schema),
    ("replay_owner_graph_rule.json", replay_owner_graph_rule),
    ("direct_body_dependency_rule.json", direct_body_dependency_rule),
    ("static_reflection_policy_demotion.json", static_reflection_policy_demotion),
    (
        "module_namespace_reach_site_classification.json",
        module_namespace_reach_site_classification,
    ),
    (
        "proof_order_and_completeness_definition.json",
        proof_order_and_completeness_definition,
    ),
    ("science_lineage_and_safety.json", science_lineage_and_safety),
)


def _children(
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build every material child from one explicit registry of callables.

    The registry holds the builder object itself, so this decision never reaches
    into its own module namespace by name to dispatch an artifact builder.
    """

    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    return {filename.removesuffix(".json"): builder() for filename, builder in registry}


# ---------------------------------------------------------------------------
# Current production expected result
# ---------------------------------------------------------------------------


def verify_current_production_expected_result(source: str) -> dict[str, Any]:
    """Bind the frozen current-production claim to the reviewed source.

    Current production has no compiled root write, clear or delete; its single
    compiled finding remains the known ``common_etf_session_status`` generator
    capture, which the closed AST grammar refuses as well.  The four artifact
    builder namespace reaches are read-only dispatch and cannot replace a frozen
    owner binding; only the wrapper installer writes, and the key it writes is
    not a replay owner.  Current production is therefore still non-conforming
    and the calendar implementation stays blocked.
    """

    produced = compiled_root_binding_witness(source)
    witness.verify_witness_binds_source(produced, source)
    if len(produced.owners) != len(FROZEN_REPLAY_OWNERS):
        raise RuntimeOwnerAttestationError(
            "compiled witness owner census is not the exact frozen eleven"
        )
    if produced.root_rebinding_findings:
        raise RuntimeOwnerAttestationError(
            "unexpected current-production root rebinding: "
            f"{produced.root_rebinding_findings!r}"
        )
    expected_capture = (
        witness.RootBindingFinding(
            KNOWN_PRODUCTION_BLOCKER_OWNER,
            "OWNER_CODE_OBJECT",
            KNOWN_PRODUCTION_BLOCKER_ROOT,
            0,
            "MAKE_CELL",
            "OWNER_ROOT_IS_CELL_VARIABLE",
        ),
    )
    if produced.root_capture_findings != expected_capture:
        raise RuntimeOwnerAttestationError(
            "current-production capture findings are not the single known "
            f"generator blocker: {produced.root_capture_findings!r}"
        )
    namespace = classify_module_namespace_reach_sites(source)
    if tuple(namespace["reach_scopes"]) != MODULE_NAMESPACE_REACH_SITES:
        raise RuntimeOwnerAttestationError(
            "current-production module-namespace reach scopes are not the frozen "
            f"known set: {namespace['reach_scopes']!r}"
        )
    if namespace["namespace_write_scopes"] != [WRAPPER_INSTALLER_SITE]:
        raise RuntimeOwnerAttestationError(
            "current-production namespace writes are not the single wrapper "
            f"installer: {namespace['namespace_write_scopes']!r}"
        )
    if namespace["unclassified_reach_scopes"] or namespace["frozen_owner_bindings_written"]:
        raise RuntimeOwnerAttestationError(
            "current-production namespace reach is unclassified or writes a frozen "
            f"owner: {namespace!r}"
        )
    try:
        narrow.audit_store_capability_normal_form(source)
    except narrow.NormalFormError as error:
        if "FORBIDDEN_NESTED_SCOPE_CAPTURE" not in str(error):
            raise RuntimeOwnerAttestationError(
                f"unexpected current-production AST refusal: {error}"
            ) from error
    else:
        raise RuntimeOwnerAttestationError(
            "current production unexpectedly conforms to the closed AST use grammar"
        )
    bodies = direct_dependency_body_findings(source)
    if bodies["bodies_absent"] or bodies["decorated_bodies"]:
        raise RuntimeOwnerAttestationError(
            f"current-production required direct bodies are not the frozen five: {bodies!r}"
        )
    if bodies["bodies_without_the_direct_dependency_assertion"] != sorted(
        REQUIRED_DIRECT_BODIES
    ):
        raise RuntimeOwnerAttestationError(
            "current production does not match the known wrapper-guard state: "
            f"{bodies!r}"
        )
    expectations = expected_owner_identities(source)
    closure = expected_execution_closure(source)
    return {
        "reviewed_source_sha256": source_sha256(source),
        "compiled_root_binding_witness": "BINDING_PROOF_COMPATIBLE",
        "root_write_clear_or_delete_findings": 0,
        "root_cell_finding": (
            f"{KNOWN_PRODUCTION_BLOCKER_OWNER}:{KNOWN_PRODUCTION_BLOCKER_ROOT}"
        ),
        "ast_store_use_normal_form": "REFUSED_AT_THE_SAME_GENERATOR_CAPTURE",
        "both_static_layers_refuse_the_same_single_construct": True,
        "module_namespace_reach_scopes": list(namespace["reach_scopes"]),
        "module_namespace_write_scopes": list(namespace["namespace_write_scopes"]),
        "artifact_builder_dispatch_rewrite_required_solely_by_this_decision": False,
        "wrapper_installer_removal_required": True,
        "direct_dependency_body_findings": dict(bodies),
        "expected_owner_code_fingerprints": {
            row.owner: row.code_fingerprint for row in expectations
        },
        "execution_closure": closure.closure.as_material(),
        "execution_closure_expectation_digest": closure.digest,
        "certified_project_closure_module_sha256": {
            row.certified_module: row.source_sha256
            for row in closure.imports
            if row.ownership == "PROJECT_OWNED"
        },
        "runtime_effective_owner_bindings": (
            "ALL_ELEVEN_ATTEST_UNDER_THE_FROZEN_CONTRACT"
        ),
        "runtime_execution_closure_bindings": (
            "REFUSED_AT_THE_WRAPPER_INSTALLED_CalendarEvidenceStore_GUARDS"
        ),
        "runtime_closure_refusal": [
            "CLOSURE_CLASS:CalendarEvidenceStore:CLOSURE_CLASS_CERTIFIED_METHOD_MISMATCH",
            "CLOSURE_CLASS:CalendarEvidenceStore:CLOSURE_CLASS_METHOD_WRAPPER_STATE_MISMATCH",
        ],
        "runtime_attestation_measured_by_this_decision_artifact": False,
        "runtime_attestation_measured_by_deterministic_regression_tests": True,
        "calendar_production_conformance": "NO",
        "calendar_implementation": "BLOCKED",
    }


# ---------------------------------------------------------------------------
# Decision parent
# ---------------------------------------------------------------------------


def runtime_owner_attestation_v1_definition(
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
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
            "failed_parent_certified": False,
            "certified_dependency_sha256": CERTIFIED_DEPENDENCY_SHA256,
            "proof_interpreter": dict(PROOF_INTERPRETER_IDENTITY),
            "material_child_count": len(children),
            "material_child_enumeration": "MECHANICALLY_ENUMERATED_FROM_ONE_REGISTRY",
            "child_definition_sha256": {
                name: child["definition_sha256"] for name, child in children.items()
            },
            "central_decisions": {
                "static_reflection_blacklist_is_owner_identity_proof": False,
                "reflection_blacklist_complete": False,
                "effective_owner_identity_measured_at_the_runtime_execution_boundary": True,
                "module_or_function_reflection_syntax_statically_enumerated": False,
                "code_fingerprint_required": True,
                "code_object_identity_comparison_is_sufficient": False,
                "same_module_namespace_required": True,
                "closure_contract_attested": True,
                "transitive_execution_closure_attested": True,
                "builtins_namespace_attested": True,
                "module_route_identity_attested": True,
                "consumer_held_owner_bindings_attested": True,
                "lazy_or_deferred_result_admitted": False,
                "exception_path_sweeps_for_persistent_drift": True,
                "defaults_attested": True,
                "kwdefaults_attested": True,
                "wrapper_state_attested": True,
                "pre_execution_attestation_required": True,
                "post_execution_attestation_required": True,
                "post_attestation_before_result_admission": True,
                "startup_attestation_required": True,
                "startup_attestation_replaces_per_epoch_attestation": False,
                "compiled_root_witness_preserved": True,
                "closed_ast_store_use_grammar_preserved": True,
                "root_may_be_a_cell_variable_of_a_conforming_owner": False,
                "exact_eleven_owner_graph_preserved": True,
                "direct_body_dependency_checks_preserved": True,
                "wrapper_installed_guards_permitted": False,
                "transient_mutate_and_restore_resistance_claimed": False,
                "process_isolation_escalation_preserved": True,
                "threat_model_strengthened": False,
                "calendar_science_changed": False,
                "calendar_production_code_changed": False,
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
    if dict(persisted) != runtime_owner_attestation_v1_definition():
        raise RuntimeOwnerAttestationError(
            "persisted runtime owner attestation decision does not reproduce"
        )
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    owners = "\n".join(f"- `{owner}`" for owner in FROZEN_REPLAY_OWNERS)
    lineage = ", ".join(FAILED_ARCHITECTURE_LINEAGE)
    interpreter = PROOF_INTERPRETER_IDENTITY
    return f"""# {DECISION_VERSION} — runtime owner attestation

- Ticket: `{PROGRAM_TICKET}`
- Decision hash: `{decision['definition_sha256']}`
- Failed parent: `{FAILED_PARENT_SHA256}`
- Status: `{STATUS}`
- Classification: `{FINAL_CLASSIFICATION}`
- Strategy: `{PROOF_STRATEGY}`
- Material children: {decision['material_child_count']}

## Why the static owner-identity proof was replaced

`POSTP1-002V2A-PAD2` failed with `MODULE OWNER IDENTITY MODEL INCOMPLETE`.
Ordinary project-owned source using `sys.modules[__name__].__dict__["owner"] =
replacement` or `owner.__setattr__("__code__", replacement.__code__)` — and the
`object.__setattr__` and `type(owner).__setattr__` equivalents — passed the whole
static pipeline while replacing what the frozen owner executes. Enumerating more
reflection names is not a correction: the enumeration itself is the defect.

This decision freezes `STATIC_REFLECTION_BLACKLIST_IS_NOT_OWNER_IDENTITY_PROOF`
and sets `reflection_blacklist_complete = false`. The source-level reflection and
namespace checks survive only as diagnostics, defence in depth and coding-policy
enforcement. They are never scientific completeness authority again.

## What replaces it

Effective scientific owner identity is measured, not enumerated. Immediately
before and immediately after every authoritative calendar or replay computation,
each of the eleven frozen owners is read out of the loaded calendar module's own
`__dict__` — the namespace a call actually resolves through — and checked against
identity material derived by independently compiling the certified reviewed
source under frozen `{interpreter['implementation_name']}`
`{interpreter['version_major']}.{interpreter['version_minor']}.{interpreter['version_micro']}`
(magic `{interpreter['magic_number_hex']}`, cache tag `{interpreter['cache_tag']}`).

The attested material is the binding's presence, its exact callable type, its
`__name__`, `__qualname__` and `__module__`, a deterministic recursive execution
fingerprint of its `__code__`, the identity of its `__globals__` and of its bound
builtins namespace, its closure contract, its `__defaults__` and `__kwdefaults__`
fingerprints and its wrapper state. The mutation syntax is irrelevant, because
none of this asks how the binding got there.

## The transitive execution closure

Attesting only the eleven entry bindings would measure who is called, not what
executes. An owner resolves other module-level names at call time, so a
persistent replacement of a reachable helper, result class, frozen constant or
imported dependency changes the scientific answer while every owner fingerprint
still matches byte for byte. The attested surface is therefore the transitive
execution closure, derived as a mechanical fixpoint over the module-level names
the certified owner code objects can actually load — seeded by the eleven owners
and by the `CalendarEvidenceStore` root type the owners declare, recursing into
nested code objects and reading instructions deoptimized. It is a derivation,
not a hand-maintained list, and a closure member missing from the frozen
expectation refuses.

Reachable functions carry the same identity contract as the owners. Reachable
classes are attested by exact metaclass, qualname, module, certified method code
fingerprints and method wrapper state, with an explicit census of any
uncertified function attribute. Reachable values are attested by a deterministic
deep typed fingerprint against the literal the reviewed source declares, and a
value that is not a reviewable literal refuses instead of being accepted.
Reachable project-owned imports are attested by `sys.modules` identity, origin
attribute identity and their own certified source digest, so drift in the
calendar semantics, flow or trusted-acquisition modules is refused too.
Interpreter-provided modules are attested by binding identity only; their
internals are not re-proved function by function, because the frozen proof
interpreter identity is already an explicit axiom of this architecture.

The module itself must also be the one callers reach: exactly a
`types.ModuleType`, the live `sys.modules` entry, the package attribute of the
same name, the only loaded instance of the certified source, and holding the
real builtins namespace. A loaded consumer that holds its own divergent binding
for a frozen owner name refuses as well.

Code identity is a fingerprint, not an object comparison: an independently
compiled equivalent code object is a different object, so
`function.__code__ is expected_code` would refuse honest sources. The fingerprint
covers the argument layout, flags, stack, name and variable tuples, the exception
table, the line table, the raw bytecode and a type-tagged canonical encoding of
the constant pool, recursing into every nested code object. `co_filename` is
excluded because it records where the text was read, and reviewed-source identity
is attested separately and exactly.

`__globals__` identity is required for its own reason: a
`types.FunctionType(expected_code, attacker_globals)` reconstruction matches the
code bytes exactly and would otherwise pass.

## The scientific execution epoch

One bounded unit encloses every authoritative computation: pre-execution
attestation, then the synchronous scientific computation in the very module
whose bindings were attested, then post-execution attestation, and only then
result admission or persistence. A pre-attestation mismatch is
`{SCIENTIFIC_EXECUTION_NOT_AUTHORIZED}` with no owner call, no partial result, no
persistence and no Stage-B evidence. A post-attestation that does not reproduce
the pre-attestation digest is `{RESULT_REJECTED}` / `{DATA_QUALITY_FAIL}`. There
is no persist-then-discover-mismatch path, and that is proven structurally over
this architecture's own source rather than asserted: the executor performs
exactly two attestations on the admitting path, the operation runs strictly
between them, and the admission call is unreachable until the post-attestation
refusal has not fired.

Because the admission call is the only place that may persist, the operation is
frozen as pure with respect to durable state: `{EPOCH_PERSISTENCE_ORDERING}`. A
lazy or deferred result would run its body after the measured window closed, so
`{EPOCH_RESULT_RULE}` and a generator, coroutine or lazy iterator result is
refused. Every exit path, including an exception raised by the operation, sweeps
for drift, so a failing epoch can never leave a persistent substitution silently
in place.

Pre-attestation catches persistent substitution from before the operation,
import-time mutation and startup drift. Post-attestation catches persistent
mutation that happened during the operation. Startup attestation additionally
refuses a process that is already wrong and records the baseline the first
pre-attestation must reproduce; it never replaces either. Import-time behaviour
is itself determined by the certified sources whose digests are attested, so the
residual window is the interval between the end of import and the startup
attestation, which the frozen ordering rule closes by running startup
attestation as the process's first action.

Epochs are serialised — `{EXECUTION_SERIALIZATION}` — and a nested or reentrant
epoch refuses. The lock exists for deterministic execution and configuration
integrity, not for hostile same-process security, and it does not serialise an
epoch against ordinary non-epoch threads.

## The bounded guarantee and its explicit limit

Any substitution or mutation anywhere in the attested closure that is still in
effect at either attestation point refuses before any result is admitted. Any
mutation that is fully reverted between the two attestation instants is **not**
detected, whatever its cause — including benign concurrent patch-and-restore by
project-owned code in a non-epoch thread, not only a deliberate adversary. That
case is classified as arbitrary adversarial same-process mutation and is outside
the accepted trust model, which is unchanged by this decision: the production
Python process is trusted, project-owned scientific drift and misconfiguration
are in scope, and arbitrary debugger, memory and interpreter mutation is out of
scope. If resistance to the transient case ever becomes required the escalation
is **process isolation**, never more Python reflection filters.

## Preserved layers

The compiled root-binding witness is re-adopted in full and freshly parent-bound:
the frozen CPython 3.12.14 identity, the exact opcode policy checked against the
interpreter's own tables, the deoptimized instruction scan, `TypeAlias` and
definition-time mutation detection, nested-body scoping correctness and the
structural rule that a conforming root may never be a cell variable. The failed
PAD2 parent itself is not certified.

The closed AST store-use grammar is preserved unchanged: an ordinary explicit
store parameter only, with aliases, store variadics, starred forwarding, bound
methods, unknown forwarding, capability escapes, nested capture and private
authoritative state access all forbidden.

Static structure and runtime measurement are separate and both required. The
static graph proves the certified source structure; runtime attestation proves
the effective bindings correspond to it. Neither substitutes for the other.
Cycles remain forbidden, every owner path must terminate at `put`, `get`,
`records` or `envelopes`, and the census is exactly eleven frozen, eleven
source-discovered and eleven runtime-attested owners.

## Frozen replay owners

{owners}

## Current production

No compiled root write, clear or delete exists in any owner. The single compiled
root finding remains the `{KNOWN_PRODUCTION_BLOCKER_OWNER}` generator-expression
capture of `{KNOWN_PRODUCTION_BLOCKER_ROOT}`, which the closed AST grammar refuses
at the same construct, so the rewrite that was already required stays required.

All eleven effective runtime owner bindings attest cleanly. The transitive
execution closure does not: the `CalendarEvidenceStore` admission and read
methods are `functools.wraps` guards installed at import, so their certified
method fingerprints and wrapper state both refuse. Runtime measurement therefore
rediscovers the wrapper-installer blocker independently of any static rule.

Of the five module-namespace reaches, exactly one — `{WRAPPER_INSTALLER_SITE}` —
writes the namespace, and the key it writes is not a replay owner. It must still
be removed, because the certified direct-body architecture forbids
wrapper-installed authority guards; that requirement is independent of owner
attestation. The other four are read-only artifact-builder dispatch lookups that
cannot change any effective owner binding, and this decision does not require
them to be rewritten for owner identity. Their determinism remains governed by
their existing artifact tests.

Current full calendar conformance is **NO** and the calendar implementation
remains blocked.

## Preserved authority and safety

Failed proof-architecture lineage `{lineage}` remains immutable, non-certified,
unused and at zero observations. Trusted persistence
`{CERTIFIED_DEPENDENCY_SHA256}` is closed, certified and unchanged, and is not
re-reviewed here. The trusted-process boundary, the five direct dependency-body
requirements, calendar science, failed calendar lineage, BTC-019 and Epic T are
unchanged, and no ETF calendar production code was modified.

No observation was collected and no real Stage-B evaluation ran. Calendar
implementation, `POSTP1-001V2R1`, `POSTP1-003R3`, `POSTP1-004` and collection
remain blocked. This candidate authorizes only `{REQUIRED_REVIEW}`.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    decision = runtime_owner_attestation_v1_definition(registry)
    output_dir.mkdir(parents=True, exist_ok=True)
    payloads = {DEFINITION_FILENAME: decision}
    payloads.update({filename: builder() for filename, builder in registry})
    for filename, payload in payloads.items():
        (output_dir / filename).write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="ascii"
        )
    (output_dir / REPORT_FILENAME).write_text(
        _report_markdown(decision), encoding="utf-8"
    )
    return decision


def restore_artifacts(output_dir: Path) -> dict[str, Any]:
    decision = json.loads((output_dir / DEFINITION_FILENAME).read_text(encoding="ascii"))
    verify_definition(decision)
    for filename, builder in _CHILD_ARTIFACTS:
        persisted = json.loads((output_dir / filename).read_text(encoding="ascii"))
        expected = builder()
        if persisted != expected:
            raise RuntimeOwnerAttestationError(
                f"persisted {filename} does not reproduce"
            )
        _verify_definition_digest(persisted)
        if decision["child_definition_sha256"].get(
            filename.removesuffix(".json")
        ) != expected["definition_sha256"]:
            raise RuntimeOwnerAttestationError(
                f"runtime owner attestation parent does not bind {filename}"
            )
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise RuntimeOwnerAttestationError(
            "persisted runtime owner attestation report does not reproduce"
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
