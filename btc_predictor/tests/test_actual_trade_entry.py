from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.db import manual_trade_journal
from btc_predictor.journal import (
    ACTUAL_TRADE_FEATURE_ID,
    ACTUAL_TRADE_POLICY_VERSION,
    FOLLOWED,
    MANUAL_ONLY,
    OVERRIDDEN,
    ActualTradeEntry,
    actual_trade_entry_from_record,
    journal_recommendation_decision,
    record_actual_trade_entry,
    verify_actual_trade_entry,
)
from btc_predictor.reporting import render_recommendation


EVALUATION_TIME = datetime(2026, 8, 31, tzinfo=timezone.utc)
DECIDED_AT = datetime(2026, 8, 31, 12, tzinfo=timezone.utc)
ENTRY_TIME = datetime(2026, 8, 31, 13, tzinfo=timezone.utc)
EXIT_TIME = datetime(2026, 9, 1, 13, tzinfo=timezone.utc)
JOURNALED_AT = datetime(2026, 9, 1, 14, tzinfo=timezone.utc)


def _recommendation(**changes: object) -> dict[str, object]:
    row: dict[str, object] = {
        "recommendation_id": 202,
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


def _advisory(**changes: object):
    config = load_strategy_config()
    recommendation = _recommendation(**changes)
    recommendation_id = int(recommendation["recommendation_id"])
    return render_recommendation(
        recommendation,
        (
            {
                "recommendation_id": recommendation_id,
                "reason_rank": 0,
                "code": "TREND_12W_POSITIVE",
                "source_component": "trend",
                "severity": "info",
                "detail": "Twelve-week momentum is positive.",
            },
        ),
        predictor_run={
            "run_id": 42,
            "evaluation_time": EVALUATION_TIME,
            **config.run_metadata(),
        },
        strategy_config=config,
    )


def _decision(decision: str = "APPROVED", **changes: object):
    arguments: dict[str, object] = {
        "decision": decision,
        "decided_at": DECIDED_AT,
        "strategy_config": load_strategy_config(),
    }
    if decision == "MODIFIED":
        arguments["modified_fields"] = ("initial_stop",)
    arguments.update(changes)
    return journal_recommendation_decision(_advisory(), **arguments)


def _entry(**changes: object) -> ActualTradeEntry:
    arguments: dict[str, object] = {
        "symbol": "BTC/USD",
        "direction": "long",
        "journaled_at": JOURNALED_AT,
        "actual_entry_time": ENTRY_TIME,
        "actual_entry_price": "100125.50",
        "actual_size": "0.05",
        "actual_size_unit": "BTC",
        "actual_stop": "89900",
        "recommendation_decision": _decision(),
    }
    arguments.update(changes)
    return record_actual_trade_entry(**arguments)


def test_linked_actual_entry_snapshots_decision_config_and_reasons() -> None:
    entry = _entry()
    config = load_strategy_config()

    assert entry.feature_id == ACTUAL_TRADE_FEATURE_ID
    assert entry.policy_version == ACTUAL_TRADE_POLICY_VERSION
    assert entry.recommendation_id == 202
    assert entry.manual_decision == FOLLOWED
    assert entry.config_metadata == config.run_metadata()
    assert entry.decision_decided_at == DECIDED_AT
    assert entry.decision_reason_codes == (
        "DECISION_JOURNAL_RECORDED",
        "DECISION_JOURNAL_APPROVED",
    )
    assert entry.discretionary_reason_codes == ()
    assert entry.actual_entry_price == Decimal("100125.50")
    assert entry.actual_size == Decimal("0.05")
    assert entry.actual_stop == Decimal("89900")
    assert entry.is_closed is False


def test_modified_decision_becomes_overridden_and_carries_btc201_reasons() -> None:
    decision = _decision(
        "MODIFIED",
        discretionary_reason_codes=("MODEL_DISAGREEMENT", "ENTRY_TOO_EXTENDED"),
    )

    entry = _entry(
        recommendation_decision=decision,
        override_reason="Used a smaller fill and tighter stop.",
    )

    assert entry.manual_decision == OVERRIDDEN
    assert entry.override_reason == "Used a smaller fill and tighter stop."
    assert entry.decision_reason_codes[-1] == "DECISION_JOURNAL_MODIFIED"
    assert entry.discretionary_reason_codes == (
        "ENTRY_TOO_EXTENDED",
        "MODEL_DISAGREEMENT",
    )


def test_serialized_decision_record_can_link_an_execution() -> None:
    decision = _decision()

    from_entry = _entry(recommendation_decision=decision)
    from_record = _entry(recommendation_decision=decision.as_record())

    assert from_record == from_entry


def test_manual_only_entry_has_no_invented_model_attribution() -> None:
    entry = _entry(
        recommendation_decision=None,
        actual_stop=None,
    )

    assert entry.manual_decision == MANUAL_ONLY
    assert entry.recommendation_id is None
    assert entry.config_metadata is None
    assert entry.decision_journal_policy_version is None
    assert entry.decision_reason_codes is None
    assert entry.discretionary_reason_policy_version is None
    assert entry.discretionary_reason_codes is None
    assert entry.actual_stop is None
    assert entry.actual_exit_time is None
    assert entry.actual_exit_price is None


@pytest.mark.parametrize("decision", ("REJECTED", "MISSED"))
def test_nonexecuted_advisory_decisions_cannot_create_a_trade(decision: str) -> None:
    with pytest.raises(ValueError, match="actual execution requires a decision"):
        _entry(recommendation_decision=_decision(decision))


def test_only_enter_advisories_can_be_linked_to_an_actual_trade_entry() -> None:
    source = journal_recommendation_decision(
        _advisory(action="ADD"),
        decision="APPROVED",
        decided_at=DECIDED_AT,
        strategy_config=load_strategy_config(),
    )

    with pytest.raises(ValueError, match="requires an ENTER advisory"):
        _entry(recommendation_decision=source)


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("symbol", "ETH/USD", "symbol does not match"),
        ("direction", "short", "direction does not match"),
    ),
)
def test_execution_identity_must_match_the_advisory(
    field: str,
    value: str,
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        _entry(**{field: value})


def test_actual_entry_may_not_precede_its_decision() -> None:
    with pytest.raises(ValueError, match="must not precede the recorded decision"):
        _entry(actual_entry_time=DECIDED_AT - timedelta(seconds=1))


def test_journal_timestamp_may_not_precede_observed_execution() -> None:
    with pytest.raises(ValueError, match="journaled_at must not precede actual_entry_time"):
        _entry(journaled_at=ENTRY_TIME - timedelta(seconds=1))


@pytest.mark.parametrize("field", ("journaled_at", "actual_entry_time"))
def test_actual_entry_timestamps_must_be_utc(field: str) -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        _entry(**{field: datetime(2026, 8, 31, 14)})


@pytest.mark.parametrize(
    ("field", "value"),
    (
        ("actual_entry_price", "0"),
        ("actual_entry_price", "NaN"),
        ("actual_size", "0"),
        ("actual_size", "Infinity"),
        ("actual_stop", "-1"),
        ("actual_exit_price", "0"),
    ),
)
def test_observed_numerical_values_must_be_positive_and_finite(
    field: str,
    value: str,
) -> None:
    changes: dict[str, object] = {field: value}
    if field == "actual_exit_price":
        changes["actual_exit_time"] = EXIT_TIME
    with pytest.raises(ValueError, match="finite and greater than zero"):
        _entry(**changes)


def test_closed_trade_records_exit_as_an_atomic_pair() -> None:
    entry = _entry(actual_exit_time=EXIT_TIME, actual_exit_price="112000")

    assert entry.is_closed is True
    assert entry.actual_exit_time == EXIT_TIME
    assert entry.actual_exit_price == Decimal("112000")

    with pytest.raises(ValueError, match="recorded together"):
        _entry(actual_exit_time=EXIT_TIME)
    with pytest.raises(ValueError, match="recorded together"):
        _entry(actual_exit_price="112000")


def test_exit_time_must_follow_entry_and_precede_journaling() -> None:
    with pytest.raises(ValueError, match="must not precede actual_entry_time"):
        _entry(
            actual_exit_time=ENTRY_TIME - timedelta(seconds=1),
            actual_exit_price="99000",
        )
    with pytest.raises(ValueError, match="journaled_at must not precede actual_exit_time"):
        _entry(
            actual_exit_time=JOURNALED_AT + timedelta(seconds=1),
            actual_exit_price="112000",
        )


def test_override_reason_is_required_only_for_modified_execution() -> None:
    with pytest.raises(ValueError, match="OVERRIDDEN requires an override_reason"):
        _entry(recommendation_decision=_decision("MODIFIED"))
    with pytest.raises(ValueError, match="only valid for OVERRIDDEN"):
        _entry(override_reason="No override occurred.")
    with pytest.raises(ValueError, match="only valid for OVERRIDDEN"):
        _entry(recommendation_decision=None, override_reason="No advisory existed.")


def test_record_and_database_row_are_deterministic_and_complete() -> None:
    first = _entry(actual_exit_time=EXIT_TIME, actual_exit_price="112000")
    second = _entry(actual_exit_time=EXIT_TIME, actual_exit_price="112000")

    assert first.as_record() == second.as_record()
    assert first.as_row() == second.as_row()
    assert set(first.as_row()) == {
        column.name for column in manual_trade_journal.columns
    } - {"manual_trade_id"}
    assert first.as_row()["execution_journal_policy_version"] == (
        ACTUAL_TRADE_POLICY_VERSION
    )
    assert first.as_row()["decision_reason_codes"] == [
        "DECISION_JOURNAL_RECORDED",
        "DECISION_JOURNAL_APPROVED",
    ]


def test_record_replays_exactly() -> None:
    entry = _entry(
        recommendation_decision=_decision(
            "MODIFIED",
            discretionary_reason_codes=("ENTRY_TOO_EXTENDED",),
        ),
        override_reason="Used a tighter stop.",
        actual_exit_time=EXIT_TIME,
        actual_exit_price="112000",
        notes="Filled manually on the execution venue.",
    )

    restored = actual_trade_entry_from_record(entry.as_record())

    assert restored == entry
    assert restored.as_record() == entry.as_record()
    verify_actual_trade_entry(restored)


def test_replay_rejects_policy_reason_and_attribution_tampering() -> None:
    entry = _entry()

    changed_policy = {**entry.as_record(), "policy_version": "MANUAL_EXECUTION_V2"}
    with pytest.raises(ValueError, match="policy_version must be"):
        actual_trade_entry_from_record(changed_policy)

    changed_reason = {
        **entry.as_record(),
        "decision_reason_codes": [
            "DECISION_JOURNAL_RECORDED",
            "DECISION_JOURNAL_MODIFIED",
        ],
    }
    with pytest.raises(ValueError, match="do not match manual_decision"):
        actual_trade_entry_from_record(changed_reason)

    manual_with_model = {
        **_entry(recommendation_decision=None).as_record(),
        "config_version": "invented",
    }
    with pytest.raises(ValueError, match="must not carry recommendation"):
        actual_trade_entry_from_record(manual_with_model)


def test_replay_rejects_unknown_fields_and_noncanonical_reason_order() -> None:
    decision = _decision(
        discretionary_reason_codes=("MACRO_CONCERN", "MODEL_DISAGREEMENT"),
    )
    record = _entry(recommendation_decision=decision).as_record()

    with pytest.raises(ValueError, match="unknown fields"):
        actual_trade_entry_from_record({**record, "execution_venue": "example"})

    record["discretionary_reason_codes"] = [
        "MODEL_DISAGREEMENT",
        "MACRO_CONCERN",
    ]
    with pytest.raises(ValueError, match="canonical order"):
        actual_trade_entry_from_record(record)


def test_tampered_entry_cannot_be_persisted() -> None:
    entry = _entry()
    tampered = replace(entry, actual_size=Decimal("0"))

    with pytest.raises(ValueError, match="greater than zero"):
        tampered.as_row()


def test_arbitrary_decision_source_is_refused() -> None:
    with pytest.raises(TypeError, match="recommendation_decision must be"):
        _entry(recommendation_decision=object())
