"""BTC-144: conviction-based risk budget."""

from decimal import Decimal

import pytest

from btc_predictor.config.strategy import load_strategy_config
from btc_predictor.risk import (
    RISK_BUDGET_FEATURE_ID,
    RISK_BUDGET_PARAMETER_STATUS,
    RISK_BUDGET_POLICY_VERSION,
    RISK_BUDGET_REASON_CODES,
    RiskBudgetBand,
    RiskBudgetResult,
    calculate_risk_budget,
    risk_schedule_from_config,
)


def test_metadata_is_stable() -> None:
    assert RISK_BUDGET_FEATURE_ID == "RISK_BUDGET"
    assert RISK_BUDGET_POLICY_VERSION == "RISK_BUDGET_V1"
    assert RISK_BUDGET_PARAMETER_STATUS == "PROVISIONAL_PENDING_BTC_185"


# --- the rulebook schedule ----------------------------------------------


@pytest.mark.parametrize(
    ("conviction", "expected"),
    [
        ("80", Decimal("0.0035")),
        ("82", Decimal("0.0035")),
        ("84", Decimal("0.0035")),
        ("84.999", Decimal("0.0035")),
        ("85", Decimal("0.005")),
        ("87", Decimal("0.005")),
        ("89", Decimal("0.005")),
        ("89.999", Decimal("0.005")),
        ("90", Decimal("0.006")),
        ("95", Decimal("0.006")),
        ("100", Decimal("0.006")),
    ],
)
def test_conviction_maps_to_the_declared_nav_fraction(
    conviction: str,
    expected: Decimal,
) -> None:
    result = calculate_risk_budget(entry_conviction=conviction)

    assert result.risk_fraction_nav == expected
    assert result.complete is True
    assert "RISK_BUDGET_ASSIGNED" in result.reason_codes


def test_bands_are_half_open_so_boundaries_are_unambiguous() -> None:
    lower = calculate_risk_budget(entry_conviction="85")
    just_below = calculate_risk_budget(entry_conviction="84.9999")

    # 85 belongs to the 85-89 band, not to 80-84.
    assert lower.risk_fraction_nav == Decimal("0.005")
    assert just_below.risk_fraction_nav == Decimal("0.0035")
    assert lower.selected_band.min_entry_conviction == Decimal("85")


def test_the_schedule_is_monotonic_in_conviction() -> None:
    fractions = [
        calculate_risk_budget(entry_conviction=value).risk_fraction_nav
        for value in ("80", "85", "90")
    ]

    assert fractions == sorted(fractions)
    assert len(set(fractions)) == 3


# --- below the lowest band ----------------------------------------------


@pytest.mark.parametrize("conviction", ["0", "50", "69", "70", "75", "79", "79.999"])
def test_conviction_below_the_lowest_band_gets_no_budget(conviction: str) -> None:
    result = calculate_risk_budget(entry_conviction=conviction, nav="1000000")

    # Under 80 is WATCH or IGNORE, so the answer is "no budget", never a
    # silently reduced one.
    assert result.complete is False
    assert result.risk_fraction_nav is None
    assert result.risk_budget_amount is None
    assert result.selected_band is None
    assert result.reason_codes == ("RISK_BUDGET_BELOW_MINIMUM_CONVICTION",)


def test_missing_conviction_yields_no_budget() -> None:
    result = calculate_risk_budget(entry_conviction=None)

    assert result.complete is False
    assert result.risk_fraction_nav is None
    assert result.reason_codes == ("RISK_BUDGET_INPUT_MISSING",)


# --- config as the single source ----------------------------------------


def test_schedule_is_read_from_the_versioned_strategy_config() -> None:
    bands, maximum = risk_schedule_from_config()
    config = load_strategy_config()

    # The bands are not hardcoded here; they mirror risk.schedule.
    assert len(bands) == len(config.risk.schedule)
    assert [band.risk_fraction_nav for band in bands] == [
        Decimal("0.0035"),
        Decimal("0.005"),
        Decimal("0.006"),
    ]
    assert maximum == Decimal(str(config.risk.max_risk_at_stop_fraction_nav))


def test_config_schedule_matches_the_rulebook_table() -> None:
    bands, _ = risk_schedule_from_config()

    assert [
        (band.min_entry_conviction, band.max_entry_conviction)
        for band in bands
    ] == [
        (Decimal("80"), Decimal("85")),
        (Decimal("85"), Decimal("90")),
        (Decimal("90"), None),
    ]


def test_an_explicit_schedule_overrides_the_config() -> None:
    schedule = (
        RiskBudgetBand(
            min_entry_conviction=Decimal("60"),
            max_entry_conviction=None,
            risk_fraction_nav=Decimal("0.002"),
        ),
    )

    result = calculate_risk_budget(
        entry_conviction="65",
        schedule=schedule,
        maximum_risk_fraction_nav="0.01",
    )

    assert result.risk_fraction_nav == Decimal("0.002")
    assert result.complete is True


