"""Bootstrap-bound isolated scientific worker architecture for the ETF calendar.

``POSTP1-002V2A-PAD4-R1`` independently regenerated the exact ``PAD4-R1``
candidate ``3415765f...fde37ebc``, reproduced 20/20 material children and
20/20 parent bindings, and then failed it with::

    FAIL — WORKER BOOTSTRAP SOURCE NOT BOUND BEFORE EXECUTION

The review reproduced four portions as **valid** and a successor may not
reopen, rebuild or renegotiate them: fresh-exec isolation, Repair A's fresh
empty per-worker bytecode-cache namespace, Repair C's trusted controller
authority context within its stated scope, and Repair D's third-party
semantic/installed-content authority.  Repair B's frozen source authority is
valid for ordinary certified source and *incomplete for the pre-trust bootstrap
sources*.  Same-process runtime-object attestation stays closed.

The blocking invariant was an authority-ordering defect::

    Already-trusted code does not establish the certified identity of the
    worker bootstrap source before that source executes.

The controller allocated the cache namespace, built the launch material and
exec'd the entrypoint path directly.  The frozen expected manifest was compared
against disk *inside* the worker, by the worker's own protocol module, so every
module that had to run to reach that comparison was outside it.  Two stable
pre-launch drift probes proved this was not merely undetected but authoritative:
entrypoint drift and protocol drift each left their execution marker
**PRESENT** and each had a fabricated scientific result **ADMITTED**.

``POSTP1-001V2A-PAD4-R2`` corrects exactly that ordering and nothing else.  It
is a bounded correction of ``PAD4-R1``, deliberately **not** a ``PAD5``: no new
proof-architecture family is created, the failed ``PAD4`` namespace at
``cc1b325a...7b809e78`` and the failed ``PAD4-R1`` namespace at
``3415765f...fde37ebc`` both stay immutable, non-certified, unused and at zero
observations in their own untouched namespaces.  The frozen rule is::

    NO PROJECT-OWNED WORKER BOOTSTRAP SOURCE MAY EXECUTE UNTIL ALREADY-TRUSTED
    CONTROLLER CODE HAS ESTABLISHED ITS EXPECTED PATH AND SOURCE SHA AGAINST
    THE TRUSTED ScientificWorkerAuthorityContext.

    bootstrap mismatch -> the subprocess is NEVER spawned.

The corrected proof strategy is::

    BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING
    + CERTIFIED_SOURCE_AUTHORITY
    + FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY
    + FROZEN_CPYTHON
    + FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE
    + CLOSED_STORE_GRAMMAR
    + COMPILED_ROOT_WITNESS
    + ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER
    + TRUSTED_CONTROLLER_AUTHORITY_CONTEXT

This module is a pre-data decision builder, a static audit specification and
the authoritative reference controller.  It never collects, persists, signs or
certifies anything, and it changes no ETF calendar production code.
"""

from __future__ import annotations

import argparse
import ast
import json
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from btc_predictor.research import etf_calendar_compiled_binding_witness as witness
from btc_predictor.research import etf_calendar_isolated_scientific_worker as pad4
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r1 as r1
from btc_predictor.research import etf_calendar_runtime_owner_attestation as attestation
from btc_predictor.research import etf_calendar_store_capability_normal_form_r1 as narrow
from etf_calendar_worker import protocol_r2 as protocol


DECISION_VERSION = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
PROGRAM_TICKET = "POSTP1-001V2A-PAD4-R2"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_isolated_scientific_worker_v1_r2"
DEFINITION_FILENAME = "etf_calendar_isolated_scientific_worker_v1_r2_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R2_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
FINAL_CLASSIFICATION = (
    "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R2_READY_FOR_FINAL_XHIGH_REVIEW"
)
PROOF_STRATEGY = (
    "BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_PLUS_CERTIFIED_SOURCE_AUTHORITY_PLUS_"
    "FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY_PLUS_FROZEN_CPYTHON_PLUS_"
    "FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE_PLUS_CLOSED_STORE_GRAMMAR_PLUS_"
    "COMPILED_ROOT_WITNESS_PLUS_ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_PLUS_"
    "TRUSTED_CONTROLLER_AUTHORITY_CONTEXT"
)
REQUIRED_REVIEW = (
    "POSTP1-002V2A-PAD4-R2_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW"
)

#: The failed ``PAD4-R1`` parent this ticket corrects, preserved unchanged.
FAILED_PAD4_R1_SHA256 = (
    "3415765f63a902e415e039ea71892087274541c1e8976a46d41c8f4afde37ebc"
)
FAILED_PAD4_R1_REVIEW = "POSTP1-002V2A-PAD4-R1"
FAILED_PAD4_R1_REVIEW_RESULT = (
    "FAIL — WORKER BOOTSTRAP SOURCE NOT BOUND BEFORE EXECUTION"
)
FAILED_PAD4_R1_DECISION_COMMIT = "37f0db2b12c86b5809d213ae3bdda77a46cc82c2"
FAILED_PAD4_R1_REVIEW_COMMIT = "0fafcef"
FAILED_PAD4_SHA256 = r1.FAILED_PAD4_SHA256

#: The one blocking finding this bounded correction repairs, and nothing else.
REPAIRED_REVIEW_FINDINGS: tuple[str, ...] = (
    "P0_WORKER_BOOTSTRAP_SOURCE_NOT_BOUND_BEFORE_EXECUTION",
    "P0_WORKER_PACKAGE_INITIALIZER_OUTSIDE_THE_BOOTSTRAP_AUTHORITY_SURFACE",
)

#: Independently reproduced as valid by ``POSTP1-002V2A-PAD4-R1``, carried
#: forward intact, and explicitly *not* rebuilt or renegotiated here.
PRESERVED_VALID_PORTIONS: tuple[str, ...] = (
    "BYTECODE_EXECUTION_BINDING_REPAIR_A",
    "CANONICAL_NON_EXECUTABLE_IPC",
    "CLOSED_STORE_GRAMMAR",
    "COMPILED_ROOT_WITNESS",
    "DIRECT_DEPENDENCY_BODY_RULE",
    "EXACT_ELEVEN_OWNER_GRAPH",
    "FRESH_EMPTY_PYCACHE_NAMESPACE",
    "FRESH_EXEC_ISOLATION",
    "FROZEN_SOURCE_AUTHORITY_FOR_ORDINARY_CERTIFIED_SOURCE_REPAIR_B",
    "ONE_REQUEST_ONE_PROCESS_LIFECYCLE",
    "RECORD_INSTALLED_CONTENT_VERIFICATION_BEFORE_DEPENDENCY_EXECUTION",
    "THIRD_PARTY_EXACT_VERSION_AND_ARTIFACT_AUTHORITY_REPAIR_D",
    "TRUSTED_CONTROLLER_AUTHORITY_CONTEXT_REPAIR_C",
)

#: Explicitly *not* reopened by this correction.
NOT_REOPENED: tuple[str, ...] = (
    *r1.NOT_REOPENED,
    "PYCACHE_PREFIX_LAUNCH_DESIGN",
)

PROJECT_ROOT = r1.PROJECT_ROOT
CALENDAR_MODULE = witness.CALENDAR_MODULE
CALENDAR_SOURCE = witness.CALENDAR_SOURCE
CERTIFIED_DEPENDENCY_VERSION = witness.CERTIFIED_DEPENDENCY_VERSION
CERTIFIED_DEPENDENCY_SHA256 = witness.CERTIFIED_DEPENDENCY_SHA256
FAILED_ARCHITECTURE_LINEAGE = (*r1.FAILED_ARCHITECTURE_LINEAGE, FAILED_PAD4_R1_SHA256)
FAILED_CALENDAR_LINEAGE = witness.FAILED_CALENDAR_LINEAGE
FROZEN_REPLAY_OWNERS = witness.FROZEN_REPLAY_OWNERS
REQUIRED_DIRECT_BODIES = witness.REQUIRED_DIRECT_BODIES
STORE_APIS = witness.STORE_APIS
PROOF_INTERPRETER_IDENTITY = witness.PROOF_INTERPRETER_IDENTITY

KNOWN_PRODUCTION_BLOCKER_OWNER = attestation.KNOWN_PRODUCTION_BLOCKER_OWNER
KNOWN_PRODUCTION_BLOCKER_ROOT = attestation.KNOWN_PRODUCTION_BLOCKER_ROOT
WRAPPER_INSTALLER_SITE = attestation.WRAPPER_INSTALLER_SITE
MODULE_NAMESPACE_REACH_SITES = attestation.MODULE_NAMESPACE_REACH_SITES

_definition = narrow._definition
_verify_definition_digest = narrow._verify_definition_digest


class IsolatedScientificWorkerR2Error(r1.IsolatedScientificWorkerR1Error):
    """Raised when the bootstrap-bound worker architecture must refuse."""


class BootstrapSourcePreVerificationError(IsolatedScientificWorkerR2Error):
    """Raised before any subprocess exists, when bootstrap binding fails.

    Every raise of this class happens strictly before ``subprocess.run``.  The
    scientific worker process is never created, so no drifted bootstrap source
    can execute, write a marker, or emit a fabricated response.
    """

    def __init__(self, reason: str, detail: str = "") -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail


def _revised(base: Mapping[str, Any], **overrides: Any) -> dict[str, Any]:
    """Re-freeze a reviewed ``PAD4-R1`` child contract under this parent.

    Every preserved contract is carried forward as the exact reviewed payload
    plus the enumerated corrections, so a reviewer can diff a child against its
    ``PAD4-R1`` original instead of re-reading a restatement.
    """

    payload = {name: value for name, value in base.items() if name != "definition_sha256"}
    payload.update(overrides)
    return _definition(payload)


def verify_worker_protocol_binds_the_frozen_interpreter() -> dict[str, Any]:
    """The R2 protocol layer must restate the one frozen interpreter identity."""

    if dict(protocol.PROOF_INTERPRETER_IDENTITY) != dict(PROOF_INTERPRETER_IDENTITY):
        raise IsolatedScientificWorkerR2Error(
            "the worker protocol interpreter identity diverges from the witness"
        )
    return dict(PROOF_INTERPRETER_IDENTITY)


# ---------------------------------------------------------------------------
# Mechanical source-manifest derivation — authority construction only
# ---------------------------------------------------------------------------

WORKER_SOURCE_MANIFEST_VERSION = "ETF_CALENDAR_WORKER_PROJECT_SOURCE_MANIFEST_V1_R2"
WORKER_ENTRYPOINT_MODULE = protocol.WORKER_ENTRYPOINT_MODULE
WORKER_ENTRYPOINT_RELATIVE_PATH = protocol.WORKER_ENTRYPOINT_RELATIVE_PATH
WORKER_PROTOCOL_MODULE = protocol.WORKER_PROTOCOL_MODULE
WORKER_PROTOCOL_RELATIVE_PATH = protocol.WORKER_PROTOCOL_RELATIVE_PATH
WORKER_PACKAGE_MODULE = protocol.WORKER_PACKAGE_MODULE
WORKER_PACKAGE_RELATIVE_PATH = protocol.WORKER_PACKAGE_RELATIVE_PATH
CERTIFIED_PACKAGE_ROOTS = protocol.CERTIFIED_PACKAGE_ROOTS

PRE_I2_FIXTURE_SEED_MODULE = r1.PRE_I2_FIXTURE_SEED_MODULE
PRE_I2_FIXTURE_VERSION = r1.PRE_I2_FIXTURE_VERSION
PRE_I2_FIXTURE_ROLE = r1.PRE_I2_FIXTURE_ROLE
PRE_I2_FIXTURE_MODULE_COUNT = r1.PRE_I2_FIXTURE_MODULE_COUNT
PRE_I2_FIXTURE_MANIFEST_DIGEST = r1.PRE_I2_FIXTURE_MANIFEST_DIGEST

#: The modules the corrected worker must actually have loaded before it may
#: evaluate.  ``etf_calendar_worker.entry_r2`` runs as ``__main__`` and is
#: therefore verified on disk rather than in ``sys.modules``.
REQUIRED_WORKER_PROJECT_MODULES: tuple[str, ...] = tuple(
    sorted({*r1.REQUIRED_WORKER_PROJECT_MODULES, WORKER_PROTOCOL_MODULE})
)

derive_project_source_manifest = r1.derive_project_source_manifest
external_import_roots = r1.external_import_roots
_module_source_path = r1._module_source_path
_entries = r1._entries


# ---------------------------------------------------------------------------
# The complete pre-trust bootstrap source set
# ---------------------------------------------------------------------------

BOOTSTRAP_SOURCE_SET_VERSION = "ETF_CALENDAR_WORKER_BOOTSTRAP_SOURCE_SET_V1_R2"
BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE = (
    protocol.BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE
)
WORKER_BOOTSTRAP_SOURCE_SET = protocol.WORKER_BOOTSTRAP_SOURCE_SET
WORKER_BOOTSTRAP_RELATIVE_PATHS = protocol.WORKER_BOOTSTRAP_RELATIVE_PATHS
WORKER_BOOTSTRAP_MODULES = protocol.WORKER_BOOTSTRAP_MODULES

#: The bootstrap execution order, as CPython performs it.
BOOTSTRAP_EXECUTION_ORDER: tuple[str, ...] = tuple(
    path for _, path in WORKER_BOOTSTRAP_SOURCE_SET
)

#: The authoritative worker package.  Nothing project-owned outside this root
#: can execute before the scientific verifier, which
#: ``audit_bootstrap_execution_order`` proves by statement order.
BOOTSTRAP_PACKAGE_ROOT = WORKER_PACKAGE_MODULE

#: The entrypoint scope inside which every deferred certified import is loaded.
BOOTSTRAP_GUARDED_SCOPE = "serve_one_request"

#: Every verifier that must already have run, in the guarded scope, before any
#: certified source outside the bootstrap set may be imported.
BOOTSTRAP_ORDERING_VERIFIERS: tuple[str, ...] = (
    "verify_bootstrap_source_set",
    "verify_project_source_manifest",
    "verify_third_party_authority",
)


