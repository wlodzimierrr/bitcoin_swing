"""Authority-closed isolated scientific worker architecture for the ETF calendar.

``POSTP1-002V2A-PAD4-R2`` independently regenerated the exact ``PAD4-R2``
candidate ``68e6bd07...e52561``, reproduced 22/22 material children and 22/22
parent bindings, and then failed it with::

    FAIL — AUTHORITATIVE LAUNCH / ADMISSION BYPASS

The review reproduced a great deal as **valid** and a successor may not reopen,
rebuild or renegotiate it: the four-member bootstrap set and its pre-execution
binding on the authoritative path, fresh-exec process isolation, Repair A's
fresh empty per-worker bytecode-cache namespace, Repair B's frozen source
authority, Repair C's trusted controller authority context, Repair D's
third-party semantic and installed-content authority, the compiled root
witness, the closed AST store-use grammar, the exact eleven-owner graph and the
direct dependency-body rule.  Same-process runtime-object attestation,
transitive mutable-object closure, reflection-blacklist completeness,
generated-method enumeration, the process-isolation architecture, the
bootstrap-source derivation, the fresh-pycache architecture and third-party
RECORD/content authority all stay closed.

The blocking invariant was an **API / admission** defect, local to one module's
admission surface::

    Scientific admission neither requires nor authenticates the
    trusted-controller bootstrap pre-verification that its evidence claims
    occurred.

``PAD4-R2`` exposed ``WorkerProcessOutcome`` and ``AdmissionOutcome`` as public
frozen dataclasses with no construction guard, and ``admit_worker_result`` and
``scientific_response_evidence`` as separately callable authority-escalation
operations.  Three independent reproducers each obtained an admitted fabricated
scientific result: the private raw spawn helper on a drifted bootstrap tree; a
caller-fabricated PASS ``bootstrap_pre_verification`` mapping, after which the
evidence falsely attested ``ALREADY_TRUSTED_CONTROLLER_CODE``; and a hand-built
``WorkerProcessOutcome`` with **no subprocess ever created**, using only public
names.  The only boundary was a leading underscore, a docstring and a test.

``POSTP1-001V2A-PAD4-R3`` corrects exactly that and nothing else.  It is a
bounded correction of ``PAD4-R2`` and is deliberately **not** a ``PAD5``: no new
proof-architecture family is created, and the failed ``PAD4``
``cc1b325a...7b809e78``, ``PAD4-R1`` ``3415765f...fde37ebc`` and ``PAD4-R2``
``68e6bd07...e52561`` namespaces all stay immutable, non-certified, unused and
at zero observations.  The frozen rule is::

    NO OUTCOME CREATED WITHOUT SUCCESSFUL TRUSTED-CONTROLLER BOOTSTRAP
    PREVERIFICATION MAY ENTER SCIENTIFIC ADMISSION OR PRODUCE AFFIRMATIVE
    SCIENTIFIC AUTHORITY EVIDENCE.

The correction is **structural, not another value-level echo check**.  The
generic composition ``raw outcome + generic admission + generic evidence`` is
removed from the production scientific API entirely.  ``admit_worker_result``,
``scientific_response_evidence``, ``run_scientific_worker``,
``WorkerProcessOutcome``, ``AdmissionOutcome`` and the raw spawn helper do not
exist in this module.  Their logic is folded inside exactly one closed
controller operation::

    run_isolated_scientific_request(
        trusted_authority_context, scientific_request, launch_material
    )

which owns preverify -> allocate -> spawn -> validate -> admit -> construct
evidence and returns an ``AuthoritativeScientificExecution``.  That type's
material lives in a closure-private registry that only the closed flow can
write, so ``__new__`` bypass, subclassing, attribute assignment and direct
construction all yield an object that refuses every accessor.  A leading
underscore is explicitly *not* the boundary; capability ownership is.

No cryptography, no shared secret, no worker-visible MAC key and no
worker-computable provenance was introduced: the worker cannot mint the
controller-side condition, because that condition is *being the closed
controller call*, which no request, response or worker can be.

The corrected proof strategy is::

    AUTHORITATIVE_SCIENTIFIC_EXECUTION_CLOSURE
    + BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING
    + CERTIFIED_SOURCE_AUTHORITY
    + FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY
    + FROZEN_CPYTHON
    + FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE
    + CLOSED_STORE_GRAMMAR
    + COMPILED_ROOT_WITNESS
    + ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER
    + TRUSTED_CONTROLLER_AUTHORITY_CONTEXT

This module is a pre-data decision builder, a static audit specification and
the authoritative reference controller.  It never collects, persists, signs or
certifies anything, and it changes no ETF calendar production code.  The worker
package is reused byte-identically from ``PAD4-R2``: the bootstrap source set
and its digest ``1811e04d...ead411`` are unchanged, because this correction is
local to the controller admission surface.
"""

from __future__ import annotations

import argparse
import ast
import inspect
import json
import shutil
import subprocess
import sys
import textwrap
import types
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence
from weakref import WeakKeyDictionary

from btc_predictor.research import etf_calendar_compiled_binding_witness as witness
from btc_predictor.research import etf_calendar_isolated_scientific_worker as pad4
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r1 as r1
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r2 as r2
from btc_predictor.research import etf_calendar_runtime_owner_attestation as attestation
from btc_predictor.research import etf_calendar_store_capability_normal_form_r1 as narrow
from etf_calendar_worker import protocol_r2 as protocol


DECISION_VERSION = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
PROGRAM_TICKET = "POSTP1-001V2A-PAD4-R3"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_isolated_scientific_worker_v1_r3"
DEFINITION_FILENAME = "etf_calendar_isolated_scientific_worker_v1_r3_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R3_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_REVIEW"
FINAL_CLASSIFICATION = (
    "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R3_READY_FOR_FINAL_XHIGH_REVIEW"
)
PROOF_STRATEGY = (
    "AUTHORITATIVE_SCIENTIFIC_EXECUTION_CLOSURE_PLUS_"
    "BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_PLUS_CERTIFIED_SOURCE_AUTHORITY_PLUS_"
    "FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY_PLUS_FROZEN_CPYTHON_PLUS_"
    "FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE_PLUS_CLOSED_STORE_GRAMMAR_PLUS_"
    "COMPILED_ROOT_WITNESS_PLUS_ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_PLUS_"
    "TRUSTED_CONTROLLER_AUTHORITY_CONTEXT"
)
REQUIRED_REVIEW = (
    "POSTP1-002V2A-PAD4-R3_INDEPENDENT_EXACT_HASH_FINAL_XHIGH_"
    "PROOF_ARCHITECTURE_REVIEW"
)

#: The failed ``PAD4-R2`` parent this ticket corrects, preserved unchanged.
FAILED_PAD4_R2_SHA256 = (
    "68e6bd074a027900b2f3dde3da0a31b6d1cb2f1b9fc6c563e9b45bdc70e52561"
)
FAILED_PAD4_R2_REVIEW = "POSTP1-002V2A-PAD4-R2"
FAILED_PAD4_R2_REVIEW_RESULT = "FAIL — AUTHORITATIVE LAUNCH / ADMISSION BYPASS"
FAILED_PAD4_R2_DECISION_COMMIT = "d6b5565a7006eec323e990d906e3a1240a2ee807"
FAILED_PAD4_R2_REVIEW_COMMIT = "8161d808b03ee7359ce64a30d8c22ddf1873b3ce"
FAILED_PAD4_R1_SHA256 = r2.FAILED_PAD4_R1_SHA256
FAILED_PAD4_SHA256 = r2.FAILED_PAD4_SHA256

#: The one blocking finding this bounded correction repairs, and nothing else.
REPAIRED_REVIEW_FINDINGS: tuple[str, ...] = (
    "P0_SCIENTIFIC_ADMISSION_DOES_NOT_REQUIRE_TRUSTED_BOOTSTRAP_PREVERIFICATION",
    "P0_AUTHORITY_BEARING_OUTCOME_AND_ADMISSION_STATE_ARE_CALLER_CONSTRUCTIBLE",
)

