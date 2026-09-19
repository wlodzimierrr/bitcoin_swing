"""Isolated one-shot scientific worker proof architecture for the ETF calendar.

``POSTP1-002V2A-PAD3`` failed with ``PROJECT IMPORT EXECUTION CLOSURE
INCOMPLETE``.  A clean attestation of the eleven frozen replay owners plus the
calendar module's own functions, classes, values and imports is *not* a
completeness proof: persistently mutating ``_flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS``,
``_flow.FIVE_DAY_ETF_FLOW_FEATURE_ID``, ``_flow.EtfFlowFeatureResult``, the
``require_utc_datetime`` re-export or the dataclass-generated
``ScientificEtfFlowResult.__init__`` changes the science while the attested
surface is unchanged.

This decision therefore abandons enumeration and changes the boundary:

    do not share mutable Python scientific execution state with the
    application process

rather than

    attempt to enumerate every mutable object capable of affecting execution.

Scientific evaluation happens in a fresh, exec'd CPython 3.12.14 process with a
fresh ``sys.modules``, a certified project source/import universe, a canonical
non-executable request/response protocol and one request per process.  The
compiled root-binding witness, the root-cell prohibition, the closed AST store
grammar, the exact eleven-owner graph and the direct dependency-body rule are
preserved and freshly parent-bound; the failed PAD2 and PAD3 parents are never
certified.

This module is a pre-data decision builder, a static audit specification and a
reference controller.  It never collects, persists, signs or certifies
anything, and it changes no ETF calendar production code.
"""

from __future__ import annotations

import argparse
import ast
import json
import subprocess
import sys
import sysconfig
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from btc_predictor.research import etf_calendar_authority_boundary_r1 as _bodies
from btc_predictor.research import etf_calendar_compiled_binding_witness as witness
from btc_predictor.research import etf_calendar_runtime_owner_attestation as attestation
from btc_predictor.research import etf_calendar_store_capability_normal_form_r1 as narrow
from btc_predictor.research import etf_calendar_worker_protocol as protocol


DECISION_VERSION = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
PROGRAM_TICKET = "POSTP1-001V2A-PAD4"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_isolated_scientific_worker_v1"
DEFINITION_FILENAME = "etf_calendar_isolated_scientific_worker_v1_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
FINAL_CLASSIFICATION = (
    "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_READY_FOR_XHIGH_REVIEW"
)
PROOF_STRATEGY = (
    "CERTIFIED_SOURCE_PLUS_FROZEN_CPYTHON_PLUS_CLOSED_STORE_GRAMMAR_PLUS_"
    "COMPILED_ROOT_WITNESS_PLUS_ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER"
)
REQUIRED_REVIEW = (
    "POSTP1-002V2A-PAD4_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW"
)

