"""Worker-safe canonical protocol for the corrected isolated scientific worker.

``POSTP1-002V2A-PAD4`` failed ``ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1`` at
``cc1b325a...7b809e78`` with four independent release-critical authority
anchoring defects.  ``POSTP1-001V2A-PAD4-R1`` repairs exactly those four while
preserving the fresh-exec isolation boundary the review reproduced and found
sound.

The four repairs owned by this module are:

``A``  executed bytecode is bound to certified source, because the worker runs
       inside a fresh, empty, controller-created bytecode-cache namespace and
       verifies that namespace before any certified module is imported;
``B``  the certified source manifest is consumed, never re-derived, at runtime;
``C``  every material authority identity is compared against a trusted
       controller authority context, not against a request/response echo; and
``D``  third-party authority is an exact reviewed semantic/artifact registry
       whose installed file bytes are verified against the declared ``RECORD``
       hashes before any dependency code executes.

This module is *worker safe*: it imports only the standard library, it imports
no project module, and it contains none of the constructs the decision forbids
inside authoritative scientific worker source.  It lives outside
``btc_predictor`` because importing that package executes third-party
scientific code, which would defeat repair ``D`` by construction.
"""

from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import io
import json
import os
import sys
import types
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence


WORKER_AUTHORITY_VERSION = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
WORKER_AUTHORITY_TICKET = "POSTP1-001V2A-PAD4-R1"
REQUEST_SCHEMA_VERSION = "ETF_CALENDAR_SCIENTIFIC_WORKER_REQUEST_V1_R1"
RESPONSE_SCHEMA_VERSION = "ETF_CALENDAR_SCIENTIFIC_WORKER_RESPONSE_V1_R1"

WORKER_ENTRYPOINT_MODULE = "etf_calendar_worker.entry_r1"
WORKER_ENTRYPOINT_RELATIVE_PATH = "etf_calendar_worker/entry_r1.py"
WORKER_PROTOCOL_MODULE = "etf_calendar_worker.protocol_r1"
WORKER_PROTOCOL_RELATIVE_PATH = "etf_calendar_worker/protocol_r1.py"
WORKER_PACKAGE_RELATIVE_PATH = "etf_calendar_worker/__init__.py"

#: The repository-owned modules that are *authoritative scientific worker
#: source*.  The closed worker-coding rule is scoped to exactly these.  Every
#: other certified module is ordinary certified project source.
AUTHORITATIVE_WORKER_SOURCE: tuple[str, ...] = (
    WORKER_ENTRYPOINT_RELATIVE_PATH,
    WORKER_PROTOCOL_RELATIVE_PATH,
)

#: The top-level import roots a certified worker process may load project code
#: from.  Anything loaded under one of these roots must be a manifest member.
CERTIFIED_PACKAGE_ROOTS: tuple[str, ...] = ("btc_predictor", "etf_calendar_worker")

#: The exact frozen proof interpreter.  The owning authority is
#: ``ETF_CALENDAR_COMPILED_BINDING_WITNESS``; the decision module verifies this
#: restatement against it mechanically so the two can never drift.
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

REFUSE_SCIENTIFIC_AUTHORITY = "REFUSE_SCIENTIFIC_AUTHORITY"
RESULT_NOT_ADMITTED = "RESULT_NOT_ADMITTED"
DATA_QUALITY_FAIL = "DATA_QUALITY_FAIL"
NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER = "NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER"
NON_CERTIFIED_DEPENDENCY_ENVIRONMENT = "NON_CERTIFIED_DEPENDENCY_ENVIRONMENT"

SUCCESS = "SUCCESS"
REFUSED = "REFUSED"

MAX_REQUEST_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 120

STDOUT_PROTOCOL = "EXACTLY_ONE_CANONICAL_JSON_PAYLOAD_PLUS_ONE_TRAILING_NEWLINE"
STDERR_PROTOCOL = "DIAGNOSTICS_ONLY_NEVER_SCIENTIFIC_EVIDENCE"

#: The exact frozen read-only scientific operations.  There is no arbitrary
#: callable dispatch anywhere in the boundary.
FROZEN_WORKER_OPERATIONS: tuple[str, ...] = (
    "common_etf_session_status",
    "derive_etf_window_calendar",
    "scientific_etf_flow_window",
)

AUTHORITATIVE_EVIDENCE_ADMISSION_MODE = "PRODUCTION_SIGNED_ENVELOPE_REPLAY"
PROTOTYPE_EVIDENCE_ADMISSION_MODE = "NON_AUTHORITATIVE_CANONICAL_RECORD_REPLAY"
EVIDENCE_ADMISSION_MODES: tuple[str, ...] = (
    AUTHORITATIVE_EVIDENCE_ADMISSION_MODE,
    PROTOTYPE_EVIDENCE_ADMISSION_MODE,
)

FORBIDDEN_SCIENTIFIC_IPC: tuple[str, ...] = ("pickle", "cloudpickle", "dill", "marshal")

PRIVATE_KEY_FILE_ENV_VAR = "BTC_TRUSTED_ACQUISITION_PRIVATE_KEY_FILE"


class ScientificWorkerProtocolError(ValueError):
    """Raised when the isolated worker protocol must refuse."""

    def __init__(self, reason: str, detail: str = "", evidence: Any = None) -> None:
        super().__init__(f"{reason}: {detail}" if detail else reason)
        self.reason = reason
        self.detail = detail
        self.evidence = evidence


# ---------------------------------------------------------------------------
# Canonical non-executable serialization
# ---------------------------------------------------------------------------


def _refuse_constant(token: str) -> Any:
    raise ScientificWorkerProtocolError(
        "NON_FINITE_JSON_CONSTANT_REFUSED", f"canonical payloads reject {token!r}"
    )


