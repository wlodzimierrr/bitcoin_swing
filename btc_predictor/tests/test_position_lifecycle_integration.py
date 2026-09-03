"""EPIC P integration: BTC-150..BTC-158 composed as one subsystem.

Every ticket in the epic passes its own suite. These are the cross-ticket
properties none of those suites can see: the ledger reducer under quantities
its own consumers produce, the canonical composition paths refusing foreign
upstream results, the Hold Score band handed from trim to exit without a gap,
and the persistence boundary surviving a refusal.
"""

from dataclasses import replace
from datetime import datetime, timedelta, timezone
from decimal import Decimal, getcontext

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.features import (
    CrowdingFlagInput,
    EuphoriaFlagInput,
    FlowScoreInput,
    HoldScoreInput,
    calculate_crowding_flag,
    calculate_euphoria_flag,
    calculate_flow_score,
    calculate_hold_score,
)
from btc_predictor.features.add import (
    AddScoreInput,
    calculate_add_score,
    risk_improvement_component_score,
)
from btc_predictor.portfolio.state_machine import (
    ADD,
    ARM_ENTRY,
    DEFEND,
    ENTER,
    EXIT,
    OPEN_ADDED,
    OPEN_INITIAL,
    STOP_MOVE,
    TRIM,
    apply_position_event,
    position_event_records,
    replay_position_event_records,
    restore_position_lifecycle,
    start_position_lifecycle,
)
from btc_predictor.quant.comparisons import decision_equal
from btc_predictor.quant.portfolio import weighted_average_entry
from btc_predictor.quant.risk import risk_improvement
from btc_predictor.risk.budget import calculate_risk_budget
from btc_predictor.risk.buffer import calculate_volatility_buffer
from btc_predictor.risk.exposure import calculate_risk_at_stop
from btc_predictor.risk.sizing import initial_position_size_for_trade
from btc_predictor.risk.stop import calculate_initial_stop
from btc_predictor.risk.trailing import (
    HIGHER_LOW,
    LOWER_HIGH,
    ConfirmedTrailingStructure,
    apply_trailing_stop,
    stop_advance_count,
    trail_stop_for_position,
)
from btc_predictor.risk.tranches import next_tranche_for_position
from btc_predictor.signals.add_requirements import add_requirements_from_results
from btc_predictor.signals.exit_rules import exit_rules_for_position
from btc_predictor.signals.trim import trim_rules_from_results


CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
SYMBOL = "BTC-USD"
START = datetime(2024, 1, 1, tzinfo=timezone.utc)


def at(day: int) -> datetime:
    return START + timedelta(days=day)


def armed(*, direction: str = "long", metadata=None):
    lifecycle = start_position_lifecycle(
        symbol=SYMBOL,
        direction=direction,
        config_metadata=dict(metadata if metadata is not None else METADATA),
    )
    return apply_position_event(lifecycle, event=ARM_ENTRY, event_time=at(0))


def entered(*, quantity="1", price="100000", stop="90000", direction="long", metadata=None):
    return apply_position_event(
        armed(direction=direction, metadata=metadata),
        event=ENTER,
        event_time=at(1),
        quantity=quantity,
        price=price,
        stop_price=stop,
    )


def hold_result(score: str = "80", *, metadata=None):
    value = Decimal(score)
    result = calculate_hold_score(
        HoldScoreInput(value, value, value, value, value),
        strategy_config=CONFIG,
    )
    return result if metadata is None else replace(result, config_metadata=dict(metadata))


def add_result(score: str = "90", *, metadata=None):
    value = Decimal(score)
    result = calculate_add_score(
        AddScoreInput(value, value, value, value, value),
        strategy_config=CONFIG,
    )
    return result if metadata is None else replace(result, config_metadata=dict(metadata))