#: The failed ``ETF_CALENDAR_RUNTIME_OWNER_ATTESTATION_V1`` parent.  Its
#: compiled root-binding witness, closed AST grammar and eleven-owner graph are
#: re-adopted under a new parent; the failed parent hash is never certified.
FAILED_PARENT_SHA256 = (
    "b8f8b92d4e3c1c80c4226f7101e71f95d125bd48afbfcde72e489408f6b5b996"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CALENDAR_MODULE = witness.CALENDAR_MODULE
CALENDAR_SOURCE = witness.CALENDAR_SOURCE
CALENDAR_MODULE_IMPORT_NAME = attestation.CALENDAR_MODULE_IMPORT_NAME
CERTIFIED_DEPENDENCY_VERSION = witness.CERTIFIED_DEPENDENCY_VERSION
CERTIFIED_DEPENDENCY_SHA256 = witness.CERTIFIED_DEPENDENCY_SHA256
FAILED_ARCHITECTURE_LINEAGE = (
    *attestation.FAILED_ARCHITECTURE_LINEAGE,
    FAILED_PARENT_SHA256,
)
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

#: The runtime-object closure PAD3 measured is demoted to archived diagnostic
#: evidence.  It is recorded so the reviewer can see exactly what stopped being
#: a completeness proof, never as a live authority.
DEMOTED_PAD3_RUNTIME_CLOSURE: Mapping[str, int] = {
    "functions": 25,
    "classes": 7,
    "values": 15,
    "imports": 14,
}


class IsolatedScientificWorkerError(attestation.RuntimeOwnerAttestationError):
    """Raised when the isolated worker architecture refuses scientific authority."""


def _canonical_json(payload: Any) -> str:
    return protocol.canonical_json_bytes(payload).decode("ascii")


def _digest(payload: Any) -> str:
    return protocol.digest_payload(payload)


def source_sha256(source: str) -> str:
    return witness.source_sha256(source)


def verify_worker_protocol_binds_the_frozen_interpreter() -> dict[str, Any]:
    """The worker-safe restatement may never drift from the owning authority."""

    if dict(protocol.PROOF_INTERPRETER_IDENTITY) != dict(PROOF_INTERPRETER_IDENTITY):
        raise IsolatedScientificWorkerError(
            "worker protocol interpreter identity diverges from the compiled "
            "root-binding witness authority"
        )
    return dict(sorted(PROOF_INTERPRETER_IDENTITY.items()))


# ---------------------------------------------------------------------------
# Certified project source manifest
# ---------------------------------------------------------------------------

WORKER_SOURCE_MANIFEST_VERSION = "ETF_CALENDAR_WORKER_PROJECT_SOURCE_MANIFEST_V1"
WORKER_ENTRYPOINT_MODULE = protocol.WORKER_ENTRYPOINT_MODULE
WORKER_ENTRYPOINT_RELATIVE_PATH = protocol.WORKER_ENTRYPOINT_RELATIVE_PATH
WORKER_PROTOCOL_MODULE = "btc_predictor.research.etf_calendar_worker_protocol"
WORKER_PROTOCOL_RELATIVE_PATH = protocol.WORKER_PROTOCOL_RELATIVE_PATH
PROJECT_PACKAGE_ROOT = protocol.PROJECT_PACKAGE_ROOT

#: The modules the worker must actually have loaded before it may evaluate.
REQUIRED_WORKER_PROJECT_MODULES: tuple[str, ...] = tuple(
    sorted(
        (
            PROJECT_PACKAGE_ROOT,
            WORKER_PROTOCOL_MODULE,
            CALENDAR_MODULE_IMPORT_NAME,
            "btc_predictor.data.etf_flows",
            "btc_predictor.data.ohlcv",
            "btc_predictor.features.flow",
            "btc_predictor.research.etf_calendar_semantics",
            "btc_predictor.research.trusted_acquisition",
        )
    )
)


def _module_source_path(project_root: Path, dotted: str) -> tuple[str, Path] | None:
    """Resolve a dotted project module to its single canonical source file."""

    module_path = protocol.module_relative_path(dotted)
    package_path = protocol.package_relative_path(dotted)
    module_file = project_root / module_path
    package_file = project_root / package_path
    if module_file.is_file() and package_file.is_file():
        raise IsolatedScientificWorkerError(
            f"project module {dotted!r} has two candidate certified sources"
        )
    if module_file.is_file():
        return module_path, module_file
    if package_file.is_file():
        return package_path, package_file
    return None


def _declared_imports(source: str, dotted: str, is_package: bool) -> set[str]:
    """Every static import declaration anywhere in a module, nested included.

    Function-level imports are ordinary static declarations and are collected,
    because the worker entrypoint deliberately defers its project imports until
    the parent-controlled ``sys.path`` is established.
    """

    package = dotted if is_package else dotted.rpartition(".")[0]
    declared: set[str] = set()
    for node in ast.walk(ast.parse(source)):
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


_MANIFEST_CACHE: dict[tuple[str, tuple[str, ...]], tuple[protocol.ProjectSourceEntry, ...]] = {}


def reset_manifest_cache() -> None:
    """Drop the derivation cache; the derivation itself is unaffected."""

    _MANIFEST_CACHE.clear()


def derive_project_source_manifest(
    project_root: Path = PROJECT_ROOT,
    seeds: Sequence[str] = (WORKER_ENTRYPOINT_MODULE,),
    *,
    use_cache: bool = True,
) -> tuple[protocol.ProjectSourceEntry, ...]:
    """Mechanically derive the recursive project import closure of the worker.

    The manifest is a *derivation*, never a hand-maintained list of helpers,
    constants or classes.  It is seeded by the scientific worker entrypoint,
    follows static import declarations, and includes every ancestor package,
    because importing ``a.b.c`` executes ``a`` and ``a.b`` as well.
    """

    key = (str(project_root), tuple(seeds))
    if use_cache and key in _MANIFEST_CACHE:
        return _MANIFEST_CACHE[key]
    resolved: dict[str, str] = {}
    pending = list(seeds)
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
        for declared in _declared_imports(
            source, dotted, relative.endswith("/__init__.py")
        ):
            root, _, _ = declared.partition(".")
            if root == PROJECT_PACKAGE_ROOT and declared not in resolved:
                pending.append(declared)
    entries = [
        protocol.ProjectSourceEntry(
            module=dotted,
            path=relative,
            sha256=protocol.file_sha256(project_root / relative),
        )
        for dotted, relative in resolved.items()
    ]
    derived = tuple(sorted(entries))
    if use_cache:
        _MANIFEST_CACHE[key] = derived
    return derived


def external_import_roots(
    project_root: Path = PROJECT_ROOT,
    entries: Sequence[protocol.ProjectSourceEntry] | None = None,
) -> tuple[str, ...]:
    """The non-stdlib top-level modules the certified source universe imports."""

    manifest = derive_project_source_manifest(project_root) if entries is None else entries
    roots: set[str] = set()
    for entry in manifest:
        source = (project_root / entry.path).read_text(encoding="utf-8")
        for declared in _declared_imports(
            source, entry.module, entry.path.endswith("/__init__.py")
        ):
            root, _, _ = declared.partition(".")
            if (
                root
                and root != PROJECT_PACKAGE_ROOT
                and root != "__future__"
                and root not in sys.stdlib_module_names
            ):
                roots.add(root)
    return tuple(sorted(roots))


def worker_project_source_manifest(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    entries = derive_project_source_manifest(project_root)
    return _definition(
        {
            "contract_version": WORKER_SOURCE_MANIFEST_VERSION,
            "derivation": (
                "RECURSIVE_STATIC_PROJECT_IMPORT_CLOSURE_FROM_THE_WORKER_ENTRYPOINT"
            ),
            "seed_entrypoint": WORKER_ENTRYPOINT_MODULE,
            "hand_maintained": False,
            "nested_function_level_import_declarations_followed": True,
            "ancestor_packages_included": True,
            "dynamic_project_import_supported": False,
            "module_count": len(entries),
            "required_loaded_modules": list(REQUIRED_WORKER_PROJECT_MODULES),
            "manifest_digest": protocol.manifest_digest(entries),
            "entries": [entry.as_material() for entry in entries],
        }
    )


# ---------------------------------------------------------------------------
# Third-party dependency manifest
# ---------------------------------------------------------------------------


def derive_third_party_manifest(
    roots: Sequence[str],
) -> tuple[protocol.ThirdPartyEntry, ...]:
    """Bind each non-stdlib distribution to a deterministic installed identity.

    The controller derives this at launch, because a distribution's install
    location and ``RECORD`` digest are environment material, not reviewed
    repository material.  The worker verifies it without ``importlib``.
    """

    import importlib.metadata as metadata

    mapping = metadata.packages_distributions()
    by_distribution: dict[str, set[str]] = {}
    for root in roots:
        names = mapping.get(root)
        if not names:
            raise IsolatedScientificWorkerError(
                f"worker dependency {root!r} has no installed distribution metadata"
            )
        by_distribution.setdefault(sorted(names)[0], set()).add(root)
    entries: list[protocol.ThirdPartyEntry] = []
    for distribution, module_roots in by_distribution.items():
        dist = metadata.distribution(distribution)
        info = Path(str(dist._path))
        record = info / "RECORD"
        if not record.is_file():
            raise IsolatedScientificWorkerError(
                f"distribution {distribution!r} declares no installed RECORD manifest"
            )
        entries.append(
            protocol.ThirdPartyEntry(
                distribution=distribution,
                version=dist.version,
                location=str(Path(dist.locate_file("")).resolve()),
                record_path=str(record.resolve()),
                record_sha256=protocol.file_sha256(record),
                root_modules=tuple(sorted(module_roots)),
            )
        )
    return tuple(sorted(entries))


# ---------------------------------------------------------------------------
# Closed worker-coding rule
# ---------------------------------------------------------------------------

FORBIDDEN_WORKER_CALLABLES: tuple[str, ...] = (
    "exec",
    "eval",
    "compile",
    "__import__",
)
FORBIDDEN_WORKER_IMPORT_ROOTS: tuple[str, ...] = (
    "cloudpickle",
    "ctypes",
    "dill",
    "http",
    "httpx",
    "importlib",
    "marshal",
    "multiprocessing",
    "pickle",
    "psycopg",
    "psycopg2",
    "requests",
    "runpy",
    "socket",
    "sqlalchemy",
    "ssl",
    "subprocess",
    "urllib",
)
FORBIDDEN_WORKER_OS_ATTRIBUTES: tuple[str, ...] = (
    "execl",
    "execle",
    "execlp",
    "execv",
    "execve",
    "execvp",
    "fork",
    "forkpty",
    "popen",
    "posix_spawn",
    "spawnl",
    "spawnv",
    "system",
)


def dynamic_import_findings(source: str, label: str) -> tuple[str, ...]:
    """Report every construct that could execute project code out of manifest."""

    findings: list[str] = []
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load):
            if node.id in FORBIDDEN_WORKER_CALLABLES:
                findings.append(f"{label}:FORBIDDEN_CALLABLE:{node.id}")
        elif isinstance(node, ast.Attribute):
            if node.attr in FORBIDDEN_WORKER_CALLABLES:
                findings.append(f"{label}:FORBIDDEN_ATTRIBUTE:{node.attr}")
            elif (
                isinstance(node.value, ast.Name)
                and node.value.id == "os"
                and node.attr in FORBIDDEN_WORKER_OS_ATTRIBUTES
            ):
                findings.append(f"{label}:FORBIDDEN_PROCESS_CAPABILITY:os.{node.attr}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.partition(".")[0]
                if root in FORBIDDEN_WORKER_IMPORT_ROOTS:
                    findings.append(f"{label}:FORBIDDEN_IMPORT:{alias.name}")
        elif isinstance(node, ast.ImportFrom):
            root = (node.module or "").partition(".")[0]
            if root in FORBIDDEN_WORKER_IMPORT_ROOTS:
                findings.append(f"{label}:FORBIDDEN_IMPORT:{node.module}")
    return tuple(sorted(set(findings)))


def audit_authoritative_worker_source(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """The two worker-owned modules must be closed against project execution."""

    findings: list[str] = []
    identities: dict[str, str] = {}
    for relative in protocol.AUTHORITATIVE_WORKER_SOURCE:
        path = project_root / relative
        source = path.read_text(encoding="utf-8")
        identities[relative] = source_sha256(source)
        findings.extend(dynamic_import_findings(source, relative))
    if findings:
        raise IsolatedScientificWorkerError(
            f"authoritative scientific worker source is not closed: {findings!r}"
        )
    return {
        "authoritative_worker_source": list(protocol.AUTHORITATIVE_WORKER_SOURCE),
        "source_sha256": dict(sorted(identities.items())),
        "findings": [],
        "closed": True,
    }


# ---------------------------------------------------------------------------
# Worker launch contract
# ---------------------------------------------------------------------------

WORKER_LAUNCH_CONTRACT = "ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_V1"
WORKER_LAUNCH_FLAGS: tuple[str, ...] = ("-I", "-S", "-B")
EXEC_LAUNCH = "EXEC_FRESH_INTERPRETER"
FORK_WITHOUT_EXEC = "FORK_WITHOUT_EXEC"
FORK_SERVER_REUSE = "REUSED_LONG_LIVED_WORKER"
AUTHORIZED_LAUNCH_MECHANISMS: tuple[str, ...] = (EXEC_LAUNCH,)
UNAUTHORIZED_LAUNCH_MECHANISMS: tuple[str, ...] = (
    FORK_WITHOUT_EXEC,
    FORK_SERVER_REUSE,
)

#: The worker receives a frozen minimal environment.  No ``PYTHON*`` variable
#: and no signing-key variable can reach it, so parent environment drift after
#: controller startup cannot change the child scientific import environment.
FROZEN_WORKER_ENVIRONMENT: Mapping[str, str] = {
    "LC_ALL": "C",
    "LANG": "C",
    "TZ": "UTC",
}

_BASE_SYS_PATH_CACHE: dict[str, tuple[str, ...]] = {}


def authorize_worker_launch_mechanism(mechanism: str) -> str:
    """Only a fresh exec'd interpreter is an authorized scientific worker."""

    if mechanism not in AUTHORIZED_LAUNCH_MECHANISMS:
        raise IsolatedScientificWorkerError(
            f"{mechanism}: {protocol.NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER}"
        )
    return mechanism


def interpreter_base_sys_path(executable: str) -> tuple[str, ...]:
    """Ask the exact frozen interpreter for its own controlled base path."""

    cached = _BASE_SYS_PATH_CACHE.get(executable)
    if cached is not None:
        return cached
    completed = subprocess.run(
        [executable, "-I", "-S", "-c", "import sys,json;print(json.dumps(sys.path))"],
        capture_output=True,
        check=True,
        env=dict(FROZEN_WORKER_ENVIRONMENT),
        timeout=protocol.DEFAULT_TIMEOUT_SECONDS,
    )
    entries = tuple(json.loads(completed.stdout.decode("ascii")))
    _BASE_SYS_PATH_CACHE[executable] = entries
    return entries


def parent_site_paths() -> tuple[str, ...]:
    """The parent-bound third-party import locations handed to the worker."""

    paths = sysconfig.get_paths()
    ordered: list[str] = []
    for key in ("purelib", "platlib"):
        candidate = paths.get(key)
        if candidate and candidate not in ordered and Path(candidate).is_dir():
            ordered.append(candidate)
    return tuple(ordered)


@dataclass(frozen=True)
class WorkerLaunch:
    """Fully parent-bound launch material for one scientific worker process."""

    executable: str
    project_root: Path
    sys_path: tuple[str, ...]
    entrypoint: Path
    cwd: Path
    mechanism: str = EXEC_LAUNCH
    timeout_seconds: int = protocol.DEFAULT_TIMEOUT_SECONDS
    environment: Mapping[str, str] = field(
        default_factory=lambda: dict(FROZEN_WORKER_ENVIRONMENT)
    )

    @property
    def argv(self) -> tuple[str, ...]:
        return (
            self.executable,
            *WORKER_LAUNCH_FLAGS,
            str(self.entrypoint),
            json.dumps(list(self.sys_path)),
        )


def worker_launch(
    project_root: Path = PROJECT_ROOT,
    *,
    executable: str | None = None,
    extra_sys_path: Sequence[str] = (),
    timeout_seconds: int = protocol.DEFAULT_TIMEOUT_SECONDS,
    mechanism: str = EXEC_LAUNCH,
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
        mechanism=mechanism,
        timeout_seconds=timeout_seconds,
    )


# ---------------------------------------------------------------------------
# Canonical scientific request
# ---------------------------------------------------------------------------


def build_scientific_request(
    launch: WorkerLaunch,
    *,
    operation: str,
    operation_inputs: Mapping[str, Any],
    evidence_records: Sequence[Mapping[str, Any]],
    decision_time: str,
    decision_sha256: str,
    evidence_admission_mode: str = protocol.PROTOTYPE_EVIDENCE_ADMISSION_MODE,
    project_source_manifest: Sequence[protocol.ProjectSourceEntry] | None = None,
    third_party_manifest: Sequence[protocol.ThirdPartyEntry] | None = None,
) -> dict[str, Any]:
    """Assemble one canonical, deterministic, non-executable request payload."""

    from btc_predictor.research import etf_publication_calendar as calendar

    entries = (
        derive_project_source_manifest(launch.project_root)
        if project_source_manifest is None
        else tuple(project_source_manifest)
    )
    third_party = (
        derive_third_party_manifest(external_import_roots(launch.project_root, entries))
        if third_party_manifest is None
        else tuple(third_party_manifest)
    )
    return {
        "request_schema_version": protocol.REQUEST_SCHEMA_VERSION,
        "worker_authority_version": protocol.WORKER_AUTHORITY_VERSION,
        "worker_authority_sha256": decision_sha256,
        "calendar_authority_version": calendar.AUTHORITY_VERSION,
        "calendar_authority_sha256": calendar.FROZEN_AUTHORITY_DEFINITION_SHA256,
        "trusted_persistence_authority_sha256": CERTIFIED_DEPENDENCY_SHA256,
        "interpreter_identity": dict(PROOF_INTERPRETER_IDENTITY),
        "project_root": str(launch.project_root),
        "sys_path": list(launch.sys_path),
        "worker_entrypoint_module": WORKER_ENTRYPOINT_MODULE,
        "worker_entrypoint_sha256": protocol.file_sha256(
            launch.project_root / WORKER_ENTRYPOINT_RELATIVE_PATH
        ),
        "worker_protocol_sha256": protocol.file_sha256(
            launch.project_root / WORKER_PROTOCOL_RELATIVE_PATH
        ),
        "project_source_manifest": [entry.as_material() for entry in entries],
        "project_source_manifest_digest": protocol.manifest_digest(entries),
        "required_project_modules": list(REQUIRED_WORKER_PROJECT_MODULES),
        "third_party_manifest": [entry.as_material() for entry in third_party],
        "third_party_manifest_digest": protocol.third_party_manifest_digest(third_party),
        "decision_time": decision_time,
        "operation": operation,
        "evidence_admission_mode": evidence_admission_mode,
        "evidence_records": [dict(record) for record in evidence_records],
        "operation_inputs": dict(operation_inputs),
    }


# ---------------------------------------------------------------------------
# Controller: launch, observe, admit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkerProcessOutcome:
    """Everything the controller observed about one worker process."""

    exit_status: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    request_digest: str

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


def run_scientific_worker(
    request: Mapping[str, Any], launch: WorkerLaunch
) -> WorkerProcessOutcome:
    """Exec one fresh interpreter, serve one request, observe the exit."""

    authorize_worker_launch_mechanism(launch.mechanism)
    payload = protocol.canonical_json_bytes(request)
    if len(payload) > protocol.MAX_REQUEST_BYTES:
        raise IsolatedScientificWorkerError(
            "scientific request exceeds the frozen input-size limit"
        )
    digest = protocol.digest_bytes(payload)
    try:
        completed = subprocess.run(
            list(launch.argv),
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
        )
    return WorkerProcessOutcome(
        exit_status=completed.returncode,
        timed_out=False,
        stdout=completed.stdout,
        stderr=completed.stderr,
        request_digest=digest,
    )


def admit_worker_result(
    request: Mapping[str, Any], outcome: WorkerProcessOutcome
) -> AdmissionOutcome:
    """Admit a scientific result only when every frozen binding reproduces."""

    def refuse(reason: str, response: Mapping[str, Any] | None = None) -> AdmissionOutcome:
        return AdmissionOutcome(False, reason, response, outcome)

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
        return refuse(
            f"WORKER_REFUSED:{parsed['failure_reason']}", parsed
        )
    expected = {
        "request_schema_version": request["request_schema_version"],
        "request_digest": outcome.request_digest,
        "worker_authority_version": request["worker_authority_version"],
        "worker_authority_sha256": request["worker_authority_sha256"],
        "calendar_authority_sha256": request["calendar_authority_sha256"],
        "trusted_persistence_authority_sha256": request[
            "trusted_persistence_authority_sha256"
        ],
        "worker_entrypoint_sha256": request["worker_entrypoint_sha256"],
        "worker_protocol_sha256": request["worker_protocol_sha256"],
        "project_source_manifest_digest": request["project_source_manifest_digest"],
        "third_party_manifest_digest": request["third_party_manifest_digest"],
        "operation": request["operation"],
        "evidence_admission_mode": request["evidence_admission_mode"],
        "decision_time": request["decision_time"],
    }
    mismatched = sorted(
        field_name
        for field_name, value in expected.items()
        if parsed.get(field_name) != value
    )
    if mismatched:
        return refuse(f"WORKER_BINDING_MISMATCH:{mismatched!r}", parsed)
    if parsed["interpreter_identity"] != dict(PROOF_INTERPRETER_IDENTITY):
        return refuse("WORKER_INTERPRETER_IDENTITY_MISMATCH", parsed)
    if parsed["sys_path_digest"] != protocol.digest_payload(list(request["sys_path"])):
        return refuse("WORKER_SYS_PATH_MISMATCH", parsed)
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
    request: Mapping[str, Any], launch: WorkerLaunch
) -> AdmissionOutcome:
    return admit_worker_result(request, run_scientific_worker(request, launch))


def scientific_response_evidence(admission: AdmissionOutcome) -> dict[str, Any]:
    """Deterministic, address-free evidence for one scientific worker decision."""

    response = admission.response or {}
    evidence = {
        "worker_authority_hash": response.get("worker_authority_sha256"),
        "calendar_authority_hash": response.get("calendar_authority_sha256"),
        "trusted_persistence_authority_hash": response.get(
            "trusted_persistence_authority_sha256"
        ),
        "interpreter_identity": response.get("interpreter_identity"),
        "worker_source_manifest_digest": response.get(
            "project_source_manifest_digest"
        ),
        "third_party_manifest_digest": response.get("third_party_manifest_digest"),
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


def compiled_root_binding_witness(source: str) -> witness.CompiledBindingWitness:
    """The re-adopted PAD2 compiled root-binding witness, freshly parent-bound."""

    return attestation.compiled_root_binding_witness(source)


def root_binding_findings(source: str) -> dict[str, Any]:
    return attestation.root_binding_findings(source)


def classify_module_namespace_reach_sites(source: str) -> dict[str, Any]:
    return attestation.classify_module_namespace_reach_sites(source)


def direct_dependency_body_findings(source: str) -> dict[str, Any]:
    return attestation.direct_dependency_body_findings(source)


def audit_direct_dependency_bodies(source: str) -> tuple[str, ...]:
    return attestation.audit_direct_dependency_bodies(source)


def verify_current_production_expected_result(source: str) -> dict[str, Any]:
    """Bind the frozen current-production claim to the reviewed calendar source.

    Process isolation does not legalize any of the known blockers.  Current
    production still captures its scientific root in a generator, still
    installs wrapper dependency guards instead of five direct bodies, and still
    does not implement an isolated worker, so the calendar implementation stays
    blocked.
    """

    produced = compiled_root_binding_witness(source)
    witness.verify_witness_binds_source(produced, source)
    if len(produced.owners) != len(FROZEN_REPLAY_OWNERS):
        raise IsolatedScientificWorkerError(
            "compiled witness owner census is not the exact frozen eleven"
        )
    if produced.root_rebinding_findings:
        raise IsolatedScientificWorkerError(
            f"unexpected current-production root rebinding: {produced.root_rebinding_findings!r}"
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
        raise IsolatedScientificWorkerError(
            "current-production capture findings are not the single known "
            f"generator blocker: {produced.root_capture_findings!r}"
        )
    namespace = classify_module_namespace_reach_sites(source)
    if tuple(namespace["reach_scopes"]) != MODULE_NAMESPACE_REACH_SITES:
        raise IsolatedScientificWorkerError(
            "current-production module-namespace reach scopes are not the frozen "
            f"known set: {namespace['reach_scopes']!r}"
        )
    if namespace["namespace_write_scopes"] != [WRAPPER_INSTALLER_SITE]:
        raise IsolatedScientificWorkerError(
            "current-production namespace writes are not the single wrapper "
            f"installer: {namespace['namespace_write_scopes']!r}"
        )
    try:
        narrow.audit_store_capability_normal_form(source)
    except narrow.NormalFormError as error:
        if "FORBIDDEN_NESTED_SCOPE_CAPTURE" not in str(error):
            raise IsolatedScientificWorkerError(
                f"unexpected current-production AST refusal: {error}"
            ) from error
    else:
        raise IsolatedScientificWorkerError(
            "current production unexpectedly conforms to the closed AST use grammar"
        )
    bodies = direct_dependency_body_findings(source)
    if bodies["bodies_absent"] or bodies["decorated_bodies"]:
        raise IsolatedScientificWorkerError(
            f"current-production required direct bodies are not the frozen five: {bodies!r}"
        )
    if bodies["bodies_without_the_direct_dependency_assertion"] != sorted(
        REQUIRED_DIRECT_BODIES
    ):
        raise IsolatedScientificWorkerError(
            f"current production does not match the known wrapper-guard state: {bodies!r}"
        )
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
        "isolated_scientific_worker_implemented_in_production": False,
        "calendar_production_conformance": "NO",
        "calendar_implementation": "BLOCKED",
    }


# ---------------------------------------------------------------------------
# Material children
# ---------------------------------------------------------------------------


def trusted_process_and_isolation_boundary() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_TRUSTED_PROCESS_AND_ISOLATION_BOUNDARY_V1_PAD4",
            "scientific_execution_boundary": "OPERATING_SYSTEM_PROCESS",
            "process_isolation_is_scientific_execution_boundary": True,
            "runtime_object_closure_is_completeness_proof": False,
            "abandoned_completeness_models": [
                "GENERATED_RUNTIME_METHOD_ENUMERATION",
                "RECURSIVE_SAME_PROCESS_RUNTIME_OBJECT_ATTESTATION",
                "REFLECTION_BLACKLIST_COMPLETENESS",
                "TRANSITIVE_MUTABLE_OBJECT_CLOSURE_ACROSS_THE_REPOSITORY",
            ],
            "escalation_rationale": (
                "same-process scientific identity approaches failed because the "
                "mutable execution surface expands transitively through "
                "project-owned modules and generated runtime objects; PAD4 "
                "isolates mutable runtime state rather than enumerating it"
            ),
            "worker_trusted_after_admission": True,
            "trusted_once": [
                "CERTIFIED_PROJECT_SOURCE_ADMISSION_PASSES",
                "CERTIFIED_THIRD_PARTY_ENVIRONMENT_ADMISSION_PASSES",
                "FROZEN_INTERPRETER_IDENTITY_PASSES",
            ],
            "out_of_scope": [
                "HOSTILE_DEBUGGER_ATTACHMENT",
                "KERNEL_COMPROMISE",
                "MALICIOUS_MODIFICATION_PERFECTLY_RACING_FILE_VERIFICATION",
                "OPERATING_SYSTEM_MEMORY_INJECTION",
            ],
            "hostile_operating_system_resistance_claimed": False,
            "certified_source_may_mutate_its_own_globals": True,
            "certified_self_mutation_is_program_behavior_not_ambient_drift": True,
            "demoted_pad3_runtime_closure": dict(DEMOTED_PAD3_RUNTIME_CLOSURE),
            "demoted_pad3_runtime_closure_role": "ARCHIVED_DIAGNOSTIC_EVIDENCE",
        }
    )


def proof_interpreter_identity() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PROOF_INTERPRETER_IDENTITY_V1_PAD4",
            "frozen_identity": dict(verify_worker_protocol_binds_the_frozen_interpreter()),
            "identity_fields": sorted(PROOF_INTERPRETER_IDENTITY),
            "worker_and_controller_share_one_identity_authority": True,
            "worker_identity_restatement_is_mechanically_bound": True,
            "mismatch": "REFUSE_SCIENTIFIC_AUTHORITY",
            "verified_before_any_scientific_call": True,
            "standard_library_semantics_rely_on_this_axiom": True,
            "stdlib_python_objects_recursively_attested": False,
            "stdlib_boundary_is_an_explicit_architecture_axiom": True,
            "future_python_upgrade": "REQUIRES_EXPLICIT_REVIEW_AND_REFREEZE",
            "different_python_interpreter_may_reuse_this_authority": False,
        }
    )


