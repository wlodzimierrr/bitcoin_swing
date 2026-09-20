"""POSTP1-001V2A-PAD4-R1 corrected isolated scientific worker proof tests."""

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
from btc_predictor.research import etf_publication_calendar as cal
from btc_predictor.tests import test_etf_publication_calendar as fixtures
from etf_calendar_worker import protocol_r1 as protocol


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / r1.OUTPUT_NAMESPACE
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
DECISION = r1.isolated_scientific_worker_v1_r1_definition()
CANDIDATE_HASH = DECISION["definition_sha256"]

#: The trusted context a reviewer or harness instantiates for this candidate.
#: The expected proof-architecture hash comes from here, never from a request.
CONTEXT = r1.candidate_review_authority_context(CANDIDATE_HASH)
LAUNCH = r1.worker_launch()
MANIFEST = r1.frozen_candidate_source_manifest()


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
    return r1.build_scientific_request(
        CONTEXT if context is None else context,
        launch=LAUNCH if launch is None else launch,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": SESSION_DAY.isoformat()},
        evidence_records=overrides.pop("evidence_records", SESSION_RECORDS),
        decision_time=DECISION_TIME.isoformat(),
        **overrides,
    )


def flow_request(context=None, launch=None, **overrides) -> dict:
    return r1.build_scientific_request(
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


def parent_flow_result():
    return cal.scientific_etf_flow_window(
        FLOW_ROWS,
        as_of=DECISION_TIME,
        funds=FUNDS,
        end_date=SESSION_DAY,
        earliest_date=WINDOW_START,
        window_days=5,
        evidence_store=_parent_store(WINDOW_RECORDS),
    )


HONEST_SESSION_STATE = parent_session_state()
HONEST_FLOW = parent_flow_result()


def certified_tree(destination: Path, mutate: str | None = None) -> Path:
    """Materialize the frozen manifest into a fresh isolated project root.

    The frozen authority artifacts under ``prospective_evidence/`` are deployment
    material rather than certified source modules, so they are linked alongside
    the manifest: the calendar's trusted-persistence dependency assertion reads
    them at evaluation time.
    """

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
    """Prove the shared installed environment is in its exact reviewed state.

    Two regressions in this module deliberately mutate the real installed
    environment and restore it.  Asserting the reviewed state before and after
    turns any interference — a concurrent run, or a restore that did not take —
    into an explicit failure here instead of a confusing refusal somewhere else.
    """

    authority = next(
        entry
        for entry in r1.frozen_third_party_authority()
        if entry.distribution == distribution
    )
    observation = r1.observe_installed_distributions((authority,))[0]
    protocol.verify_installed_distribution_content(
        authority, observation, bytecode_namespace_enforced=True
    )


def _admit(request: dict, launch=None, context=None, **kwargs):
    return r1.run_isolated_scientific_request(
        CONTEXT if context is None else context,
        request,
        LAUNCH if launch is None else launch,
        **kwargs,
    )


def _refusal(request: dict, launch=None, **kwargs) -> dict:
    outcome = r1.run_scientific_worker(
        request, LAUNCH if launch is None else launch, **kwargs
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
    assert DECISION["program_ticket"] == "POSTP1-001V2A-PAD4-R1"
    assert DECISION["status"] == (
        "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
    )
    assert DECISION["final_classification"] == (
        "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_R1_READY_FOR_FINAL_XHIGH_REVIEW"
    )
    for token in (
        "CERTIFIED_SOURCE_AUTHORITY",
        "FROZEN_THIRD_PARTY_ARTIFACT_AUTHORITY",
        "FROZEN_CPYTHON",
        "FRESH_EMPTY_BYTECODE_CACHE_NAMESPACE",
        "CLOSED_STORE_GRAMMAR",
        "COMPILED_ROOT_WITNESS",
        "ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER",
        "TRUSTED_CONTROLLER_AUTHORITY_CONTEXT",
    ):
        assert token in DECISION["proof_strategy"]
    assert DECISION["pre_data"] is True
    assert DECISION["required_review"].startswith("POSTP1-002V2A-PAD4-R1")
    assert DECISION["correction_is_a_new_architecture_family"] is False


def test_material_children_are_mechanical_bound_and_digest_valid() -> None:
    children = r1._children()
    assert DECISION["material_child_count"] == len(r1._CHILD_ARTIFACTS) == 20
    assert set(DECISION["child_definition_sha256"]) == set(children)
    for name, child in children.items():
        r1._verify_definition_digest(child)
        assert DECISION["child_definition_sha256"][name] == child["definition_sha256"]
    assert set(children) >= {
        "bytecode_execution_binding_rule",
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
    }


def test_central_decisions_bind_the_corrected_anchors() -> None:
    central = DECISION["central_decisions"]
    assert central["fresh_exec_required"] is True
    assert central["fork_only_permitted"] is False
    assert central["one_request_one_process"] is True
    assert central["fresh_empty_pycache_namespace_required"] is True
    assert central["repository_pycache_authoritative"] is False
    assert central["cached_bytecode_may_override_certified_source"] is False
    assert central["runtime_source_manifest_rederivation_permitted"] is False
    assert central["request_is_authority_root"] is False
    assert central["response_echo_is_authority_root"] is False
    assert central["trusted_controller_authority_context_required"] is True
    assert central["pre_i2_116_module_manifest_role"] == (
        "CONFORMANCE_FIXTURE_NOT_FINAL_PRODUCTION_AUTHORITY"
    )
    assert central["final_i2_source_manifest_must_be_calendar_parent_bound"] is True
    assert central["third_party_exact_reviewed_versions_required"] is True
    assert central["third_party_reviewed_artifact_identity_required"] is True
    assert central["record_declared_installed_file_hashes_must_be_verified"] is True
    assert central["arbitrary_installed_version_self_certification_permitted"] is False
    assert central["pickle_ipc_permitted"] is False
    assert central["worker_network_permitted"] is False
    assert central["worker_private_signing_key_permitted"] is False
    assert central["worker_authoritative_db_write_permitted"] is False
    assert central["lazy_result_permitted"] is False
    assert central["runtime_object_closure_is_completeness_proof"] is False
    assert central["candidate_parent_hash_self_embedded"] is False
    assert central["calendar_science_changed"] is False
    assert central["calendar_production_code_changed"] is False


def test_repaired_findings_and_the_not_reopened_scope_are_explicit() -> None:
    assert DECISION["repaired_review_findings"] == [
        "A_EXECUTED_BYTECODE_NOT_BOUND_TO_CERTIFIED_SOURCE",
        "B_CERTIFIED_SOURCE_AUTHORITY_NOT_FROZEN",
        "C_CONTROLLER_AUTHORITY_BINDING_INVALID",
        "D_THIRD_PARTY_INSTALLED_CONTENT_AND_SEMANTIC_AUTHORITY_NOT_ATTESTED",
    ]
    assert DECISION["not_reopened"] == [
        "GENERATED_METHOD_ENUMERATION",
        "REFLECTION_BLACKLIST_COMPLETENESS",
        "SAME_PROCESS_RUNTIME_OWNER_ATTESTATION",
        "TRANSITIVE_MUTABLE_OBJECT_CLOSURE",
    ]
    boundary = r1.trusted_process_and_isolation_boundary()
    assert boundary["reopened_by_this_correction"] == []
    assert boundary["isolation_boundary_was_the_defect"] is False
    assert boundary["isolation_boundary_preserved_from_the_reviewed_pad4_candidate"]


def test_failed_pad4_is_preserved_immutably_and_never_certified() -> None:
    assert DECISION["failed_pad4_sha256"] == r1.FAILED_PAD4_SHA256
    assert DECISION["failed_pad4_certified"] is False
    assert DECISION["failed_pad4_artifacts_overwritten"] is False
    assert ARTIFACT_DIR != PAD4_ARTIFACT_DIR
    # The failed PAD4 namespace still reproduces exactly and is untouched.
    assert pad4.restore_artifacts(PAD4_ARTIFACT_DIR)["definition_sha256"] == (
        r1.FAILED_PAD4_SHA256
    )
    lineage = r1.science_lineage_and_safety()["failed_architecture_lineage"]
    assert [row["definition_sha256"] for row in lineage][-1] == r1.FAILED_PAD4_SHA256
    assert len(lineage) == len(set(row["definition_sha256"] for row in lineage))
    for row in lineage:
        assert row["certified"] is False
        assert row["failed"] is True
        assert row["used"] is False
        assert row["prospective_observations"] == 0
        assert row["immutable"] is True


def test_trusted_persistence_and_safety_are_unchanged() -> None:
    assert r1.CERTIFIED_DEPENDENCY_SHA256 == (
        "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
    )
    assert DECISION["certified_dependency_sha256"] == r1.CERTIFIED_DEPENDENCY_SHA256
    authorization = DECISION["authorization"]
    assert authorization["independent_proof_architecture_xhigh_review_may_begin"]
    assert authorization["calendar_implementation_may_begin"] is False
    assert authorization["postp1_001v2a_i2_may_begin"] is False
    assert authorization["postp1_001v2r1_may_begin"] is False
    assert authorization["prospective_collection_may_begin"] is False
    lineage = r1.science_lineage_and_safety()
    assert lineage["preserved_science"]["etf_calendar_production_code_changed_by_this_decision"] is False


def test_write_and_restore_artifacts_round_trip(tmp_path: Path) -> None:
    decision = r1.write_artifacts(tmp_path)
    assert decision == DECISION
    assert r1.restore_artifacts(tmp_path) == DECISION
    assert {path.name for path in tmp_path.iterdir()} == {
        r1.DEFINITION_FILENAME,
        r1.REPORT_FILENAME,
        *(filename for filename, _ in r1._CHILD_ARTIFACTS),
    }


def test_persisted_namespace_reproduces_exactly() -> None:
    assert r1.restore_artifacts(ARTIFACT_DIR)["definition_sha256"] == CANDIDATE_HASH


def test_restore_refuses_a_mutated_child(tmp_path: Path) -> None:
    r1.write_artifacts(tmp_path)
    target = tmp_path / "bytecode_execution_binding_rule.json"
    payload = json.loads(target.read_text())
    payload["cached_bytecode_may_override_certified_source"] = True
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(
        r1.IsolatedScientificWorkerR1Error, match="does not reproduce"
    ):
        r1.restore_artifacts(tmp_path)


def test_restore_refuses_a_mutated_report(tmp_path: Path) -> None:
    r1.write_artifacts(tmp_path)
    report = tmp_path / r1.REPORT_FILENAME
    report.write_text(report.read_text() + "drift\n", encoding="utf-8")
    with pytest.raises(
        r1.IsolatedScientificWorkerR1Error, match="report does not reproduce"
    ):
        r1.restore_artifacts(tmp_path)


def test_child_order_variation_does_not_change_the_parent() -> None:
    reversed_registry = tuple(reversed(r1._CHILD_ARTIFACTS))
    assert r1.isolated_scientific_worker_v1_r1_definition(reversed_registry) == DECISION


MATERIAL_MUTATIONS: tuple[tuple[str, str, object], ...] = (
    (
        "bytecode_execution_binding_rule",
        "fresh_cache_namespace_per_worker",
        False,
    ),
    (
        "bytecode_execution_binding_rule",
        "cached_bytecode_may_override_certified_source",
        True,
    ),
    (
        "project_source_manifest_binding_rule",
        "runtime_source_manifest_rederivation_permitted",
        True,
    ),
    (
        "controller_authority_context_rule",
        "trusted_controller_authority_context_required",
        False,
    ),
    (
        "controller_result_admission_rule",
        "response_equals_request_is_sufficient",
        True,
    ),
    (
        "pre_i2_project_source_manifest_fixture",
        "is_final_production_scientific_source_authority",
        True,
    ),
    (
        "project_source_manifest_binding_rule",
        "final_i2_source_manifest_must_be_calendar_parent_bound",
        False,
    ),
    (
        "third_party_semantic_authority",
        "third_party_exact_reviewed_versions_required",
        False,
    ),
    (
        "third_party_installed_content_attestation_rule",
        "record_declared_installed_file_hashes_must_be_verified",
        False,
    ),
    (
        "third_party_semantic_authority",
        "third_party_reviewed_artifact_identity_required",
        False,
    ),
    ("worker_launch_contract", "one_request_one_exec_process", False),
    (
        "store_root_and_direct_use_grammar",
        "root_may_be_a_cell_variable_of_a_conforming_owner",
        True,
    ),
    (
        "direct_body_dependency_rule",
        "wrapper_installed_guards_permitted",
        True,
    ),
)


@pytest.mark.parametrize("child,field,value", MATERIAL_MUTATIONS)
def test_material_mutation_moves_both_child_and_parent_hashes(
    child: str, field: str, value: object
) -> None:
    builders = dict(r1._CHILD_ARTIFACTS)
    original = builders[f"{child}.json"]
    assert field in original(), f"{child} does not declare {field}"

    def mutated() -> dict:
        payload = original()
        payload.pop("definition_sha256")
        payload[field] = value
        return r1._definition(payload)

    registry = tuple(
        (name, mutated if name == f"{child}.json" else builder)
        for name, builder in r1._CHILD_ARTIFACTS
    )
    changed = r1.isolated_scientific_worker_v1_r1_definition(registry)
    assert changed["child_definition_sha256"][child] != (
        DECISION["child_definition_sha256"][child]
    )
    assert changed["definition_sha256"] != CANDIDATE_HASH


@pytest.mark.parametrize("seed", ["0", "1", "8675309"])
def test_definition_is_deterministic_across_hash_seeds(
    seed: str, tmp_path: Path
) -> None:
    script = (
        "from btc_predictor.research import "
        "etf_calendar_isolated_scientific_worker_r1 as w;"
        "print(w.isolated_scientific_worker_v1_r1_definition()['definition_sha256'])"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=True,
        cwd=str(tmp_path),
        env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(ROOT)),
    )
    assert completed.stdout.decode().strip() == CANDIDATE_HASH


def test_artifacts_reproduce_from_an_alternate_working_directory(
    tmp_path: Path,
) -> None:
    output = tmp_path / "fresh"
    script = (
        "import sys;from pathlib import Path;"
        "from btc_predictor.research import "
        "etf_calendar_isolated_scientific_worker_r1 as w;"
        "print(w.write_artifacts(Path(sys.argv[1]))['definition_sha256'])"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(output)],
        capture_output=True,
        check=True,
        cwd=str(tmp_path),
        env=dict(os.environ, PYTHONPATH=str(ROOT)),
    )
    assert completed.stdout.decode().strip() == CANDIDATE_HASH
    assert r1.restore_artifacts(output) == DECISION


