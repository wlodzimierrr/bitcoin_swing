"""Frozen admitted return-state isolated scientific worker for the ETF calendar.

``POSTP1-002V2A-PAD4-R3`` independently regenerated the exact ``PAD4-R3``
candidate ``1fd9a2f9...d8bad0``, reproduced 25/25 material children and 25/25
parent bindings, and then failed it with::

    FAIL — CALLER-CREATED STATE CAN BECOME SCIENTIFIC AUTHORITY

The review reproduced a great deal as **valid** and a successor may not reopen,
rebuild or renegotiate it: the closed ``run_isolated_scientific_request``
authority flow and its capability-owning closure, the four-member bootstrap set
and its pre-execution binding on the authoritative path, fresh-exec process
isolation, Repair A's fresh empty per-worker bytecode-cache namespace, Repair
B's frozen source authority, Repair C's trusted controller authority context,
Repair D's third-party semantic and installed-content authority, the compiled
root witness, the closed AST store-use grammar, the exact eleven-owner graph and
the direct dependency-body rule.  Process isolation, bootstrap binding, bytecode
authority, third-party authority, the worker protocol and the calendar science
all stay closed.

The blocking invariant was a **return-state / authority-container** defect,
local to one module's post-admission representation::

    A caller-created post-admission result can remain inside an admitted,
    affirmatively authoritative R3 execution without matching the bound result
    digest.

Admission itself was correct.  The failure happened *after* successful
admission: ``PAD4-R3`` stored its authority as ``dict(material)`` — a shallow
copy whose ``response`` value was the live protocol-parser mapping and whose
``result`` value was that mapping's own nested ``result`` object — and handed
those very objects back from ``execution.result`` and ``execution.response``.
Mutating the returned mapping therefore rewrote the authority-bearing state of
an admitted, affirmatively stamped execution, while the bound ``result_digest``
kept describing what had actually been admitted.

``POSTP1-001V2A-PAD4-R4`` corrects exactly that and nothing else.  It is a
bounded correction of ``PAD4-R3`` and is deliberately **not** a ``PAD5``: no new
proof-architecture family is created, and the failed ``PAD4``
``cc1b325a...7b809e78``, ``PAD4-R1`` ``3415765f...fde37ebc``, ``PAD4-R2``
``68e6bd07...e52561`` and ``PAD4-R3`` ``1fd9a2f9...d8bad0`` namespaces all stay
immutable, non-certified, unused and at zero observations.  The frozen rule is::

    ONCE SCIENTIFIC ADMISSION SUCCEEDS, NO CALLER MUTATION MAY CHANGE THE
    AUTHORITATIVE RESPONSE, RESULT OR AFFIRMATIVE EVIDENCE REPRESENTED BY THAT
    ADMITTED EXECUTION.

The correction is **structural, not a defensive copy bolted onto an accessor**.
The authority-bearing storage stops being a Python container at all.  Successful
admission canonicalises the exact validated response and result with the
already-reviewed protocol serialisation, binds the exact result digest to those
canonical bytes, and stores nothing but ``bytes``, ``str``, ``bool`` and
``None``::

    validated response/result
    -> canonical deterministic bytes
    -> digest over those exact bytes
    -> successful admission
    -> immutable canonical bytes retained as authoritative truth

Affirmative evidence is then constructed *from* that immutable snapshot, frozen
into canonical bytes of its own, and only then does the admitted execution
become caller-visible.  The three mapping-like accessors — ``result``,
``response`` and ``scientific_evidence`` — are fresh deterministic decodes of
those frozen bytes on every call, so a caller receives a wholly detached object
graph and there is no nested descendant, no outer read-only wrapper and no
shared alias between caller-visible state and authority.  A mechanical
return-state audit proves that statically, and
``authoritative_snapshot_proof()`` reproduces the bound digests from the frozen
bytes alone, never from a caller-visible object.

``PAD4-R3``'s construction authority is untouched: an
``AuthoritativeScientificExecution`` is still obtainable only as the return
value of the one closed operation, and a ``__new__``, subclass or direct
construction still carries no material and refuses every accessor.  ``R4``
changes post-admission *representation* immutability, not the already-reviewed
construction authority.

The corrected proof strategy is::

    IMMUTABLE_CANONICAL_ADMITTED_SNAPSHOT_AUTHORITY
    + AUTHORITATIVE_SCIENTIFIC_EXECUTION_CLOSURE
    + BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING
    + CERTIFIED_SOURCE_AUTHORITY
    + FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY
    + FROZEN_CPYTHON
    + FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE
    + CLOSED_STORE_GRAMMAR
    + COMPILED_ROOT_WITNESS
    + ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER
    + TRUSTED_CONTROLLER_AUTHORITY_CONTEXT

This module is a pre-data decision builder, a static audit specification and the
authoritative reference controller.  It never collects, persists, signs or
certifies anything, and it changes no ETF calendar production code.  The worker
package is reused byte-identically from ``PAD4-R2``: the bootstrap source set
and its digest ``1811e04d...ead411`` are unchanged, because this correction is
entirely parent-side.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import gc
import platform
import shutil
import subprocess
import sys
import textwrap
import types
from threading import Lock
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, NamedTuple, Sequence
from weakref import ref as weakref_ref

from btc_predictor.research import etf_calendar_compiled_binding_witness as witness
from btc_predictor.research import etf_calendar_isolated_scientific_worker as pad4
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r1 as r1
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r2 as r2
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r3 as r3
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r4 as r4
from btc_predictor.research import etf_calendar_runtime_owner_attestation as attestation
from btc_predictor.research import etf_calendar_store_capability_normal_form_r1 as narrow
from etf_calendar_worker import protocol_r2 as protocol


DECISION_VERSION = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
PROGRAM_TICKET = "POSTP1-001V2A-PAD4-R5"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_isolated_scientific_worker_v1_r5"
DEFINITION_FILENAME = "etf_calendar_isolated_scientific_worker_v1_r5_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R5_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_REVIEW"
FINAL_CLASSIFICATION = (
    "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R5_READY_FOR_FINAL_XHIGH_REVIEW"
)
PROOF_STRATEGY = (
    "EXACT_EXECUTION_IDENTITY_BINDING_PLUS_"
    "IMMUTABLE_CANONICAL_ADMITTED_SNAPSHOT_AUTHORITY_PLUS_"
    "AUTHORITATIVE_SCIENTIFIC_EXECUTION_CLOSURE_PLUS_"
    "BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_PLUS_CERTIFIED_SOURCE_AUTHORITY_PLUS_"
    "FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY_PLUS_FROZEN_CPYTHON_PLUS_"
    "FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE_PLUS_CLOSED_STORE_GRAMMAR_PLUS_"
    "COMPILED_ROOT_WITNESS_PLUS_ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_PLUS_"
    "TRUSTED_CONTROLLER_AUTHORITY_CONTEXT"
)
REQUIRED_REVIEW = (
    "POSTP1-002V2A-PAD4-R5_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_"
    "PROOF_ARCHITECTURE_REVIEW"
)

#: The failed ``PAD4-R3`` parent this ticket corrects, preserved unchanged.
FAILED_PAD4_R3_SHA256 = (
    "1fd9a2f9d5e5318505a6c48241f243b358261c100f67c4bc5b2c43ac9bd8bad0"
)
FAILED_PAD4_R3_REVIEW = "POSTP1-002V2A-PAD4-R3"
FAILED_PAD4_R3_REVIEW_RESULT = (
    "FAIL — CALLER-CREATED STATE CAN BECOME SCIENTIFIC AUTHORITY"
)
FAILED_PAD4_R3_DECISION_COMMIT = "02c48103df8f435f29cf073074f2c75259ff18f3"
FAILED_PAD4_R3_REVIEW_COMMIT = "677df17429678afa3d73815d72eab62ad1111f33"
FAILED_PAD4_R3_EXECUTION_CLASSIFICATION = (
    "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R3_REQUIRES_FIX"
)
FAILED_PAD4_R2_SHA256 = r3.FAILED_PAD4_R2_SHA256
FAILED_PAD4_R4_SHA256 = "ae25c2468972725a0ebd2f7742a532f3ec616c2e2cc8e94d93b3de46f86e65bc"
FAILED_PAD4_R4_REVIEW = "POSTP1-002V2A-PAD4-R4"
FAILED_PAD4_R4_REVIEW_RESULT = "FAIL — AUTHORITATIVE EXECUTION CONSTRUCTION BOUNDARY INVALID"
FAILED_PAD4_R4_REVIEW_COMMIT = "9514d41ba9542e747dd2d35ec83d89dc73740a74"
FAILED_PAD4_R4_GOVERNANCE_COMMIT = "6794a7354de4a5515b736d0291b4afd5dc61d902"
FAILED_PAD4_R4_EXECUTION_CLASSIFICATION = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R4_REQUIRES_FIX"
FAILED_PAD4_R1_SHA256 = r3.FAILED_PAD4_R1_SHA256
FAILED_PAD4_SHA256 = r3.FAILED_PAD4_SHA256

#: The one blocking finding this bounded correction repairs, and the material
#: consistency obligation the completed review attached to it.
REPAIRED_REVIEW_FINDINGS: tuple[str, ...] = (
    "P0_UNEARNED_RESOLUTION_EQUALITY_KEYED_BINDING_CAN_RESOLVE_FOREIGN_RECEIVER",
    "P0_CONSTRUCTION_IDENTITY_AUDIT_MUST_BEHAVIORALLY_PROVE_EXACT_RECEIVER_IDENTITY",
)

#: The exact post-admission mutations ``POSTP1-002V2A-PAD4-R3`` established
#: against the reviewed ``PAD4-R3`` controller, each of which this correction
#: must close and each of which has a mandatory regression here.
CLOSED_REVIEWED_RETURN_STATE_MUTATIONS: tuple[str, ...] = (
    "CALLER_MUTATED_RETURNED_RESPONSE_MAPPING_CHANGED_ADMITTED_AUTHORITY",
    "CALLER_MUTATED_RETURNED_RESULT_MAPPING_CHANGED_ADMITTED_AUTHORITY",
    "LIVE_AUTHORITATIVE_STATE_STOPPED_MATCHING_THE_BOUND_RESULT_DIGEST",
    "RETURNED_RESPONSE_AND_RETURNED_RESULT_SHARED_MUTABLE_DESCENDANTS",
)

#: Independently reproduced as valid by ``POSTP1-002V2A-PAD4-R3``, carried
#: forward intact, and explicitly *not* rebuilt or renegotiated here.
PRESERVED_VALID_PORTIONS: tuple[str, ...] = tuple(
    sorted(
        {
            *r3.PRESERVED_VALID_PORTIONS,
            "AUTHORITATIVE_SCIENTIFIC_EXECUTION_CLOSURE",
            "CAPABILITY_OWNED_CONSTRUCTION_AUTHORITY",
            "CLOSED_ONE_OPERATION_AUTHORITY_FLOW",
            "SCIENTIFIC_ADMISSION_DECISION_PROCEDURE",
        }
    )
)

#: Explicitly *not* reopened by this correction.
NOT_REOPENED: tuple[str, ...] = tuple(
    sorted(
        {
            *r3.NOT_REOPENED,
            "AUTHORITATIVE_EXECUTION_CONSTRUCTION_AUTHORITY",
            "CLOSED_CONTROLLER_AUTHORITY_FLOW",
            "SCIENTIFIC_ADMISSION_DECISION_PROCEDURE",
            "WORKER_PROTOCOL",
        }
    )
)

#: Confirmed by earlier independent review as **not** a defect.  Carried
#: forward unchanged and not reopened.
CONFIRMED_NOT_A_DEFECT: tuple[str, ...] = r3.CONFIRMED_NOT_A_DEFECT

PROJECT_ROOT = r3.PROJECT_ROOT
CALENDAR_MODULE = witness.CALENDAR_MODULE
CALENDAR_SOURCE = witness.CALENDAR_SOURCE
CERTIFIED_DEPENDENCY_VERSION = witness.CERTIFIED_DEPENDENCY_VERSION
CERTIFIED_DEPENDENCY_SHA256 = witness.CERTIFIED_DEPENDENCY_SHA256
FAILED_ARCHITECTURE_LINEAGE = (
    *r4.FAILED_ARCHITECTURE_LINEAGE,
    FAILED_PAD4_R4_SHA256,
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

#: This module's own path, used by the mechanical audits.  It is a *relative*
#: path resolved under the certified project root so that every audit is
#: reproducible from any working directory.
CONTROLLER_RELATIVE_PATH = (
    "btc_predictor/research/etf_calendar_isolated_scientific_worker_r5.py"
)

#: The deliberately non-production raw reproduction harness.  It is reused
#: byte-identically from ``PAD4-R3``: it is not authority, it is not production
#: scientific-controller code, it lives outside the certified worker source
#: universe, and the reviewed ``PAD4-R2`` bypass controls it exists to reproduce
#: are unchanged by this bounded return-state correction.  Forking it would add
#: a fifth near-identical raw spawn to the repository for no proof value.
RAW_REVIEW_HARNESS_RELATIVE_PATH = r3.RAW_REVIEW_HARNESS_RELATIVE_PATH

#: The superseded, failed, non-certified controller modules.  They are kept
#: byte-identical so their own frozen namespaces keep reproducing; none of them
#: is R4 authority and this module never delegates admission, freezing or
#: evidence to them.
FAILED_LINEAGE_CONTROLLER_MODULES: tuple[str, ...] = (
    *r4.FAILED_LINEAGE_CONTROLLER_MODULES,
    r4.CONTROLLER_RELATIVE_PATH,
)


class IsolatedScientificWorkerR5Error(r4.IsolatedScientificWorkerR4Error):
    """Raised when the frozen-return-state worker architecture must refuse."""


class AuthoritativeExecutionConstructionError(
    r4.AuthoritativeExecutionConstructionError
):
    """Raised when authoritative scientific material is not controller-owned.

    Every raise means a caller tried to obtain, fabricate, read or store
    affirmative scientific authority that the closed controller operation did
    not create as an immutable canonical snapshot.
    """


BootstrapSourcePreVerificationError = r4.BootstrapSourcePreVerificationError


def _revised(base: Mapping[str, Any], **overrides: Any) -> dict[str, Any]:
    """Re-freeze a reviewed ``PAD4-R3`` child contract under this parent.

    Every preserved contract is carried forward as the exact reviewed payload
    plus the enumerated corrections, so a reviewer can diff a child against its
    ``PAD4-R3`` original instead of re-reading a restatement.
    """

    payload = {
        name: value for name, value in base.items() if name != "definition_sha256"
    }
    payload.update(overrides)
    return _definition(payload)


# ---------------------------------------------------------------------------
# Preserved, reviewed and reused from PAD4-R3
# ---------------------------------------------------------------------------
#
# The worker package, its bootstrap set, the bootstrap pre-execution binding,
# the certified source manifests, the third-party authority, the launch material
# and the fresh-pycache architecture are all reproduced from the reviewed
# ``PAD4-R3`` owners rather than forked.  ``POSTP1-002V2A-PAD4-R3`` reproduced
# each of them as valid, and this correction is entirely post-admission and
# parent-side.

WORKER_SOURCE_MANIFEST_VERSION = r3.WORKER_SOURCE_MANIFEST_VERSION
WORKER_ENTRYPOINT_MODULE = r3.WORKER_ENTRYPOINT_MODULE
WORKER_ENTRYPOINT_RELATIVE_PATH = r3.WORKER_ENTRYPOINT_RELATIVE_PATH
WORKER_PROTOCOL_MODULE = r3.WORKER_PROTOCOL_MODULE
WORKER_PROTOCOL_RELATIVE_PATH = r3.WORKER_PROTOCOL_RELATIVE_PATH
WORKER_PACKAGE_MODULE = r3.WORKER_PACKAGE_MODULE
WORKER_PACKAGE_RELATIVE_PATH = r3.WORKER_PACKAGE_RELATIVE_PATH
CERTIFIED_PACKAGE_ROOTS = r3.CERTIFIED_PACKAGE_ROOTS
REQUIRED_WORKER_PROJECT_MODULES = r3.REQUIRED_WORKER_PROJECT_MODULES

PRE_I2_FIXTURE_SEED_MODULE = r3.PRE_I2_FIXTURE_SEED_MODULE
PRE_I2_FIXTURE_VERSION = r3.PRE_I2_FIXTURE_VERSION
PRE_I2_FIXTURE_ROLE = r3.PRE_I2_FIXTURE_ROLE
PRE_I2_FIXTURE_MODULE_COUNT = r3.PRE_I2_FIXTURE_MODULE_COUNT
PRE_I2_FIXTURE_MANIFEST_DIGEST = r3.PRE_I2_FIXTURE_MANIFEST_DIGEST

BOOTSTRAP_SOURCE_SET_VERSION = r3.BOOTSTRAP_SOURCE_SET_VERSION
BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE = (
    r3.BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE
)
BOOTSTRAP_PRE_VERIFICATION_VERSION = r3.BOOTSTRAP_PRE_VERIFICATION_VERSION
BOOTSTRAP_PRE_VERIFICATION_CHECKS = r3.BOOTSTRAP_PRE_VERIFICATION_CHECKS
WORKER_BOOTSTRAP_SOURCE_SET = r3.WORKER_BOOTSTRAP_SOURCE_SET
WORKER_BOOTSTRAP_RELATIVE_PATHS = r3.WORKER_BOOTSTRAP_RELATIVE_PATHS
WORKER_BOOTSTRAP_MODULES = r3.WORKER_BOOTSTRAP_MODULES
BOOTSTRAP_EXECUTION_ORDER = r3.BOOTSTRAP_EXECUTION_ORDER
BOOTSTRAP_PACKAGE_ROOT = r3.BOOTSTRAP_PACKAGE_ROOT
BOOTSTRAP_GUARDED_SCOPE = r3.BOOTSTRAP_GUARDED_SCOPE

derive_bootstrap_source_set = r3.derive_bootstrap_source_set
derive_project_source_manifest = r3.derive_project_source_manifest
external_import_roots = r3.external_import_roots
audit_bootstrap_execution_order = r3.audit_bootstrap_execution_order
audit_bootstrap_source_set = r3.audit_bootstrap_source_set
audit_authoritative_worker_source = r3.audit_authoritative_worker_source
certified_universe_closed_worker_rule_modules = (
    r3.certified_universe_closed_worker_rule_modules
)
module_level_declared_imports = r3.module_level_declared_imports
deferred_declared_imports = r3.deferred_declared_imports

FROZEN_PRE_I2_SOURCE_ROWS = r3.FROZEN_PRE_I2_SOURCE_ROWS
FROZEN_WORKER_PACKAGE_ROWS = r3.FROZEN_WORKER_PACKAGE_ROWS
CANDIDATE_SOURCE_MODULE_COUNT = r3.CANDIDATE_SOURCE_MODULE_COUNT
frozen_pre_i2_source_manifest = r3.frozen_pre_i2_source_manifest
frozen_candidate_source_manifest = r3.frozen_candidate_source_manifest
frozen_bootstrap_source_manifest = r3.frozen_bootstrap_source_manifest
verify_frozen_pre_i2_fixture = r3.verify_frozen_pre_i2_fixture
verify_frozen_bootstrap_set_is_complete = r3.verify_frozen_bootstrap_set_is_complete
verify_worker_protocol_binds_the_frozen_interpreter = (
    r3.verify_worker_protocol_binds_the_frozen_interpreter
)

THIRD_PARTY_REGISTRY_VERSION = r3.THIRD_PARTY_REGISTRY_VERSION
FROZEN_THIRD_PARTY_AUTHORITY_ROWS = r3.FROZEN_THIRD_PARTY_AUTHORITY_ROWS
frozen_third_party_authority = r3.frozen_third_party_authority
derive_third_party_authority = r3.derive_third_party_authority
observe_installed_distributions = r3.observe_installed_distributions

WORKER_LAUNCH_CONTRACT = r3.WORKER_LAUNCH_CONTRACT
WORKER_LAUNCH_FLAGS = r3.WORKER_LAUNCH_FLAGS
WORKER_LAUNCH_X_OPTION = r3.WORKER_LAUNCH_X_OPTION
EXEC_LAUNCH = r3.EXEC_LAUNCH
FORK_WITHOUT_EXEC = r3.FORK_WITHOUT_EXEC
FORK_SERVER_REUSE = r3.FORK_SERVER_REUSE
AUTHORIZED_LAUNCH_MECHANISMS = r3.AUTHORIZED_LAUNCH_MECHANISMS
UNAUTHORIZED_LAUNCH_MECHANISMS = r3.UNAUTHORIZED_LAUNCH_MECHANISMS
FROZEN_WORKER_ENVIRONMENT = r3.FROZEN_WORKER_ENVIRONMENT

authorize_worker_launch_mechanism = r3.authorize_worker_launch_mechanism
controller_pycache_root = r3.controller_pycache_root
create_fresh_pycache_namespace = r3.create_fresh_pycache_namespace
allocate_worker_pycache_namespace = r3.allocate_worker_pycache_namespace
interpreter_base_sys_path = r3.interpreter_base_sys_path
parent_site_paths = r3.parent_site_paths

WorkerLaunch = r3.WorkerLaunch
worker_launch = r3.worker_launch

compiled_root_binding_witness = r3.compiled_root_binding_witness
direct_dependency_body_findings = r3.direct_dependency_body_findings
verify_current_production_expected_result = r3.verify_current_production_expected_result


# ---------------------------------------------------------------------------
# Repair C — the trusted controller authority context, R4 identity
# ---------------------------------------------------------------------------

AUTHORITY_CONTEXT_VERSION = "ETF_CALENDAR_SCIENTIFIC_WORKER_AUTHORITY_CONTEXT_V1_R5"
AUTHORITY_CONSTRUCTION_REFREEZE = r3.AUTHORITY_CONSTRUCTION_REFREEZE
FINAL_CALENDAR_AUTHORITY = r3.FINAL_CALENDAR_AUTHORITY
REVIEW_CANDIDATE_CONTEXT = r3.REVIEW_CANDIDATE_CONTEXT
AUTHORITY_CONTEXT_ORIGINS = r3.AUTHORITY_CONTEXT_ORIGINS
FINAL_CALENDAR_AUTHORITY_WORKER_FIELD = r3.FINAL_CALENDAR_AUTHORITY_WORKER_FIELD
PRODUCTION_CONTEXT_NOT_YET_BOUND = r3.PRODUCTION_CONTEXT_NOT_YET_BOUND

#: The worker protocol is reused byte-identically from ``PAD4-R2``, so the
#: *worker protocol* authority ticket carried in the request and echoed in the
#: response stays ``POSTP1-001V2A-PAD4-R2``.  That field identifies the frozen
#: worker protocol, not the proof architecture; the proof architecture is
#: identified by ``proof_architecture_sha256`` — this candidate's own parent
#: hash — and by ``PROGRAM_TICKET``.
WORKER_PROTOCOL_AUTHORITY_TICKET = r3.WORKER_PROTOCOL_AUTHORITY_TICKET


@dataclass(frozen=True)
class ScientificWorkerAuthorityContext(r4.ScientificWorkerAuthorityContext):
    """The trusted expected values launch, request and admission all use.

    ``POSTP1-002V2A-PAD4-R3`` reproduced the ``PAD4-R3`` context as **valid**, so
    its fields, canonicalisation and three-way agreement are inherited unchanged
    rather than restated.  What this subclass adds is *type identity*: the closed
    authoritative operation accepts only an ``R4`` trusted context, so a
    superseded failed-lineage context cannot be carried into this architecture's
    authority.

    ``R4`` extends the guarantee.  Under ``PAD4-R3`` the three-way agreement
    ``request == context``, ``response == context`` and ``response == request``
    was established through admission, and the admitted state it agreed with
    could then be rewritten by a caller.  Here the agreement holds for the whole
    lifetime of the returned authoritative execution, because the state it
    agreed with is an immutable canonical snapshot that nothing can rewrite.
    """

    def as_evidence(self) -> dict[str, Any]:
        """Deterministic, address-free identity of the trusted context."""

        payload = super().as_evidence()
        payload["authority_context_version"] = AUTHORITY_CONTEXT_VERSION
        payload["proof_architecture_program_ticket"] = PROGRAM_TICKET
        return payload


def _as_r5_context(
    context: r4.ScientificWorkerAuthorityContext,
) -> ScientificWorkerAuthorityContext:
    """Rebind a reviewed ``PAD4-R3`` context builder result to the R4 type."""

    return ScientificWorkerAuthorityContext(
        origin=context.origin,
        proof_architecture_version=context.proof_architecture_version,
        proof_architecture_ticket=context.proof_architecture_ticket,
        proof_architecture_sha256=context.proof_architecture_sha256,
        interpreter_identity=dict(context.interpreter_identity),
        project_source_manifest=context.project_source_manifest,
        project_source_manifest_role=context.project_source_manifest_role,
        worker_bootstrap_manifest=context.worker_bootstrap_manifest,
        required_project_modules=context.required_project_modules,
        third_party_authority=context.third_party_authority,
        calendar_authority_version=context.calendar_authority_version,
        calendar_authority_sha256=context.calendar_authority_sha256,
        trusted_persistence_authority_sha256=(
            context.trusted_persistence_authority_sha256
        ),
    )


def candidate_review_authority_context(
    proof_architecture_sha256: str,
    *,
    origin: str = REVIEW_CANDIDATE_CONTEXT,
) -> ScientificWorkerAuthorityContext:
    """The trusted context used while this candidate is under review.

    ``POSTP1-002V2A-PAD4-R2`` independently re-evaluated that this constructor
    accepts any well-formed SHA and **confirmed it is not a defect**: the
    controller modules read no environment variable, and no scientific request,
    worker or environment can select the bound hash.  It is therefore not
    reopened, and behaviour is unchanged.
    """

    return _as_r5_context(
        r4.candidate_review_authority_context(proof_architecture_sha256, origin=origin)
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
    it is explicitly not a runtime operation.  Runtime consumes an already
    frozen context.
    """

    return _as_r5_context(
        r4.derive_authority_context_from_reviewed_source(
            proof_architecture_sha256, project_root=project_root, origin=origin
        )
    )


