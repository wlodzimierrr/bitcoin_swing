"""``ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1`` — producer, audits and namespace.

``POSTP1-002V2A-PAD4-R5`` failed the ``PAD4`` lineage for the fourth time in one
family.  R2 fabricated, R3 mutated, R4 impersonated, and R5 — having closed
impersonation — was defeated by ordinary ``gc`` object-graph traversal that
recovered the closure-owned registry and inserted an entry for a caller-created
object.  The recorded escalation decision
``DECIDE_ETF_CALENDAR_PROOF_ARCHITECTURE_AFTER_PAD4_R5_V1`` diagnosed the shared
root cause — *any object reachable in a CPython process can be enumerated and
mutated by other code in the same process* — refused to widen the domain, and
selected a different family.

This module is the **non-authoritative producer** side of that family, plus the
mechanical audits and the frozen namespace.  It is deliberately *not* authority
and it deliberately holds no authority marker.  The process it runs in is fully
untrusted at the Python level: ``gc``, class mutation, module mutation, closure
recovery, frames and ``ctypes`` are all permitted here and none of them can
matter, because nothing this module returns is authority.  Authority lives in
:mod:`btc_predictor.research.etf_calendar_evidence_verifier`, which runs as its
own isolated process over files.

What the producer does is narrow: it reuses the preserved ``PAD4-R5`` launch
path unchanged — ``run_isolated_scientific_request`` with its four-file
bootstrap pre-execution binding, fresh-exec isolation, fresh empty bytecode
namespace and Repairs A/B/C/D — and writes out the canonical request bytes, the
canonical response bytes and the signed input envelopes the request names.  It
never emits the ``R5`` affirmative evidence, and it never forks the worker, the
bootstrap set or the protocol.

The audits here compute their claims rather than assert them: that no
producer-side or verifier-side type carries an authority marker, that the
verifier's derived import closure is entirely hash-bound certified source with
no failed-lineage controller in it, that the verifier interface cannot transport
executable material, that the comparison projection is a closed inclusion list,
and that ``PAD5`` owns exactly one justified process-creation site with none
inside the 120-module certified worker universe.
"""

from __future__ import annotations

import argparse
import ast
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from btc_predictor.research import (
    etf_calendar_replay_verified_evidence_contract as contract,
)
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r5 as r5
from etf_calendar_worker import protocol_r2 as protocol


DECISION_VERSION = contract.DECISION_VERSION
PROGRAM_TICKET = contract.PROGRAM_TICKET
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_replay_verified_evidence_v1"
DEFINITION_FILENAME = "etf_calendar_replay_verified_evidence_v1_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
FINAL_CLASSIFICATION = (
    "ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1_READY_FOR_XHIGH_REVIEW"
)
REQUIRED_REVIEW = (
    "POSTP1-002V2A-PAD5 — INDEPENDENT EXACT-HASH xHIGH PROOF-ARCHITECTURE REVIEW"
)
PROOF_STRATEGY = (
    "AUTHORITY_BY_INDEPENDENT_BYTE_IDENTICAL_RE_DERIVATION_IN_A_STANDALONE_"
    "PROCESS_THAT_EXECUTES_ONLY_CERTIFIED_SOURCE__NO_IN_PROCESS_OBJECT_"
    "REGISTRY_CAPABILITY_CLOSURE_OR_TYPE_GATE_IS_AUTHORITY"
)

PROJECT_ROOT = r5.PROJECT_ROOT
CONTROLLER_RELATIVE_PATH = contract.PRODUCER_RELATIVE_PATH
VERIFIER_RELATIVE_PATH = contract.VERIFIER_ENTRY_RELATIVE_PATH
CONTRACT_RELATIVE_PATH = contract.CONTRACT_RELATIVE_PATH
RAW_REVIEW_HARNESS_RELATIVE_PATH = r5.RAW_REVIEW_HARNESS_RELATIVE_PATH

#: The failed ``PAD4-R5`` candidate this architecture replaces, and the
#: governance input that authorized replacing rather than correcting it.
FAILED_PAD4_R5_SHA256 = (
    "b4168dc9c757f3cdbdeed48e9a91cc35eb921728adb5d38d0d5b76fd2ef861c7"
)
FAILED_PAD4_R5_REVIEW = "POSTP1-002V2A-PAD4-R5"
FAILED_PAD4_R5_REVIEW_RESULT = (
    "COMPLETE / FAIL — CLOSURE-OWNED REGISTRY OBJECT-GRAPH BOUNDARY INVALID; "
    "SAME-FAMILY ESCALATION AUTOMATIC"
)
FAILED_PAD4_R5_EXECUTION_CLASSIFICATION = (
    "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R5_REQUIRES_NEW_PROOF_"
    "ARCHITECTURE_DECISION"
)
FAILED_PAD4_R5_IMPLEMENTATION_COMMIT = (
    "2d41fb13a411cd8a2a40efe2339b921116201d01"
)
ESCALATION_DECISION = "DECIDE_ETF_CALENDAR_PROOF_ARCHITECTURE_AFTER_PAD4_R5_V1"

#: Thirteen failed proof-architecture parents, extended with ``R5``.
FAILED_ARCHITECTURE_LINEAGE: tuple[str, ...] = (
    *r5.FAILED_ARCHITECTURE_LINEAGE,
    FAILED_PAD4_R5_SHA256,
)

#: The superseded, failed, non-certified controller modules, extended with the
#: ``R5`` controller.  None of them is ``PAD5`` authority, none of them is in
#: the verifier's import closure, and none of them is edited.
FAILED_LINEAGE_CONTROLLER_MODULES: tuple[str, ...] = (
    *r5.FAILED_LINEAGE_CONTROLLER_MODULES,
    r5.CONTROLLER_RELATIVE_PATH,
)

FAILED_CALENDAR_LINEAGE = r5.FAILED_CALENDAR_LINEAGE
FROZEN_REPLAY_OWNERS = r5.FROZEN_REPLAY_OWNERS
CERTIFIED_DEPENDENCY_SHA256 = r5.CERTIFIED_DEPENDENCY_SHA256

#: What the escalation decision retires as authority mechanisms.  Each was a
#: real mechanism in a real generation, and each is now kept only where it is a
#: producer convenience.
RETIRED_AUTHORITY_MECHANISMS = contract.RETIRED_AUTHORITY_MECHANISMS

#: The ``R5`` identity children.  They stay immutable in the ``R5`` namespace as
#: failed lineage and are **not** copied here as authority.
RETIRED_R5_IDENTITY_CHILDREN: tuple[str, ...] = (
    "affirmative_evidence_snapshot_rule",
    "authoritative_execution_identity_rule",
    "authoritative_return_state_rule",
    "authoritative_scientific_execution_boundary",
    "authority_receiver_validation_rule",
    "caller_visible_copy_isolation_rule",
    "canonical_admitted_snapshot_rule",
    "construction_identity_audit_rule",
    "identity_safe_snapshot_binding_rule",
    "result_digest_lifetime_binding_rule",
    "scientific_evidence_authority_rule",
)

#: Children whose semantics did not move and whose payloads assert nothing this
#: architecture contradicts.  They are bound from the reviewed ``R5`` builders
#: rather than restated, so they are byte-identical by construction rather than
#: by a claim.
CARRIED_FORWARD_CHILDREN: tuple[str, ...] = (
    "bootstrap_source_set",
    "bytecode_execution_binding_rule",
    "compiled_root_binding_witness_rule",
    "direct_body_dependency_rule",
    "dynamic_import_and_execution_prohibition",
    "pre_i2_project_source_manifest_fixture",
    "project_source_manifest_binding_rule",
    "proof_interpreter_identity",
    "replay_owner_graph_rule",
    "scientific_request_protocol",
    "scientific_response_protocol",
    "store_root_and_direct_use_grammar",
    "third_party_installed_content_attestation_rule",
    "third_party_semantic_authority",
    "worker_io_and_capability_boundary",
)

#: Children whose *subject* survives but whose reviewed payload asserts
#: in-process closure this architecture no longer claims.  Carrying those
#: byte-identically would publish a false statement, so each is re-issued under
#: a new contract version with the contradicted clauses corrected and the rest
#: preserved.  The named clauses are listed in each re-issued child.
REISSUED_CHILDREN: tuple[str, ...] = (
    "bootstrap_pre_execution_source_binding_rule",
    "replay_verified_admission_rule",
    "trusted_authority_context_rule",
    "trusted_process_and_isolation_boundary",
    "worker_launch_contract",
)

#: Children this architecture introduces.
NEW_CHILDREN: tuple[str, ...] = (
    "canonical_encoding_rule",
    "comparison_projection_definition",
    "consumer_admission_rule",
    "evidence_item_layout_rule",
    "non_authoritative_producer_rule",
    "proof_order_and_completeness_definition",
    "replay_verified_evidence_boundary",
    "science_lineage_and_safety",
    "verification_record_contract",
    "verifier_interface_boundary",
    "verifier_source_manifest",
)

PRESERVED_VALID_PORTIONS: tuple[str, ...] = tuple(
    sorted(
        {
            "BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING",
            "BYTECODE_EXECUTION_BINDING_REPAIR_A",
            "CANONICAL_WORKER_REQUEST_AND_RESPONSE_BYTES",
            "CERTIFIED_PROJECT_SOURCE_MANIFEST_AUTHORITY_REPAIR_B",
            "CERTIFIED_TRUSTED_ACQUISITION_PERSISTENCE_NOT_REOPENED",
            "CLOSED_AST_STORE_USE_GRAMMAR",
            "COMPILED_ROOT_BINDING_WITNESS",
            "DIRECT_BODY_DEPENDENCY_RULE",
            "ELEVEN_OWNER_REPLAY_GRAPH",
            "FRESH_EXEC_PROCESS_ISOLATION",
            "FROZEN_PROOF_INTERPRETER_IDENTITY",
            "ONE_SHOT_WORKER_LAUNCH_CONTRACT",
            "THIRD_PARTY_INSTALLED_CONTENT_AUTHORITY_REPAIR_D",
            "TRUSTED_EXPECTED_VALUE_AUTHORITY_CONTEXT_REPAIR_C",
            "WORKER_IO_AND_CAPABILITY_BOUNDARY",
        }
    )
)

#: Explicitly not reopened by this ticket.
NOT_REOPENED: tuple[str, ...] = tuple(
    sorted(
        {
            "CERTIFIED_TRUSTED_ACQUISITION_PERSISTENCE_AUTHORITY",
            "ETF_CALENDAR_SCIENCE",
            "WORKER_BOOTSTRAP_SOURCE_SET",
            "WORKER_PROTOCOL",
            "WORKER_SOURCE_UNIVERSE",
        }
    )
)


class ReplayVerifiedEvidenceDecisionError(ValueError):
    """Raised when the replay-verified evidence decision must refuse."""