def test_operational_pycache_paths_do_not_contaminate_authority_hashes(
    tmp_path: Path,
) -> None:
    """Operational cache namespaces are launch material, never authority."""

    namespace = r1.allocate_worker_pycache_namespace(tmp_path / "cache")
    serialized = json.dumps(DECISION, sort_keys=True)
    assert str(namespace) not in serialized
    assert str(r1.controller_pycache_root()) not in serialized
    assert "etf-calendar-worker-pycache-" not in serialized
    assert "/tmp/" not in serialized
    # A different namespace root does not move the parent hash.
    assert r1.isolated_scientific_worker_v1_r1_definition() == DECISION


def test_candidate_hash_is_not_embedded_in_its_own_certified_source() -> None:
    """Section 21: no cryptographic self-hash fixed point is attempted."""

    for entry in MANIFEST:
        text = (ROOT / entry.path).read_text(encoding="utf-8")
        assert CANDIDATE_HASH not in text, entry.path
    rule = r1.controller_authority_context_rule()
    assert rule["self_hash_fixed_point_attempted"] is False
    assert rule["candidate_review_context_binds_the_recomputed_parent_hash"] is True
    assert rule["candidate_review_context_expected_hash_source"] == (
        "TRUSTED_REVIEW_OR_CONTROLLER_CONTEXT_NEVER_THE_SCIENTIFIC_REQUEST"
    )
    assert rule["final_i2_certified_hash_binding_required"] is True


# ---------------------------------------------------------------------------
# Frozen interpreter and launch contract
# ---------------------------------------------------------------------------


def test_worker_protocol_binds_the_compiled_witness_interpreter_identity() -> None:
    assert r1.verify_worker_protocol_binds_the_frozen_interpreter() == dict(
        sorted(r1.PROOF_INTERPRETER_IDENTITY.items())
    )
    assert dict(protocol.PROOF_INTERPRETER_IDENTITY) == dict(
        r1.PROOF_INTERPRETER_IDENTITY
    )
    assert protocol.PROOF_INTERPRETER_IDENTITY["version_micro"] == 14
    assert protocol.PROOF_INTERPRETER_IDENTITY["cache_tag"] == "cpython-312"
    assert protocol.PROOF_INTERPRETER_IDENTITY["magic_number_hex"] == "cb0d0d0a"


def test_worker_launch_uses_exec_isolation_and_a_fresh_pycache_namespace(
    tmp_path: Path,
) -> None:
    namespace = r1.allocate_worker_pycache_namespace(tmp_path / "cache")
    argv = LAUNCH.argv_for(namespace)
    assert argv[0] == sys.executable
    assert argv[1:4] == ("-I", "-S", "-B")
    assert argv[4] == "-X"
    assert argv[5] == f"pycache_prefix={namespace}"
    assert argv[6] == str(ROOT / protocol.WORKER_ENTRYPOINT_RELATIVE_PATH)
    assert json.loads(argv[7]) == list(LAUNCH.sys_path)
    assert argv[8] == str(namespace)
    assert LAUNCH.mechanism == r1.EXEC_LAUNCH
    assert dict(LAUNCH.environment) == dict(r1.FROZEN_WORKER_ENVIRONMENT)
    assert not any(name.startswith("PYTHON") for name in LAUNCH.environment)
    assert str(ROOT) in LAUNCH.sys_path