def worker_launch_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": WORKER_LAUNCH_CONTRACT,
            "launch": "EXEC_STYLE_LAUNCH_OF_THE_EXACT_FROZEN_INTERPRETER",
            "authorized_mechanisms": list(AUTHORIZED_LAUNCH_MECHANISMS),
            "unauthorized_mechanisms": list(UNAUTHORIZED_LAUNCH_MECHANISMS),
            "fork_only_worker_permitted": False,
            "fresh_interpreter": True,
            "fresh_sys_modules": True,
            "fresh_project_imports": True,
            "inherited_parent_python_module_objects": False,
            "worker_reuse_permitted": False,
            "long_lived_worker_permitted": False,
            "one_request_one_exec_process": True,
            "process_exits_after_response": True,
            "worker_concurrency": "ONE_SYNCHRONOUS_REQUEST_NO_BACKGROUND_THREAD",
            "scientific_background_thread_permitted": False,
            "async_scientific_continuation_permitted": False,
            "nested_scientific_job_permitted": False,
            "launcher_flags": list(WORKER_LAUNCH_FLAGS),
            "launcher_flag_effects": dict(sorted(protocol.REQUIRED_INTERPRETER_FLAGS.items())),
            "environment_variable_python_configuration_ignored": True,
            "user_site_disabled": True,
            "sitecustomize_and_usercustomize_executed": False,
            "uncontrolled_current_directory_import_precedence": False,
            "sys_path_explicitly_parent_controlled": True,
            "ambient_pythonpath_dependency": False,
            "frozen_child_environment": dict(sorted(FROZEN_WORKER_ENVIRONMENT.items())),
            "parent_environment_drift_after_startup_reaches_the_child": False,
            "child_working_directory": "PARENT_BOUND_PROJECT_ROOT",
            "performance_subordinate_to_proof_simplicity": True,
            "resource_limits": {
                "max_request_bytes": protocol.MAX_REQUEST_BYTES,
                "max_response_bytes": protocol.MAX_RESPONSE_BYTES,
                "timeout_seconds": protocol.DEFAULT_TIMEOUT_SECONDS,
                "timeout_or_crash": "NO_SCIENTIFIC_RESULT_ADMISSION",
                "silent_retry_on_a_different_authority_path": False,
            },
        }
    )


