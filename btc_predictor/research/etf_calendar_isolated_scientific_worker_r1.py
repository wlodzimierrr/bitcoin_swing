"""Corrected isolated one-shot scientific worker architecture for the calendar.

``POSTP1-002V2A-PAD4`` independently reproduced the ``PAD4`` parent
``cc1b325a...7b809e78`` and found **the fresh-exec process-isolation boundary
sound**, but failed the candidate with
``FAIL — EXECUTED BYTECODE NOT BOUND TO CERTIFIED SOURCE`` plus three further
release-critical authority-anchoring defects:

``A``  ``-B`` suppresses bytecode *writes* only.  A forged
       ``__pycache__/flow.cpython-312.pyc`` whose timestamp invalidation header
       still matched the certified source executed inside a real worker and the
       controller admitted ``feature_id: FORGED_BYTECODE_ID``.
``B``  ``build_scientific_request`` re-derived the certified source manifest
       from live disk, so source drift that existed *before* request
       construction produced a new self-consistent digest and self-certified.
``C``  the decision hash was a request/response echo; requests declaring
       ``0000...0000`` and ``deadbeef...deadbeef`` were both admitted with a
       real scientific result.
``D``  third-party attestation hashed only ``RECORD``; a tampered installed
       dependency file executed with ``RECORD`` untouched, and a declared
       version of ``99.99.99-FORGED`` was admitted because no reviewed
       semantic dependency authority existed.

``POSTP1-001V2A-PAD4-R1`` repairs exactly those four.  It is a correction of
``PAD4``, not a new architecture family: the fresh exec'd worker, ``-I -S -B``
isolation, one request per process, the absence of shared parent Python
objects, canonical JSON IPC, lazy-result refusal, controller result admission,
fork-only refusal and parent monkeypatch isolation all remain required and
unchanged.  Same-process runtime-owner attestation, transitive mutable-object
closure, reflection-blacklist completeness and generated-method enumeration are
not reopened.  The failed ``PAD4`` parent stays immutable, non-certified,
unused and at zero observations, in its own untouched namespace.

The corrected proof strategy is::

    CERTIFIED_SOURCE_AUTHORITY
    + FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY
    + FROZEN_CPYTHON
    + FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE
    + CLOSED_STORE_GRAMMAR
    + COMPILED_ROOT_WITNESS
    + ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER
    + TRUSTED_CONTROLLER_AUTHORITY_CONTEXT

This module is a pre-data decision builder, a static audit specification and a
reference controller.  It never collects, persists, signs or certifies
anything, and it changes no ETF calendar production code.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import sysconfig
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from btc_predictor.research import etf_calendar_compiled_binding_witness as witness
from btc_predictor.research import etf_calendar_isolated_scientific_worker as pad4
from btc_predictor.research import etf_calendar_runtime_owner_attestation as attestation
from btc_predictor.research import etf_calendar_store_capability_normal_form_r1 as narrow
from etf_calendar_worker import protocol_r1 as protocol


DECISION_VERSION = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
PROGRAM_TICKET = "POSTP1-001V2A-PAD4-R1"
OUTPUT_NAMESPACE = "prospective_evidence/etf_calendar_isolated_scientific_worker_v1_r1"
DEFINITION_FILENAME = "etf_calendar_isolated_scientific_worker_v1_r1_definition.json"
REPORT_FILENAME = "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R1_REPORT.md"
STATUS = "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
FINAL_CLASSIFICATION = (
    "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R1_READY_FOR_FINAL_XHIGH_REVIEW"
)
PROOF_STRATEGY = (
    "CERTIFIED_SOURCE_AUTHORITY_PLUS_FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY_PLUS_"
    "FROZEN_CPYTHON_PLUS_FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE_PLUS_"
    "CLOSED_STORE_GRAMMAR_PLUS_COMPILED_ROOT_WITNESS_PLUS_"
    "ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_PLUS_"
    "TRUSTED_CONTROLLER_AUTHORITY_CONTEXT"
)
REQUIRED_REVIEW = (
    "POSTP1-002V2A-PAD4-R1_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW"
)

#: The failed ``PAD4`` parent this ticket corrects.  It is preserved unchanged
#: and is never certified, never used and at zero observations.
FAILED_PAD4_SHA256 = (
    "cc1b325a656f5b0be046d46700a4fcb9ad7ad94bf9b3440acac164677b809e78"
)
FAILED_PAD4_REVIEW = "POSTP1-002V2A-PAD4"
FAILED_PAD4_REVIEW_RESULT = "FAIL — EXECUTED BYTECODE NOT BOUND TO CERTIFIED SOURCE"
FAILED_PAD4_DECISION_COMMIT = "02df82c2516ebcc50a592e5466fd15a61dcee481"
FAILED_PAD4_REVIEW_COMMIT = "c0ce6a7670f5252cac4be18bf96975ae8ec8d96b"

#: The four blocking findings this bounded correction repairs, and nothing else.
REPAIRED_REVIEW_FINDINGS: tuple[str, ...] = (
    "A_EXECUTED_BYTECODE_NOT_BOUND_TO_CERTIFIED_SOURCE",
    "B_CERTIFIED_SOURCE_AUTHORITY_NOT_FROZEN",
    "C_CONTROLLER_AUTHORITY_BINDING_INVALID",
    "D_THIRD_PARTY_INSTALLED_CONTENT_AND_SEMANTIC_AUTHORITY_NOT_ATTESTED",
)

#: Explicitly *not* reopened by this correction.
NOT_REOPENED: tuple[str, ...] = (
    "GENERATED_METHOD_ENUMERATION",
    "REFLECTION_BLACKLIST_COMPLETENESS",
    "SAME_PROCESS_RUNTIME_OWNER_ATTESTATION",
    "TRANSITIVE_MUTABLE_OBJECT_CLOSURE",
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CALENDAR_MODULE = witness.CALENDAR_MODULE
CALENDAR_SOURCE = witness.CALENDAR_SOURCE
CERTIFIED_DEPENDENCY_VERSION = witness.CERTIFIED_DEPENDENCY_VERSION
CERTIFIED_DEPENDENCY_SHA256 = witness.CERTIFIED_DEPENDENCY_SHA256
FAILED_ARCHITECTURE_LINEAGE = (*pad4.FAILED_ARCHITECTURE_LINEAGE, FAILED_PAD4_SHA256)
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


class IsolatedScientificWorkerR1Error(pad4.IsolatedScientificWorkerError):
    """Raised when the corrected architecture refuses scientific authority."""


def verify_worker_protocol_binds_the_frozen_interpreter() -> dict[str, Any]:
    """The worker-safe restatement may never drift from the owning authority."""

    if dict(protocol.PROOF_INTERPRETER_IDENTITY) != dict(PROOF_INTERPRETER_IDENTITY):
        raise IsolatedScientificWorkerR1Error(
            "corrected worker protocol interpreter identity diverges from the "
            "compiled root-binding witness authority"
        )
    return dict(sorted(PROOF_INTERPRETER_IDENTITY.items()))


# ---------------------------------------------------------------------------
# Mechanical source-manifest derivation — authority construction only
# ---------------------------------------------------------------------------

WORKER_SOURCE_MANIFEST_VERSION = "ETF_CALENDAR_WORKER_PROJECT_SOURCE_MANIFEST_V1_R1"
WORKER_ENTRYPOINT_MODULE = protocol.WORKER_ENTRYPOINT_MODULE
WORKER_ENTRYPOINT_RELATIVE_PATH = protocol.WORKER_ENTRYPOINT_RELATIVE_PATH
WORKER_PROTOCOL_MODULE = protocol.WORKER_PROTOCOL_MODULE
WORKER_PROTOCOL_RELATIVE_PATH = protocol.WORKER_PROTOCOL_RELATIVE_PATH
CERTIFIED_PACKAGE_ROOTS = protocol.CERTIFIED_PACKAGE_ROOTS

#: The ``PAD4`` entrypoint seed.  Its recursive static import closure is the
#: reviewed *current* source universe, retained here as a pre-I2 conformance
#: fixture and provenance anchor, never as production scientific authority.
PRE_I2_FIXTURE_SEED_MODULE = pad4.WORKER_ENTRYPOINT_MODULE
PRE_I2_FIXTURE_VERSION = "ETF_CALENDAR_WORKER_PRE_I2_SOURCE_MANIFEST_FIXTURE_V1"
PRE_I2_FIXTURE_ROLE = "PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE"
PRE_I2_FIXTURE_MODULE_COUNT = 116
PRE_I2_FIXTURE_MANIFEST_DIGEST = (
    "674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8"
)

#: The modules the corrected worker must actually have loaded before it may
#: evaluate.  ``etf_calendar_worker.entry_r1`` runs as ``__main__`` and is
#: therefore verified on disk rather than in ``sys.modules``.
REQUIRED_WORKER_PROJECT_MODULES: tuple[str, ...] = tuple(
    sorted(
        (
            "btc_predictor",
            "btc_predictor.data.etf_flows",
            "btc_predictor.data.ohlcv",
            "btc_predictor.features.flow",
            "btc_predictor.research.etf_calendar_scientific_worker_entry",
            "btc_predictor.research.etf_calendar_semantics",
            "btc_predictor.research.etf_calendar_worker_protocol",
            "btc_predictor.research.etf_publication_calendar",
            "btc_predictor.research.trusted_acquisition",
            "etf_calendar_worker",
            WORKER_PROTOCOL_MODULE,
        )
    )
)


def _module_source_path(project_root: Path, dotted: str) -> tuple[str, Path] | None:
    """Resolve a dotted certified module to its single canonical source file."""

    module_path = protocol.module_relative_path(dotted)
    package_path = protocol.package_relative_path(dotted)
    module_file = project_root / module_path
    package_file = project_root / package_path
    if module_file.is_file() and package_file.is_file():
        raise IsolatedScientificWorkerR1Error(
            f"certified module {dotted!r} has two candidate certified sources"
        )
    if module_file.is_file():
        return module_path, module_file
    if package_file.is_file():
        return package_path, package_file
    return None


def derive_project_source_manifest(
    project_root: Path = PROJECT_ROOT,
    seeds: Sequence[str] = (WORKER_ENTRYPOINT_MODULE,),
) -> tuple[protocol.ProjectSourceEntry, ...]:
    """Mechanically derive the recursive certified import closure of a seed.

    The derivation rule is unchanged from the reviewed ``PAD4`` derivation —
    static import declarations, nested function-level declarations included,
    plus every ancestor package — and is generalized to the two certified
    package roots.  It is used for **authority construction, review, refreeze
    and consistency checking only**.  Runtime never selects scientific
    authority with it; runtime consumes an already-frozen expected manifest.
    """

    resolved: dict[str, str] = {}
    pending = list(seeds)
    while pending:
        dotted = pending.pop()
        if dotted in resolved:
            continue
        located = _module_source_path(project_root, dotted)
        if located is None:
            continue
        relative, path = located
        resolved[dotted] = relative
        parts = dotted.split(".")
        pending.extend(".".join(parts[:index]) for index in range(1, len(parts)))
        source = path.read_text(encoding="utf-8")
        for declared in pad4._declared_imports(
            source, dotted, relative.endswith("/__init__.py")
        ):
            root, _, _ = declared.partition(".")
            if root in CERTIFIED_PACKAGE_ROOTS and declared not in resolved:
                pending.append(declared)
    entries = [
        protocol.ProjectSourceEntry(
            module=dotted,
            path=relative,
            sha256=protocol.file_sha256(project_root / relative),
        )
        for dotted, relative in resolved.items()
    ]
    return tuple(sorted(entries))


def external_import_roots(
    project_root: Path = PROJECT_ROOT,
    entries: Sequence[protocol.ProjectSourceEntry] | None = None,
) -> tuple[str, ...]:
    """The non-stdlib top-level modules the certified source universe imports."""

    manifest = (
        derive_project_source_manifest(project_root) if entries is None else entries
    )
    roots: set[str] = set()
    for entry in manifest:
        source = (project_root / entry.path).read_text(encoding="utf-8")
        for declared in pad4._declared_imports(
            source, entry.module, entry.path.endswith("/__init__.py")
        ):
            root, _, _ = declared.partition(".")
            if (
                root
                and root not in CERTIFIED_PACKAGE_ROOTS
                and root != "__future__"
                and root not in sys.stdlib_module_names
            ):
                roots.add(root)
    return tuple(sorted(roots))


def _entries(rows: Sequence[Sequence[str]]) -> tuple[protocol.ProjectSourceEntry, ...]:
    return tuple(
        protocol.ProjectSourceEntry(module, path, sha256) for module, path, sha256 in rows
    )


#: The exact reviewed pre-I2 project source universe, frozen as literal
#: material so that it stays immutable when ``POSTP1-001V2A-I2`` later changes
#: ``etf_publication_calendar.py`` and the production manifest moves.  Its role
#: is an architecture conformance test vector, provenance and a pre-I2
#: source-drift regression anchor; it is *not* the future production source
#: authority.
FROZEN_PRE_I2_SOURCE_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "btc_predictor",
        "btc_predictor/__init__.py",
        "4574cd41603677a2418e647c98ce52782039067681c61e381858b9e1ae2210ab",
    ),
    (
        "btc_predictor.backtest",
        "btc_predictor/backtest/__init__.py",
        "8621121925a11b1ca0a6eea3010946774bf8f0dd614d53e166c67debe2dfc475",
    ),
    (
        "btc_predictor.backtest.costs",
        "btc_predictor/backtest/costs.py",
        "856e44c8925b4bd5a04c44085edc33700e03b6b4595826c78441e2b180330d9f",
    ),
    (
        "btc_predictor.backtest.engine",
        "btc_predictor/backtest/engine.py",
        "7d6425746023204e30af783339ce65341839e392ddb27291ad72c8287a8be44d",
    ),
    (
        "btc_predictor.backtest.parameter_surfaces",
        "btc_predictor/backtest/parameter_surfaces.py",
        "8c83788876bcc345dc84fe27b6979eb1f0b23804dfbfded0c4ffd58f08711922",
    ),
    (
        "btc_predictor.backtest.regime_performance",
        "btc_predictor/backtest/regime_performance.py",
        "d8cc62f2ae5b33884d7f0a4586b5ff54909e47a34812b0c7e1f210458c3301be",
    ),
    (
        "btc_predictor.backtest.setup_performance",
        "btc_predictor/backtest/setup_performance.py",
        "95a2fe69f5d394cd500bf71922e85e850857400065e0070a2e86737b08c7be99",
    ),
    (
        "btc_predictor.backtest.threshold_sweeps",
        "btc_predictor/backtest/threshold_sweeps.py",
        "d4fcd2608ef38c9ef03da363f13f5a0e336c95a73270b33e582bef6e0ee91a7f",
    ),
    (
        "btc_predictor.backtest.walk_forward",
        "btc_predictor/backtest/walk_forward.py",
        "b360ad15c6f5417fe90d7c4f322ce566c42c9fb6dc923b920570ef5afedf910b",
    ),
    (
        "btc_predictor.config",
        "btc_predictor/config/__init__.py",
        "5415c0338107654a4200594230648c1cb19cf7715914e3a6116b6fcc3a769bb5",
    ),
    (
        "btc_predictor.config.application",
        "btc_predictor/config/application.py",
        "724fe645a6dafd0454763f0457f1bfc20ec867ee310f8e7cbc8600c681ac7e70",
    ),
    (
        "btc_predictor.config.runtime",
        "btc_predictor/config/runtime.py",
        "c54e48ae49f9e0943ca9fc0d21045ae9541941ac660b361016275b6828103cf4",
    ),
    (
        "btc_predictor.config.strategy",
        "btc_predictor/config/strategy.py",
        "c83eee0e50648967f0a3cab18224c96411d7e6b42c6377896fa1c20ba00dc963",
    ),
    (
        "btc_predictor.data",
        "btc_predictor/data/__init__.py",
        "b111d53703dab75eeeb75165b93945879ffc025363ec694acc25cc34f8277386",
    ),
    (
        "btc_predictor.data.audit",
        "btc_predictor/data/audit.py",
        "9255003cf3824757ce9a50f1153ff26d4d56b853006bf8f129114c0b997ea0d7",
    ),
    (
        "btc_predictor.data.bitfinex",
        "btc_predictor/data/bitfinex.py",
        "0aa6bfc7ff54cf420f3e87e81a99a26a82cc95a7959707f11ce246459f158a80",
    ),
    (
        "btc_predictor.data.bitstamp",
        "btc_predictor/data/bitstamp.py",
        "866fb37f26f1a6eb6ea1b714202ebaae2f02ed56442fd3dee11b1404743c3c93",
    ),
    (
        "btc_predictor.data.coinbase",
        "btc_predictor/data/coinbase.py",
        "4003ab14e7a4c0565c4fa105d307798463281bff5d269448fed9ee9c1cd047bc",
    ),
    (
        "btc_predictor.data.derivatives",
        "btc_predictor/data/derivatives.py",
        "f347e2d62a3bbdc6a54dc00f810a5f06cf912bc357fa41dc16d8b038e2e3f931",
    ),
    (
        "btc_predictor.data.etf_flows",
        "btc_predictor/data/etf_flows.py",
        "3446c0b1901985abb00c0b051c32f2f2e400ac290f5d61f17fa9e66ba44b2d92",
    ),
    (
        "btc_predictor.data.generic_series",
        "btc_predictor/data/generic_series.py",
        "92246cffe41a9c2e4b58111863b86b425fbf0e1dd258f33198875a4151211054",
    ),
    (
        "btc_predictor.data.ohlcv",
        "btc_predictor/data/ohlcv.py",
        "5b5e19a9f61509ff4ce7b99f4e8b8c970348e59096bc8423a79176b0141e56e3",
    ),
    (
        "btc_predictor.data.quality",
        "btc_predictor/data/quality.py",
        "abd4d422c78a13d9ce512dcd09537f9690ae60f115deffae84d8c27389958a57",
    ),
    (
        "btc_predictor.db",
        "btc_predictor/db/__init__.py",
        "727888bddc13417f2f89d400ad63205f9d9fb0e50b23940cc9487350551e25b4",
    ),
    (
        "btc_predictor.db.alembic",
        "btc_predictor/db/alembic.py",
        "752d3690799a76dfab9e716d360cdb404cbaa6a0629f373eddb458b50ba0fcb2",
    ),
    (
        "btc_predictor.db.base",
        "btc_predictor/db/base.py",
        "a8104d0955d029fd15391f3ac49bf1b1052eda8ace0e51d6b3de2800c531ad85",
    ),
    (
        "btc_predictor.db.connections",
        "btc_predictor/db/connections.py",
        "cf75324fadbbaaecc5b9e49237648e0d3f7c9a2c395d65f3c392efeec8682903",
    ),
    (
        "btc_predictor.db.derived",
        "btc_predictor/db/derived.py",
        "fbe1713fe4231cce2f73fcc57bfd53976fd2eee34d6d8f1119a797c23e91ef29",
    ),
    (
        "btc_predictor.db.portfolio",
        "btc_predictor/db/portfolio.py",
        "a535ae721cf5b2576bf28d51497e002430e9a28a2d6a90008f1fe35bf0cd0823",
    ),
    (
        "btc_predictor.db.raw",
        "btc_predictor/db/raw.py",
        "43781548ed3d6675a24deb35003e8fbf5873b3a78ff9ba19ef52fcb089755d84",
    ),
    (
        "btc_predictor.db.research",
        "btc_predictor/db/research.py",
        "b49c080102aea7ba04ae1f1ff02892179c2d366a1bc6d696206217f93660dfa0",
    ),
    (
        "btc_predictor.db.signals",
        "btc_predictor/db/signals.py",
        "088cd0d66ef30c6866a2c0941f3444df56a8340e6f1f1363244358b9b355f3c2",
    ),
    (
        "btc_predictor.db.system",
        "btc_predictor/db/system.py",
        "acc206c7a16adde26eb6174eecff3c2c30f540fc9f3a9ccc3bdfc8108dc8d129",
    ),
    (
        "btc_predictor.features",
        "btc_predictor/features/__init__.py",
        "3ad251b84af1751ba11ccb38f016217bcda7287d821c47ce3e1195d02ad29050",
    ),
    (
        "btc_predictor.features._scoring",
        "btc_predictor/features/_scoring.py",
        "895cef905e6292dd36e2d584e9c41cb00530728b472eace6f2c8626ff1e6ec06",
    ),
    (
        "btc_predictor.features.add",
        "btc_predictor/features/add.py",
        "996adc4ba9648c0122bcaa439a4e607b6178e1731e731a5a0329b99d885290f8",
    ),
    (
        "btc_predictor.features.entry",
        "btc_predictor/features/entry.py",
        "061975dbf8a1c18efd6d36da9812215309fa4a7bd8ef0d9ac65555510f270f1e",
    ),
    (
        "btc_predictor.features.flow",
        "btc_predictor/features/flow.py",
        "8a05e6861ba39b19acbbb736407f497a2490d2aff4128acdfc403ed5dffcb558",
    ),
    (
        "btc_predictor.features.hold",
        "btc_predictor/features/hold.py",
        "f7724f8a6b436d2223ad3071ad221604bcc0251ac317dd38de4338b563dfafc7",
    ),
    (
        "btc_predictor.features.momentum",
        "btc_predictor/features/momentum.py",
        "9681b7093c5bd6fa7377f61b131911b5393b18d7f2c9b23799ea079ca52638b4",
    ),
    (
        "btc_predictor.features.positioning",
        "btc_predictor/features/positioning.py",
        "b23ce0f240d82f180e24c74eb552e5e46bbd2b6fc6e6af8faa1cfa430436700e",
    ),
    (
        "btc_predictor.features.regime",
        "btc_predictor/features/regime.py",
        "0e86be6a3d0f472e686d3e6086817384488f7c24b1399581ebf3d8a05ccdb7d4",
    ),
    (
        "btc_predictor.features.rolling",
        "btc_predictor/features/rolling.py",
        "2f4b8ea3330d72ad50414e558b26434ff04203082d658cd0ac93e460c948a85c",
    ),
    (
        "btc_predictor.features.scoring_contracts",
        "btc_predictor/features/scoring_contracts.py",
        "ab5ff4c4ed35a974b3c7f183c076d01a2292976329a3dc6c8a9c9c2798495257",
    ),
    (
        "btc_predictor.features.setup",
        "btc_predictor/features/setup.py",
        "bef4346343ff5a3bd0d105d1604a8fbce8709aa61e3cda6189e2d51a293fd49e",
    ),
    (
        "btc_predictor.features.structure",
        "btc_predictor/features/structure.py",
        "35576215f66ae07b43c75638b4b29abd30b2fe6a868a0607664a5d54209d76b6",
    ),
    (
        "btc_predictor.features.trend",
        "btc_predictor/features/trend.py",
        "041050e9ada0c2ce1cbcff1af602fe3e4b3f22aee4289362465607068f0fe634",
    ),
    (
        "btc_predictor.features.volatility",
        "btc_predictor/features/volatility.py",
        "bd81be840d70ee2266ba8d7003509c0ae771ecca8d0a083f39d2d47d6f37d27b",
    ),
    (
        "btc_predictor.levels",
        "btc_predictor/levels/__init__.py",
        "99e7508f39aff33e329a3245fff6b505c07cfda60589750fb67d70ebb0d22817",
    ),
    (
        "btc_predictor.levels.anchored_vwap",
        "btc_predictor/levels/anchored_vwap.py",
        "1e51daa94a4291b6ebee424056c1836e0c920ac845896d2a0265faa84c7952f1",
    ),
    (
        "btc_predictor.levels.breakout",
        "btc_predictor/levels/breakout.py",
        "d19d388ba1f2912b0efcefb11783334a9b2088d84d2eda465ee559bbae2b3d1c",
    ),
    (
        "btc_predictor.levels.clustering",
        "btc_predictor/levels/clustering.py",
        "4c2c35203e4dd520bcff53aea1e5a218f119de1e937e2f6f0906929f0d273ed4",
    ),
    (
        "btc_predictor.levels.strength",
        "btc_predictor/levels/strength.py",
        "5d74ad41159c086c37754bdd661c8e5b01d5327ee04987a0ea636cfad97a0ab2",
    ),
    (
        "btc_predictor.levels.swing",
        "btc_predictor/levels/swing.py",
        "ae7cd9ff611bfbb0d883937de69be7c050f812df7551fa254d77bdc7f9ab56eb",
    ),
    (
        "btc_predictor.levels.volume_profile",
        "btc_predictor/levels/volume_profile.py",
        "84e524f6f2b251fba9b738f6b5d5af0bbfd602518de349b4cb687ba9f5141fb3",
    ),
    (
        "btc_predictor.logging",
        "btc_predictor/logging.py",
        "559908e00e333c2487636fd3f54da3c5d5ffe0973b60bf183d6f390cced4af39",
    ),
    (
        "btc_predictor.portfolio",
        "btc_predictor/portfolio/__init__.py",
        "1fff3db1b4620954fa2752933d41e07a3e3b44f44ae1446ff999d27b31f6af60",
    ),
    (
        "btc_predictor.portfolio.account",
        "btc_predictor/portfolio/account.py",
        "6acb770d1399042d5dd214deac6b95c99842ce3f2270259d0791afa401c2d865",
    ),
    (
        "btc_predictor.portfolio.accounting",
        "btc_predictor/portfolio/accounting.py",
        "e9f007fec30d0ba5c589d47942ccacf76c51db12cc3870c970805970e5dfe219",
    ),
    (
        "btc_predictor.portfolio.add_execution",
        "btc_predictor/portfolio/add_execution.py",
        "1482827a43f5f67ff74343e9a98acd688785a12ec3827fab6f4fa745ab1f84b6",
    ),
    (
        "btc_predictor.portfolio.entry_execution",
        "btc_predictor/portfolio/entry_execution.py",
        "87eac95a5ef4ca5fb694314d7d09d6b61d0c1eaeafc862b2da12385cdbdced73",
    ),
    (
        "btc_predictor.portfolio.exit_execution",
        "btc_predictor/portfolio/exit_execution.py",
        "90297cf3ef36e80f09289e5922e268a9322bd65e227c60f490797221f7925ed2",
    ),
    (
        "btc_predictor.portfolio.lifecycle_persistence",
        "btc_predictor/portfolio/lifecycle_persistence.py",
        "ba285de8bc9260f9f7701249cb55100e0dcfb77c953d7eaa29fa22e742acbc10",
    ),
    (
        "btc_predictor.portfolio.state_machine",
        "btc_predictor/portfolio/state_machine.py",
        "88cb80d55756dfba7235d786d589c3489f38c815c23801ffc9da94903f45b09f",
    ),
    (
        "btc_predictor.portfolio.stop_execution",
        "btc_predictor/portfolio/stop_execution.py",
        "6c7613adbf74942405dab5a676b97c8e022500a6a069bb0537ed7eca7be92bf2",
    ),
    (
        "btc_predictor.portfolio.trim_execution",
        "btc_predictor/portfolio/trim_execution.py",
        "24287629714c548f40171b3b5202e9e6c510b95d5a02f2969f2393b5f9dac12e",
    ),
    (
        "btc_predictor.quant",
        "btc_predictor/quant/__init__.py",
        "3e731c565e559e66678a37d899da6ca9c079f99d1083438ab1b9ab8befbda230",
    ),
    (
        "btc_predictor.quant.arrays",
        "btc_predictor/quant/arrays.py",
        "645db15444aaec585a9a568da66fc90e0f17aa8bffce0d9a0d6245f2eaa81de5",
    ),
    (
        "btc_predictor.quant.comparisons",
        "btc_predictor/quant/comparisons.py",
        "55aa8e923819766a6ce0c3135c9e97fdbc11611fb677d1d0289b802487bf3faf",
    ),
    (
        "btc_predictor.quant.distances",
        "btc_predictor/quant/distances.py",
        "197557c355ca35674e41f40e0389217ffdcedc384a0df8035d6768a493a4a99a",
    ),
    (
        "btc_predictor.quant.portfolio",
        "btc_predictor/quant/portfolio.py",
        "3a47d5c50741451149e9f27911b34d363d6c54d2823b2b5d4c59ada3869a5060",
    ),
    (
        "btc_predictor.quant.risk",
        "btc_predictor/quant/risk.py",
        "7c0055648346de42fb221b1ab82f40189377f74904ecc11bc191449ebf57c004",
    ),
    (
        "btc_predictor.quant.rolling",
        "btc_predictor/quant/rolling.py",
        "a051263bb2b0b019cb75f76a2487c0b13fdd6182e1ce4c92c30382515b2c7448",
    ),
    (
        "btc_predictor.quant.scoring",
        "btc_predictor/quant/scoring.py",
        "2fa354c30c753fc4b402d3876502db17f153f9b19d54a5d3e4c0d608546c0780",
    ),
    (
        "btc_predictor.quant.simulation",
        "btc_predictor/quant/simulation.py",
        "ecd22cef06d34b9a7b6a8f13767e1a07f1dd48664c79f5dbbd6b938beb123831",
    ),
    (
        "btc_predictor.quant.transforms",
        "btc_predictor/quant/transforms.py",
        "ce56b842a5ca1f16fa2331b40fa2d5e3c9d94199ab6b3604f460417972d6b089",
    ),
    (
        "btc_predictor.research",
        "btc_predictor/research/__init__.py",
        "7ed16cc01be76004ddbd728f6c547c04393ac97787c24b1192384f193f210059",
    ),
    (
        "btc_predictor.research.component_ablation",
        "btc_predictor/research/component_ablation.py",
        "02f7d7e13b861c6b00cdce6cee6e5efc6e9922aaddafcc45344a6b35467f463b",
    ),
    (
        "btc_predictor.research.decision_state",
        "btc_predictor/research/decision_state.py",
        "ec8f5de75ca1e98aab74c802f81b0817d674d067a49e6a64dac169ee8493ac87",
    ),
    (
        "btc_predictor.research.etf_calendar_scientific_worker_entry",
        "btc_predictor/research/etf_calendar_scientific_worker_entry.py",
        "cf85a16b68440568a953c757512dc2638d11958e852004383f5f0c4430d6ee62",
    ),
    (
        "btc_predictor.research.etf_calendar_semantics",
        "btc_predictor/research/etf_calendar_semantics.py",
        "87367f4c75471afaeaa005c8c0503717aa40b2b54c266736642d74a611171f64",
    ),
    (
        "btc_predictor.research.etf_calendar_worker_protocol",
        "btc_predictor/research/etf_calendar_worker_protocol.py",
        "2291cf952ad4416e732ddd2e2395e91994eee6b40b6281b422cde18bf0ec6757",
    ),
    (
        "btc_predictor.research.etf_publication_calendar",
        "btc_predictor/research/etf_publication_calendar.py",
        "49fa356e48426aaaea0be987930062f85058839f9efd73feb2d210b3b79c4145",
    ),
    (
        "btc_predictor.research.feature_interactions",
        "btc_predictor/research/feature_interactions.py",
        "a5da8956ca4dd261c7095a5077cbc70e5910a3b3ea614a1d8dca52b3dbaa91a2",
    ),
    (
        "btc_predictor.research.feature_matrix",
        "btc_predictor/research/feature_matrix.py",
        "e67a43becd823dbcbe36f15127454774ca00a3302beb97ac6a56d87cf8940a49",
    ),
    (
        "btc_predictor.research.monte_carlo_risk",
        "btc_predictor/research/monte_carlo_risk.py",
        "d69aa5bd3313eec51fac6569507249cb0325de16acbe384451d4fd3cf129b6a7",
    ),
    (
        "btc_predictor.research.paper_trade_outcomes",
        "btc_predictor/research/paper_trade_outcomes.py",
        "05bd7a790a17d223def02ea408e8c87c62571d0816fd35c0e64249ddc753f733",
    ),
    (
        "btc_predictor.research.predictor_diagnostics",
        "btc_predictor/research/predictor_diagnostics.py",
        "4b23d3da3aeb2eb70ea8540f357922d28007e4727a68f5d7329ea5f319a7d72b",
    ),
    (
        "btc_predictor.research.price_source_policy",
        "btc_predictor/research/price_source_policy.py",
        "71137e8dba309a229dcc157e3df1ad29f3f9cc350c58a37c3290b8d4b0df07a0",
    ),
    (
        "btc_predictor.research.reference_composite",
        "btc_predictor/research/reference_composite.py",
        "6e4ab5d0c2ce970636728cd11e964184468e684ae0da09ec84baf2e72413a7b7",
    ),
    (
        "btc_predictor.research.strategy_comparison",
        "btc_predictor/research/strategy_comparison.py",
        "44636078d1371d87ac3aef0b87b367b3520e21ba4d4190674f45250b5d33ca77",
    ),
    (
        "btc_predictor.research.strategy_promotion",
        "btc_predictor/research/strategy_promotion.py",
        "82c9d1fe1f3df5ff20d8f76dab0170a0a4a701a0346e42f753d37536d1f55e7d",
    ),
    (
        "btc_predictor.research.trusted_acquisition",
        "btc_predictor/research/trusted_acquisition.py",
        "df13fccd4abd62a38616f253ca09e91e885be3c44d353845cac445e1b490110f",
    ),
    (
        "btc_predictor.research.trusted_acquisition_authority",
        "btc_predictor/research/trusted_acquisition_authority.py",
        "1263332d8139c669ed092bd4704270ab53c442f54516db29aa634afa1378e283",
    ),
    (
        "btc_predictor.research.trusted_acquisition_persistence",
        "btc_predictor/research/trusted_acquisition_persistence.py",
        "3fae833cb659442af632b229f71e783526beb1cfefd8ec0cc19277a1bdec3ad3",
    ),
    (
        "btc_predictor.risk",
        "btc_predictor/risk/__init__.py",
        "e8f10cb1e433c4b8d7b93558a7041182e699a92cc4bf9a5b136e6bd600906976",
    ),
    (
        "btc_predictor.risk.budget",
        "btc_predictor/risk/budget.py",
        "f16cafdda0515732e7a878af89a18450fbc40cedc908b7e8eb6fc7c1a1b342a9",
    ),
    (
        "btc_predictor.risk.buffer",
        "btc_predictor/risk/buffer.py",
        "28adc5d5e19dbdacf5c89e843bab501034035bd94d144e076e16a73059ec4c28",
    ),
    (
        "btc_predictor.risk.exposure",
        "btc_predictor/risk/exposure.py",
        "63b566aa6b421507268eb343245bc161c0c6e7ce5be9d492949bfef45bbad00a",
    ),
    (
        "btc_predictor.risk.invalidation",
        "btc_predictor/risk/invalidation.py",
        "182d62c17500c0527de82fb5e6ec76b0d53ca57678440fc973b33cf4f40f2d9d",
    ),
    (
        "btc_predictor.risk.reward",
        "btc_predictor/risk/reward.py",
        "490ff52e8a387a1150ca96b944fe2a25b704bb5252c42f6174b16e2fa7516aac",
    ),
    (
        "btc_predictor.risk.sizing",
        "btc_predictor/risk/sizing.py",
        "8c637f6d2b25e97cc98ac94188efecba3ff2875e70bf44682feca53adc8a1b3f",
    ),
    (
        "btc_predictor.risk.stop",
        "btc_predictor/risk/stop.py",
        "ac65d1b90d691454ed3abb38a392e85fdb9c073bfe30a14bd6f42e7c9d7d79c6",
    ),
    (
        "btc_predictor.risk.trailing",
        "btc_predictor/risk/trailing.py",
        "9bdd924c6d326f38cbddd3bd0310ff6dfa9ff5287389ab58498dea149971d795",
    ),
    (
        "btc_predictor.risk.tranches",
        "btc_predictor/risk/tranches.py",
        "e522bf575529e00d95482efd7cbc5c34a9888821ff326b3c4eb5f34db2ceb9fa",
    ),
    (
        "btc_predictor.signals",
        "btc_predictor/signals/__init__.py",
        "4cec6de171f26b3420adc4e33dcf68e1da339aef5a0afc68b21b5835d5dc4869",
    ),
    (
        "btc_predictor.signals.add_requirements",
        "btc_predictor/signals/add_requirements.py",
        "3f4767d5f6308870a448cb84d96d3c95b259dbaa3f4e5218ed3362cfe3acebb8",
    ),
    (
        "btc_predictor.signals.breakout_retest",
        "btc_predictor/signals/breakout_retest.py",
        "28e8649803a9d2e6502d5e38ad8570073d67d8faf6a7ad52bd442a4dedf4f999",
    ),
    (
        "btc_predictor.signals.data_quality",
        "btc_predictor/signals/data_quality.py",
        "36eda24a209dbfc13c21cb30682efb20a0ec77b221e52fe9852f175f0caed1c7",
    ),
    (
        "btc_predictor.signals.exit_rules",
        "btc_predictor/signals/exit_rules.py",
        "d76483f348ada1cf61dfdb1c4a038c41aad4254810b176c44dc8dabcd5301fff",
    ),
    (
        "btc_predictor.signals.hard_veto",
        "btc_predictor/signals/hard_veto.py",
        "b1a9d2fae0f88a2553557e3de44d3dad172c35bf32090ef4dfc4affbeb13c5ef",
    ),
    (
        "btc_predictor.signals.higher_low",
        "btc_predictor/signals/higher_low.py",
        "f0fac06e0a77cde3f5f258b994969e34247f76517020c77c12687d9356bd222b",
    ),
    (
        "btc_predictor.signals.no_chase",
        "btc_predictor/signals/no_chase.py",
        "c00773594032044920e9d547f096fb3878f965085c11ab7e0be314c810432b18",
    ),
    (
        "btc_predictor.signals.reason_codes",
        "btc_predictor/signals/reason_codes.py",
        "0a8d8f374bca3d7cf0cf57c48a1c55c7b1bebb237527698bdc553483027cc850",
    ),
    (
        "btc_predictor.signals.reclaim",
        "btc_predictor/signals/reclaim.py",
        "c95ec5ad2a75e13f7ef3937fd934bd11aedc8d3ff6d340d09570a8f95319331c",
    ),
    (
        "btc_predictor.signals.trim",
        "btc_predictor/signals/trim.py",
        "11f92d0452835d760169055504c8e0b6a3c0f90257edc76e7093c9abd1b4db2d",
    ),
)

#: The three corrected worker-owned modules this architecture adds on top of
#: the reviewed pre-I2 universe.
FROZEN_WORKER_PACKAGE_ROWS: tuple[tuple[str, str, str], ...] = (
    (
        "etf_calendar_worker",
        "etf_calendar_worker/__init__.py",
        "28b263fdb0c202e7cf22f0e64bc613437e9ddef0e15972066881c51bedba49cb",
    ),
    (
        "etf_calendar_worker.entry_r1",
        "etf_calendar_worker/entry_r1.py",
        "24aebc4e1b7536065a9cb131fa5b714e552482e0125dcfb6b89516fd56c9a535",
    ),
    (
        "etf_calendar_worker.protocol_r1",
        "etf_calendar_worker/protocol_r1.py",
        "a896925a2cc24e323e1fe54537a5b17693ef3d9e837d1221d68f34b3d08e30de",
    ),
)


def frozen_pre_i2_source_manifest() -> tuple[protocol.ProjectSourceEntry, ...]:
    return tuple(sorted(_entries(FROZEN_PRE_I2_SOURCE_ROWS)))


def frozen_candidate_source_manifest() -> tuple[protocol.ProjectSourceEntry, ...]:
    """The frozen expected manifest the corrected worker is bound to."""

    return tuple(
        sorted(_entries(FROZEN_PRE_I2_SOURCE_ROWS + FROZEN_WORKER_PACKAGE_ROWS))
    )


def verify_frozen_pre_i2_fixture() -> dict[str, Any]:
    """The frozen fixture must still state the exact reviewed universe."""

    entries = frozen_pre_i2_source_manifest()
    digest = protocol.manifest_digest(entries)
    if len(entries) != PRE_I2_FIXTURE_MODULE_COUNT:
        raise IsolatedScientificWorkerR1Error(
            f"pre-I2 source fixture is {len(entries)} modules, "
            f"frozen {PRE_I2_FIXTURE_MODULE_COUNT}"
        )
    if digest != PRE_I2_FIXTURE_MANIFEST_DIGEST:
        raise IsolatedScientificWorkerR1Error(
            f"pre-I2 source fixture digest {digest} is not the frozen "
            f"{PRE_I2_FIXTURE_MANIFEST_DIGEST}"
        )
    return {"module_count": len(entries), "manifest_digest": digest}


# ---------------------------------------------------------------------------
# Repair D — the exact reviewed third-party semantic and artifact registry
# ---------------------------------------------------------------------------

THIRD_PARTY_REGISTRY_VERSION = "ETF_CALENDAR_WORKER_THIRD_PARTY_AUTHORITY_V1_R1"

#: The exact reviewed third-party semantic and artifact authority.  These are
#: mechanically derived from the reviewed installed environment and frozen
#: here; they are never re-read from whatever happens to be installed.  Install
#: locations and absolute ``RECORD`` paths are deliberately *not* here: they are
#: launch-bound material.
FROZEN_THIRD_PARTY_AUTHORITY_ROWS: tuple[Mapping[str, Any], ...] = (
    {
        "distribution": "alembic",
        "version": "1.19.1",
        "metadata_name": "alembic",
        "dist_info_directory": "alembic-1.19.1.dist-info",
        "record_sha256": (
            "ebbb23640b1d2a9c5554db547f0af8ce79c36320e268ed25a376851e3c40dbe7"
        ),
        "record_content_manifest_digest": (
            "86960035cb916589bea1fe28cf60646154484567b8b53f1247390699ad50a6f9"
        ),
        "record_row_count": 180,
        "hashed_row_count": 103,
        "root_modules": ["alembic"],
    },
    {
        "distribution": "cryptography",
        "version": "50.0.1",
        "metadata_name": "cryptography",
        "dist_info_directory": "cryptography-50.0.1.dist-info",
        "record_sha256": (
            "e77cb6a30c87bdac2ee2ec0819a509ca45f660bd263f41da1f21ac3b48f2fb8b"
        ),
        "record_content_manifest_digest": (
            "68c3a09f5bad49e0c7a0dfa968536d85f873e5022f34e00a9f636929f1e32d59"
        ),
        "record_row_count": 200,
        "hashed_row_count": 121,
        "root_modules": ["cryptography"],
    },
    {
        "distribution": "numpy",
        "version": "2.5.2",
        "metadata_name": "numpy",
        "dist_info_directory": "numpy-2.5.2.dist-info",
        "record_sha256": (
            "7cde927bec887ea8c7a9be3d1e5c6719e504b4e11e29bddc66ed328f64dd9faa"
        ),
        "record_content_manifest_digest": (
            "cb22b41061e85436627479fe57d26d119da169035a0cac36380b84c26c3014c3"
        ),
        "record_row_count": 1336,
        "hashed_row_count": 928,
        "root_modules": ["numpy"],
    },
    {
        "distribution": "scipy",
        "version": "1.18.1",
        "metadata_name": "scipy",
        "dist_info_directory": "scipy-1.18.1.dist-info",
        "record_sha256": (
            "d376f6be3fce626b65090112b4498ae3221a25f6c8cb8d5fe46dd9f31d324858"
        ),
        "record_content_manifest_digest": (
            "c103a8d760286c146a96259969b44d6d4694c12f152d66e6e19b5829d459cd84"
        ),
        "record_row_count": 2421,
        "hashed_row_count": 1432,
        "root_modules": ["scipy"],
    },
    {
        "distribution": "sqlalchemy",
        "version": "2.0.52",
        "metadata_name": "SQLAlchemy",
        "dist_info_directory": "sqlalchemy-2.0.52.dist-info",
        "record_sha256": (
            "c386ba92b9d4998a846119301af8e71e13c741826ad4e6ad9103bde4b390a5b9"
        ),
        "record_content_manifest_digest": (
            "0a236c13e7c0de3426b0d4611965a03801c241bbd2feab0a23fc65d1bcf13807"
        ),
        "record_row_count": 531,
        "hashed_row_count": 274,
        "root_modules": ["sqlalchemy"],
    },
)


def frozen_third_party_authority() -> tuple[protocol.FrozenDistributionAuthority, ...]:
    return protocol.frozen_distribution_authorities(
        [dict(row) for row in FROZEN_THIRD_PARTY_AUTHORITY_ROWS]
    )


def derive_third_party_authority(
    roots: Sequence[str],
) -> tuple[protocol.FrozenDistributionAuthority, ...]:
    """Mechanically derive the reviewed registry from the installed environment.

    This is the **authority construction / refreeze** operation.  Runtime never
    calls it: an arbitrary installed environment may not silently become the
    scientific authority.
    """

    import importlib.metadata as metadata

    mapping = metadata.packages_distributions()
    by_distribution: dict[str, set[str]] = {}
    for root in roots:
        names = mapping.get(root)
        if not names:
            raise IsolatedScientificWorkerR1Error(
                f"worker dependency {root!r} has no installed distribution metadata"
            )
        by_distribution.setdefault(sorted(names)[0], set()).add(root)
    rows: list[dict[str, Any]] = []
    for name, module_roots in by_distribution.items():
        dist = metadata.distribution(name)
        info = Path(str(dist._path))
        record = info / "RECORD"
        if not record.is_file():
            raise IsolatedScientificWorkerR1Error(
                f"distribution {name!r} declares no installed RECORD manifest"
            )
        parsed = protocol.parse_record_rows(
            record.read_text(encoding="utf-8"), name
        )
        rows.append(
            {
                "distribution": protocol.normalize_distribution_name(name),
                "version": dist.version,
                "metadata_name": name,
                "dist_info_directory": info.name,
                "record_sha256": protocol.file_sha256(record),
                "record_content_manifest_digest": (
                    protocol.record_content_manifest_digest(parsed)
                ),
                "record_row_count": len(parsed),
                "hashed_row_count": sum(
                    1 for row in parsed if row.algorithm is not None
                ),
                "root_modules": sorted(module_roots),
            }
        )
    rows.sort(key=lambda row: row["distribution"])
    return protocol.frozen_distribution_authorities(rows)


def observe_installed_distributions(
    authorities: Sequence[protocol.FrozenDistributionAuthority],
) -> tuple[protocol.InstalledDistributionObservation, ...]:
    """Launch-bound installation material for the frozen reviewed registry.

    Only ``location``, ``record_path`` and ``environment_root`` are observed
    here.  Distribution, version and reviewed artifact identity are *not*
    observed: they come from the trusted controller authority context and the
    worker verifies the installation against them.
    """

    import importlib.metadata as metadata

    environment_root = str(Path(sys.prefix).resolve())
    rows: list[dict[str, Any]] = []
    for authority in authorities:
        try:
            dist = metadata.distribution(authority.metadata_name)
        except metadata.PackageNotFoundError as error:
            raise IsolatedScientificWorkerR1Error(
                f"reviewed distribution {authority.metadata_name!r} is not installed"
            ) from error
        info = Path(str(dist._path))
        rows.append(
            {
                "distribution": authority.distribution,
                "location": str(Path(dist.locate_file("")).resolve()),
                "record_path": str((info / "RECORD").resolve()),
                "environment_root": environment_root,
            }
        )
    rows.sort(key=lambda row: row["distribution"])
    return protocol.installed_distribution_observations(rows)


# ---------------------------------------------------------------------------
# Repair C — the trusted controller authority context
# ---------------------------------------------------------------------------

AUTHORITY_CONTEXT_VERSION = "ETF_CALENDAR_SCIENTIFIC_WORKER_AUTHORITY_CONTEXT_V1_R1"
AUTHORITY_CONSTRUCTION_REFREEZE = "AUTHORITY_CONSTRUCTION_REFREEZE"
FINAL_CALENDAR_AUTHORITY = "FINAL_CALENDAR_AUTHORITY"
REVIEW_CANDIDATE_CONTEXT = "REVIEW_CANDIDATE_CONTEXT"
AUTHORITY_CONTEXT_ORIGINS = protocol.AUTHORITY_CONTEXT_ORIGINS

#: The field the final ``ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`` refreeze must
#: carry before a production controller authority context can exist at all.
FINAL_CALENDAR_AUTHORITY_WORKER_FIELD = "isolated_scientific_worker_authority"


@dataclass(frozen=True)
class ScientificWorkerAuthorityContext:
    """The trusted expected values request construction and admission use.

    This is the central ``PAD4-R1`` correction.  A request cannot construct it,
    a response cannot construct it, live disk cannot silently replace it and
    the installed third-party environment cannot silently replace it.  The
    scientific request is compared *against* this context; the request is never
    itself the trust root.
    """

    origin: str
    proof_architecture_version: str
    proof_architecture_ticket: str
    proof_architecture_sha256: str
    interpreter_identity: Mapping[str, Any]
    project_source_manifest: tuple[protocol.ProjectSourceEntry, ...]
    project_source_manifest_role: str
    required_project_modules: tuple[str, ...]
    third_party_authority: tuple[protocol.FrozenDistributionAuthority, ...]
    calendar_authority_version: str
    calendar_authority_sha256: str
    trusted_persistence_authority_sha256: str

    def __post_init__(self) -> None:
        if self.origin not in AUTHORITY_CONTEXT_ORIGINS:
            raise IsolatedScientificWorkerR1Error(
                f"unknown authority context origin {self.origin!r}"
            )
        if self.proof_architecture_version != DECISION_VERSION:
            raise IsolatedScientificWorkerR1Error(
                "authority context does not bind the corrected architecture version"
            )
        if self.proof_architecture_ticket != PROGRAM_TICKET:
            raise IsolatedScientificWorkerR1Error(
                "authority context does not bind the corrected architecture ticket"
            )
        sha = self.proof_architecture_sha256
        if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
            raise IsolatedScientificWorkerR1Error(
                f"authority context proof-architecture hash is malformed: {sha!r}"
            )
        if dict(self.interpreter_identity) != dict(PROOF_INTERPRETER_IDENTITY):
            raise IsolatedScientificWorkerR1Error(
                "authority context does not bind the frozen proof interpreter"
            )
        if self.project_source_manifest_role not in (
            protocol.PROJECT_SOURCE_MANIFEST_ROLES
        ):
            raise IsolatedScientificWorkerR1Error(
                f"unknown source manifest role {self.project_source_manifest_role!r}"
            )
        entries = protocol.project_source_entries(
            [entry.as_material() for entry in self.project_source_manifest]
        )
        if entries != tuple(self.project_source_manifest):
            raise IsolatedScientificWorkerR1Error(
                "authority context source manifest is not canonical"
            )
        certified = {entry.module for entry in entries}
        for module in (WORKER_ENTRYPOINT_MODULE, WORKER_PROTOCOL_MODULE):
            if module not in certified:
                raise IsolatedScientificWorkerR1Error(
                    f"authority context source manifest omits {module}"
                )
        outside = sorted(set(self.required_project_modules) - certified)
        if outside:
            raise IsolatedScientificWorkerR1Error(
                f"required modules outside the frozen manifest: {outside!r}"
            )
        protocol.frozen_distribution_authorities(
            [entry.as_material() for entry in self.third_party_authority]
        )

    # -- derived trusted material ------------------------------------------

    @property
    def project_source_manifest_digest(self) -> str:
        return protocol.manifest_digest(self.project_source_manifest)

    @property
    def third_party_authority_digest(self) -> str:
        return protocol.third_party_authority_digest(self.third_party_authority)

    def _source_sha(self, relative: str) -> str:
        for entry in self.project_source_manifest:
            if entry.path == relative:
                return entry.sha256
        raise IsolatedScientificWorkerR1Error(
            f"authority context source manifest omits {relative}"
        )

    @property
    def worker_entrypoint_sha256(self) -> str:
        return self._source_sha(WORKER_ENTRYPOINT_RELATIVE_PATH)

    @property
    def worker_protocol_sha256(self) -> str:
        return self._source_sha(WORKER_PROTOCOL_RELATIVE_PATH)

    def expected_authority_fields(self) -> dict[str, Any]:
        """Every material authority identity, as the trusted context states it."""

        return {
            "calendar_authority_sha256": self.calendar_authority_sha256,
            "calendar_authority_version": self.calendar_authority_version,
            "interpreter_identity": dict(self.interpreter_identity),
            "project_source_manifest_digest": self.project_source_manifest_digest,
            "project_source_manifest_role": self.project_source_manifest_role,
            "third_party_authority_digest": self.third_party_authority_digest,
            "trusted_persistence_authority_sha256": (
                self.trusted_persistence_authority_sha256
            ),
            "worker_authority_sha256": self.proof_architecture_sha256,
            "worker_authority_ticket": self.proof_architecture_ticket,
            "worker_authority_version": self.proof_architecture_version,
            "worker_entrypoint_module": WORKER_ENTRYPOINT_MODULE,
            "worker_entrypoint_sha256": self.worker_entrypoint_sha256,
            "worker_protocol_sha256": self.worker_protocol_sha256,
        }

    def as_evidence(self) -> dict[str, Any]:
        """Deterministic, address-free identity of the trusted context."""

        return {
            "authority_context_version": AUTHORITY_CONTEXT_VERSION,
            "authority_context_origin": self.origin,
            "proof_architecture_version": self.proof_architecture_version,
            "proof_architecture_ticket": self.proof_architecture_ticket,
            "proof_architecture_sha256": self.proof_architecture_sha256,
            "project_source_manifest_digest": self.project_source_manifest_digest,
            "project_source_manifest_role": self.project_source_manifest_role,
            "project_source_module_count": len(self.project_source_manifest),
            "third_party_authority_digest": self.third_party_authority_digest,
            "third_party_distributions": [
                entry.distribution for entry in self.third_party_authority
            ],
            "calendar_authority_version": self.calendar_authority_version,
            "calendar_authority_sha256": self.calendar_authority_sha256,
            "trusted_persistence_authority_sha256": (
                self.trusted_persistence_authority_sha256
            ),
        }


def _calendar_identity() -> tuple[str, str, str]:
    from btc_predictor.research import etf_publication_calendar as calendar

    return (
        calendar.AUTHORITY_VERSION,
        calendar.FROZEN_AUTHORITY_DEFINITION_SHA256,
        calendar.TRUSTED_PERSISTENCE_AUTHORITY_SHA256,
    )


def candidate_review_authority_context(
    proof_architecture_sha256: str,
    *,
    origin: str = REVIEW_CANDIDATE_CONTEXT,
) -> ScientificWorkerAuthorityContext:
    """The trusted context used while this candidate is under review.

    The candidate's own parent hash cannot be materially embedded inside
    itself, so no cryptographic self-hash fixed point is attempted.  The
    architecture uses a two-stage boundary instead: the reviewer or the test
    harness instantiates this context with the *recomputed* parent hash, which
    comes from the trusted review context and never from the scientific
    request.  After a review PASS, ``POSTP1-001V2A-I2`` binds the certified
    hash into the final calendar authority, where no self-reference exists.
    """

    version, calendar_sha, persistence_sha = _calendar_identity()
    return ScientificWorkerAuthorityContext(
        origin=origin,
        proof_architecture_version=DECISION_VERSION,
        proof_architecture_ticket=PROGRAM_TICKET,
        proof_architecture_sha256=proof_architecture_sha256,
        interpreter_identity=dict(PROOF_INTERPRETER_IDENTITY),
        project_source_manifest=frozen_candidate_source_manifest(),
        project_source_manifest_role=(
            "PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE"
        ),
        required_project_modules=REQUIRED_WORKER_PROJECT_MODULES,
        third_party_authority=frozen_third_party_authority(),
        calendar_authority_version=version,
        calendar_authority_sha256=calendar_sha,
        trusted_persistence_authority_sha256=persistence_sha,
    )


def derive_authority_context_from_reviewed_source(
    proof_architecture_sha256: str,
    *,
    project_root: Path = PROJECT_ROOT,
    origin: str = AUTHORITY_CONSTRUCTION_REFREEZE,
) -> ScientificWorkerAuthorityContext:
    """Authority construction / refreeze: derive the manifest from source.

    This is the *only* operation permitted to read the source manifest and the
    installed dependency registry from live material, and it is explicitly not
    a runtime operation.  Runtime consumes an already-frozen context.
    """

    entries = derive_project_source_manifest(project_root)
    version, calendar_sha, persistence_sha = _calendar_identity()
    return ScientificWorkerAuthorityContext(
        origin=origin,
        proof_architecture_version=DECISION_VERSION,
        proof_architecture_ticket=PROGRAM_TICKET,
        proof_architecture_sha256=proof_architecture_sha256,
        interpreter_identity=dict(PROOF_INTERPRETER_IDENTITY),
        project_source_manifest=entries,
        project_source_manifest_role="PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE",
        required_project_modules=REQUIRED_WORKER_PROJECT_MODULES,
        third_party_authority=derive_third_party_authority(
            external_import_roots(project_root, entries)
        ),
        calendar_authority_version=version,
        calendar_authority_sha256=calendar_sha,
        trusted_persistence_authority_sha256=persistence_sha,
    )


PRODUCTION_CONTEXT_NOT_YET_BOUND = (
    "PRODUCTION_AUTHORITY_CONTEXT_NOT_YET_BOUND_BY_POSTP1_001V2A_I2"
)


def production_authority_context_from_calendar_authority(
    calendar_authority: Mapping[str, Any],
) -> ScientificWorkerAuthorityContext:
    """The frozen production rule: the context comes from the final authority.

    The production controller authority context must be derived from the final
    ``ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`` definition — never from the
    request, the current filesystem, the ambient environment or a
    caller-selected SHA.  ``POSTP1-001V2A-I2`` must bind the certified
    ``PAD4-R1`` hash, the exact final post-I2 source manifest and the reviewed
    third-party authority into that definition.  Until it does, there is no
    production context and this refuses.
    """

    material = calendar_authority.get(FINAL_CALENDAR_AUTHORITY_WORKER_FIELD)
    if not isinstance(material, Mapping):
        raise IsolatedScientificWorkerR1Error(
            f"{PRODUCTION_CONTEXT_NOT_YET_BOUND}: the final calendar authority "
            f"declares no {FINAL_CALENDAR_AUTHORITY_WORKER_FIELD!r}"
        )
    required = {
        "proof_architecture_sha256",
        "project_source_manifest",
        "required_project_modules",
        "third_party_authority",
    }
    missing = sorted(required - set(material))
    if missing:
        raise IsolatedScientificWorkerR1Error(
            f"{PRODUCTION_CONTEXT_NOT_YET_BOUND}: missing {missing!r}"
        )
    version, calendar_sha, persistence_sha = _calendar_identity()
    return ScientificWorkerAuthorityContext(
        origin=FINAL_CALENDAR_AUTHORITY,
        proof_architecture_version=DECISION_VERSION,
        proof_architecture_ticket=PROGRAM_TICKET,
        proof_architecture_sha256=str(material["proof_architecture_sha256"]),
        interpreter_identity=dict(PROOF_INTERPRETER_IDENTITY),
        project_source_manifest=protocol.project_source_entries(
            material["project_source_manifest"]
        ),
        project_source_manifest_role=(
            "POST_I2_FINAL_CALENDAR_PARENT_BOUND_PRODUCTION_AUTHORITY"
        ),
        required_project_modules=tuple(material["required_project_modules"]),
        third_party_authority=protocol.frozen_distribution_authorities(
            material["third_party_authority"]
        ),
        calendar_authority_version=version,
        calendar_authority_sha256=calendar_sha,
        trusted_persistence_authority_sha256=persistence_sha,
    )


# ---------------------------------------------------------------------------
# Repair A — fresh, empty, per-worker bytecode-cache namespaces
# ---------------------------------------------------------------------------

WORKER_LAUNCH_CONTRACT = "ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER_V1_R1"
WORKER_LAUNCH_FLAGS: tuple[str, ...] = ("-I", "-S", "-B")
WORKER_LAUNCH_X_OPTION = "pycache_prefix"
EXEC_LAUNCH = "EXEC_FRESH_INTERPRETER"
FORK_WITHOUT_EXEC = "FORK_WITHOUT_EXEC"
FORK_SERVER_REUSE = "REUSED_LONG_LIVED_WORKER"
AUTHORIZED_LAUNCH_MECHANISMS: tuple[str, ...] = (EXEC_LAUNCH,)
UNAUTHORIZED_LAUNCH_MECHANISMS: tuple[str, ...] = (
    FORK_WITHOUT_EXEC,
    FORK_SERVER_REUSE,
)

FROZEN_WORKER_ENVIRONMENT: Mapping[str, str] = {
    "LC_ALL": "C",
    "LANG": "C",
    "TZ": "UTC",
}

_BASE_SYS_PATH_CACHE: dict[str, tuple[str, ...]] = {}
_PYCACHE_ROOT: list[Path] = []


def authorize_worker_launch_mechanism(mechanism: str) -> str:
    """Only a fresh exec'd interpreter is an authorized scientific worker."""

    if mechanism not in AUTHORIZED_LAUNCH_MECHANISMS:
        raise IsolatedScientificWorkerR1Error(
            f"{mechanism}: {protocol.NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER}"
        )
    return mechanism


