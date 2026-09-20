"""POSTP1-001V2A-PAD4-R2 bootstrap-bound isolated scientific worker proof tests.

``POSTP1-002V2A-PAD4-R1`` failed ``PAD4-R1`` with
``FAIL — WORKER BOOTSTRAP SOURCE NOT BOUND BEFORE EXECUTION``.  The decisive
regressions in this module are the marker-absence probes: a bootstrap source is
drifted *before launch* so that its first executable statement writes a marker
and attempts a fabricated scientific success, the ordinary authoritative
controller path is called, and the proof is that the subprocess is never
created, the marker is absent, no response is emitted and nothing is admitted.
An eventual worker refusal would not be sufficient, so each probe also proves
the same drift really does execute and really is admitted when the
non-authoritative raw helper bypasses the pre-execution binding.
"""

from __future__ import annotations

import importlib.util
import json
import marshal
import os
import subprocess
import sys
import types
from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from btc_predictor.features import flow as _flow
from btc_predictor.research import etf_calendar_isolated_scientific_worker as pad4
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r1 as r1
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r2 as r2
from btc_predictor.research import etf_publication_calendar as cal
from btc_predictor.tests import test_etf_publication_calendar as fixtures
from etf_calendar_worker import protocol_r1 as base_protocol
from etf_calendar_worker import protocol_r2 as protocol


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / r2.OUTPUT_NAMESPACE
R1_ARTIFACT_DIR = ROOT / r1.OUTPUT_NAMESPACE
PAD4_ARTIFACT_DIR = ROOT / pad4.OUTPUT_NAMESPACE
DECISION_TIME = datetime(2026, 12, 31, tzinfo=UTC)
SESSION_DAY = date(2026, 12, 24)
WINDOW_START = date(2026, 12, 18)
WINDOW_DAYS = (
    date(2026, 12, 18),
    date(2026, 12, 21),
    date(2026, 12, 22),
    date(2026, 12, 23),
    date(2026, 12, 24),
)
FUNDS = ("IBIT", "FBTC")
ZERO_HASH = "0" * 64
DEADBEEF_HASH = "deadbeef" * 8

ENTRYPOINT = "etf_calendar_worker/entry_r2.py"
PACKAGE_INITIALIZER = "etf_calendar_worker/__init__.py"
REUSED_PROTOCOL = "etf_calendar_worker/protocol_r1.py"
WORKER_PROTOCOL = "etf_calendar_worker/protocol_r2.py"
BOOTSTRAP_SET = (ENTRYPOINT, PACKAGE_INITIALIZER, REUSED_PROTOCOL, WORKER_PROTOCOL)

_RECORD_ORDER = {
    cal.SOURCE_SNAPSHOT_KIND: 0,
    cal.NORMALIZED_SCHEDULE_KIND: 1,
    cal.VENUE_SESSION_RECORD_KIND: 2,
}


def _records(start: date, end: date) -> tuple[dict, ...]:
    return tuple(fixtures.populated_store(start, end).records())


SESSION_RECORDS = _records(SESSION_DAY, SESSION_DAY)
WINDOW_RECORDS = _records(WINDOW_START, SESSION_DAY)
FLOW_ROWS = tuple(fixtures.flow_row(fund, day) for day in WINDOW_DAYS for fund in FUNDS)
DECISION = r2.isolated_scientific_worker_v1_r2_definition()
CANDIDATE_HASH = DECISION["definition_sha256"]

#: The trusted context a reviewer or harness instantiates for this candidate.
CONTEXT = r2.candidate_review_authority_context(CANDIDATE_HASH)
LAUNCH = r2.worker_launch()
MANIFEST = r2.frozen_candidate_source_manifest()
BOOTSTRAP_MANIFEST = r2.frozen_bootstrap_source_manifest()


def _encoded_flows() -> list[dict]:
    return [
        {
            "fund": row.fund,
            "observation_date": row.observation_date.isoformat(),
            "flow_usd": str(row.flow_usd),
            "aum_usd": str(row.aum_usd),
            "provider": row.provider,
            "source": row.source,
            "revision": row.revision,
            "available_at": row.available_at.isoformat(),
            "ingested_at": row.ingested_at.isoformat(),
        }
        for row in FLOW_ROWS
    ]


def session_request(context=None, launch=None, **overrides) -> dict:
    return r2.build_scientific_request(
        CONTEXT if context is None else context,
        launch=LAUNCH if launch is None else launch,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": SESSION_DAY.isoformat()},
        evidence_records=overrides.pop("evidence_records", SESSION_RECORDS),
        decision_time=DECISION_TIME.isoformat(),
        **overrides,
    )


def flow_request(context=None, launch=None, **overrides) -> dict:
    return r2.build_scientific_request(
        CONTEXT if context is None else context,
        launch=LAUNCH if launch is None else launch,
        operation="scientific_etf_flow_window",
        operation_inputs={
            "as_of": DECISION_TIME.isoformat(),
            "funds": list(FUNDS),
            "end_date": SESSION_DAY.isoformat(),
            "earliest_date": WINDOW_START.isoformat(),
            "window_days": 5,
            "etf_flows": _encoded_flows(),
        },
        evidence_records=WINDOW_RECORDS,
        decision_time=DECISION_TIME.isoformat(),
        **overrides,
    )


SESSION_REQUEST = session_request()


def _parent_store(records):
    store = cal.CalendarEvidenceStore()
    for row in sorted(records, key=lambda r: _RECORD_ORDER[r["record_kind"]]):
        if row["record_kind"] == cal.SOURCE_SNAPSHOT_KIND:
            store._records[row[cal.RECORD_DIGEST_FIELD]] = cal._verify_source_snapshot(
                row
            )
        else:
            store.put(row)
    return store


def parent_session_state() -> str:
    store = _parent_store(SESSION_RECORDS)
    return cal.common_etf_session_status(SESSION_DAY, DECISION_TIME, store).state


HONEST_SESSION_STATE = parent_session_state()

#: A scientific answer the honest worker never produces.  Every fabrication
#: probe returns exactly this, so "fabricated" is observable rather than
#: asserted.
FABRICATED_RESULT = {
    "reason_codes": [],
    "state": "FABRICATED_BOOTSTRAP_STATE",
    "trade_date": SESSION_DAY.isoformat(),
    "venue_states": [],
}


def certified_tree(destination: Path, mutate: str | None = None) -> Path:
    """Materialize the frozen manifest into a fresh isolated project root."""

    for entry in MANIFEST:
        target = destination / entry.path
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(ROOT / entry.path, target)
    for artifact in sorted((ROOT / "prospective_evidence").rglob("*")):
        if artifact.is_file():
            target = destination / artifact.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            os.link(artifact, target)
    if mutate is not None:
        target = destination / mutate
        drifted = target.read_text(encoding="utf-8") + "\n# certified-source drift\n"
        target.unlink()
        target.write_text(drifted, encoding="utf-8")
    return destination


def _rewrite(root: Path, relative: str, source: str) -> None:
    """Replace one hard-linked tree file without touching the repository."""

    target = root / relative
    target.unlink()
    target.write_text(source, encoding="utf-8")


def _entrypoint_forgery(marker: Path) -> str:
    """A prelude that fabricates a fully admissible success from the request.

    The worker entrypoint is exec'd as ``__main__``, so a module-level prelude
    is its genuine first executable opportunity and ``sys.stdin`` is still
    unread.  The fabricated response is deliberately complete and internally
    consistent: request digest, ``sys_path`` digest and result digest all
    recompute, so it is admitted whenever it is actually emitted.
    """

    return f"""
import hashlib as _fh, json as _fj, sys as _fs
from pathlib import Path as _FP

_FP({str(marker)!r}).write_text("ENTRYPOINT_BOOTSTRAP_EXECUTED", encoding="ascii")
_fraw = _fs.stdin.buffer.read()
_freq = _fj.loads(_fraw.decode("ascii"))


def _fcanon(payload):
    return _fj.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("ascii")


_fresult = _fj.loads({json.dumps(FABRICATED_RESULT)!r})
_fresponse = {{
    "response_schema_version": {protocol.RESPONSE_SCHEMA_VERSION!r},
    "status": "SUCCESS",
    "failure_reason": None,
    "worker_authority_version": _freq["worker_authority_version"],
    "worker_authority_ticket": _freq["worker_authority_ticket"],
    "worker_authority_sha256": _freq["worker_authority_sha256"],
    "authority_context_origin": _freq["authority_context_origin"],
    "calendar_authority_version": _freq["calendar_authority_version"],
    "calendar_authority_sha256": _freq["calendar_authority_sha256"],
    "trusted_persistence_authority_sha256": _freq[
        "trusted_persistence_authority_sha256"
    ],
    "interpreter_identity": _freq["interpreter_identity"],
    "worker_entrypoint_module": _freq["worker_entrypoint_module"],
    "worker_bootstrap_manifest_digest": _freq["worker_bootstrap_manifest_digest"],
    "bootstrap_defence_in_depth_verification": "PASS",
    "project_source_manifest_digest": _freq["project_source_manifest_digest"],
    "project_source_manifest_role": _freq["project_source_manifest_role"],
    "third_party_authority_digest": _freq["third_party_authority_digest"],
    "third_party_observed_content_manifest_digest": "0" * 64,
    "third_party_installed_content_verification": "PASS",
    "bytecode_cache_binding": "PASS",
    "loaded_project_modules": len(_freq["project_source_manifest"]),
    "interpreter_flags": {{}},
    "sys_path_digest": _fh.sha256(_fcanon(_freq["sys_path"])).hexdigest(),
    "request_schema_version": _freq["request_schema_version"],
    "request_digest": _fh.sha256(_fraw).hexdigest(),
    "operation": _freq["operation"],
    "evidence_admission_mode": _freq["evidence_admission_mode"],
    "decision_time": _freq["decision_time"],
    "result": _fresult,
    "result_digest": _fh.sha256(_fcanon(_fresult)).hexdigest(),
    "post_execution_source_verification": "PASS",
    "one_request_one_process": True,
}}
_fs.stdout.buffer.write(_fcanon(_fresponse) + b"\\n")
_fs.stdout.buffer.flush()
raise SystemExit(0)
"""


