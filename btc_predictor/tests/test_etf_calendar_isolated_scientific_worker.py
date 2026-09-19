"""POSTP1-001V2A-PAD4 isolated one-shot scientific worker proof tests."""

from __future__ import annotations

import builtins
import json
import os
import subprocess
import sys
import types
from datetime import UTC, date, datetime
from pathlib import Path

import pytest

from btc_predictor.features import flow as _flow
from btc_predictor.research import etf_calendar_isolated_scientific_worker as isolated
from btc_predictor.research import etf_calendar_worker_protocol as protocol
from btc_predictor.research import etf_publication_calendar as cal
from btc_predictor.tests import test_etf_publication_calendar as fixtures


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / isolated.OUTPUT_NAMESPACE
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
DECISION = isolated.isolated_scientific_worker_v1_definition()
LAUNCH = isolated.worker_launch()
MANIFEST = isolated.derive_project_source_manifest()


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


def session_request(launch: isolated.WorkerLaunch = None, **overrides) -> dict:
    return isolated.build_scientific_request(
        LAUNCH if launch is None else launch,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": SESSION_DAY.isoformat()},
        evidence_records=overrides.pop("evidence_records", SESSION_RECORDS),
        decision_time=DECISION_TIME.isoformat(),
        decision_sha256=DECISION["definition_sha256"],
        **overrides,
    )


def flow_request(launch: isolated.WorkerLaunch = None, **overrides) -> dict:
    return isolated.build_scientific_request(
        LAUNCH if launch is None else launch,
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
        decision_sha256=DECISION["definition_sha256"],
        **overrides,
    )


SESSION_REQUEST = session_request()
FLOW_REQUEST = flow_request()


def _parent_store(records):
    store = cal.CalendarEvidenceStore()
    for row in sorted(records, key=lambda r: _RECORD_ORDER[r["record_kind"]]):
        if row["record_kind"] == cal.SOURCE_SNAPSHOT_KIND:
            store._records[row[cal.RECORD_DIGEST_FIELD]] = cal._verify_source_snapshot(row)
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
    """Materialize the certified manifest into a fresh isolated project root."""

    for entry in MANIFEST:
        target = destination / entry.path
        target.parent.mkdir(parents=True, exist_ok=True)
        os.link(ROOT / entry.path, target)
    if mutate is not None:
        target = destination / mutate
        drifted = target.read_text(encoding="utf-8") + "\n# certified-source drift\n"
        target.unlink()
        target.write_text(drifted, encoding="utf-8")
    return destination


# ---------------------------------------------------------------------------
# Decision integrity
# ---------------------------------------------------------------------------


