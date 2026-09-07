"""One-shot sealed executor regressions for BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V2.

Four things must be impossible here.

V2 must not differ from certified V1 by anything but the authorization. The
executing contract is *derived* from the parent at build time, and the computed
field-level diff is compared against an enumerated declaration before anything
is hashed -- so the tests assert the diff exactly, assert every preserved block
is byte-identical, and run a differential corpus proving the two validators
return the same verdict, the same primary reason, the same hard outcomes, the
same certifications and the same diagnostics for every bundle V1 accepts.

The sealed sample must not be openable twice. The execution lock is durable, so
the tests restart it from disk between every step: a prepared authority stays
prepared, a started execution cannot be started again, and a finalized one can
never be re-run, re-prepared, re-collected or re-finalized.

A malformed manifest, a tampered authorization record or a bundle whose
provenance does not bind the frozen manifest must not reach a verdict.

And this suite itself must not collect, open or inspect 2015-2019. Every public
entry point is exercised under watchers on `open`, `Path.read_text`,
`Path.read_bytes` and `gzip.open`, with the OHLCV collector monkeypatched to
fail the test if it is ever called.
"""

import gzip
import hashlib
import inspect
import json
import multiprocessing
import os
import shutil
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from decimal import Context, Decimal, localcontext
from itertools import product
from pathlib import Path

import pytest

