"""Independent BTC-146 aggregate-risk correctness regressions."""

from dataclasses import replace
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.portfolio import Tranche
from btc_predictor.quant import risk_at_stop as quant_risk_at_stop
from btc_predictor.risk import (
    ABSOLUTE_DISTANCE,
    FLOORED_AT_ZERO,
    RISK_AT_STOP_PARAMETER_STATUS,
    calculate_risk_at_stop,
)


NAV = Decimal("1000000")


def tranche(identifier: object, notional: object, entry: object) -> dict[str, object]:
    return {
        "tranche_id": identifier,
        "notional": notional,
        "entry_price": entry,
    }


def test_three_individually_small_tranches_breach_in_aggregate() -> None:
    result = calculate_risk_at_stop(
        [
            tranche("a", "500000", "100"),
            tranche("b", "500000", "100"),
            tranche("c", "500000", "100"),
        ],
        stop_price="99",
        nav=NAV,
    )

    assert [item.risk_contribution for item in result.tranches] == [
        Decimal("5000.00"),
        Decimal("5000.00"),
        Decimal("5000.00"),
    ]
    assert result.risk_at_stop == Decimal("15000.00")
    assert result.risk_fraction_nav == Decimal("0.015")
    assert result.within_maximum is False
    assert result.reason_codes == ("RISK_AT_STOP_EXCEEDS_MAXIMUM",)


def test_review_long_example_distinguishes_both_conventions_exactly() -> None:
    positions = [
        tranche("A", "500000", "100"),
        tranche("B", "500000", "110"),
    ]

    floored = calculate_risk_at_stop(positions, stop_price="105", nav=NAV)
    absolute = calculate_risk_at_stop(
        positions,
        stop_price="105",
        nav=NAV,
        convention=ABSOLUTE_DISTANCE,
    )

    assert floored.tranches[0].signed_loss_fraction == Decimal("-0.05")
    assert floored.tranches[0].risk_contribution == Decimal("0")
    assert floored.risk_at_stop == Decimal("22727.27272727272727272727272")
    assert absolute.tranches[0].risk_contribution == Decimal("25000.00")
    assert absolute.risk_at_stop == Decimal("47727.27272727272727272727272")


def test_short_conventions_are_directionally_symmetric() -> None:
    positions = [
        tranche("loser", "500000", "100"),
        tranche("protected", "500000", "110"),
    ]

    floored = calculate_risk_at_stop(
        positions,
        stop_price="105",
        nav=NAV,
        direction="short",
    )
    absolute = calculate_risk_at_stop(
        positions,
        stop_price="105",
        nav=NAV,
        direction="short",
        convention=ABSOLUTE_DISTANCE,
    )

    by_id = {item.tranche_id: item for item in floored.tranches}
    assert by_id["loser"].risk_contribution == Decimal("25000.00")
    assert by_id["protected"].risk_contribution == Decimal("0")
    assert absolute.risk_at_stop == Decimal("47727.27272727272727272727272")


@pytest.mark.parametrize(
    ("fraction", "reason", "within"),
    [
        ("0.007499", "RISK_AT_STOP_WITHIN_TARGET", True),
        ("0.0075", "RISK_AT_STOP_WITHIN_TARGET", True),
        ("0.007501", "RISK_AT_STOP_ABOVE_TARGET", True),
        ("0.009999", "RISK_AT_STOP_ABOVE_TARGET", True),
        ("0.01", "RISK_AT_STOP_ABOVE_TARGET", True),
        ("0.010001", "RISK_AT_STOP_EXCEEDS_MAXIMUM", False),
    ],
)
def test_target_and_ceiling_boundaries(
    fraction: str,
    reason: str,
    within: bool,
) -> None:
    desired = Decimal(fraction)
    notional = NAV * desired / Decimal("0.01")

    result = calculate_risk_at_stop(
        [tranche("boundary", notional, "100")],
        stop_price="99",
        nav=NAV,
    )

    assert result.risk_fraction_nav == desired
    assert result.reason_codes == (reason,)
    assert result.within_maximum is within
    assert result.headroom_amount == max(
        NAV * Decimal("0.01") - NAV * desired,
        Decimal("0"),
    )