def canonical_json_bytes(payload: Any) -> bytes:
    """Serialize deterministically: sorted keys, ASCII only, no NaN/Infinity."""

    try:
        text = json.dumps(
            payload,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as error:
        raise ScientificWorkerProtocolError(
            "PAYLOAD_IS_NOT_CANONICAL_JSON_SERIALIZABLE", str(error)
        ) from error
    return text.encode("ascii")


def parse_canonical_json(raw: bytes) -> Any:
    """Parse exactly one canonical JSON document; trailing data refuses."""

    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as error:
        raise ScientificWorkerProtocolError(
            "CANONICAL_PAYLOAD_IS_NOT_ASCII", str(error)
        ) from error
    try:
        return json.loads(text, parse_constant=_refuse_constant)
    except json.JSONDecodeError as error:
        raise ScientificWorkerProtocolError(
            "CANONICAL_PAYLOAD_IS_NOT_ONE_JSON_DOCUMENT", str(error)
        ) from error


def assert_canonical_request_bytes(raw: bytes) -> Any:
    """The scientific IPC payload must be exactly canonical JSON bytes.

    This is the enforceable form of the no-pickle rule: the transport is a
    deterministic non-executable document that re-serializes to itself, so no
    serialized executable Python object graph can be the request.
    """

    payload = parse_canonical_json(raw)
    if canonical_json_bytes(payload) != raw:
        raise ScientificWorkerProtocolError(
            "SCIENTIFIC_IPC_PAYLOAD_IS_NOT_CANONICAL",
            "the request does not re-serialize to the exact bytes received",
        )
    return payload


def digest_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def digest_payload(payload: Any) -> str:
    return digest_bytes(canonical_json_bytes(payload))


def file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical_utc_timestamp(value: str, field: str) -> datetime:
    """Accept only an explicit canonical UTC timestamp that round-trips."""

    if not isinstance(value, str):
        raise ScientificWorkerProtocolError(
            "TIMESTAMP_IS_NOT_A_CANONICAL_STRING", field
        )
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise ScientificWorkerProtocolError(
            "TIMESTAMP_IS_NOT_ISO_8601", f"{field}: {error}"
        ) from error
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ScientificWorkerProtocolError(
            "TIMESTAMP_IS_NOT_EXPLICIT_UTC", f"{field}={value!r}"
        )
    canonical = parsed.astimezone(UTC)
    if canonical.isoformat() != value:
        raise ScientificWorkerProtocolError(
            "TIMESTAMP_IS_NOT_CANONICAL_UTC",
            f"{field}={value!r} != {canonical.isoformat()!r}",
        )
    return canonical


def canonical_date(value: str, field: str) -> date:
    if not isinstance(value, str):
        raise ScientificWorkerProtocolError("DATE_IS_NOT_A_CANONICAL_STRING", field)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as error:
        raise ScientificWorkerProtocolError(
            "DATE_IS_NOT_ISO_8601", f"{field}: {error}"
        ) from error
    if parsed.isoformat() != value:
        raise ScientificWorkerProtocolError("DATE_IS_NOT_CANONICAL", field)
    return parsed


# ---------------------------------------------------------------------------
# Frozen proof interpreter
# ---------------------------------------------------------------------------


def current_interpreter_identity() -> dict[str, Any]:
    """Read the live interpreter identity, without importing ``importlib``."""

    version = sys.version_info
    return {
        "implementation_name": sys.implementation.name,
        "version_major": version.major,
        "version_minor": version.minor,
        "version_micro": version.micro,
        "version_releaselevel": version.releaselevel,
        "version_serial": version.serial,
        "hexversion": sys.hexversion,
        "cache_tag": sys.implementation.cache_tag,
        "magic_number_hex": _bytecode_magic_hex(),
    }


def _bytecode_magic_hex() -> str:
    """Return the bytecode magic without importing ``importlib``."""

    bootstrap = sys.modules.get("_frozen_importlib_external")
    raw = getattr(bootstrap, "MAGIC_NUMBER", None)
    if not isinstance(raw, (bytes, bytearray)):
        raise ScientificWorkerProtocolError(
            REFUSE_SCIENTIFIC_AUTHORITY, "bytecode magic number is unavailable"
        )
    return bytes(raw).hex()


def verify_proof_interpreter_identity(
    observed: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    identity = dict(current_interpreter_identity() if observed is None else observed)
    if set(identity) != set(PROOF_INTERPRETER_IDENTITY):
        raise ScientificWorkerProtocolError(
            REFUSE_SCIENTIFIC_AUTHORITY, "proof interpreter identity shape mismatch"
        )
    mismatched = sorted(
        field
        for field, expected in PROOF_INTERPRETER_IDENTITY.items()
        if identity[field] != expected
    )
    if mismatched:
        raise ScientificWorkerProtocolError(
            REFUSE_SCIENTIFIC_AUTHORITY,
            f"frozen proof interpreter mismatch on {mismatched!r}",
        )
    return identity


# ---------------------------------------------------------------------------
# Repair A — executed bytecode is bound to certified source
# ---------------------------------------------------------------------------

BYTECODE_CACHE_NAMESPACE_RULE = (
    "FRESH_CONTROLLER_CREATED_EMPTY_PER_WORKER_BYTECODE_CACHE_NAMESPACE"
)
BYTECODE_CACHE_NAMESPACE_MECHANISM = "INTERPRETER_X_OPTION_PYCACHE_PREFIX"


def _resolved(path: str | Path) -> Path:
    return Path(path).resolve()


def _is_within(candidate: Path, root: Path) -> bool:
    return candidate == root or root in candidate.parents


def verify_bytecode_cache_namespace(declared_prefix: str) -> dict[str, Any]:
    """Refuse unless the worker runs in a fresh, empty, declared cache namespace.

    ``-B`` only suppresses bytecode *writes*.  It does not suppress or validate
    bytecode *reads*, so a forged ``__pycache__`` entry whose timestamp
    invalidation header still matches the certified source executes in its
    place.  The structural repair is a controller-created, empty,
    per-worker cache namespace: adjacent ``__pycache__`` directories are then
    never consulted at all, for project source and for installed third-party
    source alike.

    This runs before *any* certified module is imported, including this
    module's own package, so it is duplicated inline in the worker entrypoint.
    """

    if not isinstance(declared_prefix, str) or not declared_prefix:
        raise ScientificWorkerProtocolError(
            "BYTECODE_CACHE_NAMESPACE_IS_NOT_DECLARED", repr(declared_prefix)
        )
    declared = _resolved(declared_prefix)
    observed_prefix = sys.pycache_prefix
    if not isinstance(observed_prefix, str) or _resolved(observed_prefix) != declared:
        raise ScientificWorkerProtocolError(
            "BYTECODE_CACHE_NAMESPACE_IS_NOT_THE_DECLARED_PREFIX",
            f"observed {observed_prefix!r} declared {str(declared)!r}",
        )
    if sys.dont_write_bytecode is not True:
        raise ScientificWorkerProtocolError(
            "WORKER_MAY_WRITE_CACHED_BYTECODE", "sys.dont_write_bytecode is not True"
        )
    if not declared.is_dir():
        raise ScientificWorkerProtocolError(
            "BYTECODE_CACHE_NAMESPACE_IS_MISSING", str(declared)
        )
    existing = sorted(entry.name for entry in declared.iterdir())
    if existing:
        raise ScientificWorkerProtocolError(
            "BYTECODE_CACHE_NAMESPACE_IS_NOT_FRESH",
            f"{str(declared)!r} already contains {existing[:8]!r}",
        )
    return {
        "bytecode_cache_namespace_rule": BYTECODE_CACHE_NAMESPACE_RULE,
        "bytecode_cache_namespace_mechanism": BYTECODE_CACHE_NAMESPACE_MECHANISM,
        "bytecode_cache_namespace_fresh_and_empty": True,
        "worker_may_write_cached_bytecode": False,
    }


def verify_cache_namespace_is_not_shared_with_the_project(
    declared_prefix: str, project_root: Path
) -> None:
    """The cache namespace may never be the repository's own ``__pycache__``."""

    declared = _resolved(declared_prefix)
    root = _resolved(project_root)
    if _is_within(declared, root) or _is_within(root, declared):
        raise ScientificWorkerProtocolError(
            "BYTECODE_CACHE_NAMESPACE_IS_SHARED_WITH_THE_PROJECT_TREE",
            f"{str(declared)!r} overlaps {str(root)!r}",
        )
    if declared.name == "__pycache__":
        raise ScientificWorkerProtocolError(
            "BYTECODE_CACHE_NAMESPACE_IS_AN_ORDINARY_PYCACHE_DIRECTORY", str(declared)
        )


def verify_loaded_module_bytecode_binding(
    declared_prefix: str, roots: Sequence[str], phase: str
) -> tuple[str, ...]:
    """Every loaded module under ``roots`` must be cached inside the namespace.

    With a fresh cache namespace CPython still records ``__cached__``; it just
    points inside the namespace instead of an adjacent ``__pycache__``.  A
    module whose ``__cached__`` lies outside the declared namespace was
    resolved through a bytecode path this architecture does not control.
    """

    declared = _resolved(declared_prefix)
    checked: list[str] = []
    for name in sorted(sys.modules):
        root = name.partition(".")[0]
        if root not in roots:
            continue
        module = sys.modules[name]
        if not isinstance(module, types.ModuleType):
            continue
        cached = getattr(module, "__cached__", None)
        if cached is None:
            continue
        if not isinstance(cached, str):
            raise ScientificWorkerProtocolError(
                "MODULE_BYTECODE_CACHE_PATH_IS_UNDECLARED", f"{phase}: {name}"
            )
        if not _is_within(_resolved(cached), declared):
            raise ScientificWorkerProtocolError(
                "MODULE_BYTECODE_IS_NOT_BOUND_TO_THE_FRESH_CACHE_NAMESPACE",
                f"{phase}: {name} cached at {cached}",
            )
        checked.append(name)
    return tuple(checked)


# ---------------------------------------------------------------------------
# One request, one process
# ---------------------------------------------------------------------------

_REQUEST_CLAIMED = False
SECOND_REQUEST_REFUSAL = "SECOND_SCIENTIFIC_REQUEST_IN_ONE_WORKER_PROCESS_UNSUPPORTED"


def claim_single_request() -> None:
    """Admit exactly one scientific request per worker process."""

    global _REQUEST_CLAIMED
    if _REQUEST_CLAIMED:
        raise ScientificWorkerProtocolError(
            SECOND_REQUEST_REFUSAL,
            "a successful worker handles exactly one request and then exits",
        )
    _REQUEST_CLAIMED = True


def reset_single_request_claim_for_tests() -> None:
    """Test-only reset; never used by the worker entrypoint."""

    global _REQUEST_CLAIMED
    _REQUEST_CLAIMED = False


# ---------------------------------------------------------------------------
# Lazy / unmaterialized result refusal
# ---------------------------------------------------------------------------

LAZY_RESULT_KINDS: tuple[str, ...] = (
    "GENERATOR",
    "ASYNC_GENERATOR",
    "COROUTINE",
    "AWAITABLE",
    "ITERATOR",
    "MEMORYVIEW",
    "CALLABLE",
)


def lazy_result_kind(value: Any) -> str | None:
    """Classify a result that would continue executing after the response."""

    if isinstance(value, types.GeneratorType):
        return "GENERATOR"
    if isinstance(value, types.AsyncGeneratorType):
        return "ASYNC_GENERATOR"
    if isinstance(value, types.CoroutineType):
        return "COROUTINE"
    if hasattr(value, "__await__"):
        return "AWAITABLE"
    if isinstance(value, memoryview):
        return "MEMORYVIEW"
    if callable(value):
        return "CALLABLE"
    if hasattr(value, "__next__"):
        return "ITERATOR"
    return None


def refuse_lazy_result(value: Any) -> None:
    kind = lazy_result_kind(value)
    if kind is not None:
        raise ScientificWorkerProtocolError(
            "LAZY_SCIENTIFIC_RESULT_REFUSED",
            f"a {kind} would execute after the worker response boundary",
        )


# ---------------------------------------------------------------------------
# Repair B — the certified project source manifest is consumed, never derived
# ---------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class ProjectSourceEntry:
    """One certified project-owned source file permitted inside the worker."""

    module: str
    path: str
    sha256: str

    def as_material(self) -> dict[str, str]:
        return {"module": self.module, "path": self.path, "sha256": self.sha256}


def module_relative_path(module: str) -> str:
    """The canonical source path of a dotted certified module file."""

    return "/".join(module.split(".")) + ".py"


def package_relative_path(module: str) -> str:
    return "/".join(module.split(".")) + "/__init__.py"


def certified_root(module: str) -> str | None:
    root = module.partition(".")[0]
    return root if root in CERTIFIED_PACKAGE_ROOTS else None


def project_source_entries(
    manifest: Sequence[Mapping[str, Any]],
) -> tuple[ProjectSourceEntry, ...]:
    entries: list[ProjectSourceEntry] = []
    seen: set[str] = set()
    for row in manifest:
        if not isinstance(row, dict) or set(row) != {"module", "path", "sha256"}:
            raise ScientificWorkerProtocolError(
                "PROJECT_SOURCE_MANIFEST_ROW_SHAPE_REFUSED",
                repr(sorted(row) if isinstance(row, dict) else row),
            )
        module, path, sha = row["module"], row["path"], row["sha256"]
        if not isinstance(module, str) or certified_root(module) is None:
            raise ScientificWorkerProtocolError(
                "PROJECT_SOURCE_MANIFEST_MODULE_REFUSED", repr(module)
            )
        if not isinstance(path, str) or path.startswith("/") or ".." in path.split("/"):
            raise ScientificWorkerProtocolError(
                "PROJECT_SOURCE_MANIFEST_PATH_REFUSED", repr(path)
            )
        if not isinstance(sha, str) or len(sha) != 64:
            raise ScientificWorkerProtocolError(
                "PROJECT_SOURCE_MANIFEST_DIGEST_REFUSED", repr(sha)
            )
        if module in seen:
            raise ScientificWorkerProtocolError(
                "PROJECT_SOURCE_MANIFEST_DUPLICATE_MODULE", module
            )
        if path not in (module_relative_path(module), package_relative_path(module)):
            raise ScientificWorkerProtocolError(
                "PROJECT_SOURCE_MANIFEST_PATH_DOES_NOT_MATCH_MODULE",
                f"{module} -> {path}",
            )
        seen.add(module)
        entries.append(ProjectSourceEntry(module, path, sha))
    if not entries:
        raise ScientificWorkerProtocolError(
            "PROJECT_SOURCE_MANIFEST_IS_EMPTY", "a worker requires certified source"
        )
    ordered = tuple(sorted(entries))
    if ordered != tuple(entries):
        raise ScientificWorkerProtocolError(
            "PROJECT_SOURCE_MANIFEST_IS_NOT_CANONICALLY_ORDERED", ""
        )
    return ordered


def manifest_digest(entries: Sequence[ProjectSourceEntry]) -> str:
    return digest_payload([entry.as_material() for entry in entries])


def verify_project_source_manifest(
    project_root: Path, entries: Sequence[ProjectSourceEntry]
) -> dict[str, str]:
    """Every certified source file must exist at its path with its exact SHA.

    ``entries`` is the *expected* manifest carried from the trusted controller
    authority context.  It is never re-derived from whatever happens to be on
    disk: an unknown, missing, additional or altered entry refuses.
    """

    resolved: dict[str, str] = {}
    for entry in entries:
        target = project_root / entry.path
        if not target.is_file():
            raise ScientificWorkerProtocolError(
                "CERTIFIED_SOURCE_FILE_MISSING", f"{entry.module} -> {entry.path}"
            )
        observed = file_sha256(target)
        if observed != entry.sha256:
            raise ScientificWorkerProtocolError(
                "CERTIFIED_SOURCE_SHA_MISMATCH",
                f"{entry.module}: expected {entry.sha256} observed {observed}",
            )
        resolved[entry.module] = str(target.resolve())
    return resolved


def verify_loaded_project_modules(
    entries: Sequence[ProjectSourceEntry],
    resolved: Mapping[str, str],
    required: Sequence[str],
    phase: str,
) -> tuple[str, ...]:
    """Loaded certified modules must be certified, at their certified origin.

    The exact ``__file__`` and ``__spec__.origin`` source-path checks are the
    preserved refusal for a project module loaded from a ``.pyc`` instead of
    its certified ``.py`` origin, or from a shadowing wrong origin.
    """

    certified = {entry.module for entry in entries}
    loaded = sorted(
        name for name in list(sys.modules) if certified_root(name) is not None
    )
    unexpected = [name for name in loaded if name not in certified]
    if unexpected:
        raise ScientificWorkerProtocolError(
            "UNEXPECTED_PROJECT_MODULE", f"{phase}: {unexpected!r}"
        )
    missing = [name for name in required if name not in loaded]
    if missing:
        raise ScientificWorkerProtocolError(
            "REQUIRED_PROJECT_MODULE_NOT_LOADED", f"{phase}: {missing!r}"
        )
    for name in loaded:
        module = sys.modules[name]
        file_attribute = getattr(module, "__file__", None)
        spec = getattr(module, "__spec__", None)
        origin = getattr(spec, "origin", None)
        if not isinstance(file_attribute, str) or not isinstance(origin, str):
            raise ScientificWorkerProtocolError(
                "PROJECT_MODULE_ORIGIN_IS_UNDECLARED", f"{phase}: {name}"
            )
        expected = resolved.get(name)
        actual = str(Path(origin).resolve())
        if expected is None or actual != expected:
            raise ScientificWorkerProtocolError(
                "WRONG_PROJECT_MODULE_ORIGIN",
                f"{phase}: {name} resolved to {actual} not {expected}",
            )
        if str(Path(file_attribute).resolve()) != expected:
            raise ScientificWorkerProtocolError(
                "PROJECT_MODULE_FILE_ATTRIBUTE_DIVERGES_FROM_ORIGIN",
                f"{phase}: {name}",
            )
    return tuple(loaded)


# ---------------------------------------------------------------------------
# Repair D — exact reviewed third-party semantic and artifact authority
# ---------------------------------------------------------------------------

#: The only ``RECORD`` content-hash algorithm this architecture accepts.  An
#: unknown algorithm is never silently skipped: it refuses.  Supporting another
#: algorithm requires explicit review and an explicit parent-bound extension.
ACCEPTED_RECORD_HASH_ALGORITHMS: tuple[str, ...] = ("sha256",)

#: The two explicitly reviewed classes of ``RECORD`` row that legitimately
#: declare no content hash.
RECORD_SELF_REFERENTIAL_EXCEPTION = "DISTRIBUTION_OWN_RECORD_MANIFEST"
RECORD_INSTALL_GENERATED_BYTECODE_EXCEPTION = "INSTALL_GENERATED_PYCACHE_BYTECODE"


def normalize_distribution_name(name: str) -> str:
    """PEP 503 canonical distribution name."""

    normalized: list[str] = []
    previous_separator = False
    for character in name.strip().lower():
        if character in "-_.":
            if not previous_separator:
                normalized.append("-")
            previous_separator = True
        else:
            normalized.append(character)
            previous_separator = False
    return "".join(normalized)


@dataclass(frozen=True, order=True)
class FrozenDistributionAuthority:
    """The exact reviewed semantic and artifact identity of one distribution.

    Every field here is parent-bound reviewed material.  Absolute installation
    paths are deliberately *not* here: they are launch material, carried by
    :class:`InstalledDistributionObservation`.
    """

    distribution: str
    version: str
    metadata_name: str
    dist_info_directory: str
    record_sha256: str
    record_content_manifest_digest: str
    record_row_count: int
    hashed_row_count: int
    root_modules: tuple[str, ...]

    def as_material(self) -> dict[str, Any]:
        return {
            "distribution": self.distribution,
            "version": self.version,
            "metadata_name": self.metadata_name,
            "dist_info_directory": self.dist_info_directory,
            "record_sha256": self.record_sha256,
            "record_content_manifest_digest": self.record_content_manifest_digest,
            "record_row_count": self.record_row_count,
            "hashed_row_count": self.hashed_row_count,
            "root_modules": list(self.root_modules),
        }


@dataclass(frozen=True, order=True)
class InstalledDistributionObservation:
    """Launch-bound observed installation material for one distribution."""

    distribution: str
    location: str
    record_path: str
    environment_root: str

    def as_material(self) -> dict[str, Any]:
        return {
            "distribution": self.distribution,
            "location": self.location,
            "record_path": self.record_path,
            "environment_root": self.environment_root,
        }


_AUTHORITY_FIELDS = frozenset(
    {
        "distribution",
        "version",
        "metadata_name",
        "dist_info_directory",
        "record_sha256",
        "record_content_manifest_digest",
        "record_row_count",
        "hashed_row_count",
        "root_modules",
    }
)
_OBSERVATION_FIELDS = frozenset(
    {"distribution", "location", "record_path", "environment_root"}
)


def frozen_distribution_authorities(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[FrozenDistributionAuthority, ...]:
    entries: list[FrozenDistributionAuthority] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != _AUTHORITY_FIELDS:
            raise ScientificWorkerProtocolError(
                "THIRD_PARTY_AUTHORITY_ROW_SHAPE_REFUSED",
                repr(sorted(row) if isinstance(row, dict) else row),
            )
        roots = row["root_modules"]
        if (
            not isinstance(roots, list)
            or not roots
            or not all(isinstance(name, str) and name for name in roots)
            or list(roots) != sorted(roots)
        ):
            raise ScientificWorkerProtocolError(
                "THIRD_PARTY_AUTHORITY_ROOT_MODULES_REFUSED", repr(roots)
            )
        for field in ("record_sha256", "record_content_manifest_digest"):
            value = row[field]
            if (
                not isinstance(value, str)
                or len(value) != 64
                or any(character not in "0123456789abcdef" for character in value)
            ):
                raise ScientificWorkerProtocolError(
                    "THIRD_PARTY_AUTHORITY_DIGEST_REFUSED", f"{field}={value!r}"
                )
        for field in ("record_row_count", "hashed_row_count"):
            value = row[field]
            if not isinstance(value, int) or isinstance(value, bool) or value < 1:
                raise ScientificWorkerProtocolError(
                    "THIRD_PARTY_AUTHORITY_ROW_COUNT_REFUSED", f"{field}={value!r}"
                )
        for field in ("distribution", "version", "metadata_name", "dist_info_directory"):
            if not isinstance(row[field], str) or not row[field]:
                raise ScientificWorkerProtocolError(
                    "THIRD_PARTY_AUTHORITY_FIELD_REFUSED", f"{field}={row[field]!r}"
                )
        if row["distribution"] != normalize_distribution_name(row["distribution"]):
            raise ScientificWorkerProtocolError(
                "THIRD_PARTY_AUTHORITY_DISTRIBUTION_IS_NOT_CANONICAL",
                repr(row["distribution"]),
            )
        entries.append(
            FrozenDistributionAuthority(
                distribution=row["distribution"],
                version=row["version"],
                metadata_name=row["metadata_name"],
                dist_info_directory=row["dist_info_directory"],
                record_sha256=row["record_sha256"],
                record_content_manifest_digest=row["record_content_manifest_digest"],
                record_row_count=row["record_row_count"],
                hashed_row_count=row["hashed_row_count"],
                root_modules=tuple(roots),
            )
        )
    if not entries:
        raise ScientificWorkerProtocolError("THIRD_PARTY_AUTHORITY_IS_EMPTY", "")
    ordered = tuple(sorted(entries))
    if ordered != tuple(entries):
        raise ScientificWorkerProtocolError(
            "THIRD_PARTY_AUTHORITY_IS_NOT_CANONICALLY_ORDERED", ""
        )
    if len({entry.distribution for entry in entries}) != len(entries):
        raise ScientificWorkerProtocolError(
            "THIRD_PARTY_AUTHORITY_DUPLICATE_DISTRIBUTION", ""
        )
    return ordered


def installed_distribution_observations(
    rows: Sequence[Mapping[str, Any]],
) -> tuple[InstalledDistributionObservation, ...]:
    entries: list[InstalledDistributionObservation] = []
    for row in rows:
        if not isinstance(row, dict) or set(row) != _OBSERVATION_FIELDS:
            raise ScientificWorkerProtocolError(
                "THIRD_PARTY_ENVIRONMENT_ROW_SHAPE_REFUSED",
                repr(sorted(row) if isinstance(row, dict) else row),
            )
        if not all(isinstance(row[field], str) and row[field] for field in row):
            raise ScientificWorkerProtocolError(
                "THIRD_PARTY_ENVIRONMENT_FIELD_REFUSED", repr(sorted(row))
            )
        entries.append(
            InstalledDistributionObservation(
                distribution=row["distribution"],
                location=row["location"],
                record_path=row["record_path"],
                environment_root=row["environment_root"],
            )
        )
    ordered = tuple(sorted(entries))
    if ordered != tuple(entries):
        raise ScientificWorkerProtocolError(
            "THIRD_PARTY_ENVIRONMENT_IS_NOT_CANONICALLY_ORDERED", ""
        )
    return ordered


def third_party_authority_digest(
    entries: Sequence[FrozenDistributionAuthority],
) -> str:
    return digest_payload([entry.as_material() for entry in entries])


def third_party_environment_digest(
    entries: Sequence[InstalledDistributionObservation],
) -> str:
    return digest_payload([entry.as_material() for entry in entries])


@dataclass(frozen=True, order=True)
class RecordRow:
    """One deterministically parsed installed ``RECORD`` row."""

    path: str
    algorithm: str | None
    digest_hex: str | None
    size: int | None

    def as_material(self) -> list[Any]:
        return [self.path, self.algorithm, self.digest_hex, self.size]


def parse_record_rows(text: str, distribution: str) -> tuple[RecordRow, ...]:
    """Bounded, deterministic ``RECORD`` parsing.

    A row must be exactly ``path,algorithm=base64,size``.  An unknown hash
    algorithm refuses rather than being silently skipped, and a malformed or
    ambiguous path refuses rather than being resolved by guesswork.
    """

    rows: list[RecordRow] = []
    seen: set[str] = set()
    for fields in csv.reader(io.StringIO(text, newline="")):
        if not fields:
            continue
        if len(fields) != 3:
            raise ScientificWorkerProtocolError(
                NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                f"{distribution}: RECORD row is not path,hash,size: {fields!r}",
            )
        raw_path, raw_hash, raw_size = fields
        if raw_path in seen:
            raise ScientificWorkerProtocolError(
                NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                f"{distribution}: duplicate RECORD row {raw_path!r}",
            )
        seen.add(raw_path)
        algorithm: str | None = None
        digest_hex: str | None = None
        if raw_hash:
            algorithm, separator, encoded = raw_hash.partition("=")
            if not separator or not encoded:
                raise ScientificWorkerProtocolError(
                    NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                    f"{distribution}: malformed RECORD hash {raw_hash!r}",
                )
            if algorithm not in ACCEPTED_RECORD_HASH_ALGORITHMS:
                raise ScientificWorkerProtocolError(
                    NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                    f"{distribution}: unreviewed RECORD hash algorithm {algorithm!r}",
                )
            padding = "=" * (-len(encoded) % 4)
            try:
                digest_hex = base64.urlsafe_b64decode(encoded + padding).hex()
            except (binascii.Error, ValueError) as error:
                raise ScientificWorkerProtocolError(
                    NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                    f"{distribution}: undecodable RECORD hash {raw_hash!r}: {error}",
                ) from error
            if len(digest_hex) != 64:
                raise ScientificWorkerProtocolError(
                    NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                    f"{distribution}: RECORD hash is not a sha256 digest {raw_hash!r}",
                )
        size: int | None = None
        if raw_size:
            try:
                size = int(raw_size)
            except ValueError as error:
                raise ScientificWorkerProtocolError(
                    NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                    f"{distribution}: malformed RECORD size {raw_size!r}",
                ) from error
            if size < 0:
                raise ScientificWorkerProtocolError(
                    NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                    f"{distribution}: negative RECORD size {raw_size!r}",
                )
        rows.append(RecordRow(raw_path, algorithm, digest_hex, size))
    if not rows:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT, f"{distribution}: RECORD is empty"
        )
    return tuple(sorted(rows, key=lambda row: row.path))


def record_content_manifest_digest(rows: Sequence[RecordRow]) -> str:
    """A normalized, machine-independent identity for a ``RECORD`` artifact."""

    return digest_payload(
        [row.as_material() for row in sorted(rows, key=lambda row: row.path)]
    )


def resolve_record_path(
    location: Path, environment_root: Path, raw: str, distribution: str
) -> Path:
    """Resolve one ``RECORD`` path deterministically and safely.

    Console-script rows legitimately escape ``site-packages`` with leading
    ``..`` segments.  Anything else — an absolute path, a Windows separator, a
    ``.`` segment, an interior ``..``, a directory row, or a resolution that
    leaves the installation environment — is malformed or ambiguous for the
    frozen installed layout and refuses.
    """

    if not raw or raw.startswith("/") or raw.startswith("~") or "\\" in raw:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{distribution}: RECORD path is not a relative installed path {raw!r}",
        )
    parts = raw.split("/")
    if any(part in ("", ".") for part in parts):
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{distribution}: ambiguous RECORD path {raw!r}",
        )
    seen_named_segment = False
    for part in parts:
        if part == "..":
            if seen_named_segment:
                raise ScientificWorkerProtocolError(
                    NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                    f"{distribution}: interior RECORD path traversal {raw!r}",
                )
        else:
            seen_named_segment = True
    target = (location / raw).resolve()
    if not _is_within(target, environment_root):
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{distribution}: RECORD path {raw!r} escapes the installation environment",
        )
    return target