def _definition(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Bind a payload to its own canonical digest.

    The canonicalisation is the already reviewed worker-protocol one, reused
    rather than reinvented: a second competing notion of canonical JSON would
    be a second authority, and this lineage has been failed once for exactly
    that shape.
    """

    result = dict(payload)
    result["definition_sha256"] = protocol.digest_payload(result)
    return result


def _verify_definition_digest(payload: Mapping[str, Any]) -> None:
    row = dict(payload)
    declared = row.pop("definition_sha256", None)
    if (
        not isinstance(declared, str)
        or len(declared) != 64
        or protocol.digest_payload(row) != declared
    ):
        raise ReplayVerifiedEvidenceDecisionError(
            "definition_sha256 does not recompute"
        )


def _module_source(relative: str, project_root: Path = PROJECT_ROOT) -> str:
    target = Path(project_root) / relative
    if not target.is_file():
        raise ReplayVerifiedEvidenceDecisionError(
            f"the mechanical audit cannot read {relative}"
        )
    return target.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# The non-authoritative producer
# ---------------------------------------------------------------------------

#: The producer's whole output vocabulary.  There is no affirmative marker in
#: it, because this architecture has no producer-side authority to affirm.
PRODUCER_OUTPUT_AUTHORITY = contract.PRODUCER_OUTPUT_AUTHORITY


def produce_evidence_item(
    item_dir: Path,
    *,
    authority_context: Any,
    scientific_request: Mapping[str, Any],
    launch_material: Any,
    input_envelopes: Sequence[Mapping[str, Any]],
    pycache_namespace: Path | None = None,
    test_trust_root: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Produce one candidate evidence item as files.  Nothing here is authority.

    The preserved ``PAD4-R5`` launch path is reused unchanged, so the bootstrap
    pre-execution binding, fresh-exec isolation, fresh empty bytecode namespace
    and Repairs A/B/C/D all still hold for the execution that produces the
    candidate bytes.  What this function then writes out is only the canonical
    request bytes, the canonical response bytes and the signed envelopes the
    request names.

    The ``R5`` affirmative evidence is deliberately **not** written.  It carries
    a retired authority marker, and a candidate evidence item that carried one
    would be claiming exactly the thing this architecture removed.

    The item manifest is labelled ``NON_AUTHORITATIVE_CANDIDATE_EVIDENCE``.  The
    verifier never reads that label to decide anything; it is there so a human
    reading the artifact cannot mistake it for a verdict.
    """

    execution = r5.run_isolated_scientific_request(
        authority_context,
        scientific_request,
        launch_material,
        pycache_namespace=pycache_namespace,
    )
    response = execution.response
    return write_evidence_item(
        item_dir,
        scientific_request=scientific_request,
        response=response,
        input_envelopes=input_envelopes,
        test_trust_root=test_trust_root,
    )


def write_evidence_item(
    item_dir: Path,
    *,
    scientific_request: Mapping[str, Any],
    response: Mapping[str, Any] | None,
    input_envelopes: Sequence[Mapping[str, Any]],
    test_trust_root: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write the frozen evidence-item layout from already-produced material.

    Separated from :func:`produce_evidence_item` because the proof obligations
    must be able to present *hostile* bytes — a fabricated result, an altered
    projected field, a re-signed envelope — through the exact same layout the
    honest producer uses.  A verifier that only ever saw honest input would
    prove nothing.
    """

    item_dir = Path(item_dir)
    item_dir.mkdir(parents=True, exist_ok=True)
    request_bytes = protocol.canonical_json_bytes(scientific_request)
    response_bytes = protocol.canonical_json_bytes(response)
    envelope_bytes = protocol.canonical_json_bytes(list(input_envelopes))

    item = {
        "authority": PRODUCER_OUTPUT_AUTHORITY,
        "evidence_item_id": item_dir.name,
        "input_envelope_count": len(input_envelopes),
        "input_envelope_digests": [
            protocol.digest_payload(envelope) for envelope in input_envelopes
        ],
        "item_layout_version": contract.EVIDENCE_ITEM_LAYOUT_VERSION,
        "producer_program_ticket": PROGRAM_TICKET,
        "producer_relative_path": CONTROLLER_RELATIVE_PATH,
        "request_digest": protocol.digest_bytes(request_bytes),
        "response_digest": protocol.digest_bytes(response_bytes),
    }
    if sorted(item) != sorted(contract.EVIDENCE_ITEM_FIELDS):
        raise ReplayVerifiedEvidenceDecisionError(
            "an evidence item manifest must be exactly the frozen field set"
        )

    (item_dir / contract.REQUEST_FILENAME).write_bytes(request_bytes)
    (item_dir / contract.RESPONSE_FILENAME).write_bytes(response_bytes)
    (item_dir / contract.ENVELOPES_FILENAME).write_bytes(envelope_bytes)
    (item_dir / contract.ITEM_FILENAME).write_bytes(
        protocol.canonical_json_bytes(item)
    )
    if test_trust_root is not None:
        (item_dir / contract.TEST_TRUST_ROOT_FILENAME).write_bytes(
            protocol.canonical_json_bytes(dict(test_trust_root))
        )
    return item


def run_verifier(
    evidence_dir: Path,
    record_dir: Path,
    *,
    executable: str,
    sys_path: Sequence[str],
    pycache_namespace: Path,
    mode: str,
    project_root: Path = PROJECT_ROOT,
    timeout_seconds: int = protocol.DEFAULT_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Launch the standalone verifier as its own isolated top-level process.

    This is a convenience for harnesses and for the proof obligations.  It is
    **not** a way for a caller to influence the verdict: everything it passes is
    a path, a list of directory paths or a frozen mode literal, and the verifier
    resolves the project root from its own file location rather than from
    anything handed to it.
    """

    Path(pycache_namespace).mkdir(parents=True, exist_ok=True)
    Path(record_dir).mkdir(parents=True, exist_ok=True)
    outcome = contract.spawn_isolated_process(
        contract.verifier_argv(
            executable=executable,
            verifier_entry=Path(project_root) / VERIFIER_RELATIVE_PATH,
            sys_path=sys_path,
            pycache_namespace=pycache_namespace,
            evidence_dir=evidence_dir,
            record_dir=record_dir,
            mode=mode,
        ),
        cwd=project_root,
        timeout_seconds=timeout_seconds,
    )
    summary: Any = None
    stdout = outcome["stdout"]
    if stdout.endswith(b"\n") and stdout.count(b"\n") == 1:
        try:
            summary = protocol.parse_canonical_json(stdout[:-1])
        except protocol.ScientificWorkerProtocolError:
            summary = None
    return {
        "exit_status": outcome["exit_status"],
        "timed_out": outcome["timed_out"],
        "stderr": outcome["stderr"],
        "summary": summary,
    }


def read_verification_records(record_dir: Path) -> tuple[dict[str, Any], ...]:
    """Read every persisted verification record, verifying its bound digest."""

    records: list[dict[str, Any]] = []
    for target in sorted(Path(record_dir).iterdir()):
        if not target.name.endswith(contract.VERIFICATION_RECORD_FILENAME_SUFFIX):
            continue
        record = protocol.parse_canonical_json(target.read_bytes())
        contract.verify_record_digest(record)
        records.append(record)
    return tuple(records)


# ---------------------------------------------------------------------------
# Mechanical audits
# ---------------------------------------------------------------------------

NO_AUTHORITY_AUDIT_VERSION = "ETF_CALENDAR_REPLAY_NO_IN_PROCESS_AUTHORITY_AUDIT_V1"
CLOSURE_AUDIT_VERSION = "ETF_CALENDAR_REPLAY_VERIFIER_SOURCE_CLOSURE_AUDIT_V1"
INTERFACE_AUDIT_VERSION = "ETF_CALENDAR_REPLAY_VERIFIER_INTERFACE_AUDIT_V1"
PROJECTION_AUDIT_VERSION = "ETF_CALENDAR_REPLAY_COMPARISON_PROJECTION_AUDIT_V1"
LAUNCH_CENSUS_AUDIT_VERSION = "ETF_CALENDAR_REPLAY_DIRECT_WORKER_LAUNCH_CENSUS_V1"

#: The process-creation primitives the census recognises, reused byte-for-byte
#: from the reviewed ``PAD4-R3`` set rather than re-listed, so the census cannot
#: quietly recognise fewer.
LAUNCH_PRIMITIVES: tuple[str, ...] = r5.LAUNCH_PRIMITIVES

_dotted_call_name = r5._dotted_call_name
_scope_index = r5._scope_index

#: The three modules this architecture adds.  Everything the audits inspect on
#: the ``PAD5`` side is one of these.
PAD5_OWNED_SOURCE: tuple[str, ...] = (
    CONTRACT_RELATIVE_PATH,
    CONTROLLER_RELATIVE_PATH,
    VERIFIER_RELATIVE_PATH,
)

#: The one justified ``PAD5``-owned process-creation site.
DECLARED_PAD5_LAUNCH_SITE = "spawn_isolated_process"

#: The preserved certified worker launch the *producer* reaches by reusing the
#: ``R5`` closed operation.  It is declared rather than hidden: the producer
#: genuinely creates a worker process, it does so through the preserved
#: reviewed path, and nothing it returns is authority.
DECLARED_PRESERVED_PRODUCER_LAUNCH = "run_isolated_scientific_request"


def audit_no_in_process_authority(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Compute that no ``PAD5`` module defines or emits an authority marker.

    The claim the frozen definition makes is that no producer-side type carries
    an authority marker.  A definition that merely asserted that would be worth
    nothing, so this walks the AST of all three ``PAD5`` modules and reports
    every occurrence of a retired marker string, every class definition, and
    every name that looks like an affirmative authority stamp.
    """

    marker_occurrences: list[dict[str, Any]] = []
    classes: list[dict[str, Any]] = []
    for relative in PAD5_OWNED_SOURCE:
        source = _module_source(relative, project_root)
        tree = ast.parse(source)
        scopes = _scope_index(tree)
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                for marker in contract.RETIRED_AUTHORITY_MARKERS:
                    if marker == node.value:
                        marker_occurrences.append(
                            {"path": relative, "marker": marker, "kind": "EXACT_STRING"}
                        )
            if isinstance(node, ast.ClassDef):
                classes.append(
                    {
                        "path": relative,
                        "name": node.name,
                        "scope": list(scopes.get(node, ())),
                    }
                )

    #: A retired marker may be *named* in the frozen retirement tuple, because
    #: naming what was retired is how a reviewer checks the retirement.  It may
    #: never be *emitted*.  The tuple is a single module-level assignment in the
    #: contract, so an occurrence anywhere else is a finding.
    permitted = {
        (CONTRACT_RELATIVE_PATH, marker)
        for marker in contract.RETIRED_AUTHORITY_MARKERS
    }
    emitted = sorted(
        f"{row['path']}:{row['marker']}"
        for row in marker_occurrences
        if (row["path"], row["marker"]) not in permitted
    )

    findings: list[str] = []
    if emitted:
        findings.append(f"RETIRED_AUTHORITY_MARKER_IS_EMITTED:{emitted!r}")
    if contract.PRODUCER_OUTPUT_AUTHORITY != "NON_AUTHORITATIVE_CANDIDATE_EVIDENCE":
        findings.append("PRODUCER_OUTPUT_IS_NOT_LABELLED_NON_AUTHORITATIVE")
    if "authority" not in contract.EVIDENCE_ITEM_FIELDS:
        findings.append("EVIDENCE_ITEM_CARRIES_NO_AUTHORITY_LABEL")
    if contract.VERIFIER_SELF_ATTESTATION_IS_AUTHORITY:
        findings.append("VERIFIER_SELF_ATTESTATION_IS_TREATED_AS_AUTHORITY")
    if contract.PRODUCER_SELF_ATTESTATION_IS_AUTHORITY:
        findings.append("PRODUCER_SELF_ATTESTATION_IS_TREATED_AS_AUTHORITY")

    return {
        "audit_version": NO_AUTHORITY_AUDIT_VERSION,
        "surveyed_paths": list(PAD5_OWNED_SOURCE),
        "retired_authority_markers": list(contract.RETIRED_AUTHORITY_MARKERS),
        "retired_marker_occurrences": marker_occurrences,
        "emitted_retired_markers": emitted,
        "pad5_class_definitions": classes,
        "pad5_class_definition_count": len(classes),
        "producer_output_authority": contract.PRODUCER_OUTPUT_AUTHORITY,
        "producer_process_trust": contract.PRODUCER_PROCESS_TRUST,
        "retired_authority_mechanisms": list(RETIRED_AUTHORITY_MECHANISMS),
        "verifier_self_attestation_is_authority": (
            contract.VERIFIER_SELF_ATTESTATION_IS_AUTHORITY
        ),
        "producer_self_attestation_is_authority": (
            contract.PRODUCER_SELF_ATTESTATION_IS_AUTHORITY
        ),
        "authority_anchor": contract.VERIFIER_AUTHORITY_ANCHOR,
        "findings": findings,
        "closed": not findings,
    }


def audit_verifier_source_closure(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Derive the verifier's transitive import closure and prove it certified.

    The derivation is a probe, not a list: it starts from the verifier entry
    module and follows every static import declaration, nested ones included,
    across both certified package roots, completing ancestor packages — exactly
    the rule that produced the four-file bootstrap set and the 120-module worker
    source universe.

    Every member must be hash-bound.  A member is hash-bound either because it
    is an entry of the frozen 120-module certified worker source manifest, or
    because it is one of the ``PAD5`` modules this child itself binds by SHA.
    Nothing else is permitted, and in particular no failed-lineage controller
    is, because none of them is a certified manifest member.
    """

    entries, unresolved = contract.derive_source_closure(Path(project_root))
    certified = {
        entry.module: entry.sha256 for entry in r5.frozen_candidate_source_manifest()
    }
    pad5 = {
        contract.CONTRACT_MODULE: CONTRACT_RELATIVE_PATH,
        contract.VERIFIER_ENTRY_MODULE: VERIFIER_RELATIVE_PATH,
    }

    members: list[dict[str, Any]] = []
    uncertified: list[str] = []
    for entry in entries:
        if entry.module in certified:
            binding = "CERTIFIED_WORKER_SOURCE_MANIFEST"
            agrees = certified[entry.module] == entry.sha256
        elif entry.module in pad5:
            binding = "PAD5_VERIFIER_SOURCE_MANIFEST"
            agrees = True
        else:
            binding = "UNCERTIFIED"
            agrees = False
            uncertified.append(entry.module)
        members.append(
            {
                "module": entry.module,
                "path": entry.path,
                "sha256": entry.sha256,
                "hash_binding": binding,
                "agrees_with_binding": agrees,
            }
        )

    failed_lineage = sorted(
        entry.module
        for entry in entries
        if entry.path in set(FAILED_LINEAGE_CONTROLLER_MODULES)
        or entry.path == CONTROLLER_RELATIVE_PATH
    )
    disagreeing = sorted(
        row["module"] for row in members if not row["agrees_with_binding"]
    )
    external = contract.external_import_roots(Path(project_root), entries)

    findings: list[str] = []
    if uncertified:
        findings.append(f"VERIFIER_CLOSURE_CONTAINS_UNCERTIFIED_MODULE:{uncertified!r}")
    if disagreeing:
        findings.append(f"VERIFIER_CLOSURE_MEMBER_IS_NOT_HASH_BOUND:{disagreeing!r}")
    if failed_lineage:
        findings.append(
            f"VERIFIER_CLOSURE_REACHES_A_FAILED_LINEAGE_CONTROLLER:{failed_lineage!r}"
        )
    if unresolved:
        # A declared certified-root import with no source file here. The
        # verifier would raise ``ImportError`` rather than run uncertified code,
        # so this is not an acceptance hole — but it is an import the audit
        # could not account for, and an audit that cannot see an import is not
        # an audit.
        findings.append(
            f"VERIFIER_CLOSURE_DECLARES_AN_UNRESOLVABLE_IMPORT:{list(unresolved)!r}"
        )

    return {
        "audit_version": CLOSURE_AUDIT_VERSION,
        "manifest_version": contract.VERIFIER_SOURCE_MANIFEST_VERSION,
        "seeds": list(contract.VERIFIER_CLOSURE_SEEDS),
        "derivation_rule": (
            "TRANSITIVE_STATIC_PROJECT_IMPORT_CLOSURE_OF_THE_VERIFIER_ENTRY_"
            "INCLUDING_NESTED_DECLARATIONS_PLUS_ANCESTOR_PACKAGES_ACROSS_BOTH_"
            "CERTIFIED_PACKAGE_ROOTS"
        ),
        "derivation_is_a_probe_not_a_list": True,
        "members": members,
        "module_count": len(members),
        "manifest_digest": contract.verifier_source_manifest_digest(entries),
        "certified_worker_source_members": sum(
            1 for row in members if row["hash_binding"] == "CERTIFIED_WORKER_SOURCE_MANIFEST"
        ),
        "pad5_members": sorted(
            row["module"]
            for row in members
            if row["hash_binding"] == "PAD5_VERIFIER_SOURCE_MANIFEST"
        ),
        "uncertified_members": uncertified,
        "unresolvable_declared_imports": list(unresolved),
        "failed_lineage_members": failed_lineage,
        "external_import_roots": list(external),
        "producer_is_outside_the_verifier_closure": (
            contract.PRODUCER_MODULE not in {row["module"] for row in members}
        ),
        "findings": findings,
        "closed": not findings,
    }


def audit_verifier_interface(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Compute that nothing executable can cross into the verifier process.

    The interface is five command-line strings and the canonical JSON documents
    they name.  What makes that airtight is not the argument count but the
    absence of any mechanism that could turn bytes into code: this walks the
    verifier's and the contract's ASTs for every forbidden name, as an
    attribute, as a bare name, as an import and as a call.
    """

    occurrences: list[dict[str, Any]] = []
    for relative in (VERIFIER_RELATIVE_PATH, CONTRACT_RELATIVE_PATH):
        source = _module_source(relative, project_root)
        tree = ast.parse(source)
        scopes = _scope_index(tree)
        for node in ast.walk(tree):
            names: list[str] = []
            if isinstance(node, ast.Name):
                names.append(node.id)
            elif isinstance(node, ast.Attribute):
                names.append(node.attr)
            elif isinstance(node, ast.Import):
                names.extend(alias.name.partition(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    names.append(node.module.partition(".")[0])
                names.extend(alias.name for alias in node.names)
            for name in names:
                if name in contract.FORBIDDEN_VERIFIER_NAMES:
                    occurrences.append(
                        {
                            "path": relative,
                            "name": name,
                            "scope": list(scopes.get(node, ())),
                        }
                    )

    verifier_tree = ast.parse(_module_source(VERIFIER_RELATIVE_PATH, project_root))
    entry = next(
        (
            node
            for node in verifier_tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "main"
        ),
        None,
    )
    if entry is None:
        raise ReplayVerifiedEvidenceDecisionError(
            "the verifier entry point 'main' is not a module-level function"
        )
    parameters = [argument.arg for argument in entry.args.args]
    annotations = [
        ast.unparse(argument.annotation) if argument.annotation else None
        for argument in entry.args.args
    ]
    has_star = entry.args.vararg is not None or entry.args.kwarg is not None

    findings: list[str] = []
    if occurrences:
        findings.append(
            f"VERIFIER_INTERFACE_REACHES_A_FORBIDDEN_NAME:"
            f"{sorted({row['name'] for row in occurrences})!r}"
        )
    if parameters != ["argv"] or annotations != ["list[str]"] or has_star:
        findings.append("VERIFIER_ENTRY_SIGNATURE_IS_NOT_A_LIST_OF_STRINGS")

    return {
        "audit_version": INTERFACE_AUDIT_VERSION,
        "surveyed_paths": [VERIFIER_RELATIVE_PATH, CONTRACT_RELATIVE_PATH],
        "forbidden_names": list(contract.FORBIDDEN_VERIFIER_NAMES),
        "forbidden_name_occurrences": occurrences,
        "entry_function": "main",
        "entry_parameters": parameters,
        "entry_parameter_annotations": annotations,
        "entry_accepts_varargs_or_kwargs": has_star,
        "argument_names": list(contract.VERIFIER_ARGUMENT_NAMES),
        "argument_count": len(contract.VERIFIER_ARGUMENT_NAMES),
        "caller_object_can_cross_the_boundary": False,
        "callback_can_cross_the_boundary": False,
        "module_can_cross_the_boundary": False,
        "pickle_can_cross_the_boundary": False,
        "findings": findings,
        "closed": not findings,
    }


def audit_comparison_projection() -> dict[str, Any]:
    """Compute that the projection is a closed inclusion list, not an exclusion.

    Three things have to be true and are computed here rather than claimed:
    every response field is classified exactly once; the inclusion list carries
    the full result, the result digest and every authority-bound field; and the
    two lists together partition the frozen response schema, so a response field
    can neither be silently projected nor silently dropped.
    """

    response_fields = set(protocol.RESPONSE_FIELDS)
    included = set(contract.IN_PROJECTION_AUTHORITY_FIELDS)
    excluded = set(contract.RUN_LOCAL_FIELDS)

    unclassified = sorted(response_fields - included - excluded)
    duplicated = sorted(included & excluded)
    unknown = sorted((included | excluded) - response_fields)
    missing_mandatory = sorted(set(contract.PROJECTION_MANDATORY_MEMBERS) - included)
    unjustified = sorted(
        (included | excluded) - set(contract.PROJECTION_FIELD_JUSTIFICATION)
    )

    findings: list[str] = []
    if unclassified:
        findings.append(f"RESPONSE_FIELD_IS_UNCLASSIFIED:{unclassified!r}")
    if duplicated:
        findings.append(f"RESPONSE_FIELD_IS_CLASSIFIED_TWICE:{duplicated!r}")
    if unknown:
        findings.append(f"PROJECTION_NAMES_AN_UNKNOWN_RESPONSE_FIELD:{unknown!r}")
    if missing_mandatory:
        findings.append(f"PROJECTION_OMITS_A_MANDATORY_MEMBER:{missing_mandatory!r}")
    if unjustified:
        findings.append(f"PROJECTION_FIELD_HAS_NO_JUSTIFICATION:{unjustified!r}")
    if not contract.PROJECTION_IS_A_CLOSED_INCLUSION_LIST:
        findings.append("PROJECTION_IS_NOT_A_CLOSED_INCLUSION_LIST")
    if contract.PROJECTION_IS_DEFINED_BY_EXCLUSION:
        findings.append("PROJECTION_IS_DEFINED_BY_EXCLUSION")

    return {
        "audit_version": PROJECTION_AUDIT_VERSION,
        "projection_version": contract.COMPARISON_PROJECTION_VERSION,
        "response_field_count": len(response_fields),
        "in_projection_authority_fields": list(
            contract.IN_PROJECTION_AUTHORITY_FIELDS
        ),
        "in_projection_field_count": len(included),
        "run_local_fields": list(contract.RUN_LOCAL_FIELDS),
        "run_local_field_count": len(excluded),
        "mandatory_members": sorted(contract.PROJECTION_MANDATORY_MEMBERS),
        "field_justifications": dict(
            sorted(contract.PROJECTION_FIELD_JUSTIFICATION.items())
        ),
        "is_a_closed_inclusion_list": contract.PROJECTION_IS_A_CLOSED_INCLUSION_LIST,
        "is_defined_by_exclusion": contract.PROJECTION_IS_DEFINED_BY_EXCLUSION,
        "unclassified_response_fields": unclassified,
        "findings": findings,
        "closed": not findings,
    }


def audit_direct_worker_launch_census(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """``PAD5``'s own direct worker-launch census.

    Two properties matter.  ``PAD5``-owned source must hold exactly one
    process-creation site, the shared ``spawn_isolated_process``, used by the
    verifier to re-execute the worker and by a harness to start a verifier.  And
    the 120-module certified worker source universe must hold **zero**: certified
    science must never be able to create a process.
    """

    surveyed: dict[str, str] = {
        CONTRACT_RELATIVE_PATH: "PAD5_SHARED_FROZEN_CONTRACT",
        CONTROLLER_RELATIVE_PATH: "PAD5_NON_AUTHORITATIVE_PRODUCER",
        VERIFIER_RELATIVE_PATH: "PAD5_STANDALONE_VERIFIER_AUTHORITY",
        RAW_REVIEW_HARNESS_RELATIVE_PATH: "TEST_AND_REVIEW_HARNESS_ONLY",
    }
    for relative in FAILED_LINEAGE_CONTROLLER_MODULES:
        surveyed[relative] = "SUPERSEDED_FAILED_LINEAGE_NOT_PAD5_AUTHORITY"
    for entry in r5.frozen_candidate_source_manifest():
        surveyed.setdefault(entry.path, "CERTIFIED_WORKER_SOURCE_UNIVERSE")

    sites: list[dict[str, Any]] = []
    for relative, classification in sorted(surveyed.items()):
        target = Path(project_root) / relative
        if not target.is_file():
            raise ReplayVerifiedEvidenceDecisionError(
                f"the direct launch census cannot read {relative}"
            )
        tree = ast.parse(target.read_text(encoding="utf-8"))
        scopes = _scope_index(tree)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            dotted = _dotted_call_name(node.func)
            if dotted in LAUNCH_PRIMITIVES:
                sites.append(
                    {
                        "path": relative,
                        "classification": classification,
                        "primitive": dotted,
                        "scope": list(scopes.get(node, ())),
                    }
                )

    pad5 = [
        site
        for site in sites
        if site["classification"].startswith("PAD5_")
    ]
    certified = [
        site
        for site in sites
        if site["classification"] == "CERTIFIED_WORKER_SOURCE_UNIVERSE"
    ]

    findings: list[str] = []
    if len(pad5) != 1:
        findings.append(
            f"PAD5_OWNED_SOURCE_HAS_{len(pad5)}_LAUNCH_SITES_NOT_EXACTLY_ONE"
        )
    else:
        only = pad5[0]
        if only["path"] != CONTRACT_RELATIVE_PATH:
            findings.append("THE_PAD5_LAUNCH_SITE_IS_NOT_IN_THE_SHARED_CONTRACT")
        if only["scope"] != [DECLARED_PAD5_LAUNCH_SITE]:
            findings.append("THE_PAD5_LAUNCH_SITE_IS_NOT_THE_DECLARED_SHARED_FUNCTION")
    if certified:
        findings.append(
            f"CERTIFIED_WORKER_SOURCE_CREATES_A_PROCESS:"
            f"{[site['path'] for site in certified]!r}"
        )

    return {
        "audit_version": LAUNCH_CENSUS_AUDIT_VERSION,
        "recognised_primitives": list(LAUNCH_PRIMITIVES),
        "surveyed_path_count": len(surveyed),
        "sites": sites,
        "pad5_owned_launch_sites": pad5,
        "pad5_owned_launch_site_count": len(pad5),
        "declared_pad5_launch_site": DECLARED_PAD5_LAUNCH_SITE,
        "shared_by": ["VERIFIER_RE_EXECUTES_THE_WORKER", "HARNESS_STARTS_A_VERIFIER"],
        "declared_preserved_producer_launch": DECLARED_PRESERVED_PRODUCER_LAUNCH,
        "preserved_producer_launch_justification": (
            "THE_PRODUCER_REUSES_THE_PRESERVED_PAD4_R5_CLOSED_WORKER_LAUNCH_"
            "UNCHANGED_AND_NOTHING_IT_RETURNS_IS_AUTHORITY"
        ),
        "certified_worker_source_launch_sites": len(certified),
        "authorized_launch_mechanisms": [contract.LAUNCH_MECHANISM],
        "unauthorized_launch_mechanisms": list(r5.UNAUTHORIZED_LAUNCH_MECHANISMS),
        "findings": findings,
        "closed": not findings,
    }


# ---------------------------------------------------------------------------
# Material children — carried forward byte-identically from reviewed PAD4-R5
# ---------------------------------------------------------------------------
#
# These are bound from the reviewed builders, not restated.  Each one's subject
# is the authentication of input bytes, the identity of the interpreter, or a
# static property of certified source — none of which moved when authority left
# the process.

bootstrap_source_set = r5.bootstrap_source_set
bytecode_execution_binding_rule = r5.bytecode_execution_binding_rule
compiled_root_binding_witness_rule = r5.compiled_root_binding_witness_rule
direct_body_dependency_rule = r5.direct_body_dependency_rule
dynamic_import_and_execution_prohibition = r5.dynamic_import_and_execution_prohibition
pre_i2_project_source_manifest_fixture = r5.pre_i2_project_source_manifest_fixture
project_source_manifest_binding_rule = r5.project_source_manifest_binding_rule
proof_interpreter_identity = r5.proof_interpreter_identity
replay_owner_graph_rule = r5.replay_owner_graph_rule
scientific_request_protocol = r5.scientific_request_protocol
scientific_response_protocol = r5.scientific_response_protocol
store_root_and_direct_use_grammar = r5.store_root_and_direct_use_grammar
third_party_installed_content_attestation_rule = (
    r5.third_party_installed_content_attestation_rule
)
third_party_semantic_authority = r5.third_party_semantic_authority
worker_io_and_capability_boundary = r5.worker_io_and_capability_boundary


# ---------------------------------------------------------------------------
# Material children — re-issued because the reviewed payload asserts something
# this architecture no longer claims
# ---------------------------------------------------------------------------


def _reissued(base: Mapping[str, Any], version: str, **overrides: Any) -> dict[str, Any]:
    """Re-issue a reviewed child under a new contract version.

    The reviewed payload is the starting point and every field that still holds
    is preserved exactly.  The overrides are the clauses the new architecture
    contradicts, and they are listed by name in the re-issued child so a
    reviewer can diff intent rather than bytes.
    """

    row = {
        key: value for key, value in base.items() if key != "definition_sha256"
    }
    row["contract_version"] = version
    row["reissued_from_contract_version"] = base["contract_version"]
    row["reissued_from_definition_sha256"] = base["definition_sha256"]
    row["reissued_because"] = (
        "THE_REVIEWED_PAYLOAD_ASSERTS_IN_PROCESS_AUTHORITY_CLOSURE_THAT_"
        "ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1_NO_LONGER_CLAIMS"
    )
    row["corrected_clauses"] = sorted(overrides)
    row.update(overrides)
    return _definition(row)


def bootstrap_pre_execution_source_binding_rule() -> dict[str, Any]:
    """The preserved pre-execution binding, re-issued for a verifier that does it.

    The rule itself is unchanged and is the reason worker bootstrap drift is
    rejected *before* execution rather than detected after it.  What changed is
    who performs it: under ``PAD4-R5`` it was the closed in-process controller
    operation, and here it is the standalone verifier, which hashes the same
    four files against the same frozen manifest digest and never reaches
    ``spawn_isolated_process`` on a mismatch.
    """

    return _reissued(
        r5.bootstrap_pre_execution_source_binding_rule(),
        "ETF_CALENDAR_WORKER_BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_V1_PAD5",
        authoritative_end_to_end_api=(
            "btc_predictor.research.etf_calendar_evidence_verifier.verify_evidence_item"
        ),
        authoritative_launch_api=(
            "btc_predictor.research.etf_calendar_replay_verified_evidence_contract."
            "spawn_isolated_process"
        ),
        private_non_authoritative_raw_subprocess_helper=None,
        binding_is_performed_by=(
            "THE_STANDALONE_VERIFIER_PROCESS_BEFORE_IT_RE_EXECUTES_THE_WORKER"
        ),
        binding_is_performed_by_an_in_process_controller_object=False,
        rejection_reason_code="REJECTED_WORKER_BOOTSTRAP_SOURCE_DRIFT",
    )


def worker_launch_contract() -> dict[str, Any]:
    """The preserved one-shot launch envelope, re-issued without encapsulation.

    Every determinism-bearing clause is preserved: one request, one exec'd fresh
    interpreter, ``-I -S -B`` plus ``-X pycache_prefix``, the frozen child
    environment, parent-controlled ``sys.path``, the frozen size and timeout
    limits, no fork-only worker and no worker reuse.  The three clauses that
    described the launch being hidden inside an authoritative in-process object
    are corrected, because there is no such object to hide it in: the launch is
    an ordinary shared function, and what stops a second one appearing is the
    frozen census, not encapsulation.
    """

    return _reissued(
        r5.worker_launch_contract(),
        "ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_V1_PAD5",
        launch_is_reachable_only_inside_the_authoritative_execution=False,
        module_accessible_spawn_primitive_exists=True,
        authoritative_launch_api=(
            "btc_predictor.research.etf_calendar_replay_verified_evidence_contract."
            "spawn_isolated_process"
        ),
        private_non_authoritative_raw_subprocess_helper=None,
        launch_sites_owned_by_this_architecture=1,
        launch_site_is_shared_by_the_verifier_and_the_harness=True,
        encapsulation_is_the_launch_boundary=False,
        frozen_census_is_the_launch_boundary=True,
    )


def trusted_process_and_isolation_boundary() -> dict[str, Any]:
    """The preserved isolation boundary, re-issued with honest authority counts.

    ``PAD4-R5``'s payload said there was exactly one authority-bearing
    production operation and that it was closed end to end in process.  Under
    this architecture the honest value of the first is zero, because no
    in-process operation bears authority at all.  The rest of the boundary — the
    closed input boundary, what is trusted once, the abandoned completeness
    models and the explicit non-claims about a hostile operating system — is
    preserved exactly, and the abandoned-models list is where this architecture
    came from.
    """

    return _reissued(
        r5.trusted_process_and_isolation_boundary(),
        "ETF_CALENDAR_TRUSTED_PROCESS_AND_ISOLATION_BOUNDARY_V1_PAD5",
        authority_bearing_production_operations=0,
        authoritative_scientific_execution_is_closed_end_to_end=False,
        authority_is_a_property_of_bytes_not_of_a_process_object=True,
        producer_process_is_trusted=False,
        producer_process_trust=contract.PRODUCER_PROCESS_TRUST,
        gc_object_graph_recovery_in_the_producer_is_in_domain_and_harmless=True,
        class_and_module_mutation_in_the_producer_is_in_domain_and_harmless=True,
        ctypes_and_frames_in_the_producer_are_in_domain_and_harmless=True,
        verifier_executes_only_certified_manifest_members=True,
        domain_text_excluding_introspection_routes=False,
    )


def trusted_authority_context_rule() -> dict[str, Any]:
    """The trusted-expected-value doctrine, re-issued for a file-driven verifier.

    The durable core is preserved verbatim: the twelve authority-bound request
    fields equal the twelve authority-bound response fields, the expected values
    come from the frozen trusted context and never from the ambient environment,
    a caller-selected SHA, the current filesystem or the scientific request, and
    neither the request nor a response echo is an authority root.  What is
    corrected is the set of clauses that tied the context to the lifetime of an
    in-process returned object.
    """

    return _reissued(
        r5.controller_authority_context_rule(),
        "ETF_CALENDAR_TRUSTED_AUTHORITY_CONTEXT_RULE_V1_PAD5",
        r5_trusted_context_type_required=False,
        three_way_agreement_valid_through_returned_authority_lifetime=False,
        returned_authority_can_drift_from_the_trusted_context=False,
        caller_mutation_can_break_the_three_way_agreement=False,
        trusted_context_identity_is_frozen_into_the_affirmative_evidence_bytes=False,
        trusted_context_is_frozen_source_of_the_verifier=True,
        trusted_context_is_a_python_object_the_caller_supplies=False,
        frozen_expected_authority=dict(sorted(contract.FROZEN_EXPECTED_AUTHORITY.items())),
        frozen_expected_authority_field_count=len(contract.FROZEN_EXPECTED_AUTHORITY),
        verifier_ever_adopts_an_expected_value_from_the_request=False,
        proof_architecture_identity_is_non_circular=True,
        proof_architecture_sha256=contract.REPLAY_VERIFIED_EVIDENCE_ARCHITECTURE_SHA256,
        proof_architecture_identity_derivation=(
            "SHA256_OVER_FROZEN_ARCHITECTURE_MATERIAL_THAT_DOES_NOT_CONTAIN_"
            "THE_DIGEST_ITSELF"
        ),
        environment_local_request_fields=list(
            contract.ENVIRONMENT_LOCAL_REQUEST_FIELDS
        ),
        environment_binding_rule=contract.ENVIRONMENT_BINDING_RULE,
        environment_relocation_rule=contract.ENVIRONMENT_RELOCATION_RULE,
        request_bytes_may_be_rewritten=contract.REQUEST_BYTES_MAY_BE_REWRITTEN,
    )


def replay_verified_admission_rule() -> dict[str, Any]:
    """The preserved admission decision procedure, re-applied by the verifier.

    The reviewed checklist is a data-level procedure and survives intact.  The
    two clauses that made admission a property of *being* the same in-process
    controller execution are corrected: admission is now a property of the bytes
    and is re-applied from scratch by a standalone process that holds no state
    from the producer at all.
    """

    return _reissued(
        r5.controller_result_admission_rule(),
        "ETF_CALENDAR_REPLAY_VERIFIED_ADMISSION_RULE_V1_PAD5",
        admission_requires_the_same_authoritative_controller_execution=False,
        admission_is_a_separately_callable_operation=False,
        admission_is_performed_by=(
            "A_STANDALONE_VERIFIER_PROCESS_OVER_RECORDED_BYTES"
        ),
        admission_requires_byte_identical_re_derivation=True,
        digest_only_acceptance_permitted=False,
        re_execution_is_required_for_every_accepted_item=True,
        self_verification_is_authority=False,
        verification_order=list(VERIFICATION_ORDER),
        rejection_reason_codes=list(contract.REJECTION_REASONS),
        acceptance_reason_code=contract.ACCEPTED_REASON,
    )


# ---------------------------------------------------------------------------
# Material children — the replay-verified architecture
# ---------------------------------------------------------------------------

#: The frozen order the verifier performs, step by step.  Nothing may be
#: reordered, and step 10 may not be skipped in favour of comparing digests.
VERIFICATION_ORDER: tuple[str, ...] = (
    "1_READ_THE_EVIDENCE_ITEM_AS_FILES_AND_CHECK_THE_FROZEN_LAYOUT",
    "2_PARSE_THE_RECORDED_REQUEST_AS_EXACT_SELF_RESERIALIZING_CANONICAL_BYTES",
    "3_VALIDATE_THE_RECORDED_REQUEST_AGAINST_THE_FROZEN_REQUEST_SCHEMA",
    "4_COMPARE_EVERY_AUTHORITY_BOUND_REQUEST_FIELD_WITH_THE_FROZEN_CONTEXT",
    "5_VERIFY_THAT_THIS_INTERPRETER_IS_THE_FROZEN_PROOF_INTERPRETER",
    "6_VERIFY_THAT_THIS_IS_THE_RECORDED_ENVIRONMENT",
    "7_VERIFY_EVERY_INPUT_ENVELOPE_UNDER_THE_CERTIFIED_TRUSTED_PERSISTENCE_PATH",
    "8_REQUIRE_THE_RECORDED_EVIDENCE_RECORDS_AND_VERIFIED_PAYLOADS_TO_AGREE",
    "9_BIND_THE_COMPLETE_BOOTSTRAP_SOURCE_SET_BEFORE_ANY_PROCESS_EXISTS",
    "10_RE_EXECUTE_THE_CERTIFIED_WORKER_ON_THE_EXACT_RECORDED_REQUEST_BYTES",
    "11_COMPARE_THE_FROZEN_PROJECTION_OF_BOTH_RESPONSES_BYTE_FOR_BYTE",
    "12_WRITE_ONE_CANONICAL_DIGEST_BOUND_RECORD_WHETHER_ACCEPTED_OR_REJECTED",
)

#: What this architecture refuses to be, named so a reviewer can check each one
#: against the source rather than against a promise.
REJECT_ON_SIGHT: tuple[str, ...] = (
    "ACCEPTING_EVIDENCE_BY_DIGEST_COMPARISON_ALONE_WITHOUT_RE_EXECUTION",
    "ANY_DOMAIN_TEXT_THAT_EXCLUDES_INTROSPECTION_ROUTES_TO_MAKE_A_CLAIM_TRUE",
    "ANY_IN_PROCESS_OBJECT_REGISTRY_CAPABILITY_CLOSURE_OR_TYPE_GATE_AS_AUTHORITY",
    "A_COMPARISON_PROJECTION_DEFINED_BY_EXCLUSION",
    "THE_PRODUCER_OR_WORKER_ATTESTING_ITS_OWN_AUTHORITY",
    "THE_VERIFIER_IMPORTING_A_MODULE_OUTSIDE_THE_CERTIFIED_CLOSURE",
    "THE_VERIFIER_RUNNING_INSIDE_THE_PRODUCERS_PROCESS",
)


def replay_verified_evidence_boundary() -> dict[str, Any]:
    """The architecture's own boundary contract, with its audits embedded."""

    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_BOUNDARY_V1",
            "invariant": contract.REPLAY_VERIFIED_EVIDENCE_INVARIANT,
            "authority_anchor": contract.VERIFIER_AUTHORITY_ANCHOR,
            "authority_is_a_property_of_bytes": True,
            "in_process_authority_objects": 0,
            "verification_order": list(VERIFICATION_ORDER),
            "reject_on_sight": list(REJECT_ON_SIGHT),
            "retired_authority_mechanisms": list(RETIRED_AUTHORITY_MECHANISMS),
            "retired_authority_markers": list(contract.RETIRED_AUTHORITY_MARKERS),
            "supersedes": FAILED_PAD4_R5_SHA256,
            "supersedes_review": FAILED_PAD4_R5_REVIEW,
            "supersedes_review_result": FAILED_PAD4_R5_REVIEW_RESULT,
            "supersedes_execution_classification": (
                FAILED_PAD4_R5_EXECUTION_CLASSIFICATION
            ),
            "escalation_decision": ESCALATION_DECISION,
            "r5_route_resolution": {
                "gc_registry_insertion_with_a_genuine_snapshot": (
                    "NOT_APPLICABLE_BY_CONSTRUCTION__THE_BYTES_A_FORGED_OBJECT_"
                    "PRESENTS_ARE_THE_GENUINE_EVIDENCE_SO_THE_VERIFIER_ACCEPTS_"
                    "THEM_AS_THAT_SAME_EVIDENCE_AND_NOTHING_NEW_IS_ADMITTED"
                ),
                "gc_registry_insertion_with_a_fabricated_snapshot": (
                    "REJECTED__FABRICATED_CONTENT_DOES_NOT_RE_DERIVE"
                ),
                "canonical_class_mutation": (
                    "NOT_APPLICABLE_BY_CONSTRUCTION__THE_AMBIGUOUS_MODULE_"
                    "MUTATION_PHRASE_IS_NOT_ADOPTED_REDEFINED_OR_RELIED_ON"
                ),
                "relay_of_genuine_bytes": (
                    "DISSOLVED_NOT_RECLASSIFIED__RE_PRESENTING_GENUINE_EVIDENCE_"
                    "BYTES_PRESENTS_THE_SAME_VERIFIED_EVIDENCE_AND_DUPLICATION_"
                    "IS_NOT_A_SCIENTIFIC_DEFECT"
                ),
                "frames_tracing_and_ctypes_in_the_producer": (
                    "IN_DOMAIN_AND_HARMLESS"
                ),
                "hostile_kernel_debugger_or_os_memory_injection": (
                    "OUT_OF_SCOPE_UNCHANGED_FROM_THE_PRESERVED_ISOLATION_BOUNDARY"
                ),
            },
            "accepted_costs": {
                "verification_re_executes_the_worker_once_per_evidence_item": True,
                "integrity_is_guaranteed": True,
                "availability_is_guaranteed": False,
                "a_hostile_producer_can_cause_rejection": True,
                "a_hostile_producer_can_cause_acceptance": False,
                "rejections_are_counted_and_recorded_never_dropped": True,
            },
            "no_in_process_authority_audit": audit_no_in_process_authority(),
            "verifier_interface_audit": audit_verifier_interface(),
            "direct_worker_launch_census": audit_direct_worker_launch_census(),
        }
    )


def verifier_source_manifest() -> dict[str, Any]:
    """The hash-bound verifier source manifest, mechanically derived."""

    return _definition(
        {
            "contract_version": contract.VERIFIER_SOURCE_MANIFEST_VERSION,
            "authority_anchor": contract.VERIFIER_AUTHORITY_ANCHOR,
            "self_attestation_is_authority": (
                contract.VERIFIER_SELF_ATTESTATION_IS_AUTHORITY
            ),
            "self_attestation_role": (
                "AUDIT_METADATA_AND_DEFENCE_IN_DEPTH__A_REPLACED_VERIFIER_COULD_"
                "REPORT_ANY_DIGEST_SO_THE_DIGEST_IT_REPORTS_PROVES_NOTHING_BY_"
                "ITSELF"
            ),
            "verifier_entry_module": contract.VERIFIER_ENTRY_MODULE,
            "verifier_entry_relative_path": VERIFIER_RELATIVE_PATH,
            "verifier_launch_flags": list(contract.LAUNCH_FLAGS),
            "verifier_launch_x_option": contract.LAUNCH_X_OPTION,
            "verifier_runs_in_isolated_mode": True,
            "verifier_runs_with_no_site": True,
            "verifier_writes_no_bytecode": True,
            "closure_audit": audit_verifier_source_closure(),
        }
    )


def verifier_interface_boundary() -> dict[str, Any]:
    """What can and cannot cross into the verifier process."""

    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_VERIFIER_INTERFACE_BOUNDARY_V1",
            "interface": "COMMAND_LINE_STRINGS_AND_CANONICAL_JSON_FILES_ONLY",
            "argument_names": list(contract.VERIFIER_ARGUMENT_NAMES),
            "argument_count": len(contract.VERIFIER_ARGUMENT_NAMES),
            "modes": list(contract.VERIFIER_MODES),
            "production_mode_refuses_test_key_envelopes": True,
            "production_mode_accepts_a_file_supplied_trust_root": False,
            "test_mode_is_explicitly_non_authoritative": True,
            "test_only_key_id_prefix": contract.TEST_ONLY_KEY_ID_PREFIX,
            "forbidden_names": list(contract.FORBIDDEN_VERIFIER_NAMES),
            "callback_can_cross": False,
            "plugin_can_cross": False,
            "pickle_can_cross": False,
            "class_can_cross": False,
            "module_can_cross": False,
            "caller_object_can_cross": False,
            "why_impossible": (
                "THE_ONLY_CHANNEL_IS_A_PROCESS_BOUNDARY_THAT_CARRIES_BYTES_AND_"
                "THE_ONLY_BYTES_ACCEPTED_ARE_FIVE_COMMAND_LINE_STRINGS_AND_THE_"
                "CANONICAL_JSON_DOCUMENTS_THEY_NAME"
            ),
            "interface_audit": audit_verifier_interface(),
        }
    )


