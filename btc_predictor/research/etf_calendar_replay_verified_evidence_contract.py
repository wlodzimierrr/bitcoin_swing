"""Frozen shared contract for ``ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1``.

``POSTP1-002V2A-PAD4-R5`` failed the ``PAD4`` lineage for the fourth time in one
family: a caller-created object acquired scientific authority, this time by
recovering the closure-owned registry through public ``gc`` graph traversal.
The recorded same-family escalation decision
``DECIDE_ETF_CALENDAR_PROOF_ARCHITECTURE_AFTER_PAD4_R5_V1`` retired in-process
authority objects outright and selected a different family::

    NO IN-PROCESS OBJECT CARRIES SCIENTIFIC AUTHORITY.  CALENDAR EVIDENCE IS
    ADMISSIBLE IF AND ONLY IF A STANDALONE VERIFIER PROCESS, EXECUTING ONLY
    CERTIFIED SOURCE AT AN EXACT REVIEWED COMMIT, (1) VERIFIES THE RECORDED
    REQUEST AGAINST THE FROZEN TRUSTED AUTHORITY CONTEXT, (2) VERIFIES EVERY
    INPUT EVIDENCE RECORD UNDER THE CERTIFIED TRUSTED-PERSISTENCE AUTHORITY,
    (3) RE-EXECUTES THE CERTIFIED FRESH-EXEC WORKER ON THE EXACT RECORDED
    REQUEST BYTES, AND (4) FINDS THE FROZEN DETERMINISTIC PROJECTION OF THE
    RESPONSE BYTE-IDENTICAL TO THE RECORDED ONE.

This module is the frozen material both sides of that boundary share.  It is
deliberately the *only* new module the verifier and the producer both import,
and it is deliberately tiny in import terms: its complete static project-import
closure is ``etf_calendar_worker`` plus the two frozen worker protocol modules.
Nothing here reaches a ``PAD4`` lineage controller, because every one of those
is outside the certified worker source universe and would therefore make the
verifier execute uncertified code.

Three properties of this file are load-bearing and are audited mechanically
rather than asserted:

* it defines **no authority marker at all**, so no producer-side or
  verifier-side type can carry one;
* it owns the **single process-creation site** in the whole ``PAD5`` surface,
  used by the verifier to re-execute the worker and by the harness to launch
  the verifier, so the direct-launch census has exactly one justified site to
  account for; and
* the deterministic comparison projection is a **closed inclusion list** of
  named response fields.  It is never "everything except", and a response field
  that is not named here is not projected.
"""

from __future__ import annotations

import ast
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

from etf_calendar_worker import protocol_r2 as protocol


DECISION_VERSION = "ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1"
PROGRAM_TICKET = "POSTP1-001V2A-PAD5"

#: The invariant the selected architecture freezes, restated exactly as the
#: escalation decision records it.
REPLAY_VERIFIED_EVIDENCE_INVARIANT = (
    "NO_IN_PROCESS_OBJECT_CARRIES_SCIENTIFIC_AUTHORITY__CALENDAR_EVIDENCE_IS_"
    "ADMISSIBLE_IF_AND_ONLY_IF_A_STANDALONE_VERIFIER_PROCESS_EXECUTING_ONLY_"
    "CERTIFIED_SOURCE_AT_AN_EXACT_REVIEWED_COMMIT_VERIFIES_THE_RECORDED_"
    "REQUEST_AGAINST_THE_FROZEN_TRUSTED_AUTHORITY_CONTEXT_VERIFIES_EVERY_"
    "INPUT_EVIDENCE_RECORD_UNDER_THE_CERTIFIED_TRUSTED_PERSISTENCE_AUTHORITY_"
    "RE_EXECUTES_THE_CERTIFIED_FRESH_EXEC_WORKER_ON_THE_EXACT_RECORDED_"
    "REQUEST_BYTES_AND_FINDS_THE_FROZEN_DETERMINISTIC_PROJECTION_OF_THE_"
    "RESPONSE_BYTE_IDENTICAL_TO_THE_RECORDED_ONE"
)

#: Authority is anchored in the exact reviewed commit the verifier runs from.
#: The verifier's own source-manifest digest, which it records, is audit
#: metadata and defence in depth; it is explicitly **not** authority, because a
#: program that attests itself proves nothing a reviewer could not already
#: forge by changing the program.
VERIFIER_AUTHORITY_ANCHOR = "EXACT_REVIEWED_COMMIT_OF_THE_VERIFIER_SOURCE"
VERIFIER_SELF_ATTESTATION_IS_AUTHORITY = False
PRODUCER_SELF_ATTESTATION_IS_AUTHORITY = False


class ReplayVerifiedEvidenceError(ValueError):
    """Raised when the replay-verified evidence contract must refuse."""


# ---------------------------------------------------------------------------
# Non-authority labelling
# ---------------------------------------------------------------------------

#: Every producer output carries this, and nothing else.  There is no
#: affirmative producer-side authority marker to carry: this architecture has
#: none to give.
NON_AUTHORITATIVE = "NON_AUTHORITATIVE"
PRODUCER_OUTPUT_AUTHORITY = "NON_AUTHORITATIVE_CANDIDATE_EVIDENCE"
PRODUCER_PROCESS_TRUST = "FULLY_UNTRUSTED_AT_THE_PYTHON_LEVEL"

#: The retired ``PAD4`` authority markers.  They are named here so the
#: mechanical audit can prove that neither the producer nor the verifier emits
#: one, rather than a reviewer having to take that on trust.  Naming them is
#: not adopting them.
RETIRED_AUTHORITY_MARKERS: tuple[str, ...] = (
    "AUTHORITATIVE_CLOSED_CONTROLLER_EXECUTION_V1_R5",
    "AUTHORITATIVE_CLOSED_CONTROLLER_EXECUTION_V1_R4",
    "AUTHORITATIVE_CLOSED_CONTROLLER_EXECUTION_V1_R3",
)

