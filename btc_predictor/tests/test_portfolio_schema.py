from btc_predictor.db import (
    COMPLETED_TRADES_PRIMARY_KEY,
    MANUAL_DECISIONS,
    MANUAL_TRADE_JOURNAL_PRIMARY_KEY,
    PAPER_ACCOUNTS_PRIMARY_KEY,
    PAPER_ACTIONS,
    PAPER_ORDERS_PRIMARY_KEY,
    POSITION_EVENTS_PRIMARY_KEY,
    POSITIONS_PRIMARY_KEY,
    STOPS_PRIMARY_KEY,
    TRANCHES_PRIMARY_KEY,
    completed_trades,
    manual_trade_journal,
    paper_accounts,
    paper_orders,
    position_events,
    positions,
    stops,
    tranches,
)


def test_paper_portfolio_schema_defines_required_entities() -> None:
    assert PAPER_ACCOUNTS_PRIMARY_KEY == ("account_id",)
    assert POSITIONS_PRIMARY_KEY == ("position_id",)
    assert TRANCHES_PRIMARY_KEY == ("tranche_id",)
    assert PAPER_ORDERS_PRIMARY_KEY == ("order_id",)
    assert STOPS_PRIMARY_KEY == ("stop_id",)
    assert POSITION_EVENTS_PRIMARY_KEY == ("event_id",)
    assert COMPLETED_TRADES_PRIMARY_KEY == ("completed_trade_id",)
    assert MANUAL_TRADE_JOURNAL_PRIMARY_KEY == ("manual_trade_id",)


def test_paper_portfolio_events_support_required_actions() -> None:
    assert PAPER_ACTIONS == ("ENTER", "HOLD", "ADD", "STOP_MOVE", "TRIM", "EXIT", "MISSED")


def test_manual_trade_journal_supports_required_decisions() -> None:
    assert MANUAL_DECISIONS == ("FOLLOWED", "OVERRIDDEN", "SKIPPED", "MANUAL_ONLY")


def test_paper_portfolio_tables_capture_lifecycle_relationships() -> None:
    assert "account_id" in paper_accounts.c
    assert "account_id" in positions.c
    assert "opening_recommendation_id" in positions.c
    assert "position_id" in tranches.c
    assert "recommendation_id" in tranches.c
    assert "position_id" in paper_orders.c
    assert "recommendation_id" in paper_orders.c
    assert "position_id" in stops.c
    assert "is_active" in stops.c
    assert "action" in position_events.c
    assert "notes" in position_events.c
    assert "realized_r" in completed_trades.c
    assert "max_risk_fraction_nav" in completed_trades.c


def test_manual_trade_journal_can_compare_recommendation_to_execution() -> None:
    for column_name in (
        "recommendation_id",
        "actual_entry_time",
        "actual_entry_price",
        "actual_size",
        "actual_size_unit",
        "actual_stop",
        "actual_exit_time",
        "actual_exit_price",
        "manual_decision",
        "override_reason",
        "notes",
    ):
        assert column_name in manual_trade_journal.c

    foreign_keys = list(manual_trade_journal.foreign_keys)

    assert any(
        foreign_key.target_fullname == "signals.recommendations.recommendation_id"
        for foreign_key in foreign_keys
    )


def test_paper_portfolio_timestamps_are_timezone_aware() -> None:
    for table, column_name in (
        (paper_accounts, "created_at"),
        (positions, "opened_at"),
        (tranches, "opened_at"),
        (paper_orders, "created_at"),
        (stops, "created_at"),
        (position_events, "event_time"),
        (completed_trades, "closed_at"),
        (manual_trade_journal, "journaled_at"),
        (manual_trade_journal, "actual_entry_time"),
        (manual_trade_journal, "actual_exit_time"),
    ):
        assert table.c[column_name].type.timezone is True
