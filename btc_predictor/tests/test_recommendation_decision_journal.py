import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.db import RECOMMENDATION_DECISIONS, recommendation_decisions
from btc_predictor.journal import (
    DECISION_JOURNAL_FEATURE_ID,
    DECISION_JOURNAL_POLICY_VERSION,
    DECISION_JOURNAL_REASON_CODES,
    MODIFIABLE_ADVISORY_FIELDS,
    ORDER_BEARING_ACTIONS,
    RecommendationDecisionEntry,
    journal_recommendation_decision,
    recommendation_decision_from_record,
    verify_decision_entry,
)
from btc_predictor.portfolio import (
    ENTER,
    PENDING_ENTRY,
    apply_position_event,
    start_position_lifecycle,
)
from btc_predictor.reporting import (
    render_json_output,
    render_position_management_report,
    render_recommendation,
)
from btc_predictor.risk import (
    HIGHER_LOW,
    calculate_risk_at_stop,
    calculate_trailing_stop,
)


EVALUATION_TIME = datetime(2026, 8, 31, tzinfo=timezone.utc)
DECIDED_AT = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)


def _recommendation(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "recommendation_id": 200,
        "run_id": 42,
        "evaluation_time": EVALUATION_TIME,
        "symbol": "BTC/USD",
        "timeframe": "1d",
        "regime": "BULL",
        "setup": "BULLISH_RESET",
        "direction": "long",
        "trend_score": Decimal("82"),
        "regime_score": Decimal("72"),
        "flow_score": Decimal("87"),
        "positioning_score": Decimal("84"),
        "volatility_score": Decimal("71"),
        "structure_score": Decimal("94"),
        "entry_conviction": Decimal("88"),
        "hold_score": None,
        "add_score": Decimal("86.25"),
        "entry_zone_lower": Decimal("98500"),
        "entry_zone_upper": Decimal("101000"),
        "invalidation_level": Decimal("91300"),
        "initial_stop": Decimal("89800"),
        "rr_ratio": Decimal("3.2"),
        "risk_fraction_nav": Decimal("0.005"),
        "risk_amount": Decimal("500"),
        "suggested_notional": Decimal("5100"),
        "action": "ENTER",
    }
    row.update(changes)
    return row


def _reason_rows(recommendation_id: int = 200) -> tuple[dict[str, object], ...]:
    return (
        {
            "recommendation_id": recommendation_id,
            "reason_rank": 0,
            "code": "TREND_12W_POSITIVE",
            "source_component": "trend",
            "severity": "info",
            "detail": "Twelve-week momentum is positive.",
        },
    )


def _predictor_run(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "run_id": 42,
        "evaluation_time": EVALUATION_TIME,
        **load_strategy_config().run_metadata(),
    }
    row.update(changes)
    return row


def _advisory(**changes: object):
    recommendation = _recommendation(**changes)
    return render_recommendation(
        recommendation,
        _reason_rows(int(recommendation["recommendation_id"])),
        predictor_run=_predictor_run(),
        strategy_config=load_strategy_config(),
    )


def _entry(**changes: object) -> RecommendationDecisionEntry:
    arguments: dict[str, object] = {
        "decision": "APPROVED",
        "decided_at": DECIDED_AT,
        "strategy_config": load_strategy_config(),
    }
    advisory = changes.pop("advisory", None) or _advisory()
    arguments.update(changes)
    return journal_recommendation_decision(advisory, **arguments)


# --- contract -------------------------------------------------------------


def test_journal_entry_contract_and_provenance_are_stable() -> None:
    entry = _entry()
    config = load_strategy_config()

    assert entry.feature_id == DECISION_JOURNAL_FEATURE_ID
    assert entry.policy_version == DECISION_JOURNAL_POLICY_VERSION
    assert entry.recommendation_id == 200
    assert entry.advised_action == "ENTER"
    assert entry.evaluation_time == EVALUATION_TIME
    assert entry.config_metadata == config.run_metadata()
    assert entry.provenance.strategy_version == config.identity.strategy_version
    assert entry.provenance.parameter_set_id == config.identity.parameter_set_id
    assert entry.reason_codes == (
        "DECISION_JOURNAL_RECORDED",
        "DECISION_JOURNAL_APPROVED",
    )
    assert set(entry.reason_codes) <= set(DECISION_JOURNAL_REASON_CODES)


