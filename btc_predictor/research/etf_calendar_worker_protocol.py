"""Worker-safe canonical protocol for the isolated ETF-calendar scientific worker.

This module is the single shared authority for the ``POSTP1-001V2A-PAD4``
process-isolation boundary: the frozen proof-interpreter identity, the canonical
non-executable request/response serialization, the certified project-source
manifest verification rule, the loaded-module verification rule, the
lazy-result refusal rule and the one-request-one-process rule.

It is deliberately *worker safe*.  It imports no project module and it contains
none of the constructs the decision forbids inside authoritative scientific
worker source: no ``exec``, ``eval``, ``compile``, ``__import__``, ``importlib``,
``runpy``, ``marshal``, ``pickle`` or arbitrary source loading.  The
``ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1`` decision module imports this
module and mechanically binds its frozen identity material, so the worker and
the controller share exactly one definition and nothing is duplicated.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import types
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Mapping, Sequence


WORKER_AUTHORITY_VERSION = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
REQUEST_SCHEMA_VERSION = "ETF_CALENDAR_SCIENTIFIC_WORKER_REQUEST_V1"
RESPONSE_SCHEMA_VERSION = "ETF_CALENDAR_SCIENTIFIC_WORKER_RESPONSE_V1"
WORKER_ENTRYPOINT_MODULE = (
    "btc_predictor.research.etf_calendar_scientific_worker_entry"
)
WORKER_ENTRYPOINT_RELATIVE_PATH = (
    "btc_predictor/research/etf_calendar_scientific_worker_entry.py"
)
WORKER_PROTOCOL_RELATIVE_PATH = (
    "btc_predictor/research/etf_calendar_worker_protocol.py"
)
#: The two repository-owned modules that are *authoritative scientific worker
#: source*.  The closed worker-coding rule of section 10 is scoped to exactly
#: these, because everything else the worker imports is governed by the
#: certified project source manifest plus the preserved compiled root witness
#: and closed AST store grammar.
AUTHORITATIVE_WORKER_SOURCE: tuple[str, ...] = (
    WORKER_ENTRYPOINT_RELATIVE_PATH,
    WORKER_PROTOCOL_RELATIVE_PATH,
)

PROJECT_PACKAGE_ROOT = "btc_predictor"

#: Frozen proof interpreter.  ``ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1``
#: mechanically asserts that this equals the compiled-root-witness identity, so
#: the restatement here can never drift from the owning authority.
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

SUCCESS = "SUCCESS"
REFUSED = "REFUSED"

#: Bounded worker execution controls.  Exact operational values may be frozen
#: later; these are the reviewed defaults of the decision.
MAX_REQUEST_BYTES = 8 * 1024 * 1024
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 120

#: stdout carries exactly one canonical scientific protocol payload terminated
#: by a single newline; stderr is diagnostics only and is never scientific
#: evidence.
STDOUT_PROTOCOL = "EXACTLY_ONE_CANONICAL_JSON_PAYLOAD_PLUS_ONE_TRAILING_NEWLINE"
STDERR_PROTOCOL = "DIAGNOSTICS_ONLY_NEVER_SCIENTIFIC_EVIDENCE"

#: The frozen read-only scientific operations an isolated worker may evaluate.
#: None of them signs, persists, writes a database or performs network I/O.
FROZEN_WORKER_OPERATIONS: tuple[str, ...] = (
    "common_etf_session_status",
    "derive_etf_window_calendar",
    "scientific_etf_flow_window",
)

#: Only deterministic data crosses the boundary.  Acquisition envelopes signed
#: by the production collector key are the authoritative evidence form; the
#: prototype regressions of this decision replay already-verified canonical
#: records and are explicitly non-authoritative.
AUTHORITATIVE_EVIDENCE_ADMISSION_MODE = "PRODUCTION_SIGNED_ENVELOPE_REPLAY"
PROTOTYPE_EVIDENCE_ADMISSION_MODE = "NON_AUTHORITATIVE_CANONICAL_RECORD_REPLAY"
EVIDENCE_ADMISSION_MODES: tuple[str, ...] = (
    AUTHORITATIVE_EVIDENCE_ADMISSION_MODE,
    PROTOTYPE_EVIDENCE_ADMISSION_MODE,
)

#: Serialized executable Python object graphs are forbidden scientific IPC.
FORBIDDEN_SCIENTIFIC_IPC: tuple[str, ...] = ("pickle", "cloudpickle", "dill", "marshal")

#: The environment variable that would hand the worker a production signing
#: capability.  Its presence refuses before any scientific evaluation.
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
    serialized executable Python object graph can be the request.  A
    ``pickle`` module may still be resident in the worker because the
    certified third-party universe imports it; that is not scientific IPC.
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
    """Return the interpreter's bytecode magic without importing ``importlib``.

    ``importlib.util.MAGIC_NUMBER`` is the ordinary accessor, but ``importlib``
    is refused inside authoritative worker source.  The frozen bootstrap module
    is already resident in ``sys.modules`` before any user code runs, so the
    constant is read from there.
    """

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
# Certified project source manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class ProjectSourceEntry:
    """One certified project-owned source file permitted inside the worker."""

    module: str
    path: str
    sha256: str

    def as_material(self) -> dict[str, str]:
        return {"module": self.module, "path": self.path, "sha256": self.sha256}


def project_source_entries(
    manifest: Sequence[Mapping[str, Any]],
) -> tuple[ProjectSourceEntry, ...]:
    entries: list[ProjectSourceEntry] = []
    seen: set[str] = set()
    for row in manifest:
        if set(row) != {"module", "path", "sha256"}:
            raise ScientificWorkerProtocolError(
                "PROJECT_SOURCE_MANIFEST_ROW_SHAPE_REFUSED", repr(sorted(row))
            )
        module, path, sha = row["module"], row["path"], row["sha256"]
        if not isinstance(module, str) or not module.startswith(PROJECT_PACKAGE_ROOT):
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


def module_relative_path(module: str) -> str:
    """The canonical source path of a dotted project module file."""

    return "/".join(module.split(".")) + ".py"


def package_relative_path(module: str) -> str:
    return "/".join(module.split(".")) + "/__init__.py"


def manifest_digest(entries: Sequence[ProjectSourceEntry]) -> str:
    return digest_payload([entry.as_material() for entry in entries])


def verify_project_source_manifest(
    project_root: Path, entries: Sequence[ProjectSourceEntry]
) -> dict[str, str]:
    """Every certified source file must exist at its path with its exact SHA."""

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
    """Loaded project modules must be certified, at their certified origin.

    ``phase`` is ``PRE_EXECUTION`` or ``POST_EXECUTION``; the post-execution
    sweep is defence in depth, not an attempt to attest every runtime object.
    """

    certified = {entry.module for entry in entries}
    loaded = sorted(
        name
        for name in list(sys.modules)
        if name == PROJECT_PACKAGE_ROOT or name.startswith(PROJECT_PACKAGE_ROOT + ".")
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
# Third-party dependency manifest
# ---------------------------------------------------------------------------


@dataclass(frozen=True, order=True)
class ThirdPartyEntry:
    """Deterministic identity for one non-stdlib distribution in the worker."""

    distribution: str
    version: str
    location: str
    record_path: str
    record_sha256: str
    root_modules: tuple[str, ...]

    def as_material(self) -> dict[str, Any]:
        return {
            "distribution": self.distribution,
            "version": self.version,
            "location": self.location,
            "record_path": self.record_path,
            "record_sha256": self.record_sha256,
            "root_modules": list(self.root_modules),
        }


def third_party_entries(
    manifest: Sequence[Mapping[str, Any]],
) -> tuple[ThirdPartyEntry, ...]:
    fields = {
        "distribution",
        "version",
        "location",
        "record_path",
        "record_sha256",
        "root_modules",
    }
    entries: list[ThirdPartyEntry] = []
    for row in manifest:
        if set(row) != fields:
            raise ScientificWorkerProtocolError(
                "THIRD_PARTY_MANIFEST_ROW_SHAPE_REFUSED", repr(sorted(row))
            )
        roots = row["root_modules"]
        if not isinstance(roots, list) or not all(isinstance(m, str) for m in roots):
            raise ScientificWorkerProtocolError(
                "THIRD_PARTY_MANIFEST_ROOT_MODULES_REFUSED", repr(roots)
            )
        if not isinstance(row["record_sha256"], str) or len(row["record_sha256"]) != 64:
            raise ScientificWorkerProtocolError(
                "THIRD_PARTY_MANIFEST_DIGEST_REFUSED", repr(row["record_sha256"])
            )
        entries.append(
            ThirdPartyEntry(
                distribution=str(row["distribution"]),
                version=str(row["version"]),
                location=str(row["location"]),
                record_path=str(row["record_path"]),
                record_sha256=str(row["record_sha256"]),
                root_modules=tuple(sorted(roots)),
            )
        )
    ordered = tuple(sorted(entries))
    if ordered != tuple(entries):
        raise ScientificWorkerProtocolError(
            "THIRD_PARTY_MANIFEST_IS_NOT_CANONICALLY_ORDERED", ""
        )
    return ordered


def third_party_manifest_digest(entries: Sequence[ThirdPartyEntry]) -> str:
    return digest_payload([entry.as_material() for entry in entries])


def verify_third_party_manifest(entries: Sequence[ThirdPartyEntry]) -> None:
    """Bind each non-stdlib distribution to an exact installed file identity.

    The installed ``RECORD`` of a distribution is itself a hash manifest of
    every file the distribution owns, so binding its digest is a bounded and
    deterministic identity for the whole distribution.  Arbitrary
    ``site-packages`` state is never scientific authority.
    """

    for entry in entries:
        record = Path(entry.record_path)
        if not record.is_file():
            raise ScientificWorkerProtocolError(
                "NON_CERTIFIED_DEPENDENCY_ENVIRONMENT",
                f"{entry.distribution}: {entry.record_path} is missing",
            )
        observed = file_sha256(record)
        if observed != entry.record_sha256:
            raise ScientificWorkerProtocolError(
                "NON_CERTIFIED_DEPENDENCY_ENVIRONMENT",
                f"{entry.distribution}: expected {entry.record_sha256} observed {observed}",
            )
        location = Path(entry.location).resolve()
        for root in entry.root_modules:
            module = sys.modules.get(root)
            if module is None:
                continue
            origin = getattr(getattr(module, "__spec__", None), "origin", None)
            if not isinstance(origin, str):
                raise ScientificWorkerProtocolError(
                    "NON_CERTIFIED_DEPENDENCY_ENVIRONMENT",
                    f"{root} declares no origin",
                )
            if not str(Path(origin).resolve()).startswith(str(location)):
                raise ScientificWorkerProtocolError(
                    "NON_CERTIFIED_DEPENDENCY_ENVIRONMENT",
                    f"{root} loaded from {origin} outside {entry.location}",
                )


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
    "worker_authority_sha256": str,
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
    "required_project_modules": list,
    "third_party_manifest": list,
    "third_party_manifest_digest": str,
    "decision_time": str,
    "operation": str,
    "evidence_admission_mode": str,
    "evidence_records": list,
    "operation_inputs": dict,
}

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
    def third_party(self) -> tuple[ThirdPartyEntry, ...]:
        return third_party_entries(self.payload["third_party_manifest"])


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
        "third_party_manifest_digest",
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
    third_party = third_party_entries(payload["third_party_manifest"])
    if third_party_manifest_digest(third_party) != payload["third_party_manifest_digest"]:
        raise ScientificWorkerProtocolError("THIRD_PARTY_MANIFEST_DIGEST_MISMATCH", "")
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
    if WORKER_ENTRYPOINT_MODULE not in certified:
        raise ScientificWorkerProtocolError(
            "WORKER_ENTRYPOINT_IS_NOT_IN_THE_CERTIFIED_MANIFEST", ""
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
                    "ETF_FLOW_ROW_SHAPE_REFUSED", repr(sorted(row) if isinstance(row, dict) else row)
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
    "worker_authority_sha256",
    "calendar_authority_sha256",
    "trusted_persistence_authority_sha256",
    "interpreter_identity",
    "worker_entrypoint_sha256",
    "worker_protocol_sha256",
    "project_source_manifest_digest",
    "third_party_manifest_digest",
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