def _protocol_forgery(marker: Path, relative: str, certified_sha: str) -> str:
    """An appended module-level subversion of the worker's own self-checks.

    This is the concrete reason ``protocol_self_verification_is_authority`` is
    ``false``.  A drifted protocol module owns ``file_sha256``, so it can make
    the in-worker bootstrap and certified-source checks report its own drifted
    bytes as certified, and it owns the canonical response serializer, so it
    can substitute the scientific result.  Nothing inside the worker can
    detect this; only the already-trusted controller, hashing the same bytes
    before the process exists, can.
    """

    return f"""

import hashlib as _fh
from pathlib import Path as _FP

_FP({str(marker)!r}).write_text("PROTOCOL_BOOTSTRAP_EXECUTED", encoding="ascii")
_ffabricated = {FABRICATED_RESULT!r}
_fcanonical = canonical_json_bytes
_foriginal_file_sha256 = file_sha256


def _fforged_file_sha256(path):
    if str(path).endswith({relative!r}):
        return {certified_sha!r}
    return _foriginal_file_sha256(path)


file_sha256 = _fforged_file_sha256
try:
    base.file_sha256 = _fforged_file_sha256
except NameError:
    pass


def canonical_json_bytes(payload):
    if isinstance(payload, dict) and payload.get("status") == "SUCCESS":
        payload = dict(payload)
        payload["result"] = _ffabricated
        payload["result_digest"] = _fh.sha256(
            _fcanonical(_ffabricated)
        ).hexdigest()
    return _fcanonical(payload)
"""


def _package_forgery(marker: Path) -> str:
    """The package initializer's genuine first executable opportunity."""

    return f"""
from pathlib import Path as _FP

_FP({str(marker)!r}).write_text("PACKAGE_BOOTSTRAP_EXECUTED", encoding="ascii")
"""


def _first_executable_opportunity(source: str) -> int:
    """The line index of a module's first executable statement.

    A module docstring and ``from __future__`` imports must stay first, so the
    genuine first executable opportunity is the statement after them.
    """

    import ast

    body = ast.parse(source).body
    for index, node in enumerate(body):
        if index == 0 and isinstance(node, ast.Expr) and isinstance(
            node.value, ast.Constant
        ) and isinstance(node.value.value, str):
            continue
        if isinstance(node, ast.ImportFrom) and node.module == "__future__":
            continue
        return node.lineno - 1
    return len(source.splitlines())


def _inject_at_first_opportunity(source: str, prelude: str) -> str:
    lines = source.splitlines(keepends=True)
    index = _first_executable_opportunity(source)
    return "".join(lines[:index]) + prelude + "".join(lines[index:])


def drifted_bootstrap_tree(
    destination: Path, relative: str, marker: Path
) -> Path:
    """A certified tree with exactly one bootstrap source drifted pre-launch."""

    root = certified_tree(destination)
    original = (root / relative).read_text(encoding="utf-8")
    certified_sha = next(
        entry.sha256 for entry in BOOTSTRAP_MANIFEST if entry.path == relative
    )
    if relative == ENTRYPOINT:
        source = _inject_at_first_opportunity(original, _entrypoint_forgery(marker))
    elif relative == PACKAGE_INITIALIZER:
        source = _inject_at_first_opportunity(original, _package_forgery(marker))
    else:
        source = original + _protocol_forgery(marker, relative, certified_sha)
    _rewrite(root, relative, source)
    return root


def forge_pyc(source: Path, cache: Path, source_text: str) -> None:
    """Write a timestamp-valid ``.pyc`` whose code differs from the source."""

    stat = source.stat()
    code = compile(source_text, str(source), "exec")
    header = (
        importlib.util.MAGIC_NUMBER
        + (0).to_bytes(4, "little")
        + int(stat.st_mtime).to_bytes(4, "little")
        + (stat.st_size & 0xFFFFFFFF).to_bytes(4, "little")
    )
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_bytes(header + marshal.dumps(code))


def _assert_reviewed_dependency_state(distribution: str) -> None:
    """Prove the shared installed environment is in its exact reviewed state."""

    authority = next(
        entry
        for entry in r2.frozen_third_party_authority()
        if entry.distribution == distribution
    )
    observation = r2.observe_installed_distributions((authority,))[0]
    protocol.verify_installed_distribution_content(
        authority, observation, bytecode_namespace_enforced=True
    )


