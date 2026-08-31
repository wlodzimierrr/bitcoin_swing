"""BTC-158 full-exit policy tests."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features import HoldScoreInput, calculate_hold_score
from btc_predictor.portfolio import (
    ENTER,
    EXIT,
    PENDING_ENTRY,
    STOP_MOVE,
    apply_position_event,
    position_event_records,
    replay_position_event_records,
    start_position_lifecycle,
)
from btc_predictor.signals import (
    DATA_RISK,
    EXIT_ACTION,
    EXIT_EFFECTS,
    EXIT_REASON_IDS,
    EXIT_RULE_INPUT_IDS,
    EXIT_RULE_REASON_CODES,
    EXIT_RULES_PARAMETER_STATUS,
    EXIT_RULES_POLICY_VERSION,
    EXIT_SIGNAL_FEATURE_ID,
    HOLD_SCORE_COLLAPSE,
    MANUAL_RESEARCH_OVERRIDE,
    REGIME_INVALIDATION,
    STRUCTURAL_STOP,
    ExitRuleInput,
    evaluate_exit_rules,
    exit_rules_for_position,
    exit_signal_from_record,
    structural_stop_triggered,
)


START = datetime(2026, 9, 1, tzinfo=timezone.utc)


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def neutral_input(**overrides) -> ExitRuleInput:
    base = ExitRuleInput(
        position_open=True,
        direction="long",
        standing_stop=Decimal("90"),
        current_price=Decimal("100"),
        hold_score=Decimal("70"),
        regime_invalidated=False,
        data_risk_exit_required=False,
        manual_research_override=False,
    )
    return replace(base, **overrides) if overrides else base


def evaluate(inputs: ExitRuleInput | None = None):
    return evaluate_exit_rules(
        inputs or neutral_input(),
        strategy_config=load_strategy_config(),
        evaluated_at=at(3),
    )


def open_lifecycle(*, direction: str = "long", stop: str = "90"):
    config = load_strategy_config()
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        direction=direction,
        state=PENDING_ENTRY,
        config_metadata=config.run_metadata(),
    )
    return apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(1),
        quantity="1",
        price="100",
        stop_price=stop,
    )


def hold_result(score: str = "70"):
    value = Decimal(score)
    return calculate_hold_score(
        HoldScoreInput(value, value, value, value, value),
        strategy_config=load_strategy_config(),
    )


def canonical_result(**overrides):
    values = {
        "lifecycle": open_lifecycle(),
        "current_price": "100",
        "hold_score": hold_result(),
        "regime_invalidated": False,
        "data_risk_exit_required": False,
        "manual_research_override": False,
        "manual_override_reason": None,
        "strategy_config": load_strategy_config(),
        "evaluated_at": at(3),
    }
    return exit_rules_for_position(**{**values, **overrides})


def test_contract_is_stable_and_full_exit_only() -> None:
    assert EXIT_SIGNAL_FEATURE_ID == "EXIT_SIGNAL"
    assert EXIT_RULES_POLICY_VERSION == "EXIT_RULES_V1"
    assert EXIT_RULES_PARAMETER_STATUS == "PROVISIONAL_PENDING_BTC_185"
    assert EXIT_ACTION == "EXIT"
    assert EXIT_EFFECTS == ("FULL_EXIT",)
    assert EXIT_REASON_IDS == (
        "STRUCTURAL_STOP",
        "HOLD_SCORE_COLLAPSE",
        "REGIME_INVALIDATION",
        "DATA_RISK",
        "MANUAL_RESEARCH_OVERRIDE",
    )
    assert EXIT_RULE_INPUT_IDS == (
        "position_open",
        "direction",
        "standing_stop",
        "current_price",
        "hold_score",
        "regime_invalidated",
        "data_risk_exit_required",
        "manual_research_override",
    )
    assert EXIT_RULE_REASON_CODES == (
        "EXIT_INPUT_MISSING",
        "EXIT_NO_OPEN_POSITION",
        *EXIT_REASON_IDS,
        "EXIT_NOT_TRIGGERED",
    )
    assert "PARTIAL_REDUCTION" not in EXIT_EFFECTS


def test_no_trigger_holds_the_open_position() -> None:
    result = evaluate()

    assert result.signal is False
    assert result.action is None
    assert result.effects == ()
    assert result.exit_reasons == ()
    assert result.complete is True
    assert result.reason_codes == ("EXIT_NOT_TRIGGERED",)


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"current_price": Decimal("90")}, STRUCTURAL_STOP),
        ({"hold_score": Decimal("39")}, HOLD_SCORE_COLLAPSE),
        ({"regime_invalidated": True}, REGIME_INVALIDATION),
        ({"data_risk_exit_required": True}, DATA_RISK),
        (
            {
                "manual_research_override": True,
                "manual_override_reason": "Thesis invalidated by research review",
            },
            MANUAL_RESEARCH_OVERRIDE,
        ),
    ],
)
def test_each_declared_reason_independently_emits_exit(
    changes: dict,
    reason: str,
) -> None:
    result = evaluate(neutral_input(**changes))

    assert result.signal is True
    assert result.action == "EXIT"
    assert result.full_exit is True
    assert result.effects == ("FULL_EXIT",)
    assert result.exit_reasons == (reason,)
    assert result.reason_codes == (reason,)


def test_all_exit_reasons_are_retained_in_declared_order() -> None:
    result = evaluate(
        neutral_input(
            current_price=Decimal("89"),
            hold_score=Decimal("30"),
            regime_invalidated=True,
            data_risk_exit_required=True,
            manual_research_override=True,
            manual_override_reason="Research override",
        )
    )

    assert result.exit_reasons == EXIT_REASON_IDS
    assert result.reason_codes == EXIT_REASON_IDS


@pytest.mark.parametrize(
    ("score", "triggered"),
    [
        ("40", False),
        ("39.999999999999", False),
        ("39.99999999", True),
        ("0", True),
    ],
)
def test_hold_score_exit_boundary_uses_config_and_shared_tolerance(
    score: str,
    triggered: bool,
) -> None:
    result = evaluate(neutral_input(hold_score=Decimal(score)))

    assert result.signal is triggered
    assert (HOLD_SCORE_COLLAPSE in result.exit_reasons) is triggered


def test_hold_score_exit_boundary_is_loaded_from_strategy_config() -> None:
    config = load_strategy_config()
    custom = replace(
        config,
        hold_thresholds=replace(config.hold_thresholds, exit_below=35),
    )
    result = evaluate_exit_rules(
        neutral_input(hold_score=Decimal("37")),
        strategy_config=custom,
        evaluated_at=at(3),
    )

    assert result.exit_below == Decimal("35")
    assert result.signal is False
    assert result.reason_codes == ("EXIT_NOT_TRIGGERED",)


@pytest.mark.parametrize(
    ("direction", "price", "triggered"),
    [
        ("long", "90.000000001", False),
        ("long", "90", True),
        ("long", "89", True),
        ("short", "109.999999999", False),
        ("short", "110", True),
        ("short", "111", True),
    ],
)
def test_structural_stop_geometry_is_directionally_correct(
    direction: str,
    price: str,
    triggered: bool,
) -> None:
    stop = "90" if direction == "long" else "110"
    assert structural_stop_triggered(
        direction=direction,
        standing_stop=stop,
        current_price=price,
    ) is triggered


def test_structural_stop_boundary_uses_shared_tolerance() -> None:
    assert structural_stop_triggered(
        direction="long", standing_stop="90", current_price="90.00000000001"
    ) is True
    assert structural_stop_triggered(
        direction="short", standing_stop="110", current_price="109.99999999995"
    ) is True


def test_no_open_position_suppresses_every_exit_reason() -> None:
    result = evaluate(
        neutral_input(
            position_open=False,
            current_price=Decimal("80"),
            hold_score=Decimal("20"),
            regime_invalidated=True,
            data_risk_exit_required=True,
            manual_research_override=True,
            manual_override_reason="Review",
        )
    )

    assert result.signal is False
    assert result.exit_reasons == ()
    assert result.reason_codes == ("EXIT_NO_OPEN_POSITION",)


def test_missing_evidence_is_not_silently_filled() -> None:
    result = evaluate(
        neutral_input(current_price=None, regime_invalidated=None)
    )

    assert result.signal is False
    assert result.complete is False
    assert result.missing_inputs == ("current_price", "regime_invalidated")
    assert result.reason_codes == ("EXIT_INPUT_MISSING",)


def test_known_safety_exit_survives_unrelated_missing_evidence() -> None:
    result = evaluate(
        neutral_input(
            current_price=None,
            hold_score=None,
            regime_invalidated=None,
            data_risk_exit_required=True,
        )
    )

    assert result.signal is True
    assert result.complete is False
    assert result.action == "EXIT"
    assert result.exit_reasons == (DATA_RISK,)
    assert result.reason_codes == ("EXIT_INPUT_MISSING", DATA_RISK)


def test_data_risk_requires_an_explicit_exit_conclusion() -> None:
    result = evaluate(neutral_input(data_risk_exit_required=False))

    assert result.signal is False
    assert DATA_RISK not in result.reason_codes


def test_manual_override_requires_an_auditable_reason() -> None:
    with pytest.raises(ValueError, match="requires manual_override_reason"):
        evaluate(neutral_input(manual_research_override=True))
    with pytest.raises(ValueError, match="requires manual_research_override"):
        evaluate(neutral_input(manual_override_reason="Unlinked reason"))


@pytest.mark.parametrize(
    ("field", "value", "match"),
    [
        ("position_open", "yes", "position_open"),
        ("direction", "flat", "direction"),
        ("standing_stop", Decimal("0"), "standing_stop"),
        ("current_price", Decimal("NaN"), "current_price"),
        ("hold_score", Decimal("101"), "hold_score"),
        ("regime_invalidated", 1, "regime_invalidated"),
    ],
)
def test_malformed_inputs_fail_fast(field: str, value: object, match: str) -> None:
    with pytest.raises((TypeError, ValueError), match=match):
        evaluate(neutral_input(**{field: value}))


def test_record_persists_all_inputs_policy_reasons_and_config() -> None:
    result = evaluate(
        neutral_input(
            hold_score=Decimal("35"),
            regime_invalidated=True,
            source_reason_codes={
                "hold_score": ("HOLD_SCORE_COMPLETE",),
                "regime": ("REGIME_BEAR",),
            },
        )
    )
    record = result.as_record()

    assert record["feature_id"] == "EXIT_SIGNAL"
    assert record["policy_version"] == "EXIT_RULES_V1"
    assert record["exit_below"] == "40.0"
    assert record["evaluated_at"] == at(3).isoformat()
    assert record["inputs"]["standing_stop"] == "90"
    assert record["inputs"]["source_reason_codes"] == {
        "hold_score": ["HOLD_SCORE_COMPLETE"],
        "regime": ["REGIME_BEAR"],
    }
    assert record["exit_reasons"] == [
        "HOLD_SCORE_COLLAPSE",
        "REGIME_INVALIDATION",
    ]
    assert record["config_metadata"] == load_strategy_config().run_metadata()
    assert exit_signal_from_record(record) == result


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("feature_id", "OTHER"),
        ("policy_version", "EXIT_RULES_V0"),
        ("exit_below", "30"),
        ("signal", False),
        ("action", None),
        ("full_exit", False),
        ("effects", []),
        ("exit_reasons", ["DATA_RISK"]),
        ("complete", False),
        ("reason_codes", ["EXIT_NOT_TRIGGERED"]),
    ],
)
def test_persisted_result_tampering_is_rejected(field: str, value: object) -> None:
    record = evaluate(neutral_input(hold_score=Decimal("35"))).as_record()
    record[field] = value

    with pytest.raises((TypeError, ValueError)):
        exit_signal_from_record(record)


def test_persisted_input_tampering_is_rejected() -> None:
    record = evaluate(neutral_input(hold_score=Decimal("35"))).as_record()
    record["inputs"]["hold_score"] = "70"

    with pytest.raises(ValueError):
        exit_signal_from_record(record)


def test_evaluation_and_serialization_are_deterministic() -> None:
    inputs = neutral_input(
        data_risk_exit_required=True,
        source_reason_codes={"risk": ("PROVIDER_UNAVAILABLE",)},
    )
    first = evaluate(inputs)
    second = evaluate(inputs)

    assert first == second
    assert first.as_record() == second.as_record()


def test_canonical_path_composes_lifecycle_hold_score_and_evidence() -> None:
    result = canonical_result(
        hold_score=hold_result("35"),
        regime_invalidated=True,
        source_reason_codes={"regime": ("REGIME_STRONG_BEAR",)},
    )

    assert result.signal is True
    assert result.exit_reasons == (
        HOLD_SCORE_COLLAPSE,
        REGIME_INVALIDATION,
    )
    assert result.inputs.direction == "long"
    assert result.inputs.standing_stop == Decimal("90")
    assert result.inputs.source_reason_codes["lifecycle"] == (
        "POSITION_STATE_ENTERED",
    )
    assert result.inputs.source_reason_codes["hold_score"] == (
        "HOLD_SCORE_COMPLETE",
    )
    assert result.inputs.source_reason_codes["regime"] == (
        "REGIME_STRONG_BEAR",
    )


def test_canonical_path_uses_the_latest_trailed_stop_from_the_ledger() -> None:
    lifecycle = apply_position_event(
        open_lifecycle(),
        event=STOP_MOVE,
        event_time=at(2),
        stop_price="95",
    )
    result = canonical_result(
        lifecycle=lifecycle,
        current_price="94",
    )

    assert result.signal is True
    assert result.exit_reasons == (STRUCTURAL_STOP,)
    assert result.inputs.standing_stop == Decimal("95")
    assert lifecycle.stop_price == Decimal("95")


def test_canonical_short_path_mirrors_structural_stop_touch() -> None:
    result = canonical_result(
        lifecycle=open_lifecycle(direction="short", stop="110"),
        current_price="111",
    )

    assert result.signal is True
    assert result.inputs.direction == "short"
    assert result.exit_reasons == (STRUCTURAL_STOP,)


def test_canonical_evaluation_does_not_mutate_the_lifecycle() -> None:
    lifecycle = open_lifecycle()
    before = lifecycle.as_record()
    result = canonical_result(lifecycle=lifecycle, current_price="89")

    assert result.signal is True
    assert lifecycle.as_record() == before
    assert lifecycle.is_open is True


def test_closed_lifecycle_suppresses_an_otherwise_triggered_exit() -> None:
    lifecycle = apply_position_event(
        open_lifecycle(),
        event=EXIT,
        event_time=at(2),
        price="100",
    )
    result = canonical_result(
        lifecycle=lifecycle,
        current_price="80",
        hold_score=hold_result("20"),
        regime_invalidated=True,
        data_risk_exit_required=True,
        manual_research_override=True,
        manual_override_reason="Research review",
    )

    assert result.signal is False
    assert result.reason_codes == ("EXIT_NO_OPEN_POSITION",)


def test_canonical_path_rejects_stale_decision_time() -> None:
    with pytest.raises(ValueError, match="lifecycle watermark"):
        canonical_result(evaluated_at=at(0))


def test_canonical_path_rejects_cross_config_sources() -> None:
    config = load_strategy_config()
    wrong_lifecycle = replace(
        open_lifecycle(),
        config_metadata={**config.run_metadata(), "parameter_set_id": "other"},
    )
    with pytest.raises(ValueError, match="lifecycle config_metadata"):
        canonical_result(lifecycle=wrong_lifecycle)

    wrong_hold = replace(
        hold_result(),
        config_metadata={**config.run_metadata(), "parameter_set_id": "other"},
    )
    with pytest.raises(ValueError, match="hold_score config_metadata"):
        canonical_result(hold_score=wrong_hold)


def test_canonical_evidence_cannot_replace_authoritative_sources() -> None:
    with pytest.raises(ValueError, match="cannot replace canonical"):
        canonical_result(
            source_reason_codes={"lifecycle": ("FAKE_STATE",)},
        )


def test_lifecycle_database_replay_produces_the_same_exit_signal() -> None:
    lifecycle = apply_position_event(
        open_lifecycle(),
        event=STOP_MOVE,
        event_time=at(2),
        stop_price="95",
    )
    replayed = replay_position_event_records(
        position_event_records(lifecycle),
        symbol="BTC-USD",
        config_metadata=load_strategy_config().run_metadata(),
    )

    live = canonical_result(lifecycle=lifecycle, current_price="94")
    restored = canonical_result(lifecycle=replayed, current_price="94")

    assert restored == live
    assert restored.as_record() == live.as_record()


def test_incomplete_hold_score_is_preserved_as_missing_evidence() -> None:
    config = load_strategy_config()
    incomplete = calculate_hold_score(
        HoldScoreInput(None, Decimal("50"), Decimal("50"), Decimal("50"), Decimal("50")),
        strategy_config=config,
    )
    result = canonical_result(
        hold_score=incomplete,
        data_risk_exit_required=True,
    )

    assert result.signal is True
    assert result.complete is False
    assert result.inputs.hold_score is None
    assert result.missing_inputs == ("hold_score",)
    assert result.reason_codes == ("EXIT_INPUT_MISSING", DATA_RISK)
