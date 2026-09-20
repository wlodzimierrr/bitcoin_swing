"""Corrected one-shot isolated ETF-calendar scientific worker entrypoint.

``POSTP1-001V2A-PAD4-R1`` repairs the four authority-anchoring defects that
failed ``POSTP1-002V2A-PAD4`` and preserves the fresh-exec isolation boundary
the review reproduced and found sound.  This file is the *only* corrected
scientific worker entrypoint.  It is launched as a fresh exec'd CPython 3.12.14
process by the controller, it serves exactly one canonical scientific request,
it emits exactly one canonical response on stdout and it exits.  No Python
object, module, class, function or pickle crosses the process boundary; only
deterministic canonical data does.

The proof order this file executes is the frozen order of the decision:

``8``   verify interpreter, startup and bytecode-cache-namespace controls;
``9``   verify the canonical request schema;
``10``  verify source files against the *trusted expected* manifest;
``11``  verify the exact reviewed third-party semantic/artifact identities;
``12``  verify installed files against ``RECORD`` before dependency execution;
``13``  establish the controlled project import path;
``14``  load certified scientific source;
``15``  verify loaded module origins and bytecode-cache binding;
``16``  execute exactly one frozen scientific operation;
``17``  refuse any lazy output;
``18``  post-verify the source and module boundary;
``19``  emit exactly one canonical response;
``20``  exit.

Steps 8 to 12 run **before** any ``btc_predictor`` import, because importing
that package executes ``numpy``, ``scipy``, ``sqlalchemy`` and ``alembic``
through its re-export graph.  That is why the corrected protocol lives in
``etf_calendar_worker`` rather than under ``btc_predictor``: the third-party
attestation would otherwise run after the code it is supposed to attest.

The bytecode-cache-namespace check is additionally duplicated inline below,
using the standard library only, because it has to pass before even the
certified protocol module is imported.  Otherwise a forged
``etf_calendar_worker/__pycache__/protocol_r1.cpython-312.pyc`` would be the
thing that decides whether the cache namespace is trustworthy.

Because ``sys.path`` is parent-controlled and is only established inside
``main``, this file performs every other import inside a function.  Those are
ordinary static import declarations: the certified project source manifest is
derived from them mechanically, and the closed worker-coding rule forbids
``exec``, ``eval``, ``compile``, ``__import__``, ``importlib``, ``runpy``,
``marshal`` and ``pickle`` anywhere in authoritative worker source.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXIT_SUCCESS = 0
EXIT_REFUSED = 3
EXIT_PROTOCOL_FAILURE = 4
EXIT_WRONG_INTERPRETER = 5
EXIT_UNCONTROLLED_BYTECODE_CACHE = 6

REFUSE_SCIENTIFIC_AUTHORITY = "REFUSE_SCIENTIFIC_AUTHORITY"


def live_interpreter_identity() -> dict[str, Any]:
    """Read the live interpreter identity using only the standard library.

    This runs before any certified import so that a wrong interpreter refuses
    before the certified source universe is executed at all.  It holds no
    frozen constant of its own: the expected identity is request material the
    controller binds from the trusted authority context.
    """

    bootstrap = sys.modules.get("_frozen_importlib_external")
    magic = getattr(bootstrap, "MAGIC_NUMBER", b"")
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
        "magic_number_hex": bytes(magic).hex(),
    }


def bytecode_cache_namespace_is_controlled(declared_prefix: str) -> bool:
    """Pre-import restatement of the frozen fresh-cache-namespace rule.

    ``-B`` suppresses bytecode *writes* only.  Nothing suppresses or validates
    bytecode *reads*, so this must hold before the first certified import:
    ``sys.pycache_prefix`` is exactly the controller-declared operational cache
    prefix, ``sys.dont_write_bytecode`` is ``True``, and the namespace exists
    and is empty.  ``etf_calendar_worker/protocol_r1.py`` re-verifies the same
    property as the owning authority once it is safe to import it.

    A worker entrypoint is executed as ``__main__`` from its source path, which
    CPython never serves from a bytecode cache, so this file's own executed
    bytecode is always compiled from its certified bytes.
    """

    if not declared_prefix:
        return False
    observed = sys.pycache_prefix
    if not isinstance(observed, str):
        return False
    if Path(observed).resolve() != Path(declared_prefix).resolve():
        return False
    if sys.dont_write_bytecode is not True:
        return False
    namespace = Path(declared_prefix).resolve()
    if not namespace.is_dir():
        return False
    return not any(namespace.iterdir())


def _load_protocol() -> Any:
    from etf_calendar_worker import protocol_r1 as protocol

    return protocol


def _load_calendar() -> Any:
    from btc_predictor.research import etf_publication_calendar as calendar

    return calendar


def _load_frozen_operations() -> tuple[Any, Any]:
    """The reviewed scientific encoders and the frozen operation dispatch.

    ``POSTP1-002V2A-PAD4`` found the isolation boundary and the frozen
    read-only operation registry sound; only authority anchoring failed.  The
    reviewed encoders and dispatch are therefore reused from their owning
    modules rather than restated here, and both are ordinary certified members
    of this architecture's frozen source manifest, verified by exact SHA-256
    before either is allowed to execute.  The failed ``PAD4`` decision
    artifact and its hash are never certified and are never used.
    """

    from btc_predictor.research import etf_calendar_scientific_worker_entry as frozen
    from btc_predictor.research import etf_calendar_worker_protocol as frozen_protocol

    return frozen, frozen_protocol


# ---------------------------------------------------------------------------
# One-shot worker
# ---------------------------------------------------------------------------


def serve_one_request(
    raw_request: bytes, entry_path: Path, declared_pycache_prefix: str
) -> dict[str, Any]:
    """Serve exactly one scientific request and return the canonical response."""

    protocol = _load_protocol()
    protocol.claim_single_request()

    # Step 8 — interpreter, startup and bytecode-cache-namespace controls.
    cache = protocol.verify_bytecode_cache_namespace(declared_pycache_prefix)
    protocol.verify_proof_interpreter_identity()

    # Step 9 — the canonical request schema.
    if len(raw_request) > protocol.MAX_REQUEST_BYTES:
        raise protocol.ScientificWorkerProtocolError(
            "REQUEST_EXCEEDS_THE_FROZEN_INPUT_SIZE_LIMIT", str(len(raw_request))
        )
    request = protocol.validate_request(
        protocol.assert_canonical_request_bytes(raw_request)
    )
    payload = request.payload
    request_digest = protocol.digest_bytes(raw_request)
    startup = protocol.verify_controlled_startup(payload["sys_path"])
    project_root = request.project_root
    protocol.verify_cache_namespace_is_not_shared_with_the_project(
        declared_pycache_prefix, project_root
    )

    expected_entry = (
        project_root / protocol.WORKER_ENTRYPOINT_RELATIVE_PATH
    ).resolve()
    if entry_path.resolve() != expected_entry:
        raise protocol.ScientificWorkerProtocolError(
            "WORKER_ENTRYPOINT_IS_NOT_THE_CERTIFIED_PATH",
            f"{entry_path} != {expected_entry}",
        )
    observed_entry_sha = protocol.file_sha256(expected_entry)
    if observed_entry_sha != payload["worker_entrypoint_sha256"]:
        raise protocol.ScientificWorkerProtocolError(
            "WORKER_ENTRYPOINT_SOURCE_MISMATCH", observed_entry_sha
        )
    observed_protocol_sha = protocol.file_sha256(
        (project_root / protocol.WORKER_PROTOCOL_RELATIVE_PATH).resolve()
    )
    if observed_protocol_sha != payload["worker_protocol_sha256"]:
        raise protocol.ScientificWorkerProtocolError(
            "WORKER_PROTOCOL_SOURCE_MISMATCH", observed_protocol_sha
        )

    # Step 10 — certified source against the trusted expected manifest.
    entries = request.source_entries
    resolved = protocol.verify_project_source_manifest(project_root, entries)

    # Steps 11 and 12 — reviewed third-party semantics, then installed bytes,
    # before any dependency code can execute.
    third_party = protocol.verify_third_party_authority(
        request.third_party_authority,
        request.third_party_environment,
        bytecode_namespace_enforced=True,
    )

    # Steps 13 and 14 — the controlled project import path, then certified
    # scientific source.
    calendar = _load_calendar()
    frozen_operations, frozen_protocol = _load_frozen_operations()
    if dict(frozen_protocol.PROOF_INTERPRETER_IDENTITY) != dict(
        protocol.PROOF_INTERPRETER_IDENTITY
    ):
        raise protocol.ScientificWorkerProtocolError(
            "REUSED_FROZEN_OPERATION_MODULE_INTERPRETER_IDENTITY_DIVERGES", ""
        )

    # Step 15 — loaded module origins and executed-bytecode binding.
    protocol.verify_loaded_project_modules(
        entries, resolved, payload["required_project_modules"], "PRE_EXECUTION"
    )
    protocol.verify_loaded_module_bytecode_binding(
        declared_pycache_prefix, protocol.CERTIFIED_PACKAGE_ROOTS, "PRE_EXECUTION"
    )
    dependency_roots = tuple(
        sorted(
            {
                root
                for authority in request.third_party_authority
                for root in authority.root_modules
            }
        )
    )
    protocol.verify_loaded_module_bytecode_binding(
        declared_pycache_prefix, dependency_roots, "PRE_EXECUTION_DEPENDENCIES"
    )
    protocol.verify_loaded_dependency_origins(
        request.third_party_authority, request.third_party_environment
    )
    if calendar.FROZEN_AUTHORITY_DEFINITION_SHA256 != payload[
        "calendar_authority_sha256"
    ]:
        raise protocol.ScientificWorkerProtocolError(
            "CALENDAR_AUTHORITY_IDENTITY_MISMATCH",
            calendar.FROZEN_AUTHORITY_DEFINITION_SHA256,
        )
    if calendar.AUTHORITY_VERSION != payload["calendar_authority_version"]:
        raise protocol.ScientificWorkerProtocolError(
            "CALENDAR_AUTHORITY_VERSION_MISMATCH", calendar.AUTHORITY_VERSION
        )
    if calendar.TRUSTED_PERSISTENCE_AUTHORITY_SHA256 != payload[
        "trusted_persistence_authority_sha256"
    ]:
        raise protocol.ScientificWorkerProtocolError(
            "TRUSTED_PERSISTENCE_IDENTITY_MISMATCH",
            calendar.TRUSTED_PERSISTENCE_AUTHORITY_SHA256,
        )

    # Step 16 — exactly one frozen read-only scientific operation.
    store = frozen_operations.reconstruct_evidence_store(
        calendar, payload["evidence_admission_mode"], payload["evidence_records"]
    )
    raw_result, encoded = frozen_operations.evaluate_operation(
        calendar,
        payload["operation"],
        payload["operation_inputs"],
        request.decision_time,
        store,
    )

    # Step 17 — the admitted result must already be fully materialized.
    protocol.refuse_lazy_result(raw_result)
    protocol.refuse_lazy_result(encoded)

    # Step 18 — defence in depth, never runtime object attestation.
    protocol.verify_loaded_project_modules(
        entries, resolved, payload["required_project_modules"], "POST_EXECUTION"
    )
    protocol.verify_loaded_module_bytecode_binding(
        declared_pycache_prefix, protocol.CERTIFIED_PACKAGE_ROOTS, "POST_EXECUTION"
    )
    loaded = protocol.verify_project_source_manifest(project_root, entries)
    if loaded != resolved:
        raise protocol.ScientificWorkerProtocolError(
            "CERTIFIED_SOURCE_DRIFTED_DURING_EXECUTION", ""
        )

    # Step 19 — exactly one canonical response.
    response = protocol.build_response(
        response_schema_version=protocol.RESPONSE_SCHEMA_VERSION,
        status=protocol.SUCCESS,
        failure_reason=None,
        worker_authority_version=protocol.WORKER_AUTHORITY_VERSION,
        worker_authority_ticket=protocol.WORKER_AUTHORITY_TICKET,
        worker_authority_sha256=payload["worker_authority_sha256"],
        authority_context_origin=payload["authority_context_origin"],
        calendar_authority_version=calendar.AUTHORITY_VERSION,
        calendar_authority_sha256=calendar.FROZEN_AUTHORITY_DEFINITION_SHA256,
        trusted_persistence_authority_sha256=(
            calendar.TRUSTED_PERSISTENCE_AUTHORITY_SHA256
        ),
        interpreter_identity=protocol.current_interpreter_identity(),
        worker_entrypoint_module=protocol.WORKER_ENTRYPOINT_MODULE,
        worker_entrypoint_sha256=observed_entry_sha,
        worker_protocol_sha256=observed_protocol_sha,
        project_source_manifest_digest=protocol.manifest_digest(entries),
        project_source_manifest_role=payload["project_source_manifest_role"],
        third_party_authority_digest=third_party["third_party_authority_digest"],
        third_party_observed_content_manifest_digest=(
            third_party["observed_content_manifest_digest"]
        ),
        third_party_installed_content_verification=(
            third_party["installed_content_verification"]
        ),
        bytecode_cache_binding="PASS" if cache else "FAIL",
        loaded_project_modules=len(resolved),
        interpreter_flags=startup["interpreter_flags"],
        sys_path_digest=startup["sys_path_digest"],
        request_schema_version=protocol.REQUEST_SCHEMA_VERSION,
        request_digest=request_digest,
        operation=payload["operation"],
        evidence_admission_mode=payload["evidence_admission_mode"],
        decision_time=payload["decision_time"],
        result=encoded,
        result_digest=protocol.result_digest(encoded),
        post_execution_source_verification="PASS",
        one_request_one_process=True,
    )
    protocol.assert_address_free(response)
    return response


def refusal_response(reason: str, request_digest: str | None) -> dict[str, Any]:
    """A deterministic typed failure never carries a scientific result."""

    protocol = _load_protocol()
    return protocol.build_response(
        response_schema_version=protocol.RESPONSE_SCHEMA_VERSION,
        status=protocol.REFUSED,
        failure_reason=reason,
        worker_authority_version=protocol.WORKER_AUTHORITY_VERSION,
        worker_authority_ticket=protocol.WORKER_AUTHORITY_TICKET,
        worker_authority_sha256=None,
        authority_context_origin=None,
        calendar_authority_version=None,
        calendar_authority_sha256=None,
        trusted_persistence_authority_sha256=None,
        interpreter_identity=None,
        worker_entrypoint_module=protocol.WORKER_ENTRYPOINT_MODULE,
        worker_entrypoint_sha256=None,
        worker_protocol_sha256=None,
        project_source_manifest_digest=None,
        project_source_manifest_role=None,
        third_party_authority_digest=None,
        third_party_observed_content_manifest_digest=None,
        third_party_installed_content_verification="NOT_REACHED",
        bytecode_cache_binding="NOT_REACHED",
        loaded_project_modules=None,
        interpreter_flags=None,
        sys_path_digest=None,
        request_schema_version=protocol.REQUEST_SCHEMA_VERSION,
        request_digest=request_digest,
        operation=None,
        evidence_admission_mode=None,
        decision_time=None,
        result=None,
        result_digest=None,
        post_execution_source_verification="NOT_REACHED",
        one_request_one_process=True,
    )


def _declared_interpreter_identity(raw_request: bytes) -> dict[str, Any] | None:
    """Read the expected interpreter identity without validating the request.

    An unreadable or malformed payload declares nothing, so the ordinary
    canonical-protocol path produces the typed refusal instead.
    """

    try:
        payload = json.loads(raw_request.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        return None
    declared = payload.get("interpreter_identity") if isinstance(payload, dict) else None
    return declared if isinstance(declared, dict) else None


def _typed_reason(error: BaseException) -> str:
    reason = getattr(error, "reason", None)
    if isinstance(reason, str) and reason:
        return reason
    return f"WORKER_SCIENTIFIC_EXCEPTION:{type(error).__name__}"


def main(
    argv: list[str], raw_request: bytes, entry_path: Path
) -> tuple[int, bytes]:
    """Return the worker exit status and the single canonical stdout payload."""

    sys.path[:] = [str(entry) for entry in json.loads(argv[1])]
    declared_pycache_prefix = str(argv[2])
    if not bytecode_cache_namespace_is_controlled(declared_pycache_prefix):
        return EXIT_UNCONTROLLED_BYTECODE_CACHE, b""
    declared = _declared_interpreter_identity(raw_request)
    if declared is not None and live_interpreter_identity() != declared:
        return EXIT_WRONG_INTERPRETER, b""
    protocol = _load_protocol()
    try:
        response = serve_one_request(raw_request, entry_path, declared_pycache_prefix)
        status = EXIT_SUCCESS
    except Exception as error:  # deterministic typed failure, never partial admission
        response = refusal_response(_typed_reason(error), None)
        status = EXIT_REFUSED
    payload = protocol.canonical_json_bytes(response) + b"\n"
    if len(payload) > protocol.MAX_RESPONSE_BYTES:
        return EXIT_PROTOCOL_FAILURE, b""
    return status, payload


if __name__ == "__main__":  # pragma: no cover - exercised through the controller
    _status, _payload = main(
        sys.argv, sys.stdin.buffer.read(), Path(__file__).resolve()
    )
    if _status == EXIT_WRONG_INTERPRETER:
        sys.stderr.write(
            f"{REFUSE_SCIENTIFIC_AUTHORITY}: frozen proof interpreter mismatch\n"
        )
    if _status == EXIT_UNCONTROLLED_BYTECODE_CACHE:
        sys.stderr.write(
            f"{REFUSE_SCIENTIFIC_AUTHORITY}: bytecode cache namespace is not "
            "the fresh controller-declared namespace\n"
        )
    sys.stdout.buffer.write(_payload)
    sys.stdout.buffer.flush()
    raise SystemExit(_status)