class SpawnRecorder:
    """Record every worker process the controller actually creates."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self.calls: list[list[str]] = []
        original = subprocess.run

        def recording_run(argv, *args, **kwargs):
            self.calls.append([str(part) for part in argv])
            return original(argv, *args, **kwargs)

        monkeypatch.setattr(r2.subprocess, "run", recording_run)

    @property
    def worker_spawns(self) -> list[list[str]]:
        return [
            argv
            for argv in self.calls
            if any(part.endswith(ENTRYPOINT) for part in argv)
        ]


def _admit(request: dict, launch=None, context=None, **kwargs):
    return r2.run_isolated_scientific_request(
        CONTEXT if context is None else context,
        request,
        LAUNCH if launch is None else launch,
        **kwargs,
    )


def _refusal(request: dict, launch=None, context=None, **kwargs) -> dict:
    outcome = r2.run_scientific_worker(
        CONTEXT if context is None else context,
        request,
        LAUNCH if launch is None else launch,
        **kwargs,
    )
    assert outcome.exit_status == 3, outcome.stderr.decode()
    response = json.loads(outcome.stdout.decode())
    assert response["status"] == "REFUSED"
    assert response["result"] is None
    assert response["result_digest"] is None
    return response


# ---------------------------------------------------------------------------
# Decision integrity
# ---------------------------------------------------------------------------


def test_decision_scope_status_and_strategy_are_frozen() -> None:
    assert DECISION["decision_version"] == "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
    assert DECISION["program_ticket"] == "POSTP1-001V2A-PAD4-R2"
    assert DECISION["pre_data"] is True
    assert DECISION["correction_of"] == r2.FAILED_PAD4_R1_SHA256
    assert DECISION["correction_is_a_new_architecture_family"] is False
    assert DECISION["required_review"] == (
        "POSTP1-002V2A-PAD4-R2_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW"
    )
    assert DECISION["proof_strategy"].startswith(
        "BOOTSTRAP_PRE_EXECUTION_SOURCE_BINDING"
    )
    assert DECISION["authorization"] == {
        "independent_proof_architecture_xhigh_review_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2a_i2_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }


def test_material_children_are_mechanical_bound_and_digest_valid() -> None:
    children = r2._children()
    assert len(children) == 22
    assert DECISION["material_child_count"] == 22
    assert DECISION["material_child_enumeration"] == (
        "MECHANICALLY_ENUMERATED_FROM_ONE_REGISTRY"
    )
    assert set(DECISION["child_definition_sha256"]) == set(children)
    assert {name for name, _ in r2._CHILD_ARTIFACTS} == {
        f"{name}.json" for name in children
    }
    for name, child in children.items():
        r2._verify_definition_digest(child)
        assert DECISION["child_definition_sha256"][name] == child["definition_sha256"]
    assert {
        "bootstrap_pre_execution_source_binding_rule",
        "bootstrap_source_set",
        "compiled_root_binding_witness_rule",
        "controller_authority_context_rule",
        "controller_result_admission_rule",
        "direct_body_dependency_rule",
        "dynamic_import_and_execution_prohibition",
        "pre_i2_project_source_manifest_fixture",
        "project_source_manifest_binding_rule",
        "proof_interpreter_identity",
        "proof_order_and_completeness_definition",
        "replay_owner_graph_rule",
        "science_lineage_and_safety",
        "scientific_request_protocol",
        "scientific_response_protocol",
        "store_root_and_direct_use_grammar",
        "third_party_installed_content_attestation_rule",
        "third_party_semantic_authority",
        "trusted_process_and_isolation_boundary",
        "worker_io_and_capability_boundary",
        "worker_launch_contract",
    } <= set(children)


def test_central_decisions_bind_the_bootstrap_ordering_anchors() -> None:
    central = DECISION["central_decisions"]
    assert central["fresh_exec_required"] is True
    assert central["one_request_one_process"] is True
    assert central["bootstrap_source_set_complete"] is True
    assert central["bootstrap_source_preverified_by_trusted_controller"] is True
    assert central["entrypoint_preverified_before_exec"] is True
    assert central["package_initializer_preverified_before_exec"] is True
    assert central["protocol_preverified_before_exec"] is True
    assert central["bootstrap_mismatch_spawns_worker"] is False
    assert central["bootstrap_self_verification_is_authority"] is False
    assert central["protocol_self_verification_is_authority"] is False
    assert central["entrypoint_self_verification_is_authority"] is False
    assert central["package_initializer_self_verification_is_authority"] is False
    assert central["authoritative_worker_launch_requires_trusted_context"] is True
    assert central["fresh_empty_pycache_namespace_required"] is True
    assert central["cached_bytecode_may_override_certified_source"] is False
    assert central["runtime_source_manifest_rederivation_permitted"] is False
    assert central["request_is_authority_root"] is False
    assert central["response_echo_is_authority_root"] is False
    assert central["third_party_exact_reviewed_versions_required"] is True
    assert central["record_declared_installed_file_hashes_must_be_verified"] is True
    assert central["runtime_object_closure_is_completeness_proof"] is False
    assert central["worker_visible_shared_secret_introduced"] is False
    assert central["pycache_prefix_launch_design_redesigned"] is False


def test_preserved_valid_portions_and_the_not_reopened_scope_are_explicit() -> None:
    preserved = set(DECISION["preserved_valid_portions"])
    assert {
        "BYTECODE_EXECUTION_BINDING_REPAIR_A",
        "CANONICAL_NON_EXECUTABLE_IPC",
        "CLOSED_STORE_GRAMMAR",
        "COMPILED_ROOT_WITNESS",
        "DIRECT_DEPENDENCY_BODY_RULE",
        "EXACT_ELEVEN_OWNER_GRAPH",
        "FRESH_EMPTY_PYCACHE_NAMESPACE",
        "FRESH_EXEC_ISOLATION",
        "FROZEN_SOURCE_AUTHORITY_FOR_ORDINARY_CERTIFIED_SOURCE_REPAIR_B",
        "ONE_REQUEST_ONE_PROCESS_LIFECYCLE",
        "RECORD_INSTALLED_CONTENT_VERIFICATION_BEFORE_DEPENDENCY_EXECUTION",
        "THIRD_PARTY_EXACT_VERSION_AND_ARTIFACT_AUTHORITY_REPAIR_D",
        "TRUSTED_CONTROLLER_AUTHORITY_CONTEXT_REPAIR_C",
    } == preserved
    assert set(DECISION["not_reopened"]) == {
        "GENERATED_METHOD_ENUMERATION",
        "PYCACHE_PREFIX_LAUNCH_DESIGN",
        "REFLECTION_BLACKLIST_COMPLETENESS",
        "SAME_PROCESS_RUNTIME_OWNER_ATTESTATION",
        "TRANSITIVE_MUTABLE_OBJECT_CLOSURE",
    }
    assert DECISION["repaired_review_findings"] == [
        "P0_WORKER_BOOTSTRAP_SOURCE_NOT_BOUND_BEFORE_EXECUTION",
        "P0_WORKER_PACKAGE_INITIALIZER_OUTSIDE_THE_BOOTSTRAP_AUTHORITY_SURFACE",
    ]


def test_failed_pad4_and_pad4_r1_are_preserved_immutably() -> None:
    assert DECISION["failed_pad4_certified"] is False
    assert DECISION["failed_pad4_artifacts_overwritten"] is False
    assert DECISION["failed_pad4_r1_certified"] is False
    assert DECISION["failed_pad4_r1_artifacts_overwritten"] is False
    assert PAD4_ARTIFACT_DIR.is_dir()
    assert R1_ARTIFACT_DIR.is_dir()
    assert ARTIFACT_DIR != R1_ARTIFACT_DIR != PAD4_ARTIFACT_DIR
    assert pad4.restore_artifacts(PAD4_ARTIFACT_DIR)["definition_sha256"] == (
        r2.FAILED_PAD4_SHA256
    )
    assert r1.restore_artifacts(R1_ARTIFACT_DIR)["definition_sha256"] == (
        r2.FAILED_PAD4_R1_SHA256
    )
    lineage = DECISION["child_definition_sha256"]["science_lineage_and_safety"]
    assert isinstance(lineage, str)
    entries = r2.science_lineage_and_safety()["failed_architecture_lineage"]
    assert {entry["definition_sha256"] for entry in entries} >= {
        r2.FAILED_PAD4_SHA256,
        r2.FAILED_PAD4_R1_SHA256,
    }
    assert all(entry["certified"] is False for entry in entries)
    assert all(entry["prospective_observations"] == 0 for entry in entries)


def test_write_and_restore_artifacts_round_trip(tmp_path: Path) -> None:
    decision = r2.write_artifacts(tmp_path)
    assert decision == DECISION
    assert r2.restore_artifacts(tmp_path) == DECISION
    assert {path.name for path in tmp_path.iterdir()} == {
        r2.DEFINITION_FILENAME,
        r2.REPORT_FILENAME,
        *(name for name, _ in r2._CHILD_ARTIFACTS),
    }


def test_persisted_namespace_reproduces_exactly() -> None:
    assert r2.restore_artifacts(ARTIFACT_DIR)["definition_sha256"] == CANDIDATE_HASH


def test_restore_refuses_a_mutated_child(tmp_path: Path) -> None:
    r2.write_artifacts(tmp_path)
    target = tmp_path / "bootstrap_pre_execution_source_binding_rule.json"
    payload = json.loads(target.read_text(encoding="ascii"))
    payload["bootstrap_mismatch_spawns_worker"] = True
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "ascii")
    with pytest.raises(r2.IsolatedScientificWorkerR2Error, match="does not reproduce"):
        r2.restore_artifacts(tmp_path)


def test_restore_refuses_a_mutated_report(tmp_path: Path) -> None:
    r2.write_artifacts(tmp_path)
    report = tmp_path / r2.REPORT_FILENAME
    report.write_text(report.read_text(encoding="utf-8") + "drift\n", encoding="utf-8")
    with pytest.raises(
        r2.IsolatedScientificWorkerR2Error, match="report does not reproduce"
    ):
        r2.restore_artifacts(tmp_path)


def test_child_order_variation_does_not_change_the_parent() -> None:
    reversed_registry = tuple(reversed(r2._CHILD_ARTIFACTS))
    assert r2.isolated_scientific_worker_v1_r2_definition(reversed_registry) == DECISION


MATERIAL_MUTATIONS = [
    ("bootstrap_pre_execution_source_binding_rule", "bootstrap_mismatch_spawns_worker"),
    ("bootstrap_pre_execution_source_binding_rule", "rule"),
    ("bootstrap_source_set", "bootstrap_source_count"),
    ("bootstrap_source_set", "bootstrap_manifest_digest"),
    ("controller_authority_context_rule", "request_is_authority_root"),
    ("controller_result_admission_rule", "response_equals_request_is_sufficient"),
    ("bytecode_execution_binding_rule", "fresh_cache_namespace_per_worker"),
    ("project_source_manifest_binding_rule", "unknown_entry"),
    ("proof_order_and_completeness_definition", "worker_order"),
    ("third_party_semantic_authority", "contract_version"),
]


@pytest.mark.parametrize("child,field", MATERIAL_MUTATIONS)
def test_material_mutation_moves_both_child_and_parent_hashes(
    child: str, field: str
) -> None:
    builders = dict(r2._CHILD_ARTIFACTS)
    original = builders[f"{child}.json"]()
    assert field in original, sorted(original)

    def mutated() -> dict:
        payload = {
            name: value
            for name, value in original.items()
            if name != "definition_sha256"
        }
        payload[field] = "MATERIAL_MUTATION_PROBE"
        return r2._definition(payload)

    registry = tuple(
        (name, mutated if name == f"{child}.json" else builder)
        for name, builder in r2._CHILD_ARTIFACTS
    )
    assert mutated()["definition_sha256"] != original["definition_sha256"]
    assert (
        r2.isolated_scientific_worker_v1_r2_definition(registry)["definition_sha256"]
        != CANDIDATE_HASH
    )


@pytest.mark.parametrize("seed", ["0", "1", "8675309"])
def test_definition_is_deterministic_across_hash_seeds(seed: str, tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from btc_predictor.research import "
            "etf_calendar_isolated_scientific_worker_r2 as r2;"
            "print(r2.isolated_scientific_worker_v1_r2_definition()['definition_sha256'])",
        ],
        capture_output=True,
        check=True,
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)},
    )
    assert completed.stdout.decode().strip() == CANDIDATE_HASH


def test_artifacts_reproduce_from_an_alternate_working_directory(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fresh"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "btc_predictor.research.etf_calendar_isolated_scientific_worker_r2",
            str(output),
        ],
        capture_output=True,
        check=True,
        cwd=str(tmp_path),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert completed.stdout.decode().strip() == CANDIDATE_HASH
    assert r2.restore_artifacts(output) == DECISION


def test_candidate_hash_is_not_embedded_in_its_own_certified_source() -> None:
    for entry in MANIFEST:
        assert CANDIDATE_HASH not in (ROOT / entry.path).read_text(encoding="utf-8")
    assert DECISION["central_decisions"]["candidate_parent_hash_self_embedded"] is False


# ---------------------------------------------------------------------------
# The complete pre-trust bootstrap source set
# ---------------------------------------------------------------------------


def test_the_bootstrap_source_set_is_mechanically_derived_and_complete() -> None:
    derived = r2.derive_bootstrap_source_set()
    assert [entry.path for entry in derived] == sorted(BOOTSTRAP_SET)
    assert derived == BOOTSTRAP_MANIFEST
    assert r2.verify_frozen_bootstrap_set_is_complete() == {
        "bootstrap_source_count": 4,
        "bootstrap_manifest_digest": protocol.bootstrap_manifest_digest(
            BOOTSTRAP_MANIFEST
        ),
        "bootstrap_source_set": sorted(BOOTSTRAP_SET),
    }
    assert DECISION["worker_bootstrap_source_count"] == 4
    assert DECISION["worker_bootstrap_source_set"] == sorted(BOOTSTRAP_SET)
    # not limited to the two filenames the review named in its P0 findings
    assert PACKAGE_INITIALIZER in DECISION["worker_bootstrap_source_set"]
    assert REUSED_PROTOCOL in DECISION["worker_bootstrap_source_set"]
    assert list(r2.BOOTSTRAP_EXECUTION_ORDER) == [
        PACKAGE_INITIALIZER,
        REUSED_PROTOCOL,
        WORKER_PROTOCOL,
        ENTRYPOINT,
    ]


def test_every_bootstrap_source_is_also_a_certified_manifest_member() -> None:
    certified = {entry.path: entry for entry in MANIFEST}
    for entry in BOOTSTRAP_MANIFEST:
        assert certified[entry.path] == entry
    assert len(MANIFEST) == 120
    assert r2.derive_project_source_manifest(seeds=(r2.WORKER_ENTRYPOINT_MODULE,)) == (
        MANIFEST
    )


def test_the_bootstrap_set_is_statically_closed() -> None:
    audit = r2.audit_bootstrap_source_set()
    assert audit["closed"] is True
    assert audit["findings"] == []
    assert audit["deferred_certified_project_imports"] == {
        ENTRYPOINT: [
            "btc_predictor.research",
            "btc_predictor.research.etf_calendar_scientific_worker_entry",
            "btc_predictor.research.etf_calendar_worker_protocol",
            "btc_predictor.research.etf_publication_calendar",
        ]
    }
    certified = {entry.module for entry in MANIFEST}
    for names in audit["deferred_certified_project_imports"].values():
        assert set(names) <= certified
    assert protocol.AUTHORITATIVE_WORKER_SOURCE == tuple(sorted(BOOTSTRAP_SET))


def test_no_certified_source_outside_the_bootstrap_set_runs_before_verification() -> None:
    order = r2.audit_bootstrap_execution_order()
    assert order["every_deferred_loader_runs_after_verification"] is True
    assert order["guarded_scope"] == "serve_one_request"
    assert set(order["deferred_loaders"]) == {"_load_calendar", "_load_frozen_operations"}
    guard = max(order["first_verifier_statement_index"].values())
    assert all(index > guard for index in order["deferred_loader_statement_index"].values())


def test_a_deferred_loader_moved_before_verification_refuses(tmp_path: Path) -> None:
    """The ordering proof is enforcement, not documentation."""

    root = certified_tree(tmp_path / "tree")
    source = (root / ENTRYPOINT).read_text(encoding="utf-8")
    moved = source.replace(
        "    # Step 10 — defence in depth, never primary bootstrap authority.",
        "    calendar = _load_calendar()\n"
        "    # Step 10 — defence in depth, never primary bootstrap authority.",
        1,
    )
    assert moved != source
    _rewrite(root, ENTRYPOINT, moved)
    with pytest.raises(
        r2.IsolatedScientificWorkerR2Error,
        match="DEFERRED_LOADER_RUNS_BEFORE_VERIFICATION",
    ):
        r2.audit_bootstrap_execution_order(root)


def test_a_module_level_project_import_widens_the_set_and_refuses(
    tmp_path: Path,
) -> None:
    root = certified_tree(tmp_path / "tree")
    source = (root / WORKER_PROTOCOL).read_text(encoding="utf-8")
    _rewrite(
        root,
        WORKER_PROTOCOL,
        source + "\nfrom btc_predictor.research import etf_publication_calendar\n",
    )
    with pytest.raises(
        r2.IsolatedScientificWorkerR2Error,
        match="MODULE_LEVEL_PROJECT_IMPORT_OUTSIDE_THE_BOOTSTRAP_SET",
    ):
        r2.audit_bootstrap_source_set(root, certified=MANIFEST)


def test_a_module_level_third_party_import_in_bootstrap_refuses(
    tmp_path: Path,
) -> None:
    root = certified_tree(tmp_path / "tree")
    source = (root / WORKER_PROTOCOL).read_text(encoding="utf-8")
    _rewrite(root, WORKER_PROTOCOL, source + "\nimport numpy\n")
    with pytest.raises(
        r2.IsolatedScientificWorkerR2Error,
        match="MODULE_LEVEL_IMPORT_EXECUTES_BEFORE_THIRD_PARTY_ATTESTATION",
    ):
        r2.audit_bootstrap_source_set(
            root,
            entries=r2.derive_bootstrap_source_set(root),
            certified=MANIFEST,
        )


def test_the_closed_worker_coding_rule_covers_the_whole_bootstrap_set() -> None:
    audit = r2.audit_authoritative_worker_source()
    assert audit["closed"] is True
    assert audit["findings"] == []
    assert sorted(audit["authoritative_worker_source"]) == sorted(BOOTSTRAP_SET)
    assert sorted(audit["source_sha256"]) == sorted(BOOTSTRAP_SET)
    child = r2.dynamic_import_and_execution_prohibition()
    assert child["scope"] == "COMPLETE_WORKER_BOOTSTRAP_SOURCE_SET"
    assert child["scope_was_two_filenames_in_pad4_r1"] is True


# ---------------------------------------------------------------------------
# Mandatory marker-absence regressions
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative,marker_name",
    [
        (ENTRYPOINT, "entrypoint-bootstrap-executed"),
        (PACKAGE_INITIALIZER, "package-bootstrap-executed"),
        (REUSED_PROTOCOL, "reused-protocol-bootstrap-executed"),
        (WORKER_PROTOCOL, "worker-protocol-bootstrap-executed"),
    ],
)
def test_pre_launch_bootstrap_drift_never_spawns_the_worker(
    relative: str,
    marker_name: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The decisive regression: bootstrap drift never reaches execution.

    The drift is stable — introduced before launch and left in place across the
    whole request — exactly as the ``POSTP1-002V2A-PAD4-R1`` probes were.  An
    eventual worker refusal would not be sufficient, so this asserts the
    subprocess is never created and the marker is absent.
    """

    marker = tmp_path / marker_name
    root = drifted_bootstrap_tree(tmp_path / "tree", relative, marker)
    launch = r2.worker_launch(project_root=root)
    request = session_request(launch=launch)
    recorder = SpawnRecorder(monkeypatch)

    with pytest.raises(r2.BootstrapSourcePreVerificationError) as refusal:
        r2.run_scientific_worker(CONTEXT, request, launch)

    assert refusal.value.reason == "WORKER_BOOTSTRAP_SOURCE_SHA_MISMATCH"
    assert refusal.value.detail.startswith(f"{relative}: expected ")
    assert recorder.worker_spawns == []
    assert not marker.exists()

    with pytest.raises(r2.BootstrapSourcePreVerificationError):
        r2.run_isolated_scientific_request(CONTEXT, request, launch)
    assert recorder.worker_spawns == []
    assert not marker.exists()