def test_decision_scope_status_and_strategy_are_frozen() -> None:
    assert DECISION["decision_version"] == "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1"
    assert DECISION["program_ticket"] == "POSTP1-001V2A-PAD4"
    assert DECISION["workstream"] == "EPIC X — PROSPECTIVE INTEGRATION EVIDENCE"
    assert DECISION["status"] == (
        "FROZEN_PRE_DATA_AWAITING_INDEPENDENT_EXACT_HASH_XHIGH_REVIEW"
    )
    assert DECISION["final_classification"] == (
        "ETF_CALENDAR_ISOLATED_SCIENTIFIC_WORKER_V1_READY_FOR_XHIGH_REVIEW"
    )
    assert DECISION["proof_strategy"] == (
        "CERTIFIED_SOURCE_PLUS_FROZEN_CPYTHON_PLUS_CLOSED_STORE_GRAMMAR_PLUS_"
        "COMPILED_ROOT_WITNESS_PLUS_ONE_SHOT_EXEC_ISOLATED_SCIENTIFIC_WORKER"
    )
    assert DECISION["pre_data"] is True
    assert DECISION["required_review"] == (
        "POSTP1-002V2A-PAD4_INDEPENDENT_EXACT_HASH_XHIGH_PROOF_ARCHITECTURE_REVIEW"
    )
    assert DECISION["failed_parent_sha256"] == isolated.FAILED_PARENT_SHA256
    assert DECISION["failed_parent_certified"] is False
    assert DECISION["authorization"] == {
        "independent_proof_architecture_xhigh_review_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }


def test_material_children_are_mechanical_bound_and_digest_valid() -> None:
    children = isolated._children()
    assert DECISION["material_child_count"] == len(isolated._CHILD_ARTIFACTS) == 17
    assert DECISION["material_child_enumeration"] == (
        "MECHANICALLY_ENUMERATED_FROM_ONE_REGISTRY"
    )
    assert DECISION["child_definition_sha256"] == {
        name: payload["definition_sha256"] for name, payload in children.items()
    }
    for payload in children.values():
        isolated._verify_definition_digest(payload)
    isolated.verify_definition(DECISION)


def test_central_decisions_bind_the_frozen_isolation_choices() -> None:
    assert DECISION["central_decisions"] == {
        "one_request_one_exec_process": True,
        "fork_only_worker_permitted": False,
        "parent_python_objects_shared": False,
        "pickle_ipc_permitted": False,
        "worker_network_permitted": False,
        "worker_private_signing_key_permitted": False,
        "worker_authoritative_db_write_permitted": False,
        "project_source_manifest_required": True,
        "unexpected_project_module_permitted": False,
        "dynamic_project_import_permitted": False,
        "lazy_result_permitted": False,
        "long_lived_worker_permitted": False,
        "runtime_object_closure_is_completeness_proof": False,
        "process_isolation_is_scientific_execution_boundary": True,
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
        "hostile_operating_system_resistance_claimed": False,
        "calendar_science_changed": False,
        "calendar_production_code_changed": False,
    }


def test_runtime_object_closure_is_demoted_to_archived_diagnostic_evidence() -> None:
    boundary = isolated.trusted_process_and_isolation_boundary()
    assert boundary["runtime_object_closure_is_completeness_proof"] is False
    assert boundary["process_isolation_is_scientific_execution_boundary"] is True
    assert boundary["demoted_pad3_runtime_closure"] == {
        "functions": 25,
        "classes": 7,
        "values": 15,
        "imports": 14,
    }
    assert boundary["demoted_pad3_runtime_closure_role"] == "ARCHIVED_DIAGNOSTIC_EVIDENCE"
    assert boundary["abandoned_completeness_models"] == [
        "GENERATED_RUNTIME_METHOD_ENUMERATION",
        "RECURSIVE_SAME_PROCESS_RUNTIME_OBJECT_ATTESTATION",
        "REFLECTION_BLACKLIST_COMPLETENESS",
        "TRANSITIVE_MUTABLE_OBJECT_CLOSURE_ACROSS_THE_REPOSITORY",
    ]
    assert boundary["hostile_operating_system_resistance_claimed"] is False
    assert boundary["certified_source_may_mutate_its_own_globals"] is True


def test_failed_lineage_is_preserved_unchanged_and_never_certified() -> None:
    assert isolated.FAILED_ARCHITECTURE_LINEAGE == (
        "0c237c1b217b1fd406ec3967309774293c01d3e27574b9f4a7d1b9a0e887b55d",
        "a7d2b08741080494cc4ca0269bf21e28e631c7f2e70887bcb0e1beb302534dd0",
        "dc36ffe228b7a3bc6d9145042b4e301c8624c99a79d71a88b46fc268f1372c3e",
        "9f6af1794e8b49dce38288b9f1b9710bffd04ba70303b5c380e8fb447ac86295",
        "7ef114fede9efebe594f0ecf119d097a1161119f448737d0df10afdf9468d17b",
        "b5ca36bfa9b96970b667cc44b10c5c5da7eb5ce7c57e5739601640d9b2a8abe9",
        "b8f8b92d4e3c1c80c4226f7101e71f95d125bd48afbfcde72e489408f6b5b996",
    )
    lineage = isolated.science_lineage_and_safety()
    assert [
        row["definition_sha256"] for row in lineage["failed_architecture_lineage"]
    ] == list(isolated.FAILED_ARCHITECTURE_LINEAGE)
    assert all(
        row["certified"] is False
        and row["failed"] is True
        and row["used"] is False
        and row["prospective_observations"] == 0
        for row in lineage["failed_architecture_lineage"]
    )
    assert lineage["failed_calendar_lineage"] == [
        "a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9",
        "b81c1702c65e1e042b7a2f948216305618fd21fabe2e629edc46376882b357af",
        "0524334396e529afbd057db25721b92c3074dd10205dd08be0946e512f99c855",
        "b499c6a4d1a8a6c25c6b108279831f26508742de97bdbcd57c7bee58e584e076",
        "901f572e03781030906cd6fe72a73ec5804f9ffbdefe6a8a944c067f7fd9853f",
    ]
    assert lineage["preserved_hashes"] == {
        "certified_prospective_v1": (
            "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7"
        ),
        "failed_prospective_v2": (
            "488251df7bc1b49f801caa0dc28eb5224836574b154db9e4a70d4be670ec0b6d"
        ),
    }


def test_trusted_persistence_and_safety_are_unchanged() -> None:
    lineage = isolated.science_lineage_and_safety()
    assert lineage["certified_dependency"]["definition_sha256"] == (
        "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
    )
    assert lineage["certified_dependency"]["changed"] is False
    assert lineage["safety"] == {
        "btc019": "UNTOUCHED",
        "calendar_certified": False,
        "calendar_implementation": "BLOCKED_PENDING_REVIEW_PASS",
        "collection_authorized": False,
        "epic_t": "UNCHANGED",
        "postp1_001v2r1": "BLOCKED",
        "postp1_003r3": "BLOCKED",
        "postp1_004": "BLOCKED",
        "prospective_observations": 0,
        "real_stage_b_evaluation": False,
        "trusted_persistence": "CLOSED_UNCHANGED",
    }
    assert (
        lineage["preserved_science"][
            "etf_calendar_production_code_changed_by_this_decision"
        ]
        is False
    )


# ---------------------------------------------------------------------------
# Artifact determinism
# ---------------------------------------------------------------------------


def test_write_and_restore_artifacts_round_trip(tmp_path: Path) -> None:
    decision = isolated.write_artifacts(tmp_path)
    assert decision == DECISION
    assert isolated.restore_artifacts(tmp_path) == DECISION
    assert {path.name for path in tmp_path.iterdir()} == {
        isolated.DEFINITION_FILENAME,
        isolated.REPORT_FILENAME,
        *(filename for filename, _ in isolated._CHILD_ARTIFACTS),
    }


def test_persisted_namespace_reproduces_exactly() -> None:
    assert isolated.restore_artifacts(ARTIFACT_DIR)["definition_sha256"] == (
        DECISION["definition_sha256"]
    )


def test_restore_refuses_a_mutated_child(tmp_path: Path) -> None:
    isolated.write_artifacts(tmp_path)
    target = tmp_path / "worker_launch_contract.json"
    payload = json.loads(target.read_text())
    payload["fork_only_worker_permitted"] = True
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(isolated.IsolatedScientificWorkerError, match="does not reproduce"):
        isolated.restore_artifacts(tmp_path)


def test_restore_refuses_a_mutated_report(tmp_path: Path) -> None:
    isolated.write_artifacts(tmp_path)
    report = tmp_path / isolated.REPORT_FILENAME
    report.write_text(report.read_text() + "drift\n", encoding="utf-8")
    with pytest.raises(
        isolated.IsolatedScientificWorkerError, match="report does not reproduce"
    ):
        isolated.restore_artifacts(tmp_path)


def test_child_order_variation_does_not_change_the_parent() -> None:
    reversed_registry = tuple(reversed(isolated._CHILD_ARTIFACTS))
    assert isolated.isolated_scientific_worker_v1_definition(reversed_registry) == DECISION


def test_material_mutation_moves_both_child_and_parent_hashes() -> None:
    def mutated() -> dict:
        payload = isolated.worker_launch_contract()
        payload.pop("definition_sha256")
        payload["fork_only_worker_permitted"] = True
        return isolated._definition(payload)

    registry = tuple(
        (name, mutated if name == "worker_launch_contract.json" else builder)
        for name, builder in isolated._CHILD_ARTIFACTS
    )
    changed = isolated.isolated_scientific_worker_v1_definition(registry)
    assert changed["definition_sha256"] != DECISION["definition_sha256"]
    assert changed["child_definition_sha256"]["worker_launch_contract"] != (
        DECISION["child_definition_sha256"]["worker_launch_contract"]
    )


@pytest.mark.parametrize("seed", ["0", "1", "12345"])
def test_definition_is_deterministic_across_hash_seeds(seed: str, tmp_path: Path) -> None:
    script = (
        "from btc_predictor.research import etf_calendar_isolated_scientific_worker as w;"
        "print(w.isolated_scientific_worker_v1_definition()['definition_sha256'])"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        check=True,
        cwd=str(tmp_path),
        env=dict(os.environ, PYTHONHASHSEED=seed, PYTHONPATH=str(ROOT)),
    )
    assert completed.stdout.decode().strip() == DECISION["definition_sha256"]


def test_artifacts_reproduce_from_an_alternate_working_directory(tmp_path: Path) -> None:
    output = tmp_path / "fresh"
    script = (
        "import sys;from pathlib import Path;"
        "from btc_predictor.research import etf_calendar_isolated_scientific_worker as w;"
        "print(w.write_artifacts(Path(sys.argv[1]))['definition_sha256'])"
    )
    completed = subprocess.run(
        [sys.executable, "-c", script, str(output)],
        capture_output=True,
        check=True,
        cwd=str(tmp_path),
        env=dict(os.environ, PYTHONPATH=str(ROOT)),
    )
    assert completed.stdout.decode().strip() == DECISION["definition_sha256"]
    assert isolated.restore_artifacts(output) == DECISION


# ---------------------------------------------------------------------------
# Frozen interpreter
# ---------------------------------------------------------------------------


def test_worker_protocol_binds_the_compiled_witness_interpreter_identity() -> None:
    assert dict(protocol.PROOF_INTERPRETER_IDENTITY) == dict(
        isolated.PROOF_INTERPRETER_IDENTITY
    )
    assert isolated.verify_worker_protocol_binds_the_frozen_interpreter() == dict(
        sorted(isolated.PROOF_INTERPRETER_IDENTITY.items())
    )
    assert protocol.verify_proof_interpreter_identity() == {
        "implementation_name": "cpython",
        "version_major": 3,
        "version_minor": 12,
        "version_micro": 14,
        "version_releaselevel": "final",
        "version_serial": 0,
        "hexversion": 51121904,
        "cache_tag": "cpython-312",
        "magic_number_hex": "cb0d0d0a",
    }


def test_interpreter_identity_mismatch_refuses_scientific_authority() -> None:
    wrong = dict(protocol.PROOF_INTERPRETER_IDENTITY, version_micro=13)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="REFUSE_SCIENTIFIC_AUTHORITY"
    ):
        protocol.verify_proof_interpreter_identity(wrong)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="REFUSE_SCIENTIFIC_AUTHORITY"
    ):
        protocol.verify_proof_interpreter_identity({"implementation_name": "cpython"})


