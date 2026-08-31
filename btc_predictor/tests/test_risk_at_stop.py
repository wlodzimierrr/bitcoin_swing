"""BTC-146: portfolio risk-at-stop constraint."""

from decimal import Decimal

import pytest

from btc_predictor.config.strategy import load_strategy_config
from btc_predictor.risk import (
    ABSOLUTE_DISTANCE,
    DEFAULT_RISK_AT_STOP_CONVENTION,
    DEFAULT_RISK_AT_STOP_TARGET_FRACTION,
    FLOORED_AT_ZERO,
    RISK_AT_STOP_CONVENTIONS,
    RISK_AT_STOP_FEATURE_ID,
    RISK_AT_STOP_PARAMETER_STATUS,
    RISK_AT_STOP_POLICY_VERSION,
    RISK_AT_STOP_REASON_CODES,
    RiskAtStopResult,
    calculate_risk_at_stop,
)

NAV = "10000000"


def tranche(
    tranche_id: str,
    notional: str,
    entry_price: str,
) -> dict[str, object]:
    return {
        "tranche_id": tranche_id,
        "notional": notional,
        "entry_price": entry_price,
    }


def test_metadata_is_stable() -> None:
    assert RISK_AT_STOP_FEATURE_ID == "RISK_AT_STOP"
    assert RISK_AT_STOP_POLICY_VERSION == "RISK_AT_STOP_V1"
    assert RISK_AT_STOP_CONVENTIONS == (FLOORED_AT_ZERO, ABSOLUTE_DISTANCE)
    assert DEFAULT_RISK_AT_STOP_CONVENTION == FLOORED_AT_ZERO
    assert DEFAULT_RISK_AT_STOP_TARGET_FRACTION == Decimal("0.0075")
    assert RISK_AT_STOP_PARAMETER_STATUS == "PROVISIONAL_PENDING_BTC_185"


# --- aggregation across tranches ----------------------------------------


def test_risk_is_summed_across_tranches_not_measured_per_trade() -> None:
    result = calculate_risk_at_stop(
        [
            tranche("t1", "100000", "100000"),
            tranche("t2", "200000", "100000"),
        ],
        stop_price="95000",
        nav=NAV,
    )

    # 5% loss on 300,000 of combined notional.
    assert result.risk_at_stop == Decimal("15000.00")
    assert len(result.tranches) == 2
    assert sum(
        (item.risk_contribution for item in result.tranches), Decimal("0")
    ) == result.risk_at_stop


def test_all_tranches_share_one_stop() -> None:
    result = calculate_risk_at_stop(
        [
            tranche("low", "100000", "90000"),
            tranche("high", "100000", "110000"),
        ],
        stop_price="85000",
        nav=NAV,
    )
    contributions = {item.tranche_id: item.loss_fraction for item in result.tranches}

    # Each tranche measures its own entry against the same shared stop.
    assert contributions["low"] == (
        Decimal("90000") - Decimal("85000")
    ) / Decimal("90000")
    assert contributions["high"] == (
        Decimal("110000") - Decimal("85000")
    ) / Decimal("110000")
    assert contributions["high"] > contributions["low"]


def test_quantity_and_notional_forms_are_equivalent() -> None:
    by_notional = calculate_risk_at_stop(
        [tranche("t", "200000", "100000")], stop_price="95000", nav=NAV
    )
    by_quantity = calculate_risk_at_stop(
        [{"tranche_id": "t", "quantity": "2", "entry_price": "100000"}],
        stop_price="95000",
        nav=NAV,
    )

    # Rulebook 19 gives both forms as equivalent.
    assert by_notional.risk_at_stop == by_quantity.risk_at_stop == Decimal("10000.00")


def test_a_tranche_without_notional_or_quantity_is_rejected() -> None:
    with pytest.raises(ValueError, match="notional or quantity"):
        calculate_risk_at_stop(
            [{"tranche_id": "t", "entry_price": "100000"}],
            stop_price="95000",
            nav=NAV,
        )


def test_no_positions_means_no_open_risk() -> None:
    result = calculate_risk_at_stop([], stop_price="95000", nav=NAV)

    assert result.complete is True
    assert result.risk_at_stop == Decimal("0")
    assert "RISK_AT_STOP_NO_OPEN_RISK" in result.reason_codes


# --- the two rulebook conventions ---------------------------------------


def test_floored_convention_zeroes_a_profitable_tranche() -> None:
    result = calculate_risk_at_stop(
        [
            tranche("winner", "100000", "90000"),
            tranche("new", "100000", "100000"),
        ],
        stop_price="95000",
        nav=NAV,
    )
    by_id = {item.tranche_id: item for item in result.tranches}

    # The stop sits above the first entry, so that tranche cannot lose.
    assert by_id["winner"].profitable_at_stop is True
    assert by_id["winner"].risk_contribution == Decimal("0")
    assert result.risk_at_stop == Decimal("5000.00")


