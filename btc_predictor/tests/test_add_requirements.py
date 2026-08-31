"""BTC-154 pyramiding requirement tests."""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features.add import (
    AddScoreInput,
    calculate_add_score,
    risk_improvement_component_score,
)
from btc_predictor.portfolio import (
    ADD,
    ENTER,
    PENDING_ENTRY,
    apply_position_event,
    start_position_lifecycle,
)
from btc_predictor.risk.exposure import calculate_risk_at_stop
from btc_predictor.signals.add_requirements import (
    ADD_REQUIREMENTS_EFFECTS,
    ADD_REQUIREMENTS_FEATURE_ID,
    ADD_REQUIREMENTS_INPUT_IDS,
    ADD_REQUIREMENTS_PARAMETER_STATUS,
    ADD_REQUIREMENTS_POLICY_VERSION,
    ADD_REQUIREMENTS_REASON_CODES,
    AddRequirementsInput,
    AddRequirementsResult,
    add_requirements_from_results,
    evaluate_add_requirements,
)


SYMBOL = "BTC-USD"
START = datetime(2024, 5, 1, tzinfo=timezone.utc)


def at(hours: int) -> datetime:
    return START + timedelta(hours=hours)


def satisfied_input(**overrides) -> AddRequirementsInput:
    base = AddRequirementsInput(
        position_profitable=True,
        new_structural_confirmation=True,
        signed_risk_improvement=Decimal("1500"),
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        add_score=Decimal("86"),
        projected_risk_at_stop_within_maximum=True,
    )
    return replace(base, **overrides) if overrides else base


def test_contract_is_stable() -> None:
    assert ADD_REQUIREMENTS_FEATURE_ID == "ADD_REQUIREMENTS"
    assert ADD_REQUIREMENTS_POLICY_VERSION == "ADD_REQUIREMENTS_V1"
    assert ADD_REQUIREMENTS_PARAMETER_STATUS == "PROVISIONAL_PENDING_BTC_185"
    assert ADD_REQUIREMENTS_EFFECTS == ("NO_ADD",)
    assert ADD_REQUIREMENTS_INPUT_IDS == (
        "position_profitable",
        "new_structural_confirmation",
        "signed_risk_improvement",
        "regime_supportive",
        "flow_supportive",
        "positioning_healthy",
        "add_score",
        "projected_risk_at_stop_within_maximum",
    )


def test_every_ticket_requirement_has_its_own_input_and_reason_code() -> None:
    # The eight requirements listed in BTC-154, each independently refusable.
    assert len(ADD_REQUIREMENTS_INPUT_IDS) == 8
    refusals = [
        code
        for code in ADD_REQUIREMENTS_REASON_CODES
        if code
        not in ("ADD_REQUIREMENTS_INPUT_MISSING", "ADD_REQUIREMENTS_SATISFIED")
    ]
    assert len(refusals) == 8


def test_all_requirements_met_permits_the_add() -> None:
    config = load_strategy_config()

    result = evaluate_add_requirements(satisfied_input(), strategy_config=config)

    assert isinstance(result, AddRequirementsResult)
    assert result.permitted is True
    assert result.blocked is False
    assert result.complete is True
    assert result.effects == ()
    assert result.reason_codes == ("ADD_REQUIREMENTS_SATISFIED",)


