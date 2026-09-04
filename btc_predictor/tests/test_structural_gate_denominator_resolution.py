"""STRUCTURAL_GATE_DENOMINATOR_RESOLUTION regressions.

The record exists to make one thing impossible: publishing a structural
disagreement rate whose denominator nobody wrote down. These tests pin the
preservation invariants around the frozen BTC_REFERENCE_COMPOSITE_V2 protocol,
prove every affected metric carries explicit semantics, and prove the record is
reconstructable from already-inspected evidence alone -- with no path to the
sealed 2015-2019 sample and no dependency on any collected history.
"""

import decimal
import json
import shutil
from datetime import UTC, datetime
from decimal import Context, Decimal
from pathlib import Path

import pytest

from btc_predictor.research.cross_provider_structure_comparison import (
    AFFECTED_V2_GATE_METRICS,
    COMPARISON_CONTRACT_VERSION,
)
from btc_predictor.research.reference_composite_v2 import (
    EXPECTED_V2_PROTOCOL_ARTIFACT_SHA256,
    FROZEN_V2_DEFINITION_SHA256,
    UntouchedValidationSampleGuardError,
)
from btc_predictor.research.structural_gate_denominator_resolution import (
    ALL_DETECTED_EVENT_UNION,
    COMPARABLE_DETECTED_EVENT_UNION,
    COMPARABLE_DETECTED_EVENT_UNION_PAIRS_MERGED,
    DENOMINATOR_INTENT_NOT_RECOVERABLE,
    DENOMINATOR_SEMANTICS_VERSION,
    NEW_PROTOCOL_VERSION_REQUIRED,
    NOT_COMPARABLE_EXCLUDED,
    NOT_COMPARABLE_TREATMENTS,
    PARENT_DEFINITION_SHA256,
    PARENT_PROTOCOL_VERSION,
    RESOLUTION_OUTPUT_NAMESPACE,
    RESOLUTION_RECORD_FILENAME,
    RESOLUTION_SCHEMA_VERSION,
    STRUCTURAL_METRIC_RESOLUTIONS,
    SUCCESSOR_DEFINITION_FILENAME,
    SUCCESSOR_PROTOCOL_VERSION,
    SUCCESSOR_STATUS,
    THRESHOLD_CARRIED_FORWARD_UNCALIBRATED,
    THRESHOLD_SEMANTICS_NOT_RECOVERABLE,
    DenominatorResolutionError,
    EvidenceItem,
    StructuralMetricResolution,
    btc019b_threshold_anchor,
    build_resolution_record,
    denominator_materiality,
    frozen_parent_definition,
    frozen_structural_gates,
    guard_sealed_sample,
    restore_resolution_record,
    restore_successor_definition,
    successor_protocol_definition,
    verify_resolution_artifacts,
    write_resolution_artifacts,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
RESOLUTION_DIR = REPOSITORY_ROOT / RESOLUTION_OUTPUT_NAMESPACE

# The six frozen numbers, retyped here from the frozen artifact on purpose: a
# test that reads them from the same file it is guarding proves nothing.
FROZEN_STRUCTURAL_GATES = {
    "exact_timestamp_swing_disagreement_rate": ("0.15", "maximum", False),
    "within_1_week_swing_disagreement_rate": ("0.05", "maximum", True),
    "within_2_week_swing_disagreement_rate": ("0.02", "maximum", True),
    "structural_state_disagreement_rate": ("0.05", "maximum", True),
    "breakout_disagreement_rate": ("0.05", "maximum", True),
    "reclaim_disagreement_rate": ("0.05", "maximum", True),
}

# Everything the resolution reads. Deliberately excludes every collected
# history: nothing under data/ appears, so no sample can be a dependency.
_RESOLUTION_INPUTS = (
    "research_artifacts",
    "btc_predictor/research/reference_composite_empirical.py",
    "btc_predictor/research/btc019b_diagnostics.py",
)


@pytest.fixture(scope="module")
def record() -> dict:
    return build_resolution_record(REPOSITORY_ROOT)


def _isolated_root(destination: Path) -> Path:
    """Copy only the resolution's declared inputs into a fresh root."""

    for relative in _RESOLUTION_INPUTS:
        source = REPOSITORY_ROOT / relative
        target = destination / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return destination


# --- preservation of the frozen parent ---------------------------------------


def test_frozen_v2_definition_hash_is_unchanged() -> None:
    definition = frozen_parent_definition(REPOSITORY_ROOT)
    assert definition["definition_sha256"] == (
        "bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a"
    )
    assert definition["definition_sha256"] == FROZEN_V2_DEFINITION_SHA256
    assert definition["status"] == "FROZEN_RESEARCH_PROTOCOL"


def test_frozen_v2_protocol_artifact_bytes_are_unchanged() -> None:
    import hashlib

    directory = (
        REPOSITORY_ROOT
        / "research_artifacts/btc_reference_composite/BTC_REFERENCE_COMPOSITE_V2"
    )
    actual = {
        path.name: hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(directory.iterdir())
        if path.is_file()
    }
    assert actual == EXPECTED_V2_PROTOCOL_ARTIFACT_SHA256


def test_frozen_structural_thresholds_and_directions_are_unchanged() -> None:
    gates = frozen_structural_gates(REPOSITORY_ROOT)
    assert set(gates) == set(AFFECTED_V2_GATE_METRICS)
    for metric, (threshold, direction, hard) in FROZEN_STRUCTURAL_GATES.items():
        assert gates[metric]["threshold"] == threshold
        assert gates[metric]["direction"] == direction
        assert gates[metric]["hard"] is hard
        assert gates[metric]["validation_stage"] == "historical_oos"


def test_record_and_successor_carry_the_frozen_numbers_verbatim(record: dict) -> None:
    successor = successor_protocol_definition(REPOSITORY_ROOT)
    published = {item["metric"]: item for item in successor["structural_metrics"]}
    for metric, (threshold, direction, hard) in FROZEN_STRUCTURAL_GATES.items():
        assert published[metric]["frozen_threshold"] == threshold
        assert published[metric]["frozen_direction"] == direction
        assert published[metric]["frozen_hard"] is hard
    assert record["frozen_thresholds_changed"] is False
    assert record["frozen_gate_directions_changed"] is False
    assert record["parent_definition_unchanged"] is True


def test_a_changed_parent_hash_is_refused(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path / "root")
    path = (
        root
        / "research_artifacts/btc_reference_composite/BTC_REFERENCE_COMPOSITE_V2"
        / "protocol_definition.json"
    )
    definition = json.loads(path.read_text())
    definition["definition_sha256"] = "0" * 64
    path.write_text(json.dumps(definition, indent=2, sort_keys=True) + "\n")
    with pytest.raises(DenominatorResolutionError, match="definition hash changed"):
        frozen_parent_definition(root)


def test_a_changed_calibration_artifact_is_refused(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path / "root")
    path = root / "research_artifacts/btc019b/swing_disagreement_diagnostics.json"
    path.write_text(path.read_text() + " ")
    with pytest.raises(DenominatorResolutionError, match="calibration evidence changed"):
        build_resolution_record(root)


# --- explicit semantics for all six ------------------------------------------


def test_every_affected_metric_is_resolved_exactly_once(record: dict) -> None:
    metrics = [item["metric"] for item in record["metric_resolutions"]]
    assert metrics == list(AFFECTED_V2_GATE_METRICS)
    assert len(set(metrics)) == len(AFFECTED_V2_GATE_METRICS) == 6


def test_every_metric_declares_an_explicit_denominator(record: dict) -> None:
    for item in record["metric_resolutions"]:
        assert item["denominator_id"] in (
            COMPARABLE_DETECTED_EVENT_UNION,
            COMPARABLE_DETECTED_EVENT_UNION_PAIRS_MERGED,
        )
        assert item["numerator"].strip()
        assert item["denominator"].strip()
        assert item["candidate_universe"].strip()
        assert item["aggregation"].strip()


def test_every_metric_declares_an_explicit_not_comparable_treatment(
    record: dict,
) -> None:
    for item in record["metric_resolutions"]:
        assert item["not_comparable_treatment"] in NOT_COMPARABLE_TREATMENTS
        assert item["not_comparable_treatment"] == NOT_COMPARABLE_EXCLUDED
        assert item["availability_gap_treatment"].strip()
        assert item["pending_confirmation_treatment"].strip()
        assert item["absent_source_level_treatment"].strip()


def test_the_six_metrics_do_not_all_share_one_denominator(record: dict) -> None:
    by_metric = {item["metric"]: item["denominator_id"] for item in record["metric_resolutions"]}
    assert by_metric["exact_timestamp_swing_disagreement_rate"] == (
        COMPARABLE_DETECTED_EVENT_UNION
    )
    assert by_metric["within_1_week_swing_disagreement_rate"] == (
        COMPARABLE_DETECTED_EVENT_UNION_PAIRS_MERGED
    )
    assert by_metric["within_2_week_swing_disagreement_rate"] == (
        COMPARABLE_DETECTED_EVENT_UNION_PAIRS_MERGED
    )


def test_a_metric_may_not_silently_default_a_denominator() -> None:
    template = STRUCTURAL_METRIC_RESOLUTIONS[0]
    gate = frozen_structural_gates(REPOSITORY_ROOT)[template.metric]
    blank = StructuralMetricResolution(
        **{**template.__dict__, "denominator": "   "},
    )
    with pytest.raises(DenominatorResolutionError, match="leaves denominator undefined"):
        blank.as_record(gate)
    unknown = StructuralMetricResolution(
        **{**template.__dict__, "denominator_id": "whatever_passes"},
    )
    with pytest.raises(DenominatorResolutionError, match="unknown denominator"):
        unknown.as_record(gate)
    silent = StructuralMetricResolution(
        **{**template.__dict__, "not_comparable_treatment": ""},
    )
    with pytest.raises(DenominatorResolutionError, match="NOT_COMPARABLE treatment"):
        silent.as_record(gate)


def test_a_metric_outside_the_six_is_refused() -> None:
    template = STRUCTURAL_METRIC_RESOLUTIONS[0]
    gate = frozen_structural_gates(REPOSITORY_ROOT)[template.metric]
    stranger = StructuralMetricResolution(
        **{**template.__dict__, "metric": "stop_touch_disagreement_rate"},
    )
    with pytest.raises(DenominatorResolutionError, match="not an affected"):
        stranger.as_record(gate)


# --- threshold semantics ------------------------------------------------------


def test_no_frozen_structural_threshold_is_declared_portable(record: dict) -> None:
    for item in record["metric_resolutions"]:
        assert item["threshold_semantics"] == THRESHOLD_SEMANTICS_NOT_RECOVERABLE
        assert item["threshold_portability"] == THRESHOLD_CARRIED_FORWARD_UNCALIBRATED
        assert item["threshold_intent_evidence"].strip()


def test_breakout_and_reclaim_have_no_recoverable_denominator(record: dict) -> None:
    unrecoverable = record["classification"]["metrics_with_unrecoverable_denominator"]
    assert unrecoverable == [
        "breakout_disagreement_rate",
        "reclaim_disagreement_rate",
    ]
    by_metric = {item["metric"]: item for item in record["metric_resolutions"]}
    for metric in unrecoverable:
        assert by_metric[metric]["denominator_intent"] == (
            DENOMINATOR_INTENT_NOT_RECOVERABLE
        )


def test_the_only_numeric_threshold_anchor_is_availability_driven() -> None:
    anchor = btc019b_threshold_anchor(REPOSITORY_ROOT)
    exact = anchor["exact_timestamp"]
    assert exact["frozen_numerator"] == 4
    assert exact["frozen_denominator"] == 33
    assert exact["frozen_denominator_id"] == ALL_DETECTED_EVENT_UNION
    assert exact["frozen_rate"].startswith("0.12121212")
    # The frozen rationale reads "BTC-019B observed 12.1212%".
    assert exact["numerator_events_not_comparable"] == 4
    assert exact["numerator_under_resolved_denominator"] == 0
    assert exact["rate_under_resolved_denominator_numerator"] == "0"
    # The structural-state observation was already above its own frozen gate.
    assert anchor["structural_state"]["frozen_rate"].startswith("0.0606")
    assert Decimal(anchor["structural_state"]["frozen_rate"]) > Decimal("0.05")
    assert anchor["within_week_denominator"] == 31


def test_threshold_anchor_ignores_the_ambient_decimal_context() -> None:
    baseline = btc019b_threshold_anchor(REPOSITORY_ROOT)
    with decimal.localcontext(Context(prec=3, rounding=decimal.ROUND_UP)):
        narrowed = btc019b_threshold_anchor(REPOSITORY_ROOT)
    assert narrowed == baseline
    assert narrowed["exact_timestamp"]["frozen_rate"] == (
        "0.1212121212121212121212121212"
    )


# --- the governance conclusion ------------------------------------------------


def test_classification_is_new_protocol_version_required(record: dict) -> None:
    assert record["classification"]["outcome"] == NEW_PROTOCOL_VERSION_REQUIRED
    assert record["classification"]["reason_codes"] == sorted(
        record["classification"]["reason_codes"]
    )
    assert "ONLY_RECOVERABLE_READING_IS_THE_KNOWN_DEFECT" in (
        record["classification"]["reason_codes"]
    )
    assert "SUCCESSOR_REQUIRED_BY_PARENT_GOVERNANCE" in (
        record["classification"]["reason_codes"]
    )


def test_the_resolution_approves_and_opens_nothing(record: dict) -> None:
    assert record["btc019_status"] == "IN PROGRESS"
    assert record["production_canonical_reference"] == "UNRESOLVED"
    assert record["production_strategy_semantics_changed"] is False
    assert record["research_only"] is True
    assert record["may_build_sealed_validator"] is False
    assert record["may_collect_sealed_sample"] is False
    assert record["may_open_sealed_sample"] is False
    assert record["sealed_sample"]["opened"] is False
    assert record["sealed_sample"]["collected"] is False
    assert record["sealed_sample"]["statistics_derived"] is False


def test_denominator_choice_was_not_made_on_the_measured_verdicts(
    record: dict,
) -> None:
    materiality = record["denominator_materiality"]
    assert materiality["admitted_for"] == "materiality only"
    assert materiality["sealed_sample_used"] is False
    # Material: every one of the six moves on at least one measured pair.
    assert materiality["metrics_with_any_verdict_flip"] == 6
    assert materiality["hard_metrics_with_any_verdict_flip"] == 5
    # And not chosen for convenience: the adopted denominator still fails.
    assert materiality["resolved_denominator_is_uniformly_favourable"] is False
    by_metric = {item["metric"]: item for item in materiality["per_metric"]}
    assert by_metric["reclaim_disagreement_rate"]["fails_on_resolved_denominator"] == 5
    assert by_metric["within_2_week_swing_disagreement_rate"][
        "fails_on_resolved_denominator"
    ] == 4
    assert record["outcome_driven_reasoning"][
        "already_inspected_outcomes_influenced_denominator_choice"
    ] is False
    assert record["outcome_driven_reasoning"]["same_decision_if_verdicts_reversed"] is True


def test_coverage_contract_keeps_not_comparable_visible_without_a_new_rate_gate(
    record: dict,
) -> None:
    coverage = record["coverage_contract"]
    assert coverage["new_threshold_created"] is False
    assert coverage["new_numeric_gate_created"] is False
    assert coverage["structural_comparability_rate"].startswith(
        "comparable_event_count / all_detected_event_count"
    )
    assert coverage["why_no_numeric_floor"].strip()
    required = coverage["required_evidence"]
    assert "comparable_event_count" in required
    assert "not_comparable_event_count" in required
    assert "structural_comparability_rate" in required
    assert "candidate_event_count" in required
    provenance = coverage["provenance_requirement"]
    assert provenance["threshold"] == 0
    assert provenance["direction"] == "equal"
    assert provenance["hard"] is True


# --- the successor ------------------------------------------------------------


def test_successor_binds_the_parent_and_carries_its_own_hash() -> None:
    successor = successor_protocol_definition(REPOSITORY_ROOT)
    assert successor["reference_policy_version"] == SUCCESSOR_PROTOCOL_VERSION
    assert successor["parent_protocol_version"] == PARENT_PROTOCOL_VERSION
    assert successor["parent_definition_sha256"] == PARENT_DEFINITION_SHA256
    assert successor["definition_sha256"] != PARENT_DEFINITION_SHA256
    assert len(successor["definition_sha256"]) == 64
    assert successor["comparison_contract_version"] == COMPARISON_CONTRACT_VERSION
    assert successor["denominator_semantics_version"] == DENOMINATOR_SEMANTICS_VERSION


def test_successor_is_not_frozen_and_calibrates_nothing() -> None:
    successor = successor_protocol_definition(REPOSITORY_ROOT)
    assert successor["status"] == SUCCESSOR_STATUS
    assert successor["status"] != "FROZEN_RESEARCH_PROTOCOL"
    assert successor["production_promotion_authorized"] is False
    assert successor["research_only"] is True
    calibration = successor["threshold_calibration"]
    assert calibration["performed_here"] is False
    assert calibration["status"] == "REQUIRED_BEFORE_ANY_SEALED_EVALUATION"
    assert sorted(calibration["scope"]) == sorted(AFFECTED_V2_GATE_METRICS)
    assert successor["sealed_sample"]["opened"] is False
    assert successor["sealed_sample"]["collected"] is False


def test_successor_is_deterministic_and_order_independent(tmp_path: Path) -> None:
    first = successor_protocol_definition(REPOSITORY_ROOT)
    second = successor_protocol_definition(REPOSITORY_ROOT)
    assert first == second
    isolated = successor_protocol_definition(_isolated_root(tmp_path / "root"))
    assert isolated == first
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


# --- persistence and tamper rejection ----------------------------------------


def test_persisted_artifacts_recompute_from_the_repository() -> None:
    verified = verify_resolution_artifacts(REPOSITORY_ROOT, RESOLUTION_DIR)
    assert verified["schema_version"] == RESOLUTION_SCHEMA_VERSION
    successor = restore_successor_definition(RESOLUTION_DIR)
    assert verified["successor_definition_sha256"] == successor["definition_sha256"]


def test_written_artifacts_are_deterministic_ascii(tmp_path: Path) -> None:
    root = _isolated_root(tmp_path / "root")
    first_dir = tmp_path / "first"
    second_dir = tmp_path / "second"
    write_resolution_artifacts(root, first_dir)
    write_resolution_artifacts(root, second_dir)
    for name in (RESOLUTION_RECORD_FILENAME, SUCCESSOR_DEFINITION_FILENAME):
        assert (first_dir / name).read_bytes() == (second_dir / name).read_bytes()
        (first_dir / name).read_text(encoding="ascii")
    assert (first_dir / RESOLUTION_RECORD_FILENAME).read_bytes() == (
        RESOLUTION_DIR / RESOLUTION_RECORD_FILENAME
    ).read_bytes()


def test_tampered_resolution_record_is_refused(tmp_path: Path) -> None:
    write_resolution_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / RESOLUTION_RECORD_FILENAME
    record = json.loads(path.read_text())
    record["classification"]["outcome"] = "CLARIFICATION_VALID"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(DenominatorResolutionError, match="tampered"):
        restore_resolution_record(tmp_path)


def test_tampered_successor_definition_is_refused(tmp_path: Path) -> None:
    write_resolution_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / SUCCESSOR_DEFINITION_FILENAME
    definition = json.loads(path.read_text())
    definition["structural_metrics"][0]["frozen_threshold"] = "0.99"
    path.write_text(json.dumps(definition, indent=2, sort_keys=True) + "\n")
    with pytest.raises(DenominatorResolutionError, match="tampered"):
        restore_successor_definition(tmp_path)


def test_unknown_denominator_semantics_version_is_refused(tmp_path: Path) -> None:
    write_resolution_artifacts(REPOSITORY_ROOT, tmp_path)
    for filename, restore in (
        (RESOLUTION_RECORD_FILENAME, restore_resolution_record),
        (SUCCESSOR_DEFINITION_FILENAME, restore_successor_definition),
    ):
        path = tmp_path / filename
        payload = json.loads(path.read_text())
        payload["denominator_semantics_version"] = "SOMETHING_ELSE_V9"
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        with pytest.raises(DenominatorResolutionError, match="denominator-semantics"):
            restore(tmp_path)
        write_resolution_artifacts(REPOSITORY_ROOT, tmp_path)


def test_wrong_parent_protocol_hash_is_refused(tmp_path: Path) -> None:
    write_resolution_artifacts(REPOSITORY_ROOT, tmp_path)
    for filename, restore in (
        (RESOLUTION_RECORD_FILENAME, restore_resolution_record),
        (SUCCESSOR_DEFINITION_FILENAME, restore_successor_definition),
    ):
        path = tmp_path / filename
        payload = json.loads(path.read_text())
        payload["parent_definition_sha256"] = "f" * 64
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
        with pytest.raises(DenominatorResolutionError, match="parent protocol hash"):
            restore(tmp_path)
        write_resolution_artifacts(REPOSITORY_ROOT, tmp_path)


def test_a_record_missing_a_metric_is_refused(tmp_path: Path) -> None:
    write_resolution_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / RESOLUTION_RECORD_FILENAME
    record = json.loads(path.read_text())
    record["metric_resolutions"] = record["metric_resolutions"][:-1]
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(DenominatorResolutionError, match="exactly the six"):
        restore_resolution_record(tmp_path)


def test_a_record_with_a_blank_denominator_is_refused(tmp_path: Path) -> None:
    write_resolution_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / RESOLUTION_RECORD_FILENAME
    record = json.loads(path.read_text())
    record["metric_resolutions"][2]["denominator"] = ""
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(DenominatorResolutionError, match="has no denominator"):
        restore_resolution_record(tmp_path)


def test_a_record_without_a_not_comparable_treatment_is_refused(
    tmp_path: Path,
) -> None:
    write_resolution_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / RESOLUTION_RECORD_FILENAME
    record = json.loads(path.read_text())
    record["metric_resolutions"][0].pop("not_comparable_treatment")
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(DenominatorResolutionError, match="NOT_COMPARABLE treatment"):
        restore_resolution_record(tmp_path)


def test_an_unknown_schema_is_refused(tmp_path: Path) -> None:
    write_resolution_artifacts(REPOSITORY_ROOT, tmp_path)
    path = tmp_path / RESOLUTION_RECORD_FILENAME
    record = json.loads(path.read_text())
    record["schema_version"] = "SOMETHING_V2"
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(DenominatorResolutionError, match=RESOLUTION_SCHEMA_VERSION):
        restore_resolution_record(tmp_path)


# --- sealed-sample containment ------------------------------------------------


def test_sealed_sample_guard_still_rejects_overlapping_access() -> None:
    with pytest.raises(UntouchedValidationSampleGuardError):
        guard_sealed_sample(
            start=datetime(2015, 7, 20, 21, tzinfo=UTC),
            end=datetime(2019, 11, 30, 23, tzinfo=UTC),
            purpose="denominator resolution",
        )
    with pytest.raises(UntouchedValidationSampleGuardError):
        guard_sealed_sample(
            start=datetime(2019, 11, 1, tzinfo=UTC),
            end=datetime(2020, 1, 1, tzinfo=UTC),
            purpose="denominator resolution",
        )
    guard_sealed_sample(
        start=datetime(2019, 12, 1, tzinfo=UTC),
        end=datetime(2022, 12, 31, 23, tzinfo=UTC),
        purpose="already-inspected sample",
    )


def test_the_record_has_no_collected_history_dependency(tmp_path: Path) -> None:
    """It rebuilds byte-identically in a root that holds no data/ at all."""

    root = _isolated_root(tmp_path / "root")
    assert not (root / "data").exists()
    assert build_resolution_record(root) == build_resolution_record(REPOSITORY_ROOT)


def test_no_examined_evidence_reaches_the_sealed_period(record: dict) -> None:
    for item in record["examined_evidence"]:
        assert not item["path"].startswith("data/")
        assert "2015" not in item["path"]
    assert record["denominator_materiality"]["samples"] == (
        "already-inspected 2019-2022 and 2023-2025 only"
    )


def test_missing_pre_existing_evidence_fails_closed(tmp_path: Path) -> None:
    item = EvidenceItem(
        tier=1,
        identifier="gone",
        path="research_artifacts/does_not_exist.json",
        establishes="nothing",
        predates_defect_discovery=True,
    )
    with pytest.raises(DenominatorResolutionError, match="is missing"):
        item.as_record(REPOSITORY_ROOT)


# --- determinism --------------------------------------------------------------


def test_record_is_deterministic_and_independent_of_ambient_decimal(
    record: dict,
) -> None:
    assert build_resolution_record(REPOSITORY_ROOT) == record
    with decimal.localcontext(Context(prec=2, rounding=decimal.ROUND_FLOOR)):
        assert build_resolution_record(REPOSITORY_ROOT) == record


def test_materiality_rows_follow_the_frozen_metric_order() -> None:
    materiality = denominator_materiality(REPOSITORY_ROOT)
    order = [item["metric"] for item in materiality["per_metric"]]
    assert order == list(AFFECTED_V2_GATE_METRICS)