def euphoria_result(*, flagged: bool = False):
    return calculate_euphoria_flag(
        EuphoriaFlagInput(
            range_percentile=Decimal("50"),
            upside_return=Decimal("0.20") if flagged else Decimal("0"),
            funding_zscore=Decimal("3") if flagged else Decimal("0"),
            basis_zscore=Decimal("0"),
            oi_intensity_percentile=Decimal("50"),
            volatility_percentile=Decimal("50"),
            systemic_euphoria=False,
        ),
        config_metadata=METADATA,
    )


def crowding_result(*, flagged: bool = False):
    return calculate_crowding_flag(
        CrowdingFlagInput(
            funding_zscore=Decimal("3") if flagged else Decimal("0"),
            basis_zscore=Decimal("0"),
            oi_intensity_percentile=Decimal("50"),
        ),
        config_metadata=METADATA,
    )


def flow_result(zscore: str):
    value = Decimal(zscore)
    return calculate_flow_score(
        FlowScoreInput(value, value, value),
        core_weights=CONFIG.scoring_weights.core_flow,
        full_weights=CONFIG.scoring_weights.full_flow,
        config_metadata=METADATA,
    )


def projected_risk(*, notional="50000", stop="95000", nav="10000000"):
    return calculate_risk_at_stop(
        [{"tranche_id": "a", "notional": notional, "entry_price": "100000"}],
        stop_price=stop,
        nav=nav,
        config_metadata=METADATA,
    )


def sized_position(*, entry="100000", stop="95000", nav="1000000"):
    budget = calculate_risk_budget(entry_conviction="90", nav=nav, config=CONFIG)
    initial_stop = calculate_initial_stop(
        invalidation_price=stop,
        buffer="0",
        direction="long",
        entry_price=entry,
        config_metadata=METADATA,
    )
    return initial_position_size_for_trade(budget, initial_stop)


def structure(price: str, *, direction="long", structure_id="hl-1", day=2):
    return ConfirmedTrailingStructure(
        structure_id=structure_id,
        source_feature_id="ENTRY_TRIGGER_HIGHER_LOW",
        direction=direction,
        structure_type=HIGHER_LOW if direction == "long" else LOWER_HIGH,
        price=Decimal(price),
        level_timestamp=at(day),
        detected_at=at(day),
        config_metadata=METADATA,
    )


def buffer_for(price: str):
    del price
    return calculate_volatility_buffer(
        atr=Decimal("500"),
        level_noise_estimate=Decimal("200"),
        config_metadata=METADATA,
    )


# --- the ledger under quantities its own consumers produce -----------------


@pytest.mark.parametrize(
    ("tranche_quantities", "trim_quantity"),
    [
        (("3",), "2"),
        (("1", "2"), "1"),
        (("0.1302867181481690246697856190", "0.3609573397402851939866565344"),
         "0.1621105391031898921566259106"),
        (("0.4930138715026494582760592859", "0.3460240466634134181201912252"),
         "0.2768825129948007492107626687"),
    ],
)
def test_a_prorata_trim_leaves_an_exact_ledger_for_any_representable_split(
    tranche_quantities: tuple[str, ...],
    trim_quantity: str,
) -> None:
    # BTC-155 divides a notional by a price, so a tranche quantity routinely
    # fills the Decimal context; scaling it by a non-terminating pro-rata
    # factor then rounds. Before the epic review the rounded ledger no longer
    # summed to the position and BTC-150 raised on an ordinary permitted trim,
    # aborting the BTC-180 run rather than refusing.
    lifecycle = entered(quantity=tranche_quantities[0])
    for index, quantity in enumerate(tranche_quantities[1:], start=2):
        lifecycle = apply_position_event(
            lifecycle,
            event=ADD,
            event_time=at(index),
            quantity=quantity,
            price="110000",
        )
    before = lifecycle.average_entry_price

    trimmed = apply_position_event(
        lifecycle,
        event=TRIM,
        event_time=at(9),
        quantity=trim_quantity,
    )

    assert trimmed.accepted is True
    assert trimmed.quantity == lifecycle.quantity - Decimal(trim_quantity)
    assert sum((item.quantity for item in trimmed.tranches), Decimal("0")) == (
        trimmed.quantity
    )
    # The applied reduction is still exactly the requested one.
    assert trimmed.transitions[-1].quantity_delta == -Decimal(trim_quantity)
    assert trimmed.transitions[-1].requested_quantity == Decimal(trim_quantity)
    # Pro-rata: the weighted average entry is not re-based. The residual left
    # by scaling onto a common quantum is bounded by the context precision.
    drift = abs(trimmed.average_entry_price - before) / before
    assert drift < Decimal(1).scaleb(-(getcontext().prec - 6))
    assert trimmed.tranche_count == lifecycle.tranche_count