def controller_pycache_root() -> Path:
    """The controller-owned base directory for per-worker cache namespaces."""

    if not _PYCACHE_ROOT:
        _PYCACHE_ROOT.append(
            Path(tempfile.mkdtemp(prefix="etf-calendar-worker-pycache-")).resolve()
        )
    return _PYCACHE_ROOT[0]


def create_fresh_pycache_namespace(directory: Path) -> Path:
    """Create, and prove, one empty per-worker bytecode-cache namespace.

    A namespace that already holds anything is refused outright rather than
    silently accepted: a pre-populated "fresh" cache is exactly the controlled
    poisoning the review requires to fail closed.
    """

    resolved = Path(directory).resolve()
    resolved.mkdir(parents=True, exist_ok=True)
    existing = sorted(entry.name for entry in resolved.iterdir())
    if existing:
        raise IsolatedScientificWorkerR1Error(
            f"bytecode cache namespace {str(resolved)!r} is not fresh: "
            f"{existing[:8]!r}"
        )
    return resolved


def allocate_worker_pycache_namespace(base: Path | None = None) -> Path:
    root = controller_pycache_root() if base is None else Path(base)
    root.mkdir(parents=True, exist_ok=True)
    return create_fresh_pycache_namespace(
        Path(tempfile.mkdtemp(dir=str(root), prefix="worker-"))
    )