def test_wrong_interpreter_refuses_before_any_project_import() -> None:
    other = "/usr/bin/python3"
    if not Path(other).exists():  # pragma: no cover - environment dependent
        pytest.skip("no alternate system interpreter available")
    launch = isolated.worker_launch(executable=other)
    admission = isolated.run_isolated_scientific_request(session_request(launch), launch)
    assert admission.admitted is False
    assert admission.outcome.exit_status == 5
    assert admission.outcome.stdout == b""
    assert b"REFUSE_SCIENTIFIC_AUTHORITY" in admission.outcome.stderr


# ---------------------------------------------------------------------------
# Certified project source manifest
# ---------------------------------------------------------------------------


def test_project_source_manifest_is_mechanically_derived_and_canonical() -> None:
    assert MANIFEST == tuple(sorted(MANIFEST))
    assert len({entry.module for entry in MANIFEST}) == len(MANIFEST)
    assert DECISION["worker_project_source_module_count"] == len(MANIFEST)
    assert DECISION["worker_project_source_manifest_digest"] == protocol.manifest_digest(
        MANIFEST
    )
    for entry in MANIFEST:
        assert entry.module.startswith("btc_predictor")
        assert entry.path in (
            protocol.module_relative_path(entry.module),
            protocol.package_relative_path(entry.module),
        )
        assert entry.sha256 == protocol.file_sha256(ROOT / entry.path)
    material = isolated.worker_project_source_manifest()
    assert material["module_count"] == len(MANIFEST)
    assert material["hand_maintained"] is False
    assert material["derivation"] == (
        "RECURSIVE_STATIC_PROJECT_IMPORT_CLOSURE_FROM_THE_WORKER_ENTRYPOINT"
    )
    assert material["seed_entrypoint"] == isolated.WORKER_ENTRYPOINT_MODULE


def test_manifest_contains_the_worker_entrypoint_protocol_and_calendar() -> None:
    modules = {entry.module for entry in MANIFEST}
    assert isolated.WORKER_ENTRYPOINT_MODULE in modules
    assert isolated.WORKER_PROTOCOL_MODULE in modules
    assert isolated.CALENDAR_MODULE_IMPORT_NAME in modules
    assert set(isolated.REQUIRED_WORKER_PROJECT_MODULES) <= modules


def test_manifest_is_a_superset_of_what_the_worker_actually_loads() -> None:
    admission = isolated.run_isolated_scientific_request(SESSION_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert admission.response["loaded_project_modules"] == len(MANIFEST)


def test_manifest_row_shape_and_ordering_are_enforced() -> None:
    rows = [entry.as_material() for entry in MANIFEST]
    with pytest.raises(protocol.ScientificWorkerProtocolError, match="ROW_SHAPE_REFUSED"):
        protocol.project_source_entries([{"module": "btc_predictor"}])
    with pytest.raises(protocol.ScientificWorkerProtocolError, match="MODULE_REFUSED"):
        protocol.project_source_entries([dict(rows[0], module="numpy")])
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="PATH_DOES_NOT_MATCH_MODULE"
    ):
        protocol.project_source_entries([dict(rows[0], path="btc_predictor/elsewhere.py")])
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="NOT_CANONICALLY_ORDERED"
    ):
        protocol.project_source_entries(list(reversed(rows)))
    with pytest.raises(protocol.ScientificWorkerProtocolError, match="DUPLICATE_MODULE"):
        protocol.project_source_entries([rows[0], rows[0]])
    with pytest.raises(protocol.ScientificWorkerProtocolError, match="MANIFEST_IS_EMPTY"):
        protocol.project_source_entries([])