def verify_installed_distribution_content(
    authority: FrozenDistributionAuthority,
    observation: InstalledDistributionObservation,
    *,
    bytecode_namespace_enforced: bool,
) -> dict[str, Any]:
    """Verify one installed distribution against its reviewed ``RECORD``.

    ``PAD4`` hashed the ``RECORD`` file and stopped there, so a tampered
    installed file whose ``RECORD`` bytes were untouched executed inside the
    worker.  This verifies the exact reviewed semantic identity, the exact
    reviewed artifact identity, and then every byte of every installed file the
    reviewed ``RECORD`` declares a hash for — before any dependency code runs.
    """

    if authority.distribution != observation.distribution:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: environment row does not match the authority row",
        )
    environment_root = _resolved(observation.environment_root)
    location = _resolved(observation.location)
    record = _resolved(observation.record_path)
    if not _is_within(location, environment_root):
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: install location is outside its environment",
        )
    if not _is_within(record, environment_root):
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: RECORD is outside its environment",
        )
    if not record.is_file():
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: {observation.record_path} is missing",
        )
    dist_info = record.parent
    if dist_info.name != authority.dist_info_directory:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: installed metadata directory is "
            f"{dist_info.name!r} not the reviewed {authority.dist_info_directory!r}",
        )

    observed_record_sha = file_sha256(record)
    if observed_record_sha != authority.record_sha256:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: reviewed RECORD artifact identity "
            f"{authority.record_sha256} observed {observed_record_sha}",
        )
    try:
        text = record.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: RECORD is not UTF-8: {error}",
        ) from error
    rows = parse_record_rows(text, authority.distribution)
    if len(rows) != authority.record_row_count:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: RECORD declares {len(rows)} rows, "
            f"reviewed {authority.record_row_count}",
        )
    observed_manifest = record_content_manifest_digest(rows)
    if observed_manifest != authority.record_content_manifest_digest:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: reviewed RECORD content manifest "
            f"{authority.record_content_manifest_digest} observed {observed_manifest}",
        )

    _verify_reviewed_semantic_version(authority, dist_info)

    record_row_name = f"{authority.dist_info_directory}/RECORD"
    verified: list[list[Any]] = []
    unhashed: list[str] = []
    hashed_rows = 0
    for row in rows:
        if row.algorithm is None:
            if row.path == record_row_name:
                unhashed.append(RECORD_SELF_REFERENTIAL_EXCEPTION)
                continue
            if (
                bytecode_namespace_enforced
                and row.path.endswith(".pyc")
                and "__pycache__/" in row.path
            ):
                unhashed.append(RECORD_INSTALL_GENERATED_BYTECODE_EXCEPTION)
                continue
            raise ScientificWorkerProtocolError(
                NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                f"{authority.distribution}: installed file {row.path!r} declares "
                "no reviewed content hash",
            )
        hashed_rows += 1
        target = resolve_record_path(
            location, environment_root, row.path, authority.distribution
        )
        if not target.is_file():
            raise ScientificWorkerProtocolError(
                NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                f"{authority.distribution}: declared installed file {row.path!r} is missing",
            )
        data = target.read_bytes()
        observed = hashlib.sha256(data).hexdigest()
        if observed != row.digest_hex:
            raise ScientificWorkerProtocolError(
                NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                f"{authority.distribution}: installed file {row.path!r} declares "
                f"{row.digest_hex} observed {observed}",
            )
        if row.size is not None and len(data) != row.size:
            raise ScientificWorkerProtocolError(
                NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                f"{authority.distribution}: installed file {row.path!r} declares "
                f"size {row.size} observed {len(data)}",
            )
        verified.append([row.path, observed, len(data)])
    if hashed_rows != authority.hashed_row_count:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: verified {hashed_rows} hashed rows, "
            f"reviewed {authority.hashed_row_count}",
        )
    return {
        "distribution": authority.distribution,
        "version": authority.version,
        "reviewed_record_sha256": authority.record_sha256,
        "reviewed_record_content_manifest_digest": (
            authority.record_content_manifest_digest
        ),
        "observed_verified_content_manifest_digest": digest_payload(verified),
        "verified_installed_files": len(verified),
        "reviewed_unhashed_row_exceptions": sorted(set(unhashed)),
    }