def test_a_trim_ledger_still_matches_the_btc047_weighted_entry_kernel() -> None:
    lifecycle = apply_position_event(
        entered(quantity="1", price="100000"),
        event=ADD,
        event_time=at(2),
        quantity="2",
        price="112000",
    )
    trimmed = apply_position_event(
        lifecycle, event=TRIM, event_time=at(3), quantity="2"
    )

    expected = weighted_average_entry(
        [float(item.entry_price) for item in trimmed.tranches],
        [float(item.quantity) for item in trimmed.tranches],
    )

    assert abs(float(trimmed.average_entry_price) - float(expected)) < 1e-6


def test_a_composed_add_then_trim_never_raises_across_realistic_prices() -> None:
    # Entry price walks the last digits, which is what decides whether the
    # pro-rata factor terminates. Every one of these must apply or refuse.
    for offset in range(0, 40):
        entry = Decimal("100000") + Decimal(offset) / Decimal("7")
        size = sized_position(entry=str(entry), stop=str(entry * Decimal("0.95")))
        first = next_tranche_for_position(
            armed(), size, entry_price=entry, config=CONFIG, config_metadata=METADATA
        )
        lifecycle = apply_position_event(
            armed(),
            event=ENTER,
            event_time=at(1),
            quantity=first.allocation.quantity,
            price=entry,
            stop_price=entry * Decimal("0.95"),
        )
        add_price = entry * Decimal("1.07")
        second = next_tranche_for_position(
            lifecycle,
            size,
            entry_price=add_price,
            config=CONFIG,
            config_metadata=METADATA,
        )
        lifecycle = apply_position_event(
            lifecycle,
            event=ADD,
            event_time=at(2),
            quantity=second.allocation.quantity,
            price=add_price,
        )
        assert lifecycle.state == OPEN_ADDED

        trimmed = apply_position_event(
            lifecycle,
            event=TRIM,
            event_time=at(3),
            quantity=lifecycle.quantity * Decimal("0.33"),
        )

        assert trimmed.accepted is True
        assert sum(
            (item.quantity for item in trimmed.tranches), Decimal("0")
        ) == trimmed.quantity


# --- one whole position, one price per tranche ----------------------------


def test_a_later_tranche_is_sized_at_its_own_fill_price() -> None:
    size = sized_position()
    lifecycle = entered(quantity="1", price="100000", stop="95000")
    add_price = Decimal("130000")

    allocation = next_tranche_for_position(
        lifecycle, size, entry_price=add_price, config=CONFIG, config_metadata=METADATA
    ).allocation

    # The schedule is a share of the final *notional*, so a tranche's two views
    # must agree at the price it fills at. Sizing a later tranche at BTC-145's
    # original entry price delivered 130% of its authorized notional while the
    # record still reported 100%.
    assert allocation.quantity * add_price == allocation.notional
    assert allocation.notional == size.position_notional * allocation.fraction_of_final


def test_a_later_tranche_without_its_own_price_gets_no_allocation() -> None:
    result = next_tranche_for_position(
        entered(), sized_position(), config=CONFIG, config_metadata=METADATA
    )

    assert result.complete is False
    assert result.allocation is None
    assert result.reason_codes == ("TRANCHE_SIZING_NO_ADD_PRICE",)


