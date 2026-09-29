"""Standalone ETF-calendar evidence verifier — the only scientific authority.

This file is a **program**, not a library the producer calls.  It runs as its
own top-level isolated interpreter process, it executes only certified source,
and nothing a caller holds can cross into it.  Under
``ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1`` it is the sole thing that can make
ETF calendar evidence admissible::

    NO IN-PROCESS OBJECT CARRIES SCIENTIFIC AUTHORITY.

The four ``PAD4`` generations all failed the same way: a caller-created object
acquired authority — by fabricating a result, by mutating admitted state, by
impersonating a receiver, and finally by recovering the closure-owned registry
through ordinary ``gc`` graph traversal.  Every one of those exploits needed
only that the authority live in the same interpreter as the caller.  Here it
does not live in an interpreter at all.  Authority is a **property of bytes**:
evidence is admissible exactly when this program, running the certified source
of an exact reviewed commit, re-derives the recorded response byte-for-byte
from authenticated inputs.

That makes every named ``PAD4-R5`` route inapplicable by construction rather
than excluded by domain text.  A forged object in the producer's process
presents bytes; if they are the genuine bytes, this program accepts them as
the same evidence and nothing new is admitted, and if they are fabricated, they
do not re-derive and this program rejects them.  The producer's process may use
``gc``, class mutation, closure recovery, frames and ``ctypes`` freely.  None of
it reaches here.

Interface
---------

The whole interface is five command-line strings — a JSON array of ``sys.path``
directories, a bytecode-cache namespace directory, an evidence directory, a
record directory and one of two frozen mode literals.  There is no channel that
can transport a callback, a plugin, a pickle, a class, a module or any caller
object: the process boundary refuses everything that is not bytes, and the only
bytes accepted are those five arguments and the canonical JSON documents they
name.  ``pickle``, ``marshal``, ``eval``, ``exec``, ``compile``, ``__import__``,
``importlib`` and ``runpy`` occur nowhere in this file or its contract, which
the mechanical interface audit computes rather than assumes.

Self-attestation is not authority
---------------------------------

This program records the digest of its own derived source manifest.  That is
audit metadata and defence in depth.  It is **not** authority, because a
program that has been replaced can report whatever manifest digest it likes.
Authority is anchored in the exact reviewed commit this source is.

Because ``sys.path`` is established from ``argv`` inside ``main``, every project
import in this file is declared inside a function.  Those are ordinary static
import declarations and the mechanical closure derivation follows them, exactly
as it follows the worker entrypoint's.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


EXIT_ALL_ACCEPTED = 0
EXIT_SOME_REJECTED = 3
EXIT_VERIFIER_FAILURE = 4

#: The ``PAD5`` verifier never writes scientific evidence to stdout; it writes
#: one canonical summary a harness may read for convenience, and the records
#: themselves are files.
STDOUT_PROTOCOL = "EXACTLY_ONE_CANONICAL_JSON_SUMMARY_PLUS_ONE_TRAILING_NEWLINE"


def _install_sys_path(raw: str) -> list[str]:
    """Establish the parent-declared ``sys.path`` before any project import."""

    entries = json.loads(raw)
    if not isinstance(entries, list) or not all(
        isinstance(entry, str) for entry in entries
    ):
        raise ValueError("the verifier sys.path argument must be a JSON array of paths")
    sys.path[:] = list(entries)
    return list(entries)


def _read_exact_bytes(path: Path) -> bytes:
    return path.read_bytes()


def _canonical_document(raw: bytes) -> Any:
    """Parse one canonical JSON document that re-serializes to its own bytes.

    The re-serialisation equality check is what makes the transport a
    deterministic non-executable document.  A payload that parses but does not
    re-serialize to the received bytes is refused rather than normalised,
    because normalising it would be rewriting recorded bytes.
    """

    from etf_calendar_worker import protocol_r2 as protocol

    payload = protocol.parse_canonical_json(raw)
    if protocol.canonical_json_bytes(payload) != raw:
        raise protocol.ScientificWorkerProtocolError(
            "SCIENTIFIC_IPC_PAYLOAD_IS_NOT_CANONICAL",
            "the recorded document does not re-serialize to the exact bytes stored",
        )
    return payload


def verifier_identity(project_root: Path) -> dict[str, Any]:
    """Derive this verifier's own source manifest, digest, count and commit."""

    from btc_predictor.research import (
        etf_calendar_replay_verified_evidence_contract as contract,
    )

    entries = contract.derive_source_manifest(project_root)
    return {
        "verifier_source_manifest_digest": contract.verifier_source_manifest_digest(
            entries
        ),
        "verifier_source_module_count": len(entries),
        "verifier_commit": contract.resolve_commit(project_root),
        "entries": entries,
    }