def _verify_reviewed_semantic_version(
    authority: FrozenDistributionAuthority, dist_info: Path
) -> None:
    """The observed installed version must be the exact reviewed version.

    ``METADATA`` is itself a ``RECORD``-hashed file whose content manifest has
    already been bound above, so reading the observed name and version from it
    ties the semantic identity to the reviewed artifact rather than to a
    caller-declared string.
    """

    expected_directory = (
        f"{normalize_distribution_name(authority.metadata_name)}-{authority.version}"
        ".dist-info"
    )
    if authority.dist_info_directory != expected_directory:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: reviewed metadata directory "
            f"{authority.dist_info_directory!r} does not state version "
            f"{authority.version!r}",
        )
    metadata = dist_info / "METADATA"
    if not metadata.is_file():
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: installed METADATA is missing",
        )
    observed_name: str | None = None
    observed_version: str | None = None
    for line in metadata.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line:
            break
        if observed_name is None and line.startswith("Name: "):
            observed_name = line[len("Name: ") :].strip()
        elif observed_version is None and line.startswith("Version: "):
            observed_version = line[len("Version: ") :].strip()
    if observed_name is None or observed_version is None:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: installed METADATA declares no name/version",
        )
    if normalize_distribution_name(observed_name) != authority.distribution:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: installed METADATA names {observed_name!r}",
        )
    if observed_name != authority.metadata_name:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: installed METADATA name {observed_name!r} is "
            f"not the reviewed {authority.metadata_name!r}",
        )
    if observed_version != authority.version:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"{authority.distribution}: installed version {observed_version!r} is not "
            f"the reviewed {authority.version!r}",
        )