def _module_level_nodes(node: ast.AST) -> list[ast.AST]:
    """Every node that executes when the module is imported.

    Function and lambda bodies are skipped because they do not execute at
    import time; class bodies are kept because they do.
    """

    collected: list[ast.AST] = []
    for child in ast.iter_child_nodes(node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            continue
        collected.append(child)
        collected.extend(_module_level_nodes(child))
    return collected


def module_level_declared_imports(
    source: str, dotted: str, is_package: bool
) -> set[str]:
    """Static import declarations that execute when the module is imported."""

    package = dotted if is_package else dotted.rpartition(".")[0]
    declared: set[str] = set()
    for node in _module_level_nodes(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                declared.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".")
                if node.level > 1:
                    parts = parts[: len(parts) - (node.level - 1)]
                base = ".".join(parts + ([node.module] if node.module else []))
            else:
                base = node.module or ""
            declared.add(base)
            for alias in node.names:
                declared.add(f"{base}.{alias.name}")
    return declared


def deferred_declared_imports(source: str, dotted: str, is_package: bool) -> set[str]:
    """Static import declarations that only execute when a function is called."""

    return pad4._declared_imports(source, dotted, is_package) - (
        module_level_declared_imports(source, dotted, is_package)
    )


def derive_bootstrap_source_set(
    project_root: Path = PROJECT_ROOT,
    seed: str = WORKER_ENTRYPOINT_MODULE,
) -> tuple[protocol.ProjectSourceEntry, ...]:
    """Mechanically derive every project source that executes before trust.

    The worker entrypoint is exec'd by path, and the first thing it does is
    import the worker protocol, which executes the package initializer and the
    reused reviewed protocol implementation.  All of that runs before the
    scientific verifier exists, so the closure follows **every** static import
    declaration — module-level and function-scoped alike, because
    ``_load_protocol`` is function-scoped and still runs first — restricted to
    the authoritative worker package root plus every ancestor package.

    Certified ``btc_predictor`` source is deliberately *not* bootstrap: it is
    imported only after the certified-source and third-party verifications have
    passed, which ``audit_bootstrap_source_set`` proves by statement order
    rather than by assertion.
    """

    resolved: dict[str, str] = {}
    pending = [seed]
    while pending:
        dotted = pending.pop()
        if dotted in resolved:
            continue
        located = _module_source_path(project_root, dotted)
        if located is None:
            continue
        relative, path = located
        resolved[dotted] = relative
        parts = dotted.split(".")
        pending.extend(".".join(parts[:index]) for index in range(1, len(parts)))
        source = path.read_text(encoding="utf-8")
        for declared in pad4._declared_imports(
            source, dotted, relative.endswith("/__init__.py")
        ):
            root, _, _ = declared.partition(".")
            if root == BOOTSTRAP_PACKAGE_ROOT and declared not in resolved:
                pending.append(declared)
    entries = [
        protocol.ProjectSourceEntry(
            module=dotted,
            path=relative,
            sha256=protocol.file_sha256(project_root / relative),
        )
        for dotted, relative in resolved.items()
    ]
    return tuple(sorted(entries))


def _called_names(node: ast.AST) -> set[str]:
    """Every bare-name callee inside a subtree."""

    return {
        child.func.id
        for child in ast.walk(node)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Name)
    }


def _called_attributes(node: ast.AST) -> set[str]:
    """Every attribute callee inside a subtree, by attribute name."""

    return {
        child.func.attr
        for child in ast.walk(node)
        if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
    }


def audit_bootstrap_execution_order(
    project_root: Path = PROJECT_ROOT,
    bootstrap: Sequence[protocol.ProjectSourceEntry] | None = None,
) -> dict[str, Any]:
    """Prove certified project source cannot execute before it is verified.

    This is the ordering claim that makes a bootstrap set restricted to
    ``etf_calendar_worker`` a *complete* one.  Every entrypoint function that
    declares a certified import outside the bootstrap set is a deferred loader,
    and the audit requires, purely from statement order in the AST, that:

    * every deferred loader is called only inside the guarded scope; and
    * every such call sits after the first call to each required verifier.

    If a future edit moved ``_load_calendar`` above
    ``verify_project_source_manifest``, this refuses instead of quietly
    widening the pre-trust surface.
    """

    entries = derive_bootstrap_source_set(project_root) if bootstrap is None else tuple(
        bootstrap
    )
    bootstrap_modules = {entry.module for entry in entries}
    findings: list[str] = []
    loaders: dict[str, list[str]] = {}
    entry_path = project_root / WORKER_ENTRYPOINT_RELATIVE_PATH
    tree = ast.parse(entry_path.read_text(encoding="utf-8"))
    functions = [
        node
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    for function in functions:
        declared = sorted(
            name
            for name in _declared_imports_of(function)
            if name.partition(".")[0] in CERTIFIED_PACKAGE_ROOTS
            and name not in bootstrap_modules
            and _module_source_path(project_root, name) is not None
        )
        if declared:
            loaders[function.name] = declared
    guarded = next(
        (node for node in functions if node.name == BOOTSTRAP_GUARDED_SCOPE), None
    )
    if guarded is None:
        raise IsolatedScientificWorkerR2Error(
            f"the worker entrypoint declares no {BOOTSTRAP_GUARDED_SCOPE!r} scope"
        )
    for function in functions:
        if function.name == BOOTSTRAP_GUARDED_SCOPE:
            continue
        escaped = sorted(_called_names(function) & set(loaders))
        if escaped:
            findings.append(
                f"{function.name}:DEFERRED_LOADER_CALLED_OUTSIDE_THE_GUARDED_SCOPE:"
                f"{escaped!r}"
            )
    first_verifier: dict[str, int] = {}
    loader_calls: dict[str, int] = {}
    for index, statement in enumerate(guarded.body):
        attributes = _called_attributes(statement)
        for verifier in BOOTSTRAP_ORDERING_VERIFIERS:
            if verifier in attributes and verifier not in first_verifier:
                first_verifier[verifier] = index
        for name in sorted(_called_names(statement) & set(loaders)):
            loader_calls.setdefault(name, index)
    missing = sorted(set(BOOTSTRAP_ORDERING_VERIFIERS) - set(first_verifier))
    if missing:
        findings.append(
            f"{BOOTSTRAP_GUARDED_SCOPE}:REQUIRED_VERIFIER_NEVER_CALLED:{missing!r}"
        )
    guard_index = max(first_verifier.values(), default=-1)
    for name, index in sorted(loader_calls.items()):
        if index <= guard_index:
            findings.append(
                f"{BOOTSTRAP_GUARDED_SCOPE}:DEFERRED_LOADER_RUNS_BEFORE_"
                f"VERIFICATION:{name}"
            )
    if findings:
        raise IsolatedScientificWorkerR2Error(
            f"bootstrap execution order is not proven: {sorted(set(findings))!r}"
        )
    return {
        "guarded_scope": BOOTSTRAP_GUARDED_SCOPE,
        "required_verifiers": list(BOOTSTRAP_ORDERING_VERIFIERS),
        "first_verifier_statement_index": dict(sorted(first_verifier.items())),
        "deferred_loaders": {name: sorted(mods) for name, mods in sorted(loaders.items())},
        "deferred_loader_statement_index": dict(sorted(loader_calls.items())),
        "every_deferred_loader_runs_after_verification": True,
        "findings": [],
    }


def _declared_imports_of(node: ast.AST) -> set[str]:
    """Every dotted module a subtree statically declares an import of."""

    declared: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Import):
            for alias in child.names:
                declared.add(alias.name)
        elif isinstance(child, ast.ImportFrom) and not child.level:
            base = child.module or ""
            declared.add(base)
            for alias in child.names:
                declared.add(f"{base}.{alias.name}")
    return declared


def audit_bootstrap_source_set(
    project_root: Path = PROJECT_ROOT,
    entries: Sequence[protocol.ProjectSourceEntry] | None = None,
    certified: Sequence[protocol.ProjectSourceEntry] | None = None,
) -> dict[str, Any]:
    """Prove the bootstrap set is closed, stdlib-only and statically audited.

    Four properties are checked mechanically, because together they are what
    makes a *finite* bootstrap set a complete one:

    1. no bootstrap module declares any import of certified project source
       outside the bootstrap set at module level, so nothing project-owned can
       join the set at import time;
    2. no bootstrap module declares a module-level import outside the standard
       library, so no third-party code can execute before the reviewed
       installed-content attestation runs;
    3. every deferred, function-scoped certified import declared by a bootstrap
       module is an ordinary member of the certified source manifest, so the
       reviewed Repair B frozen-source authority covers it; and
    4. every deferred loader runs strictly after the certified-source and
       third-party verifications, proven by statement order.

    The closed worker-coding rule is enforced over the whole bootstrap set
    rather than over two filenames.
    """

    bootstrap = derive_bootstrap_source_set(project_root) if entries is None else tuple(
        entries
    )
    manifest = (
        frozen_candidate_source_manifest() if certified is None else tuple(certified)
    )
    bootstrap_modules = {entry.module for entry in bootstrap}
    certified_modules = {entry.module for entry in manifest}
    findings: list[str] = []
    identities: dict[str, str] = {}
    deferred: dict[str, list[str]] = {}
    for entry in bootstrap:
        source = (project_root / entry.path).read_text(encoding="utf-8")
        identities[entry.path] = witness.source_sha256(source)
        findings.extend(pad4.dynamic_import_findings(source, entry.path))
        is_package = entry.path.endswith("/__init__.py")
        for declared in sorted(
            module_level_declared_imports(source, entry.module, is_package)
        ):
            root, _, _ = declared.partition(".")
            if root in CERTIFIED_PACKAGE_ROOTS:
                if declared not in bootstrap_modules:
                    findings.append(
                        f"{entry.path}:MODULE_LEVEL_PROJECT_IMPORT_OUTSIDE_THE_"
                        f"BOOTSTRAP_SET:{declared}"
                    )
            elif root and root != "__future__" and root not in sys.stdlib_module_names:
                findings.append(
                    f"{entry.path}:MODULE_LEVEL_IMPORT_EXECUTES_BEFORE_THIRD_PARTY_"
                    f"ATTESTATION:{declared}"
                )
        outside: list[str] = []
        for declared in sorted(
            deferred_declared_imports(source, entry.module, is_package)
        ):
            root, _, _ = declared.partition(".")
            if root not in CERTIFIED_PACKAGE_ROOTS:
                continue
            if _module_source_path(project_root, declared) is None:
                continue
            if declared in bootstrap_modules:
                continue
            outside.append(declared)
            if declared not in certified_modules:
                findings.append(
                    f"{entry.path}:DEFERRED_PROJECT_IMPORT_OUTSIDE_THE_CERTIFIED_"
                    f"MANIFEST:{declared}"
                )
        if outside:
            deferred[entry.path] = outside
    if findings:
        raise IsolatedScientificWorkerR2Error(
            f"the worker bootstrap source set is not closed: {sorted(set(findings))!r}"
        )
    order = audit_bootstrap_execution_order(project_root, bootstrap)
    return {
        "bootstrap_source_set": [entry.path for entry in bootstrap],
        "bootstrap_execution_order": list(BOOTSTRAP_EXECUTION_ORDER),
        "source_sha256": dict(sorted(identities.items())),
        "deferred_certified_project_imports": {
            path: sorted(names) for path, names in sorted(deferred.items())
        },
        "execution_order_proof": order,
        "findings": [],
        "closed": True,
    }


# ---------------------------------------------------------------------------
# Frozen source material
# ---------------------------------------------------------------------------

#: The reviewed pre-I2 project source universe is unchanged by this correction
#: and is reused verbatim as immutable literal material.  Its role is still an
#: architecture conformance test vector, provenance and a pre-I2 source-drift
#: regression anchor; it is *not* the future production source authority, and
#: ``POSTP1-001V2A-I2`` must still derive and calendar-parent-bind its own exact
#: final post-rewrite manifest.
FROZEN_PRE_I2_SOURCE_ROWS = r1.FROZEN_PRE_I2_SOURCE_ROWS

#: The four worker-owned modules of the corrected bootstrap architecture.  The
#: package initializer and ``protocol_r1`` are byte-identical to the reviewed
#: ``PAD4-R1`` files: this correction changes bootstrap *ordering*, not the
#: reviewed protocol implementation, which is reused rather than forked.
FROZEN_WORKER_PACKAGE_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "etf_calendar_worker",
        "etf_calendar_worker/__init__.py",
        "28b263fdb0c202e7cf22f0e64bc613437e9ddef0e15972066881c51bedba49cb",
    ),
    (
        "etf_calendar_worker.entry_r2",
        "etf_calendar_worker/entry_r2.py",
        "945588c73bf902ef8ea6c05dce66ae8acc34ef6786f088a8a8b389501b566851",
    ),
    (
        "etf_calendar_worker.protocol_r1",
        "etf_calendar_worker/protocol_r1.py",
        "a896925a2cc24e323e1fe54537a5b17693ef3d9e837d1221d68f34b3d08e30de",
    ),
    (
        "etf_calendar_worker.protocol_r2",
        "etf_calendar_worker/protocol_r2.py",
        "ea00785b18f30c34e40269f840269473d5ed194531e33ab38048a2ee59ff3f8d",
    ),
)

CANDIDATE_SOURCE_MODULE_COUNT = PRE_I2_FIXTURE_MODULE_COUNT + len(
    FROZEN_WORKER_PACKAGE_ROWS
)


def frozen_pre_i2_source_manifest() -> tuple[protocol.ProjectSourceEntry, ...]:
    return r1.frozen_pre_i2_source_manifest()


def frozen_candidate_source_manifest() -> tuple[protocol.ProjectSourceEntry, ...]:
    """The frozen expected manifest the corrected worker is bound to."""

    return tuple(
        sorted(_entries(FROZEN_PRE_I2_SOURCE_ROWS + FROZEN_WORKER_PACKAGE_ROWS))
    )


def frozen_bootstrap_source_manifest() -> tuple[protocol.ProjectSourceEntry, ...]:
    """The frozen complete pre-trust bootstrap set, as trusted material.

    Every member is also an ordinary member of the frozen certified manifest,
    with the identical path and SHA-256.  The bootstrap manifest is not a
    second, weaker source of truth; it is the subset the already-trusted
    controller must verify *before* the certified manifest can be verified at
    all.
    """

    certified = {entry.path: entry for entry in frozen_candidate_source_manifest()}
    return protocol.bootstrap_source_entries(
        [
            certified[path].as_material()
            for path in protocol.WORKER_BOOTSTRAP_RELATIVE_PATHS
        ]
    )


def verify_frozen_pre_i2_fixture() -> dict[str, Any]:
    """The frozen fixture must still state the exact reviewed universe."""

    return r1.verify_frozen_pre_i2_fixture()