def test_manifest_digest_binds_every_entry() -> None:
    drifted = (
        protocol.ProjectSourceEntry(MANIFEST[0].module, MANIFEST[0].path, "f" * 64),
        *MANIFEST[1:],
    )
    assert protocol.manifest_digest(drifted) != protocol.manifest_digest(MANIFEST)


# ---------------------------------------------------------------------------
# Closed worker-coding rule
# ---------------------------------------------------------------------------


def test_authoritative_worker_source_is_closed_against_project_execution() -> None:
    audit = isolated.audit_authoritative_worker_source()
    assert audit["closed"] is True
    assert audit["findings"] == []
    assert set(audit["source_sha256"]) == set(protocol.AUTHORITATIVE_WORKER_SOURCE)
    for relative, digest in audit["source_sha256"].items():
        assert digest == protocol.file_sha256(ROOT / relative)


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("exec('x = 1')", "FORBIDDEN_CALLABLE:exec"),
        ("eval('1')", "FORBIDDEN_CALLABLE:eval"),
        ("compile('1', 'x', 'eval')", "FORBIDDEN_CALLABLE:compile"),
        ("__import__('btc_predictor')", "FORBIDDEN_CALLABLE:__import__"),
        ("import importlib", "FORBIDDEN_IMPORT:importlib"),
        ("from importlib import import_module", "FORBIDDEN_IMPORT:importlib"),
        ("import runpy", "FORBIDDEN_IMPORT:runpy"),
        ("import pickle", "FORBIDDEN_IMPORT:pickle"),
        ("import marshal", "FORBIDDEN_IMPORT:marshal"),
        ("import socket", "FORBIDDEN_IMPORT:socket"),
        ("import urllib.request", "FORBIDDEN_IMPORT:urllib.request"),
        ("import sqlalchemy", "FORBIDDEN_IMPORT:sqlalchemy"),
        ("import os\nos.fork()", "FORBIDDEN_PROCESS_CAPABILITY:os.fork"),
        ("import os\nos.system('ls')", "FORBIDDEN_PROCESS_CAPABILITY:os.system"),
    ],
)
def test_dynamic_import_findings_detect_each_forbidden_construct(
    source: str, expected: str
) -> None:
    assert f"probe.py:{expected}" in isolated.dynamic_import_findings(source, "probe.py")


def test_dynamic_import_prohibition_child_reports_the_closed_worker_rule() -> None:
    child = isolated.dynamic_import_and_execution_prohibition()
    assert child["dynamic_project_import_permitted"] is False
    assert child["pickle_cloudpickle_dill_permitted"] is False
    assert child["claims_to_enumerate_hostile_python_techniques"] is False
    assert child["closed"] is True
    assert child["current_findings"] == []
    assert child["scope"] == "AUTHORITATIVE_SCIENTIFIC_WORKER_SOURCE"


# ---------------------------------------------------------------------------
# Launch contract
# ---------------------------------------------------------------------------


def test_worker_launch_uses_an_exec_style_isolated_interpreter_launch() -> None:
    assert LAUNCH.argv[0] == sys.executable
    assert LAUNCH.argv[1:4] == ("-I", "-S", "-B")
    assert LAUNCH.argv[4] == str(ROOT / protocol.WORKER_ENTRYPOINT_RELATIVE_PATH)
    assert json.loads(LAUNCH.argv[5]) == list(LAUNCH.sys_path)
    assert LAUNCH.mechanism == isolated.EXEC_LAUNCH
    assert dict(LAUNCH.environment) == dict(isolated.FROZEN_WORKER_ENVIRONMENT)
    assert not any(name.startswith("PYTHON") for name in LAUNCH.environment)
    assert str(ROOT) in LAUNCH.sys_path


def test_fork_only_worker_is_not_an_authorized_scientific_worker() -> None:
    assert isolated.authorize_worker_launch_mechanism(isolated.EXEC_LAUNCH) == (
        isolated.EXEC_LAUNCH
    )
    for mechanism in isolated.UNAUTHORIZED_LAUNCH_MECHANISMS:
        with pytest.raises(
            isolated.IsolatedScientificWorkerError,
            match="NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER",
        ):
            isolated.authorize_worker_launch_mechanism(mechanism)
    forked = isolated.WorkerLaunch(
        executable=sys.executable,
        project_root=ROOT,
        sys_path=LAUNCH.sys_path,
        entrypoint=LAUNCH.entrypoint,
        cwd=ROOT,
        mechanism=isolated.FORK_WITHOUT_EXEC,
    )
    with pytest.raises(
        isolated.IsolatedScientificWorkerError,
        match="NOT_AN_AUTHORIZED_SCIENTIFIC_WORKER",
    ):
        isolated.run_scientific_worker(SESSION_REQUEST, forked)


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


# ---------------------------------------------------------------------------
# Canonical protocol
# ---------------------------------------------------------------------------


def test_request_validation_refuses_unknown_and_missing_fields() -> None:
    with pytest.raises(protocol.ScientificWorkerProtocolError, match="UNKNOWN_REQUEST_FIELD"):
        protocol.validate_request(dict(SESSION_REQUEST, extra=1))
    incomplete = dict(SESSION_REQUEST)
    incomplete.pop("operation")
    with pytest.raises(protocol.ScientificWorkerProtocolError, match="MISSING_REQUEST_FIELD"):
        protocol.validate_request(incomplete)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="UNKNOWN_SCIENTIFIC_OPERATION"
    ):
        protocol.validate_request(dict(SESSION_REQUEST, operation="collect_official_calendar"))
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="OPERATION_INPUT_SHAPE_REFUSED"
    ):
        protocol.validate_request(
            dict(SESSION_REQUEST, operation_inputs={"trade_date": "2026-12-24", "x": 1})
        )