def comparison_projection_definition() -> dict[str, Any]:
    """The frozen deterministic comparison projection."""

    return _definition(
        {
            "contract_version": contract.COMPARISON_PROJECTION_VERSION,
            "comparison": "BYTE_FOR_BYTE_OVER_THE_CANONICAL_PROJECTION_BYTES",
            "digest_only_acceptance_permitted": False,
            "environment_local_request_fields": list(
                contract.ENVIRONMENT_LOCAL_REQUEST_FIELDS
            ),
            "environment_binding_rule": contract.ENVIRONMENT_BINDING_RULE,
            "environment_relocation_rule": contract.ENVIRONMENT_RELOCATION_RULE,
            "environment_binding_justification": (
                "A_RELOCATION_RULE_WOULD_BE_A_SECOND_CANONICALISATION_OF_"
                "AUTHORITY_BEARING_BYTES_AND_IS_ONE_EDIT_FROM_REWRITING_THEM__"
                "THE_RECORDED_ENVIRONMENT_IS_ALREADY_PINNED_BY_THE_FROZEN_"
                "INTERPRETER_IDENTITY_THE_CERTIFIED_SOURCE_MANIFEST_AND_THE_"
                "THIRD_PARTY_INSTALLED_CONTENT_AUTHORITY_ALL_THREE_OF_WHICH_"
                "ARE_INSIDE_THE_PROJECTION__THE_COST_IS_AVAILABILITY_NOT_"
                "INTEGRITY"
            ),
            "request_bytes_may_be_rewritten": contract.REQUEST_BYTES_MAY_BE_REWRITTEN,
            "run_local_measurement": (
                "MEASURED_EMPIRICALLY_BY_RE_EXECUTING_THE_SAME_RECORDED_REQUEST_"
                "IN_SEPARATE_PROCESSES_WITH_DIFFERENT_BYTECODE_CACHE_NAMESPACES_"
                "DIFFERENT_WORKING_DIRECTORIES_AND_DIFFERENT_PYTHONHASHSEED_"
                "VALUES"
            ),
            "projection_audit": audit_comparison_projection(),
        }
    )