#: Mechanisms this architecture retires as authority carriers.  Each one is a
#: thing an earlier ``PAD4`` generation used and a review refused.
RETIRED_AUTHORITY_MECHANISMS: tuple[str, ...] = (
    "CAPABILITY_GATED_BIND",
    "CLOSURE_OWNED_IDENTITY_REGISTRY",
    "DOMAIN_SCOPED_INTROSPECTION_EXCLUSION_TEXT",
    "EXACT_TYPE_RECEIVER_GATE",
    "IN_PROCESS_AUTHORITATIVE_EXECUTION_OBJECT",
)


# ---------------------------------------------------------------------------
# Verifier modes
# ---------------------------------------------------------------------------

#: Production verification.  Input envelopes are verified against the one
#: frozen production trust root, so a test-key envelope is refused.
PRODUCTION_MODE = "PRODUCTION"

#: Explicitly non-authoritative test verification.  It exists so the proof
#: obligations can be exercised without a production signing key, and every
#: record it writes says so in its own ``verifier_mode`` field.
NON_AUTHORITATIVE_TEST_MODE = "NON_AUTHORITATIVE_TEST"

VERIFIER_MODES: tuple[str, ...] = (PRODUCTION_MODE, NON_AUTHORITATIVE_TEST_MODE)

#: The one key-id prefix the certified trusted-acquisition authority reserves
#: for test material.  Production verification refuses such an envelope because
#: the frozen production registry does not contain the key, which is the
#: certified module's own behaviour and not a second rule invented here.
TEST_ONLY_KEY_ID_PREFIX = "TEST_ONLY_"


# ---------------------------------------------------------------------------
# Frozen evidence-item layout
# ---------------------------------------------------------------------------

EVIDENCE_ITEM_LAYOUT_VERSION = "ETF_CALENDAR_REPLAY_EVIDENCE_ITEM_LAYOUT_V1"

#: One directory per candidate evidence item, holding exactly these four files
#: and nothing else.  Each is *exact canonical bytes* with no trailing newline,
#: so the digest of the file is the digest of the payload and there is no
#: second serialisation anywhere in the boundary.
ITEM_FILENAME = "item.canonical.json"
REQUEST_FILENAME = "request.canonical.json"
RESPONSE_FILENAME = "response.canonical.json"
ENVELOPES_FILENAME = "input_envelopes.canonical.json"

EVIDENCE_ITEM_FILENAMES: tuple[str, ...] = (
    ENVELOPES_FILENAME,
    ITEM_FILENAME,
    REQUEST_FILENAME,
    RESPONSE_FILENAME,
)

#: The one optional member of the layout, and the only one that may name a
#: verification key.  It is permitted **only** in the explicitly
#: non-authoritative test mode, and production verification refuses an item that
#: carries it.  ``POSTP1-002V2B`` failed an earlier candidate for exactly the
#: shape this forbids — a caller-supplied trust registry reaching production
#: verification — so the production trust root stays the frozen one inside the
#: certified trusted-acquisition module and is never file-supplied.
TEST_TRUST_ROOT_FILENAME = "test_trust_root.canonical.json"

TEST_TRUST_ROOT_FIELDS: tuple[str, ...] = (
    "algorithm",
    "authority_version",
    "key_id",
    "public_key_base64",
    "public_key_sha256",
    "status",
)

EVIDENCE_ITEM_OPTIONAL_FILENAMES: tuple[str, ...] = (TEST_TRUST_ROOT_FILENAME,)

#: The producer manifest fields.  ``authority`` is present so that a reviewer
#: can see the non-authoritative label on the artifact itself; the verifier
#: never reads it to decide anything.
EVIDENCE_ITEM_FIELDS: tuple[str, ...] = (
    "authority",
    "evidence_item_id",
    "input_envelope_count",
    "input_envelope_digests",
    "item_layout_version",
    "producer_program_ticket",
    "producer_relative_path",
    "request_digest",
    "response_digest",
)

VERIFICATION_RECORD_FILENAME_SUFFIX = ".verification.canonical.json"


# ---------------------------------------------------------------------------
# The deterministic comparison projection
# ---------------------------------------------------------------------------

COMPARISON_PROJECTION_VERSION = (
    "ETF_CALENDAR_DETERMINISTIC_COMPARISON_PROJECTION_V1"
)

#: The closed inclusion list.  Byte-identical re-derivation is checked over
#: exactly these response fields and no others.  It is *not* defined as "the
#: response minus something": a response field that is not named here is not
#: projected at all, so adding a field to the worker protocol cannot silently
#: widen or narrow what is compared.  The frozen worker protocol independently
#: refuses an unknown response field, so an unnamed field cannot arrive
#: unnoticed either.
IN_PROJECTION_AUTHORITY_FIELDS: tuple[str, ...] = (
    "authority_context_origin",
    "bootstrap_defence_in_depth_verification",
    "bytecode_cache_binding",
    "calendar_authority_sha256",
    "calendar_authority_version",
    "decision_time",
    "evidence_admission_mode",
    "failure_reason",
    "interpreter_flags",
    "interpreter_identity",
    "loaded_project_modules",
    "one_request_one_process",
    "operation",
    "post_execution_source_verification",
    "project_source_manifest_digest",
    "project_source_manifest_role",
    "request_digest",
    "request_schema_version",
    "response_schema_version",
    "result",
    "result_digest",
    "status",
    "sys_path_digest",
    "third_party_authority_digest",
    "third_party_installed_content_verification",
    "third_party_observed_content_manifest_digest",
    "trusted_persistence_authority_sha256",
    "worker_authority_sha256",
    "worker_authority_ticket",
    "worker_authority_version",
    "worker_bootstrap_manifest_digest",
    "worker_entrypoint_module",
)