def test_the_first_tranche_still_uses_the_price_btc145_sized_it_at() -> None:
    size = sized_position()

    result = next_tranche_for_position(
        armed(), size, config=CONFIG, config_metadata=METADATA
    )

    assert result.complete is True
    assert result.entry_price == size.entry_price


def test_the_schedule_caps_adds_that_the_ledger_would_still_accept() -> None:
    size = sized_position()
    lifecycle = entered()
    for day, price in ((2, "110000"), (3, "120000")):
        lifecycle = apply_position_event(
            lifecycle, event=ADD, event_time=at(day), quantity="1", price=price
        )

    exhausted = next_tranche_for_position(
        lifecycle,
        size,
        entry_price="130000",
        config=CONFIG,
        config_metadata=METADATA,
    )
    fourth = apply_position_event(
        lifecycle, event=ADD, event_time=at(4), quantity="1", price="130000"
    )

    # BTC-155 is the cap; BTC-150 owns the ledger and would record a fourth
    # tranche, so a consumer that ignores an exhausted schedule sizes risk
    # nothing authorized.
    assert exhausted.complete is False
    assert exhausted.reason_codes == ("TRANCHE_SIZING_SCHEDULE_EXHAUSTED",)
    assert fourth.accepted is True
    assert fourth.tranche_count == 4


# --- canonical composition refuses foreign upstream results ---------------


def add_gate(**overrides):
    base = {
        "lifecycle": entered(),
        "current_price": "118000",
        "add_score": add_result(),
        "risk_improvement": risk_improvement_component_score(
            current_risk="10000", proposed_risk="6000"
        ),
        "projected_risk_at_stop": projected_risk(),
        "new_structural_confirmation": True,
        "regime_supportive": True,
        "flow_supportive": True,
        "positioning_healthy": True,
        "strategy_config": CONFIG,
    }
    return add_requirements_from_results(**{**base, **overrides})


def test_the_add_gate_permits_a_well_formed_pyramid_add() -> None:
    result = add_gate()

    assert result.permitted is True
    assert result.reason_codes == ("ADD_REQUIREMENTS_SATISFIED",)
    assert result.inputs.source_reason_codes["add_score"] == ("ADD_SCORE_COMPLETE",)


def test_the_add_gate_refuses_a_hold_score_standing_in_for_an_add_score() -> None:
    # Rulebook 21 removes HoldScore from the Add Score arithmetic and BTC-153
    # makes that structural: no field, no weight key, no input route. Both
    # results expose ``score`` and ``complete``, so composing them structurally
    # re-nested Hold inside the add decision -- and the persisted evidence said
    # HOLD_SCORE_COMPLETE while nothing refused it.
    with pytest.raises(TypeError, match="AddScoreResult"):
        add_gate(add_score=hold_result("90"))


@pytest.mark.parametrize(
    "overrides",
    [
        {"lifecycle": entered(metadata={**METADATA, "parameter_set_id": "other"})},
        {"add_score": add_result(metadata={**METADATA, "strategy_version": "v9"})},
        {"projected_risk_at_stop": None},
    ],
)
def test_the_add_gate_refuses_a_mixed_parameter_set(overrides) -> None:
    if overrides.get("projected_risk_at_stop", "keep") is None:
        overrides = {
            "projected_risk_at_stop": replace(
                projected_risk(),
                config_metadata={**METADATA, "config_version": "other"},
            )
        }

    with pytest.raises(ValueError, match="config_metadata"):
        add_gate(**overrides)