def project_source_manifest_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_WORKER_PROJECT_SOURCE_MANIFEST_RULE_V1_PAD4",
            "manifest_version": WORKER_SOURCE_MANIFEST_VERSION,
            "proof_boundary": "CERTIFIED_SOURCE_MODULES",
            "proof_boundary_is_not": (
                "EVERY_RUNTIME_CONSTANT_FUNCTION_CLASS_OBJECT_REACHABLE_AFTER_IMPORT"
            ),
            "bound_per_entry": ["canonical_module_name", "canonical_source_path", "sha256"],
            "derivation_rule": (
                "RECURSIVE_PROJECT_IMPORT_CLOSURE_FROM_THE_SCIENTIFIC_WORKER_"
                "ENTRYPOINT_USING_STATIC_IMPORT_DECLARATIONS"
            ),
            "mechanically_derivable": True,
            "hand_maintained_helper_constant_or_class_list": False,
            "ancestor_packages_included": True,
            "project_owned_module_outside_the_manifest_may_execute": False,
            "unexpected_project_module": "REFUSE",
            "missing_required_manifest_member": "REFUSE",
            "certified_source_sha_mismatch": "REFUSE",
            "wrong_project_module_origin": "REFUSE",
            "verified_before_scientific_execution": True,
            "verified_again_before_emitting_a_successful_result": True,
            "post_execution_verification_is_defence_in_depth": True,
            "post_execution_verification_attests_every_runtime_object": False,
            "project_runtime_objects_are_freshly_constructed_from_certified_source": True,
            "generated_class_methods_governed_by": [
                "CERTIFIED_CPYTHON_AND_STDLIB_ENVIRONMENT",
                "CERTIFIED_SOURCE_DECLARATION",
                "FRESH_ISOLATED_CONSTRUCTION",
            ],
            "generated_runtime_methods_hand_fingerprinted": False,
            "source_change_altering_a_generated_class": "CHANGES_THE_MANIFEST_AND_REQUIRES_REFREEZE",
            "package_reexport_direct_import_reduction": "PERMITTED_LATER_NOT_IN_THIS_TICKET",
        }
    )