def test_an_empty_schedule_is_rejected() -> None:
    with pytest.raises(ValueError, match="risk schedule must not be empty"):
        calculate_risk_budget(
            entry_conviction="85", schedule=(), maximum_risk_fraction_nav="0.01"
        )


# --- the global cap ------------------------------------------------------


def test_a_band_above_the_global_cap_is_capped() -> None:
    schedule = (
        RiskBudgetBand(
            min_entry_conviction=Decimal("80"),
            max_entry_conviction=None,
            risk_fraction_nav=Decimal("0.05"),
        ),
    )

    result = calculate_risk_budget(
        entry_conviction="85",
        schedule=schedule,
        maximum_risk_fraction_nav="0.01",
    )

    # The schedule can never exceed the configured maximum risk at stop.
    assert result.risk_fraction_nav == Decimal("0.01")
    assert "RISK_BUDGET_CAPPED_AT_MAXIMUM" in result.reason_codes


def test_the_default_schedule_sits_below_the_configured_cap() -> None:
    for conviction in ("80", "85", "90"):
        result = calculate_risk_budget(entry_conviction=conviction)
        assert result.risk_fraction_nav < result.maximum_risk_fraction_nav
        assert "RISK_BUDGET_CAPPED_AT_MAXIMUM" not in result.reason_codes


# --- NAV denomination ----------------------------------------------------


def test_nav_converts_the_fraction_into_a_currency_budget() -> None:
    result = calculate_risk_budget(entry_conviction="85", nav="1000000")

    # BTC-145 divides this by the stop distance to size a position.
    assert result.risk_budget_amount == Decimal("5000.000")
    assert result.nav == Decimal("1000000")


def test_nav_is_optional() -> None:
    result = calculate_risk_budget(entry_conviction="85")

    assert result.complete is True
    assert result.risk_fraction_nav == Decimal("0.005")
    assert result.nav is None
    assert result.risk_budget_amount is None


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"entry_conviction": "-1"}, "entry_conviction must be between"),
        ({"entry_conviction": "101"}, "entry_conviction must be between"),
        ({"entry_conviction": "85", "nav": "0"}, "nav must be positive"),
        ({"entry_conviction": "85", "nav": "-100"}, "nav must be positive"),
    ],
)
def test_invalid_inputs_fail_fast(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        calculate_risk_budget(**kwargs)


# --- determinism and persistence ----------------------------------------


def test_recomputation_is_deterministic() -> None:
    first = calculate_risk_budget(entry_conviction="87", nav="250000")
    second = calculate_risk_budget(entry_conviction="87", nav="250000")

    assert first.as_record() == second.as_record()


def test_record_is_persistable_and_reconstructable() -> None:
    result = calculate_risk_budget(
        entry_conviction="87",
        nav="1000000",
        config_metadata={"config_version": "strategy_config_v2"},
    )
    record = result.as_record()

    assert isinstance(result, RiskBudgetResult)
    assert record["feature_id"] == "RISK_BUDGET"
    assert record["policy_version"] == "RISK_BUDGET_V1"
    assert record["entry_conviction"] == "87"
    assert record["risk_fraction_nav"] == "0.005"
    assert record["risk_budget_amount"] == "5000.000"
    # The band that produced the fraction is persisted, not just the result.
    # Bounds render as floats because the strategy config stores them as TOML
    # floats; Decimal comparison is unaffected.
    assert record["selected_band"] == {
        "min_entry_conviction": "85.0",
        "max_entry_conviction": "90.0",
        "risk_fraction_nav": "0.005",
    }
    assert Decimal(record["selected_band"]["min_entry_conviction"]) == Decimal("85")
    # The whole schedule is retained so the assignment is reconstructable.
    assert len(record["schedule"]) == 3
    assert record["maximum_risk_fraction_nav"] == "0.01"
    assert record["config_metadata"] == {"config_version": "strategy_config_v2"}
    assert (
        Decimal(record["nav"]) * Decimal(record["risk_fraction_nav"])
        == Decimal(record["risk_budget_amount"])
    )


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    results = [
        calculate_risk_budget(entry_conviction="85"),
        calculate_risk_budget(entry_conviction="70"),
        calculate_risk_budget(entry_conviction=None),
        calculate_risk_budget(
            entry_conviction="85",
            schedule=(
                RiskBudgetBand(
                    min_entry_conviction=Decimal("80"),
                    max_entry_conviction=None,
                    risk_fraction_nav=Decimal("0.05"),
                ),
            ),
            maximum_risk_fraction_nav="0.01",
        ),
    ]

    for result in results:
        for code in result.reason_codes:
            assert code in RISK_BUDGET_REASON_CODES