@pytest.mark.parametrize(
    ("override", "expected"),
    [
        ({"position_profitable": False}, "ADD_REQUIREMENTS_POSITION_NOT_PROFITABLE"),
        ({"new_structural_confirmation": False}, "ADD_REQUIREMENTS_NO_NEW_STRUCTURE"),
        (
            {"signed_risk_improvement": Decimal("-1")},
            "ADD_REQUIREMENTS_STOP_CANNOT_IMPROVE",
        ),
        ({"regime_supportive": False}, "ADD_REQUIREMENTS_REGIME_UNSUPPORTIVE"),
        ({"flow_supportive": False}, "ADD_REQUIREMENTS_FLOW_UNSUPPORTIVE"),
        ({"positioning_healthy": False}, "ADD_REQUIREMENTS_POSITIONING_UNHEALTHY"),
        ({"add_score": Decimal("84.99")}, "ADD_REQUIREMENTS_ADD_SCORE_BELOW_MINIMUM"),
        (
            {"projected_risk_at_stop_within_maximum": False},
            "ADD_REQUIREMENTS_RISK_AT_STOP_EXCEEDED",
        ),
    ],
)
def test_any_single_unmet_requirement_blocks_the_add(
    override: dict,
    expected: str,
) -> None:
    config = load_strategy_config()

    result = evaluate_add_requirements(
        satisfied_input(**override),
        strategy_config=config,
    )

    # Requirements are conjunctive: one failure is enough.
    assert result.blocked is True
    assert result.effects == ("NO_ADD",)
    assert result.reason_codes == (expected,)


def test_several_failures_are_all_reported() -> None:
    config = load_strategy_config()

    result = evaluate_add_requirements(
        satisfied_input(
            flow_supportive=False,
            add_score=Decimal("40"),
            projected_risk_at_stop_within_maximum=False,
        ),
        strategy_config=config,
    )

    # A blocked add explains every reason it was blocked, not just the first.
    assert result.reason_codes == (
        "ADD_REQUIREMENTS_FLOW_UNSUPPORTIVE",
        "ADD_REQUIREMENTS_ADD_SCORE_BELOW_MINIMUM",
        "ADD_REQUIREMENTS_RISK_AT_STOP_EXCEEDED",
    )


# --- fail closed ---------------------------------------------------------


@pytest.mark.parametrize("input_id", list(ADD_REQUIREMENTS_INPUT_IDS))
def test_an_unresolved_input_fails_closed(input_id: str) -> None:
    config = load_strategy_config()

    result = evaluate_add_requirements(
        satisfied_input(**{input_id: None}),
        strategy_config=config,
    )

    # An unknown state is never assumed favourable.
    assert result.blocked is True
    assert result.complete is False
    assert result.missing_inputs == (input_id,)
    assert "ADD_REQUIREMENTS_INPUT_MISSING" in result.reason_codes


def test_a_fully_unresolved_input_set_blocks_with_every_reason() -> None:
    config = load_strategy_config()

    result = evaluate_add_requirements(
        AddRequirementsInput(None, None, None, None, None, None, None, None),
        strategy_config=config,
    )

    assert result.blocked is True
    assert result.missing_inputs == ADD_REQUIREMENTS_INPUT_IDS
    assert len(result.reason_codes) == len(ADD_REQUIREMENTS_REASON_CODES) - 1


# --- thresholds ----------------------------------------------------------


@pytest.mark.parametrize(
    ("score", "permitted"),
    [("84.999", False), ("85", True), ("85.000000000001", True), ("100", True)],
)
def test_the_add_score_boundary_is_inclusive_at_the_configured_minimum(
    score: str,
    permitted: bool,
) -> None:
    config = load_strategy_config()

    result = evaluate_add_requirements(
        satisfied_input(add_score=Decimal(score)),
        strategy_config=config,
    )

    assert config.add_thresholds.add_min == 85
    assert result.permitted is permitted


def test_the_minimum_comes_from_config_not_a_literal() -> None:
    config = load_strategy_config()
    relaxed = replace(
        config,
        add_thresholds=replace(config.add_thresholds, add_min=70.0),
    )

    blocked = evaluate_add_requirements(
        satisfied_input(add_score=Decimal("72")),
        strategy_config=config,
    )
    permitted = evaluate_add_requirements(
        satisfied_input(add_score=Decimal("72")),
        strategy_config=relaxed,
    )

    assert blocked.blocked is True
    assert permitted.permitted is True
    assert permitted.minimum_add_score == Decimal("70.0")