def test_every_lifecycle_policy_refuses_a_mixed_parameter_set() -> None:
    # BTC-154, BTC-157 and BTC-158 are the epic's three composition boundaries.
    # A run must not mix parameter sets at any of them and then record itself
    # under only one.
    foreign = {**METADATA, "parameter_set_id": "other"}
    with pytest.raises(ValueError, match="config_metadata"):
        trim_rules_from_results(
            lifecycle=entered(metadata=foreign),
            hold_score=hold_result("45"),
            euphoria=euphoria_result(),
            crowding=crowding_result(),
            current_flow=flow_result("-0.5"),
            prior_flow=flow_result("0.5"),
            strategy_config=CONFIG,
        )
    with pytest.raises(ValueError, match="config_metadata"):
        exit_rules_for_position(
            lifecycle=entered(metadata=foreign),
            current_price="99000",
            hold_score=hold_result("80"),
            regime_invalidated=False,
            data_risk_exit_required=False,
            manual_research_override=False,
            manual_override_reason=None,
            strategy_config=CONFIG,
            evaluated_at=at(5),
        )
    with pytest.raises(ValueError, match="config_metadata"):
        add_gate(lifecycle=entered(metadata=foreign))


def test_the_add_gate_takes_its_signed_improvement_from_the_btc047_owner() -> None:
    component = risk_improvement_component_score(
        current_risk="10000", proposed_risk="12000"
    )

    result = add_gate(risk_improvement=component)

    # Independently: BTC-047's signed delta, not the floored one, is what tells
    # a worsened stop from an unchanged one, and both must block.
    assert component.signed_improvement == Decimal(
        str(risk_improvement(10000.0, 12000.0, floor_at_zero=False))
    )
    assert component.score == Decimal("0")
    assert result.permitted is False
    assert "ADD_REQUIREMENTS_STOP_CANNOT_IMPROVE" in result.reason_codes


# --- point in time across the epic ----------------------------------------


def test_a_trailing_stop_cannot_be_evaluated_before_the_ledger_watermark() -> None:
    lifecycle = apply_position_event(
        entered(), event=STOP_MOVE, event_time=at(9), stop_price="95000"
    )

    # The standing stop and the advance count come from the ledger as it stands
    # now, so a result stamped at day 4 would claim state from day 9. BTC-158
    # already refused the same composition.
    with pytest.raises(ValueError, match="watermark"):
        trail_stop_for_position(
            lifecycle, structure=structure("98000"), buffer=None, as_of=at(4)
        )


def test_an_exit_and_a_trailing_stop_agree_on_the_watermark_rule() -> None:
    lifecycle = apply_position_event(
        entered(), event=STOP_MOVE, event_time=at(9), stop_price="95000"
    )

    with pytest.raises(ValueError, match="watermark"):
        exit_rules_for_position(
            lifecycle=lifecycle,
            current_price="99000",
            hold_score=hold_result("80"),
            regime_invalidated=False,
            data_risk_exit_required=False,
            manual_research_override=False,
            manual_override_reason=None,
            strategy_config=CONFIG,
            evaluated_at=at(4),
        )


def test_a_structure_that_is_not_yet_available_cannot_advance_the_stop() -> None:
    lifecycle = entered()

    with pytest.raises(ValueError, match="available by as_of"):
        trail_stop_for_position(
            lifecycle,
            structure=structure("98000", day=8),
            buffer=buffer_for("98000"),
            as_of=at(4),
        )


# --- the composed long chain and its short mirror -------------------------