def verify_third_party_authority(
    authorities: Sequence[FrozenDistributionAuthority],
    observations: Sequence[InstalledDistributionObservation],
    *,
    bytecode_namespace_enforced: bool,
) -> dict[str, Any]:
    """Verify the exact reviewed dependency set, semantics and installed bytes."""

    declared = {entry.distribution for entry in authorities}
    observed = {entry.distribution for entry in observations}
    if declared != observed:
        raise ScientificWorkerProtocolError(
            NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            f"dependency set mismatch: {sorted(declared ^ observed)!r}",
        )
    by_distribution = {entry.distribution: entry for entry in observations}
    evidence = [
        verify_installed_distribution_content(
            authority,
            by_distribution[authority.distribution],
            bytecode_namespace_enforced=bytecode_namespace_enforced,
        )
        for authority in authorities
    ]
    return {
        "distributions": len(evidence),
        "third_party_authority_digest": third_party_authority_digest(authorities),
        "installed_content_verification": "PASS",
        "observed_content_manifest_digest": digest_payload(evidence),
        "per_distribution": evidence,
    }


def verify_loaded_dependency_origins(
    authorities: Sequence[FrozenDistributionAuthority],
    observations: Sequence[InstalledDistributionObservation],
) -> tuple[str, ...]:
    """Every loaded reviewed root module must come from its verified location."""

    by_distribution = {entry.distribution: entry for entry in observations}
    loaded: list[str] = []
    for authority in authorities:
        location = _resolved(by_distribution[authority.distribution].location)
        for root in authority.root_modules:
            module = sys.modules.get(root)
            if module is None:
                continue
            origin = getattr(getattr(module, "__spec__", None), "origin", None)
            if not isinstance(origin, str):
                raise ScientificWorkerProtocolError(
                    NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                    f"{root} declares no origin",
                )
            if not _is_within(_resolved(origin), location):
                raise ScientificWorkerProtocolError(
                    NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
                    f"{root} loaded from {origin} outside {str(location)}",
                )
            loaded.append(root)
    return tuple(sorted(loaded))