def interpreter_base_sys_path(executable: str) -> tuple[str, ...]:
    """Ask the exact frozen interpreter for its own controlled base path."""

    cached = _BASE_SYS_PATH_CACHE.get(executable)
    if cached is not None:
        return cached
    completed = subprocess.run(
        [
            executable,
            "-I",
            "-S",
            "-B",
            "-c",
            "import sys,json;print(json.dumps(sys.path))",
        ],
        capture_output=True,
        check=True,
        env=dict(FROZEN_WORKER_ENVIRONMENT),
        timeout=protocol.DEFAULT_TIMEOUT_SECONDS,
    )
    entries = tuple(json.loads(completed.stdout.decode("ascii")))
    _BASE_SYS_PATH_CACHE[executable] = entries
    return entries


def parent_site_paths() -> tuple[str, ...]:
    """The parent-bound third-party import locations handed to the worker."""

    paths = sysconfig.get_paths()
    ordered: list[str] = []
    for key in ("purelib", "platlib"):
        candidate = paths.get(key)
        if candidate and candidate not in ordered and Path(candidate).is_dir():
            ordered.append(candidate)
    return tuple(ordered)


@dataclass(frozen=True)
class WorkerLaunch:
    """Fully parent-bound launch material for one scientific worker process."""

    executable: str
    project_root: Path
    sys_path: tuple[str, ...]
    entrypoint: Path
    cwd: Path
    pycache_namespace_root: Path
    mechanism: str = EXEC_LAUNCH
    timeout_seconds: int = protocol.DEFAULT_TIMEOUT_SECONDS
    environment: Mapping[str, str] = field(
        default_factory=lambda: dict(FROZEN_WORKER_ENVIRONMENT)
    )

    def argv_for(self, pycache_namespace: Path) -> tuple[str, ...]:
        return (
            self.executable,
            *WORKER_LAUNCH_FLAGS,
            "-X",
            f"{WORKER_LAUNCH_X_OPTION}={Path(pycache_namespace).resolve()}",
            str(self.entrypoint),
            json.dumps(list(self.sys_path)),
            str(Path(pycache_namespace).resolve()),
        )


