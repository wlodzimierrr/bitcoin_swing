"""Corrected bootstrap-bound scientific worker protocol for the ETF calendar.

``POSTP1-002V2A-PAD4-R1`` independently reproduced the exact ``PAD4-R1``
candidate ``3415765f...fde37ebc``, confirmed fresh-exec isolation, the
bytecode-cache repair, the trusted controller authority context and the
third-party semantic/content repair, and then failed the candidate with::

    FAIL — WORKER BOOTSTRAP SOURCE NOT BOUND BEFORE EXECUTION

The blocking invariant was an *authority-ordering* defect, not an isolation
defect: the frozen expected source manifest was compared against disk **inside
the worker, by the worker's own protocol module**, so every module that had to
execute in order to reach that comparison was outside it.  Stable pre-launch
drift of ``etf_calendar_worker/entry_r1.py`` and of
``etf_calendar_worker/protocol_r1.py`` both executed their markers and both had
a fabricated scientific result admitted by the controller.

``POSTP1-001V2A-PAD4-R2`` is a bounded correction of exactly that ordering.  It
adds no new proof-architecture family, it reopens nothing the R1 review
reproduced as valid, and it does not reopen same-process runtime-object
attestation.  The corrected rule is::

    NO PROJECT-OWNED WORKER BOOTSTRAP SOURCE MAY EXECUTE UNTIL ALREADY-TRUSTED
    CONTROLLER CODE HAS ESTABLISHED ITS EXPECTED PATH AND SOURCE SHA AGAINST
    THE TRUSTED ScientificWorkerAuthorityContext.

This module is therefore deliberately *not* the primary authority for its own
identity.  Everything it verifies about the bootstrap source set is defence in
depth that runs long after the already-trusted controller has hashed the same
bytes and refused to spawn anything on a mismatch::

    bootstrap_self_verification_is_authority       = False
    entrypoint_self_verification_is_authority      = False
    protocol_self_verification_is_authority        = False
    package_initializer_self_verification_is_authority = False

The reviewed ``PAD4-R1`` protocol implementation is reused verbatim from
``etf_calendar_worker.protocol_r1`` rather than restated, so none of the
independently validated verification logic is forked.  That makes
``protocol_r1`` itself a member of the R2 bootstrap source set: it executes
before the scientific verifier is trustworthy, so the trusted controller
pre-verifies it too.  Like ``protocol_r1`` this module imports the standard
library only, and it must stay importable with no third-party side effect at
all, because the reviewed third-party attestation has to run before any
dependency code executes.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping, Sequence

from etf_calendar_worker import protocol_r1 as base


ScientificWorkerProtocolError = base.ScientificWorkerProtocolError

WORKER_AUTHORITY_VERSION = base.WORKER_AUTHORITY_VERSION
WORKER_AUTHORITY_TICKET = "POSTP1-001V2A-PAD4-R2"
REQUEST_SCHEMA_VERSION = "ETF_CALENDAR_SCIENTIFIC_WORKER_REQUEST_V1_R2"
RESPONSE_SCHEMA_VERSION = "ETF_CALENDAR_SCIENTIFIC_WORKER_RESPONSE_V1_R2"

WORKER_PACKAGE_MODULE = "etf_calendar_worker"
WORKER_PACKAGE_RELATIVE_PATH = base.WORKER_PACKAGE_RELATIVE_PATH
WORKER_BASE_PROTOCOL_MODULE = base.WORKER_PROTOCOL_MODULE
WORKER_BASE_PROTOCOL_RELATIVE_PATH = base.WORKER_PROTOCOL_RELATIVE_PATH
WORKER_PROTOCOL_MODULE = "etf_calendar_worker.protocol_r2"
WORKER_PROTOCOL_RELATIVE_PATH = "etf_calendar_worker/protocol_r2.py"
WORKER_ENTRYPOINT_MODULE = "etf_calendar_worker.entry_r2"
WORKER_ENTRYPOINT_RELATIVE_PATH = "etf_calendar_worker/entry_r2.py"

# ---------------------------------------------------------------------------
# The complete pre-trust bootstrap source set
# ---------------------------------------------------------------------------

#: Every project-owned source file that can execute before the scientific
#: verifier is trustworthy, in the order CPython executes it.
#:
#: ``etf_calendar_worker/entry_r2.py`` is exec'd by path as ``__main__``.  Its
#: first project import is ``etf_calendar_worker.protocol_r2``, which executes
#: the package initializer ``etf_calendar_worker/__init__.py`` first and then
#: imports ``etf_calendar_worker.protocol_r1``.  Nothing else project-owned can
#: run before the certified-source manifest verification, because no bootstrap
#: module declares a module-level import outside this set and every deferred
#: project import in this set is a member of the certified source manifest that
#: the reviewed ``PAD4-R1`` frozen-source authority already covers.
#:
#: The set is *mechanically derived* by
#: ``etf_calendar_isolated_scientific_worker_r2.derive_bootstrap_source_set``
#: and this ordered restatement is checked against that derivation.  It is
#: deliberately not limited to the two filenames the review named in its P0
#: findings.
WORKER_BOOTSTRAP_SOURCE_SET: tuple[tuple[str, str], ...] = (
    (WORKER_PACKAGE_MODULE, WORKER_PACKAGE_RELATIVE_PATH),
    (WORKER_BASE_PROTOCOL_MODULE, WORKER_BASE_PROTOCOL_RELATIVE_PATH),
    (WORKER_PROTOCOL_MODULE, WORKER_PROTOCOL_RELATIVE_PATH),
    (WORKER_ENTRYPOINT_MODULE, WORKER_ENTRYPOINT_RELATIVE_PATH),
)

#: The same set as canonical relative paths, sorted.  Order is execution order
#: above and canonical order here; both are frozen.
WORKER_BOOTSTRAP_RELATIVE_PATHS: tuple[str, ...] = tuple(
    sorted(path for _, path in WORKER_BOOTSTRAP_SOURCE_SET)
)
WORKER_BOOTSTRAP_MODULES: tuple[str, ...] = tuple(
    sorted(module for module, _ in WORKER_BOOTSTRAP_SOURCE_SET)
)

#: The closed worker-coding rule is scoped to exactly the bootstrap set: these
#: are the files that run before anything can check them.
AUTHORITATIVE_WORKER_SOURCE: tuple[str, ...] = WORKER_BOOTSTRAP_RELATIVE_PATHS

BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE = (
    "NO_PROJECT_OWNED_WORKER_BOOTSTRAP_SOURCE_MAY_EXECUTE_UNTIL_ALREADY_TRUSTED_"
    "CONTROLLER_CODE_HAS_ESTABLISHED_ITS_EXPECTED_PATH_AND_SOURCE_SHA_AGAINST_"
    "THE_TRUSTED_SCIENTIFIC_WORKER_AUTHORITY_CONTEXT"
)

#: The worker may restate the bootstrap binding, but it can never establish it.
BOOTSTRAP_SELF_VERIFICATION_IS_AUTHORITY = False
ENTRYPOINT_SELF_VERIFICATION_IS_AUTHORITY = False
PROTOCOL_SELF_VERIFICATION_IS_AUTHORITY = False
PACKAGE_INITIALIZER_SELF_VERIFICATION_IS_AUTHORITY = False
BOOTSTRAP_SELF_VERIFICATION_ROLE = (
    "DEFENCE_IN_DEPTH_NEVER_PRIMARY_BOOTSTRAP_AUTHORITY"
)

# ---------------------------------------------------------------------------
# Reused reviewed PAD4-R1 protocol surface
# ---------------------------------------------------------------------------

ACCEPTED_RECORD_HASH_ALGORITHMS = base.ACCEPTED_RECORD_HASH_ALGORITHMS
AUTHORITY_CONTEXT_ORIGINS = base.AUTHORITY_CONTEXT_ORIGINS
BYTECODE_CACHE_NAMESPACE_MECHANISM = base.BYTECODE_CACHE_NAMESPACE_MECHANISM
BYTECODE_CACHE_NAMESPACE_RULE = base.BYTECODE_CACHE_NAMESPACE_RULE
CERTIFIED_PACKAGE_ROOTS = base.CERTIFIED_PACKAGE_ROOTS
DATA_QUALITY_FAIL = base.DATA_QUALITY_FAIL
DEFAULT_TIMEOUT_SECONDS = base.DEFAULT_TIMEOUT_SECONDS
EVIDENCE_ADMISSION_MODES = base.EVIDENCE_ADMISSION_MODES
FORBIDDEN_SCIENTIFIC_IPC = base.FORBIDDEN_SCIENTIFIC_IPC
FROZEN_WORKER_OPERATIONS = base.FROZEN_WORKER_OPERATIONS
MAX_REQUEST_BYTES = base.MAX_REQUEST_BYTES
MAX_RESPONSE_BYTES = base.MAX_RESPONSE_BYTES
NON_CERTIFIED_DEPENDENCY_ENVIRONMENT = base.NON_CERTIFIED_DEPENDENCY_ENVIRONMENT
NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER = base.NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER
PRIVATE_KEY_FILE_ENV_VAR = base.PRIVATE_KEY_FILE_ENV_VAR
PROJECT_SOURCE_MANIFEST_ROLES = base.PROJECT_SOURCE_MANIFEST_ROLES
PROOF_INTERPRETER_IDENTITY = base.PROOF_INTERPRETER_IDENTITY
PROTOTYPE_EVIDENCE_ADMISSION_MODE = base.PROTOTYPE_EVIDENCE_ADMISSION_MODE
AUTHORITATIVE_EVIDENCE_ADMISSION_MODE = base.AUTHORITATIVE_EVIDENCE_ADMISSION_MODE
REFUSE_SCIENTIFIC_AUTHORITY = base.REFUSE_SCIENTIFIC_AUTHORITY
REQUIRED_INTERPRETER_FLAGS = base.REQUIRED_INTERPRETER_FLAGS
RESULT_NOT_ADMITTED = base.RESULT_NOT_ADMITTED
SECOND_REQUEST_REFUSAL = base.SECOND_REQUEST_REFUSAL
STDERR_PROTOCOL = base.STDERR_PROTOCOL
STDOUT_PROTOCOL = base.STDOUT_PROTOCOL
SUCCESS = base.SUCCESS
REFUSED = base.REFUSED

FrozenDistributionAuthority = base.FrozenDistributionAuthority
InstalledDistributionObservation = base.InstalledDistributionObservation
ProjectSourceEntry = base.ProjectSourceEntry

assert_address_free = base.assert_address_free
assert_canonical_request_bytes = base.assert_canonical_request_bytes
canonical_json_bytes = base.canonical_json_bytes
canonical_utc_timestamp = base.canonical_utc_timestamp
certified_root = base.certified_root
claim_single_request = base.claim_single_request
current_interpreter_identity = base.current_interpreter_identity
digest_bytes = base.digest_bytes
digest_payload = base.digest_payload
file_sha256 = base.file_sha256
frozen_distribution_authorities = base.frozen_distribution_authorities
installed_distribution_observations = base.installed_distribution_observations
manifest_digest = base.manifest_digest
module_relative_path = base.module_relative_path
package_relative_path = base.package_relative_path
parse_canonical_json = base.parse_canonical_json
project_source_entries = base.project_source_entries
refuse_lazy_result = base.refuse_lazy_result
reset_single_request_claim_for_tests = base.reset_single_request_claim_for_tests
result_digest = base.result_digest
third_party_authority_digest = base.third_party_authority_digest
third_party_environment_digest = base.third_party_environment_digest
verify_bytecode_cache_namespace = base.verify_bytecode_cache_namespace
verify_cache_namespace_is_not_shared_with_the_project = (
    base.verify_cache_namespace_is_not_shared_with_the_project
)
verify_controlled_startup = base.verify_controlled_startup
verify_installed_distribution_content = base.verify_installed_distribution_content
verify_loaded_dependency_origins = base.verify_loaded_dependency_origins
verify_loaded_module_bytecode_binding = base.verify_loaded_module_bytecode_binding
verify_loaded_project_modules = base.verify_loaded_project_modules
verify_project_source_manifest = base.verify_project_source_manifest
verify_proof_interpreter_identity = base.verify_proof_interpreter_identity
verify_third_party_authority = base.verify_third_party_authority


# ---------------------------------------------------------------------------
# Bootstrap manifest material
# ---------------------------------------------------------------------------


def bootstrap_source_entries(
    manifest: Sequence[Mapping[str, Any]],
) -> tuple[ProjectSourceEntry, ...]:
    """Validate a bootstrap manifest and refuse anything but the exact set.

    The bootstrap manifest is not a free-form source list.  It must describe
    the complete frozen bootstrap source set, no more and no less, so that a
    caller cannot silently shrink the set that gets pre-verified.
    """

    entries = project_source_entries(manifest)
    paths = tuple(entry.path for entry in entries)
    if paths != WORKER_BOOTSTRAP_RELATIVE_PATHS:
        raise ScientificWorkerProtocolError(
            "WORKER_BOOTSTRAP_SOURCE_SET_IS_NOT_THE_FROZEN_COMPLETE_SET",
            f"{list(paths)!r} != {list(WORKER_BOOTSTRAP_RELATIVE_PATHS)!r}",
        )
    modules = tuple(sorted(entry.module for entry in entries))
    if modules != WORKER_BOOTSTRAP_MODULES:
        raise ScientificWorkerProtocolError(
            "WORKER_BOOTSTRAP_MODULE_SET_IS_NOT_THE_FROZEN_COMPLETE_SET",
            f"{list(modules)!r} != {list(WORKER_BOOTSTRAP_MODULES)!r}",
        )
    return entries


def bootstrap_manifest_digest(entries: Sequence[ProjectSourceEntry]) -> str:
    return manifest_digest(entries)


def verify_bootstrap_source_set(
    project_root: Path, entries: Sequence[ProjectSourceEntry]
) -> dict[str, str]:
    """Defence in depth only — restate the bootstrap binding inside the worker.

    This is deliberately **not** authority.  By the time any statement in this
    function can run, every file it inspects has already executed.  The primary
    binding is the already-trusted controller's pre-execution verification,
    which hashes the same bytes against the same trusted authority context and
    never spawns a process on a mismatch.
    """

    resolved: dict[str, str] = {}
    for entry in entries:
        target = Path(project_root) / entry.path
        if not target.is_file():
            raise ScientificWorkerProtocolError(
                "WORKER_BOOTSTRAP_SOURCE_FILE_MISSING",
                f"{entry.module} -> {entry.path}",
            )
        observed = file_sha256(target)
        if observed != entry.sha256:
            raise ScientificWorkerProtocolError(
                "WORKER_BOOTSTRAP_SOURCE_SHA_MISMATCH",
                f"{entry.module}: expected {entry.sha256} observed {observed}",
            )
        resolved[entry.module] = str(target.resolve())
    return resolved


# ---------------------------------------------------------------------------
# Request schema
# ---------------------------------------------------------------------------

#: ``PAD4-R1`` carried two ad-hoc bootstrap digests, ``worker_entrypoint_sha256``
#: and ``worker_protocol_sha256``.  The review found both inadequate: they omit
#: the package initializer entirely and they are verified by code that has
#: already run.  They are replaced by the complete bootstrap manifest, which the
#: already-trusted controller verifies before the worker exists.
_REPLACED_REQUEST_FIELDS: tuple[str, ...] = (
    "worker_entrypoint_sha256",
    "worker_protocol_sha256",
)

REQUEST_FIELDS: Mapping[str, type | tuple[type, ...]] = {
    **{
        name: kind
        for name, kind in base.REQUEST_FIELDS.items()
        if name not in _REPLACED_REQUEST_FIELDS
    },
    "worker_bootstrap_manifest": list,
    "worker_bootstrap_manifest_digest": str,
}

AUTHORITY_BOUND_REQUEST_FIELDS: tuple[str, ...] = tuple(
    sorted(
        {
            *(
                name
                for name in base.AUTHORITY_BOUND_REQUEST_FIELDS
                if name not in _REPLACED_REQUEST_FIELDS
            ),
            "worker_bootstrap_manifest_digest",
        }
    )
)

_REQUEST_DIGEST_FIELDS: tuple[str, ...] = (
    "calendar_authority_sha256",
    "project_source_manifest_digest",
    "third_party_authority_digest",
    "trusted_persistence_authority_sha256",
    "worker_authority_sha256",
    "worker_bootstrap_manifest_digest",
)


class ScientificWorkerRequest(base.ScientificWorkerRequest):
    """A validated canonical ``R2`` scientific request."""

    @property
    def bootstrap_entries(self) -> tuple[ProjectSourceEntry, ...]:
        return bootstrap_source_entries(self.payload["worker_bootstrap_manifest"])


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
    for name, kind in REQUEST_FIELDS.items():
        if not isinstance(payload[name], kind):
            raise ScientificWorkerProtocolError(
                "REQUEST_FIELD_TYPE_REFUSED",
                f"{name} is {type(payload[name]).__name__}",
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
    for name in _REQUEST_DIGEST_FIELDS:
        value = payload[name]
        if len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value):
            raise ScientificWorkerProtocolError(
                "REQUEST_DIGEST_FIELD_REFUSED", f"{name}={value!r}"
            )
    canonical_utc_timestamp(payload["decision_time"], "decision_time")
    verify_proof_interpreter_identity(payload["interpreter_identity"])
    bootstrap = bootstrap_source_entries(payload["worker_bootstrap_manifest"])
    if bootstrap_manifest_digest(bootstrap) != payload[
        "worker_bootstrap_manifest_digest"
    ]:
        raise ScientificWorkerProtocolError(
            "WORKER_BOOTSTRAP_MANIFEST_DIGEST_MISMATCH", ""
        )
    entries = project_source_entries(payload["project_source_manifest"])
    if manifest_digest(entries) != payload["project_source_manifest_digest"]:
        raise ScientificWorkerProtocolError(
            "PROJECT_SOURCE_MANIFEST_DIGEST_MISMATCH", ""
        )
    certified = {entry.module: entry for entry in entries}
    for entry in bootstrap:
        member = certified.get(entry.module)
        if member is None or member != entry:
            raise ScientificWorkerProtocolError(
                "WORKER_BOOTSTRAP_SOURCE_DIVERGES_FROM_THE_CERTIFIED_MANIFEST",
                entry.module,
            )
    authorities = frozen_distribution_authorities(payload["third_party_authority"])
    if third_party_authority_digest(authorities) != payload[
        "third_party_authority_digest"
    ]:
        raise ScientificWorkerProtocolError("THIRD_PARTY_AUTHORITY_DIGEST_MISMATCH", "")
    installed_distribution_observations(payload["third_party_environment"])
    required = payload["required_project_modules"]
    if not all(isinstance(name, str) for name in required):
        raise ScientificWorkerProtocolError("REQUIRED_PROJECT_MODULES_REFUSED", "")
    if list(required) != sorted(required) or len(set(required)) != len(required):
        raise ScientificWorkerProtocolError(
            "REQUIRED_PROJECT_MODULES_NOT_CANONICALLY_ORDERED", ""
        )
    outside = sorted(set(required) - set(certified))
    if outside:
        raise ScientificWorkerProtocolError(
            "REQUIRED_PROJECT_MODULE_OUTSIDE_MANIFEST", repr(outside)
        )
    base._validate_operation_inputs(payload["operation"], payload["operation_inputs"])
    base._validate_evidence_records(payload["evidence_records"])
    if not all(isinstance(entry, str) for entry in payload["sys_path"]):
        raise ScientificWorkerProtocolError("SYS_PATH_ENTRY_REFUSED", "")
    return ScientificWorkerRequest(payload)


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

RESPONSE_FIELDS: tuple[str, ...] = tuple(
    [
        *(
            name
            for name in base.RESPONSE_FIELDS
            if name not in _REPLACED_REQUEST_FIELDS
        ),
        "worker_bootstrap_manifest_digest",
        "bootstrap_defence_in_depth_verification",
    ]
)

AUTHORITY_BOUND_RESPONSE_FIELDS: tuple[str, ...] = tuple(
    sorted(
        {
            *(
                name
                for name in base.AUTHORITY_BOUND_RESPONSE_FIELDS
                if name not in _REPLACED_REQUEST_FIELDS
            ),
            "worker_bootstrap_manifest_digest",
        }
    )
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