#: Response fields deliberately excluded from the comparison because they vary
#: between two runs of the same request bytes.  Measurement, not assumption,
#: decides membership: the ``PAD5`` suite re-executes the same recorded request
#: in separate processes with different bytecode-cache namespaces, different
#: working directories and different ``PYTHONHASHSEED`` values and compares
#: every field.  Every field was stable, so this list is empty, and the frozen
#: definition says so rather than implying an exclusion that does not exist.
#:
#: An empty exclusion list is the strict direction: every excluded field would
#: be a field an attacker could change freely.  It also costs availability
#: rather than integrity — a genuinely varying field would make honest evidence
#: be *rejected*, never make fabricated evidence be accepted.
RUN_LOCAL_FIELDS: tuple[str, ...] = ()

#: Why each response field is classified as it is.  Written out per field so a
#: reviewer checks 32 stated reasons instead of one sweeping claim.
PROJECTION_FIELD_JUSTIFICATION: Mapping[str, str] = {
    "authority_context_origin": (
        "IN_PROJECTION_AUTHORITY: echoed from the recorded request, so it is a "
        "pure function of the request bytes"
    ),
    "bootstrap_defence_in_depth_verification": (
        "IN_PROJECTION_AUTHORITY: the worker's restatement of the bootstrap "
        "binding; drift of any bootstrap source changes it"
    ),
    "bytecode_cache_binding": (
        "IN_PROJECTION_AUTHORITY: the preserved Repair A verdict; a cache "
        "namespace that is not fresh and empty changes it"
    ),
    "calendar_authority_sha256": (
        "IN_PROJECTION_AUTHORITY: authority-bound, compared against the frozen "
        "trusted context before execution and again after"
    ),
    "calendar_authority_version": (
        "IN_PROJECTION_AUTHORITY: authority-bound frozen constant"
    ),
    "decision_time": (
        "IN_PROJECTION_AUTHORITY: echoed from the recorded request; it is the "
        "decision time the request names, never a clock read at run time"
    ),
    "evidence_admission_mode": (
        "IN_PROJECTION_AUTHORITY: echoed from the recorded request"
    ),
    "failure_reason": (
        "IN_PROJECTION_AUTHORITY: the worker's own verdict; a refusal that "
        "re-derives as a success, or the reverse, must not compare equal"
    ),
    "interpreter_flags": (
        "IN_PROJECTION_AUTHORITY: fixed by the frozen launch contract, so a "
        "changed launch flag is a rejection rather than a silent difference"
    ),
    "interpreter_identity": (
        "IN_PROJECTION_AUTHORITY: authority-bound; this is the field that makes "
        "an interpreter-identity mismatch a rejection"
    ),
    "loaded_project_modules": (
        "IN_PROJECTION_AUTHORITY: the count of certified project modules the "
        "worker actually imported; source drift changes it"
    ),
    "one_request_one_process": (
        "IN_PROJECTION_AUTHORITY: the preserved one-shot declaration"
    ),
    "operation": "IN_PROJECTION_AUTHORITY: echoed from the recorded request",
    "post_execution_source_verification": (
        "IN_PROJECTION_AUTHORITY: the preserved post-execution source verdict"
    ),
    "project_source_manifest_digest": (
        "IN_PROJECTION_AUTHORITY: authority-bound; certified worker source "
        "drift changes it"
    ),
    "project_source_manifest_role": (
        "IN_PROJECTION_AUTHORITY: authority-bound frozen constant"
    ),
    "request_digest": (
        "IN_PROJECTION_AUTHORITY: the digest of the exact canonical request "
        "bytes the worker received, so it is a pure function of those bytes"
    ),
    "request_schema_version": (
        "IN_PROJECTION_AUTHORITY: echoed from the recorded request"
    ),
    "response_schema_version": (
        "IN_PROJECTION_AUTHORITY: frozen worker protocol constant"
    ),
    "result": (
        "IN_PROJECTION_AUTHORITY: the full scientific result. The projection "
        "carries the whole result object, not a summary of it"
    ),
    "result_digest": (
        "IN_PROJECTION_AUTHORITY: the digest the worker bound to its result"
    ),
    "status": "IN_PROJECTION_AUTHORITY: the worker's SUCCESS or REFUSED verdict",
    "sys_path_digest": (
        "IN_PROJECTION_AUTHORITY: a digest of the recorded request's sys_path, "
        "so it is a pure function of the request bytes"
    ),
    "third_party_authority_digest": (
        "IN_PROJECTION_AUTHORITY: authority-bound frozen reviewed registry digest"
    ),
    "third_party_installed_content_verification": (
        "IN_PROJECTION_AUTHORITY: the preserved Repair D verdict"
    ),
    "third_party_observed_content_manifest_digest": (
        "IN_PROJECTION_AUTHORITY: measured from the installed third-party "
        "content. It is environment-derived, which is exactly why it is "
        "projected: installed-content drift then rejects instead of passing"
    ),
    "trusted_persistence_authority_sha256": (
        "IN_PROJECTION_AUTHORITY: authority-bound certified trusted-persistence "
        "hash"
    ),
    "worker_authority_sha256": (
        "IN_PROJECTION_AUTHORITY: authority-bound proof-architecture identity"
    ),
    "worker_authority_ticket": (
        "IN_PROJECTION_AUTHORITY: authority-bound frozen worker protocol ticket"
    ),
    "worker_authority_version": (
        "IN_PROJECTION_AUTHORITY: authority-bound frozen constant"
    ),
    "worker_bootstrap_manifest_digest": (
        "IN_PROJECTION_AUTHORITY: authority-bound; any bootstrap source drift "
        "changes it"
    ),
    "worker_entrypoint_module": (
        "IN_PROJECTION_AUTHORITY: authority-bound frozen constant"
    ),
}

PROJECTION_IS_A_CLOSED_INCLUSION_LIST = True
PROJECTION_IS_DEFINED_BY_EXCLUSION = False