from btc_predictor.research.cross_provider_structure_comparison import (
    COMPARISON_CONTRACT_VERSION,
    WEEKLY_STRUCTURE_DETECTOR_VERSION,
)
from btc_predictor.research.price_source_policy import PRICE_SOURCE_POLICY_VERSION
from btc_predictor.research.reference_composite_v2 import (
    UNTOUCHED_OOS_END,
    UNTOUCHED_OOS_START,
    UntouchedValidationSampleGuardError,
)
from btc_predictor.research.structural_gate_denominator_resolution import (
    DENOMINATOR_SEMANTICS_VERSION,
)
from btc_predictor.research.structural_threshold_calibration import (
    PAIR_ADMISSIBLE,
    PAIR_INADMISSIBLE,
)
from btc_predictor.research.reference_composite_v3_convergence import (
    GATE_FAIL,
    GATE_INSUFFICIENT,
    GATE_PASS,
    INHERITED_TIER4_HARD_GATES,
    NORMAL_QUANTILE_0_975,
    PAIR_CERTIFIED,
    PAIR_INSUFFICIENT_EVIDENCE,
    v3_protocol_definition,
)
from btc_predictor.research import reference_composite_v3_validator as v1
from btc_predictor.research.reference_composite_v3_validator import (
    DIAGNOSTIC_METRICS,
    DIAGNOSTIC_REQUIRED_FIELDS,
    EVIDENCE_BUNDLE_SCHEMA_VERSION,
    EXACT_TIMESTAMP_METRIC,
    HARD_REQUIREMENT_IDS,
    REQUIREMENTS_THAT_CAN_FAIL,
    REQUIREMENT_DERIVED_LEVEL_REVIEW,
    REQUIREMENT_INHERITED_GATES,
    REQUIREMENT_NOT_COMPARABLE,
    REQUIREMENT_STRUCTURAL_GATE,
    REQUIREMENT_TRANSFER_GUARD,
    STRUCTURAL_METRIC,
    VERDICT_FAIL,
    VERDICT_INSUFFICIENT,
    VERDICT_PASS,
    VERDICT_VOCABULARY,
    ValidatorBindingError,
    ValidatorError,
    ValidatorInputError,
    compose_verdict,
    inherited_gate_definitions,
)
from btc_predictor.research import reference_composite_v3_sealed_executor as v2
from btc_predictor.research.reference_composite_v3_sealed_executor import (
    ALLOWED_CONTRACT_ADDED_FIELDS,
    ALLOWED_CONTRACT_CHANGED_FIELDS,
    ALLOWED_CONTRACT_REMOVED_FIELDS,
    AUTHORIZATION_FILENAME,
    AUTHORIZATION_SCHEMA_VERSION,
    EVIDENCE_FILENAME,
    EXECUTION_STATES,
    LEGAL_EXECUTION_TRANSITIONS,
    MANIFEST_SCHEMA_VERSION,
    MANIFEST_FILENAME,
    PARENT_VALIDATOR_DEFINITION_SHA256,
    PRESERVED_CONTRACT_FIELDS,
    SEALED_EXECUTION_AUTHORIZED,
    SEALED_EXECUTION_RESULT_FIELDS,
    SEALED_EXECUTION_RESULT_SCHEMA_VERSION,
    SEALED_EXECUTOR_OUTPUT_NAMESPACE,
    SEALED_PROVIDER_IDS,
    SEALED_EVIDENCE_BUILDER_VERSION,
    SEALED_WINDOW_END_ISO,
    SEALED_WINDOW_START_ISO,
    STATE_COLLECTED_FROZEN,
    STATE_EXECUTION_STARTED,
    STATE_FINALIZED,
    STATE_NOT_PREPARED,
    STATE_PREPARED,
    RESULT_FILENAME,
    VALIDATOR_DEFINITION_FILENAME,
    VALIDATOR_RECORD_SCHEMA_VERSION,
    VALIDATOR_SCHEMA_VERSION,
    VALIDATOR_VERSION,
    SealedExecutionAuthorizationError,
    SealedExecutionStateError,
    SealedSampleManifestError,
    SemanticDriftError,
    begin_sealed_execution,
    derive_execution_id,
    execute_sealed_validation,
    manifest_digest,
    prepare_sealed_execution,
    read_finalized_result,
    read_execution_authorization,
    record_frozen_collection_manifest,
    recover_sealed_execution,
    sealed_collection_plan,
    sealed_execution_status,
    semantic_delta,
    validate_sealed_sample_manifest,
    validator_definition,
    validator_definition_sha256,
    verify_parent_authority,
    verify_sealed_executor_artifacts,
    write_sealed_executor_artifacts,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# Both authorities, retyped rather than imported, so an edit to either module's
# own constant cannot make this suite agree with itself about the wrong thing.
FROZEN_V3_DEFINITION_SHA256 = (
    "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
)
CERTIFIED_V1_VALIDATOR_SHA256 = (
    "8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7"
)
PREVIOUS_CORRECTED_V2_VALIDATOR_SHA256 = (
    "49abd68975217bb78affc0b6bd6f5e2ba066e84ec745dc5b9bdf82d3bea99729"
)
CORRECTED_V2_VALIDATOR_SHA256 = "7fda8ac31f92de6a4adfc547260c0fb8f221564de34982ff8a72e85c07ad8be6"
FAILED_V2_VALIDATOR_SHA256 = (
    "e21e6ad8e8a40e4ee0763d7f3176efc168dacc0701f8e1199ae8a25ee5f9d784"
)
FROZEN_V2_PARENT_SHA256 = (
    "bc312f3e6a6035e00a3cd80103aacdee7b5a02ae69732b7bbca5785a3dd6106a"
)

GATE_PAIRS = (
    "MEDIAN_OHLC_V2_vs_bitfinex",
    "MEDIAN_OHLC_V2_vs_bitstamp",
    "MEDIAN_OHLC_V2_vs_coinbase",
)
GUARD_PAIRS = (
    "bitfinex_vs_bitstamp",
    "bitfinex_vs_coinbase",
    "bitstamp_vs_coinbase",
)

SYNTHETIC_START = "2023-01-01T00:00:00+00:00"
SYNTHETIC_END = "2025-12-31T23:00:00+00:00"

SEALED_YEARS = ("2015", "2016", "2017", "2018", "2019")


def _race_prepare_worker(repository_root, execution_root, barrier, queue) -> None:
    barrier.wait()
    try:
        record = v2.prepare_sealed_execution(
            Path(repository_root), authorization_dir=Path(execution_root)
        )
        queue.put(("SUCCESS", record["execution_id"]))
    except Exception as error:  # pragma: no cover - asserted in parent
        queue.put(("REFUSED", type(error).__name__))


def _race_begin_worker(repository_root, execution_root, barrier, queue) -> None:
    barrier.wait()
    try:
        v2.begin_sealed_execution(
            Path(repository_root), authorization_dir=Path(execution_root)
        )
        queue.put("SUCCESS")
    except Exception:  # pragma: no cover - asserted in parent
        queue.put("REFUSED")


def _race_execute_worker(repository_root, execution_root, barrier, queue) -> None:
    raw_reads = 0
    builder_calls = 0
    original = v2._read_regular_file_under_root

    def watched_read(*args, **kwargs):
        nonlocal raw_reads
        raw_reads += 1
        return original(*args, **kwargs)

    def observe_builder(builder, collection):
        nonlocal builder_calls
        builder_calls += 1

    v2._read_regular_file_under_root = watched_read
    v2._evidence_builder_invocation_point = observe_builder
    barrier.wait()
    try:
        v2.execute_sealed_validation(
            Path(execution_root),
            repository_root=Path(repository_root),
        )
        outcome = "SUCCESS"
    except Exception:  # pragma: no cover - asserted in parent
        outcome = "REFUSED"
    queue.put((outcome, raw_reads, builder_calls))


@pytest.fixture(scope="module")
def protocol() -> dict:
    return v3_protocol_definition(REPOSITORY_ROOT)


@pytest.fixture(scope="module")
def parent_contract() -> dict:
    return v1.validator_definition(REPOSITORY_ROOT)


@pytest.fixture(scope="module")
def contract() -> dict:
    return validator_definition(REPOSITORY_ROOT)


# =============================================================================
# synthetic fixtures -- no candidate history and no collected sample anywhere
# =============================================================================


def _pair_row(
    comparison_id: str,
    metric: str,
    numerator: int,
    denominator: int,
    *,
    comparability: str | None = "1",
    not_comparable: int = 0,
    state: str = PAIR_ADMISSIBLE,
    **overrides,
) -> dict:
    series_pair = sorted(comparison_id.split("_vs_"))
    detected = denominator + not_comparable
    row: dict = {
        "all_detected_event_count": detected,
        "candidate_event_count": denominator,
        "comparable_event_count": denominator,
        "comparison_id": comparison_id,
        "denominator": denominator,
        "metric": metric,
        "not_comparable_event_count": not_comparable,
        "not_comparable_rate": None if comparability is None else "0",
        "not_comparable_reason_counts": {},
        "numerator": numerator,
        "series_pair": series_pair,
        "state": state,
        "structural_comparability_rate": comparability,
    }
    row.update(overrides)
    return row


def _gate_rows(numerator: int = 0, denominator: int = 40, **overrides) -> list[dict]:
    return [
        _pair_row(name, STRUCTURAL_METRIC, numerator, denominator, **overrides)
        for name in GATE_PAIRS
    ]


def _guard_rows(numerator: int = 0, denominator: int = 40, **overrides) -> list[dict]:
    return [
        _pair_row(name, STRUCTURAL_METRIC, numerator, denominator, **overrides)
        for name in GUARD_PAIRS
    ]


def _soft_rows(numerator: int = 0, denominator: int = 40, **overrides) -> list[dict]:
    return [
        _pair_row(name, EXACT_TIMESTAMP_METRIC, numerator, denominator, **overrides)
        for name in GATE_PAIRS
    ]


def _diagnostic_row(comparison_id: str, count: int = 0, rate: str | None = "0") -> dict:
    row = {
        "calendar_displacement_weeks": [],
        "comparable_event_count": 12,
        "comparison_id": comparison_id,
        "count": count,
        "matched_pair_count": 0,
        "not_comparable_event_count": 0,
        "not_comparable_reason_counts": {},
        "rate": rate,
        "reason_codes": [],
    }
    assert not set(DIAGNOSTIC_REQUIRED_FIELDS) - set(row)
    return row


def _diagnostics(**counts_by_metric) -> dict:
    payload = {}
    for metric in DIAGNOSTIC_METRICS:
        counts = counts_by_metric.get(metric, {})
        payload[metric] = [
            _diagnostic_row(name, counts.get(name, 0)) for name in GATE_PAIRS
        ]
    return payload


def _inherited_measurements(protocol: dict, **overrides) -> dict:
    measurements = {}
    for gate in inherited_gate_definitions(protocol):
        threshold = gate["threshold"]
        measurements[gate["metric"]] = (
            threshold if isinstance(threshold, bool) else str(threshold)
        )
    measurements.update(overrides)
    return {key: value for key, value in measurements.items() if value is not None}


def _bundle(protocol: dict, **overrides) -> dict:
    bundle: dict = {
        "derived_level_review": {
            "observed_disagreements": [],
            "reviews": [],
            "unreviewed_derived_level_disagreement_count": 0,
        },
        "diagnostics": _diagnostics(),
        "gate_pair_measurements": _gate_rows(),
        "identities": {
            "candidate_method_version": "MEDIAN_OHLC_V2",
            "candidate_series_id": "MEDIAN_OHLC_V2",
            "comparison_contract_version": COMPARISON_CONTRACT_VERSION,
            "denominator_semantics_version": DENOMINATOR_SEMANTICS_VERSION,
            "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
            "provider_ids": ["bitfinex", "bitstamp", "coinbase"],
            "source_detector_version": WEEKLY_STRUCTURE_DETECTOR_VERSION,
        },
        "inherited_gate_measurements": _inherited_measurements(protocol),
        "not_comparable_accounting": {"unrecorded_not_comparable_event_count": 0},
        "provenance": {
            "evidence_builder_version": "SYNTHETIC_EVIDENCE_BUILDER_V1",
            "measurement_record_digest": "a" * 64,
            "sample_manifest_digest": "b" * 64,
        },
        "sample": {
            "end": SYNTHETIC_END,
            "sample_id": "SYNTHETIC_DRY_RUN",
            "start": SYNTHETIC_START,
        },
        "schema_version": EVIDENCE_BUNDLE_SCHEMA_VERSION,
        "soft_gate_pair_measurements": _soft_rows(),
        "transfer_guard_pair_measurements": _guard_rows(),
    }
    bundle.update(overrides)
    return bundle


def _v1_validate(bundle: dict, **kwargs):
    return v1.validate_v3_candidate(bundle, repository_root=REPOSITORY_ROOT, **kwargs)


def _v2_validate(bundle: dict, **kwargs):
    return v2.validate_v3_candidate(bundle, repository_root=REPOSITORY_ROOT, **kwargs)


# --- the synthetic sealed-sample collection manifest --------------------------


def _synthetic_raw_bytes(plan: dict) -> bytes:
    records = []
    for timestamp in (SEALED_WINDOW_START_ISO, SEALED_WINDOW_END_ISO):
        records.append(
            {
                "close": "100",
                "exchange": plan["exchange"],
                "fallback_used": False,
                "high": "101",
                "ingested_at": "2020-01-01T00:00:00+00:00",
                "low": "99",
                "open": "100",
                "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
                "price_source_roles": plan["price_source_roles"],
                "provider": plan["provider_id"],
                "schema_version": v2.RAW_ARTIFACT_SCHEMA_VERSION,
                "symbol": plan["instrument_symbol"],
                "timeframe": "1h",
                "timestamp": timestamp,
                "volume": "1",
            }
        )
    text = "".join(
        json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n"
        for row in records
    )
    return gzip.compress(text.encode(), mtime=0)


def _missing_synthetic_intervals() -> list[str]:
    start = datetime.fromisoformat(SEALED_WINDOW_START_ISO) + timedelta(hours=1)
    end = datetime.fromisoformat(SEALED_WINDOW_END_ISO)
    values = []
    while start < end:
        values.append(start.isoformat())
        start += timedelta(hours=1)
    return values


SYNTHETIC_MISSING_INTERVALS = _missing_synthetic_intervals()


def _manifest(
    digest: str, *, execution_root: Path | None = None, **overrides
) -> dict:
    """A synthetic manifest; optional raw files contain no market observations."""

    files = []
    for plan in sealed_collection_plan():
        provider_id = plan["provider_id"]
        raw = _synthetic_raw_bytes(plan)
        if execution_root is not None:
            path = execution_root / plan["raw_relative_path"]
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        files.append(
            {
                "byte_count": len(raw),
                "collection_source_identifier": v2._collection_source_identifier(
                    provider_id
                ),
                "duplicate_interval_count": 0,
                "duplicate_intervals": [],
                "first_observation": SEALED_WINDOW_START_ISO,
                "last_observation": SEALED_WINDOW_END_ISO,
                "missing_interval_count": len(SYNTHETIC_MISSING_INTERVALS),
                "missing_intervals": SYNTHETIC_MISSING_INTERVALS,
                "path": plan["raw_relative_path"],
                "provider_id": provider_id,
                "raw_mutation_count": 0,
                "row_count": 2,
                "sha256": hashlib.sha256(raw).hexdigest(),
                "source_provenance": {
                    "endpoint": plan["endpoint"],
                    "exchange": plan["exchange"],
                    "instrument_symbol": plan["instrument_symbol"],
                    "request_count": 1,
                },
            }
        )
    root = REPOSITORY_ROOT if execution_root is None else execution_root
    manifest = {
        "bar_interval": "1h",
        "bound_protocol_definition_sha256": FROZEN_V3_DEFINITION_SHA256,
        "collection_method": v2.COLLECTION_METHOD,
        "collection_method_version": v2.COLLECTION_METHOD_VERSION,
        "execution_id": derive_execution_id(digest, execution_root=root),
        "files": files,
        "manifest_sha256": "0" * 64,
        "manifest_version": MANIFEST_SCHEMA_VERSION,
        "parent_validator_definition_sha256": CERTIFIED_V1_VALIDATOR_SHA256,
        "provider_ids": list(SEALED_PROVIDER_IDS),
        "timezone": "UTC",
        "validator_definition_sha256": digest,
        "window_end": SEALED_WINDOW_END_ISO,
        "window_start": SEALED_WINDOW_START_ISO,
    }
    manifest.update(overrides)
    manifest["manifest_sha256"] = manifest_digest(manifest)
    return manifest


def _sealed_bundle(protocol: dict, manifest: dict, **overrides) -> dict:
    """A synthetic bundle labelled with the sealed window. Carries no market data."""

    bundle = _bundle(
        protocol,
        sample={
            "end": SEALED_WINDOW_END_ISO,
            "sample_id": "BTC019_SEALED_2015_07_20__2019_11_30",
            "start": SEALED_WINDOW_START_ISO,
        },
    )
    bundle["provenance"] = dict(
        bundle["provenance"],
        evidence_builder_version=SEALED_EVIDENCE_BUILDER_VERSION,
        sample_manifest_digest=manifest["manifest_sha256"],
    )
    bundle.update(overrides)
    return bundle


def _prepared(tmp_path: Path) -> tuple[Path, str, dict]:
    directory = tmp_path / "authorization"
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    prepare_sealed_execution(REPOSITORY_ROOT, authorization_dir=directory)
    return directory, digest, _manifest(digest, execution_root=directory)


def _collected(tmp_path: Path) -> tuple[Path, str, dict]:
    directory, digest, manifest = _prepared(tmp_path)
    record_frozen_collection_manifest(
        REPOSITORY_ROOT, authorization_dir=directory, manifest=manifest
    )
    return directory, digest, manifest


def _started(tmp_path: Path) -> tuple[Path, str, dict]:
    directory, digest, manifest = _collected(tmp_path)
    begin_sealed_execution(REPOSITORY_ROOT, authorization_dir=directory)
    return directory, digest, manifest


# =============================================================================
# 1. the two authorities reproduce before anything is prepared
# =============================================================================


def test_the_frozen_v3_definition_still_reproduces_its_hash(protocol: dict) -> None:
    assert protocol["definition_sha256"] == FROZEN_V3_DEFINITION_SHA256
    assert protocol["parent_definition_sha256"] == FROZEN_V2_PARENT_SHA256


def test_the_certified_v1_validator_still_reproduces_its_hash() -> None:
    assert v1.validator_definition_sha256(REPOSITORY_ROOT) == (
        CERTIFIED_V1_VALIDATOR_SHA256
    )


def test_the_persisted_v1_artifact_still_verifies() -> None:
    persisted = v1.verify_validator_artifacts(
        REPOSITORY_ROOT, REPOSITORY_ROOT / v1.VALIDATOR_OUTPUT_NAMESPACE
    )
    assert persisted["validator_definition_sha256"] == CERTIFIED_V1_VALIDATOR_SHA256


def test_the_parent_authority_check_returns_the_certified_contract() -> None:
    parent = verify_parent_authority(REPOSITORY_ROOT)
    assert parent["validator_definition_sha256"] == CERTIFIED_V1_VALIDATOR_SHA256
    assert parent["sealed_sample"]["sealed_execution_authorized"] is False


def test_a_parent_whose_hash_moved_refuses_to_prepare(monkeypatch) -> None:
    monkeypatch.setattr(
        v2, "PARENT_VALIDATOR_DEFINITION_SHA256", "f" * 64
    )
    with pytest.raises(ValidatorBindingError, match="REFUSE_TO_PREPARE"):
        verify_parent_authority(REPOSITORY_ROOT)


def test_a_moved_v3_hash_refuses_to_prepare(monkeypatch) -> None:
    monkeypatch.setattr(
        v2, "BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED", "e" * 64
    )
    with pytest.raises(ValidatorBindingError, match="REFUSE_TO_PREPARE"):
        verify_parent_authority(REPOSITORY_ROOT)


def test_a_parent_that_already_authorises_sealed_execution_refuses(
    monkeypatch,
) -> None:
    """The successor may only descend from the reviewed non-executing contract."""

    certified = v1.validator_definition(REPOSITORY_ROOT)
    forged = dict(certified)
    forged["sealed_sample"] = dict(
        certified["sealed_sample"], sealed_execution_authorized=True
    )
    monkeypatch.setattr(v1, "validator_definition", lambda root: forged)
    with pytest.raises(ValidatorBindingError, match="already authorises"):
        verify_parent_authority(REPOSITORY_ROOT)


# =============================================================================
# 2. the semantic delta is exactly the authorization and its controls
# =============================================================================


def test_the_computed_delta_is_exactly_the_declared_delta() -> None:
    delta = semantic_delta(REPOSITORY_ROOT)
    assert delta["changed_fields"] == sorted(ALLOWED_CONTRACT_CHANGED_FIELDS)
    assert delta["added_fields"] == sorted(ALLOWED_CONTRACT_ADDED_FIELDS)
    assert delta["removed_fields"] == sorted(ALLOWED_CONTRACT_REMOVED_FIELDS) == []


def test_the_one_verdict_affecting_delta_is_the_authorization_flag(
    parent_contract: dict, contract: dict
) -> None:
    assert parent_contract["sealed_sample"]["sealed_execution_authorized"] is False
    assert contract["sealed_sample"]["sealed_execution_authorized"] is True
    assert SEALED_EXECUTION_AUTHORIZED is True
    delta = contract["semantic_delta"]["verdict_affecting_delta"]
    assert delta == {
        "field": "sealed_sample.sealed_execution_authorized",
        "parent_value": False,
        "value": True,
    }


@pytest.mark.parametrize("field", PRESERVED_CONTRACT_FIELDS)
def test_every_preserved_parent_field_is_byte_identical(
    field: str, parent_contract: dict, contract: dict
) -> None:
    assert json.dumps(contract[field], sort_keys=True) == json.dumps(
        parent_contract[field], sort_keys=True
    )


def test_no_surprise_field_difference_survives(
    parent_contract: dict, contract: dict
) -> None:
    """Any field difference the declaration does not name fails the build."""

    delta = v2._compute_semantic_delta(parent_contract, contract)
    surprises = (
        set(delta["changed_fields"]) - set(ALLOWED_CONTRACT_CHANGED_FIELDS)
    ) | (set(delta["added_fields"]) - set(ALLOWED_CONTRACT_ADDED_FIELDS))
    assert surprises == set()
    assert delta["removed_fields"] == []


def test_a_contract_that_changed_something_else_refuses_to_freeze(
    parent_contract: dict, contract: dict
) -> None:
    drifted = dict(contract)
    drifted["verdict_vocabulary"] = ["PASS"]
    delta = v2._compute_semantic_delta(parent_contract, drifted)
    with pytest.raises(SemanticDriftError, match="REFUSE_TO_FREEZE"):
        v2._assert_delta_is_authorized(delta)


def test_a_contract_that_dropped_a_parent_block_refuses_to_freeze(
    parent_contract: dict, contract: dict
) -> None:
    drifted = {key: value for key, value in contract.items() if key != "hard_requirements"}
    delta = v2._compute_semantic_delta(parent_contract, drifted)
    with pytest.raises(SemanticDriftError, match="REFUSE_TO_FREEZE"):
        v2._assert_delta_is_authorized(delta)


def test_a_declared_delta_the_contracts_do_not_exhibit_refuses(monkeypatch) -> None:
    monkeypatch.setattr(
        v2,
        "ALLOWED_CONTRACT_CHANGED_FIELDS",
        ALLOWED_CONTRACT_CHANGED_FIELDS + ("materiality_limit",),
    )
    with pytest.raises(SemanticDriftError, match="do not actually differ"):
        validator_definition(REPOSITORY_ROOT)


def test_the_declared_thresholds_are_all_identical(
    parent_contract: dict, contract: dict
) -> None:
    """Every number a verdict can turn on travels unchanged."""

    for block, field in (
        ("soft_requirements", "limit"),
        ("certification_rule", "normal_quantile"),
        ("certification_rule", "confidence_level_percent"),
    ):
        assert contract[block][field] == parent_contract[block][field]
    assert contract["certification_rule"]["boundary_vectors"] == (
        parent_contract["certification_rule"]["boundary_vectors"]
    )
    limits = {
        row["requirement"]: row
        for row in contract["hard_requirements"]
        if isinstance(row, dict)
    }
    parent_limits = {
        row["requirement"]: row
        for row in parent_contract["hard_requirements"]
        if isinstance(row, dict)
    }
    assert limits == parent_limits


def test_the_delta_record_binds_both_hashes() -> None:
    delta = semantic_delta(REPOSITORY_ROOT)
    assert delta["parent_validator_definition_sha256"] == CERTIFIED_V1_VALIDATOR_SHA256
    assert delta["validator_definition_sha256"] == validator_definition_sha256(
        REPOSITORY_ROOT
    )
    assert delta["validator_version"] == VALIDATOR_VERSION


# =============================================================================
# 3. lineage, identity and the executing hash
# =============================================================================


def test_the_contract_declares_its_lineage(contract: dict) -> None:
    assert contract["validator_version"] == VALIDATOR_VERSION
    assert contract["validator_schema_version"] == VALIDATOR_SCHEMA_VERSION
    parent = contract["parent_validator"]
    assert parent["validator_version"] == "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1"
    assert parent["validator_definition_sha256"] == CERTIFIED_V1_VALIDATOR_SHA256
    assert parent["sealed_execution_authorized"] is False
    assert parent["certification"] == (
        "VALIDATOR_CERTIFIED_FOR_SEALED_EXECUTION_PREPARATION"
    )
    assert contract["binding"]["bound_protocol_definition_sha256"] == (
        FROZEN_V3_DEFINITION_SHA256
    )
    assert contract["binding"]["parent_protocol_definition_sha256"] == (
        FROZEN_V2_PARENT_SHA256
    )


def test_the_executing_hash_is_not_either_authority(contract: dict) -> None:
    digest = contract["validator_definition_sha256"]
    assert digest == CORRECTED_V2_VALIDATOR_SHA256
    assert digest != FAILED_V2_VALIDATOR_SHA256
    assert digest not in {
        CERTIFIED_V1_VALIDATOR_SHA256,
        FROZEN_V3_DEFINITION_SHA256,
        FROZEN_V2_PARENT_SHA256,
    }
    assert len(digest) == 64


def test_v1_is_not_mutated_in_place() -> None:
    """The certified parent stays exactly what was reviewed."""

    assert v1.SEALED_EXECUTION_AUTHORIZED is False
    assert v1.VALIDATOR_VERSION == "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1"
    assert v1.validator_definition_sha256(REPOSITORY_ROOT) == (
        CERTIFIED_V1_VALIDATOR_SHA256
    )
    with pytest.raises(v1.SealedExecutionNotAuthorizedError):
        _v1_validate(_bundle(v3_protocol_definition(REPOSITORY_ROOT)),
                     execution_mode=v1.EXECUTION_MODE_SEALED)


# =============================================================================
# 4. V1 <-> V2 differential parity
# =============================================================================

_CORPUS_MUTATIONS: dict[str, dict] = {}


def _corpus(protocol: dict) -> dict[str, dict]:
    """A deterministic corpus spanning every verdict and every requirement."""

    gates = inherited_gate_definitions(protocol)
    hard_metric = next(gate["metric"] for gate in gates if gate["hard"])
    soft_metric = next(gate["metric"] for gate in gates if not gate["hard"])
    census_review = {
        "observed_disagreements": [
            {
                "comparison_id": GATE_PAIRS[0],
                "event_id": "e1",
                "family": "breakout",
                "week": "2024-01-01",
            }
        ],
        "reviews": [],
        "unreviewed_derived_level_disagreement_count": 1,
    }
    bundles = {
        "all_pass": _bundle(protocol),
        "structural_material_failure": _bundle(
            protocol, gate_pair_measurements=_gate_rows(20, 40)
        ),
        "structural_thin": _bundle(protocol, gate_pair_measurements=_gate_rows(0, 10)),
        "structural_zero_denominator": _bundle(
            protocol, gate_pair_measurements=_gate_rows(0, 0, comparability=None)
        ),
        "structural_boundary_certifies": _bundle(
            protocol, gate_pair_measurements=_gate_rows(3, 40)
        ),
        "structural_boundary_insufficient": _bundle(
            protocol, gate_pair_measurements=_gate_rows(3, 39)
        ),
        "guard_failure": _bundle(
            protocol, transfer_guard_pair_measurements=_guard_rows(20, 40)
        ),
        "guard_undefined_thin": _bundle(
            protocol, transfer_guard_pair_measurements=_guard_rows(2, 28)
        ),
        "guard_pair_missing": _bundle(
            protocol, transfer_guard_pair_measurements=_guard_rows()[:2]
        ),
        "comparability_below_floor": _bundle(
            protocol,
            gate_pair_measurements=_gate_rows(
                0, 40, comparability="0.4", not_comparable=60
            ),
        ),
        "gate_pair_missing": _bundle(protocol, gate_pair_measurements=_gate_rows()[:2]),
        "gate_pair_inadmissible": _bundle(
            protocol, gate_pair_measurements=_gate_rows(0, 40, state=PAIR_INADMISSIBLE)
        ),
        "not_comparable_positive": _bundle(
            protocol,
            not_comparable_accounting={"unrecorded_not_comparable_event_count": 3},
        ),
        "derived_level_unreviewed": _bundle(
            protocol,
            derived_level_review=census_review,
            diagnostics=_diagnostics(breakout_disagreement_rate={GATE_PAIRS[0]: 1}),
        ),
        "inherited_hard_gate_violated": _bundle(
            protocol,
            inherited_gate_measurements=_inherited_measurements(
                protocol, **{hard_metric: "999"}
            ),
        ),
        "inherited_soft_gate_violated": _bundle(
            protocol,
            inherited_gate_measurements=_inherited_measurements(
                protocol, **{soft_metric: "999"}
            ),
        ),
        "soft_gate_warning": _bundle(protocol, soft_gate_pair_measurements=_soft_rows(20, 40)),
        "soft_gate_missing": _bundle(
            protocol, soft_gate_pair_measurements=_soft_rows()[:1]
        ),
        "diagnostics_extreme": _bundle(
            protocol,
            diagnostics={
                metric: [
                    _diagnostic_row(name, 0, rate="0.99") for name in GATE_PAIRS
                ]
                for metric in DIAGNOSTIC_METRICS
            },
        ),
        "failure_outranks_insufficiency": _bundle(
            protocol,
            gate_pair_measurements=_gate_rows(20, 40),
            transfer_guard_pair_measurements=_guard_rows(2, 28),
        ),
        "everything_wrong_at_once": _bundle(
            protocol,
            gate_pair_measurements=_gate_rows(20, 40),
            transfer_guard_pair_measurements=_guard_rows(20, 40),
            not_comparable_accounting={"unrecorded_not_comparable_event_count": 9},
            inherited_gate_measurements=_inherited_measurements(
                protocol, **{hard_metric: "999"}
            ),
        ),
    }
    for numerator, denominator in (
        (0, 15),
        (0, 16),
        (1, 24),
        (1, 25),
        (2, 32),
        (2, 33),
    ):
        bundles[f"wilson_{numerator}_of_{denominator}"] = _bundle(
            protocol, gate_pair_measurements=_gate_rows(numerator, denominator)
        )
    return bundles


# The fields V2 is permitted to differ in. Everything else must be identical.
ALLOWED_RECORD_CHANGED_FIELDS = frozenset(
    {
        "schema_version",
        "validation_record_digest",
        "validator_definition_sha256",
        "validator_version",
    }
)
ALLOWED_RECORD_ADDED_FIELDS = frozenset(
    {
        "parent_validator_definition_sha256",
        "parent_validator_version",
        "sealed_execution",
    }
)


def _record_delta(left: dict, right: dict) -> tuple[set[str], set[str], set[str]]:
    keys = set(left) | set(right)
    changed = {
        key
        for key in keys & set(left) & set(right)
        if json.dumps(left[key], sort_keys=True)
        != json.dumps(right[key], sort_keys=True)
    }
    return changed, set(right) - set(left), set(left) - set(right)


def test_every_corpus_bundle_returns_the_same_verdict(protocol: dict) -> None:
    """V1 and V2 agree on every bundle V1 accepts, field for field."""

    corpus = _corpus(protocol)
    assert len(corpus) >= 25
    verdicts = set()
    for name, bundle in sorted(corpus.items()):
        left = _v1_validate(bundle).as_record()
        right = _v2_validate(bundle).as_record()
        changed, added, removed = _record_delta(left, right)
        assert changed == ALLOWED_RECORD_CHANGED_FIELDS, name
        assert added == ALLOWED_RECORD_ADDED_FIELDS, name
        assert removed == set(), name
        assert left["verdict"] == right["verdict"], name
        assert left["primary_reason"] == right["primary_reason"], name
        assert left["reason_codes"] == right["reason_codes"], name
        assert left["hard_requirement_outcomes"] == right["hard_requirement_outcomes"]
        assert left["hard_requirements"] == right["hard_requirements"], name
        assert left["soft_gate"] == right["soft_gate"], name
        assert left["diagnostics"] == right["diagnostics"], name
        assert left["composition"] == right["composition"], name
        assert left["input_evidence_digest"] == right["input_evidence_digest"], name
        assert left["provenance"] == right["provenance"], name
        assert left["statistical_limitation"] == right["statistical_limitation"], name
        verdicts.add(right["verdict"])
    assert verdicts == set(VERDICT_VOCABULARY)


def test_the_pair_certifications_are_identical(protocol: dict) -> None:
    for bundle in _corpus(protocol).values():
        left = _v1_validate(bundle).as_record()["hard_requirements"]
        right = _v2_validate(bundle).as_record()["hard_requirements"]
        for requirement in (REQUIREMENT_STRUCTURAL_GATE, REQUIREMENT_TRANSFER_GUARD):
            assert left[requirement].get("pairs") == right[requirement].get("pairs")
            assert left[requirement]["outcome"] == right[requirement]["outcome"]


def test_the_inherited_gate_outcomes_are_identical(protocol: dict) -> None:
    for bundle in _corpus(protocol).values():
        left = _v1_validate(bundle).as_record()["hard_requirements"]
        right = _v2_validate(bundle).as_record()["hard_requirements"]
        assert left[REQUIREMENT_INHERITED_GATES] == right[REQUIREMENT_INHERITED_GATES]


# --- the complete 648 legal hard-state combinations ---------------------------

_LEGAL_OUTCOMES = {
    requirement: (
        (GATE_PASS, GATE_FAIL, GATE_INSUFFICIENT)
        if requirement in REQUIREMENTS_THAT_CAN_FAIL
        else (GATE_PASS, GATE_INSUFFICIENT)
    )
    for requirement in HARD_REQUIREMENT_IDS
}


def _legal_states():
    for combination in product(
        *(_LEGAL_OUTCOMES[name] for name in HARD_REQUIREMENT_IDS)
    ):
        yield dict(zip(HARD_REQUIREMENT_IDS, combination))


def test_all_648_legal_states_compose_identically() -> None:
    states = list(_legal_states())
    assert len(states) == 3**4 * 2**3 == 648
    passing = 0
    for outcomes in states:
        left = compose_verdict(outcomes)
        right = v2._v1.compose_verdict(outcomes)
        assert left == right
        assert left["verdict"] in VERDICT_VOCABULARY
        if left["verdict"] == VERDICT_PASS:
            passing += 1
    assert passing == 1


def test_v2_composes_through_the_certified_function_itself() -> None:
    """Not a parallel implementation: literally the parent's own object."""

    assert v2._v1.compose_verdict is compose_verdict
    assert v2._v1.certify_pair is v1.certify_pair
    assert v2._v1.evaluate_soft_gate is v1.evaluate_soft_gate
    assert v2._v1.evaluate_hard_structural_gate is v1.evaluate_hard_structural_gate
    assert v2._v1.evaluate_transfer_guard is v1.evaluate_transfer_guard


def test_v2_defines_no_verdict_vocabulary_of_its_own() -> None:
    assert v2.VERDICT_VOCABULARY is VERDICT_VOCABULARY
    assert list(VERDICT_VOCABULARY) == [
        "PASS",
        "FAIL",
        "UNDEFINED_INSUFFICIENT_EVIDENCE",
    ]
    assert v2.HARD_REQUIREMENT_IDS is HARD_REQUIREMENT_IDS


# =============================================================================
# 5. Wilson parity -- the eight reviewed vectors, again
# =============================================================================

WILSON_VECTORS = (
    (0, 15, PAIR_INSUFFICIENT_EVIDENCE),
    (0, 16, PAIR_CERTIFIED),
    (1, 24, PAIR_INSUFFICIENT_EVIDENCE),
    (1, 25, PAIR_CERTIFIED),
    (2, 32, PAIR_INSUFFICIENT_EVIDENCE),
    (2, 33, PAIR_CERTIFIED),
    (3, 39, PAIR_INSUFFICIENT_EVIDENCE),
    (3, 40, PAIR_CERTIFIED),
)


@pytest.mark.parametrize("numerator,denominator,outcome", WILSON_VECTORS)
def test_the_eight_boundary_vectors_are_pinned_in_the_executing_contract(
    numerator: int, denominator: int, outcome: str, contract: dict, protocol: dict
) -> None:
    pinned = contract["certification_rule"]["boundary_vectors"]
    assert {
        "numerator": numerator,
        "denominator": denominator,
        "outcome": outcome,
    } in pinned
    assert contract["certification_rule"]["continuity_correction_applied"] is False
    actual = v1._pair_outcome_at(
        numerator,
        denominator,
        limit=v1.operative_structural_limit(protocol),
        quantile=v1.operative_normal_quantile(protocol),
    )
    assert actual == outcome


def test_the_executing_contract_refuses_a_moved_boundary(monkeypatch) -> None:
    """A continuity-corrected substitution refuses before V2 is even built."""

    from btc_predictor.research import reference_composite_v3_convergence as owner

    def _continuity_corrected(
        numerator: int, denominator: int, *, quantile: Decimal = NORMAL_QUANTILE_0_975
    ) -> Decimal | None:
        if denominator == 0:
            return None
        n = Decimal(denominator)
        p = Decimal(numerator) / n
        z2 = quantile * quantile
        inner = z2 + 2 - 1 / n + 4 * p * (n * (1 - p) - 1)
        if inner < 0:
            inner = Decimal(0)
        return min(
            (2 * n * p + z2 + 1 + quantile * inner.sqrt()) / (2 * (n + z2)), Decimal(1)
        )

    monkeypatch.setattr(owner, "wilson_upper_bound", _continuity_corrected)
    with pytest.raises(ValidatorBindingError, match="the certification rule makes"):
        validator_definition(REPOSITORY_ROOT)


def test_v2_uses_the_parents_own_bound() -> None:
    assert v2._v1.structural_upper_bound is v1.structural_upper_bound
    assert v2._v1.WILSON_CONTINUITY_CORRECTION_APPLIED is False


# =============================================================================
# 6. pair-value, census, NOT_COMPARABLE and Tier-4 parity
# =============================================================================


def _refuses_identically(bundle: dict, match: str) -> None:
    with pytest.raises(ValidatorInputError, match=match):
        _v1_validate(bundle)
    with pytest.raises(ValidatorInputError, match=match):
        _v2_validate(bundle)


def test_a_fake_denominator_still_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0] = _pair_row(GATE_PAIRS[0], STRUCTURAL_METRIC, 0, 2, comparability="0.5",
                        not_comparable=2)
    rows[0]["denominator"] = 40
    _refuses_identically(
        _bundle(protocol, gate_pair_measurements=rows), "declares a denominator of 40"
    )