# ---------------------------------------------------------------------------
# Controlled worker startup environment
# ---------------------------------------------------------------------------

REQUIRED_INTERPRETER_FLAGS: Mapping[str, str] = {
    "isolated": "ENVIRONMENT_VARIABLE_PYTHON_CONFIGURATION_IGNORED",
    "ignore_environment": "ENVIRONMENT_VARIABLE_PYTHON_CONFIGURATION_IGNORED",
    "no_user_site": "USER_SITE_DISABLED",
    "no_site": "SITECUSTOMIZE_AND_USERCUSTOMIZE_NOT_EXECUTED",
    "safe_path": "UNCONTROLLED_CURRENT_DIRECTORY_IMPORT_PRECEDENCE_DISABLED",
    "dont_write_bytecode": "NO_CACHED_BYTECODE_WRITTEN_BY_THE_WORKER",
}


def verify_controlled_startup(declared_sys_path: Sequence[str]) -> dict[str, Any]:
    """The worker must be running in the frozen, parent-controlled environment."""

    observed = {
        flag: bool(getattr(sys.flags, flag, False))
        for flag in REQUIRED_INTERPRETER_FLAGS
    }
    unmet = sorted(flag for flag, value in observed.items() if not value)
    if unmet:
        raise ScientificWorkerProtocolError(
            "WORKER_STARTUP_IS_NOT_CONTROLLED", f"missing interpreter flags {unmet!r}"
        )
    declared = [str(entry) for entry in declared_sys_path]
    if list(sys.path) != declared:
        raise ScientificWorkerProtocolError(
            "WORKER_SYS_PATH_IS_NOT_PARENT_CONTROLLED",
            f"observed {list(sys.path)!r} declared {declared!r}",
        )
    leaked = sorted(name for name in os.environ if name.startswith("PYTHON"))
    if leaked:
        raise ScientificWorkerProtocolError(
            "AMBIENT_PYTHON_ENVIRONMENT_LEAKED_INTO_THE_WORKER", repr(leaked)
        )
    if PRIVATE_KEY_FILE_ENV_VAR in os.environ:
        raise ScientificWorkerProtocolError(
            "WORKER_SIGNING_CAPABILITY_REFUSED",
            "the scientific worker is an evaluator, never the acquisition signer",
        )
    return {
        "interpreter_flags": dict(sorted(observed.items())),
        "sys_path_digest": digest_payload(declared),
    }


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