def canonical_encoding_rule() -> dict[str, Any]:
    """The one canonical encoding every byte comparison in this architecture uses.

    Extracted from the retired ``R5`` snapshot child, because byte-identical
    re-derivation depends on exactly these four serialisation rules and nothing
    else in this namespace owns them.  There is deliberately no second encoder:
    a competing notion of canonical form would be a second authority.
    """

    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_CANONICAL_ENCODING_RULE_V1",
            "canonical_encoder": "etf_calendar_worker.protocol_r1.canonical_json_bytes",
            "canonical_decoder": "etf_calendar_worker.protocol_r1.parse_canonical_json",
            "canonical_digest": "etf_calendar_worker.protocol_r1.digest_bytes",
            "canonical_serialization_rules": [
                "ASCII_ONLY",
                "COMPACT_SEPARATORS",
                "NO_NAN_OR_INFINITY",
                "SORTED_KEYS",
            ],
            "digest_algorithm": "SHA256_OVER_CANONICAL_JSON_BYTES",
            "second_competing_canonical_form_exists": False,
            "preserved_canonical_rejections": list(r5.PRESERVED_CANONICAL_REJECTIONS),
            "preserved_timestamp_rejection": r5.PRESERVED_TIMESTAMP_REJECTION,
            "received_bytes_must_reserialize_to_themselves": True,
            "extracted_from": "ETF_CALENDAR_CANONICAL_ADMITTED_SNAPSHOT_RULE_V1_R5",
            "extracted_because": (
                "THE_R5_CHILD_MIXED_ARCHITECTURE_NEUTRAL_CANONICALISATION_WITH_"
                "IN_PROCESS_IDENTITY_BINDING_AND_COULD_NOT_BE_CARRIED_WHOLE"
            ),
        }
    )