def test_a_fake_comparability_rate_still_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0] = _pair_row(
        GATE_PAIRS[0], STRUCTURAL_METRIC, 0, 40, comparability="0.90", not_comparable=400
    )
    _refuses_identically(
        _bundle(protocol, gate_pair_measurements=rows), "disagrees with its own"
    )


def test_a_null_rate_beside_detected_events_still_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0]["not_comparable_rate"] = None
    _refuses_identically(
        _bundle(protocol, gate_pair_measurements=rows), "cannot be null"
    )


def test_a_rate_present_with_nothing_detected_still_refuses(protocol: dict) -> None:
    rows = _gate_rows(0, 0, comparability=None)
    rows[0]["structural_comparability_rate"] = "1"
    _refuses_identically(_bundle(protocol, gate_pair_measurements=rows), "must be null")


def test_a_missing_admissibility_state_still_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0].pop("state")
    _refuses_identically(
        _bundle(protocol, gate_pair_measurements=rows), "omits required fields"
    )


def test_an_unknown_pair_field_still_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0]["shadow_rate"] = "0"
    _refuses_identically(
        _bundle(protocol, gate_pair_measurements=rows), "unknown fields"
    )


def test_a_duplicated_pair_still_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    rows.append(dict(rows[0]))
    _refuses_identically(
        _bundle(protocol, gate_pair_measurements=rows), "DUPLICATE_PAIR_MEASUREMENT"
    )


def test_a_wrong_provider_identity_still_refuses(protocol: dict) -> None:
    rows = _gate_rows()
    rows[0]["series_pair"] = ["MEDIAN_OHLC_V2", "kraken"]
    rows[0]["comparison_id"] = "MEDIAN_OHLC_V2_vs_kraken"
    _refuses_identically(
        _bundle(protocol, gate_pair_measurements=rows), "PROVIDER_IDENTITY_MISMATCH"
    )


def test_a_wrong_tier4_identity_still_refuses(protocol: dict) -> None:
    measurements = _inherited_measurements(protocol)
    measurements["an_invented_tier4_gate"] = "0"
    _refuses_identically(
        _bundle(protocol, inherited_gate_measurements=measurements),
        "does not inherit",
    )


def test_the_derived_level_census_rule_is_unchanged(
    parent_contract: dict, contract: dict
) -> None:
    assert contract["diagnostic_requirements"] == parent_contract[
        "diagnostic_requirements"
    ]
    census = next(
        row
        for row in contract["hard_requirements"]
        if row["requirement"] == REQUIREMENT_DERIVED_LEVEL_REVIEW
    )
    assert census["census_verification"] == v1.CENSUS_VERIFICATION_RULE
    # The reviewed rule reads a diagnostic *count* and never a diagnostic rate,
    # and can only refuse. Neither word moved.
    assert "count" in v1.CENSUS_VERIFICATION_RULE
    assert "never approve" in v1.CENSUS_VERIFICATION_RULE


def test_a_census_mismatch_still_refuses(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        diagnostics=_diagnostics(breakout_disagreement_rate={GATE_PAIRS[0]: 2}),
    )
    left = _v1_validate(bundle).as_record()
    right = _v2_validate(bundle).as_record()
    assert left["verdict"] == right["verdict"] == VERDICT_INSUFFICIENT
    assert (
        right["hard_requirements"][REQUIREMENT_DERIVED_LEVEL_REVIEW]
        == left["hard_requirements"][REQUIREMENT_DERIVED_LEVEL_REVIEW]
    )


def test_the_not_comparable_rule_is_the_reviewed_declared_zero_count(
    parent_contract: dict, contract: dict
) -> None:
    assert contract["not_comparable_handling"] == parent_contract[
        "not_comparable_handling"
    ]
    assert contract["not_comparable_handling"]["zero_count"] == VERDICT_PASS
    assert contract["not_comparable_handling"]["positive_count"] == VERDICT_FAIL
    assert contract["not_comparable_handling"]["missing_count"] == VERDICT_INSUFFICIENT


def test_no_new_not_comparable_cross_check_was_invented(protocol: dict) -> None:
    """A reason-count sum may not be used to derive the unrecorded count."""

    rows = _gate_rows(0, 40, not_comparable=6)
    rows = [
        dict(row, not_comparable_reason_counts={"MISSING_WEEK": 6}) for row in rows
    ]
    bundle = _bundle(protocol, gate_pair_measurements=rows)
    left = _v1_validate(bundle).as_record()
    right = _v2_validate(bundle).as_record()
    assert left["hard_requirements"][REQUIREMENT_NOT_COMPARABLE] == (
        right["hard_requirements"][REQUIREMENT_NOT_COMPARABLE]
    )
    assert right["hard_requirements"][REQUIREMENT_NOT_COMPARABLE]["outcome"] == GATE_PASS


def test_all_33_inherited_gates_are_byte_identical(
    parent_contract: dict, contract: dict
) -> None:
    left = parent_contract["tier4_inheritance"]
    right = contract["tier4_inheritance"]
    assert left == right
    assert right["total_gate_count"] == 33
    assert right["hard_gate_count"] == 29
    assert right["soft_gate_count"] == 4
    assert right["named_tier4_hard_gates"] == list(INHERITED_TIER4_HARD_GATES)
    assert len(INHERITED_TIER4_HARD_GATES) == 13
    assert right["soft_gates_can_regain_a_hard_veto"] is False


def test_every_named_tier4_hard_gate_still_fails_the_run(protocol: dict) -> None:
    gates = {gate["metric"]: gate for gate in inherited_gate_definitions(protocol)}
    for metric in INHERITED_TIER4_HARD_GATES:
        gate = gates[metric]
        if isinstance(gate["threshold"], bool):
            violation = not gate["threshold"]
        elif gate["direction"] == "minimum":
            violation = "0"
        else:
            violation = "999999"
        bundle = _bundle(
            protocol,
            inherited_gate_measurements=_inherited_measurements(
                protocol, **{metric: violation}
            ),
        )
        left = _v1_validate(bundle).as_record()
        right = _v2_validate(bundle).as_record()
        assert left["verdict"] == right["verdict"] == VERDICT_FAIL, metric
        assert left["primary_reason"] == right["primary_reason"], metric


# =============================================================================
# 7. sealed execution authorization
# =============================================================================


def test_authorization_alone_does_not_execute(protocol: dict, tmp_path: Path) -> None:
    """Building the contract and preparing do not produce a validation at all."""

    contract = validator_definition(REPOSITORY_ROOT)
    assert contract["sealed_sample"]["sealed_execution_authorized"] is True
    directory, digest, _ = _prepared(tmp_path)
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_PREPARED
    with pytest.raises(SealedExecutionStateError, match="requires COLLECTED_FROZEN"):
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )


def test_sealed_mode_without_an_authorization_record_refuses(protocol: dict) -> None:
    bundle = _bundle(
        protocol,
        sample={
            "end": SEALED_WINDOW_END_ISO,
            "sample_id": "x",
            "start": SEALED_WINDOW_START_ISO,
        },
    )
    with pytest.raises(SealedExecutionAuthorizationError, match="in-memory evidence"):
        _v2_validate(bundle, execution_mode=v2.EXECUTION_MODE_SEALED)


def test_an_unauthorized_contract_refuses_sealed_mode(
    protocol: dict, monkeypatch
) -> None:
    monkeypatch.setattr(v2, "SEALED_EXECUTION_AUTHORIZED", False)
    with pytest.raises(SealedExecutionAuthorizationError, match="in-memory evidence"):
        _v2_validate(_bundle(protocol), execution_mode=v2.EXECUTION_MODE_SEALED)


def test_an_unauthorized_contract_refuses_to_prepare(
    tmp_path: Path, monkeypatch
) -> None:
    contract = validator_definition(REPOSITORY_ROOT)
    forged = dict(contract)
    forged["sealed_sample"] = dict(
        contract["sealed_sample"], sealed_execution_authorized=False
    )
    monkeypatch.setattr(v2, "validator_definition", lambda root: forged)
    with pytest.raises(
        v1.SealedExecutionNotAuthorizedError, match="does not authorise"
    ):
        prepare_sealed_execution(REPOSITORY_ROOT, authorization_dir=tmp_path / "a")


def test_a_missing_authorization_record_refuses(tmp_path: Path) -> None:
    root = tmp_path / "empty"
    root.mkdir()
    with pytest.raises(SealedExecutionAuthorizationError, match="no .* record exists"):
        read_execution_authorization(
            root,
            validator_definition_sha256="0" * 64,
        )


def test_a_valid_unused_authorization_is_preparable(tmp_path: Path) -> None:
    directory, digest, _ = _prepared(tmp_path)
    record = read_execution_authorization(
        directory, validator_definition_sha256=digest
    )
    assert record["status"] == STATE_PREPARED
    assert record["execution_id"] == derive_execution_id(
        digest, execution_root=directory
    )
    assert record["collection_manifest_digest"] is None
    assert record["evidence_bundle_digest"] is None
    assert record["execution_result_digest"] is None


def test_preparation_populates_no_market_derived_field(tmp_path: Path) -> None:
    record = prepare_sealed_execution(
        REPOSITORY_ROOT, authorization_dir=tmp_path / "a"
    )
    for field in v2.MARKET_DERIVED_AUTHORIZATION_FIELDS:
        assert record[field] is None


@pytest.mark.parametrize(
    "field,value",
    [
        ("validator_definition_sha256", "f" * 64),
        ("bound_protocol_definition_sha256", "e" * 64),
        ("parent_validator_definition_sha256", "d" * 64),
        ("sealed_window_start", "2016-01-01T00:00:00+00:00"),
        ("sealed_window_end", "2020-01-01T00:00:00+00:00"),
        ("candidate_series_id", "SOMETHING_ELSE"),
        ("validator_version", "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V9"),
        ("one_shot_execution", False),
        ("reuse_after_finalized_run", "ALLOW"),
        ("status", STATE_FINALIZED),
    ],
)
def test_a_tampered_authorization_field_refuses(
    tmp_path: Path, field: str, value
) -> None:
    directory, digest, _ = _prepared(tmp_path)
    path = directory / AUTHORIZATION_FILENAME
    record = json.loads(path.read_text())
    record[field] = value
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(
        (SealedExecutionAuthorizationError, SealedExecutionStateError),
        match="REFUSE_TO_RUN",
    ):
        read_execution_authorization(directory, validator_definition_sha256=digest)


def test_a_redigested_authorization_tamper_still_refuses(tmp_path: Path) -> None:
    """Recomputing the record digest does not launder a changed authority."""

    directory, digest, _ = _prepared(tmp_path)
    path = directory / AUTHORIZATION_FILENAME
    record = json.loads(path.read_text())
    record["sealed_window_end"] = "2021-01-01T00:00:00+00:00"
    record["authorization_record_sha256"] = v2._authorization_digest(record)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(SealedExecutionAuthorizationError, match="not the sealed"):
        read_execution_authorization(directory, validator_definition_sha256=digest)


def test_an_unknown_authorization_field_refuses(tmp_path: Path) -> None:
    directory, digest, _ = _prepared(tmp_path)
    path = directory / AUTHORIZATION_FILENAME
    record = json.loads(path.read_text())
    record["shadow"] = 1
    record["authorization_record_sha256"] = v2._authorization_digest(record)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(SealedExecutionAuthorizationError, match="unknown fields"):
        read_execution_authorization(directory, validator_definition_sha256=digest)


def test_a_second_authorization_for_the_same_authority_refuses(
    tmp_path: Path,
) -> None:
    directory, _, _ = _prepared(tmp_path)
    with pytest.raises(SealedExecutionStateError, match="already exists in state"):
        prepare_sealed_execution(REPOSITORY_ROOT, authorization_dir=directory)


def test_the_execution_id_is_derived_from_its_own_authority(tmp_path: Path) -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    root = tmp_path / "root"
    root.mkdir()
    assert derive_execution_id(digest, execution_root=root) == derive_execution_id(
        digest, execution_root=root
    )
    assert derive_execution_id(
        digest, execution_root=root
    ) != derive_execution_id("f" * 64, execution_root=root)
    assert derive_execution_id(digest, execution_root=root).startswith(
        "BTC019_V3_SEALED_EXECUTION_"
    )


# =============================================================================
# 8. the one-shot invariant, across restarts
# =============================================================================


def test_the_state_machine_is_strictly_forward() -> None:
    assert EXECUTION_STATES == (
        STATE_NOT_PREPARED,
        STATE_PREPARED,
        STATE_COLLECTED_FROZEN,
        STATE_EXECUTION_STARTED,
        STATE_FINALIZED,
    )
    order = {name: index for index, name in enumerate(EXECUTION_STATES)}
    for row in LEGAL_EXECUTION_TRANSITIONS:
        assert order[row["to"]] == order[row["from"]] + 1
    assert v2.TERMINAL_EXECUTION_STATES == (STATE_FINALIZED,)


def test_the_hash_bound_contract_carries_exact_history_field_and_artifact_matrices(
    contract: dict,
) -> None:
    control = contract["sealed_execution_control"]
    assert control["exact_state_histories"] == v2.STATE_HISTORY_CONTRACT
    assert control["exact_state_earned_fields"] == v2.STATE_EARNED_FIELD_CONTRACT
    assert control["exact_state_artifact_matrix"] == v2.STATE_ARTIFACT_CONTRACT
    assert control["execution_started_allowed_checkpoints"] == list(
        v2.EXECUTION_STARTED_ALLOWED_CHECKPOINTS
    )
    assert control["started_consumes_authority_permanently"] is True
    assert control["normal_execute_allowed_from"] == STATE_COLLECTED_FROZEN
    assert control["normal_execute_forbidden_from"] == [
        STATE_EXECUTION_STARTED,
        STATE_FINALIZED,
    ]
    assert "fcntl.flock" in control["exclusive_locking_rule"]
    assert "os.replace" in control["atomic_persistence_rule"]
    assert control["supersedes_failed_executor_hash"] == (
        PREVIOUS_CORRECTED_V2_VALIDATOR_SHA256
    )
    assert control["failure_review_commit"] == (
        "45c5e04044d054757b583cbb2aaed5915d196852"
    )
    assert [row["definition_sha256"] for row in control["executor_lineage"]] == [
        FAILED_V2_VALIDATOR_SHA256,
        PREVIOUS_CORRECTED_V2_VALIDATOR_SHA256,
    ]


def test_a_prepared_authority_survives_a_restart(tmp_path: Path) -> None:
    directory, digest, _ = _prepared(tmp_path)
    reread = sealed_execution_status(directory, validator_definition_sha256=digest)
    assert reread == STATE_PREPARED
    # A fresh process cannot re-prepare it either.
    with pytest.raises(SealedExecutionStateError):
        prepare_sealed_execution(REPOSITORY_ROOT, authorization_dir=directory)


def test_a_started_execution_cannot_be_started_again(tmp_path: Path) -> None:
    directory, digest, _ = _started(tmp_path)
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_EXECUTION_STARTED
    with pytest.raises(SealedExecutionStateError, match="not a forward transition"):
        begin_sealed_execution(REPOSITORY_ROOT, authorization_dir=directory)


def test_a_finalized_execution_can_never_run_again(
    protocol: dict, tmp_path: Path
) -> None:
    directory, digest, manifest = _collected(tmp_path)
    result = execute_sealed_validation(
        directory,
        repository_root=REPOSITORY_ROOT,
    )
    assert result["final_verdict"] in VERDICT_VOCABULARY
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_FINALIZED
    for call in (
        lambda: execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        ),
        lambda: begin_sealed_execution(REPOSITORY_ROOT, authorization_dir=directory),
        lambda: prepare_sealed_execution(REPOSITORY_ROOT, authorization_dir=directory),
        lambda: record_frozen_collection_manifest(
            REPOSITORY_ROOT, authorization_dir=directory, manifest=manifest
        ),
    ):
        with pytest.raises(SealedExecutionStateError):
            call()


def test_a_finalized_record_keeps_its_result_digest(
    protocol: dict, tmp_path: Path
) -> None:
    directory, digest, manifest = _collected(tmp_path)
    result = execute_sealed_validation(
        directory,
        repository_root=REPOSITORY_ROOT,
    )
    record = read_execution_authorization(
        directory, validator_definition_sha256=digest
    )
    assert record["execution_result_digest"] == result["result_sha256"]
    assert record["collection_manifest_digest"] == manifest["manifest_sha256"]
    assert record["evidence_bundle_digest"] == result["candidate_evidence_digest"]
    assert [row["to"] for row in record["state_history"]] == [
        STATE_PREPARED,
        STATE_COLLECTED_FROZEN,
        STATE_EXECUTION_STARTED,
        STATE_FINALIZED,
    ]


def test_execution_cannot_start_before_the_manifest_is_frozen(
    tmp_path: Path,
) -> None:
    directory, _, _ = _prepared(tmp_path)
    with pytest.raises(SealedExecutionStateError, match="requires state"):
        begin_sealed_execution(REPOSITORY_ROOT, authorization_dir=directory)


def test_a_collected_run_is_consumed_by_the_single_execution_call(
    protocol: dict, tmp_path: Path
) -> None:
    directory, digest, manifest = _collected(tmp_path)
    result = execute_sealed_validation(
        directory,
        repository_root=REPOSITORY_ROOT,
    )
    assert result["final_verdict"] in VERDICT_VOCABULARY
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_FINALIZED


def test_a_forged_in_memory_authorization_cannot_produce_a_sealed_verdict(
    protocol: dict,
) -> None:
    forged = {
        "status": STATE_EXECUTION_STARTED,
        "execution_id": "forged",
        "collection_manifest_digest": "a" * 64,
    }
    with pytest.raises(SealedExecutionAuthorizationError, match="in-memory evidence"):
        _v2_validate(
            _sealed_bundle(protocol, _manifest(validator_definition_sha256(REPOSITORY_ROOT))),
            execution_mode=v2.EXECUTION_MODE_SEALED,
            sealed_execution_authorization=forged,
        )


def test_a_prebuilt_bundle_is_not_a_live_execution_argument(protocol: dict) -> None:
    bundle = _bundle(protocol)
    with pytest.raises(SealedExecutionAuthorizationError, match="prebuilt evidence"):
        execute_sealed_validation(
            bundle,
            repository_root=REPOSITORY_ROOT,
        )


def test_the_live_api_has_no_caller_supplied_builder_argument(tmp_path: Path) -> None:
    assert "evidence_builder" not in inspect.signature(
        execute_sealed_validation
    ).parameters
    with pytest.raises(TypeError, match="unexpected keyword argument 'evidence_builder'"):
        execute_sealed_validation(
            tmp_path,
            repository_root=REPOSITORY_ROOT,
            evidence_builder=lambda collection: {},
        )


def test_a_self_rehashed_skipped_state_is_refused(tmp_path: Path) -> None:
    directory, digest, _ = _prepared(tmp_path)
    path = directory / AUTHORIZATION_FILENAME
    record = json.loads(path.read_text())
    record["status"] = STATE_EXECUTION_STARTED
    record["state_history"] = [
        dict(row) for row in v2.STATE_HISTORY_CONTRACT[STATE_EXECUTION_STARTED]
    ]
    record["collection_manifest_digest"] = "a" * 64
    record["authorization_record_sha256"] = v2._authorization_digest(record)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(v2.SealedExecutionIntegrityError, match="requires canonical"):
        read_execution_authorization(directory, validator_definition_sha256=digest)


@pytest.mark.parametrize("history_mutation", ["missing", "extra", "duplicate", "wrong_order"])
def test_every_noncanonical_state_history_is_refused(
    tmp_path: Path, history_mutation: str
) -> None:
    directory, digest, _ = _collected(tmp_path)
    path = directory / AUTHORIZATION_FILENAME
    record = json.loads(path.read_text())
    history = list(record["state_history"])
    if history_mutation == "missing":
        history = history[:-1]
    elif history_mutation == "extra":
        history.append(dict(v2.LEGAL_EXECUTION_TRANSITIONS[2]))
    elif history_mutation == "duplicate":
        history.append(dict(history[-1]))
    else:
        history = list(reversed(history))
    record["state_history"] = history
    record["authorization_record_sha256"] = v2._authorization_digest(record)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(SealedExecutionStateError, match="exact legal prefix"):
        read_execution_authorization(directory, validator_definition_sha256=digest)


def test_a_prepared_state_carrying_a_future_field_is_refused(tmp_path: Path) -> None:
    directory, digest, _ = _prepared(tmp_path)
    path = directory / AUTHORIZATION_FILENAME
    record = json.loads(path.read_text())
    record["evidence_bundle_digest"] = "a" * 64
    record["authorization_record_sha256"] = v2._authorization_digest(record)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(SealedExecutionStateError, match="future field"):
        read_execution_authorization(directory, validator_definition_sha256=digest)


def test_a_started_state_cannot_claim_an_unpublished_evidence_digest(
    tmp_path: Path,
) -> None:
    directory, digest, _ = _started(tmp_path)
    path = directory / AUTHORIZATION_FILENAME
    record = json.loads(path.read_text())
    record["evidence_bundle_digest"] = "a" * 64
    record["authorization_record_sha256"] = v2._authorization_digest(record)
    path.write_text(json.dumps(record, indent=2, sort_keys=True) + "\n")
    with pytest.raises(v2.SealedExecutionIntegrityError, match="unreachable"):
        read_execution_authorization(directory, validator_definition_sha256=digest)


def test_copying_an_authority_to_another_root_refuses(tmp_path: Path) -> None:
    directory, digest, _ = _prepared(tmp_path / "source")
    copied = tmp_path / "copied"
    shutil.copytree(directory, copied)
    with pytest.raises(SealedExecutionAuthorizationError, match="execution_root_sha256"):
        read_execution_authorization(copied, validator_definition_sha256=digest)