@pytest.mark.parametrize("decision", RECOMMENDATION_DECISIONS)
def test_every_decision_is_recordable_with_its_own_reason_code(decision: str) -> None:
    fields = ("initial_stop",) if decision == "MODIFIED" else ()

    entry = _entry(decision=decision, modified_fields=fields)

    assert entry.decision == decision
    assert entry.reason_codes == (
        "DECISION_JOURNAL_RECORDED",
        f"DECISION_JOURNAL_{decision}",
    )
    assert entry.as_record()["decision"] == decision


def test_decision_vocabulary_is_the_persisted_vocabulary() -> None:
    assert RECOMMENDATION_DECISIONS == ("APPROVED", "REJECTED", "MODIFIED", "MISSED")


def test_unknown_decision_is_refused() -> None:
    with pytest.raises(ValueError, match="decision must be one of"):
        _entry(decision="FOLLOWED")


# --- determinism and advisory evidence ------------------------------------


def test_record_is_deterministic_and_digests_the_decided_advisory() -> None:
    first = _entry()
    second = _entry()
    advisory_json = render_json_output(_advisory())

    assert first.as_record() == second.as_record()
    assert first.advisory_digest == second.advisory_digest
    assert first.advisory_body == advisory_json.body
    assert json.loads(first.advisory_body)["document_type"] == "recommendation"
    assert first.advisory().as_record() == _advisory().as_record()


def test_a_different_advisory_produces_a_different_digest() -> None:
    entry = _entry()

    other = _entry(advisory=_advisory(initial_stop=Decimal("89900")))

    assert other.advisory_digest != entry.advisory_digest


def test_an_already_encoded_recommendation_document_can_be_journaled() -> None:
    advisory = _advisory()

    entry = _entry(advisory=render_json_output(advisory))

    assert entry.advisory_body == render_json_output(advisory).body
    assert entry.as_record() == _entry(advisory=advisory).as_record()


def test_a_position_management_document_is_not_a_recommendation_decision() -> None:
    report = _position_management_report()

    with pytest.raises(ValueError, match="only be recorded against a recommendation"):
        _entry(advisory=render_json_output(report))


def test_an_arbitrary_object_is_not_an_advisory() -> None:
    with pytest.raises(TypeError, match="advisory must be"):
        _entry(advisory={"recommendation_id": 200})


# --- provenance and point-in-time correctness -----------------------------


def test_decision_config_identity_must_match_the_advisory() -> None:
    config = load_strategy_config()
    other = replace(
        config,
        identity=replace(config.identity, parameter_set_id="research_only"),
    )

    with pytest.raises(ValueError, match="config identity does not match"):
        _entry(strategy_config=other)


def test_decision_may_not_precede_the_advisory_it_answers() -> None:
    with pytest.raises(ValueError, match="must not precede the advisory"):
        _entry(decided_at=EVALUATION_TIME - timedelta(seconds=1))


def test_decision_at_the_advisory_instant_is_allowed() -> None:
    entry = _entry(decided_at=EVALUATION_TIME)

    assert entry.decided_at == EVALUATION_TIME


def test_naive_decision_time_is_refused() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _entry(decided_at=datetime(2026, 8, 31, 12))


def test_strategy_config_is_required() -> None:
    with pytest.raises(TypeError, match="strategy_config must be a StrategyConfig"):
        _entry(strategy_config=load_strategy_config().run_metadata())


# --- MODIFIED semantics ---------------------------------------------------


def test_modified_must_name_the_departed_fields() -> None:
    with pytest.raises(ValueError, match="MODIFIED must name"):
        _entry(decision="MODIFIED")


def test_modified_fields_are_stored_in_canonical_order() -> None:
    entry = _entry(
        decision="MODIFIED",
        modified_fields=("suggested_notional", "initial_stop", "entry_zone_lower"),
    )

    assert entry.modified_fields == (
        "entry_zone_lower",
        "initial_stop",
        "suggested_notional",
    )
    assert [
        MODIFIABLE_ADVISORY_FIELDS.index(name) for name in entry.modified_fields
    ] == sorted(MODIFIABLE_ADVISORY_FIELDS.index(n) for n in entry.modified_fields)


def test_only_advisory_geometry_can_be_modified() -> None:
    assert "action" not in MODIFIABLE_ADVISORY_FIELDS

    with pytest.raises(ValueError, match="modified_fields must be drawn from"):
        _entry(decision="MODIFIED", modified_fields=("action",))


def test_a_field_cannot_be_modified_twice() -> None:
    with pytest.raises(ValueError, match="must not repeat a field"):
        _entry(decision="MODIFIED", modified_fields=("initial_stop", "initial_stop"))