def production_authority_context_from_calendar_authority(
    calendar_authority: Mapping[str, Any],
) -> ScientificWorkerAuthorityContext:
    """The frozen production rule: the context comes from the final authority.

    ``POSTP1-001V2A-I2`` must bind the *certified* successor hash, the exact
    final post-I2 source manifest, the exact final bootstrap source set and the
    reviewed third-party authority into the final calendar authority.  Until it
    does, there is no production context and this refuses.
    """

    return _as_r5_context(
        r4.production_authority_context_from_calendar_authority(calendar_authority)
    )


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

    Building a request is *not* an authority-bearing operation: a request is only
    ever an input to the closed authoritative execution, it can never be admitted
    by itself, and it can never produce evidence.  The reviewed ``PAD4-R3``
    builder is reused unchanged, with the R4 trusted-context type required.

    The mapping returned here is the caller's own object.  The closed flow reads
    it, canonicalises what it sends and binds the request digest; it never keeps
    a reference to it in authority-bearing storage, so mutating or discarding it
    afterwards cannot reach an admitted execution.
    """

    require_trusted_authority_context(authority_context)
    return r4.build_scientific_request(
        authority_context,
        launch=launch,
        operation=operation,
        operation_inputs=operation_inputs,
        evidence_records=evidence_records,
        decision_time=decision_time,
        evidence_admission_mode=evidence_admission_mode,
    )


def require_trusted_authority_context(
    authority_context: Any,
) -> ScientificWorkerAuthorityContext:
    """Only an ``R4`` trusted controller context may reach this architecture."""

    if not isinstance(authority_context, ScientificWorkerAuthorityContext):
        raise IsolatedScientificWorkerR5Error(
            "the frozen-return-state scientific architecture requires an R4 "
            "trusted controller authority context, not "
            f"{type(authority_context).__name__}"
        )
    return authority_context


def preverify_worker_bootstrap_sources(
    authority_context: ScientificWorkerAuthorityContext,
    launch: WorkerLaunch,
) -> dict[str, Any]:
    """Bind every bootstrap source before any of it can execute.

    The reviewed ``PAD4-R3`` implementation is reused unchanged: the review
    reproduced it as valid on the authoritative path, with all four bootstrap
    members refusing before spawn, zero subprocesses, zero pycache allocations
    and markers absent.

    The mapping this returns is **diagnostic, not authority**.  Its presence,
    shape or contents can never make an outcome admissible, because R4 never
    reads a pre-verification mapping to decide admission: it decides on whether
    the closed controller operation itself performed the pre-verification.
    """

    require_trusted_authority_context(authority_context)
    return r4.preverify_worker_bootstrap_sources(authority_context, launch)


def verify_request_against_authority_context(
    authority_context: ScientificWorkerAuthorityContext,
    request: Mapping[str, Any],
) -> tuple[str, ...]:
    """Every material authority field of the request must be the trusted one.

    This is a pure comparison.  It returns the drifted field names and it is
    never, by itself, an admission: it cannot admit, it cannot create an
    execution and it cannot produce evidence.
    """

    return r4.verify_request_against_authority_context(authority_context, request)


def verify_response_against_authority_context(
    authority_context: ScientificWorkerAuthorityContext,
    response: Mapping[str, Any],
) -> tuple[str, ...]:
    """Every material authority field of the response must be the trusted one.

    A pure comparison, exactly as above: it admits nothing and evidences
    nothing.
    """

    return r4.verify_response_against_authority_context(authority_context, response)


# ---------------------------------------------------------------------------
# The correction — the frozen admitted return state
# ---------------------------------------------------------------------------

AUTHORITATIVE_EXECUTION_BOUNDARY_VERSION = (
    "ETF_CALENDAR_AUTHORITATIVE_SCIENTIFIC_EXECUTION_BOUNDARY_V1_R5"
)

AUTHORITATIVE_RETURN_STATE_VERSION = (
    "ETF_CALENDAR_AUTHORITATIVE_ADMITTED_RETURN_STATE_V1_R4"
)

#: The one affirmative authority marker.  It is constructed at exactly one site,
#: inside the closed controller operation, from the immutable canonical admitted
#: snapshot, and the mechanical API-closure audit proves that no other
#: project-owned module and no other call site in this module can produce it.
#: Superseded failed-lineage evidence builders cannot emit it, so an admitted
#: ``PAD4-R3`` evidence payload — including one a caller mutated after
#: admission — can never be mistaken for affirmative ``R4`` scientific
#: authority.
AUTHORITATIVE_SCIENTIFIC_AUTHORITY = "AUTHORITATIVE_CLOSED_CONTROLLER_EXECUTION_V1_R5"

#: The stamp every non-authoritative execution must carry instead.  Reused
#: unchanged so the reviewed raw-execution controls keep their exact meaning.
NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY = r3.NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY

#: The closed controller order, exactly as ``run_isolated_scientific_request``
#: performs it.  Nothing may enter at step 6 or later, and step 13 is a property
#: of the returned object rather than a further controller action: it is frozen
#: here because it is the step ``PAD4-R3`` did not have.
AUTHORITATIVE_EXECUTION_ORDER: tuple[str, ...] = (
    "1_RECEIVE_THE_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT",
    "2_VALIDATE_THE_REQUEST_AGAINST_THE_TRUSTED_AUTHORITY",
    "3_PREVERIFY_THE_COMPLETE_BOOTSTRAP_SOURCE_SET",
    "4_ALLOCATE_THE_FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE",
    "5_SPAWN_THE_EXACT_WORKER_AND_OBTAIN_THE_EXACT_EXECUTION_RESULT",
    "6_VALIDATE_THE_RESPONSE_PROTOCOL_INSIDE_THE_SAME_CLOSED_FLOW",
    "7_CANONICALIZE_THE_EXACT_VALIDATED_RESPONSE_AND_RESULT",
    "8_VERIFY_AND_BIND_THE_EXACT_RESULT_DIGEST_TO_THOSE_CANONICAL_BYTES",
    "9_PERFORM_SUCCESSFUL_SCIENTIFIC_ADMISSION_INSIDE_THAT_FLOW",
    "10_STORE_THE_IMMUTABLE_CANONICAL_ADMITTED_SNAPSHOT_AS_AUTHORITATIVE_TRUTH",
    "11_CONSTRUCT_AFFIRMATIVE_EVIDENCE_FROM_THAT_IMMUTABLE_AUTHORITATIVE_TRUTH",
    "12_RETURN_THE_AUTHORITATIVE_EXECUTION",
    "13_SERVE_CALLER_FACING_ACCESS_WITHOUT_EXPOSING_AUTHORITY_BY_MUTABLE_REFERENCE",
)

#: The material an ``AuthoritativeScientificExecution`` exposes.  Every one of
#: these is produced by the closed flow and by nothing else.
AUTHORITATIVE_EXECUTION_MATERIAL: tuple[str, ...] = (
    "admitted",
    "authoritative_snapshot_proof",
    "failure_reason",
    "request_digest",
    "response",
    "result",
    "scientific_evidence",
)

#: The caller-facing accessors that hand back a *mutable* Python structure for
#: convenience.  Each one must be a fresh deterministic decode of the frozen
#: canonical bytes, so the object a caller receives is detached from authority
#: and detached from every other returned object.
MUTABLE_CONVENIENCE_ACCESSORS: tuple[str, ...] = (
    "response",
    "result",
    "scientific_evidence",
)

#: The caller-facing accessors that return an immutable value straight out of
#: the frozen snapshot.  There is nothing to detach, because there is nothing a
#: caller could mutate.
IMMUTABLE_CONVENIENCE_ACCESSORS: tuple[str, ...] = (
    "admitted",
    "failure_reason",
    "request_digest",
)

#: The exact authority-bearing storage.  These nine names are the *whole* of
#: what an admitted execution represents, and every one of them holds a
#: ``bytes``, ``str``, ``bool`` or ``None`` — never a ``dict``, ``list``,
#: ``set`` or any other caller-mutable container.  There is therefore no nested
#: descendant for a caller to reach, and no read-only wrapper is needed: an
#: outer ``MappingProxyType`` over a mutable graph is explicitly *not* the
#: mechanism here and is explicitly not sufficient.
FROZEN_AUTHORITY_FIELDS: tuple[str, ...] = (
    "admitted",
    "affirmative_evidence_bytes",
    "affirmative_evidence_digest",
    "failure_reason",
    "request_digest",
    "response_bytes",
    "response_digest",
    "result_bytes",
    "result_digest",
)

#: The only value types authority-bearing storage may hold, and exactly the four
#: the nine frozen fields actually hold: ``bool`` for the admitted flag, ``bytes``
#: for each canonical snapshot, ``str`` for each digest and ``None`` where a
#: refusal binds no digest.  Every one is immutable and none has a mutable
#: descendant, which — together with the immutable snapshot container — is what
#: makes the store in ``__init__`` a complete freeze rather than the shallow copy
#: the review refused.
IMMUTABLE_AUTHORITY_VALUE_TYPES: tuple[type, ...] = (bool, bytes, str, type(None))

#: The canonical serialisation the authority is stored as.  It is the already
#: reviewed worker-protocol canonicalisation, reused rather than reinvented: a
#: second competing notion of canonical JSON would be a second authority.
CANONICAL_AUTHORITY_ENCODER = "etf_calendar_worker.protocol_r1.canonical_json_bytes"
CANONICAL_AUTHORITY_DECODER = "etf_calendar_worker.protocol_r1.parse_canonical_json"
CANONICAL_AUTHORITY_DIGEST = "etf_calendar_worker.protocol_r1.digest_bytes"

#: Rejections the reused canonical protocol keeps enforcing, named by the exact
#: reason identifiers ``etf_calendar_worker.protocol_r1`` and ``protocol_r2``
#: raise rather than by invented labels, so a reviewer can grep each one.  R4
#: introduces no second encoding, so none of them is weakened.  One entry is
#: scope-qualified below because it is enforced on the request transport only.
PRESERVED_CANONICAL_REJECTIONS: tuple[str, ...] = (
    "CANONICAL_PAYLOAD_IS_NOT_ASCII",
    "CANONICAL_PAYLOAD_IS_NOT_ONE_JSON_DOCUMENT",
    "NON_FINITE_JSON_CONSTANT_REFUSED",
    "PAYLOAD_IS_NOT_CANONICAL_JSON_SERIALIZABLE",
    "REQUEST_FIELD_TYPE_REFUSED",
    "RESPONSE_SCHEMA_VERSION_REFUSED",
    "RESPONSE_SHAPE_REFUSED",
    "SCIENTIFIC_IPC_PAYLOAD_IS_NOT_CANONICAL",
    "UNKNOWN_RESPONSE_FIELD",
)

#: ``SCIENTIFIC_IPC_PAYLOAD_IS_NOT_CANONICAL`` is the re-serialisation equality
#: check, and the worker applies it to the *request* transport.  The controller's
#: own admission path parses and validates the response without a separate
#: re-serialisation equality check, so the response's canonical identity is
#: established by the frozen snapshot this correction stores rather than by a
#: transport rejection.  Naming the scope is the honest alternative to implying a
#: response-side rejection that does not exist.
REQUEST_TRANSPORT_ONLY_CANONICAL_REJECTIONS: tuple[str, ...] = (
    "SCIENTIFIC_IPC_PAYLOAD_IS_NOT_CANONICAL",
)

#: The canonical UTC timestamp rejection the reused protocol raises.  It is a
#: field-semantics rejection rather than a serialisation one, so it is named
#: separately instead of being folded into the list above.
PRESERVED_TIMESTAMP_REJECTION = "TIMESTAMP_IS_NOT_CANONICAL_UTC"


class FrozenAuthoritySnapshot(NamedTuple):
    """The complete admitted authority, as an immutable tuple of immutable values.

    ``PAD4-R3`` stored its authority in a ``dict`` and handed that dict back, and
    the review refused it.  Freezing only the *members* of a ``dict`` is not
    enough either: the container itself still has ``__setitem__``, ``update``,
    ``setdefault`` and ``pop``, so anything holding the mapping can rewrite a
    field, promote a refusal to an admitted execution, or make the affirmative
    evidence describe something that was never admitted.  A ``tuple`` subclass
    has no mutating API at all, in pure Python or through ``object.__setattr__``,
    so an admitted snapshot cannot be changed in place by anything.

    This type is **inert**.  It carries no capability, it grants nothing, and a
    caller may construct one freely: an ``AuthoritativeScientificExecution`` is
    still obtainable only from ``run_isolated_scientific_request``, which is what
    makes a snapshot useless without the closed flow that produced it.
    """

    admitted: bool
    affirmative_evidence_bytes: bytes
    affirmative_evidence_digest: str
    failure_reason: str | None
    request_digest: str
    response_bytes: bytes
    response_digest: str
    result_bytes: bytes
    result_digest: str | None


def verify_frozen_authority_snapshot(material: Any) -> FrozenAuthoritySnapshot:
    """Accept only a complete, wholly immutable admitted snapshot.

    This is the single gate every authority-bearing value passes through, and it
    is deliberately module-level and behaviourally testable: a guard hidden
    inside the closure could have its whole body deleted without any mechanical
    audit noticing, which would leave the correction resting on an unverified
    claim.  Being callable proves nothing and grants nothing — it validates a
    mapping and returns an inert immutable tuple.

    The exact frozen field set is required, and every value must be ``bool``,
    ``bytes``, ``str`` or ``None``.  A ``dict``, ``list``, ``set``,
    ``bytearray`` or any other caller-mutable container refuses rather than being
    copied, because a container reaching this point would mean the canonicalising
    freeze upstream had been bypassed.
    """

    if not isinstance(material, Mapping):
        raise AuthoritativeExecutionConstructionError(
            "an authoritative snapshot must be a mapping of the frozen authority "
            f"fields, not {type(material).__name__}"
        )
    # Materialise once.  Validating one mapping and then constructing from a
    # second read of it would let a mapping whose ``__getitem__`` answers
    # differently on a second call be checked on an immutable value and built from
    # a mutable one.  Every check below, and the construction itself, reads this
    # one materialised copy.
    candidate = dict(material)
    if sorted(candidate) != sorted(FROZEN_AUTHORITY_FIELDS):
        raise AuthoritativeExecutionConstructionError(
            "an authoritative snapshot must be exactly the frozen authority "
            f"field set, not {sorted(candidate)!r}"
        )
    mutable = sorted(
        name
        for name, value in candidate.items()
        if not isinstance(value, IMMUTABLE_AUTHORITY_VALUE_TYPES)
    )
    if mutable:
        raise AuthoritativeExecutionConstructionError(
            f"authoritative fields {mutable!r} are not immutable canonical "
            "material; authority is stored only as canonical bytes and immutable "
            "scalars"
        )
    return FrozenAuthoritySnapshot(**candidate)


#: Which frozen field each caller-facing accessor reads.  The mechanical
#: return-state audit checks this against the accessors' own AST, so an accessor
#: silently rebound to the wrong frozen field is a finding rather than a quiet
#: mis-answer.
ACCESSOR_FROZEN_FIELDS: Mapping[str, str] = {
    "admitted": "admitted",
    "failure_reason": "failure_reason",
    "request_digest": "request_digest",
    "response": "response_bytes",
    "result": "result_bytes",
    "scientific_evidence": "affirmative_evidence_bytes",
}


def _build_authoritative_scientific_execution_boundary() -> tuple[type, Callable[..., Any]]:
    """Create the one closed R5 authority boundary.

    R4's immutable canonical FrozenAuthoritySnapshot is preserved.  R5 changes
    only how that snapshot is associated with the returned execution.  _material
    is an integer-bucket registry: id(receiver) selects a bucket but grants no
    authority.  The bucket contains a weak live witness and the frozen snapshot.
    The single reader first applies the pinned exact-type defence in depth, then
    performs one registry fetch, and authority resolves only when
    live_witness is receiver.

    The registry never keys on the receiver or on weakref.ref(receiver), never
    invokes receiver-controlled equality/hash/class/getattr/bool/repr code, and
    never retains the execution strongly.  Weakref cleanup deletes a bucket only
    if its current witness is the exact callback witness, so a delayed callback
    cannot erase a newer entry after allocator identifier reuse.

    Closure-cell recovery, private-name reflection and module mutation remain
    outside the stated ordinary-caller domain.  Relay remains an open residual.
    """

    _capability = object()
    _registry_lock = Lock()
    _material: dict[int, tuple[Any, FrozenAuthoritySnapshot]] = {}

    def _refuse_unowned_receiver() -> None:
        raise AuthoritativeExecutionConstructionError(
            "this receiver is not the exact live controller-owned authoritative scientific execution identity"
        )

    def _cleanup_binding(bucket: int, dead_witness: Any) -> None:
        with _registry_lock:
            current = _material.get(bucket)
            if current is not None and current[0] is dead_witness:
                del _material[bucket]

    def _bind_authority(receiver: Any, capability: Any, material: Any) -> None:
        if capability is not _capability:
            _refuse_unowned_receiver()
        snapshot = verify_frozen_authority_snapshot(material)
        bucket = id(receiver)

        def cleanup(dead_witness: Any, bucket: int = bucket) -> None:
            _cleanup_binding(bucket, dead_witness)

        live_witness = weakref_ref(receiver, cleanup)
        with _registry_lock:
            _material[bucket] = (live_witness, snapshot)

    def _frozen(receiver: Any) -> FrozenAuthoritySnapshot:
        """The single exact-identity authority reader."""

        if receiver is None:
            _refuse_unowned_receiver()
        if type(receiver) is not AuthoritativeScientificExecution:
            _refuse_unowned_receiver()
        bucket = id(receiver)
        with _registry_lock:
            binding = _material.get(bucket)
        if binding is None:
            _refuse_unowned_receiver()
        live_witness = binding[0]()
        if live_witness is receiver:
            return binding[1]
        _refuse_unowned_receiver()

    class AuthoritativeScientificExecution:
        """One complete authoritative scientific execution and its evidence.

        An instance is obtainable only as the return value of
        ``run_isolated_scientific_request``.  Direct construction refuses, and an
        instance manufactured around ``__init__`` carries no material, so every
        accessor refuses rather than returning a fabricated answer.

        What the instance *represents* is fixed at successful admission and can
        never change afterwards.  It holds the immutable canonical bytes of the
        admitted response, the admitted result and the affirmative evidence, plus
        the digests bound to those exact bytes.  ``result``, ``response`` and
        ``scientific_evidence`` each decode their frozen bytes afresh, so a
        caller always receives a new, fully detached object graph: mutating one —
        at the top level, in a nested mapping or in a nested sequence — changes
        nothing about this execution, nothing about any other value it hands out,
        and nothing about any other execution.
        """

        __slots__ = ("__weakref__",)

        def __init_subclass__(cls, **kwargs: Any) -> None:
            """Refuse subclasses as non-load-bearing defence in depth."""

            raise AuthoritativeExecutionConstructionError(
                "the authoritative scientific execution type may not be subclassed"
            )

        def __init__(self, capability: Any = None, material: Any = None) -> None:
            _bind_authority(self, capability, material)

        @property
        def admitted(self) -> bool:
            return _frozen(self).admitted

        @property
        def failure_reason(self) -> str | None:
            return _frozen(self).failure_reason

        @property
        def request_digest(self) -> str:
            return _frozen(self).request_digest

        @property
        def result(self) -> Any:
            """A fresh decode of the immutable admitted result snapshot."""

            return protocol.parse_canonical_json(_frozen(self).result_bytes)

        @property
        def response(self) -> Mapping[str, Any] | None:
            """A fresh decode of the immutable admitted response snapshot."""

            return protocol.parse_canonical_json(_frozen(self).response_bytes)

        @property
        def scientific_evidence(self) -> dict[str, Any]:
            """A fresh decode of the immutable affirmative evidence snapshot."""

            return protocol.parse_canonical_json(
                _frozen(self).affirmative_evidence_bytes
            )

        def authoritative_snapshot_proof(self) -> dict[str, Any]:
            """Reproduce the bound digests from the frozen snapshot alone.

            Nothing here reads a caller-visible convenience object, and nothing
            here redefines authority: each ``*_recomputed_from_frozen_bytes``
            value is a SHA-256 over the exact immutable bytes this execution
            stores, and it must equal the digest bound at successful admission.
            This is how a reviewer establishes, without trusting an accessor,
            that what is represented now is what was admitted then.
            """

            snapshot = _frozen(self)
            bound = {
                "affirmative_evidence": (
                    snapshot.affirmative_evidence_digest,
                    protocol.digest_bytes(snapshot.affirmative_evidence_bytes),
                ),
                "response": (
                    snapshot.response_digest,
                    protocol.digest_bytes(snapshot.response_bytes),
                ),
                "result": (
                    snapshot.result_digest,
                    protocol.digest_bytes(snapshot.result_bytes),
                ),
            }
            return {
                "admitted": snapshot.admitted,
                # One uniform verdict a reviewer can apply on every path.  A
                # refusal binds no result digest, so an unbound digest is reported
                # as unbound rather than compared against the digest of the
                # canonical "no result" snapshot, which would read as a mismatch.
                "bound_digests_reproduce": all(
                    recomputed == declared
                    for declared, recomputed in bound.values()
                    if declared is not None
                ),
                "bound_digest_names": sorted(
                    name for name, (declared, _) in bound.items() if declared is not None
                ),
                "unbound_digest_names": sorted(
                    name for name, (declared, _) in bound.items() if declared is None
                ),
                "result_digest_is_bound": snapshot.result_digest is not None,
                "authoritative_return_state": AUTHORITATIVE_RETURN_STATE_VERSION,
                "bound_affirmative_evidence_digest": (
                    snapshot.affirmative_evidence_digest
                ),
                "bound_response_digest": snapshot.response_digest,
                "bound_result_digest": snapshot.result_digest,
                "affirmative_evidence_digest_recomputed_from_frozen_bytes": (
                    protocol.digest_bytes(snapshot.affirmative_evidence_bytes)
                ),
                "response_digest_recomputed_from_frozen_bytes": (
                    protocol.digest_bytes(snapshot.response_bytes)
                ),
                "result_digest_recomputed_from_frozen_bytes": (
                    protocol.digest_bytes(snapshot.result_bytes)
                ),
                "authority_snapshot_type": type(snapshot).__name__,
                "authority_snapshot_is_immutable": isinstance(snapshot, tuple),
                "authority_snapshot_field_types": {
                    name: type(value).__name__
                    for name, value in sorted(snapshot._asdict().items())
                },
                "authority_snapshot_holds_a_mutable_container": any(
                    not isinstance(value, IMMUTABLE_AUTHORITY_VALUE_TYPES)
                    for value in snapshot
                ),
            }

        def __repr__(self) -> str:  # pragma: no cover - diagnostic only
            snapshot = _frozen(self)
            return (
                "<AuthoritativeScientificExecution "
                f"admitted={snapshot.admitted!r} "
                f"failure_reason={snapshot.failure_reason!r}>"
            )

    def _execute_exact_worker(
        request: Mapping[str, Any],
        launch: WorkerLaunch,
        pycache_namespace: Path | None,
    ) -> dict[str, Any]:
        """Steps 4-5.  Closure-local: there is no module-accessible spawn."""

        authorize_worker_launch_mechanism(launch.mechanism)
        payload = protocol.canonical_json_bytes(request)
        if len(payload) > protocol.MAX_REQUEST_BYTES:
            raise IsolatedScientificWorkerR5Error(
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
            return {
                "exit_status": None,
                "timed_out": True,
                "stdout": expired.stdout or b"",
                "stderr": expired.stderr or b"",
                "request_digest": digest,
            }
        finally:
            if owned:
                shutil.rmtree(namespace, ignore_errors=True)
        return {
            "exit_status": completed.returncode,
            "timed_out": False,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
            "request_digest": digest,
        }

    def _validate_and_admit(
        authority_context: ScientificWorkerAuthorityContext,
        request: Mapping[str, Any],
        execution: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Steps 6-9.  Closure-local: there is no generic admission function.

        This is the reviewed ``PAD4-R3`` admission decision procedure, unchanged
        in every verdict it reaches, folded inside the closed flow rather than
        exposed as a separately callable authority-escalation operation.  It is
        unreachable with a caller-built outcome because it is unreachable at all
        from outside this closure.

        What ``R4`` changes is the *shape of what admission returns*.  ``PAD4-R3``
        returned the live protocol-parser mapping and its nested ``result``
        object, which then became the authority-bearing storage a caller could
        rewrite.  Admission here canonicalises the exact validated response and
        result (step 7), binds the exact result digest to those canonical bytes
        (step 8) and returns nothing but immutable values (step 9), so from this
        point on there is no mutable authority-bearing object anywhere in the
        flow.
        """

        def frozen(
            admitted: bool,
            failure_reason: str | None,
            response_bytes: bytes,
            result_bytes: bytes,
            result_digest: str | None,
        ) -> dict[str, Any]:
            """The admission verdict, carrying only immutable canonical values."""

            return {
                "admitted": admitted,
                "failure_reason": failure_reason,
                "response_bytes": response_bytes,
                "response_digest": protocol.digest_bytes(response_bytes),
                "result_bytes": result_bytes,
                "result_digest": result_digest,
            }

        def refuse(
            reason: str, response: Mapping[str, Any] | None = None
        ) -> dict[str, Any]:
            """A refusal represents no admitted result, canonically and always."""

            return frozen(
                False,
                reason,
                protocol.canonical_json_bytes(response),
                protocol.canonical_json_bytes(None),
                None,
            )

        def worker_refusal_payload() -> Mapping[str, Any] | None:
            """The worker's own refusal, reported but never trusted.

            A non-zero exit refuses before anything is parsed.  Parsing the
            payload afterwards is diagnostic only: it changes no verdict, it can
            only ever be attached to a refusal, and a payload that is not a
            well-formed canonical REFUSED response is simply dropped.  Without
            this the closed flow would be *less* informative than the surface it
            replaces, because the worker's reason would be unreachable.
            """

            payload = execution["stdout"]
            if not payload.endswith(b"\n") or payload.count(b"\n") != 1:
                return None
            try:
                parsed = protocol.validate_response(
                    protocol.parse_canonical_json(payload[:-1])
                )
            except protocol.ScientificWorkerProtocolError:
                return None
            if parsed["status"] == protocol.SUCCESS:
                return None
            return parsed

        drifted = verify_request_against_authority_context(authority_context, request)
        if drifted:
            return refuse(f"REQUEST_AUTHORITY_MISMATCH:{list(drifted)!r}")
        if execution["timed_out"]:
            return refuse("WORKER_TIMEOUT")
        if execution["exit_status"] != 0:
            return refuse(
                f"WORKER_EXIT_STATUS_{execution['exit_status']}",
                worker_refusal_payload(),
            )
        stdout = execution["stdout"]
        if len(stdout) > protocol.MAX_RESPONSE_BYTES:
            return refuse("WORKER_OUTPUT_EXCEEDS_THE_FROZEN_LIMIT")
        if not stdout.endswith(b"\n") or stdout.count(b"\n") != 1:
            return refuse("WORKER_STDOUT_IS_NOT_EXACTLY_ONE_PROTOCOL_PAYLOAD")
        try:
            parsed = protocol.validate_response(
                protocol.parse_canonical_json(stdout[:-1])
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
            "request_digest": execution["request_digest"],
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
        if parsed["sys_path_digest"] != protocol.digest_payload(
            list(request["sys_path"])
        ):
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

        # Step 7 — canonicalise the exact validated response, then take the
        # admitted result snapshot out of *that* frozen response snapshot rather
        # than out of the live parser object.  Response authority and result
        # authority therefore derive from one frozen canonical source and cannot
        # drift apart.
        response_bytes = protocol.canonical_json_bytes(parsed)
        frozen_response = protocol.parse_canonical_json(response_bytes)
        result_bytes = protocol.canonical_json_bytes(frozen_response["result"])
        bound_result_digest = frozen_response["result_digest"]

        # Step 8 — bind the exact result digest to those exact canonical bytes.
        # A divergence here is unreachable while the protocol canonicalisation
        # round-trips, which the reused encoder guarantees and the admitted
        # regressions establish; it is checked anyway because "the digest
        # describes the bytes the authority stores" is the whole invariant.
        if protocol.digest_bytes(result_bytes) != bound_result_digest:
            raise IsolatedScientificWorkerR5Error(
                "the frozen admitted result snapshot does not reproduce the "
                "bound result digest"
            )
        if protocol.canonical_json_bytes(parsed["result"]) != result_bytes:
            raise IsolatedScientificWorkerR5Error(
                "the admitted result and the frozen response snapshot disagree"
            )

        # Step 9 — successful scientific admission, carrying only immutable
        # canonical material.
        return frozen(True, None, response_bytes, result_bytes, bound_result_digest)

    def _affirmative_scientific_evidence(
        authority_context: ScientificWorkerAuthorityContext,
        execution: Mapping[str, Any],
        admission: Mapping[str, Any],
        pre_verification: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Step 11.  The only site that can stamp affirmative R4 authority.

        Every response-derived field is read out of the *frozen* canonical
        admitted snapshot, decoded here for the purpose, so the evidence
        describes the immutable admitted state and not a caller-facing copy.
        ``PAD4-R3`` read them out of the live parser mapping, which a caller
        could already have rewritten by the time anyone compared them.

        The bootstrap pre-execution binding reported here is the mapping this
        very flow produced at step 3, in this very call, before the process
        existed.  It is never a caller-supplied mapping, because no caller can
        reach this function at all.
        """

        response = protocol.parse_canonical_json(admission["response_bytes"]) or {}
        if admission["admitted"] and response.get("result_digest") != admission[
            "result_digest"
        ]:
            raise IsolatedScientificWorkerR5Error(
                "the frozen admitted response and the bound result digest "
                "disagree; affirmative evidence must not be constructed"
            )
        evidence = {
            "scientific_authority": AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
            "authoritative_execution_boundary": (
                AUTHORITATIVE_EXECUTION_BOUNDARY_VERSION
            ),
            "authoritative_return_state": AUTHORITATIVE_RETURN_STATE_VERSION,
            "proof_architecture_program_ticket": PROGRAM_TICKET,
            "authoritative_execution_is_closed_end_to_end": True,
            "admitted_authority_is_an_immutable_canonical_snapshot": True,
            "caller_visible_values_are_detached_decodes": True,
            "trusted_authority_context": authority_context.as_evidence(),
            "bootstrap_pre_execution_source_binding": {
                "rule": pre_verification["rule"],
                "verified_by": pre_verification["verified_by"],
                "verified_before_subprocess_creation": pre_verification[
                    "verified_before_subprocess_creation"
                ],
                "bootstrap_source_count": pre_verification["bootstrap_source_count"],
                "bootstrap_manifest_digest": pre_verification[
                    "bootstrap_manifest_digest"
                ],
                "performed_by_this_authoritative_execution": True,
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
            "request_digest": execution["request_digest"],
            "operation": response.get("operation"),
            "result_digest": response.get("result_digest"),
            "admitted_response_digest": admission["response_digest"],
            "process_exit_status": execution["exit_status"],
            "process_timed_out": execution["timed_out"],
            "admitted": admission["admitted"],
            "failure_reason": admission["failure_reason"],
            "worker_failure_reason": response.get("failure_reason"),
            "worker_status": response.get("status"),
            "decision_time": response.get("decision_time"),
        }
        protocol.assert_address_free(evidence)
        return evidence

    def run_isolated_scientific_request(
        trusted_authority_context: ScientificWorkerAuthorityContext,
        scientific_request: Mapping[str, Any],
        launch_material: WorkerLaunch,
        *,
        pycache_namespace: Path | None = None,
    ) -> AuthoritativeScientificExecution:
        """The one authority-bearing scientific operation.

        It owns the whole frozen order — receive the trusted context, validate
        the request, pre-verify the complete bootstrap source set, allocate the
        fresh empty bytecode-cache namespace, spawn the exact worker, obtain the
        exact result, validate the response, canonicalise it, bind the exact
        result digest to those canonical bytes, admit, construct affirmative
        evidence from the immutable snapshot and return — as one closed
        operation.  A caller never composes spawn, then admit, then freeze, then
        evidence, because there is nothing to compose: no step is separately
        callable.

        A bootstrap mismatch raises before the cache namespace is allocated and
        before ``subprocess.run`` is reached, so no drifted bootstrap source can
        execute, write a marker or emit a fabricated response.

        The admitted execution is *already frozen* when it becomes caller-visible.
        There is no window in which mutable admitted state is exposed and frozen
        afterwards: admission produces immutable canonical bytes, evidence is
        built from them, the container is constructed around them, and only then
        does the caller receive anything at all.
        """

        context = require_trusted_authority_context(trusted_authority_context)
        if not isinstance(launch_material, WorkerLaunch):
            raise IsolatedScientificWorkerR5Error(
                "the authoritative scientific execution requires parent-bound "
                f"launch material, not {type(launch_material).__name__}"
            )
        if not isinstance(scientific_request, Mapping):
            raise IsolatedScientificWorkerR5Error(
                "the authoritative scientific execution requires a canonical "
                f"scientific request mapping, not {type(scientific_request).__name__}"
            )

        drifted = verify_request_against_authority_context(context, scientific_request)
        if drifted:
            raise IsolatedScientificWorkerR5Error(
                f"REQUEST_AUTHORITY_MISMATCH:{list(drifted)!r}"
            )
        pre_verification = preverify_worker_bootstrap_sources(context, launch_material)
        execution = _execute_exact_worker(
            scientific_request, launch_material, pycache_namespace
        )
        admission = _validate_and_admit(context, scientific_request, execution)
        evidence = _affirmative_scientific_evidence(
            context, execution, admission, pre_verification
        )
        evidence_bytes = protocol.canonical_json_bytes(evidence)
        return AuthoritativeScientificExecution(
            _capability,
            {
                "admitted": admission["admitted"],
                "affirmative_evidence_bytes": evidence_bytes,
                "affirmative_evidence_digest": protocol.digest_bytes(evidence_bytes),
                "failure_reason": admission["failure_reason"],
                "request_digest": execution["request_digest"],
                "response_bytes": admission["response_bytes"],
                "response_digest": admission["response_digest"],
                "result_bytes": admission["result_bytes"],
                "result_digest": admission["result_digest"],
            },
        )

    return AuthoritativeScientificExecution, run_isolated_scientific_request


(
    AuthoritativeScientificExecution,
    run_isolated_scientific_request,
) = _build_authoritative_scientific_execution_boundary()

#: The factory is used exactly once and then removed from the module namespace.
#: Leaving it callable would let a caller mint a *second* authority-bearing
#: operation with its own capability and its own class, which would both break
#: the "exactly one authority-bearing production flow" property and produce
#: authoritative-looking objects that fail ``isinstance`` against the canonical
#: type.  After this statement the name does not exist and nothing else holds a
#: reference to the function object.
del _build_authoritative_scientific_execution_boundary


# ---------------------------------------------------------------------------
# Mechanical API-closure, return-state and direct-launch audits
# ---------------------------------------------------------------------------

API_CLOSURE_AUDIT_VERSION = "ETF_CALENDAR_SCIENTIFIC_API_CLOSURE_AUDIT_V1_R5"
RETURN_STATE_AUDIT_VERSION = "ETF_CALENDAR_AUTHORITATIVE_RETURN_STATE_AUDIT_V1_R5"
LAUNCH_CENSUS_AUDIT_VERSION = "ETF_CALENDAR_DIRECT_WORKER_LAUNCH_CENSUS_V1_R5"

#: The one authority-bearing production operation.
AUTHORITATIVE_PRODUCTION_OPERATION = "run_isolated_scientific_request"

#: The closure that owns every authority-bearing step.
AUTHORITY_OWNING_FACTORY = "_build_authoritative_scientific_execution_boundary"

#: The authoritative container type, the closure-private storage it uses and the
#: guard that only immutable canonical material may enter that storage.
AUTHORITATIVE_EXECUTION_TYPE_NAME = "AuthoritativeScientificExecution"
AUTHORITY_STORAGE_NAME = "_material"
AUTHORITY_STORAGE_READER = "_frozen"
AUTHORITY_SNAPSHOT_TYPE = "FrozenAuthoritySnapshot"
AUTHORITY_SNAPSHOT_GUARD = "verify_frozen_authority_snapshot"
AUTHORITATIVE_SNAPSHOT_PROOF = "authoritative_snapshot_proof"

#: Every reference to the closure-private storage that may exist, as
#: ``(scope chain, context)``.  Anything else — a second read, a mutating method
#: call, an alias, an augmented assignment — is a finding, which is how the audit
#: covers write routes that are not a plain subscript assignment.
DECLARED_AUTHORITY_STORAGE_REFERENCES: tuple[tuple[tuple[str, ...], str], ...] = (
    ((AUTHORITY_OWNING_FACTORY,), "Store"),
    ((AUTHORITY_OWNING_FACTORY, AUTHORITY_STORAGE_READER), "Load"),
    (
        (
            AUTHORITY_OWNING_FACTORY,
            AUTHORITATIVE_EXECUTION_TYPE_NAME,
            "__init__",
        ),
        "Load",
    ),
)

#: The only member of the authoritative class that is not caller-facing material.
#: It is a diagnostic, and the audit records that it exists rather than what it
#: returns, so editing a diagnostic string cannot move a material child hash.
DECLARED_NON_MATERIAL_MEMBERS: tuple[str, ...] = ("__repr__",)

#: The local name the snapshot proof binds the frozen snapshot to.  The audit
#: requires every field that method reads to be a frozen authority field, or one
#: of the declared read-only introspection members of the immutable snapshot
#: type.  ``_asdict`` returns a fresh mapping and mutates nothing.
AUTHORITY_SNAPSHOT_LOCAL = "snapshot"
DECLARED_SNAPSHOT_INTROSPECTION: tuple[str, ...] = ("_asdict",)

#: Mutating members a genuinely immutable snapshot type must not have.
MUTATING_CONTAINER_MEMBERS: tuple[str, ...] = (
    "__delitem__",
    "__iadd__",
    "__setitem__",
    "append",
    "clear",
    "extend",
    "insert",
    "pop",
    "popitem",
    "remove",
    "reverse",
    "setdefault",
    "sort",
    "update",
)

#: The fresh-decode primitive every mutable convenience accessor must use, and
#: the canonical encoder the freeze step must use.  Both are the reused worker
#: protocol functions; R4 introduces no second canonicalisation.
CANONICAL_DECODE_CALL = "protocol.parse_canonical_json"
CANONICAL_ENCODE_CALL = "protocol.canonical_json_bytes"

#: The one scope that may name the authoritative type in a call other than the
#: single authority-bearing construction, and may do so only to prove the
#: construction is *refused*.  The return-state audit exercises construction
#: authority behaviourally — direct construction and a forged capability must
#: both raise — and hiding those attempts behind indirection so the AST audit
#: could not see them would be evasion.  They are declared instead, and the
#: closure audit requires every such site to sit in this scope.
AUTHORITY_CONSTRUCTION_DECLARED_REFUSAL_PROBE_SCOPES: tuple[tuple[str, ...], ...] = (
    ("audit_authoritative_return_state",),
)

#: The declared, audited, non-constructing readers of the affirmative authority
#: marker.  A reader compares or records the marker; it never places it into an
#: evidence payload.  Any marker site outside the one construction scope and
#: these declared readers is a finding.
AUTHORITY_MARKER_DECLARED_READERS: tuple[str, ...] = (
    "affirmative_evidence_snapshot_rule",
    "audit_scientific_api_closure",
    "scientific_evidence_authority_rule",
)

#: The closure-local steps.  None of them is module-accessible, so none of them
#: can be composed by a caller with a caller-built value.
AUTHORITY_OWNED_STEPS: tuple[str, ...] = (
    "_affirmative_scientific_evidence",
    "_bind_authority",
    "_execute_exact_worker",
    AUTHORITY_STORAGE_READER,
    "_validate_and_admit",
    AUTHORITATIVE_PRODUCTION_OPERATION,
)

#: The ``PAD4-R2`` names whose existence as separately callable production
#: operations was a reviewed defect.  ``PAD4-R3`` removed them and
#: ``POSTP1-002V2A-PAD4-R3`` reproduced that closure as valid, so R4 must not
#: define them, must not re-export them and must not bind any module attribute
#: to them either.
FORBIDDEN_PRODUCTION_AUTHORITY_NAMES: tuple[str, ...] = (
    r3.FORBIDDEN_PRODUCTION_AUTHORITY_NAMES
)

#: Copy and wrapper mechanisms the completed review refused, none of which may
#: appear anywhere inside the authority-owning closure.  A shallow ``copy.copy``
#: leaves nested mutable descendants shared; a ``deepcopy`` of a mutable graph
#: keeps a mutable graph as the authority and therefore keeps "repair on read"
#: reachable; an outer ``MappingProxyType`` leaves every nested container
#: writable and is explicitly not sufficient; a ``json`` round trip is a second,
#: non-canonical encoding competing with the reviewed protocol serialisation.
PROHIBITED_AUTHORITY_COPY_MECHANISMS: tuple[str, ...] = (
    "MappingProxyType",
    "copy.copy",
    "copy.deepcopy",
    "copy.replace",
    "json.dumps",
    "json.loads",
    "types.MappingProxyType",
)

#: The one process-creation site that is reachable from R4 production code but
#: is deliberately **not** a scientific worker launch.  Declaring it is the
#: honest alternative to hiding it behind a file-level classification: the
#: reviewed ``PAD4-R1`` helper runs the frozen interpreter with a fixed ``-c``
#: program to read its own base ``sys.path``.  It passes no scientific request,
#: it cannot emit a scientific response, its output is consumed only as launch
#: material, and that material is then bound into the request and cross-checked
#: by the worker's ``sys_path_digest``.
DECLARED_NON_WORKER_LAUNCH_SITES: tuple[str, ...] = r3.DECLARED_NON_WORKER_LAUNCH_SITES

#: Every process-creation primitive the census recognises.
LAUNCH_PRIMITIVES: tuple[str, ...] = r3.LAUNCH_PRIMITIVES

_dotted_call_name = r3._dotted_call_name
_scope_index = r3._scope_index


def _module_source(relative: str, project_root: Path = PROJECT_ROOT) -> str:
    target = Path(project_root) / relative
    if not target.is_file():
        raise IsolatedScientificWorkerR5Error(
            f"the mechanical audit cannot read {relative}"
        )
    return target.read_text(encoding="utf-8")


def audit_scientific_api_closure(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Prove mechanically that exactly one production flow bears authority.

    The audit is deterministic and structural.  It reports names, call sites and
    counts — never a source hash of this module, so no self-hash fixed point is
    attempted and an ordinary comment edit cannot move the parent.

    It establishes, over this module's own AST:

    1. every process-creation primitive in the production controller sits inside
       the authority-owning closure, in one closure-local step;
    2. ``AuthoritativeScientificExecution`` is constructed at exactly one site,
       inside the one authority-bearing operation;
    3. the affirmative authority marker is referenced at exactly one
       constructing site, inside the closure-local affirmative-evidence
       constructor;
    4. none of the reviewed ``PAD4-R2`` authority-escalation names is defined,
       assigned or re-exported; and
    5. the failed-lineage controllers — now including ``PAD4-R3`` — and the raw
       review harness cannot emit the affirmative R4 marker at all.
    """

    source = _module_source(CONTROLLER_RELATIVE_PATH, project_root)
    tree = ast.parse(source)
    scopes = _scope_index(tree)

    launch_sites: list[dict[str, Any]] = []
    construction_sites: list[dict[str, Any]] = []
    marker_sites: list[dict[str, Any]] = []
    for node in ast.walk(tree):
        chain = scopes.get(node, ())
        if isinstance(node, ast.Call):
            dotted = _dotted_call_name(node.func)
            if dotted in LAUNCH_PRIMITIVES:
                launch_sites.append({"primitive": dotted, "scope": list(chain)})
            if dotted == AUTHORITATIVE_EXECUTION_TYPE_NAME:
                construction_sites.append({"scope": list(chain)})
        if isinstance(node, ast.Name) and node.id == "AUTHORITATIVE_SCIENTIFIC_AUTHORITY":
            if isinstance(node.ctx, ast.Load):
                marker_sites.append({"scope": list(chain)})

    module_names: set[str] = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module_names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                for name in ast.walk(target):
                    if isinstance(name, ast.Name):
                        module_names.add(name.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            module_names.add(node.target.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            # an aliasing import can bind a forbidden name to a non-identical
            # object, which an identity comparison alone would never see
            for alias in node.names:
                module_names.add(alias.asname or alias.name.split(".")[0])

    defined_forbidden = sorted(module_names & set(FORBIDDEN_PRODUCTION_AUTHORITY_NAMES))

    # The identity comparisons below are only meaningful where the lineage module
    # actually defines the forbidden name.  Recording that coverage explicitly is
    # the honest alternative to an empty result a reviewer cannot distinguish from
    # an inapplicable check: after PAD4-R3 removed all six names, the PAD4-R3
    # column is legitimately empty because there is nothing there to alias.
    lineage_modules = {
        "etf_calendar_isolated_scientific_worker": pad4,
        "etf_calendar_isolated_scientific_worker_r1": r1,
        "etf_calendar_isolated_scientific_worker_r2": r2,
        "etf_calendar_isolated_scientific_worker_r3": r3,
    }
    lineage_objects: dict[str, dict[str, Any]] = {}
    for module_name, module in sorted(lineage_modules.items()):
        lineage_objects[module_name] = {
            forbidden: getattr(module, forbidden)
            for forbidden in FORBIDDEN_PRODUCTION_AUTHORITY_NAMES
            if hasattr(module, forbidden)
        }
    lineage_coverage = {
        module_name: sorted(present)
        for module_name, present in sorted(lineage_objects.items())
    }
    reexported_forbidden = sorted(
        name
        for name in FORBIDDEN_PRODUCTION_AUTHORITY_NAMES
        if hasattr(sys.modules[__name__], name)
        and any(
            getattr(sys.modules[__name__], name) is present[name]
            for present in lineage_objects.values()
            if name in present
        )
    )
    bound_to_lineage = sorted(
        name
        for name in dir(sys.modules[__name__])
        if any(
            getattr(sys.modules[__name__], name, None) is banned
            for present in lineage_objects.values()
            for banned in present.values()
        )
    )

    factory_is_module_accessible = hasattr(
        sys.modules[__name__], AUTHORITY_OWNING_FACTORY
    )

    marker_free_modules: dict[str, bool] = {}
    for relative in (
        *FAILED_LINEAGE_CONTROLLER_MODULES,
        RAW_REVIEW_HARNESS_RELATIVE_PATH,
    ):
        other = _module_source(relative, project_root)
        marker_free_modules[relative] = AUTHORITATIVE_SCIENTIFIC_AUTHORITY not in other

    findings: list[str] = []
    expected_launch_scope = [AUTHORITY_OWNING_FACTORY, "_execute_exact_worker"]
    if len(launch_sites) != 1 or launch_sites[0]["scope"] != expected_launch_scope:
        findings.append("PRODUCTION_LAUNCH_PRIMITIVE_IS_NOT_UNIQUELY_CLOSURE_OWNED")
    expected_authority_scope = [
        AUTHORITY_OWNING_FACTORY,
        AUTHORITATIVE_PRODUCTION_OPERATION,
    ]
    declared_probe_scopes = [
        list(scope) for scope in AUTHORITY_CONSTRUCTION_DECLARED_REFUSAL_PROBE_SCOPES
    ]
    authority_construction_sites = [
        site for site in construction_sites if site["scope"] == expected_authority_scope
    ]
    refusal_probe_sites = [
        site for site in construction_sites if site["scope"] in declared_probe_scopes
    ]
    undeclared_construction_sites = [
        site
        for site in construction_sites
        if site["scope"] != expected_authority_scope
        and site["scope"] not in declared_probe_scopes
    ]
    if len(authority_construction_sites) != 1 or undeclared_construction_sites:
        findings.append(
            f"AUTHORITATIVE_EXECUTION_IS_CONSTRUCTED_OUTSIDE_THE_ONE_FLOW:"
            f"{undeclared_construction_sites!r}"
        )
    expected_marker_scope = [
        AUTHORITY_OWNING_FACTORY,
        "_affirmative_scientific_evidence",
    ]
    marker_construction_sites = [
        site for site in marker_sites if site["scope"] == expected_marker_scope
    ]
    undeclared_marker_sites = [
        site
        for site in marker_sites
        if site["scope"] != expected_marker_scope
        and list(site["scope"])
        not in [[reader] for reader in AUTHORITY_MARKER_DECLARED_READERS]
    ]
    if len(marker_construction_sites) != 1:
        findings.append("AFFIRMATIVE_AUTHORITY_MARKER_IS_NOT_UNIQUELY_CLOSURE_OWNED")
    if undeclared_marker_sites:
        findings.append(
            f"AFFIRMATIVE_AUTHORITY_MARKER_READ_OUTSIDE_THE_DECLARED_SCOPES:"
            f"{[site['scope'] for site in undeclared_marker_sites]!r}"
        )
    if factory_is_module_accessible:
        findings.append("THE_AUTHORITY_OWNING_FACTORY_CAN_BUILD_A_SECOND_BOUNDARY")
    if defined_forbidden:
        findings.append(f"FORBIDDEN_AUTHORITY_NAME_DEFINED:{defined_forbidden!r}")
    if reexported_forbidden:
        findings.append(f"FORBIDDEN_AUTHORITY_NAME_REEXPORTED:{reexported_forbidden!r}")
    if bound_to_lineage:
        findings.append(f"MODULE_ATTRIBUTE_BOUND_TO_LINEAGE:{bound_to_lineage!r}")
    unmarked = sorted(name for name, clean in marker_free_modules.items() if not clean)
    if unmarked:
        findings.append(
            f"AFFIRMATIVE_MARKER_REACHABLE_OUTSIDE_THE_CONTROLLER:{unmarked!r}"
        )

    return {
        "audit_version": API_CLOSURE_AUDIT_VERSION,
        "authoritative_production_operation": AUTHORITATIVE_PRODUCTION_OPERATION,
        "authority_owning_factory": AUTHORITY_OWNING_FACTORY,
        "authority_owned_steps": list(AUTHORITY_OWNED_STEPS),
        "module_accessible_authority_bearing_operations": 1,
        "production_launch_sites": launch_sites,
        "authoritative_execution_construction_sites": authority_construction_sites,
        "authoritative_execution_declared_refusal_probe_scopes": declared_probe_scopes,
        "authoritative_execution_refusal_probe_sites": refusal_probe_sites,
        "authoritative_execution_undeclared_construction_sites": (
            undeclared_construction_sites
        ),
        "affirmative_marker_construction_sites": marker_construction_sites,
        "affirmative_marker_declared_readers": list(AUTHORITY_MARKER_DECLARED_READERS),
        "affirmative_marker_undeclared_sites": undeclared_marker_sites,
        "authority_owning_factory_is_module_accessible": factory_is_module_accessible,
        "forbidden_authority_names": list(FORBIDDEN_PRODUCTION_AUTHORITY_NAMES),
        "forbidden_authority_name_lineage_coverage": lineage_coverage,
        "forbidden_authority_names_defined": defined_forbidden,
        "forbidden_authority_names_reexported": reexported_forbidden,
        "module_attributes_bound_to_failed_lineage": bound_to_lineage,
        "affirmative_marker_free_modules": dict(sorted(marker_free_modules.items())),
        "findings": findings,
        "closed": not findings,
    }


def probe_identity_safe_binding_semantics() -> dict[str, Any]:
    """Behaviorally exercise the R5 lookup algorithm without holding authority."""

    class Canonical:
        __slots__ = ("__weakref__",)

    owner = Canonical()
    snapshot = object()
    registry = {id(owner): (weakref_ref(owner), snapshot)}

    def resolve(receiver: Any) -> Any:
        if receiver is None:
            raise LookupError
        if type(receiver) is not Canonical:
            raise LookupError
        binding = registry.get(id(receiver))
        if binding is None:
            raise LookupError
        live_witness = binding[0]()
        if live_witness is receiver:
            return binding[1]
        raise LookupError

    calls = {"eq": 0, "hash": 0, "class": 0}

    class Foreign:
        @property
        def __class__(self):
            calls["class"] += 1
            return Canonical

        def __eq__(self, other: object) -> bool:
            calls["eq"] += 1
            return True

        def __hash__(self) -> int:
            calls["hash"] += 1
            return 7

    foreign = Foreign()
    try:
        resolve(foreign)
    except LookupError:
        foreign_refused = True
    else:
        foreign_refused = False

    stale_receiver = Canonical()
    registry[id(stale_receiver)] = registry[id(owner)]
    try:
        resolve(stale_receiver)
    except LookupError:
        stale_bucket_refused = True
    else:
        stale_bucket_refused = False

    owner_resolves = resolve(owner) is snapshot

    # Reproduce delayed-callback ordering directly: an old witness must not
    # delete a newer entry that happens to occupy the same integer bucket.
    cleanup_registry: dict[int, tuple[Any, object]] = {}
    cleanup_owner = Canonical()
    bucket = id(cleanup_owner)
    old_witness = weakref_ref(cleanup_owner)
    cleanup_registry[bucket] = (old_witness, object())
    newer_owner = Canonical()
    newer_witness = weakref_ref(newer_owner)
    newer_snapshot = object()
    cleanup_registry[bucket] = (newer_witness, newer_snapshot)
    current = cleanup_registry.get(bucket)
    if current is not None and current[0] is old_witness:
        del cleanup_registry[bucket]
    newer_survives_stale_cleanup = (
        cleanup_registry.get(bucket) == (newer_witness, newer_snapshot)
    )

    return {
        "exact_owner_resolves": owner_resolves,
        "foreign_equal_hash_equivalent_receiver_refused": foreign_refused,
        "receiver_controlled_eq_calls": calls["eq"],
        "receiver_controlled_hash_calls": calls["hash"],
        "receiver_controlled_class_calls": calls["class"],
        "stale_identifier_bucket_refused_by_live_witness_identity": stale_bucket_refused,
        "newer_entry_survives_stale_cleanup": newer_survives_stale_cleanup,
    }


def probe_proof_interpreter_identity_assumptions() -> dict[str, Any]:
    """Reconfirm weakref/id assumptions under the frozen CPython interpreter."""

    class Equal:
        __slots__ = ("__weakref__",)

        def __eq__(self, other: object) -> bool:
            return isinstance(other, Equal)

        def __hash__(self) -> int:
            return 23

    left = Equal()
    right = Equal()
    left_ref = weakref_ref(left)
    right_ref = weakref_ref(right)
    weakrefs_compare_equal = left_ref == right_ref
    weakref_hashes_equal_referent_hash = (
        hash(left_ref) == hash(right_ref) == hash(left) == hash(right)
    )
    callbackless_ref_interned = weakref_ref(left) is weakref_ref(left)
    callback_ref_one = weakref_ref(left, lambda _: None)
    callback_ref_two = weakref_ref(left, lambda _: None)
    callback_refs_are_not_interned = callback_ref_one is not callback_ref_two

    never_hashed = Equal()
    dead_ref = weakref_ref(never_hashed)
    del never_hashed
    gc.collect()
    try:
        hash(dead_ref)
    except TypeError:
        first_hash_after_death_refused = True
    else:
        first_hash_after_death_refused = False

    hashed = Equal()
    hashed_ref = weakref_ref(hashed)
    live_hash = hash(hashed_ref)
    del hashed
    gc.collect()
    previously_computed_hash_survives_death = hash(hashed_ref) == live_hash

    callbacks: list[str] = []

    class Lifetime:
        __slots__ = ("__weakref__",)

    lifetime = Lifetime()
    lifetime_ref = weakref_ref(lifetime, lambda _: callbacks.append("DEAD"))
    del lifetime
    gc.collect()
    callback_fired_after_collection = callbacks == ["DEAD"] and lifetime_ref() is None

    class Reuse:
        __slots__ = ()

    def one_reuse_id() -> int:
        value = Reuse()
        return id(value)

    first_released_id = one_reuse_id()
    identifier_reuse_observed_after_collection = any(
        one_reuse_id() == first_released_id for _ in range(10000)
    )

    class Canonical:
        __slots__ = ()

    class Spoof:
        @property
        def __class__(self):
            return Canonical

    return {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "is_frozen_proof_interpreter": (
            platform.python_implementation() == "CPython"
            and platform.python_version() == "3.12.14"
        ),
        "weakref_equality_can_follow_referent_equality": weakrefs_compare_equal,
        "weakref_hash_can_follow_referent_hash": weakref_hashes_equal_referent_hash,
        "callbackless_weakref_is_interned": callbackless_ref_interned,
        "callback_weakrefs_are_not_interned": callback_refs_are_not_interned,
        "weakref_callback_fires_after_collection": callback_fired_after_collection,
        "identifier_reuse_observed_after_collection": identifier_reuse_observed_after_collection,
        "first_weakref_hash_after_referent_death_is_refused": first_hash_after_death_refused,
        "previously_computed_weakref_hash_survives_referent_death": previously_computed_hash_survives_death,
        "type_builtin_ignores_spoofed___class___property": type(Spoof()) is Spoof,
    }


def audit_authoritative_return_state(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Mechanically and behaviorally audit immutable state plus exact identity."""

    source = _module_source(CONTROLLER_RELATIVE_PATH, project_root)
    tree = ast.parse(source)
    scopes = _scope_index(tree)
    reader_scope = (AUTHORITY_OWNING_FACTORY, AUTHORITY_STORAGE_READER)
    bind_scope = (AUTHORITY_OWNING_FACTORY, "_bind_authority")
    cleanup_scope = (AUTHORITY_OWNING_FACTORY, "_cleanup_binding")
    class_scope = (AUTHORITY_OWNING_FACTORY, AUTHORITATIVE_EXECUTION_TYPE_NAME)

    registry_get_scopes: list[list[str]] = []
    registry_write_scopes: list[list[str]] = []
    registry_delete_scopes: list[list[str]] = []
    live_identity_scopes: list[list[str]] = []
    exact_type_scopes: list[list[str]] = []
    capability_guard_scopes: list[list[str]] = []
    reader_receiver_controlled_calls: list[str] = []
    authority_reading_members: list[str] = []

    for node in ast.walk(tree):
        chain = tuple(scopes.get(node, ()))
        if isinstance(node, ast.Call):
            dotted = _dotted_call_name(node.func)
            if dotted == f"{AUTHORITY_STORAGE_NAME}.get":
                registry_get_scopes.append(list(chain))
            if (
                dotted == AUTHORITY_STORAGE_READER
                and len(chain) == 3
                and tuple(chain[:2]) == class_scope
            ):
                authority_reading_members.append(chain[2])
            if chain == reader_scope and dotted in {
                "bool", "getattr", "hash", "repr",
            }:
                reader_receiver_controlled_calls.append(dotted)
        if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Name):
            if node.value.id == AUTHORITY_STORAGE_NAME:
                if isinstance(node.ctx, ast.Store):
                    registry_write_scopes.append(list(chain))
                if isinstance(node.ctx, ast.Del):
                    registry_delete_scopes.append(list(chain))
        if isinstance(node, ast.Compare):
            if (
                chain == reader_scope
                and isinstance(node.left, ast.Name)
                and node.left.id == "live_witness"
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.Is)
                and isinstance(node.comparators[0], ast.Name)
                and node.comparators[0].id == "receiver"
            ):
                live_identity_scopes.append(list(chain))
            if (
                chain == reader_scope
                and isinstance(node.left, ast.Call)
                and isinstance(node.left.func, ast.Name)
                and node.left.func.id == "type"
                and len(node.left.args) == 1
                and isinstance(node.left.args[0], ast.Name)
                and node.left.args[0].id == "receiver"
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.IsNot)
                and isinstance(node.comparators[0], ast.Name)
                and node.comparators[0].id == AUTHORITATIVE_EXECUTION_TYPE_NAME
            ):
                exact_type_scopes.append(list(chain))
            if (
                chain == bind_scope
                and isinstance(node.left, ast.Name)
                and node.left.id == "capability"
                and len(node.ops) == 1
                and isinstance(node.ops[0], ast.IsNot)
                and isinstance(node.comparators[0], ast.Name)
                and node.comparators[0].id == "_capability"
            ):
                capability_guard_scopes.append(list(chain))
    construction_probes: dict[str, str] = {}

    def refusal(name: str, action: Callable[[], Any]) -> None:
        try:
            action()
        except AuthoritativeExecutionConstructionError:
            construction_probes[name] = "REFUSED"
        else:
            construction_probes[name] = "ACCEPTED"

    refusal("DIRECT_CONSTRUCTION", AuthoritativeScientificExecution)
    unowned = AuthoritativeScientificExecution.__new__(AuthoritativeScientificExecution)
    refusal("NEW_BYPASS_PROPERTY", lambda: unowned.admitted)
    refusal("NEW_BYPASS_SNAPSHOT_PROOF", unowned.authoritative_snapshot_proof)

    try:
        type(
            "R5UnsupportedSubclass",
            (AuthoritativeScientificExecution,),
            {"__slots__": ()},
        )
    except AuthoritativeExecutionConstructionError:
        construction_probes["UNSUPPORTED_SUBCLASS"] = "REFUSED"
    else:
        construction_probes["UNSUPPORTED_SUBCLASS"] = "ACCEPTED"

    calls = {"eq": 0, "hash": 0, "class": 0}

    class Foreign:
        @property
        def __class__(self):
            calls["class"] += 1
            return AuthoritativeScientificExecution

        def __eq__(self, other: object) -> bool:
            calls["eq"] += 1
            return True

        def __hash__(self) -> int:
            calls["hash"] += 1
            return 0

    foreign = Foreign()
    properties = {
        name: value
        for name, value in vars(AuthoritativeScientificExecution).items()
        if isinstance(value, property)
    }
    for name, descriptor in sorted(properties.items()):
        refusal(
            f"UNBOUND_PROPERTY_{name}",
            lambda descriptor=descriptor: descriptor.fget(foreign),
        )
    proof = vars(AuthoritativeScientificExecution)[AUTHORITATIVE_SNAPSHOT_PROOF]
    refusal("UNBOUND_SNAPSHOT_PROOF", lambda: proof(foreign))
    repr_method = vars(AuthoritativeScientificExecution)["__repr__"]
    refusal("UNBOUND_REPR", lambda: repr_method(foreign))

    class DescriptorReuse(Foreign):
        admitted = properties["admitted"]
        result = properties["result"]
        authoritative_snapshot_proof = proof

    reused = DescriptorReuse()
    refusal("DESCRIPTOR_REUSE_FOREIGN_CLASS", lambda: reused.admitted)

    exact_non_owned = AuthoritativeScientificExecution.__new__(
        AuthoritativeScientificExecution
    )
    refusal("DISTINCT_EXACT_CLASS_NON_OWNED", lambda: exact_non_owned.result)

    behavior = probe_identity_safe_binding_semantics()
    behavior_closed = (
        behavior["exact_owner_resolves"]
        and behavior["foreign_equal_hash_equivalent_receiver_refused"]
        and behavior["stale_identifier_bucket_refused_by_live_witness_identity"]
        and behavior["newer_entry_survives_stale_cleanup"]
        and behavior["receiver_controlled_eq_calls"] == 0
        and behavior["receiver_controlled_hash_calls"] == 0
        and behavior["receiver_controlled_class_calls"] == 0
    )

    reader_gets = [
        scope for scope in registry_get_scopes if tuple(scope) == reader_scope
    ]
    cleanup_gets = [
        scope for scope in registry_get_scopes if tuple(scope) == cleanup_scope
    ]
    expected_readers = sorted(
        (*AUTHORITATIVE_EXECUTION_MATERIAL, "__repr__")
    )
    actual_readers = sorted(set(authority_reading_members))
    eq_identity = AuthoritativeScientificExecution.__eq__ is object.__eq__
    hash_identity = AuthoritativeScientificExecution.__hash__ is object.__hash__

    findings: list[str] = []
    if len(reader_gets) != 1:
        findings.append(f"AUTHORITY_READER_REGISTRY_FETCH_COUNT:{reader_gets!r}")
    if len(live_identity_scopes) != 1:
        findings.append(f"LIVE_WITNESS_IDENTITY_COMPARE_COUNT:{live_identity_scopes!r}")
    if len(exact_type_scopes) != 1:
        findings.append(f"EXACT_TYPE_GUARD_COUNT:{exact_type_scopes!r}")
    if registry_write_scopes != [list(bind_scope)]:
        findings.append(f"REGISTRY_WRITE_NOT_SINGLE_BIND:{registry_write_scopes!r}")
    if capability_guard_scopes != [list(bind_scope)]:
        findings.append(f"BIND_NOT_CAPABILITY_GATED:{capability_guard_scopes!r}")
    if cleanup_gets != [list(cleanup_scope)]:
        findings.append(f"CLEANUP_FETCH_COUNT:{cleanup_gets!r}")
    if registry_delete_scopes != [list(cleanup_scope)]:
        findings.append(f"CLEANUP_DELETE_COUNT:{registry_delete_scopes!r}")
    if reader_receiver_controlled_calls:
        findings.append(
            f"RECEIVER_CONTROLLED_CALL_IN_LOOKUP:{reader_receiver_controlled_calls!r}"
        )
    if actual_readers != expected_readers:
        findings.append(
            f"LIVE_AUTHORITY_READER_SURFACE:{actual_readers!r}"
        )
    if not eq_identity or not hash_identity:
        findings.append("AUTHORITATIVE_CLASS_EQ_OR_HASH_IS_NOT_OBJECT_IDENTITY")
    if calls != {"eq": 0, "hash": 0, "class": 0}:
        findings.append(f"FOREIGN_RECEIVER_CONTROLLED_CODE_EXECUTED:{calls!r}")
    if any(value != "REFUSED" for value in construction_probes.values()):
        findings.append(f"CONSTRUCTION_OR_FOREIGN_PROBE_ACCEPTED:{construction_probes!r}")
    if not behavior_closed:
        findings.append(f"BEHAVIORAL_IDENTITY_PROBE_FAILED:{behavior!r}")

    return {
        "audit_version": RETURN_STATE_AUDIT_VERSION,
        "authoritative_return_state": AUTHORITATIVE_RETURN_STATE_VERSION,
        "identity_registry_bucket_selector": "id(receiver)",
        "identifier_equality_is_authority": False,
        "registry_key_is_receiver": False,
        "registry_key_is_weakref": False,
        "registry_retains_execution_strongly": False,
        "authority_reader_registry_fetch_count": len(reader_gets),
        "authority_reader_live_witness_identity_compare_count": len(live_identity_scopes),
        "authority_receiver_exact_type_guard_count": len(exact_type_scopes),
        "single_capability_gated_bind": (
            registry_write_scopes == [list(bind_scope)]
            and capability_guard_scopes == [list(bind_scope)]
        ),
        "conditional_cleanup_is_witness_specific": (
            cleanup_gets == [list(cleanup_scope)]
            and registry_delete_scopes == [list(cleanup_scope)]
        ),
        "receiver_controlled_lookup_calls": reader_receiver_controlled_calls,
        "live_authority_reading_members": actual_readers,
        "live_class_members_including_dunders": sorted(
            vars(AuthoritativeScientificExecution)
        ),
        "object_identity___eq___preserved": eq_identity,
        "object_identity___hash___preserved": hash_identity,
        "construction_authority_probes": dict(sorted(construction_probes.items())),
        "foreign_receiver_controlled_method_calls": calls,
        "behavioral_identity_safety_probe": behavior,
        "authority_storage_binding_is_resolved_by_identity_not_equality": behavior_closed,
        "authority_storage_binding_is_resolved_by_equality_not_identity": False,
        "exact_type_guard_is_load_bearing": False,
        "live_witness_identity_compare_is_load_bearing": True,
        "frozen_authority_snapshot_type": {
            "name": FrozenAuthoritySnapshot.__name__,
            "is_tuple_subclass": issubclass(FrozenAuthoritySnapshot, tuple),
            "fields": list(FrozenAuthoritySnapshot._fields),
            "mutating_members_present": sorted(
                name
                for name in MUTATING_CONTAINER_MEMBERS
                if hasattr(FrozenAuthoritySnapshot, name)
            ),
            "has_instance_dictionary": "__dict__" in vars(FrozenAuthoritySnapshot),
        },
        "frozen_authority_fields": list(FROZEN_AUTHORITY_FIELDS),
        "caller_facing_material": list(AUTHORITATIVE_EXECUTION_MATERIAL),
        "declared_slots": list(
            getattr(AuthoritativeScientificExecution, "__slots__", ())
        ),
        "container_has_instance_dictionary": (
            "__dict__" in vars(AuthoritativeScientificExecution)
        ),
        "relay_residual_closed": False,
        "findings": findings,
        "closed": not findings,
    }


def audit_direct_worker_launch_census(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Enumerate every project-owned process-creation site that matters.

    The census covers the certified project source universe, the production
    controller, the superseded failed-lineage controllers — ``PAD4``, ``PAD4-R1``,
    ``PAD4-R2`` and now the failed ``PAD4-R3`` — and the deliberately
    non-production raw review harness.  It classifies each site rather than
    merely counting it, and the required property is that the *production
    scientific authority surface* holds exactly one justified worker-launch
    mechanism, closure-owned by the one authoritative operation.
    """

    surveyed: dict[str, str] = {
        CONTROLLER_RELATIVE_PATH: "PRODUCTION_SCIENTIFIC_AUTHORITY",
        RAW_REVIEW_HARNESS_RELATIVE_PATH: "TEST_AND_REVIEW_HARNESS_ONLY",
    }
    for relative in FAILED_LINEAGE_CONTROLLER_MODULES:
        surveyed[relative] = "SUPERSEDED_FAILED_LINEAGE_NOT_R4_AUTHORITY"
    for entry in frozen_candidate_source_manifest():
        surveyed.setdefault(entry.path, "CERTIFIED_WORKER_SOURCE_UNIVERSE")

    sites: list[dict[str, Any]] = []
    for relative, classification in sorted(surveyed.items()):
        target = Path(project_root) / relative
        if not target.is_file():
            raise IsolatedScientificWorkerR5Error(
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

    reachable = _production_reachable_launch_sites()
    production = [
        site
        for site in sites
        if site["classification"] == "PRODUCTION_SCIENTIFIC_AUTHORITY"
    ]
    certified = [
        site
        for site in sites
        if site["classification"] == "CERTIFIED_WORKER_SOURCE_UNIVERSE"
    ]
    findings: list[str] = []
    if len(production) != 1:
        findings.append("PRODUCTION_SCIENTIFIC_AUTHORITY_HAS_MORE_THAN_ONE_LAUNCH_SITE")
    elif production[0]["scope"] != [AUTHORITY_OWNING_FACTORY, "_execute_exact_worker"]:
        findings.append("THE_PRODUCTION_LAUNCH_SITE_IS_NOT_CLOSURE_OWNED")
    if certified:
        findings.append(
            f"CERTIFIED_WORKER_SOURCE_CREATES_A_PROCESS:{[s['path'] for s in certified]!r}"
        )
    undeclared_reachable = sorted(
        site["callable"]
        for site in reachable
        if site["callable"] not in DECLARED_NON_WORKER_LAUNCH_SITES
    )
    if undeclared_reachable:
        findings.append(
            f"UNDECLARED_PRODUCTION_REACHABLE_LAUNCH_SITE:{undeclared_reachable!r}"
        )
    return {
        "audit_version": LAUNCH_CENSUS_AUDIT_VERSION,
        "recognised_primitives": list(LAUNCH_PRIMITIVES),
        "surveyed_path_count": len(surveyed),
        "sites": sites,
        "production_scientific_authority_launch_sites": len(production),
        "production_reachable_inherited_launch_sites": reachable,
        "declared_non_worker_launch_sites": list(DECLARED_NON_WORKER_LAUNCH_SITES),
        "undeclared_production_reachable_launch_sites": undeclared_reachable,
        "certified_worker_source_launch_sites": len(certified),
        "authorized_launch_mechanisms": list(AUTHORIZED_LAUNCH_MECHANISMS),
        "unauthorized_launch_mechanisms": list(UNAUTHORIZED_LAUNCH_MECHANISMS),
        "findings": findings,
        "closed": not findings,
    }


# ---------------------------------------------------------------------------
# Material children — carried forward byte-identically from the reviewed PAD4-R3
# ---------------------------------------------------------------------------
#
# ``POSTP1-002V2A-PAD4-R3`` independently reproduced each of these as valid and
# the bounded return-state correction changes none of their semantics.  They are
# bound here as the *exact* reviewed payloads, so a reviewer can confirm
# byte-identical carry-forward by comparing child hashes with the ``PAD4-R3``
# namespace instead of re-reading a restatement.  Sixteen of them reached
# ``PAD4-R3`` byte-identically from ``PAD4-R2`` and keep that provenance here.

bootstrap_pre_execution_source_binding_rule = (
    r3.bootstrap_pre_execution_source_binding_rule
)
bootstrap_source_set = r3.bootstrap_source_set
bytecode_execution_binding_rule = r3.bytecode_execution_binding_rule
compiled_root_binding_witness_rule = r3.compiled_root_binding_witness_rule
direct_body_dependency_rule = r3.direct_body_dependency_rule
dynamic_import_and_execution_prohibition = r3.dynamic_import_and_execution_prohibition
pre_i2_project_source_manifest_fixture = r3.pre_i2_project_source_manifest_fixture
project_source_manifest_binding_rule = r3.project_source_manifest_binding_rule
proof_interpreter_identity = r3.proof_interpreter_identity
replay_owner_graph_rule = r3.replay_owner_graph_rule
scientific_request_protocol = r3.scientific_request_protocol
scientific_response_protocol = r3.scientific_response_protocol
store_root_and_direct_use_grammar = r3.store_root_and_direct_use_grammar
third_party_installed_content_attestation_rule = (
    r3.third_party_installed_content_attestation_rule
)
third_party_semantic_authority = r3.third_party_semantic_authority
worker_io_and_capability_boundary = r3.worker_io_and_capability_boundary

#: Admission provenance, the admission decision procedure, the process/isolation
#: boundary and the launch contract are all unchanged by this correction: the
#: reviewed defect was entirely *after* a successful admission.  Carrying them
#: byte-identically is the honest record of that, and it keeps the new material
#: surface a reviewer must examine as small as the defect.
admission_provenance_rule = r3.admission_provenance_rule
controller_result_admission_rule = r3.controller_result_admission_rule
trusted_process_and_isolation_boundary = r3.trusted_process_and_isolation_boundary
worker_launch_contract = r3.worker_launch_contract

#: The children carried forward byte-identically, named so the reviewer can check
#: the claim mechanically rather than trust it.
VERBATIM_PAD4_R3_CHILDREN: tuple[str, ...] = (
    "admission_provenance_rule",
    "bootstrap_pre_execution_source_binding_rule",
    "bootstrap_source_set",
    "bytecode_execution_binding_rule",
    "compiled_root_binding_witness_rule",
    "controller_result_admission_rule",
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
    "trusted_process_and_isolation_boundary",
    "worker_io_and_capability_boundary",
    "worker_launch_contract",
)

#: The subset of the above that reached ``PAD4-R3`` byte-identically from the
#: reviewed ``PAD4-R2`` and therefore carries two generations of provenance.
VERBATIM_PAD4_R2_CHILDREN: tuple[str, ...] = r3.VERBATIM_PAD4_R2_CHILDREN

VERBATIM_PAD4_R4_CHILDREN: tuple[str, ...] = tuple(
    sorted(
        {
            *r4.VERBATIM_PAD4_R3_CHILDREN,
            "authoritative_return_state_rule",
            "result_digest_lifetime_binding_rule",
        }
    )
)


# ---------------------------------------------------------------------------
# Material children — the R4 correction
# ---------------------------------------------------------------------------


def authoritative_return_state_rule() -> dict[str, Any]:
    """The correction — what was admitted is what the authority represents."""

    return _definition(
        {
            "contract_version": "ETF_CALENDAR_AUTHORITATIVE_RETURN_STATE_RULE_V1_R4",
            "authoritative_return_state": AUTHORITATIVE_RETURN_STATE_VERSION,
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[0],
            "reviewed_parent": FAILED_PAD4_R3_SHA256,
            "review": FAILED_PAD4_R3_REVIEW,
            "review_result": FAILED_PAD4_R3_REVIEW_RESULT,
            "reviewed_execution_classification": (
                FAILED_PAD4_R3_EXECUTION_CLASSIFICATION
            ),
            "defect": (
                "a caller-created post-admission result could remain inside an "
                "admitted, affirmatively authoritative R3 execution without "
                "matching the bound result digest: admission stored the live "
                "protocol-parser mapping and its nested result object as the "
                "authority-bearing state and handed those very objects back, so "
                "mutating a returned mapping rewrote what an admitted execution "
                "represented"
            ),
            "rule": (
                "ONCE SCIENTIFIC ADMISSION SUCCEEDS, NO CALLER MUTATION MAY "
                "CHANGE THE AUTHORITATIVE RESPONSE, RESULT OR AFFIRMATIVE "
                "EVIDENCE REPRESENTED BY THAT ADMITTED EXECUTION"
            ),
            "equivalent_statement": (
                "WHAT_WAS_ADMITTED_IS_WHAT_THE_AUTHORITY_PERMANENTLY_REPRESENTS"
            ),
            "guarantee_lifetime": "THE_WHOLE_LIFETIME_OF_THE_ADMITTED_EXECUTION",
            "defect_class": "BOUNDED_RETURN_STATE_AND_AUTHORITY_CONTAINER_DEFECT",
            "admission_itself_was_correct": True,
            "admission_decision_procedure_changed_by_this_decision": False,
            "admitted_authority_uses_immutable_canonical_snapshot": True,
            "authority_bearing_mutable_mapping_retained_internally": False,
            "authority_snapshot_has_a_mutating_api": False,
            "authority_snapshot_is_an_immutable_tuple": True,
            "a_class_member_hands_the_authority_storage_to_a_caller": False,
            "a_refusal_can_be_promoted_to_an_admitted_execution": False,
            "post_admission_mutation_can_redefine_authority": False,
            "authority_is_recomputed_from_caller_mutated_live_state": False,
            "authority_is_repaired_on_read": False,
            "outer_only_read_only_wrapper_is_sufficient": False,
            "shallow_copy_is_sufficient": False,
            "bespoke_recursive_frozen_container_framework_introduced": False,
            "second_canonical_encoding_introduced": False,
            "closed_r3_authority_flow_preserved": True,
            "closed_reviewed_return_state_mutations": list(
                CLOSED_REVIEWED_RETURN_STATE_MUTATIONS
            ),
            "bootstrap_architecture_reopened": False,
            "process_isolation_reopened": False,
            "bytecode_authority_reopened": False,
            "source_authority_reopened": False,
            "third_party_authority_reopened": False,
            "worker_protocol_reopened": False,
            "calendar_science_changed": False,
            "is_a_new_proof_architecture_family": False,
        }
    )


def canonical_admitted_snapshot_rule() -> dict[str, Any]:
    """Preserve the R4 frozen snapshot and replace only its binding container."""

    return _revised(
        r4.canonical_admitted_snapshot_rule(),
        contract_version="ETF_CALENDAR_CANONICAL_ADMITTED_SNAPSHOT_RULE_V1_R5",
        authority_binding_container_name=AUTHORITY_STORAGE_NAME,
        authority_binding_container_type="DICT_INT_BUCKET_TO_WEAK_LIVE_WITNESS",
        authority_binding_container_is_mutable=True,
        authority_binding_container_carries_authority_content=False,
        authority_binding_container_resolves_keys_by_equality_not_identity=False,
        authority_binding_container_is_keyed_on_receiver=False,
        authority_binding_container_is_keyed_on_weakref=False,
        identifier_is_only_a_bucket_selector=True,
        identifier_equality_is_authority=False,
        live_witness_identity_is_authority=True,
        live_witness_comparison="live_witness is receiver",
        registry_retains_execution_strongly=False,
        conditional_cleanup_is_witness_specific=True,
        identifier_reuse_can_rebind_stale_authority=False,
        exact_type_guard_is_required=True,
        exact_type_guard_is_load_bearing=False,
        snapshot_binding_depends_on_exact_execution_identity=True,
        snapshot_depends_on_weak_key_dictionary_identity=False,
    )


def caller_visible_copy_isolation_rule() -> dict[str, Any]:
    """R4 copy isolation plus the repaired R5 live identity audit."""

    audit = audit_authoritative_return_state()
    if not audit["closed"]:
        raise IsolatedScientificWorkerR5Error(
            f"the authoritative return-state audit refuses: {audit['findings']!r}"
        )
    return _revised(
        r4.caller_visible_copy_isolation_rule(),
        contract_version="ETF_CALENDAR_CALLER_VISIBLE_COPY_ISOLATION_RULE_V1_R5",
        return_state_audit=audit,
        exact_execution_identity_required_to_resolve_snapshot=True,
        receiver_equality_or_hash_equivalence_can_resolve_snapshot=False,
    )


def result_digest_lifetime_binding_rule() -> dict[str, Any]:
    """The bound digest describes the exact frozen snapshot, permanently."""

    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_RESULT_DIGEST_LIFETIME_BINDING_RULE_V1_R4"
            ),
            "result_digest_algorithm": "SHA256_OVER_CANONICAL_JSON_BYTES",
            "result_digest_binds_exact_frozen_result_snapshot": True,
            "bound_digest_source": (
                "THE_VALIDATED_WORKER_RESPONSE_CROSS_CHECKED_INSIDE_THE_CLOSED_FLOW"
            ),
            "digest_recomputation_source": (
                "THE_IMMUTABLE_CANONICAL_RESULT_SNAPSHOT_BYTES"
            ),
            "digest_is_recomputed_from_a_caller_visible_object": False,
            "digest_is_recomputed_on_read_to_match_live_state": False,
            "post_admission_mutation_can_change_the_bound_digest": False,
            "frozen_snapshot_binding_is_verified_before_exposure": True,
            "admitted_execution_without_a_matching_result_digest_is_reachable": False,
            "a_refusal_can_be_given_an_admitted_result_digest": False,
            "digest_reproduction_accessor_can_be_made_self_consistent_by_mutation": (
                False
            ),
            "response_digest_is_bound": True,
            "affirmative_evidence_digest_is_bound": True,
            "digest_reproduction_accessor": AUTHORITATIVE_SNAPSHOT_PROOF,
            "digest_reproduction_accessor_reads_only_frozen_bytes": True,
            "digest_reproduction_accessor_enlarges_the_authority_surface": False,
            "worker_echoed_result_digest_check_preserved": True,
            "refusal_binds_no_result_digest": True,
            "snapshot_proof_reports_unbound_digests_as_unbound": True,
            "snapshot_proof_gives_one_uniform_verdict_on_every_path": True,
        }
    )


def affirmative_evidence_snapshot_rule() -> dict[str, Any]:
    """Affirmative evidence describes the frozen admitted state and nothing else."""

    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_AFFIRMATIVE_EVIDENCE_SNAPSHOT_RULE_V1_R5"
            ),
            "affirmative_authority_marker": AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
            "non_authoritative_marker": NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
            "evidence_constructed_from": (
                "THE_IMMUTABLE_CANONICAL_ADMITTED_SNAPSHOT_DECODED_FOR_THE_PURPOSE"
            ),
            "evidence_constructed_from_caller_facing_copies": False,
            "evidence_constructed_from_live_parser_state": False,
            "evidence_is_stored_as_immutable_canonical_bytes": True,
            "evidence_construction_sites": 1,
            "evidence_construction_happens_after_the_snapshot_is_frozen": True,
            "caller_visible_evidence_mutation_changes_affirmative_authority": False,
            "caller_visible_evidence_mutation_changes_admission": False,
            "caller_visible_evidence_mutation_changes_the_result_digest": False,
            "caller_visible_evidence_mutation_changes_authoritative_evidence": False,
            "evidence_fields_derived_from_controller_owned_authority": [
                "admitted",
                "admitted_response_digest",
                "bootstrap_pre_execution_source_binding",
                "calendar_authority_hash",
                "failure_reason",
                "request_digest",
                "result_digest",
                "scientific_authority",
                "trusted_authority_context",
                "worker_authority_hash",
                "worker_bootstrap_manifest_digest",
                "worker_source_manifest_digest",
            ],
            "evidence_cross_checks_the_bound_result_digest": True,
            "evidence_is_address_free": True,
            "evidence_is_deterministic": True,
            "superseded_lineage_evidence_can_emit_the_affirmative_marker": False,
            "mutated_superseded_lineage_evidence_can_be_mistaken_for_r5_authority": False,
        }
    )


