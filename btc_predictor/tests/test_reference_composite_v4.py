"""Stage-ownership and fail-closed readiness tests for BTC_REFERENCE_COMPOSITE_V4."""

from __future__ import annotations

import hashlib
import json
from decimal import Context, ROUND_CEILING, ROUND_FLOOR, localcontext
from pathlib import Path

import pytest

from btc_predictor.research.reference_composite_v3_convergence import (
    v3_protocol_definition,
)
from btc_predictor.research.reference_composite_v4 import (
    LIVE_SHADOW_METRIC,
    NO_EXECUTABLE_OWNER,
    OUTPUT_NAMESPACE,
    PARENT_PROTOCOL_DEFINITION_SHA256,
    SEMANTIC_DIFF_FILENAME,
    STAGE_HISTORICAL,
    STAGE_PROMOTION,
    V4StageCorrectionError,
    assert_stage_a_hard_gate_owner_completeness,
    inherited_gate_ownership_table,
    restore_v4_artifacts,
    semantic_diff,
    unresolved_stage_a_hard_gate_owners,
    v4_protocol_definition,
    write_v4_artifacts,
)
from btc_predictor.research.reference_composite_v4_validator import (
    PARENT_VALIDATOR_DEFINITION_SHA256,
    STAGE_A_PASS_CONSEQUENCE,
    V4ValidatorError,
    evaluate_stage_b_promotion,
    stage_a_inherited_gate_definitions,
    validate_stage_a_candidate,
    validator_definition,
    verify_validator_artifacts,
    write_validator_artifacts,
)
from btc_predictor.research.reference_composite_v3_validator import (
    VERDICT_FAIL,
    VERDICT_INSUFFICIENT,
    VERDICT_PASS,
    inherited_gate_definitions,
)
from btc_predictor.tests.test_reference_composite_v3_validator import (
    _bundle,
    _inherited_measurements,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
FROZEN_V3_HASH = "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
CERTIFIED_V1_HASH = "8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7"
FROZEN_V4_HASH = "670ff12dd3d63615e9ddb3be05d65505bab16b50e50c1fd9ad077a4923a3f501"
V4_VALIDATOR_HASH = "8cf091fb8c0374f876dc54237d0226cea3f11a3d7554f6abae5ba5c1df498c28"

EXPECTED_UNRESOLVED_STAGE_A_OWNERS = (
    "cross_market_confirmed_stop_preservation_rate",
    "deterministic_rerun_hash_match",
    "gap_through_stop_consensus_agreement_rate",
    "isolated_venue_stop_suppression_rate",
    "provenance_complete_rate",
    "regime_classification_disagreement_rate",
    "risk_size_p95_relative_difference",
    "setup_classification_disagreement_rate",
    "trade_action_disagreement_rate",
    "trade_eligibility_disagreement_rate",
)


@pytest.fixture(scope="module")
def v3() -> dict:
    return v3_protocol_definition(REPOSITORY_ROOT)


@pytest.fixture(scope="module")
def v4() -> dict:
    return v4_protocol_definition(REPOSITORY_ROOT)


def _stage_a_bundle(v3: dict, **measurement_overrides) -> dict:
    measurements = _inherited_measurements(v3, **measurement_overrides)
    measurements.pop(LIVE_SHADOW_METRIC)
    return _bundle(v3, inherited_gate_measurements=measurements)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_the_33_gate_ownership_table_is_complete_and_deterministic() -> None:
    left = inherited_gate_ownership_table(REPOSITORY_ROOT)
    right = inherited_gate_ownership_table(REPOSITORY_ROOT)
    assert left == right
    assert len(left) == 33
    assert len({row["metric"] for row in left}) == 33
    required = {
        "authoritative_evidence_owner",
        "authoritative_owner_count",
        "authoritative_owner_status",
        "blocking_reason",
        "metric",
        "hard",
        "threshold",
        "direction",
        "v3_role",
        "required_evidence",
        "existing_repository_owner",
        "historical_sealed_data_derivable",
        "pre_existing_nonsealed_evidence",
        "prospective_only",
        "v4_stage",
    }
    assert all(required <= set(row) for row in left)


def test_live_shadow_is_the_only_prospective_and_promotion_stage_gate() -> None:
    rows = inherited_gate_ownership_table(REPOSITORY_ROOT)
    assert [row["metric"] for row in rows if row["prospective_only"]] == [
        LIVE_SHADOW_METRIC
    ]
    assert [row["metric"] for row in rows if row["v4_stage"] == STAGE_PROMOTION] == [
        LIVE_SHADOW_METRIC
    ]
    live = next(row for row in rows if row["metric"] == LIVE_SHADOW_METRIC)
    assert live["hard"] is True
    assert live["threshold"] == 90
    assert live["direction"] == "minimum"
    assert live["historical_sealed_data_derivable"] is False


def test_all_other_gates_remain_in_historical_validation() -> None:
    rows = inherited_gate_ownership_table(REPOSITORY_ROOT)
    assert sum(row["v4_stage"] == STAGE_HISTORICAL for row in rows) == 32
    assert sum(row["hard"] and row["v4_stage"] == STAGE_HISTORICAL for row in rows) == 28
    assert sum(not row["hard"] and row["v4_stage"] == STAGE_HISTORICAL for row in rows) == 4


def test_every_non_stage_attribute_is_identical_to_v3(v3: dict, v4: dict) -> None:
    left = {
        row["metric"]: {
            "direction": row["direction"],
            "hard": row["hard"],
            "threshold": row["threshold"],
        }
        for row in inherited_gate_definitions(v3)
    }
    right = {
        row["metric"]: {
            "direction": row["direction"],
            "hard": row["hard"],
            "threshold": row["threshold"],
        }
        for row in v4["inherited_approval_gates"]
    }
    assert left == right


def test_the_semantic_diff_contains_one_relocation_and_no_other_change() -> None:
    diff = semantic_diff(REPOSITORY_ROOT)
    assert diff["threshold_changes"] == []
    assert diff["other_gate_definition_changes"] == []
    assert diff["stage_relocations"] == [
        {
            "direction": "minimum",
            "from": STAGE_HISTORICAL,
            "hard": True,
            "metric": LIVE_SHADOW_METRIC,
            "threshold": 90,
            "to": STAGE_PROMOTION,
        }
    ]


def test_v4_binds_the_exact_immutable_parent_and_certified_validator(v4: dict) -> None:
    assert PARENT_PROTOCOL_DEFINITION_SHA256 == FROZEN_V3_HASH
    assert v4["parent_protocol_hash"] == FROZEN_V3_HASH
    assert PARENT_VALIDATOR_DEFINITION_SHA256 == CERTIFIED_V1_HASH
    assert v4["definition_sha256"] == FROZEN_V4_HASH
    assert validator_definition(REPOSITORY_ROOT)["validator_definition_sha256"] == (
        V4_VALIDATOR_HASH
    )


def test_repository_v4_and_validator_artifacts_reproduce() -> None:
    protocol = restore_v4_artifacts(
        REPOSITORY_ROOT, REPOSITORY_ROOT / OUTPUT_NAMESPACE
    )
    validator = verify_validator_artifacts(
        REPOSITORY_ROOT,
        REPOSITORY_ROOT / "research_artifacts/btc019_v4_validator",
    )
    assert protocol["definition_sha256"] == FROZEN_V4_HASH
    assert validator["validator_definition_sha256"] == V4_VALIDATOR_HASH


def test_stage_a_validator_excludes_live_shadow_and_preserves_all_other_roles(v4: dict) -> None:
    gates = stage_a_inherited_gate_definitions(v4)
    assert len(gates) == 32
    assert sum(row["hard"] for row in gates) == 28
    assert sum(not row["hard"] for row in gates) == 4
    assert LIVE_SHADOW_METRIC not in {row["metric"] for row in gates}


def test_stage_a_pass_is_reachable_without_live_shadow(v3: dict) -> None:
    record = validate_stage_a_candidate(
        _stage_a_bundle(v3), repository_root=REPOSITORY_ROOT
    ).as_record()
    assert record["verdict"] == VERDICT_PASS
    assert record["consequence"] == STAGE_A_PASS_CONSEQUENCE
    assert record["live_shadow_days_consulted"] is False


def test_stage_a_fail_is_reachable(v3: dict) -> None:
    record = validate_stage_a_candidate(
        _stage_a_bundle(v3, reference_usable_rate="0"),
        repository_root=REPOSITORY_ROOT,
    ).as_record()
    assert record["verdict"] == VERDICT_FAIL
    assert "reference_usable_rate" in record["hard_requirements"][
        "inherited_approval_hard_gates"
    ]["failing_hard_gates"]


def test_stage_a_insufficient_is_reachable(v3: dict) -> None:
    bundle = _stage_a_bundle(v3)
    bundle["inherited_gate_measurements"].pop("reference_usable_rate")
    record = validate_stage_a_candidate(bundle, repository_root=REPOSITORY_ROOT).as_record()
    assert record["verdict"] == VERDICT_INSUFFICIENT
    assert "reference_usable_rate" in record["hard_requirements"][
        "inherited_approval_hard_gates"
    ]["blocking_hard_gates"]


def test_stage_b_keeps_the_90_day_requirement(v3: dict) -> None:
    stage_a = validate_stage_a_candidate(
        _stage_a_bundle(v3), repository_root=REPOSITORY_ROOT
    ).as_record()
    assert evaluate_stage_b_promotion(stage_a, live_shadow_days=None).verdict == (
        VERDICT_INSUFFICIENT
    )
    assert evaluate_stage_b_promotion(stage_a, live_shadow_days=89).verdict == VERDICT_FAIL
    passed = evaluate_stage_b_promotion(stage_a, live_shadow_days=90).as_record()
    assert passed["verdict"] == VERDICT_PASS
    assert passed["threshold"] == 90


def test_stage_b_cannot_promote_a_nonpassing_historical_candidate(v3: dict) -> None:
    stage_a = validate_stage_a_candidate(
        _stage_a_bundle(v3, reference_usable_rate="0"),
        repository_root=REPOSITORY_ROOT,
    ).as_record()
    assert evaluate_stage_b_promotion(stage_a, live_shadow_days=365).verdict == (
        VERDICT_INSUFFICIENT
    )


def test_owner_completeness_refuses_executor_certification() -> None:
    assert unresolved_stage_a_hard_gate_owners(REPOSITORY_ROOT) == (
        EXPECTED_UNRESOLVED_STAGE_A_OWNERS
    )
    rows = {
        row["metric"]: row for row in inherited_gate_ownership_table(REPOSITORY_ROOT)
    }
    assert all(
        rows[metric]["authoritative_evidence_owner"] == []
        and rows[metric]["authoritative_owner_status"] == NO_EXECUTABLE_OWNER
        and rows[metric]["blocking_reason"]
        and rows[metric]["existing_repository_owner"]
        for metric in EXPECTED_UNRESOLVED_STAGE_A_OWNERS
    )
    with pytest.raises(V4StageCorrectionError, match="V4_EVIDENCE_PIPELINE_INCOMPLETE"):
        assert_stage_a_hard_gate_owner_completeness(REPOSITORY_ROOT)


def test_validator_contract_truthfully_refuses_sealed_execution() -> None:
    definition = validator_definition(REPOSITORY_ROOT)
    readiness = definition["execution_readiness"]
    assert readiness["every_stage_a_hard_gate_has_exactly_one_owner"] is False
    assert readiness["sealed_execution_authorized"] is False
    assert readiness["unresolved_stage_a_hard_gate_owners"] == list(
        EXPECTED_UNRESOLVED_STAGE_A_OWNERS
    )


def test_stage_contract_hashes_ignore_ambient_decimal_context() -> None:
    results = []
    for context in (
        Context(prec=6, rounding=ROUND_FLOOR),
        Context(prec=50, rounding=ROUND_CEILING),
    ):
        with localcontext(context):
            results.append(
                (
                    v4_protocol_definition(REPOSITORY_ROOT)["definition_sha256"],
                    validator_definition(REPOSITORY_ROOT)[
                        "validator_definition_sha256"
                    ],
                )
            )
    assert results[0] == results[1]


def test_artifacts_round_trip_and_a_tampered_diff_refuses(tmp_path: Path) -> None:
    v4_dir = tmp_path / "v4"
    validator_dir = tmp_path / "validator"
    written = write_v4_artifacts(REPOSITORY_ROOT, v4_dir)
    assert restore_v4_artifacts(REPOSITORY_ROOT, v4_dir) == written
    write_validator_artifacts(REPOSITORY_ROOT, validator_dir)
    diff_path = v4_dir / SEMANTIC_DIFF_FILENAME
    diff = json.loads(diff_path.read_text())
    diff["stage_relocations"][0]["threshold"] = 89
    diff_path.write_text(json.dumps(diff, indent=2, sort_keys=True) + "\n")
    with pytest.raises(V4StageCorrectionError, match="diff does not reproduce"):
        restore_v4_artifacts(REPOSITORY_ROOT, v4_dir)


def test_building_v4_does_not_change_v3_or_v1_artifacts(tmp_path: Path) -> None:
    v3_path = (
        REPOSITORY_ROOT
        / "research_artifacts/btc019_v3_gate_architecture_convergence/reference_composite_v3_protocol.json"
    )
    v1_path = REPOSITORY_ROOT / "research_artifacts/btc019_v3_validator/validator_definition.json"
    before = (_sha256(v3_path), _sha256(v1_path))
    write_v4_artifacts(REPOSITORY_ROOT, tmp_path / OUTPUT_NAMESPACE)
    assert (_sha256(v3_path), _sha256(v1_path)) == before


def test_no_sealed_data_path_is_read(monkeypatch) -> None:
    reads: list[str] = []
    original = Path.read_bytes

    def watched(path: Path, *args, **kwargs):
        reads.append(str(path))
        return original(path, *args, **kwargs)

    monkeypatch.setattr(Path, "read_bytes", watched)
    v4_protocol_definition(REPOSITORY_ROOT)
    assert not any("2015-07-20_2019-11-30" in path for path in reads)


def test_stage_b_rejects_a_tampered_stage_a_record(v3: dict) -> None:
    stage_a = validate_stage_a_candidate(
        _stage_a_bundle(v3), repository_root=REPOSITORY_ROOT
    ).as_record()
    stage_a["verdict"] = VERDICT_FAIL
    with pytest.raises(V4ValidatorError, match="digest does not reproduce"):
        evaluate_stage_b_promotion(stage_a, live_shadow_days=90)