def test_a_field_the_advisory_never_stated_cannot_be_modified() -> None:
    exit_advisory = _advisory(action="EXIT", initial_stop=None, hold_score=Decimal("30"))

    with pytest.raises(ValueError, match="did not state these modified fields"):
        journal_recommendation_decision(
            exit_advisory,
            decision="MODIFIED",
            decided_at=DECIDED_AT,
            strategy_config=load_strategy_config(),
            modified_fields=("initial_stop",),
        )


@pytest.mark.parametrize("decision", ("APPROVED", "REJECTED", "MISSED"))
def test_only_a_modification_may_name_modified_fields(decision: str) -> None:
    with pytest.raises(ValueError, match="cannot name modified advisory fields"):
        _entry(decision=decision, modified_fields=("initial_stop",))


# --- decisions the advisory cannot support --------------------------------


@pytest.mark.parametrize("decision", ("MODIFIED", "MISSED"))
@pytest.mark.parametrize("action", ("NO_TRADE", "WATCH", "HOLD"))
def test_an_advisory_without_an_order_cannot_be_modified_or_missed(
    decision: str,
    action: str,
) -> None:
    advisory = _advisory(action=action, hold_score=Decimal("70"))
    fields = ("initial_stop",) if decision == "MODIFIED" else ()

    with pytest.raises(ValueError, match="requires an advisory action in"):
        journal_recommendation_decision(
            advisory,
            decision=decision,
            decided_at=DECIDED_AT,
            strategy_config=load_strategy_config(),
            modified_fields=fields,
        )


@pytest.mark.parametrize("action", ("NO_TRADE", "WATCH", "HOLD"))
@pytest.mark.parametrize("decision", ("APPROVED", "REJECTED"))
def test_an_advisory_without_an_order_can_still_be_approved_or_rejected(
    action: str,
    decision: str,
) -> None:
    advisory = _advisory(action=action, hold_score=Decimal("70"))

    entry = journal_recommendation_decision(
        advisory,
        decision=decision,
        decided_at=DECIDED_AT,
        strategy_config=load_strategy_config(),
    )

    assert entry.advised_action == action
    assert action not in ORDER_BEARING_ACTIONS
    assert entry.decision == decision


# --- notes ----------------------------------------------------------------


def test_note_is_optional_and_single_line() -> None:
    assert _entry().note is None
    assert _entry(note="Waited for the weekly close.").note == (
        "Waited for the weekly close."
    )

    with pytest.raises(ValueError, match="single-line"):
        _entry(note="Two\nlines")
    with pytest.raises(ValueError, match="single-line"):
        _entry(note="   ")


# --- persistence row ------------------------------------------------------


def test_row_matches_the_decision_journal_table_exactly() -> None:
    entry = _entry(decision="MODIFIED", modified_fields=("initial_stop",))

    row = entry.as_row()

    columns = {column.name for column in recommendation_decisions.columns}
    assert set(row) == columns - {"decision_id"}
    assert row["recommendation_id"] == 200
    assert row["strategy_version"] == entry.provenance.strategy_version
    assert row["parameter_set_id"] == entry.provenance.parameter_set_id
    assert row["config_version"] == entry.config_version
    assert row["evaluation_time"] == EVALUATION_TIME
    assert row["decided_at"] == DECIDED_AT
    assert row["decision"] == "MODIFIED"
    assert row["advised_action"] == "ENTER"
    assert row["modified_fields"] == ["initial_stop"]
    assert row["journal_policy_version"] == DECISION_JOURNAL_POLICY_VERSION
    assert row["advisory_schema_version"] == "ADVISORY_JSON_SCHEMA_V1"
    assert row["advisory_digest"] == entry.advisory_digest
    assert len(row["advisory_digest"]) == 64
    assert row["reason_codes"] == list(entry.reason_codes)


def test_row_is_refused_when_the_entry_is_inconsistent() -> None:
    entry = _entry()
    tampered = RecommendationDecisionEntry(**{**vars(entry), "decision": "MISSED"})

    with pytest.raises(ValueError, match="reason_codes do not match"):
        tampered.as_row()


# --- replay ---------------------------------------------------------------


def test_record_replays_exactly() -> None:
    entry = _entry(
        decision="MODIFIED",
        modified_fields=("initial_stop",),
        note="Tightened the stop.",
    )

    restored = recommendation_decision_from_record(entry.as_record())

    assert restored == entry
    assert restored.as_record() == entry.as_record()
    verify_decision_entry(restored)


def test_replay_rejects_a_tampered_advisory_body() -> None:
    record = _entry().as_record()
    record["advisory_body"] = record["advisory_body"].replace("89800", "88000")

    with pytest.raises(ValueError):
        recommendation_decision_from_record(record)