#: The three fields the ticket requires the projection to carry explicitly.
#: Named separately so the audit can check them by name.
PROJECTION_MANDATORY_MEMBERS: tuple[str, ...] = (
    "result",
    "result_digest",
    *protocol.AUTHORITY_BOUND_RESPONSE_FIELDS,
)


def comparison_projection(response: Mapping[str, Any]) -> dict[str, Any]:
    """Project a response onto the frozen closed inclusion list.

    Built by explicit inclusion.  A field that is in the response but not in
    the frozen list is not carried, and a field that is in the frozen list but
    missing from the response refuses rather than being silently dropped: a
    missing projected field would otherwise make two different responses
    compare equal.
    """

    if not isinstance(response, Mapping):
        raise ReplayVerifiedEvidenceError(
            "a comparison projection requires a response mapping, not "
            f"{type(response).__name__}"
        )
    projected: dict[str, Any] = {}
    for name in IN_PROJECTION_AUTHORITY_FIELDS:
        if name not in response:
            raise ReplayVerifiedEvidenceError(
                f"the response does not carry projected field {name!r}"
            )
        projected[name] = response[name]
    return projected


def projection_bytes(response: Mapping[str, Any]) -> bytes:
    """The canonical bytes the byte-for-byte comparison is performed on."""

    return protocol.canonical_json_bytes(comparison_projection(response))


def projection_digest(response: Mapping[str, Any]) -> str:
    return protocol.digest_bytes(projection_bytes(response))


# ---------------------------------------------------------------------------
# Environment-local request fields
# ---------------------------------------------------------------------------

#: Request fields whose value names something about the machine and checkout
#: the producer ran on rather than something about the science.
ENVIRONMENT_LOCAL_REQUEST_FIELDS: tuple[str, ...] = (
    "project_root",
    "sys_path",
    "third_party_environment",
)

#: The chosen rule, of the two the ticket permits.  Verification happens in the
#: recorded environment; no canonical relocation rule is frozen.
#:
#: Why this and not relocation: a relocation rule is a second canonicalisation
#: of authority-bearing bytes, and this lineage has already been failed once for
#: letting a second notion of canonical form exist. Relocation is also one edit
#: away from rewriting request bytes, which is forbidden outright. Requiring the
#: recorded environment introduces no new trust root, because the environment is
#: already pinned by three mechanisms that passed review — the frozen
#: interpreter identity, the certified project source manifest and the
#: third-party installed-content authority — and all three are inside the
#: comparison projection. The cost is availability, never integrity: evidence
#: produced elsewhere is *rejected* with a named reason code rather than
#: silently adapted.
ENVIRONMENT_BINDING_RULE = "VERIFY_IN_THE_RECORDED_ENVIRONMENT"
ENVIRONMENT_RELOCATION_RULE = "NONE_FROZEN"
REQUEST_BYTES_MAY_BE_REWRITTEN = False


# ---------------------------------------------------------------------------
# Frozen trusted authority context
# ---------------------------------------------------------------------------

#: The self-contained identity of this proof architecture.  It is a digest over
#: frozen architecture material that does not contain the digest itself, so it
#: is computable by the verifier without reading any namespace artifact and
#: without the circularity a parent-hash self-reference would create.
REPLAY_VERIFIED_EVIDENCE_ARCHITECTURE: Mapping[str, Any] = {
    "authority_bound_request_fields": list(
        protocol.AUTHORITY_BOUND_REQUEST_FIELDS
    ),
    "authority_bound_response_fields": list(
        protocol.AUTHORITY_BOUND_RESPONSE_FIELDS
    ),
    "comparison_projection_version": COMPARISON_PROJECTION_VERSION,
    "decision_version": DECISION_VERSION,
    "environment_binding_rule": ENVIRONMENT_BINDING_RULE,
    "environment_local_request_fields": list(ENVIRONMENT_LOCAL_REQUEST_FIELDS),
    "evidence_item_layout_version": EVIDENCE_ITEM_LAYOUT_VERSION,
    "in_projection_authority_fields": list(IN_PROJECTION_AUTHORITY_FIELDS),
    "invariant": REPLAY_VERIFIED_EVIDENCE_INVARIANT,
    "program_ticket": PROGRAM_TICKET,
    "request_fields": sorted(protocol.REQUEST_FIELDS),
    "response_fields": sorted(protocol.RESPONSE_FIELDS),
    "run_local_fields": list(RUN_LOCAL_FIELDS),
    "worker_bootstrap_relative_paths": list(
        protocol.WORKER_BOOTSTRAP_RELATIVE_PATHS
    ),
    "worker_entrypoint_module": protocol.WORKER_ENTRYPOINT_MODULE,
}

REPLAY_VERIFIED_EVIDENCE_ARCHITECTURE_SHA256 = protocol.digest_payload(
    REPLAY_VERIFIED_EVIDENCE_ARCHITECTURE
)

#: The certified ETF publication calendar authority the worker universe is
#: bound to, unchanged from the preserved lineage.
FROZEN_CALENDAR_AUTHORITY_VERSION = "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1"
FROZEN_CALENDAR_AUTHORITY_SHA256 = (
    "901f572e03781030906cd6fe72a73ec5804f9ffbdefe6a8a944c067f7fd9853f"
)

#: The certified trusted-acquisition persistence authority.  It is CLOSED and is
#: not reopened by this ticket.
CERTIFIED_TRUSTED_PERSISTENCE_SHA256 = (
    "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
)

#: The preserved certified worker source universe and its role.
FROZEN_PROJECT_SOURCE_MANIFEST_DIGEST = (
    "7ffbf15792d33e0cd387eb995d8d733c1fa1b98b2859153957c670f796a44e8e"
)
FROZEN_PROJECT_SOURCE_MANIFEST_ROLE = "PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE"
FROZEN_PROJECT_SOURCE_MODULE_COUNT = 120

#: The preserved four-file worker bootstrap source set digest.
FROZEN_WORKER_BOOTSTRAP_MANIFEST_DIGEST = (
    "1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411"
)
FROZEN_WORKER_BOOTSTRAP_SOURCE_COUNT = 4