@pytest.mark.parametrize(
    ("improvement", "permitted"),
    [("-1", False), ("0", False), ("0.01", True), ("50000", True)],
)
def test_the_stop_must_strictly_improve(improvement: str, permitted: bool) -> None:
    config = load_strategy_config()

    result = evaluate_add_requirements(
        satisfied_input(signed_risk_improvement=Decimal(improvement)),
        strategy_config=config,
    )

    # An unchanged stop earns no extra size, and a worsened one must not be
    # indistinguishable from it.
    assert result.permitted is permitted


def test_disabled_config_gates_drop_their_requirement_and_are_persisted() -> None:
    config = load_strategy_config()
    relaxed = replace(
        config,
        add_thresholds=replace(
            config.add_thresholds,
            existing_position_must_be_profitable=False,
            stop_must_improve=False,
        ),
    )

    result = evaluate_add_requirements(
        satisfied_input(position_profitable=False, signed_risk_improvement=None),
        strategy_config=relaxed,
    )

    # The gate set a run used is auditable rather than implied.
    assert result.permitted is True
    assert result.missing_inputs == ()
    assert result.require_profitable_position is False
    assert result.require_stop_improvement is False
    assert result.as_record()["require_stop_improvement"] is False


def test_default_config_keeps_both_optional_gates_enabled() -> None:
    config = load_strategy_config()

    result = evaluate_add_requirements(satisfied_input(), strategy_config=config)

    assert result.require_profitable_position is True
    assert result.require_stop_improvement is True


# --- canonical path over real upstream results ---------------------------


def open_position(*, add_price: str | None = None):
    lifecycle = start_position_lifecycle(symbol=SYMBOL, state=PENDING_ENTRY)
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(1),
        quantity="1",
        price="100000",
        stop_price="90000",
    )
    if add_price is not None:
        lifecycle = apply_position_event(
            lifecycle,
            event=ADD,
            event_time=at(2),
            quantity="1",
            price=add_price,
        )
    return lifecycle


def upstream(config, *, score: str, current: str, proposed: str, nav: str = "10000000"):
    return {
        "add_score": calculate_add_score(
            AddScoreInput(
                new_structure_score=Decimal(score),
                flow_score=Decimal(score),
                positioning_score=Decimal(score),
                momentum_score=Decimal(score),
                risk_improvement_score=Decimal(score),
            ),
            strategy_config=config,
        ),
        "risk_improvement": risk_improvement_component_score(
            current_risk=current,
            proposed_risk=proposed,
        ),
        "projected_risk_at_stop": calculate_risk_at_stop(
            [{"tranche_id": "a", "notional": "50000", "entry_price": "100000"}],
            stop_price="95000",
            nav=nav,
        ),
    }


def test_canonical_path_permits_an_add_on_a_profitable_position() -> None:
    config = load_strategy_config()

    result = add_requirements_from_results(
        lifecycle=open_position(),
        current_price="118000",
        **upstream(config, score="90", current="10000", proposed="6000"),
        new_structural_confirmation=True,
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        strategy_config=config,
    )

    assert result.permitted is True
    assert result.inputs.position_profitable is True
    assert result.inputs.add_score == Decimal("90.0000")
    assert result.inputs.signed_risk_improvement == Decimal("4000.0")
    assert result.inputs.projected_risk_at_stop_within_maximum is True


def test_canonical_path_reads_profitability_from_the_weighted_average_entry() -> None:
    config = load_strategy_config()
    # Two tranches at 100000 and 130000 average to 115000.
    lifecycle = open_position(add_price="130000")
    assert lifecycle.average_entry_price == Decimal("115000")

    common = dict(
        **upstream(config, score="90", current="10000", proposed="6000"),
        new_structural_confirmation=True,
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        strategy_config=config,
    )
    above = add_requirements_from_results(
        lifecycle=lifecycle, current_price="120000", **common
    )
    between = add_requirements_from_results(
        lifecycle=lifecycle, current_price="110000", **common
    )
    breakeven = add_requirements_from_results(
        lifecycle=lifecycle, current_price="115000", **common
    )

    # 120000 beats the average even though it is below the second tranche's
    # entry; 110000 beats the first tranche but not the position.
    assert above.permitted is True
    assert between.blocked is True
    assert "ADD_REQUIREMENTS_POSITION_NOT_PROFITABLE" in between.reason_codes
    # Breakeven is not profitable; BTC-151 permits it, BTC-154 does not.
    assert breakeven.blocked is True