def test_absolute_convention_counts_a_profitable_tranche() -> None:
    result = calculate_risk_at_stop(
        [
            tranche("winner", "100000", "90000"),
            tranche("new", "100000", "100000"),
        ],
        stop_price="95000",
        nav=NAV,
        convention=ABSOLUTE_DISTANCE,
    )

    # The unsigned distance keeps the profitable tranche in the total, which is
    # why the two conventions are not interchangeable.
    assert result.risk_at_stop > Decimal("5000")
    assert result.convention == ABSOLUTE_DISTANCE


def test_the_conventions_agree_when_no_tranche_is_profitable() -> None:
    positions = [tranche("a", "100000", "100000"), tranche("b", "50000", "105000")]

    floored = calculate_risk_at_stop(positions, stop_price="95000", nav=NAV)
    absolute = calculate_risk_at_stop(
        positions, stop_price="95000", nav=NAV, convention=ABSOLUTE_DISTANCE
    )

    assert floored.risk_at_stop == absolute.risk_at_stop


def test_convention_is_persisted_so_the_choice_is_never_implicit() -> None:
    result = calculate_risk_at_stop(
        [tranche("t", "100000", "100000")], stop_price="95000", nav=NAV
    )

    # Rulebook 19 requires the convention be explicit and consistent across
    # advisory, paper trading and backtesting.
    assert result.as_record()["convention"] == FLOORED_AT_ZERO


def test_an_unknown_convention_is_rejected() -> None:
    with pytest.raises(ValueError, match="convention must be one of"):
        calculate_risk_at_stop(
            [tranche("t", "100000", "100000")],
            stop_price="95000",
            nav=NAV,
            convention="MARK_TO_MARKET",
        )


def test_the_rulebook_objective_holds_under_the_default_convention() -> None:
    """Notional can increase while total downside risk stays bounded."""

    first = calculate_risk_at_stop(
        [tranche("t1", "100000", "100000")], stop_price="95000", nav=NAV
    )
    added = calculate_risk_at_stop(
        [
            tranche("t1", "100000", "100000"),
            tranche("t2", "100000", "120000"),
        ],
        stop_price="115000",
        nav=NAV,
    )
    by_id = {item.tranche_id: item for item in added.tranches}

    # Exposure doubles, yet the raised stop makes the original tranche
    # riskless, so aggregate risk falls rather than compounding.
    assert sum(item.notional for item in added.tranches) == Decimal("200000")
    assert by_id["t1"].risk_contribution == Decimal("0")
    assert added.risk_at_stop < first.risk_at_stop
    assert added.within_maximum is True


def test_a_large_add_raises_risk_but_stays_measurable_against_the_cap() -> None:
    """Adding is not automatically safe; the constraint is what bounds it."""

    added = calculate_risk_at_stop(
        [
            tranche("t1", "100000", "100000"),
            tranche("t2", "300000", "120000"),
        ],
        stop_price="115000",
        nav=NAV,
    )

    # A tranche three times the size still carries its own risk to the stop.
    assert added.risk_at_stop == Decimal("12500.00000000000000000000000")
    assert added.within_maximum is True
    assert added.headroom_amount > 0


# --- the NAV ceiling -----------------------------------------------------


def test_risk_within_the_target_is_reported_as_such() -> None:
    result = calculate_risk_at_stop(
        [tranche("t", "1000000", "100000")], stop_price="95000", nav=NAV
    )

    # 50,000 on 10,000,000 NAV is 0.5%, inside the 0.75% target.
    assert result.risk_fraction_nav == Decimal("0.005")
    assert result.within_maximum is True
    assert result.reason_codes == ("RISK_AT_STOP_WITHIN_TARGET",)


def test_risk_between_target_and_maximum_warns_without_breaching() -> None:
    result = calculate_risk_at_stop(
        [tranche("t", "1800000", "100000")], stop_price="95000", nav=NAV
    )

    # 90,000 is 0.9% of NAV: above the 0.75% target, under the 1.00% ceiling.
    assert result.risk_fraction_nav == Decimal("0.009")
    assert result.within_maximum is True
    assert result.reason_codes == ("RISK_AT_STOP_ABOVE_TARGET",)


def test_risk_above_the_maximum_is_a_breach() -> None:
    result = calculate_risk_at_stop(
        [tranche("t", "3000000", "100000")], stop_price="95000", nav=NAV
    )

    # 150,000 is 1.5% of NAV, beyond the configured 1.00% ceiling.
    assert result.risk_fraction_nav == Decimal("0.015")
    assert result.within_maximum is False
    assert "RISK_AT_STOP_EXCEEDS_MAXIMUM" in result.reason_codes


def test_the_maximum_boundary_is_inclusive() -> None:
    result = calculate_risk_at_stop(
        [tranche("t", "2000000", "100000")], stop_price="95000", nav=NAV
    )

    assert result.risk_fraction_nav == Decimal("0.01")
    assert result.within_maximum is True


def test_the_ceiling_comes_from_the_versioned_strategy_config() -> None:
    result = calculate_risk_at_stop(
        [tranche("t", "100000", "100000")], stop_price="95000", nav=NAV
    )
    config = load_strategy_config()

    assert result.maximum_fraction_nav == Decimal(
        str(config.risk.max_risk_at_stop_fraction_nav)
    )
    # The rulebook band is 0.75%-1.00%; config picks the upper end.
    assert Decimal("0.0075") <= result.maximum_fraction_nav <= Decimal("0.01")