def worker_launch(
    project_root: Path = PROJECT_ROOT,
    *,
    executable: str | None = None,
    extra_sys_path: Sequence[str] = (),
    timeout_seconds: int = protocol.DEFAULT_TIMEOUT_SECONDS,
    mechanism: str = EXEC_LAUNCH,
    pycache_namespace_root: Path | None = None,
) -> WorkerLaunch:
    authorize_worker_launch_mechanism(mechanism)
    interpreter = executable or sys.executable
    base = interpreter_base_sys_path(interpreter)
    entries = [
        *extra_sys_path,
        *base,
        str(project_root),
        *parent_site_paths(),
    ]
    deduplicated: list[str] = []
    for entry in entries:
        if entry not in deduplicated:
            deduplicated.append(entry)
    return WorkerLaunch(
        executable=interpreter,
        project_root=project_root,
        sys_path=tuple(deduplicated),
        entrypoint=project_root / WORKER_ENTRYPOINT_RELATIVE_PATH,
        cwd=project_root,
        pycache_namespace_root=(
            controller_pycache_root()
            if pycache_namespace_root is None
            else Path(pycache_namespace_root)
        ),
        mechanism=mechanism,
        timeout_seconds=timeout_seconds,
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

    There is deliberately no ``decision_sha256`` parameter and no manifest
    parameter.  A caller cannot select scientific authority, and the builder
    never re-derives the certified source manifest or the third-party registry
    from live material: source drift that exists before request construction
    cannot self-certify, because the request still carries the frozen expected
    values and the worker then refuses the drifted disk.
    """

    if not isinstance(authority_context, ScientificWorkerAuthorityContext):
        raise IsolatedScientificWorkerR1Error(
            "a scientific request requires a trusted controller authority context"
        )
    expected = authority_context.expected_authority_fields()
    observations = observe_installed_distributions(
        authority_context.third_party_authority
    )
    return {
        "request_schema_version": protocol.REQUEST_SCHEMA_VERSION,
        "worker_authority_version": expected["worker_authority_version"],
        "worker_authority_ticket": expected["worker_authority_ticket"],
        "worker_authority_sha256": expected["worker_authority_sha256"],
        "authority_context_origin": authority_context.origin,
        "calendar_authority_version": expected["calendar_authority_version"],
        "calendar_authority_sha256": expected["calendar_authority_sha256"],
        "trusted_persistence_authority_sha256": expected[
            "trusted_persistence_authority_sha256"
        ],
        "interpreter_identity": dict(expected["interpreter_identity"]),
        "project_root": str(launch.project_root),
        "sys_path": list(launch.sys_path),
        "worker_entrypoint_module": expected["worker_entrypoint_module"],
        "worker_entrypoint_sha256": expected["worker_entrypoint_sha256"],
        "worker_protocol_sha256": expected["worker_protocol_sha256"],
        "project_source_manifest": [
            entry.as_material() for entry in authority_context.project_source_manifest
        ],
        "project_source_manifest_digest": expected["project_source_manifest_digest"],
        "project_source_manifest_role": expected["project_source_manifest_role"],
        "required_project_modules": list(authority_context.required_project_modules),
        "third_party_authority": [
            entry.as_material() for entry in authority_context.third_party_authority
        ],
        "third_party_authority_digest": expected["third_party_authority_digest"],
        "third_party_environment": [
            entry.as_material() for entry in observations
        ],
        "decision_time": decision_time,
        "operation": operation,
        "evidence_admission_mode": evidence_admission_mode,
        "evidence_records": [dict(record) for record in evidence_records],
        "operation_inputs": dict(operation_inputs),
    }


# ---------------------------------------------------------------------------
# Controller: launch, observe, admit
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WorkerProcessOutcome:
    """Everything the controller observed about one worker process."""

    exit_status: int | None
    timed_out: bool
    stdout: bytes
    stderr: bytes
    request_digest: str

    @property
    def clean_termination(self) -> bool:
        return self.exit_status == 0 and not self.timed_out


@dataclass(frozen=True)
class AdmissionOutcome:
    """The controller's admission decision for one scientific worker result."""

    admitted: bool
    failure_reason: str | None
    response: Mapping[str, Any] | None
    outcome: WorkerProcessOutcome
    result: Any = None


def run_scientific_worker(
    request: Mapping[str, Any],
    launch: WorkerLaunch,
    *,
    pycache_namespace: Path | None = None,
) -> WorkerProcessOutcome:
    """Exec one fresh interpreter in a fresh cache namespace, serve one request.

    A new, empty, controller-created bytecode-cache namespace is allocated for
    every launch and removed afterwards, so no namespace is ever shared between
    workers or with the repository's own ``__pycache__`` directories.
    """

    authorize_worker_launch_mechanism(launch.mechanism)
    payload = protocol.canonical_json_bytes(request)
    if len(payload) > protocol.MAX_REQUEST_BYTES:
        raise IsolatedScientificWorkerR1Error(
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
        return WorkerProcessOutcome(
            exit_status=None,
            timed_out=True,
            stdout=expired.stdout or b"",
            stderr=expired.stderr or b"",
            request_digest=digest,
        )
    finally:
        if owned:
            shutil.rmtree(namespace, ignore_errors=True)
    return WorkerProcessOutcome(
        exit_status=completed.returncode,
        timed_out=False,
        stdout=completed.stdout,
        stderr=completed.stderr,
        request_digest=digest,
    )


def verify_request_against_authority_context(
    authority_context: ScientificWorkerAuthorityContext,
    request: Mapping[str, Any],
) -> tuple[str, ...]:
    """Every material authority field of the request must be the trusted one."""

    expected = authority_context.expected_authority_fields()
    mismatched = sorted(
        name
        for name in protocol.AUTHORITY_BOUND_REQUEST_FIELDS
        if request.get(name) != expected[name]
    )
    if request.get("project_source_manifest") != [
        entry.as_material() for entry in authority_context.project_source_manifest
    ]:
        mismatched = sorted({*mismatched, "project_source_manifest"})
    if request.get("third_party_authority") != [
        entry.as_material() for entry in authority_context.third_party_authority
    ]:
        mismatched = sorted({*mismatched, "third_party_authority"})
    if request.get("authority_context_origin") != authority_context.origin:
        mismatched = sorted({*mismatched, "authority_context_origin"})
    return tuple(mismatched)


def verify_response_against_authority_context(
    authority_context: ScientificWorkerAuthorityContext,
    response: Mapping[str, Any],
) -> tuple[str, ...]:
    """Every material authority field of the response must be the trusted one."""

    expected = authority_context.expected_authority_fields()
    return tuple(
        sorted(
            name
            for name in protocol.AUTHORITY_BOUND_RESPONSE_FIELDS
            if response.get(name) != expected[name]
        )
    )


def admit_worker_result(
    authority_context: ScientificWorkerAuthorityContext,
    request: Mapping[str, Any],
    outcome: WorkerProcessOutcome,
) -> AdmissionOutcome:
    """Admit a result only when request, response and trusted context agree.

    ``PAD4`` compared the response echo with the request and called that a
    binding.  Caller, request and worker agreeing with each other is necessary
    but never sufficient: the request must agree with the trusted controller
    authority context, the response must agree with that same context, and the
    response must cross-bind to the request.
    """

    def refuse(
        reason: str, response: Mapping[str, Any] | None = None
    ) -> AdmissionOutcome:
        return AdmissionOutcome(False, reason, response, outcome)

    drifted = verify_request_against_authority_context(authority_context, request)
    if drifted:
        return refuse(f"REQUEST_AUTHORITY_MISMATCH:{list(drifted)!r}")
    if outcome.timed_out:
        return refuse("WORKER_TIMEOUT")
    if outcome.exit_status != 0:
        return refuse(f"WORKER_EXIT_STATUS_{outcome.exit_status}")
    if len(outcome.stdout) > protocol.MAX_RESPONSE_BYTES:
        return refuse("WORKER_OUTPUT_EXCEEDS_THE_FROZEN_LIMIT")
    if not outcome.stdout.endswith(b"\n") or outcome.stdout.count(b"\n") != 1:
        return refuse("WORKER_STDOUT_IS_NOT_EXACTLY_ONE_PROTOCOL_PAYLOAD")
    try:
        parsed = protocol.validate_response(
            protocol.parse_canonical_json(outcome.stdout[:-1])
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
        "request_digest": outcome.request_digest,
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
    if parsed["sys_path_digest"] != protocol.digest_payload(list(request["sys_path"])):
        return refuse("WORKER_SYS_PATH_MISMATCH", parsed)
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
    return AdmissionOutcome(True, None, parsed, outcome, parsed["result"])


def run_isolated_scientific_request(
    authority_context: ScientificWorkerAuthorityContext,
    request: Mapping[str, Any],
    launch: WorkerLaunch,
    *,
    pycache_namespace: Path | None = None,
) -> AdmissionOutcome:
    return admit_worker_result(
        authority_context,
        request,
        run_scientific_worker(request, launch, pycache_namespace=pycache_namespace),
    )


def scientific_response_evidence(
    authority_context: ScientificWorkerAuthorityContext, admission: AdmissionOutcome
) -> dict[str, Any]:
    """Deterministic, address-free evidence for one scientific worker decision."""

    response = admission.response or {}
    evidence = {
        "trusted_authority_context": authority_context.as_evidence(),
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
        "request_digest": admission.outcome.request_digest,
        "operation": response.get("operation"),
        "result_digest": response.get("result_digest"),
        "process_exit_status": admission.outcome.exit_status,
        "process_timed_out": admission.outcome.timed_out,
        "admitted": admission.admitted,
        "failure_reason": admission.failure_reason,
        "decision_time": response.get("decision_time"),
    }
    protocol.assert_address_free(evidence)
    return evidence


# ---------------------------------------------------------------------------
# Preserved static authority
# ---------------------------------------------------------------------------


def compiled_root_binding_witness(source: str) -> witness.CompiledBindingWitness:
    return attestation.compiled_root_binding_witness(source)


def direct_dependency_body_findings(source: str) -> dict[str, Any]:
    return attestation.direct_dependency_body_findings(source)


def verify_current_production_expected_result(source: str) -> dict[str, Any]:
    """The preserved current-production claim, freshly bound under this parent."""

    produced = dict(pad4.verify_current_production_expected_result(source))
    produced["isolated_scientific_worker_implemented_in_production"] = False
    produced["corrected_worker_integrated_in_production"] = False
    produced["calendar_production_conformance"] = "NO"
    produced["calendar_implementation"] = "BLOCKED"
    return produced


def audit_authoritative_worker_source(
    project_root: Path = PROJECT_ROOT,
) -> dict[str, Any]:
    """The corrected worker-owned modules must be closed against project code."""

    findings: list[str] = []
    identities: dict[str, str] = {}
    for relative in protocol.AUTHORITATIVE_WORKER_SOURCE:
        path = project_root / relative
        source = path.read_text(encoding="utf-8")
        identities[relative] = witness.source_sha256(source)
        findings.extend(pad4.dynamic_import_findings(source, relative))
    if findings:
        raise IsolatedScientificWorkerR1Error(
            f"authoritative scientific worker source is not closed: {findings!r}"
        )
    return {
        "authoritative_worker_source": list(protocol.AUTHORITATIVE_WORKER_SOURCE),
        "source_sha256": dict(sorted(identities.items())),
        "findings": [],
        "closed": True,
    }


def certified_universe_closed_worker_rule_modules(
    project_root: Path = PROJECT_ROOT,
    entries: Sequence[protocol.ProjectSourceEntry] | None = None,
) -> tuple[str, ...]:
    """Certified modules containing a construct the closed worker rule forbids.

    The scan covers exactly what that rule covers: the dynamic execution
    callables, the forbidden import roots — which include ordinary network and
    database client modules — and the process-spawning ``os`` capabilities.  A
    hit is therefore *not* by itself evidence of a dynamic project import; most
    are the network- and database-capable modules the current package
    re-export graph drags into the certified universe.

    This is recorded as a *verified current-source fact* about the present
    universe, never as an eternal universal claim that every certified module
    is free of every dynamic import mechanism.  Enforcement is the statically
    audited authoritative worker source plus the ``UNEXPECTED_PROJECT_MODULE``
    refusal, not this list.
    """

    manifest = frozen_candidate_source_manifest() if entries is None else entries
    found: list[str] = []
    for entry in manifest:
        source = (project_root / entry.path).read_text(encoding="utf-8")
        if pad4.dynamic_import_findings(source, entry.module):
            found.append(entry.module)
    return tuple(sorted(found))


# ---------------------------------------------------------------------------
# Material children
# ---------------------------------------------------------------------------


def trusted_process_and_isolation_boundary() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_TRUSTED_PROCESS_AND_ISOLATION_BOUNDARY_V1_PAD4_R1"
            ),
            "scientific_execution_boundary": "OPERATING_SYSTEM_PROCESS",
            "process_isolation_is_scientific_execution_boundary": True,
            "isolation_boundary_preserved_from_the_reviewed_pad4_candidate": True,
            "isolation_boundary_was_the_defect": False,
            "runtime_object_closure_is_completeness_proof": False,
            "abandoned_completeness_models": list(NOT_REOPENED),
            "reopened_by_this_correction": [],
            "closed_input_boundary": [
                "CANONICAL_JSON_IPC",
                "CONTROLLER_RESULT_ADMISSION",
                "FORK_ONLY_REFUSAL",
                "FRESH_EXEC_CPYTHON_WORKER",
                "ISOLATED_NO_SITE_NO_BYTECODE_WRITE_STARTUP",
                "LAZY_RESULT_REFUSAL",
                "NO_PARENT_PYTHON_OBJECT_SHARING",
                "NO_PICKLE_CLOUDPICKLE_DILL_MARSHAL_IPC",
                "ONE_REQUEST_ONE_PROCESS",
                "PARENT_MONKEYPATCH_ISOLATION",
            ],
            "worker_trusted_after_admission": True,
            "trusted_once": [
                "CERTIFIED_PROJECT_SOURCE_ADMISSION_PASSES",
                "CERTIFIED_THIRD_PARTY_INSTALLED_CONTENT_ADMISSION_PASSES",
                "FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE_PASSES",
                "FROZEN_INTERPRETER_IDENTITY_PASSES",
            ],
            "out_of_scope": [
                "HOSTILE_DEBUGGER_ATTACHMENT",
                "KERNEL_COMPROMISE",
                "MALICIOUS_MODIFICATION_PERFECTLY_RACING_VERIFICATION_OR_USE",
                "OPERATING_SYSTEM_MEMORY_INJECTION",
            ],
            "hostile_filesystem_race_resistance_claimed": False,
            "accepted_race_boundary": (
                "a malicious modification perfectly racing verification or use is "
                "outside the accepted trusted-operating-system boundary; the "
                "requirement is deterministic project and deployment integrity, "
                "not hostile kernel defence"
            ),
            "hostile_operating_system_resistance_claimed": False,
            "certified_source_may_mutate_its_own_globals": True,
            "certified_self_mutation_is_program_behavior_not_ambient_drift": True,
            "demoted_pad3_runtime_closure": dict(pad4.DEMOTED_PAD3_RUNTIME_CLOSURE),
            "demoted_pad3_runtime_closure_role": "ARCHIVED_DIAGNOSTIC_EVIDENCE",
        }
    )