#: The preserved exact reviewed third-party semantic and installed-content
#: authority.
FROZEN_THIRD_PARTY_AUTHORITY_DIGEST = (
    "23e4f1d89a503b43fc39ee0ae3516b742f6db72028224d78a9181be6726298a6"
)

#: The complete frozen trusted authority context: the expected value of every
#: authority-bound request and response field.  The verifier compares against
#: *these* and never adopts a value from the request it is verifying, which is
#: what makes an altered authority-bound request field a rejection rather than
#: a self-consistent lie.
FROZEN_EXPECTED_AUTHORITY: Mapping[str, Any] = {
    "calendar_authority_sha256": FROZEN_CALENDAR_AUTHORITY_SHA256,
    "calendar_authority_version": FROZEN_CALENDAR_AUTHORITY_VERSION,
    "interpreter_identity": dict(protocol.PROOF_INTERPRETER_IDENTITY),
    "project_source_manifest_digest": FROZEN_PROJECT_SOURCE_MANIFEST_DIGEST,
    "project_source_manifest_role": FROZEN_PROJECT_SOURCE_MANIFEST_ROLE,
    "third_party_authority_digest": FROZEN_THIRD_PARTY_AUTHORITY_DIGEST,
    "trusted_persistence_authority_sha256": CERTIFIED_TRUSTED_PERSISTENCE_SHA256,
    "worker_authority_sha256": REPLAY_VERIFIED_EVIDENCE_ARCHITECTURE_SHA256,
    "worker_authority_ticket": protocol.WORKER_AUTHORITY_TICKET,
    "worker_authority_version": protocol.WORKER_AUTHORITY_VERSION,
    "worker_bootstrap_manifest_digest": FROZEN_WORKER_BOOTSTRAP_MANIFEST_DIGEST,
    "worker_entrypoint_module": protocol.WORKER_ENTRYPOINT_MODULE,
}


def expected_authority_drift(
    payload: Mapping[str, Any], fields: Sequence[str]
) -> tuple[str, ...]:
    """Names of the given fields whose value is not the frozen trusted one.

    A pure comparison against frozen material.  It admits nothing, it creates
    nothing, and it never reads an expected value out of ``payload``.
    """

    drifted: list[str] = []
    for name in sorted(fields):
        if name not in FROZEN_EXPECTED_AUTHORITY:
            raise ReplayVerifiedEvidenceError(
                f"{name!r} is not a frozen authority-bound field"
            )
        if payload.get(name) != FROZEN_EXPECTED_AUTHORITY[name]:
            drifted.append(name)
    return tuple(drifted)


# ---------------------------------------------------------------------------
# Verification record contract
# ---------------------------------------------------------------------------

VERIFICATION_RECORD_SCHEMA_VERSION = (
    "ETF_CALENDAR_EVIDENCE_VERIFICATION_RECORD_V1"
)

ACCEPTED = "ACCEPTED"
REJECTED = "REJECTED"
VERDICTS: tuple[str, ...] = (ACCEPTED, REJECTED)

#: The closed set of reason codes a record may carry.  A rejection is always
#: recorded with one of these; rejections are never dropped.
ACCEPTED_REASON = "ACCEPTED_BYTE_IDENTICAL_REDERIVATION"

REJECTION_REASONS: tuple[str, ...] = (
    "REJECTED_ENVELOPE_PAYLOAD_IS_NOT_A_RECORDED_EVIDENCE_RECORD",
    "REJECTED_EVIDENCE_ITEM_LAYOUT_INVALID",
    "REJECTED_EVIDENCE_RECORD_HAS_NO_VERIFIED_ENVELOPE",
    "REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED",
    "REJECTED_INTERPRETER_IDENTITY_MISMATCH",
    "REJECTED_NOT_THE_RECORDED_ENVIRONMENT",
    "REJECTED_PROJECTION_IS_NOT_BYTE_IDENTICAL",
    "REJECTED_RECORDED_REQUEST_AUTHORITY_MISMATCH",
    "REJECTED_RECORDED_REQUEST_IS_NOT_CANONICAL",
    "REJECTED_RECORDED_REQUEST_SCHEMA_INVALID",
    "REJECTED_RECORDED_RESPONSE_AUTHORITY_MISMATCH",
    "REJECTED_RECORDED_RESPONSE_DOES_NOT_BIND_THE_RECORDED_REQUEST",
    "REJECTED_RECORDED_RESPONSE_IS_NOT_A_SUCCESS",
    "REJECTED_RECORDED_RESPONSE_IS_NOT_CANONICAL",
    "REJECTED_RECORDED_RESPONSE_RESULT_DIGEST_MISMATCH",
    "REJECTED_RECORDED_RESPONSE_SCHEMA_INVALID",
    "REJECTED_REDERIVED_RESPONSE_IS_NOT_A_SUCCESS",
    "REJECTED_REDERIVED_RESPONSE_IS_NOT_CANONICAL",
    "REJECTED_REDERIVED_RESPONSE_SCHEMA_INVALID",
    "REJECTED_TEST_KEY_ENVELOPE_IN_PRODUCTION_MODE",
    "REJECTED_WORKER_BOOTSTRAP_SOURCE_DRIFT",
    "REJECTED_WORKER_EXECUTION_FAILED",
)

VERIFICATION_REASON_CODES: tuple[str, ...] = (ACCEPTED_REASON, *REJECTION_REASONS)

#: Exactly what a verification record carries.  There is deliberately no
#: timestamp, no duration, no path, no process identifier and no address in it:
#: verifying the same evidence twice has to produce byte-identical records, and
#: a record that carried any of those could not.
VERIFICATION_RECORD_FIELDS: tuple[str, ...] = (
    "evidence_item_id",
    "input_envelope_count",
    "input_envelope_digests",
    "interpreter_identity",
    "reason_code",
    "reason_detail",
    "recorded_projection_digest",
    "rederived_projection_digest",
    "record_schema_version",
    "request_digest",
    "response_digest",
    "verdict",
    "verifier_commit",
    "verifier_mode",
    "verifier_source_manifest_digest",
    "verifier_source_module_count",
)