def evidence_item_layout_rule() -> dict[str, Any]:
    """The frozen on-disk layout of one candidate evidence item."""

    return _definition(
        {
            "contract_version": contract.EVIDENCE_ITEM_LAYOUT_VERSION,
            "required_filenames": list(contract.EVIDENCE_ITEM_FILENAMES),
            "required_file_count": len(contract.EVIDENCE_ITEM_FILENAMES),
            "optional_filenames": list(contract.EVIDENCE_ITEM_OPTIONAL_FILENAMES),
            "item_manifest_fields": list(contract.EVIDENCE_ITEM_FIELDS),
            "file_encoding": "EXACT_CANONICAL_JSON_BYTES_WITH_NO_TRAILING_NEWLINE",
            "file_digest_is_the_payload_digest": True,
            "request_file": contract.REQUEST_FILENAME,
            "response_file": contract.RESPONSE_FILENAME,
            "input_envelopes_file": contract.ENVELOPES_FILENAME,
            "item_manifest_file": contract.ITEM_FILENAME,
            "test_trust_root_file": contract.TEST_TRUST_ROOT_FILENAME,
            "test_trust_root_permitted_in_production_mode": False,
            "test_trust_root_refusal_reason": (
                "A_CALLER_SUPPLIED_TRUST_REGISTRY_REACHING_PRODUCTION_"
                "VERIFICATION_IS_THE_EXACT_SHAPE_POSTP1_002V2B_FAILED"
            ),
            "affirmative_evidence_is_written": False,
            "affirmative_evidence_is_written_because": (
                "IT_CARRIES_A_RETIRED_AUTHORITY_MARKER_AND_A_CANDIDATE_ITEM_"
                "THAT_CARRIED_ONE_WOULD_CLAIM_THE_THING_THIS_ARCHITECTURE_"
                "REMOVED"
            ),
        }
    )