def _test_verification_key(payload: Any) -> Any:
    """Rebuild an explicitly test-only verification key from canonical fields."""

    from btc_predictor.research import (
        etf_calendar_replay_verified_evidence_contract as contract,
    )
    from btc_predictor.research import trusted_acquisition as trusted

    if not isinstance(payload, dict) or sorted(payload) != sorted(
        contract.TEST_TRUST_ROOT_FIELDS
    ):
        raise contract.ReplayVerifiedEvidenceError(
            "a test trust root must be exactly the frozen test trust-root fields"
        )
    if not str(payload["key_id"]).startswith(contract.TEST_ONLY_KEY_ID_PREFIX):
        raise contract.ReplayVerifiedEvidenceError(
            "a file-supplied trust root must be a test-only key"
        )
    return trusted.VerificationKey(
        key_id=payload["key_id"],
        algorithm=payload["algorithm"],
        public_key_base64=payload["public_key_base64"],
        public_key_sha256=payload["public_key_sha256"],
        authority_version=payload["authority_version"],
        status=payload["status"],
    )


def verify_evidence_item(
    item_dir: Path,
    *,
    project_root: Path,
    pycache_namespace: Path,
    mode: str,
    identity: dict[str, Any],
) -> dict[str, Any]:
    """Verify one candidate evidence item and return its verification record.

    The frozen order is: layout, recorded request, request authority, this
    interpreter's identity, the recorded environment, every input envelope,
    the evidence-record/envelope correspondence, the bootstrap pre-execution
    binding, the recorded response, re-execution, and finally the byte-for-byte
    projection comparison.  Every refusal returns a record; none is dropped.
    """

    from btc_predictor.research import (
        etf_calendar_replay_verified_evidence_contract as contract,
    )
    from btc_predictor.research import trusted_acquisition as trusted
    from etf_calendar_worker import protocol_r2 as protocol

    item_id = item_dir.name
    empty: dict[str, Any] = {
        "evidence_item_id": item_id,
        "request_digest": None,
        "response_digest": None,
        "recorded_projection_digest": None,
        "rederived_projection_digest": None,
        "input_envelope_count": 0,
        "input_envelope_digests": [],
        "verifier_source_manifest_digest": identity[
            "verifier_source_manifest_digest"
        ],
        "verifier_source_module_count": identity["verifier_source_module_count"],
        "verifier_commit": identity["verifier_commit"],
        "verifier_mode": mode,
        "interpreter_identity": dict(protocol.current_interpreter_identity()),
    }

    def reject(code: str, detail: str, **extra: Any) -> dict[str, Any]:
        return contract.verification_record(
            **{**empty, **extra},
            verdict=contract.REJECTED,
            reason_code=code,
            reason_detail=detail,
        )

    # 1 — layout.  Exactly the frozen required files, plus the test trust root
    # only in the explicitly non-authoritative test mode.
    present = sorted(child.name for child in item_dir.iterdir())
    allowed = set(contract.EVIDENCE_ITEM_FILENAMES)
    if mode == contract.NON_AUTHORITATIVE_TEST_MODE:
        allowed |= set(contract.EVIDENCE_ITEM_OPTIONAL_FILENAMES)
    missing = sorted(set(contract.EVIDENCE_ITEM_FILENAMES) - set(present))
    unexpected = sorted(set(present) - allowed)
    if missing or unexpected:
        return reject(
            "REJECTED_EVIDENCE_ITEM_LAYOUT_INVALID",
            f"missing={missing!r} unexpected={unexpected!r}",
        )
    trust_root_file = item_dir / contract.TEST_TRUST_ROOT_FILENAME
    if mode == contract.PRODUCTION_MODE and trust_root_file.exists():
        return reject(
            "REJECTED_EVIDENCE_ITEM_LAYOUT_INVALID",
            "production verification never accepts a file-supplied trust root",
        )

    # 2 — the recorded request, as exact canonical bytes.
    request_raw = _read_exact_bytes(item_dir / contract.REQUEST_FILENAME)
    try:
        request = _canonical_document(request_raw)
    except protocol.ScientificWorkerProtocolError as error:
        return reject("REJECTED_RECORDED_REQUEST_IS_NOT_CANONICAL", error.reason)
    request_digest = protocol.digest_bytes(request_raw)
    empty["request_digest"] = request_digest
    try:
        protocol.validate_request(request)
    except protocol.ScientificWorkerProtocolError as error:
        return reject("REJECTED_RECORDED_REQUEST_SCHEMA_INVALID", error.reason)

    # 3 — every authority-bound request field against the frozen trusted
    # context.  No expected value is ever taken from the request itself.
    drifted = contract.expected_authority_drift(
        request, protocol.AUTHORITY_BOUND_REQUEST_FIELDS
    )
    if drifted:
        return reject(
            "REJECTED_RECORDED_REQUEST_AUTHORITY_MISMATCH", repr(list(drifted))
        )

    # 4 — this interpreter must be the frozen proof interpreter.
    try:
        protocol.verify_proof_interpreter_identity()
    except protocol.ScientificWorkerProtocolError as error:
        return reject("REJECTED_INTERPRETER_IDENTITY_MISMATCH", error.reason)

    # 5 — the recorded environment.  The frozen rule is verification in the
    # recorded environment; request bytes are never rewritten to fit this one.
    recorded_root = Path(str(request["project_root"]))
    if recorded_root.resolve() != Path(project_root).resolve():
        return reject(
            "REJECTED_NOT_THE_RECORDED_ENVIRONMENT",
            f"recorded project_root {str(recorded_root)!r} is not this checkout",
        )
    if str(recorded_root) not in request["sys_path"]:
        return reject(
            "REJECTED_NOT_THE_RECORDED_ENVIRONMENT",
            "the recorded sys_path does not contain the recorded project root",
        )
    # The installed third-party environment the request names must be the one
    # present here.  Each ``RECORD`` is a real file, so its absence means the
    # dependency environment moved.  Deliberately *not* checked: that every
    # recorded ``sys.path`` entry exists.  CPython always synthesises a
    # ``pythonXY.zip`` entry whether or not the file is there, so requiring
    # existence would reject every honest verification.  What actually binds
    # the environment is stricter than a path check anyway: the worker is
    # re-executed with exactly the recorded ``sys.path``, and
    # ``sys_path_digest``, ``project_source_manifest_digest``,
    # ``interpreter_identity`` and
    # ``third_party_observed_content_manifest_digest`` are all inside the
    # comparison projection, so a moved environment cannot re-derive.
    absent = sorted(
        str(row.get("record_path"))
        for row in request["third_party_environment"]
        if not Path(str(row.get("record_path"))).is_file()
    )
    if absent:
        return reject(
            "REJECTED_NOT_THE_RECORDED_ENVIRONMENT",
            f"recorded third-party install records are absent here: {absent!r}",
        )

    # 6 — every input envelope, under the certified trusted-persistence
    # verification path.
    envelopes_raw = _read_exact_bytes(item_dir / contract.ENVELOPES_FILENAME)
    try:
        envelopes = _canonical_document(envelopes_raw)
    except protocol.ScientificWorkerProtocolError as error:
        return reject("REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED", error.reason)
    if not isinstance(envelopes, list):
        return reject(
            "REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED",
            "the recorded input envelopes are not a JSON array",
        )
    empty["input_envelope_count"] = len(envelopes)
    empty["input_envelope_digests"] = [
        protocol.digest_payload(envelope) for envelope in envelopes
    ]

    test_key = None
    if mode == contract.NON_AUTHORITATIVE_TEST_MODE:
        if not trust_root_file.exists():
            return reject(
                "REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED",
                "test-mode verification requires an explicit test trust root",
            )
        try:
            test_key = _test_verification_key(
                _canonical_document(_read_exact_bytes(trust_root_file))
            )
        except (
            contract.ReplayVerifiedEvidenceError,
            protocol.ScientificWorkerProtocolError,
        ) as error:
            return reject(
                "REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED", str(error)
            )

    payloads: list[Any] = []
    for index, envelope in enumerate(envelopes):
        if not isinstance(envelope, dict):
            return reject(
                "REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED",
                f"envelope {index} is not a JSON object",
            )
        signing_key_id = envelope.get("signing_key_id")
        if mode == contract.PRODUCTION_MODE and isinstance(signing_key_id, str):
            # Named explicitly so the record says *why* a test-key envelope was
            # refused.  The certified production verifier refuses it anyway,
            # because the frozen production registry does not contain the key;
            # this only turns a generic refusal into a precise reason code.
            if signing_key_id.startswith(contract.TEST_ONLY_KEY_ID_PREFIX):
                return reject(
                    "REJECTED_TEST_KEY_ENVELOPE_IN_PRODUCTION_MODE",
                    f"envelope {index} is signed by {signing_key_id!r}",
                )
        try:
            if mode == contract.PRODUCTION_MODE:
                payloads.append(trusted.verify_production_envelope(envelope))
            else:
                payloads.append(
                    trusted.verify_test_envelope_non_authoritative_test_only(
                        envelope, test_key
                    )
                )
        except trusted.TrustedAcquisitionError as error:
            return reject(
                "REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED",
                f"envelope {index}: {error}",
            )

    # 7 — the request's evidence records and the verified envelope payloads
    # must be the same set of canonical documents.  An evidence record with no
    # verified envelope is unauthenticated input, and a verified envelope the
    # request never names did not contribute to this result.
    recorded_records = {
        protocol.digest_payload(record) for record in request["evidence_records"]
    }
    verified_payloads = {protocol.digest_payload(payload) for payload in payloads}
    unauthenticated = sorted(recorded_records - verified_payloads)
    if unauthenticated:
        return reject(
            "REJECTED_EVIDENCE_RECORD_HAS_NO_VERIFIED_ENVELOPE",
            repr(unauthenticated),
        )
    unnamed = sorted(verified_payloads - recorded_records)
    if unnamed:
        return reject(
            "REJECTED_ENVELOPE_PAYLOAD_IS_NOT_A_RECORDED_EVIDENCE_RECORD",
            repr(unnamed),
        )

    # 8 — the bootstrap pre-execution source binding.  Already-trusted code
    # hashes every bootstrap source and refuses before any process exists, so
    # drifted bootstrap source cannot run, write a marker or emit a response.
    try:
        bootstrap_entries = protocol.bootstrap_source_entries(
            request["worker_bootstrap_manifest"]
        )
        if (
            protocol.bootstrap_manifest_digest(bootstrap_entries)
            != contract.FROZEN_WORKER_BOOTSTRAP_MANIFEST_DIGEST
        ):
            raise protocol.ScientificWorkerProtocolError(
                "WORKER_BOOTSTRAP_MANIFEST_DIGEST_REFUSED",
                "the recorded bootstrap manifest is not the frozen one",
            )
        protocol.verify_bootstrap_source_set(Path(project_root), bootstrap_entries)
    except protocol.ScientificWorkerProtocolError as error:
        return reject("REJECTED_WORKER_BOOTSTRAP_SOURCE_DRIFT", error.reason)

    # 9 — the recorded response.
    response_raw = _read_exact_bytes(item_dir / contract.RESPONSE_FILENAME)
    try:
        recorded_response = _canonical_document(response_raw)
    except protocol.ScientificWorkerProtocolError as error:
        return reject("REJECTED_RECORDED_RESPONSE_IS_NOT_CANONICAL", error.reason)
    empty["response_digest"] = protocol.digest_bytes(response_raw)
    try:
        protocol.validate_response(recorded_response)
    except protocol.ScientificWorkerProtocolError as error:
        return reject("REJECTED_RECORDED_RESPONSE_SCHEMA_INVALID", error.reason)
    drifted = contract.expected_authority_drift(
        recorded_response, protocol.AUTHORITY_BOUND_RESPONSE_FIELDS
    )
    if drifted:
        return reject(
            "REJECTED_RECORDED_RESPONSE_AUTHORITY_MISMATCH", repr(list(drifted))
        )
    # A refusal that re-derives as the same refusal is a faithfully recorded
    # refusal, not calendar evidence.  Accepting it would be a real hole: a
    # consumer applying the admission rule would treat "the certified worker
    # declined to answer" as an answer.  It is recorded with its own reason
    # code rather than dropped.
    if recorded_response["status"] != protocol.SUCCESS:
        return reject(
            "REJECTED_RECORDED_RESPONSE_IS_NOT_A_SUCCESS",
            f"worker status {recorded_response['status']!r} with failure_reason "
            f"{recorded_response['failure_reason']!r}",
        )
    # The response must bind the request it is filed with.  Re-derivation would
    # catch a mismatched pair anyway, because the re-executed worker echoes the
    # digest of the bytes it actually received; checking it here only makes the
    # recorded reason precise instead of reporting a generic drift.
    if recorded_response["request_digest"] != request_digest:
        return reject(
            "REJECTED_RECORDED_RESPONSE_DOES_NOT_BIND_THE_RECORDED_REQUEST",
            f"response names {recorded_response['request_digest']!r}",
        )
    if recorded_response["result_digest"] != protocol.result_digest(
        recorded_response["result"]
    ):
        return reject(
            "REJECTED_RECORDED_RESPONSE_RESULT_DIGEST_MISMATCH",
            "the recorded result digest does not describe the recorded result",
        )
    try:
        recorded_projection = contract.projection_digest(recorded_response)
    except contract.ReplayVerifiedEvidenceError as error:
        return reject("REJECTED_RECORDED_RESPONSE_SCHEMA_INVALID", str(error))
    empty["recorded_projection_digest"] = recorded_projection

    # 10 — re-execute the certified fresh-exec worker on the exact recorded
    # request bytes, in a fresh empty per-item bytecode-cache namespace.
    namespace = Path(pycache_namespace) / "worker" / item_id
    namespace.mkdir(parents=True, exist_ok=True)
    outcome = contract.spawn_isolated_process(
        contract.worker_argv(
            executable=sys.executable,
            entrypoint=Path(project_root) / protocol.WORKER_ENTRYPOINT_RELATIVE_PATH,
            sys_path=request["sys_path"],
            pycache_namespace=namespace,
        ),
        stdin_bytes=request_raw,
        cwd=project_root,
    )
    if outcome["timed_out"] or outcome["exit_status"] != 0:
        return reject(
            "REJECTED_WORKER_EXECUTION_FAILED",
            f"timed_out={outcome['timed_out']} exit_status={outcome['exit_status']}",
        )
    stdout = outcome["stdout"]
    if not stdout.endswith(b"\n") or stdout.count(b"\n") != 1:
        return reject(
            "REJECTED_REDERIVED_RESPONSE_IS_NOT_CANONICAL",
            "the worker did not emit exactly one protocol payload",
        )
    try:
        rederived = _canonical_document(stdout[:-1])
    except protocol.ScientificWorkerProtocolError as error:
        return reject("REJECTED_REDERIVED_RESPONSE_IS_NOT_CANONICAL", error.reason)
    try:
        protocol.validate_response(rederived)
    except protocol.ScientificWorkerProtocolError as error:
        return reject("REJECTED_REDERIVED_RESPONSE_SCHEMA_INVALID", error.reason)
    if rederived["status"] != protocol.SUCCESS:
        return reject(
            "REJECTED_REDERIVED_RESPONSE_IS_NOT_A_SUCCESS",
            f"re-execution refused with {rederived['failure_reason']!r}",
        )

    # 11 — the byte-for-byte comparison, over the frozen closed inclusion list.
    try:
        rederived_projection = contract.projection_digest(rederived)
    except contract.ReplayVerifiedEvidenceError as error:
        return reject("REJECTED_REDERIVED_RESPONSE_SCHEMA_INVALID", str(error))
    empty["rederived_projection_digest"] = rederived_projection
    recorded_bytes = contract.projection_bytes(recorded_response)
    rederived_bytes = contract.projection_bytes(rederived)
    if recorded_bytes != rederived_bytes:
        differing = sorted(
            name
            for name in contract.IN_PROJECTION_AUTHORITY_FIELDS
            if recorded_response.get(name) != rederived.get(name)
        )
        return reject("REJECTED_PROJECTION_IS_NOT_BYTE_IDENTICAL", repr(differing))

    return contract.verification_record(
        **empty,
        verdict=contract.ACCEPTED,
        reason_code=contract.ACCEPTED_REASON,
        reason_detail="",
    )