def test_large_add_can_cross_target_and_hard_ceiling() -> None:
    original = tranche("original", "500000", "100")
    small_add = tranche("small_add", "180000", "120")
    large_add = tranche("large_add", "300000", "120")

    target_cross = calculate_risk_at_stop(
        [original, small_add],
        stop_price="115",
        nav=NAV,
    )
    ceiling_breach = calculate_risk_at_stop(
        [original, large_add],
        stop_price="115",
        nav=NAV,
    )

    assert target_cross.risk_at_stop == Decimal(
        "7500.000000000000000000000001",
    )
    assert target_cross.reason_codes == ("RISK_AT_STOP_WITHIN_TARGET",)
    assert ceiling_breach.risk_at_stop == Decimal("12500.00")
    assert ceiling_breach.reason_codes == ("RISK_AT_STOP_EXCEEDS_MAXIMUM",)


def test_exposure_can_rise_while_floored_risk_falls() -> None:
    before = calculate_risk_at_stop(
        [tranche("original", "500000", "100")],
        stop_price="95",
        nav=NAV,
    )
    after = calculate_risk_at_stop(
        [
            tranche("original", "500000", "100"),
            tranche("add", "250000", "120"),
        ],
        stop_price="118",
        nav=NAV,
    )

    assert sum(item.notional for item in after.tranches) > sum(
        item.notional for item in before.tranches
    )
    assert after.risk_at_stop < before.risk_at_stop


@pytest.mark.parametrize("direction", ["long", "short"])
def test_floored_convention_matches_btc047_across_mixed_tranches(
    direction: str,
) -> None:
    entries = [Decimal("100"), Decimal("110"), Decimal("90"), Decimal("105")]
    notionals = [Decimal("0"), Decimal("500000"), Decimal("250000"), Decimal("1")]
    stop = Decimal("105") if direction == "short" else Decimal("95")
    positions = [
        tranche(str(index), notional, entry)
        for index, (notional, entry) in enumerate(zip(notionals, entries), start=1)
    ]

    result = calculate_risk_at_stop(
        positions,
        stop_price=stop,
        nav="100000000",
        direction=direction,
    )
    expected = quant_risk_at_stop(
        [float(value) for value in notionals],
        [float(value) for value in entries],
        [float(stop)] * len(entries),
        side=direction,
    )

    assert float(result.risk_at_stop) == pytest.approx(float(expected))
    assert result.risk_at_stop == sum(
        (item.risk_contribution for item in result.tranches),
        Decimal("0"),
    )


def test_persisted_contributions_are_canonical_and_order_independent() -> None:
    positions = [
        tranche("b", "500000", "110"),
        tranche("a", "500000", "100"),
        tranche("c", "250000", "120"),
    ]

    first = calculate_risk_at_stop(positions, stop_price="105", nav=NAV)
    second = calculate_risk_at_stop(
        list(reversed(positions)),
        stop_price="105",
        nav=NAV,
    )

    assert [item.tranche_id for item in first.tranches] == ["a", "b", "c"]
    assert first.as_record() == second.as_record()


@pytest.mark.parametrize(
    "positions",
    [
        [tranche("duplicate", "1", "100"), tranche("duplicate", "2", "100")],
        [{"notional": "1", "entry_price": "100"}],
        [tranche("", "1", "100")],
    ],
)
def test_missing_or_duplicate_tranche_identity_is_rejected(
    positions: list[dict[str, object]],
) -> None:
    with pytest.raises(ValueError, match="tranche ident"):
        calculate_risk_at_stop(positions, stop_price="99", nav=NAV)