def third_party_dependency_manifest_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_WORKER_THIRD_PARTY_MANIFEST_RULE_V1_PAD4",
            "non_stdlib_dependency_must_be_explicitly_frozen": True,
            "frozen_distribution_roots": list(external_import_roots()),
            "bound_per_entry": [
                "distribution",
                "installed_record_manifest_sha256",
                "installed_record_manifest_path",
                "install_location",
                "root_modules",
                "version",
            ],
            "installed_record_is_itself_a_per_file_hash_manifest": True,
            "arbitrary_site_packages_state_is_scientific_authority": False,
            "loaded_dependency_must_resolve_inside_the_certified_location": True,
            "environment_manifest_is_launch_bound_not_artifact_bound": True,
            "environment_manifest_binding_reason": (
                "install locations, versions and wheel record digests are "
                "machine-specific environment material; binding them into the "
                "decision artifact would make the frozen decision hash "
                "environment-dependent and unreproducible for an independent "
                "reviewer, so the artifact freezes the rule and the derived "
                "distribution roots while every launch binds the exact "
                "environment identity into the request and the response"
            ),
            "non_certified_dependency_environment": "REFUSE",
            "worker_verifies_without_importlib": True,
            "stdlib_modules_recursively_attested": False,
        }
    )


def dynamic_import_and_execution_prohibition() -> dict[str, Any]:
    audit = audit_authoritative_worker_source()
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_WORKER_DYNAMIC_IMPORT_PROHIBITION_V1_PAD4",
            "scope": "AUTHORITATIVE_SCIENTIFIC_WORKER_SOURCE",
            "authoritative_worker_source": list(audit["authoritative_worker_source"]),
            "authoritative_worker_source_sha256": dict(audit["source_sha256"]),
            "forbidden_callables": list(FORBIDDEN_WORKER_CALLABLES),
            "forbidden_import_roots": list(FORBIDDEN_WORKER_IMPORT_ROOTS),
            "forbidden_process_capabilities": [
                f"os.{name}" for name in FORBIDDEN_WORKER_OS_ATTRIBUTES
            ],
            "dynamic_project_import_permitted": False,
            "runpy_execution_permitted": False,
            "arbitrary_source_loading_permitted": False,
            "pickle_cloudpickle_dill_permitted": False,
            "forbidden_scientific_ipc": list(protocol.FORBIDDEN_SCIENTIFIC_IPC),
            "serialized_executable_python_object_graph_permitted": False,
            "closed_worker_coding_rule": True,
            "claims_to_enumerate_hostile_python_techniques": False,
            "production_calendar_source_governed_separately_by": [
                "CLOSED_AST_STORE_USE_GRAMMAR",
                "COMPILED_ROOT_BINDING_WITNESS",
            ],
            "current_findings": list(audit["findings"]),
            "closed": audit["closed"],
        }
    )


