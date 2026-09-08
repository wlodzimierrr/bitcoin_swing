"""V5 three-stage ownership and terminal-integration-corpus tests."""

from __future__ import annotations

import hashlib
import json
from decimal import Context, ROUND_CEILING, ROUND_FLOOR, localcontext
from pathlib import Path

import pytest

from btc_predictor.research.reference_composite_v3_sealed_executor import (
    VerifiedRawCollection,
    VerifiedRawFile,
)
from btc_predictor.research.reference_composite_v3_validator import (
    VERDICT_FAIL,
    VERDICT_INSUFFICIENT,
    VERDICT_PASS,
)
from btc_predictor.research import reference_composite_v5
from btc_predictor.research.reference_composite_v5 import (
    CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256,
    CORPUS_ASSESSMENT_FILENAME,
    DETERMINISTIC_RERUN_OWNER,
    DEVELOPMENT_EVENT_STOP_METRICS,
    FINAL_CLASSIFICATION,
    FROZEN_V3_DEFINITION_SHA256,
    INTEGRATION_CORPUS_REQUIRED_FIELDS,
    LIVE_SHADOW_METRIC,
    LIVE_SHADOW_THRESHOLD,
    MECHANICAL_STAGE_A_METRICS,
    OUTPUT_NAMESPACE,
    PARENT_PROTOCOL_DEFINITION_SHA256,
    PARENT_VALIDATOR_DEFINITION_SHA256,
    PHASE1_CONSEQUENCE_METRICS,
    PROVENANCE_COMPLETE_OWNER,
    SEMANTIC_DIFF_FILENAME,
    STAGE_A,
    STAGE_B,
    STAGE_B_METRICS,
    STAGE_C,
    V5CertificationError,
    assert_stage_a_hard_gate_owner_completeness,
    assert_stage_b_issuance_ready,
    inherited_gate_stage_table,
    integration_corpus_assessment,
    measure_deterministic_rerun_hash_match,
    measure_provenance_complete_rate,
    restore_v5_artifacts,
    stage_a_measurement_inventory,
    synthetic_reachability,
    v4_to_v5_semantic_diff,
    v5_protocol_definition,
    write_v5_artifacts,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FROZEN_V4_HASH = "670ff12dd3d63615e9ddb3be05d65505bab16b50e50c1fd9ad077a4923a3f501"
V4_VALIDATOR_HASH = "8cf091fb8c0374f876dc54237d0226cea3f11a3d7554f6abae5ba5c1df498c28"
FROZEN_V3_HASH = "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
CERTIFIED_V1_HASH = "8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7"


def _verified_collection() -> VerifiedRawCollection:
    raw = b"already verified synthetic raw bytes"
    row = VerifiedRawFile(
        provider_id="synthetic",
        relative_path="raw_collection/synthetic.jsonl.gz",
        sha256=hashlib.sha256(raw).hexdigest(),
        raw_bytes=raw,
        bars=(),
        device=1,
        inode=1,
    )
    return VerifiedRawCollection(
        manifest={"manifest_sha256": "a" * 64, "synthetic": True}, files=(row,)
    )


def _complete_provenance_records(inventory: list[dict]) -> list[dict]:
    records = []
    for row in inventory:
        fraction = row["numerator_denominator_required"]
        records.append(
            {
                "authoritative_owner": row["authoritative_owner"],
                "configuration_identity": "b" * 64,
                "denominator": 1 if fraction else None,
                "input_identity": "a" * 64,
                "manifest_execution_identity": "c" * 64,
                "measurement_id": row["measurement_id"],
                "numerator": 1 if fraction else None,
                "owner_version_identity": row["owner_version_identity"],
                "pit_evaluation_window": {
                    "available_at_rule": "available_at <= decision_time",
                    "end": "2025-01-02T00:00:00+00:00",
                    "start": "2025-01-01T00:00:00+00:00",
                },
                "semantic_definition_hash": row["semantic_definition_hash"],
                "undefined_reason": None,
            }
        )
    return records


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_v5_binds_immutable_v4_v3_and_certified_v1_lineage() -> None:
    assert PARENT_PROTOCOL_DEFINITION_SHA256 == FROZEN_V4_HASH
    assert PARENT_VALIDATOR_DEFINITION_SHA256 == V4_VALIDATOR_HASH
    assert FROZEN_V3_DEFINITION_SHA256 == FROZEN_V3_HASH
    assert CERTIFIED_V1_VALIDATOR_DEFINITION_SHA256 == CERTIFIED_V1_HASH
    protocol = v5_protocol_definition(REPOSITORY_ROOT)
    assert protocol["lineage"] == {
        "certified_v1_validator_definition_sha256": CERTIFIED_V1_HASH,
        "frozen_v3_definition_sha256": FROZEN_V3_HASH,
        "parent_v4_definition_sha256": FROZEN_V4_HASH,
        "parent_v4_validator_definition_sha256": V4_VALIDATOR_HASH,
    }


def test_three_stage_assignment_is_driven_by_evidence_dependency() -> None:
    rows = inherited_gate_stage_table(REPOSITORY_ROOT)
    by_stage = {
        stage: [row for row in rows if row["v5_stage"] == stage]
        for stage in (STAGE_A, STAGE_B, STAGE_C)
    }
    assert len(by_stage[STAGE_A]) == 24
    assert sum(row["hard"] for row in by_stage[STAGE_A]) == 20
    assert tuple(row["metric"] for row in by_stage[STAGE_B]) == tuple(
        sorted(STAGE_B_METRICS)
    )
    assert all(row["hard"] for row in by_stage[STAGE_B])
    assert [row["metric"] for row in by_stage[STAGE_C]] == [LIVE_SHADOW_METRIC]
    assert by_stage[STAGE_C][0]["threshold"] == LIVE_SHADOW_THRESHOLD == 90
    assert by_stage[STAGE_C][0]["direction"] == "minimum"


def test_the_three_stop_metrics_do_not_reuse_the_development_event_list() -> None:
    rows = {row["metric"]: row for row in inherited_gate_stage_table(REPOSITORY_ROOT)}
    for metric in DEVELOPMENT_EVENT_STOP_METRICS:
        assert rows[metric]["v5_stage"] == STAGE_B
        assert "development-specific" in rows[metric]["evidence_dependency_reason"]
        assert rows[metric]["stage_b_frozen_corpus_count"] == 0


def test_the_five_phase1_consequence_gates_are_stage_b_without_fabrication() -> None:
    rows = {row["metric"]: row for row in inherited_gate_stage_table(REPOSITORY_ROOT)}
    for metric in PHASE1_CONSEQUENCE_METRICS:
        assert rows[metric]["v5_stage"] == STAGE_B
        assert "complete non-price" in rows[metric]["evidence_dependency_reason"]
        assert rows[metric]["authoritative_owner_count"] == 0


def test_v4_to_v5_diff_preserves_every_threshold_direction_role_and_definition() -> None:
    diff = v4_to_v5_semantic_diff(REPOSITORY_ROOT)
    assert diff["gate_count"] == 33
    assert diff["threshold_change_count"] == 0
    assert diff["direction_change_count"] == 0
    assert diff["hard_soft_change_count"] == 0
    assert diff["evidence_stage_reassignment_count"] == 8
    assert all(
        set(row)
        == {
            "definition",
            "direction",
            "hard_soft_role",
            "metric",
            "new_stage",
            "old_stage",
            "old_stage_v5_equivalent",
            "threshold",
        }
        for row in diff["gate_semantic_diff"]
    )


def test_semantic_diff_counts_are_measured_against_v4_not_asserted(
    monkeypatch,
) -> None:
    baseline = inherited_gate_stage_table(REPOSITORY_ROOT)

    for field, moved in (
        ("threshold", "0.99"),
        ("direction", "minimum"),
        ("role", "SOFT"),
    ):
        moved_table = [dict(row) for row in baseline]
        moved_table[0][field] = moved
        monkeypatch.setattr(
            reference_composite_v5,
            "inherited_gate_stage_table",
            lambda _root, _table=moved_table: [dict(row) for row in _table],
        )
        with pytest.raises(V5CertificationError, match="evidence-stage ownership"):
            v4_to_v5_semantic_diff(REPOSITORY_ROOT)


def test_every_stage_a_hard_gate_has_one_real_executable_owner() -> None:
    assert_stage_a_hard_gate_owner_completeness(REPOSITORY_ROOT)
    rows = inherited_gate_stage_table(REPOSITORY_ROOT)
    hard = [row for row in rows if row["hard"] and row["v5_stage"] == STAGE_A]
    assert len(hard) == 20
    assert all(
        row["authoritative_owner_count"] == 1
        and row["authoritative_owner_executable"] is True
        for row in hard
    )
    mechanical = {row["metric"]: row for row in hard if row["metric"] in MECHANICAL_STAGE_A_METRICS}
    assert mechanical["deterministic_rerun_hash_match"][
        "authoritative_evidence_owner"
    ] == [DETERMINISTIC_RERUN_OWNER]
    assert mechanical["provenance_complete_rate"]["authoritative_evidence_owner"] == [
        PROVENANCE_COMPLETE_OWNER
    ]


def test_deterministic_rerun_is_an_actual_second_in_memory_transformation() -> None:
    collection = _verified_collection()
    calls = []

    def transform(received: VerifiedRawCollection) -> dict:
        assert received is collection
        calls.append(received)
        return {"evidence": "same"}

    result = measure_deterministic_rerun_hash_match(
        collection,
        transform=transform,
        frozen_configuration={"version": "frozen"},
        semantic_dependency_identities={"owner": "f" * 64},
    )
    assert calls == [collection, collection]
    assert result["transformation_invocation_count"] == 2
    assert result["same_verified_collection_object"] is True
    assert result["digest_1"] == result["digest_2"]
    assert result["value"] is True


def test_deterministic_rerun_can_measure_a_real_mismatch() -> None:
    invocation = 0

    def transform(_: VerifiedRawCollection) -> dict:
        nonlocal invocation
        invocation += 1
        return {"invocation": invocation}

    result = measure_deterministic_rerun_hash_match(
        _verified_collection(),
        transform=transform,
        frozen_configuration={"version": "frozen"},
        semantic_dependency_identities={"owner": "f" * 64},
    )
    assert result["digest_1"] != result["digest_2"]
    assert result["value"] is False


def test_deterministic_rerun_refuses_input_mutation() -> None:
    collection = _verified_collection()

    def transform(_: VerifiedRawCollection) -> dict:
        collection.manifest["mutated"] = True
        return {"evidence": "invalid"}

    with pytest.raises(V5CertificationError, match="mutated its input"):
        measure_deterministic_rerun_hash_match(
            collection,
            transform=transform,
            frozen_configuration={"version": "frozen"},
            semantic_dependency_identities={"owner": "f" * 64},
        )


def test_provenance_complete_rate_is_derived_from_the_full_inventory() -> None:
    inventory = stage_a_measurement_inventory(REPOSITORY_ROOT)
    records = _complete_provenance_records(inventory)
    result = measure_provenance_complete_rate(
        records,
        required_inventory=inventory,
        expected_configuration_identity="b" * 64,
        expected_input_identity="a" * 64,
        expected_manifest_execution_identity="c" * 64,
    )
    assert len(inventory) == 49
    assert result["numerator"] == result["denominator"] == 49
    assert result["value"] == "1"
    assert all(row["complete"] for row in result["census"])


def test_provenance_census_detects_missing_duplicate_and_invalid_records() -> None:
    inventory = stage_a_measurement_inventory(REPOSITORY_ROOT)
    records = _complete_provenance_records(inventory)
    missing_id = records[-1]["measurement_id"]
    missing = measure_provenance_complete_rate(
        records[:-1],
        required_inventory=inventory,
        expected_configuration_identity="b" * 64,
        expected_input_identity="a" * 64,
        expected_manifest_execution_identity="c" * 64,
    )
    assert missing["numerator"] == 48
    assert missing["value"] != "1"
    assert next(
        row for row in missing["census"] if row["measurement_id"] == missing_id
    )["reasons"] == ["measurement_record_missing"]

    records[0]["semantic_definition_hash"] = "0" * 64
    records.append(dict(records[1]))
    invalid = measure_provenance_complete_rate(
        records,
        required_inventory=inventory,
        expected_configuration_identity="b" * 64,
        expected_input_identity="a" * 64,
        expected_manifest_execution_identity="c" * 64,
    )
    assert invalid["numerator"] == 47
    assert invalid["value"] != "1"


def test_provenance_accepts_a_reasoned_undefined_fraction_record() -> None:
    inventory = stage_a_measurement_inventory(REPOSITORY_ROOT)
    records = _complete_provenance_records(inventory)
    target = next(
        record
        for record in records
        if record["measurement_id"].startswith("diagnostic:")
    )
    target["numerator"] = None
    target["denominator"] = None
    target["undefined_reason"] = "zero admissible events"
    result = measure_provenance_complete_rate(
        records,
        required_inventory=inventory,
        expected_configuration_identity="b" * 64,
        expected_input_identity="a" * 64,
        expected_manifest_execution_identity="c" * 64,
    )
    assert result["value"] == "1"


def test_stage_a_and_stage_b_each_have_all_three_synthetic_outcomes() -> None:
    reachability = synthetic_reachability(REPOSITORY_ROOT)
    expected = {
        "fail": VERDICT_FAIL,
        "pass": VERDICT_PASS,
        "undefined_insufficient_evidence": VERDICT_INSUFFICIENT,
    }
    assert reachability[STAGE_A]["outcomes"] == expected
    assert reachability[STAGE_B]["outcomes"] == expected
    assert reachability[STAGE_A]["does_not_claim_real_evidence"] is True
    assert reachability[STAGE_B]["does_not_claim_real_evidence"] is True


def test_repository_has_no_complete_reproducible_stage_b_corpus() -> None:
    assessment = integration_corpus_assessment(REPOSITORY_ROOT)
    assert assessment["reproducible_integration_corpus_exists"] is False
    assert assessment["complete_corpus_candidates"] == []
    assert assessment["corpus_definition_sha256"] is None
    assert tuple(assessment["required_fields"]) == INTEGRATION_CORPUS_REQUIRED_FIELDS
    assert assessment["candidate_reference_state"] == (
        "MEDIAN_OHLC_V2_NOT_CONSTRUCTED_OR_EVALUATED"
    )
    assert assessment["final_classification"] == FINAL_CLASSIFICATION
    with pytest.raises(V5CertificationError, match=FINAL_CLASSIFICATION):
        assert_stage_b_issuance_ready(REPOSITORY_ROOT)


def test_terminal_protocol_issues_no_validator_builder_or_executor_hash() -> None:
    protocol = v5_protocol_definition(REPOSITORY_ROOT)
    assert protocol["final_classification"] == FINAL_CLASSIFICATION
    assert protocol["production_promotion_authorized"] is False
    assert protocol["issuance"] == {
        "complete_certification_pipeline_definition_sha256": None,
        "sealed_execution_authorized": False,
        "stage_a_builder_definition_sha256": None,
        "v5_executor_definition_sha256": None,
        "v5_validator_definition_sha256": None,
    }
    assert protocol["stage_a_readiness"][
        "every_hard_gate_has_exactly_one_executable_owner"
    ] is True
    assert protocol["stage_a_readiness"]["numerical_correctness_certified"] is False


def test_v5_artifacts_round_trip_and_tamper_refuses(tmp_path: Path) -> None:
    output = tmp_path / "v5"
    written = write_v5_artifacts(REPOSITORY_ROOT, output)
    assert restore_v5_artifacts(REPOSITORY_ROOT, output) == written
    assessment_path = output / CORPUS_ASSESSMENT_FILENAME
    assessment = json.loads(assessment_path.read_text())
    assessment["reproducible_integration_corpus_exists"] = True
    assessment_path.write_text(json.dumps(assessment, indent=2, sort_keys=True) + "\n")
    with pytest.raises(V5CertificationError, match=CORPUS_ASSESSMENT_FILENAME):
        restore_v5_artifacts(REPOSITORY_ROOT, output)


def test_v5_hash_and_mechanical_results_ignore_ambient_decimal_context() -> None:
    inventory = stage_a_measurement_inventory(REPOSITORY_ROOT)
    records = _complete_provenance_records(inventory)
    results = []
    for context in (
        Context(prec=6, rounding=ROUND_FLOOR),
        Context(prec=50, rounding=ROUND_CEILING),
    ):
        with localcontext(context):
            results.append(
                (
                    v5_protocol_definition(REPOSITORY_ROOT)["definition_sha256"],
                    measure_provenance_complete_rate(
                        records,
                        required_inventory=inventory,
                        expected_configuration_identity="b" * 64,
                        expected_input_identity="a" * 64,
                        expected_manifest_execution_identity="c" * 64,
                    )["value"],
                )
            )
    assert results[0] == results[1]


def test_v5_artifact_generation_does_not_mutate_v3_or_v4(tmp_path: Path) -> None:
    paths = (
        REPOSITORY_ROOT
        / "research_artifacts/btc019_v3_gate_architecture_convergence/reference_composite_v3_protocol.json",
        REPOSITORY_ROOT
        / "research_artifacts/btc019_v4_stage_correction/reference_composite_v4_protocol.json",
        REPOSITORY_ROOT
        / "research_artifacts/btc019_v4_validator/validator_definition.json",
    )
    before = tuple(_sha256(path) for path in paths)
    write_v5_artifacts(REPOSITORY_ROOT, tmp_path / OUTPUT_NAMESPACE)
    assert tuple(_sha256(path) for path in paths) == before


def test_v5_never_reads_a_real_sealed_sample_path(monkeypatch) -> None:
    reads = []
    original = Path.read_bytes

    def watched(path: Path, *args, **kwargs):
        reads.append(path.as_posix())
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", watched)
    v5_protocol_definition(REPOSITORY_ROOT)
    assert not any("2015-07-20_2019-11-30" in path for path in reads)


def test_persisted_v5_artifacts_reproduce_after_generation() -> None:
    output = REPOSITORY_ROOT / OUTPUT_NAMESPACE
    if not output.exists():
        pytest.skip("canonical V5 artifacts have not been generated yet")
    restored = restore_v5_artifacts(REPOSITORY_ROOT, output)
    assert restored["definition_sha256"] == v5_protocol_definition(REPOSITORY_ROOT)[
        "definition_sha256"
    ]
    assert (output / SEMANTIC_DIFF_FILENAME).is_file()