# ---------------------------------------------------------------------------
# Material children — re-frozen under this parent
# ---------------------------------------------------------------------------


def authoritative_scientific_execution_boundary() -> dict[str, Any]:
    """R4 immutable authority, bound to one exact live R5 execution identity."""

    closure = audit_scientific_api_closure()
    census = audit_direct_worker_launch_census()
    identity = audit_authoritative_return_state()
    if not closure["closed"]:
        raise IsolatedScientificWorkerR5Error(
            f"the scientific API closure audit refuses: {closure['findings']!r}"
        )
    if not census["closed"]:
        raise IsolatedScientificWorkerR5Error(
            f"the direct worker launch census refuses: {census['findings']!r}"
        )
    if not identity["closed"]:
        raise IsolatedScientificWorkerR5Error(
            f"the construction identity audit refuses: {identity['findings']!r}"
        )
    return _revised(
        r4.authoritative_scientific_execution_boundary(),
        contract_version=AUTHORITATIVE_EXECUTION_BOUNDARY_VERSION,
        reviewed_parent=FAILED_PAD4_R4_SHA256,
        review=FAILED_PAD4_R4_REVIEW,
        review_result=FAILED_PAD4_R4_REVIEW_RESULT,
        defect=(
            "the R4 immutable snapshot was stored correctly but its "
            "WeakKeyDictionary execution binding resolved by equality/hash, so "
            "a distinct unrelated caller object reusing public descriptors could "
            "resolve another execution's authority"
        ),
        rule=(
            "THE FROZEN ADMITTED AUTHORITY RESOLVES ONLY FOR A RECEIVER THAT IS, "
            "BY PYTHON is, THE EXACT OBJECT PASSED TO THE SINGLE CAPABILITY-GATED "
            "BIND, AND ONLY WHILE THAT OBJECT IS ALIVE"
        ),
        authority_mechanism=(
            "IMMUTABLE_CANONICAL_SNAPSHOT_PLUS_NONAUTHORITATIVE_ID_BUCKET_PLUS_"
            "WEAK_LIVE_WITNESS_EXACT_IDENTITY"
        ),
        identity_safe_snapshot_lookup_is_load_bearing=True,
        exact_type_receiver_guard_is_required=True,
        exact_type_receiver_guard_is_load_bearing=False,
        receiver_equality_or_hash_equivalence_is_authority=False,
        identifier_is_only_a_bucket_selector=True,
        identifier_equality_is_authority=False,
        live_witness_is_receiver_required=True,
        registry_retains_execution_strongly=False,
        conditional_cleanup_is_witness_specific=True,
        identifier_reuse_can_rebind_stale_authority=False,
        relay_residual_closed=False,
        repaired_review_finding=REPAIRED_REVIEW_FINDINGS[0],
        authority_owned_steps=list(AUTHORITY_OWNED_STEPS),
        closed_authority_path=(
            "TRUSTED_BOOTSTRAP_PREVERIFICATION_THEN_EXACT_WORKER_LAUNCH_THEN_"
            "CANONICAL_ADMISSION_THEN_FROZEN_SNAPSHOT_THEN_EXACT_LIVE_EXECUTION_"
            "IDENTITY_BINDING_THEN_FROZEN_AFFIRMATIVE_EVIDENCE"
        ),
        construction_identity_audit=identity,
        api_closure_audit=closure,
        direct_worker_launch_census=census,
    )