def test_concurrent_preparation_issues_one_authority(tmp_path: Path) -> None:
    context = multiprocessing.get_context("fork")
    for iteration in range(4):
        execution_root = tmp_path / f"prepare-{iteration}"
        barrier = context.Barrier(2)
        queue = context.Queue()
        processes = [
            context.Process(
                target=_race_prepare_worker,
                args=(REPOSITORY_ROOT, execution_root, barrier, queue),
            )
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(20)
            assert process.exitcode == 0
        outcomes = [queue.get(timeout=2)[0] for _ in processes]
        assert sorted(outcomes) == ["REFUSED", "SUCCESS"]


def test_concurrent_begin_has_exactly_one_consumer(tmp_path: Path) -> None:
    context = multiprocessing.get_context("fork")
    for iteration in range(4):
        directory, digest, _ = _collected(tmp_path / f"begin-{iteration}")
        barrier = context.Barrier(2)
        queue = context.Queue()
        processes = [
            context.Process(
                target=_race_begin_worker,
                args=(REPOSITORY_ROOT, directory, barrier, queue),
            )
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(20)
            assert process.exitcode == 0
        assert sorted(queue.get(timeout=2) for _ in processes) == ["REFUSED", "SUCCESS"]
        record = read_execution_authorization(
            directory, validator_definition_sha256=digest
        )
        assert record["status"] == STATE_EXECUTION_STARTED
        assert [row["to"] for row in record["state_history"]].count(
            STATE_EXECUTION_STARTED
        ) == 1


def test_concurrent_execute_loser_reads_zero_raw_bytes(
    protocol: dict, tmp_path: Path
) -> None:
    context = multiprocessing.get_context("fork")
    for iteration in range(3):
        directory, digest, _ = _collected(tmp_path / f"execute-{iteration}")
        barrier = context.Barrier(2)
        queue = context.Queue()
        processes = [
            context.Process(
                target=_race_execute_worker,
                args=(REPOSITORY_ROOT, directory, barrier, queue),
            )
            for _ in range(2)
        ]
        for process in processes:
            process.start()
        for process in processes:
            process.join(30)
            assert process.exitcode == 0
        outcomes = [queue.get(timeout=2) for _ in processes]
        assert sorted(item[0] for item in outcomes) == ["REFUSED", "SUCCESS"]
        loser = next(item for item in outcomes if item[0] == "REFUSED")
        winner = next(item for item in outcomes if item[0] == "SUCCESS")
        assert loser[1:] == (0, 0)
        assert winner[1:] == (len(SEALED_PROVIDER_IDS), 1)
        assert sealed_execution_status(
            directory, validator_definition_sha256=digest
        ) == STATE_FINALIZED


# =============================================================================
# 9. the sealed sample and its collection contract
# =============================================================================


def test_the_sealed_window_is_exactly_the_frozen_one(contract: dict) -> None:
    assert SEALED_WINDOW_START_ISO == "2015-07-20T21:00:00+00:00"
    assert SEALED_WINDOW_END_ISO == "2019-11-30T23:00:00+00:00"
    assert SEALED_WINDOW_START_ISO == UNTOUCHED_OOS_START.isoformat()
    assert SEALED_WINDOW_END_ISO == UNTOUCHED_OOS_END.isoformat()
    sample = contract["sealed_sample_contract"]
    assert sample["window_start"] == SEALED_WINDOW_START_ISO
    assert sample["window_end"] == SEALED_WINDOW_END_ISO
    assert contract["sealed_sample"]["start"] == SEALED_WINDOW_START_ISO
    assert contract["sealed_sample"]["end"] == SEALED_WINDOW_END_ISO


def test_the_providers_are_inherited_from_the_frozen_policy(contract: dict) -> None:
    assert SEALED_PROVIDER_IDS == ("bitfinex", "bitstamp", "coinbase")
    sample = contract["sealed_sample_contract"]
    assert sample["provider_ids"] == list(SEALED_PROVIDER_IDS)
    assert sample["price_source_policy_version"] == PRICE_SOURCE_POLICY_VERSION
    symbols = {row["provider_id"]: row["instrument_symbol"] for row in
               sample["collection_plan"]}
    assert symbols == {
        "bitfinex": "BTC/USD",
        "bitstamp": "BTC/USD",
        "coinbase": "BTC-USD",
    }


def test_the_collection_sequence_freezes_bytes_before_analysis(
    contract: dict,
) -> None:
    sequence = contract["sealed_sample_contract"]["collection_sequence"]
    assert sequence[0].startswith("collect raw")
    assert "immutable raw files" in sequence[1]
    assert "SHA-256" in sequence[2]
    assert "manifest" in sequence[3]
    assert "freeze" in sequence[4]
    assert sequence[-1].startswith("only then construct the candidate")
    assert contract["sealed_sample_contract"]["manifest_carries_no_strategy_outcome"]


@pytest.mark.parametrize("operation", v2.PRE_FREEZE_ALLOWED_OPERATIONS)
def test_a_technical_integrity_check_is_allowed_before_freeze(operation: str) -> None:
    v2.assert_pre_freeze_operation_allowed(operation)


@pytest.mark.parametrize("operation", v2.PRE_FREEZE_FORBIDDEN_OPERATIONS)
def test_research_is_refused_before_the_manifest_is_frozen(operation: str) -> None:
    with pytest.raises(SealedSampleManifestError, match="REFUSE_TO_RUN"):
        v2.assert_pre_freeze_operation_allowed(operation)


def test_a_well_formed_manifest_validates() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    validated = validate_sealed_sample_manifest(
        manifest,
        execution_id=derive_execution_id(digest, execution_root=REPOSITORY_ROOT),
        validator_definition_sha256=digest,
    )
    assert validated["manifest_sha256"] == manifest["manifest_sha256"]
    assert {row["provider_id"] for row in validated["files"]} == set(
        SEALED_PROVIDER_IDS
    )


def _validate_manifest(manifest: dict, digest: str):
    return validate_sealed_sample_manifest(
        manifest,
        execution_id=derive_execution_id(digest, execution_root=REPOSITORY_ROOT),
        validator_definition_sha256=digest,
    )


def test_a_manifest_naming_a_wrong_provider_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    manifest["files"][0]["provider_id"] = "kraken"
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="canonical provider order"):
        _validate_manifest(manifest, digest)


def test_a_manifest_with_a_duplicate_provider_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    manifest["files"][1] = dict(manifest["files"][0])
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="canonical provider order"):
        _validate_manifest(manifest, digest)


def test_a_manifest_with_a_wrong_window_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest, window_end="2020-06-30T23:00:00+00:00")
    with pytest.raises(SealedExecutionAuthorizationError, match="not the sealed"):
        _validate_manifest(manifest, digest)


def test_a_manifest_with_a_wrong_bar_interval_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest, bar_interval="4h")
    with pytest.raises(SealedSampleManifestError, match="bar interval"):
        _validate_manifest(manifest, digest)


def test_a_manifest_with_a_wrong_timezone_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest, timezone="Europe/London")
    with pytest.raises(SealedSampleManifestError, match="timezone"):
        _validate_manifest(manifest, digest)


def test_a_manifest_missing_provenance_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    manifest["files"][0]["source_provenance"].pop("endpoint")
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="omits required fields"):
        _validate_manifest(manifest, digest)


def test_a_manifest_naming_a_wrong_instrument_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    manifest["files"][0]["source_provenance"]["instrument_symbol"] = "ETH/USD"
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="collected instrument"):
        _validate_manifest(manifest, digest)


def test_a_manifest_whose_own_digest_disagrees_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    manifest["files"][0]["row_count"] += 1
    with pytest.raises(SealedSampleManifestError, match="digests to"):
        _validate_manifest(manifest, digest)


def test_a_file_changed_after_it_was_hashed_refuses(tmp_path: Path) -> None:
    """The recomputation catches a raw file edited after its digest was taken."""

    digest = validator_definition_sha256(REPOSITORY_ROOT)
    root = tmp_path / "repo"
    root.mkdir()
    manifest = _manifest(digest, execution_root=root)
    v2.verify_collected_file_digests(manifest, root)
    path = root / manifest["files"][0]["path"]
    path.write_bytes(path.read_bytes() + b"edited")
    with pytest.raises(SealedSampleManifestError, match="changed after it was hashed"):
        v2.verify_collected_file_digests(manifest, root)


def test_a_manifest_carrying_a_strategy_outcome_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    for field in ("candidate_verdict", "breakout_count", "mfe_summary"):
        manifest = _manifest(digest)
        manifest[field] = 1
        manifest["manifest_sha256"] = manifest_digest(manifest)
        with pytest.raises(SealedSampleManifestError, match="strategy outcome"):
            _validate_manifest(manifest, digest)


def test_a_nested_strategy_outcome_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    manifest["files"][0]["source_provenance"]["swing_high_count"] = 4
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="strategy outcome"):
        _validate_manifest(manifest, digest)


def test_a_mutated_raw_file_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    manifest["files"][0]["raw_mutation_count"] = 1
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="raw mutations"):
        _validate_manifest(manifest, digest)


def test_a_manifest_binding_another_validator_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest, validator_definition_sha256="f" * 64)
    with pytest.raises(SealedSampleManifestError, match="another executing validator"):
        _validate_manifest(manifest, digest)


def test_a_manifest_binding_another_protocol_refuses() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest, bound_protocol_definition_sha256="e" * 64)
    with pytest.raises(SealedSampleManifestError, match="another frozen V3"):
        _validate_manifest(manifest, digest)


def test_observations_outside_the_sealed_window_refuse() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    manifest["files"][0]["last_observation"] = "2020-01-01T00:00:00+00:00"
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="outside the sealed window"):
        _validate_manifest(manifest, digest)


def test_freeze_refuses_a_nonexistent_raw_file(tmp_path: Path) -> None:
    directory, _, manifest = _prepared(tmp_path)
    (directory / manifest["files"][0]["path"]).unlink()
    with pytest.raises(SealedSampleManifestError, match="raw collection files"):
        record_frozen_collection_manifest(
            REPOSITORY_ROOT, authorization_dir=directory, manifest=manifest
        )
    assert not (directory / MANIFEST_FILENAME).exists()


def test_freeze_persists_the_exact_canonical_manifest(tmp_path: Path) -> None:
    directory, digest, manifest = _collected(tmp_path)
    persisted = json.loads((directory / MANIFEST_FILENAME).read_text())
    assert persisted == manifest
    record = read_execution_authorization(
        directory, validator_definition_sha256=digest
    )
    assert record["collection_manifest_digest"] == manifest["manifest_sha256"]


def test_raw_mutation_after_freeze_refuses_before_evidence_building(
    protocol: dict, tmp_path: Path, monkeypatch
) -> None:
    directory, digest, manifest = _collected(tmp_path)
    path = directory / manifest["files"][0]["path"]
    path.write_bytes(path.read_bytes() + b"mutation")
    calls = []
    monkeypatch.setattr(
        v2,
        "_evidence_builder_invocation_point",
        lambda builder, collection: calls.append(collection),
    )
    with pytest.raises(SealedSampleManifestError, match="changed after it was hashed"):
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )
    assert calls == []
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_EXECUTION_STARTED


def test_deleted_raw_file_after_freeze_refuses_before_evidence_building(
    protocol: dict, tmp_path: Path, monkeypatch
) -> None:
    directory, digest, manifest = _collected(tmp_path)
    (directory / manifest["files"][0]["path"]).unlink()
    calls = []
    monkeypatch.setattr(
        v2,
        "_evidence_builder_invocation_point",
        lambda builder, collection: calls.append(collection),
    )
    with pytest.raises(SealedSampleManifestError, match="raw collection files"):
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )
    assert calls == []
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_EXECUTION_STARTED


def test_provider_file_swap_refuses_before_evidence_building(
    protocol: dict, tmp_path: Path, monkeypatch
) -> None:
    directory, _, manifest = _collected(tmp_path)
    left = directory / manifest["files"][0]["path"]
    right = directory / manifest["files"][1]["path"]
    left_bytes, right_bytes = left.read_bytes(), right.read_bytes()
    left.write_bytes(right_bytes)
    right.write_bytes(left_bytes)
    calls = []
    monkeypatch.setattr(
        v2,
        "_evidence_builder_invocation_point",
        lambda builder, collection: calls.append(collection),
    )
    with pytest.raises(SealedSampleManifestError, match="changed after it was hashed"):
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )
    assert calls == []


def test_same_inode_for_two_providers_refuses(tmp_path: Path) -> None:
    directory, _, manifest = _prepared(tmp_path)
    first = directory / manifest["files"][0]["path"]
    second = directory / manifest["files"][1]["path"]
    second.unlink()
    os.link(first, second)
    manifest["files"][1].update(
        {
            key: manifest["files"][0][key]
            for key in (
                "byte_count",
                "duplicate_interval_count",
                "duplicate_intervals",
                "first_observation",
                "last_observation",
                "missing_interval_count",
                "missing_intervals",
                "row_count",
                "sha256",
            )
        }
    )
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="same raw file inode"):
        record_frozen_collection_manifest(
            REPOSITORY_ROOT, authorization_dir=directory, manifest=manifest
        )


def test_extra_raw_file_refuses_freeze(tmp_path: Path) -> None:
    directory, _, manifest = _prepared(tmp_path)
    (directory / v2.RAW_COLLECTION_DIRNAME / "extra.jsonl.gz").write_bytes(b"x")
    with pytest.raises(SealedSampleManifestError, match="raw collection files"):
        record_frozen_collection_manifest(
            REPOSITORY_ROOT, authorization_dir=directory, manifest=manifest
        )


def test_unsafe_symlink_refuses_freeze(tmp_path: Path) -> None:
    directory, _, manifest = _prepared(tmp_path)
    target = directory / manifest["files"][0]["path"]
    payload = directory / "outside.gz"
    target.rename(payload)
    target.symlink_to(payload)
    with pytest.raises(SealedSampleManifestError, match="safe regular file"):
        record_frozen_collection_manifest(
            REPOSITORY_ROOT, authorization_dir=directory, manifest=manifest
        )


def test_path_traversal_and_self_consistent_manifest_tamper_refuse() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    manifest["files"][0]["path"] = "../bitfinex.jsonl.gz"
    manifest["files"][0]["sha256"] = "f" * 64
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="raw path must be"):
        _validate_manifest(manifest, digest)


@pytest.mark.parametrize("operation", ["delete", "corrupt"])
def test_missing_or_corrupt_persisted_manifest_refuses_execution(
    protocol: dict, tmp_path: Path, monkeypatch, operation: str
) -> None:
    directory, _, manifest = _collected(tmp_path)
    path = directory / MANIFEST_FILENAME
    if operation == "delete":
        path.unlink()
    else:
        path.write_text("not-json")
    calls = []
    monkeypatch.setattr(
        v2,
        "_evidence_builder_invocation_point",
        lambda builder, collection: calls.append(collection),
    )
    with pytest.raises((v2.SealedExecutionIntegrityError, SealedExecutionAuthorizationError)):
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )
    assert calls == []


@pytest.mark.parametrize(
    "mutation",
    [
        "changed_row",
        "changed_digest",
        "provider_file_association",
        "raw_digest_declaration",
    ],
)
def test_post_start_manifest_mutation_refuses_before_raw_or_builder(
    tmp_path: Path, monkeypatch, mutation: str
) -> None:
    directory, digest, _ = _collected(tmp_path)
    manifest_path = directory / MANIFEST_FILENAME
    raw_reads = []
    builder_calls = []
    original_read = v2._read_regular_file_under_root

    def watched_read(*args, **kwargs):
        raw_reads.append(args)
        return original_read(*args, **kwargs)

    def mutate_after_start(point: str) -> None:
        if point != "after_execution_started_before_raw_read":
            return
        persisted = json.loads(manifest_path.read_text())
        if mutation == "changed_row":
            persisted["files"][0]["source_provenance"]["request_count"] += 1
        elif mutation == "changed_digest":
            persisted["manifest_sha256"] = "f" * 64
        elif mutation == "provider_file_association":
            persisted["files"][0]["path"], persisted["files"][1]["path"] = (
                persisted["files"][1]["path"],
                persisted["files"][0]["path"],
            )
            persisted["manifest_sha256"] = manifest_digest(persisted)
        else:
            persisted["files"][0]["sha256"] = "f" * 64
            persisted["manifest_sha256"] = manifest_digest(persisted)
        manifest_path.write_text(json.dumps(persisted, indent=2, sort_keys=True) + "\n")

    monkeypatch.setattr(v2, "_crash_injection_point", mutate_after_start)
    monkeypatch.setattr(v2, "_read_regular_file_under_root", watched_read)
    monkeypatch.setattr(
        v2,
        "_evidence_builder_invocation_point",
        lambda builder, collection: builder_calls.append(collection),
    )

    with pytest.raises((SealedSampleManifestError, v2.SealedExecutionIntegrityError)):
        execute_sealed_validation(directory, repository_root=REPOSITORY_ROOT)

    assert raw_reads == []
    assert builder_calls == []
    authority = json.loads((directory / AUTHORIZATION_FILENAME).read_text())
    assert authority["status"] == STATE_EXECUTION_STARTED
    assert authority["validator_definition_sha256"] == digest


