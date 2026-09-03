"""BTC-160: paper trading account and its execution cost model."""

from dataclasses import replace
from datetime import datetime, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.db.portfolio import paper_accounts
from btc_predictor.portfolio import (
    ACCOUNT_ACTIVE,
    ACCOUNT_ARCHIVED,
    BASIS_POINT,
    EXECUTION_COST_POLICY_VERSION,
    PAPER_ACCOUNT_FEATURE_ID,
    PAPER_ACCOUNT_POLICY_VERSION,
    PAPER_ACCOUNT_REASON_CODES,
    PAPER_ACCOUNT_STATUSES,
    ExecutionCosts,
    PaperAccount,
    execution_costs_from_config,
    open_paper_account,
)


CREATED_AT = datetime(2024, 8, 1, tzinfo=timezone.utc)
NOTIONAL = "100000"


def account(**kwargs) -> PaperAccount:
    base = {"account_name": "paper-1", "created_at": CREATED_AT}
    return open_paper_account(**{**base, **kwargs})


def test_metadata_is_stable() -> None:
    assert PAPER_ACCOUNT_FEATURE_ID == "PAPER_ACCOUNT"
    assert PAPER_ACCOUNT_POLICY_VERSION == "PAPER_ACCOUNT_V1"
    assert EXECUTION_COST_POLICY_VERSION == "EXECUTION_COST_V1"
    assert BASIS_POINT == Decimal("0.0001")


# --- the five configurables ----------------------------------------------


def test_every_configurable_comes_from_versioned_config() -> None:
    config = load_strategy_config()

    opened = account(config=config)

    # Rulebook 32 rule 15: advisory, paper and backtest share one set of
    # assumptions, so these are read rather than restated in a paper-only block.
    assert opened.starting_nav == Decimal(str(config.backtest.initial_cash))
    assert opened.costs.fee_bps == Decimal(str(config.backtest.fee_bps))
    assert opened.costs.slippage_bps == Decimal(str(config.backtest.slippage_bps))
    assert opened.costs.funding_cost_bps_per_day == Decimal(
        str(config.backtest.funding_cost_bps_per_day)
    )
    assert opened.available_cash == opened.cash


def test_execution_costs_are_shared_with_the_backtest_assumptions() -> None:
    config = load_strategy_config()

    assert execution_costs_from_config(config) == account(config=config).costs


def test_configurables_can_be_overridden_deliberately() -> None:
    costs = ExecutionCosts(
        policy_version=EXECUTION_COST_POLICY_VERSION,
        fee_bps=Decimal("2"),
        slippage_bps=Decimal("1"),
        funding_cost_bps_per_day=Decimal("0.5"),
    )

    opened = account(starting_nav="250000", reserved_cash="50000", costs=costs)

    assert opened.starting_nav == Decimal("250000")
    assert opened.costs.fee_bps == Decimal("2")
    assert opened.available_cash == Decimal("200000")


def test_opened_account_starts_active_and_flat() -> None:
    opened = account()

    assert opened.status == ACCOUNT_ACTIVE
    assert opened.is_active is True
    assert opened.cash == opened.starting_nav
    assert opened.realized_pnl == Decimal("0")
    assert opened.fees_paid == Decimal("0")
    assert opened.funding_paid == Decimal("0")
    assert opened.reason_codes == ("PAPER_ACCOUNT_OPENED",)


# --- NAV is not cash ------------------------------------------------------


def test_nav_is_cash_plus_unrealized_value() -> None:
    opened = account(starting_nav="100000")

    # BTC-144, BTC-145 and BTC-146 all size against NAV. Sizing against cash
    # would shrink every position as soon as a trade moved into profit.
    assert opened.nav() == Decimal("100000")
    assert opened.nav(unrealized_pnl="25000") == Decimal("125000")
    assert opened.nav(unrealized_pnl="-10000") == Decimal("90000")


def test_nav_and_cash_diverge_once_a_position_is_open() -> None:
    opened = account(starting_nav="100000")

    assert opened.nav(unrealized_pnl="8000") != opened.cash


def test_sizing_reads_nav_not_available_cash() -> None:
    from btc_predictor.risk import calculate_risk_budget

    opened = account(starting_nav="100000", reserved_cash="40000")
    budget = calculate_risk_budget(
        entry_conviction="85",
        nav=opened.nav(unrealized_pnl="20000"),
    )

    # The reserve constrains deployable cash, never the risk denominator.
    assert opened.available_cash == Decimal("60000")
    assert budget.nav == Decimal("120000")
    assert budget.risk_budget_amount == Decimal("600.000")