def proof_interpreter_identity() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_PROOF_INTERPRETER_IDENTITY_V1_PAD4_R1",
            "frozen_identity": dict(
                verify_worker_protocol_binds_the_frozen_interpreter()
            ),
            "identity_fields": sorted(PROOF_INTERPRETER_IDENTITY),
            "worker_and_controller_share_one_identity_authority": True,
            "worker_identity_restatement_is_mechanically_bound": True,
            "mismatch": "REFUSE_SCIENTIFIC_AUTHORITY",
            "verified_before_any_scientific_call": True,
            "standard_library_semantics_rely_on_this_axiom": True,
            "stdlib_python_objects_recursively_attested": False,
            "stdlib_boundary_is_an_explicit_architecture_axiom": True,
            "future_python_upgrade": "REQUIRES_EXPLICIT_REVIEW_AND_REFREEZE",
            "different_python_interpreter_may_reuse_this_authority": False,
        }
    )


def worker_launch_contract() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": WORKER_LAUNCH_CONTRACT,
            "launch": "EXEC_STYLE_LAUNCH_OF_THE_EXACT_FROZEN_INTERPRETER",
            "authorized_mechanisms": list(AUTHORIZED_LAUNCH_MECHANISMS),
            "unauthorized_mechanisms": list(UNAUTHORIZED_LAUNCH_MECHANISMS),
            "fork_only_worker_permitted": False,
            "fresh_interpreter": True,
            "fresh_sys_modules": True,
            "fresh_project_imports": True,
            "inherited_parent_python_module_objects": False,
            "worker_reuse_permitted": False,
            "long_lived_worker_permitted": False,
            "one_request_one_exec_process": True,
            "process_exits_after_response": True,
            "worker_concurrency": "ONE_SYNCHRONOUS_REQUEST_NO_BACKGROUND_THREAD",
            "scientific_background_thread_permitted": False,
            "async_scientific_continuation_permitted": False,
            "nested_scientific_job_permitted": False,
            "launcher_flags": list(WORKER_LAUNCH_FLAGS),
            "launcher_x_options": [WORKER_LAUNCH_X_OPTION],
            "launcher_flag_effects": dict(
                sorted(protocol.REQUIRED_INTERPRETER_FLAGS.items())
            ),
            "fresh_empty_pycache_namespace_required": True,
            "pycache_namespace_is_operational_launch_material": True,
            "pycache_namespace_is_scientific_identity_evidence": False,
            "pycache_namespace_selected_by_the_scientific_request": False,
            "environment_variable_python_configuration_ignored": True,
            "user_site_disabled": True,
            "sitecustomize_and_usercustomize_executed": False,
            "uncontrolled_current_directory_import_precedence": False,
            "sys_path_explicitly_parent_controlled": True,
            "ambient_pythonpath_dependency": False,
            "frozen_child_environment": dict(sorted(FROZEN_WORKER_ENVIRONMENT.items())),
            "parent_environment_drift_after_startup_reaches_the_child": False,
            "child_working_directory": "PARENT_BOUND_PROJECT_ROOT",
            "performance_subordinate_to_proof_simplicity": True,
            "resource_limits": {
                "max_request_bytes": protocol.MAX_REQUEST_BYTES,
                "max_response_bytes": protocol.MAX_RESPONSE_BYTES,
                "timeout_seconds": protocol.DEFAULT_TIMEOUT_SECONDS,
                "timeout_or_crash": "NO_SCIENTIFIC_RESULT_ADMISSION",
                "silent_retry_on_a_different_authority_path": False,
            },
        }
    )


def bytecode_execution_binding_rule() -> dict[str, Any]:
    """Repair A — executed bytecode is bound to certified source."""

    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_WORKER_BYTECODE_EXECUTION_BINDING_RULE_V1_PAD4_R1"
            ),
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[0],
            "defect": (
                "-B prevents cached bytecode writes but does not prevent cached "
                "bytecode reads; a forged timestamp-valid "
                "__pycache__/flow.cpython-312.pyc executed while the certified "
                ".py source SHA-256 was unchanged"
            ),
            "repair": protocol.BYTECODE_CACHE_NAMESPACE_RULE,
            "mechanism": protocol.BYTECODE_CACHE_NAMESPACE_MECHANISM,
            "interpreter_option": f"-X {WORKER_LAUNCH_X_OPTION}=<fresh_empty_dir>",
            "additional_flags": list(WORKER_LAUNCH_FLAGS),
            "fresh_cache_namespace_per_worker": True,
            "empty_before_launch": True,
            "shared_with_repository_pycache": False,
            "reused_between_workers": False,
            "caller_selected_from_the_scientific_request": False,
            "controller_created": True,
            "removed_after_the_worker_exits": True,
            "repository_pycache_authoritative": False,
            "cached_bytecode_may_override_certified_source": False,
            "worker_verifies_before_project_imports": [
                "sys.pycache_prefix == controller-declared operational cache prefix",
                "sys.dont_write_bytecode is True",
                "the declared cache namespace exists and is empty",
            ],
            "worker_verification_is_duplicated_in_the_entrypoint": True,
            "worker_verification_duplication_reason": (
                "the check must pass before even the certified protocol module is "
                "imported, otherwise a forged protocol bytecode cache entry would "
                "be the thing deciding whether the cache namespace is trustworthy"
            ),
            "entrypoint_bytecode_is_never_cached": True,
            "entrypoint_bytecode_reason": (
                "a worker entrypoint executes as __main__ from its source path, "
                "which CPython never serves from a bytecode cache"
            ),
            "failure": protocol.REFUSE_SCIENTIFIC_AUTHORITY,
            "loaded_module_cached_path_must_be_inside_the_namespace": True,
            "loaded_module_origin_must_be_the_certified_py_source": True,
            "sourceless_or_wrong_origin_project_module": "REFUSE",
            "applies_to_third_party_modules": True,
            "third_party_cached_bytecode_may_override_verified_source": False,
            "install_generated_site_packages_pyc_is_authoritative": False,
            "hostile_filesystem_race_resistance_claimed": False,
        }
    )


