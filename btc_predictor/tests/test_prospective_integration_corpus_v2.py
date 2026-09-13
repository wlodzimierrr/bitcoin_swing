"""POSTP1-001V2 pre-data tests for ``PROSPECTIVE_INTEGRATION_CORPUS_V2``.

Every fixture here is synthetic. No test collects a qualifying observation, no
test produces a real Stage-B aggregate, and a suite-level audit hook proves the
whole module opens nothing under ``data/`` and nothing on a sealed 2015-2019
path.

The adversarial tests are the point of the file: a replay-complete parent is a
claim about what *refuses*, so a complete valid graph is built and then damaged
one reference at a time.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from decimal import Context, Decimal, localcontext
from pathlib import Path
from typing import Any

import pytest

from btc_predictor.portfolio import account as _account
from btc_predictor.portfolio import state_machine as sm
from btc_predictor.research import feature_matrix as _feature_matrix
from btc_predictor.research import prospective_integration_corpus as v1
from btc_predictor.research import prospective_integration_corpus_v2 as v2
from btc_predictor.research.prospective_integration_corpus_v2 import (
    EVALUABLE,
    NOT_EVALUABLE,
    WARMUP_STATE_COMPLETE,
    WARMUP_STATE_INCOMPLETE,
    EvidenceStore,
    ProspectiveCorpusV2Error,
    ReplayRefusedError,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
ARTIFACT_DIR = REPOSITORY_ROOT / v2.OUTPUT_NAMESPACE
V1_ARTIFACT_DIR = REPOSITORY_ROOT / v1.OUTPUT_NAMESPACE
CORPUS = "0" * 64
ANCHOR = datetime(2026, 9, 10, tzinfo=UTC)
_AUDIT_CHILD_ENV = "PROSPECTIVE_V2_AUDIT_CHILD"


@pytest.fixture(scope="module")
def census() -> dict[str, Any]:
    return v2.owner_evaluability_census()


def _daily_slot() -> v2.DecisionSlot:
    return v2.decision_slot(v1.STRATEGY_DAILY_CADENCE, ANCHOR)


def _hourly_slot(offset_hours: int) -> v2.DecisionSlot:
    return v2.decision_slot(
        v1.STOP_HOURLY_CADENCE, ANCHOR + timedelta(hours=offset_hours)
    )


def _owner_graph(
    census: dict[str, Any], features: tuple[str, ...]
) -> tuple[EvidenceStore, v2.DecisionSlot, dict[str, str]]:
    """Build a complete valid owner-history graph for a bounded owner set."""

    store = EvidenceStore()
    slot = _daily_slot()
    v2.seed_complete_slot_evidence(
        store, slot=slot, corpus_sha256=CORPUS, census=census
    )
    manifests = v2.build_slot_owner_history_graph(
        store, slot=slot, corpus_sha256=CORPUS, census=census, features=features
    )
    return store, slot, manifests


def _republish(store: EvidenceStore, sha256: str, **changes: Any) -> str:
    record = store.get(sha256)
    record.pop(v2.DIGEST_FIELD)
    record.update(changes)
    return store.put(record)


# =============================================================================
# 1. identity, classification and the V1 authority decision
# =============================================================================


def test_v2_is_a_distinct_version_in_a_distinct_artifact_directory() -> None:
    assert v2.PROTOCOL_VERSION == "PROSPECTIVE_INTEGRATION_CORPUS_V2"
    assert v2.PROTOCOL_VERSION != v1.PROTOCOL_VERSION
    assert v2.OUTPUT_NAMESPACE != v1.OUTPUT_NAMESPACE
    assert v2.OUTPUT_NAMESPACE.startswith("prospective_evidence/")
    assert not v2.OUTPUT_NAMESPACE.startswith(("data/", "research_artifacts/"))


def test_v2_may_not_classify_itself_as_certified() -> None:
    protocol = v2.protocol_definition()
    assert protocol["final_classification"] == (
        "PROSPECTIVE_INTEGRATION_CORPUS_V2_READY_FOR_XHIGH_REVIEW"
    )
    assert protocol["final_classification"] in v2.FAIL_CLOSED_CLASSIFICATIONS
    assert len(v2.FAIL_CLOSED_CLASSIFICATIONS) == 4
    assert protocol["certification"]["certified"] is False
    assert "CERTIFIED" not in protocol["status"].replace("UNCERTIFIED", "")
    assert protocol["status"] == (
        "FROZEN_PRE_DATA_REPLAY_COMPLETE_PARENT_V2_AWAITING_XHIGH_REVIEW"
    )


def test_v1_remains_immutable_certified_lineage_and_is_not_called_invalid() -> None:
    lineage = v2.protocol_definition()["lineage"]["parent_v1"]
    assert lineage["definition_sha256"] == (
        "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7"
    )
    assert lineage["certification"] == "POSTP1-002R5 PASS"
    assert lineage["qualifying_observations_collected"] is False
    assert lineage["mutated_by_v2"] is False
    assert lineage["limitation"] == (
        "REPLAY PROVENANCE INCOMPLETE FOR THE NEW SUFFICIENCY-AUTHORITY "
        "REQUIREMENT"
    )
    assert "invalid" not in lineage["limitation_scope"].lower().replace(
        "is not invalid", ""
    )
    assert lineage["classification_after_v2_review_pass"] == (
        "SUPERSEDED_PRE_COLLECTION_BY_REPLAY_COMPLETE_V2"
    )
    # Before V2 certification V1 is not marked a replaced collection authority.
    assert lineage["classification_now"] == (
        "IMMUTABLE_CERTIFIED_LINEAGE_COLLECTION_AUTHORITY_UNCHANGED_UNTIL_"
        "V2_REVIEW_PASS"
    )


def test_the_v2_canonical_encoding_is_the_certified_parents_own() -> None:
    payloads = [
        {"a": 1, "b": [1, 2, {"c": "x"}]},
        {"z": None, "y": True, "x": "unicode é"},
        v2.owner_evaluability_census(),
    ]
    for payload in payloads:
        assert v2._digest(payload) == v1._digest(payload)


# =============================================================================
# 2. the owner census
# =============================================================================


def test_every_frozen_feature_lands_in_exactly_one_owner_class(census) -> None:
    assert census["feature_count"] == 33
    assert set(census["rows"]) == set(_feature_matrix.INITIAL_FEATURE_NAMES)
    members = [
        feature
        for group in census["owners_by_class"].values()
        for feature in group
    ]
    assert sorted(members) == sorted(_feature_matrix.INITIAL_FEATURE_NAMES)
    assert len(members) == len(set(members))
    assert census["every_feature_in_exactly_one_class"] is True


def test_the_census_keeps_heterogeneous_predicates_not_one_count_rule(census) -> None:
    used = {row["owner_class"] for row in census["rows"].values()}
    assert len(used) >= 10, "the owner classes collapsed into too few shapes"
    assert used <= set(v2.OWNER_CLASSES)
    assert census["generic_count_rule_substituted_for_owner_predicates"] is False
    predicates = {census["class_predicates"][name] for name in used}
    assert len(predicates) == len(used), "two classes share one predicate"


def test_every_owner_the_census_freezes_resolves_to_a_real_symbol(census) -> None:
    for feature, row in census["rows"].items():
        assert v2._resolve_owner_symbol(row["owner_contract"]), feature
        assert v2._resolve_owner_symbol(row["resolved_feature_owner"]), feature


def test_the_census_records_the_parents_four_non_resolving_owner_labels(
    census,
) -> None:
    unresolved = census["parent_declared_feature_owners_that_do_not_resolve"]
    assert unresolved == [
        "FUNDING_7D_AVG",
        "FUNDING_ZSCORE_180D",
        "OI_GROWTH_7D",
        "OI_GROWTH_ZSCORE_180D",
    ]
    for feature in unresolved:
        row = census["rows"][feature]
        # The label is corrected to the parent's own evaluability owner, so the
        # predicate that is measured does not move.
        assert row["resolved_feature_owner"] == row["owner_contract"]
        assert not v2._resolve_owner_symbol(row["parent_declared_feature_owner"])


def test_the_census_agrees_with_the_certified_parent_on_every_owner(census) -> None:
    warmup = v1.warmup_history_contract()["rows"]
    coverage = v1.feature_input_coverage_contract()["rows"]
    for feature, row in census["rows"].items():
        assert row["owner_contract"] == warmup[feature]["owner"]
        assert row["parent_declared_feature_owner"] == (
            coverage[feature]["deterministic_feature_owner"]
        )
    assert census["parent_v1_warmup_history_sha256"] == (
        v1.warmup_history_contract()["definition_sha256"]
    )


def test_owner_parameters_are_read_from_the_owners_not_restated(census) -> None:
    from btc_predictor.features import flow, momentum, positioning, trend, volatility

    parameters = census["owner_parameters"]
    assert parameters["momentum_4w_periods"] == (
        momentum.FOUR_WEEK_MOMENTUM_LOOKBACK_DAYS
    )
    assert parameters["momentum_12w_periods"] == (
        momentum.TWELVE_WEEK_MOMENTUM_LOOKBACK_DAYS
    )
    assert parameters["ma_distance_weeks"] == (
        trend.TWENTY_WEEK_MA_DISTANCE_LOOKBACK_WEEKS
    )
    assert parameters["high_distance_weeks"] == (
        trend.FIFTY_TWO_WEEK_HIGH_DISTANCE_LOOKBACK_WEEKS
    )
    assert parameters["etf_5_days"] == flow.FIVE_DAY_ETF_FLOW_WINDOW_DAYS
    assert parameters["etf_20_days"] == flow.TWENTY_DAY_ETF_FLOW_WINDOW_DAYS
    assert parameters["funding_min"] == (
        positioning.DEFAULT_FUNDING_MIN_ZSCORE_OBSERVATIONS
    )
    assert parameters["vol_percentile_min_prior"] == (
        volatility.volatility_percentile.__kwdefaults__["min_percentile_observations"]
    )
    assert parameters["vol_percentile_window_days"] == (
        volatility.volatility_percentile.__kwdefaults__["percentile_window_days"]
    )
    assert parameters["cvd_prior_observations"] == (
        flow.spot_perp_cvd_spread.__kwdefaults__["zscore_window_periods"]
    )


def test_the_census_declares_rather_than_hides_its_unowned_inputs(census) -> None:
    boundaries = census["unowned_input_boundaries"]
    assert set(boundaries) == {
        "canonical_bar_derivation_cutoff",
        "market_holidays",
        "same_timestamp_revision_resolution",
    }
    assert boundaries["market_holidays"]["existing_owner"] is None
    assert census["frozen_input_policies"]["revision_policy"] == v1.REVISION_POLICY
    assert census["frozen_input_policies"]["duplicate_policy"] == v1.DUPLICATE_POLICY
    assert census["frozen_input_policies"]["late_data_policy"] == v1.LATE_DATA_POLICY
    assert census["delegated_grid_owners"]["pit_policy_owner"] == v1.PIT_POLICY_OWNER


def test_the_liquidation_zero_event_day_counts_as_history(census) -> None:
    # The certified parent freezes observed_zero_events_enters_history: True, so
    # V2 must treat an observed zero as a scientific observation, not a gap.
    assert v2.OBSERVED_ZERO_EVENTS in v2.QUALIFYING_OBSERVATION_STATUSES
    assert v2.SOURCE_UNAVAILABLE in v2.ADVERSE_OBSERVATION_STATUSES
    assert set(v2.QUALIFYING_OBSERVATION_STATUSES) | set(
        v2.ADVERSE_OBSERVATION_STATUSES
    ) == set(v1.LIQUIDATION_FEED_STATUSES)


# =============================================================================
# 3. owner-history closure and its adversarial cases
# =============================================================================

_HISTORY_OWNERS = ("VOL_PERCENTILE_2Y", "RV_20")


def test_a_complete_owner_history_graph_replays_to_evaluable(census) -> None:
    store, slot, manifests = _owner_graph(census, _HISTORY_OWNERS)
    for feature in _HISTORY_OWNERS:
        result = v2.replay_owner_history_manifest(
            store,
            manifest_sha256=manifests[feature],
            slot=slot,
            corpus_sha256=CORPUS,
            component_states={
                name: EVALUABLE for name in census["rows"][feature][
                    "evidence_selector"
                ]["components"]
            },
        )
        assert result["evaluability_state"] == EVALUABLE, feature
        assert result["reason_codes"] == []


def test_an_omitted_qualifying_observation_refuses(census) -> None:
    store, slot, manifests = _owner_graph(census, _HISTORY_OWNERS)
    manifest = store.get(manifests["VOL_PERCENTILE_2Y"])
    forged = _republish(
        store,
        manifests["VOL_PERCENTILE_2Y"],
        observation_record_sha256s=manifest["observation_record_sha256s"][1:],
    )
    with pytest.raises(ReplayRefusedError, match="does not equal the expected"):
        v2.replay_owner_history_manifest(
            store,
            manifest_sha256=forged,
            slot=slot,
            corpus_sha256=CORPUS,
            component_states={"RV_20": EVALUABLE},
        )


def test_an_omitted_adverse_observation_refuses(census) -> None:
    store, slot, manifests = _owner_graph(census, ("FUNDING_ZSCORE_180D",))
    # Publish an adverse observation inside the required window *after* the
    # manifest was built; the stale manifest now omits evidence the predicate
    # needs, and the independently recomputed expected set catches it.
    store.put(
        v2.source_observation_record(
            corpus_sha256=CORPUS,
            series_id=v2.SERIES_FUNDING_RATE,
            observation_time=slot.observation_time - timedelta(days=3),
            available_at=slot.observation_time - timedelta(days=2),
            value=None,
            observation_status=v2.SOURCE_UNAVAILABLE,
            revision=2,
        )
    )
    with pytest.raises(ReplayRefusedError, match="does not equal the expected"):
        v2.replay_owner_history_manifest(
            store,
            manifest_sha256=manifests["FUNDING_ZSCORE_180D"],
            slot=slot,
            corpus_sha256=CORPUS,
        )


def test_an_adverse_observation_makes_the_owner_not_evaluable(census) -> None:
    store, slot, _ = _owner_graph(census, ("FUNDING_ZSCORE_180D",))
    store.put(
        v2.source_observation_record(
            corpus_sha256=CORPUS,
            series_id=v2.SERIES_FUNDING_RATE,
            observation_time=slot.observation_time - timedelta(days=3),
            available_at=slot.observation_time - timedelta(days=2),
            value=None,
            observation_status=v2.SOURCE_UNAVAILABLE,
            revision=2,
        )
    )
    manifests = v2.build_slot_owner_history_graph(
        store,
        slot=slot,
        corpus_sha256=CORPUS,
        census=census,
        features=("FUNDING_ZSCORE_180D",),
    )
    result = v2.replay_owner_history_manifest(
        store,
        manifest_sha256=manifests["FUNDING_ZSCORE_180D"],
        slot=slot,
        corpus_sha256=CORPUS,
    )
    assert result["evaluability_state"] == NOT_EVALUABLE
    assert v2.REASON_ADVERSE_OBSERVATION in result["reason_codes"]
    assert v2.REASON_HISTORY_INCOMPLETE in result["reason_codes"]


@pytest.mark.parametrize(
    ("owner", "series_kind", "series"),
    [
        ("VOL_PERCENTILE_2Y", v2.SERIES_KIND_DERIVED, "RV_20"),
        ("OI_INTENSITY_PERCENTILE_180D", v2.SERIES_KIND_DERIVED, "OI_INTENSITY"),
        ("CVD_SPREAD", v2.SERIES_KIND_SOURCE, v2.SERIES_SPOT_PERP_CVD),
    ],
)
def test_omitting_one_prior_result_of_each_history_family_refuses(
    census, owner, series_kind, series
) -> None:
    """A prior percentile, volatility and flow/CVD observation each matter."""

    store, slot, manifests = _owner_graph(census, (owner,))
    manifest = store.get(manifests[owner])
    assert manifest["series_identity"]["series_kind"] == series_kind
    assert manifest["series_identity"]["series_id"] == series
    forged = _republish(
        store,
        manifests[owner],
        observation_record_sha256s=manifest["observation_record_sha256s"][:-2]
        + manifest["observation_record_sha256s"][-1:],
    )
    with pytest.raises(ReplayRefusedError, match="does not equal the expected"):
        v2.replay_owner_history_manifest(
            store,
            manifest_sha256=forged,
            slot=slot,
            corpus_sha256=CORPUS,
            component_states=dict.fromkeys(
                census["rows"][owner]["evidence_selector"]["components"], EVALUABLE
            ),
        )


def test_a_future_available_history_record_is_excluded_and_refused(census) -> None:
    store, slot, manifests = _owner_graph(census, ("RV_20",))
    future = store.put(
        v2.source_observation_record(
            corpus_sha256=CORPUS,
            series_id=v2.SERIES_CANONICAL_DAILY_CLOSE,
            observation_time=slot.observation_time,
            available_at=slot.decision_time + timedelta(hours=1),
            value="999",
            revision=9,
        )
    )
    manifest = store.get(manifests["RV_20"])
    forged = _republish(
        store,
        manifests["RV_20"],
        observation_record_sha256s=[*manifest["observation_record_sha256s"], future],
    )
    with pytest.raises(ReplayRefusedError):
        v2.replay_owner_history_manifest(
            store, manifest_sha256=forged, slot=slot, corpus_sha256=CORPUS
        )
    # The expected set never admitted it in the first place.
    expected = v2.expected_owner_evidence(
        store, feature="RV_20", slot=slot, census=census
    )
    assert future not in expected["observation_record_sha256s"]


def test_a_same_shaped_record_from_another_source_refuses(census) -> None:
    store, slot, manifests = _owner_graph(census, ("RV_20",))
    other = store.put(
        v2.source_observation_record(
            corpus_sha256=CORPUS,
            series_id=v2.SERIES_FUNDING_RATE,
            observation_time=slot.observation_time,
            available_at=slot.observation_time,
            value="1",
        )
    )
    manifest = store.get(manifests["RV_20"])
    forged = _republish(
        store,
        manifests["RV_20"],
        observation_record_sha256s=manifest["observation_record_sha256s"][:-1]
        + [other],
    )
    with pytest.raises(ReplayRefusedError):
        v2.replay_owner_history_manifest(
            store, manifest_sha256=forged, slot=slot, corpus_sha256=CORPUS
        )


def test_another_slots_history_refuses(census) -> None:
    store, slot, manifests = _owner_graph(census, ("RV_20",))
    other_slot = v2.decision_slot(
        v1.STRATEGY_DAILY_CADENCE, ANCHOR - timedelta(days=1)
    )
    with pytest.raises(ReplayRefusedError, match="another slot"):
        v2.replay_owner_history_manifest(
            store,
            manifest_sha256=manifests["RV_20"],
            slot=other_slot,
            corpus_sha256=CORPUS,
        )


def test_a_manifest_bound_to_another_corpus_refuses(census) -> None:
    store, slot, manifests = _owner_graph(census, ("RV_20",))
    with pytest.raises(ReplayRefusedError, match="different certified corpus"):
        v2.replay_owner_history_manifest(
            store,
            manifest_sha256=manifests["RV_20"],
            slot=slot,
            corpus_sha256="1" * 64,
        )


def test_an_owner_history_manifest_may_not_carry_a_conclusion(census) -> None:
    store, slot, manifests = _owner_graph(census, ("RV_20",))
    record = store.get(manifests["RV_20"])
    record.pop(v2.DIGEST_FIELD)
    record["warmup_history_complete"] = True
    forged = store.put(record)
    with pytest.raises(ReplayRefusedError, match="may not carry the conclusion"):
        v2.replay_owner_history_manifest(
            store, manifest_sha256=forged, slot=slot, corpus_sha256=CORPUS
        )


def test_a_missing_evidence_reference_refuses(census) -> None:
    store, slot, manifests = _owner_graph(census, ("RV_20",))
    manifest = store.get(manifests["RV_20"])
    store._records.pop(manifest["observation_record_sha256s"][0])
    with pytest.raises(ReplayRefusedError):
        v2.replay_owner_history_manifest(
            store, manifest_sha256=manifests["RV_20"], slot=slot, corpus_sha256=CORPUS
        )


# =============================================================================
# 4. warmup is derived, never asserted
# =============================================================================


def test_the_v2_decision_record_carries_no_authoritative_warmup_boolean() -> None:
    contract = v2.decision_observation_contract()
    assert contract["parent_v1_warmup_boolean"]["field"] == "warmup_history_complete"
    assert contract["parent_v1_warmup_boolean"]["v1_role"] == (
        "INDEPENDENT_SCIENTIFIC_AUTHORITY"
    )
    assert contract["parent_v1_warmup_boolean"]["v2_role"] == (
        "NON_AUTHORITATIVE_CACHED_DERIVED_PROJECTION"
    )
    assert "warmup_history_complete" not in v2.DECISION_OBSERVATION_FIELDS
    assert "warmup_history_state" in v2.CACHED_PROJECTION_FIELDS
    assert v2.decision_evaluability_contract()[
        "warmup_boolean_is_authoritative"
    ] is False


def test_the_v1_table_carried_the_boolean_and_the_v2_table_does_not() -> None:
    v1_columns = v1.data_schema_contract()["tables"][
        "prospective_decision_observation"
    ]["columns"]
    assert "warmup_history_complete" in v1_columns
    v2_columns = v2.data_schema_contract_v2()["tables"][
        "prospective_decision_observation_v2"
    ]["columns"]
    assert "warmup_history_complete" not in v2_columns
    assert "cached_projections" in v2_columns
    assert "slot_evidence_manifest_sha256" in v2_columns


def test_a_complete_graph_derives_a_complete_warmup_state(census) -> None:
    store, slot, manifests = _owner_graph(
        census, tuple(_feature_matrix.INITIAL_FEATURE_NAMES)
    )
    result = v2.replay_decision_evaluability(
        store,
        slot=slot,
        corpus_sha256=CORPUS,
        owner_manifest_sha256s=manifests,
        census=census,
    )
    assert result["derived_warmup_state"] == WARMUP_STATE_COMPLETE
    assert result["not_evaluable_owners"] == []
    assert len(result["required_owners"]) == 33


def test_a_cached_true_warmup_over_an_incomplete_graph_refuses(census) -> None:
    store, slot, manifests = _owner_graph(
        census, tuple(_feature_matrix.INITIAL_FEATURE_NAMES)
    )
    manifest = store.get(manifests["VOL_PERCENTILE_2Y"])
    forged = _republish(
        store,
        manifests["VOL_PERCENTILE_2Y"],
        observation_record_sha256s=manifest["observation_record_sha256s"][1:],
    )
    with pytest.raises(ReplayRefusedError):
        v2.replay_decision_evaluability(
            store,
            slot=slot,
            corpus_sha256=CORPUS,
            owner_manifest_sha256s={**manifests, "VOL_PERCENTILE_2Y": forged},
            census=census,
            cached_warmup_state=WARMUP_STATE_COMPLETE,
        )


def test_a_cached_false_warmup_over_a_complete_graph_still_refuses(census) -> None:
    """A cache may not lower an authoritative result any more than raise it."""

    store, slot, manifests = _owner_graph(
        census, tuple(_feature_matrix.INITIAL_FEATURE_NAMES)
    )
    derived = v2.replay_decision_evaluability(
        store,
        slot=slot,
        corpus_sha256=CORPUS,
        owner_manifest_sha256s=manifests,
        census=census,
    )
    assert derived["derived_warmup_state"] == WARMUP_STATE_COMPLETE
    with pytest.raises(ReplayRefusedError, match="disagrees with the replayed"):
        v2.replay_decision_evaluability(
            store,
            slot=slot,
            corpus_sha256=CORPUS,
            owner_manifest_sha256s=manifests,
            census=census,
            cached_warmup_state=WARMUP_STATE_INCOMPLETE,
        )


def test_deleting_one_required_record_changes_the_derived_warmup_state(
    census,
) -> None:
    store, slot, _ = _owner_graph(census, ("RV_20",))
    manifests = v2.build_slot_owner_history_graph(
        store, slot=slot, corpus_sha256=CORPUS, census=census, features=("RV_20",)
    )
    assert (
        v2.replay_owner_history_manifest(
            store, manifest_sha256=manifests["RV_20"], slot=slot, corpus_sha256=CORPUS
        )["evaluability_state"]
        == EVALUABLE
    )
    oldest = store.get(manifests["RV_20"])["observation_record_sha256s"][0]
    store._records.pop(oldest)
    rebuilt = v2.build_slot_owner_history_graph(
        store, slot=slot, corpus_sha256=CORPUS, census=census, features=("RV_20",)
    )
    result = v2.replay_owner_history_manifest(
        store, manifest_sha256=rebuilt["RV_20"], slot=slot, corpus_sha256=CORPUS
    )
    assert result["evaluability_state"] == NOT_EVALUABLE
    assert v2.REASON_CONTIGUITY_BROKEN in result["reason_codes"]


def test_a_slot_that_omits_a_required_owner_manifest_refuses(census) -> None:
    store, slot, manifests = _owner_graph(
        census, tuple(_feature_matrix.INITIAL_FEATURE_NAMES)
    )
    reduced = {k: v for k, v in manifests.items() if k != "MOMENTUM_4W"}
    with pytest.raises(ReplayRefusedError, match="omits owner-history manifests"):
        v2.replay_decision_evaluability(
            store,
            slot=slot,
            corpus_sha256=CORPUS,
            owner_manifest_sha256s=reduced,
            census=census,
        )


def test_the_hourly_cadence_requires_no_feature_owner_and_says_so(census) -> None:
    contract = v2.decision_evaluability_contract()
    assert contract["required_owners_by_cadence"][v1.STOP_HOURLY_CADENCE] == []
    assert len(contract["required_owners_by_cadence"][v1.STRATEGY_DAILY_CADENCE]) == 33
    fields = set(contract["stop_event_classifier_input_fields"])
    assert not fields & set(_feature_matrix.INITIAL_FEATURE_NAMES)
    assert contract["stop_event_classifier_owner"] == v1.STOP_EVENT_CLASSIFIER_OWNER


# =============================================================================
# 5. the content-addressed acyclic portfolio graph
# =============================================================================


def _account_record() -> dict[str, Any]:
    return v2._synthetic_account_record()


class _Graph:
    """A synthetic control-track graph: GENESIS, ENTER A, moves, ADD, TRIM."""

    def __init__(self, track: str = v1.CONTROL_TRACK) -> None:
        self.store = EvidenceStore()
        self.track = track
        self.genesis = v2.build_portfolio_genesis_state(
            self.store,
            track=track,
            corpus_sha256=CORPUS,
            slot=_hourly_slot(-1),
            symbol="BTCUSD",
            account_record=_account_record(),
        )
        self.states: list[str] = [self.genesis]
        self.transitions: list[str] = []

    def action(self, slot: v2.DecisionSlot) -> str:
        return self.store.put(
            v2.decision_owner_output_record(
                corpus_sha256=CORPUS,
                slot=slot,
                track=self.track,
                owner=v2.DECISION_OWNER_TRADE_ACTION,
                owner_version=v2.DECISION_OWNER_VERSIONS[
                    v2.DECISION_OWNER_TRADE_ACTION
                ],
                output={"action": "SYNTHETIC"},
                input_record_sha256s=[],
            )
        )

    def risk(self, slot: v2.DecisionSlot) -> str:
        return v2.build_risk_evaluation(
            self.store,
            corpus_sha256=CORPUS,
            slot=slot,
            track=self.track,
            reference_role=v1.CONTROL_REFERENCE_ROLE,
            reference_identity="SYNTHETIC_CONTROL",
            sizing_inputs={
                "entry_price": "100000",
                "maximum_notional_fraction_nav": None,
                "nav": "1000000",
                "risk_fraction_nav": "0.005",
                "stop_distance_fraction": "0.05",
            },
            trade_permitted=True,
            input_record_sha256s=[],
        )

    def step(
        self,
        hours: int,
        events: list[dict[str, Any]],
        *,
        opens_new: bool = False,
        prior: str | None = None,
    ) -> str:
        slot = _hourly_slot(hours)
        last = events[-1]["event"]
        transition_class = v2.TRANSITION_CLASS_BY_EVENT[last]
        kwargs: dict[str, Any] = {}
        if transition_class in (
            v2.TRANSITION_CLASS_ENTER,
            v2.TRANSITION_CLASS_STOP_MOVE,
        ):
            kwargs["stop_evidence_record_sha256"] = self.action(slot)
        if transition_class in (v2.TRANSITION_CLASS_ENTER, v2.TRANSITION_CLASS_ADD):
            kwargs["risk_evidence_record_sha256"] = self.risk(slot)
        if opens_new:
            kwargs["opens_new_position_lifecycle"] = True
            kwargs["new_lifecycle_parameters"] = {
                "direction": "long",
                "initial_state": sm.WATCH,
                "symbol": "BTCUSD",
            }
        predecessor = prior if prior is not None else self.states[-1]
        transition = v2.build_portfolio_transition(
            self.store,
            track=self.track,
            corpus_sha256=CORPUS,
            slot=slot,
            prior_state_record_sha256=predecessor,
            position_events=events,
            action_evidence_record_sha256=self.action(slot),
            **kwargs,
        )
        state = v2.build_portfolio_state(
            self.store,
            corpus_sha256=CORPUS,
            slot=slot,
            prior_state_record_sha256=predecessor,
            producing_transition_record_sha256=transition,
        )
        self.transitions.append(transition)
        self.states.append(state)
        return state


def _enter(hours: int, *, price: str = "100000", stop: str = "90000") -> list[dict]:
    slot = _hourly_slot(hours)
    return [
        v2.position_event(event=sm.ARM_ENTRY, event_time=slot.decision_time),
        v2.position_event(
            event=sm.ENTER,
            event_time=slot.decision_time,
            quantity="3",
            price=price,
            stop_price=stop,
            source_feature_id="INITIAL_STOP",
            source_record_id=f"STOP_{hours}",
        ),
    ]


def _episode_a() -> _Graph:
    graph = _Graph()
    graph.step(1, _enter(1))
    for hours, stop in ((2, "92000"), (3, "94000")):
        slot = _hourly_slot(hours)
        graph.step(
            hours,
            [
                v2.position_event(
                    event=sm.STOP_MOVE,
                    event_time=slot.decision_time,
                    stop_price=stop,
                    source_feature_id="TRAILING_STOP",
                    source_record_id=f"STRUCTURE_{hours}",
                )
            ],
        )
    graph.step(
        4,
        [
            v2.position_event(
                event=sm.ADD,
                event_time=_hourly_slot(4).decision_time,
                quantity="2",
                price="110000",
            )
        ],
    )
    graph.step(
        5,
        [
            v2.position_event(
                event=sm.TRIM,
                event_time=_hourly_slot(5).decision_time,
                quantity="1",
                price="115000",
            )
        ],
    )
    return graph


def test_the_state_binds_its_predecessor_record_and_producing_transition() -> None:
    graph = _episode_a()
    tip = graph.store.get(graph.states[-1])
    assert tip["state_kind"] == v2.STATE_KIND_DERIVED
    assert tip["prior_state_record_sha256"] == graph.states[-2]
    assert tip["producing_transition_record_sha256"] == graph.transitions[-1]
    transition = graph.store.get(graph.transitions[-1])
    assert transition["prior_state_record_sha256"] == graph.states[-2]
    assert "resulting_state_record_sha256" not in transition


def test_the_graph_is_acyclic_and_the_whole_chain_replays() -> None:
    graph = _episode_a()
    chain = v2.replay_portfolio_chain(
        graph.store, state_record_sha256=graph.states[-1], corpus_sha256=CORPUS
    )
    assert len(chain) == len(graph.states)
    assert chain[0]["is_genesis"] is True
    assert [node["state_record_sha256"] for node in chain] == graph.states
    # A transition names its predecessor and never its result, so no content
    # hash can contain itself.
    for index, transition in enumerate(graph.transitions):
        payload = json.dumps(graph.store.get(transition))
        assert graph.states[index] in payload
        assert graph.states[index + 1] not in payload


def test_genesis_is_distinguishable_from_a_missing_predecessor() -> None:
    graph = _Graph()
    genesis = graph.store.get(graph.genesis)
    assert genesis["state_kind"] == v2.STATE_KIND_GENESIS
    assert genesis["prior_state_record_sha256"] is None
    assert genesis["producing_transition_record_sha256"] is None
    forged = _republish(
        graph.store, graph.genesis, state_kind=v2.STATE_KIND_DERIVED
    )
    with pytest.raises(ReplayRefusedError, match="must bind its predecessor"):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_a_later_state_may_not_use_a_null_predecessor() -> None:
    graph = _episode_a()
    forged = _republish(
        graph.store, graph.states[-1], prior_state_record_sha256=None
    )
    with pytest.raises(ReplayRefusedError, match="must bind its predecessor"):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_a_state_referencing_the_wrong_predecessor_refuses() -> None:
    graph = _episode_a()
    forged = _republish(
        graph.store,
        graph.states[-1],
        prior_state_record_sha256=graph.states[1],
    )
    with pytest.raises(ReplayRefusedError, match="belongs to another predecessor"):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_a_state_referencing_another_predecessors_transition_refuses() -> None:
    graph = _episode_a()
    forged = _republish(
        graph.store,
        graph.states[-1],
        producing_transition_record_sha256=graph.transitions[0],
    )
    with pytest.raises(ReplayRefusedError, match="belongs to another predecessor"):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_a_missing_producing_transition_refuses() -> None:
    graph = _episode_a()
    graph.store._records.pop(graph.transitions[-1])
    with pytest.raises(ReplayRefusedError, match="missing evidence reference"):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=graph.states[-1], corpus_sha256=CORPUS
        )


def test_a_missing_predecessor_state_refuses() -> None:
    graph = _episode_a()
    graph.store._records.pop(graph.states[-2])
    with pytest.raises(ReplayRefusedError, match="missing evidence reference"):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=graph.states[-1], corpus_sha256=CORPUS
        )


def test_an_altered_transition_with_an_unchanged_state_refuses() -> None:
    graph = _episode_a()
    transition = graph.store.get(graph.transitions[-1])
    events = [dict(event) for event in transition["position_events"]]
    events[-1]["quantity"] = "2"
    altered = _republish(graph.store, graph.transitions[-1], position_events=events)
    forged = _republish(
        graph.store,
        graph.states[-1],
        producing_transition_record_sha256=altered,
    )
    with pytest.raises(ReplayRefusedError, match="does not equal the state replayed"):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_an_altered_state_with_an_unchanged_transition_refuses() -> None:
    graph = _episode_a()
    state = graph.store.get(graph.states[-1])
    lifecycle = json.loads(json.dumps(state["position_lifecycle_record"]))
    lifecycle["stop_price"] = "1"
    forged = _republish(
        graph.store, graph.states[-1], position_lifecycle_record=lifecycle
    )
    with pytest.raises(ReplayRefusedError):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_an_altered_nav_refuses() -> None:
    graph = _episode_a()
    forged = _republish(graph.store, graph.states[-1], nav="999999")
    with pytest.raises(ReplayRefusedError, match="does not equal the state replayed"):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_a_cross_track_predecessor_refuses() -> None:
    graph = _episode_a()
    candidate_genesis = v2.build_portfolio_genesis_state(
        graph.store,
        track=v1.CANDIDATE_TRACK,
        corpus_sha256=CORPUS,
        slot=_hourly_slot(-1),
        symbol="BTCUSD",
        account_record=_account_record(),
    )
    forged_transition = _republish(
        graph.store,
        graph.transitions[0],
        prior_state_record_sha256=candidate_genesis,
    )
    forged_state = _republish(
        graph.store,
        graph.states[1],
        prior_state_record_sha256=candidate_genesis,
        producing_transition_record_sha256=forged_transition,
    )
    with pytest.raises(ReplayRefusedError, match="crosses portfolio tracks"):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=forged_state, corpus_sha256=CORPUS
        )


def test_a_stop_move_injected_without_a_current_position_installs_no_stop() -> None:
    """The authoritative owner refuses the event, so no stop can appear."""

    graph = _Graph()
    slot = _hourly_slot(1)
    transition = v2.build_portfolio_transition(
        graph.store,
        track=graph.track,
        corpus_sha256=CORPUS,
        slot=slot,
        prior_state_record_sha256=graph.genesis,
        position_events=[
            v2.position_event(
                event=sm.STOP_MOVE,
                event_time=slot.decision_time,
                stop_price="90000",
            )
        ],
        action_evidence_record_sha256=graph.action(slot),
        stop_evidence_record_sha256=graph.action(slot),
    )
    state = v2.build_portfolio_state(
        graph.store,
        corpus_sha256=CORPUS,
        slot=slot,
        prior_state_record_sha256=graph.genesis,
        producing_transition_record_sha256=transition,
    )
    replayed = v2.replay_portfolio_state(
        graph.store, state_record_sha256=state, corpus_sha256=CORPUS
    )
    assert replayed["stop_price"] is None
    lifecycle = replayed["position_lifecycle_record"]
    assert lifecycle["accepted"] is False
    assert "POSITION_STATE_TRANSITION_NOT_PERMITTED" in lifecycle["reason_codes"]
    # And a forged state that claims the stop anyway cannot replay.
    forged_lifecycle = json.loads(json.dumps(lifecycle))
    forged_lifecycle["stop_price"] = "90000"
    forged = _republish(
        graph.store, state, position_lifecycle_record=forged_lifecycle
    )
    with pytest.raises(ReplayRefusedError):
        v2.replay_portfolio_state(
            graph.store, state_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_a_forged_continuation_of_an_exited_position_refuses() -> None:
    graph = _episode_a()
    graph.step(
        6,
        [
            v2.position_event(
                event=sm.EXIT,
                event_time=_hourly_slot(6).decision_time,
                quantity="4",
                price="120000",
            )
        ],
    )
    slot = _hourly_slot(7)
    transition = v2.build_portfolio_transition(
        graph.store,
        track=graph.track,
        corpus_sha256=CORPUS,
        slot=slot,
        prior_state_record_sha256=graph.states[-1],
        position_events=[
            v2.position_event(
                event=sm.ADD,
                event_time=slot.decision_time,
                quantity="1",
                price="121000",
            )
        ],
        action_evidence_record_sha256=graph.action(slot),
        risk_evidence_record_sha256=graph.risk(slot),
    )
    state = v2.build_portfolio_state(
        graph.store,
        corpus_sha256=CORPUS,
        slot=slot,
        prior_state_record_sha256=graph.states[-1],
        producing_transition_record_sha256=transition,
    )
    replayed = v2.replay_portfolio_state(
        graph.store, state_record_sha256=state, corpus_sha256=CORPUS
    )
    lifecycle = replayed["position_lifecycle_record"]
    assert lifecycle["state"] == sm.CLOSED
    assert lifecycle["accepted"] is False
    assert "POSITION_STATE_TERMINAL" in lifecycle["reason_codes"]
    assert lifecycle["tranches"] == []


def test_opening_a_new_lifecycle_over_a_live_position_refuses() -> None:
    graph = _episode_a()
    slot = _hourly_slot(6)
    transition = v2.build_portfolio_transition(
        graph.store,
        track=graph.track,
        corpus_sha256=CORPUS,
        slot=slot,
        prior_state_record_sha256=graph.states[-1],
        opens_new_position_lifecycle=True,
        new_lifecycle_parameters={
            "direction": "long",
            "initial_state": sm.WATCH,
            "symbol": "BTCUSD",
        },
        position_events=_enter(6),
        action_evidence_record_sha256=graph.action(slot),
        stop_evidence_record_sha256=graph.action(slot),
        risk_evidence_record_sha256=graph.risk(slot),
    )
    with pytest.raises(ReplayRefusedError, match="forged continuation|terminal state"):
        v2.build_portfolio_state(
            graph.store,
            corpus_sha256=CORPUS,
            slot=slot,
            prior_state_record_sha256=graph.states[-1],
            producing_transition_record_sha256=transition,
        )


# =============================================================================
# 6. root lifecycle, active-stop lineage and exit/re-entry
# =============================================================================


def test_every_state_in_one_episode_derives_the_same_root_enter() -> None:
    graph = _episode_a()
    roots = [
        v2.derive_root_opening_transition(
            graph.store, state_record_sha256=state, corpus_sha256=CORPUS
        )
        for state in graph.states[1:]
    ]
    assert all(root["position_open"] for root in roots)
    identities = {root["root_opening_transition_sha256"] for root in roots}
    assert len(identities) == 1
    assert identities == {graph.transitions[0]}


def test_exit_then_reentry_produces_a_different_root() -> None:
    graph = _episode_a()
    root_a = v2.derive_root_opening_transition(
        graph.store, state_record_sha256=graph.states[-1], corpus_sha256=CORPUS
    )["root_opening_transition_sha256"]
    graph.step(
        6,
        [
            v2.position_event(
                event=sm.EXIT,
                event_time=_hourly_slot(6).decision_time,
                quantity="4",
                price="120000",
            )
        ],
    )
    flat = v2.derive_root_opening_transition(
        graph.store, state_record_sha256=graph.states[-1], corpus_sha256=CORPUS
    )
    assert flat["position_open"] is False
    assert flat["root_opening_transition_sha256"] is None
    graph.step(7, _enter(7, price="121000", stop="110000"), opens_new=True)
    root_b = v2.derive_root_opening_transition(
        graph.store, state_record_sha256=graph.states[-1], corpus_sha256=CORPUS
    )["root_opening_transition_sha256"]
    assert root_b is not None
    assert root_b != root_a


def test_stop_moves_inside_one_position_keep_one_root() -> None:
    graph = _episode_a()
    stops = [
        v2.derive_active_stop(
            graph.store, state_record_sha256=state, corpus_sha256=CORPUS
        )
        for state in graph.states[1:]
    ]
    assert [stop["active_stop"] for stop in stops] == [
        "90000",
        "92000",
        "94000",
        "94000",
        "94000",
    ]
    assert [stop["stop_advance_count"] for stop in stops] == [0, 1, 2, 2, 2]
    assert len({stop["root_opening_transition_sha256"] for stop in stops}) == 1


def test_no_stop_appears_without_a_producing_transition() -> None:
    graph = _episode_a()
    derived = v2.derive_active_stop(
        graph.store, state_record_sha256=graph.states[-1], corpus_sha256=CORPUS
    )
    installing = graph.store.get(derived["installing_transition_sha256"])
    assert installing["transition_class"] == v2.TRANSITION_CLASS_STOP_MOVE
    assert installing["stop_evidence_record_sha256"] is not None


def _stop_event_graph() -> tuple[_Graph, str, v2.DecisionSlot]:
    graph = _episode_a()
    slot = _hourly_slot(8)
    providers = [
        graph.store.put(
            v2.source_observation_record(
                corpus_sha256=CORPUS,
                series_id=v2.SERIES_CANONICAL_HOURLY_BAR,
                observation_time=slot.observation_time,
                available_at=slot.decision_time,
                value="93000",
                provider=provider,
            )
        )
        for provider in sorted(v1.REQUIRED_PROVIDER_IDS)
    ]
    event = v2.build_stop_event(
        graph.store,
        corpus_sha256=CORPUS,
        slot=slot,
        control_state_record_sha256=graph.states[-1],
        provider_observation_sha256s=providers,
        classification=v1.EVENT_CROSS_MARKET,
    )
    return graph, event, slot


def test_active_stop_membership_is_proved_from_the_graph() -> None:
    graph, event, _ = _stop_event_graph()
    proof = v2.prove_active_stop_membership(
        graph.store, stop_event_record_sha256=event, corpus_sha256=CORPUS
    )
    assert proof["membership_proved"] is True
    assert proof["active_stop"] == "94000"
    assert proof["root_opening_transition_sha256"] == graph.transitions[0]


def test_a_forged_active_stop_identity_refuses() -> None:
    graph, event, _ = _stop_event_graph()
    forged = _republish(graph.store, event, active_stop_identity="f" * 64)
    with pytest.raises(ReplayRefusedError, match="derived from the portfolio"):
        v2.prove_active_stop_membership(
            graph.store, stop_event_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_a_stop_from_another_position_refuses() -> None:
    graph, event, _ = _stop_event_graph()
    forged = _republish(graph.store, event, active_stop="90000")
    with pytest.raises(ReplayRefusedError, match="replayed active stop"):
        v2.prove_active_stop_membership(
            graph.store, stop_event_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_a_control_state_stamped_after_the_bar_refuses() -> None:
    graph = _episode_a()
    slot = _hourly_slot(5)
    with pytest.raises(ProspectiveCorpusV2Error):
        # The TRIM state is stamped at 05:05, after the 05:00 bar it would be
        # read onto, so it was not the stop in force while that bar formed.
        event = v2.build_stop_event(
            graph.store,
            corpus_sha256=CORPUS,
            slot=slot,
            control_state_record_sha256=graph.states[-1],
            provider_observation_sha256s=[],
        )
        v2.prove_active_stop_membership(
            graph.store, stop_event_record_sha256=event, corpus_sha256=CORPUS
        )
        raise ProspectiveCorpusV2Error("not refused")


def test_a_stop_event_may_not_be_anchored_to_the_candidate_track() -> None:
    graph, event, _ = _stop_event_graph()
    forged = _republish(graph.store, event, track=v1.CANDIDATE_TRACK)
    with pytest.raises(ReplayRefusedError, match="anchored to the control track"):
        v2.prove_active_stop_membership(
            graph.store, stop_event_record_sha256=forged, corpus_sha256=CORPUS
        )


# =============================================================================
# 7. the paired risk-sizing opportunity
# =============================================================================


def _sizing_pair(
    *,
    candidate_stop: str = "0.052",
    control_stop: str = "0.05",
    candidate_identity: str = "CANDIDATE_REF",
    control_identity: str = "CONTROL_REF",
    candidate_permitted: bool = True,
) -> tuple[EvidenceStore, v2.DecisionSlot, dict[str, str]]:
    store = EvidenceStore()
    slot = _daily_slot()
    records = {}
    for role, track, stop, identity, permitted in (
        (
            v1.CANDIDATE_REFERENCE_ROLE,
            v1.CANDIDATE_TRACK,
            candidate_stop,
            candidate_identity,
            candidate_permitted,
        ),
        (
            v1.CONTROL_REFERENCE_ROLE,
            v1.CONTROL_TRACK,
            control_stop,
            control_identity,
            True,
        ),
    ):
        records[role] = v2.build_risk_evaluation(
            store,
            corpus_sha256=CORPUS,
            slot=slot,
            track=track,
            reference_role=role,
            reference_identity=identity,
            sizing_inputs={
                "entry_price": "100000",
                "maximum_notional_fraction_nav": None,
                "nav": "1000000",
                "risk_fraction_nav": "0.005",
                "stop_distance_fraction": stop,
            },
            trade_permitted=permitted,
            input_record_sha256s=[],
        )
    return store, slot, records


def test_a_genuine_paired_sizing_opportunity_is_proved_from_evidence() -> None:
    store, slot, records = _sizing_pair()
    proof = v2.prove_paired_sizing_opportunity(
        store, slot=slot, corpus_sha256=CORPUS, risk_record_sha256_by_role=records
    )
    assert proof["opportunity_proved"] is True
    assert Decimal(proof["relative_difference"]) > 0
    assert len(set(proof["reference_identities"])) == 2


def test_the_risk_record_replays_to_the_sizing_owners_own_result() -> None:
    store, slot, records = _sizing_pair()
    replayed = v2.replay_risk_evaluation(
        store,
        risk_record_sha256=records[v1.CONTROL_REFERENCE_ROLE],
        corpus_sha256=CORPUS,
    )
    assert replayed["risk_size_complete"] is True
    assert Decimal(replayed["position_notional"]) == Decimal("1000000") * Decimal(
        "0.005"
    ) / Decimal("0.05")
    assert replayed["owner_record"]["policy_version"] == (
        v2.RISK_SIZING_OWNER_VERSION
    )


def test_a_tampered_notional_refuses_because_the_owner_is_re_run() -> None:
    store, _, records = _sizing_pair()
    record = store.get(records[v1.CONTROL_REFERENCE_ROLE])
    owner = json.loads(json.dumps(record["owner_record"]))
    owner["position_notional"] = "1"
    forged = _republish(
        store,
        records[v1.CONTROL_REFERENCE_ROLE],
        owner_record=owner,
        position_notional="1",
    )
    with pytest.raises(ReplayRefusedError, match="owner's replayed result"):
        v2.replay_risk_evaluation(
            store, risk_record_sha256=forged, corpus_sha256=CORPUS
        )


def test_an_identical_reference_identity_refuses() -> None:
    store, slot, records = _sizing_pair(candidate_identity="CONTROL_REF")
    with pytest.raises(ReplayRefusedError, match="REFERENCE_IDENTITY_NOT_DISTINCT"):
        v2.prove_paired_sizing_opportunity(
            store, slot=slot, corpus_sha256=CORPUS, risk_record_sha256_by_role=records
        )


def test_one_track_without_a_permitted_size_refuses() -> None:
    store, slot, records = _sizing_pair(candidate_permitted=False)
    with pytest.raises(
        ReplayRefusedError, match="ONE_TRACK_PRODUCED_NO_POSITIVE_RISK_SIZE"
    ):
        v2.prove_paired_sizing_opportunity(
            store, slot=slot, corpus_sha256=CORPUS, risk_record_sha256_by_role=records
        )


def test_an_incomplete_pair_refuses() -> None:
    store, slot, records = _sizing_pair()
    with pytest.raises(ReplayRefusedError, match="SIZING_PAIR_INCOMPLETE"):
        v2.prove_paired_sizing_opportunity(
            store,
            slot=slot,
            corpus_sha256=CORPUS,
            risk_record_sha256_by_role={
                v1.CONTROL_REFERENCE_ROLE: records[v1.CONTROL_REFERENCE_ROLE]
            },
        )


def test_a_risk_record_from_another_slot_refuses() -> None:
    store, slot, records = _sizing_pair()
    other = v2.decision_slot(v1.STRATEGY_DAILY_CADENCE, ANCHOR - timedelta(days=1))
    with pytest.raises(ReplayRefusedError, match="another slot"):
        v2.prove_paired_sizing_opportunity(
            store, slot=other, corpus_sha256=CORPUS, risk_record_sha256_by_role=records
        )


def test_trade_permitted_may_not_be_null() -> None:
    store = EvidenceStore()
    slot = _daily_slot()
    with pytest.raises(ProspectiveCorpusV2Error, match="strict Boolean"):
        v2.build_risk_evaluation(
            store,
            corpus_sha256=CORPUS,
            slot=slot,
            track=v1.CONTROL_TRACK,
            reference_role=v1.CONTROL_REFERENCE_ROLE,
            reference_identity="CONTROL_REF",
            sizing_inputs={
                "entry_price": "100000",
                "maximum_notional_fraction_nav": None,
                "nav": "1000000",
                "risk_fraction_nav": "0.005",
                "stop_distance_fraction": "0.05",
            },
            trade_permitted=None,
            input_record_sha256s=[],
        )
    assert v1.data_schema_contract()["tables"]["prospective_risk_evaluation"][
        "columns"
    ]["trade_permitted"].endswith("null")
    assert v2.data_schema_contract_v2()["tables"]["prospective_risk_evaluation_v2"][
        "columns"
    ]["trade_permitted"] == "boolean not null"


# =============================================================================
# 8. slot evidence manifest closure
# =============================================================================


def test_a_slot_manifest_carries_references_and_never_conclusions() -> None:
    contract = v2.slot_evidence_manifest_contract()
    assert contract["conclusion_fields_permitted"] is False
    refused = set(contract["conclusion_fields_refused"])
    assert {
        "warmup_history_complete",
        "quality_state",
        "universe_member",
        "comparability",
        "control_root_position_sha256",
        "active_stop_identity",
        "sizing_opportunity",
    } <= refused
    assert not refused & set(v2.SLOT_EVIDENCE_MANIFEST_FIELDS)


def test_a_slot_manifest_with_a_conclusion_field_refuses(census) -> None:
    store, slot, manifests = _owner_graph(census, ("RV_20",))
    manifest = v2.build_slot_evidence_manifest(
        store,
        slot=slot,
        corpus_sha256=CORPUS,
        owner_history_manifest_sha256s=manifests,
    )
    record = store.get(manifest)
    record.pop(v2.DIGEST_FIELD)
    record["quality_state"] = "OK"
    forged = store.put(record)
    with pytest.raises(ReplayRefusedError, match="may not carry the conclusion"):
        v2.replay_slot_evidence_manifest(
            store,
            manifest_sha256=forged,
            slot=slot,
            corpus_sha256=CORPUS,
            census=census,
        )


def test_the_generic_input_snapshot_is_a_convenience_not_the_evidence_root() -> None:
    assert v2.INPUT_SNAPSHOT_ROLE == (
        "QUERY_CONVENIENCE_INDEX_NOT_THE_TOTAL_SCIENTIFIC_EVIDENCE_ROOT"
    )
    contract = v2.slot_evidence_manifest_contract()
    assert contract["input_snapshot_role"] == v2.INPUT_SNAPSHOT_ROLE
    assert contract["self_consistent_manifest_with_omitted_history"] == "REFUSE"


def test_a_decision_observation_binds_the_slot_manifest_root(census) -> None:
    store, slot, manifests = _owner_graph(
        census, tuple(_feature_matrix.INITIAL_FEATURE_NAMES)
    )
    manifest = v2.build_slot_evidence_manifest(
        store,
        slot=slot,
        corpus_sha256=CORPUS,
        owner_history_manifest_sha256s=manifests,
    )
    observation = v2.build_decision_observation(
        store,
        corpus_sha256=CORPUS,
        slot=slot,
        slot_evidence_manifest_sha256=manifest,
        strategy_identity_sha256=v2._digest({"strategy": "SYNTHETIC"}),
        observation_state=v1.STATE_EVALUATED,
        cached_projections={"warmup_history_state": WARMUP_STATE_COMPLETE},
    )
    replayed = v2.replay_decision_observation(
        store, observation_sha256=observation, slot=slot, corpus_sha256=CORPUS,
        census=census,
    )
    assert replayed["derived_warmup_state"] == WARMUP_STATE_COMPLETE
    record = store.get(observation)
    assert record["slot_evidence_manifest_sha256"] == manifest
    assert "warmup_history_complete" not in record


def test_a_decision_observation_with_a_wrong_cached_warmup_refuses(census) -> None:
    store, slot, manifests = _owner_graph(
        census, tuple(_feature_matrix.INITIAL_FEATURE_NAMES)
    )
    manifest = v2.build_slot_evidence_manifest(
        store,
        slot=slot,
        corpus_sha256=CORPUS,
        owner_history_manifest_sha256s=manifests,
    )
    observation = v2.build_decision_observation(
        store,
        corpus_sha256=CORPUS,
        slot=slot,
        slot_evidence_manifest_sha256=manifest,
        strategy_identity_sha256=v2._digest({"strategy": "SYNTHETIC"}),
        observation_state=v1.STATE_EVALUATED,
        cached_projections={"warmup_history_state": WARMUP_STATE_INCOMPLETE},
    )
    with pytest.raises(ReplayRefusedError, match="disagrees with the replayed"):
        v2.replay_decision_observation(
            store,
            observation_sha256=observation,
            slot=slot,
            corpus_sha256=CORPUS,
            census=census,
        )


# =============================================================================
# 9. metric and feature replay closure
# =============================================================================


def test_all_eight_stage_b_metrics_are_replayable() -> None:
    matrix = v2.metric_replay_closure_matrix()
    assert matrix["replayable_ratio"] == "8/8"
    assert set(matrix["rows"]) == set(v1.TARGET_METRICS)
    for metric, row in matrix["rows"].items():
        assert row["replayable"] == "YES", metric
        assert row["universe_predicate_replayable"] is True
        assert row["comparability_predicate_replayable"] is True
        assert row["denominator_membership_predicate_replayable"] is True
        assert row["required_v2_evidence_references"]
        assert row["replay_owners"]
    assert matrix["governance_authored_conclusions_required"] is False


def test_the_metric_matrix_carries_the_frozen_gate_numbers_unchanged() -> None:
    authority = v1.historical_gate_authority()
    for metric, row in v2.metric_replay_closure_matrix()["rows"].items():
        assert row["threshold"] == authority[metric]["threshold"]
        assert row["direction"] == authority[metric]["direction"]
        assert row["hard"] == authority[metric]["hard"]
        assert row["universe"] in v1.DECISION_UNIVERSES


@pytest.mark.parametrize("metric", sorted(v1.TARGET_METRICS))
def test_every_metric_names_a_real_v2_evidence_reference(metric) -> None:
    row = v2.metric_replay_closure_matrix()["rows"][metric]
    for reference in row["required_v2_evidence_references"]:
        kind, _, field = reference.partition(".")
        assert kind in v2.RECORD_KINDS, reference
        fields = {
            v2.SLOT_EVIDENCE_MANIFEST_KIND: v2.SLOT_EVIDENCE_MANIFEST_FIELDS,
            v2.OWNER_HISTORY_MANIFEST_KIND: v2.OWNER_HISTORY_MANIFEST_FIELDS,
            v2.PORTFOLIO_STATE_KIND: v2.PORTFOLIO_STATE_FIELDS,
            v2.PORTFOLIO_TRANSITION_KIND: v2.PORTFOLIO_TRANSITION_FIELDS,
            v2.RISK_EVALUATION_KIND: v2.RISK_EVALUATION_FIELDS,
            v2.STOP_EVENT_KIND: v2.STOP_EVENT_FIELDS,
        }[kind]
        assert field in fields, reference
    for owner in row["replay_owners"]:
        assert hasattr(v2, owner.rsplit(".", 1)[1]), owner


def test_all_thirty_three_features_are_replayable() -> None:
    matrix = v2.feature_replay_closure_matrix()
    assert matrix["replayable_ratio"] == "33/33"
    assert set(matrix["rows"]) == set(_feature_matrix.INITIAL_FEATURE_NAMES)
    for feature, row in matrix["rows"].items():
        assert row["replayable"] == "YES", feature
        assert row["exact_input_history_reference"]
        assert row["source_identity_reference"]
        assert row["pit_valid_revision_reference"]
        assert row["evaluability_predicate"]
        assert row["resulting_value_reference"]


@pytest.mark.parametrize(
    "owner_class", sorted(v2.OWNER_CLASSES)
)
def test_one_representative_owner_of_every_class_replays(census, owner_class) -> None:
    """Every distinct owner class is exercised, not just the convenient ones."""

    members = census["owners_by_class"][owner_class]
    assert members, owner_class
    feature = members[0]
    store, slot, manifests = _owner_graph(census, (feature,))
    result = v2.replay_owner_history_manifest(
        store,
        manifest_sha256=manifests[feature],
        slot=slot,
        corpus_sha256=CORPUS,
        census=census,
    )
    assert result["evaluability_state"] == EVALUABLE, feature
    assert result["owner_class"] == owner_class


@pytest.mark.parametrize("owner_class", sorted(v2.OWNER_CLASSES))
def test_a_missing_required_history_gives_the_frozen_missing_behavior(
    census, owner_class
) -> None:
    feature = census["owners_by_class"][owner_class][0]
    selector = census["rows"][feature]["evidence_selector"]
    if selector["series_kind"] == v2.SERIES_KIND_COMPONENTS:
        pytest.skip("a composite inherits its components' behavior")
    store, slot, original = _owner_graph(census, (feature,))
    kind = (
        v2.DERIVED_FEATURE_KIND
        if selector["series_kind"] == v2.SERIES_KIND_DERIVED
        else v2.SOURCE_OBSERVATION_KIND
    )
    key = "feature" if kind == v2.DERIVED_FEATURE_KIND else "series_id"
    matching = [
        record
        for record in store.of_kind(kind)
        if record[key] == selector["series_id"]
    ]
    assert matching, feature
    store._records.pop(
        max(matching, key=lambda record: record[v2.OBSERVATION_TIME_FIELD])[
            v2.DIGEST_FIELD
        ]
    )

    # Removing one required record must be detectable. The already-persisted
    # manifest now disagrees with the independently recomputed expected set, so
    # it refuses -- that alone is the detection the ticket requires.
    with pytest.raises(ReplayRefusedError):
        v2.replay_owner_history_manifest(
            store,
            manifest_sha256=original[feature],
            slot=slot,
            corpus_sha256=CORPUS,
            census=census,
        )

    # A manifest rebuilt over the damaged store is self-consistent again, and
    # then the owner's own predicate decides. Some owners need only one
    # observation in their window, so a shortened history stays evaluable; that
    # is the owner's frozen behavior and V2 must not invent a stricter one.
    manifests = v2.build_slot_owner_history_graph(
        store, slot=slot, corpus_sha256=CORPUS, census=census, features=(feature,)
    )
    result = v2.replay_owner_history_manifest(
        store,
        manifest_sha256=manifests[feature],
        slot=slot,
        corpus_sha256=CORPUS,
        census=census,
    )
    assert result["evaluability_state"] in (EVALUABLE, NOT_EVALUABLE)
    assert set(result["reason_codes"]) <= set(v2.EVALUABILITY_REASON_CODES)
    if result["evaluability_state"] == NOT_EVALUABLE:
        assert result["reason_codes"], feature
    else:
        assert int(selector["minimum_count"] or 0) <= 1, (
            f"{feature} stayed evaluable after losing required history"
        )


# =============================================================================
# 10. content-addressed immutability
# =============================================================================


def test_a_caller_may_not_assert_a_record_identity() -> None:
    store = EvidenceStore()
    with pytest.raises(ProspectiveCorpusV2Error, match="identity is computed"):
        store.put(
            {
                v2.RECORD_KIND_FIELD: v2.SOURCE_OBSERVATION_KIND,
                v2.SCHEMA_VERSION_FIELD: v2.RECORD_SCHEMA_VERSIONS[
                    v2.SOURCE_OBSERVATION_KIND
                ],
                v2.DIGEST_FIELD: "0" * 64,
            }
        )


@pytest.mark.parametrize(
    ("builder", "field", "value"),
    [
        ("history", "observation_record_sha256s", []),
        ("history", "owner_contract_sha256", "a" * 64),
        ("history", "slot_id", "b" * 64),
        ("history", "evidence_selector", {}),
        ("state", "prior_state_record_sha256", "c" * 64),
        ("state", "producing_transition_record_sha256", "d" * 64),
        ("state", "nav", "1"),
        ("transition", "prior_state_record_sha256", "e" * 64),
        ("transition", "transition_type", sm.HOLD),
        ("source", "value", "12345"),
        ("source", "available_at", "2020-01-01T00:00:00+00:00"),
    ],
)
def test_changing_any_material_field_moves_the_record_identity(
    census, builder, field, value
) -> None:
    if builder in {"history", "source"}:
        store, slot, manifests = _owner_graph(census, ("RV_20",))
        if builder == "history":
            original = manifests["RV_20"]
        else:
            original = store.get(manifests["RV_20"])[
                "observation_record_sha256s"
            ][0]
    else:
        graph = _episode_a()
        store = graph.store
        original = graph.states[-1] if builder == "state" else graph.transitions[-1]
    moved = _republish(store, original, **{field: value})
    assert moved != original


def test_the_store_refuses_a_record_that_does_not_re_digest(census) -> None:
    store, _, manifests = _owner_graph(census, ("RV_20",))
    sha = manifests["RV_20"]
    store._records[sha] = {**store._records[sha], "owner_id": "TAMPERED"}
    with pytest.raises(ReplayRefusedError, match="does not re-digest"):
        store.get(sha)


def test_the_immutability_rule_is_frozen_in_the_parent() -> None:
    rule = v2.protocol_definition()["content_addressed_immutability"]
    assert set(rule["identity_moves_when_any_of_these_change"]) == {
        "a history reference",
        "a predecessor state",
        "a transition",
        "a source record",
        "an owner contract",
        "a slot identity",
    }


# =============================================================================
# 11. determinism
# =============================================================================


def test_the_parent_hash_is_invariant_to_the_ambient_decimal_context() -> None:
    baseline = v2.protocol_definition()["definition_sha256"]
    for precision in (3, 20, 50, 200):
        with localcontext(Context(prec=precision)):
            assert v2.protocol_definition()["definition_sha256"] == baseline


def test_every_v2_record_hash_is_invariant_to_the_ambient_decimal_context(
    census,
) -> None:
    def build() -> dict[str, str]:
        graph = _episode_a()
        store, slot, manifests = _owner_graph(census, ("RV_20", "VOL_PERCENTILE_2Y"))
        _, _, risk = _sizing_pair()
        return {
            "manifest": manifests["VOL_PERCENTILE_2Y"],
            "risk": risk[v1.CONTROL_REFERENCE_ROLE],
            "state": graph.states[-1],
            "transition": graph.transitions[-1],
        }

    baseline = build()
    for precision in (3, 20, 50, 200):
        with localcontext(Context(prec=precision)):
            assert build() == baseline, precision


def test_the_acceptance_demonstration_is_invariant_to_the_decimal_context() -> None:
    baseline = v2.demonstrate_parent_completeness()
    for precision in (3, 20, 50, 200):
        with localcontext(Context(prec=precision)):
            assert v2.demonstrate_parent_completeness() == baseline


def test_the_parent_hash_is_invariant_to_hash_seed_and_working_directory(
    tmp_path: Path,
) -> None:
    expected = v2.protocol_definition()["definition_sha256"]
    script = (
        "import json, sys;"
        "from btc_predictor.research import prospective_integration_corpus_v2 as c;"
        "print(json.dumps(c.protocol_hashes()))"
    )
    for seed, cwd in (("0", REPOSITORY_ROOT), ("12345", tmp_path), ("7", tmp_path)):
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            cwd=cwd,
            env={
                **os.environ,
                "PYTHONHASHSEED": seed,
                "PYTHONPATH": str(REPOSITORY_ROOT),
            },
            text=True,
        )
        assert result.returncode == 0, result.stderr
        assert json.loads(result.stdout)["corpus_protocol_v2"] == expected


def test_the_parent_hash_is_invariant_to_input_ordering(census) -> None:
    baseline = v2.protocol_definition()["definition_sha256"]
    # A permuted owner ordering must not move the census or the parent, because
    # every payload is canonically sorted before it is hashed.
    permuted = dict(reversed(list(census["rows"].items())))
    assert v2._digest(permuted) == v2._digest(census["rows"])
    assert v2.protocol_definition()["definition_sha256"] == baseline


def test_the_child_registry_is_mechanically_enumerated_and_unique() -> None:
    filenames = [filename for filename, _ in v2._CHILD_ARTIFACTS]
    builders = [builder for _, builder in v2._CHILD_ARTIFACTS]
    assert len(filenames) == len(set(filenames))
    assert len(builders) == len(set(builders))
    for builder in builders:
        assert callable(getattr(v2, builder))
    protocol = v2.protocol_definition()
    assert protocol["material_child_count"] == len(filenames)
    assert set(protocol["child_definition_sha256"]) == {
        name[: -len(".json")] for name in filenames
    }


# =============================================================================
# 12. semantic parity and the V1 / historical regression
# =============================================================================


def test_v2_changes_no_trading_source_metric_risk_or_stop_science() -> None:
    diff = v2.semantic_diff_v1_to_v2()
    assert diff["changes"] == {
        "acquisition_source_changes": 0,
        "decision_rule_changes": 0,
        "feature_formula_changes": 0,
        "metric_intent_changes": 0,
        "risk_changes": 0,
        "stage_b_direction_changes": 0,
        "stage_b_hard_role_changes": 0,
        "stage_b_threshold_changes": 0,
        "stop_event_definition_changes": 0,
    }
    assert all(value == 0 for value in diff["expected_semantic_parity_with_v1"].values())
    assert diff["v2_changes_are_evidence_architecture_only"] is True
    assert set(diff["permitted_v2_changes"]) == set(v2.PERMITTED_V2_CHANGES)


def test_the_semantic_diff_is_recomputed_not_asserted() -> None:
    rows = v2.semantic_diff_v1_to_v2()["metric_parity"]
    authority = v1.historical_gate_authority()
    assert set(rows) == set(v1.TARGET_METRICS)
    for metric, row in rows.items():
        assert row["threshold"] == authority[metric]["threshold"]
        assert row["threshold_changed"] is False
        assert row["direction_changed"] is False
        assert row["hard_role_changed"] is False
        assert row["metric_intent_changed"] is False


def test_the_semantic_diff_refuses_a_live_gate_drift(monkeypatch) -> None:
    authority = v1.historical_gate_authority()
    metric = sorted(v1.TARGET_METRICS)[0]
    authority[metric] = {**authority[metric], "threshold": "0.0001_TAMPERED"}
    monkeypatch.setattr(v1, "historical_gate_authority", lambda: authority)

    with pytest.raises(
        ProspectiveCorpusV2Error, match="stage_b_threshold_changes"
    ):
        v2.semantic_diff_v1_to_v2()


def test_v2_reuses_the_certified_source_layer_unchanged() -> None:
    reuse = v2.source_evidence_reuse_contract()
    assert reuse["redesigned"] is False
    assert reuse["certified_parent_sha256"] == v2.PARENT_V1_DEFINITION_SHA256
    children = v1.protocol_definition()["child_definition_sha256"]
    for name, sha256 in reuse["reused_child_sha256"].items():
        assert children[name] == sha256
    assert reuse["v2_resolver_extension"]["changes_source_semantics"] is False
    assert reuse["reused_child_count"] >= 14


def test_the_certified_v1_parent_and_its_children_are_unchanged() -> None:
    hashes = v1.protocol_hashes()
    assert hashes["corpus_protocol"] == (
        "8915d991fde536450a959a350f1a619544289ea0b9544f308b184cf7fbfac7d7"
    )
    assert len(hashes) - 1 == 25
    protocol = v1.protocol_definition()
    assert protocol["material_child_count"] == 25
    assert protocol["protocol_version"] == "PROSPECTIVE_INTEGRATION_CORPUS_V1"


def test_the_persisted_v1_artifacts_still_reproduce() -> None:
    protocol = v1.restore_artifacts(V1_ARTIFACT_DIR)
    assert protocol["definition_sha256"] == v2.PARENT_V1_DEFINITION_SHA256


def test_v2_binds_every_v1_child_and_mutates_none() -> None:
    bindings = v2.inherited_v1_child_bindings()
    children = v1.protocol_definition()["child_definition_sha256"]
    assert bindings["certified_parent_child_count"] == 25
    assert set(bindings["rows"]) == set(children)
    for name, row in bindings["rows"].items():
        assert row["v1_definition_sha256"] == children[name]
    assert bindings["v1_mutated"] is False
    assert bindings["v1_artifact_directory"] != bindings["v2_artifact_directory"]
    total = (
        bindings["reused_unchanged_count"]
        + bindings["extended_count"]
        + bindings["superseded_count"]
    )
    assert total == 25


def test_v2_refuses_a_v1_child_that_moved_behind_the_parent_claim(monkeypatch) -> None:
    parent = v1.protocol_definition()
    children = dict(parent["child_definition_sha256"])
    child = sorted(children)[0]
    children[child] = "0" * 64
    parent["child_definition_sha256"] = children
    monkeypatch.setattr(v1, "protocol_definition", lambda: parent)

    with pytest.raises(ProspectiveCorpusV2Error, match="children moved"):
        v2.inherited_v1_child_bindings()


def test_the_historical_authorities_are_preserved() -> None:
    lineage = v2.protocol_definition()["lineage"]
    assert lineage["frozen_v3_definition_sha256"] == (
        "4232e886e7888b85833f778fcba6b2cb3eb5b7d802748aebf3b8adf19c5bf71a"
    )
    assert lineage["certified_v1_validator_definition_sha256"] == (
        "8e6254e0354c04de077bf482ccb6852bfe4299f138d3c97f1ba33859bfc7ffe7"
    )
    assert lineage["frozen_v4_definition_sha256"] == (
        "670ff12dd3d63615e9ddb3be05d65505bab16b50e50f1fd9ad077a4923a3f501"
    )
    assert lineage["frozen_v5_definition_sha256"] == (
        "95e43ee10441909f710e3efbb85e196ba5fb6ed536e9902570eeb42605775a89"
    )
    assert v2.protocol_definition()["btc019"]["terminal_classification"] == (
        "BTC019_TERMINALLY_BLOCKED_BY_MISSING_INTEGRATION_EVIDENCE"
    )


def test_v2_persists_nothing_inside_the_frozen_v5_json_census() -> None:
    """One new artifact under ``data/`` or ``research_artifacts/`` would move V5."""

    assert not v2.OUTPUT_NAMESPACE.startswith("research_artifacts/")
    assert not v2.OUTPUT_NAMESPACE.startswith("data/")
    assert list(ARTIFACT_DIR.glob("*.json"))
    script = (
        "from pathlib import Path;"
        "from btc_predictor.research import reference_composite_v5 as v5;"
        "print(v5.v5_protocol_definition(Path('.'))['definition_sha256'])"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        cwd=REPOSITORY_ROOT,
        env={**os.environ, "PYTHONPATH": str(REPOSITORY_ROOT)},
        text=True,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == v2.FROZEN_V5_DEFINITION_SHA256


# =============================================================================
# 13. persisted artifacts
# =============================================================================


def test_the_persisted_v2_artifacts_reproduce_from_the_module() -> None:
    protocol = v2.restore_artifacts(ARTIFACT_DIR)
    assert protocol["definition_sha256"] == (
        v2.protocol_definition()["definition_sha256"]
    )
    assert protocol["protocol_version"] == v2.PROTOCOL_VERSION
    assert protocol["final_classification"] == v2.FINAL_CLASSIFICATION


def test_writing_the_v2_artifacts_is_deterministic(tmp_path: Path) -> None:
    v2.write_artifacts(tmp_path)
    first = {path.name: path.read_bytes() for path in sorted(tmp_path.iterdir())}
    v2.write_artifacts(tmp_path)
    second = {path.name: path.read_bytes() for path in sorted(tmp_path.iterdir())}
    assert first == second
    assert len(first) == len(v2._CHILD_ARTIFACTS) + 2


def test_a_tampered_persisted_parent_is_refused(tmp_path: Path) -> None:
    protocol = v2.protocol_definition()
    tampered = json.loads(json.dumps(protocol))
    tampered["status"] = "CERTIFIED"
    tampered.pop("definition_sha256")
    tampered["definition_sha256"] = v2._digest(tampered)
    with pytest.raises(ProspectiveCorpusV2Error, match="does not reproduce"):
        v2.verify_protocol_definition(tampered)


def test_a_tampered_persisted_child_is_refused(tmp_path: Path) -> None:
    v2.write_artifacts(tmp_path)
    target = tmp_path / "metric_replay_closure_matrix.json"
    payload = json.loads(target.read_text(encoding="ascii"))
    payload["replayable_ratio"] = "7/8"
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", "ascii")
    with pytest.raises(ProspectiveCorpusV2Error, match="does not reproduce"):
        v2.restore_artifacts(tmp_path)


def test_the_report_reproduces_and_names_the_key_results(tmp_path: Path) -> None:
    v2.write_artifacts(tmp_path)
    report = (tmp_path / v2.REPORT_FILENAME).read_text(encoding="utf-8")
    assert v2.protocol_definition()["definition_sha256"] in report
    assert v2.PARENT_V1_DEFINITION_SHA256 in report
    assert "8/8" in report
    assert "33/33" in report
    assert v2.FINAL_CLASSIFICATION in report


# =============================================================================
# 14. the parent-completeness acceptance
# =============================================================================


def test_every_required_blind_fact_is_derivable_from_the_parent_graph() -> None:
    acceptance = v2.parent_completeness_acceptance()
    assert set(acceptance["required_blind_facts"]) == set(v2.REQUIRED_BLIND_FACTS)
    assert acceptance["invented_outside_the_parent_graph"] == []
    assert set(acceptance["surrogate_authorities_not_required"]) == {
        "active_stop_membership",
        "comparability Boolean",
        "control root SHA",
        "quality_state",
        "sizing-opportunity Boolean",
        "universe Boolean",
        "warmup Boolean",
    }
    demonstration = acceptance["demonstration"]
    assert demonstration["derived_warmup_state"] == WARMUP_STATE_COMPLETE
    assert demonstration["owner_history_manifest_count"] == 33
    assert demonstration["stop_membership_proved"] is True
    assert demonstration["stop_replay_membership_proved"] is True
    assert demonstration["root_opening_transition_sha256"] == (
        demonstration["stop_membership_root_sha256"]
    )
    assert Decimal(demonstration["sizing_relative_difference"]) > 0
    assert demonstration["evidence_record_count"] > 500


def test_the_replay_registry_binds_every_executable_owner() -> None:
    registry = v2.parent_replay_contract_registry()
    assert registry["contract_count"] == len(v2._REPLAY_CONTRACTS)
    for identity, row in registry["contracts"].items():
        assert callable(getattr(v2, identity))
        assert row["failure_semantics"] == "REFUSE"
        assert row["selection_semantics"]
        assert row["required_evidence_schemas"]
        assert v2._is_sha256(row["owner_contract_sha256"])
        recomputed = {k: v for k, v in row.items() if k != "owner_contract_sha256"}
        assert v2._digest(recomputed) == row["owner_contract_sha256"]


def test_the_replay_registry_covers_the_whole_replay_surface() -> None:
    registry = set(v2.parent_replay_contract_registry()["contracts"])
    assert {
        "expected_owner_evidence",
        "evaluate_owner_predicate",
        "replay_owner_history_manifest",
        "replay_decision_evaluability",
        "replay_portfolio_state",
        "derive_root_opening_transition",
        "prove_active_stop_membership",
        "replay_risk_evaluation",
        "prove_paired_sizing_opportunity",
        "replay_slot_evidence_manifest",
        "replay_decision_observation",
    } <= registry


# =============================================================================
# 15. safety and the blocked successors
# =============================================================================


def test_collection_and_postp1_004_remain_unauthorized() -> None:
    protocol = v2.protocol_definition()
    assert protocol["collection_authorized"] is False
    assert v2.COLLECTION_AUTHORIZED is False
    assert v2.POSTP1_004_AUTHORIZED is False
    epoch = v2.collection_epoch_contract()
    assert epoch["collection_authorized"] is False
    assert epoch["postp1_004_authorized"] is False
    assert epoch["preconditions_in_order"] == [
        "V2 implementation",
        "exact-hash independent xHigh review PASS",
        "sufficiency governance reissued against V2",
        "sufficiency governance exact-hash review PASS",
        "POSTP1-004 implementation",
        "POSTP1-004 independent review PASS",
    ]
    assert epoch["v1_evidence_counts_toward_v2_sufficiency"] is False
    assert epoch["v1_migration_required"] is False
    assert epoch["v1_observation_fabrication_permitted"] is False
    v2.assert_collection_not_authorized()


def test_no_new_sufficiency_governance_hash_is_issued_here() -> None:
    governance = v2.protocol_definition()["sufficiency_governance"]
    assert governance["new_governance_hash_issued_here"] is False
    assert governance["postp1_003r3_blocked_pending_v2_review"] is True
    assert governance["postp1_003r3_rules_unchanged"] == "381 / 93 / 0.99"
    assert governance["failed_hashes_retained_non_authoritative"] == [
        "3f51c4d9d8f14689b3f6c863e1731a6ef170b9764162b79bd56cc369af4ae2c7",
        "0ca7a2a8487e9c54b1b0f5ad07201ec39dfd20b328b5e09cb3b51b0de86c8242",
        "0c0c0f96bc68afee0cbecc285546e0721e6fc621b09354af079adffd5863c64e",
    ]
    assert set(governance["postp1_003r3_must_then"]) == {
        "bind the V2 parent",
        "perform true owner-level replay",
        "bind executable semantics",
        "enforce canonical candidate/control identity",
    }


def test_btc019_and_epic_t_are_untouched() -> None:
    protocol = v2.protocol_definition()
    assert protocol["btc019"]["reopened"] is False
    assert protocol["btc019"]["sealed_data_accessed"] is False
    assert protocol["btc019"]["sealed_sample_collected"] is False
    assert protocol["btc019"]["sealed_sample_opened"] is False
    assert protocol["relationship_to_epic_t"]["epic_t_modified"] is False
    assert protocol["relationship_to_epic_t"]["epic_t_re_review_required"] is False
    assert protocol["safety"]["qualifying_observations_collected"] is False
    assert protocol["safety"]["real_stage_b_evaluated"] is False
    assert protocol["safety"]["persistent_live_collection_started"] is False
    assert protocol["safety"]["synthetic_evidence_only"] is True


def test_the_parent_states_its_primary_requirement_and_required_facts() -> None:
    protocol = v2.protocol_definition()
    assert "without trusting a Boolean" in protocol["primary_requirement"]
    assert set(protocol["required_replayable_facts"]) == set(v2.REQUIRED_BLIND_FACTS)
    assert len(protocol["required_replayable_facts"]) == 9


# =============================================================================
# 16. the suite proves it opens nothing sealed or collected
# =============================================================================

_AUDIT_DRIVER = """
import os
import sys