def scientific_evidence_authority_rule() -> dict[str, Any]:
    """Only the exact R5 closed flow may state affirmative scientific authority."""

    return _revised(
        r4.scientific_evidence_authority_rule(),
        contract_version="ETF_CALENDAR_SCIENTIFIC_EVIDENCE_AUTHORITY_RULE_V1_R5",
        affirmative_authority_marker=AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
        affirmative_scientific_evidence_is_stored_as_immutable_canonical_bytes=True,
        affirmative_evidence_is_constructed_from_the_frozen_admitted_snapshot=True,
        caller_visible_evidence_mutation_can_change_affirmative_authority=False,
        superseded_lineage_marker=r4.AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
        mutated_superseded_lineage_evidence_is_r5_authority=False,
        exact_execution_identity_required_to_resolve_authority=True,
        relay_residual_closed=False,
    )


def controller_authority_context_rule() -> dict[str, Any]:
    """Preserve R4 context agreement under the exact-identity R5 container."""

    return _revised(
        r4.controller_authority_context_rule(),
        contract_version="ETF_CALENDAR_CONTROLLER_AUTHORITY_CONTEXT_RULE_V1_PAD4_R5",
        authority_context_version=AUTHORITY_CONTEXT_VERSION,
        r5_trusted_context_type_required=True,
        three_way_agreement_valid_through_admission=True,
        three_way_agreement_valid_through_returned_authority_lifetime=True,
        returned_authority_can_drift_from_the_trusted_context=False,
        caller_mutation_can_break_the_three_way_agreement=False,
        trusted_context_identity_is_frozen_into_the_affirmative_evidence_bytes=True,
        exact_execution_identity_binding_changes_context_semantics=False,
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    base = r4.proof_order_and_completeness_definition()
    return _revised(
        base,
        contract_version="ETF_CALENDAR_ISOLATED_WORKER_PROOF_ORDER_V1_PAD4_R5",
        exact_execution_identity_binding_required=True,
        identity_safe_snapshot_lookup_is_load_bearing=True,
        exact_type_guard_is_non_load_bearing_defence_in_depth=True,
        relay_residual_closed=False,
        completeness_claim=(
            base["completeness_claim"]
            + "; R5 additionally binds the frozen authority to one exact live "
            "controller-owned execution by weak witness identity, while "
            "id(receiver) is only a non-authoritative bucket selector"
        ),
        required_adversarial_regressions=sorted(
            {
                *base["required_adversarial_regressions"],
                "R4_DESCRIPTOR_REUSE_DEFECT_REPRODUCES_AS_A_CONTROL",
                "DISTINCT_EQUAL_HASH_EQUIVALENT_UNRELATED_OBJECT_IS_REFUSED",
                "DESCRIPTOR_REUSE_ON_UNRELATED_CLASS_IS_REFUSED",
                "UNBOUND_PROPERTY_GETTER_WITH_FOREIGN_RECEIVER_IS_REFUSED",
                "UNBOUND_SNAPSHOT_PROOF_WITH_FOREIGN_RECEIVER_IS_REFUSED",
                "SPOOFED___CLASS___RECEIVER_IS_REFUSED",
                "FOREIGN_REPR_RECEIVER_IS_REFUSED",
                "DIRECT_CONSTRUCTION_IS_REFUSED",
                "NEW_BYPASS_IS_REFUSED",
                "UNSUPPORTED_SUBCLASS_IS_REFUSED",
                "DISTINCT_EXACT_CLASS_NON_OWNED_OBJECT_IS_REFUSED",
                "IDENTIFIER_REUSE_CANNOT_REBIND_STALE_AUTHORITY",
                "DEAD_EXECUTION_CLEANUP_CANNOT_DELETE_NEWER_BINDING",
                "SEQUENTIAL_LEGITIMATE_REQUESTS_REMAIN_INDEPENDENT",
                "AUTHORITY_LOOKUP_CALLS_NO_RECEIVER_CONTROLLED_CODE",
                "AUTHORITATIVE_CLASS_EQ_AND_HASH_REMAIN_OBJECT_IDENTITY_SEMANTICS",
            }
        ),
    )


def science_lineage_and_safety() -> dict[str, Any]:
    return _revised(
        r4.science_lineage_and_safety(),
        contract_version=(
            "ETF_CALENDAR_ISOLATED_WORKER_SCIENCE_LINEAGE_AND_SAFETY_V1_PAD4_R5"
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
            "definition_sha256": FAILED_PAD4_R4_SHA256,
            "review": FAILED_PAD4_R4_REVIEW,
            "review_commit": FAILED_PAD4_R4_REVIEW_COMMIT,
            "review_result": FAILED_PAD4_R4_REVIEW_RESULT,
            "execution_classification": FAILED_PAD4_R4_EXECUTION_CLASSIFICATION,
            "material_children": 30,
            "artifacts_overwritten_by_this_correction": False,
            "namespace_mutated_by_this_correction": False,
            "certified": False,
            "used": False,
            "prospective_observations": 0,
        },
        relay_residual_status="OPEN_RESIDUAL_NOT_CLOSED_BY_R5",
    )


def authoritative_execution_identity_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_AUTHORITATIVE_EXECUTION_IDENTITY_RULE_V1_R5",
            "reviewed_parent": FAILED_PAD4_R4_SHA256,
            "rule": (
                "THE FROZEN ADMITTED AUTHORITY RESOLVES ONLY FOR A RECEIVER THAT "
                "IS, BY PYTHON is, THE EXACT OBJECT PASSED TO THE SINGLE "
                "CAPABILITY-GATED BIND, AND ONLY WHILE THAT OBJECT IS ALIVE"
            ),
            "exact_execution_identity_is_load_bearing": True,
            "identifier_equality_is_authority": False,
            "receiver_equality_is_authority": False,
            "receiver_hash_equivalence_is_authority": False,
            "relay_residual_closed": False,
        }
    )