def test_raw_technical_metadata_is_verified_from_bytes(tmp_path: Path) -> None:
    directory, _, manifest = _prepared(tmp_path)
    manifest["files"][0]["row_count"] += 1
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="row_count"):
        record_frozen_collection_manifest(
            REPOSITORY_ROOT, authorization_dir=directory, manifest=manifest
        )


def test_wrong_exchange_refuses_manifest() -> None:
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    manifest = _manifest(digest)
    manifest["files"][0]["source_provenance"]["exchange"] = "wrong"
    manifest["manifest_sha256"] = manifest_digest(manifest)
    with pytest.raises(SealedSampleManifestError, match="another exchange"):
        _validate_manifest(manifest, digest)


# =============================================================================
# 10. input provenance and the terminal result
# =============================================================================


def test_the_fixed_builder_identity_and_implementation_are_hash_bound(
    contract: dict,
) -> None:
    definition = v2.fixed_evidence_builder_definition()
    control = contract["sealed_execution_control"]
    assert control["evidence_builder"] == definition
    assert definition["builder_module"] == v2.SEALED_EVIDENCE_BUILDER_MODULE
    assert definition["builder_function"] == v2.SEALED_EVIDENCE_BUILDER_FUNCTION
    assert definition["builder_version"] == v2.SEALED_EVIDENCE_BUILDER_VERSION
    assert definition["builder_input_type"] == "VerifiedRawCollection"
    assert definition["builder_definition_sha256"] == (
        v2.SEALED_EVIDENCE_BUILDER_DEFINITION_SHA256
    )


def test_fixed_builder_implementation_drift_refuses_without_contract_update(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        v2._evidence_owner,
        "build_sealed_evidence",
        lambda collection: {},
    )
    with pytest.raises(ValidatorBindingError, match="function object moved"):
        validator_definition(REPOSITORY_ROOT)


def test_live_execution_invokes_the_fixed_builder_once_with_verified_raw(
    tmp_path: Path, monkeypatch
) -> None:
    directory, _, manifest = _collected(tmp_path)
    calls = []

    def observe(builder, collection) -> None:
        calls.append((builder, collection))

    monkeypatch.setattr(v2, "_evidence_builder_invocation_point", observe)
    result = execute_sealed_validation(directory, repository_root=REPOSITORY_ROOT)
    assert result["final_verdict"] in VERDICT_VOCABULARY
    assert len(calls) == 1
    builder, collection = calls[0]
    assert builder is v2._evidence_owner.build_sealed_evidence
    assert isinstance(collection, v2.VerifiedRawCollection)
    assert collection.manifest["manifest_sha256"] == manifest["manifest_sha256"]

    artifact = json.loads((directory / EVIDENCE_FILENAME).read_text())
    assert artifact["evidence_builder_module"] == v2.SEALED_EVIDENCE_BUILDER_MODULE
    assert artifact["evidence_builder_function"] == v2.SEALED_EVIDENCE_BUILDER_FUNCTION
    assert artifact["evidence_builder_version"] == v2.SEALED_EVIDENCE_BUILDER_VERSION
    assert artifact["evidence_builder_definition_sha256"] == (
        v2.SEALED_EVIDENCE_BUILDER_DEFINITION_SHA256
    )


def test_the_result_publishes_every_declared_field(
    protocol: dict, tmp_path: Path
) -> None:
    directory, _, manifest = _collected(tmp_path)
    result = execute_sealed_validation(
        directory,
        repository_root=REPOSITORY_ROOT,
    )
    assert set(result) == set(SEALED_EXECUTION_RESULT_FIELDS)
    assert result["schema_version"] == SEALED_EXECUTION_RESULT_SCHEMA_VERSION
    assert result["bound_protocol_definition_sha256"] == FROZEN_V3_DEFINITION_SHA256
    assert result["parent_validator_definition_sha256"] == (
        CERTIFIED_V1_VALIDATOR_SHA256
    )
    assert result["validator_definition_sha256"] == validator_definition_sha256(
        REPOSITORY_ROOT
    )
    assert result["sealed_sample_manifest_sha256"] == manifest["manifest_sha256"]
    assert result["final_verdict"] in VERDICT_VOCABULARY
    assert set(result["seven_hard_requirements"]) == set(HARD_REQUIREMENT_IDS)
    assert result["primary_reason"] in result["all_reasons"]
    assert [row["comparison_id"] for row in result["candidate_pair_certifications"]] == (
        list(GATE_PAIRS)
    )
    assert [
        row["comparison_id"] for row in result["transfer_guard_pair_certifications"]
    ] == list(GUARD_PAIRS)


def test_evidence_is_durable_before_certified_validation(
    tmp_path: Path, monkeypatch
) -> None:
    directory, _, _ = _collected(tmp_path)
    original_validate = v2._validate_v3_candidate_core
    observations = []

    def validate_after_evidence(*args, **kwargs):
        evidence = json.loads((directory / EVIDENCE_FILENAME).read_text())
        authority = json.loads((directory / AUTHORIZATION_FILENAME).read_text())
        assert authority["evidence_bundle_digest"] == evidence[
            "evidence_bundle_digest"
        ]
        observations.append("evidence_durable")
        return original_validate(*args, **kwargs)

    monkeypatch.setattr(v2, "_validate_v3_candidate_core", validate_after_evidence)
    execute_sealed_validation(directory, repository_root=REPOSITORY_ROOT)
    assert observations == ["evidence_durable"]


def test_the_sealed_record_says_it_opened_the_sample(
    protocol: dict, tmp_path: Path
) -> None:
    directory, _, manifest = _collected(tmp_path)
    result = execute_sealed_validation(
        directory,
        repository_root=REPOSITORY_ROOT,
    )
    sealed = result["validation_record"]["sealed_execution"]
    assert sealed["this_record_opened_the_sealed_sample"] is True
    assert sealed["execution_state"] == STATE_FINALIZED
    assert sealed["one_shot_execution"] is True
    assert sealed["sealed_sample_manifest_sha256"] == manifest["manifest_sha256"]
    assert result["validation_record"]["execution_mode"] == v2.EXECUTION_MODE_SEALED


def test_a_dry_run_record_says_it_opened_nothing(protocol: dict) -> None:
    record = _v2_validate(_bundle(protocol)).as_record()
    sealed = record["sealed_execution"]
    assert sealed["this_record_opened_the_sealed_sample"] is False
    assert sealed["execution_id"] is None
    assert sealed["sealed_sample_manifest_sha256"] is None
    assert record["execution_mode"] == v2.EXECUTION_MODE_DRY_RUN


@pytest.mark.parametrize(
    "point,evidence_present",
    [
        ("after_execution_started_before_raw_read", False),
        ("after_first_raw_file_read", False),
        ("after_evidence_persisted", True),
        ("after_result_temp_write", True),
    ],
)
def test_crash_before_result_permanently_consumes_authority(
    protocol: dict,
    tmp_path: Path,
    monkeypatch,
    point: str,
    evidence_present: bool,
) -> None:
    directory, digest, manifest = _collected(tmp_path)
    calls = []

    def crash(actual: str) -> None:
        if actual == point:
            raise RuntimeError(f"CRASH:{point}")

    monkeypatch.setattr(v2, "_crash_injection_point", crash)
    monkeypatch.setattr(
        v2,
        "_evidence_builder_invocation_point",
        lambda builder, collection: calls.append(collection),
    )
    with pytest.raises(RuntimeError, match=f"CRASH:{point}"):
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_EXECUTION_STARTED
    assert (directory / EVIDENCE_FILENAME).exists() is evidence_present
    assert not (directory / RESULT_FILENAME).exists()
    before_retry = len(calls)
    with pytest.raises(SealedExecutionStateError, match="consumed execution cannot retry"):
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )
    assert len(calls) == before_retry
    monkeypatch.setattr(v2, "_crash_injection_point", lambda _: None)
    recovery = recover_sealed_execution(
        REPOSITORY_ROOT, execution_root=directory
    )
    assert recovery["operational_state"] == v2.RECOVERY_INTERRUPTED_NO_RESULT
    assert recovery["scientific_verdict"] is None
    assert recovery["normal_retry_permitted"] is False
    assert recovery["raw_reopen_permitted"] is False


def test_crash_after_prepared_write_leaves_one_prepared_authority(
    tmp_path: Path, monkeypatch
) -> None:
    directory = tmp_path / "prepared-crash"

    def crash(actual: str) -> None:
        if actual == "after_prepared_write":
            raise RuntimeError("prepared crash")

    monkeypatch.setattr(v2, "_crash_injection_point", crash)
    with pytest.raises(RuntimeError, match="prepared crash"):
        prepare_sealed_execution(REPOSITORY_ROOT, authorization_dir=directory)
    monkeypatch.setattr(v2, "_crash_injection_point", lambda _: None)
    digest = validator_definition_sha256(REPOSITORY_ROOT)
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_PREPARED
    with pytest.raises(SealedExecutionStateError, match="already exists"):
        prepare_sealed_execution(REPOSITORY_ROOT, authorization_dir=directory)


def test_crash_after_collected_frozen_leaves_runnable_frozen_authority(
    tmp_path: Path, monkeypatch
) -> None:
    directory, digest, manifest = _prepared(tmp_path)

    def crash(actual: str) -> None:
        if actual == "after_collected_frozen":
            raise RuntimeError("collected crash")

    monkeypatch.setattr(v2, "_crash_injection_point", crash)
    with pytest.raises(RuntimeError, match="collected crash"):
        record_frozen_collection_manifest(
            REPOSITORY_ROOT, authorization_dir=directory, manifest=manifest
        )
    monkeypatch.setattr(v2, "_crash_injection_point", lambda _: None)
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_COLLECTED_FROZEN


@pytest.mark.parametrize(
    "point",
    [
        "after_result_atomic_publish",
        "after_result_digest_persisted_before_finalized",
    ],
)
def test_recovery_finalizes_a_durable_result_without_raw_reread(
    protocol: dict, tmp_path: Path, monkeypatch, point: str
) -> None:
    directory, digest, manifest = _collected(tmp_path)

    def crash(actual: str) -> None:
        if actual == point:
            raise RuntimeError(f"CRASH:{point}")

    monkeypatch.setattr(v2, "_crash_injection_point", crash)
    with pytest.raises(RuntimeError, match=f"CRASH:{point}"):
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )
    assert (directory / EVIDENCE_FILENAME).exists()
    assert (directory / RESULT_FILENAME).exists()
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_EXECUTION_STARTED
    monkeypatch.setattr(v2, "_crash_injection_point", lambda _: None)
    monkeypatch.setattr(
        v2,
        "verify_collected_file_digests",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("recovery reopened raw bytes")
        ),
    )
    recovered = recover_sealed_execution(
        REPOSITORY_ROOT, execution_root=directory
    )
    assert recovered["operational_state"] == v2.RECOVERY_FINALIZED_EXISTING_RESULT
    assert recovered["raw_reopen_permitted"] is False
    assert recovered["result"]["final_verdict"] in VERDICT_VOCABULARY
    assert sealed_execution_status(
        directory, validator_definition_sha256=digest
    ) == STATE_FINALIZED


def test_fixed_builder_interruption_is_operational_not_scientific(
    protocol: dict, tmp_path: Path, monkeypatch
) -> None:
    directory, digest, manifest = _collected(tmp_path)

    def interrupt_fixed_builder(builder, collection):
        raise RuntimeError("synthetic fixed-builder interruption")

    monkeypatch.setattr(
        v2, "_evidence_builder_invocation_point", interrupt_fixed_builder
    )
    with pytest.raises(RuntimeError, match="synthetic fixed-builder interruption"):
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )
    record = read_execution_authorization(
        directory, validator_definition_sha256=digest
    )
    assert record["status"] == STATE_EXECUTION_STARTED
    assert record["execution_result_digest"] is None
    recovered = recover_sealed_execution(
        REPOSITORY_ROOT, execution_root=directory
    )
    assert recovered["scientific_verdict"] is None


def test_crash_after_finalized_is_read_only(
    protocol: dict, tmp_path: Path, monkeypatch
) -> None:
    directory, _, manifest = _collected(tmp_path)

    def crash(actual: str) -> None:
        if actual == "after_finalized":
            raise RuntimeError("CRASH:after_finalized")

    monkeypatch.setattr(v2, "_crash_injection_point", crash)
    with pytest.raises(RuntimeError, match="after_finalized"):
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )
    monkeypatch.setattr(v2, "_crash_injection_point", lambda _: None)
    recovered = recover_sealed_execution(
        REPOSITORY_ROOT, execution_root=directory
    )
    assert recovered["operational_state"] == v2.RECOVERY_ALREADY_FINALIZED


def test_manifest_publication_crash_can_only_resume_the_same_freeze(
    tmp_path: Path, monkeypatch
) -> None:
    directory, digest, manifest = _prepared(tmp_path)

    def crash(actual: str) -> None:
        if actual == "after_manifest_persisted_before_collected_frozen":
            raise RuntimeError("manifest publication crash")

    monkeypatch.setattr(v2, "_crash_injection_point", crash)
    with pytest.raises(RuntimeError, match="publication crash"):
        record_frozen_collection_manifest(
            REPOSITORY_ROOT, authorization_dir=directory, manifest=manifest
        )
    with pytest.raises(v2.SealedExecutionIntegrityError, match="PREPARED"):
        read_execution_authorization(directory, validator_definition_sha256=digest)
    changed = json.loads(json.dumps(manifest))
    changed["files"][0]["source_provenance"]["request_count"] += 1
    changed["manifest_sha256"] = manifest_digest(changed)
    monkeypatch.setattr(v2, "_crash_injection_point", lambda _: None)
    with pytest.raises(v2.SealedExecutionIntegrityError, match="orphan manifest differs"):
        record_frozen_collection_manifest(
            REPOSITORY_ROOT, authorization_dir=directory, manifest=changed
        )
    frozen = record_frozen_collection_manifest(
        REPOSITORY_ROOT, authorization_dir=directory, manifest=manifest
    )
    assert frozen["status"] == STATE_COLLECTED_FROZEN


def test_finalized_result_restores_across_restart(
    protocol: dict, tmp_path: Path
) -> None:
    directory, _, manifest = _collected(tmp_path)
    result = execute_sealed_validation(
        directory,
        repository_root=REPOSITORY_ROOT,
    )
    assert read_finalized_result(
        REPOSITORY_ROOT, execution_root=directory
    ) == result


def test_redigested_result_semantic_tamper_refuses_restore(
    protocol: dict, tmp_path: Path
) -> None:
    directory, digest, manifest = _collected(tmp_path)
    execute_sealed_validation(
        directory,
        repository_root=REPOSITORY_ROOT,
    )
    result_path = directory / RESULT_FILENAME
    result = json.loads(result_path.read_text())
    result["final_verdict"] = (
        VERDICT_FAIL if result["final_verdict"] != VERDICT_FAIL else VERDICT_PASS
    )
    result["result_sha256"] = v2._digest(
        {key: value for key, value in result.items() if key != "result_sha256"}
    )
    result_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    authorization_path = directory / AUTHORIZATION_FILENAME
    authorization = json.loads(authorization_path.read_text())
    authorization["execution_result_digest"] = result["result_sha256"]
    authorization["authorization_record_sha256"] = v2._authorization_digest(
        authorization
    )
    authorization_path.write_text(
        json.dumps(authorization, indent=2, sort_keys=True) + "\n"
    )
    with pytest.raises(v2.SealedExecutionIntegrityError, match="do not reproduce"):
        read_finalized_result(REPOSITORY_ROOT, execution_root=directory)