def scientific_request_protocol() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": protocol.REQUEST_SCHEMA_VERSION,
            "encoding": "CANONICAL_JSON_BYTES",
            "executable_payload_permitted": False,
            "transport": "WORKER_STDIN",
            "fields": sorted(protocol.REQUEST_FIELDS),
            "schema_validated": True,
            "unknown_fields": "REFUSE",
            "missing_fields": "REFUSE",
            "nan_or_infinity": "REFUSE",
            "timestamps": "CANONICAL_UTC_ROUND_TRIP_REQUIRED",
            "decimals": "CANONICAL_STRINGS_NEVER_BINARY_FLOATS",
            "input_digest_persisted": True,
            "frozen_operations": list(protocol.FROZEN_WORKER_OPERATIONS),
            "operation_inputs": {
                name: sorted(fields)
                for name, fields in sorted(protocol.OPERATION_INPUT_FIELDS.items())
            },
            "parent_python_objects_shared": False,
            "forbidden_request_payloads": [
                "ARBITRARY_CALLABLE_OBJECTS",
                "ARBITRARY_PICKLED_OBJECTS",
                "CLASSES",
                "FUNCTIONS",
                "LIVE_CalendarEvidenceStore_OBJECT",
                "MODULE_OBJECTS",
            ],
            "evidence_reconstruction": (
                "THE_WORKER_REBUILDS_A_READ_ONLY_EVIDENCE_VIEW_FROM_CANONICAL_DATA"
            ),
            "authoritative_evidence_admission_mode": (
                protocol.AUTHORITATIVE_EVIDENCE_ADMISSION_MODE
            ),
            "authoritative_envelope_replay_uses_the_certified_trusted_persistence_authority": True,
            "prototype_evidence_admission_mode": (
                protocol.PROTOTYPE_EVIDENCE_ADMISSION_MODE
            ),
            "prototype_mode_is_scientific_authority": False,
        }
    )


def scientific_response_protocol() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": protocol.RESPONSE_SCHEMA_VERSION,
            "encoding": "CANONICAL_JSON_BYTES",
            "transport": "WORKER_STDOUT",
            "stdout_protocol": protocol.STDOUT_PROTOCOL,
            "stderr_protocol": protocol.STDERR_PROTOCOL,
            "extra_or_ambiguous_protocol_output": "REFUSE",
            "fields": sorted(protocol.RESPONSE_FIELDS),
            "fully_materialized_result_required": True,
            "forbidden_result_kinds": list(protocol.LAZY_RESULT_KINDS),
            "lazy_result": "REFUSE",
            "scientific_execution_after_the_response_boundary": False,
            "result_digest_required": True,
            "memory_addresses_in_evidence": False,
            "typed_failure_protocol": True,
            "partial_result_admission_on_any_exception_path": False,
            "evidence_fields": [
                "admitted",
                "calendar_authority_hash",
                "decision_time",
                "failure_reason",
                "interpreter_identity",
                "operation",
                "process_exit_status",
                "request_digest",
                "request_schema_version",
                "result_digest",
                "third_party_manifest_digest",
                "trusted_persistence_authority_hash",
                "worker_authority_hash",
                "worker_source_manifest_digest",
            ],
        }
    )


def worker_io_and_capability_boundary() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_WORKER_IO_AND_CAPABILITY_BOUNDARY_V1_PAD4",
            "worker_network_permitted": False,
            "worker_https_permitted": False,
            "scientific_input_supplied_by_the_controller": True,
            "collection_remains_a_separate_governed_boundary": True,
            "worker_private_signing_key_permitted": False,
            "worker_collector_signing_capability_permitted": False,
            "signing_key_environment_variable_present": "REFUSE",
            "worker_is_a_scientific_evaluator_not_the_acquisition_signer": True,
            "worker_authoritative_db_write_permitted": False,
            "worker_database_connection": "NOT_ESTABLISHED_BY_ANY_FROZEN_OPERATION",
            "result_admission_is_a_controller_responsibility": True,
            "preferred_boundary": "NO_WORKER_DATABASE_CONNECTION",
            "enforcement": [
                "FROZEN_READ_ONLY_OPERATION_REGISTRY",
                "FROZEN_MINIMAL_CHILD_ENVIRONMENT",
                "STATIC_CLOSED_WORKER_SOURCE_PROHIBITION",
            ],
            "operating_system_level_network_sandbox_claimed": False,
            "certified_source_universe_includes_db_and_network_capable_modules": True,
            "capability_width_reason": (
                "the current package re-export graph pulls btc_predictor.db and "
                "HTTPS-capable calendar collection modules into the certified "
                "import closure even though no frozen operation reaches them; "
                "the direct-import reduction that narrows this is explicitly "
                "deferred to the final calendar implementation ticket"
            ),
            "collection_authority_moved_into_the_worker": False,
        }
    )


def compiled_root_binding_witness_rule() -> dict[str, Any]:
    payload = dict(attestation.compiled_root_binding_witness_rule())
    payload.pop("definition_sha256", None)
    payload["contract_version"] = "ETF_CALENDAR_COMPILED_ROOT_BINDING_WITNESS_RULE_V1_PAD4"
    payload["freshly_parent_bound_by"] = DECISION_VERSION
    payload["failed_pad2_parent_certified"] = False
    payload["failed_pad3_parent_certified"] = False
    payload["preserved_under_process_isolation"] = True
    payload["applies_to_certified_calendar_source_before_final_implementation"] = True
    return _definition(payload)


def store_root_and_direct_use_grammar() -> dict[str, Any]:
    payload = dict(attestation.store_root_and_direct_use_grammar())
    payload.pop("definition_sha256", None)
    payload["contract_version"] = "ETF_CALENDAR_STORE_ROOT_AND_DIRECT_USE_GRAMMAR_V1_PAD4"
    payload["freshly_parent_bound_by"] = DECISION_VERSION
    payload["preserved_under_process_isolation"] = True
    payload["process_isolation_legalizes_wrappers"] = False
    payload["root_may_be_a_cell_variable_of_a_conforming_owner"] = False
    payload["known_generator_capture_rewrite_still_required"] = (
        f"{KNOWN_PRODUCTION_BLOCKER_OWNER}:{KNOWN_PRODUCTION_BLOCKER_ROOT}"
    )
    return _definition(payload)


def replay_owner_graph_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_OWNER_GRAPH_RULE_V1_PAD4",
            "owner_count": len(FROZEN_REPLAY_OWNERS),
            "owners": list(FROZEN_REPLAY_OWNERS),
            "owner_census_relation": "FROZEN_EQUALS_SOURCE_DISCOVERED_EQUALS_11",
            "process_isolation_redefines_the_owner_graph": False,
            "cycles_permitted": False,
            "unknown_forwarding_permitted": False,
            "every_owner_has_an_evidence_edge": True,
            "every_owner_path_terminates_at_documented_store_api": True,
            "documented_terminals": list(STORE_APIS),
            "edge_kinds": [
                "DOCUMENTED_STORE_API_TERMINAL",
                "ENUMERATED_REPLAY_OWNER_EDGE",
            ],
            "compiled_root_witness_must_pass_before_graph_extraction": True,
            "ast_use_audit_must_pass_before_graph_extraction": True,
            "both_layers_required": True,
            "either_layer_substitutes_for_the_other": False,
            "static_graph_proves": "CERTIFIED_SOURCE_STRUCTURE",
            "runtime_owner_attestation_required_at_execution": False,
            "runtime_owner_attestation_demoted_reason": (
                "measured same-process owner identity is not a completeness "
                "proof; the certified isolated source universe replaces it"
            ),
        }
    )


def direct_body_dependency_rule() -> dict[str, Any]:
    payload = dict(attestation.direct_body_dependency_rule())
    payload.pop("definition_sha256", None)
    payload["contract_version"] = "ETF_CALENDAR_DIRECT_BODY_DEPENDENCY_RULE_V1_PAD4"
    payload["freshly_parent_bound_by"] = DECISION_VERSION
    payload["required_direct_bodies"] = list(REQUIRED_DIRECT_BODIES)
    payload["wrapper_installed_guards_permitted"] = False
    payload["wrapper_installer_removal_required"] = WRAPPER_INSTALLER_SITE
    payload["functools_wraps_authority_guards_permitted"] = False
    payload["process_isolation_legalizes_wrappers"] = False
    payload["certified_dependency_sha256"] = CERTIFIED_DEPENDENCY_SHA256
    return _definition(payload)