def verify_evidence_directory(
    evidence_dir: Path,
    record_dir: Path,
    *,
    project_root: Path,
    pycache_namespace: Path,
    mode: str,
) -> dict[str, Any]:
    """Verify every evidence item and write one canonical record for each."""

    from btc_predictor.research import (
        etf_calendar_replay_verified_evidence_contract as contract,
    )
    from etf_calendar_worker import protocol_r2 as protocol

    if mode not in contract.VERIFIER_MODES:
        raise contract.ReplayVerifiedEvidenceError(f"unknown verifier mode {mode!r}")
    identity = verifier_identity(Path(project_root))
    record_dir.mkdir(parents=True, exist_ok=True)

    accepted = 0
    rejected = 0
    reason_counts: dict[str, int] = {}
    for item_dir in sorted(
        child for child in Path(evidence_dir).iterdir() if child.is_dir()
    ):
        record = verify_evidence_item(
            item_dir,
            project_root=Path(project_root),
            pycache_namespace=Path(pycache_namespace),
            mode=mode,
            identity=identity,
        )
        target = record_dir / (
            item_dir.name + contract.VERIFICATION_RECORD_FILENAME_SUFFIX
        )
        target.write_bytes(protocol.canonical_json_bytes(record))
        if record["verdict"] == contract.ACCEPTED:
            accepted += 1
        else:
            rejected += 1
        reason_counts[record["reason_code"]] = (
            reason_counts.get(record["reason_code"], 0) + 1
        )

    return {
        "accepted": accepted,
        "reason_counts": dict(sorted(reason_counts.items())),
        "record_schema_version": contract.VERIFICATION_RECORD_SCHEMA_VERSION,
        "rejected": rejected,
        "verifier_commit": identity["verifier_commit"],
        "verifier_mode": mode,
        "verifier_source_manifest_digest": identity[
            "verifier_source_manifest_digest"
        ],
        "verifier_source_module_count": identity["verifier_source_module_count"],
    }