def identity_safe_snapshot_binding_rule() -> dict[str, Any]:
    audit = audit_authoritative_return_state()
    if not audit["closed"]:
        raise IsolatedScientificWorkerR5Error(
            f"identity-safe binding audit refuses: {audit['findings']!r}"
        )
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_IDENTITY_SAFE_SNAPSHOT_BINDING_RULE_V1_R5",
            "bucket_selector": "id(receiver)",
            "bucket_selector_is_authority": False,
            "registry_key_type": "int",
            "registry_is_keyed_on_receiver": False,
            "registry_is_keyed_on_weakref": False,
            "registry_value": "weak_live_witness_plus_FrozenAuthoritySnapshot",
            "registry_retains_execution_strongly": False,
            "live_witness_comparison": "live_witness is receiver",
            "authority_reader_registry_fetch_count": audit[
                "authority_reader_registry_fetch_count"
            ],
            "conditional_cleanup_is_witness_specific": audit[
                "conditional_cleanup_is_witness_specific"
            ],
            "identifier_reuse_can_rebind_stale_authority": False,
            "behavioral_identity_safety_probe": audit[
                "behavioral_identity_safety_probe"
            ],
        }
    )


def authority_receiver_validation_rule() -> dict[str, Any]:
    audit = audit_authoritative_return_state()
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_AUTHORITY_RECEIVER_VALIDATION_RULE_V1_R5",
            "receiver_none_is_refused": True,
            "receiver_type_guard": "type(receiver) is AuthoritativeScientificExecution",
            "exact_type_guard_is_required": True,
            "exact_type_guard_is_load_bearing": False,
            "load_bearing_guard": "live_witness is receiver",
            "receiver_controlled_lookup_calls": audit[
                "receiver_controlled_lookup_calls"
            ],
            "object_identity___eq___preserved": audit[
                "object_identity___eq___preserved"
            ],
            "object_identity___hash___preserved": audit[
                "object_identity___hash___preserved"
            ],
            "uniform_refusal_error": "AuthoritativeExecutionConstructionError",
        }
    )