def test_request_validation_refuses_non_canonical_scalars() -> None:
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="NON_FINITE_JSON_CONSTANT_REFUSED"
    ):
        protocol.parse_canonical_json(b'{"a": NaN}')
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="NON_FINITE_JSON_CONSTANT_REFUSED"
    ):
        protocol.parse_canonical_json(b'{"a": Infinity}')
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="TIMESTAMP_IS_NOT_EXPLICIT_UTC"
    ):
        protocol.validate_request(dict(SESSION_REQUEST, decision_time="2026-12-31T00:00:00"))
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="TIMESTAMP_IS_NOT_EXPLICIT_UTC"
    ):
        protocol.validate_request(
            dict(SESSION_REQUEST, decision_time="2026-12-31T01:00:00+01:00")
        )
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="TIMESTAMP_IS_NOT_CANONICAL_UTC"
    ):
        protocol.validate_request(dict(SESSION_REQUEST, decision_time="2026-12-31T00:00:00Z"))
    with pytest.raises(protocol.ScientificWorkerProtocolError, match="DATE_IS_NOT_CANONICAL"):
        protocol.validate_request(
            dict(SESSION_REQUEST, operation_inputs={"trade_date": "20261224"})
        )


def test_canonical_ipc_bytes_must_re_serialize_to_themselves() -> None:
    raw = protocol.canonical_json_bytes(SESSION_REQUEST)
    assert protocol.assert_canonical_request_bytes(raw) == SESSION_REQUEST
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="SCIENTIFIC_IPC_PAYLOAD_IS_NOT_CANONICAL",
    ):
        protocol.assert_canonical_request_bytes(b'{ "a" : 1 }')
    with pytest.raises(
        protocol.ScientificWorkerProtocolError,
        match="CANONICAL_PAYLOAD_IS_NOT_ONE_JSON_DOCUMENT",
    ):
        protocol.assert_canonical_request_bytes(raw + raw)


def test_lazy_and_unmaterialized_results_are_refused() -> None:
    async def coroutine() -> None:  # pragma: no cover - never awaited
        return None

    running = coroutine()
    try:
        for value, kind in (
            ((index for index in range(2)), "GENERATOR"),
            (running, "COROUTINE"),
            (iter([1]), "ITERATOR"),
            (memoryview(b"x"), "MEMORYVIEW"),
            (lambda: 1, "CALLABLE"),
        ):
            assert protocol.lazy_result_kind(value) == kind
            with pytest.raises(
                protocol.ScientificWorkerProtocolError,
                match="LAZY_SCIENTIFIC_RESULT_REFUSED",
            ):
                protocol.refuse_lazy_result(value)
    finally:
        running.close()
    assert protocol.lazy_result_kind({"state": "EXPECTED"}) is None


def test_one_request_one_process_claim_refuses_a_second_request() -> None:
    protocol.reset_single_request_claim_for_tests()
    try:
        protocol.claim_single_request()
        with pytest.raises(
            protocol.ScientificWorkerProtocolError,
            match="SECOND_SCIENTIFIC_REQUEST_IN_ONE_WORKER_PROCESS_UNSUPPORTED",
        ):
            protocol.claim_single_request()
    finally:
        protocol.reset_single_request_claim_for_tests()


def test_two_requests_sent_to_one_worker_process_are_refused() -> None:
    payload = protocol.canonical_json_bytes(SESSION_REQUEST)
    completed = subprocess.run(
        list(LAUNCH.argv),
        input=payload + payload,
        capture_output=True,
        cwd=str(LAUNCH.cwd),
        env=dict(LAUNCH.environment),
        timeout=protocol.DEFAULT_TIMEOUT_SECONDS,
    )
    assert completed.returncode == 3
    response = json.loads(completed.stdout.decode())
    assert response["status"] == "REFUSED"
    assert response["failure_reason"] == "CANONICAL_PAYLOAD_IS_NOT_ONE_JSON_DOCUMENT"
    assert response["result"] is None