def non_authoritative_producer_rule() -> dict[str, Any]:
    """What the producer is, and what it explicitly is not."""

    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_NON_AUTHORITATIVE_PRODUCER_V1",
            "producer_module": contract.PRODUCER_MODULE,
            "producer_relative_path": CONTROLLER_RELATIVE_PATH,
            "producer_output_authority": contract.PRODUCER_OUTPUT_AUTHORITY,
            "producer_process_trust": contract.PRODUCER_PROCESS_TRUST,
            "producer_output_is_authority": False,
            "producer_self_attestation_is_authority": False,
            "producer_side_type_carries_an_authority_marker": False,
            "producer_reuses_the_preserved_launch_path": True,
            "preserved_launch_path": DECLARED_PRESERVED_PRODUCER_LAUNCH,
            "producer_forks_the_worker": False,
            "producer_forks_the_bootstrap_set": False,
            "producer_forks_the_protocol": False,
            "producer_is_inside_the_verifier_import_closure": False,
            "permitted_in_the_producer_process": [
                "CLASS_AND_MODULE_MUTATION",
                "CLOSURE_CELL_RECOVERY",
                "CTYPES",
                "FRAMES_AND_TRACING",
                "GC_OBJECT_GRAPH_ENUMERATION_AND_MUTATION",
                "PRIVATE_NAME_REFLECTION",
            ],
            "why_that_is_harmless": (
                "NOTHING_THE_PRODUCER_RETURNS_IS_AUTHORITY_SO_AN_OBJECT_THAT_"
                "ACQUIRES_ANYTHING_IN_ITS_PROCESS_HAS_ACQUIRED_NOTHING_THE_"
                "VERIFIER_READS"
            ),
            "no_in_process_authority_audit": audit_no_in_process_authority(),
        }
    )


