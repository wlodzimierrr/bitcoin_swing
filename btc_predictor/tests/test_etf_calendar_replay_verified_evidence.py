"""POSTP1-001V2A-PAD5 replay-verified ETF calendar evidence tests.

The decisive regressions reproduce all three ``POSTP1-002V2A-PAD4-R5`` routes
**in process, against the producer**, and then show what the standalone verifier
does with each.  The ``gc`` registry insertion that failed R5 is performed here
exactly as the review performed it, and so is the canonical-class mutation the
review left as a blocking ambiguity.  Neither is excluded by domain text; both
are run, and the verifier's verdict is the proof.

Everything the ``PAD4-R5`` review reproduced as valid is re-proved rather than
assumed: the four-file bootstrap pre-execution binding, fresh-exec isolation,
Repairs A/B/C/D, the frozen interpreter identity, the certified source manifest
and the third-party authority.  The reviewed ``PAD4-R2`` fixtures — the
certified tree and the pre-launch drifted bootstrap trees — are imported rather
than forked.
"""

from __future__ import annotations

import ast
import gc
import json
import os
import subprocess
import sys
from pathlib import Path
from weakref import ref

import pytest

from btc_predictor.research import etf_calendar_evidence_verifier as verifier
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r5 as r5
from btc_predictor.research import etf_calendar_replay_verified_evidence as pad5
from btc_predictor.research import (
    etf_calendar_replay_verified_evidence_contract as contract,
)
from btc_predictor.research import etf_calendar_isolated_scientific_worker_r1 as r1
from btc_predictor.research import trusted_acquisition as trusted
from btc_predictor.tests import test_etf_calendar_isolated_scientific_worker_r2 as base
from etf_calendar_worker import protocol_r2 as protocol


ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = ROOT / pad5.OUTPUT_NAMESPACE
R5_ARTIFACT_DIR = ROOT / r5.OUTPUT_NAMESPACE

DECISION = pad5.replay_verified_evidence_v1_definition()
CANDIDATE_HASH = DECISION["definition_sha256"]

#: The trusted context the producer builds requests from.  Its
#: ``worker_authority_sha256`` is the non-circular architecture identity the
#: verifier independently computes from its own frozen source, so the verifier
#: never has to be told what to expect.
CONTEXT = r5.candidate_review_authority_context(
    contract.REPLAY_VERIFIED_EVIDENCE_ARCHITECTURE_SHA256
)
LAUNCH = r5.worker_launch()

SIGNER = trusted.AcquisitionSigner.generate_test_only()
SECOND_SIGNER = trusted.AcquisitionSigner.generate_test_only("TEST_ONLY_SECOND_V1")


def _trust_root(signer: trusted.AcquisitionSigner) -> dict:
    key = signer.verification_key()
    return {
        "algorithm": key.algorithm,
        "authority_version": key.authority_version,
        "key_id": key.key_id,
        "public_key_base64": key.public_key_base64,
        "public_key_sha256": key.public_key_sha256,
        "status": key.status,
    }


TRUST_ROOT = _trust_root(SIGNER)
SECOND_TRUST_ROOT = _trust_root(SECOND_SIGNER)


def session_request(**overrides) -> dict:
    return r5.build_scientific_request(
        CONTEXT,
        launch=LAUNCH,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": base.SESSION_DAY.isoformat()},
        evidence_records=base.SESSION_RECORDS,
        decision_time=base.DECISION_TIME.isoformat(),
        **overrides,
    )


REQUEST = session_request()
ENVELOPES = [SIGNER.sign_payload(record) for record in base.SESSION_RECORDS]


def _genuine_response() -> dict:
    """One real end-to-end worker execution through the preserved launch path."""

    execution = r5.run_isolated_scientific_request(CONTEXT, REQUEST, LAUNCH)
    assert execution.admitted is True
    return execution.response


RESPONSE = _genuine_response()


# ---------------------------------------------------------------------------
# Harness
# ---------------------------------------------------------------------------


def _sibling_base() -> Path:
    """A temp base on the repository filesystem but outside the repository tree.

    The ``PAD4-R5`` review recorded two invalid placements: ``/tmp`` produced
    cross-device hard-link failures in the certified-tree fixtures, and an
    in-repository base contaminated the certified project namespace.  A sibling
    of the repository root is on the same filesystem and outside the tree.
    """

    sibling = ROOT.parent / "pad5_tmp"
    sibling.mkdir(parents=True, exist_ok=True)
    return sibling


_COUNTER = [0]


@pytest.fixture
def workspace() -> Path:
    return _unique(_sibling_base())


def _unique(base_dir: Path) -> Path:
    _COUNTER[0] += 1
    target = base_dir / f"case{os.getpid()}_{_COUNTER[0]:04d}"
    target.mkdir(parents=True, exist_ok=False)
    return target


def write_item(
    workspace: Path,
    *,
    request: dict | None = None,
    response: dict | None = None,
    envelopes=None,
    trust_root: dict | None = TRUST_ROOT,
    item_id: str = "item0001",
) -> Path:
    evidence = workspace / "evidence"
    pad5.write_evidence_item(
        evidence / item_id,
        scientific_request=REQUEST if request is None else request,
        response=RESPONSE if response is None else response,
        input_envelopes=ENVELOPES if envelopes is None else envelopes,
        test_trust_root=trust_root,
    )
    return evidence


def verify(
    workspace: Path,
    evidence: Path,
    *,
    mode: str = contract.NON_AUTHORITATIVE_TEST_MODE,
    project_root: Path = ROOT,
    sys_path=None,
) -> tuple[dict, ...]:
    """Run the standalone verifier and return its persisted records."""

    records_dir = workspace / "records"
    outcome = pad5.run_verifier(
        evidence,
        records_dir,
        executable=sys.executable,
        sys_path=list(LAUNCH.sys_path) if sys_path is None else list(sys_path),
        pycache_namespace=workspace / "pycache",
        mode=mode,
        project_root=project_root,
        timeout_seconds=600,
    )
    assert not outcome["timed_out"], outcome["stderr"].decode()
    assert outcome["exit_status"] in (
        verifier.EXIT_ALL_ACCEPTED,
        verifier.EXIT_SOME_REJECTED,
    ), outcome["stderr"].decode()
    return pad5.read_verification_records(records_dir)


def only(records) -> dict:
    assert len(records) == 1, records
    return records[0]


def _replaced(payload: dict, **overrides) -> dict:
    row = json.loads(json.dumps(payload))
    row.update(overrides)
    return row


# ---------------------------------------------------------------------------
# Decision integrity
# ---------------------------------------------------------------------------