observed = []
violations = []
module_path = os.path.abspath(sys.argv[1])
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
    if os.path.isfile(resolved):
        violations.append(text)


sys.addaudithook(_hook)

import pytest

code = pytest.main(['-q', '-p', 'no:cacheprovider', module_path])
marker = 'PROSPECTIVE' + '_V2_AUDIT'
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
def test_the_whole_suite_opens_no_sealed_or_collected_path(tmp_path: Path) -> None:
    """Run this entire module under an audit hook on every ``open``.

    A pre-data parent must be provable, not merely asserted: nothing in this
    suite may reach the BTC-019 sealed window or any collected market data.
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
    assert result.returncode == 0, tail
    marker = "PROSPECTIVE" + "_V2_AUDIT"
    assert f"{marker}_BEGIN" in result.stdout, tail
    body = result.stdout.rsplit(f"{marker}_BEGIN", 1)[1]
    violations = [
        line for line in body.rsplit(f"{marker}_END", 1)[0].splitlines() if line.strip()
    ]
    assert violations == [], f"the suite opened sealed or collected paths: {violations}"
    observed = int(
        next(
            line for line in result.stdout.splitlines() if line.startswith(f"{marker}_OPENS")
        ).split()[-1]
    )
    # A positive control: an empty observation set would make the proof vacuous.
    assert observed > 0