def verification_record_contract() -> dict[str, Any]:
    """One canonical digest-bound record per evidence item, accepted or not."""

    return _definition(
        {
            "contract_version": contract.VERIFICATION_RECORD_SCHEMA_VERSION,
            "record_fields": list(contract.VERIFICATION_RECORD_FIELDS),
            "record_field_count": len(contract.VERIFICATION_RECORD_FIELDS),
            "bound_digest_field": "record_sha256",
            "verdicts": list(contract.VERDICTS),
            "acceptance_reason_code": contract.ACCEPTED_REASON,
            "rejection_reason_codes": list(contract.REJECTION_REASONS),
            "reason_code_count": len(contract.VERIFICATION_REASON_CODES),
            "rejections_are_recorded_never_dropped": True,
            "repeated_verification_yields_identical_bytes": True,
            "record_carries_a_timestamp": False,
            "record_carries_a_duration": False,
            "record_carries_a_path": False,
            "record_carries_a_process_identifier": False,
            "record_carries_a_memory_address": False,
            "why_no_timestamp": (
                "VERIFYING_THE_SAME_EVIDENCE_TWICE_MUST_PRODUCE_BYTE_IDENTICAL_"
                "RECORDS_AND_A_RECORD_CARRYING_A_CLOCK_READ_COULD_NOT"
            ),
            "record_carries_the_request_digest": True,
            "record_carries_the_response_digest": True,
            "record_carries_the_projection_digests": True,
            "record_carries_the_verifier_source_manifest_digest": True,
            "record_carries_the_verifier_commit": True,
            "record_carries_the_interpreter_identity": True,
            "record_filename_suffix": contract.VERIFICATION_RECORD_FILENAME_SUFFIX,
        }
    )


def consumer_admission_rule() -> dict[str, Any]:
    """How every downstream owner must admit ETF calendar evidence.

    ``PAD5`` freezes the rule only.  Wiring each consumer belongs to that
    consumer's own ticket, and no consumer is wired here.
    """

    return _definition(
        {
            "contract_version": contract.CONSUMER_ADMISSION_RULE_VERSION,
            "rule": contract.CONSUMER_ADMISSION_RULE,
            "bound_consumers": list(contract.BOUND_CONSUMERS),
            "bound_consumer_count": len(contract.BOUND_CONSUMERS),
            "admission_predicate": (
                "btc_predictor.research.etf_calendar_replay_verified_evidence_"
                "contract.admits"
            ),
            "admitting_verifier_mode": contract.PRODUCTION_MODE,
            "admitting_verdict": contract.ACCEPTED,
            "admitting_reason_code": contract.ACCEPTED_REASON,
            "a_non_authoritative_test_record_admits": False,
            "a_rejection_record_admits": False,
            "a_record_with_a_broken_digest_admits": False,
            "stage_b_must_verify_every_observation_before_evaluating": True,
            "consumers_wired_by_this_ticket": 0,
            "wiring_belongs_to": "EACH_CONSUMERS_OWN_TICKET",
        }
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    """The frozen order, the determinism axes and the explicit limits."""

    reviewed = r5.proof_order_and_completeness_definition()
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_VERIFIED_PROOF_ORDER_V1",
            "verification_order": list(VERIFICATION_ORDER),
            "worker_order": list(reviewed["worker_order"]),
            "determinism": list(reviewed["determinism"]),
            "explicit_limits": list(reviewed["explicit_limits"]),
            "reject_on_sight": list(REJECT_ON_SIGHT),
            "completeness_claim": (
                "THIS_ARCHITECTURE_CLAIMS_EXACTLY_ONE_THING: BYTES_THAT_WERE_"
                "NOT_RE_DERIVED_FROM_AUTHENTICATED_INPUTS_BY_CERTIFIED_CODE_"
                "RUNNING_IN_A_SEPARATE_PROCESS_ARE_NEVER_ACCEPTED_AS_EVIDENCE. "
                "IT_DOES_NOT_CLAIM_THAT_THE_PRODUCERS_PROCESS_IS_HONEST, THAT_"
                "CPYTHON_INTROSPECTION_CAN_BE_ENUMERATED, OR_THAT_AVAILABILITY_"
                "IS_GUARANTEED. A_HOSTILE_PRODUCER_CAN_MAKE_EVIDENCE_BE_"
                "REJECTED_AND_CANNOT_MAKE_IT_BE_ACCEPTED."
            ),
            "carried_forward_children": list(CARRIED_FORWARD_CHILDREN),
            "reissued_children": list(REISSUED_CHILDREN),
            "new_children": list(NEW_CHILDREN),
            "retired_r5_identity_children": list(RETIRED_R5_IDENTITY_CHILDREN),
            "retired_children_are_copied_here_as_authority": False,
        }
    )


def science_lineage_and_safety() -> dict[str, Any]:
    """The lineage ledger and the unchanged safety position."""

    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_REPLAY_VERIFIED_SCIENCE_LINEAGE_AND_SAFETY_V1"
            ),
            "failed_architecture_lineage": [
                {
                    "sha256": sha,
                    "certified": False,
                    "failed": True,
                    "used": False,
                    "prospective_observations": 0,
                    "superseded_before_use": True,
                    "immutable": True,
                }
                for sha in FAILED_ARCHITECTURE_LINEAGE
            ],
            "failed_architecture_lineage_count": len(FAILED_ARCHITECTURE_LINEAGE),
            "failed_calendar_lineage": list(FAILED_CALENDAR_LINEAGE),
            "failed_lineage_controller_modules": list(
                FAILED_LINEAGE_CONTROLLER_MODULES
            ),
            "superseded_predecessor": {
                "sha256": FAILED_PAD4_R5_SHA256,
                "review": FAILED_PAD4_R5_REVIEW,
                "review_result": FAILED_PAD4_R5_REVIEW_RESULT,
                "execution_classification": FAILED_PAD4_R5_EXECUTION_CLASSIFICATION,
                "implementation_commit": FAILED_PAD4_R5_IMPLEMENTATION_COMMIT,
                "namespace_is_untouched": True,
                "identity_children_are_retired_as_failed_lineage": True,
            },
            "escalation_decision": ESCALATION_DECISION,
            "correction_is_a_new_architecture_family": True,
            "preserved_science": {
                "etf_calendar_science_changed": False,
                "worker_protocol_changed": False,
                "worker_bootstrap_set_changed": False,
                "worker_source_universe_changed": False,
                "trusted_persistence_reopened": False,
                "eleven_owner_replay_graph_changed": False,
            },
            "certified_trusted_persistence_sha256": CERTIFIED_DEPENDENCY_SHA256,
            "safety": {
                "prospective_observations": 0,
                "real_stage_b_evaluation": False,
                "etf_calendar_certified": False,
                "prospective_collection_authorized": False,
                "postp1_001v2a_i2_may_begin": False,
                "postp1_001v2r1_may_begin": False,
                "postp1_003r3_may_begin": False,
                "postp1_004_may_begin": False,
                "btc_019_untouched": True,
                "btc_019_sealed_sample_opened": False,
                "epic_t_unchanged": True,
                "epic_y_unchanged": True,
            },
        }
    )


_CHILD_ARTIFACTS: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
    ("bootstrap_pre_execution_source_binding_rule.json", bootstrap_pre_execution_source_binding_rule),
    ("bootstrap_source_set.json", bootstrap_source_set),
    ("bytecode_execution_binding_rule.json", bytecode_execution_binding_rule),
    ("canonical_encoding_rule.json", canonical_encoding_rule),
    ("comparison_projection_definition.json", comparison_projection_definition),
    ("compiled_root_binding_witness_rule.json", compiled_root_binding_witness_rule),
    ("consumer_admission_rule.json", consumer_admission_rule),
    ("direct_body_dependency_rule.json", direct_body_dependency_rule),
    ("dynamic_import_and_execution_prohibition.json", dynamic_import_and_execution_prohibition),
    ("evidence_item_layout_rule.json", evidence_item_layout_rule),
    ("non_authoritative_producer_rule.json", non_authoritative_producer_rule),
    ("pre_i2_project_source_manifest_fixture.json", pre_i2_project_source_manifest_fixture),
    ("project_source_manifest_binding_rule.json", project_source_manifest_binding_rule),
    ("proof_interpreter_identity.json", proof_interpreter_identity),
    ("proof_order_and_completeness_definition.json", proof_order_and_completeness_definition),
    ("replay_owner_graph_rule.json", replay_owner_graph_rule),
    ("replay_verified_admission_rule.json", replay_verified_admission_rule),
    ("replay_verified_evidence_boundary.json", replay_verified_evidence_boundary),
    ("science_lineage_and_safety.json", science_lineage_and_safety),
    ("scientific_request_protocol.json", scientific_request_protocol),
    ("scientific_response_protocol.json", scientific_response_protocol),
    ("store_root_and_direct_use_grammar.json", store_root_and_direct_use_grammar),
    ("third_party_installed_content_attestation_rule.json", third_party_installed_content_attestation_rule),
    ("third_party_semantic_authority.json", third_party_semantic_authority),
    ("trusted_authority_context_rule.json", trusted_authority_context_rule),
    ("trusted_process_and_isolation_boundary.json", trusted_process_and_isolation_boundary),
    ("verification_record_contract.json", verification_record_contract),
    ("verifier_interface_boundary.json", verifier_interface_boundary),
    ("verifier_source_manifest.json", verifier_source_manifest),
    ("worker_io_and_capability_boundary.json", worker_io_and_capability_boundary),
    ("worker_launch_contract.json", worker_launch_contract),
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