def test_headroom_reports_how_much_risk_remains() -> None:
    result = calculate_risk_at_stop(
        [tranche("t", "1000000", "100000")], stop_price="95000", nav=NAV
    )

    # 1.00% of 10,000,000 is 100,000; 50,000 is used.
    assert result.headroom_amount == Decimal("50000.00")


def test_headroom_never_goes_negative_on_a_breach() -> None:
    result = calculate_risk_at_stop(
        [tranche("t", "3000000", "100000")], stop_price="95000", nav=NAV
    )

    assert result.headroom_amount == Decimal("0")
    assert result.within_maximum is False


def test_a_target_above_the_maximum_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not exceed maximum"):
        calculate_risk_at_stop(
            [tranche("t", "100000", "100000")],
            stop_price="95000",
            nav=NAV,
            target_fraction_nav="0.05",
            maximum_fraction_nav="0.01",
        )


# --- short side ----------------------------------------------------------


def test_short_risk_is_measured_upward_to_the_stop() -> None:
    result = calculate_risk_at_stop(
        [tranche("t", "1000000", "100000")],
        stop_price="105000",
        nav=NAV,
        direction="short",
    )

    assert result.risk_at_stop == Decimal("50000.00")
    assert result.tranches[0].profitable_at_stop is False


def test_a_short_tranche_below_the_stop_is_floored() -> None:
    result = calculate_risk_at_stop(
        [tranche("winner", "1000000", "110000")],
        stop_price="105000",
        nav=NAV,
        direction="short",
    )

    assert result.tranches[0].profitable_at_stop is True
    assert result.risk_at_stop == Decimal("0")


# --- BTC-047 parity ------------------------------------------------------


def test_matches_the_btc047_risk_at_stop_kernel() -> None:
    from btc_predictor.quant.risk import risk_at_stop

    result = calculate_risk_at_stop(
        [
            tranche("a", "100000", "100000"),
            tranche("b", "200000", "110000"),
            tranche("c", "150000", "90000"),
        ],
        stop_price="95000",
        nav=NAV,
    )
    expected = risk_at_stop(
        [100000.0, 200000.0, 150000.0],
        [100000.0, 110000.0, 90000.0],
        [95000.0, 95000.0, 95000.0],
        side="long",
    )

    assert abs(float(result.risk_at_stop) - float(expected)) < 1e-6


# --- missing inputs, determinism, persistence ----------------------------


@pytest.mark.parametrize("missing", ["stop_price", "nav"])
def test_missing_inputs_yield_no_measurement(missing: str) -> None:
    kwargs = {"stop_price": "95000", "nav": NAV}
    kwargs[missing] = None

    result = calculate_risk_at_stop([tranche("t", "100000", "100000")], **kwargs)

    assert result.complete is False
    assert result.risk_at_stop is None
    assert result.within_maximum is False
    assert result.reason_codes == ("RISK_AT_STOP_INPUT_MISSING",)


def test_recomputation_is_deterministic() -> None:
    positions = [tranche("a", "100000", "100000"), tranche("b", "50000", "92000")]

    first = calculate_risk_at_stop(positions, stop_price="95000", nav=NAV)
    second = calculate_risk_at_stop(positions, stop_price="95000", nav=NAV)

    assert first.as_record() == second.as_record()


def test_record_is_persistable_and_reconstructable() -> None:
    config = load_strategy_config()
    result = calculate_risk_at_stop(
        [tranche("t1", "1000000", "100000")],
        stop_price="95000",
        nav=NAV,
        config=config,
        config_metadata=config.run_metadata(),
    )
    record = result.as_record()

    assert isinstance(result, RiskAtStopResult)
    assert record["feature_id"] == "RISK_AT_STOP"
    assert record["convention"] == "FLOORED_AT_ZERO"
    assert record["risk_at_stop"] == "50000.00"
    assert record["risk_fraction_nav"] == "0.005"
    assert record["maximum_fraction_nav"] == "0.01"
    assert record["within_maximum"] is True
    # Every tranche contribution is retained, so the total is auditable.
    assert record["tranches"][0]["risk_contribution"] == "50000.00"
    assert record["config_metadata"] == config.run_metadata()
    assert (
        Decimal(record["risk_at_stop"]) / Decimal(record["nav"])
        == Decimal(record["risk_fraction_nav"])
    )


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        calculate_risk_at_stop(
            [tranche("t", "1000000", "100000")], stop_price="95000", nav=NAV
        ),
        calculate_risk_at_stop(
            [tranche("t", "1800000", "100000")], stop_price="95000", nav=NAV
        ),
        calculate_risk_at_stop(
            [tranche("t", "3000000", "100000")], stop_price="95000", nav=NAV
        ),
        calculate_risk_at_stop([], stop_price="95000", nav=NAV),
        calculate_risk_at_stop([], stop_price=None, nav=NAV),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in RISK_AT_STOP_REASON_CODES