@pytest.mark.parametrize(
    ("direction", "entry", "stop", "advance_structure", "expected_stop_moves"),
    [
        ("long", "100000", "95000", "104000", True),
        ("short", "100000", "105000", "96000", True),
    ],
)
def test_the_epic_composes_into_one_coherent_trade(
    direction: str,
    entry: str,
    stop: str,
    advance_structure: str,
    expected_stop_moves: bool,
) -> None:
    lifecycle = entered(direction=direction, price=entry, stop=stop)
    assert lifecycle.state == OPEN_INITIAL

    trailed = trail_stop_for_position(
        lifecycle,
        structure=structure(advance_structure, direction=direction),
        buffer=buffer_for(advance_structure),
        as_of=at(2),
    )
    assert trailed.advanced is expected_stop_moves
    lifecycle = apply_trailing_stop(lifecycle, trailed, event_time=at(2))
    assert lifecycle.accepted is True
    assert lifecycle.stop_price == trailed.stop_price
    assert stop_advance_count(lifecycle) == 1

    # A stop that has advanced can never retreat, in either direction.
    retreat = apply_position_event(
        lifecycle, event=STOP_MOVE, event_time=at(3), stop_price=stop
    )
    assert retreat.accepted is False
    assert "POSITION_STATE_STOP_WOULD_WIDEN" in retreat.reason_codes
    assert retreat.stop_price == lifecycle.stop_price

    trim = trim_rules_from_results(
        lifecycle=lifecycle,
        hold_score=hold_result("45"),
        euphoria=euphoria_result(),
        crowding=crowding_result(),
        current_flow=flow_result("0.5"),
        prior_flow=flow_result("0.5"),
        strategy_config=CONFIG,
    )
    assert trim.signal is True
    assert trim.action == "TRIM"
    assert "EXIT" not in trim.effects

    reduced = apply_position_event(
        lifecycle, event=TRIM, event_time=at(4), quantity="0.4"
    )
    assert reduced.accepted is True
    assert reduced.quantity == Decimal("0.6")

    safe = reduced.stop_price * (
        Decimal("1.01") if direction == "long" else Decimal("0.99")
    )
    exit_signal = exit_rules_for_position(
        lifecycle=reduced,
        current_price=safe,
        hold_score=hold_result("30"),
        regime_invalidated=False,
        data_risk_exit_required=False,
        manual_research_override=False,
        manual_override_reason=None,
        strategy_config=CONFIG,
        evaluated_at=at(5),
    )
    assert exit_signal.signal is True
    assert exit_signal.exit_reasons == ("HOLD_SCORE_COLLAPSE",)

    # BTC-158 reads the stop BTC-156 advanced through BTC-150, not the entry
    # stop the trade was sized against.
    stopped = exit_rules_for_position(
        lifecycle=reduced,
        current_price=reduced.stop_price,
        hold_score=hold_result("80"),
        regime_invalidated=False,
        data_risk_exit_required=False,
        manual_research_override=False,
        manual_override_reason=None,
        strategy_config=CONFIG,
        evaluated_at=at(5),
    )
    assert stopped.exit_reasons == ("STRUCTURAL_STOP",)
    assert reduced.stop_price == trailed.stop_price

    closed = apply_position_event(reduced, event=EXIT, event_time=at(6))
    assert closed.state == "CLOSED"
    assert closed.quantity == 0
    assert closed.average_entry_price == reduced.average_entry_price
    assert restore_position_lifecycle(closed.as_record()).as_record() == (
        closed.as_record()
    )


def test_trim_and_exit_partition_the_hold_score_band_without_a_gap() -> None:
    thresholds = CONFIG.hold_thresholds
    lifecycle = entered()

    for raw in ("39.9", "40", "45", "49.9", "50", "60", "80"):
        score = Decimal(raw)
        trim = trim_rules_from_results(
            lifecycle=lifecycle,
            hold_score=hold_result(raw),
            euphoria=euphoria_result(),
            crowding=crowding_result(),
            current_flow=flow_result("0.5"),
            prior_flow=flow_result("0.5"),
            strategy_config=CONFIG,
        )
        exiting = exit_rules_for_position(
            lifecycle=lifecycle,
            current_price="99000",
            hold_score=hold_result(raw),
            regime_invalidated=False,
            data_risk_exit_required=False,
            manual_research_override=False,
            manual_override_reason=None,
            strategy_config=CONFIG,
            evaluated_at=at(5),
        )

        # Rulebook 20: <40 exits, 40-50 trims. Computed here from the config
        # rather than from either module, so the two cannot drift together.
        expect_exit = score < Decimal(str(thresholds.exit_below))
        expect_trim = (
            not expect_exit
            and score >= Decimal(str(thresholds.trim_min))
            and score < Decimal(str(thresholds.defensive_min))
        )
        assert exiting.signal is expect_exit, raw
        assert trim.signal is expect_trim, raw
        assert not (trim.signal and exiting.signal), raw