def replay_verified_evidence_v1_definition(
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    """Build the frozen parent, verifying every preserved authority as it goes."""

    r5.verify_worker_protocol_binds_the_frozen_interpreter()
    r5.verify_frozen_pre_i2_fixture()
    completeness = r5.verify_frozen_bootstrap_set_is_complete()
    children = _children(child_artifacts)
    fixture = r5.frozen_pre_i2_source_manifest()
    candidate = r5.frozen_candidate_source_manifest()
    bootstrap = r5.frozen_bootstrap_source_manifest()
    verifier_entries = contract.derive_source_manifest(PROJECT_ROOT)
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
            "supersedes": FAILED_PAD4_R5_SHA256,
            "supersedes_review": FAILED_PAD4_R5_REVIEW,
            "supersedes_review_result": FAILED_PAD4_R5_REVIEW_RESULT,
            "correction_is_a_new_architecture_family": True,
            "escalation_decision": ESCALATION_DECISION,
            "invariant": contract.REPLAY_VERIFIED_EVIDENCE_INVARIANT,
            "authority_anchor": contract.VERIFIER_AUTHORITY_ANCHOR,
            "proof_architecture_sha256": (
                contract.REPLAY_VERIFIED_EVIDENCE_ARCHITECTURE_SHA256
            ),
            "verification_order": list(VERIFICATION_ORDER),
            "reject_on_sight": list(REJECT_ON_SIGHT),
            "preserved_valid_portions": list(PRESERVED_VALID_PORTIONS),
            "not_reopened": list(NOT_REOPENED),
            "retired_authority_mechanisms": list(RETIRED_AUTHORITY_MECHANISMS),
            "carried_forward_children": list(CARRIED_FORWARD_CHILDREN),
            "carried_forward_child_count": len(CARRIED_FORWARD_CHILDREN),
            "reissued_children": list(REISSUED_CHILDREN),
            "reissued_child_count": len(REISSUED_CHILDREN),
            "new_children": list(NEW_CHILDREN),
            "new_child_count": len(NEW_CHILDREN),
            "retired_r5_identity_children": list(RETIRED_R5_IDENTITY_CHILDREN),
            "retired_r5_identity_child_count": len(RETIRED_R5_IDENTITY_CHILDREN),
            "failed_architecture_lineage": list(FAILED_ARCHITECTURE_LINEAGE),
            "failed_lineage_controller_modules": list(
                FAILED_LINEAGE_CONTROLLER_MODULES
            ),
            "worker_bootstrap_source_set": list(
                protocol.WORKER_BOOTSTRAP_RELATIVE_PATHS
            ),
            "worker_bootstrap_manifest_digest": protocol.bootstrap_manifest_digest(
                bootstrap
            ),
            "worker_bootstrap_source_count": len(bootstrap),
            "worker_bootstrap_set_completeness": completeness,
            "pre_i2_project_source_manifest_digest": protocol.manifest_digest(fixture),
            "pre_i2_project_source_module_count": len(fixture),
            "pre_i2_project_source_manifest_role": (
                contract.FROZEN_PROJECT_SOURCE_MANIFEST_ROLE
            ),
            "candidate_worker_source_manifest_digest": protocol.manifest_digest(
                candidate
            ),
            "candidate_worker_source_module_count": len(candidate),
            "third_party_authority_digest": (
                contract.FROZEN_THIRD_PARTY_AUTHORITY_DIGEST
            ),
            "trusted_persistence_authority_sha256": CERTIFIED_DEPENDENCY_SHA256,
            "calendar_authority_version": contract.FROZEN_CALENDAR_AUTHORITY_VERSION,
            "calendar_authority_sha256": contract.FROZEN_CALENDAR_AUTHORITY_SHA256,
            "verifier_source_manifest_digest": (
                contract.verifier_source_manifest_digest(verifier_entries)
            ),
            "verifier_source_module_count": len(verifier_entries),
            "verifier_entry_module": contract.VERIFIER_ENTRY_MODULE,
            "producer_module": contract.PRODUCER_MODULE,
            "frozen_replay_owners": list(FROZEN_REPLAY_OWNERS),
            "material_child_count": len(children),
            "child_definition_sha256": {
                name: payload["definition_sha256"]
                for name, payload in sorted(children.items())
            },
            "properties": {
                "authority_is_a_property_of_bytes": True,
                "caller_object_can_reach_the_verifier": False,
                "digest_only_acceptance_permitted": False,
                "domain_text_excludes_introspection_routes": False,
                "in_process_authority_objects": 0,
                "producer_output_is_authority": False,
                "producer_self_attestation_is_authority": False,
                "projection_defined_by_exclusion": False,
                "re_execution_required_for_acceptance": True,
                "rejections_are_recorded_never_dropped": True,
                "repeated_verification_is_byte_identical": True,
                "request_bytes_may_be_rewritten": False,
                "verifier_executes_only_certified_manifest_members": True,
                "verifier_runs_in_the_producers_process": False,
                "verifier_self_attestation_is_authority": False,
                "worker_bootstrap_set_forked": False,
                "worker_protocol_forked": False,
            },
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
    if dict(persisted) != replay_verified_evidence_v1_definition():
        raise ReplayVerifiedEvidenceDecisionError(
            "persisted replay-verified evidence decision does not reproduce"
        )
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    owners = "\n".join(f"- `{owner}`" for owner in FROZEN_REPLAY_OWNERS)
    lineage = "\n".join(f"- `{sha}`" for sha in FAILED_ARCHITECTURE_LINEAGE)
    bootstrap = "\n".join(
        f"{index}. `{path}`"
        for index, path in enumerate(decision["worker_bootstrap_source_set"], start=1)
    )
    order = "\n".join(step for step in VERIFICATION_ORDER)
    carried = "\n".join(f"- `{name}`" for name in CARRIED_FORWARD_CHILDREN)
    reissued = "\n".join(f"- `{name}`" for name in REISSUED_CHILDREN)
    fresh = "\n".join(f"- `{name}`" for name in NEW_CHILDREN)
    retired = "\n".join(f"- `{name}`" for name in RETIRED_R5_IDENTITY_CHILDREN)
    rejected = "\n".join(f"- `{name}`" for name in REJECT_ON_SIGHT)
    projection = "\n".join(
        f"- `{name}` — {contract.PROJECTION_FIELD_JUSTIFICATION[name]}"
        for name in contract.IN_PROJECTION_AUTHORITY_FIELDS
    )
    children = "\n".join(
        f"- `{name}` — `{sha}`"
        for name, sha in sorted(decision["child_definition_sha256"].items())
    )
    return f"""# {DECISION_VERSION} — {PROGRAM_TICKET}

**Decision hash:** `{decision["definition_sha256"]}`
**Status:** `{decision["status"]}`
**Final classification:** `{decision["final_classification"]}`
**Required review:** `{decision["required_review"]}`

## What this replaces

`{FAILED_PAD4_R5_REVIEW}` failed the exact-identity `PAD4-R5` candidate
`{FAILED_PAD4_R5_SHA256}` with:

```text
{FAILED_PAD4_R5_REVIEW_RESULT}
```

That was the fourth failure in one family — fabricate, mutate, impersonate,
recover — and the pre-committed rule escalated automatically to a new
proof-architecture decision, `{ESCALATION_DECISION}`. No `PAD4-R6` was created.

The shared root cause is that any object reachable in a CPython process can be
enumerated and mutated by other code in that process. No arrangement of
in-process Python state can make "only the exact controller-owned object
resolves authority" true while uncertified caller code shares the interpreter.

## The frozen invariant

```text
{contract.REPLAY_VERIFIED_EVIDENCE_INVARIANT}
```

Authority is a property of bytes, not of an object. It is anchored in the exact
reviewed commit the verifier runs from; the verifier recording its own source
manifest digest is audit metadata and defence in depth, and is **not**
authority.

## The verification order

```text
{order}
```

## Deterministic comparison projection

The projection is a **closed inclusion list** of
{len(contract.IN_PROJECTION_AUTHORITY_FIELDS)} named response fields. It is
never "everything except". `RUN_LOCAL` is empty — measured, not assumed, by
re-executing the same recorded request in separate processes with different
bytecode-cache namespaces, different working directories and different
`PYTHONHASHSEED` values.

{projection}

**Environment-local request fields:** `{"`, `".join(contract.ENVIRONMENT_LOCAL_REQUEST_FIELDS)}`.
The frozen choice is `{contract.ENVIRONMENT_BINDING_RULE}`; no relocation rule is
frozen and request bytes are never rewritten.

## Verifier

- Entry: `{contract.VERIFIER_ENTRY_MODULE}`
- Launch: `{" ".join(contract.LAUNCH_FLAGS)}` plus `-X {contract.LAUNCH_X_OPTION}`
- Source manifest: {decision["verifier_source_module_count"]} modules at
  `{decision["verifier_source_manifest_digest"]}`
- Interface: {len(contract.VERIFIER_ARGUMENT_NAMES)} command-line strings and the
  canonical JSON documents they name. No callback, plugin, pickle, class, module
  or caller object can cross.

## Reject-on-sight

{rejected}

## Children carried forward byte-identically from `PAD4-R5` ({len(CARRIED_FORWARD_CHILDREN)})

{carried}

## Children re-issued because the reviewed payload asserted in-process closure ({len(REISSUED_CHILDREN)})

{reissued}

## New children ({len(NEW_CHILDREN)})

{fresh}

## Retired `R5` identity children — failed lineage, not copied here ({len(RETIRED_R5_IDENTITY_CHILDREN)})

{retired}

## Worker bootstrap source set

Unchanged and not forked.

{bootstrap}

**Bootstrap manifest digest:** `{decision["worker_bootstrap_manifest_digest"]}`

## Source authority

- PRE-I2 conformance fixture: {decision["pre_i2_project_source_module_count"]} modules
  at `{decision["pre_i2_project_source_manifest_digest"]}`
- Candidate worker source universe:
  {decision["candidate_worker_source_module_count"]} modules at
  `{decision["candidate_worker_source_manifest_digest"]}`
- Third-party authority digest: `{decision["third_party_authority_digest"]}`

## Preserved eleven replay owners

{owners}

## Failed architecture lineage — immutable, non-certified, unused ({len(FAILED_ARCHITECTURE_LINEAGE)})

{lineage}

Trusted persistence `{CERTIFIED_DEPENDENCY_SHA256}` is closed, certified,
unchanged and not re-reviewed by this decision.

## Accepted costs

Verification re-executes the worker once per evidence item. Integrity is
guaranteed; availability is not. A hostile producer can make evidence be
**rejected**; it cannot make evidence be **accepted**. Rejections are counted
and recorded, never silently dropped.

## Material children ({decision["material_child_count"]})

{children}

## Safety

Observations remain **0**. No real Stage-B evaluation ran. The ETF calendar is
**not** certified, no calendar production code changed, collection is **NOT
AUTHORIZED**, `BTC-019` is untouched with its sealed sample unopened, Epic T is
unchanged and EPIC Y is unchanged.

Successful implementation authorizes only `POSTP1-002V2A-PAD5`. It does **not**
authorize `POSTP1-001V2A-I2`, `POSTP1-001V2R1`, `POSTP1-003R3`, `POSTP1-004` or
any prospective collection.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    decision = replay_verified_evidence_v1_definition(registry)
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
            raise ReplayVerifiedEvidenceDecisionError(
                f"persisted {filename} does not reproduce"
            )
        _verify_definition_digest(persisted)
        if decision["child_definition_sha256"].get(
            filename.removesuffix(".json")
        ) != expected["definition_sha256"]:
            raise ReplayVerifiedEvidenceDecisionError(
                f"the replay-verified evidence parent does not bind {filename}"
            )
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise ReplayVerifiedEvidenceDecisionError(
            "persisted replay-verified evidence report does not reproduce"
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