def construction_identity_audit_rule() -> dict[str, Any]:
    audit = audit_authoritative_return_state()
    if not audit["closed"]:
        raise IsolatedScientificWorkerR5Error(
            f"construction identity audit refuses: {audit['findings']!r}"
        )
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_CONSTRUCTION_IDENTITY_AUDIT_RULE_V1_R5",
            "audit": audit,
            "checked_in_r4_fails_r5_passes_descriptor_reuse_control_required": True,
            "proof_interpreter_entry_probe": "probe_proof_interpreter_identity_assumptions",
            "proof_interpreter_required_implementation": "CPython",
            "proof_interpreter_required_version": "3.12.14",
            "live_surface_audit_includes_dunders": True,
            "single_authority_reader_required": True,
            "single_capability_gated_bind_required": True,
            "relay_residual_closed": False,
        }
    )


_CHILD_ARTIFACTS: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
    ("authoritative_execution_identity_rule.json", authoritative_execution_identity_rule),
    ("identity_safe_snapshot_binding_rule.json", identity_safe_snapshot_binding_rule),
    ("authority_receiver_validation_rule.json", authority_receiver_validation_rule),
    ("construction_identity_audit_rule.json", construction_identity_audit_rule),
    ("authoritative_scientific_execution_boundary.json", authoritative_scientific_execution_boundary),
    ("authoritative_return_state_rule.json", r4.authoritative_return_state_rule),
    ("canonical_admitted_snapshot_rule.json", canonical_admitted_snapshot_rule),
    ("caller_visible_copy_isolation_rule.json", caller_visible_copy_isolation_rule),
    ("result_digest_lifetime_binding_rule.json", r4.result_digest_lifetime_binding_rule),
    ("affirmative_evidence_snapshot_rule.json", affirmative_evidence_snapshot_rule),
    ("admission_provenance_rule.json", admission_provenance_rule),
    ("scientific_evidence_authority_rule.json", scientific_evidence_authority_rule),
    ("bootstrap_pre_execution_source_binding_rule.json", r4.bootstrap_pre_execution_source_binding_rule),
    ("bootstrap_source_set.json", r4.bootstrap_source_set),
    ("trusted_process_and_isolation_boundary.json", r4.trusted_process_and_isolation_boundary),
    ("proof_interpreter_identity.json", r4.proof_interpreter_identity),
    ("worker_launch_contract.json", r4.worker_launch_contract),
    ("bytecode_execution_binding_rule.json", r4.bytecode_execution_binding_rule),
    ("controller_authority_context_rule.json", controller_authority_context_rule),
    ("project_source_manifest_binding_rule.json", r4.project_source_manifest_binding_rule),
    ("pre_i2_project_source_manifest_fixture.json", r4.pre_i2_project_source_manifest_fixture),
    ("third_party_semantic_authority.json", r4.third_party_semantic_authority),
    ("third_party_installed_content_attestation_rule.json", r4.third_party_installed_content_attestation_rule),
    ("dynamic_import_and_execution_prohibition.json", r4.dynamic_import_and_execution_prohibition),
    ("scientific_request_protocol.json", r4.scientific_request_protocol),
    ("scientific_response_protocol.json", r4.scientific_response_protocol),
    ("worker_io_and_capability_boundary.json", r4.worker_io_and_capability_boundary),
    ("compiled_root_binding_witness_rule.json", r4.compiled_root_binding_witness_rule),
    ("store_root_and_direct_use_grammar.json", r4.store_root_and_direct_use_grammar),
    ("replay_owner_graph_rule.json", r4.replay_owner_graph_rule),
    ("direct_body_dependency_rule.json", r4.direct_body_dependency_rule),
    ("controller_result_admission_rule.json", r4.controller_result_admission_rule),
    ("proof_order_and_completeness_definition.json", proof_order_and_completeness_definition),
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


