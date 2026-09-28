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
    "P0_CALLER_CREATED_POST_ADMISSION_STATE_CAN_REMAIN_INSIDE_AFFIRMATIVE_AUTHORITY",
    "P0_MATERIAL_CHILDREN_MUST_DESCRIBE_THE_IMPLEMENTED_RETURN_STATE_SEMANTICS",
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
    context: r3.ScientificWorkerAuthorityContext,
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
        r3.candidate_review_authority_context(proof_architecture_sha256, origin=origin)
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
        r3.derive_authority_context_from_reviewed_source(
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
        r3.production_authority_context_from_calendar_authority(calendar_authority)
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
    return r3.build_scientific_request(
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
    return r3.preverify_worker_bootstrap_sources(authority_context, launch)


def verify_request_against_authority_context(
    authority_context: ScientificWorkerAuthorityContext,
    request: Mapping[str, Any],
) -> tuple[str, ...]:
    """Every material authority field of the request must be the trusted one.

    This is a pure comparison.  It returns the drifted field names and it is
    never, by itself, an admission: it cannot admit, it cannot create an
    execution and it cannot produce evidence.
    """

    return r3.verify_request_against_authority_context(authority_context, request)


def verify_response_against_authority_context(
    authority_context: ScientificWorkerAuthorityContext,
    response: Mapping[str, Any],
) -> tuple[str, ...]:
    """Every material authority field of the response must be the trusted one.

    A pure comparison, exactly as above: it admits nothing and evidences
    nothing.
    """

    return r3.verify_response_against_authority_context(authority_context, response)


# ---------------------------------------------------------------------------
# The correction — the frozen admitted return state
# ---------------------------------------------------------------------------

AUTHORITATIVE_EXECUTION_BOUNDARY_VERSION = (
    "ETF_CALENDAR_AUTHORITATIVE_SCIENTIFIC_EXECUTION_BOUNDARY_V1_R4"
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
AUTHORITATIVE_SCIENTIFIC_AUTHORITY = "AUTHORITATIVE_CLOSED_CONTROLLER_EXECUTION_V1_R4"

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
    """Create the closed authority boundary and the one operation that owns it.

    Everything authority-bearing is captured in this factory's closure:

    * ``_capability`` is a bare object bound to no module global, no class
      attribute and no returned value, so it cannot be named by a caller;
    * ``_material`` is a closure-private ``WeakKeyDictionary`` that is not
      reachable *by name* from any module global, class attribute or returned
      value, and that only the closed operation writes, so an instance obtained
      by ``__new__`` bypass, by subclassing or by ``copy`` has no material and
      refuses every accessor.  Reflective recovery of the store — through the
      class's closure cells, the instance's weak-reference callback or a
      debugger — is deliberately *not* claimed to be impossible: arbitrary
      reflective namespace manipulation is outside the trusted-process threat
      model this architecture states.  What R4 guarantees instead is that every
      *value* the store holds is an **immutable** snapshot, so no route reaches a
      mutable object carrying authority content.  The store itself is an
      ordinary mutable ``WeakKeyDictionary``: it binds an execution to its
      snapshot and carries no authority content of its own, and the cell holding
      the closure-local reader is writable too, so a reflective route is met by
      the threat model rather than by a claim of impossibility;
    * ``_frozen``, ``_execute_exact_worker``, ``_validate_and_admit`` and
      ``_affirmative_scientific_evidence`` are closure-local, so there is no
      module-accessible spawn primitive, no module-accessible admission function,
      no module-accessible authority-storage write and no module-accessible
      affirmative-evidence constructor.

    ``PAD4-R3`` already established the capability boundary, and
    ``POSTP1-002V2A-PAD4-R3`` reproduced it as valid.  What this factory adds is
    the *representation*: ``_material`` holds one ``FrozenAuthoritySnapshot`` per
    admitted execution — an immutable tuple of immutable canonical bytes and
    immutable scalars — no member of the returned class hands that snapshot to a
    caller, and every mapping-like accessor decodes the frozen bytes afresh.  The
    reviewed defect was that ``_material`` held the live protocol-parser mapping
    and handed it straight back.
    """

    _capability = object()
    _material: "WeakKeyDictionary[Any, FrozenAuthoritySnapshot]" = WeakKeyDictionary()

    def _frozen(execution: Any) -> FrozenAuthoritySnapshot:
        """The one read of the closure-private authority storage.

        It is a closure-local function rather than a method, so the class the
        caller receives exposes no member at all that hands out the stored
        snapshot.  ``PAD4-R3``'s equivalent was a method, and a method on the
        returned object is a caller-visible surface however it is spelled — a
        leading underscore is explicitly *not* the boundary in this
        architecture.
        """

        try:
            return _material[execution]
        except KeyError:
            raise AuthoritativeExecutionConstructionError(
                "this object carries no controller-owned scientific material "
                "and is not an authoritative scientific execution"
            ) from None

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
            """Refuse subclassing outright.

            The closure-private store is keyed on the execution itself, and a
            ``WeakKeyDictionary`` resolves a key by ``__hash__``/``__eq__`` rather
            than by identity.  A subclass that spoofs those two methods would
            therefore resolve to *another* execution's admitted snapshot and
            report its authority while carrying none of its own — an unowned
            object that does not refuse.  Only a subclass can mount that: an
            unrelated class can spoof equality just as easily but has no accessor
            to expose the snapshot through, and the accessors cannot be added to
            the canonical type without mutating a shared class.  Closing
            subclassing therefore closes the route, and it strictly strengthens
            the reviewed ``PAD4-R3`` construction authority rather than weakening
            it: ``PAD4-R3`` accepted the subclass and refused only its accessors.
            """

            raise AuthoritativeExecutionConstructionError(
                "the authoritative scientific execution type may not be "
                "subclassed; the closure-private store is keyed on the execution, "
                "so a subclass that spoofs __eq__ and __hash__ would resolve to "
                "another execution's admitted snapshot"
            )

        def __init__(self, capability: Any = None, material: Any = None) -> None:
            if capability is not _capability:
                raise AuthoritativeExecutionConstructionError(
                    "an authoritative scientific execution is produced only by "
                    "run_isolated_scientific_request; it cannot be constructed"
                )
            _material[self] = verify_frozen_authority_snapshot(material)

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
            try:
                snapshot = _frozen(self)
            except AuthoritativeExecutionConstructionError:
                return "<AuthoritativeScientificExecution UNOWNED>"
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

API_CLOSURE_AUDIT_VERSION = "ETF_CALENDAR_SCIENTIFIC_API_CLOSURE_AUDIT_V1_R4"
RETURN_STATE_AUDIT_VERSION = "ETF_CALENDAR_AUTHORITATIVE_RETURN_STATE_AUDIT_V1_R4"
LAUNCH_CENSUS_AUDIT_VERSION = "ETF_CALENDAR_DIRECT_WORKER_LAUNCH_CENSUS_V1_R4"

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


def audit_authoritative_return_state(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Prove mechanically that caller-visible state cannot reach authority.

    This is the ``R4`` correction's own audit, and it is the mechanical answer to
    the reviewed finding.  It is deterministic and structural: it reports names,
    scopes, types, counts and the outcomes of fixed behavioural probes, never a
    source hash and never a filesystem path.

    It is deliberately *behavioural as well as structural*, because a purely
    name-shaped audit can be satisfied by an implementation that leaks: it
    actually calls the immutability gate with a mutable container, with a short
    field set and with an extra field, and requires each to refuse, so deleting
    the gate's body is a finding rather than an invisible change.  It is also
    *surface-complete*: it enumerates the live class's own members rather than a
    declared allow-list, so an undeclared member that hands out stored state is a
    finding rather than something the audit never looks at.

    It establishes, over this module's own AST and the live types:

    1. the closure-private authority storage is referenced at exactly the three
       declared places — its declaration, the one write in ``__init__`` and the
       one closure-local read — so no second read, no mutating method call, no
       alias and no augmented assignment exists;
    2. the value written at that one write site is the immutability gate's return
       value, the gate is module-level so it can be exercised, and exercising it
       refuses every mutable and malformed snapshot while accepting a complete
       immutable one;
    3. the stored snapshot type is a ``tuple`` subclass carrying exactly the
       frozen authority fields, with no mutating member and no instance
       dictionary, so an admitted snapshot cannot be changed in place by any
       route — including a reflective route that recovers the store and reads a
       value out of it;
    4. the live class exposes exactly the declared caller-facing material and
       nothing else, no member returns stored state, every mapping-like accessor
       returns a *fresh decode* of the frozen canonical bytes, and each accessor
       reads the frozen field it is declared to read;
    5. no refused copy or wrapper mechanism — shallow ``copy.copy``, a
       ``deepcopy`` of a mutable graph, an outer ``MappingProxyType`` or a second
       ``json`` encoding — appears anywhere inside the authority-owning closure;
       and
    6. the container exposes no material setter, no material deleter and no
       instance dictionary, so an admitted execution's representation cannot be
       reassigned from outside either.
    """

    source = _module_source(CONTROLLER_RELATIVE_PATH, project_root)
    tree = ast.parse(source)
    scopes = _scope_index(tree)
    class_scope = (AUTHORITY_OWNING_FACTORY, AUTHORITATIVE_EXECUTION_TYPE_NAME)

    member_return_mechanisms: dict[str, list[str]] = {}
    member_frozen_fields: dict[str, list[str]] = {}
    storage_references: list[dict[str, Any]] = []
    storage_write_sites: list[dict[str, Any]] = []
    construction_material_fields: list[str] = []
    prohibited_sites: list[dict[str, Any]] = []
    reader_definition_scopes: list[list[str]] = []

    for node in ast.walk(tree):
        chain = scopes.get(node, ())
        # (4) every member of the authoritative class, not an allow-list
        if (
            isinstance(node, ast.Return)
            and len(chain) == 3
            and tuple(chain[:2]) == class_scope
        ):
            value = node.value
            mechanism = (
                _dotted_call_name(value.func) or "CALL"
                if isinstance(value, ast.Call)
                else type(value).__name__.upper()
            )
            member_return_mechanisms.setdefault(chain[2], []).append(mechanism)
            for inner in ast.walk(node):
                if not isinstance(inner, ast.Attribute):
                    continue
                if (
                    isinstance(inner.value, ast.Call)
                    and _dotted_call_name(inner.value.func) == AUTHORITY_STORAGE_READER
                ) or (
                    isinstance(inner.value, ast.Name)
                    and inner.value.id == AUTHORITY_SNAPSHOT_LOCAL
                ):
                    member_frozen_fields.setdefault(chain[2], []).append(inner.attr)
        # (1) every reference to the closure-private storage
        if isinstance(node, ast.Name) and node.id == AUTHORITY_STORAGE_NAME:
            storage_references.append(
                {"scope": list(chain), "context": type(node.ctx).__name__}
            )
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if (
                    isinstance(target, ast.Subscript)
                    and isinstance(target.value, ast.Name)
                    and target.value.id == AUTHORITY_STORAGE_NAME
                ):
                    storage_write_sites.append(
                        {
                            "scope": list(chain),
                            "value": (
                                _dotted_call_name(node.value.func) or "CALL"
                                if isinstance(node.value, ast.Call)
                                else type(node.value).__name__.upper()
                            ),
                        }
                    )
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == AUTHORITY_STORAGE_READER:
                reader_definition_scopes.append(list(chain[:-1]))
        if isinstance(node, ast.Call):
            dotted = _dotted_call_name(node.func)
            if dotted == AUTHORITATIVE_EXECUTION_TYPE_NAME and len(node.args) == 2:
                literal = node.args[1]
                if isinstance(literal, ast.Dict):
                    construction_material_fields = sorted(
                        key.value
                        for key in literal.keys
                        if isinstance(key, ast.Constant) and isinstance(key.value, str)
                    )
        # (5) refused copy and wrapper mechanisms inside the authority closure
        if chain and chain[0] == AUTHORITY_OWNING_FACTORY:
            if isinstance(node, (ast.Name, ast.Attribute)):
                dotted = _dotted_call_name(node)
                if dotted in PROHIBITED_AUTHORITY_COPY_MECHANISMS:
                    site = {"mechanism": dotted, "scope": list(chain)}
                    if site not in prohibited_sites:
                        prohibited_sites.append(site)

    # (2) exercise the immutability gate rather than merely naming it
    accepted = {
        "admitted": False,
        "affirmative_evidence_bytes": b"null",
        "affirmative_evidence_digest": "",
        "failure_reason": None,
        "request_digest": "",
        "response_bytes": b"null",
        "response_digest": "",
        "result_bytes": b"null",
        "result_digest": None,
    }
    probes: dict[str, Any] = {
        "COMPLETE_IMMUTABLE_SNAPSHOT": dict(accepted),
        "EXTRA_FIELD": {**accepted, "injected_field": "EXTRA"},
        "MISSING_FIELD": {
            name: value for name, value in accepted.items() if name != "result_digest"
        },
        "MUTABLE_BYTEARRAY_VALUE": {**accepted, "result_bytes": bytearray(b"null")},
        "MUTABLE_MAPPING_VALUE": {**accepted, "result_bytes": {"state": "MUTABLE"}},
        "MUTABLE_SEQUENCE_VALUE": {**accepted, "response_bytes": ["MUTABLE"]},
        "MUTABLE_SET_VALUE": {**accepted, "response_digest": {"MUTABLE"}},
        "NOT_A_MAPPING": ["not", "a", "mapping"],
    }
    gate_probes: dict[str, str] = {}
    for name, probe in sorted(probes.items()):
        try:
            produced = verify_frozen_authority_snapshot(probe)
        except AuthoritativeExecutionConstructionError:
            gate_probes[name] = "REFUSED"
        else:
            gate_probes[name] = (
                "ACCEPTED_AS_FROZEN_SNAPSHOT"
                if type(produced) is FrozenAuthoritySnapshot
                else f"ACCEPTED_AS_{type(produced).__name__}"
            )

    # (2b) exercise construction authority, not only the gate.  Every probe below
    # is an attempt a caller can actually make, and each must refuse.
    construction_probes: dict[str, str] = {}
    try:
        type(
            "ReturnStateAuditProbeSubclass",
            (AuthoritativeScientificExecution,),
            {"__slots__": ()},
        )
    except AuthoritativeExecutionConstructionError:
        construction_probes["SUBCLASS"] = "REFUSED"
    else:  # pragma: no cover - a finding, not a path
        construction_probes["SUBCLASS"] = "ACCEPTED"
    try:
        AuthoritativeScientificExecution()
    except AuthoritativeExecutionConstructionError:
        construction_probes["DIRECT_CONSTRUCTION"] = "REFUSED"
    else:  # pragma: no cover - a finding, not a path
        construction_probes["DIRECT_CONSTRUCTION"] = "ACCEPTED"
    try:
        AuthoritativeScientificExecution(
            object(), {name: b"" for name in FROZEN_AUTHORITY_FIELDS}
        )
    except AuthoritativeExecutionConstructionError:
        construction_probes["FORGED_CAPABILITY"] = "REFUSED"
    else:  # pragma: no cover - a finding, not a path
        construction_probes["FORGED_CAPABILITY"] = "ACCEPTED"
    unowned = AuthoritativeScientificExecution.__new__(AuthoritativeScientificExecution)
    for probe, read in (
        ("NEW_BYPASS_SCALAR_ACCESSOR", lambda: unowned.admitted),
        ("NEW_BYPASS_MAPPING_ACCESSOR", lambda: unowned.result),
        ("NEW_BYPASS_SNAPSHOT_PROOF", unowned.authoritative_snapshot_proof),
    ):
        try:
            read()
        except AuthoritativeExecutionConstructionError:
            construction_probes[probe] = "REFUSED"
        else:  # pragma: no cover - a finding, not a path
            construction_probes[probe] = "ACCEPTED"

    # (3) the stored snapshot type is genuinely immutable
    snapshot_type = {
        "name": FrozenAuthoritySnapshot.__name__,
        "is_tuple_subclass": issubclass(FrozenAuthoritySnapshot, tuple),
        "fields": list(FrozenAuthoritySnapshot._fields),
        "mutating_members_present": sorted(
            name
            for name in MUTATING_CONTAINER_MEMBERS
            if hasattr(FrozenAuthoritySnapshot, name)
        ),
        "has_instance_dictionary": "__dict__" in vars(FrozenAuthoritySnapshot),
    }

    # (4) and (6) the live class surface
    live_members = sorted(
        name
        for name in vars(AuthoritativeScientificExecution)
        if not (name.startswith("__") and name.endswith("__"))
    )
    descriptors: dict[str, dict[str, Any]] = {}
    for name in sorted((*MUTABLE_CONVENIENCE_ACCESSORS, *IMMUTABLE_CONVENIENCE_ACCESSORS)):
        descriptor = vars(AuthoritativeScientificExecution).get(name)
        descriptors[name] = {
            "is_read_only_property": isinstance(descriptor, property)
            and descriptor.fset is None
            and descriptor.fdel is None,
        }
    declared_slots = list(getattr(AuthoritativeScientificExecution, "__slots__", ()))
    has_instance_dictionary = "__dict__" in vars(AuthoritativeScientificExecution)

    findings: list[str] = []
    declared_references = [
        {"scope": list(scope), "context": context}
        for scope, context in DECLARED_AUTHORITY_STORAGE_REFERENCES
    ]
    if storage_references != declared_references:
        findings.append(
            f"THE_AUTHORITY_STORAGE_IS_REFERENCED_OUTSIDE_THE_DECLARED_SITES:"
            f"{storage_references!r}"
        )
    expected_store_scope = [
        AUTHORITY_OWNING_FACTORY,
        AUTHORITATIVE_EXECUTION_TYPE_NAME,
        "__init__",
    ]
    if storage_write_sites != [
        {"scope": expected_store_scope, "value": AUTHORITY_SNAPSHOT_GUARD}
    ]:
        findings.append(
            f"AUTHORITY_STORAGE_IS_NOT_WRITTEN_ONLY_THROUGH_THE_IMMUTABILITY_GATE:"
            f"{storage_write_sites!r}"
        )
    if reader_definition_scopes != [[AUTHORITY_OWNING_FACTORY]]:
        findings.append(
            f"THE_AUTHORITY_STORAGE_READER_IS_NOT_UNIQUELY_CLOSURE_LOCAL:"
            f"{reader_definition_scopes!r}"
        )
    if construction_material_fields != sorted(FROZEN_AUTHORITY_FIELDS):
        findings.append(
            f"THE_CONSTRUCTION_SITE_DOES_NOT_STORE_THE_FROZEN_AUTHORITY_FIELD_SET:"
            f"{construction_material_fields!r}"
        )
    expected_probes = {
        name: ("ACCEPTED_AS_FROZEN_SNAPSHOT" if name == "COMPLETE_IMMUTABLE_SNAPSHOT"
               else "REFUSED")
        for name in probes
    }
    if gate_probes != expected_probes:
        findings.append(
            f"THE_IMMUTABILITY_GATE_DOES_NOT_REFUSE_MUTABLE_OR_MALFORMED_MATERIAL:"
            f"{gate_probes!r}"
        )
    if sorted(construction_probes.values()) != ["REFUSED"] * len(construction_probes):
        findings.append(
            f"A_CONSTRUCTION_BYPASS_IS_NOT_REFUSED:{construction_probes!r}"
        )
    if not snapshot_type["is_tuple_subclass"]:
        findings.append("THE_STORED_SNAPSHOT_TYPE_IS_NOT_IMMUTABLE")
    if snapshot_type["fields"] != list(FROZEN_AUTHORITY_FIELDS):
        findings.append(
            f"THE_STORED_SNAPSHOT_TYPE_DOES_NOT_CARRY_THE_FROZEN_FIELD_SET:"
            f"{snapshot_type['fields']!r}"
        )
    if snapshot_type["mutating_members_present"] or snapshot_type[
        "has_instance_dictionary"
    ]:
        findings.append(
            f"THE_STORED_SNAPSHOT_TYPE_EXPOSES_A_MUTATING_MEMBER:"
            f"{snapshot_type['mutating_members_present']!r}"
        )
    if live_members != sorted(AUTHORITATIVE_EXECUTION_MATERIAL):
        findings.append(
            f"THE_AUTHORITATIVE_CLASS_EXPOSES_AN_UNDECLARED_MEMBER:{live_members!r}"
        )
    returning_members = sorted(member_return_mechanisms)
    if returning_members != sorted(
        (*AUTHORITATIVE_EXECUTION_MATERIAL, *DECLARED_NON_MATERIAL_MEMBERS)
    ):
        findings.append(
            f"A_CLASS_MEMBER_RETURNS_WITHOUT_BEING_DECLARED:{returning_members!r}"
        )
    proof_fields = sorted(set(member_frozen_fields.get(AUTHORITATIVE_SNAPSHOT_PROOF, ())))
    if not proof_fields or not set(proof_fields) <= {
        *FROZEN_AUTHORITY_FIELDS,
        *DECLARED_SNAPSHOT_INTROSPECTION,
    }:
        findings.append(
            f"THE_SNAPSHOT_PROOF_READS_SOMETHING_OTHER_THAN_A_FROZEN_FIELD:"
            f"{proof_fields!r}"
        )
    for name in MUTABLE_CONVENIENCE_ACCESSORS:
        mechanisms = member_return_mechanisms.get(name, [])
        if mechanisms != [CANONICAL_DECODE_CALL]:
            findings.append(
                f"MUTABLE_CONVENIENCE_ACCESSOR_IS_NOT_A_FRESH_CANONICAL_DECODE:"
                f"{name!r}:{mechanisms!r}"
            )
    for name in IMMUTABLE_CONVENIENCE_ACCESSORS:
        mechanisms = member_return_mechanisms.get(name, [])
        if mechanisms != ["ATTRIBUTE"]:
            findings.append(
                f"IMMUTABLE_CONVENIENCE_ACCESSOR_IS_NOT_A_DIRECT_FROZEN_FIELD_READ:"
                f"{name!r}:{mechanisms!r}"
            )
    if member_return_mechanisms.get(AUTHORITATIVE_SNAPSHOT_PROOF) != ["DICT"]:
        findings.append(
            f"THE_SNAPSHOT_PROOF_IS_NOT_A_PURE_DERIVATION_OF_THE_FROZEN_SNAPSHOT:"
            f"{member_return_mechanisms.get(AUTHORITATIVE_SNAPSHOT_PROOF)!r}"
        )
    misbound = sorted(
        f"{name}->{member_frozen_fields.get(name)!r}"
        for name, field in ACCESSOR_FROZEN_FIELDS.items()
        if member_frozen_fields.get(name) != [field]
    )
    if misbound:
        findings.append(f"AN_ACCESSOR_READS_THE_WRONG_FROZEN_FIELD:{misbound!r}")
    if prohibited_sites:
        findings.append(
            f"A_REFUSED_COPY_OR_WRAPPER_MECHANISM_IS_USED_INSIDE_THE_AUTHORITY_CLOSURE:"
            f"{prohibited_sites!r}"
        )
    not_read_only = sorted(
        name for name, row in descriptors.items() if not row["is_read_only_property"]
    )
    if not_read_only:
        findings.append(f"CALLER_FACING_ACCESSOR_IS_NOT_READ_ONLY:{not_read_only!r}")
    if declared_slots != ["__weakref__"] or has_instance_dictionary:
        findings.append(
            f"THE_AUTHORITATIVE_CONTAINER_EXPOSES_INSTANCE_STATE:{declared_slots!r}"
        )
    expected_material = sorted(
        (
            *MUTABLE_CONVENIENCE_ACCESSORS,
            *IMMUTABLE_CONVENIENCE_ACCESSORS,
            AUTHORITATIVE_SNAPSHOT_PROOF,
        )
    )
    if sorted(AUTHORITATIVE_EXECUTION_MATERIAL) != expected_material:
        findings.append(
            f"THE_DECLARED_CALLER_FACING_MATERIAL_IS_NOT_THE_ACCESSOR_SET:"
            f"{expected_material!r}"
        )

    return {
        "audit_version": RETURN_STATE_AUDIT_VERSION,
        "authoritative_return_state": AUTHORITATIVE_RETURN_STATE_VERSION,
        "authority_storage_name": AUTHORITY_STORAGE_NAME,
        "authority_storage_reader": AUTHORITY_STORAGE_READER,
        "authority_storage_references": storage_references,
        "declared_authority_storage_references": declared_references,
        "authority_storage_write_sites": storage_write_sites,
        "authority_storage_reader_scopes": reader_definition_scopes,
        "authority_immutability_gate": AUTHORITY_SNAPSHOT_GUARD,
        "authority_immutability_gate_is_module_level_and_inert": True,
        "authority_immutability_gate_probes": gate_probes,
        "construction_authority_probes": dict(sorted(construction_probes.items())),
        "authority_storage_binding_is_resolved_by_equality_not_identity": True,
        "subclassing_the_authoritative_execution_is_refused": (
            construction_probes.get("SUBCLASS") == "REFUSED"
        ),
        "frozen_authority_snapshot_type": snapshot_type,
        "frozen_authority_fields": list(FROZEN_AUTHORITY_FIELDS),
        "construction_site_material_fields": construction_material_fields,
        "canonical_decode_call": CANONICAL_DECODE_CALL,
        "canonical_encode_call": CANONICAL_ENCODE_CALL,
        "caller_facing_material": list(AUTHORITATIVE_EXECUTION_MATERIAL),
        "live_class_members": live_members,
        "mutable_convenience_accessors": list(MUTABLE_CONVENIENCE_ACCESSORS),
        "immutable_convenience_accessors": list(IMMUTABLE_CONVENIENCE_ACCESSORS),
        "accessor_frozen_fields": dict(sorted(ACCESSOR_FROZEN_FIELDS.items())),
        "declared_non_material_members": list(DECLARED_NON_MATERIAL_MEMBERS),
        "declared_snapshot_introspection": list(DECLARED_SNAPSHOT_INTROSPECTION),
        "returning_class_members": returning_members,
        "material_member_return_mechanisms": {
            name: mechanisms
            for name, mechanisms in sorted(member_return_mechanisms.items())
            if name in AUTHORITATIVE_EXECUTION_MATERIAL
        },
        "material_member_frozen_field_reads": {
            name: sorted(set(fields))
            for name, fields in sorted(member_frozen_fields.items())
            if name in AUTHORITATIVE_EXECUTION_MATERIAL
        },
        "caller_facing_accessor_descriptors": dict(sorted(descriptors.items())),
        "prohibited_authority_copy_mechanisms": list(
            PROHIBITED_AUTHORITY_COPY_MECHANISMS
        ),
        "prohibited_mechanism_sites": prohibited_sites,
        "declared_slots": declared_slots,
        "container_has_instance_dictionary": has_instance_dictionary,
        "findings": findings,
        "closed": not findings,
    }


def _production_reachable_launch_sites() -> list[dict[str, Any]]:
    """Inherited helpers this module re-exports that themselves create a process.

    A file-level classification would hide these: the helper's *source* lives in
    a superseded module, but R4 production code calls it, so the census must name
    it.  Every one found must be a declared non-worker launch site.

    Each row is keyed on the *resolved callable* — its defining module, qualified
    name and primitive — and never on the module attribute that happens to point
    at it, so a second re-export or a diagnostic alias of an already declared
    helper cannot move this candidate's parent hash for a non-material reason.
    """

    found: list[dict[str, Any]] = []
    module = sys.modules[__name__]
    for name in sorted(vars(module)):
        value = getattr(module, name)
        if not isinstance(value, types.FunctionType):
            continue
        if value.__module__ == __name__:
            continue
        try:
            snippet = textwrap.dedent(inspect.getsource(value))
        except OSError:  # pragma: no cover - source always available here
            continue
        for node in ast.walk(ast.parse(snippet)):
            if isinstance(node, ast.Call) and _dotted_call_name(node.func) in (
                LAUNCH_PRIMITIVES
            ):
                found.append(
                    {
                        "callable": value.__name__,
                        "defining_module": value.__module__.rsplit(".", 1)[-1],
                        "primitive": _dotted_call_name(node.func),
                        "qualname": value.__qualname__,
                    }
                )
    deduplicated: list[dict[str, Any]] = []
    for site in found:
        if site not in deduplicated:
            deduplicated.append(site)
    return sorted(
        deduplicated, key=lambda site: (site["qualname"], site["primitive"])
    )


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
    """How the admitted material becomes immutable, and with whose rules."""

    return _definition(
        {
            "contract_version": "ETF_CALENDAR_CANONICAL_ADMITTED_SNAPSHOT_RULE_V1_R4",
            "authority_bearing_representation": "IMMUTABLE_CANONICAL_JSON_BYTES",
            "canonical_encoder": CANONICAL_AUTHORITY_ENCODER,
            "canonical_decoder": CANONICAL_AUTHORITY_DECODER,
            "canonical_digest": CANONICAL_AUTHORITY_DIGEST,
            "canonicalization_is_the_reviewed_worker_protocol": True,
            "second_canonical_encoding_introduced": False,
            "canonical_serialization_rules": [
                "ASCII_ONLY",
                "COMPACT_SEPARATORS",
                "NO_NAN_OR_INFINITY",
                "SORTED_KEYS",
            ],
            "preserved_canonical_rejections": list(PRESERVED_CANONICAL_REJECTIONS),
            "preserved_canonical_rejections_are_exact_protocol_reasons": True,
            "request_transport_only_canonical_rejections": list(
                REQUEST_TRANSPORT_ONLY_CANONICAL_REJECTIONS
            ),
            "preserved_timestamp_rejection": PRESERVED_TIMESTAMP_REJECTION,
            "response_side_re_serialization_equality_check_claimed": False,
            "response_canonical_identity_is_established_by_the_frozen_snapshot": True,
            "frozen_authority_fields": list(FROZEN_AUTHORITY_FIELDS),
            "authority_snapshot_type": AUTHORITY_SNAPSHOT_TYPE,
            "authority_snapshot_is_an_immutable_tuple": True,
            "authority_snapshot_has_a_mutating_api": False,
            "authority_snapshot_value_types": sorted(
                value_type.__name__ for value_type in IMMUTABLE_AUTHORITY_VALUE_TYPES
            ),
            "authority_snapshot_holds_a_mutable_container": False,
            "authority_snapshot_holds_a_nested_mutable_descendant": False,
            # Two different objects, named separately on purpose.  The SNAPSHOT is
            # the immutable tuple that carries the authority content.  The BINDING
            # CONTAINER is the closure-private mapping that binds an execution to
            # its snapshot; it is an ordinary mutable WeakKeyDictionary, it carries
            # no authority content of its own, and it resolves a key by equality
            # rather than identity — which is why subclassing the authoritative
            # execution is refused outright.
            "authority_binding_container_name": AUTHORITY_STORAGE_NAME,
            "authority_binding_container_type": "WeakKeyDictionary",
            "authority_binding_container_is_mutable": True,
            "authority_binding_container_carries_authority_content": False,
            "authority_binding_container_resolves_keys_by_equality_not_identity": True,
            "subclassing_the_authoritative_execution_is_refused": True,
            "snapshot_established_before_the_execution_is_caller_visible": True,
            "mutable_admitted_state_is_exposed_and_frozen_afterwards": False,
            "response_and_result_authority_derive_from_one_frozen_source": True,
            "result_snapshot_is_taken_from_the_frozen_response_snapshot": True,
            "refusal_snapshots_are_canonicalized_the_same_way": True,
            "snapshot_depends_on_object_identity": False,
            "snapshot_depends_on_memory_address": False,
            "snapshot_depends_on_dict_insertion_order": False,
            "snapshot_depends_on_a_temporary_filesystem_path": False,
            "snapshot_depends_on_the_process_identifier": False,
            "snapshot_depends_on_weak_key_dictionary_identity": False,
            "immutability_gate": AUTHORITY_SNAPSHOT_GUARD,
            "immutability_gate_is_module_level_so_it_can_be_exercised": True,
            "immutability_gate_is_inert_and_grants_nothing": True,
            "immutability_gate_refuses_a_mutable_container": True,
            "immutability_gate_refusals_are_mechanically_exercised": True,
            "immutability_gate_is_the_only_write_path_into_authority": True,
            "immutable_authority_value_types": [
                value_type.__name__ for value_type in IMMUTABLE_AUTHORITY_VALUE_TYPES
            ],
            "candidate_snapshot_is_materialized_once_before_validation": True,
        }
    )


def caller_visible_copy_isolation_rule() -> dict[str, Any]:
    """Caller-facing convenience values are detached from authority storage."""

    audit = audit_authoritative_return_state()
    if not audit["closed"]:
        raise IsolatedScientificWorkerR5Error(
            f"the authoritative return-state audit refuses: {audit['findings']!r}"
        )
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_CALLER_VISIBLE_COPY_ISOLATION_RULE_V1_R4",
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[1],
            "caller_facing_material": list(AUTHORITATIVE_EXECUTION_MATERIAL),
            "mutable_convenience_accessors": list(MUTABLE_CONVENIENCE_ACCESSORS),
            "immutable_convenience_accessors": list(IMMUTABLE_CONVENIENCE_ACCESSORS),
            "accessor_mechanism": (
                "FRESH_DETERMINISTIC_DECODE_OF_THE_FROZEN_CANONICAL_BYTES_PER_CALL"
            ),
            "caller_visible_mutable_result_is_authority_storage": False,
            "caller_visible_mutable_response_is_authority_storage": False,
            "caller_visible_mutable_evidence_is_authority_storage": False,
            "nested_mutable_alias_can_change_authority": False,
            "top_level_mutation_is_isolated": True,
            "nested_mapping_mutation_is_isolated": True,
            "nested_sequence_mutation_is_isolated": True,
            "repeated_accessor_values_are_equal": True,
            "repeated_accessor_values_share_mutable_descendants": False,
            "response_and_result_convenience_values_share_mutable_descendants": False,
            "a_class_member_returns_the_authority_storage": False,
            "class_surface_is_a_verified_enumeration_not_an_allow_list": True,
            "authority_storage_reader_is_closure_local_and_not_a_member": True,
            "authority_storage_reachable_through_a_declared_member": False,
            # Honest rather than flat: the class's closure cells are reachable from
            # the returned object, so the binding container and the reader cell can
            # both be recovered reflectively.  That is met by the stated
            # trusted-process threat model, not by a claim of impossibility, and
            # what the correction guarantees is that every value so recovered is an
            # immutable snapshot.
            "authority_storage_reachable_through_closure_cells": True,
            "reflective_recovery_of_the_storage_is_claimed_impossible": False,
            "reflectively_recovered_snapshot_is_immutable": True,
            "reflectively_recovered_binding_container_is_mutable": True,
            "temporary_protocol_parser_state_is_retained_by_authority": False,
            "temporary_admission_state_is_retained_by_authority": False,
            "affirmative_evidence_mapping_is_retained_by_authority": False,
            "caller_supplied_request_object_is_retained_by_authority": False,
            "mapping_proxy_outer_wrapper_is_the_mechanism": False,
            "shallow_copy_is_the_mechanism": False,
            "deep_copy_of_a_mutable_graph_is_the_mechanism": False,
            "authoritative_execution_exposes_a_material_setter": False,
            "authoritative_execution_exposes_a_material_deleter": False,
            "authoritative_execution_has_an_instance_dictionary": False,
            "prohibited_authority_copy_mechanisms": list(
                PROHIBITED_AUTHORITY_COPY_MECHANISMS
            ),
            "return_state_audit": audit,
        }
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
                "ETF_CALENDAR_AFFIRMATIVE_EVIDENCE_SNAPSHOT_RULE_V1_R4"
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
            "mutated_r3_evidence_can_be_mistaken_for_r4_authority": False,
        }
    )


# ---------------------------------------------------------------------------
# Material children — re-frozen under this parent
# ---------------------------------------------------------------------------


def authoritative_scientific_execution_boundary() -> dict[str, Any]:
    """The closed boundary, now with an immutable post-admission representation.

    Every key the reviewed ``PAD4-R3`` child carried is carried here, so a
    reviewer can diff this child against its ``PAD4-R3`` original key by key; the
    additional keys are the return-state correction and nothing else.
    """

    closure = audit_scientific_api_closure()
    census = audit_direct_worker_launch_census()
    if not closure["closed"]:
        raise IsolatedScientificWorkerR5Error(
            f"the scientific API closure audit refuses: {closure['findings']!r}"
        )
    if not census["closed"]:
        raise IsolatedScientificWorkerR5Error(
            f"the direct worker launch census refuses: {census['findings']!r}"
        )
    return _definition(
        {
            "contract_version": AUTHORITATIVE_EXECUTION_BOUNDARY_VERSION,
            "authoritative_return_state": AUTHORITATIVE_RETURN_STATE_VERSION,
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[0],
            "reviewed_parent": FAILED_PAD4_R3_SHA256,
            "review": FAILED_PAD4_R3_REVIEW,
            "review_result": FAILED_PAD4_R3_REVIEW_RESULT,
            "defect": (
                "the closed authority flow was correct through admission and "
                "then stored its authority as a shallow copy whose response "
                "value was the live protocol-parser mapping and whose result "
                "value was that mapping's own nested result object, and handed "
                "both straight back, so caller mutation of a returned mapping "
                "rewrote the authority-bearing state of an admitted, "
                "affirmatively stamped execution while the bound result digest "
                "kept describing what had actually been admitted"
            ),
            "rule": (
                "ONCE SCIENTIFIC ADMISSION SUCCEEDS, NO CALLER MUTATION MAY "
                "CHANGE THE AUTHORITATIVE RESPONSE, RESULT OR AFFIRMATIVE "
                "EVIDENCE REPRESENTED BY THAT ADMITTED EXECUTION"
            ),
            "preserved_r3_rule": (
                "NO OUTCOME CREATED WITHOUT SUCCESSFUL TRUSTED-CONTROLLER "
                "BOOTSTRAP PREVERIFICATION MAY ENTER SCIENTIFIC ADMISSION OR "
                "PRODUCE AFFIRMATIVE SCIENTIFIC AUTHORITY EVIDENCE"
            ),
            "closed_authority_path": (
                "TRUSTED_BOOTSTRAP_PREVERIFICATION_THEN_EXACT_WORKER_LAUNCH_THEN_"
                "EXACT_WORKER_OUTCOME_THEN_CANONICAL_ADMITTED_SNAPSHOT_THEN_"
                "SCIENTIFIC_ADMISSION_THEN_FROZEN_AFFIRMATIVE_EVIDENCE"
            ),
            "authoritative_production_operation": AUTHORITATIVE_PRODUCTION_OPERATION,
            "authoritative_execution_order": list(AUTHORITATIVE_EXECUTION_ORDER),
            "authoritative_execution_material": list(AUTHORITATIVE_EXECUTION_MATERIAL),
            "frozen_authority_fields": list(FROZEN_AUTHORITY_FIELDS),
            "mutable_convenience_accessors": list(MUTABLE_CONVENIENCE_ACCESSORS),
            "immutable_convenience_accessors": list(IMMUTABLE_CONVENIENCE_ACCESSORS),
            "authority_mechanism": (
                "CLOSED_CONTROL_FLOW_AND_CAPABILITY_OWNERSHIP_PLUS_IMMUTABLE_"
                "CANONICAL_ADMITTED_SNAPSHOT_STORAGE"
            ),
            "authority_owning_factory": AUTHORITY_OWNING_FACTORY,
            "authority_owned_steps": list(AUTHORITY_OWNED_STEPS),
            "closed_reviewed_bypasses": list(r3.CLOSED_REVIEWED_BYPASSES),
            "closed_reviewed_return_state_mutations": list(
                CLOSED_REVIEWED_RETURN_STATE_MUTATIONS
            ),
            "closed_r3_authority_flow_preserved": True,
            "admitted_authority_uses_immutable_canonical_snapshot": True,
            "post_admission_representation_is_immutable": True,
            "post_admission_mutation_can_redefine_authority": False,
            "caller_created_post_admission_state_can_remain_inside_authority": False,
            "authority_bearing_mutable_mapping_retained_internally": False,
            "generic_admission_function_exists": False,
            "generic_evidence_function_exists": False,
            "generic_snapshot_store_function_exists": False,
            "module_accessible_authority_storage_write_exists": False,
            "module_accessible_snapshot_gate_is_inert_and_grants_nothing": True,
            "authority_snapshot_type": AUTHORITY_SNAPSHOT_TYPE,
            "authority_snapshot_is_an_immutable_tuple": True,
            "no_class_member_returns_authority_storage": True,
            "return_state_audit_is_behavioural_not_only_structural": True,
            "construction_authority_probes_are_behavioural": True,
            "construction_authority_strengthened_by_this_decision": True,
            "subclassing_the_authoritative_execution_is_refused": True,
            "generic_raw_outcome_type_exists_in_production": False,
            "raw_unverified_spawn_in_production_authority_surface": False,
            "raw_unverified_spawn_location": RAW_REVIEW_HARNESS_RELATIVE_PATH,
            "leading_underscore_is_authority_boundary": False,
            "isinstance_of_a_public_dataclass_is_authority": False,
            "field_values_are_authority": False,
            "class_naming_is_authority": False,
            "caller_may_construct_the_authoritative_execution": False,
            "construction_bypass_yields_unowned_object_that_refuses": True,
            "construction_authority_weakened_by_this_decision": False,
            "cryptographic_ceremony_introduced": False,
            "worker_visible_secret_introduced": False,
            "worker_computable_mac_key_introduced": False,
            "api_closure_audit": closure,
            "direct_worker_launch_census": census,
        }
    )


def scientific_evidence_authority_rule() -> dict[str, Any]:
    """Only the closed flow may state that a scientific execution is authority."""

    return _revised(
        r3.scientific_evidence_authority_rule(),
        contract_version="ETF_CALENDAR_SCIENTIFIC_EVIDENCE_AUTHORITY_RULE_V1_R4",
        affirmative_authority_marker=AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
        affirmative_scientific_evidence_is_stored_as_immutable_canonical_bytes=True,
        affirmative_evidence_is_constructed_from_the_frozen_admitted_snapshot=True,
        caller_visible_evidence_mutation_can_change_affirmative_authority=False,
        superseded_lineage_marker=r3.AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
        mutated_superseded_lineage_evidence_is_r4_authority=False,
    )


def controller_authority_context_rule() -> dict[str, Any]:
    """Repair C, extended across the lifetime of the returned authority."""

    return _revised(
        r3.controller_authority_context_rule(),
        contract_version="ETF_CALENDAR_CONTROLLER_AUTHORITY_CONTEXT_RULE_V1_PAD4_R4",
        authority_context_version=AUTHORITY_CONTEXT_VERSION,
        r4_trusted_context_type_required=True,
        three_way_agreement_valid_through_admission=True,
        three_way_agreement_valid_through_returned_authority_lifetime=True,
        returned_authority_can_drift_from_the_trusted_context=False,
        caller_mutation_can_break_the_three_way_agreement=False,
        trusted_context_identity_is_frozen_into_the_affirmative_evidence_bytes=True,
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    base = r3.proof_order_and_completeness_definition()
    return _revised(
        base,
        contract_version="ETF_CALENDAR_ISOLATED_WORKER_PROOF_ORDER_V1_PAD4_R4",
        controller_or_review_order=list(AUTHORITATIVE_EXECUTION_ORDER[:5]),
        controller_admission_order=list(AUTHORITATIVE_EXECUTION_ORDER[5:]),
        admitted_authority_is_frozen_before_it_becomes_caller_visible=True,
        caller_facing_access_is_a_fresh_decode_of_frozen_bytes=True,
        post_admission_mutation_can_redefine_authority=False,
        # the list below unions this parent's own required regressions with every
        # one inherited from the reviewed PAD4-R3 set.  An inherited entry names
        # the property its own parent required, so an R3-framed name is read
        # against PAD4-R3 rather than reinterpreted under this parent; the
        # R4-framed counterpart of each such property is listed alongside it.
        inherited_adversarial_regressions_are_read_against_their_own_parent=True,
        completeness_claim=(
            "the scientific answer is produced by certified source whose "
            "pre-trust bootstrap set was bound by already-trusted controller code "
            "before any of it executed, executed as certified bytecode, under a "
            "certified interpreter, against a reviewed third-party artifact whose "
            "installed bytes were verified first, in a process that shares no "
            "mutable Python state with the application, every material authority "
            "identity reproduces against a trusted controller context, the "
            "preverification, the launch, the outcome, the canonicalisation, the "
            "digest binding, the admission and the affirmative evidence are one "
            "closed controller operation that no caller can enter part-way and no "
            "caller can compose, and what that operation admitted is what the "
            "returned authority permanently represents because the authority is "
            "an immutable canonical snapshot and every caller-facing value is a "
            "detached decode of it"
        ),
        required_adversarial_regressions=sorted(
            {
                *base["required_adversarial_regressions"],
                "AFFIRMATIVE_EVIDENCE_MUTATION_IS_ISOLATED",
                "BOUND_RESULT_DIGEST_REPRODUCES_FROM_THE_FROZEN_SNAPSHOT",
                "CALLER_MUTATED_NESTED_MAPPING_CANNOT_CHANGE_AUTHORITY",
                "CALLER_MUTATED_NESTED_SEQUENCE_CANNOT_CHANGE_AUTHORITY",
                "CALLER_MUTATED_RESPONSE_CANNOT_CHANGE_AUTHORITY",
                "CALLER_MUTATED_RESULT_CANNOT_CHANGE_AUTHORITY",
                "CROSS_ACCESSOR_VALUES_SHARE_NO_MUTABLE_DESCENDANT",
                "DISCARDED_TEMPORARY_PARSER_STATE_CANNOT_CHANGE_AUTHORITY",
                "REPEATED_READS_RETURN_THE_ORIGINAL_ADMITTED_STATE",
                "A_REFUSAL_CANNOT_BE_PROMOTED_TO_AN_ADMITTED_EXECUTION",
                "A_SUBCLASS_CANNOT_SPOOF_EQUALITY_TO_INHERIT_ADMITTED_AUTHORITY",
                "NO_CLASS_MEMBER_HANDS_OUT_THE_AUTHORITY_STORAGE",
                "SEQUENTIAL_REQUESTS_HAVE_INDEPENDENT_RETURN_STATE",
                "SUPERSEDED_LINEAGE_EVIDENCE_IS_NOT_R4_AUTHORITY",
                "THE_FROZEN_AUTHORITY_SNAPSHOT_HAS_NO_MUTATING_API",
                "THE_IMMUTABILITY_GATE_REFUSES_MUTABLE_AND_MALFORMED_MATERIAL",
                "THE_REVIEWED_R3_RETURN_STATE_DEFECT_REPRODUCES_AS_A_CONTROL",
            }
        ),
    )


def science_lineage_and_safety() -> dict[str, Any]:
    return _revised(
        r3.science_lineage_and_safety(),
        contract_version=(
            "ETF_CALENDAR_ISOLATED_WORKER_SCIENCE_LINEAGE_AND_SAFETY_V1_PAD4_R4"
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
            "definition_sha256": FAILED_PAD4_R3_SHA256,
            "decision_commit": FAILED_PAD4_R3_DECISION_COMMIT,
            "review": FAILED_PAD4_R3_REVIEW,
            "review_commit": FAILED_PAD4_R3_REVIEW_COMMIT,
            "review_result": FAILED_PAD4_R3_REVIEW_RESULT,
            "execution_classification": FAILED_PAD4_R3_EXECUTION_CLASSIFICATION,
            "material_children": 25,
            "artifacts_overwritten_by_this_correction": False,
            "namespace_mutated_by_this_correction": False,
            "certified": False,
            "used": False,
            "prospective_observations": 0,
        },
    )


_CHILD_ARTIFACTS: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
    (
        "authoritative_scientific_execution_boundary.json",
        authoritative_scientific_execution_boundary,
    ),
    ("authoritative_return_state_rule.json", authoritative_return_state_rule),
    ("canonical_admitted_snapshot_rule.json", canonical_admitted_snapshot_rule),
    (
        "caller_visible_copy_isolation_rule.json",
        caller_visible_copy_isolation_rule,
    ),
    (
        "result_digest_lifetime_binding_rule.json",
        result_digest_lifetime_binding_rule,
    ),
    (
        "affirmative_evidence_snapshot_rule.json",
        affirmative_evidence_snapshot_rule,
    ),
    ("admission_provenance_rule.json", admission_provenance_rule),
    ("scientific_evidence_authority_rule.json", scientific_evidence_authority_rule),
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
            "correction_of": FAILED_PAD4_R3_SHA256,
            "correction_is_a_new_architecture_family": False,
            "correction_scope": "BOUNDED_POST_ADMISSION_RETURN_STATE_IMMUTABILITY",
            "repaired_review_findings": list(REPAIRED_REVIEW_FINDINGS),
            "closed_reviewed_bypasses": list(r3.CLOSED_REVIEWED_BYPASSES),
            "closed_reviewed_return_state_mutations": list(
                CLOSED_REVIEWED_RETURN_STATE_MUTATIONS
            ),
            "preserved_valid_portions": list(PRESERVED_VALID_PORTIONS),
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
                # -- the R4 correction ---------------------------------------
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
            "persisted frozen-return-state isolated scientific worker decision "
            "does not reproduce"
        )
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    owners = "\n".join(f"- `{owner}`" for owner in FROZEN_REPLAY_OWNERS)
    lineage = "\n".join(f"- `{sha}`" for sha in FAILED_ARCHITECTURE_LINEAGE)
    bootstrap = "\n".join(
        f"{index}. `{path}`"
        for index, path in enumerate(decision["worker_bootstrap_source_set"], start=1)
    )
    order = "\n".join(f"{step}" for step in AUTHORITATIVE_EXECUTION_ORDER)
    mutations = "\n".join(
        f"- `{name}`" for name in CLOSED_REVIEWED_RETURN_STATE_MUTATIONS
    )
    preserved = "\n".join(f"- `{name}`" for name in PRESERVED_VALID_PORTIONS)
    verbatim = "\n".join(f"- `{name}`" for name in VERBATIM_PAD4_R3_CHILDREN)
    storage = "\n".join(f"- `{name}`" for name in FROZEN_AUTHORITY_FIELDS)
    children = "\n".join(
        f"- `{name}` — `{sha}`"
        for name, sha in sorted(decision["child_definition_sha256"].items())
    )
    return f"""# ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1 — {PROGRAM_TICKET}

**Decision hash:** `{decision["definition_sha256"]}`
**Status:** `{decision["status"]}`
**Final classification:** `{decision["final_classification"]}`
**Required review:** `{decision["required_review"]}`

## What this corrects

`{FAILED_PAD4_R3_REVIEW}` failed the `PAD4-R3` candidate
`{FAILED_PAD4_R3_SHA256}` with:

```text
{FAILED_PAD4_R3_REVIEW_RESULT}
```

Admission itself was correct. The failure happened *after* successful admission:
the closed flow stored its authority as a shallow copy whose `response` value was
the live protocol-parser mapping and whose `result` value was that mapping's own
nested `result` object, and handed both straight back. Mutating a returned
mapping therefore rewrote the authority-bearing state of an admitted,
affirmatively stamped execution, while the bound `result_digest` kept describing
what had actually been admitted.

This is a bounded return-state / authority-container correction. It is not a
bootstrap, process-isolation, bytecode, source-authority, third-party-authority
or worker-protocol correction, and it is not a `PAD5`.

## The frozen rule

```text
ONCE SCIENTIFIC ADMISSION SUCCEEDS, NO CALLER MUTATION MAY CHANGE THE
AUTHORITATIVE RESPONSE, RESULT OR AFFIRMATIVE EVIDENCE REPRESENTED BY THAT
ADMITTED EXECUTION.
```

Equivalently: what was admitted is what the authority permanently represents,
for the whole lifetime of the admitted execution.

## The authority-bearing storage

The authority stops being a Python container. These nine fields are the whole of
what an admitted execution represents, and every one of them holds `bytes`,
`str`, `bool` or `None`:

{storage}

There is therefore no nested mutable descendant to reach, and no read-only
wrapper is used: an outer `MappingProxyType` over a mutable graph would leave
every nested container writable and is explicitly **not** the mechanism. The
canonical serialisation is the already reviewed worker protocol
`{CANONICAL_AUTHORITY_ENCODER}` — no second canonical encoding was invented — and
`{CANONICAL_AUTHORITY_DECODER}` produces a fresh, fully detached object graph on
every mapping-like accessor call.

## The closed authoritative order

```text
{order}
```

Affirmative evidence is constructed *from* the frozen snapshot, and the admitted
execution is already frozen when it first becomes caller-visible. There is no
window in which mutable admitted state is exposed and frozen afterwards.

## Closed reviewed return-state mutations

{mutations}

## Authority mechanism

Capability ownership and closed control flow, preserved exactly from the reviewed
`PAD4-R3`, plus immutable canonical snapshot storage. Not naming, not a field
value, not a dataclass identity, not a secret, not a signature, and not a
defensive copy bolted onto an accessor. `{AUTHORITATIVE_SNAPSHOT_PROOF}()`
reproduces the bound digests from the frozen bytes alone.

## Preserved valid portions

{preserved}

## Children carried forward byte-identically from `PAD4-R3`

{verbatim}

## Worker bootstrap source set

Unchanged from the reviewed `PAD4-R2` set carried through `PAD4-R3`, because this
correction is entirely parent-side and post-admission.

{bootstrap}

**Bootstrap manifest digest:** `{decision["worker_bootstrap_manifest_digest"]}`

## Source authority

- PRE-I2 conformance fixture: {decision["pre_i2_project_source_module_count"]} modules
  at `{decision["pre_i2_project_source_manifest_digest"]}`
  (role `{decision["pre_i2_project_source_manifest_role"]}`)
- Candidate worker source universe:
  {decision["candidate_worker_source_module_count"]} modules at
  `{decision["candidate_worker_source_manifest_digest"]}`
- Third-party authority digest: `{decision["third_party_authority_digest"]}`

## Preserved eleven replay owners

{owners}

## Failed architecture lineage — immutable, non-certified, unused

{lineage}

Trusted persistence `{CERTIFIED_DEPENDENCY_SHA256}` is closed, certified,
unchanged and not re-reviewed by this decision.

## Material children ({decision["material_child_count"]})

{children}

## Safety

Observations remain **0**. No real Stage-B evaluation ran. The ETF calendar is
**not** certified, no calendar production code changed, collection is **NOT
AUTHORIZED**, `BTC-019` is untouched with its sealed sample unopened, and Epic T
is unchanged.

Successful implementation authorizes only `POSTP1-002V2A-PAD4-R4`. It does
**not** authorize `POSTP1-001V2A-I2`, `POSTP1-001V2R1`, `POSTP1-003R3`,
`POSTP1-004` or any prospective collection.
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