REQUEST_FIELDS: Mapping[str, type | tuple[type, ...]] = {
    "request_schema_version": str,
    "worker_authority_version": str,
    "worker_authority_ticket": str,
    "worker_authority_sha256": str,
    "authority_context_origin": str,
    "calendar_authority_version": str,
    "calendar_authority_sha256": str,
    "trusted_persistence_authority_sha256": str,
    "interpreter_identity": dict,
    "project_root": str,
    "sys_path": list,
    "worker_entrypoint_module": str,
    "worker_entrypoint_sha256": str,
    "worker_protocol_sha256": str,
    "project_source_manifest": list,
    "project_source_manifest_digest": str,
    "project_source_manifest_role": str,
    "required_project_modules": list,
    "third_party_authority": list,
    "third_party_authority_digest": str,
    "third_party_environment": list,
    "decision_time": str,
    "operation": str,
    "evidence_admission_mode": str,
    "evidence_records": list,
    "operation_inputs": dict,
}

#: The request field names that carry *scientific authority identity*.  Every
#: one of them must reproduce against the trusted controller authority context;
#: agreement between the request and the response is never sufficient.
AUTHORITY_BOUND_REQUEST_FIELDS: tuple[str, ...] = (
    "calendar_authority_sha256",
    "calendar_authority_version",
    "interpreter_identity",
    "project_source_manifest_digest",
    "project_source_manifest_role",
    "third_party_authority_digest",
    "trusted_persistence_authority_sha256",
    "worker_authority_sha256",
    "worker_authority_ticket",
    "worker_authority_version",
    "worker_entrypoint_module",
    "worker_entrypoint_sha256",
    "worker_protocol_sha256",
)

OPERATION_INPUT_FIELDS: Mapping[str, frozenset[str]] = {
    "common_etf_session_status": frozenset({"trade_date"}),
    "derive_etf_window_calendar": frozenset(
        {"end_date", "earliest_date", "window_days"}
    ),
    "scientific_etf_flow_window": frozenset(
        {"as_of", "funds", "end_date", "earliest_date", "window_days", "etf_flows"}
    ),
}

ETF_FLOW_FIELDS: tuple[str, ...] = (
    "fund",
    "observation_date",
    "flow_usd",
    "aum_usd",
    "provider",
    "source",
    "revision",
    "available_at",
    "ingested_at",
)

PROJECT_SOURCE_MANIFEST_ROLES: tuple[str, ...] = (
    "PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE",
    "POST_I2_FINAL_CALENDAR_PARENT_BOUND_PRODUCTION_AUTHORITY",
)

AUTHORITY_CONTEXT_ORIGINS: tuple[str, ...] = (
    "AUTHORITY_CONSTRUCTION_REFREEZE",
    "FINAL_CALENDAR_AUTHORITY",
    "REVIEW_CANDIDATE_CONTEXT",
)


@dataclass(frozen=True)
class ScientificWorkerRequest:
    """A validated canonical scientific request."""

    payload: Mapping[str, Any]

    @property
    def operation(self) -> str:
        return str(self.payload["operation"])

    @property
    def decision_time(self) -> datetime:
        return canonical_utc_timestamp(
            str(self.payload["decision_time"]), "decision_time"
        )

    @property
    def project_root(self) -> Path:
        return Path(str(self.payload["project_root"]))

    @property
    def source_entries(self) -> tuple[ProjectSourceEntry, ...]:
        return project_source_entries(self.payload["project_source_manifest"])

    @property
    def third_party_authority(self) -> tuple[FrozenDistributionAuthority, ...]:
        return frozen_distribution_authorities(self.payload["third_party_authority"])

    @property
    def third_party_environment(
        self,
    ) -> tuple[InstalledDistributionObservation, ...]:
        return installed_distribution_observations(
            self.payload["third_party_environment"]
        )


def validate_request(payload: Any) -> ScientificWorkerRequest:
    """Refuse unknown fields, wrong types and non-canonical scalars."""

    if not isinstance(payload, dict):
        raise ScientificWorkerProtocolError(
            "REQUEST_IS_NOT_A_JSON_OBJECT", type(payload).__name__
        )
    unknown = sorted(set(payload) - set(REQUEST_FIELDS))
    if unknown:
        raise ScientificWorkerProtocolError("UNKNOWN_REQUEST_FIELD", repr(unknown))
    missing = sorted(set(REQUEST_FIELDS) - set(payload))
    if missing:
        raise ScientificWorkerProtocolError("MISSING_REQUEST_FIELD", repr(missing))
    for field, kind in REQUEST_FIELDS.items():
        if not isinstance(payload[field], kind):
            raise ScientificWorkerProtocolError(
                "REQUEST_FIELD_TYPE_REFUSED",
                f"{field} is {type(payload[field]).__name__}",
            )
    if payload["request_schema_version"] != REQUEST_SCHEMA_VERSION:
        raise ScientificWorkerProtocolError(
            "REQUEST_SCHEMA_VERSION_REFUSED", repr(payload["request_schema_version"])
        )
    if payload["worker_authority_version"] != WORKER_AUTHORITY_VERSION:
        raise ScientificWorkerProtocolError(
            "WORKER_AUTHORITY_VERSION_REFUSED",
            repr(payload["worker_authority_version"]),
        )
    if payload["worker_authority_ticket"] != WORKER_AUTHORITY_TICKET:
        raise ScientificWorkerProtocolError(
            "WORKER_AUTHORITY_TICKET_REFUSED", repr(payload["worker_authority_ticket"])
        )
    if payload["authority_context_origin"] not in AUTHORITY_CONTEXT_ORIGINS:
        raise ScientificWorkerProtocolError(
            "AUTHORITY_CONTEXT_ORIGIN_REFUSED",
            repr(payload["authority_context_origin"]),
        )
    if payload["project_source_manifest_role"] not in PROJECT_SOURCE_MANIFEST_ROLES:
        raise ScientificWorkerProtocolError(
            "PROJECT_SOURCE_MANIFEST_ROLE_REFUSED",
            repr(payload["project_source_manifest_role"]),
        )
    if payload["operation"] not in FROZEN_WORKER_OPERATIONS:
        raise ScientificWorkerProtocolError(
            "UNKNOWN_SCIENTIFIC_OPERATION", repr(payload["operation"])
        )
    if payload["evidence_admission_mode"] not in EVIDENCE_ADMISSION_MODES:
        raise ScientificWorkerProtocolError(
            "UNKNOWN_EVIDENCE_ADMISSION_MODE",
            repr(payload["evidence_admission_mode"]),
        )
    if payload["worker_entrypoint_module"] != WORKER_ENTRYPOINT_MODULE:
        raise ScientificWorkerProtocolError(
            "WORKER_ENTRYPOINT_MODULE_REFUSED",
            repr(payload["worker_entrypoint_module"]),
        )
    for field in (
        "worker_authority_sha256",
        "calendar_authority_sha256",
        "trusted_persistence_authority_sha256",
        "worker_entrypoint_sha256",
        "worker_protocol_sha256",
        "project_source_manifest_digest",
        "third_party_authority_digest",
    ):
        value = payload[field]
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ScientificWorkerProtocolError(
                "REQUEST_DIGEST_FIELD_REFUSED", f"{field}={value!r}"
            )
    canonical_utc_timestamp(payload["decision_time"], "decision_time")
    verify_proof_interpreter_identity(payload["interpreter_identity"])
    entries = project_source_entries(payload["project_source_manifest"])
    if manifest_digest(entries) != payload["project_source_manifest_digest"]:
        raise ScientificWorkerProtocolError(
            "PROJECT_SOURCE_MANIFEST_DIGEST_MISMATCH", ""
        )
    authorities = frozen_distribution_authorities(payload["third_party_authority"])
    if third_party_authority_digest(authorities) != payload[
        "third_party_authority_digest"
    ]:
        raise ScientificWorkerProtocolError("THIRD_PARTY_AUTHORITY_DIGEST_MISMATCH", "")
    installed_distribution_observations(payload["third_party_environment"])
    required = payload["required_project_modules"]
    certified = {entry.module for entry in entries}
    if not all(isinstance(name, str) for name in required):
        raise ScientificWorkerProtocolError("REQUIRED_PROJECT_MODULES_REFUSED", "")
    if list(required) != sorted(required) or len(set(required)) != len(required):
        raise ScientificWorkerProtocolError(
            "REQUIRED_PROJECT_MODULES_NOT_CANONICALLY_ORDERED", ""
        )
    outside = sorted(set(required) - certified)
    if outside:
        raise ScientificWorkerProtocolError(
            "REQUIRED_PROJECT_MODULE_OUTSIDE_MANIFEST", repr(outside)
        )
    for module in (WORKER_ENTRYPOINT_MODULE, WORKER_PROTOCOL_MODULE):
        if module not in certified:
            raise ScientificWorkerProtocolError(
                "AUTHORITATIVE_WORKER_MODULE_IS_NOT_IN_THE_CERTIFIED_MANIFEST", module
            )
    _validate_operation_inputs(payload["operation"], payload["operation_inputs"])
    _validate_evidence_records(payload["evidence_records"])
    if not all(isinstance(entry, str) for entry in payload["sys_path"]):
        raise ScientificWorkerProtocolError("SYS_PATH_ENTRY_REFUSED", "")
    return ScientificWorkerRequest(payload)