def isolated_scientific_worker_v1_r5_definition(
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
            "correction_of": FAILED_PAD4_R4_SHA256,
            "correction_is_a_new_architecture_family": False,
            "correction_scope": "BOUNDED_AUTHORITATIVE_EXECUTION_EXACT_IDENTITY_BINDING",
            "repaired_review_findings": list(REPAIRED_REVIEW_FINDINGS),
            "closed_reviewed_bypasses": list(r3.CLOSED_REVIEWED_BYPASSES),
            "closed_reviewed_return_state_mutations": list(
                CLOSED_REVIEWED_RETURN_STATE_MUTATIONS
            ),
            "preserved_valid_portions": list(PRESERVED_VALID_PORTIONS),
            "verbatim_pad4_r4_children": list(VERBATIM_PAD4_R4_CHILDREN),
            "verbatim_pad4_r3_children": list(VERBATIM_PAD4_R3_CHILDREN),
            "verbatim_pad4_r2_children": list(VERBATIM_PAD4_R2_CHILDREN),
            "not_reopened": list(NOT_REOPENED),
            "confirmed_not_a_defect": list(CONFIRMED_NOT_A_DEFECT),
            "failed_pad4_sha256": FAILED_PAD4_SHA256,
            "failed_pad4_certified": False,
            "failed_pad4_artifacts_overwritten": False,
            "failed_pad4_r1_sha256": FAILED_PAD4_R1_SHA256,
            "failed_pad4_r1_certified": False,
            "failed_pad4_r1_artifacts_overwritten": False,
            "failed_pad4_r2_sha256": FAILED_PAD4_R2_SHA256,
            "failed_pad4_r2_certified": False,
            "failed_pad4_r2_artifacts_overwritten": False,
            "failed_pad4_r3_sha256": FAILED_PAD4_R3_SHA256,
            "failed_pad4_r3_certified": False,
            "failed_pad4_r3_artifacts_overwritten": False,
            "failed_pad4_r3_namespace_mutated": False,
            "failed_pad4_r3_material_children": 25,
            "failed_pad4_r4_sha256": FAILED_PAD4_R4_SHA256,
            "failed_pad4_r4_certified": False,
            "failed_pad4_r4_artifacts_overwritten": False,
            "failed_pad4_r4_namespace_mutated": False,
            "failed_pad4_r4_material_children": 30,
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
                # -- the R5 correction ---------------------------------------
                "exact_execution_identity_is_load_bearing": True,
                "identity_safe_snapshot_lookup": True,
                "identifier_is_only_a_bucket_selector": True,
                "identifier_equality_is_authority": False,
                "live_witness_is_receiver_required": True,
                "receiver_is_registry_key": False,
                "weakref_is_registry_key": False,
                "registry_retains_execution_strongly": False,
                "conditional_cleanup_is_witness_specific": True,
                "identifier_reuse_can_rebind_stale_authority": False,
                "receiver_exact_type_guard_required": True,
                "receiver_exact_type_guard_is_load_bearing": False,
                "receiver_controlled_hash_or_equality_in_lookup": False,
                "relay_residual_closed": False,
                # -- the R4 correction, preserved ---------------------------- ---------------------------------------
                "admitted_authority_uses_immutable_canonical_snapshot": True,
                "caller_visible_mutable_result_is_authority_storage": False,
                "caller_visible_mutable_response_is_authority_storage": False,
                "caller_visible_mutable_evidence_is_authority_storage": False,
                "nested_mutable_alias_can_change_authority": False,
                "result_digest_binds_exact_frozen_result_snapshot": True,
                "post_admission_mutation_can_redefine_authority": False,
                "authority_is_recomputed_from_caller_mutated_live_state": False,
                "outer_only_read_only_wrapper_is_sufficient": False,
                "closed_r3_authority_flow_preserved": True,
                "bootstrap_architecture_reopened": False,
                "worker_protocol_reopened": False,
                "admission_decision_procedure_changed_by_this_decision": False,
                "affirmative_evidence_constructed_from_the_frozen_snapshot": True,
                "authority_bearing_mutable_mapping_retained_internally": False,
                "authority_is_repaired_on_read": False,
                "caller_visible_values_are_fresh_deterministic_decodes": True,
                "construction_authority_weakened_by_this_decision": False,
                "second_canonical_encoding_introduced_by_this_decision": False,
                "shallow_copy_is_sufficient_post_admission_protection": False,
                "temporary_parser_state_retained_by_authority": False,
                "worker_package_changed_by_this_decision": False,
                # -- the R3 correction, preserved ----------------------------
                "affirmative_scientific_evidence_created_only_inside_"
                "authoritative_path": True,
                "authoritative_scientific_execution_is_closed_end_to_end": True,
                "bootstrap_preverification_required_before_spawn": True,
                "bootstrap_preverification_mapping_is_diagnostic_not_authority": True,
                "caller_constructed_admission_state_is_authority": False,
                "caller_constructed_outcome_is_authority": False,
                "caller_fabricated_preverification_mapping_is_authority": False,
                "generic_raw_outcome_to_scientific_admission_supported": False,
                "leading_underscore_is_authority_boundary": False,
                "raw_unverified_spawn_in_production_authority_surface": False,
                "scientific_admission_requires_same_authoritative_controller_"
                "execution": True,
                "unverified_worker_outcome_scientifically_admissible": False,
                "worker_can_mint_controller_admission_provenance": False,
                "worker_visible_shared_secret_introduced": False,
                "cryptographic_ceremony_introduced_by_this_decision": False,
                # -- preserved and carried forward ---------------------------
                "arbitrary_installed_version_self_certification_permitted": False,
                "artifact_builder_dispatch_rewrite_required_by_this_decision": False,
                "authoritative_worker_launch_requires_trusted_context": True,
                "bootstrap_mismatch_spawns_worker": False,
                "bootstrap_self_verification_is_authority": False,
                "bootstrap_source_preverified_by_trusted_controller": True,
                "bootstrap_source_set_changed_by_this_decision": False,
                "bootstrap_source_set_complete": True,
                "cached_bytecode_may_override_certified_source": False,
                "calendar_production_code_changed": False,
                "calendar_science_changed": False,
                "candidate_parent_hash_self_embedded": False,
                "closed_ast_store_use_grammar_preserved": True,
                "compiled_root_witness_preserved": True,
                "direct_body_dependency_checks_preserved": True,
                "dynamic_project_import_permitted": False,
                "entrypoint_preverified_before_exec": True,
                "entrypoint_self_verification_is_authority": False,
                "exact_eleven_owner_graph_preserved": True,
                "final_i2_source_manifest_must_be_calendar_parent_bound": True,
                "fork_only_permitted": False,
                "fresh_empty_pycache_namespace_required": True,
                "fresh_exec_required": True,
                "generated_runtime_method_enumeration_required": False,
                "hostile_filesystem_race_resistance_claimed": False,
                "hostile_operating_system_resistance_claimed": False,
                "i2_calendar_production_work_performed": False,
                "lazy_result_permitted": False,
                "long_lived_worker_permitted": False,
                "one_request_one_process": True,
                "operating_system_level_network_sandbox_claimed": False,
                "package_initializer_preverified_before_exec": True,
                "package_initializer_self_verification_is_authority": False,
                "parent_python_objects_shared": False,
                "pickle_ipc_permitted": False,
                "pre_i2_116_module_manifest_role": (
                    "CONFORMANCE_FIXTURE_NOT_FINAL_PRODUCTION_AUTHORITY"
                ),
                "process_isolation_is_scientific_execution_boundary": True,
                "project_source_manifest_required": True,
                "protocol_preverified_before_exec": True,
                "protocol_self_verification_is_authority": False,
                "pycache_prefix_launch_design_redesigned": False,
                "record_declared_installed_file_hashes_must_be_verified": True,
                "reflection_blacklist_complete": False,
                "repository_pycache_authoritative": False,
                "request_is_authority_root": False,
                "response_echo_is_authority_root": False,
                "root_may_be_a_cell_variable_of_a_conforming_owner": False,
                "runtime_object_closure_is_completeness_proof": False,
                "runtime_source_manifest_rederivation_permitted": False,
                "third_party_exact_reviewed_versions_required": True,
                "third_party_installed_file_verification_required": True,
                "third_party_reviewed_artifact_identity_required": True,
                "transitive_mutable_object_closure_required": False,
                "trusted_controller_authority_context_required": True,
                "unexpected_project_module_permitted": False,
                "worker_authoritative_db_write_permitted": False,
                "worker_network_permitted": False,
                "worker_private_signing_key_permitted": False,
                "worker_protocol_reused_unchanged_from_pad4_r2": True,
                "wrapper_installed_guards_permitted": False,
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
    if dict(persisted) != isolated_scientific_worker_v1_r5_definition():
        raise IsolatedScientificWorkerR5Error(
            "persisted exact-identity isolated scientific worker decision "
            "does not reproduce"
        )
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    children = "\n".join(
        f"- `{name}` — `{sha}`"
        for name, sha in sorted(decision["child_definition_sha256"].items())
    )
    return f"""# ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1 — {PROGRAM_TICKET}

**Decision hash:** `{decision["definition_sha256"]}`
**Status:** `{decision["status"]}`
**Final classification:** `{decision["final_classification"]}`
**Required review:** `{decision["required_review"]}`

## Bounded correction

PAD4-R4 `{FAILED_PAD4_R4_SHA256}` remains failed, non-certified, unused,
immutable and at zero observations. Its immutable canonical
`FrozenAuthoritySnapshot`, fresh caller-visible decode isolation, response /
result / affirmative-evidence digest lifetime binding, one supported
authority-bearing flow, bootstrap pre-execution binding, fresh-exec process
isolation, worker protocol, worker source authority, third-party installed-
content authority, compiled root witness, closed store grammar, eleven-owner
graph and direct dependency-body rule remain preserved.

R5 changes only authoritative execution construction identity. The operative rule
is:

```text
THE FROZEN ADMITTED AUTHORITY RESOLVES ONLY FOR A RECEIVER THAT IS, BY PYTHON
is, THE EXACT OBJECT PASSED TO THE SINGLE CAPABILITY-GATED BIND, AND ONLY WHILE
THAT OBJECT IS ALIVE.
```

`id(receiver)` is only a non-authoritative integer bucket selector. One
registry fetch yields a weak live witness plus the frozen snapshot. The
load-bearing authority check is `live_witness is receiver`. The registry is not
keyed by receiver or weakref, does not retain executions strongly, and its
weakref cleanup deletes only the exact witness for which the callback was
created. `type(receiver) is AuthoritativeScientificExecution` is required
defence in depth and is not load-bearing.

Relay remains an open residual and R5 makes no claim that it is closed.

## Material children

{children}

## Safety and authorization

Observations remain zero. Real Stage-B is NO. Calendar authority is not
certified. Prospective collection is not authorized. BTC-019 remains untouched
and Epic T remains unchanged.

Successful R5 implementation authorizes only
`POSTP1-002V2A-PAD4-R5`, the independent exact-hash final xHigh
proof-architecture review. Only an R5 review PASS may make
`POSTP1-001V2A-I2` dependency-satisfied.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    decision = isolated_scientific_worker_v1_r5_definition(registry)
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
            raise IsolatedScientificWorkerR5Error(
                f"persisted {filename} does not reproduce"
            )
        _verify_definition_digest(persisted)
        if decision["child_definition_sha256"].get(
            filename.removesuffix(".json")
        ) != expected["definition_sha256"]:
            raise IsolatedScientificWorkerR5Error(
                f"frozen-return-state isolated scientific worker parent does not "
                f"bind {filename}"
            )
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise IsolatedScientificWorkerR5Error(
            "persisted frozen-return-state isolated scientific worker report "
            "does not reproduce"
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