def controller_result_admission_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_CONTROLLER_RESULT_ADMISSION_RULE_V1_PAD4",
            "validated_before_admission": [
                "clean_process_termination",
                "interpreter_identity",
                "operation_identity",
                "request_digest_echo_binding",
                "response_schema_version",
                "result_digest",
                "success_status",
                "worker_authority_identity",
                "worker_source_manifest_identity",
            ],
            "any_mismatch": [protocol.RESULT_NOT_ADMITTED, protocol.DATA_QUALITY_FAIL],
            "scientific_success_requires": [
                "EXPECTED_PROCESS_EXIT",
                "SUCCESSFUL_WORKER_SELF_VERIFICATION",
                "VALID_CANONICAL_RESPONSE",
            ],
            "unexpected_crash_signal_timeout_protocol_error_or_extra_output": [
                protocol.RESULT_NOT_ADMITTED,
                protocol.DATA_QUALITY_FAIL,
            ],
            "silent_retry_with_a_different_authority_path": False,
            "worker_authority_hash_is_controller_bound": True,
            "worker_authority_hash_binding_reason": (
                "the decision hash is derived from the decision artifact, which "
                "is deliberately outside the worker's certified source universe; "
                "the worker proves its entrypoint, protocol, project source, "
                "dependency and interpreter identity, and the controller binds "
                "the frozen decision hash by echo comparison"
            ),
            "result_admission_precedes_any_persistence": False,
            "persistence_follows_admission": True,
        }
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_ISOLATED_WORKER_PROOF_ORDER_V1_PAD4",
            "order": [
                "1_VERIFY_FROZEN_INTERPRETER_IDENTITY",
                "2_VERIFY_CONTROLLED_WORKER_STARTUP_AND_PARENT_BOUND_SYS_PATH",
                "3_VERIFY_WORKER_ENTRYPOINT_AND_PROTOCOL_SOURCE_IDENTITY",
                "4_VERIFY_CERTIFIED_PROJECT_SOURCE_MANIFEST_ON_DISK",
                "5_VERIFY_CERTIFIED_THIRD_PARTY_ENVIRONMENT",
                "6_IMPORT_CERTIFIED_PROJECT_SOURCE",
                "7_VERIFY_EVERY_LOADED_PROJECT_MODULE_AGAINST_THE_MANIFEST",
                "8_RECONSTRUCT_THE_READ_ONLY_EVIDENCE_VIEW_FROM_CANONICAL_DATA",
                "9_EVALUATE_EXACTLY_ONE_FROZEN_OPERATION",
                "10_REFUSE_ANY_UNMATERIALIZED_RESULT",
                "11_REVERIFY_LOADED_PROJECT_MODULES_AND_SOURCE_IDENTITY",
                "12_EMIT_EXACTLY_ONE_CANONICAL_RESPONSE_AND_EXIT",
                "13_CONTROLLER_ADMISSION_THEN_PERSISTENCE",
            ],
            "no_scientific_call_before_self_verification_passes": True,
            "completeness_claim": (
                "the scientific answer is produced by certified source executed "
                "under a certified interpreter in a process that shares no "
                "mutable Python state with the application"
            ),
            "completeness_claim_is_not": (
                "an enumeration of every mutable Python object capable of "
                "affecting execution"
            ),
            "explicit_limits": [
                "ARBITRARY_OPERATING_SYSTEM_LEVEL_COMPROMISE_IS_OUT_OF_SCOPE",
                "CERTIFIED_SOURCE_EXECUTING_ITS_OWN_SEMANTICS_IS_NOT_DRIFT",
                "STDLIB_OBJECTS_ARE_TRUSTED_THROUGH_THE_INTERPRETER_AXIOM",
                "THE_DECISION_ARTIFACT_ITSELF_IS_CONTROLLER_BOUND_NOT_WORKER_PROVED",
            ],
            "required_adversarial_regressions": [
                "CERTIFIED_SOURCE_FILE_MUTATION_REFUSES",
                "FORK_ONLY_INHERITED_INTERPRETER_IS_NOT_AUTHORIZED",
                "LAZY_RESULT_REFUSES",
                "NON_CERTIFIED_DEPENDENCY_ENVIRONMENT_REFUSES",
                "PARENT_BUILTINS_MUTATION_LEAVES_THE_WORKER_UNAFFECTED",
                "PARENT_GENERATED_DATACLASS_METHOD_MUTATION_LEAVES_THE_WORKER_UNAFFECTED",
                "PARENT_IMPORTED_CLASS_MUTATION_LEAVES_THE_WORKER_UNAFFECTED",
                "PARENT_PACKAGE_REEXPORT_MUTATION_LEAVES_THE_WORKER_UNAFFECTED",
                "PARENT_SYS_MODULES_SUBSTITUTION_LEAVES_THE_WORKER_UNAFFECTED",
                "PARENT_FLOW_CONSTANT_MUTATION_LEAVES_THE_WORKER_UNAFFECTED",
                "PARENT_FLOW_FEATURE_ID_MUTATION_LEAVES_THE_WORKER_UNAFFECTED",
                "SECOND_REQUEST_IN_ONE_WORKER_REFUSES",
                "UNEXPECTED_PROJECT_MODULE_REFUSES",
                "WRONG_INTERPRETER_REFUSES",
                "WRONG_SOURCE_ORIGIN_REFUSES",
            ],
            "determinism": [
                "ALTERNATE_CURRENT_DIRECTORY",
                "CHILD_ORDER_VARIATION",
                "FRESH_OUTPUT_DIRECTORY",
                "FRESH_PROCESS",
                "MULTIPLE_PYTHONHASHSEED_VALUES",
            ],
            "worker_evidence_is_address_free": True,
        }
    )


def science_lineage_and_safety() -> dict[str, Any]:
    payload = dict(attestation.science_lineage_and_safety())
    payload.pop("definition_sha256", None)
    payload["contract_version"] = (
        "ETF_CALENDAR_ISOLATED_WORKER_SCIENCE_LINEAGE_AND_SAFETY_V1_PAD4"
    )
    payload["failed_architecture_lineage"] = [
        {
            "definition_sha256": sha,
            "certified": False,
            "failed": True,
            "used": False,
            "prospective_observations": 0,
            "superseded_before_use": True,
        }
        for sha in FAILED_ARCHITECTURE_LINEAGE
    ]
    payload["preserved_science"] = {
        "calendar_normalization_early_closes_pit_common_session_rules": "UNCHANGED",
        "etf_formulas_and_revision_semantics": "UNCHANGED",
        "etf_calendar_production_code_changed_by_this_decision": False,
        "parser_science": "UNCHANGED",
        "source_urls_profiles_tls_redirects": "UNCHANGED",
        "stage_b_metrics_risk_stops_thresholds": "UNCHANGED",
    }
    return _definition(payload)


_CHILD_ARTIFACTS: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
    ("trusted_process_and_isolation_boundary.json", trusted_process_and_isolation_boundary),
    ("proof_interpreter_identity.json", proof_interpreter_identity),
    ("worker_launch_contract.json", worker_launch_contract),
    ("project_source_manifest_rule.json", project_source_manifest_rule),
    ("worker_project_source_manifest.json", worker_project_source_manifest),
    ("third_party_dependency_manifest_rule.json", third_party_dependency_manifest_rule),
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