def test_fork_only_worker_is_not_an_authorized_scientific_worker() -> None:
    assert r1.authorize_worker_launch_mechanism(r1.EXEC_LAUNCH) == r1.EXEC_LAUNCH
    for mechanism in r1.UNAUTHORIZED_LAUNCH_MECHANISMS:
        with pytest.raises(
            r1.IsolatedScientificWorkerR1Error,
            match="NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER",
        ):
            r1.authorize_worker_launch_mechanism(mechanism)
    forked = replace(LAUNCH, mechanism=r1.FORK_WITHOUT_EXEC)
    with pytest.raises(
        r1.IsolatedScientificWorkerR1Error,
        match="NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER",
    ):
        r1.run_scientific_worker(SESSION_REQUEST, forked)


def test_a_forked_child_inherits_the_parent_mutation_that_exec_does_not(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Why the proof depends on exec: fork keeps the parent's mutable state."""

    monkeypatch.setattr(_flow, "FIVE_DAY_ETF_FLOW_FEATURE_ID", "WRONG")
    read, write = os.pipe()
    pid = os.fork()
    if pid == 0:  # pragma: no cover - executed in the forked child
        try:
            os.close(read)
            os.write(write, _flow.FIVE_DAY_ETF_FLOW_FEATURE_ID.encode("ascii"))
            os.close(write)
        finally:
            os._exit(0)
    os.close(write)
    inherited = os.read(read, 64).decode("ascii")
    os.close(read)
    os.waitpid(pid, 0)
    assert inherited == "WRONG"


def test_wrong_interpreter_refuses_before_any_project_import(tmp_path: Path) -> None:
    namespace = r1.allocate_worker_pycache_namespace(tmp_path / "cache")
    drifted = dict(SESSION_REQUEST)
    drifted["interpreter_identity"] = dict(
        SESSION_REQUEST["interpreter_identity"], version_micro=99
    )
    completed = subprocess.run(
        list(LAUNCH.argv_for(namespace)),
        input=protocol.canonical_json_bytes(drifted),
        capture_output=True,
        cwd=str(ROOT),
        env=dict(LAUNCH.environment),
        timeout=protocol.DEFAULT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 5
    assert completed.stdout == b""
    assert b"REFUSE_SCIENTIFIC_AUTHORITY" in completed.stderr


# ---------------------------------------------------------------------------
# Repair A — executed bytecode is bound to certified source
# ---------------------------------------------------------------------------


def _forged_package(tmp_path: Path) -> tuple[Path, Path]:
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "__init__.py").write_text("", encoding="utf-8")
    module = package / "mod.py"
    module.write_text('FEATURE_ID = "CERTIFIED"\n', encoding="utf-8")
    forge_pyc(
        module,
        package / "__pycache__" / "mod.cpython-312.pyc",
        'FEATURE_ID = "FORGED_BYTECODE_ID"',
    )
    return tmp_path, module


def test_the_pad4_bytecode_defect_reproduces_without_a_fresh_namespace(
    tmp_path: Path,
) -> None:
    """The exact review defect, and the exact structural repair, side by side."""

    root, module = _forged_package(tmp_path)
    assert "FORGED" not in module.read_text(encoding="utf-8")
    probe = (
        "import sys;sys.path.insert(0,sys.argv[1]);"
        "import pkg.mod as m;print(m.FEATURE_ID)"
    )
    pad4_style = subprocess.run(
        [sys.executable, "-I", "-S", "-B", "-c", probe, str(root)],
        capture_output=True,
        check=True,
        env=dict(r1.FROZEN_WORKER_ENVIRONMENT),
    )
    assert pad4_style.stdout.decode().strip() == "FORGED_BYTECODE_ID"

    namespace = r1.allocate_worker_pycache_namespace(tmp_path / "cache")
    corrected = subprocess.run(
        [
            sys.executable,
            "-I",
            "-S",
            "-B",
            "-X",
            f"pycache_prefix={namespace}",
            "-c",
            probe,
            str(root),
        ],
        capture_output=True,
        check=True,
        env=dict(r1.FROZEN_WORKER_ENVIRONMENT),
    )
    assert corrected.stdout.decode().strip() == "CERTIFIED"


def test_forged_repository_pyc_is_not_executed_by_a_real_worker(
    tmp_path: Path,
) -> None:
    """Section 9: the exact PAD4 failure, closed against a real worker."""

    root = certified_tree(tmp_path / "tree")
    flow_source = root / "btc_predictor/features/flow.py"
    certified_bytes = flow_source.read_bytes()
    forged_text = flow_source.read_text(encoding="utf-8").replace(
        'FIVE_DAY_ETF_FLOW_FEATURE_ID = "ETF_FLOW_5D"',
        'FIVE_DAY_ETF_FLOW_FEATURE_ID = "FORGED_BYTECODE_ID"',
    )
    assert "FORGED_BYTECODE_ID" in forged_text
    forge_pyc(
        flow_source,
        root / "btc_predictor/features/__pycache__/flow.cpython-312.pyc",
        forged_text,
    )
    # the certified .py source is byte-for-byte unchanged
    assert flow_source.read_bytes() == certified_bytes
    assert flow_source.read_bytes() == (ROOT / "btc_predictor/features/flow.py").read_bytes()

    launch = r1.worker_launch(project_root=root)
    admission = _admit(flow_request(launch=launch), launch=launch)
    assert admission.admitted, admission.failure_reason
    assert admission.result["feature"]["feature_id"] == "ETF_FLOW_5D"
    assert admission.response["bytecode_cache_binding"] == "PASS"


def test_controlled_cache_poisoning_refuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Section 10: a pre-populated 'fresh' namespace never silently passes."""

    poisoned = tmp_path / "poisoned"
    poisoned.mkdir()
    (poisoned / "stale.pyc").write_bytes(b"\x00")
    with pytest.raises(r1.IsolatedScientificWorkerR1Error, match="is not fresh"):
        r1.create_fresh_pycache_namespace(poisoned)
    # The worker entrypoint refuses before it imports even the certified
    # protocol module, so the refusal is an early typed exit with no stdout.
    outcome = r1.run_scientific_worker(
        SESSION_REQUEST, LAUNCH, pycache_namespace=poisoned
    )
    assert outcome.exit_status == 6
    assert outcome.stdout == b""
    assert b"bytecode cache namespace is not the fresh" in outcome.stderr
    admission = r1.admit_worker_result(CONTEXT, SESSION_REQUEST, outcome)
    assert admission.admitted is False
    assert admission.failure_reason == "WORKER_EXIT_STATUS_6"
    # the owning protocol authority states the same refusal
    monkeypatch.setattr(sys, "pycache_prefix", str(poisoned))
    monkeypatch.setattr(sys, "dont_write_bytecode", True)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="BYTECODE_CACHE_NAMESPACE_IS_NOT_FRESH",
    ):
        protocol.verify_bytecode_cache_namespace(str(poisoned))
    fresh = r1.allocate_worker_pycache_namespace(tmp_path / "fresh")
    monkeypatch.setattr(sys, "pycache_prefix", str(fresh))
    assert protocol.verify_bytecode_cache_namespace(str(fresh))[
        "bytecode_cache_namespace_fresh_and_empty"
    ]
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="WORKER_MAY_WRITE_CACHED_BYTECODE",
    ):
        protocol.verify_bytecode_cache_namespace(str(fresh))


def test_a_missing_cache_namespace_refuses(tmp_path: Path) -> None:
    missing = tmp_path / "absent"
    outcome = r1.run_scientific_worker(
        SESSION_REQUEST, LAUNCH, pycache_namespace=missing
    )
    assert outcome.exit_status == 6
    assert outcome.stdout == b""
    assert b"bytecode cache namespace" in outcome.stderr


def test_forged_third_party_pyc_is_not_executed(tmp_path: Path) -> None:
    """Section 46: install-generated site-packages bytecode is never consulted."""

    _assert_reviewed_dependency_state("alembic")
    location = Path(
        r1.observe_installed_distributions(r1.frozen_third_party_authority())[0].location
    )
    source = location / "alembic" / "__init__.py"
    assert source.is_file()
    cached = location / "alembic" / "__pycache__" / "__init__.cpython-312.pyc"
    marker = tmp_path / "forged-third-party-executed"
    forged_text = (
        source.read_text(encoding="utf-8")
        + "\nimport pathlib as _p\n"
        + f"_p.Path({str(marker)!r}).write_text('executed')\n"
    )
    original = cached.read_bytes() if cached.is_file() else None
    try:
        forge_pyc(source, cached, forged_text)
        admission = _admit(SESSION_REQUEST)
        assert admission.admitted, admission.failure_reason
        assert not marker.exists()
    finally:
        if original is None:
            cached.unlink(missing_ok=True)
        else:
            cached.write_bytes(original)
    _assert_reviewed_dependency_state("alembic")


def test_loaded_module_bytecode_must_be_bound_to_the_fresh_namespace(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    namespace = r1.allocate_worker_pycache_namespace(tmp_path / "cache")
    module = types.ModuleType("btc_predictor")
    module.__cached__ = str(tmp_path / "elsewhere" / "btc_predictor.pyc")
    monkeypatch.setitem(sys.modules, "btc_predictor", module)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="MODULE_BYTECODE_IS_NOT_BOUND_TO_THE_FRESH_CACHE_NAMESPACE",
    ):
        protocol.verify_loaded_module_bytecode_binding(
            str(namespace), ("btc_predictor",), "PRE_EXECUTION"
        )


def test_a_sourceless_project_module_origin_refuses(tmp_path: Path) -> None:
    """Section 11: a module loaded from a .pyc is not its certified .py origin.

    A fresh cache namespace does not cover this case at all: a *sourceless*
    ``flow/__init__.pyc`` package shadows the certified ``flow.py`` module and
    executes different code regardless of ``sys.pycache_prefix``.  The exact
    ``__file__`` and ``__spec__.origin`` source-path checks are what close it,
    which is why both layers are required.
    """

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
    launch = r1.worker_launch(project_root=root)
    assert _refusal(session_request(launch=launch), launch=launch)[
        "failure_reason"
    ] == "WRONG_PROJECT_MODULE_ORIGIN"


def test_a_pyc_only_project_module_can_never_satisfy_the_frozen_manifest(
    tmp_path: Path,
) -> None:
    root = certified_tree(tmp_path / "tree")
    flow_source = root / "btc_predictor/features/flow.py"
    forge_pyc(flow_source, root / "btc_predictor/features/flow.pyc", "X = 1")
    flow_source.unlink()
    launch = r1.worker_launch(project_root=root)
    assert _refusal(session_request(launch=launch), launch=launch)[
        "failure_reason"
    ] == "CERTIFIED_SOURCE_FILE_MISSING"


def test_the_cache_namespace_may_not_be_shared_with_the_project_tree(
    tmp_path: Path,
) -> None:
    import shutil
    import tempfile

    inside = Path(tempfile.mkdtemp(dir=str(ROOT), prefix=".r1-cache-probe-"))
    try:
        with pytest.raises(
            protocol.ScientificWorkerProtocolError,
            match="BYTECODE_CACHE_NAMESPACE_IS_SHARED_WITH_THE_PROJECT_TREE",
        ):
            protocol.verify_cache_namespace_is_not_shared_with_the_project(
                str(inside), ROOT
            )
    finally:
        shutil.rmtree(inside, ignore_errors=True)
    outside = r1.allocate_worker_pycache_namespace(tmp_path / "cache")
    protocol.verify_cache_namespace_is_not_shared_with_the_project(str(outside), ROOT)


# ---------------------------------------------------------------------------
# Repair B — frozen certified source authority
# ---------------------------------------------------------------------------


def test_frozen_pre_i2_fixture_is_the_reviewed_source_universe() -> None:
    assert r1.verify_frozen_pre_i2_fixture() == {
        "module_count": 116,
        "manifest_digest": (
            "674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8"
        ),
    }
    assert DECISION["pre_i2_project_source_module_count"] == 116
    assert DECISION["pre_i2_project_source_manifest_digest"] == (
        "674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8"
    )


def test_the_fixture_role_is_provenance_never_production_authority() -> None:
    fixture = r1.pre_i2_project_source_manifest_fixture()
    assert fixture["role"] == "PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE"
    assert fixture["is_final_production_scientific_source_authority"] is False
    assert fixture["immutable_when_i2_later_changes_source"] is True
    assert fixture["i2_will_change_at_least"] == [
        "btc_predictor/research/etf_publication_calendar.py"
    ]
    assert fixture["future_production_source_manifest_role"] == (
        "I2_DERIVED_AND_FINAL_CALENDAR_PARENT_BOUND"
    )
    rule = r1.project_source_manifest_binding_rule()
    assert rule["final_i2_source_manifest_owner"] == "POSTP1-001V2A-I2"
    assert rule["final_i2_source_manifest_parent"] == (
        "ETF_PUBLICATION_CALENDAR_AUTHORITY_V1"
    )
    assert rule["final_i2_source_manifest_derivation_time"] == (
        "AFTER_ALL_I2_SOURCE_CHANGES_ARE_COMPLETE"
    )
    assert rule["i2_may_narrow_the_source_universe"] is True
    assert rule["proof_architecture_hash_changes_when_production_manifest_narrows"] is (
        False
    )


def test_mechanical_derivation_reproduces_the_frozen_manifests() -> None:
    assert r1.derive_project_source_manifest(
        seeds=(r1.PRE_I2_FIXTURE_SEED_MODULE,)
    ) == r1.frozen_pre_i2_source_manifest()
    assert r1.derive_project_source_manifest() == r1.frozen_candidate_source_manifest()
    assert len(MANIFEST) == 119
    modules = {entry.module for entry in MANIFEST}
    assert {
        "btc_predictor.research.etf_calendar_scientific_worker_entry",
        "btc_predictor.research.etf_calendar_worker_protocol",
        "btc_predictor.research.etf_publication_calendar",
        "etf_calendar_worker",
        "etf_calendar_worker.entry_r1",
        "etf_calendar_worker.protocol_r1",
    } <= modules
    assert r1.external_import_roots(entries=MANIFEST) == (
        "alembic",
        "cryptography",
        "numpy",
        "scipy",
        "sqlalchemy",
    )


def test_the_request_builder_exposes_no_authority_parameter() -> None:
    """Section 18: no raw decision-hash or manifest parameter may exist."""

    import inspect

    parameters = set(inspect.signature(r1.build_scientific_request).parameters)
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
    assert "third_party_manifest" not in parameters
    with pytest.raises(
        r1.IsolatedScientificWorkerR1Error, match="trusted controller authority context"
    ):
        r1.build_scientific_request(
            {"worker_authority_sha256": ZERO_HASH},
            launch=LAUNCH,
            operation="common_etf_session_status",
            operation_inputs={"trade_date": SESSION_DAY.isoformat()},
            evidence_records=SESSION_RECORDS,
            decision_time=DECISION_TIME.isoformat(),
        )


@pytest.mark.parametrize(
    "relative",
    [
        "btc_predictor/features/flow.py",
        "etf_calendar_worker/entry_r1.py",
        "etf_calendar_worker/protocol_r1.py",
        "btc_predictor/research/etf_calendar_scientific_worker_entry.py",
        "btc_predictor/research/etf_calendar_worker_protocol.py",
    ],
)
def test_pre_request_source_drift_cannot_redefine_scientific_authority(
    relative: str, tmp_path: Path
) -> None:
    """Sections 29, 30 and 72: drift before request construction fails closed."""

    root = certified_tree(tmp_path / "tree", mutate=relative)
    launch = r1.worker_launch(project_root=root)
    # the ordinary builder, using the trusted authority context
    request = session_request(launch=launch)
    # the request is still bound to the frozen expected manifest
    assert request["project_source_manifest_digest"] == (
        CONTEXT.project_source_manifest_digest
    )
    assert r1.verify_request_against_authority_context(CONTEXT, request) == ()
    expected = {
        "etf_calendar_worker/entry_r1.py": "WORKER_ENTRYPOINT_SOURCE_MISMATCH",
        "etf_calendar_worker/protocol_r1.py": "WORKER_PROTOCOL_SOURCE_MISMATCH",
    }.get(relative, "CERTIFIED_SOURCE_SHA_MISMATCH")
    assert _refusal(request, launch=launch)["failure_reason"] == expected
    admission = _admit(request, launch=launch)
    assert admission.admitted is False


def test_manifest_row_shape_and_ordering_are_enforced() -> None:
    rows = [entry.as_material() for entry in MANIFEST]
    assert protocol.project_source_entries(rows) == MANIFEST
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="ROW_SHAPE_REFUSED"
    ):
        protocol.project_source_entries([dict(rows[0], extra=1)])
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="MODULE_REFUSED"
    ):
        protocol.project_source_entries([dict(rows[0], module="os")])
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="PATH_REFUSED"
    ):
        protocol.project_source_entries([dict(rows[0], path="/etc/passwd")])
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="NOT_CANONICALLY_ORDERED"
    ):
        protocol.project_source_entries(list(reversed(rows)))
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="DUPLICATE_MODULE"
    ):
        protocol.project_source_entries([rows[0], rows[0]])


def test_unexpected_project_module_refuses() -> None:
    reduced = tuple(
        entry
        for entry in MANIFEST
        if entry.module != "btc_predictor.research.strategy_promotion"
    )
    assert len(reduced) == len(MANIFEST) - 1
    context = replace(CONTEXT, project_source_manifest=reduced)
    assert _refusal(session_request(context=context))["failure_reason"] == (
        "UNEXPECTED_PROJECT_MODULE"
    )


# ---------------------------------------------------------------------------
# Repair C — the trusted controller authority context
# ---------------------------------------------------------------------------


def test_the_authority_context_cannot_be_built_from_a_request_or_response() -> None:
    for name in ("from_request", "from_response", "from_payload"):
        assert not hasattr(r1.ScientificWorkerAuthorityContext, name)
    assert CONTEXT.origin == r1.REVIEW_CANDIDATE_CONTEXT
    assert CONTEXT.proof_architecture_sha256 == CANDIDATE_HASH
    rule = r1.controller_authority_context_rule()
    assert rule["request_can_construct_the_authority_context"] is False
    assert rule["response_can_construct_the_authority_context"] is False
    assert rule["live_disk_can_silently_replace_the_authority_context"] is False
    assert rule["installed_environment_can_silently_replace_the_authority_context"] is (
        False
    )
    assert rule["raw_caller_supplied_decision_hash_parameter"] is False
    assert rule["caller_request_worker_agreement_is_sufficient"] is False
    assert rule["agreement_with_trusted_controller_authority_also_required"] is True


@pytest.mark.parametrize("forged", [ZERO_HASH, DEADBEEF_HASH])
def test_a_wrong_self_consistent_decision_hash_is_never_admitted(
    forged: str,
) -> None:
    """Sections 20 and 71: request and response may agree and still be refused."""

    tampered = dict(SESSION_REQUEST, worker_authority_sha256=forged)
    admission = _admit(tampered)
    assert admission.admitted is False
    assert admission.failure_reason.startswith("REQUEST_AUTHORITY_MISMATCH")
    assert "worker_authority_sha256" in admission.failure_reason
    # the worker itself still echoes the forged value consistently
    outcome = r1.run_scientific_worker(tampered, LAUNCH)
    assert outcome.exit_status == 0
    response = json.loads(outcome.stdout.decode())
    assert response["status"] == "SUCCESS"
    assert response["worker_authority_sha256"] == forged
    assert r1.verify_response_against_authority_context(CONTEXT, response) == (
        ("worker_authority_sha256",)
    )


def test_a_context_expecting_a_different_hash_refuses_a_consistent_request() -> None:
    wrong_context = r1.candidate_review_authority_context(DEADBEEF_HASH)
    admission = _admit(SESSION_REQUEST, context=wrong_context)
    assert admission.admitted is False
    assert admission.failure_reason.startswith("REQUEST_AUTHORITY_MISMATCH")


def test_a_response_that_drifts_from_the_trusted_context_is_not_admitted() -> None:
    outcome = r1.run_scientific_worker(SESSION_REQUEST, LAUNCH)
    response = json.loads(outcome.stdout.decode())
    drifted = dict(response, project_source_manifest_digest=ZERO_HASH)
    replayed = r1.WorkerProcessOutcome(
        exit_status=0,
        timed_out=False,
        stdout=protocol.canonical_json_bytes(drifted) + b"\n",
        stderr=b"",
        request_digest=outcome.request_digest,
    )
    admission = r1.admit_worker_result(CONTEXT, SESSION_REQUEST, replayed)
    assert admission.admitted is False
    assert admission.failure_reason.startswith("RESPONSE_AUTHORITY_MISMATCH")


def test_the_production_authority_context_requires_the_i2_binding() -> None:
    """Sections 23, 24 and 27: production authority comes from the calendar."""

    with pytest.raises(
        r1.IsolatedScientificWorkerR1Error,
        match=r1.PRODUCTION_CONTEXT_NOT_YET_BOUND,
    ):
        r1.production_authority_context_from_calendar_authority({})
    with pytest.raises(
        r1.IsolatedScientificWorkerR1Error,
        match=r1.PRODUCTION_CONTEXT_NOT_YET_BOUND,
    ):
        r1.production_authority_context_from_calendar_authority(
            {r1.FINAL_CALENDAR_AUTHORITY_WORKER_FIELD: {"proof_architecture_sha256": ""}}
        )
    rule = r1.controller_authority_context_rule()
    assert rule["production_authority_context_available_today"] is False
    assert rule["final_production_context_may_never_come_from"] == [
        "AMBIENT_ENVIRONMENT",
        "CALLER_SELECTED_SHA",
        "CURRENT_FILESYSTEM",
        "THE_SCIENTIFIC_REQUEST",
    ]


def test_a_calendar_bound_production_context_is_accepted_once_i2_binds_it() -> None:
    """The frozen production rule, exercised against a simulated I2 binding."""

    bound = {
        r1.FINAL_CALENDAR_AUTHORITY_WORKER_FIELD: {
            "proof_architecture_sha256": CANDIDATE_HASH,
            "project_source_manifest": [entry.as_material() for entry in MANIFEST],
            "required_project_modules": list(r1.REQUIRED_WORKER_PROJECT_MODULES),
            "third_party_authority": [
                entry.as_material() for entry in r1.frozen_third_party_authority()
            ],
        }
    }
    context = r1.production_authority_context_from_calendar_authority(bound)
    assert context.origin == r1.FINAL_CALENDAR_AUTHORITY
    assert context.proof_architecture_sha256 == CANDIDATE_HASH
    assert context.project_source_manifest_role == (
        "POST_I2_FINAL_CALENDAR_PARENT_BOUND_PRODUCTION_AUTHORITY"
    )
    # A request built from the review context does not satisfy a production one.
    assert "project_source_manifest_role" in r1.verify_request_against_authority_context(
        context, SESSION_REQUEST
    )


def test_authority_construction_is_separate_from_runtime_admission() -> None:
    derived = r1.derive_authority_context_from_reviewed_source(CANDIDATE_HASH)
    assert derived.origin == r1.AUTHORITY_CONSTRUCTION_REFREEZE
    assert derived.project_source_manifest == CONTEXT.project_source_manifest
    assert derived.third_party_authority == CONTEXT.third_party_authority
    rule = r1.project_source_manifest_binding_rule()
    assert rule["runtime_source_manifest_rederivation_permitted"] is False
    assert rule["runtime_request_construction_derives_authority_from_live_disk"] is False
    assert sorted(rule["mechanical_derivation_is_used_for"]) == [
        "AUTHORITY_CONSTRUCTION",
        "CONSISTENCY_CHECKING",
        "REFREEZE",
        "REVIEW",
    ]
    assert rule["mechanical_derivation_is_used_for_runtime_authority_selection"] is False


# ---------------------------------------------------------------------------
# Repair D — third-party semantic and installed-content authority
# ---------------------------------------------------------------------------


def test_the_frozen_registry_matches_the_reviewed_installed_environment() -> None:
    frozen = r1.frozen_third_party_authority()
    derived = r1.derive_third_party_authority(r1.external_import_roots())
    assert frozen == derived
    assert [entry.distribution for entry in frozen] == [
        "alembic",
        "cryptography",
        "numpy",
        "scipy",
        "sqlalchemy",
    ]
    assert [entry.version for entry in frozen] == [
        "1.19.1",
        "50.0.1",
        "2.5.2",
        "1.18.1",
        "2.0.52",
    ]
    assert DECISION["third_party_authority_digest"] == (
        protocol.third_party_authority_digest(frozen)
    )


def test_record_hash_algorithm_policy_is_frozen_and_never_skips() -> None:
    assert protocol.ACCEPTED_RECORD_HASH_ALGORITHMS == ("sha256",)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="unreviewed RECORD hash algorithm"
    ):
        protocol.parse_record_rows("a/b.py,md5=aGVsbG8,3\n", "probe")
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="malformed RECORD hash"
    ):
        protocol.parse_record_rows("a/b.py,notahash,3\n", "probe")
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="not a sha256 digest"
    ):
        protocol.parse_record_rows("a/b.py,sha256=aGVsbG8,3\n", "probe")
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="duplicate RECORD row"
    ):
        protocol.parse_record_rows("a/b.py,,3\na/b.py,,3\n", "probe")


def test_record_path_semantics_reject_ambiguous_traversal(tmp_path: Path) -> None:
    environment = tmp_path / "env"
    location = environment / "lib/python3.12/site-packages"
    location.mkdir(parents=True)
    (environment / "bin").mkdir()
    assert protocol.resolve_record_path(
        location, environment, "../../../bin/alembic", "probe"
    ) == (environment / "bin/alembic")
    for malformed in (
        "/etc/passwd",
        "a\\b.py",
        "a/./b.py",
        "a/../b.py",
        "~/b.py",
        "../../../../../../etc/passwd",
    ):
        with pytest.raises(
            protocol.ScientificWorkerProtocolError,
            match="NON_CERTIFIED_DEPENDENCY_ENVIRONMENT",
        ):
            protocol.resolve_record_path(location, environment, malformed, "probe")


def test_unhashed_record_rows_are_never_silently_certified() -> None:
    rule = r1.third_party_installed_content_attestation_rule()
    exceptions = rule["reviewed_unhashed_row_exceptions"]
    assert set(exceptions) == {
        protocol.RECORD_SELF_REFERENTIAL_EXCEPTION,
        protocol.RECORD_INSTALL_GENERATED_BYTECODE_EXCEPTION,
    }
    assert rule["any_other_unhashed_installed_file"] == "REFUSE"
    assert rule["missing_hashes_silently_treated_as_certified"] is False
    authority = r1.frozen_third_party_authority()[0]
    observation = r1.observe_installed_distributions((authority,))[0]
    evidence = protocol.verify_installed_distribution_content(
        authority, observation, bytecode_namespace_enforced=True
    )
    assert evidence["verified_installed_files"] == authority.hashed_row_count
    assert sorted(evidence["reviewed_unhashed_row_exceptions"]) == sorted(exceptions)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="declares\\s+no reviewed content hash"
    ):
        protocol.verify_installed_distribution_content(
            authority, observation, bytecode_namespace_enforced=False
        )


def test_record_verification_covers_compiled_extension_files() -> None:
    """Section 45: binary extension rows are verified, not only .py source."""

    authority = next(
        entry
        for entry in r1.frozen_third_party_authority()
        if entry.distribution == "numpy"
    )
    observation = r1.observe_installed_distributions((authority,))[0]
    rows = protocol.parse_record_rows(
        Path(observation.record_path).read_text(encoding="utf-8"),
        authority.distribution,
    )
    hashed = [row for row in rows if row.algorithm is not None]
    binary = [row for row in hashed if row.path.endswith((".so", ".pyd", ".dylib"))]
    assert binary, "the reviewed numpy artifact declares no hashed extension rows"
    evidence = protocol.verify_installed_distribution_content(
        authority, observation, bytecode_namespace_enforced=True
    )
    assert evidence["verified_installed_files"] == len(hashed)
    assert evidence["reviewed_record_sha256"] == authority.record_sha256
    assert evidence["observed_verified_content_manifest_digest"]


def test_the_frozen_proof_order_is_complete_and_dependency_safe() -> None:
    order = r1.proof_order_and_completeness_definition()
    assert [step.split("_", 1)[0] for step in order["controller_or_review_order"]] == [
        str(n) for n in range(1, 8)
    ]
    assert [step.split("_", 1)[0] for step in order["worker_order"]] == [
        str(n) for n in range(8, 21)
    ]
    assert [
        step.split("_", 1)[0] for step in order["controller_admission_order"]
    ] == [str(n) for n in range(21, 27)]
    assert order["dependency_code_executes_before_its_content_is_verified"] is False
    assert order["operational_pycache_paths_contaminate_authority_hashes"] is False
    assert order["no_scientific_call_before_self_verification_passes"] is True
    for required in (
        "ALTERED_INSTALLED_DEPENDENCY_FILE_WITH_UNCHANGED_RECORD_REFUSES",
        "CONTROLLED_CACHE_POISONING_REFUSES",
        "FORGED_PROJECT_PYC_IS_NOT_EXECUTED",
        "FORGED_THIRD_PARTY_PYC_IS_NOT_EXECUTED",
        "PRE_REQUEST_SOURCE_DRIFT_REFUSES",
        "SAME_VERSION_WRONG_ARTIFACT_REFUSES",
        "SOURCELESS_OR_WRONG_ORIGIN_PROJECT_MODULE_REFUSES",
        "WRONG_SELF_CONSISTENT_DECISION_HASH_IS_NOT_ADMITTED",
        "WRONG_THIRD_PARTY_VERSION_REFUSES",
    ):
        assert required in order["required_adversarial_regressions"]


def test_a_forged_dependency_version_refuses() -> None:
    """Sections 35 and 75: an arbitrary declared version is never authority."""

    forged = [
        dict(row, version="99.99.99-FORGED")
        for row in SESSION_REQUEST["third_party_authority"]
    ]
    tampered = dict(
        SESSION_REQUEST,
        third_party_authority=forged,
        third_party_authority_digest=protocol.third_party_authority_digest(
            protocol.frozen_distribution_authorities(forged)
        ),
    )
    assert _refusal(tampered)["failure_reason"] == (
        protocol.NON_CERTIFIED_DEPENDENCY_ENVIRONMENT
    )
    admission = _admit(tampered)
    assert admission.admitted is False
    assert admission.failure_reason.startswith("REQUEST_AUTHORITY_MISMATCH")


def test_the_same_version_with_a_wrong_artifact_refuses(tmp_path: Path) -> None:
    """Section 76: a self-consistent unreviewed artifact is not authorized."""

    import base64
    import hashlib
    import shutil

    authority = r1.frozen_third_party_authority()[0]
    observation = r1.observe_installed_distributions((authority,))[0]
    source_location = Path(observation.location)
    environment = tmp_path / "env"
    location = environment / "lib/python3.12/site-packages"
    location.mkdir(parents=True)
    shutil.copytree(source_location / "alembic", location / "alembic")
    shutil.copytree(
        source_location / authority.dist_info_directory,
        location / authority.dist_info_directory,
    )
    # a different build of the *same* version, with an internally valid RECORD
    changed = location / "alembic/__init__.py"
    changed.write_text(
        changed.read_text(encoding="utf-8") + "\n# different unreviewed build\n",
        encoding="utf-8",
    )
    record = location / authority.dist_info_directory / "RECORD"
    rebuilt: list[str] = []
    for line in record.read_text(encoding="utf-8").splitlines():
        path, digest, size = line.rsplit(",", 2)
        if path == "alembic/__init__.py":
            data = changed.read_bytes()
            encoded = (
                base64.urlsafe_b64encode(hashlib.sha256(data).digest())
                .decode("ascii")
                .rstrip("=")
            )
            rebuilt.append(f"{path},sha256={encoded},{len(data)}")
        else:
            rebuilt.append(line)
    record.write_text("\n".join(rebuilt) + "\n", encoding="utf-8")

    swapped = protocol.installed_distribution_observations(
        [
            {
                "distribution": authority.distribution,
                "location": str(location.resolve()),
                "record_path": str(record.resolve()),
                "environment_root": str(environment.resolve()),
            }
        ]
    )[0]
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="reviewed RECORD artifact identity",
    ):
        protocol.verify_installed_distribution_content(
            authority, swapped, bytecode_namespace_enforced=True
        )
    rows = protocol.parse_record_rows(
        record.read_text(encoding="utf-8"), authority.distribution
    )
    assert protocol.record_content_manifest_digest(rows) != (
        authority.record_content_manifest_digest
    )


def test_a_tampered_installed_file_refuses_before_it_can_execute(
    tmp_path: Path,
) -> None:
    """Section 44: RECORD unchanged, one executable installed file altered."""

    _assert_reviewed_dependency_state("alembic")
    authority = next(
        entry
        for entry in r1.frozen_third_party_authority()
        if entry.distribution == "alembic"
    )
    observation = r1.observe_installed_distributions((authority,))[0]
    target = Path(observation.location) / "alembic/__init__.py"
    record = Path(observation.record_path)
    original_target = target.read_bytes()
    original_record = record.read_bytes()
    marker = tmp_path / "tampered-dependency-executed"
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
    assert record.read_bytes() == original_record
    _assert_reviewed_dependency_state("alembic")


def test_dependency_content_is_verified_before_any_project_import() -> None:
    """Section 43: the ordering is structural, not incidental."""

    entry_source = (ROOT / "etf_calendar_worker/entry_r1.py").read_text(
        encoding="utf-8"
    )
    verify_index = entry_source.index("verify_third_party_authority(")
    calendar_index = entry_source.index("calendar = _load_calendar()")
    assert verify_index < calendar_index
    import ast

    protocol_source = (ROOT / "etf_calendar_worker/protocol_r1.py").read_text(
        encoding="utf-8"
    )
    imported: set[str] = set()
    for node in ast.walk(ast.parse(protocol_source)):
        if isinstance(node, ast.Import):
            imported.update(alias.name.partition(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.add((node.module or "").partition(".")[0])
    assert imported <= set(sys.stdlib_module_names) | {"__future__"}
    assert "btc_predictor" not in imported
    rule = r1.third_party_installed_content_attestation_rule()
    assert rule["verification_precedes_dependency_execution"] is True
    assert rule["forbidden_sequence"] == "IMPORT_DEPENDENCIES_THEN_VERIFY_THEIR_FILES"
    assert rule["worker_protocol_lives_outside_the_application_package"] is True
    assert rule["covers_compiled_native_extension_and_shared_library_rows"] is True
    assert rule["verifies_only_python_source"] is False


def test_third_party_evidence_is_deterministic_and_path_free() -> None:
    admission = _admit(SESSION_REQUEST)
    assert admission.admitted, admission.failure_reason
    evidence = r1.scientific_response_evidence(CONTEXT, admission)
    serialized = json.dumps(evidence, sort_keys=True)
    assert str(ROOT) not in serialized
    assert "site-packages" not in serialized
    assert evidence["third_party_installed_content_verification"] == "PASS"
    assert evidence["third_party_authority_digest"] == (
        CONTEXT.third_party_authority_digest
    )
    assert evidence["third_party_observed_content_manifest_digest"]
    assert evidence["bytecode_cache_binding"] == "PASS"
    assert evidence["trusted_authority_context"]["proof_architecture_sha256"] == (
        CANDIDATE_HASH
    )


# ---------------------------------------------------------------------------
# Preserved isolation results
# ---------------------------------------------------------------------------


def test_isolated_worker_reproduces_the_honest_session_result() -> None:
    admission = _admit(SESSION_REQUEST)
    assert admission.admitted, admission.failure_reason
    assert admission.result["state"] == HONEST_SESSION_STATE == "EXPECTED"
    assert admission.response["one_request_one_process"] is True
    assert admission.outcome.exit_status == 0


def test_isolated_worker_reproduces_the_honest_flow_window_result() -> None:
    admission = _admit(flow_request())
    assert admission.admitted, admission.failure_reason
    assert admission.result["evaluability_state"] == HONEST_FLOW.evaluability_state
    assert admission.result["feature"]["feature_id"] == HONEST_FLOW.feature.feature_id
    assert admission.result["feature"]["feature_id"] == "ETF_FLOW_5D"


def test_parent_flow_feature_id_mutation_leaves_the_worker_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Section 77: the central preserved PAD4 success."""

    monkeypatch.setattr(_flow, "FIVE_DAY_ETF_FLOW_FEATURE_ID", "WRONG")
    assert parent_flow_result().feature.feature_id == "WRONG"
    admission = _admit(flow_request())
    assert admission.admitted, admission.failure_reason
    assert admission.result["feature"]["feature_id"] == "ETF_FLOW_5D"


def test_parent_generated_dataclass_method_mutation_leaves_the_worker_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Section 78: no generated-method runtime enumeration anywhere."""

    original = cal.ScientificEtfFlowResult.__init__

    def replacement(self, evaluability_state, calendar, feature, reason_codes=()):
        original(self, "WRONG", calendar, feature, reason_codes)

    monkeypatch.setattr(cal.ScientificEtfFlowResult, "__init__", replacement)
    assert parent_flow_result().evaluability_state == "WRONG"
    admission = _admit(flow_request())
    assert admission.admitted, admission.failure_reason
    assert admission.result["evaluability_state"] == "EVALUABLE"


def test_parent_sys_modules_substitution_leaves_the_worker_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    substitute = types.ModuleType("btc_predictor.features.flow")
    substitute.FIVE_DAY_ETF_FLOW_FEATURE_ID = "WRONG"
    monkeypatch.setitem(sys.modules, "btc_predictor.features.flow", substitute)
    admission = _admit(flow_request())
    assert admission.admitted, admission.failure_reason
    assert admission.result["feature"]["feature_id"] == "ETF_FLOW_5D"


def test_parent_environment_drift_does_not_reach_the_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/definitely/not/certified")
    monkeypatch.setenv("BTC_TRUSTED_ACQUISITION_PRIVATE_KEY_FILE", "/tmp/key.pem")
    admission = _admit(SESSION_REQUEST)
    assert admission.admitted, admission.failure_reason
    assert admission.result["state"] == "EXPECTED"


# ---------------------------------------------------------------------------
# Canonical protocol
# ---------------------------------------------------------------------------


def test_request_validation_refuses_unknown_and_missing_fields() -> None:
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="UNKNOWN_REQUEST_FIELD"
    ):
        protocol.validate_request(dict(SESSION_REQUEST, extra=1))
    incomplete = dict(SESSION_REQUEST)
    incomplete.pop("operation")
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="MISSING_REQUEST_FIELD"
    ):
        protocol.validate_request(incomplete)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="WORKER_AUTHORITY_TICKET_REFUSED"
    ):
        protocol.validate_request(
            dict(SESSION_REQUEST, worker_authority_ticket="POSTP1-001V2A-PAD4")
        )
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="PROJECT_SOURCE_MANIFEST_ROLE_REFUSED",
    ):
        protocol.validate_request(
            dict(SESSION_REQUEST, project_source_manifest_role="ANYTHING")
        )
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="UNKNOWN_SCIENTIFIC_OPERATION"
    ):
        protocol.validate_request(dict(SESSION_REQUEST, operation="os.system"))


def test_canonical_ipc_bytes_must_re_serialize_to_themselves() -> None:
    raw = protocol.canonical_json_bytes(SESSION_REQUEST)
    assert protocol.assert_canonical_request_bytes(raw) == SESSION_REQUEST
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="SCIENTIFIC_IPC_PAYLOAD_IS_NOT_CANONICAL",
    ):
        protocol.assert_canonical_request_bytes(b" " + raw)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="CANONICAL_PAYLOAD_IS_NOT_ONE_JSON_DOCUMENT",
    ):
        protocol.assert_canonical_request_bytes(raw + b"{}")
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="NON_FINITE_JSON_CONSTANT_REFUSED"
    ):
        protocol.parse_canonical_json(b'{"a":NaN}')
    assert protocol.FORBIDDEN_SCIENTIFIC_IPC == (
        "pickle",
        "cloudpickle",
        "dill",
        "marshal",
    )


def test_lazy_and_unmaterialized_results_are_refused() -> None:
    async def coroutine():  # pragma: no cover - never awaited
        return 1

    candidates = [
        (item for item in (1, 2)),
        iter([1, 2]),
        memoryview(b"ab"),
        len,
        coroutine(),
    ]
    for candidate in candidates:
        assert protocol.lazy_result_kind(candidate) in protocol.LAZY_RESULT_KINDS
        with pytest.raises(
            protocol.ScientificWorkerProtocolError, match="LAZY_SCIENTIFIC_RESULT_REFUSED"
        ):
            protocol.refuse_lazy_result(candidate)
    candidates[-1].close()
    protocol.refuse_lazy_result({"state": "EXPECTED"})


def test_one_request_one_process_claim_refuses_a_second_request() -> None:
    protocol.reset_single_request_claim_for_tests()
    protocol.claim_single_request()
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match=protocol.SECOND_REQUEST_REFUSAL
    ):
        protocol.claim_single_request()
    protocol.reset_single_request_claim_for_tests()


def test_two_requests_sent_to_one_worker_process_are_refused(tmp_path: Path) -> None:
    namespace = r1.allocate_worker_pycache_namespace(tmp_path / "cache")
    payload = protocol.canonical_json_bytes(SESSION_REQUEST)
    completed = subprocess.run(
        list(LAUNCH.argv_for(namespace)),
        input=payload + b"\n" + payload,
        capture_output=True,
        cwd=str(ROOT),
        env=dict(LAUNCH.environment),
        timeout=protocol.DEFAULT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 3
    response = json.loads(completed.stdout.decode())
    assert response["status"] == "REFUSED"
    assert response["result"] is None
    assert completed.stdout.count(b"\n") == 1


def test_response_shape_and_result_digest_are_enforced() -> None:
    outcome = r1.run_scientific_worker(SESSION_REQUEST, LAUNCH)
    response = json.loads(outcome.stdout.decode())
    assert sorted(response) == sorted(protocol.RESPONSE_FIELDS)
    assert response["result_digest"] == protocol.result_digest(response["result"])
    tampered = dict(response, result=dict(response["result"], state="WRONG"))
    replayed = r1.WorkerProcessOutcome(
        exit_status=0,
        timed_out=False,
        stdout=protocol.canonical_json_bytes(tampered) + b"\n",
        stderr=b"",
        request_digest=outcome.request_digest,
    )
    admission = r1.admit_worker_result(CONTEXT, SESSION_REQUEST, replayed)
    assert admission.admitted is False
    assert admission.failure_reason == "WORKER_RESULT_DIGEST_MISMATCH"
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="RESPONSE_SHAPE_REFUSED"
    ):
        protocol.validate_response(dict(response, extra=1))


def test_timeout_crash_and_extra_output_are_never_admitted() -> None:
    cases = {
        "WORKER_TIMEOUT": r1.WorkerProcessOutcome(None, True, b"", b"", "d" * 64),
        "WORKER_EXIT_STATUS_1": r1.WorkerProcessOutcome(1, False, b"", b"", "d" * 64),
        "WORKER_STDOUT_IS_NOT_EXACTLY_ONE_PROTOCOL_PAYLOAD": r1.WorkerProcessOutcome(
            0, False, b"{}\n{}\n", b"", "d" * 64
        ),
    }
    for reason, outcome in cases.items():
        admission = r1.admit_worker_result(CONTEXT, SESSION_REQUEST, outcome)
        assert admission.admitted is False
        assert admission.failure_reason == reason


def test_real_worker_timeout_is_not_admitted() -> None:
    impatient = replace(LAUNCH, timeout_seconds=1)
    outcome = r1.run_scientific_worker(SESSION_REQUEST, impatient)
    admission = r1.admit_worker_result(CONTEXT, SESSION_REQUEST, outcome)
    if outcome.timed_out:
        assert admission.failure_reason == "WORKER_TIMEOUT"
    else:  # pragma: no cover - only on an unusually fast machine
        assert admission.admitted
    assert admission.admitted is not True or not outcome.timed_out


def test_worker_scientific_exception_is_a_typed_failure() -> None:
    broken = session_request(
        evidence_records=tuple(
            dict(row, record_kind="UNKNOWN_KIND") for row in SESSION_RECORDS
        )
    )
    response = _refusal(broken)
    assert response["failure_reason"] in {
        "UNKNOWN_EVIDENCE_RECORD_KIND",
        "WORKER_SCIENTIFIC_EXCEPTION:ScientificWorkerProtocolError",
    }
    assert response["post_execution_source_verification"] == "NOT_REACHED"


def test_worker_signing_capability_and_leaked_python_environment_refuse(
    tmp_path: Path,
) -> None:
    for variable, reason in (
        ("PYTHONPATH", "AMBIENT_PYTHON_ENVIRONMENT_LEAKED_INTO_THE_WORKER"),
        (
            protocol.PRIVATE_KEY_FILE_ENV_VAR,
            "WORKER_SIGNING_CAPABILITY_REFUSED",
        ),
    ):
        namespace = r1.allocate_worker_pycache_namespace(tmp_path / variable)
        completed = subprocess.run(
            list(LAUNCH.argv_for(namespace)),
            input=protocol.canonical_json_bytes(SESSION_REQUEST),
            capture_output=True,
            cwd=str(ROOT),
            env=dict(LAUNCH.environment, **{variable: "/leaked"}),
            timeout=protocol.DEFAULT_TIMEOUT_SECONDS,
        )
        assert completed.returncode == 3
        assert json.loads(completed.stdout.decode())["failure_reason"] == reason


def test_declared_sys_path_must_match_the_parent_controlled_launch() -> None:
    drifted = dict(SESSION_REQUEST, sys_path=[*SESSION_REQUEST["sys_path"], "/elsewhere"])
    assert _refusal(drifted)["failure_reason"] == (
        "WORKER_SYS_PATH_IS_NOT_PARENT_CONTROLLED"
    )


def test_scientific_response_evidence_is_complete_and_address_free() -> None:
    admission = _admit(SESSION_REQUEST)
    evidence = r1.scientific_response_evidence(CONTEXT, admission)
    assert evidence["admitted"] is True
    assert evidence["failure_reason"] is None
    assert evidence["worker_authority_hash"] == CANDIDATE_HASH
    assert evidence["worker_authority_ticket"] == "POSTP1-001V2A-PAD4-R1"
    assert evidence["worker_source_manifest_digest"] == (
        CONTEXT.project_source_manifest_digest
    )
    assert evidence["worker_source_manifest_role"] == (
        "PRE_I2_CONFORMANCE_FIXTURE_AND_PROVENANCE"
    )
    protocol.assert_address_free(evidence)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="SCIENTIFIC_EVIDENCE_CONTAINS_A_MEMORY_ADDRESS",
    ):
        protocol.assert_address_free({"store": "<object at 0x7f1234abcd>"})


# ---------------------------------------------------------------------------
# Preserved static authority and current production
# ---------------------------------------------------------------------------


def test_compiled_root_witness_and_current_production_blockers_are_preserved() -> None:
    source = r1.CALENDAR_SOURCE.read_text(encoding="utf-8")
    production = r1.verify_current_production_expected_result(source)
    assert production["root_write_clear_or_delete_findings"] == 0
    assert production["root_cell_finding"] == (
        "common_etf_session_status:evidence_store"
    )
    assert production["ast_store_use_normal_form"] == (
        "REFUSED_AT_THE_SAME_GENERATOR_CAPTURE"
    )
    assert production["both_static_layers_refuse_the_same_single_construct"] is True
    assert production["wrapper_installer_removal_required"] is True
    assert production["corrected_worker_integrated_in_production"] is False
    assert production["calendar_production_conformance"] == "NO"
    assert production["calendar_implementation"] == "BLOCKED"
    assert production["artifact_builder_dispatch_rewrite_required_solely_by_this_decision"] is (
        False
    )


def test_closed_store_grammar_and_root_cell_rule_are_preserved() -> None:
    grammar = r1.store_root_and_direct_use_grammar()
    assert grammar["preserved_under_process_isolation"] is True
    assert grammar["process_isolation_legalizes_wrappers"] is False
    assert grammar["root_may_be_a_cell_variable_of_a_conforming_owner"] is False
    assert grammar["known_generator_capture_rewrite_still_required"] == (
        "common_etf_session_status:evidence_store"
    )
    witness_rule = r1.compiled_root_binding_witness_rule()
    assert witness_rule["failed_pad4_parent_certified"] is False
    assert witness_rule["preserved_under_process_isolation"] is True


def test_exact_eleven_owner_census_and_graph_are_preserved() -> None:
    graph = r1.replay_owner_graph_rule()
    assert graph["owner_count"] == 11
    assert graph["owners"] == list(r1.FROZEN_REPLAY_OWNERS)
    assert graph["owner_census_relation"] == "FROZEN_EQUALS_SOURCE_DISCOVERED_EQUALS_11"
    assert graph["cycles_permitted"] is False
    assert graph["unknown_forwarding_permitted"] is False
    assert graph["every_owner_path_terminates_at_documented_store_api"] is True
    assert graph["documented_terminals"] == ["put", "get", "records", "envelopes"]
    source = r1.CALENDAR_SOURCE.read_text(encoding="utf-8")
    produced = r1.compiled_root_binding_witness(source)
    assert len(produced.owners) == 11


def test_direct_dependency_body_rule_is_preserved_and_still_blocked() -> None:
    rule = r1.direct_body_dependency_rule()
    assert rule["wrapper_installed_guards_permitted"] is False
    assert rule["wrapper_installer_removal_required"] == r1.WRAPPER_INSTALLER_SITE
    assert rule["certified_dependency_sha256"] == r1.CERTIFIED_DEPENDENCY_SHA256
    assert rule["artifact_builder_dispatch_rewrite_required_by_this_decision"] is False
    source = r1.CALENDAR_SOURCE.read_text(encoding="utf-8")
    bodies = r1.direct_dependency_body_findings(source)
    assert bodies["bodies_absent"] == []
    assert bodies["bodies_without_the_direct_dependency_assertion"] == sorted(
        r1.REQUIRED_DIRECT_BODIES
    )


def test_io_and_capability_boundary_is_explicit_about_its_limits() -> None:
    boundary = r1.worker_io_and_capability_boundary()
    assert boundary["operating_system_level_network_sandbox_claimed"] is False
    assert boundary["operating_system_network_sandbox_added_by_this_correction"] is False
    assert boundary["worker_network_permitted"] is False
    assert boundary["worker_private_signing_key_permitted"] is False
    assert boundary["worker_authoritative_db_write_permitted"] is False
    assert boundary["worker_database_connection"] == (
        "NOT_ESTABLISHED_BY_ANY_FROZEN_OPERATION"
    )
    assert boundary["collection_authority_moved_into_the_worker"] is False
    isolation = r1.trusted_process_and_isolation_boundary()
    assert isolation["hostile_filesystem_race_resistance_claimed"] is False
    assert "perfectly racing" in isolation["accepted_race_boundary"]


def test_dynamic_import_claim_scope_is_precise() -> None:
    """Section 54: a scoped, verified fact, never an eternal universal claim."""

    child = r1.dynamic_import_and_execution_prohibition()
    assert child["authoritative_worker_dynamic_project_execution"] == (
        "FORBIDDEN_AND_STATICALLY_AUDITED"
    )
    assert child["certified_source_universe_derivation"] == (
        "MECHANICALLY_DERIVED_FROM_STATIC_IMPORT_DECLARATIONS"
    )
    assert child["unexpected_loaded_project_module"] == "REFUSE"
    assert child[
        "universal_claim_that_every_certified_module_is_free_of_every_dynamic_import_mechanism"
    ] is False
    scan = child["current_certified_source_scan"]
    assert scan["claim_kind"] == (
        "VERIFIED_CURRENT_SOURCE_FACT_NOT_AN_ETERNAL_UNIVERSAL_CLAIM"
    )
    assert scan["a_hit_is_evidence_of_a_dynamic_project_import"] is False
    assert "CLOSED_WORKER_CODING_RULE_CONSTRUCTS" in scan["scanned_for"]
    assert scan["modules_scanned"] == len(MANIFEST)
    assert scan["modules_containing_a_closed_worker_rule_construct"] == len(
        scan["modules"]
    )
    assert set(scan["modules"]) <= {entry.module for entry in MANIFEST}
    assert scan["modules"] == sorted(scan["modules"])


def test_authoritative_worker_source_is_closed_against_project_execution() -> None:
    audit = r1.audit_authoritative_worker_source()
    assert audit["closed"] is True
    assert audit["findings"] == []
    assert audit["authoritative_worker_source"] == [
        "etf_calendar_worker/entry_r1.py",
        "etf_calendar_worker/protocol_r1.py",
    ]
    assert set(audit["source_sha256"]) == set(audit["authoritative_worker_source"])
    frozen_paths = {entry.path for entry in MANIFEST}
    assert set(audit["authoritative_worker_source"]) <= frozen_paths


def test_no_etf_calendar_production_source_was_modified() -> None:
    """The bounded correction changes no ETF calendar production science."""

    completed = subprocess.run(
        [
            "git",
            "diff",
            "HEAD",
            "--name-only",
            "--",
            "btc_predictor/research/etf_publication_calendar.py",
            "btc_predictor/research/etf_calendar_semantics.py",
            "btc_predictor/features/flow.py",
            "btc_predictor/data/etf_flows.py",
            "btc_predictor/research/etf_calendar_scientific_worker_entry.py",
            "btc_predictor/research/etf_calendar_worker_protocol.py",
            "btc_predictor/research/etf_calendar_isolated_scientific_worker.py",
        ],
        capture_output=True,
        check=True,
        cwd=str(ROOT),
    )
    assert completed.stdout.decode().strip() == ""