def test_decision_scope_status_and_strategy_are_frozen() -> None:
    assert DECISION["decision_version"] == "ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1"
    assert DECISION["program_ticket"] == "POSTP1-001V2A-PAD5"
    assert DECISION["pre_data"] is True
    assert DECISION["correction_is_a_new_architecture_family"] is True
    assert DECISION["supersedes"] == pad5.FAILED_PAD4_R5_SHA256
    assert DECISION["final_classification"] == (
        "ETF_CALENDAR_REPLAY_VERIFIED_EVIDENCE_V1_READY_FOR_XHIGH_REVIEW"
    )
    assert DECISION["authorization"] == {
        "independent_proof_architecture_xhigh_review_may_begin": True,
        "calendar_implementation_may_begin": False,
        "postp1_001v2a_i2_may_begin": False,
        "postp1_001v2r1_may_begin": False,
        "prospective_collection_may_begin": False,
    }


def test_material_children_are_mechanical_bound_and_digest_valid() -> None:
    children = pad5._children()
    assert len(children) == DECISION["material_child_count"]
    for name, payload in children.items():
        pad5._verify_definition_digest(payload)
        assert DECISION["child_definition_sha256"][name] == payload["definition_sha256"]
    declared = set(
        pad5.CARRIED_FORWARD_CHILDREN + pad5.REISSUED_CHILDREN + pad5.NEW_CHILDREN
    )
    assert declared == set(children)


def test_carried_forward_children_are_byte_identical_to_the_reviewed_r5() -> None:
    """Carried children are *bound* from the reviewed builders, not restated."""

    persisted = {
        target.stem: json.loads(target.read_text("ascii"))
        for target in R5_ARTIFACT_DIR.glob("*.json")
    }
    children = pad5._children()
    for name in pad5.CARRIED_FORWARD_CHILDREN:
        assert children[name] == persisted[name], name


def test_retired_r5_identity_children_are_not_copied_here() -> None:
    children = pad5._children()
    for name in pad5.RETIRED_R5_IDENTITY_CHILDREN:
        assert name not in children, name
    assert (R5_ARTIFACT_DIR / "identity_safe_snapshot_binding_rule.json").is_file()


def test_reissued_children_correct_only_the_contradicted_clauses() -> None:
    children = pad5._children()
    for name in pad5.REISSUED_CHILDREN:
        payload = children[name]
        assert payload["reissued_because"].startswith("THE_REVIEWED_PAYLOAD_ASSERTS")
        assert payload["corrected_clauses"]
        assert len(payload["reissued_from_definition_sha256"]) == 64
        assert payload["contract_version"] != payload["reissued_from_contract_version"]
    boundary = children["trusted_process_and_isolation_boundary"]
    assert boundary["authority_bearing_production_operations"] == 0
    assert boundary["authoritative_scientific_execution_is_closed_end_to_end"] is False


def test_failed_lineage_is_extended_with_r5() -> None:
    assert pad5.FAILED_PAD4_R5_SHA256 == (
        "b4168dc9c757f3cdbdeed48e9a91cc35eb921728adb5d38d0d5b76fd2ef861c7"
    )
    assert pad5.FAILED_ARCHITECTURE_LINEAGE[-1] == pad5.FAILED_PAD4_R5_SHA256
    assert len(pad5.FAILED_ARCHITECTURE_LINEAGE) == len(
        r5.FAILED_ARCHITECTURE_LINEAGE
    ) + 1
    assert r5.CONTROLLER_RELATIVE_PATH in pad5.FAILED_LINEAGE_CONTROLLER_MODULES
    assert pad5.FAILED_LINEAGE_CONTROLLER_MODULES[-1] == r5.CONTROLLER_RELATIVE_PATH


def test_preserved_authority_values_reproduce_exactly() -> None:
    assert DECISION["worker_bootstrap_source_count"] == 4
    assert DECISION["worker_bootstrap_manifest_digest"] == (
        "1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411"
    )
    assert DECISION["candidate_worker_source_module_count"] == 120
    assert DECISION["candidate_worker_source_manifest_digest"] == (
        "7ffbf15792d33e0cd387eb995d8d733c1fa1b98b2859153957c670f796a44e8e"
    )
    assert DECISION["pre_i2_project_source_module_count"] == 116
    assert DECISION["pre_i2_project_source_manifest_digest"] == (
        "674b006ae66b8aace3458cb870f898ecad33e1f23833436954d36749b3aadbb8"
    )
    assert DECISION["third_party_authority_digest"] == (
        "23e4f1d89a503b43fc39ee0ae3516b742f6db72028224d78a9181be6726298a6"
    )
    assert DECISION["trusted_persistence_authority_sha256"] == (
        "02f96203bf4ff21a5603161c54db2e5325f81deacfb0af5caa1478c2f1a12772"
    )


def test_failed_r5_namespace_still_reproduces_unchanged() -> None:
    assert r5.restore_artifacts(R5_ARTIFACT_DIR)["definition_sha256"] == (
        pad5.FAILED_PAD4_R5_SHA256
    )


def test_write_and_restore_artifacts_round_trip(workspace: Path) -> None:
    decision = pad5.write_artifacts(workspace / "out")
    assert decision == DECISION
    assert pad5.restore_artifacts(workspace / "out") == DECISION


def test_persisted_namespace_reproduces_exactly() -> None:
    assert pad5.restore_artifacts(ARTIFACT_DIR) == DECISION


def test_restore_refuses_a_mutated_child(workspace: Path) -> None:
    pad5.write_artifacts(workspace / "out")
    target = workspace / "out" / "comparison_projection_definition.json"
    payload = json.loads(target.read_text("ascii"))
    payload["digest_only_acceptance_permitted"] = True
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "ascii")
    with pytest.raises(pad5.ReplayVerifiedEvidenceDecisionError):
        pad5.restore_artifacts(workspace / "out")


def test_restore_refuses_a_mutated_report(workspace: Path) -> None:
    pad5.write_artifacts(workspace / "out")
    target = workspace / "out" / pad5.REPORT_FILENAME
    target.write_text(target.read_text("utf-8") + "\ndrift\n", "utf-8")
    with pytest.raises(pad5.ReplayVerifiedEvidenceDecisionError):
        pad5.restore_artifacts(workspace / "out")


def test_child_order_variation_does_not_change_the_parent() -> None:
    reversed_registry = tuple(reversed(pad5._CHILD_ARTIFACTS))
    assert pad5.replay_verified_evidence_v1_definition(reversed_registry) == DECISION