# --- available cash -------------------------------------------------------


def test_available_cash_is_the_balance_less_the_reserve() -> None:
    opened = account(starting_nav="200000", reserved_cash="50000")

    assert opened.cash == Decimal("200000")
    assert opened.available_cash == Decimal("150000")


def test_available_cash_defaults_to_the_whole_balance() -> None:
    opened = account(starting_nav="200000")

    assert opened.reserved_cash == Decimal("0")
    assert opened.available_cash == Decimal("200000")


def test_available_cash_is_floored_at_zero() -> None:
    opened = account(starting_nav="100000", reserved_cash="90000")
    drawn = opened.settle_realized_pnl("-50000")

    assert drawn.cash == Decimal("50000")
    assert drawn.available_cash == Decimal("0")


def test_a_reserve_larger_than_the_account_is_a_configuration_error() -> None:
    # Silently clamping would produce an account that refuses every trade for
    # no stated reason.
    with pytest.raises(ValueError, match="reserved_cash must not exceed"):
        account(starting_nav="100000", reserved_cash="150000")


# --- fees, slippage, funding ---------------------------------------------


def test_ten_basis_points_is_one_tenth_of_one_percent() -> None:
    costs = execution_costs_from_config()

    assert costs.fee_bps == Decimal("10.0")
    assert costs.fee(NOTIONAL) == Decimal("100.00000")
    assert costs.fee(NOTIONAL) == Decimal(NOTIONAL) * Decimal("0.001")


def test_slippage_is_charged_at_its_own_rate() -> None:
    costs = execution_costs_from_config()

    assert costs.slippage_bps == Decimal("5.0")
    assert costs.slippage(NOTIONAL) == Decimal("50.00000")


@pytest.mark.parametrize(
    ("side", "expected"),
    [("buy", "100050.00000"), ("sell", "99950.00000")],
)
def test_slippage_is_always_adverse(side: str, expected: str) -> None:
    costs = execution_costs_from_config()

    # A buy fills higher and a sell fills lower. No configuration makes a paper
    # fill better than the reference price.
    assert costs.fill_price("100000", side=side) == Decimal(expected)


def test_a_round_trip_costs_both_fills() -> None:
    costs = execution_costs_from_config()

    # A 2R target is not 2R after costs, so the round trip is one number.
    assert costs.round_trip_cost(NOTIONAL) == Decimal("300.00000")
    assert costs.round_trip_cost(NOTIONAL) == (
        costs.fee(NOTIONAL) + costs.slippage(NOTIONAL)
    ) * 2


def test_funding_accrues_per_day_on_notional() -> None:
    costs = ExecutionCosts(
        policy_version=EXECUTION_COST_POLICY_VERSION,
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        funding_cost_bps_per_day=Decimal("1"),
    )

    assert costs.funding(NOTIONAL, days=1) == Decimal("10.0000")
    assert costs.funding(NOTIONAL, days="30") == Decimal("300.0000")
    assert costs.funding(NOTIONAL, days=0) == Decimal("0.0000")


def test_the_shipped_funding_rate_is_zero_and_says_so() -> None:
    costs = execution_costs_from_config()

    # Phase 1 ships with no funding assumption; it is configured to zero
    # rather than absent, so a later calibration is a config change.
    assert costs.funding_cost_bps_per_day == Decimal("0.0")
    assert costs.funding(NOTIONAL, days=30) == Decimal("0.00000")


def test_zero_notional_costs_nothing() -> None:
    costs = execution_costs_from_config()

    assert costs.fee("0") == Decimal("0.00000")
    assert costs.slippage("0") == Decimal("0.00000")