def verification_record(
    *,
    evidence_item_id: str,
    verdict: str,
    reason_code: str,
    reason_detail: str,
    request_digest: str | None,
    response_digest: str | None,
    recorded_projection_digest: str | None,
    rederived_projection_digest: str | None,
    input_envelope_count: int,
    input_envelope_digests: Sequence[str],
    verifier_source_manifest_digest: str,
    verifier_source_module_count: int,
    verifier_commit: str,
    verifier_mode: str,
    interpreter_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Assemble one canonical, digest-bound verification record."""

    if verdict not in VERDICTS:
        raise ReplayVerifiedEvidenceError(f"unknown verification verdict {verdict!r}")
    if reason_code not in VERIFICATION_REASON_CODES:
        raise ReplayVerifiedEvidenceError(f"unknown reason code {reason_code!r}")
    if (verdict == ACCEPTED) != (reason_code == ACCEPTED_REASON):
        raise ReplayVerifiedEvidenceError(
            "the acceptance verdict and the acceptance reason code must agree"
        )
    if verifier_mode not in VERIFIER_MODES:
        raise ReplayVerifiedEvidenceError(f"unknown verifier mode {verifier_mode!r}")
    record = {
        "evidence_item_id": evidence_item_id,
        "input_envelope_count": input_envelope_count,
        "input_envelope_digests": list(input_envelope_digests),
        "interpreter_identity": dict(interpreter_identity),
        "reason_code": reason_code,
        "reason_detail": reason_detail,
        "recorded_projection_digest": recorded_projection_digest,
        "rederived_projection_digest": rederived_projection_digest,
        "record_schema_version": VERIFICATION_RECORD_SCHEMA_VERSION,
        "request_digest": request_digest,
        "response_digest": response_digest,
        "verdict": verdict,
        "verifier_commit": verifier_commit,
        "verifier_mode": verifier_mode,
        "verifier_source_manifest_digest": verifier_source_manifest_digest,
        "verifier_source_module_count": verifier_source_module_count,
    }
    if sorted(record) != sorted(VERIFICATION_RECORD_FIELDS):
        raise ReplayVerifiedEvidenceError(
            "a verification record must be exactly the frozen record field set"
        )
    record["record_sha256"] = protocol.digest_payload(record)
    return record


def verify_record_digest(record: Mapping[str, Any]) -> None:
    """A persisted record must reproduce its own bound digest."""

    row = dict(record)
    declared = row.pop("record_sha256", None)
    if not isinstance(declared, str) or protocol.digest_payload(row) != declared:
        raise ReplayVerifiedEvidenceError("record_sha256 does not recompute")


# ---------------------------------------------------------------------------
# Consumer admission rule
# ---------------------------------------------------------------------------

CONSUMER_ADMISSION_RULE_VERSION = (
    "ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_CONSUMER_ADMISSION_V1"
)

#: The owners that may never treat ETF calendar evidence as scientific without
#: an accepting verifier record.  ``PAD5`` freezes the rule; wiring each
#: consumer belongs to that consumer's own ticket.
BOUND_CONSUMERS: tuple[str, ...] = (
    "POSTP1-001V2A-I2",
    "POSTP1-001V2R1",
    "POSTP1-003R3_SUFFICIENCY_GOVERNANCE",
    "PROSPECTIVE_COLLECTION",
    "STAGE_B_EVALUATION",
)

CONSUMER_ADMISSION_RULE = (
    "NO_BOUND_CONSUMER_MAY_TREAT_ETF_CALENDAR_EVIDENCE_AS_SCIENTIFIC_UNLESS_A_"
    "PRODUCTION_MODE_VERIFICATION_RECORD_WITH_VERDICT_ACCEPTED_AND_REASON_CODE_"
    "ACCEPTED_BYTE_IDENTICAL_REDERIVATION_EXISTS_FOR_THE_EXACT_REQUEST_AND_"
    "RESPONSE_DIGESTS_IT_CONSUMES"
)


def admits(record: Mapping[str, Any]) -> bool:
    """The whole consumer admission test, as one total function.

    A record admits only when it is a well-formed record that reproduces its
    own digest, was written in production mode, accepted, and carries the
    acceptance reason code.  Everything else — including every rejection —
    returns ``False`` rather than raising, so a consumer cannot accidentally
    treat an error path as admission.
    """

    try:
        verify_record_digest(record)
    except ReplayVerifiedEvidenceError:
        return False
    return (
        record.get("record_schema_version") == VERIFICATION_RECORD_SCHEMA_VERSION
        and record.get("verifier_mode") == PRODUCTION_MODE
        and record.get("verdict") == ACCEPTED
        and record.get("reason_code") == ACCEPTED_REASON
    )


# ---------------------------------------------------------------------------
# The single process-creation site
# ---------------------------------------------------------------------------

#: The preserved launch contract, reused rather than redefined.
LAUNCH_FLAGS: tuple[str, ...] = ("-I", "-S", "-B")
LAUNCH_X_OPTION = "pycache_prefix"
LAUNCH_MECHANISM = "EXEC_FRESH_INTERPRETER"
FROZEN_PROCESS_ENVIRONMENT: Mapping[str, str] = {
    "LC_ALL": "C",
    "LANG": "C",
    "TZ": "UTC",
}

VERIFIER_ENTRY_MODULE = "btc_predictor.research.etf_calendar_evidence_verifier"
VERIFIER_ENTRY_RELATIVE_PATH = (
    "btc_predictor/research/etf_calendar_evidence_verifier.py"
)
CONTRACT_MODULE = "btc_predictor.research.etf_calendar_replay_verified_evidence_contract"
CONTRACT_RELATIVE_PATH = (
    "btc_predictor/research/etf_calendar_replay_verified_evidence_contract.py"
)
PRODUCER_MODULE = "btc_predictor.research.etf_calendar_replay_verified_evidence"
PRODUCER_RELATIVE_PATH = (
    "btc_predictor/research/etf_calendar_replay_verified_evidence.py"
)

#: The verifier's whole interface, as command-line strings.  Every element is a
#: path, a JSON array of directory paths, or one of two frozen mode literals.
#: None of them can carry a callback, a plugin, a pickle, a class, a module or
#: any caller object, because the interface has no channel that transports one:
#: the process boundary refuses everything that is not bytes, and the only bytes
#: it accepts are these five arguments and the canonical JSON files they name.
VERIFIER_ARGUMENT_NAMES: tuple[str, ...] = (
    "sys_path_json",
    "pycache_namespace",
    "evidence_dir",
    "record_dir",
    "mode",
)

#: Names that would make the verifier able to execute caller-supplied material.
#: The mechanical interface audit proves none of them occurs in the verifier's
#: source or in this contract.
FORBIDDEN_VERIFIER_NAMES: tuple[str, ...] = (
    "__import__",
    "cloudpickle",
    "compile",
    "dill",
    "eval",
    "exec",
    "importlib",
    "marshal",
    "pickle",
    "runpy",
    "shelve",
    "yaml",
)


# ---------------------------------------------------------------------------
# Mechanical verifier source-closure derivation
# ---------------------------------------------------------------------------

#: The seed of the verifier's import closure.  The closure is *derived*, never
#: listed: a hand-written list would go stale the moment an import moved, and a
#: stale list is exactly how uncertified code gets into a process that claims
#: to run only certified code.
VERIFIER_CLOSURE_SEEDS: tuple[str, ...] = (VERIFIER_ENTRY_MODULE,)

VERIFIER_SOURCE_MANIFEST_VERSION = (
    "ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_VERIFIER_SOURCE_MANIFEST_V1"
)


def declared_imports(source: str, module: str, is_package: bool) -> tuple[str, ...]:
    """Every module name this source declares an import of, dotted and absolute.

    The rule is the one the reviewed bootstrap-set derivation uses: static
    import declarations anywhere in the file, **including declarations nested
    inside functions and classes**, with relative imports resolved against the
    declaring module.  Nested declarations count because the worker entrypoint
    deliberately imports inside ``main`` and those imports still execute.
    """

    package = module if is_package else module.rpartition(".")[0]
    found: set[str] = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                parts = package.split(".") if package else []
                base = ".".join(parts[: len(parts) - node.level + 1])
                root = f"{base}.{node.module}" if node.module else base
            elif node.module:
                root = node.module
            else:  # pragma: no cover - unreachable for absolute imports
                continue
            if not root:
                continue
            found.add(root)
            for alias in node.names:
                found.add(f"{root}.{alias.name}")
    return tuple(sorted(found))


def _module_source_path(project_root: Path, dotted: str) -> tuple[str, Path] | None:
    """Locate a certified project module's source file, module or package."""

    if protocol.certified_root(dotted) is None:
        return None
    for relative in (
        protocol.module_relative_path(dotted),
        protocol.package_relative_path(dotted),
    ):
        candidate = Path(project_root) / relative
        if candidate.is_file():
            return relative, candidate
    return None


def derive_source_closure(
    project_root: Path,
    seeds: Sequence[str] = VERIFIER_CLOSURE_SEEDS,
) -> tuple[tuple[protocol.ProjectSourceEntry, ...], tuple[str, ...]]:
    """Derive a transitive certified-source import closure and what it could not resolve.

    Same rule, same two certified package roots and same ancestor-package
    completion as the reviewed derivation that produced the worker bootstrap
    set and the 120-module worker source universe.  The ``PAD5`` suite asserts
    that the entries this returns agree exactly with that reviewed derivation on
    the same seeds, so the two cannot drift apart silently.

    The second element is the part the reviewed derivation drops on the floor:
    module names under a certified package root that the verifier declares an
    import of but that have no source file here.  Dropping them silently would
    be a real hole — an import outside the closure would be reachable at run
    time and invisible to the audit — so they are returned and the audit treats
    any of them as a finding.  A module that genuinely does not exist would
    raise ``ImportError`` in the verifier process, which is a refusal rather
    than a silent success, but "the audit cannot see it" is not a property this
    architecture is willing to have.
    """

    resolved: dict[str, str] = {}
    unresolved: set[str] = set()
    pending = list(seeds)
    while pending:
        dotted = pending.pop()
        if dotted in resolved:
            continue
        located = _module_source_path(Path(project_root), dotted)
        if located is None:
            if protocol.certified_root(dotted) is not None:
                unresolved.add(dotted)
            continue
        relative, path = located
        resolved[dotted] = relative
        parts = dotted.split(".")
        pending.extend(".".join(parts[:index]) for index in range(1, len(parts)))
        source = path.read_text(encoding="utf-8")
        for declared in declared_imports(
            source, dotted, relative.endswith("/__init__.py")
        ):
            if (
                protocol.certified_root(declared) is not None
                and declared not in resolved
            ):
                pending.append(declared)
    entries = [
        protocol.ProjectSourceEntry(
            module=dotted,
            path=relative,
            sha256=protocol.file_sha256(Path(project_root) / relative),
        )
        for dotted, relative in resolved.items()
    ]
    # ``from pkg import name`` declares both ``pkg`` and ``pkg.name``.  When
    # ``name`` is an ordinary attribute rather than a submodule there is no file
    # for it and that is not a hole.  The discrimination is exact rather than
    # heuristic: a submodule can only live under a *package*, and an attribute
    # must be bound at module level in that package's initializer.  Anything
    # else — a name under a package that the package does not define and that
    # has no source file — is a declared import the audit could not account for,
    # and is reported.
    reportable: list[str] = []
    for name in sorted(unresolved):
        parent, _, attribute = name.rpartition(".")
        parent_relative = resolved.get(parent)
        if parent_relative is None or not parent_relative.endswith("/__init__.py"):
            continue
        initializer = (Path(project_root) / parent_relative).read_text(
            encoding="utf-8"
        )
        if attribute not in _module_level_bindings(initializer):
            reportable.append(name)
    return tuple(sorted(entries)), tuple(reportable)


def _module_level_bindings(source: str) -> frozenset[str]:
    """Every name a module binds at its own top level."""

    bound: set[str] = set()
    for node in ast.parse(source).body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    bound.add(target.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            bound.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            for alias in node.names:
                bound.add(alias.asname or alias.name.partition(".")[0])
    return frozenset(bound)


def derive_source_manifest(
    project_root: Path,
    seeds: Sequence[str] = VERIFIER_CLOSURE_SEEDS,
) -> tuple[protocol.ProjectSourceEntry, ...]:
    """The entries of :func:`derive_source_closure`, for runtime self-recording."""

    return derive_source_closure(project_root, seeds)[0]


def external_import_roots(
    project_root: Path,
    entries: Sequence[protocol.ProjectSourceEntry],
) -> tuple[str, ...]:
    """The non-stdlib top-level modules a derived closure imports."""

    roots: set[str] = set()
    for entry in entries:
        source = (Path(project_root) / entry.path).read_text(encoding="utf-8")
        for declared in declared_imports(
            source, entry.module, entry.path.endswith("/__init__.py")
        ):
            root, _, _ = declared.partition(".")
            if (
                root
                and root not in protocol.CERTIFIED_PACKAGE_ROOTS
                and root != "__future__"
                and root not in sys.stdlib_module_names
            ):
                roots.add(root)
    return tuple(sorted(roots))


def verifier_source_manifest_digest(
    entries: Sequence[protocol.ProjectSourceEntry],
) -> str:
    return protocol.manifest_digest(entries)


def resolve_commit(project_root: Path) -> str:
    """Read the checked-out commit from the git metadata files directly.

    Deliberately not a ``git`` subprocess: the verifier owns no second process
    creation site, and reading two small files needs none.  An unavailable or
    unreadable commit is reported as such rather than guessed, because a
    fabricated commit in a verification record would be worse than an absent
    one.  The commit is audit metadata: authority is the reviewed commit the
    verifier's source actually is, not the string it prints.
    """

    git_dir = Path(project_root) / ".git"
    head = git_dir / "HEAD"
    try:
        raw = head.read_text(encoding="utf-8").strip()
    except OSError:
        return "COMMIT_UNAVAILABLE"
    if not raw.startswith("ref: "):
        return raw if len(raw) == 40 else "COMMIT_UNAVAILABLE"
    reference = raw[len("ref: ") :].strip()
    loose = git_dir / reference
    try:
        return loose.read_text(encoding="utf-8").strip()
    except OSError:
        pass
    try:
        packed = (git_dir / "packed-refs").read_text(encoding="utf-8")
    except OSError:
        return "COMMIT_UNAVAILABLE"
    for line in packed.splitlines():
        if line.startswith("#") or line.startswith("^"):
            continue
        sha, _, name = line.partition(" ")
        if name.strip() == reference:
            return sha.strip()
    return "COMMIT_UNAVAILABLE"


def worker_argv(
    *,
    executable: str,
    entrypoint: Path | str,
    sys_path: Sequence[str],
    pycache_namespace: Path | str,
) -> tuple[str, ...]:
    """The preserved worker launch argv, rebuilt from the recorded material."""

    namespace = Path(pycache_namespace).resolve()
    return (
        str(executable),
        *LAUNCH_FLAGS,
        "-X",
        f"{LAUNCH_X_OPTION}={namespace}",
        str(entrypoint),
        json.dumps(list(sys_path)),
        str(namespace),
    )


def verifier_argv(
    *,
    executable: str,
    verifier_entry: Path | str,
    sys_path: Sequence[str],
    pycache_namespace: Path | str,
    evidence_dir: Path | str,
    record_dir: Path | str,
    mode: str,
) -> tuple[str, ...]:
    """The verifier launch argv: an isolated interpreter and five strings."""

    if mode not in VERIFIER_MODES:
        raise ReplayVerifiedEvidenceError(f"unknown verifier mode {mode!r}")
    namespace = Path(pycache_namespace).resolve()
    return (
        str(executable),
        *LAUNCH_FLAGS,
        "-X",
        f"{LAUNCH_X_OPTION}={namespace}",
        str(verifier_entry),
        json.dumps(list(sys_path)),
        str(namespace),
        str(Path(evidence_dir).resolve()),
        str(Path(record_dir).resolve()),
        mode,
    )


def spawn_isolated_process(
    argv: Sequence[str],
    *,
    stdin_bytes: bytes = b"",
    cwd: Path | str,
    timeout_seconds: int = protocol.DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """The one process-creation site in the whole ``PAD5`` surface.

    The verifier uses it to re-execute the certified worker, and the harness
    that starts a verifier uses the same function.  Keeping it single means the
    frozen direct-launch census has exactly one site to justify, and it means a
    second spawn cannot be added anywhere without the census moving.

    The environment is the frozen one, never the caller's, and the interpreter
    is always started in isolated mode with no site initialisation and no
    bytecode writes.
    """

    completed_env = dict(FROZEN_PROCESS_ENVIRONMENT)
    try:
        completed = subprocess.run(
            list(argv),
            input=stdin_bytes,
            capture_output=True,
            cwd=str(cwd),
            env=completed_env,
            timeout=timeout_seconds,
            close_fds=True,
        )
    except subprocess.TimeoutExpired as expired:
        return {
            "exit_status": None,
            "timed_out": True,
            "stdout": expired.stdout or b"",
            "stderr": expired.stderr or b"",
        }
    return {
        "exit_status": completed.returncode,
        "timed_out": False,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