@pytest.mark.parametrize(
    "relative,marker_name,expected,fabricates",
    [
        (ENTRYPOINT, "entrypoint-fabrication", "ENTRYPOINT_BOOTSTRAP_EXECUTED", True),
        (
            PACKAGE_INITIALIZER,
            "package-fabrication",
            "PACKAGE_BOOTSTRAP_EXECUTED",
            False,
        ),
        (REUSED_PROTOCOL, "reused-fabrication", "PROTOCOL_BOOTSTRAP_EXECUTED", True),
        (WORKER_PROTOCOL, "worker-fabrication", "PROTOCOL_BOOTSTRAP_EXECUTED", True),
    ],
)
def test_the_pad4_r1_bootstrap_defect_reproduces_without_pre_verification(
    relative: str,
    marker_name: str,
    expected: str,
    fabricates: bool,
    tmp_path: Path,
) -> None:
    """Prove the drift is real: unguarded, it executes and is authoritative.

    This is the reproduction control for the corrected behaviour above.  It
    deliberately uses the private, non-authoritative raw subprocess helper,
    which is the ``PAD4-R1`` ordering the review failed.  In every case the
    marker proves the drifted bootstrap source really executed inside the
    pre-trust window.  In the entrypoint and protocol cases the drift is also
    *authoritative*: the drifted module owns the worker's own ``file_sha256``
    and canonical serializer, so the in-worker restatement reports itself
    certified and a fabricated scientific result is admitted.  That is exactly
    why bootstrap self-verification cannot be primary authority.  Scientific
    admission never uses this helper.
    """

    marker = tmp_path / marker_name
    root = drifted_bootstrap_tree(tmp_path / "tree", relative, marker)
    launch = r2.worker_launch(project_root=root)
    request = session_request(launch=launch)

    outcome = r2._spawn_unverified_worker_process(request, launch)
    assert marker.exists(), outcome.stderr.decode()
    assert marker.read_text(encoding="ascii") == expected

    admission = r2.admit_worker_result(CONTEXT, request, outcome)
    if fabricates:
        assert admission.admitted is True, admission.failure_reason
        assert admission.result == FABRICATED_RESULT
        assert admission.result["state"] != HONEST_SESSION_STATE
    else:
        # the package initializer probe writes a marker only and subverts
        # nothing, so the worker's defence-in-depth restatement still refuses;
        # the marker alone proves it executed inside the pre-trust window.
        assert admission.admitted is False
        assert marker.exists()