def test_the_terminal_outcomes_are_documented(contract: dict) -> None:
    outcomes = contract["sealed_execution_control"]["terminal_outcomes"]
    assert set(outcomes) == set(VERDICT_VOCABULARY)
    assert "PRICE_SOURCE_POLICY_V2" in outcomes[VERDICT_PASS]
    assert "rejected" in outcomes[VERDICT_FAIL]
    assert "unresolved" in outcomes[VERDICT_INSUFFICIENT]
    rule = contract["sealed_execution_control"]["terminal_outcome_rule"]
    assert "does not promise" not in rule
    assert "no post-sealed tuning" in rule.lower()
    for text in outcomes.values():
        assert "retuned" in text or "PRICE_SOURCE_POLICY_V2" in text


def test_no_result_dependent_behaviour_is_declared(contract: dict) -> None:
    statement = contract["sealed_execution_control"]["no_result_dependent_behaviour"]
    assert "widens the window" in statement
    assert "extends the sample" in statement


def test_post_review_immutability_is_declared(contract: dict) -> None:
    statement = contract["sealed_execution_control"]["post_review_immutability"]
    assert "no edit" in statement
    assert "reviewed validator_definition_sha256" in statement


# =============================================================================
# 11. hash completeness -- every semantic tamper moves the hash or is refused
# =============================================================================


def _rebuild_or_refuse() -> str | None:
    try:
        return validator_definition_sha256(REPOSITORY_ROOT)
    except ValidatorError:
        return None


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("SEALED_EXECUTION_AUTHORIZED", False),
        ("ONE_SHOT_EXECUTION", False),
        ("REUSE_AFTER_FINALIZED_RUN", "ALLOW"),
        ("ONE_SHOT_RULE", "the sample may be reopened at will"),
        ("ONE_SHOT_RULE_ID", "ANY_NUMBER_OF_OPENINGS_V1"),
        ("PARENT_VALIDATOR_DEFINITION_SHA256", "f" * 64),
        ("BOUND_PROTOCOL_DEFINITION_SHA256_EXPECTED", "e" * 64),
        ("SEALED_WINDOW_START_ISO", "2014-01-01T00:00:00+00:00"),
        ("SEALED_WINDOW_END_ISO", "2020-12-31T23:00:00+00:00"),
        ("EXECUTION_STATES", ("NOT_PREPARED", "FINALIZED")),
        ("MANIFEST_SCHEMA_VERSION", "BTC019_V3_SEALED_SAMPLE_MANIFEST_V9"),
        ("MANIFEST_REQUIRED_KEYS", ("manifest_version",)),
        ("SEALED_EVIDENCE_BUILDER_VERSION", "OTHER_BUILDER_V1"),
        ("SEALED_EVIDENCE_BUILDER_MODULE", "other.builder"),
        ("SEALED_EVIDENCE_BUILDER_FUNCTION", "other_builder"),
        ("SEALED_EVIDENCE_BUILDER_DEFINITION_SHA256", "d" * 64),
        ("POST_START_MANIFEST_VALIDATION_RULE_ID", "OTHER_RULE_V1"),
        ("POST_START_MANIFEST_VALIDATION_RULE", "skip manifest validation"),
        ("MANIFEST_DIGEST_EQUALITY_RULE_ID", "OTHER_EQUALITY_V1"),
        ("MANIFEST_DIGEST_EQUALITY_RULE", "trust any manifest digest"),
        (
            "SEALED_EXECUTION_RESULT_SCHEMA_VERSION",
            "BTC019_V3_SEALED_VALIDATION_RESULT_V9",
        ),
        ("SEALED_EXECUTION_RESULT_FIELDS", ("final_verdict",)),
        ("SEALED_PROVIDER_IDS", ("bitstamp",)),
        ("PRE_FREEZE_ALLOWED_OPERATIONS", ("anything",)),
        ("TERMINAL_OUTCOME_RULE", "BTC-019 must pass"),
        ("VALIDATOR_RECORD_SCHEMA_VERSION", "SOMETHING_ELSE_V1"),
    ],
)
def test_a_semantic_tamper_moves_the_hash_or_is_refused(
    monkeypatch, attribute: str, value
) -> None:
    baseline = validator_definition_sha256(REPOSITORY_ROOT)
    monkeypatch.setattr(v2, attribute, value)
    tampered = _rebuild_or_refuse()
    assert tampered != baseline, f"{attribute} moved nothing and was not refused"


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("VERDICT_VOCABULARY", ("PASS", "FAIL")),
        ("HARD_REQUIREMENT_IDS", ("structural_state_hard_gate",)),
        ("REASON_PRECEDENCE", ("ALL_HARD_REQUIREMENTS_SATISFIED",)),
        ("WILSON_BOUNDARY_VECTORS", ()),
        ("VERDICT_PRECEDENCE_RULE", "always PASS"),
    ],
)
def test_a_parent_semantic_tamper_refuses_the_successor(
    monkeypatch, attribute: str, value
) -> None:
    """A changed parent semantic moves the parent hash, so V2 refuses to build."""

    monkeypatch.setattr(v1, attribute, value)
    with pytest.raises(ValidatorError):
        validator_definition(REPOSITORY_ROOT)


def test_the_persisted_contract_verifies(tmp_path: Path) -> None:
    persisted = verify_sealed_executor_artifacts(
        REPOSITORY_ROOT, REPOSITORY_ROOT / SEALED_EXECUTOR_OUTPUT_NAMESPACE
    )
    assert persisted["validator_definition_sha256"] == validator_definition_sha256(
        REPOSITORY_ROOT
    )


@pytest.mark.parametrize(
    "path,value",
    [
        (("sealed_sample", "sealed_execution_authorized"), False),
        (("sealed_sample", "one_shot_execution"), False),
        (("sealed_sample", "reuse_after_finalized_run"), "ALLOW"),
        (("sealed_sample", "start"), "2014-01-01T00:00:00+00:00"),
        (("parent_validator", "validator_definition_sha256"), "f" * 64),
        (("binding", "bound_protocol_definition_sha256"), "e" * 64),
        (("sealed_execution_control", "one_shot_rule_id"), "OPEN_FOREVER_V1"),
        (("sealed_execution_control", "result_schema_version"), "OTHER_V1"),
        (("sealed_execution_control", "evidence_builder_module"), "other.builder"),
        (("sealed_execution_control", "evidence_builder_function"), "other_builder"),
        (
            ("sealed_execution_control", "evidence_builder_definition_sha256"),
            "d" * 64,
        ),
        (
            ("sealed_sample_contract", "collection_manifest_schema_version"),
            "OTHER_V1",
        ),
        (("validator_version",), "BTC_REFERENCE_COMPOSITE_V3_VALIDATOR_V1"),
        (("verdict_vocabulary",), ["PASS"]),
    ],
)
def test_a_persisted_contract_tamper_is_refused(
    tmp_path: Path, path: tuple, value
) -> None:
    write_sealed_executor_artifacts(REPOSITORY_ROOT, tmp_path)
    target = tmp_path / VALIDATOR_DEFINITION_FILENAME
    payload = json.loads(target.read_text())
    node = payload
    for key in path[:-1]:
        node = node[key]
    node[path[-1]] = value
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValidatorError):
        verify_sealed_executor_artifacts(REPOSITORY_ROOT, tmp_path)


def test_a_redigested_persisted_tamper_is_still_caught(tmp_path: Path) -> None:
    """`verify_` recomputes from the repository, so re-digesting does not help."""

    write_sealed_executor_artifacts(REPOSITORY_ROOT, tmp_path)
    target = tmp_path / VALIDATOR_DEFINITION_FILENAME
    payload = json.loads(target.read_text())
    payload["soft_requirements"]["limit"] = "0.99"
    body = {
        key: value
        for key, value in payload.items()
        if key != "validator_definition_sha256"
    }
    payload["validator_definition_sha256"] = v2._digest(body)
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    with pytest.raises(ValidatorError, match="does not recompute"):
        verify_sealed_executor_artifacts(REPOSITORY_ROOT, tmp_path)


# =============================================================================
# 12. determinism and reproducibility
# =============================================================================


def test_the_hash_is_stable_across_repeated_builds() -> None:
    assert validator_definition_sha256(REPOSITORY_ROOT) == (
        validator_definition_sha256(REPOSITORY_ROOT)
    )


def test_the_working_directory_cannot_change_the_hash(
    tmp_path: Path, monkeypatch
) -> None:
    expected = validator_definition_sha256(REPOSITORY_ROOT)
    monkeypatch.chdir(tmp_path)
    assert validator_definition_sha256(REPOSITORY_ROOT) == expected


def test_the_ambient_decimal_context_cannot_change_a_result(protocol: dict) -> None:
    baseline = _v2_validate(_bundle(protocol)).as_record()
    expected = validator_definition_sha256(REPOSITORY_ROOT)
    with localcontext(Context(prec=6)):
        assert _v2_validate(_bundle(protocol)).as_record() == baseline
        assert validator_definition_sha256(REPOSITORY_ROOT) == expected


def test_the_hash_survives_a_process_restart_and_hash_seed() -> None:
    script = (
        "from pathlib import Path;"
        "from btc_predictor.research.reference_composite_v3_sealed_executor import "
        "validator_definition_sha256;"
        "print(validator_definition_sha256(Path('.')))"
    )
    digests = []
    for seed in ("0", "12345"):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            check=True,
            cwd=REPOSITORY_ROOT,
            env={**os.environ, "PYTHONHASHSEED": seed},
            text=True,
        )
        digests.append(result.stdout.strip())
    assert digests[0] == digests[1] == validator_definition_sha256(REPOSITORY_ROOT)


def test_provider_and_dictionary_order_cannot_change_a_sealed_result(
    protocol: dict, tmp_path: Path
) -> None:
    """The same frozen inputs give a byte-identical semantic result."""

    def _run(directory: str) -> dict:
        auth, _, _ = _collected(tmp_path / directory)
        return execute_sealed_validation(
            auth,
            repository_root=REPOSITORY_ROOT,
        )

    straight = _run("first")
    repeated = _run("second")
    for field in (
        "final_verdict",
        "primary_reason",
        "all_reasons",
        "hard_requirement_outcomes",
        "seven_hard_requirements",
        "candidate_pair_certifications",
        "transfer_guard_pair_certifications",
        "soft_gate",
        "diagnostics",
        "inherited_gate_outcomes",
    ):
        assert straight[field] == repeated[field]


def test_the_written_artifacts_are_deterministic_ascii(tmp_path: Path) -> None:
    first, second = tmp_path / "first", tmp_path / "second"
    write_sealed_executor_artifacts(REPOSITORY_ROOT, first)
    write_sealed_executor_artifacts(REPOSITORY_ROOT, second)
    for name in (
        VALIDATOR_DEFINITION_FILENAME,
        v2.SEMANTIC_DELTA_FILENAME,
        v2.SEALED_EXECUTOR_REPORT_FILENAME,
    ):
        left = (first / name).read_bytes()
        assert left == (second / name).read_bytes()
        assert left.decode("ascii")


def test_the_contract_carries_no_wall_clock_or_filesystem_path(
    contract: dict,
) -> None:
    rendered = json.dumps(contract)
    assert str(REPOSITORY_ROOT) not in rendered
    assert "/home/" not in rendered


def test_the_authorization_record_carries_no_wall_clock(tmp_path: Path) -> None:
    """Deterministic except for what the run itself earns."""

    first = prepare_sealed_execution(
        REPOSITORY_ROOT, authorization_dir=tmp_path / "a"
    )
    second = prepare_sealed_execution(
        REPOSITORY_ROOT, authorization_dir=tmp_path / "b"
    )
    for record in (first, second):
        record.pop("authorization_record_sha256")
        record.pop("execution_id")
        record.pop("execution_root_sha256")
    assert first == second


# =============================================================================
# 13. the sealed sample is never collected, opened or inspected here
# =============================================================================


def test_no_sealed_history_exists_on_disk() -> None:
    for path in (REPOSITORY_ROOT / "data").rglob("*"):
        if not path.is_file():
            continue
        for year in SEALED_YEARS:
            if year in path.name:
                pytest.fail(f"sealed-window history is present at {path}")


def test_the_whole_execution_surface_reads_no_market_data(
    protocol: dict, tmp_path: Path, monkeypatch
) -> None:
    """Watch every filesystem read every public entry point performs."""

    import builtins
    import gzip

    opened: list[str] = []
    real_open = builtins.open
    real_read_text = Path.read_text
    real_read_bytes = Path.read_bytes
    real_gzip_open = gzip.open

    def watched_open(file, *args, **kwargs):
        opened.append(str(file))
        return real_open(file, *args, **kwargs)

    def watched_read_text(self, *args, **kwargs):
        opened.append(str(self))
        return real_read_text(self, *args, **kwargs)

    def watched_read_bytes(self, *args, **kwargs):
        opened.append(str(self))
        return real_read_bytes(self, *args, **kwargs)

    def watched_gzip_open(filename, *args, **kwargs):
        opened.append(str(filename))
        return real_gzip_open(filename, *args, **kwargs)

    monkeypatch.setattr(builtins, "open", watched_open)
    monkeypatch.setattr(Path, "read_text", watched_read_text)
    monkeypatch.setattr(Path, "read_bytes", watched_read_bytes)
    monkeypatch.setattr(gzip, "open", watched_gzip_open)

    validator_definition(REPOSITORY_ROOT)
    semantic_delta(REPOSITORY_ROOT)
    verify_sealed_executor_artifacts(
        REPOSITORY_ROOT, REPOSITORY_ROOT / SEALED_EXECUTOR_OUTPUT_NAMESPACE
    )
    _v2_validate(_bundle(protocol))
    directory, digest, manifest = _collected(tmp_path)
    execute_sealed_validation(
        directory,
        repository_root=REPOSITORY_ROOT,
    )
    monkeypatch.undo()

    assert opened, "the watchers observed nothing at all"
    data_root = str(REPOSITORY_ROOT / "data")
    for path in opened:
        assert not path.startswith(data_root), f"a run read collected data at {path}"
        for year in SEALED_YEARS:
            assert year not in path, f"a run touched {year} history at {path}"


def test_the_collector_is_never_called(protocol: dict, tmp_path: Path) -> None:
    from btc_predictor.data import ohlcv

    calls: list[str] = []

    def _refuse(*args, **kwargs):  # pragma: no cover - must never run
        calls.append("collect")
        raise AssertionError("the sealed executor called the OHLCV collector")

    original = ohlcv.collect_btc_ohlcv
    ohlcv.collect_btc_ohlcv = _refuse
    try:
        validator_definition(REPOSITORY_ROOT)
        _v2_validate(_bundle(protocol))
        directory, _, manifest = _collected(tmp_path)
        execute_sealed_validation(
            directory,
            repository_root=REPOSITORY_ROOT,
        )
    finally:
        ohlcv.collect_btc_ohlcv = original
    assert calls == []


def test_the_dry_run_mode_still_refuses_the_sealed_window(protocol: dict) -> None:
    """Outside an authorised sealed execution the inherited guard still bites."""

    for start, end in (
        (SEALED_WINDOW_START_ISO, SEALED_WINDOW_END_ISO),
        ("2014-01-01T00:00:00+00:00", "2016-01-01T00:00:00+00:00"),
        ("2019-01-01T00:00:00+00:00", "2021-01-01T00:00:00+00:00"),
    ):
        bundle = _bundle(
            protocol, sample={"end": end, "sample_id": "x", "start": start}
        )
        with pytest.raises(UntouchedValidationSampleGuardError):
            _v2_validate(bundle)
        with pytest.raises(UntouchedValidationSampleGuardError):
            _v1_validate(bundle)