def controller_authority_context_rule() -> dict[str, Any]:
    """Repair C — the trusted controller authority context."""

    version, calendar_sha, persistence_sha = _calendar_identity()
    return _definition(
        {
            "contract_version": AUTHORITY_CONTEXT_VERSION,
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[2],
            "defect": (
                "the worker echoed the request decision hash and admission "
                "compared that echo with the same request value, so requests "
                "declaring 0000...0000 and deadbeef...deadbeef were admitted "
                "with a real scientific result"
            ),
            "trusted_controller_authority_context_required": True,
            "authority_context_origins": list(AUTHORITY_CONTEXT_ORIGINS),
            "trusted_expected_values": [
                "calendar_authority_identity",
                "certified_project_source_manifest",
                "certified_project_source_manifest_digest",
                "certified_third_party_semantic_and_artifact_authority",
                "certified_worker_proof_architecture_identity",
                "frozen_interpreter_identity",
                "trusted_persistence_identity",
            ],
            "request_can_construct_the_authority_context": False,
            "response_can_construct_the_authority_context": False,
            "live_disk_can_silently_replace_the_authority_context": False,
            "installed_environment_can_silently_replace_the_authority_context": False,
            "request_is_authority_root": False,
            "response_echo_is_authority_root": False,
            "raw_caller_supplied_decision_hash_parameter": False,
            "request_authority_fields_are_copied_from_the_trusted_context": True,
            "authority_bound_request_fields": list(
                protocol.AUTHORITY_BOUND_REQUEST_FIELDS
            ),
            "authority_bound_response_fields": list(
                protocol.AUTHORITY_BOUND_RESPONSE_FIELDS
            ),
            "self_hash_fixed_point_attempted": False,
            "self_hash_circularity_acknowledged": (
                "the candidate parent hash cannot be materially embedded inside "
                "itself; the architecture uses a two-stage boundary instead"
            ),
            "candidate_review_context_binds_the_recomputed_parent_hash": True,
            "candidate_review_context_expected_hash_source": (
                "TRUSTED_REVIEW_OR_CONTROLLER_CONTEXT_NEVER_THE_SCIENTIFIC_REQUEST"
            ),
            "final_production_context_source": FINAL_CALENDAR_AUTHORITY,
            "final_production_context_may_come_from": [FINAL_CALENDAR_AUTHORITY],
            "final_production_context_may_never_come_from": [
                "AMBIENT_ENVIRONMENT",
                "CALLER_SELECTED_SHA",
                "CURRENT_FILESYSTEM",
                "THE_SCIENTIFIC_REQUEST",
            ],
            "final_i2_certified_hash_binding_required": True,
            "final_i2_certified_hash_binding_ticket": "POSTP1-001V2A-I2",
            "final_calendar_authority_worker_field": (
                FINAL_CALENDAR_AUTHORITY_WORKER_FIELD
            ),
            "production_authority_context_available_today": False,
            "production_authority_context_refusal": PRODUCTION_CONTEXT_NOT_YET_BOUND,
            "calendar_authority_version": version,
            "calendar_authority_sha256": calendar_sha,
            "trusted_persistence_authority_sha256": persistence_sha,
            "caller_request_worker_agreement_is_sufficient": False,
            "agreement_with_trusted_controller_authority_also_required": True,
        }
    )


def project_source_manifest_binding_rule() -> dict[str, Any]:
    """Repair B — frozen source authority, consumed and never re-derived."""

    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_WORKER_PROJECT_SOURCE_MANIFEST_BINDING_RULE_V1_PAD4_R1"
            ),
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[1],
            "defect": (
                "request construction derived the manifest from whatever source "
                "was on disk, put it into the request and verified the worker "
                "against that same newly derived manifest, so source drift that "
                "existed before request construction self-certified"
            ),
            "manifest_version": WORKER_SOURCE_MANIFEST_VERSION,
            "two_distinct_operations": {
                "AUTHORITY_CONSTRUCTION_OR_REFREEZE": (
                    "derive the exact source manifest from reviewed source"
                ),
                "RUNTIME": (
                    "consume an already-frozen expected source manifest"
                ),
            },
            "runtime_source_manifest_rederivation_permitted": False,
            "runtime_request_construction_derives_authority_from_live_disk": False,
            "derivation_rule": (
                "RECURSIVE_STATIC_PROJECT_IMPORT_CLOSURE_FROM_THE_SCIENTIFIC_"
                "WORKER_ENTRYPOINT"
            ),
            "mechanically_derivable": True,
            "nested_declaration_imports_followed": True,
            "ancestor_packages_included": True,
            "hand_maintained_helper_constant_or_class_list": False,
            "mechanical_derivation_is_used_for": [
                "AUTHORITY_CONSTRUCTION",
                "CONSISTENCY_CHECKING",
                "REFREEZE",
                "REVIEW",
            ],
            "mechanical_derivation_is_used_for_runtime_authority_selection": False,
            "certified_package_roots": list(CERTIFIED_PACKAGE_ROOTS),
            "bound_per_entry": [
                "canonical_module_name",
                "canonical_source_path",
                "sha256",
            ],
            "runtime_comparison_is_exact": [
                "manifest_digest",
                "module",
                "relative_path",
                "sha256",
            ],
            "unknown_entry": "REFUSE",
            "missing_entry": "REFUSE",
            "additional_entry": "REFUSE",
            "altered_entry": "REFUSE",
            "unexpected_project_module": "REFUSE",
            "wrong_project_module_origin": "REFUSE",
            "verified_before_scientific_execution": True,
            "verified_again_before_emitting_a_successful_result": True,
            "post_execution_verification_is_defence_in_depth": True,
            "post_execution_verification_attests_every_runtime_object": False,
            "project_runtime_objects_are_freshly_constructed_from_certified_source": (
                True
            ),
            "generated_runtime_methods_hand_fingerprinted": False,
            "source_change_altering_a_generated_class": (
                "CHANGES_THE_MANIFEST_AND_REQUIRES_REFREEZE"
            ),
            "final_i2_source_manifest_must_be_calendar_parent_bound": True,
            "final_i2_source_manifest_owner": "POSTP1-001V2A-I2",
            "final_i2_source_manifest_parent": "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1",
            "final_i2_source_manifest_derivation_time": (
                "AFTER_ALL_I2_SOURCE_CHANGES_ARE_COMPLETE"
            ),
            "i2_may_narrow_the_source_universe": True,
            "i2_direct_import_reduction_requirements": [
                "FINAL_EXACT_MANIFEST_PARENT_BOUND_TO_THE_CALENDAR_AUTHORITY",
                "SAME_CALENDAR_SCIENCE",
                "SAME_OUTPUTS",
                "SAME_REPLAY_OWNER_GRAPH",
                "SOURCE_MANIFEST_MECHANICALLY_REDERIVED",
            ],
            "proof_architecture_hash_changes_when_production_manifest_narrows": (
                False
            ),
        }
    )


def pre_i2_project_source_manifest_fixture() -> dict[str, Any]:
    """The reviewed pre-I2 source universe, frozen as provenance not authority."""

    fixture = frozen_pre_i2_source_manifest()
    candidate = frozen_candidate_source_manifest()
    verify_frozen_pre_i2_fixture()
    return _definition(
        {
            "contract_version": PRE_I2_FIXTURE_VERSION,
            "role": PRE_I2_FIXTURE_ROLE,
            "roles": [
                "ARCHITECTURE_CONFORMANCE_TEST_VECTOR",
                "PRE_I2_SOURCE_DRIFT_REGRESSION_ANCHOR",
                "PROVENANCE",
            ],
            "is_final_production_scientific_source_authority": False,
            "immutable_when_i2_later_changes_source": True,
            "i2_will_change_at_least": [
                "btc_predictor/research/etf_publication_calendar.py"
            ],
            "reviewed_pre_i2_source_universe": {
                "seed_entrypoint": PRE_I2_FIXTURE_SEED_MODULE,
                "module_count": len(fixture),
                "manifest_digest": protocol.manifest_digest(fixture),
                "entries": [entry.as_material() for entry in fixture],
            },
            "candidate_worker_source_universe": {
                "seed_entrypoint": WORKER_ENTRYPOINT_MODULE,
                "module_count": len(candidate),
                "manifest_digest": protocol.manifest_digest(candidate),
                "entries": [entry.as_material() for entry in candidate],
            },
            "required_loaded_modules": list(REQUIRED_WORKER_PROJECT_MODULES),
            "future_production_source_manifest_role": (
                "I2_DERIVED_AND_FINAL_CALENDAR_PARENT_BOUND"
            ),
            "package_reexport_direct_import_reduction": (
                "PERMITTED_IN_I2_NOT_IN_THIS_TICKET"
            ),
        }
    )


def third_party_semantic_authority() -> dict[str, Any]:
    """Repair D, part one — exact reviewed semantic and artifact identity."""

    authorities = frozen_third_party_authority()
    return _definition(
        {
            "contract_version": THIRD_PARTY_REGISTRY_VERSION,
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[3],
            "defect": (
                "the declared version was never compared to anything, so a "
                "manifest declaring 99.99.99-FORGED for every distribution was "
                "admitted and no reviewed semantic dependency authority existed"
            ),
            "third_party_exact_reviewed_versions_required": True,
            "third_party_reviewed_artifact_identity_required": True,
            "arbitrary_installed_version_self_certification_permitted": False,
            "arbitrary_site_packages_state_is_scientific_authority": False,
            "observed_version_differs_from_the_frozen_reviewed_version": "REFUSE",
            "caller_declared_version_may_become_authority": False,
            "same_version_different_unreviewed_artifact_is_authorized": False,
            "parent_bound_material": [
                "distribution",
                "expected_root_modules",
                "reviewed_record_artifact_identity",
                "reviewed_record_content_manifest_identity",
                "version",
            ],
            "launch_bound_material": [
                "absolute_installation_location",
                "absolute_record_path",
                "installation_environment_root",
            ],
            "environment_portability_rule": (
                "install location may remain machine-specific launch material; "
                "scientific semantic authority may not"
            ),
            "reviewed_distribution_count": len(authorities),
            "reviewed_distributions": [
                entry.as_material() for entry in authorities
            ],
            "observed_version_source": [
                "INSTALLED_DIST_INFO_DIRECTORY_NAME",
                "INSTALLED_METADATA_NAME_AND_VERSION_HEADERS",
            ],
            "observed_version_is_record_hash_bound": True,
            "new_unreviewed_distribution": "REQUIRES_EXPLICIT_REVIEW_AND_REFREEZE",
            "new_version": "REQUIRES_EXPLICIT_REVIEW_AND_REFREEZE",
            "new_artifact_identity": "REQUIRES_EXPLICIT_REVIEW_AND_REFREEZE",
            "i2_final_dependency_set_may_be_a_subset": True,
            "i2_final_dependency_set_may_add_unreviewed_material": False,
            "loaded_dependency_must_resolve_inside_the_verified_location": True,
            "stdlib_modules_recursively_attested": False,
        }
    )


def third_party_installed_content_attestation_rule() -> dict[str, Any]:
    """Repair D, part two — installed file bytes are verified against RECORD."""

    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_WORKER_THIRD_PARTY_INSTALLED_CONTENT_RULE_V1_PAD4_R1"
            ),
            "repaired_review_finding": REPAIRED_REVIEW_FINDINGS[3],
            "defect": (
                "verification hashed only the RECORD file and never checked any "
                "installed file against the per-file hashes RECORD declares, so "
                "a tampered dependency file executed with RECORD unchanged"
            ),
            "record_declared_installed_file_hashes_must_be_verified": True,
            "verification_precedes_dependency_execution": True,
            "verification_order_is_critical": True,
            "forbidden_sequence": "IMPORT_DEPENDENCIES_THEN_VERIFY_THEIR_FILES",
            "worker_protocol_lives_outside_the_application_package": True,
            "worker_protocol_placement_reason": (
                "importing btc_predictor executes numpy, scipy, sqlalchemy and "
                "alembic through the package re-export graph, so a protocol "
                "module under btc_predictor could only attest dependencies after "
                "they had already executed"
            ),
            "record_parsing": "BOUNDED_DETERMINISTIC_CSV_ROWS",
            "record_row_shape": "path,algorithm=base64,size",
            "accepted_hash_algorithms": list(
                protocol.ACCEPTED_RECORD_HASH_ALGORITHMS
            ),
            "unknown_hash_algorithm": "REFUSE",
            "unknown_hash_algorithm_silently_skipped": False,
            "per_row_verification": [
                "COMPARE_DECLARED_SIZE_WHERE_AVAILABLE",
                "COMPUTE_THE_DECLARED_HASH_OVER_THE_INSTALLED_BYTES",
                "READ_THE_INSTALLED_BYTES",
                "RESOLVE_THE_INSTALLED_FILE",
            ],
            "covers_compiled_native_extension_and_shared_library_rows": True,
            "verifies_only_python_source": False,
            "declared_file_missing": "REFUSE",
            "content_mismatch": protocol.NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            "size_mismatch": protocol.NON_CERTIFIED_DEPENDENCY_ENVIRONMENT,
            "reviewed_unhashed_row_exceptions": {
                protocol.RECORD_SELF_REFERENTIAL_EXCEPTION: (
                    "the distribution's own RECORD cannot hash itself; it is the "
                    "explicitly reviewed self-referential exception and its exact "
                    "bytes are parent-bound as reviewed artifact identity"
                ),
                protocol.RECORD_INSTALL_GENERATED_BYTECODE_EXCEPTION: (
                    "install-generated __pycache__ bytecode is never consulted, "
                    "because every worker runs in a fresh empty bytecode-cache "
                    "namespace; the exception is conditional on that enforced "
                    "structural property, not on silence"
                ),
            },
            "any_other_unhashed_installed_file": "REFUSE",
            "missing_hashes_silently_treated_as_certified": False,
            "record_path_semantics": [
                "ABSOLUTE_PATH_REFUSED",
                "AMBIGUOUS_OR_INTERIOR_TRAVERSAL_REFUSED",
                "LEADING_PARENT_SEGMENTS_PERMITTED_FOR_CONSOLE_SCRIPT_ROWS",
                "RESOLUTION_MUST_STAY_INSIDE_THE_INSTALLATION_ENVIRONMENT",
                "WINDOWS_SEPARATOR_REFUSED",
            ],
            "scientific_authority_inferred_from_arbitrary_absolute_caller_paths": (
                False
            ),
            "request_may_carry_observed_environment_material": True,
            "request_agreement_with_itself_is_authority": False,
            "worker_compares_semantic_identity_against_the_trusted_registry": True,
            "controller_compares_response_against_the_trusted_registry": True,
            "persisted_evidence": [
                "distribution",
                "observed_verified_content_manifest_digest",
                "reviewed_record_artifact_digest",
                "reviewed_version",
            ],
            "installation_memory_addresses_in_evidence": False,
            "absolute_machine_paths_are_scientific_evidence": False,
            "hostile_filesystem_race_resistance_claimed": False,
        }
    )


def dynamic_import_and_execution_prohibition() -> dict[str, Any]:
    audit = audit_authoritative_worker_source()
    flagged_modules = certified_universe_closed_worker_rule_modules()
    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_WORKER_DYNAMIC_IMPORT_PROHIBITION_V1_PAD4_R1"
            ),
            "scope": "AUTHORITATIVE_SCIENTIFIC_WORKER_SOURCE",
            "authoritative_worker_source": list(audit["authoritative_worker_source"]),
            "authoritative_worker_source_sha256": dict(audit["source_sha256"]),
            "authoritative_worker_dynamic_project_execution": (
                "FORBIDDEN_AND_STATICALLY_AUDITED"
            ),
            "certified_source_universe_derivation": (
                "MECHANICALLY_DERIVED_FROM_STATIC_IMPORT_DECLARATIONS"
            ),
            "unexpected_loaded_project_module": "REFUSE",
            "forbidden_callables": list(pad4.FORBIDDEN_WORKER_CALLABLES),
            "forbidden_import_roots": list(pad4.FORBIDDEN_WORKER_IMPORT_ROOTS),
            "forbidden_process_capabilities": [
                f"os.{name}" for name in pad4.FORBIDDEN_WORKER_OS_ATTRIBUTES
            ],
            "dynamic_project_import_permitted": False,
            "runpy_execution_permitted": False,
            "arbitrary_source_loading_permitted": False,
            "pickle_cloudpickle_dill_permitted": False,
            "forbidden_scientific_ipc": list(protocol.FORBIDDEN_SCIENTIFIC_IPC),
            "serialized_executable_python_object_graph_permitted": False,
            "closed_worker_coding_rule": True,
            "claims_to_enumerate_hostile_python_techniques": False,
            "universal_claim_that_every_certified_module_is_free_of_every_dynamic_import_mechanism": (
                False
            ),
            "current_certified_source_scan": {
                "scope": "CURRENT_CERTIFIED_SOURCE_UNIVERSE",
                "claim_kind": (
                    "VERIFIED_CURRENT_SOURCE_FACT_NOT_AN_ETERNAL_UNIVERSAL_CLAIM"
                ),
                "scanned_for": (
                    "CLOSED_WORKER_CODING_RULE_CONSTRUCTS: the dynamic execution "
                    "callables, the forbidden import roots including ordinary "
                    "network and database client modules, and the "
                    "process-spawning os capabilities"
                ),
                "a_hit_is_evidence_of_a_dynamic_project_import": False,
                "hit_interpretation": (
                    "most hits are the network- and database-capable modules the "
                    "current package re-export graph drags into the certified "
                    "universe; no frozen operation reaches them, and the "
                    "direct-import reduction that narrows this is deferred to "
                    "POSTP1-001V2A-I2"
                ),
                "modules_scanned": len(frozen_candidate_source_manifest()),
                "modules_containing_a_closed_worker_rule_construct": len(
                    flagged_modules
                ),
                "modules": list(flagged_modules),
            },
            "production_calendar_source_governed_separately_by": [
                "CLOSED_AST_STORE_USE_GRAMMAR",
                "COMPILED_ROOT_BINDING_WITNESS",
            ],
            "current_findings": list(audit["findings"]),
            "closed": audit["closed"],
        }
    )