def test_canonical_path_blocks_when_the_add_score_is_incomplete() -> None:
    config = load_strategy_config()
    incomplete = calculate_add_score(
        AddScoreInput(Decimal("90"), Decimal("90"), Decimal("90"), Decimal("90"), None),
        strategy_config=config,
    )
    results = upstream(config, score="90", current="10000", proposed="6000")
    results["add_score"] = incomplete

    result = add_requirements_from_results(
        lifecycle=open_position(),
        current_price="118000",
        **results,
        new_structural_confirmation=True,
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        strategy_config=config,
    )

    assert result.blocked is True
    assert result.inputs.add_score is None
    assert "add_score" in result.missing_inputs


def test_canonical_path_blocks_when_a_lifecycle_is_not_open() -> None:
    config = load_strategy_config()

    result = add_requirements_from_results(
        lifecycle=start_position_lifecycle(symbol=SYMBOL),
        current_price="118000",
        **upstream(config, score="90", current="10000", proposed="6000"),
        new_structural_confirmation=True,
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        strategy_config=config,
    )

    # There is no position to add to; profitability is unresolved, not False.
    assert result.blocked is True
    assert result.inputs.position_profitable is None
    assert "position_profitable" in result.missing_inputs


def test_canonical_path_blocks_when_projected_risk_breaches_the_ceiling() -> None:
    config = load_strategy_config()
    results = upstream(config, score="90", current="10000", proposed="6000")
    # The same book against a much smaller NAV breaches max_risk_at_stop.
    results["projected_risk_at_stop"] = calculate_risk_at_stop(
        [{"tranche_id": "a", "notional": "50000", "entry_price": "100000"}],
        stop_price="95000",
        nav="100000",
    )

    result = add_requirements_from_results(
        lifecycle=open_position(),
        current_price="118000",
        **results,
        new_structural_confirmation=True,
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        strategy_config=config,
    )

    assert result.blocked is True
    assert result.inputs.projected_risk_at_stop_within_maximum is False
    assert "ADD_REQUIREMENTS_RISK_AT_STOP_EXCEEDED" in result.reason_codes


def test_canonical_path_retains_upstream_evidence() -> None:
    config = load_strategy_config()

    result = add_requirements_from_results(
        lifecycle=open_position(),
        current_price="118000",
        **upstream(config, score="90", current="10000", proposed="6000"),
        new_structural_confirmation=True,
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        strategy_config=config,
        source_reason_codes={"structure": ("BREAKOUT_RETEST_CONFIRMED",)},
    )
    record = result.as_record()

    evidence = record["inputs"]["source_reason_codes"]
    assert evidence["structure"] == ["BREAKOUT_RETEST_CONFIRMED"]
    assert evidence["add_score"] == ["ADD_SCORE_COMPLETE"]
    assert "RISK_AT_STOP_WITHIN_TARGET" in evidence["projected_risk_at_stop"]
    assert evidence["lifecycle"] == ["POSITION_STATE_ENTERED"]


def test_a_worsened_stop_from_the_btc153_bridge_blocks_the_add() -> None:
    config = load_strategy_config()

    result = add_requirements_from_results(
        lifecycle=open_position(),
        current_price="118000",
        # Proposed risk exceeds current: the stop moved the wrong way.
        **upstream(config, score="90", current="10000", proposed="14000"),
        new_structural_confirmation=True,
        regime_supportive=True,
        flow_supportive=True,
        positioning_healthy=True,
        strategy_config=config,
    )

    assert result.blocked is True
    assert result.inputs.signed_risk_improvement == Decimal("-4000.0")
    assert "ADD_REQUIREMENTS_STOP_CANNOT_IMPROVE" in result.reason_codes


# --- persistence and validation ------------------------------------------