@pytest.mark.parametrize(
    ("call", "match"),
    [
        (lambda c: c.fee("-1"), "notional must be non-negative"),
        (lambda c: c.slippage("-1"), "notional must be non-negative"),
        (lambda c: c.funding("100", days="-1"), "days must be non-negative"),
        (lambda c: c.fill_price("0", side="buy"), "price must be positive"),
        (lambda c: c.fill_price("100", side="hold"), "side must be one of"),
        (lambda c: c.fee("abc"), "notional must be numeric"),
    ],
)
def test_cost_inputs_fail_fast(call, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        call(execution_costs_from_config())


# --- immutable balance transitions ---------------------------------------


def test_charging_a_fee_returns_a_new_account() -> None:
    opened = account(starting_nav="100000")

    charged = opened.charge_fee(NOTIONAL)

    # A rejected or replayed step can never leave a half-applied balance.
    assert opened.cash == Decimal("100000")
    assert opened.fees_paid == Decimal("0")
    assert charged.cash == Decimal("99900.00000")
    assert charged.fees_paid == Decimal("100.00000")
    assert charged.reason_codes == ("PAPER_ACCOUNT_FEE_CHARGED",)


def test_charges_and_settlements_accumulate() -> None:
    opened = account(starting_nav="100000")

    final = (
        opened.charge_fee(NOTIONAL)
        .charge_funding(NOTIONAL, days=10, direction="long")
        .settle_realized_pnl("5000")
        .charge_fee(NOTIONAL)
    )

    assert final.fees_paid == Decimal("200.00000")
    assert final.realized_pnl == Decimal("5000")
    assert final.total_costs_paid == final.fees_paid + final.funding_paid
    assert final.cash == Decimal("100000") - final.total_costs_paid + Decimal("5000")


def test_cash_exhaustion_survives_the_step_that_caused_it() -> None:
    """A floored balance is not a balance, and the record must keep saying so.

    Flooring at zero keeps the row insertable under the
    ``paper_accounts_current_cash_non_negative`` CHECK, but it throws the
    deficit away. When the code cleared on the next charge, a consumer reading
    only the final account saw a clean zero with nothing to distinguish it
    from an account that simply spent everything exactly.
    """

    wiped = account(starting_nav="100").settle_realized_pnl("-1000")

    assert wiped.cash == Decimal("0")
    assert wiped.cash_exhausted is True
    assert "PAPER_ACCOUNT_CASH_EXHAUSTED" in wiped.reason_codes
    # The deficit really is gone from cash; realized P&L still records it.
    assert wiped.realized_pnl == Decimal("-1000")

    for later in (
        wiped.charge_fee(NOTIONAL),
        wiped.settle_realized_pnl("50"),
        wiped.apply_funding_cost("-10"),
        wiped.archive(),
    ):
        assert later.cash_exhausted is True
        assert "PAPER_ACCOUNT_CASH_EXHAUSTED" in later.reason_codes

    # A healthy account never claims exhaustion.
    healthy = account(starting_nav="100000").charge_fee(NOTIONAL)
    assert healthy.cash_exhausted is False
    assert healthy.reason_codes == ("PAPER_ACCOUNT_FEE_CHARGED",)


def test_funding_is_signed_by_the_side_that_pays_it() -> None:
    """A long pays the carry and a short receives it, the BTC-165 convention.

    ``ExecutionCosts.funding`` returns an unsigned magnitude, so an account
    that defaulted the side would debit a short the carry it actually
    collects, and the two funding paths in the epic would disagree about the
    same position.
    """

    costs = ExecutionCosts(
        policy_version="EXECUTION_COST_V1",
        fee_bps=Decimal("0"),
        slippage_bps=Decimal("0"),
        funding_cost_bps_per_day=Decimal("10"),
    )
    opened = account(starting_nav="100000", costs=costs)
    magnitude = costs.funding(NOTIONAL, days=10)

    paid = opened.charge_funding(NOTIONAL, days=10, direction="long")
    received = opened.charge_funding(NOTIONAL, days=10, direction="short")

    assert magnitude > 0
    assert paid.funding_paid == magnitude
    assert paid.cash == opened.cash - magnitude
    assert received.funding_paid == -magnitude
    assert received.cash == opened.cash + magnitude
    # The signed figure is the one BTC-165 would produce for the same event.
    assert received.funding_paid == opened.apply_funding_cost(-magnitude).funding_paid


def test_funding_refuses_an_unknown_side() -> None:
    with pytest.raises(ValueError, match="direction must be one of"):
        account().charge_funding(NOTIONAL, days=1, direction="flat")


def test_a_realized_loss_reduces_cash() -> None:
    settled = account(starting_nav="100000").settle_realized_pnl("-2500")

    assert settled.cash == Decimal("97500")
    assert settled.realized_pnl == Decimal("-2500")
    assert settled.reason_codes == ("PAPER_ACCOUNT_PNL_SETTLED",)


def test_cash_is_floored_at_zero_and_reported() -> None:
    exhausted = account(starting_nav="1000").settle_realized_pnl("-5000")

    # A negative paper balance is not a real state; the DB CHECK forbids it.
    assert exhausted.cash == Decimal("0")
    assert exhausted.realized_pnl == Decimal("-5000")
    assert "PAPER_ACCOUNT_CASH_EXHAUSTED" in exhausted.reason_codes


def test_archiving_preserves_balances() -> None:
    opened = account(starting_nav="100000").charge_fee(NOTIONAL)

    archived = opened.archive()

    assert archived.status == ACCOUNT_ARCHIVED
    assert archived.is_active is False
    assert archived.cash == opened.cash
    assert archived.reason_codes == ("PAPER_ACCOUNT_ARCHIVED",)


# --- persistence ----------------------------------------------------------


def test_record_is_persistable_and_reconstructable() -> None:
    record = account(
        starting_nav="100000",
        reserved_cash="10000",
        config_metadata={"config_version": "strategy_config_v2"},
    ).as_record()

    assert record == {
        "feature_id": "PAPER_ACCOUNT",
        "policy_version": "PAPER_ACCOUNT_V1",
        "account_name": "paper-1",
        "base_currency": "USD",
        "starting_nav": "100000",
        "cash": "100000",
        "reserved_cash": "10000",
        "available_cash": "90000",
        "realized_pnl": "0",
        "fees_paid": "0",
        "funding_paid": "0",
        "costs": {
            "policy_version": "EXECUTION_COST_V1",
            "fee_bps": "10.0",
            "slippage_bps": "5.0",
            "funding_cost_bps_per_day": "0.0",
        },
        "status": "active",
        "created_at": "2024-08-01T00:00:00+00:00",
        "config_metadata": {"config_version": "strategy_config_v2"},
        "reason_codes": ["PAPER_ACCOUNT_OPENED"],
    }
    # The cost assumptions travel with the account, so a replayed run cannot
    # silently pick up different fees.
    assert Decimal(record["available_cash"]) == Decimal(record["cash"]) - Decimal(
        record["reserved_cash"]
    )


def test_db_record_matches_the_paper_accounts_columns() -> None:
    record = account(starting_nav="100000").charge_fee(NOTIONAL).as_db_record()
    columns = {column.name for column in paper_accounts.columns}

    # The table stores cash, not NAV, and only these columns exist.
    assert set(record) <= columns
    assert record["starting_cash"] == Decimal("100000")
    assert record["current_cash"] == Decimal("99900.00000")
    assert record["status"] in PAPER_ACCOUNT_STATUSES


def test_db_status_values_satisfy_the_schema_check() -> None:
    opened = account()

    assert PAPER_ACCOUNT_STATUSES == ("active", "archived")
    assert opened.as_db_record()["status"] == "active"
    assert opened.archive().as_db_record()["status"] == "archived"


def test_record_rejects_an_invalid_status() -> None:
    with pytest.raises(ValueError, match="status must be one of"):
        replace(account(), status="paused").as_record()


def test_record_rejects_a_negative_balance() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        replace(account(), cash=Decimal("-1")).as_record()


def test_record_rejects_a_reserve_above_the_account() -> None:
    with pytest.raises(ValueError, match="reserved_cash must not exceed"):
        replace(account(starting_nav="1000"), reserved_cash=Decimal("5000")).as_record()


def test_reason_codes_are_drawn_from_the_declared_set() -> None:
    accounts = [
        account(),
        account().charge_fee(NOTIONAL),
        account().charge_funding(NOTIONAL, days=1, direction="long"),
        account().settle_realized_pnl("100"),
        account(starting_nav="100").settle_realized_pnl("-1000"),
        account().archive(),
    ]

    for item in accounts:
        for code in item.reason_codes:
            assert code in PAPER_ACCOUNT_REASON_CODES


# --- malformed input ------------------------------------------------------


@pytest.mark.parametrize(
    ("kwargs", "match"),
    [
        ({"account_name": ""}, "account_name must not be empty"),
        ({"account_name": "   "}, "account_name must not be empty"),
        ({"base_currency": ""}, "base_currency must not be empty"),
        ({"starting_nav": "0"}, "starting_nav must be positive"),
        ({"starting_nav": "-1"}, "starting_nav must be positive"),
        ({"starting_nav": "abc"}, "starting_nav must be numeric"),
        ({"reserved_cash": "-1"}, "reserved_cash must be non-negative"),
    ],
)
def test_opening_an_account_validates_its_identity(kwargs, match: str) -> None:
    with pytest.raises(ValueError, match=match):
        account(**kwargs)


def test_a_naive_created_at_is_rejected() -> None:
    with pytest.raises(ValueError):
        open_paper_account(account_name="paper-1", created_at=datetime(2024, 8, 1))


def test_a_non_config_is_rejected() -> None:
    with pytest.raises(TypeError, match="StrategyConfig"):
        account(config={"backtest": {}})
    with pytest.raises(TypeError, match="StrategyConfig"):
        execution_costs_from_config({"fee_bps": 10})


def test_opening_is_deterministic() -> None:
    assert account().as_record() == account().as_record()