def _validate_operation_inputs(operation: str, inputs: Mapping[str, Any]) -> None:
    expected = OPERATION_INPUT_FIELDS[operation]
    if set(inputs) != expected:
        raise ScientificWorkerProtocolError(
            "OPERATION_INPUT_SHAPE_REFUSED",
            f"{operation}: {sorted(set(inputs) ^ expected)!r}",
        )
    if "trade_date" in inputs:
        canonical_date(inputs["trade_date"], "trade_date")
    for field in ("end_date", "earliest_date"):
        if field in inputs:
            canonical_date(inputs[field], field)
    if "as_of" in inputs:
        canonical_utc_timestamp(inputs["as_of"], "as_of")
    if "window_days" in inputs:
        window = inputs["window_days"]
        if not isinstance(window, int) or isinstance(window, bool) or window < 1:
            raise ScientificWorkerProtocolError(
                "WINDOW_DAYS_REFUSED", repr(inputs["window_days"])
            )
    if "funds" in inputs:
        funds = inputs["funds"]
        if not isinstance(funds, list) or not all(isinstance(f, str) for f in funds):
            raise ScientificWorkerProtocolError("FUNDS_REFUSED", repr(funds))
    if "etf_flows" in inputs:
        flows = inputs["etf_flows"]
        if not isinstance(flows, list):
            raise ScientificWorkerProtocolError("ETF_FLOWS_REFUSED", "")
        for row in flows:
            if not isinstance(row, dict) or set(row) != set(ETF_FLOW_FIELDS):
                raise ScientificWorkerProtocolError(
                    "ETF_FLOW_ROW_SHAPE_REFUSED",
                    repr(sorted(row) if isinstance(row, dict) else row),
                )
            canonical_date(row["observation_date"], "observation_date")
            canonical_utc_timestamp(row["available_at"], "available_at")
            canonical_utc_timestamp(row["ingested_at"], "ingested_at")
            for field in ("flow_usd", "aum_usd"):
                value = row[field]
                if value is None:
                    continue
                if not isinstance(value, str):
                    raise ScientificWorkerProtocolError(
                        "DECIMAL_MUST_BE_A_CANONICAL_STRING", f"{field}={value!r}"
                    )


def _validate_evidence_records(records: Sequence[Any]) -> None:
    for row in records:
        if not isinstance(row, dict):
            raise ScientificWorkerProtocolError("EVIDENCE_RECORD_IS_NOT_AN_OBJECT", "")
        if "record_kind" not in row or "record_sha256" not in row:
            raise ScientificWorkerProtocolError(
                "EVIDENCE_RECORD_IS_NOT_CANONICAL", repr(sorted(row))
            )


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

RESPONSE_FIELDS: tuple[str, ...] = (
    "response_schema_version",
    "status",
    "failure_reason",
    "worker_authority_version",
    "worker_authority_ticket",
    "worker_authority_sha256",
    "authority_context_origin",
    "calendar_authority_version",
    "calendar_authority_sha256",
    "trusted_persistence_authority_sha256",
    "interpreter_identity",
    "worker_entrypoint_module",
    "worker_entrypoint_sha256",
    "worker_protocol_sha256",
    "project_source_manifest_digest",
    "project_source_manifest_role",
    "third_party_authority_digest",
    "third_party_observed_content_manifest_digest",
    "third_party_installed_content_verification",
    "bytecode_cache_binding",
    "loaded_project_modules",
    "interpreter_flags",
    "sys_path_digest",
    "request_schema_version",
    "request_digest",
    "operation",
    "evidence_admission_mode",
    "decision_time",
    "result",
    "result_digest",
    "post_execution_source_verification",
    "one_request_one_process",
)

#: The response field names that must reproduce against the trusted controller
#: authority context.  A response that merely echoes the request proves nothing.
AUTHORITY_BOUND_RESPONSE_FIELDS: tuple[str, ...] = (
    "calendar_authority_sha256",
    "calendar_authority_version",
    "interpreter_identity",
    "project_source_manifest_digest",
    "project_source_manifest_role",
    "third_party_authority_digest",
    "trusted_persistence_authority_sha256",
    "worker_authority_sha256",
    "worker_authority_ticket",
    "worker_authority_version",
    "worker_entrypoint_module",
    "worker_entrypoint_sha256",
    "worker_protocol_sha256",
)


def build_response(**fields: Any) -> dict[str, Any]:
    unknown = sorted(set(fields) - set(RESPONSE_FIELDS))
    if unknown:
        raise ScientificWorkerProtocolError("UNKNOWN_RESPONSE_FIELD", repr(unknown))
    missing = sorted(set(RESPONSE_FIELDS) - set(fields))
    if missing:
        raise ScientificWorkerProtocolError("MISSING_RESPONSE_FIELD", repr(missing))
    return dict(sorted(fields.items()))


def validate_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        raise ScientificWorkerProtocolError(
            "RESPONSE_IS_NOT_A_JSON_OBJECT", type(payload).__name__
        )
    if sorted(payload) != sorted(RESPONSE_FIELDS):
        raise ScientificWorkerProtocolError(
            "RESPONSE_SHAPE_REFUSED",
            repr(sorted(set(payload) ^ set(RESPONSE_FIELDS))),
        )
    if payload["response_schema_version"] != RESPONSE_SCHEMA_VERSION:
        raise ScientificWorkerProtocolError(
            "RESPONSE_SCHEMA_VERSION_REFUSED", repr(payload["response_schema_version"])
        )
    if payload["status"] not in (SUCCESS, REFUSED):
        raise ScientificWorkerProtocolError(
            "RESPONSE_STATUS_REFUSED", repr(payload["status"])
        )
    return payload


def result_digest(result: Any) -> str:
    return digest_payload(result)


# ---------------------------------------------------------------------------
# Evidence record without memory addresses
# ---------------------------------------------------------------------------


def assert_address_free(payload: Any) -> None:
    """Scientific evidence may never carry a memory address."""

    raw = canonical_json_bytes(payload).decode("ascii")
    marker = "0x"
    index = raw.find(marker)
    while index != -1:
        tail = raw[index + 2 : index + 8]
        if len(tail) >= 6 and all(ch in "0123456789abcdefABCDEF" for ch in tail):
            raise ScientificWorkerProtocolError(
                "SCIENTIFIC_EVIDENCE_CONTAINS_A_MEMORY_ADDRESS", raw[index : index + 20]
            )
        index = raw.find(marker, index + 1)
    if " object at " in raw or "<built-in" in raw:
        raise ScientificWorkerProtocolError(
            "SCIENTIFIC_EVIDENCE_CONTAINS_AN_OBJECT_REPR", ""
        )