def test_response_shape_and_result_digest_are_enforced() -> None:
    admission = isolated.run_isolated_scientific_request(SESSION_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    response = dict(admission.response)
    assert sorted(response) == sorted(protocol.RESPONSE_FIELDS)
    assert response["result_digest"] == protocol.result_digest(response["result"])
    with pytest.raises(protocol.ScientificWorkerProtocolError, match="RESPONSE_SHAPE_REFUSED"):
        protocol.validate_response(dict(response, extra=1))
    tampered = isolated.WorkerProcessOutcome(
        exit_status=0,
        timed_out=False,
        stdout=protocol.canonical_json_bytes(dict(response, result={"state": "WRONG"})) + b"\n",
        stderr=b"",
        request_digest=admission.outcome.request_digest,
    )
    assert isolated.admit_worker_result(SESSION_REQUEST, tampered).failure_reason == (
        "WORKER_RESULT_DIGEST_MISMATCH"
    )


# ---------------------------------------------------------------------------
# End-to-end isolation regressions
# ---------------------------------------------------------------------------


def test_isolated_worker_reproduces_the_honest_session_result() -> None:
    admission = isolated.run_isolated_scientific_request(SESSION_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert admission.result["state"] == HONEST_SESSION_STATE == cal.EXPECTED
    assert admission.result["trade_date"] == SESSION_DAY.isoformat()
    assert admission.outcome.exit_status == 0
    assert admission.response["evidence_admission_mode"] == (
        protocol.PROTOTYPE_EVIDENCE_ADMISSION_MODE
    )


def test_isolated_worker_reproduces_the_honest_flow_window_result() -> None:
    admission = isolated.run_isolated_scientific_request(FLOW_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert HONEST_FLOW.evaluability_state == "EVALUABLE"
    assert HONEST_FLOW.feature.feature_id == "ETF_FLOW_5D"
    assert admission.result["evaluability_state"] == "EVALUABLE"
    assert admission.result["feature"]["feature_id"] == "ETF_FLOW_5D"
    assert admission.result["calendar"]["expected_dates"] == [
        day.isoformat() for day in WINDOW_DAYS
    ]


def test_parent_flow_feature_id_mutation_leaves_the_worker_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The principal PAD4 architecture regression."""

    monkeypatch.setattr(_flow, "FIVE_DAY_ETF_FLOW_FEATURE_ID", "WRONG")
    assert parent_flow_result().feature.feature_id == "WRONG"
    admission = isolated.run_isolated_scientific_request(FLOW_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert admission.result["feature"]["feature_id"] == "ETF_FLOW_5D"
    assert admission.result["evaluability_state"] == "EVALUABLE"


def test_parent_flow_window_constant_mutation_leaves_the_worker_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(_flow, "FIVE_DAY_ETF_FLOW_WINDOW_DAYS", 6)
    with pytest.raises(cal.EtfCalendarAuthorityError, match="frozen 5/20-day windows"):
        parent_flow_result()
    admission = isolated.run_isolated_scientific_request(FLOW_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert admission.result["feature"]["feature_id"] == "ETF_FLOW_5D"
    assert admission.result["feature"]["window_days"] == 5


def test_parent_generated_dataclass_init_mutation_leaves_the_worker_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def replacement(self, *args, **kwargs) -> None:
        object.__setattr__(self, "evaluability_state", "WRONG")
        object.__setattr__(self, "calendar", None)
        object.__setattr__(self, "feature", None)
        object.__setattr__(self, "reason_codes", ())

    monkeypatch.setattr(cal.ScientificEtfFlowResult, "__init__", replacement)
    assert parent_flow_result().evaluability_state == "WRONG"
    admission = isolated.run_isolated_scientific_request(FLOW_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert admission.result["evaluability_state"] == "EVALUABLE"
    assert admission.result["feature"]["feature_id"] == "ETF_FLOW_5D"


def test_parent_imported_class_replacement_leaves_the_worker_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class Substitute(_flow.EtfFlowFeatureResult):  # type: ignore[misc]
        @property
        def feature_id(self) -> str:  # type: ignore[override]
            return "WRONG"

    monkeypatch.setattr(_flow, "EtfFlowFeatureResult", Substitute)
    assert _flow.EtfFlowFeatureResult is Substitute
    admission = isolated.run_isolated_scientific_request(FLOW_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert admission.result["feature"]["feature_id"] == "ETF_FLOW_5D"


def test_parent_package_reexport_mutation_leaves_the_worker_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import btc_predictor.data as data_package

    def drifted(value, field_name):
        return datetime(2000, 1, 1, tzinfo=UTC)

    monkeypatch.setattr(data_package, "require_utc_datetime", drifted)
    monkeypatch.setattr(cal, "require_utc_datetime", drifted)
    assert parent_session_state() == cal.UNRESOLVED
    admission = isolated.run_isolated_scientific_request(SESSION_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert admission.result["state"] == cal.EXPECTED


def test_parent_sys_modules_substitution_leaves_the_worker_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    honest = sys.modules["btc_predictor.research.etf_calendar_semantics"]
    substitute = types.ModuleType(honest.__name__)
    substitute.__dict__.update(honest.__dict__)
    substitute.reduce_common_session = lambda states: cal.UNRESOLVED
    monkeypatch.setitem(
        sys.modules, "btc_predictor.research.etf_calendar_semantics", substitute
    )
    monkeypatch.setattr(cal, "_semantics", substitute)
    assert parent_session_state() == cal.UNRESOLVED
    admission = isolated.run_isolated_scientific_request(SESSION_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert admission.result["state"] == cal.EXPECTED


def test_parent_builtins_mutation_leaves_the_worker_unaffected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    honest_sum = builtins.sum
    monkeypatch.setattr(
        builtins, "sum", lambda *args, **kwargs: honest_sum(*args, **kwargs) * 2
    )
    assert parent_flow_result().feature.flow_sum_usd != HONEST_FLOW.feature.flow_sum_usd
    admission = isolated.run_isolated_scientific_request(FLOW_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert admission.result["feature"]["flow_sum_usd"] == str(
        HONEST_FLOW.feature.flow_sum_usd
    )


def test_parent_environment_drift_does_not_reach_the_worker(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYTHONPATH", "/nonexistent-scientific-path")
    monkeypatch.setenv("PYTHONHASHSEED", "7")
    monkeypatch.setenv("PYTHONSTARTUP", "/nonexistent-startup.py")
    admission = isolated.run_isolated_scientific_request(SESSION_REQUEST, LAUNCH)
    assert admission.admitted, admission.failure_reason
    assert admission.result["state"] == cal.EXPECTED
    assert admission.response["interpreter_flags"] == {
        "dont_write_bytecode": True,
        "ignore_environment": True,
        "isolated": True,
        "no_site": True,
        "no_user_site": True,
        "safe_path": True,
    }


# ---------------------------------------------------------------------------
# Fail-closed refusals
# ---------------------------------------------------------------------------


def _refusal(request: dict, launch: isolated.WorkerLaunch = None) -> dict:
    outcome = isolated.run_scientific_worker(request, LAUNCH if launch is None else launch)
    assert outcome.exit_status == 3, outcome.stderr.decode()
    response = json.loads(outcome.stdout.decode())
    assert response["status"] == "REFUSED"
    assert response["result"] is None
    assert response["result_digest"] is None
    return response


def test_on_disk_certified_source_mutation_refuses(tmp_path: Path) -> None:
    root = certified_tree(tmp_path / "tree", mutate="btc_predictor/features/flow.py")
    launch = isolated.worker_launch(project_root=root)
    request = session_request(launch, project_source_manifest=MANIFEST)
    assert _refusal(request, launch)["failure_reason"] == "CERTIFIED_SOURCE_SHA_MISMATCH"


def test_wrong_project_origin_refuses(tmp_path: Path) -> None:
    root = certified_tree(tmp_path / "tree")
    shadow = root / "btc_predictor/features/flow"
    shadow.mkdir(parents=True)
    (shadow / "__init__.py").write_text(
        (ROOT / "btc_predictor/features/flow.py").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    launch = isolated.worker_launch(project_root=root)
    request = session_request(launch, project_source_manifest=MANIFEST)
    assert _refusal(request, launch)["failure_reason"] == "WRONG_PROJECT_MODULE_ORIGIN"


def test_unexpected_project_module_refuses() -> None:
    loaded = {
        name
        for name in sys.modules
        if name == "btc_predictor" or name.startswith("btc_predictor.")
    }
    droppable = sorted(
        entry.module
        for entry in MANIFEST
        if entry.module in loaded
        and entry.module not in isolated.REQUIRED_WORKER_PROJECT_MODULES
        and entry.module != isolated.WORKER_ENTRYPOINT_MODULE
        and not entry.path.endswith("/__init__.py")
    )
    assert droppable
    reduced = tuple(entry for entry in MANIFEST if entry.module != droppable[-1])
    assert _refusal(session_request(project_source_manifest=reduced))[
        "failure_reason"
    ] == "UNEXPECTED_PROJECT_MODULE"


def test_non_certified_dependency_environment_refuses() -> None:
    honest = isolated.derive_third_party_manifest(isolated.external_import_roots())
    tampered = (
        protocol.ThirdPartyEntry(
            distribution=honest[0].distribution,
            version=honest[0].version,
            location=honest[0].location,
            record_path=honest[0].record_path,
            record_sha256="f" * 64,
            root_modules=honest[0].root_modules,
        ),
        *honest[1:],
    )
    assert _refusal(session_request(third_party_manifest=tampered))[
        "failure_reason"
    ] == "NON_CERTIFIED_DEPENDENCY_ENVIRONMENT"


def test_third_party_manifest_binds_a_deterministic_installed_identity() -> None:
    entries = isolated.derive_third_party_manifest(isolated.external_import_roots())
    assert entries == tuple(sorted(entries))
    assert {entry.distribution for entry in entries} >= {"cryptography", "numpy"}
    for entry in entries:
        assert entry.record_sha256 == protocol.file_sha256(Path(entry.record_path))
        assert entry.version
    rule = isolated.third_party_dependency_manifest_rule()
    assert rule["non_stdlib_dependency_must_be_explicitly_frozen"] is True
    assert rule["arbitrary_site_packages_state_is_scientific_authority"] is False
    assert rule["environment_manifest_is_launch_bound_not_artifact_bound"] is True
    assert set(rule["frozen_distribution_roots"]) == set(isolated.external_import_roots())


def test_worker_signing_capability_and_leaked_python_environment_refuse() -> None:
    signing = isolated.WorkerLaunch(
        executable=LAUNCH.executable,
        project_root=ROOT,
        sys_path=LAUNCH.sys_path,
        entrypoint=LAUNCH.entrypoint,
        cwd=ROOT,
        environment={
            **isolated.FROZEN_WORKER_ENVIRONMENT,
            protocol.PRIVATE_KEY_FILE_ENV_VAR: "/k",
        },
    )
    assert _refusal(SESSION_REQUEST, signing)["failure_reason"] == (
        "WORKER_SIGNING_CAPABILITY_REFUSED"
    )
    leaked = isolated.WorkerLaunch(
        executable=LAUNCH.executable,
        project_root=ROOT,
        sys_path=LAUNCH.sys_path,
        entrypoint=LAUNCH.entrypoint,
        cwd=ROOT,
        environment={**isolated.FROZEN_WORKER_ENVIRONMENT, "PYTHONHASHSEED": "3"},
    )
    assert _refusal(SESSION_REQUEST, leaked)["failure_reason"] == (
        "AMBIENT_PYTHON_ENVIRONMENT_LEAKED_INTO_THE_WORKER"
    )


def test_declared_sys_path_must_match_the_parent_controlled_launch() -> None:
    drifted = dict(SESSION_REQUEST, sys_path=[*SESSION_REQUEST["sys_path"], "/extra"])
    assert _refusal(drifted)["failure_reason"] == (
        "WORKER_SYS_PATH_IS_NOT_PARENT_CONTROLLED"
    )


def test_worker_scientific_exception_is_a_typed_failure_never_partial_admission() -> None:
    broken = tuple(
        row for row in SESSION_RECORDS if row["record_kind"] != cal.NORMALIZED_SCHEDULE_KIND
    )
    request = session_request(evidence_records=broken)
    assert _refusal(request)["failure_reason"].startswith("WORKER_SCIENTIFIC_EXCEPTION:")
    admission = isolated.admit_worker_result(
        request, isolated.run_scientific_worker(request, LAUNCH)
    )
    assert admission.admitted is False
    assert admission.result is None


def test_timeout_crash_and_extra_output_are_never_admitted() -> None:
    timed_out = isolated.WorkerProcessOutcome(
        exit_status=None, timed_out=True, stdout=b"", stderr=b"", request_digest="a" * 64
    )
    assert isolated.admit_worker_result(SESSION_REQUEST, timed_out).failure_reason == (
        "WORKER_TIMEOUT"
    )
    crashed = isolated.WorkerProcessOutcome(
        exit_status=-9, timed_out=False, stdout=b"", stderr=b"", request_digest="a" * 64
    )
    assert isolated.admit_worker_result(SESSION_REQUEST, crashed).failure_reason == (
        "WORKER_EXIT_STATUS_-9"
    )
    admitted = isolated.run_isolated_scientific_request(SESSION_REQUEST, LAUNCH)
    noisy = isolated.WorkerProcessOutcome(
        exit_status=0,
        timed_out=False,
        stdout=b"log line\n" + admitted.outcome.stdout,
        stderr=b"",
        request_digest=admitted.outcome.request_digest,
    )
    assert isolated.admit_worker_result(SESSION_REQUEST, noisy).failure_reason == (
        "WORKER_STDOUT_IS_NOT_EXACTLY_ONE_PROTOCOL_PAYLOAD"
    )
    replayed = isolated.WorkerProcessOutcome(
        exit_status=0,
        timed_out=False,
        stdout=admitted.outcome.stdout,
        stderr=b"",
        request_digest="b" * 64,
    )
    assert "WORKER_BINDING_MISMATCH" in isolated.admit_worker_result(
        SESSION_REQUEST, replayed
    ).failure_reason


def test_real_worker_timeout_is_not_admitted() -> None:
    impatient = isolated.WorkerLaunch(
        executable=LAUNCH.executable,
        project_root=ROOT,
        sys_path=LAUNCH.sys_path,
        entrypoint=LAUNCH.entrypoint,
        cwd=ROOT,
        timeout_seconds=1,
    )
    admission = isolated.run_isolated_scientific_request(SESSION_REQUEST, impatient)
    assert admission.admitted is False
    assert admission.failure_reason == "WORKER_TIMEOUT"
    assert admission.result is None


# ---------------------------------------------------------------------------
# Scientific response evidence
# ---------------------------------------------------------------------------


def test_scientific_response_evidence_is_complete_and_address_free() -> None:
    admission = isolated.run_isolated_scientific_request(SESSION_REQUEST, LAUNCH)
    evidence = isolated.scientific_response_evidence(admission)
    assert sorted(evidence) == [
        "admitted",
        "calendar_authority_hash",
        "decision_time",
        "failure_reason",
        "interpreter_identity",
        "operation",
        "process_exit_status",
        "process_timed_out",
        "request_digest",
        "request_schema_version",
        "result_digest",
        "third_party_manifest_digest",
        "trusted_persistence_authority_hash",
        "worker_authority_hash",
        "worker_source_manifest_digest",
    ]
    assert evidence["admitted"] is True
    assert evidence["failure_reason"] is None
    assert evidence["process_exit_status"] == 0
    assert evidence["worker_authority_hash"] == DECISION["definition_sha256"]
    assert evidence["trusted_persistence_authority_hash"] == (
        "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
    )
    assert evidence["worker_source_manifest_digest"] == protocol.manifest_digest(MANIFEST)
    protocol.assert_address_free(evidence)
    with pytest.raises(
        protocol.ScientificWorkerProtocolError, match="CONTAINS_A_MEMORY_ADDRESS"
    ):
        protocol.assert_address_free({"owner": "<object at 0x7f1234ab>"})


# ---------------------------------------------------------------------------
# Preserved static authority
# ---------------------------------------------------------------------------


def test_compiled_root_witness_and_current_production_blockers_are_preserved() -> None:
    production = DECISION["current_production_expected_result"]
    source = isolated.CALENDAR_SOURCE.read_text(encoding="utf-8")
    assert production["reviewed_source_sha256"] == isolated.source_sha256(source)
    assert production["root_write_clear_or_delete_findings"] == 0
    assert production["root_cell_finding"] == "common_etf_session_status:evidence_store"
    assert production["ast_store_use_normal_form"] == (
        "REFUSED_AT_THE_SAME_GENERATOR_CAPTURE"
    )
    assert production["both_static_layers_refuse_the_same_single_construct"] is True
    assert production["wrapper_installer_removal_required"] is True
    assert production["isolated_scientific_worker_implemented_in_production"] is False
    assert production["calendar_production_conformance"] == "NO"
    assert production["calendar_implementation"] == "BLOCKED"
    assert production["module_namespace_write_scopes"] == [
        "_install_exact_dependency_guards"
    ]
    assert (
        production["artifact_builder_dispatch_rewrite_required_solely_by_this_decision"]
        is False
    )


def test_closed_store_grammar_and_root_cell_rule_are_preserved() -> None:
    grammar = isolated.store_root_and_direct_use_grammar()
    assert grammar["preserved_under_process_isolation"] is True
    assert grammar["process_isolation_legalizes_wrappers"] is False
    assert grammar["root_may_be_a_cell_variable_of_a_conforming_owner"] is False
    assert grammar["known_generator_capture_rewrite_still_required"] == (
        "common_etf_session_status:evidence_store"
    )
    source = isolated.CALENDAR_SOURCE.read_text(encoding="utf-8")
    with pytest.raises(
        isolated.narrow.NormalFormError, match="FORBIDDEN_NESTED_SCOPE_CAPTURE"
    ):
        isolated.narrow.audit_store_capability_normal_form(source)


def test_exact_eleven_owner_census_and_graph_are_preserved() -> None:
    rule = isolated.replay_owner_graph_rule()
    assert rule["owner_count"] == 11
    assert rule["owners"] == [
        "derive_normalized_schedule_from_official_source",
        "venue_session_calendar_record",
        "_verify_schedule",
        "_verify_schedule_record",
        "validate_normalized_schedule_against_source",
        "_verify_venue_row",
        "venue_session_status",
        "common_etf_session_status",
        "expected_etf_publication_dates",
        "derive_etf_window_calendar",
        "scientific_etf_flow_window",
    ]
    assert rule["cycles_permitted"] is False
    assert rule["unknown_forwarding_permitted"] is False
    assert rule["every_owner_path_terminates_at_documented_store_api"] is True
    assert rule["documented_terminals"] == ["put", "get", "records", "envelopes"]
    assert rule["process_isolation_redefines_the_owner_graph"] is False
    source = isolated.CALENDAR_SOURCE.read_text(encoding="utf-8")
    assert sorted(isolated.narrow.verify_replay_owner_census(source)) == sorted(
        isolated.FROZEN_REPLAY_OWNERS
    )


def test_direct_dependency_body_rule_is_preserved_and_still_blocked() -> None:
    rule = isolated.direct_body_dependency_rule()
    assert rule["wrapper_installed_guards_permitted"] is False
    assert rule["functools_wraps_authority_guards_permitted"] is False
    assert rule["wrapper_installer_removal_required"] == "_install_exact_dependency_guards"
    assert sorted(rule["required_direct_bodies"]) == sorted(
        [
            "CalendarEvidenceStore.put",
            "CalendarEvidenceStore.get",
            "CalendarEvidenceStore.records",
            "CalendarEvidenceStore.envelopes",
            "collect_official_calendar",
        ]
    )
    findings = isolated.direct_dependency_body_findings(
        isolated.CALENDAR_SOURCE.read_text(encoding="utf-8")
    )
    assert findings["bodies_absent"] == []
    assert findings["decorated_bodies"] == []
    assert findings["conforms"] is False


def test_io_and_capability_boundary_is_explicit_about_its_limits() -> None:
    boundary = isolated.worker_io_and_capability_boundary()
    assert boundary["worker_network_permitted"] is False
    assert boundary["worker_private_signing_key_permitted"] is False
    assert boundary["worker_authoritative_db_write_permitted"] is False
    assert boundary["result_admission_is_a_controller_responsibility"] is True
    assert boundary["operating_system_level_network_sandbox_claimed"] is False
    assert (
        boundary["certified_source_universe_includes_db_and_network_capable_modules"]
        is True
    )
    assert boundary["collection_authority_moved_into_the_worker"] is False


def test_no_etf_calendar_production_source_was_modified() -> None:
    completed = subprocess.run(
        [
            "git",
            "status",
            "--porcelain",
            "--",
            "btc_predictor/research/etf_publication_calendar.py",
        ],
        capture_output=True,
        check=True,
        cwd=str(ROOT),
    )
    assert completed.stdout.decode().strip() == ""