#: The exact bypasses ``POSTP1-002V2A-PAD4-R2`` reproduced, each of which this
#: correction must close and each of which has a mandatory regression here.
CLOSED_REVIEWED_BYPASSES: tuple[str, ...] = (
    "CALLER_BUILT_ADMISSION_STATE_INTO_AFFIRMATIVE_EVIDENCE",
    "CALLER_FABRICATED_PASS_BOOTSTRAP_PRE_VERIFICATION_MAPPING",
    "HAND_BUILT_WORKER_PROCESS_OUTCOME_WITH_NO_SUBPROCESS",
    "RAW_UNVERIFIED_SPAWN_HELPER_INTO_GENERIC_ADMISSION",
)

#: Independently reproduced as valid by ``POSTP1-002V2A-PAD4-R2``, carried
#: forward intact, and explicitly *not* rebuilt or renegotiated here.
PRESERVED_VALID_PORTIONS: tuple[str, ...] = (
    "BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_ON_THE_AUTHORITATIVE_PATH",
    "BYTECODE_EXECUTION_BINDING_REPAIR_A",
    "CANONICAL_NON_EXECUTABLE_IPC",
    "CLOSED_STORE_GRAMMAR",
    "COMPILED_ROOT_WITNESS",
    "DIRECT_DEPENDENCY_BODY_RULE",
    "EXACT_ELEVEN_OWNER_GRAPH",
    "FOUR_MEMBER_BOOTSTRAP_SOURCE_SET",
    "FRESH_EMPTY_PYCACHE_NAMESPACE",
    "FRESH_EXEC_ISOLATION",
    "FROZEN_SOURCE_AUTHORITY_REPAIR_B",
    "ONE_REQUEST_ONE_PROCESS_LIFECYCLE",
    "RECORD_INSTALLED_CONTENT_VERIFICATION_BEFORE_DEPENDENCY_EXECUTION",
    "THIRD_PARTY_EXACT_VERSION_AND_ARTIFACT_AUTHORITY_REPAIR_D",
    "TRUSTED_CONTROLLER_AUTHORITY_CONTEXT_REPAIR_C",
)

#: Explicitly *not* reopened by this correction.
NOT_REOPENED: tuple[str, ...] = tuple(
    sorted(
        {
            *r2.NOT_REOPENED,
            "BOOTSTRAP_SOURCE_DERIVATION",
            "FRESH_PYCACHE_ARCHITECTURE",
            "PROCESS_ISOLATION_ARCHITECTURE",
            "THIRD_PARTY_RECORD_AND_CONTENT_AUTHORITY",
        }
    )
)

#: ``POSTP1-002V2A-PAD4-R2`` independently re-evaluated this secondary
#: candidate and confirmed it is **not** a defect.  It is not reopened here and
#: behaviour is unchanged.
CONFIRMED_NOT_A_DEFECT: tuple[str, ...] = (
    "CANDIDATE_REVIEW_AUTHORITY_CONTEXT_ACCEPTS_A_WELL_FORMED_CANDIDATE_SHA",
)

PROJECT_ROOT = r2.PROJECT_ROOT
CALENDAR_MODULE = witness.CALENDAR_MODULE
CALENDAR_SOURCE = witness.CALENDAR_SOURCE
CERTIFIED_DEPENDENCY_VERSION = witness.CERTIFIED_DEPENDENCY_VERSION
CERTIFIED_DEPENDENCY_SHA256 = witness.CERTIFIED_DEPENDENCY_SHA256
FAILED_ARCHITECTURE_LINEAGE = (*r2.FAILED_ARCHITECTURE_LINEAGE, FAILED_PAD4_R2_SHA256)
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

#: This module's own path, used by the mechanical API-closure audit.  It is a
#: *relative* path resolved under the certified project root so that the audit
#: is reproducible from any working directory.
CONTROLLER_RELATIVE_PATH = (
    "btc_predictor/research/etf_calendar_isolated_scientific_worker_r3.py"
)

#: The deliberately non-production raw reproduction harness.  It lives outside
#: the production scientific-controller package so that no production module
#: can compose a raw spawn with an admission surface, and it exists only so the
#: reviewed ``PAD4-R2`` bypasses can be reproduced as controls.
RAW_REVIEW_HARNESS_RELATIVE_PATH = (
    "btc_predictor/tests/etf_calendar_raw_worker_harness_r3.py"
)

#: The superseded, failed, non-certified controller modules.  They are kept
#: byte-identical so their own frozen namespaces keep reproducing; they are not
#: R3 authority and this module never delegates admission or evidence to them.
FAILED_LINEAGE_CONTROLLER_MODULES: tuple[str, ...] = (
    "btc_predictor/research/etf_calendar_isolated_scientific_worker.py",
    "btc_predictor/research/etf_calendar_isolated_scientific_worker_r1.py",
    "btc_predictor/research/etf_calendar_isolated_scientific_worker_r2.py",
)


class IsolatedScientificWorkerR3Error(r2.IsolatedScientificWorkerR2Error):
    """Raised when the authority-closed worker architecture must refuse."""


class AuthoritativeExecutionConstructionError(IsolatedScientificWorkerR3Error):
    """Raised when authoritative scientific material is not controller-owned.

    Every raise means a caller tried to obtain, fabricate or read affirmative
    scientific authority that the closed controller operation did not create.
    """


BootstrapSourcePreVerificationError = r2.BootstrapSourcePreVerificationError


def _revised(base: Mapping[str, Any], **overrides: Any) -> dict[str, Any]:
    """Re-freeze a reviewed ``PAD4-R2`` child contract under this parent.

    Every preserved contract is carried forward as the exact reviewed payload
    plus the enumerated corrections, so a reviewer can diff a child against its
    ``PAD4-R2`` original instead of re-reading a restatement.
    """

    payload = {
        name: value for name, value in base.items() if name != "definition_sha256"
    }
    payload.update(overrides)
    return _definition(payload)


# ---------------------------------------------------------------------------
# Preserved, reviewed and reused verbatim from PAD4-R2
# ---------------------------------------------------------------------------
#
# The worker package, its bootstrap set, the bootstrap pre-execution binding,
# the certified source manifests, the third-party authority and the launch
# material are all reproduced from the reviewed ``PAD4-R2`` owners rather than
# forked.  ``POSTP1-002V2A-PAD4-R2`` reproduced each of them as valid, and this
# correction is local to the controller admission surface.

WORKER_SOURCE_MANIFEST_VERSION = r2.WORKER_SOURCE_MANIFEST_VERSION
WORKER_ENTRYPOINT_MODULE = r2.WORKER_ENTRYPOINT_MODULE
WORKER_ENTRYPOINT_RELATIVE_PATH = r2.WORKER_ENTRYPOINT_RELATIVE_PATH
WORKER_PROTOCOL_MODULE = r2.WORKER_PROTOCOL_MODULE
WORKER_PROTOCOL_RELATIVE_PATH = r2.WORKER_PROTOCOL_RELATIVE_PATH
WORKER_PACKAGE_MODULE = r2.WORKER_PACKAGE_MODULE
WORKER_PACKAGE_RELATIVE_PATH = r2.WORKER_PACKAGE_RELATIVE_PATH
CERTIFIED_PACKAGE_ROOTS = r2.CERTIFIED_PACKAGE_ROOTS
REQUIRED_WORKER_PROJECT_MODULES = r2.REQUIRED_WORKER_PROJECT_MODULES

PRE_I2_FIXTURE_SEED_MODULE = r2.PRE_I2_FIXTURE_SEED_MODULE
PRE_I2_FIXTURE_VERSION = r2.PRE_I2_FIXTURE_VERSION
PRE_I2_FIXTURE_ROLE = r2.PRE_I2_FIXTURE_ROLE
PRE_I2_FIXTURE_MODULE_COUNT = r2.PRE_I2_FIXTURE_MODULE_COUNT
PRE_I2_FIXTURE_MANIFEST_DIGEST = r2.PRE_I2_FIXTURE_MANIFEST_DIGEST