def verify_frozen_bootstrap_set_is_complete(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """The frozen bootstrap set must equal the mechanical derivation."""

    derived = derive_bootstrap_source_set(project_root)
    frozen = frozen_bootstrap_source_manifest()
    if derived != frozen:
        raise IsolatedScientificWorkerR2Error(
            "the frozen bootstrap source set is not the mechanically derived set: "
            f"{[entry.path for entry in derived]!r} != "
            f"{[entry.path for entry in frozen]!r}"
        )
    certified = {entry.module: entry for entry in frozen_candidate_source_manifest()}
    for entry in frozen:
        if certified.get(entry.module) != entry:
            raise IsolatedScientificWorkerR2Error(
                f"bootstrap source {entry.module} diverges from the certified manifest"
            )
    return {
        "bootstrap_source_count": len(frozen),
        "bootstrap_manifest_digest": protocol.bootstrap_manifest_digest(frozen),
        "bootstrap_source_set": [entry.path for entry in frozen],
    }


# ---------------------------------------------------------------------------
# Repair D — the exact reviewed third-party semantic and artifact registry
# ---------------------------------------------------------------------------

THIRD_PARTY_REGISTRY_VERSION = "ETF_CALENDAR_WORKER_THIRD_PARTY_AUTHORITY_V1_R2"
FROZEN_THIRD_PARTY_AUTHORITY_ROWS = r1.FROZEN_THIRD_PARTY_AUTHORITY_ROWS
frozen_third_party_authority = r1.frozen_third_party_authority
derive_third_party_authority = r1.derive_third_party_authority
observe_installed_distributions = r1.observe_installed_distributions


# ---------------------------------------------------------------------------
# Repair C — the trusted controller authority context, bootstrap-extended
# ---------------------------------------------------------------------------

AUTHORITY_CONTEXT_VERSION = "ETF_CALENDAR_SCIENTIFIC_WORKER_AUTHORITY_CONTEXT_V1_R2"
AUTHORITY_CONSTRUCTION_REFREEZE = r1.AUTHORITY_CONSTRUCTION_REFREEZE
FINAL_CALENDAR_AUTHORITY = r1.FINAL_CALENDAR_AUTHORITY
REVIEW_CANDIDATE_CONTEXT = r1.REVIEW_CANDIDATE_CONTEXT
AUTHORITY_CONTEXT_ORIGINS = protocol.AUTHORITY_CONTEXT_ORIGINS
FINAL_CALENDAR_AUTHORITY_WORKER_FIELD = r1.FINAL_CALENDAR_AUTHORITY_WORKER_FIELD


@dataclass(frozen=True)
class ScientificWorkerAuthorityContext:
    """The trusted expected values launch, request and admission all use.

    ``PAD4-R1`` established this context and the review reproduced it as valid
    *for its stated scope*: a request cannot construct it, a response cannot
    construct it, live disk cannot silently replace it and the installed
    environment cannot silently replace it.  What it did not do was hand
    already-trusted code an expected identity for the bootstrap source that has
    to run before any of it can be checked.

    ``worker_bootstrap_manifest`` closes exactly that.  It is the complete
    frozen pre-trust bootstrap set, it must agree entry-for-entry with the
    certified project source manifest, and the controller verifies it against
    disk *before* it creates a worker process.
    """

    origin: str
    proof_architecture_version: str
    proof_architecture_ticket: str
    proof_architecture_sha256: str
    interpreter_identity: Mapping[str, Any]
    project_source_manifest: tuple[protocol.ProjectSourceEntry, ...]
    project_source_manifest_role: str
    worker_bootstrap_manifest: tuple[protocol.ProjectSourceEntry, ...]
    required_project_modules: tuple[str, ...]
    third_party_authority: tuple[protocol.FrozenDistributionAuthority, ...]
    calendar_authority_version: str
    calendar_authority_sha256: str
    trusted_persistence_authority_sha256: str

    def __post_init__(self) -> None:
        if self.origin not in AUTHORITY_CONTEXT_ORIGINS:
            raise IsolatedScientificWorkerR2Error(
                f"unknown authority context origin {self.origin!r}"
            )
        if self.proof_architecture_version != DECISION_VERSION:
            raise IsolatedScientificWorkerR2Error(
                "authority context does not bind the corrected architecture version"
            )
        if self.proof_architecture_ticket != PROGRAM_TICKET:
            raise IsolatedScientificWorkerR2Error(
                "authority context does not bind the corrected architecture ticket"
            )
        sha = self.proof_architecture_sha256
        if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
            raise IsolatedScientificWorkerR2Error(
                f"authority context proof-architecture hash is malformed: {sha!r}"
            )
        if dict(self.interpreter_identity) != dict(PROOF_INTERPRETER_IDENTITY):
            raise IsolatedScientificWorkerR2Error(
                "authority context does not bind the frozen proof interpreter"
            )
        if self.project_source_manifest_role not in (
            protocol.PROJECT_SOURCE_MANIFEST_ROLES
        ):
            raise IsolatedScientificWorkerR2Error(
                f"unknown source manifest role {self.project_source_manifest_role!r}"
            )
        entries = protocol.project_source_entries(
            [entry.as_material() for entry in self.project_source_manifest]
        )
        if entries != tuple(self.project_source_manifest):
            raise IsolatedScientificWorkerR2Error(
                "authority context source manifest is not canonical"
            )
        bootstrap = protocol.bootstrap_source_entries(
            [entry.as_material() for entry in self.worker_bootstrap_manifest]
        )
        if bootstrap != tuple(self.worker_bootstrap_manifest):
            raise IsolatedScientificWorkerR2Error(
                "authority context bootstrap manifest is not canonical"
            )
        certified = {entry.module: entry for entry in entries}
        for entry in bootstrap:
            if certified.get(entry.module) != entry:
                raise IsolatedScientificWorkerR2Error(
                    "authority context bootstrap source "
                    f"{entry.module} diverges from its certified manifest entry"
                )
        outside = sorted(set(self.required_project_modules) - set(certified))
        if outside:
            raise IsolatedScientificWorkerR2Error(
                f"required modules outside the frozen manifest: {outside!r}"
            )
        protocol.frozen_distribution_authorities(
            [entry.as_material() for entry in self.third_party_authority]
        )

    # -- derived trusted material ------------------------------------------

    @property
    def project_source_manifest_digest(self) -> str:
        return protocol.manifest_digest(self.project_source_manifest)

    @property
    def worker_bootstrap_manifest_digest(self) -> str:
        return protocol.bootstrap_manifest_digest(self.worker_bootstrap_manifest)

    @property
    def third_party_authority_digest(self) -> str:
        return protocol.third_party_authority_digest(self.third_party_authority)

    def bootstrap_source_sha256(self, relative: str) -> str:
        for entry in self.worker_bootstrap_manifest:
            if entry.path == relative:
                return entry.sha256
        raise IsolatedScientificWorkerR2Error(
            f"authority context bootstrap manifest omits {relative}"
        )

    def expected_authority_fields(self) -> dict[str, Any]:
        """Every material authority identity, as the trusted context states it."""

        return {
            "calendar_authority_sha256": self.calendar_authority_sha256,
            "calendar_authority_version": self.calendar_authority_version,
            "interpreter_identity": dict(self.interpreter_identity),
            "project_source_manifest_digest": self.project_source_manifest_digest,
            "project_source_manifest_role": self.project_source_manifest_role,
            "third_party_authority_digest": self.third_party_authority_digest,
            "trusted_persistence_authority_sha256": (
                self.trusted_persistence_authority_sha256
            ),
            "worker_authority_sha256": self.proof_architecture_sha256,
            "worker_authority_ticket": self.proof_architecture_ticket,
            "worker_authority_version": self.proof_architecture_version,
            "worker_bootstrap_manifest_digest": self.worker_bootstrap_manifest_digest,
            "worker_entrypoint_module": WORKER_ENTRYPOINT_MODULE,
        }

    def as_evidence(self) -> dict[str, Any]:
        """Deterministic, address-free identity of the trusted context."""

        return {
            "authority_context_version": AUTHORITY_CONTEXT_VERSION,
            "authority_context_origin": self.origin,
            "proof_architecture_version": self.proof_architecture_version,
            "proof_architecture_ticket": self.proof_architecture_ticket,
            "proof_architecture_sha256": self.proof_architecture_sha256,
            "project_source_manifest_digest": self.project_source_manifest_digest,
            "project_source_manifest_role": self.project_source_manifest_role,
            "project_source_module_count": len(self.project_source_manifest),
            "worker_bootstrap_manifest_digest": self.worker_bootstrap_manifest_digest,
            "worker_bootstrap_source_count": len(self.worker_bootstrap_manifest),
            "worker_bootstrap_source_set": [
                entry.path for entry in self.worker_bootstrap_manifest
            ],
            "third_party_authority_digest": self.third_party_authority_digest,
            "third_party_distributions": [
                entry.distribution for entry in self.third_party_authority
            ],
            "calendar_authority_version": self.calendar_authority_version,
            "calendar_authority_sha256": self.calendar_authority_sha256,
            "trusted_persistence_authority_sha256": (
                self.trusted_persistence_authority_sha256
            ),
        }


_calendar_identity = r1._calendar_identity


def candidate_review_authority_context(
    proof_architecture_sha256: str,
    *,
    origin: str = REVIEW_CANDIDATE_CONTEXT,
) -> ScientificWorkerAuthorityContext:
    """The trusted context used while this candidate is under review.

    The candidate's own parent hash cannot be materially embedded inside
    itself, so no cryptographic self-hash fixed point is attempted.  The
    reviewer or harness instantiates this context with the *recomputed* parent
    hash, which comes from the trusted review context and never from the
    scientific request.

    ``POSTP1-002V2A-PAD4-R1`` raised, as a secondary candidate, that this
    constructor accepts any well-formed SHA.  That behaviour is independently
    reproduced here and is deliberately retained: constraining it to one
    literal value is precisely the self-hash fixed point the architecture
    refuses, and the hash's trust does not come from this constructor.  It
    comes from the caller being the trusted review context, which is the same
    two-stage boundary ``POSTP1-002V2A-PAD4`` required and
    ``POSTP1-002V2A-PAD4-R1`` reproduced as valid.  See
    ``controller_authority_context_rule`` for the frozen statement.
    """

    version, calendar_sha, persistence_sha = _calendar_identity()
    return ScientificWorkerAuthorityContext(
        origin=origin,
        proof_architecture_version=DECISION_VERSION,
        proof_architecture_ticket=PROGRAM_TICKET,
        proof_architecture_sha256=proof_architecture_sha256,
        interpreter_identity=dict(PROOF_INTERPRETER_IDENTITY),
        project_source_manifest=frozen_candidate_source_manifest(),
        project_source_manifest_role=PRE_I2_FIXTURE_ROLE,
        worker_bootstrap_manifest=frozen_bootstrap_source_manifest(),
        required_project_modules=REQUIRED_WORKER_PROJECT_MODULES,
        third_party_authority=frozen_third_party_authority(),
        calendar_authority_version=version,
        calendar_authority_sha256=calendar_sha,
        trusted_persistence_authority_sha256=persistence_sha,
    )


def derive_authority_context_from_reviewed_source(
    proof_architecture_sha256: str,
    *,
    project_root: Path = PROJECT_ROOT,
    origin: str = AUTHORITY_CONSTRUCTION_REFREEZE,
) -> ScientificWorkerAuthorityContext:
    """Authority construction / refreeze: derive the manifests from source.

    This is the *only* operation permitted to read the source manifest, the
    bootstrap set and the installed dependency registry from live material, and
    it is explicitly not a runtime operation.  Runtime consumes an
    already-frozen context.
    """

    entries = derive_project_source_manifest(project_root, (WORKER_ENTRYPOINT_MODULE,))
    bootstrap = derive_bootstrap_source_set(project_root)
    version, calendar_sha, persistence_sha = _calendar_identity()
    return ScientificWorkerAuthorityContext(
        origin=origin,
        proof_architecture_version=DECISION_VERSION,
        proof_architecture_ticket=PROGRAM_TICKET,
        proof_architecture_sha256=proof_architecture_sha256,
        interpreter_identity=dict(PROOF_INTERPRETER_IDENTITY),
        project_source_manifest=entries,
        project_source_manifest_role=PRE_I2_FIXTURE_ROLE,
        worker_bootstrap_manifest=bootstrap,
        required_project_modules=REQUIRED_WORKER_PROJECT_MODULES,
        third_party_authority=derive_third_party_authority(
            external_import_roots(project_root, entries)
        ),
        calendar_authority_version=version,
        calendar_authority_sha256=calendar_sha,
        trusted_persistence_authority_sha256=persistence_sha,
    )


PRODUCTION_CONTEXT_NOT_YET_BOUND = r1.PRODUCTION_CONTEXT_NOT_YET_BOUND


def production_authority_context_from_calendar_authority(
    calendar_authority: Mapping[str, Any],
) -> ScientificWorkerAuthorityContext:
    """The frozen production rule: the context comes from the final authority.

    The production controller authority context must be derived from the final
    ``ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`` definition — never from the
    request, the current filesystem, the ambient environment or a
    caller-selected SHA.  ``POSTP1-001V2A-I2`` must bind the certified
    ``PAD4-R2`` hash, the exact final post-I2 source manifest, the exact final
    bootstrap source set and the reviewed third-party authority into that
    definition.  Until it does, there is no production context and this
    refuses.
    """

    material = calendar_authority.get(FINAL_CALENDAR_AUTHORITY_WORKER_FIELD)
    if not isinstance(material, Mapping):
        raise IsolatedScientificWorkerR2Error(
            f"{PRODUCTION_CONTEXT_NOT_YET_BOUND}: the final calendar authority "
            f"declares no {FINAL_CALENDAR_AUTHORITY_WORKER_FIELD!r}"
        )
    required = {
        "proof_architecture_sha256",
        "project_source_manifest",
        "required_project_modules",
        "third_party_authority",
        "worker_bootstrap_manifest",
    }
    missing = sorted(required - set(material))
    if missing:
        raise IsolatedScientificWorkerR2Error(
            f"{PRODUCTION_CONTEXT_NOT_YET_BOUND}: missing {missing!r}"
        )
    version, calendar_sha, persistence_sha = _calendar_identity()
    return ScientificWorkerAuthorityContext(
        origin=FINAL_CALENDAR_AUTHORITY,
        proof_architecture_version=DECISION_VERSION,
        proof_architecture_ticket=PROGRAM_TICKET,
        proof_architecture_sha256=str(material["proof_architecture_sha256"]),
        interpreter_identity=dict(PROOF_INTERPRETER_IDENTITY),
        project_source_manifest=protocol.project_source_entries(
            material["project_source_manifest"]
        ),
        project_source_manifest_role=(
            "POST_I2_FINAL_CALENDAR_PARENT_BOUND_PRODUCTION_AUTHORITY"
        ),
        worker_bootstrap_manifest=protocol.bootstrap_source_entries(
            material["worker_bootstrap_manifest"]
        ),
        required_project_modules=tuple(material["required_project_modules"]),
        third_party_authority=protocol.frozen_distribution_authorities(
            material["third_party_authority"]
        ),
        calendar_authority_version=version,
        calendar_authority_sha256=calendar_sha,
        trusted_persistence_authority_sha256=persistence_sha,
    )


# ---------------------------------------------------------------------------
# Repair A — fresh, empty, per-worker bytecode-cache namespaces (preserved)
# ---------------------------------------------------------------------------

WORKER_LAUNCH_CONTRACT = "ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_V1_R2"
WORKER_LAUNCH_FLAGS = r1.WORKER_LAUNCH_FLAGS
WORKER_LAUNCH_X_OPTION = r1.WORKER_LAUNCH_X_OPTION
EXEC_LAUNCH = r1.EXEC_LAUNCH
FORK_WITHOUT_EXEC = r1.FORK_WITHOUT_EXEC
FORK_SERVER_REUSE = r1.FORK_SERVER_REUSE
AUTHORIZED_LAUNCH_MECHANISMS = r1.AUTHORIZED_LAUNCH_MECHANISMS
UNAUTHORIZED_LAUNCH_MECHANISMS = r1.UNAUTHORIZED_LAUNCH_MECHANISMS
FROZEN_WORKER_ENVIRONMENT = r1.FROZEN_WORKER_ENVIRONMENT

authorize_worker_launch_mechanism = r1.authorize_worker_launch_mechanism
controller_pycache_root = r1.controller_pycache_root
create_fresh_pycache_namespace = r1.create_fresh_pycache_namespace
allocate_worker_pycache_namespace = r1.allocate_worker_pycache_namespace
interpreter_base_sys_path = r1.interpreter_base_sys_path
parent_site_paths = r1.parent_site_paths


@dataclass(frozen=True)
class WorkerLaunch:
    """Fully parent-bound launch material for one scientific worker process."""

    executable: str
    project_root: Path
    sys_path: tuple[str, ...]
    entrypoint: Path
    cwd: Path
    pycache_namespace_root: Path
    mechanism: str = EXEC_LAUNCH
    timeout_seconds: int = protocol.DEFAULT_TIMEOUT_SECONDS
    environment: Mapping[str, str] = field(
        default_factory=lambda: dict(FROZEN_WORKER_ENVIRONMENT)
    )

    def argv_for(self, pycache_namespace: Path) -> tuple[str, ...]:
        return (
            self.executable,
            *WORKER_LAUNCH_FLAGS,
            "-X",
            f"{WORKER_LAUNCH_X_OPTION}={Path(pycache_namespace).resolve()}",
            str(self.entrypoint),
            json.dumps(list(self.sys_path)),
            str(Path(pycache_namespace).resolve()),
        )


def worker_launch(
    project_root: Path = PROJECT_ROOT,
    *,
    executable: str | None = None,
    extra_sys_path: Sequence[str] = (),
    timeout_seconds: int = protocol.DEFAULT_TIMEOUT_SECONDS,
    mechanism: str = EXEC_LAUNCH,
    pycache_namespace_root: Path | None = None,
) -> WorkerLaunch:
    authorize_worker_launch_mechanism(mechanism)
    interpreter = executable or sys.executable
    base = interpreter_base_sys_path(interpreter)
    entries = [
        *extra_sys_path,
        *base,
        str(project_root),
        *parent_site_paths(),
    ]
    deduplicated: list[str] = []
    for entry in entries:
        if entry not in deduplicated:
            deduplicated.append(entry)
    return WorkerLaunch(
        executable=interpreter,
        project_root=project_root,
        sys_path=tuple(deduplicated),
        entrypoint=project_root / WORKER_ENTRYPOINT_RELATIVE_PATH,
        cwd=project_root,
        pycache_namespace_root=(
            controller_pycache_root()
            if pycache_namespace_root is None
            else Path(pycache_namespace_root)
        ),
        mechanism=mechanism,
        timeout_seconds=timeout_seconds,
    )


# ---------------------------------------------------------------------------
# The correction — trusted controller bootstrap pre-execution verification
# ---------------------------------------------------------------------------

BOOTSTRAP_PRE_VERIFICATION_VERSION = (
    "ETF_CALENDAR_WORKER_BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_V1_R2"
)

#: Everything the trusted controller establishes about one bootstrap source
#: before the worker process can exist.
BOOTSTRAP_PRE_VERIFICATION_CHECKS: tuple[str, ...] = (
    "EXACT_SHA256",
    "EXPECTED_RELATIVE_PATH",
    "NO_ALTERNATE_SOURCE_CANDIDATE",
    "NO_EARLIER_SYS_PATH_PACKAGE_SHADOW",
    "NO_SOURCELESS_BYTECODE_REPLACEMENT",
    "REGULAR_CERTIFIED_SOURCE_FILE",
    "RESOLVED_EXPECTED_PROJECT_ROOT",
)


def _bytecode_shadow_candidates(relative: str) -> tuple[str, ...]:
    """Sourceless replacements that would win over a missing ``.py`` file."""

    stem = relative.removesuffix(".py")
    return (f"{stem}.pyc", f"{stem}.pyo")


def _alternate_source_candidates(entry: protocol.ProjectSourceEntry) -> tuple[str, ...]:
    """The other canonical source path the same dotted module could resolve to."""

    module_path = protocol.module_relative_path(entry.module)
    package_path = protocol.package_relative_path(entry.module)
    other = package_path if entry.path == module_path else module_path
    return (other, *_bytecode_shadow_candidates(entry.path))


def _sys_path_package_shadows(
    launch: WorkerLaunch, project_root: Path
) -> tuple[str, ...]:
    """Earlier ``sys.path`` entries that would provide the worker package.

    The entrypoint is exec'd by path, but every other bootstrap module is
    resolved through the parent-controlled ``sys.path``.  An earlier entry that
    provides ``etf_calendar_worker`` would silently supply a different package
    initializer and a different protocol module, so it refuses here rather than
    inside a worker that has already imported it.
    """

    shadows: list[str] = []
    root = str(project_root)
    for candidate in launch.sys_path:
        if candidate == root:
            break
        directory = Path(candidate)
        if not directory.is_dir():
            continue
        package = directory / WORKER_PACKAGE_MODULE
        module = directory / f"{WORKER_PACKAGE_MODULE}.py"
        if package.exists() or module.exists():
            shadows.append(candidate)
    return tuple(shadows)


def preverify_worker_bootstrap_sources(
    authority_context: ScientificWorkerAuthorityContext,
    launch: WorkerLaunch,
) -> dict[str, Any]:
    """Bind every bootstrap source before any of it can execute.

    This is the whole ``PAD4-R2`` correction.  It runs in already-trusted
    controller code, it reads the trusted ``ScientificWorkerAuthorityContext``
    rather than the scientific request, and it raises
    ``BootstrapSourcePreVerificationError`` — never spawning a process — on any
    mismatch.  The worker's own restatement of the same property is defence in
    depth and is not authority: by the time it can run, the bootstrap source
    has already executed.
    """

    if not isinstance(authority_context, ScientificWorkerAuthorityContext):
        raise BootstrapSourcePreVerificationError(
            "BOOTSTRAP_PRE_VERIFICATION_REQUIRES_A_TRUSTED_AUTHORITY_CONTEXT",
            type(authority_context).__name__,
        )
    if not isinstance(launch, WorkerLaunch):
        raise BootstrapSourcePreVerificationError(
            "BOOTSTRAP_PRE_VERIFICATION_REQUIRES_PARENT_BOUND_LAUNCH_MATERIAL",
            type(launch).__name__,
        )
    authorize_worker_launch_mechanism(launch.mechanism)

    expected = authority_context.worker_bootstrap_manifest
    if tuple(entry.path for entry in expected) != WORKER_BOOTSTRAP_RELATIVE_PATHS:
        raise BootstrapSourcePreVerificationError(
            "WORKER_BOOTSTRAP_SOURCE_SET_IS_NOT_THE_FROZEN_COMPLETE_SET",
            repr([entry.path for entry in expected]),
        )

    root = Path(launch.project_root)
    if not root.is_dir():
        raise BootstrapSourcePreVerificationError(
            "CERTIFIED_PROJECT_ROOT_IS_NOT_A_DIRECTORY", str(root)
        )
    resolved_root = root.resolve()

    shadows = _sys_path_package_shadows(launch, root)
    if shadows:
        raise BootstrapSourcePreVerificationError(
            "ALTERNATE_WORKER_PACKAGE_SHADOWS_THE_CERTIFIED_PROJECT_ROOT",
            repr(list(shadows)),
        )

    expected_entrypoint = (resolved_root / WORKER_ENTRYPOINT_RELATIVE_PATH).resolve()
    declared_entrypoint = Path(launch.entrypoint).resolve()
    if declared_entrypoint != expected_entrypoint:
        raise BootstrapSourcePreVerificationError(
            "WORKER_ENTRYPOINT_IS_NOT_THE_CERTIFIED_PATH",
            f"{declared_entrypoint} != {expected_entrypoint}",
        )

    verified: dict[str, str] = {}
    for entry in expected:
        target = root / entry.path
        for alternate in _alternate_source_candidates(entry):
            if (root / alternate).exists():
                raise BootstrapSourcePreVerificationError(
                    "ALTERNATE_WORKER_BOOTSTRAP_SOURCE_CANDIDATE",
                    f"{entry.module} -> {alternate}",
                )
        if target.is_symlink():
            raise BootstrapSourcePreVerificationError(
                "WORKER_BOOTSTRAP_SOURCE_IS_NOT_A_REGULAR_CERTIFIED_FILE",
                f"{entry.path} is a symbolic link",
            )
        if not target.is_file():
            raise BootstrapSourcePreVerificationError(
                "WORKER_BOOTSTRAP_SOURCE_FILE_MISSING", f"{entry.module} -> {entry.path}"
            )
        resolved = target.resolve()
        if resolved != resolved_root / entry.path:
            raise BootstrapSourcePreVerificationError(
                "WORKER_BOOTSTRAP_SOURCE_RESOLVES_OUTSIDE_THE_CERTIFIED_ROOT",
                f"{resolved} != {resolved_root / entry.path}",
            )
        observed = protocol.digest_bytes(target.read_bytes())
        if observed != entry.sha256:
            raise BootstrapSourcePreVerificationError(
                "WORKER_BOOTSTRAP_SOURCE_SHA_MISMATCH",
                f"{entry.path}: expected {entry.sha256} observed {observed}",
            )
        verified[entry.path] = observed
    return {
        "rule": BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE,
        "verified_by": "ALREADY_TRUSTED_CONTROLLER_CODE",
        "verified_before_subprocess_creation": True,
        "bootstrap_source_count": len(expected),
        "bootstrap_manifest_digest": (
            authority_context.worker_bootstrap_manifest_digest
        ),
        "bootstrap_source_sha256": dict(sorted(verified.items())),
        "checks": list(BOOTSTRAP_PRE_VERIFICATION_CHECKS),
    }


# ---------------------------------------------------------------------------
# Repair B and C — request construction from the trusted authority context
# ---------------------------------------------------------------------------


def build_scientific_request(
    authority_context: ScientificWorkerAuthorityContext,
    *,
    launch: WorkerLaunch,
    operation: str,
    operation_inputs: Mapping[str, Any],
    evidence_records: Sequence[Mapping[str, Any]],
    decision_time: str,
    evidence_admission_mode: str = protocol.PROTOTYPE_EVIDENCE_ADMISSION_MODE,
) -> dict[str, Any]:
    """Assemble one canonical request whose authority is copied from the context.

    There is deliberately no ``decision_sha256`` parameter, no manifest
    parameter and no bootstrap-manifest parameter.  A caller cannot select
    scientific authority, and the builder never re-derives the certified source
    manifest, the bootstrap source set or the third-party registry from live
    material.
    """

    if not isinstance(authority_context, ScientificWorkerAuthorityContext):
        raise IsolatedScientificWorkerR2Error(
            "a scientific request requires a trusted controller authority context"
        )
    expected = authority_context.expected_authority_fields()
    observations = observe_installed_distributions(
        authority_context.third_party_authority
    )
    return {
        "request_schema_version": protocol.REQUEST_SCHEMA_VERSION,
        "worker_authority_version": expected["worker_authority_version"],
        "worker_authority_ticket": expected["worker_authority_ticket"],
        "worker_authority_sha256": expected["worker_authority_sha256"],
        "authority_context_origin": authority_context.origin,
        "calendar_authority_version": expected["calendar_authority_version"],
        "calendar_authority_sha256": expected["calendar_authority_sha256"],
        "trusted_persistence_authority_sha256": expected[
            "trusted_persistence_authority_sha256"
        ],
        "interpreter_identity": dict(expected["interpreter_identity"]),
        "project_root": str(launch.project_root),
        "sys_path": list(launch.sys_path),
        "worker_entrypoint_module": expected["worker_entrypoint_module"],
        "worker_bootstrap_manifest": [
            entry.as_material() for entry in authority_context.worker_bootstrap_manifest
        ],
        "worker_bootstrap_manifest_digest": expected["worker_bootstrap_manifest_digest"],
        "project_source_manifest": [
            entry.as_material() for entry in authority_context.project_source_manifest
        ],
        "project_source_manifest_digest": expected["project_source_manifest_digest"],
        "project_source_manifest_role": expected["project_source_manifest_role"],
        "required_project_modules": list(authority_context.required_project_modules),
        "third_party_authority": [
            entry.as_material() for entry in authority_context.third_party_authority
        ],
        "third_party_authority_digest": expected["third_party_authority_digest"],
        "third_party_environment": [
            entry.as_material() for entry in observations
        ],
        "decision_time": decision_time,
        "operation": operation,
        "evidence_admission_mode": evidence_admission_mode,
        "evidence_records": [dict(record) for record in evidence_records],
        "operation_inputs": dict(operation_inputs),
    }


# ---------------------------------------------------------------------------
# Controller: pre-verify, launch, observe, admit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkerProcessOutcome:
    """Everything the controller observed about one worker process."""

    exit_status: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    request_digest: str
    bootstrap_pre_verification: Mapping[str, Any] | None = None

    @property
    def clean_termination(self) -> bool:
        return self.exit_status == 0 and not self.timed_out


@dataclass(frozen=True)
class AdmissionOutcome:
    """The controller's admission decision for one scientific worker result."""

    admitted: bool
    failure_reason: str | None
    response: Mapping[str, Any] | None
    outcome: WorkerProcessOutcome
    result: Any = None


def _spawn_unverified_worker_process(
    request: Mapping[str, Any],
    launch: WorkerLaunch,
    *,
    pycache_namespace: Path | None = None,
    bootstrap_pre_verification: Mapping[str, Any] | None = None,
) -> WorkerProcessOutcome:
    """PRIVATE / NON-AUTHORITATIVE raw subprocess helper.

    This helper performs **no** bootstrap pre-verification.  It exists only so
    that the authoritative launch path has one place to exec from, and so that
    the reviewed ``PAD4-R1`` defect can be reproduced deliberately under test.
    Scientific admission must never call it directly: ``run_scientific_worker``
    is the only supported scientific launch path, it requires the trusted
    authority context, and it makes bootstrap pre-verification unavoidable.
    """

    authorize_worker_launch_mechanism(launch.mechanism)
    payload = protocol.canonical_json_bytes(request)
    if len(payload) > protocol.MAX_REQUEST_BYTES:
        raise IsolatedScientificWorkerR2Error(
            "scientific request exceeds the frozen input-size limit"
        )
    digest = protocol.digest_bytes(payload)
    owned = pycache_namespace is None
    namespace = (
        allocate_worker_pycache_namespace(launch.pycache_namespace_root)
        if owned
        else Path(pycache_namespace).resolve()
    )
    try:
        completed = subprocess.run(
            list(launch.argv_for(namespace)),
            input=payload,
            capture_output=True,
            cwd=str(launch.cwd),
            env=dict(launch.environment),
            timeout=launch.timeout_seconds,
            close_fds=True,
        )
    except subprocess.TimeoutExpired as expired:
        return WorkerProcessOutcome(
            exit_status=None,
            timed_out=True,
            stdout=expired.stdout or b"",
            stderr=expired.stderr or b"",
            request_digest=digest,
            bootstrap_pre_verification=bootstrap_pre_verification,
        )
    finally:
        if owned:
            shutil.rmtree(namespace, ignore_errors=True)
    return WorkerProcessOutcome(
        exit_status=completed.returncode,
        timed_out=False,
        stdout=completed.stdout,
        stderr=completed.stderr,
        request_digest=digest,
        bootstrap_pre_verification=bootstrap_pre_verification,
    )


def run_scientific_worker(
    authority_context: ScientificWorkerAuthorityContext,
    request: Mapping[str, Any],
    launch: WorkerLaunch,
    *,
    pycache_namespace: Path | None = None,
) -> WorkerProcessOutcome:
    """The only supported scientific launch path.

    The trusted authority context is a required positional argument, so no
    scientific worker can be launched without it.  The frozen order is
    absolute::

        1-4  pre-verify every bootstrap source against the trusted context
        5    any mismatch -> STOP, no subprocess
        6    allocate the fresh empty bytecode-cache namespace
        7    exec the exact frozen interpreter

    A bootstrap mismatch raises before the cache namespace is allocated and
    before ``subprocess.run`` is reached, so the worker process is never
    created and no drifted bootstrap source can execute at all.
    """

    pre_verification = preverify_worker_bootstrap_sources(authority_context, launch)
    return _spawn_unverified_worker_process(
        request,
        launch,
        pycache_namespace=pycache_namespace,
        bootstrap_pre_verification=pre_verification,
    )


def verify_request_against_authority_context(
    authority_context: ScientificWorkerAuthorityContext,
    request: Mapping[str, Any],
) -> tuple[str, ...]:
    """Every material authority field of the request must be the trusted one."""

    expected = authority_context.expected_authority_fields()
    mismatched = sorted(
        name
        for name in protocol.AUTHORITY_BOUND_REQUEST_FIELDS
        if request.get(name) != expected[name]
    )
    if request.get("project_source_manifest") != [
        entry.as_material() for entry in authority_context.project_source_manifest
    ]:
        mismatched = sorted({*mismatched, "project_source_manifest"})
    if request.get("worker_bootstrap_manifest") != [
        entry.as_material() for entry in authority_context.worker_bootstrap_manifest
    ]:
        mismatched = sorted({*mismatched, "worker_bootstrap_manifest"})
    if request.get("third_party_authority") != [
        entry.as_material() for entry in authority_context.third_party_authority
    ]:
        mismatched = sorted({*mismatched, "third_party_authority"})
    if request.get("authority_context_origin") != authority_context.origin:
        mismatched = sorted({*mismatched, "authority_context_origin"})
    return tuple(mismatched)


def verify_response_against_authority_context(
    authority_context: ScientificWorkerAuthorityContext,
    response: Mapping[str, Any],
) -> tuple[str, ...]:
    """Every material authority field of the response must be the trusted one."""

    expected = authority_context.expected_authority_fields()
    return tuple(
        sorted(
            name
            for name in protocol.AUTHORITY_BOUND_RESPONSE_FIELDS
            if response.get(name) != expected[name]
        )
    )


def admit_worker_result(
    authority_context: ScientificWorkerAuthorityContext,
    request: Mapping[str, Any],
    outcome: WorkerProcessOutcome,
) -> AdmissionOutcome:
    """Admit a result only when request, response and trusted context agree."""

    def refuse(
        reason: str, response: Mapping[str, Any] | None = None
    ) -> AdmissionOutcome:
        return AdmissionOutcome(False, reason, response, outcome)

    drifted = verify_request_against_authority_context(authority_context, request)
    if drifted:
        return refuse(f"REQUEST_AUTHORITY_MISMATCH:{list(drifted)!r}")
    if outcome.timed_out:
        return refuse("WORKER_TIMEOUT")
    if outcome.exit_status != 0:
        return refuse(f"WORKER_EXIT_STATUS_{outcome.exit_status}")
    if len(outcome.stdout) > protocol.MAX_RESPONSE_BYTES:
        return refuse("WORKER_OUTPUT_EXCEEDS_THE_FROZEN_LIMIT")
    if not outcome.stdout.endswith(b"\n") or outcome.stdout.count(b"\n") != 1:
        return refuse("WORKER_STDOUT_IS_NOT_EXACTLY_ONE_PROTOCOL_PAYLOAD")
    try:
        parsed = protocol.validate_response(
            protocol.parse_canonical_json(outcome.stdout[:-1])
        )
    except protocol.ScientificWorkerProtocolError as error:
        return refuse(f"WORKER_PROTOCOL_ERROR:{error.reason}")
    if parsed["status"] != protocol.SUCCESS:
        return refuse(f"WORKER_REFUSED:{parsed['failure_reason']}", parsed)

    unbound = verify_response_against_authority_context(authority_context, parsed)
    if unbound:
        return refuse(f"RESPONSE_AUTHORITY_MISMATCH:{list(unbound)!r}", parsed)

    echoed = {
        "request_schema_version": request["request_schema_version"],
        "request_digest": outcome.request_digest,
        "authority_context_origin": request["authority_context_origin"],
        "operation": request["operation"],
        "evidence_admission_mode": request["evidence_admission_mode"],
        "decision_time": request["decision_time"],
    }
    mismatched = sorted(
        name for name, value in echoed.items() if parsed.get(name) != value
    )
    if mismatched:
        return refuse(f"WORKER_BINDING_MISMATCH:{mismatched!r}", parsed)
    if parsed["sys_path_digest"] != protocol.digest_payload(list(request["sys_path"])):
        return refuse("WORKER_SYS_PATH_MISMATCH", parsed)
    if parsed["bootstrap_defence_in_depth_verification"] != "PASS":
        return refuse("WORKER_BOOTSTRAP_DEFENCE_IN_DEPTH_FAILED", parsed)
    if parsed["bytecode_cache_binding"] != "PASS":
        return refuse("WORKER_BYTECODE_CACHE_BINDING_FAILED", parsed)
    if parsed["third_party_installed_content_verification"] != "PASS":
        return refuse("WORKER_THIRD_PARTY_CONTENT_VERIFICATION_FAILED", parsed)
    if parsed["post_execution_source_verification"] != "PASS":
        return refuse("WORKER_POST_EXECUTION_VERIFICATION_FAILED", parsed)
    if parsed["one_request_one_process"] is not True:
        return refuse("WORKER_DID_NOT_DECLARE_ONE_REQUEST_ONE_PROCESS", parsed)
    if parsed["result_digest"] != protocol.result_digest(parsed["result"]):
        return refuse("WORKER_RESULT_DIGEST_MISMATCH", parsed)
    try:
        protocol.assert_address_free(parsed)
    except protocol.ScientificWorkerProtocolError as error:
        return refuse(f"WORKER_EVIDENCE_NOT_ADDRESS_FREE:{error.reason}", parsed)
    return AdmissionOutcome(True, None, parsed, outcome, parsed["result"])


def run_isolated_scientific_request(
    authority_context: ScientificWorkerAuthorityContext,
    request: Mapping[str, Any],
    launch: WorkerLaunch,
    *,
    pycache_namespace: Path | None = None,
) -> AdmissionOutcome:
    """The authoritative end-to-end scientific path: pre-verify, run, admit."""

    return admit_worker_result(
        authority_context,
        request,
        run_scientific_worker(
            authority_context, request, launch, pycache_namespace=pycache_namespace
        ),
    )


def scientific_response_evidence(
    authority_context: ScientificWorkerAuthorityContext, admission: AdmissionOutcome
) -> dict[str, Any]:
    """Deterministic, address-free evidence for one scientific worker decision."""

    response = admission.response or {}
    pre_verification = admission.outcome.bootstrap_pre_verification or {}
    evidence = {
        "trusted_authority_context": authority_context.as_evidence(),
        "bootstrap_pre_execution_source_binding": {
            "rule": pre_verification.get("rule"),
            "verified_by": pre_verification.get("verified_by"),
            "verified_before_subprocess_creation": pre_verification.get(
                "verified_before_subprocess_creation"
            ),
            "bootstrap_source_count": pre_verification.get("bootstrap_source_count"),
            "bootstrap_manifest_digest": pre_verification.get(
                "bootstrap_manifest_digest"
            ),
        },
        "worker_bootstrap_manifest_digest": response.get(
            "worker_bootstrap_manifest_digest"
        ),
        "bootstrap_defence_in_depth_verification": response.get(
            "bootstrap_defence_in_depth_verification"
        ),
        "worker_authority_hash": response.get("worker_authority_sha256"),
        "worker_authority_ticket": response.get("worker_authority_ticket"),
        "calendar_authority_hash": response.get("calendar_authority_sha256"),
        "trusted_persistence_authority_hash": response.get(
            "trusted_persistence_authority_sha256"
        ),
        "interpreter_identity": response.get("interpreter_identity"),
        "worker_source_manifest_digest": response.get(
            "project_source_manifest_digest"
        ),
        "worker_source_manifest_role": response.get("project_source_manifest_role"),
        "third_party_authority_digest": response.get("third_party_authority_digest"),
        "third_party_observed_content_manifest_digest": response.get(
            "third_party_observed_content_manifest_digest"
        ),
        "third_party_installed_content_verification": response.get(
            "third_party_installed_content_verification"
        ),
        "bytecode_cache_binding": response.get("bytecode_cache_binding"),
        "request_schema_version": response.get("request_schema_version"),
        "request_digest": admission.outcome.request_digest,
        "operation": response.get("operation"),
        "result_digest": response.get("result_digest"),
        "process_exit_status": admission.outcome.exit_status,
        "process_timed_out": admission.outcome.timed_out,
        "admitted": admission.admitted,
        "failure_reason": admission.failure_reason,
        "decision_time": response.get("decision_time"),
    }
    protocol.assert_address_free(evidence)
    return evidence


# ---------------------------------------------------------------------------
# Preserved static authority
# ---------------------------------------------------------------------------

compiled_root_binding_witness = r1.compiled_root_binding_witness
direct_dependency_body_findings = r1.direct_dependency_body_findings


def verify_current_production_expected_result(source: str) -> dict[str, Any]:
    """The preserved current-production claim, freshly bound under this parent."""

    produced = dict(r1.verify_current_production_expected_result(source))
    produced["bootstrap_pre_execution_source_binding_in_production"] = False
    return produced


def audit_authoritative_worker_source(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """The whole bootstrap set must be closed against project code.

    ``PAD4-R1`` scoped this audit to two filenames.  The review showed the
    bootstrap surface is wider than those two, so the audit now covers the
    complete mechanically derived bootstrap source set.
    """

    audit = audit_bootstrap_source_set(project_root)
    return {
        "authoritative_worker_source": list(protocol.AUTHORITATIVE_WORKER_SOURCE),
        "source_sha256": dict(audit["source_sha256"]),
        "deferred_certified_project_imports": dict(
            audit["deferred_certified_project_imports"]
        ),
        "findings": list(audit["findings"]),
        "closed": audit["closed"],
    }


def certified_universe_closed_worker_rule_modules(
    project_root: Path = PROJECT_ROOT,
    entries: Sequence[protocol.ProjectSourceEntry] | None = None,
) -> tuple[str, ...]:
    """Certified modules containing a construct the closed worker rule forbids.

    Recorded as a *verified current-source fact* about the present universe,
    never as an eternal universal claim.  Enforcement is the statically audited
    bootstrap source set plus the ``UNEXPECTED_PROJECT_MODULE`` refusal.
    """

    manifest = frozen_candidate_source_manifest() if entries is None else entries
    return r1.certified_universe_closed_worker_rule_modules(project_root, manifest)


# ---------------------------------------------------------------------------
# Material children
# ---------------------------------------------------------------------------


def bootstrap_pre_execution_source_binding_rule() -> dict[str, Any]:
    """The correction — already-trusted code binds bootstrap source first."""

    return _definition(
        {
            "contract_version": BOOTSTRAP_PRE_VERIFICATION_VERSION,
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[0],
            "reviewed_parent": FAILED_PAD4_R1_SHA256,
            "review": FAILED_PAD4_R1_REVIEW,
            "review_result": FAILED_PAD4_R1_REVIEW_RESULT,
            "defect": (
                "the controller allocated the cache namespace, built the launch "
                "material and exec'd the entrypoint path directly; the frozen "
                "expected manifest was compared against disk inside the worker "
                "by the worker's own protocol module, so every module that had "
                "to execute to reach that comparison was outside it"
            ),
            "defect_class": "AUTHORITY_ORDERING",
            "isolation_boundary_was_the_defect": False,
            "rule": BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE,
            "bootstrap_source_preverified_by_trusted_controller": True,
            "bootstrap_mismatch_spawns_worker": False,
            "bootstrap_mismatch_allocates_a_cache_namespace": False,
            "trusted_controller_order": [
                "1_RECEIVE_THE_TRUSTED_SCIENTIFIC_WORKER_AUTHORITY_CONTEXT",
                "2_OBTAIN_THE_EXPECTED_BOOTSTRAP_MANIFEST_PATHS_AND_SHA_IDENTITIES",
                "3_RESOLVE_EACH_EXPECTED_BOOTSTRAP_SOURCE_BENEATH_THE_CERTIFIED_ROOT",
                "4_READ_THE_EXACT_SOURCE_BYTES",
                "5_COMPUTE_SHA256",
                "6_COMPARE_PATH_AND_SHA_AGAINST_THE_TRUSTED_EXPECTED_AUTHORITY",
                "7_REFUSE_IMMEDIATELY_ON_ANY_MISMATCH",
                "8_ONLY_THEN_ALLOCATE_THE_FRESH_PYCACHE_NAMESPACE_AND_EXEC",
            ],
            "per_source_checks": list(BOOTSTRAP_PRE_VERIFICATION_CHECKS),
            "rejected_stable_pre_launch_substitutions": [
                "ALTERNATE_FILE",
                "ALTERNATE_PROJECT_ROOT",
                "SOURCELESS_REPLACEMENT",
                "WRONG_ENTRYPOINT",
                "WRONG_PACKAGE_INITIALIZER",
                "WRONG_PROTOCOL",
            ],
            "module_name_alone_is_sufficient_identity": False,
            "path_and_content_identity_required": True,
            "bootstrap_self_verification_is_authority": False,
            "entrypoint_self_verification_is_authority": False,
            "protocol_self_verification_is_authority": False,
            "package_initializer_self_verification_is_authority": False,
            "in_worker_bootstrap_checks_retained_as": (
                protocol.BOOTSTRAP_SELF_VERIFICATION_ROLE
            ),
            "authoritative_worker_launch_requires_trusted_context": True,
            "authoritative_launch_api": "run_scientific_worker",
            "authoritative_end_to_end_api": "run_isolated_scientific_request",
            "private_non_authoritative_raw_subprocess_helper": (
                "_spawn_unverified_worker_process"
            ),
            "scientific_admission_may_use_the_private_helper": False,
            "supported_launch_path_without_the_trusted_context": False,
            "reproduced_pad4_r1_defect": {
                "entrypoint_drift_marker": "PRESENT",
                "entrypoint_drift_fabricated_result": "ADMITTED",
                "protocol_drift_marker": "PRESENT",
                "protocol_drift_fabricated_result": "ADMITTED",
                "reproduced_through": "_spawn_unverified_worker_process",
            },
            "corrected_behaviour": {
                "entrypoint_drift_marker": "ABSENT",
                "entrypoint_drift_subprocess": "NEVER_SPAWNED",
                "package_initializer_drift_marker": "ABSENT",
                "package_initializer_drift_subprocess": "NEVER_SPAWNED",
                "protocol_drift_marker": "ABSENT",
                "protocol_drift_subprocess": "NEVER_SPAWNED",
                "fabricated_response_emitted": False,
                "fabricated_result_admitted": False,
            },
            "an_eventual_worker_refusal_is_sufficient": False,
            "hostile_filesystem_race_resistance_claimed": False,
        }
    )


def bootstrap_source_set() -> dict[str, Any]:
    """The complete, mechanically derived pre-trust bootstrap source set."""

    audit = audit_bootstrap_source_set()
    frozen = frozen_bootstrap_source_manifest()
    completeness = verify_frozen_bootstrap_set_is_complete()
    return _definition(
        {
            "contract_version": BOOTSTRAP_SOURCE_SET_VERSION,
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[1],
            "definition": (
                "every project-owned source file that can execute before the "
                "scientific verifier is trustworthy"
            ),
            "derivation_rule": (
                "TRANSITIVE_MODULE_LEVEL_PROJECT_IMPORT_CLOSURE_OF_THE_EXEC_D_"
                "ENTRYPOINT_PLUS_ANCESTOR_PACKAGES"
            ),
            "mechanically_derivable": True,
            "hand_maintained_filename_list": False,
            "limited_to_the_two_p0_filenames": False,
            "bootstrap_source_set_complete": True,
            "bootstrap_source_count": completeness["bootstrap_source_count"],
            "bootstrap_manifest_digest": completeness["bootstrap_manifest_digest"],
            "bootstrap_execution_order": list(BOOTSTRAP_EXECUTION_ORDER),
            "entries": [entry.as_material() for entry in frozen],
            "package_initializer_included": True,
            "package_initializer_inclusion_reason": (
                "importing the worker protocol executes "
                f"{WORKER_PACKAGE_RELATIVE_PATH} first, and PAD4-R1 covered it by "
                "neither worker_entrypoint_sha256 nor worker_protocol_sha256"
            ),
            "reused_reviewed_protocol_included": True,
            "reused_reviewed_protocol_inclusion_reason": (
                "the reviewed PAD4-R1 protocol implementation is reused rather "
                "than forked, so it executes during bootstrap and is "
                "pre-verified with the rest of the set"
            ),
            "every_member_is_also_a_certified_manifest_member": True,
            "bootstrap_manifest_is_a_second_weaker_source_of_truth": False,
            "closure_properties_proven": [
                "EVERY_DEFERRED_PROJECT_IMPORT_IS_A_CERTIFIED_MANIFEST_MEMBER",
                "NO_MODULE_LEVEL_NON_STDLIB_IMPORT_EXECUTES_BEFORE_ATTESTATION",
                "NO_MODULE_LEVEL_PROJECT_IMPORT_ESCAPES_THE_BOOTSTRAP_SET",
            ],
            "deferred_certified_project_imports": dict(
                audit["deferred_certified_project_imports"]
            ),
            "execution_order_proof": dict(audit["execution_order_proof"]),
            "certified_source_outside_the_bootstrap_set_executes_before_verification": (
                False
            ),
            "closed_worker_coding_rule_scope": list(
                protocol.AUTHORITATIVE_WORKER_SOURCE
            ),
            "closed_worker_coding_rule_scope_was_two_filenames": True,
            "source_sha256": dict(audit["source_sha256"]),
            "findings": list(audit["findings"]),
            "closed": audit["closed"],
            "i2_must_rederive_the_bootstrap_set_after_its_source_changes": True,
        }
    )


def trusted_process_and_isolation_boundary() -> dict[str, Any]:
    return _revised(
        r1.trusted_process_and_isolation_boundary(),
        contract_version=(
            "ETF_CALENDAR_TRUSTED_PROCESS_AND_ISOLATION_BOUNDARY_V1_PAD4_R2"
        ),
        isolation_boundary_preserved_from_the_reviewed_pad4_candidate=True,
        isolation_boundary_independently_reproduced_again_by=FAILED_PAD4_R1_REVIEW,
        abandoned_completeness_models=list(NOT_REOPENED),
        trusted_once=[
            "BOOTSTRAP_SOURCE_PRE_EXECUTION_BINDING_PASSES",
            "CERTIFIED_PROJECT_SOURCE_ADMISSION_PASSES",
            "CERTIFIED_THIRD_PARTY_INSTALLED_CONTENT_ADMISSION_PASSES",
            "FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE_PASSES",
            "FROZEN_INTERPRETER_IDENTITY_PASSES",
        ],
        bootstrap_source_executes_before_it_is_trusted=False,
        preserved_valid_portions=list(PRESERVED_VALID_PORTIONS),
    )


def proof_interpreter_identity() -> dict[str, Any]:
    return _revised(
        r1.proof_interpreter_identity(),
        contract_version="ETF_CALENDAR_PROOF_INTERPRETER_IDENTITY_V1_PAD4_R2",
        frozen_identity=dict(verify_worker_protocol_binds_the_frozen_interpreter()),
    )


def worker_launch_contract() -> dict[str, Any]:
    return _revised(
        r1.worker_launch_contract(),
        contract_version=WORKER_LAUNCH_CONTRACT,
        bootstrap_source_preverified_before_launch=True,
        bootstrap_pre_verification_precedes_cache_namespace_allocation=True,
        launch_without_the_trusted_authority_context_permitted=False,
        authoritative_launch_api="run_scientific_worker",
        private_non_authoritative_raw_subprocess_helper=(
            "_spawn_unverified_worker_process"
        ),
        pycache_prefix_launch_design_redesigned_by_this_correction=False,
    )


def bytecode_execution_binding_rule() -> dict[str, Any]:
    return _revised(
        r1.bytecode_execution_binding_rule(),
        contract_version=(
            "ETF_CALENDAR_WORKER_BYTECODE_EXECUTION_BINDING_RULE_V1_PAD4_R2"
        ),
        independently_reproduced_as_valid_by=FAILED_PAD4_R1_REVIEW,
        redesigned_by_this_correction=False,
        entrypoint_bytecode_reason=(
            "a worker entrypoint executes as __main__ from its source path, "
            "which CPython never serves from a bytecode cache; that is a "
            "statement about the entrypoint's bytecode, never about its source "
            "identity, which the trusted controller binds before exec"
        ),
    )


def controller_authority_context_rule() -> dict[str, Any]:
    return _revised(
        r1.controller_authority_context_rule(),
        contract_version=AUTHORITY_CONTEXT_VERSION,
        independently_reproduced_as_valid_for_its_stated_scope_by=(
            FAILED_PAD4_R1_REVIEW
        ),
        stated_scope_limit_found_by_the_review=(
            "worker-visible authority fields are derivable from the supplied "
            "request, so the context could not by itself close bootstrap "
            "ordering; the pre-execution binding closes it in the controller"
        ),
        trusted_expected_values=[
            "calendar_authority_identity",
            "certified_project_source_manifest",
            "certified_project_source_manifest_digest",
            "certified_third_party_semantic_and_artifact_authority",
            "certified_worker_proof_architecture_identity",
            "complete_worker_bootstrap_source_manifest",
            "frozen_interpreter_identity",
            "trusted_persistence_identity",
        ],
        authority_bound_request_fields=list(
            protocol.AUTHORITY_BOUND_REQUEST_FIELDS
        ),
        authority_bound_response_fields=list(
            protocol.AUTHORITY_BOUND_RESPONSE_FIELDS
        ),
        bootstrap_manifest_is_trusted_context_material=True,
        bootstrap_manifest_may_come_from_the_request=False,
        raw_caller_supplied_bootstrap_manifest_parameter=False,
        candidate_review_context_accepts_any_well_formed_sha=True,
        candidate_review_context_accepts_any_well_formed_sha_classification=(
            "REPRODUCED_AND_RECLASSIFIED_AS_NOT_A_DEFECT"
        ),
        candidate_review_context_accepts_any_well_formed_sha_reason=(
            "constraining the constructor to one literal value is exactly the "
            "self-hash fixed point this architecture refuses; the hash's trust "
            "comes from the caller being the trusted review or controller "
            "context, which POSTP1-002V2A-PAD4 required and "
            "POSTP1-002V2A-PAD4-R1 reproduced as valid, and the production "
            "context is derived from the final calendar authority instead"
        ),
        final_production_context_must_bind_the_bootstrap_manifest=True,
    )


def project_source_manifest_binding_rule() -> dict[str, Any]:
    return _revised(
        r1.project_source_manifest_binding_rule(),
        contract_version=(
            "ETF_CALENDAR_WORKER_PROJECT_SOURCE_MANIFEST_BINDING_RULE_V1_PAD4_R2"
        ),
        manifest_version=WORKER_SOURCE_MANIFEST_VERSION,
        independently_reproduced_as_valid_for_ordinary_certified_source_by=(
            FAILED_PAD4_R1_REVIEW
        ),
        incomplete_for_the_pre_trust_bootstrap_sources_in_pad4_r1=True,
        pre_trust_bootstrap_sources_now_bound_by=BOOTSTRAP_SOURCE_SET_VERSION,
        bootstrap_sources_are_also_certified_manifest_members=True,
        verified_before_scientific_execution=True,
        verified_by_code_that_has_already_executed=False,
    )


def pre_i2_project_source_manifest_fixture() -> dict[str, Any]:
    fixture = frozen_pre_i2_source_manifest()
    candidate = frozen_candidate_source_manifest()
    verify_frozen_pre_i2_fixture()
    return _revised(
        r1.pre_i2_project_source_manifest_fixture(),
        candidate_worker_source_universe={
            "seed_entrypoint": WORKER_ENTRYPOINT_MODULE,
            "module_count": len(candidate),
            "manifest_digest": protocol.manifest_digest(candidate),
            "entries": [entry.as_material() for entry in candidate],
        },
        reviewed_pre_i2_source_universe={
            "seed_entrypoint": PRE_I2_FIXTURE_SEED_MODULE,
            "module_count": len(fixture),
            "manifest_digest": protocol.manifest_digest(fixture),
            "entries": [entry.as_material() for entry in fixture],
        },
        required_loaded_modules=list(REQUIRED_WORKER_PROJECT_MODULES),
        worker_bootstrap_source_set=list(WORKER_BOOTSTRAP_RELATIVE_PATHS),
        i2_must_rederive_the_bootstrap_set_after_its_source_changes=True,
    )


def third_party_semantic_authority() -> dict[str, Any]:
    return _revised(
        r1.third_party_semantic_authority(),
        contract_version=THIRD_PARTY_REGISTRY_VERSION,
        independently_reproduced_as_valid_by=FAILED_PAD4_R1_REVIEW,
        changed_by_this_correction=False,
    )


def third_party_installed_content_attestation_rule() -> dict[str, Any]:
    return _revised(
        r1.third_party_installed_content_attestation_rule(),
        contract_version=(
            "ETF_CALENDAR_WORKER_THIRD_PARTY_INSTALLED_CONTENT_RULE_V1_PAD4_R2"
        ),
        independently_reproduced_as_valid_by=FAILED_PAD4_R1_REVIEW,
        changed_by_this_correction=False,
        # POSTP1-002V2A-PAD4-R1 secondary P3 candidate: the PAD4-R1 wording said
        # "importing btc_predictor" executes the four distributions.  Reproduced
        # mechanically: importing the top-level btc_predictor namespace alone
        # executes none of them; importing btc_predictor.research, which every
        # frozen operation requires, executes all four.  This is a documentation
        # wording correction only and changes no proof architecture.
        worker_protocol_placement_reason=(
            "importing the btc_predictor.research package every frozen operation "
            "requires executes numpy, scipy, sqlalchemy and alembic through the "
            "package re-export graph, so a protocol module under btc_predictor "
            "could only attest dependencies after they had already executed"
        ),
        worker_protocol_placement_reason_correction=(
            "MECHANICAL_WORDING_ONLY: the top-level btc_predictor namespace "
            "alone executes none of the four; btc_predictor.research executes "
            "all four"
        ),
        worker_protocol_placement_reason_alters_proof_architecture=False,
    )


def dynamic_import_and_execution_prohibition() -> dict[str, Any]:
    audit = audit_authoritative_worker_source()
    reviewed = r1.dynamic_import_and_execution_prohibition()
    flagged = certified_universe_closed_worker_rule_modules()
    return _revised(
        reviewed,
        contract_version="ETF_CALENDAR_WORKER_DYNAMIC_IMPORT_PROHIBITION_V1_PAD4_R2",
        scope="COMPLETE_WORKER_BOOTSTRAP_SOURCE_SET",
        scope_was_two_filenames_in_pad4_r1=True,
        authoritative_worker_source=list(audit["authoritative_worker_source"]),
        authoritative_worker_source_sha256=dict(audit["source_sha256"]),
        deferred_certified_project_imports=dict(
            audit["deferred_certified_project_imports"]
        ),
        current_certified_source_scan={
            **reviewed["current_certified_source_scan"],
            "modules_scanned": len(frozen_candidate_source_manifest()),
            "modules_containing_a_closed_worker_rule_construct": len(flagged),
            "modules": list(flagged),
        },
        current_findings=list(audit["findings"]),
        closed=audit["closed"],
    )


def scientific_request_protocol() -> dict[str, Any]:
    return _revised(
        r1.scientific_request_protocol(),
        contract_version=protocol.REQUEST_SCHEMA_VERSION,
        fields=sorted(protocol.REQUEST_FIELDS),
        authority_bound_fields=list(protocol.AUTHORITY_BOUND_REQUEST_FIELDS),
        caller_may_supply_a_worker_bootstrap_manifest=False,
        bootstrap_manifest_is_copied_from_the_trusted_context=True,
        replaced_pad4_r1_fields=list(protocol._REPLACED_REQUEST_FIELDS),
        replaced_pad4_r1_fields_reason=(
            "worker_entrypoint_sha256 and worker_protocol_sha256 omitted the "
            "package initializer and were verified by code that had already "
            "run; the complete bootstrap manifest replaces them"
        ),
    )


def scientific_response_protocol() -> dict[str, Any]:
    return _revised(
        r1.scientific_response_protocol(),
        contract_version=protocol.RESPONSE_SCHEMA_VERSION,
        fields=sorted(protocol.RESPONSE_FIELDS),
        authority_bound_fields=list(protocol.AUTHORITY_BOUND_RESPONSE_FIELDS),
        worker_bootstrap_self_verification_is_authority=False,
        worker_bootstrap_self_verification_role=(
            protocol.BOOTSTRAP_SELF_VERIFICATION_ROLE
        ),
        evidence_fields=[
            "admitted",
            "bootstrap_defence_in_depth_verification",
            "bootstrap_pre_execution_source_binding",
            "bytecode_cache_binding",
            "calendar_authority_hash",
            "decision_time",
            "failure_reason",
            "interpreter_identity",
            "operation",
            "process_exit_status",
            "request_digest",
            "request_schema_version",
            "result_digest",
            "third_party_authority_digest",
            "third_party_installed_content_verification",
            "third_party_observed_content_manifest_digest",
            "trusted_authority_context",
            "trusted_persistence_authority_hash",
            "worker_authority_hash",
            "worker_authority_ticket",
            "worker_bootstrap_manifest_digest",
            "worker_source_manifest_digest",
            "worker_source_manifest_role",
        ],
    )


def worker_io_and_capability_boundary() -> dict[str, Any]:
    return _revised(
        r1.worker_io_and_capability_boundary(),
        contract_version="ETF_CALENDAR_WORKER_IO_AND_CAPABILITY_BOUNDARY_V1_PAD4_R2",
        changed_by_this_correction=False,
    )


def compiled_root_binding_witness_rule() -> dict[str, Any]:
    return _revised(
        r1.compiled_root_binding_witness_rule(),
        contract_version=(
            "ETF_CALENDAR_COMPILED_ROOT_BINDING_WITNESS_RULE_V1_PAD4_R2"
        ),
        freshly_parent_bound_by=f"{DECISION_VERSION}_{PROGRAM_TICKET}",
        failed_pad4_r1_parent_certified=False,
    )


def store_root_and_direct_use_grammar() -> dict[str, Any]:
    return _revised(
        r1.store_root_and_direct_use_grammar(),
        contract_version=(
            "ETF_CALENDAR_STORE_ROOT_AND_DIRECT_USE_GRAMMAR_V1_PAD4_R2"
        ),
        freshly_parent_bound_by=f"{DECISION_VERSION}_{PROGRAM_TICKET}",
    )


def replay_owner_graph_rule() -> dict[str, Any]:
    return _revised(
        r1.replay_owner_graph_rule(),
        contract_version="ETF_CALENDAR_REPLAY_OWNER_GRAPH_RULE_V1_PAD4_R2",
        bootstrap_pre_execution_binding_redefines_the_owner_graph=False,
    )


def direct_body_dependency_rule() -> dict[str, Any]:
    return _revised(
        r1.direct_body_dependency_rule(),
        contract_version="ETF_CALENDAR_DIRECT_BODY_DEPENDENCY_RULE_V1_PAD4_R2",
        freshly_parent_bound_by=f"{DECISION_VERSION}_{PROGRAM_TICKET}",
    )


def controller_result_admission_rule() -> dict[str, Any]:
    return _revised(
        r1.controller_result_admission_rule(),
        contract_version=(
            "ETF_CALENDAR_CONTROLLER_RESULT_ADMISSION_RULE_V1_PAD4_R2"
        ),
        admission_requires_all_three=[
            "REQUEST_AGREES_WITH_THE_TRUSTED_AUTHORITY_CONTEXT",
            "RESPONSE_AGREES_WITH_THE_TRUSTED_AUTHORITY_CONTEXT",
            "RESPONSE_CROSS_BINDS_TO_THE_REQUEST",
        ],
        admission_is_preceded_by_bootstrap_pre_execution_binding=True,
        validated_before_admission=[
            "bootstrap_defence_in_depth_verification",
            "bootstrap_pre_execution_source_binding",
            "bytecode_cache_binding",
            "clean_process_termination",
            "interpreter_identity",
            "operation_identity",
            "request_authority_context_agreement",
            "request_digest_cross_binding",
            "response_authority_context_agreement",
            "response_schema_version",
            "result_digest",
            "success_status",
            "third_party_installed_content_verification",
            "worker_authority_identity",
            "worker_bootstrap_manifest_identity",
            "worker_source_manifest_identity",
        ],
        an_eventual_worker_refusal_replaces_pre_execution_binding=False,
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    return _revised(
        r1.proof_order_and_completeness_definition(),
        contract_version="ETF_CALENDAR_ISOLATED_WORKER_PROOF_ORDER_V1_PAD4_R2",
        controller_or_review_order=[
            "1_LOAD_THE_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT",
            "2_ESTABLISH_THE_EXPECTED_BOOTSTRAP_SOURCE_SET",
            "3_RESOLVE_READ_AND_HASH_EVERY_BOOTSTRAP_SOURCE",
            "4_COMPARE_EVERY_BOOTSTRAP_PATH_AND_SHA_WITH_THE_TRUSTED_AUTHORITY",
            "5_ANY_MISMATCH_STOP_WITH_NO_SUBPROCESS",
            "6_ALLOCATE_THE_FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE",
            "7_EXEC_THE_EXACT_FROZEN_INTERPRETER",
        ],
        worker_order=[
            "8_VERIFY_INTERPRETER_STARTUP_AND_PYCACHE_CONTROLS",
            "9_PARSE_THE_CANONICAL_REQUEST",
            "10_DEFENCE_IN_DEPTH_SOURCE_CHECKS",
            "11_VERIFY_THE_THIRD_PARTY_ENVIRONMENT_BEFORE_DEPENDENCY_CODE",
            "12_ESTABLISH_CERTIFIED_PROJECT_IMPORTS",
            "13_EXECUTE_EXACTLY_ONE_SCIENTIFIC_OPERATION",
            "14_REFUSE_A_LAZY_RESULT",
            "15_POST_VERIFY",
            "16_EMIT_THE_CANONICAL_RESULT",
            "17_EXIT",
        ],
        controller_admission_order=[
            "18_VERIFY_PROCESS_SUCCESS",
            "19_VERIFY_REQUEST_EQUALS_THE_TRUSTED_CONTEXT",
            "20_VERIFY_RESPONSE_EQUALS_THE_TRUSTED_CONTEXT",
            "21_VERIFY_RESPONSE_EQUALS_REQUEST",
            "22_VERIFY_THE_RESULT_DIGEST",
            "23_ADMIT",
        ],
        no_bootstrap_project_source_executes_before_step_4_succeeds=True,
        no_scientific_call_before_self_verification_passes=True,
        completeness_claim=(
            "the scientific answer is produced by certified source whose "
            "pre-trust bootstrap set was bound by already-trusted controller "
            "code before any of it executed, executed as certified bytecode, "
            "under a certified interpreter, against a reviewed third-party "
            "artifact whose installed bytes were verified first, in a process "
            "that shares no mutable Python state with the application, and "
            "every material authority identity reproduces against a trusted "
            "controller context"
        ),
        required_adversarial_regressions=sorted(
            {
                *r1.proof_order_and_completeness_definition()[
                    "required_adversarial_regressions"
                ],
                "PRE_LAUNCH_ENTRYPOINT_DRIFT_NEVER_SPAWNS_THE_WORKER",
                "PRE_LAUNCH_ENTRYPOINT_DRIFT_MARKER_IS_ABSENT",
                "PRE_LAUNCH_PACKAGE_INITIALIZER_DRIFT_NEVER_SPAWNS_THE_WORKER",
                "PRE_LAUNCH_PACKAGE_INITIALIZER_DRIFT_MARKER_IS_ABSENT",
                "PRE_LAUNCH_PROTOCOL_DRIFT_NEVER_SPAWNS_THE_WORKER",
                "PRE_LAUNCH_PROTOCOL_DRIFT_MARKER_IS_ABSENT",
                "FABRICATED_BOOTSTRAP_SUCCESS_IS_NEVER_EMITTED_OR_ADMITTED",
                "ALTERNATE_WORKER_PACKAGE_ROOT_SHADOW_REFUSES",
                "SOURCELESS_BOOTSTRAP_REPLACEMENT_REFUSES",
                "CLEAN_POSITIVE_BOOTSTRAP_CONTROL_IS_ADMITTED",
            }
        ),
    )


def science_lineage_and_safety() -> dict[str, Any]:
    payload = r1.science_lineage_and_safety()
    return _revised(
        payload,
        contract_version=(
            "ETF_CALENDAR_ISOLATED_WORKER_SCIENCE_LINEAGE_AND_SAFETY_V1_PAD4_R2"
        ),
        failed_architecture_lineage=[
            {
                "definition_sha256": sha,
                "certified": False,
                "failed": True,
                "used": False,
                "prospective_observations": 0,
                "superseded_before_use": True,
                "immutable": True,
            }
            for sha in FAILED_ARCHITECTURE_LINEAGE
        ],
        corrected_predecessor={
            "definition_sha256": FAILED_PAD4_R1_SHA256,
            "decision_commit": FAILED_PAD4_R1_DECISION_COMMIT,
            "review": FAILED_PAD4_R1_REVIEW,
            "review_commit": FAILED_PAD4_R1_REVIEW_COMMIT,
            "review_result": FAILED_PAD4_R1_REVIEW_RESULT,
            "artifacts_overwritten_by_this_correction": False,
            "certified": False,
            "used": False,
            "prospective_observations": 0,
        },
    )


_CHILD_ARTIFACTS: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
    (
        "bootstrap_pre_execution_source_binding_rule.json",
        bootstrap_pre_execution_source_binding_rule,
    ),
    ("bootstrap_source_set.json", bootstrap_source_set),
    (
        "trusted_process_and_isolation_boundary.json",
        trusted_process_and_isolation_boundary,
    ),
    ("proof_interpreter_identity.json", proof_interpreter_identity),
    ("worker_launch_contract.json", worker_launch_contract),
    ("bytecode_execution_binding_rule.json", bytecode_execution_binding_rule),
    ("controller_authority_context_rule.json", controller_authority_context_rule),
    (
        "project_source_manifest_binding_rule.json",
        project_source_manifest_binding_rule,
    ),
    (
        "pre_i2_project_source_manifest_fixture.json",
        pre_i2_project_source_manifest_fixture,
    ),
    ("third_party_semantic_authority.json", third_party_semantic_authority),
    (
        "third_party_installed_content_attestation_rule.json",
        third_party_installed_content_attestation_rule,
    ),
    (
        "dynamic_import_and_execution_prohibition.json",
        dynamic_import_and_execution_prohibition,
    ),
    ("scientific_request_protocol.json", scientific_request_protocol),
    ("scientific_response_protocol.json", scientific_response_protocol),
    ("worker_io_and_capability_boundary.json", worker_io_and_capability_boundary),
    ("compiled_root_binding_witness_rule.json", compiled_root_binding_witness_rule),
    ("store_root_and_direct_use_grammar.json", store_root_and_direct_use_grammar),
    ("replay_owner_graph_rule.json", replay_owner_graph_rule),
    ("direct_body_dependency_rule.json", direct_body_dependency_rule),
    ("controller_result_admission_rule.json", controller_result_admission_rule),
    (
        "proof_order_and_completeness_definition.json",
        proof_order_and_completeness_definition,
    ),
    ("science_lineage_and_safety.json", science_lineage_and_safety),
)


def _children(
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, dict[str, Any]]:
    """Build every material child from one explicit registry of callables."""

    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    return {filename.removesuffix(".json"): builder() for filename, builder in registry}


# ---------------------------------------------------------------------------
# Decision parent
# ---------------------------------------------------------------------------


def isolated_scientific_worker_v1_r2_definition(
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    source = CALENDAR_SOURCE.read_text(encoding="utf-8")
    narrow.verify_replay_owner_census(source)
    verify_worker_protocol_binds_the_frozen_interpreter()
    verify_frozen_pre_i2_fixture()
    completeness = verify_frozen_bootstrap_set_is_complete()
    production = verify_current_production_expected_result(source)
    children = _children(child_artifacts)
    fixture = frozen_pre_i2_source_manifest()
    candidate = frozen_candidate_source_manifest()
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
            "correction_of": FAILED_PAD4_R1_SHA256,
            "correction_is_a_new_architecture_family": False,
            "repaired_review_findings": list(REPAIRED_REVIEW_FINDINGS),
            "preserved_valid_portions": list(PRESERVED_VALID_PORTIONS),
            "not_reopened": list(NOT_REOPENED),
            "failed_pad4_sha256": FAILED_PAD4_SHA256,
            "failed_pad4_certified": False,
            "failed_pad4_artifacts_overwritten": False,
            "failed_pad4_r1_sha256": FAILED_PAD4_R1_SHA256,
            "failed_pad4_r1_certified": False,
            "failed_pad4_r1_artifacts_overwritten": False,
            "certified_dependency_sha256": CERTIFIED_DEPENDENCY_SHA256,
            "proof_interpreter": dict(PROOF_INTERPRETER_IDENTITY),
            "material_child_count": len(children),
            "material_child_enumeration": "MECHANICALLY_ENUMERATED_FROM_ONE_REGISTRY",
            "child_definition_sha256": {
                name: child["definition_sha256"] for name, child in children.items()
            },
            "pre_i2_project_source_manifest_digest": protocol.manifest_digest(fixture),
            "pre_i2_project_source_module_count": len(fixture),
            "pre_i2_project_source_manifest_role": PRE_I2_FIXTURE_ROLE,
            "candidate_worker_source_manifest_digest": protocol.manifest_digest(
                candidate
            ),
            "candidate_worker_source_module_count": len(candidate),
            "worker_bootstrap_manifest_digest": completeness[
                "bootstrap_manifest_digest"
            ],
            "worker_bootstrap_source_count": completeness["bootstrap_source_count"],
            "worker_bootstrap_source_set": completeness["bootstrap_source_set"],
            "third_party_authority_digest": protocol.third_party_authority_digest(
                frozen_third_party_authority()
            ),
            "central_decisions": {
                "fresh_exec_required": True,
                "one_request_one_process": True,
                "bootstrap_source_set_complete": True,
                "bootstrap_source_preverified_by_trusted_controller": True,
                "entrypoint_preverified_before_exec": True,
                "package_initializer_preverified_before_exec": True,
                "protocol_preverified_before_exec": True,
                "bootstrap_mismatch_spawns_worker": False,
                "bootstrap_self_verification_is_authority": False,
                "protocol_self_verification_is_authority": False,
                "entrypoint_self_verification_is_authority": False,
                "package_initializer_self_verification_is_authority": False,
                "authoritative_worker_launch_requires_trusted_context": True,
                "fork_only_permitted": False,
                "fresh_empty_pycache_namespace_required": True,
                "pycache_prefix_launch_design_redesigned": False,
                "repository_pycache_authoritative": False,
                "cached_bytecode_may_override_certified_source": False,
                "runtime_source_manifest_rederivation_permitted": False,
                "request_is_authority_root": False,
                "response_echo_is_authority_root": False,
                "trusted_controller_authority_context_required": True,
                "pre_i2_116_module_manifest_role": (
                    "CONFORMANCE_FIXTURE_NOT_FINAL_PRODUCTION_AUTHORITY"
                ),
                "final_i2_source_manifest_must_be_calendar_parent_bound": True,
                "third_party_exact_reviewed_versions_required": True,
                "third_party_reviewed_artifact_identity_required": True,
                "record_declared_installed_file_hashes_must_be_verified": True,
                "arbitrary_installed_version_self_certification_permitted": False,
                "pickle_ipc_permitted": False,
                "worker_network_permitted": False,
                "worker_private_signing_key_permitted": False,
                "worker_authoritative_db_write_permitted": False,
                "worker_visible_shared_secret_introduced": False,
                "lazy_result_permitted": False,
                "runtime_object_closure_is_completeness_proof": False,
                "parent_python_objects_shared": False,
                "process_isolation_is_scientific_execution_boundary": True,
                "project_source_manifest_required": True,
                "unexpected_project_module_permitted": False,
                "dynamic_project_import_permitted": False,
                "long_lived_worker_permitted": False,
                "reflection_blacklist_complete": False,
                "generated_runtime_method_enumeration_required": False,
                "transitive_mutable_object_closure_required": False,
                "compiled_root_witness_preserved": True,
                "root_may_be_a_cell_variable_of_a_conforming_owner": False,
                "closed_ast_store_use_grammar_preserved": True,
                "exact_eleven_owner_graph_preserved": True,
                "direct_body_dependency_checks_preserved": True,
                "wrapper_installed_guards_permitted": False,
                "artifact_builder_dispatch_rewrite_required_by_this_decision": False,
                "operating_system_level_network_sandbox_claimed": False,
                "hostile_filesystem_race_resistance_claimed": False,
                "hostile_operating_system_resistance_claimed": False,
                "candidate_parent_hash_self_embedded": False,
                "calendar_science_changed": False,
                "calendar_production_code_changed": False,
            },
            "current_production_expected_result": production,
            "authorization": {
                "independent_proof_architecture_xhigh_review_may_begin": True,
                "calendar_implementation_may_begin": False,
                "postp1_001v2a_i2_may_begin": False,
                "postp1_001v2r1_may_begin": False,
                "prospective_collection_may_begin": False,
            },
        }
    )


def verify_definition(persisted: Mapping[str, Any]) -> None:
    if dict(persisted) != isolated_scientific_worker_v1_r2_definition():
        raise IsolatedScientificWorkerR2Error(
            "persisted bootstrap-bound isolated scientific worker decision does "
            "not reproduce"
        )
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    owners = "\n".join(f"- `{owner}`" for owner in FROZEN_REPLAY_OWNERS)
    lineage = "\n".join(f"- `{sha}`" for sha in FAILED_ARCHITECTURE_LINEAGE)
    bootstrap = "\n".join(
        f"{index}. `{path}`"
        for index, path in enumerate(BOOTSTRAP_EXECUTION_ORDER, start=1)
    )
    interpreter = PROOF_INTERPRETER_IDENTITY
    production = decision["current_production_expected_result"]
    launch_flags = " ".join(WORKER_LAUNCH_FLAGS)
    store_apis = "`, `".join(STORE_APIS)
    dependencies = "\n".join(
        f"- `{entry.distribution}` `{entry.version}` roots "
        f"`{', '.join(entry.root_modules)}` RECORD `{entry.record_sha256}` "
        f"content `{entry.record_content_manifest_digest}`"
        for entry in frozen_third_party_authority()
    )
    return f"""# {DECISION_VERSION} — bootstrap-bound isolated one-shot scientific worker

- Ticket: `{PROGRAM_TICKET}`
- Decision hash: `{decision['definition_sha256']}`
- Corrected predecessor: `{FAILED_PAD4_R1_SHA256}` (failed, never certified, never overwritten)
- Status: `{STATUS}`
- Classification: `{FINAL_CLASSIFICATION}`
- Strategy: `{PROOF_STRATEGY}`
- Material children: {decision['material_child_count']}
- Pre-I2 source fixture: {decision['pre_i2_project_source_module_count']} modules at `{decision['pre_i2_project_source_manifest_digest']}`
- Candidate worker source universe: {decision['candidate_worker_source_module_count']} modules at `{decision['candidate_worker_source_manifest_digest']}`
- Bootstrap source set: {decision['worker_bootstrap_source_count']} files at `{decision['worker_bootstrap_manifest_digest']}`
- Third-party authority digest: `{decision['third_party_authority_digest']}`

## What this corrects, and what it does not

`{FAILED_PAD4_R1_REVIEW}` independently regenerated the exact `PAD4-R1` parent
`{FAILED_PAD4_R1_SHA256}`, reproduced 20/20 material children and 20/20 parent
bindings, and failed the candidate with `{FAILED_PAD4_R1_REVIEW_RESULT}`.

The blocking invariant was authority *ordering*, not isolation:

> Already-trusted code does not establish the certified identity of the worker
> bootstrap source before that source executes.

The controller allocated the fresh cache namespace, built the parent-bound
launch material and exec'd the entrypoint path directly. The frozen expected
manifest was compared against disk inside the worker, by the worker's own
protocol module, so every module that had to execute in order to reach that
comparison was outside it: the manifest check was the first thing the bootstrap
did, not the last thing the controller did. Two stable pre-launch drift probes
proved this was authoritative rather than merely undetected — entrypoint drift
and protocol drift each left the execution marker **PRESENT** and each had a
fabricated scientific result **ADMITTED**.

This is a bounded correction of that one ordering defect. It is deliberately
**not** a `PAD5`: no new proof-architecture family is created, the failed
`PAD4` namespace at `{FAILED_PAD4_SHA256}` and the failed `PAD4-R1` namespace
at `{FAILED_PAD4_R1_SHA256}` both keep their own untouched namespaces and both
remain failed, non-certified, unused, immutable, superseded before use and at
zero observations. Same-process runtime-object attestation is **not** reopened,
and `-X {WORKER_LAUNCH_X_OPTION}` is **not** redesigned.

These portions were independently reproduced as valid by
`{FAILED_PAD4_R1_REVIEW}` and are carried forward intact rather than rebuilt:

{chr(10).join(f'- `{name}`' for name in PRESERVED_VALID_PORTIONS)}

## The complete pre-trust bootstrap source set

The review named two filenames in its P0 findings. The corrected set is derived
mechanically instead — the transitive *module-level* project-import closure of
the exec'd entrypoint plus every ancestor package — and it is wider than two
files, in this execution order:

{bootstrap}

`etf_calendar_worker/__init__.py` is a member because importing the protocol
executes the package initializer first, and `PAD4-R1` covered it by neither
`worker_entrypoint_sha256` nor `worker_protocol_sha256`.
`etf_calendar_worker/protocol_r1.py` is a member because the reviewed `PAD4-R1`
protocol implementation is *reused rather than forked*, so it executes during
bootstrap too. Every member is also an ordinary member of the certified source
manifest with the identical path and SHA-256; the bootstrap manifest is not a
second, weaker source of truth.

Three closure properties are proven mechanically, and together they are what
makes a finite set a complete one: no bootstrap module declares a module-level
project import outside the set; no bootstrap module declares a module-level
import outside the standard library, so no third-party code can run before the
reviewed installed-content attestation; and every deferred, function-scoped
project import declared by a bootstrap module is an ordinary certified manifest
member that Repair B already covers. The closed worker-coding rule is enforced
over the whole set rather than over two filenames.

## Trusted controller pre-execution binding

```
{BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE}
```

Before a worker process can exist, already-trusted controller code receives the
trusted `ScientificWorkerAuthorityContext`, takes the expected bootstrap
manifest from it, resolves each expected source beneath the certified project
root, reads the exact bytes, computes SHA-256, compares path and SHA against the
trusted expected authority, and refuses immediately on any mismatch. Only after
every bootstrap source passes does it allocate the fresh empty bytecode-cache
namespace and exec the frozen interpreter.

    bootstrap mismatch -> the subprocess is NEVER spawned.

Per source the binding checks the expected relative path, the resolved expected
project root, the absence of any alternate source candidate, the absence of a
sourceless bytecode replacement, regular certified-source file semantics, the
absence of an earlier `sys.path` entry that would shadow the worker package,
and the exact SHA-256. Module name alone is never identity.

`run_scientific_worker(authority_context, request, launch)` is the only
supported scientific launch path and the context is a required positional
argument, so bootstrap pre-verification is unavoidable.
`_spawn_unverified_worker_process` remains as a **private, non-authoritative**
raw helper; scientific admission never uses it, and it exists so the reviewed
`PAD4-R1` defect can be reproduced deliberately under test.

## No bootstrap self-certification

```
bootstrap_self_verification_is_authority            = false
entrypoint_self_verification_is_authority           = false
protocol_self_verification_is_authority             = false
package_initializer_self_verification_is_authority  = false
```

The in-worker bootstrap checks are retained as
`{protocol.BOOTSTRAP_SELF_VERIFICATION_ROLE}`. No worker-visible shared secret
was invented as a substitute for correct pre-exec ordering.

## Frozen proof order

```
TRUSTED CONTROLLER
1  load the trusted authority context
2  establish the expected bootstrap source set
3  resolve, read and hash every bootstrap source
4  compare every path and SHA with the trusted authority
5  any mismatch -> STOP, no subprocess
6  allocate the fresh pycache namespace
7  exec the exact frozen interpreter

WORKER
8  verify interpreter and cache startup
9  parse the canonical request
10 defence-in-depth source checks
11 verify the third-party environment before dependency code
12 establish certified project imports
13 execute exactly one scientific operation
14 refuse a lazy result
15 post-verify
16 emit the canonical result
17 exit

CONTROLLER
18 verify process success
19 verify request == trusted context
20 verify response == trusted context
21 verify response == request
22 verify the result digest
23 admit
```

No bootstrap project source executes before step 4 succeeds.

## Preserved Repair A — executed bytecode is bound to certified source

Every worker still runs under `{launch_flags}` plus
`-X {WORKER_LAUNCH_X_OPTION}=<fresh empty per-worker directory>`. The namespace
is controller-created, proven empty before launch, never shared with any
repository or `site-packages` `__pycache__`, never reused between workers, never
selected from the scientific request and removed after the worker exits. A
forged repository `.pyc` is not executed, a forged third-party `.pyc` is not
executed, a pre-populated "fresh" namespace refuses and a sourceless scientific
module shadow refuses. The `-X {WORKER_LAUNCH_X_OPTION}` design is unchanged.

## Preserved Repair C — the trusted controller authority context

Admission still requires request equals context **and** response equals context
**and** response cross-binds to the request. `0000...0000` and
`deadbeef...deadbeef` still refuse. The review's secondary candidate — that
`candidate_review_authority_context` accepts any well-formed SHA — was
independently reproduced and reclassified as **not a defect**: constraining the
constructor to one literal value is exactly the self-hash fixed point this
architecture refuses, the hash's trust comes from the caller being the trusted
review or controller context, and the production context is derived from the
final calendar authority instead. `production_authority_context_from_calendar_authority`
still refuses with `{PRODUCTION_CONTEXT_NOT_YET_BOUND}`, and it now also
requires the final authority to bind the exact bootstrap manifest.

## Preserved Repair D — third-party semantic and installed-content authority

The exact reviewed registry is unchanged:

{dependencies}

Installed bytes are still verified against `RECORD` before any dependency
executes, a tampered dependency's marker stays absent, and a `99.99.99-FORGED`
version still refuses. The review's secondary P3 candidate about
`worker_protocol_placement_reason` was independently reproduced — importing the
top-level `btc_predictor` namespace alone executes none of the four
distributions, while importing `btc_predictor.research`, which every frozen
operation requires, executes all four — and corrected as a mechanical
documentation wording change that alters no proof architecture.

## Preserved static authority

Compiled root-binding witness, root-cell prohibition, closed AST store-use
grammar, the exact eleven-owner census and the documented `{store_apis}`
terminals are preserved and freshly parent-bound.

{owners}

## Failed architecture lineage, preserved and never certified

{lineage}

## Current production and authorization

No ETF calendar production code was modified. Current production still reports
compiled root write, clear or delete findings
`{production['root_write_clear_or_delete_findings']}`, the single
`{KNOWN_PRODUCTION_BLOCKER_OWNER}` generator capture, the five
wrapper-installed dependency guards and no isolated worker, so full conformance
is `{production['calendar_production_conformance']}` and calendar
implementation stays `{production['calendar_implementation']}`.

The frozen proof interpreter is
`{interpreter['implementation_name']} {interpreter['version_major']}.{interpreter['version_minor']}.{interpreter['version_micro']}`
with cache tag `{interpreter['cache_tag']}` and magic
`{interpreter['magic_number_hex']}`.

Successful implementation authorizes only `{REQUIRED_REVIEW}`. Only that review
PASS may authorize `POSTP1-001V2A-I2`, which must then bind the certified
`PAD4-R2` hash into the final calendar authority, derive and
calendar-parent-bind both the final post-I2 project source manifest **and** the
final post-I2 bootstrap source set, and refreeze
`ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` before an independent exact-hash
calendar closure review. Collection remains **NOT AUTHORIZED** and prospective
observations remain **0**.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    decision = isolated_scientific_worker_v1_r2_definition(registry)
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
            raise IsolatedScientificWorkerR2Error(
                f"persisted {filename} does not reproduce"
            )
        _verify_definition_digest(persisted)
        if decision["child_definition_sha256"].get(
            filename.removesuffix(".json")
        ) != expected["definition_sha256"]:
            raise IsolatedScientificWorkerR2Error(
                f"bootstrap-bound isolated scientific worker parent does not "
                f"bind {filename}"
            )
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise IsolatedScientificWorkerR2Error(
            "persisted bootstrap-bound isolated scientific worker report does "
            "not reproduce"
        )
    return decision


def main() -> None:  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument("output_dir", nargs="?", type=Path)
    args = parser.parse_args()
    output_dir = args.output_dir or PROJECT_ROOT / OUTPUT_NAMESPACE
    print(write_artifacts(output_dir)["definition_sha256"])


if __name__ == "__main__":  # pragma: no cover
    main()