@pytest.mark.parametrize("seed", ["0", "1", "8675309"])
def test_definition_is_deterministic_across_hash_seeds(
    seed: str, workspace: Path
) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "from btc_predictor.research import "
            "etf_calendar_replay_verified_evidence as pad5;"
            "print(pad5.replay_verified_evidence_v1_definition()"
            "['definition_sha256'])",
        ],
        capture_output=True,
        check=True,
        cwd=str(workspace),
        env={**os.environ, "PYTHONHASHSEED": seed, "PYTHONPATH": str(ROOT)},
    )
    assert completed.stdout.decode().strip() == CANDIDATE_HASH


def test_artifacts_reproduce_from_an_alternate_working_directory(
    workspace: Path,
) -> None:
    output = workspace / "fresh"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "btc_predictor.research.etf_calendar_replay_verified_evidence",
            str(output),
        ],
        capture_output=True,
        check=True,
        cwd=str(workspace),
        env={**os.environ, "PYTHONPATH": str(ROOT)},
    )
    assert completed.stdout.decode().strip() == CANDIDATE_HASH
    assert pad5.restore_artifacts(output) == DECISION
    for filename in sorted(p.name for p in ARTIFACT_DIR.iterdir()):
        assert (output / filename).read_bytes() == (ARTIFACT_DIR / filename).read_bytes()


# ---------------------------------------------------------------------------
# Verifier closure and interface
# ---------------------------------------------------------------------------


def test_verifier_closure_is_derived_not_listed_and_wholly_certified() -> None:
    audit = pad5.audit_verifier_source_closure()
    assert audit["closed"] is True and audit["findings"] == []
    assert audit["derivation_is_a_probe_not_a_list"] is True
    assert audit["uncertified_members"] == []
    assert audit["failed_lineage_members"] == []
    assert audit["producer_is_outside_the_verifier_closure"] is True
    assert audit["pad5_members"] == [
        contract.VERIFIER_ENTRY_MODULE,
        contract.CONTRACT_MODULE,
    ]
    assert audit["module_count"] == DECISION["verifier_source_module_count"]


def test_verifier_closure_agrees_with_the_reviewed_derivation() -> None:
    """The new derivation must be the reviewed one, not a lookalike."""

    mine = contract.derive_source_manifest(ROOT)
    reviewed = r1.derive_project_source_manifest(
        ROOT, seeds=contract.VERIFIER_CLOSURE_SEEDS
    )
    assert [entry.as_material() for entry in mine] == [
        entry.as_material() for entry in reviewed
    ]


def test_verifier_closure_holds_no_failed_lineage_controller() -> None:
    modules = {row["module"] for row in pad5.audit_verifier_source_closure()["members"]}
    for relative in pad5.FAILED_LINEAGE_CONTROLLER_MODULES:
        dotted = relative.removesuffix(".py").replace("/", ".")
        assert dotted not in modules, dotted
    assert contract.PRODUCER_MODULE not in modules