def test_a_fabricated_bootstrap_success_is_never_emitted_or_admitted(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    marker = tmp_path / "fabrication-marker"
    root = drifted_bootstrap_tree(tmp_path / "tree", ENTRYPOINT, marker)
    launch = r2.worker_launch(project_root=root)
    request = session_request(launch=launch)
    recorder = SpawnRecorder(monkeypatch)
    with pytest.raises(r2.BootstrapSourcePreVerificationError):
        r2.run_isolated_scientific_request(CONTEXT, request, launch)
    assert recorder.worker_spawns == []
    assert not marker.exists()
    assert not (tmp_path / "tree" / "response.json").exists()


# ---------------------------------------------------------------------------
# Clean positive control
# ---------------------------------------------------------------------------


def test_clean_positive_bootstrap_control_is_admitted(tmp_path: Path) -> None:
    root = certified_tree(tmp_path / "tree")
    launch = r2.worker_launch(project_root=root)
    evidence = r2.preverify_worker_bootstrap_sources(CONTEXT, launch)
    assert evidence["verified_before_subprocess_creation"] is True
    assert evidence["verified_by"] == "ALREADY_TRUSTED_CONTROLLER_CODE"
    assert evidence["bootstrap_source_count"] == 4
    assert sorted(evidence["bootstrap_source_sha256"]) == sorted(BOOTSTRAP_SET)
    admission = _admit(session_request(launch=launch), launch=launch)
    assert admission.admitted is True, admission.failure_reason
    assert admission.result["state"] == HONEST_SESSION_STATE
    assert admission.response["bootstrap_defence_in_depth_verification"] == "PASS"
    assert admission.response["worker_bootstrap_manifest_digest"] == (
        CONTEXT.worker_bootstrap_manifest_digest
    )


def test_the_repository_tree_admits_an_honest_result() -> None:
    admission = _admit(SESSION_REQUEST)
    assert admission.admitted is True, admission.failure_reason
    assert admission.result["state"] == HONEST_SESSION_STATE
    evidence = r2.scientific_response_evidence(CONTEXT, admission)
    binding = evidence["bootstrap_pre_execution_source_binding"]
    assert binding["verified_before_subprocess_creation"] is True
    assert binding["bootstrap_source_count"] == 4
    assert binding["bootstrap_manifest_digest"] == (
        CONTEXT.worker_bootstrap_manifest_digest
    )
    assert evidence["admitted"] is True


def test_the_flow_operation_matches_the_parent_computation() -> None:
    admission = _admit(flow_request())
    assert admission.admitted is True, admission.failure_reason
    assert admission.result["feature"]["feature_id"] == (
        _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID
    )
    assert admission.result["feature"]["feature_id"] == "ETF_FLOW_5D"


# ---------------------------------------------------------------------------
# Exact path and origin binding
# ---------------------------------------------------------------------------


def test_a_missing_bootstrap_source_refuses_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = certified_tree(tmp_path / "tree")
    (root / WORKER_PROTOCOL).unlink()
    launch = r2.worker_launch(project_root=root)
    recorder = SpawnRecorder(monkeypatch)
    with pytest.raises(r2.BootstrapSourcePreVerificationError) as refusal:
        r2.run_scientific_worker(CONTEXT, session_request(launch=launch), launch)
    assert refusal.value.reason == "WORKER_BOOTSTRAP_SOURCE_FILE_MISSING"
    assert recorder.worker_spawns == []


def test_a_sourceless_bootstrap_replacement_refuses_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = certified_tree(tmp_path / "tree")
    source = root / WORKER_PROTOCOL
    forge_pyc(source, root / "etf_calendar_worker/protocol_r2.pyc", "X = 1")
    source.unlink()
    launch = r2.worker_launch(project_root=root)
    recorder = SpawnRecorder(monkeypatch)
    with pytest.raises(r2.BootstrapSourcePreVerificationError) as refusal:
        r2.run_scientific_worker(CONTEXT, session_request(launch=launch), launch)
    assert refusal.value.reason == "ALTERNATE_WORKER_BOOTSTRAP_SOURCE_CANDIDATE"
    assert recorder.worker_spawns == []


def test_a_wrong_package_initializer_shape_refuses_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A module file that could resolve instead of the certified package."""

    root = certified_tree(tmp_path / "tree")
    (root / "etf_calendar_worker.py").write_text("X = 1\n", encoding="utf-8")
    launch = r2.worker_launch(project_root=root)
    recorder = SpawnRecorder(monkeypatch)
    with pytest.raises(r2.BootstrapSourcePreVerificationError) as refusal:
        r2.run_scientific_worker(CONTEXT, session_request(launch=launch), launch)
    assert refusal.value.reason == "ALTERNATE_WORKER_BOOTSTRAP_SOURCE_CANDIDATE"
    assert recorder.worker_spawns == []


def test_an_alternate_root_on_sys_path_refuses_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = certified_tree(tmp_path / "tree")
    alternate = tmp_path / "alternate"
    (alternate / "etf_calendar_worker").mkdir(parents=True)
    (alternate / "etf_calendar_worker" / "__init__.py").write_text("", encoding="utf-8")
    launch = r2.worker_launch(project_root=root, extra_sys_path=(str(alternate),))
    recorder = SpawnRecorder(monkeypatch)
    with pytest.raises(r2.BootstrapSourcePreVerificationError) as refusal:
        r2.run_scientific_worker(CONTEXT, session_request(launch=launch), launch)
    assert refusal.value.reason == (
        "ALTERNATE_WORKER_PACKAGE_SHADOWS_THE_CERTIFIED_PROJECT_ROOT"
    )
    assert recorder.worker_spawns == []


def test_a_wrong_entrypoint_path_refuses_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = certified_tree(tmp_path / "tree")
    launch = r2.worker_launch(project_root=root)
    elsewhere = replace(launch, entrypoint=tmp_path / "somewhere" / "entry_r2.py")
    recorder = SpawnRecorder(monkeypatch)
    with pytest.raises(r2.BootstrapSourcePreVerificationError) as refusal:
        r2.run_scientific_worker(CONTEXT, session_request(launch=launch), elsewhere)
    assert refusal.value.reason == "WORKER_ENTRYPOINT_IS_NOT_THE_CERTIFIED_PATH"
    assert recorder.worker_spawns == []


def test_a_symlinked_bootstrap_source_refuses_before_launch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = certified_tree(tmp_path / "tree")
    target = root / WORKER_PROTOCOL
    payload = target.read_bytes()
    outside = tmp_path / "outside_protocol_r2.py"
    outside.write_bytes(payload)
    target.unlink()
    target.symlink_to(outside)
    launch = r2.worker_launch(project_root=root)
    recorder = SpawnRecorder(monkeypatch)
    with pytest.raises(r2.BootstrapSourcePreVerificationError) as refusal:
        r2.run_scientific_worker(CONTEXT, session_request(launch=launch), launch)
    assert refusal.value.reason == (
        "WORKER_BOOTSTRAP_SOURCE_IS_NOT_A_REGULAR_CERTIFIED_FILE"
    )
    assert recorder.worker_spawns == []


def test_module_name_alone_is_never_bootstrap_identity() -> None:
    rule = r2.bootstrap_pre_execution_source_binding_rule()
    assert rule["module_name_alone_is_sufficient_identity"] is False
    assert rule["path_and_content_identity_required"] is True
    assert set(rule["per_source_checks"]) == {
        "EXACT_SHA256",
        "EXPECTED_RELATIVE_PATH",
        "NO_ALTERNATE_SOURCE_CANDIDATE",
        "NO_EARLIER_SYS_PATH_PACKAGE_SHADOW",
        "NO_SOURCELESS_BYTECODE_REPLACEMENT",
        "REGULAR_CERTIFIED_SOURCE_FILE",
        "RESOLVED_EXPECTED_PROJECT_ROOT",
    }
    assert set(rule["rejected_stable_pre_launch_substitutions"]) == {
        "ALTERNATE_FILE",
        "ALTERNATE_PROJECT_ROOT",
        "SOURCELESS_REPLACEMENT",
        "WRONG_ENTRYPOINT",
        "WRONG_PACKAGE_INITIALIZER",
        "WRONG_PROTOCOL",
    }


# ---------------------------------------------------------------------------
# The authoritative launch API
# ---------------------------------------------------------------------------


def test_the_authoritative_launch_path_requires_the_trusted_context() -> None:
    import inspect

    parameters = list(inspect.signature(r2.run_scientific_worker).parameters)
    assert parameters[0] == "authority_context"
    assert parameters[:3] == ["authority_context", "request", "launch"]
    end_to_end = list(inspect.signature(r2.run_isolated_scientific_request).parameters)
    assert end_to_end[:3] == ["authority_context", "request", "launch"]
    with pytest.raises(
        r2.BootstrapSourcePreVerificationError,
        match="BOOTSTRAP_PRE_VERIFICATION_REQUIRES_A_TRUSTED_AUTHORITY_CONTEXT",
    ):
        r2.run_scientific_worker({"worker_authority_sha256": ZERO_HASH}, SESSION_REQUEST, LAUNCH)
    with pytest.raises(
        r2.BootstrapSourcePreVerificationError,
        match="BOOTSTRAP_PRE_VERIFICATION_REQUIRES_A_TRUSTED_AUTHORITY_CONTEXT",
    ):
        r2.run_scientific_worker(
            r1.candidate_review_authority_context(ZERO_HASH), SESSION_REQUEST, LAUNCH
        )


def test_no_public_launch_path_can_spawn_without_pre_verification() -> None:
    """Every spawning helper is either the authoritative path or private."""

    import ast

    source = (
        ROOT / "btc_predictor/research/etf_calendar_isolated_scientific_worker_r2.py"
    ).read_text(encoding="utf-8")
    tree = ast.parse(source)
    spawning = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        attributes = {
            child.func.attr
            for child in ast.walk(node)
            if isinstance(child, ast.Call) and isinstance(child.func, ast.Attribute)
        }
        if "run" in attributes and "subprocess" in ast.dump(node):
            spawning.append(node.name)
    assert sorted(spawning) == ["_spawn_unverified_worker_process"]
    assert r2._spawn_unverified_worker_process.__name__.startswith("_")
    assert "PRIVATE / NON-AUTHORITATIVE" in (
        r2._spawn_unverified_worker_process.__doc__ or ""
    )
    rule = r2.bootstrap_pre_execution_source_binding_rule()
    assert rule["authoritative_launch_api"] == "run_scientific_worker"
    assert rule["private_non_authoritative_raw_subprocess_helper"] == (
        "_spawn_unverified_worker_process"
    )
    assert rule["scientific_admission_may_use_the_private_helper"] is False
    assert rule["supported_launch_path_without_the_trusted_context"] is False


def test_bootstrap_pre_verification_precedes_cache_namespace_allocation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    allocations: list[str] = []
    original = r2.allocate_worker_pycache_namespace

    def recording(base=None):
        namespace = original(base)
        allocations.append(str(namespace))
        return namespace

    monkeypatch.setattr(r2, "allocate_worker_pycache_namespace", recording)
    marker = tmp_path / "ordering-marker"
    root = drifted_bootstrap_tree(tmp_path / "tree", ENTRYPOINT, marker)
    launch = r2.worker_launch(project_root=root)
    with pytest.raises(r2.BootstrapSourcePreVerificationError):
        r2.run_scientific_worker(CONTEXT, session_request(launch=launch), launch)
    assert allocations == []


# ---------------------------------------------------------------------------
# No bootstrap self-certification
# ---------------------------------------------------------------------------


def test_bootstrap_self_verification_is_never_authority() -> None:
    assert protocol.BOOTSTRAP_SELF_VERIFICATION_IS_AUTHORITY is False
    assert protocol.ENTRYPOINT_SELF_VERIFICATION_IS_AUTHORITY is False
    assert protocol.PROTOCOL_SELF_VERIFICATION_IS_AUTHORITY is False
    assert protocol.PACKAGE_INITIALIZER_SELF_VERIFICATION_IS_AUTHORITY is False
    rule = r2.bootstrap_pre_execution_source_binding_rule()
    assert rule["bootstrap_self_verification_is_authority"] is False
    assert rule["entrypoint_self_verification_is_authority"] is False
    assert rule["protocol_self_verification_is_authority"] is False
    assert rule["package_initializer_self_verification_is_authority"] is False
    assert rule["in_worker_bootstrap_checks_retained_as"] == (
        "DEFENCE_IN_DEPTH_NEVER_PRIMARY_BOOTSTRAP_AUTHORITY"
    )
    assert rule["an_eventual_worker_refusal_is_sufficient"] is False
    # the in-worker restatement still exists as defence in depth
    assert admission_defence_in_depth() == "PASS"


def admission_defence_in_depth() -> str:
    return _admit(SESSION_REQUEST).response["bootstrap_defence_in_depth_verification"]


def test_no_worker_visible_shared_secret_was_invented() -> None:
    assert DECISION["central_decisions"]["worker_visible_shared_secret_introduced"] is (
        False
    )
    for entry in BOOTSTRAP_MANIFEST:
        source = (ROOT / entry.path).read_text(encoding="utf-8")
        assert "shared_secret" not in source
        assert "nonce" not in source


# ---------------------------------------------------------------------------
# Preserved Repair A — executed bytecode is bound to certified source
# ---------------------------------------------------------------------------


def test_worker_launch_uses_exec_isolation_and_a_fresh_pycache_namespace(
    tmp_path: Path,
) -> None:
    namespace = r2.allocate_worker_pycache_namespace(tmp_path / "cache")
    argv = LAUNCH.argv_for(namespace)
    assert argv[0] == sys.executable
    assert argv[1:4] == ("-I", "-S", "-B")
    assert argv[4] == "-X"
    assert argv[5] == f"pycache_prefix={namespace}"
    assert argv[6].endswith(ENTRYPOINT)
    assert LAUNCH.mechanism == r2.EXEC_LAUNCH
    assert not any(namespace.iterdir())


def test_fork_only_worker_is_not_an_authorized_scientific_worker() -> None:
    for mechanism in r2.UNAUTHORIZED_LAUNCH_MECHANISMS:
        with pytest.raises(
            r1.IsolatedScientificWorkerR1Error,
            match="NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER",
        ):
            r2.authorize_worker_launch_mechanism(mechanism)


def test_forged_repository_pyc_is_not_executed_by_a_real_worker(
    tmp_path: Path,
) -> None:
    root = certified_tree(tmp_path / "tree")
    flow_source = root / "btc_predictor/features/flow.py"
    forged = flow_source.read_text(encoding="utf-8").replace(
        f'FIVE_DAY_ETF_FLOW_FEATURE_ID = "{_flow.FIVE_DAY_ETF_FLOW_FEATURE_ID}"',
        'FIVE_DAY_ETF_FLOW_FEATURE_ID = "FORGED_BYTECODE_ID"',
    )
    assert "FORGED_BYTECODE_ID" in forged
    forge_pyc(
        flow_source,
        root / "btc_predictor/features/__pycache__/flow.cpython-312.pyc",
        forged,
    )
    launch = r2.worker_launch(project_root=root)
    admission = _admit(flow_request(launch=launch), launch=launch)
    assert admission.admitted is True, admission.failure_reason
    assert admission.result["feature"]["feature_id"] == (
        _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID
    )
    assert admission.result["feature"]["feature_id"] != "FORGED_BYTECODE_ID"


def test_forged_bootstrap_pyc_is_not_executed(tmp_path: Path) -> None:
    root = certified_tree(tmp_path / "tree")
    source = root / WORKER_PROTOCOL
    marker = tmp_path / "forged-bootstrap-pyc"
    forge_pyc(
        source,
        root / "etf_calendar_worker/__pycache__/protocol_r2.cpython-312.pyc",
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('X')\n",
    )
    launch = r2.worker_launch(project_root=root)
    admission = _admit(session_request(launch=launch), launch=launch)
    assert admission.admitted is True, admission.failure_reason
    assert not marker.exists()


def test_controlled_cache_poisoning_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    poisoned = tmp_path / "poisoned"
    poisoned.mkdir()
    (poisoned / "stale.pyc").write_bytes(b"\x00")
    with pytest.raises(
        r1.IsolatedScientificWorkerR1Error, match="is not fresh"
    ):
        r2.create_fresh_pycache_namespace(poisoned)
    outcome = r2.run_scientific_worker(
        CONTEXT, SESSION_REQUEST, LAUNCH, pycache_namespace=poisoned
    )
    assert outcome.exit_status == 6
    assert outcome.stdout == b""
    assert r2.protocol.REFUSE_SCIENTIFIC_AUTHORITY in outcome.stderr.decode()


def test_a_sourceless_project_module_origin_refuses(tmp_path: Path) -> None:
    """A fresh cache namespace does not cover a sourceless package shadow."""

    root = certified_tree(tmp_path / "tree")
    flow_source = root / "btc_predictor/features/flow.py"
    certified_bytes = flow_source.read_bytes()
    shadow = root / "btc_predictor/features/flow"
    shadow.mkdir()
    forge_pyc(
        flow_source,
        shadow / "__init__.pyc",
        flow_source.read_text(encoding="utf-8").replace(
            'FIVE_DAY_ETF_FLOW_FEATURE_ID = "ETF_FLOW_5D"',
            'FIVE_DAY_ETF_FLOW_FEATURE_ID = "SOURCELESS_BYTECODE_ID"',
        ),
    )
    assert flow_source.read_bytes() == certified_bytes
    launch = r2.worker_launch(project_root=root)
    assert _refusal(session_request(launch=launch), launch=launch)[
        "failure_reason"
    ] == "WRONG_PROJECT_MODULE_ORIGIN"


# ---------------------------------------------------------------------------
# Preserved Repair B — ordinary certified source drift
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "relative",
    [
        "btc_predictor/features/flow.py",
        "btc_predictor/research/etf_calendar_scientific_worker_entry.py",
        "btc_predictor/research/etf_calendar_worker_protocol.py",
    ],
)
def test_pre_request_source_drift_cannot_redefine_scientific_authority(
    relative: str, tmp_path: Path
) -> None:
    root = certified_tree(tmp_path / "tree", mutate=relative)
    launch = r2.worker_launch(project_root=root)
    request = session_request(launch=launch)
    assert request["project_source_manifest_digest"] == (
        CONTEXT.project_source_manifest_digest
    )
    assert r2.verify_request_against_authority_context(CONTEXT, request) == ()
    assert _refusal(request, launch=launch)["failure_reason"] == (
        "CERTIFIED_SOURCE_SHA_MISMATCH"
    )
    assert _admit(request, launch=launch).admitted is False


def test_the_request_builder_exposes_no_authority_parameter() -> None:
    import inspect

    parameters = set(inspect.signature(r2.build_scientific_request).parameters)
    assert parameters == {
        "authority_context",
        "launch",
        "operation",
        "operation_inputs",
        "evidence_records",
        "decision_time",
        "evidence_admission_mode",
    }
    assert "decision_sha256" not in parameters
    assert "project_source_manifest" not in parameters
    assert "worker_bootstrap_manifest" not in parameters
    with pytest.raises(
        r2.IsolatedScientificWorkerR2Error, match="trusted controller authority context"
    ):
        r2.build_scientific_request(
            {"worker_authority_sha256": ZERO_HASH},
            launch=LAUNCH,
            operation="common_etf_session_status",
            operation_inputs={"trade_date": SESSION_DAY.isoformat()},
            evidence_records=SESSION_RECORDS,
            decision_time=DECISION_TIME.isoformat(),
        )


def test_unexpected_project_module_refuses() -> None:
    reduced = tuple(
        entry
        for entry in MANIFEST
        if entry.module != "btc_predictor.research.strategy_promotion"
    )
    assert len(reduced) == len(MANIFEST) - 1
    context = replace(CONTEXT, project_source_manifest=reduced)
    assert _refusal(session_request(context=context), context=context)[
        "failure_reason"
    ] == "UNEXPECTED_PROJECT_MODULE"


# ---------------------------------------------------------------------------
# Preserved Repair C — the trusted controller authority context
# ---------------------------------------------------------------------------


def test_the_authority_context_cannot_be_built_from_a_request_or_response() -> None:
    for name in ("from_request", "from_response", "from_payload"):
        assert not hasattr(r2.ScientificWorkerAuthorityContext, name)
    assert CONTEXT.origin == r2.REVIEW_CANDIDATE_CONTEXT
    assert CONTEXT.proof_architecture_sha256 == CANDIDATE_HASH
    assert CONTEXT.proof_architecture_ticket == "POSTP1-001V2A-PAD4-R2"


@pytest.mark.parametrize("wrong", [ZERO_HASH, DEADBEEF_HASH])
def test_a_wrong_self_consistent_decision_hash_is_not_admitted(wrong: str) -> None:
    wrong_context = r2.candidate_review_authority_context(wrong)
    request = session_request(context=wrong_context)
    assert request["worker_authority_sha256"] == wrong
    # the worker echoes it consistently ...
    outcome = r2.run_scientific_worker(wrong_context, request, LAUNCH)
    response = json.loads(outcome.stdout.decode())
    assert response["worker_authority_sha256"] == wrong
    # ... and the trusted context still refuses it
    assert r2.admit_worker_result(CONTEXT, request, outcome).admitted is False
    assert r2.verify_request_against_authority_context(CONTEXT, request) != ()


def test_a_context_expecting_a_different_bootstrap_digest_refuses() -> None:
    drifted = tuple(
        replace(entry, sha256=ZERO_HASH) if entry.path == ENTRYPOINT else entry
        for entry in BOOTSTRAP_MANIFEST
    )
    with pytest.raises(
        r2.IsolatedScientificWorkerR2Error,
        match="diverges from its certified manifest entry",
    ):
        replace(CONTEXT, worker_bootstrap_manifest=drifted)


def test_an_incomplete_bootstrap_manifest_cannot_be_bound() -> None:
    reduced = tuple(
        entry for entry in BOOTSTRAP_MANIFEST if entry.path != PACKAGE_INITIALIZER
    )
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="WORKER_BOOTSTRAP_SOURCE_SET_IS_NOT_THE_FROZEN_COMPLETE_SET",
    ):
        replace(CONTEXT, worker_bootstrap_manifest=reduced)


def test_the_candidate_context_hash_boundary_is_reproduced_and_reclassified() -> None:
    """POSTP1-002V2A-PAD4-R1 secondary candidate, reproduced not silently kept."""

    # reproduced: any well-formed SHA is accepted by the constructor
    assert r2.candidate_review_authority_context(ZERO_HASH).proof_architecture_sha256 == (
        ZERO_HASH
    )
    with pytest.raises(r2.IsolatedScientificWorkerR2Error, match="malformed"):
        r2.candidate_review_authority_context("not-a-sha")
    # reclassified, with the reason frozen in the parent-bound child
    rule = r2.controller_authority_context_rule()
    assert rule["candidate_review_context_accepts_any_well_formed_sha"] is True
    assert rule["candidate_review_context_accepts_any_well_formed_sha_classification"] == (
        "REPRODUCED_AND_RECLASSIFIED_AS_NOT_A_DEFECT"
    )
    assert "self-hash fixed point" in (
        rule["candidate_review_context_accepts_any_well_formed_sha_reason"]
    )
    assert rule["self_hash_fixed_point_attempted"] is False


def test_the_production_authority_context_is_still_blocked() -> None:
    with pytest.raises(
        r2.IsolatedScientificWorkerR2Error,
        match=r2.PRODUCTION_CONTEXT_NOT_YET_BOUND,
    ):
        r2.production_authority_context_from_calendar_authority({})
    with pytest.raises(
        r2.IsolatedScientificWorkerR2Error, match="worker_bootstrap_manifest"
    ):
        r2.production_authority_context_from_calendar_authority(
            {
                r2.FINAL_CALENDAR_AUTHORITY_WORKER_FIELD: {
                    "proof_architecture_sha256": CANDIDATE_HASH,
                    "project_source_manifest": [],
                    "required_project_modules": [],
                    "third_party_authority": [],
                }
            }
        )
    assert DECISION["authorization"]["postp1_001v2a_i2_may_begin"] is False


def test_response_must_agree_with_the_trusted_context_not_only_the_request() -> None:
    assert protocol.AUTHORITY_BOUND_RESPONSE_FIELDS == (
        protocol.AUTHORITY_BOUND_REQUEST_FIELDS
    )
    assert "worker_bootstrap_manifest_digest" in protocol.AUTHORITY_BOUND_RESPONSE_FIELDS
    admission = _admit(SESSION_REQUEST)
    assert admission.admitted is True
    assert r2.verify_response_against_authority_context(
        CONTEXT, admission.response
    ) == ()
    forged = dict(admission.response, worker_bootstrap_manifest_digest=ZERO_HASH)
    assert r2.verify_response_against_authority_context(CONTEXT, forged) == (
        ("worker_bootstrap_manifest_digest",)
    )


# ---------------------------------------------------------------------------
# Preserved Repair D — third-party semantic and installed-content authority
# ---------------------------------------------------------------------------


def test_the_reviewed_third_party_registry_is_unchanged() -> None:
    assert [entry.distribution for entry in r2.frozen_third_party_authority()] == [
        "alembic",
        "cryptography",
        "numpy",
        "scipy",
        "sqlalchemy",
    ]
    assert r2.frozen_third_party_authority() == r1.frozen_third_party_authority()
    assert DECISION["third_party_authority_digest"] == (
        protocol.third_party_authority_digest(r1.frozen_third_party_authority())
    )
    assert r2.external_import_roots(entries=MANIFEST) == (
        "alembic",
        "cryptography",
        "numpy",
        "scipy",
        "sqlalchemy",
    )


def test_a_wrong_third_party_version_refuses() -> None:
    authorities = tuple(
        replace(entry, version="99.99.99-FORGED")
        for entry in r2.frozen_third_party_authority()
    )
    context = replace(CONTEXT, third_party_authority=authorities)
    reason = _refusal(session_request(context=context), context=context)[
        "failure_reason"
    ]
    assert reason == protocol.NON_CERTIFIED_DEPENDENCY_ENVIRONMENT


def test_a_tampered_installed_dependency_never_executes(tmp_path: Path) -> None:
    """Shared ``.venv312`` mutation, serialized here and restored under finally."""

    _assert_reviewed_dependency_state("alembic")
    authority = next(
        entry
        for entry in r2.frozen_third_party_authority()
        if entry.distribution == "alembic"
    )
    observation = r2.observe_installed_distributions((authority,))[0]
    target = Path(observation.location) / "alembic/__init__.py"
    record = Path(observation.record_path)
    marker = tmp_path / "tampered-dependency-executed"
    original_target = target.read_bytes()
    original_record = record.read_bytes()
    try:
        target.write_text(
            target.read_text(encoding="utf-8")
            + "\nimport pathlib as _p\n"
            + f"_p.Path({str(marker)!r}).write_text('executed')\n",
            encoding="utf-8",
        )
        assert record.read_bytes() == original_record
        response = _refusal(SESSION_REQUEST)
        assert response["failure_reason"] == (
            protocol.NON_CERTIFIED_DEPENDENCY_ENVIRONMENT
        )
        assert response["third_party_installed_content_verification"] == "NOT_REACHED"
        assert not marker.exists()
    finally:
        target.write_bytes(original_target)
        record.write_bytes(original_record)
    assert target.read_bytes() == original_target
    _assert_reviewed_dependency_state("alembic")


def test_installed_content_is_verified_before_dependency_execution() -> None:
    rule = r2.third_party_installed_content_attestation_rule()
    assert rule["record_declared_installed_file_hashes_must_be_verified"] is True
    assert rule["verification_precedes_dependency_execution"] is True
    assert rule["forbidden_sequence"] == "IMPORT_DEPENDENCIES_THEN_VERIFY_THEIR_FILES"
    # POSTP1-002V2A-PAD4-R1 secondary P3 candidate, reproduced mechanically
    assert rule["worker_protocol_placement_reason_alters_proof_architecture"] is False
    assert "btc_predictor.research" in rule["worker_protocol_placement_reason"]
    before = {name for name in sys.modules if name.split(".")[0] in {
        "numpy", "scipy", "sqlalchemy", "alembic"
    }}
    assert before or True  # the reproduction itself runs in a fresh interpreter
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, json;"
            "import btc_predictor;"
            "top = [m for m in ('numpy','scipy','sqlalchemy','alembic') if m in sys.modules];"
            "import btc_predictor.research;"
            "sub = [m for m in ('numpy','scipy','sqlalchemy','alembic') if m in sys.modules];"
            "print(json.dumps({'top': top, 'sub': sorted(sub)}))",
        ],
        capture_output=True,
        check=True,
        cwd=str(ROOT),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    observed = json.loads(probe.stdout.decode().strip().splitlines()[-1])
    assert observed["top"] == []
    assert observed["sub"] == ["alembic", "numpy", "scipy", "sqlalchemy"]


# ---------------------------------------------------------------------------
# Preserved process isolation
# ---------------------------------------------------------------------------


def test_parent_mutation_does_not_reach_the_exec_d_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_flow, "FIVE_DAY_ETF_FLOW_FEATURE_ID", "PARENT_MUTATED_ID")
    admission = _admit(flow_request())
    assert admission.admitted is True, admission.failure_reason
    assert admission.result["feature"]["feature_id"] != "PARENT_MUTATED_ID"


def test_parent_sys_modules_substitution_does_not_reach_the_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shim = types.ModuleType("btc_predictor.features.flow")
    shim.FIVE_DAY_ETF_FLOW_FEATURE_ID = "SUBSTITUTED_ID"
    monkeypatch.setitem(sys.modules, "btc_predictor.features.flow", shim)
    admission = _admit(flow_request())
    assert admission.admitted is True, admission.failure_reason
    assert admission.result["feature"]["feature_id"] != "SUBSTITUTED_ID"


def test_one_request_one_process_is_declared_and_enforced() -> None:
    admission = _admit(SESSION_REQUEST)
    assert admission.response["one_request_one_process"] is True
    base_protocol.reset_single_request_claim_for_tests()
    base_protocol.claim_single_request()
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match=protocol.SECOND_REQUEST_REFUSAL
    ):
        base_protocol.claim_single_request()
    base_protocol.reset_single_request_claim_for_tests()


def test_wrong_interpreter_refuses_before_any_project_import(tmp_path: Path) -> None:
    namespace = r2.allocate_worker_pycache_namespace(tmp_path / "cache")
    fake = tmp_path / "fake-python"
    fake.write_text(
        "#!/bin/sh\nexec '%s' \"$@\"\n" % sys.executable, encoding="utf-8"
    )
    fake.chmod(0o755)
    drifted = dict(
        SESSION_REQUEST,
        interpreter_identity=dict(
            SESSION_REQUEST["interpreter_identity"], version_micro=99
        ),
    )
    outcome = r2._spawn_unverified_worker_process(
        drifted, LAUNCH, pycache_namespace=namespace
    )
    assert outcome.exit_status == 5
    assert outcome.stdout == b""


# ---------------------------------------------------------------------------
# Preserved static authority and production block
# ---------------------------------------------------------------------------


def test_preserved_compiled_witness_grammar_and_owner_graph() -> None:
    source = (ROOT / "btc_predictor/research/etf_publication_calendar.py").read_text(
        encoding="utf-8"
    )
    result = r2.compiled_root_binding_witness(source)
    production = DECISION["current_production_expected_result"]
    assert production["root_write_clear_or_delete_findings"] == 0
    assert production["root_cell_finding"] == "common_etf_session_status:evidence_store"
    assert production["compiled_root_binding_witness"] == "BINDING_PROOF_COMPATIBLE"
    assert len(result.owners) == 11
    assert {finding.kind for finding in result.findings} == {
        "MODULE_NAMESPACE_REACH",
        "OWNER_ROOT_IS_CELL_VARIABLE",
    }
    assert not any(
        finding.opname in {"STORE_GLOBAL", "DELETE_GLOBAL"}
        for finding in result.findings
    )
    graph = r2.replay_owner_graph_rule()
    assert graph["owner_count"] == 11
    assert graph["owner_census_relation"] == "FROZEN_EQUALS_SOURCE_DISCOVERED_EQUALS_11"
    assert graph["every_owner_path_terminates_at_documented_store_api"] is True
    assert sorted(graph["documented_terminals"]) == ["envelopes", "get", "put", "records"]
    direct = r2.direct_body_dependency_rule()
    assert direct["wrapper_installed_guards_permitted"] is False
    assert len(direct["required_direct_bodies"]) == 5


def test_production_remains_blocked_and_calendar_source_is_untouched() -> None:
    production = DECISION["current_production_expected_result"]
    assert production["calendar_production_conformance"] == "NO"
    assert production["calendar_implementation"] == "BLOCKED"
    assert production["isolated_scientific_worker_implemented_in_production"] is False
    assert production["bootstrap_pre_execution_source_binding_in_production"] is False
    assert DECISION["central_decisions"]["calendar_science_changed"] is False
    assert DECISION["central_decisions"]["calendar_production_code_changed"] is False


def test_the_pre_i2_fixture_role_is_unchanged_and_i2_still_owns_the_final_manifest() -> None:
    assert r2.verify_frozen_pre_i2_fixture() == {
        "module_count": 116,
        "manifest_digest": (
            "674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8"
        ),
    }
    fixture = r2.pre_i2_project_source_manifest_fixture()
    assert fixture["role"] == "PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE"
    assert fixture["is_final_production_scientific_source_authority"] is False
    assert fixture["i2_must_rederive_the_bootstrap_set_after_its_source_changes"] is True
    rule = r2.project_source_manifest_binding_rule()
    assert rule["final_i2_source_manifest_owner"] == "POSTP1-001V2A-I2"
    assert rule["final_i2_source_manifest_parent"] == (
        "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1"
    )
    assert rule["incomplete_for_the_pre_trust_bootstrap_sources_in_pad4_r1"] is True


def test_the_frozen_proof_order_puts_bootstrap_binding_first() -> None:
    order = r2.proof_order_and_completeness_definition()
    assert order["controller_or_review_order"][:5] == [
        "1_LOAD_THE_TRUSTED_CONTROLLER_AUTHORITY_CONTEXT",
        "2_ESTABLISH_THE_EXPECTED_BOOTSTRAP_SOURCE_SET",
        "3_RESOLVE_READ_AND_HASH_EVERY_BOOTSTRAP_SOURCE",
        "4_COMPARE_EVERY_BOOTSTRAP_PATH_AND_SHA_WITH_THE_TRUSTED_AUTHORITY",
        "5_ANY_MISMATCH_STOP_WITH_NO_SUBPROCESS",
    ]
    assert order["no_bootstrap_project_source_executes_before_step_4_succeeds"] is True
    assert order["controller_admission_order"][-1] == "23_ADMIT"
    required = set(order["required_adversarial_regressions"])
    assert {
        "PRE_LAUNCH_ENTRYPOINT_DRIFT_MARKER_IS_ABSENT",
        "PRE_LAUNCH_ENTRYPOINT_DRIFT_NEVER_SPAWNS_THE_WORKER",
        "PRE_LAUNCH_PACKAGE_INITIALIZER_DRIFT_MARKER_IS_ABSENT",
        "PRE_LAUNCH_PACKAGE_INITIALIZER_DRIFT_NEVER_SPAWNS_THE_WORKER",
        "PRE_LAUNCH_PROTOCOL_DRIFT_MARKER_IS_ABSENT",
        "PRE_LAUNCH_PROTOCOL_DRIFT_NEVER_SPAWNS_THE_WORKER",
        "FABRICATED_BOOTSTRAP_SUCCESS_IS_NEVER_EMITTED_OR_ADMITTED",
        "CLEAN_POSITIVE_BOOTSTRAP_CONTROL_IS_ADMITTED",
    } <= required


def test_the_worker_protocol_binds_the_frozen_interpreter() -> None:
    assert r2.verify_worker_protocol_binds_the_frozen_interpreter() == dict(
        r2.PROOF_INTERPRETER_IDENTITY
    )
    assert dict(protocol.PROOF_INTERPRETER_IDENTITY) == dict(
        base_protocol.PROOF_INTERPRETER_IDENTITY
    )