def scientific_request_protocol() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": protocol.REQUEST_SCHEMA_VERSION,
            "encoding": "CANONICAL_JSON_BYTES",
            "executable_payload_permitted": False,
            "transport": "WORKER_STDIN",
            "fields": sorted(protocol.REQUEST_FIELDS),
            "authority_bound_fields": list(protocol.AUTHORITY_BOUND_REQUEST_FIELDS),
            "schema_validated": True,
            "unknown_fields": "REFUSE",
            "missing_fields": "REFUSE",
            "nan_or_infinity": "REFUSE",
            "timestamps": "CANONICAL_UTC_ROUND_TRIP_REQUIRED",
            "decimals": "CANONICAL_STRINGS_NEVER_BINARY_FLOATS",
            "exact_one_document_parsing": True,
            "received_bytes_must_reserialize_to_themselves": True,
            "input_digest_persisted": True,
            "frozen_operations": list(protocol.FROZEN_WORKER_OPERATIONS),
            "arbitrary_callable_dispatch_permitted": False,
            "operation_inputs": {
                name: sorted(fields)
                for name, fields in sorted(protocol.OPERATION_INPUT_FIELDS.items())
            },
            "parent_python_objects_shared": False,
            "forbidden_request_payloads": [
                "ARBITRARY_CALLABLE_OBJECTS",
                "ARBITRARY_PICKLED_OBJECTS",
                "CLASSES",
                "FUNCTIONS",
                "LIVE_CalendarEvidenceStore_OBJECT",
                "MODULE_OBJECTS",
            ],
            "authority_fields_are_copied_from_the_trusted_context": True,
            "caller_may_select_a_raw_decision_hash": False,
            "caller_may_supply_a_project_source_manifest": False,
            "caller_may_supply_a_third_party_semantic_registry": False,
            "evidence_reconstruction": (
                "THE_WORKER_REBUILDS_A_READ_ONLY_EVIDENCE_VIEW_FROM_CANONICAL_DATA"
            ),
            "authoritative_evidence_admission_mode": (
                protocol.AUTHORITATIVE_EVIDENCE_ADMISSION_MODE
            ),
            "prototype_evidence_admission_mode": (
                protocol.PROTOTYPE_EVIDENCE_ADMISSION_MODE
            ),
            "prototype_mode_is_scientific_authority": False,
        }
    )


def scientific_response_protocol() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": protocol.RESPONSE_SCHEMA_VERSION,
            "encoding": "CANONICAL_JSON_BYTES",
            "transport": "WORKER_STDOUT",
            "stdout_protocol": protocol.STDOUT_PROTOCOL,
            "stderr_protocol": protocol.STDERR_PROTOCOL,
            "extra_or_ambiguous_protocol_output": "REFUSE",
            "fields": sorted(protocol.RESPONSE_FIELDS),
            "authority_bound_fields": list(protocol.AUTHORITY_BOUND_RESPONSE_FIELDS),
            "fully_materialized_result_required": True,
            "forbidden_result_kinds": list(protocol.LAZY_RESULT_KINDS),
            "lazy_result": "REFUSE",
            "scientific_execution_after_the_response_boundary": False,
            "result_digest_required": True,
            "memory_addresses_in_evidence": False,
            "typed_failure_protocol": True,
            "partial_result_admission_on_any_exception_path": False,
            "response_echo_alone_establishes_authority": False,
            "evidence_fields": [
                "admitted",
                "bytecode_cache_binding",
                "calendar_authority_hash",
                "decision_time",
                "failure_reason",
                "interpreter_identity",
                "operation",
                "process_exit_status",
                "request_digest",
                "request_schema_version",
                "result_digest",
                "third_party_authority_digest",
                "third_party_installed_content_verification",
                "third_party_observed_content_manifest_digest",
                "trusted_authority_context",
                "trusted_persistence_authority_hash",
                "worker_authority_hash",
                "worker_authority_ticket",
                "worker_source_manifest_digest",
                "worker_source_manifest_role",
            ],
        }
    )


def worker_io_and_capability_boundary() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_WORKER_IO_AND_CAPABILITY_BOUNDARY_V1_PAD4_R1"
            ),
            "worker_network_permitted": False,
            "worker_https_permitted": False,
            "scientific_input_supplied_by_the_controller": True,
            "collection_remains_a_separate_governed_boundary": True,
            "worker_private_signing_key_permitted": False,
            "worker_collector_signing_capability_permitted": False,
            "signing_key_environment_variable_present": "REFUSE",
            "worker_is_a_scientific_evaluator_not_the_acquisition_signer": True,
            "worker_authoritative_db_write_permitted": False,
            "worker_database_connection": (
                "NOT_ESTABLISHED_BY_ANY_FROZEN_OPERATION"
            ),
            "result_admission_is_a_controller_responsibility": True,
            "preferred_boundary": "NO_WORKER_DATABASE_CONNECTION",
            "enforcement": [
                "FROZEN_MINIMAL_CHILD_ENVIRONMENT",
                "FROZEN_READ_ONLY_OPERATION_REGISTRY",
                "STATIC_CLOSED_WORKER_SOURCE_PROHIBITION",
            ],
            "operating_system_level_network_sandbox_claimed": False,
            "operating_system_network_sandbox_added_by_this_correction": False,
            "no_network_guarantee_basis": (
                "the frozen read-only operation registry, the frozen minimal "
                "child environment and the static closed worker-source "
                "prohibition; consistent with the reviewed PAD4 finding and "
                "deliberately not strengthened into a kernel-level claim"
            ),
            "certified_source_universe_includes_db_and_network_capable_modules": True,
            "capability_width_reason": (
                "the current package re-export graph pulls btc_predictor.db and "
                "HTTPS-capable calendar collection modules into the certified "
                "import closure even though no frozen operation reaches them; "
                "the direct-import reduction that narrows this is deferred to "
                "POSTP1-001V2A-I2"
            ),
            "collection_authority_moved_into_the_worker": False,
        }
    )


def compiled_root_binding_witness_rule() -> dict[str, Any]:
    payload = dict(attestation.compiled_root_binding_witness_rule())
    payload.pop("definition_sha256", None)
    payload["contract_version"] = (
        "ETF_CALENDAR_COMPILED_ROOT_BINDING_WITNESS_RULE_V1_PAD4_R1"
    )
    payload["freshly_parent_bound_by"] = f"{DECISION_VERSION}_{PROGRAM_TICKET}"
    payload["failed_pad2_parent_certified"] = False
    payload["failed_pad3_parent_certified"] = False
    payload["failed_pad4_parent_certified"] = False
    payload["preserved_under_process_isolation"] = True
    payload["applies_to_certified_calendar_source_before_final_implementation"] = True
    return _definition(payload)


def store_root_and_direct_use_grammar() -> dict[str, Any]:
    payload = dict(attestation.store_root_and_direct_use_grammar())
    payload.pop("definition_sha256", None)
    payload["contract_version"] = (
        "ETF_CALENDAR_STORE_ROOT_AND_DIRECT_USE_GRAMMAR_V1_PAD4_R1"
    )
    payload["freshly_parent_bound_by"] = f"{DECISION_VERSION}_{PROGRAM_TICKET}"
    payload["preserved_under_process_isolation"] = True
    payload["process_isolation_legalizes_wrappers"] = False
    payload["root_may_be_a_cell_variable_of_a_conforming_owner"] = False
    payload["known_generator_capture_rewrite_still_required"] = (
        f"{KNOWN_PRODUCTION_BLOCKER_OWNER}:{KNOWN_PRODUCTION_BLOCKER_ROOT}"
    )
    return _definition(payload)


def replay_owner_graph_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": "ETF_CALENDAR_REPLAY_OWNER_GRAPH_RULE_V1_PAD4_R1",
            "owner_count": len(FROZEN_REPLAY_OWNERS),
            "owners": list(FROZEN_REPLAY_OWNERS),
            "owner_census_relation": "FROZEN_EQUALS_SOURCE_DISCOVERED_EQUALS_11",
            "process_isolation_redefines_the_owner_graph": False,
            "cycles_permitted": False,
            "unknown_forwarding_permitted": False,
            "every_owner_has_an_evidence_edge": True,
            "every_owner_path_terminates_at_documented_store_api": True,
            "documented_terminals": list(STORE_APIS),
            "edge_kinds": [
                "DOCUMENTED_STORE_API_TERMINAL",
                "ENUMERATED_REPLAY_OWNER_EDGE",
            ],
            "compiled_root_witness_must_pass_before_graph_extraction": True,
            "ast_use_audit_must_pass_before_graph_extraction": True,
            "both_layers_required": True,
            "either_layer_substitutes_for_the_other": False,
            "static_graph_proves": "CERTIFIED_SOURCE_STRUCTURE",
            "runtime_owner_attestation_required_at_execution": False,
            "runtime_owner_attestation_demoted_reason": (
                "measured same-process owner identity is not a completeness "
                "proof; the certified isolated source universe replaces it"
            ),
        }
    )


def direct_body_dependency_rule() -> dict[str, Any]:
    payload = dict(attestation.direct_body_dependency_rule())
    payload.pop("definition_sha256", None)
    payload["contract_version"] = (
        "ETF_CALENDAR_DIRECT_BODY_DEPENDENCY_RULE_V1_PAD4_R1"
    )
    payload["freshly_parent_bound_by"] = f"{DECISION_VERSION}_{PROGRAM_TICKET}"
    payload["required_direct_bodies"] = list(REQUIRED_DIRECT_BODIES)
    payload["wrapper_installed_guards_permitted"] = False
    payload["wrapper_installer_removal_required"] = WRAPPER_INSTALLER_SITE
    payload["functools_wraps_authority_guards_permitted"] = False
    payload["process_isolation_legalizes_wrappers"] = False
    payload["certified_dependency_sha256"] = CERTIFIED_DEPENDENCY_SHA256
    payload["artifact_builder_dispatch_rewrite_required_by_this_decision"] = False
    return _definition(payload)


def controller_result_admission_rule() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_CONTROLLER_RESULT_ADMISSION_RULE_V1_PAD4_R1"
            ),
            "admission_requires_all_three": [
                "REQUEST_AGREES_WITH_THE_TRUSTED_AUTHORITY_CONTEXT",
                "RESPONSE_AGREES_WITH_THE_TRUSTED_AUTHORITY_CONTEXT",
                "RESPONSE_CROSS_BINDS_TO_THE_REQUEST",
            ],
            "response_equals_request_is_sufficient": False,
            "caller_request_worker_agreement_is_necessary_but_not_sufficient": True,
            "validated_before_admission": [
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
                "worker_source_manifest_identity",
            ],
            "expected_dependency_authority_validated": [
                "EXACT_DEPENDENCY_SET",
                "EXACT_REVIEWED_RECORD_AND_ARTIFACT_IDENTITIES",
                "EXACT_REVIEWED_VERSIONS",
                "SUCCESSFUL_INSTALLED_CONTENT_VERIFICATION",
            ],
            "any_mismatch": [protocol.RESULT_NOT_ADMITTED, protocol.DATA_QUALITY_FAIL],
            "scientific_success_requires": [
                "EXPECTED_PROCESS_EXIT",
                "SUCCESSFUL_WORKER_SELF_VERIFICATION",
                "VALID_CANONICAL_RESPONSE",
            ],
            "unexpected_crash_signal_timeout_protocol_error_or_extra_output": [
                protocol.RESULT_NOT_ADMITTED,
                protocol.DATA_QUALITY_FAIL,
            ],
            "silent_retry_with_a_different_authority_path": False,
            "worker_authority_hash_is_controller_bound": True,
            "worker_authority_hash_binding_mechanism": (
                "TRUSTED_CONTROLLER_AUTHORITY_CONTEXT_NOT_REQUEST_RESPONSE_ECHO"
            ),
            "result_admission_precedes_any_persistence": False,
            "persistence_follows_admission": True,
        }
    )


def proof_order_and_completeness_definition() -> dict[str, Any]:
    return _definition(
        {
            "contract_version": (
                "ETF_CALENDAR_ISOLATED_WORKER_PROOF_ORDER_V1_PAD4_R1"
            ),
            "controller_or_review_order": [
                "1_LOAD_THE_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT",
                "2_VERIFY_THE_EXPECTED_PROOF_ARCHITECTURE_IDENTITY",
                "3_VERIFY_THE_FROZEN_PROJECT_SOURCE_MANIFEST_IDENTITY",
                "4_VERIFY_THE_EXACT_REVIEWED_THIRD_PARTY_SEMANTIC_AND_ARTIFACT_REGISTRY",
                "5_CREATE_A_FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE",
                "6_BUILD_THE_CANONICAL_REQUEST_FROM_THE_TRUSTED_AUTHORITY_CONTEXT",
                "7_LAUNCH_THE_FRESH_EXACT_INTERPRETER",
            ],
            "worker_order": [
                "8_VERIFY_INTERPRETER_STARTUP_AND_PYCACHE_CONTROLS",
                "9_VERIFY_THE_REQUEST_SCHEMA",
                "10_VERIFY_SOURCE_FILES_AGAINST_THE_TRUSTED_EXPECTED_MANIFEST",
                "11_VERIFY_THIRD_PARTY_SEMANTIC_AND_ARTIFACT_IDENTITIES",
                "12_VERIFY_INSTALLED_FILES_AGAINST_RECORD_BEFORE_DEPENDENCY_EXECUTION",
                "13_ESTABLISH_THE_CONTROLLED_PROJECT_IMPORT_PATH",
                "14_LOAD_CERTIFIED_SCIENTIFIC_SOURCE",
                "15_VERIFY_LOADED_MODULE_ORIGINS_AND_BYTECODE_CACHE_BINDING",
                "16_EXECUTE_ONE_FROZEN_SCIENTIFIC_OPERATION",
                "17_REFUSE_LAZY_OUTPUT",
                "18_POST_VERIFY_THE_SOURCE_AND_MODULE_BOUNDARY",
                "19_EMIT_EXACTLY_ONE_CANONICAL_RESPONSE",
                "20_EXIT",
            ],
            "controller_admission_order": [
                "21_VERIFY_A_CLEAN_PROCESS_RESULT",
                "22_VERIFY_THE_REQUEST_AGAINST_THE_TRUSTED_CONTEXT",
                "23_VERIFY_THE_RESPONSE_AGAINST_THE_TRUSTED_CONTEXT",
                "24_VERIFY_REQUEST_RESPONSE_CROSS_BINDING",
                "25_VERIFY_THE_RESULT_DIGEST",
                "26_ADMIT_THE_SCIENTIFIC_RESULT",
            ],
            "no_scientific_call_before_self_verification_passes": True,
            "dependency_code_executes_before_its_content_is_verified": False,
            "completeness_claim": (
                "the scientific answer is produced by certified source, executed "
                "as certified bytecode, under a certified interpreter, against a "
                "reviewed third-party artifact whose installed bytes were "
                "verified first, in a process that shares no mutable Python "
                "state with the application, and every material authority "
                "identity reproduces against a trusted controller context"
            ),
            "completeness_claim_is_not": (
                "an enumeration of every mutable Python object capable of "
                "affecting execution"
            ),
            "explicit_limits": [
                "ARBITRARY_OPERATING_SYSTEM_LEVEL_COMPROMISE_IS_OUT_OF_SCOPE",
                "CERTIFIED_SOURCE_EXECUTING_ITS_OWN_SEMANTICS_IS_NOT_DRIFT",
                "MODIFICATION_PERFECTLY_RACING_VERIFICATION_OR_USE_IS_OUT_OF_SCOPE",
                "STDLIB_OBJECTS_ARE_TRUSTED_THROUGH_THE_INTERPRETER_AXIOM",
                "THE_CANDIDATE_PARENT_HASH_IS_BOUND_BY_THE_REVIEW_CONTEXT",
            ],
            "required_adversarial_regressions": [
                "ALTERED_INSTALLED_DEPENDENCY_FILE_WITH_UNCHANGED_RECORD_REFUSES",
                "CERTIFIED_SOURCE_FILE_MUTATION_REFUSES",
                "CONTROLLED_CACHE_POISONING_REFUSES",
                "FORGED_PROJECT_PYC_IS_NOT_EXECUTED",
                "FORGED_THIRD_PARTY_PYC_IS_NOT_EXECUTED",
                "FORK_ONLY_INHERITED_INTERPRETER_IS_NOT_AUTHORIZED",
                "LAZY_RESULT_REFUSES",
                "PARENT_BUILTINS_MUTATION_LEAVES_THE_WORKER_UNAFFECTED",
                "PARENT_FLOW_FEATURE_ID_MUTATION_LEAVES_THE_WORKER_UNAFFECTED",
                "PARENT_GENERATED_DATACLASS_METHOD_MUTATION_LEAVES_THE_WORKER_UNAFFECTED",
                "PARENT_SYS_MODULES_SUBSTITUTION_LEAVES_THE_WORKER_UNAFFECTED",
                "PRE_REQUEST_SOURCE_DRIFT_REFUSES",
                "PRE_REQUEST_WORKER_ENTRY_OR_PROTOCOL_DRIFT_REFUSES",
                "SAME_VERSION_WRONG_ARTIFACT_REFUSES",
                "SECOND_REQUEST_IN_ONE_WORKER_REFUSES",
                "SOURCELESS_OR_WRONG_ORIGIN_PROJECT_MODULE_REFUSES",
                "UNEXPECTED_PROJECT_MODULE_REFUSES",
                "WRONG_INTERPRETER_REFUSES",
                "WRONG_SELF_CONSISTENT_DECISION_HASH_IS_NOT_ADMITTED",
                "WRONG_THIRD_PARTY_VERSION_REFUSES",
            ],
            "determinism": [
                "ALTERNATE_CURRENT_DIRECTORY",
                "CHILD_ORDER_VARIATION",
                "FRESH_OUTPUT_DIRECTORY",
                "FRESH_PROCESS",
                "MULTIPLE_PYTHONHASHSEED_VALUES",
            ],
            "operational_pycache_paths_contaminate_authority_hashes": False,
            "worker_evidence_is_address_free": True,
        }
    )