def test_verifier_closure_gaining_an_uncertified_module_fails_the_audit(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mutation probe: an uncertified import in the verifier must fail the audit."""

    tree = workspace / "tree"
    _pad5_tree(tree)
    target = tree / pad5.VERIFIER_RELATIVE_PATH
    original = target.read_text("utf-8")
    source = original.replace(
        "    mode = argv[5]\n",
        "    mode = argv[5]\n"
        "    from btc_predictor.research import "
        "etf_calendar_isolated_scientific_worker_r5 as _uncertified\n",
        1,
    )
    assert source != original
    target.unlink()
    target.write_text(source, "utf-8")
    audit = pad5.audit_verifier_source_closure(tree)
    assert audit["closed"] is False
    assert any(
        finding.startswith("VERIFIER_CLOSURE_DECLARES_AN_UNRESOLVABLE_IMPORT")
        for finding in audit["findings"]
    ), audit["findings"]


def test_verifier_closure_reaching_a_failed_lineage_controller_fails_the_audit(
    workspace: Path,
) -> None:
    """Mutation probe: the same import, with the module actually present."""

    tree = workspace / "tree"
    _pad5_tree(tree)
    for relative in pad5.FAILED_LINEAGE_CONTROLLER_MODULES:
        target = tree / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            os.link(ROOT / relative, target)
    target = tree / pad5.VERIFIER_RELATIVE_PATH
    original = target.read_text("utf-8")
    source = original.replace(
        "    mode = argv[5]\n",
        "    mode = argv[5]\n"
        "    from btc_predictor.research import "
        "etf_calendar_isolated_scientific_worker_r5 as _uncertified\n",
        1,
    )
    assert source != original
    target.unlink()
    target.write_text(source, "utf-8")
    audit = pad5.audit_verifier_source_closure(tree)
    assert audit["closed"] is False
    assert any(
        finding.startswith("VERIFIER_CLOSURE_REACHES_A_FAILED_LINEAGE_CONTROLLER")
        or finding.startswith("VERIFIER_CLOSURE_CONTAINS_UNCERTIFIED_MODULE")
        for finding in audit["findings"]
    ), audit["findings"]


def test_verifier_interface_admits_nothing_executable() -> None:
    audit = pad5.audit_verifier_interface()
    assert audit["closed"] is True and audit["findings"] == []
    assert audit["forbidden_name_occurrences"] == []
    assert audit["entry_parameters"] == ["argv"]
    assert audit["entry_parameter_annotations"] == ["list[str]"]
    assert audit["entry_accepts_varargs_or_kwargs"] is False
    assert len(contract.VERIFIER_ARGUMENT_NAMES) == 5


@pytest.mark.parametrize(
    "injection",
    [
        "def main(argv: list[str], callback=None) -> int:",
        "def main(argv: list[str], *plugins) -> int:",
    ],
)
def test_a_caller_object_added_to_the_verifier_interface_fails_the_audit(
    injection: str, workspace: Path
) -> None:
    """Mutation probe: any caller-object channel must fail the interface audit."""

    tree = workspace / "tree"
    _pad5_tree(tree)
    target = tree / pad5.VERIFIER_RELATIVE_PATH
    source = target.read_text("utf-8").replace(
        "def main(argv: list[str]) -> int:", injection, 1
    )
    target.unlink()
    target.write_text(source, "utf-8")
    audit = pad5.audit_verifier_interface(tree)
    assert audit["closed"] is False
    assert "VERIFIER_ENTRY_SIGNATURE_IS_NOT_A_LIST_OF_STRINGS" in audit["findings"]


def test_a_pickle_channel_added_to_the_verifier_fails_the_audit(
    workspace: Path,
) -> None:
    tree = workspace / "tree"
    _pad5_tree(tree)
    target = tree / pad5.VERIFIER_RELATIVE_PATH
    source = target.read_text("utf-8").replace(
        "import json\nimport sys\n", "import json\nimport pickle\nimport sys\n", 1
    )
    target.unlink()
    target.write_text(source, "utf-8")
    audit = pad5.audit_verifier_interface(tree)
    assert audit["closed"] is False
    assert any(
        "VERIFIER_INTERFACE_REACHES_A_FORBIDDEN_NAME" in finding
        for finding in audit["findings"]
    )


def _pad5_tree(destination: Path) -> Path:
    """A certified tree that also carries the three ``PAD5`` modules."""

    root = base.certified_tree(destination)
    for relative in pad5.PAD5_OWNED_SOURCE:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            os.link(ROOT / relative, target)
    return root


# ---------------------------------------------------------------------------
# The deterministic comparison projection
# ---------------------------------------------------------------------------


def test_projection_is_a_closed_inclusion_list_over_every_response_field() -> None:
    audit = pad5.audit_comparison_projection()
    assert audit["closed"] is True and audit["findings"] == []
    assert audit["is_a_closed_inclusion_list"] is True
    assert audit["is_defined_by_exclusion"] is False
    assert audit["unclassified_response_fields"] == []
    assert set(contract.IN_PROJECTION_AUTHORITY_FIELDS) | set(
        contract.RUN_LOCAL_FIELDS
    ) == set(protocol.RESPONSE_FIELDS)
    assert "result" in contract.IN_PROJECTION_AUTHORITY_FIELDS
    assert "result_digest" in contract.IN_PROJECTION_AUTHORITY_FIELDS
    for name in protocol.AUTHORITY_BOUND_RESPONSE_FIELDS:
        assert name in contract.IN_PROJECTION_AUTHORITY_FIELDS


def test_every_projected_field_carries_a_written_justification() -> None:
    for name in contract.IN_PROJECTION_AUTHORITY_FIELDS:
        assert contract.PROJECTION_FIELD_JUSTIFICATION[name].startswith(
            "IN_PROJECTION_AUTHORITY:"
        )
    for name in contract.RUN_LOCAL_FIELDS:
        assert contract.PROJECTION_FIELD_JUSTIFICATION[name].startswith("RUN_LOCAL:")


def test_projection_refuses_a_response_missing_a_projected_field() -> None:
    incomplete = {k: v for k, v in RESPONSE.items() if k != "result_digest"}
    with pytest.raises(contract.ReplayVerifiedEvidenceError):
        contract.comparison_projection(incomplete)


def test_run_to_run_variation_is_measured_not_assumed(workspace: Path) -> None:
    """Two more re-executions, different pycache namespaces and cwds.

    This is the empirical basis for ``RUN_LOCAL`` being empty.  Every response
    field is compared, not just the projected ones.
    """

    from dataclasses import replace as _replace

    responses = []
    for index in range(2):
        namespace = workspace / f"ns{index}"
        namespace.mkdir(parents=True)
        cwd = workspace / f"cwd{index}"
        cwd.mkdir(parents=True)
        inner = namespace / "inner"
        inner.mkdir(parents=True)
        launch = _replace(LAUNCH, cwd=cwd, pycache_namespace_root=namespace)
        execution = r5.run_isolated_scientific_request(
            CONTEXT, REQUEST, launch, pycache_namespace=inner
        )
        assert execution.admitted is True, execution.failure_reason
        responses.append(execution.response)
    first, second = responses
    differing = sorted(
        name for name in protocol.RESPONSE_FIELDS if first.get(name) != second.get(name)
    )
    assert differing == []
    assert protocol.canonical_json_bytes(first) == protocol.canonical_json_bytes(second)
    assert set(contract.RUN_LOCAL_FIELDS) == set(differing)


# ---------------------------------------------------------------------------
# Proof obligations — acceptance
# ---------------------------------------------------------------------------


def test_genuine_producer_output_is_accepted(workspace: Path) -> None:
    record = only(verify(workspace, write_item(workspace)))
    assert record["verdict"] == contract.ACCEPTED
    assert record["reason_code"] == contract.ACCEPTED_REASON
    assert record["recorded_projection_digest"] == record["rederived_projection_digest"]
    assert record["input_envelope_count"] == len(ENVELOPES)
    assert record["verifier_source_module_count"] == (
        DECISION["verifier_source_module_count"]
    )


def test_genuine_bytes_relayed_by_another_process_are_the_same_evidence(
    workspace: Path,
) -> None:
    """Relay is dissolved, not reclassified: the same bytes are the same evidence."""

    first = only(verify(workspace, write_item(workspace)))
    relay = _unique(_sibling_base())
    evidence = write_item(relay, item_id="relayed")
    second = only(verify(relay, evidence))
    assert second["verdict"] == contract.ACCEPTED
    assert second["request_digest"] == first["request_digest"]
    assert second["response_digest"] == first["response_digest"]
    assert second["recorded_projection_digest"] == first["recorded_projection_digest"]


def test_verifying_the_same_evidence_twice_yields_byte_identical_records(
    workspace: Path,
) -> None:
    evidence = write_item(workspace)
    first_dir = workspace / "records"
    verify(workspace, evidence)
    first = (first_dir / ("item0001" + contract.VERIFICATION_RECORD_FILENAME_SUFFIX)).read_bytes()
    second_workspace = _unique(_sibling_base())
    verify(second_workspace, evidence)
    second = (
        second_workspace
        / "records"
        / ("item0001" + contract.VERIFICATION_RECORD_FILENAME_SUFFIX)
    ).read_bytes()
    assert first == second


# ---------------------------------------------------------------------------
# Proof obligations — the three PAD4-R5 routes, reproduced in process
# ---------------------------------------------------------------------------


def _recover_r5_registry():
    """Recover the closure-owned R5 registry exactly as the review did.

    Public ``gc`` graph traversal only: no closure-cell recovery, no
    private-name reflection and no module mutation.  This is the exact
    ``POSTP1-002V2A-PAD4-R5`` P0.
    """

    gc.collect()
    found = []
    for candidate in gc.get_objects():
        if not isinstance(candidate, dict) or not candidate:
            continue
        try:
            items = list(candidate.items())
        except RuntimeError:  # pragma: no cover - concurrent mutation
            continue
        if all(
            isinstance(key, int)
            and isinstance(value, tuple)
            and len(value) == 2
            and isinstance(value[1], r5.FrozenAuthoritySnapshot)
            for key, value in items
        ):
            found.append(candidate)
    return found


def test_the_r5_gc_registry_route_still_reproduces_in_process() -> None:
    """The R5 P0 is reproduced, not excluded by domain text."""

    execution = r5.run_isolated_scientific_request(CONTEXT, REQUEST, LAUNCH)
    registries = _recover_r5_registry()
    assert registries, "the R5 closure-owned registry was not recoverable"
    registry = next(r for r in registries if id(execution) in r)
    entry = registry[id(execution)]
    forged = object.__new__(r5.AuthoritativeScientificExecution)
    try:
        registry[id(forged)] = type(entry)(ref(forged), entry.snapshot)
        assert forged is not execution
        assert forged.admitted is True
        assert forged.response == execution.response
    finally:
        registry.pop(id(forged), None)


def test_gc_registry_insertion_with_a_genuine_snapshot_is_the_same_evidence(
    workspace: Path,
) -> None:
    """A forged object holding genuine bytes presents the genuine evidence.

    The verifier accepts them as that same evidence and nothing new is
    admitted: the accepted record carries the same digests the honest item
    produced.
    """

    execution = r5.run_isolated_scientific_request(CONTEXT, REQUEST, LAUNCH)
    registry = next(r for r in _recover_r5_registry() if id(execution) in r)
    entry = registry[id(execution)]
    forged = object.__new__(r5.AuthoritativeScientificExecution)
    try:
        registry[id(forged)] = type(entry)(ref(forged), entry.snapshot)
        presented = forged.response
    finally:
        registry.pop(id(forged), None)

    evidence = write_item(workspace, response=presented)
    record = only(verify(workspace, evidence))
    assert record["verdict"] == contract.ACCEPTED
    control = _unique(_sibling_base())
    honest = only(verify(control, write_item(control)))
    assert record["response_digest"] == honest["response_digest"]
    assert record["recorded_projection_digest"] == honest["recorded_projection_digest"]


def test_gc_registry_insertion_with_a_fabricated_snapshot_is_rejected(
    workspace: Path,
) -> None:
    """The exact R5 P0, but carrying fabricated content."""

    execution = r5.run_isolated_scientific_request(CONTEXT, REQUEST, LAUNCH)
    registry = next(r for r in _recover_r5_registry() if id(execution) in r)
    entry = registry[id(execution)]
    fabricated_response = _replaced(RESPONSE, result=dict(base.FABRICATED_RESULT))
    fabricated_response["result_digest"] = protocol.result_digest(
        fabricated_response["result"]
    )
    fabricated_bytes = protocol.canonical_json_bytes(fabricated_response)
    snapshot = entry.snapshot._replace(
        response_bytes=fabricated_bytes,
        response_digest=protocol.digest_bytes(fabricated_bytes),
        result_bytes=protocol.canonical_json_bytes(fabricated_response["result"]),
        result_digest=fabricated_response["result_digest"],
    )
    forged = object.__new__(r5.AuthoritativeScientificExecution)
    try:
        registry[id(forged)] = type(entry)(ref(forged), snapshot)
        assert forged.admitted is True
        presented = forged.response
        assert presented["result"]["state"] == "FABRICATED_BOOTSTRAP_STATE"
    finally:
        registry.pop(id(forged), None)

    record = only(verify(workspace, write_item(workspace, response=presented)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_PROJECTION_IS_NOT_BYTE_IDENTICAL"


def test_canonical_class_mutation_presenting_fabricated_content_is_rejected(
    workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The unresolved R5 P1 route, run rather than excluded.

    ``PAD4-R5`` could not decide whether replacing descriptors on the canonical
    class counted as the excluded "module mutation".  This architecture does not
    adopt, redefine or rely on that phrase: the route is performed, and the
    fabricated content simply fails to re-derive.
    """

    fabricated = _replaced(RESPONSE, result=dict(base.FABRICATED_RESULT))
    fabricated["result_digest"] = protocol.result_digest(fabricated["result"])
    monkeypatch.setattr(
        r5.AuthoritativeScientificExecution,
        "response",
        property(lambda self: json.loads(json.dumps(fabricated))),
        raising=True,
    )
    monkeypatch.setattr(
        r5.AuthoritativeScientificExecution,
        "admitted",
        property(lambda self: True),
        raising=True,
    )
    impostor = object.__new__(r5.AuthoritativeScientificExecution)
    assert impostor.admitted is True
    presented = impostor.response
    assert presented["result"]["state"] == "FABRICATED_BOOTSTRAP_STATE"

    record = only(verify(workspace, write_item(workspace, response=presented)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_PROJECTION_IS_NOT_BYTE_IDENTICAL"


def test_a_hostile_producer_fabricating_a_result_is_rejected(
    workspace: Path,
) -> None:
    """Closure recovery, ctypes-free hostile Python, straight past every gate.

    The capability object is lifted out of the closure cells of the R5 bound
    operation and used to mint a genuine-type execution around a fabricated
    snapshot.  Every R5 accessor answers.  The verifier rejects it anyway,
    because the bytes do not re-derive.
    """

    capability = None
    for cell in r5.run_isolated_scientific_request.__closure__ or ():
        value = cell.cell_contents
        if type(value) is object:
            capability = value
    assert capability is not None, "the R5 capability was not recoverable"

    fabricated = _replaced(RESPONSE, result=dict(base.FABRICATED_RESULT))
    fabricated["result_digest"] = protocol.result_digest(fabricated["result"])
    response_bytes = protocol.canonical_json_bytes(fabricated)
    evidence_bytes = protocol.canonical_json_bytes({"forged": True})
    minted = r5.AuthoritativeScientificExecution(
        capability,
        {
            "admitted": True,
            "affirmative_evidence_bytes": evidence_bytes,
            "affirmative_evidence_digest": protocol.digest_bytes(evidence_bytes),
            "failure_reason": None,
            "request_digest": protocol.digest_payload(REQUEST),
            "response_bytes": response_bytes,
            "response_digest": protocol.digest_bytes(response_bytes),
            "result_bytes": protocol.canonical_json_bytes(fabricated["result"]),
            "result_digest": fabricated["result_digest"],
        },
    )
    assert minted.admitted is True
    assert minted.authoritative_snapshot_proof()["bound_digests_reproduce"] is True

    record = only(verify(workspace, write_item(workspace, response=minted.response)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_PROJECTION_IS_NOT_BYTE_IDENTICAL"


# ---------------------------------------------------------------------------
# Proof obligations — rejection
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("field", sorted(contract.IN_PROJECTION_AUTHORITY_FIELDS))
def test_altering_any_in_projection_response_field_is_rejected(
    field: str, workspace: Path
) -> None:
    """Mutation probe over every projected field, one test each."""

    altered = _replaced(RESPONSE, **{field: _mutate(RESPONSE[field])})
    assert altered[field] != RESPONSE[field]
    record = only(verify(workspace, write_item(workspace, response=altered)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] in {
        "REJECTED_PROJECTION_IS_NOT_BYTE_IDENTICAL",
        "REJECTED_RECORDED_RESPONSE_AUTHORITY_MISMATCH",
        "REJECTED_RECORDED_RESPONSE_DOES_NOT_BIND_THE_RECORDED_REQUEST",
        "REJECTED_RECORDED_RESPONSE_IS_NOT_A_SUCCESS",
        "REJECTED_RECORDED_RESPONSE_RESULT_DIGEST_MISMATCH",
        "REJECTED_RECORDED_RESPONSE_SCHEMA_INVALID",
    }, record


def _mutate(value):
    if isinstance(value, bool):
        return not value
    if isinstance(value, int):
        return value + 1
    if isinstance(value, str):
        return value + "_DRIFT"
    if value is None:
        return "DRIFT"
    if isinstance(value, dict):
        return {**value, "__drift__": True}
    if isinstance(value, list):
        return [*value, "__drift__"]
    raise AssertionError(f"unmutatable value {value!r}")


@pytest.mark.parametrize("field", sorted(protocol.AUTHORITY_BOUND_REQUEST_FIELDS))
def test_altering_any_authority_bound_request_field_is_rejected(
    field: str, workspace: Path
) -> None:
    altered = _replaced(REQUEST, **{field: _mutate(REQUEST[field])})
    record = only(verify(workspace, write_item(workspace, request=altered)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] in {
        "REJECTED_RECORDED_REQUEST_AUTHORITY_MISMATCH",
        "REJECTED_RECORDED_REQUEST_SCHEMA_INVALID",
    }, record


def test_an_unsigned_evidence_record_is_rejected(workspace: Path) -> None:
    evidence = write_item(workspace, envelopes=[])
    record = only(verify(workspace, evidence))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_EVIDENCE_RECORD_HAS_NO_VERIFIED_ENVELOPE"


def test_an_altered_envelope_payload_is_rejected(workspace: Path) -> None:
    altered = json.loads(json.dumps(ENVELOPES))
    altered[0]["signed_payload"]["venue_id"] = "FORGED_VENUE"
    record = only(verify(workspace, write_item(workspace, envelopes=altered)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED"


def test_an_envelope_re_signed_by_another_key_is_rejected(workspace: Path) -> None:
    resigned = [SECOND_SIGNER.sign_payload(r) for r in base.SESSION_RECORDS]
    record = only(verify(workspace, write_item(workspace, envelopes=resigned)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED"


def test_an_envelope_naming_a_record_the_request_never_uses_is_rejected(
    workspace: Path,
) -> None:
    extra = [*ENVELOPES, SIGNER.sign_payload({"unrelated": True})]
    record = only(verify(workspace, write_item(workspace, envelopes=extra)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == (
        "REJECTED_ENVELOPE_PAYLOAD_IS_NOT_A_RECORDED_EVIDENCE_RECORD"
    )


def test_production_mode_refuses_a_test_key_envelope(workspace: Path) -> None:
    evidence = write_item(workspace, trust_root=None)
    record = only(verify(workspace, evidence, mode=contract.PRODUCTION_MODE))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_TEST_KEY_ENVELOPE_IN_PRODUCTION_MODE"
    assert record["verifier_mode"] == contract.PRODUCTION_MODE


def test_production_mode_refuses_an_envelope_wearing_the_production_key_id(
    workspace: Path,
) -> None:
    """A key-id string is not a key: the signature must verify under the root."""

    disguised = json.loads(json.dumps(ENVELOPES))
    for envelope in disguised:
        envelope["signing_key_id"] = trusted.PRODUCTION_KEY_ID
        envelope.pop("envelope_sha256")
        envelope["envelope_sha256"] = trusted.sha256_json(envelope)
    record = only(
        verify(
            workspace,
            write_item(workspace, envelopes=disguised, trust_root=None),
            mode=contract.PRODUCTION_MODE,
        )
    )
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED"


def test_production_mode_refuses_a_file_supplied_trust_root(workspace: Path) -> None:
    evidence = write_item(workspace, trust_root=TRUST_ROOT)
    record = only(verify(workspace, evidence, mode=contract.PRODUCTION_MODE))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_EVIDENCE_ITEM_LAYOUT_INVALID"


def test_test_mode_requires_an_explicit_test_trust_root(workspace: Path) -> None:
    evidence = write_item(workspace, trust_root=None)
    record = only(verify(workspace, evidence))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_INPUT_ENVELOPE_VERIFICATION_FAILED"


def test_a_recorded_bootstrap_manifest_drift_is_rejected(workspace: Path) -> None:
    drifted = json.loads(json.dumps(REQUEST))
    drifted["worker_bootstrap_manifest"][0]["sha256"] = base.ZERO_HASH
    drifted["worker_bootstrap_manifest_digest"] = protocol.bootstrap_manifest_digest(
        protocol.bootstrap_source_entries(drifted["worker_bootstrap_manifest"])
    )
    record = only(verify(workspace, write_item(workspace, request=drifted)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] in {
        "REJECTED_RECORDED_REQUEST_AUTHORITY_MISMATCH",
        "REJECTED_RECORDED_REQUEST_SCHEMA_INVALID",
    }, record


def test_on_disk_bootstrap_source_drift_is_rejected(workspace: Path) -> None:
    """Drifted bootstrap source on disk is refused against the frozen manifest."""

    tree = _pad5_tree(workspace / "tree")
    target = tree / base.ENTRYPOINT
    drifted = target.read_text("utf-8") + "\n# bootstrap drift\n"
    target.unlink()
    target.write_text(drifted, "utf-8")

    tree_launch = r5.worker_launch(project_root=tree)
    tree_request = r5.build_scientific_request(
        CONTEXT,
        launch=tree_launch,
        operation="common_etf_session_status",
        operation_inputs={"trade_date": base.SESSION_DAY.isoformat()},
        evidence_records=base.SESSION_RECORDS,
        decision_time=base.DECISION_TIME.isoformat(),
    )
    evidence = write_item(workspace, request=tree_request)
    record = only(
        verify(
            workspace,
            evidence,
            project_root=tree,
            sys_path=list(tree_launch.sys_path),
        )
    )
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_WORKER_BOOTSTRAP_SOURCE_DRIFT"


def test_bootstrap_binding_precedes_process_creation_in_the_verifier_source() -> None:
    """The refusal is structurally before the spawn, not merely observed to be."""

    source = (ROOT / pad5.VERIFIER_RELATIVE_PATH).read_text("utf-8")
    tree = ast.parse(source)
    function = next(
        node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name == "verify_evidence_item"
    )
    bootstrap_line = min(
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Attribute) and node.attr == "verify_bootstrap_source_set"
    )
    spawn_line = min(
        node.lineno
        for node in ast.walk(function)
        if isinstance(node, ast.Attribute) and node.attr == "spawn_isolated_process"
    )
    assert bootstrap_line < spawn_line


def test_an_interpreter_identity_mismatch_is_rejected(workspace: Path) -> None:
    drifted = _replaced(
        REQUEST, interpreter_identity={**REQUEST["interpreter_identity"], "version_micro": 99}
    )
    record = only(verify(workspace, write_item(workspace, request=drifted)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] in {
        "REJECTED_RECORDED_REQUEST_AUTHORITY_MISMATCH",
        "REJECTED_RECORDED_REQUEST_SCHEMA_INVALID",
    }, record


def test_third_party_installed_content_drift_is_rejected(workspace: Path) -> None:
    """Preserved Repair D: the observed content digest is inside the projection.

    The drift is injected on the *recorded* side rather than by mutating the
    shared installed environment, because mutating the exclusive proof venv
    would corrupt every other suite. The mechanism proved is the one that
    matters: a response whose observed installed-content digest is not the one
    re-derivation produces cannot be accepted.
    """

    drifted = _replaced(
        RESPONSE, third_party_observed_content_manifest_digest=base.DEADBEEF_HASH
    )
    record = only(verify(workspace, write_item(workspace, response=drifted)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_PROJECTION_IS_NOT_BYTE_IDENTICAL"


def test_a_third_party_authority_digest_drift_is_rejected(workspace: Path) -> None:
    drifted = _replaced(REQUEST, third_party_authority_digest=base.DEADBEEF_HASH)
    record = only(verify(workspace, write_item(workspace, request=drifted)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] in {
        "REJECTED_RECORDED_REQUEST_AUTHORITY_MISMATCH",
        "REJECTED_RECORDED_REQUEST_SCHEMA_INVALID",
    }, record


def test_the_frozen_trusted_context_comparison_is_load_bearing(
    workspace: Path,
) -> None:
    """A drifted authority value the worker protocol itself accepts.

    Eleven of the twelve authority-bound request fields are also refused by the
    frozen worker protocol, so a test that only exercised those would not show
    whether the frozen-context comparison does anything at all.
    ``calendar_authority_version`` is schema-valid under the protocol, so the
    only thing that can refuse it is the comparison against the frozen trusted
    context — and that is the check that makes "the verifier never adopts a
    value from the request" true rather than merely stated.
    """

    drifted = _replaced(REQUEST, calendar_authority_version="FORGED_AUTHORITY_V9")
    protocol.validate_request(drifted)  # the protocol itself is content with it
    record = only(verify(workspace, write_item(workspace, request=drifted)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_RECORDED_REQUEST_AUTHORITY_MISMATCH"


def test_a_faithfully_recorded_refusal_is_not_calendar_evidence(
    workspace: Path,
) -> None:
    """A refusal that re-derives as the same refusal is still not evidence."""

    refusal = _replaced(
        RESPONSE,
        status=protocol.REFUSED,
        failure_reason="WORKER_REFUSED_FOR_THE_PURPOSES_OF_THIS_REGRESSION",
    )
    record = only(verify(workspace, write_item(workspace, response=refusal)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_RECORDED_RESPONSE_IS_NOT_A_SUCCESS"
    assert contract.admits(record) is False


def test_a_response_filed_with_another_request_is_rejected(
    workspace: Path,
) -> None:
    mismatched = _replaced(RESPONSE, request_digest=base.DEADBEEF_HASH)
    record = only(verify(workspace, write_item(workspace, response=mismatched)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == (
        "REJECTED_RECORDED_RESPONSE_DOES_NOT_BIND_THE_RECORDED_REQUEST"
    )


def test_a_response_whose_result_digest_does_not_describe_its_result_is_rejected(
    workspace: Path,
) -> None:
    mismatched = _replaced(RESPONSE, result_digest=base.DEADBEEF_HASH)
    record = only(verify(workspace, write_item(workspace, response=mismatched)))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_RECORDED_RESPONSE_RESULT_DIGEST_MISMATCH"


def test_a_non_canonical_recorded_request_is_rejected(workspace: Path) -> None:
    evidence = write_item(workspace)
    target = evidence / "item0001" / contract.REQUEST_FILENAME
    target.write_bytes(b" " + target.read_bytes())
    record = only(verify(workspace, evidence))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_RECORDED_REQUEST_IS_NOT_CANONICAL"


def test_an_incomplete_evidence_item_is_rejected(workspace: Path) -> None:
    evidence = write_item(workspace)
    (evidence / "item0001" / contract.RESPONSE_FILENAME).unlink()
    record = only(verify(workspace, evidence))
    assert record["verdict"] == contract.REJECTED
    assert record["reason_code"] == "REJECTED_EVIDENCE_ITEM_LAYOUT_INVALID"


def test_rejections_are_recorded_never_dropped(workspace: Path) -> None:
    evidence = workspace / "evidence"
    pad5.write_evidence_item(
        evidence / "good",
        scientific_request=REQUEST,
        response=RESPONSE,
        input_envelopes=ENVELOPES,
        test_trust_root=TRUST_ROOT,
    )
    pad5.write_evidence_item(
        evidence / "bad",
        scientific_request=REQUEST,
        response=_replaced(RESPONSE, operation="FORGED"),
        input_envelopes=ENVELOPES,
        test_trust_root=TRUST_ROOT,
    )
    records = verify(workspace, evidence)
    assert len(records) == 2
    verdicts = {record["evidence_item_id"]: record["verdict"] for record in records}
    assert verdicts == {"good": contract.ACCEPTED, "bad": contract.REJECTED}


# ---------------------------------------------------------------------------
# Non-authority, consumer admission and the launch census
# ---------------------------------------------------------------------------


def test_no_producer_side_type_carries_an_authority_marker() -> None:
    audit = pad5.audit_no_in_process_authority()
    assert audit["closed"] is True and audit["findings"] == []
    assert audit["emitted_retired_markers"] == []
    assert audit["producer_output_authority"] == "NON_AUTHORITATIVE_CANDIDATE_EVIDENCE"
    assert audit["verifier_self_attestation_is_authority"] is False
    assert audit["producer_self_attestation_is_authority"] is False


def test_the_producer_never_writes_the_r5_affirmative_evidence(
    workspace: Path,
) -> None:
    evidence = write_item(workspace)
    blob = b"".join(
        target.read_bytes() for target in sorted((evidence / "item0001").iterdir())
    )
    for marker in contract.RETIRED_AUTHORITY_MARKERS:
        assert marker.encode("ascii") not in blob
    item = json.loads((evidence / "item0001" / contract.ITEM_FILENAME).read_bytes())
    assert item["authority"] == contract.PRODUCER_OUTPUT_AUTHORITY


def test_only_an_accepting_production_record_admits(workspace: Path) -> None:
    record = only(verify(workspace, write_item(workspace)))
    assert record["verdict"] == contract.ACCEPTED
    assert contract.admits(record) is False  # non-authoritative test mode
    promoted = {**record, "verifier_mode": contract.PRODUCTION_MODE}
    assert contract.admits(promoted) is False  # the bound digest no longer holds
    rejection = {**record, "verdict": contract.REJECTED}
    assert contract.admits(rejection) is False


def test_the_consumer_admission_rule_binds_every_owner() -> None:
    child = pad5.consumer_admission_rule()
    assert set(child["bound_consumers"]) == {
        "POSTP1-001V2A-I2",
        "POSTP1-001V2R1",
        "POSTP1-003R3_SUFFICIENCY_GOVERNANCE",
        "PROSPECTIVE_COLLECTION",
        "STAGE_B_EVALUATION",
    }
    assert child["consumers_wired_by_this_ticket"] == 0
    assert child["stage_b_must_verify_every_observation_before_evaluating"] is True


def test_pad5_owns_exactly_one_justified_launch_site() -> None:
    census = pad5.audit_direct_worker_launch_census()
    assert census["closed"] is True and census["findings"] == []
    assert census["pad5_owned_launch_site_count"] == 1
    site = census["pad5_owned_launch_sites"][0]
    assert site["path"] == pad5.CONTRACT_RELATIVE_PATH
    assert site["scope"] == ["spawn_isolated_process"]
    assert site["primitive"] == "subprocess.run"
    assert census["certified_worker_source_launch_sites"] == 0


def test_the_certified_worker_universe_creates_no_process() -> None:
    census = pad5.audit_direct_worker_launch_census()
    certified = [
        site
        for site in census["sites"]
        if site["classification"] == "CERTIFIED_WORKER_SOURCE_UNIVERSE"
    ]
    assert certified == []


# ---------------------------------------------------------------------------
# Mutation-sensitivity probes — each must move its child and the parent
# ---------------------------------------------------------------------------


def _moved(builder, name: str, **overrides) -> None:
    """A mutated child must change its own hash and the parent's."""

    original = builder()
    mutated = pad5._definition(
        {
            key: value
            for key, value in {**original, **overrides}.items()
            if key != "definition_sha256"
        }
    )
    assert mutated["definition_sha256"] != original["definition_sha256"], name
    registry = tuple(
        (filename, (lambda m=mutated: m) if filename == f"{name}.json" else b)
        for filename, b in pad5._CHILD_ARTIFACTS
    )
    moved = pad5.replay_verified_evidence_v1_definition(registry)
    assert moved["definition_sha256"] != CANDIDATE_HASH, name


def test_dropping_re_execution_for_digest_only_moves_the_parent() -> None:
    _moved(
        pad5.comparison_projection_definition,
        "comparison_projection_definition",
        digest_only_acceptance_permitted=True,
    )
    _moved(
        pad5.replay_verified_admission_rule,
        "replay_verified_admission_rule",
        re_execution_is_required_for_every_accepted_item=False,
    )


def test_changing_the_projection_field_list_moves_the_parent() -> None:
    audit = pad5.audit_comparison_projection()
    _moved(
        pad5.comparison_projection_definition,
        "comparison_projection_definition",
        projection_audit={
            **audit,
            "in_projection_authority_fields": [
                *audit["in_projection_authority_fields"],
                "invented_field",
            ],
        },
    )
    _moved(
        pad5.comparison_projection_definition,
        "comparison_projection_definition",
        projection_audit={
            **audit,
            "in_projection_authority_fields": audit["in_projection_authority_fields"][
                :-1
            ],
        },
    )


def test_admitting_in_the_producers_process_moves_the_parent() -> None:
    _moved(
        pad5.non_authoritative_producer_rule,
        "non_authoritative_producer_rule",
        producer_output_is_authority=True,
    )
    _moved(
        pad5.trusted_process_and_isolation_boundary,
        "trusted_process_and_isolation_boundary",
        authority_bearing_production_operations=1,
    )


def test_producer_self_attestation_moves_the_parent() -> None:
    _moved(
        pad5.non_authoritative_producer_rule,
        "non_authoritative_producer_rule",
        producer_self_attestation_is_authority=True,
    )
    _moved(
        pad5.verifier_source_manifest,
        "verifier_source_manifest",
        self_attestation_is_authority=True,
    )


def test_defining_the_projection_by_exclusion_moves_the_parent() -> None:
    audit = pad5.audit_comparison_projection()
    _moved(
        pad5.comparison_projection_definition,
        "comparison_projection_definition",
        projection_audit={
            **audit,
            "is_defined_by_exclusion": True,
            "is_a_closed_inclusion_list": False,
        },
    )


def test_adding_domain_exclusion_text_moves_the_parent() -> None:
    _moved(
        pad5.trusted_process_and_isolation_boundary,
        "trusted_process_and_isolation_boundary",
        domain_text_excluding_introspection_routes=True,
    )
    _moved(
        pad5.replay_verified_evidence_boundary,
        "replay_verified_evidence_boundary",
        excluded_introspection_routes=["GC", "CLASS_MUTATION"],
    )


# ---------------------------------------------------------------------------
# Safety
# ---------------------------------------------------------------------------


def test_safety_position_is_unchanged() -> None:
    safety = pad5.science_lineage_and_safety()["safety"]
    assert safety == {
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
    }


def test_no_frozen_namespace_or_certified_module_was_edited() -> None:
    """The preserved authorities still reproduce from their own controllers."""

    assert r5.restore_artifacts(R5_ARTIFACT_DIR)["definition_sha256"] == (
        pad5.FAILED_PAD4_R5_SHA256
    )
    assert protocol.bootstrap_manifest_digest(r5.frozen_bootstrap_source_manifest()) == (
        "1811e04dac7a033de2c8e6620bf7d5aa227b94eebdf419657ecccf4d3fead411"
    )
    assert protocol.manifest_digest(r5.frozen_candidate_source_manifest()) == (
        "7ffbf15792d33e0cd387eb995d8d733c1fa1b98b2859153957c670f796a44e8e"
    )