def isolated_scientific_worker_v1_definition(
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    source = CALENDAR_SOURCE.read_text(encoding="utf-8")
    narrow.verify_replay_owner_census(source)
    verify_worker_protocol_binds_the_frozen_interpreter()
    production = verify_current_production_expected_result(source)
    children = _children(child_artifacts)
    manifest = derive_project_source_manifest()
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
            "worker_project_source_manifest_digest": protocol.manifest_digest(manifest),
            "worker_project_source_module_count": len(manifest),
            "central_decisions": {
                "one_request_one_exec_process": True,
                "fork_only_worker_permitted": False,
                "parent_python_objects_shared": False,
                "pickle_ipc_permitted": False,
                "worker_network_permitted": False,
                "worker_private_signing_key_permitted": False,
                "worker_authoritative_db_write_permitted": False,
                "project_source_manifest_required": True,
                "unexpected_project_module_permitted": False,
                "dynamic_project_import_permitted": False,
                "lazy_result_permitted": False,
                "long_lived_worker_permitted": False,
                "runtime_object_closure_is_completeness_proof": False,
                "process_isolation_is_scientific_execution_boundary": True,
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
                "hostile_operating_system_resistance_claimed": False,
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
    if dict(persisted) != isolated_scientific_worker_v1_definition():
        raise IsolatedScientificWorkerError(
            "persisted isolated scientific worker decision does not reproduce"
        )
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    owners = "\n".join(f"- `{owner}`" for owner in FROZEN_REPLAY_OWNERS)
    lineage = "\n".join(f"- `{sha}`" for sha in FAILED_ARCHITECTURE_LINEAGE)
    interpreter = PROOF_INTERPRETER_IDENTITY
    production = decision["current_production_expected_result"]
    launch_flags = " ".join(WORKER_LAUNCH_FLAGS)
    store_apis = "`, `".join(STORE_APIS)
    demoted_closure = ", ".join(
        f"{count} {kind}" for kind, count in sorted(DEMOTED_PAD3_RUNTIME_CLOSURE.items())
    )
    return f"""# {DECISION_VERSION} — isolated one-shot scientific worker

- Ticket: `{PROGRAM_TICKET}`
- Decision hash: `{decision['definition_sha256']}`
- Failed parent: `{FAILED_PARENT_SHA256}` (never certified)
- Status: `{STATUS}`
- Classification: `{FINAL_CLASSIFICATION}`
- Strategy: `{PROOF_STRATEGY}`
- Material children: {decision['material_child_count']}
- Certified worker project source modules: {decision['worker_project_source_module_count']}
- Worker project source manifest digest: `{decision['worker_project_source_manifest_digest']}`

## Why same-process identity was abandoned

`POSTP1-002V2A-PAD3` failed with `PROJECT IMPORT EXECUTION CLOSURE INCOMPLETE`.
A clean attestation of the eleven frozen replay owners plus the calendar
module's own functions, classes, values and imports left the complete
attestation digest unchanged while persistent mutation of
`_flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS`, `_flow.FIVE_DAY_ETF_FLOW_FEATURE_ID`,
`_flow.EtfFlowFeatureResult`, the `require_utc_datetime` re-export origin and
the dataclass-generated `ScientificEtfFlowResult.__init__` changed the
scientific answer.

Each previous decision answered a defect by enlarging the enumerated surface.
That is not a bounded completeness argument: the mutable execution surface
expands transitively through project-owned modules and generated runtime
objects, so the enumeration can always be one object short. This decision
therefore changes the boundary instead of the list:

> do not share mutable Python scientific execution state with the application
> process.

The following are explicitly abandoned as completeness proofs: recursive
same-process runtime object attestation, transitive mutable-object closure
across the repository, reflection blacklist completeness, and
generated-runtime-method enumeration. PAD3's measured closure of
{demoted_closure} survives only as archived diagnostic evidence explaining why
PAD3 failed.

## The scientific worker

`ETF_CALENDAR_SCIENTIFIC_WORKER` is a fresh operating-system process created by
an exec-style launch of the exact frozen interpreter, with a fresh
`sys.modules`, fresh project imports and no inherited Python module object. A
fork-only inherited interpreter is `{protocol.NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER}`.
One request enters, one fully materialized response leaves, and the process
exits. There is no worker pool, no reuse, no background thread and no async
continuation. Given the system's low-frequency design, performance is
subordinate to proof simplicity.

The worker starts under `{launch_flags}`: environment-variable
Python configuration ignored, user site disabled, `sitecustomize`/
`usercustomize` not executed, uncontrolled current-directory import precedence
disabled and `sys.path` explicitly parent-controlled. The child receives a
frozen minimal environment, so parent environment drift after controller
startup cannot change the child scientific import environment, and there is no
dependency on ambient `PYTHONPATH`.

## Exact interpreter

- implementation: `{interpreter['implementation_name']}`
- version: `{interpreter['version_major']}.{interpreter['version_minor']}.{interpreter['version_micro']} {interpreter['version_releaselevel']}/{interpreter['version_serial']}`
- hexversion: `{interpreter['hexversion']}`
- cache tag: `{interpreter['cache_tag']}`
- bytecode magic: `{interpreter['magic_number_hex']}`

Any mismatch is `{protocol.REFUSE_SCIENTIFIC_AUTHORITY}`. Standard-library
implementation semantics rely on this exact interpreter identity as an explicit
architecture axiom; stdlib Python objects are never recursively attested.

## Certified source universe, not object closure

`{WORKER_SOURCE_MANIFEST_VERSION}` is the recursive project import closure of
the scientific worker entrypoint, derived mechanically from static import
declarations and every ancestor package, binding each module's canonical name,
canonical source path and SHA-256. No project-owned module outside the manifest
may execute in the worker. The proof boundary is *certified source modules*,
not every runtime constant, function or class object reachable after import,
because under a fresh one-shot process every project-owned runtime object —
including a dataclass-generated `__init__` — is freshly constructed from the
certified source universe under the frozen interpreter.

Third-party dependencies are explicitly frozen. The artifact freezes the rule
and the derived distribution roots; each launch binds the exact distribution,
version, install location and installed `RECORD` manifest digest into the
request, and the worker verifies them without `importlib`. Arbitrary
`site-packages` state is never scientific authority.

## Capability boundary

No parent Python object crosses the boundary: no function, class, module
object, live `CalendarEvidenceStore`, pickled object or callable. Pickle,
cloudpickle, dill and marshal are forbidden scientific IPC. The worker performs
no network I/O, loads no production signing key and writes no authoritative
database evidence; result admission stays a controller responsibility.

## Preserved static authority

The compiled root-binding witness, the root-cell prohibition, the closed AST
store-use grammar, the exact eleven-owner census and graph and the direct
dependency-body requirement are preserved and freshly parent-bound under this
decision. The failed PAD2 and PAD3 parents are not certified. The owners remain
exactly:

{owners}

Every owner path still terminates at a documented store API
(`{store_apis}`), cycles and unknown forwarding remain forbidden,
and `assert_trusted_persistence_dependency()` must still execute directly
inside each of the five required bodies. Process isolation does not legalize
wrappers.

## Current production

- reviewed calendar source: `{production['reviewed_source_sha256']}`
- root write/clear/delete findings: {production['root_write_clear_or_delete_findings']}
- root-cell blocker: `{production['root_cell_finding']}`
- AST store grammar: `{production['ast_store_use_normal_form']}`
- wrapper-installer removal required: {production['wrapper_installer_removal_required']}
- isolated worker implemented in production: {production['isolated_scientific_worker_implemented_in_production']}
- full conformance: `{production['calendar_production_conformance']}`

## Failed lineage

All of the following remain failed, non-certified, unused and at zero
observations:

{lineage}

Failed calendar authority hashes are preserved unchanged, the certified
predecessor corpus protocol `8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7`
and the failed V2 `488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d`
are unchanged, and trusted persistence `{CERTIFIED_DEPENDENCY_SHA256}` remains
closed, certified and unchanged.

## Safety

Prospective observations remain 0. No real Stage-B evaluation ran. The calendar
authority is not certified, calendar implementation is blocked, POSTP1-001V2R1,
POSTP1-003R3 and POSTP1-004 are blocked, collection is not authorized, BTC-019
is untouched and Epic T is unchanged. This candidate authorizes only
`{REQUIRED_REVIEW}`.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    decision = isolated_scientific_worker_v1_definition(registry)
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
            raise IsolatedScientificWorkerError(f"persisted {filename} does not reproduce")
        _verify_definition_digest(persisted)
        if decision["child_definition_sha256"].get(
            filename.removesuffix(".json")
        ) != expected["definition_sha256"]:
            raise IsolatedScientificWorkerError(
                f"isolated scientific worker parent does not bind {filename}"
            )
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise IsolatedScientificWorkerError(
            "persisted isolated scientific worker report does not reproduce"
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