# --- refusals are economic no-ops -----------------------------------------


@pytest.mark.parametrize(
    ("event", "kwargs"),
    [
        (ADD, {"quantity": "1", "price": "90000"}),
        (TRIM, {"quantity": "5"}),
        (STOP_MOVE, {"stop_price": "80000"}),
        (ENTER, {"quantity": "1", "price": "100000", "stop_price": "90000"}),
    ],
)
def test_a_refused_lifecycle_event_mutates_no_economics(event, kwargs) -> None:
    lifecycle = entered()
    before = lifecycle.as_record()

    refused = apply_position_event(
        lifecycle, event=event, event_time=at(4), **kwargs
    )

    assert refused.accepted is False
    after = refused.as_record()
    for field in (
        "state",
        "quantity",
        "average_entry_price",
        "stop_price",
        "tranches",
        "opened_at",
        "closed_at",
        "last_event_at",
    ):
        assert after[field] == before[field], field


def test_a_defensive_position_refuses_the_add_the_gate_would_permit() -> None:
    defensive = apply_position_event(entered(), event=DEFEND, event_time=at(2))
    gate = add_gate(lifecycle=defensive, current_price="118000")

    refused = apply_position_event(
        defensive, event=ADD, event_time=at(3), quantity="1", price="118000"
    )

    # BTC-154 knows nothing of the transition table; the ledger is what makes
    # rulebook 24's NO ADDING effect binding once DEFENSIVE is entered.
    assert gate.permitted is True
    assert refused.accepted is False
    assert "POSITION_STATE_ADD_REFUSED_WHILE_DEFENSIVE" in refused.reason_codes
    assert refused.quantity == defensive.quantity


def test_no_epic_module_maps_a_hard_flag_onto_the_add_gate() -> None:
    # Known composition limit. Rulebook 24 gives STRESS / CROWDING / EUPHORIA
    # the shared effect NO ADDING, and BTC-150 makes DEFENSIVE the state that
    # enforces it -- but nothing in EPIC P emits DEFEND, and BTC-154 has no
    # hard-flag requirement. BTC-157 consumes the same flags for TRIM. Until an
    # owner wires the flags to DEFEND or to an add requirement, the composed
    # chain permits an add while CROWDING is active. Pinned rather than closed
    # here: choosing the mapping is a strategy decision, not a review fix.
    crowding = crowding_result(flagged=True)
    euphoria = euphoria_result(flagged=True)
    lifecycle = entered()

    trim = trim_rules_from_results(
        lifecycle=lifecycle,
        hold_score=hold_result("80"),
        euphoria=euphoria,
        crowding=crowding,
        current_flow=flow_result("0.5"),
        prior_flow=flow_result("0.5"),
        strategy_config=CONFIG,
    )
    gate = add_gate(lifecycle=lifecycle)

    assert crowding.flagged is True
    assert "TRIM_CROWDING_ACTIVE" in trim.reason_codes
    assert lifecycle.state == OPEN_INITIAL
    assert gate.permitted is True


# --- persistence and replay -----------------------------------------------