def main(argv: list[str]) -> int:
    """Five string arguments in, one canonical summary and N records out."""

    if len(argv) != 6:
        sys.stderr.write(
            "usage: etf_calendar_evidence_verifier.py SYS_PATH_JSON "
            "PYCACHE_NAMESPACE EVIDENCE_DIR RECORD_DIR MODE\n"
        )
        return EXIT_VERIFIER_FAILURE
    _install_sys_path(argv[1])
    pycache_namespace = Path(argv[2])
    evidence_dir = Path(argv[3])
    record_dir = Path(argv[4])
    mode = argv[5]

    from etf_calendar_worker import protocol_r2 as protocol

    project_root = Path(__file__).resolve().parents[2]
    try:
        summary = verify_evidence_directory(
            evidence_dir,
            record_dir,
            project_root=project_root,
            pycache_namespace=pycache_namespace,
            mode=mode,
        )
    except Exception as error:  # pragma: no cover - reported, never swallowed
        sys.stderr.write(f"{type(error).__name__}: {error}\n")
        return EXIT_VERIFIER_FAILURE
    sys.stdout.buffer.write(protocol.canonical_json_bytes(summary) + b"\n")
    return EXIT_ALL_ACCEPTED if summary["rejected"] == 0 else EXIT_SOME_REJECTED


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main(sys.argv))