BOOTSTRAP_SOURCE_SET_VERSION = r2.BOOTSTRAP_SOURCE_SET_VERSION
BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE = (
    r2.BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING_RULE
)
BOOTSTRAP_PRE_VERIFICATION_VERSION = r2.BOOTSTRAP_PRE_VERIFICATION_VERSION
BOOTSTRAP_PRE_VERIFICATION_CHECKS = r2.BOOTSTRAP_PRE_VERIFICATION_CHECKS
WORKER_BOOTSTRAP_SOURCE_SET = r2.WORKER_BOOTSTRAP_SOURCE_SET
WORKER_BOOTSTRAP_RELATIVE_PATHS = r2.WORKER_BOOTSTRAP_RELATIVE_PATHS
WORKER_BOOTSTRAP_MODULES = r2.WORKER_BOOTSTRAP_MODULES
BOOTSTRAP_EXECUTION_ORDER = r2.BOOTSTRAP_EXECUTION_ORDER
BOOTSTRAP_PACKAGE_ROOT = r2.BOOTSTRAP_PACKAGE_ROOT
BOOTSTRAP_GUARDED_SCOPE = r2.BOOTSTRAP_GUARDED_SCOPE

derive_bootstrap_source_set = r2.derive_bootstrap_source_set
derive_project_source_manifest = r2.derive_project_source_manifest
external_import_roots = r2.external_import_roots
audit_bootstrap_execution_order = r2.audit_bootstrap_execution_order
audit_bootstrap_source_set = r2.audit_bootstrap_source_set
audit_authoritative_worker_source = r2.audit_authoritative_worker_source
certified_universe_closed_worker_rule_modules = (
    r2.certified_universe_closed_worker_rule_modules
)
module_level_declared_imports = r2.module_level_declared_imports
deferred_declared_imports = r2.deferred_declared_imports

FROZEN_PRE_I2_SOURCE_ROWS = r2.FROZEN_PRE_I2_SOURCE_ROWS
FROZEN_WORKER_PACKAGE_ROWS = r2.FROZEN_WORKER_PACKAGE_ROWS
CANDIDATE_SOURCE_MODULE_COUNT = r2.CANDIDATE_SOURCE_MODULE_COUNT
frozen_pre_i2_source_manifest = r2.frozen_pre_i2_source_manifest
frozen_candidate_source_manifest = r2.frozen_candidate_source_manifest
frozen_bootstrap_source_manifest = r2.frozen_bootstrap_source_manifest
verify_frozen_pre_i2_fixture = r2.verify_frozen_pre_i2_fixture
verify_frozen_bootstrap_set_is_complete = r2.verify_frozen_bootstrap_set_is_complete
verify_worker_protocol_binds_the_frozen_interpreter = (
    r2.verify_worker_protocol_binds_the_frozen_interpreter
)

THIRD_PARTY_REGISTRY_VERSION = r2.THIRD_PARTY_REGISTRY_VERSION
FROZEN_THIRD_PARTY_AUTHORITY_ROWS = r2.FROZEN_THIRD_PARTY_AUTHORITY_ROWS
frozen_third_party_authority = r2.frozen_third_party_authority
derive_third_party_authority = r2.derive_third_party_authority
observe_installed_distributions = r2.observe_installed_distributions

WORKER_LAUNCH_CONTRACT = "ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_V1_R3"
WORKER_LAUNCH_FLAGS = r2.WORKER_LAUNCH_FLAGS
WORKER_LAUNCH_X_OPTION = r2.WORKER_LAUNCH_X_OPTION
EXEC_LAUNCH = r2.EXEC_LAUNCH
FORK_WITHOUT_EXEC = r2.FORK_WITHOUT_EXEC
FORK_SERVER_REUSE = r2.FORK_SERVER_REUSE
AUTHORIZED_LAUNCH_MECHANISMS = r2.AUTHORIZED_LAUNCH_MECHANISMS
UNAUTHORIZED_LAUNCH_MECHANISMS = r2.UNAUTHORIZED_LAUNCH_MECHANISMS
FROZEN_WORKER_ENVIRONMENT = r2.FROZEN_WORKER_ENVIRONMENT

authorize_worker_launch_mechanism = r2.authorize_worker_launch_mechanism
controller_pycache_root = r2.controller_pycache_root
create_fresh_pycache_namespace = r2.create_fresh_pycache_namespace
allocate_worker_pycache_namespace = r2.allocate_worker_pycache_namespace
interpreter_base_sys_path = r2.interpreter_base_sys_path
parent_site_paths = r2.parent_site_paths

WorkerLaunch = r2.WorkerLaunch
worker_launch = r2.worker_launch

compiled_root_binding_witness = r2.compiled_root_binding_witness
direct_dependency_body_findings = r2.direct_dependency_body_findings
verify_current_production_expected_result = r2.verify_current_production_expected_result


# ---------------------------------------------------------------------------
# Repair C — the trusted controller authority context, R3 identity
# ---------------------------------------------------------------------------

AUTHORITY_CONTEXT_VERSION = "ETF_CALENDAR_SCIENTIFIC_WORKER_AUTHORITY_CONTEXT_V1_R3"
AUTHORITY_CONSTRUCTION_REFREEZE = r2.AUTHORITY_CONSTRUCTION_REFREEZE
FINAL_CALENDAR_AUTHORITY = r2.FINAL_CALENDAR_AUTHORITY
REVIEW_CANDIDATE_CONTEXT = r2.REVIEW_CANDIDATE_CONTEXT
AUTHORITY_CONTEXT_ORIGINS = r2.AUTHORITY_CONTEXT_ORIGINS
FINAL_CALENDAR_AUTHORITY_WORKER_FIELD = r2.FINAL_CALENDAR_AUTHORITY_WORKER_FIELD
PRODUCTION_CONTEXT_NOT_YET_BOUND = r2.PRODUCTION_CONTEXT_NOT_YET_BOUND

#: The worker protocol is reused byte-identically from ``PAD4-R2``, so the
#: *worker protocol* authority ticket carried in the request and echoed in the
#: response stays ``POSTP1-001V2A-PAD4-R2``.  That field identifies the frozen
#: worker protocol, not the proof architecture; the proof architecture is
#: identified by ``proof_architecture_sha256`` — this candidate's own parent
#: hash — and by ``PROGRAM_TICKET``.
WORKER_PROTOCOL_AUTHORITY_TICKET = protocol.WORKER_AUTHORITY_TICKET


@dataclass(frozen=True)
class ScientificWorkerAuthorityContext(r2.ScientificWorkerAuthorityContext):
    """The trusted expected values launch, request and admission all use.

    ``POSTP1-002V2A-PAD4-R2`` reproduced the ``PAD4-R2`` context as **valid**,
    so its fields, canonicalisation and three-way agreement are inherited
    unchanged rather than restated.  What this subclass adds is *type
    identity*: the closed authoritative operation accepts only an ``R3``
    trusted context, so a superseded failed-lineage context cannot be carried
    into this architecture's authority.

    The context still cannot be constructed by a request, by a response, by
    live disk or by the installed environment, and the worker protocol ticket
    it binds must be the frozen reused ``PAD4-R2`` protocol ticket.
    """

    def __post_init__(self) -> None:
        super().__post_init__()
        if self.proof_architecture_ticket != WORKER_PROTOCOL_AUTHORITY_TICKET:
            raise IsolatedScientificWorkerR3Error(
                "authority context does not bind the frozen reused worker "
                f"protocol ticket {WORKER_PROTOCOL_AUTHORITY_TICKET!r}"
            )

    def as_evidence(self) -> dict[str, Any]:
        """Deterministic, address-free identity of the trusted context."""

        payload = super().as_evidence()
        payload["authority_context_version"] = AUTHORITY_CONTEXT_VERSION
        payload["proof_architecture_program_ticket"] = PROGRAM_TICKET
        payload["worker_protocol_authority_ticket"] = WORKER_PROTOCOL_AUTHORITY_TICKET
        return payload


