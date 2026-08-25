from btc_predictor.db import (
    COMPLETED_TRADES_PRIMARY_KEY,
    PAPER_ACCOUNTS_PRIMARY_KEY,
    PAPER_ACTIONS,
    PAPER_ORDERS_PRIMARY_KEY,
    POSITION_EVENTS_PRIMARY_KEY,
    POSITIONS_PRIMARY_KEY,
    STOPS_PRIMARY_KEY,
    TRANCHES_PRIMARY_KEY,
    completed_trades,
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


def test_paper_portfolio_events_support_required_actions() -> None:
    assert PAPER_ACTIONS == ("ENTER", "HOLD", "ADD", "STOP_MOVE", "TRIM", "EXIT", "MISSED")


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


def test_paper_portfolio_timestamps_are_timezone_aware() -> None:
    for table, column_name in (
        (paper_accounts, "created_at"),
        (positions, "opened_at"),
        (tranches, "opened_at"),
        (paper_orders, "created_at"),
        (stops, "created_at"),
        (position_events, "event_time"),
        (completed_trades, "closed_at"),
    ):
        assert table.c[column_name].type.timezone is True