def test_lifecycle_tranche_number_is_a_supported_identifier() -> None:
    result = calculate_risk_at_stop(
        [
            Tranche(
                tranche_number=2,
                quantity=Decimal("1"),
                entry_price=Decimal("100"),
                opened_at=datetime(2026, 8, 31, tzinfo=UTC),
            ),
        ],
        stop_price="99",
        nav=NAV,
    )

    assert result.tranches[0].tranche_id == "2"


def test_config_identity_and_parameter_status_are_persisted_automatically() -> None:
    config = load_strategy_config()
    result = calculate_risk_at_stop(
        [tranche("one", "1", "100")],
        stop_price="99",
        nav=NAV,
        config=config,
    )
    record = result.as_record()

    assert record["config_metadata"] == config.run_metadata()
    assert record["parameter_status"] == RISK_AT_STOP_PARAMETER_STATUS
    assert record["target_fraction_nav"] == "0.0075"
    assert record["maximum_fraction_nav"] == "0.01"


def test_mismatched_config_identity_is_rejected() -> None:
    with pytest.raises(ValueError, match="must match the supplied strategy config"):
        calculate_risk_at_stop(
            [tranche("one", "1", "100")],
            stop_price="99",
            nav=NAV,
            config_metadata={
                "config_version": "strategy_config_v2",
                "strategy_version": "swing_v1.2",
                "parameter_set_id": "different",
            },
        )


def test_persisted_result_rejects_aggregate_or_tranche_drift() -> None:
    result = calculate_risk_at_stop(
        [tranche("one", "500000", "100")],
        stop_price="99",
        nav=NAV,
    )

    with pytest.raises(ValueError, match="sum of tranche contributions"):
        replace(result, risk_at_stop=Decimal("0")).as_record()
    bad_tranche = replace(result.tranches[0], risk_contribution=Decimal("0"))
    with pytest.raises(ValueError, match="shared-stop geometry"):
        replace(result, tranches=(bad_tranche,)).as_record()


@pytest.mark.parametrize("value", ["NaN", "Infinity", "-Infinity"])
def test_non_finite_inputs_fail_with_domain_errors(value: str) -> None:
    with pytest.raises(ValueError, match="must be finite"):
        calculate_risk_at_stop(
            [tranche("one", value, "100")],
            stop_price="99",
            nav=NAV,
        )


def test_zero_notional_is_valid_zero_risk_not_missing_data() -> None:
    result = calculate_risk_at_stop(
        [tranche("zero", "0", "100")],
        stop_price="99",
        nav=NAV,
    )

    assert result.complete is True
    assert result.risk_at_stop == Decimal("0")
    assert result.reason_codes == (
        "RISK_AT_STOP_NO_OPEN_RISK",
        "RISK_AT_STOP_WITHIN_TARGET",
    )


def test_shared_stop_movement_is_monotonic_for_unchanged_positions() -> None:
    positions = [tranche("a", "500000", "100"), tranche("b", "500000", "110")]
    long_risks = [
        calculate_risk_at_stop(positions, stop_price=stop, nav=NAV).risk_at_stop
        for stop in ("90", "100", "105", "115")
    ]
    short_risks = [
        calculate_risk_at_stop(
            positions,
            stop_price=stop,
            nav=NAV,
            direction="short",
        ).risk_at_stop
        for stop in ("120", "110", "105", "95")
    ]

    assert long_risks == sorted(long_risks, reverse=True)
    assert short_risks == sorted(short_risks, reverse=True)


def test_large_exposure_does_not_change_the_risk_only_verdict_contract() -> None:
    result = calculate_risk_at_stop(
        [tranche("leveraged", "2000000", "100")],
        stop_price="99.9",
        nav=NAV,
    )

    assert sum(item.notional for item in result.tranches) == NAV * Decimal("2")
    assert result.risk_fraction_nav == Decimal("0.002")
    assert result.within_maximum is True
    assert not hasattr(result, "within_leverage_limit")