def test_replay_rejects_a_noncanonical_advisory_body() -> None:
    record = _entry().as_record()
    record["advisory_body"] = json.dumps(json.loads(record["advisory_body"]))

    with pytest.raises(ValueError, match="canonical advisory JSON encoding"):
        recommendation_decision_from_record(record)


def test_replay_rejects_a_forged_digest() -> None:
    record = _entry().as_record()
    record["advisory_digest"] = "0" * 64

    with pytest.raises(ValueError, match="does not match its validated entry"):
        recommendation_decision_from_record(record)


def test_replay_rejects_a_decision_swapped_after_the_fact() -> None:
    record = _entry().as_record()
    record["decision"] = "REJECTED"

    with pytest.raises(ValueError, match="reason_codes do not match"):
        recommendation_decision_from_record(record)


def test_replay_rejects_provenance_that_belongs_to_another_recommendation() -> None:
    record = _entry().as_record()
    record["provenance"] = {**record["provenance"], "recommendation_id": 201}

    with pytest.raises(ValueError, match="not attributed to the advised recommendation"):
        recommendation_decision_from_record(record)


def test_replay_rejects_a_restamped_strategy_version() -> None:
    record = _entry().as_record()
    record["provenance"] = {**record["provenance"], "strategy_version": "swing_v9.9"}

    with pytest.raises(ValueError, match="config identity does not match the advisory"):
        recommendation_decision_from_record(record)


def test_replay_rejects_an_altered_evaluation_time() -> None:
    record = _entry().as_record()
    record["evaluation_time"] = (EVALUATION_TIME - timedelta(days=1)).isoformat()

    with pytest.raises(ValueError, match="evaluation_time does not match"):
        recommendation_decision_from_record(record)


def test_replay_rejects_an_altered_advised_action() -> None:
    record = _entry().as_record()
    record["advised_action"] = "EXIT"

    with pytest.raises(ValueError, match="advised_action does not match"):
        recommendation_decision_from_record(record)


def test_replay_rejects_modified_fields_out_of_canonical_order() -> None:
    record = _entry(
        decision="MODIFIED",
        modified_fields=("entry_zone_lower", "initial_stop"),
    ).as_record()
    record["modified_fields"] = ["initial_stop", "entry_zone_lower"]

    with pytest.raises(ValueError, match="canonical advisory order"):
        recommendation_decision_from_record(record)


def test_replay_rejects_an_unknown_record_field() -> None:
    record = _entry().as_record()
    record["approved_by"] = "operator"

    with pytest.raises(ValueError, match="unknown fields"):
        recommendation_decision_from_record(record)


def test_replay_rejects_a_foreign_policy_version() -> None:
    record = _entry().as_record()
    record["policy_version"] = "RECOMMENDATION_DECISION_JOURNAL_V2"

    with pytest.raises(ValueError, match="policy_version must be"):
        recommendation_decision_from_record(record)


def _position_management_report():
    """A BTC-171 report, so the journal can prove it is not a decidable advisory."""

    config = load_strategy_config()
    lifecycle = apply_position_event(
        start_position_lifecycle(
            symbol="BTC/USD",
            direction="long",
            state=PENDING_ENTRY,
            config_metadata=config.run_metadata(),
        ),
        event=ENTER,
        event_time=EVALUATION_TIME - timedelta(days=1),
        quantity="1",
        price="100000",
        stop_price="90000",
    )
    return render_position_management_report(
        advisory=_advisory(action="HOLD", hold_score=Decimal("76")),
        lifecycle=lifecycle,
        trailing_stop=calculate_trailing_stop(
            direction="long",
            previous_stop=lifecycle.stop_price,
            structure_price="98000",
            buffer="1500",
            current_price="105000",
            evaluated_at=EVALUATION_TIME,
            structure_type=HIGHER_LOW,
            config_metadata=config.run_metadata(),
            structure_id="structure-200",
            structure_source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
            structure_level_timestamp=EVALUATION_TIME - timedelta(days=2),
            structure_detected_at=EVALUATION_TIME - timedelta(hours=1),
            structure_reason_codes=("STRUCTURE_CONFIRMED",),
        ),
        risk_at_stop=calculate_risk_at_stop(
            lifecycle.tranches,
            stop_price=lifecycle.stop_price,
            nav="2000000",
            direction="long",
            config=config,
        ),
        mark_price="105000",
        marked_at=EVALUATION_TIME,
        mark_source_id="reference:BTC/USD:1d",
    )