def test_a_refusal_before_the_fill_still_leaves_replayable_rows() -> None:
    # The refusal is recorded in the authoritative snapshot, but it has no
    # ``positions`` row to belong to. Persisting one skipped the accepted
    # arming that moved WATCH to PENDING_ENTRY, and the row set could no longer
    # be replayed at all.
    lifecycle = start_position_lifecycle(symbol=SYMBOL, config_metadata=METADATA)
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(0),
        quantity="1",
        price="100000",
        stop_price="90000",
    )
    assert lifecycle.accepted is False
    lifecycle = apply_position_event(lifecycle, event=ARM_ENTRY, event_time=at(1))
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=at(2),
        quantity="1",
        price="100000",
        stop_price="90000",
    )
    lifecycle = apply_position_event(
        lifecycle, event=TRIM, event_time=at(3), quantity="0.4"
    )
    lifecycle = apply_position_event(lifecycle, event=EXIT, event_time=at(4))

    rows = position_event_records(lifecycle)
    replayed = replay_position_event_records(
        rows, symbol=SYMBOL, config_metadata=METADATA
    )

    assert [row["action"] for row in rows] == ["ENTER", "TRIM", "EXIT"]
    assert replayed.state == lifecycle.state
    assert replayed.quantity == lifecycle.quantity
    assert replayed.average_entry_price == lifecycle.average_entry_price
    assert replayed.stop_price == lifecycle.stop_price
    # The pre-fill refusal is not lost; it stays in the authoritative snapshot.
    assert lifecycle.transitions[0].accepted is False
    assert restore_position_lifecycle(lifecycle.as_record()).transitions[0] == (
        lifecycle.transitions[0]
    )


def test_a_post_fill_refusal_is_still_persisted_and_replayed() -> None:
    lifecycle = entered()
    lifecycle = apply_position_event(
        lifecycle, event=ADD, event_time=at(2), quantity="1", price="90000"
    )
    assert lifecycle.accepted is False
    lifecycle = apply_position_event(lifecycle, event=EXIT, event_time=at(3))

    rows = position_event_records(lifecycle)
    replayed = replay_position_event_records(
        rows, symbol=SYMBOL, config_metadata=METADATA
    )

    assert [row["action"] for row in rows] == ["ENTER", "HOLD", "EXIT"]
    assert replayed.transitions[1].accepted is False
    assert "POSITION_STATE_ADD_REFUSED_AVERAGE_DOWN" in (
        replayed.transitions[1].reason_codes
    )


def test_a_trailing_advance_survives_the_round_trip_with_its_structure() -> None:
    lifecycle = entered(stop="95000")
    trailed = trail_stop_for_position(
        lifecycle,
        structure=structure("104000"),
        buffer=buffer_for("104000"),
        as_of=at(2),
    )
    lifecycle = apply_trailing_stop(lifecycle, trailed, event_time=at(2))

    replayed = replay_position_event_records(
        position_event_records(lifecycle), symbol=SYMBOL, config_metadata=METADATA
    )

    assert replayed.stop_price == lifecycle.stop_price
    assert stop_advance_count(replayed) == 1
    # A used structure cannot advance the stop a second time after replay.
    again = trail_stop_for_position(
        replayed,
        structure=structure("104000"),
        buffer=buffer_for("104000"),
        as_of=at(3),
    )
    assert again.advanced is False
    assert again.reason_codes == ("TRAILING_STOP_STRUCTURE_ALREADY_USED",)


def test_the_same_composed_inputs_produce_the_same_decisions() -> None:
    first = add_gate()
    second = add_gate()
    trim_one = trim_rules_from_results(
        lifecycle=entered(),
        hold_score=hold_result("45"),
        euphoria=euphoria_result(),
        crowding=crowding_result(),
        current_flow=flow_result("-0.5"),
        prior_flow=flow_result("0.5"),
        strategy_config=CONFIG,
    )
    trim_two = trim_rules_from_results(
        lifecycle=entered(),
        hold_score=hold_result("45"),
        euphoria=euphoria_result(),
        crowding=crowding_result(),
        current_flow=flow_result("-0.5"),
        prior_flow=flow_result("0.5"),
        strategy_config=CONFIG,
    )

    assert first.as_record() == second.as_record()
    assert trim_one.as_record() == trim_two.as_record()
    assert decision_equal(first.minimum_add_score, CONFIG.add_thresholds.add_min)