def science_lineage_and_safety() -> dict[str, Any]:
    payload = dict(attestation.science_lineage_and_safety())
    payload.pop("definition_sha256", None)
    payload["contract_version"] = (
        "ETF_CALENDAR_ISOLATED_WORKER_SCIENCE_LINEAGE_AND_SAFETY_V1_PAD4_R1"
    )
    payload["failed_architecture_lineage"] = [
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
    ]
    payload["corrected_predecessor"] = {
        "definition_sha256": FAILED_PAD4_SHA256,
        "decision_commit": FAILED_PAD4_DECISION_COMMIT,
        "review": FAILED_PAD4_REVIEW,
        "review_commit": FAILED_PAD4_REVIEW_COMMIT,
        "review_result": FAILED_PAD4_REVIEW_RESULT,
        "artifacts_overwritten_by_this_correction": False,
        "certified": False,
        "used": False,
        "prospective_observations": 0,
    }
    payload["preserved_science"] = {
        "calendar_normalization_early_closes_pit_common_session_rules": "UNCHANGED",
        "etf_formulas_and_revision_semantics": "UNCHANGED",
        "etf_calendar_production_code_changed_by_this_decision": False,
        "parser_science": "UNCHANGED",
        "source_urls_profiles_tls_redirects": "UNCHANGED",
        "stage_b_metrics_risk_stops_thresholds": "UNCHANGED",
    }
    return _definition(payload)


_CHILD_ARTIFACTS: tuple[tuple[str, Callable[[], dict[str, Any]]], ...] = (
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


def isolated_scientific_worker_v1_r1_definition(
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    source = CALENDAR_SOURCE.read_text(encoding="utf-8")
    narrow.verify_replay_owner_census(source)
    verify_worker_protocol_binds_the_frozen_interpreter()
    verify_frozen_pre_i2_fixture()
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
            "correction_of": FAILED_PAD4_SHA256,
            "correction_is_a_new_architecture_family": False,
            "repaired_review_findings": list(REPAIRED_REVIEW_FINDINGS),
            "not_reopened": list(NOT_REOPENED),
            "failed_pad4_sha256": FAILED_PAD4_SHA256,
            "failed_pad4_certified": False,
            "failed_pad4_artifacts_overwritten": False,
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
            "third_party_authority_digest": protocol.third_party_authority_digest(
                frozen_third_party_authority()
            ),
            "central_decisions": {
                "fresh_exec_required": True,
                "fork_only_permitted": False,
                "one_request_one_process": True,
                "fresh_empty_pycache_namespace_required": True,
                "repository_pycache_authoritative": False,
                "cached_bytecode_may_override_certified_source": False,
                "runtime_source_manifest_rederivation_permitted": False,
                "request_is_authority_root": False,
                "response_echo_is_authority_root": False,
                "trusted_controller_authority_context_required": True,
                "pre_i2_116_module_manifest_role": (
                    "CONFORMANCE_FIXTURE_NOT_FINAL_PRODUCTION_AUTHORITY"
                ),
                "final_i2_source_manifest_must_be_calendar_parent_bound": True,
                "third_party_exact_reviewed_versions_required": True,
                "third_party_reviewed_artifact_identity_required": True,
                "record_declared_installed_file_hashes_must_be_verified": True,
                "arbitrary_installed_version_self_certification_permitted": False,
                "pickle_ipc_permitted": False,
                "worker_network_permitted": False,
                "worker_private_signing_key_permitted": False,
                "worker_authoritative_db_write_permitted": False,
                "lazy_result_permitted": False,
                "runtime_object_closure_is_completeness_proof": False,
                "parent_python_objects_shared": False,
                "process_isolation_is_scientific_execution_boundary": True,
                "project_source_manifest_required": True,
                "unexpected_project_module_permitted": False,
                "dynamic_project_import_permitted": False,
                "long_lived_worker_permitted": False,
                "reflection_blacklist_complete": False,
                "generated_runtime_method_enumeration_required": False,
                "transitive_mutable_object_closure_required": False,
                "compiled_root_witness_preserved": True,
                "root_may_be_a_cell_variable_of_a_conforming_owner": False,
                "closed_ast_store_use_grammar_preserved": True,
                "exact_eleven_owner_graph_preserved": True,
                "direct_body_dependency_checks_preserved": True,
                "wrapper_installed_guards_permitted": False,
                "artifact_builder_dispatch_rewrite_required_by_this_decision": False,
                "operating_system_level_network_sandbox_claimed": False,
                "hostile_filesystem_race_resistance_claimed": False,
                "hostile_operating_system_resistance_claimed": False,
                "candidate_parent_hash_self_embedded": False,
                "calendar_science_changed": False,
                "calendar_production_code_changed": False,
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
    if dict(persisted) != isolated_scientific_worker_v1_r1_definition():
        raise IsolatedScientificWorkerR1Error(
            "persisted corrected isolated scientific worker decision does not reproduce"
        )
    _verify_definition_digest(persisted)


def _report_markdown(decision: Mapping[str, Any]) -> str:
    owners = "\n".join(f"- `{owner}`" for owner in FROZEN_REPLAY_OWNERS)
    lineage = "\n".join(f"- `{sha}`" for sha in FAILED_ARCHITECTURE_LINEAGE)
    interpreter = PROOF_INTERPRETER_IDENTITY
    production = decision["current_production_expected_result"]
    launch_flags = " ".join(WORKER_LAUNCH_FLAGS)
    store_apis = "`, `".join(STORE_APIS)
    dependencies = "\n".join(
        f"- `{entry.distribution}` `{entry.version}` roots `{', '.join(entry.root_modules)}` "
        f"RECORD `{entry.record_sha256}` content `{entry.record_content_manifest_digest}`"
        for entry in frozen_third_party_authority()
    )
    return f"""# {DECISION_VERSION} — corrected isolated one-shot scientific worker

- Ticket: `{PROGRAM_TICKET}`
- Decision hash: `{decision['definition_sha256']}`
- Corrected predecessor: `{FAILED_PAD4_SHA256}` (failed, never certified, never overwritten)
- Status: `{STATUS}`
- Classification: `{FINAL_CLASSIFICATION}`
- Strategy: `{PROOF_STRATEGY}`
- Material children: {decision['material_child_count']}
- Pre-I2 source fixture: {decision['pre_i2_project_source_module_count']} modules at `{decision['pre_i2_project_source_manifest_digest']}`
- Candidate worker source universe: {decision['candidate_worker_source_module_count']} modules at `{decision['candidate_worker_source_manifest_digest']}`
- Third-party authority digest: `{decision['third_party_authority_digest']}`

## What this corrects, and what it does not

`{FAILED_PAD4_REVIEW}` independently reproduced the `PAD4` parent and found the
fresh-exec process-isolation boundary **sound**. It failed the candidate with
`{FAILED_PAD4_REVIEW_RESULT}` plus three further release-critical
authority-anchoring defects. This ticket is a bounded correction of exactly
those four findings:

1. **Executed bytecode was not bound to certified source.** `-B`
   suppresses bytecode *writes* only; nothing suppressed or validated bytecode
   *reads*. A forged timestamp-valid `__pycache__/flow.cpython-312.pyc`
   executed while the certified `.py` bytes were unchanged, and the controller
   admitted `FORGED_BYTECODE_ID`. The repair is structural: every worker runs
   under `-X {WORKER_LAUNCH_X_OPTION}=<fresh empty per-worker directory>`, the
   namespace is controller-created, verified empty before launch and removed
   afterwards, and the worker refuses unless `sys.pycache_prefix` is exactly
   the declared namespace, `sys.dont_write_bytecode` is `True` and the
   namespace is empty. Adjacent `__pycache__` directories are then never
   consulted at all, for certified project source and for installed
   third-party source alike, and every loaded module's `__cached__` path must
   lie inside the namespace.
2. **Certified source authority was not frozen.** Request construction derived
   the manifest from live disk and verified the worker against that same newly
   derived manifest, so drift existing *before* request construction
   self-certified. Authority construction and runtime are now two distinct
   operations: derivation from reviewed source happens only at authority
   construction or refreeze, and runtime consumes an already-frozen expected
   manifest.
3. **Controller authority binding was invalid.** The decision hash was a
   request/response echo, so `0000...0000` and `deadbeef...deadbeef` were both
   admitted with real scientific results. Every material authority identity is
   now compared against a trusted `ScientificWorkerAuthorityContext` that a
   request cannot construct, a response cannot construct, live disk cannot
   silently replace and the installed environment cannot silently replace.
4. **Third-party installed content and semantics were not attested.**
   Verification hashed only `RECORD`, and the declared version was compared to
   nothing. The reviewed semantic and artifact registry is now frozen, and
   every installed file byte the reviewed `RECORD` declares a hash for is
   verified before any dependency code executes.

Same-process runtime-owner attestation, transitive mutable-object closure,
reflection-blacklist completeness and generated-method enumeration are **not**
reopened. This is a correction of `PAD4`, not a new architecture family, and no
`PAD5` exists.

## Preserved closed-input isolation boundary

The proven boundary is unchanged and still required: a fresh exec'd CPython
{interpreter['version_major']}.{interpreter['version_minor']}.{interpreter['version_micro']} worker under `{launch_flags}`, one request per
process, no parent Python object sharing, canonical JSON IPC, no
pickle/cloudpickle/dill/marshal IPC, lazy-result refusal, controller result
admission, fork-only refusal and parent monkeypatch isolation.

## Exact interpreter

- implementation: `{interpreter['implementation_name']}`
- version: `{interpreter['version_major']}.{interpreter['version_minor']}.{interpreter['version_micro']} {interpreter['version_releaselevel']}/{interpreter['version_serial']}`
- hexversion: `{interpreter['hexversion']}`
- cache tag: `{interpreter['cache_tag']}`
- bytecode magic: `{interpreter['magic_number_hex']}`

## Source authority and the pre-I2 fixture

`{PRE_I2_FIXTURE_VERSION}` freezes the exact reviewed current source universe —
{decision['pre_i2_project_source_module_count']} modules at
`{decision['pre_i2_project_source_manifest_digest']}` — as literal material, so
it stays immutable when `POSTP1-001V2A-I2` later rewrites
`etf_publication_calendar.py`. Its role is an architecture conformance test
vector, provenance and a pre-I2 source-drift regression anchor. It is
explicitly **not** the future production scientific source authority.

`POSTP1-001V2A-I2` must derive the exact final worker project-source manifest
*after* all its source changes are complete and parent-bind that exact manifest
and digest to `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1`. I2 may perform the
anticipated direct-import reduction, provided the calendar science, the
outputs and the replay-owner graph are unchanged and the manifest is
mechanically re-derived. This proof-architecture hash does not change merely
because the eventual production source manifest becomes narrower.

## Reviewed third-party authority

{dependencies}

An observed version that differs from the frozen reviewed version refuses. A
same-version but different unreviewed artifact refuses, because the reviewed
`RECORD` artifact digest and normalized content-manifest digest are both
parent-bound. Absolute install locations and `RECORD` paths remain launch
material, never scientific authority.

## Authority context and the self-hash boundary

The candidate parent hash cannot be materially embedded inside itself, and no
cryptographic self-hash fixed point is attempted. The architecture uses a
two-stage boundary: while this candidate is under review the reviewer or the
test harness instantiates the trusted context with the *recomputed* parent
hash, which comes from the trusted review context and never from the scientific
request. After a review PASS, `POSTP1-001V2A-I2` binds the exact certified
`PAD4-R1` hash into the final calendar authority, where no self-reference
exists because the proof-architecture hash is already certified before the
final `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1` hash is created. Until I2 does
so, `production_authority_context_from_calendar_authority` refuses with
`{PRODUCTION_CONTEXT_NOT_YET_BOUND}`.

## Accepted limits

No operating-system-level network sandbox is claimed and none is added here.
Hostile filesystem race resistance is explicitly not claimed: a malicious
modification perfectly racing verification or use is outside the accepted
trusted-operating-system boundary. The requirement is deterministic project and
deployment integrity, not hostile kernel defence. The dynamic-import claim is
scoped precisely: authoritative worker entry/protocol dynamic project execution
is forbidden and statically audited, the certified source universe is
mechanically derived from static import declarations, and an unexpected loaded
project module refuses. There is no universal claim that every certified module
is free of every dynamic import mechanism.

## Preserved static authority

The compiled root-binding witness, the root-cell prohibition, the closed AST
store-use grammar, the exact eleven-owner census and graph and the direct
dependency-body requirement are preserved and freshly parent-bound. The failed
PAD2, PAD3 and PAD4 parents are not certified. The owners remain exactly:

{owners}

Every owner path still terminates at a documented store API
(`{store_apis}`), cycles and unknown forwarding remain forbidden, and
`assert_trusted_persistence_dependency()` must still execute directly inside
each of the five required bodies. Process isolation does not legalize wrappers.

## Current production

- reviewed calendar source: `{production['reviewed_source_sha256']}`
- root write/clear/delete findings: {production['root_write_clear_or_delete_findings']}
- root-cell blocker: `{production['root_cell_finding']}`
- AST store grammar: `{production['ast_store_use_normal_form']}`
- wrapper-installer removal required: {production['wrapper_installer_removal_required']}
- corrected worker integrated in production: {production['corrected_worker_integrated_in_production']}
- full conformance: `{production['calendar_production_conformance']}`

## Failed lineage

All of the following remain failed, non-certified, unused, immutable and at
zero observations:

{lineage}

Failed calendar authority hashes are preserved unchanged, the certified
predecessor corpus protocol
`8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7` and the
failed V2 `488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d`
are unchanged, and trusted persistence `{CERTIFIED_DEPENDENCY_SHA256}` remains
closed, certified and unchanged.

## Safety

Prospective observations remain 0. No real Stage-B evaluation ran. The calendar
authority is not certified, calendar implementation is blocked,
POSTP1-001V2A-I2, POSTP1-001V2R1, POSTP1-003R3 and POSTP1-004 are blocked,
collection is not authorized, BTC-019 is untouched and Epic T is unchanged.
This candidate authorizes only `{REQUIRED_REVIEW}`.
"""


def write_artifacts(
    output_dir: Path,
    child_artifacts: Sequence[tuple[str, Callable[[], dict[str, Any]]]] | None = None,
) -> dict[str, Any]:
    registry = _CHILD_ARTIFACTS if child_artifacts is None else tuple(child_artifacts)
    decision = isolated_scientific_worker_v1_r1_definition(registry)
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
            raise IsolatedScientificWorkerR1Error(
                f"persisted {filename} does not reproduce"
            )
        _verify_definition_digest(persisted)
        if decision["child_definition_sha256"].get(
            filename.removesuffix(".json")
        ) != expected["definition_sha256"]:
            raise IsolatedScientificWorkerR1Error(
                f"corrected isolated scientific worker parent does not bind {filename}"
            )
    report = (output_dir / REPORT_FILENAME).read_text(encoding="utf-8")
    if report != _report_markdown(decision):
        raise IsolatedScientificWorkerR1Error(
            "persisted corrected isolated scientific worker report does not reproduce"
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