def test_record_is_persistable_and_reconstructable() -> None:
    config = load_strategy_config()
    record = evaluate_add_requirements(
        satisfied_input(),
        strategy_config=config,
    ).as_record()

    assert record == {
        "feature_id": "ADD_REQUIREMENTS",
        "policy_version": "ADD_REQUIREMENTS_V1",
        "parameter_status": "PROVISIONAL_PENDING_BTC_185",
        "inputs": {
            "position_profitable": True,
            "new_structural_confirmation": True,
            "signed_risk_improvement": "1500",
            "regime_supportive": True,
            "flow_supportive": True,
            "positioning_healthy": True,
            "add_score": "86",
            "projected_risk_at_stop_within_maximum": True,
            "source_reason_codes": {},
        },
        "minimum_add_score": "85.0",
        "require_profitable_position": True,
        "require_stop_improvement": True,
        "blocked": False,
        "effects": [],
        "missing_inputs": [],
        "config_metadata": {
            "config_version": "strategy_config_v2",
            "strategy_version": "swing_v1.2",
            "parameter_set_id": "default_phase1",
        },
        "complete": True,
        "reason_codes": ["ADD_REQUIREMENTS_SATISFIED"],
    }


def test_result_validation_rejects_persistence_drift() -> None:
    config = load_strategy_config()
    result = evaluate_add_requirements(satisfied_input(), strategy_config=config)

    with pytest.raises(ValueError, match="blocked does not match"):
        replace(result, blocked=True).as_record()
    with pytest.raises(ValueError, match="reason_codes do not match"):
        replace(result, reason_codes=("ADD_REQUIREMENTS_INPUT_MISSING",)).as_record()
    with pytest.raises(ValueError, match="effects do not match"):
        replace(result, effects=("NO_ADD",)).as_record()
    with pytest.raises(ValueError, match="policy_version"):
        replace(result, policy_version="ADD_REQUIREMENTS_V2").as_record()


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    config = load_strategy_config()
    results = [
        evaluate_add_requirements(satisfied_input(), strategy_config=config),
        evaluate_add_requirements(
            AddRequirementsInput(None, None, None, None, None, None, None, None),
            strategy_config=config,
        ),
        evaluate_add_requirements(
            satisfied_input(add_score=Decimal("10")),
            strategy_config=config,
        ),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in ADD_REQUIREMENTS_REASON_CODES


@pytest.mark.parametrize(
    ("override", "error", "match"),
    [
        ({"regime_supportive": "yes"}, TypeError, "regime_supportive"),
        ({"flow_supportive": 1}, TypeError, "flow_supportive"),
        ({"add_score": Decimal("100.01")}, ValueError, "add_score"),
        ({"add_score": Decimal("NaN")}, ValueError, "add_score"),
        (
            {"signed_risk_improvement": Decimal("Infinity")},
            ValueError,
            "signed_risk_improvement",
        ),
        ({"signed_risk_improvement": "abc"}, ValueError, "signed_risk_improvement"),
        ({"source_reason_codes": {"": ("A",)}}, ValueError, "non-empty"),
        ({"source_reason_codes": {"a": "A"}}, TypeError, "sequence"),
    ],
)
def test_malformed_inputs_fail_fast(override: dict, error, match: str) -> None:
    config = load_strategy_config()

    with pytest.raises(error, match=match):
        evaluate_add_requirements(
            satisfied_input(**override),
            strategy_config=config,
        )


def test_non_input_types_are_rejected() -> None:
    config = load_strategy_config()

    with pytest.raises(TypeError, match="AddRequirementsInput"):
        evaluate_add_requirements({"add_score": 90}, strategy_config=config)
    with pytest.raises(TypeError, match="StrategyConfig"):
        evaluate_add_requirements(satisfied_input(), strategy_config={"add_min": 85})


def test_evaluation_is_deterministic() -> None:
    config = load_strategy_config()
    first = evaluate_add_requirements(satisfied_input(), strategy_config=config)
    second = evaluate_add_requirements(satisfied_input(), strategy_config=config)

    assert first.as_record() == second.as_record()