def _as_r3_context(
    context: r2.ScientificWorkerAuthorityContext,
) -> ScientificWorkerAuthorityContext:
    """Rebind a reviewed ``PAD4-R2`` context builder result to the R3 type."""

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

    return _as_r3_context(
        r2.candidate_review_authority_context(proof_architecture_sha256, origin=origin)
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
    it is explicitly not a runtime operation.  Runtime consumes an
    already-frozen context.
    """

    return _as_r3_context(
        r2.derive_authority_context_from_reviewed_source(
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

    return _as_r3_context(
        r2.production_authority_context_from_calendar_authority(calendar_authority)
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

    Building a request is *not* an authority-bearing operation: a request is
    only ever an input to the closed authoritative execution, it can never be
    admitted by itself, and it can never produce evidence.  The reviewed
    ``PAD4-R2`` builder is reused unchanged, with the R3 trusted-context type
    required.
    """

    require_trusted_authority_context(authority_context)
    return r2.build_scientific_request(
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
    """Only an ``R3`` trusted controller context may reach this architecture."""

    if not isinstance(authority_context, ScientificWorkerAuthorityContext):
        raise IsolatedScientificWorkerR3Error(
            "the authority-closed scientific architecture requires an R3 trusted "
            f"controller authority context, not {type(authority_context).__name__}"
        )
    return authority_context


def preverify_worker_bootstrap_sources(
    authority_context: ScientificWorkerAuthorityContext,
    launch: WorkerLaunch,
) -> dict[str, Any]:
    """Bind every bootstrap source before any of it can execute.

    The reviewed ``PAD4-R2`` implementation is reused unchanged: the review
    reproduced it as valid on the authoritative path, with all four bootstrap
    members refusing before spawn, zero subprocesses, zero pycache allocations
    and markers absent.

    The mapping this returns is **diagnostic, not authority**.  Its presence,
    shape or contents can never make an outcome admissible, because R3 never
    reads a pre-verification mapping to decide admission: it decides on whether
    the closed controller operation itself performed the pre-verification.
    """

    require_trusted_authority_context(authority_context)
    return r2.preverify_worker_bootstrap_sources(authority_context, launch)


# ---------------------------------------------------------------------------
# The correction — the closed authoritative scientific execution boundary
# ---------------------------------------------------------------------------

AUTHORITATIVE_EXECUTION_BOUNDARY_VERSION = (
    "ETF_CALENDAR_AUTHORITATIVE_SCIENTIFIC_EXECUTION_BOUNDARY_V1_R3"
)

#: The one affirmative authority marker.  It is constructed at exactly one
#: site, inside the closed controller operation, and the mechanical API-closure
#: audit proves that no other project-owned module and no other call site in
#: this module can produce it.  Superseded failed-lineage evidence builders
#: cannot emit it, so an admitted ``PAD4-R2`` evidence payload can never be
#: mistaken for affirmative ``R3`` scientific authority.
AUTHORITATIVE_SCIENTIFIC_AUTHORITY = "AUTHORITATIVE_CLOSED_CONTROLLER_EXECUTION_V1_R3"

#: The stamp every non-authoritative execution must carry instead.
NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY = "NON_AUTHORITATIVE_RAW_EXECUTION"

#: The closed controller order, exactly as ``run_isolated_scientific_request``
#: performs it.  Nothing may enter at step 6, 7, 8 or 9.
AUTHORITATIVE_EXECUTION_ORDER: tuple[str, ...] = (
    "1_RECEIVE_THE_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT",
    "2_VALIDATE_THE_REQUEST_AGAINST_THE_TRUSTED_AUTHORITY",
    "3_PREVERIFY_THE_COMPLETE_BOOTSTRAP_SOURCE_SET",
    "4_ALLOCATE_THE_FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE",
    "5_SPAWN_THE_EXACT_WORKER",
    "6_OBTAIN_THE_EXACT_WORKER_EXECUTION_RESULT",
    "7_VALIDATE_THE_RESPONSE_INSIDE_THE_SAME_CLOSED_FLOW",
    "8_PERFORM_SCIENTIFIC_ADMISSION_INSIDE_THAT_FLOW",
    "9_CONSTRUCT_AFFIRMATIVE_SCIENTIFIC_EVIDENCE_INSIDE_THAT_FLOW",
    "10_RETURN_THE_FINAL_ADMITTED_RESULT_AND_EVIDENCE",
)

#: The material an ``AuthoritativeScientificExecution`` exposes.  Every one of
#: these is produced by the closed flow and by nothing else.
AUTHORITATIVE_EXECUTION_MATERIAL: tuple[str, ...] = (
    "admitted",
    "failure_reason",
    "request_digest",
    "response",
    "result",
    "scientific_evidence",
)


def _build_authoritative_scientific_execution_boundary() -> tuple[type, Callable[..., Any]]:
    """Create the closed authority boundary and the one operation that owns it.

    Everything authority-bearing is captured in this factory's closure:

    * ``_capability`` is a bare object bound to no module global, no class
      attribute and no returned value, so it cannot be named by a caller;
    * ``_material`` is a closure-private ``WeakKeyDictionary`` that only the
      closed operation writes, so an instance obtained by ``__new__`` bypass,
      by subclassing or by ``copy`` has no material and refuses every accessor;
    * ``_execute_exact_worker``, ``_validate_and_admit`` and
      ``_affirmative_scientific_evidence`` are closure-local, so there is no
      module-accessible spawn primitive, no module-accessible admission
      function and no module-accessible affirmative-evidence constructor.

    This is capability ownership, not naming: a leading underscore is
    explicitly *not* the boundary, no field value is the boundary, no dataclass
    identity is the boundary, and no secret or signature is involved.
    """

    _capability = object()
    _material: "WeakKeyDictionary[Any, Mapping[str, Any]]" = WeakKeyDictionary()

    class AuthoritativeScientificExecution:
        """One complete authoritative scientific execution and its evidence.

        An instance is obtainable only as the return value of
        ``run_isolated_scientific_request``.  Direct construction refuses, and
        an instance manufactured around ``__init__`` carries no material, so
        every accessor refuses rather than returning a fabricated answer.
        """

        __slots__ = ("__weakref__",)

        def __init__(self, capability: Any = None, material: Any = None) -> None:
            if capability is not _capability:
                raise AuthoritativeExecutionConstructionError(
                    "an authoritative scientific execution is produced only by "
                    "run_isolated_scientific_request; it cannot be constructed"
                )
            _material[self] = dict(material)

        def _owned(self) -> Mapping[str, Any]:
            try:
                return _material[self]
            except KeyError:
                raise AuthoritativeExecutionConstructionError(
                    "this object carries no controller-owned scientific "
                    "material and is not an authoritative scientific execution"
                ) from None

        @property
        def admitted(self) -> bool:
            return self._owned()["admitted"]

        @property
        def failure_reason(self) -> str | None:
            return self._owned()["failure_reason"]

        @property
        def result(self) -> Any:
            return self._owned()["result"]

        @property
        def response(self) -> Mapping[str, Any] | None:
            return self._owned()["response"]

        @property
        def request_digest(self) -> str:
            return self._owned()["request_digest"]

        @property
        def scientific_evidence(self) -> dict[str, Any]:
            """The evidence this execution produced, as a fresh copy."""

            return json.loads(json.dumps(self._owned()["scientific_evidence"]))

        def __repr__(self) -> str:  # pragma: no cover - diagnostic only
            try:
                owned = self._owned()
            except AuthoritativeExecutionConstructionError:
                return "<AuthoritativeScientificExecution UNOWNED>"
            return (
                "<AuthoritativeScientificExecution "
                f"admitted={owned['admitted']!r} "
                f"failure_reason={owned['failure_reason']!r}>"
            )

    def _execute_exact_worker(
        request: Mapping[str, Any],
        launch: WorkerLaunch,
        pycache_namespace: Path | None,
    ) -> dict[str, Any]:
        """Steps 4-6.  Closure-local: there is no module-accessible spawn."""

        authorize_worker_launch_mechanism(launch.mechanism)
        payload = protocol.canonical_json_bytes(request)
        if len(payload) > protocol.MAX_REQUEST_BYTES:
            raise IsolatedScientificWorkerR3Error(
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
        """Steps 7-8.  Closure-local: there is no generic admission function.

        This is the reviewed ``PAD4-R2`` admission logic, folded inside the
        closed flow rather than exposed as a separately callable
        authority-escalation operation.  It is unreachable with a caller-built
        outcome because it is unreachable at all from outside this closure.
        """

        def refuse(
            reason: str, response: Mapping[str, Any] | None = None
        ) -> dict[str, Any]:
            return {"admitted": False, "failure_reason": reason, "response": response,
                    "result": None}

        def worker_refusal_payload() -> Mapping[str, Any] | None:
            """The worker's own refusal, reported but never trusted.

            A non-zero exit refuses before anything is parsed.  Parsing the
            payload afterwards is diagnostic only: it changes no verdict, it
            can only ever be attached to a refusal, and a payload that is not a
            well-formed canonical REFUSED response is simply dropped.  Without
            this the closed flow would be *less* informative than the surface
            it replaces, because the worker's reason would be unreachable.
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
        return {
            "admitted": True,
            "failure_reason": None,
            "response": parsed,
            "result": parsed["result"],
        }

    def _affirmative_scientific_evidence(
        authority_context: ScientificWorkerAuthorityContext,
        execution: Mapping[str, Any],
        admission: Mapping[str, Any],
        pre_verification: Mapping[str, Any],
    ) -> dict[str, Any]:
        """Step 9.  The only site that can stamp affirmative R3 authority.

        The bootstrap pre-execution binding reported here is the mapping this
        very flow produced at step 3, in this very call, before the process
        existed.  It is never a caller-supplied mapping, because no caller can
        reach this function at all.
        """

        response = admission["response"] or {}
        evidence = {
            "scientific_authority": AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
            "authoritative_execution_boundary": (
                AUTHORITATIVE_EXECUTION_BOUNDARY_VERSION
            ),
            "proof_architecture_program_ticket": PROGRAM_TICKET,
            "authoritative_execution_is_closed_end_to_end": True,
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
        exact result, validate the response, admit, construct affirmative
        evidence and return — as one closed operation.  A caller never composes
        spawn, then admit, then evidence, because there is nothing to compose:
        no step is separately callable.

        A bootstrap mismatch raises before the cache namespace is allocated and
        before ``subprocess.run`` is reached, so no drifted bootstrap source can
        execute, write a marker or emit a fabricated response.
        """

        context = require_trusted_authority_context(trusted_authority_context)
        if not isinstance(launch_material, WorkerLaunch):
            raise IsolatedScientificWorkerR3Error(
                "the authoritative scientific execution requires parent-bound "
                f"launch material, not {type(launch_material).__name__}"
            )
        if not isinstance(scientific_request, Mapping):
            raise IsolatedScientificWorkerR3Error(
                "the authoritative scientific execution requires a canonical "
                f"scientific request mapping, not {type(scientific_request).__name__}"
            )

        drifted = verify_request_against_authority_context(context, scientific_request)
        if drifted:
            raise IsolatedScientificWorkerR3Error(
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
        return AuthoritativeScientificExecution(
            _capability,
            {
                "admitted": admission["admitted"],
                "failure_reason": admission["failure_reason"],
                "response": admission["response"],
                "result": admission["result"],
                "request_digest": execution["request_digest"],
                "scientific_evidence": evidence,
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


def verify_request_against_authority_context(
    authority_context: ScientificWorkerAuthorityContext,
    request: Mapping[str, Any],
) -> tuple[str, ...]:
    """Every material authority field of the request must be the trusted one.

    This is a pure comparison.  It returns the drifted field names and it is
    never, by itself, an admission: it cannot admit, it cannot create an
    outcome and it cannot produce evidence.
    """

    return r2.verify_request_against_authority_context(authority_context, request)


def verify_response_against_authority_context(
    authority_context: ScientificWorkerAuthorityContext,
    response: Mapping[str, Any],
) -> tuple[str, ...]:
    """Every material authority field of the response must be the trusted one.

    A pure comparison, exactly as above: it admits nothing and evidences
    nothing.
    """

    return r2.verify_response_against_authority_context(authority_context, response)


# ---------------------------------------------------------------------------
# Mechanical API-closure and direct-launch census
# ---------------------------------------------------------------------------

API_CLOSURE_AUDIT_VERSION = "ETF_CALENDAR_SCIENTIFIC_API_CLOSURE_AUDIT_V1_R3"

#: The one authority-bearing production operation.
AUTHORITATIVE_PRODUCTION_OPERATION = "run_isolated_scientific_request"

#: The closure that owns every authority-bearing step.
AUTHORITY_OWNING_FACTORY = "_build_authoritative_scientific_execution_boundary"

#: The declared, audited, non-constructing readers of the affirmative
#: authority marker.  A reader compares the marker; it never places it into an
#: evidence payload.  Any marker site outside the one construction scope and
#: these declared readers is a finding.
AUTHORITY_MARKER_DECLARED_READERS: tuple[str, ...] = (
    "audit_scientific_api_closure",
    "scientific_evidence_authority_rule",
)

#: The closure-local steps.  None of them is module-accessible, so none of them
#: can be composed by a caller with a caller-built value.
AUTHORITY_OWNED_STEPS: tuple[str, ...] = (
    "_affirmative_scientific_evidence",
    "_execute_exact_worker",
    "_validate_and_admit",
    AUTHORITATIVE_PRODUCTION_OPERATION,
)

#: The ``PAD4-R2`` names whose existence as separately callable production
#: operations *was* the reviewed defect.  R3 must not define them, must not
#: re-export them and must not bind any module attribute to them.
FORBIDDEN_PRODUCTION_AUTHORITY_NAMES: tuple[str, ...] = (
    "AdmissionOutcome",
    "WorkerProcessOutcome",
    "_spawn_unverified_worker_process",
    "admit_worker_result",
    "run_scientific_worker",
    "scientific_response_evidence",
)

#: The one process-creation site that is reachable from R3 production code
#: but is deliberately **not** a scientific worker launch.  Declaring it is the
#: honest alternative to hiding it behind a file-level classification: the
#: reviewed ``PAD4-R1`` helper runs the frozen interpreter with a fixed ``-c``
#: program to read its own base ``sys.path``.  It passes no scientific request,
#: it cannot emit a scientific response, its output is consumed only as launch
#: material, and that material is then bound into the request and cross-checked
#: by the worker's ``sys_path_digest``.
DECLARED_NON_WORKER_LAUNCH_SITES: tuple[str, ...] = ("interpreter_base_sys_path",)

#: Every process-creation primitive the census recognises.
LAUNCH_PRIMITIVES: tuple[str, ...] = (
    "multiprocessing.Process",
    "os.execl",
    "os.execle",
    "os.execlp",
    "os.execlpe",
    "os.execv",
    "os.execve",
    "os.execvp",
    "os.execvpe",
    "os.posix_spawn",
    "os.posix_spawnp",
    "os.spawnl",
    "os.spawnle",
    "os.spawnlp",
    "os.spawnlpe",
    "os.spawnv",
    "os.spawnve",
    "os.spawnvp",
    "os.spawnvpe",
    "subprocess.Popen",
    "subprocess.call",
    "subprocess.check_call",
    "subprocess.check_output",
    "subprocess.run",
)


def _dotted_call_name(node: ast.AST) -> str | None:
    """The dotted name a call targets, for attribute and plain-name calls."""

    parts: list[str] = []
    current = node
    while isinstance(current, ast.Attribute):
        parts.append(current.attr)
        current = current.value
    if isinstance(current, ast.Name):
        parts.append(current.id)
    else:
        return None
    return ".".join(reversed(parts))


def _scope_index(tree: ast.AST) -> dict[ast.AST, tuple[str, ...]]:
    """Map every node to the chain of function/class scopes that contain it."""

    scopes: dict[ast.AST, tuple[str, ...]] = {}

    def walk(node: ast.AST, chain: tuple[str, ...]) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(
                child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
            ):
                inner = (*chain, child.name)
            else:
                inner = chain
            scopes[child] = inner
            walk(child, inner)

    scopes[tree] = ()
    walk(tree, ())
    return scopes


def _module_source(relative: str, project_root: Path = PROJECT_ROOT) -> str:
    target = Path(project_root) / relative
    if not target.is_file():
        raise IsolatedScientificWorkerR3Error(
            f"the API closure audit cannot read {relative}"
        )
    return target.read_text(encoding="utf-8")


def audit_scientific_api_closure(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Prove mechanically that exactly one production flow bears authority.

    The audit is deterministic and structural.  It reports names, call sites
    and counts — never a source hash of this module, so no self-hash fixed
    point is attempted and an ordinary comment edit cannot move the parent.

    It establishes, over this module's own AST:

    1. every process-creation primitive in the production controller sits
       inside the authority-owning closure, in one closure-local step;
    2. ``AuthoritativeScientificExecution`` is constructed at exactly one site,
       inside the one authority-bearing operation;
    3. the affirmative authority marker is referenced at exactly one site,
       inside the closure-local affirmative-evidence constructor;
    4. none of the reviewed ``PAD4-R2`` authority-escalation names is defined,
       assigned or re-exported; and
    5. the failed-lineage controllers and the raw review harness cannot emit
       the affirmative marker at all.
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
            if dotted == "AuthoritativeScientificExecution":
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

    defined_forbidden = sorted(module_names & set(FORBIDDEN_PRODUCTION_AUTHORITY_NAMES))
    reexported_forbidden = sorted(
        name
        for name in FORBIDDEN_PRODUCTION_AUTHORITY_NAMES
        if getattr(sys.modules[__name__], name, None) is not None
        and getattr(sys.modules[__name__], name, None)
        is getattr(r2, name, object())
    )
    bound_to_lineage = sorted(
        name
        for name in dir(sys.modules[__name__])
        if any(
            getattr(sys.modules[__name__], name, None)
            is getattr(module, forbidden, object())
            for module in (pad4, r1, r2)
            for forbidden in FORBIDDEN_PRODUCTION_AUTHORITY_NAMES
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
        marker_free_modules[relative] = (
            AUTHORITATIVE_SCIENTIFIC_AUTHORITY not in other
        )

    findings: list[str] = []
    expected_launch_scope = [AUTHORITY_OWNING_FACTORY, "_execute_exact_worker"]
    if len(launch_sites) != 1 or launch_sites[0]["scope"] != expected_launch_scope:
        findings.append("PRODUCTION_LAUNCH_PRIMITIVE_IS_NOT_UNIQUELY_CLOSURE_OWNED")
    expected_authority_scope = [
        AUTHORITY_OWNING_FACTORY,
        AUTHORITATIVE_PRODUCTION_OPERATION,
    ]
    if (
        len(construction_sites) != 1
        or construction_sites[0]["scope"] != expected_authority_scope
    ):
        findings.append("AUTHORITATIVE_EXECUTION_IS_CONSTRUCTED_OUTSIDE_THE_ONE_FLOW")
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
        and list(site["scope"]) not in [
            [reader] for reader in AUTHORITY_MARKER_DECLARED_READERS
        ]
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
        findings.append(f"AFFIRMATIVE_MARKER_REACHABLE_OUTSIDE_THE_CONTROLLER:{unmarked!r}")

    return {
        "audit_version": API_CLOSURE_AUDIT_VERSION,
        "authoritative_production_operation": AUTHORITATIVE_PRODUCTION_OPERATION,
        "authority_owning_factory": AUTHORITY_OWNING_FACTORY,
        "authority_owned_steps": list(AUTHORITY_OWNED_STEPS),
        "module_accessible_authority_bearing_operations": 1,
        "production_launch_sites": launch_sites,
        "authoritative_execution_construction_sites": construction_sites,
        "affirmative_marker_construction_sites": marker_construction_sites,
        "affirmative_marker_declared_readers": list(
            AUTHORITY_MARKER_DECLARED_READERS
        ),
        "affirmative_marker_undeclared_sites": undeclared_marker_sites,
        "authority_owning_factory_is_module_accessible": factory_is_module_accessible,
        "forbidden_authority_names": list(FORBIDDEN_PRODUCTION_AUTHORITY_NAMES),
        "forbidden_authority_names_defined": defined_forbidden,
        "forbidden_authority_names_reexported": reexported_forbidden,
        "module_attributes_bound_to_failed_lineage": bound_to_lineage,
        "affirmative_marker_free_modules": dict(sorted(marker_free_modules.items())),
        "findings": findings,
        "closed": not findings,
    }


def _production_reachable_launch_sites() -> list[dict[str, Any]]:
    """Inherited helpers this module re-exports that themselves create a process.

    A file-level classification would hide these: the helper's *source* lives in
    a superseded module, but R3 production code calls it, so the census must
    name it.  Every one found must be a declared non-worker launch site.
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
                        "attribute": name,
                        "callable": value.__name__,
                        "defining_module": value.__module__.rsplit(".", 1)[-1],
                        "primitive": _dotted_call_name(node.func),
                    }
                )
    deduplicated: list[dict[str, Any]] = []
    for site in found:
        if site not in deduplicated:
            deduplicated.append(site)
    return sorted(deduplicated, key=lambda site: (site["attribute"], site["primitive"]))


def audit_direct_worker_launch_census(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """Enumerate every project-owned process-creation site that matters.

    The census covers the certified project source universe, the production
    controller, the superseded failed-lineage controllers and the deliberately
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
        surveyed[relative] = "SUPERSEDED_FAILED_LINEAGE_NOT_R3_AUTHORITY"
    for entry in frozen_candidate_source_manifest():
        surveyed.setdefault(entry.path, "CERTIFIED_WORKER_SOURCE_UNIVERSE")

    sites: list[dict[str, Any]] = []
    for relative, classification in sorted(surveyed.items()):
        target = Path(project_root) / relative
        if not target.is_file():
            raise IsolatedScientificWorkerR3Error(
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
        "audit_version": "ETF_CALENDAR_DIRECT_WORKER_LAUNCH_CENSUS_V1_R3",
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
# Material children — preserved verbatim from the reviewed PAD4-R2 originals
# ---------------------------------------------------------------------------
#
# ``POSTP1-002V2A-PAD4-R2`` independently reproduced each of these as valid.
# They are bound here as the *exact* reviewed payloads, so a reviewer can
# confirm byte-identical carry-forward by comparing child hashes with the
# ``PAD4-R2`` namespace instead of re-reading a restatement.

bootstrap_pre_execution_source_binding_rule = (
    r2.bootstrap_pre_execution_source_binding_rule
)
bootstrap_source_set = r2.bootstrap_source_set
proof_interpreter_identity = r2.proof_interpreter_identity
bytecode_execution_binding_rule = r2.bytecode_execution_binding_rule
project_source_manifest_binding_rule = r2.project_source_manifest_binding_rule
pre_i2_project_source_manifest_fixture = r2.pre_i2_project_source_manifest_fixture
third_party_semantic_authority = r2.third_party_semantic_authority
third_party_installed_content_attestation_rule = (
    r2.third_party_installed_content_attestation_rule
)
dynamic_import_and_execution_prohibition = r2.dynamic_import_and_execution_prohibition
scientific_request_protocol = r2.scientific_request_protocol
scientific_response_protocol = r2.scientific_response_protocol
worker_io_and_capability_boundary = r2.worker_io_and_capability_boundary
compiled_root_binding_witness_rule = r2.compiled_root_binding_witness_rule
store_root_and_direct_use_grammar = r2.store_root_and_direct_use_grammar
replay_owner_graph_rule = r2.replay_owner_graph_rule
direct_body_dependency_rule = r2.direct_body_dependency_rule

#: The children carried forward byte-identically, named so the reviewer can
#: check the claim mechanically rather than trust it.
VERBATIM_PAD4_R2_CHILDREN: tuple[str, ...] = (
    "bootstrap_pre_execution_source_binding_rule",
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


# ---------------------------------------------------------------------------
# Material children — the R3 correction
# ---------------------------------------------------------------------------


def authoritative_scientific_execution_boundary() -> dict[str, Any]:
    """The correction — one closed operation owns every authority-bearing step."""

    closure = audit_scientific_api_closure()
    census = audit_direct_worker_launch_census()
    if not closure["closed"]:
        raise IsolatedScientificWorkerR3Error(
            f"the scientific API closure audit refuses: {closure['findings']!r}"
        )
    if not census["closed"]:
        raise IsolatedScientificWorkerR3Error(
            f"the direct worker launch census refuses: {census['findings']!r}"
        )
    return _definition(
        {
            "contract_version": AUTHORITATIVE_EXECUTION_BOUNDARY_VERSION,
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[0],
            "reviewed_parent": FAILED_PAD4_R2_SHA256,
            "review": FAILED_PAD4_R2_REVIEW,
            "review_result": FAILED_PAD4_R2_REVIEW_RESULT,
            "defect": (
                "scientific admission neither required nor authenticated the "
                "trusted-controller bootstrap pre-verification its evidence "
                "claimed occurred; the generic composition of a public "
                "constructible outcome, a generic admission function and a "
                "generic evidence function let a project-owned caller mint "
                "admitted fabricated scientific results"
            ),
            "rule": (
                "NO OUTCOME CREATED WITHOUT SUCCESSFUL TRUSTED-CONTROLLER "
                "BOOTSTRAP PREVERIFICATION MAY ENTER SCIENTIFIC ADMISSION OR "
                "PRODUCE AFFIRMATIVE SCIENTIFIC AUTHORITY EVIDENCE"
            ),
            "closed_authority_path": (
                "TRUSTED_BOOTSTRAP_PREVERIFICATION_THEN_EXACT_WORKER_LAUNCH_THEN_"
                "EXACT_WORKER_OUTCOME_THEN_SCIENTIFIC_ADMISSION"
            ),
            "authoritative_production_operation": AUTHORITATIVE_PRODUCTION_OPERATION,
            "authoritative_execution_order": list(AUTHORITATIVE_EXECUTION_ORDER),
            "authoritative_execution_material": list(AUTHORITATIVE_EXECUTION_MATERIAL),
            "authority_mechanism": "CLOSED_CONTROL_FLOW_AND_CAPABILITY_OWNERSHIP",
            "authority_owning_factory": AUTHORITY_OWNING_FACTORY,
            "authority_owned_steps": list(AUTHORITY_OWNED_STEPS),
            "closed_reviewed_bypasses": list(CLOSED_REVIEWED_BYPASSES),
            "generic_admission_function_exists": False,
            "generic_evidence_function_exists": False,
            "generic_raw_outcome_type_exists_in_production": False,
            "raw_unverified_spawn_in_production_authority_surface": False,
            "raw_unverified_spawn_location": RAW_REVIEW_HARNESS_RELATIVE_PATH,
            "leading_underscore_is_authority_boundary": False,
            "isinstance_of_a_public_dataclass_is_authority": False,
            "field_values_are_authority": False,
            "class_naming_is_authority": False,
            "caller_may_construct_the_authoritative_execution": False,
            "construction_bypass_yields_unowned_object_that_refuses": True,
            "cryptographic_ceremony_introduced": False,
            "worker_visible_secret_introduced": False,
            "worker_computable_mac_key_introduced": False,
            "api_closure_audit": closure,
            "direct_worker_launch_census": census,
        }
    )


def admission_provenance_rule() -> dict[str, Any]:
    """Where admission provenance comes from, and where it cannot come from."""

    return _definition(
        {
            "contract_version": "ETF_CALENDAR_ADMISSION_PROVENANCE_RULE_V1_R3",
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[1],
            "provenance_root": (
                "BEING_THE_CLOSED_AUTHORITATIVE_CONTROLLER_EXECUTION_ITSELF"
            ),
            "provenance_is_a_value": False,
            "provenance_is_a_field": False,
            "provenance_is_a_mapping": False,
            "provenance_is_a_type_hint": False,
            "provenance_is_a_secret": False,
            "provenance_is_a_signature": False,
            "bootstrap_preverification_required_before_spawn": True,
            "bootstrap_preverification_mapping_is_diagnostic_not_authority": True,
            "caller_fabricated_preverification_mapping_is_authority": False,
            "caller_constructed_outcome_is_authority": False,
            "caller_constructed_admission_state_is_authority": False,
            "worker_can_mint_controller_admission_provenance": False,
            "worker_copied_request_authority_is_sufficient_for_admission": False,
            "unverified_worker_outcome_scientifically_admissible": False,
            "generic_raw_outcome_to_scientific_admission_supported": False,
            "scientific_admission_requires_same_authoritative_controller_execution": (
                True
            ),
            "admission_is_reachable_without_the_closed_flow": False,
            "why_the_worker_cannot_mint_it": (
                "the controller-side condition is not data the worker could "
                "compute, copy or observe; it is the fact that the closed "
                "controller operation pre-verified the bootstrap source and "
                "then created this very process, which no request, response, "
                "environment or worker can be"
            ),
            "validated_inside_the_closed_flow": [
                "bootstrap_defence_in_depth_verification",
                "bootstrap_pre_execution_source_binding_performed_by_this_execution",
                "bytecode_cache_binding",
                "clean_process_termination",
                "interpreter_identity",
                "operation_identity",
                "request_authority_context_agreement",
                "request_digest_cross_binding",
                "response_authority_context_agreement",
                "response_schema_version",
                "result_digest",
                "success_status",
                "third_party_installed_content_verification",
                "worker_authority_identity",
                "worker_bootstrap_manifest_identity",
                "worker_source_manifest_identity",
            ],
        }
    )


def scientific_evidence_authority_rule() -> dict[str, Any]:
    """Only the closed flow may state that a scientific execution is authority."""

    return _definition(
        {
            "contract_version": "ETF_CALENDAR_SCIENTIFIC_EVIDENCE_AUTHORITY_RULE_V1_R3",
            "affirmative_authority_marker": AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
            "non_authoritative_marker": NON_AUTHORITATIVE_SCIENTIFIC_AUTHORITY,
            "affirmative_scientific_evidence_created_only_inside_authoritative_path": (
                True
            ),
            "affirmative_evidence_creation_location": (
                f"{AUTHORITY_OWNING_FACTORY}._affirmative_scientific_evidence"
            ),
            "affirmative_evidence_construction_sites": 1,
            "module_accessible_evidence_constructor_exists": False,
            "caller_built_admission_state_can_mint_evidence": False,
            "raw_execution_may_produce_diagnostic_evidence": True,
            "raw_diagnostic_is_unambiguously_non_authoritative": True,
            "raw_diagnostic_admitted_field": False,
            "raw_diagnostic_location": RAW_REVIEW_HARNESS_RELATIVE_PATH,
            "evidence_may_claim_trusted_preverification_only_when_it_occurred": True,
            "superseded_lineage_evidence_can_emit_the_affirmative_marker": False,
            "evidence_is_address_free": True,
            "evidence_is_deterministic": True,
        }
    )


# ---------------------------------------------------------------------------
# Material children — re-frozen under this parent
# ---------------------------------------------------------------------------


def trusted_process_and_isolation_boundary() -> dict[str, Any]:
    return _revised(
        r2.trusted_process_and_isolation_boundary(),
        contract_version=(
            "ETF_CALENDAR_TRUSTED_PROCESS_AND_ISOLATION_BOUNDARY_V1_PAD4_R3"
        ),
        authoritative_scientific_execution_is_closed_end_to_end=True,
        authority_bearing_production_operations=1,
        process_isolation_architecture_reopened=False,
    )


def worker_launch_contract() -> dict[str, Any]:
    return _revised(
        r2.worker_launch_contract(),
        contract_version=WORKER_LAUNCH_CONTRACT,
        launch_is_reachable_only_inside_the_authoritative_execution=True,
        module_accessible_spawn_primitive_exists=False,
        raw_unverified_spawn_is_test_and_review_harness_only=True,
        declared_non_worker_launch_sites=list(DECLARED_NON_WORKER_LAUNCH_SITES),
    )


def controller_authority_context_rule() -> dict[str, Any]:
    return _revised(
        r2.controller_authority_context_rule(),
        contract_version=(
            "ETF_CALENDAR_CONTROLLER_AUTHORITY_CONTEXT_RULE_V1_PAD4_R3"
        ),
        authority_context_version=AUTHORITY_CONTEXT_VERSION,
        r3_trusted_context_type_required=True,
        superseded_lineage_context_accepted_by_the_authoritative_flow=False,
        worker_protocol_authority_ticket=WORKER_PROTOCOL_AUTHORITY_TICKET,
        worker_protocol_reused_unchanged_from_pad4_r2=True,
        candidate_review_authority_context_reopened=False,
        candidate_review_authority_context_review_finding=(
            "CONFIRMED_NOT_A_DEFECT_BY_POSTP1_002V2A_PAD4_R2"
        ),
    )


def controller_result_admission_rule() -> dict[str, Any]:
    return _revised(
        r2.controller_result_admission_rule(),
        contract_version=(
            "ETF_CALENDAR_CONTROLLER_RESULT_ADMISSION_RULE_V1_PAD4_R3"
        ),
        admission_is_a_separately_callable_operation=False,
        admission_accepts_a_caller_constructed_outcome=False,
        admission_requires_the_same_authoritative_controller_execution=True,
        admission_is_preceded_by_bootstrap_pre_execution_binding=True,
        bootstrap_pre_execution_binding_is_performed_by_the_admitting_flow=True,
        validated_before_admission=sorted(
            {
                *r2.controller_result_admission_rule()["validated_before_admission"],
                "bootstrap_pre_execution_source_binding_performed_by_this_execution",
            }
        ),
        an_eventual_worker_refusal_replaces_pre_execution_binding=False,
        closed_reviewed_bypasses=list(CLOSED_REVIEWED_BYPASSES),
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    base = r2.proof_order_and_completeness_definition()
    return _revised(
        base,
        contract_version="ETF_CALENDAR_ISOLATED_WORKER_PROOF_ORDER_V1_PAD4_R3",
        controller_or_review_order=list(AUTHORITATIVE_EXECUTION_ORDER[:5]),
        controller_admission_order=list(AUTHORITATIVE_EXECUTION_ORDER[5:]),
        raw_or_test_path_order=[
            "A_MAY_REPRODUCE_UNVERIFIED_WORKER_BEHAVIOUR",
            "B_CANNOT_ENTER_SCIENTIFIC_ADMISSION",
            "C_CANNOT_CONSTRUCT_AFFIRMATIVE_SCIENTIFIC_EVIDENCE",
        ],
        every_authority_bearing_step_is_owned_by_one_closed_operation=True,
        completeness_claim=(
            "the scientific answer is produced by certified source whose "
            "pre-trust bootstrap set was bound by already-trusted controller "
            "code before any of it executed, executed as certified bytecode, "
            "under a certified interpreter, against a reviewed third-party "
            "artifact whose installed bytes were verified first, in a process "
            "that shares no mutable Python state with the application, every "
            "material authority identity reproduces against a trusted "
            "controller context, and the preverification, the launch, the "
            "outcome, the admission and the affirmative evidence are one "
            "closed controller operation that no caller can enter part-way "
            "and no caller can compose"
        ),
        required_adversarial_regressions=sorted(
            {
                *base["required_adversarial_regressions"],
                "CALLER_BUILT_ADMISSION_STATE_CANNOT_MINT_AFFIRMATIVE_EVIDENCE",
                "CALLER_CONSTRUCTED_AUTHORITATIVE_EXECUTION_REFUSES",
                "CLEAN_AUTHORITATIVE_PATH_IS_ADMITTED",
                "FABRICATED_PREVERIFICATION_MAPPING_IS_NON_AUTHORITATIVE",
                "HAND_BUILT_RAW_OUTCOME_IS_NOT_ADMITTED",
                "NEW_BYPASS_CONSTRUCTED_EXECUTION_CARRIES_NO_MATERIAL",
                "RAW_UNVERIFIED_SPAWN_FABRICATION_REPRODUCES_AS_A_CONTROL",
                "RAW_UNVERIFIED_SPAWN_RESULT_CANNOT_ENTER_ADMISSION",
                "SUPERSEDED_LINEAGE_EVIDENCE_IS_NOT_R3_AUTHORITY",
                "WORKER_COPIED_REQUEST_AUTHORITY_IS_INSUFFICIENT",
            }
        ),
    )


def science_lineage_and_safety() -> dict[str, Any]:
    return _revised(
        r2.science_lineage_and_safety(),
        contract_version=(
            "ETF_CALENDAR_ISOLATED_WORKER_SCIENCE_LINEAGE_AND_SAFETY_V1_PAD4_R3"
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
            "definition_sha256": FAILED_PAD4_R2_SHA256,
            "decision_commit": FAILED_PAD4_R2_DECISION_COMMIT,
            "review": FAILED_PAD4_R2_REVIEW,
            "review_commit": FAILED_PAD4_R2_REVIEW_COMMIT,
            "review_result": FAILED_PAD4_R2_REVIEW_RESULT,
            "artifacts_overwritten_by_this_correction": False,
            "namespace_mutated_by_this_correction": False,
            "certified": False,
            "used": False,
            "prospective_observations": 0,
        },
        trusted_persistence_authority={
            "definition_sha256": CERTIFIED_DEPENDENCY_SHA256,
            "status": "CLOSED_CERTIFIED_UNCHANGED",
            "re_reviewed_by_this_decision": False,
        },
    )


_CHILD_ARTIFACTS: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
    (
        "authoritative_scientific_execution_boundary.json",
        authoritative_scientific_execution_boundary,
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


def isolated_scientific_worker_v1_r3_definition(
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
            "correction_of": FAILED_PAD4_R2_SHA256,
            "correction_is_a_new_architecture_family": False,
            "repaired_review_findings": list(REPAIRED_REVIEW_FINDINGS),
            "closed_reviewed_bypasses": list(CLOSED_REVIEWED_BYPASSES),
            "preserved_valid_portions": list(PRESERVED_VALID_PORTIONS),
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
            "failed_pad4_r2_namespace_mutated": False,
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
                # -- the R3 correction ---------------------------------------
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
    if dict(persisted) != isolated_scientific_worker_v1_r3_definition():
        raise IsolatedScientificWorkerR3Error(
            "persisted authority-closed isolated scientific worker decision does "
            "not reproduce"
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
    bypasses = "\n".join(f"- `{name}`" for name in CLOSED_REVIEWED_BYPASSES)
    preserved = "\n".join(f"- `{name}`" for name in PRESERVED_VALID_PORTIONS)
    verbatim = "\n".join(f"- `{name}`" for name in VERBATIM_PAD4_R2_CHILDREN)
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

`{FAILED_PAD4_R2_REVIEW}` failed the `PAD4-R2` candidate
`{FAILED_PAD4_R2_SHA256}` with:

```text
{FAILED_PAD4_R2_REVIEW_RESULT}
```

Scientific admission neither required nor authenticated the trusted-controller
bootstrap pre-verification that its evidence claimed occurred. Three
independent reproducers each obtained an admitted fabricated scientific result:
the private raw spawn helper on a drifted bootstrap tree; a caller-fabricated
PASS `bootstrap_pre_verification` mapping, after which the evidence falsely
attested `ALREADY_TRUSTED_CONTROLLER_CODE`; and a hand-built
`WorkerProcessOutcome` with no subprocess ever created, using only public
names.

## The frozen rule

```text
NO OUTCOME CREATED WITHOUT SUCCESSFUL TRUSTED-CONTROLLER BOOTSTRAP
PREVERIFICATION MAY ENTER SCIENTIFIC ADMISSION OR PRODUCE AFFIRMATIVE
SCIENTIFIC AUTHORITY EVIDENCE.
```

The correction is structural. The generic composition of a caller-constructible
outcome, a generic admission function and a generic evidence function is gone
from the production scientific API. `admit_worker_result`,
`scientific_response_evidence`, `run_scientific_worker`, `WorkerProcessOutcome`,
`AdmissionOutcome` and the raw spawn helper do not exist in the production
controller. Their logic is folded inside one closed operation.

## The closed authoritative order

```text
{order}
```

The raw / test path may reproduce unverified worker behaviour, cannot enter
scientific admission, and cannot construct affirmative scientific evidence.

## Closed reviewed bypasses

{bypasses}

## Authority mechanism

Capability ownership and closed control flow — not naming, not a field value,
not a dataclass identity, not a secret and not a signature. The affirmative
authority marker is constructed at exactly one site, inside the closure-local
evidence constructor, and the mechanical API-closure audit proves it.

## Preserved valid portions

{preserved}

## Children carried forward byte-identically from `PAD4-R2`

{verbatim}

## Worker bootstrap source set

Unchanged from the reviewed `PAD4-R2` set, because this correction is local to
the controller admission surface.

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

Successful implementation authorizes only `POSTP1-002V2A-PAD4-R3`. It does
**not** authorize `POSTP1-001V2A-I2`, `POSTP1-001V2R1`, `POSTP1-003R3`,
`POSTP1-004` or any prospective collection.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    decision = isolated_scientific_worker_v1_r3_definition(registry)
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
            raise IsolatedScientificWorkerR3Error(
                f"persisted {filename} does not reproduce"
            )
        _verify_definition_digest(persisted)
        if decision["child_definition_sha256"].get(
            filename.removesuffix(".json")
        ) != expected["definition_sha256"]:
            raise IsolatedScientificWorkerR3Error(
                f"authority-closed isolated scientific worker parent does not "
                f"bind {filename}"
            )
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise IsolatedScientificWorkerR3Error(
            "persisted authority-closed isolated scientific worker report does "
            "not reproduce"
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