def test_the_candidate_is_never_constructed_here(protocol: dict) -> None:
    record = _v2_validate(_bundle(protocol)).as_record()
    assert record["provenance"]["candidate_series_id"] == "MEDIAN_OHLC_V2"
    for row in record["hard_requirements"][REQUIREMENT_TRANSFER_GUARD]["pairs"]:
        assert "MEDIAN_OHLC" not in row["comparison_id"]


def test_the_bound_definition_still_says_the_sample_is_unopened(
    protocol: dict,
) -> None:
    sealed = protocol["sample_governance"]["sealed_sample"]
    assert sealed["status"] == "SEALED_UNOPENED"
    assert sealed["collected"] is False
    assert sealed["opened"] is False
    assert sealed["inspected"] is False


def test_no_live_authorization_record_was_created_by_this_ticket() -> None:
    """The one-shot clock starts in the next task, not in this one."""

    live = REPOSITORY_ROOT / SEALED_EXECUTOR_OUTPUT_NAMESPACE / AUTHORIZATION_FILENAME
    assert not live.exists()
    assert sealed_execution_status(
        REPOSITORY_ROOT / SEALED_EXECUTOR_OUTPUT_NAMESPACE,
        validator_definition_sha256=validator_definition_sha256(REPOSITORY_ROOT),
    ) == STATE_NOT_PREPARED


def test_the_persisted_report_names_the_delta_and_the_window() -> None:
    report = (
        REPOSITORY_ROOT
        / SEALED_EXECUTOR_OUTPUT_NAMESPACE
        / v2.SEALED_EXECUTOR_REPORT_FILENAME
    ).read_text()
    assert FROZEN_V3_DEFINITION_SHA256 in report
    assert CERTIFIED_V1_VALIDATOR_SHA256 in report
    assert SEALED_WINDOW_START_ISO in report
    assert SEALED_WINDOW_END_ISO in report
    assert "sealed_sample.sealed_execution_authorized" in report
    assert "Collected: no" in report
    assert "Opened: no" in report


def test_the_previous_v2_artifact_is_preserved_under_its_hash() -> None:
    history = (
        REPOSITORY_ROOT
        / SEALED_EXECUTOR_OUTPUT_NAMESPACE
        / "history"
        / PREVIOUS_CORRECTED_V2_VALIDATOR_SHA256
    )
    prior_contract = json.loads((history / VALIDATOR_DEFINITION_FILENAME).read_text())
    prior_delta = json.loads((history / v2.SEMANTIC_DELTA_FILENAME).read_text())
    prior_report = (history / v2.SEALED_EXECUTOR_REPORT_FILENAME).read_text()
    assert prior_contract["validator_definition_sha256"] == (
        PREVIOUS_CORRECTED_V2_VALIDATOR_SHA256
    )
    assert prior_delta["validator_definition_sha256"] == (
        PREVIOUS_CORRECTED_V2_VALIDATOR_SHA256
    )
    assert PREVIOUS_CORRECTED_V2_VALIDATOR_SHA256 in prior_report


# =============================================================================
# 14. suite-level instrumentation: this whole module opens no sealed path
# =============================================================================

_AUDIT_CHILD_ENV = "BTC019_SEALED_EXECUTOR_AUDIT_CHILD"

_AUDIT_DRIVER = """
import os
import sys

violations = []
observed = []
module_path = sys.argv[1]
data_root = os.path.abspath(sys.argv[2])
repository_root = os.path.abspath(sys.argv[3])
patterns = ('2015', '2016', '2017', '2018', '2019')


def _hook(event, args):
    if event != 'open' or not args:
        return
    name = args[0]
    if not isinstance(name, (str, bytes)):
        return
    text = name.decode('utf-8', 'replace') if isinstance(name, bytes) else name
    observed.append(text)
    resolved = os.path.abspath(text)
    if resolved != repository_root and not resolved.startswith(
        repository_root + os.sep
    ):
        return
    base = os.path.basename(resolved)
    if base.endswith('.pyc'):
        return
    under_data = resolved == data_root or resolved.startswith(data_root + os.sep)
    dated = any(pattern in base for pattern in patterns)
    if not under_data and not dated:
        return
    # An open made relative to a directory descriptor -- pytest's own stale
    # tmp-dir cleanup does exactly this through shutil.rmtree -- reports only a
    # bare entry name, which abspath would misread as a repository path. Only a
    # path that really is a file in this repository can be a sealed read.
    if os.path.isfile(resolved):
        violations.append(text)


sys.addaudithook(_hook)

import pytest

code = pytest.main(['-q', '-p', 'no:cacheprovider', module_path])
marker = 'BTC019' + '_AUDIT'
print(marker + '_OPENS', len(observed))
print(marker + '_BEGIN')
for path in sorted(set(violations)):
    print(path)
print(marker + '_END')
sys.exit(int(code))
"""


@pytest.mark.skipif(
    os.environ.get(_AUDIT_CHILD_ENV) == "1",
    reason="the audit child must not re-enter its own driver",
)
def test_the_whole_suite_opens_no_sealed_path(tmp_path: Path) -> None:
    """Run this entire module under an audit hook on every `open`.

    `sys.addaudithook` sees every file the interpreter opens, including the ones
    `gzip.open`, `Path.read_text` and any collector would reach through, so this
    is a stronger claim than monkeypatching a handful of call sites: nothing in
    this suite opens anything under `data/` or any 2015-2019 path at all.
    """

    driver = tmp_path / "audit_driver.py"
    driver.write_text(_AUDIT_DRIVER, encoding="ascii")
    result = subprocess.run(
        [
            sys.executable,
            str(driver),
            str(Path(__file__).resolve()),
            str(REPOSITORY_ROOT / "data"),
            str(REPOSITORY_ROOT),
        ],
        capture_output=True,
        cwd=REPOSITORY_ROOT,
        env={**os.environ, _AUDIT_CHILD_ENV: "1"},
        text=True,
    )
    tail = result.stdout[-8000:] + result.stderr[-8000:]
    # The child's own pass/fail is checked first. A failing child prints a
    # traceback that can echo any string, so parsing its report before knowing
    # it succeeded would read pytest output as if it were a violation list.
    assert result.returncode == 0, tail
    marker = "BTC019" + "_AUDIT"
    assert f"{marker}_BEGIN" in result.stdout, tail
    body = result.stdout.rsplit(f"{marker}_BEGIN", 1)[1]
    violations = [
        line
        for line in body.rsplit(f"{marker}_END", 1)[0].splitlines()
        if line.strip()
    ]
    assert violations == [], f"the suite opened sealed or collected paths: {violations}"
    # A positive control: the hook must actually have seen the suite work, so an
    # empty violation list means "opened nothing sealed", never "saw nothing".
    observed = int(
        next(
            line
            for line in result.stdout.splitlines()
            if line.startswith(f"{marker}_OPENS ")
        ).split()[1]
    )
    assert observed > 100, f"the audit hook observed only {observed} opens"


# =============================================================================
# 15. the refusal surface is identical too
# =============================================================================


def _malformed_bundles(protocol: dict) -> dict[str, dict]:
    """Every known fail-open shape, as a bundle V1 must refuse."""

    fake_denominator = _gate_rows()
    fake_denominator[0] = _pair_row(
        GATE_PAIRS[0], STRUCTURAL_METRIC, 0, 2, comparability="0.5", not_comparable=2
    )
    fake_denominator[0]["denominator"] = 40

    fake_comparability = _gate_rows()
    fake_comparability[0] = _pair_row(
        GATE_PAIRS[0], STRUCTURAL_METRIC, 0, 40, comparability="0.90", not_comparable=400
    )

    missing_state = _gate_rows()
    missing_state[0].pop("state")

    missing_comparability = _gate_rows()
    missing_comparability[0].pop("structural_comparability_rate")

    duplicate_pair = _gate_rows()
    duplicate_pair.append(dict(duplicate_pair[0]))

    unknown_field = _gate_rows()
    unknown_field[0]["shadow_rate"] = "0"

    wrong_provider = _gate_rows()
    wrong_provider[0]["series_pair"] = ["MEDIAN_OHLC_V2", "kraken"]
    wrong_provider[0]["comparison_id"] = "MEDIAN_OHLC_V2_vs_kraken"

    non_canonical_id = _gate_rows()
    non_canonical_id[0]["comparison_id"] = "bitfinex_vs_MEDIAN_OHLC_V2"

    guard_pair_in_gates = _gate_rows()
    guard_pair_in_gates[0] = _pair_row(GUARD_PAIRS[0], STRUCTURAL_METRIC, 0, 40)

    float_measurement = _inherited_measurements(protocol)
    float_measurement[next(iter(sorted(float_measurement)))] = 0.5

    bundles = {
        "fake_denominator": _bundle(protocol, gate_pair_measurements=fake_denominator),
        "fake_comparability": _bundle(
            protocol, gate_pair_measurements=fake_comparability
        ),
        "missing_state": _bundle(protocol, gate_pair_measurements=missing_state),
        "missing_comparability": _bundle(
            protocol, gate_pair_measurements=missing_comparability
        ),
        "duplicate_pair": _bundle(protocol, gate_pair_measurements=duplicate_pair),
        "unknown_pair_field": _bundle(protocol, gate_pair_measurements=unknown_field),
        "wrong_provider_identity": _bundle(
            protocol, gate_pair_measurements=wrong_provider
        ),
        "non_canonical_comparison_id": _bundle(
            protocol, gate_pair_measurements=non_canonical_id
        ),
        "guard_pair_in_the_gate_universe": _bundle(
            protocol, gate_pair_measurements=guard_pair_in_gates
        ),
        "wrong_tier4_identity": _bundle(
            protocol,
            inherited_gate_measurements=dict(
                _inherited_measurements(protocol), an_invented_gate="0"
            ),
        ),
        "binary_float_measurement": _bundle(
            protocol, inherited_gate_measurements=float_measurement
        ),
        "unknown_top_level_field": _bundle(protocol, shadow_block={}),
        "wrong_schema_version": _bundle(protocol, schema_version="SOMETHING_ELSE_V1"),
        "wrong_comparison_contract": _bundle(
            protocol,
            identities=dict(
                _bundle(protocol)["identities"],
                comparison_contract_version="CROSS_PROVIDER_STRUCTURE_COMPARISON_V1",
            ),
        ),
        "malformed_provenance_digest": _bundle(
            protocol,
            provenance=dict(
                _bundle(protocol)["provenance"], measurement_record_digest="short"
            ),
        ),
        "naive_sample_instant": _bundle(
            protocol,
            sample={"end": SYNTHETIC_END, "sample_id": "x", "start": "2023-01-01"},
        ),
        "sample_ends_before_it_starts": _bundle(
            protocol,
            sample={"end": SYNTHETIC_START, "sample_id": "x", "start": SYNTHETIC_END},
        ),
        "unknown_derived_level_field": _bundle(
            protocol,
            derived_level_review={
                "observed_disagreements": [],
                "reviews": [],
                "shadow": 1,
                "unreviewed_derived_level_disagreement_count": 0,
            },
        ),
        "unknown_not_comparable_field": _bundle(
            protocol,
            not_comparable_accounting={
                "shadow": 1,
                "unrecorded_not_comparable_event_count": 0,
            },
        ),
    }
    short = _bundle(protocol)
    short.pop("diagnostics")
    bundles["missing_top_level_field"] = short
    return bundles


def test_every_known_fail_open_stays_closed_in_both(protocol: dict) -> None:
    """V1 and V2 refuse the same bundles, with the same error and the same words."""

    cases = _malformed_bundles(protocol)
    assert len(cases) >= 20
    for name, bundle in sorted(cases.items()):
        # `ValidatorError` subclasses `ValueError`, and a malformed instant
        # surfaces the owner module's own `ValueError`. Catching the base and
        # comparing exact types proves the two refuse identically either way.
        with pytest.raises(ValueError) as left:
            _v1_validate(bundle)
        with pytest.raises(ValueError) as right:
            _v2_validate(bundle)
        assert type(left.value) is type(right.value), name
        assert str(left.value) == str(right.value), name


def test_a_short_pair_universe_can_never_pass_in_either(protocol: dict) -> None:
    for present in (0, 1, 2):
        bundle = _bundle(protocol, gate_pair_measurements=_gate_rows()[:present])
        left = _v1_validate(bundle).as_record()
        right = _v2_validate(bundle).as_record()
        assert left["verdict"] == right["verdict"] == VERDICT_INSUFFICIENT
        assert left["primary_reason"] == right["primary_reason"]


def test_a_wrong_wilson_boundary_would_refuse_both(monkeypatch, protocol: dict) -> None:
    from btc_predictor.research import reference_composite_v3_convergence as owner

    monkeypatch.setattr(
        owner,
        "wilson_upper_bound",
        lambda k, n, *, quantile=None: Decimal(0) if n else None,
    )
    with pytest.raises(ValidatorBindingError, match="the certification rule makes"):
        _v1_validate(_bundle(protocol))
    with pytest.raises(ValidatorBindingError, match="the certification rule makes"):
        _v2_validate(_bundle(protocol))


# =============================================================================
# 16. the instrumentation validates itself
# =============================================================================


def _run_audit_driver(tmp_path: Path, module: Path, root: Path) -> list[str]:
    """Run the audit driver over one module and return the paths it flagged."""

    driver = tmp_path / "driver.py"
    driver.write_text(_AUDIT_DRIVER, encoding="ascii")
    result = subprocess.run(
        [sys.executable, str(driver), str(module), str(root / "data"), str(root)],
        capture_output=True,
        cwd=root,
        env={**os.environ, _AUDIT_CHILD_ENV: "1"},
        text=True,
    )
    marker = "BTC019" + "_AUDIT"
    assert f"{marker}_BEGIN" in result.stdout, result.stdout + result.stderr
    body = result.stdout.rsplit(f"{marker}_BEGIN", 1)[1]
    return [
        line
        for line in body.rsplit(f"{marker}_END", 1)[0].splitlines()
        if line.strip()
    ]


def test_the_audit_hook_catches_a_real_data_read(tmp_path: Path) -> None:
    """A negative control, so an empty violation list is evidence, not luck.

    The synthetic repository is entirely inside `tmp_path`; this proves the
    mechanism without the suite reading one byte of the real `data/` tree.
    """

    root = tmp_path / "repo"
    (root / "data" / "sealed_2017").mkdir(parents=True)
    (root / "data" / "sealed_2017" / "bars.jsonl").write_text("synthetic\n")
    module = root / "test_reads_data.py"
    module.write_text(
        "from pathlib import Path\n"
        "def test_reads():\n"
        "    assert Path('data/sealed_2017/bars.jsonl').read_text()\n"
    )
    assert _run_audit_driver(tmp_path, module, root) == [
        "data/sealed_2017/bars.jsonl"
    ]


def test_the_audit_hook_ignores_a_directory_relative_cleanup(
    tmp_path: Path,
) -> None:
    """A false-positive control for pytest's own stale tmp-dir cleanup.

    `shutil.rmtree` opens each entry by bare name against a directory
    descriptor, so the audit event carries `data` and
    `external_2019-12-01_2022-12-31` with no directory part at all. Resolving
    those against the current directory would read them as repository paths.
    They are not files in this repository and must never be reported.
    """

    root = tmp_path / "repo"
    (root / "data").mkdir(parents=True)
    victim = tmp_path / "stale" / "data" / "external_2019-12-01_2022-12-31"
    victim.mkdir(parents=True)
    (victim / "bitstamp_btc_usd_1h.jsonl.gz").write_bytes(b"synthetic")
    module = root / "test_cleans_up.py"
    module.write_text(
        "import shutil\n"
        "def test_cleanup():\n"
        f"    shutil.rmtree({str(tmp_path / 'stale')!r})\n"
    )
    assert _run_audit_driver(tmp_path, module, root) == []
