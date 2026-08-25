"""Paper portfolio database table definitions."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
)

from btc_predictor.db.base import NAMING_CONVENTION


PORTFOLIO_SCHEMA = "portfolio"

PAPER_ACTIONS = ("ENTER", "HOLD", "ADD", "STOP_MOVE", "TRIM", "EXIT", "MISSED")

PAPER_ACCOUNTS_PRIMARY_KEY = ("account_id",)
POSITIONS_PRIMARY_KEY = ("position_id",)
TRANCHES_PRIMARY_KEY = ("tranche_id",)
PAPER_ORDERS_PRIMARY_KEY = ("order_id",)
STOPS_PRIMARY_KEY = ("stop_id",)
POSITION_EVENTS_PRIMARY_KEY = ("event_id",)
COMPLETED_TRADES_PRIMARY_KEY = ("completed_trade_id",)

portfolio_metadata = MetaData(schema=PORTFOLIO_SCHEMA, naming_convention=NAMING_CONVENTION)

paper_accounts = Table(
    "paper_accounts",
    portfolio_metadata,
    Column("account_id", BigInteger, Identity(always=True), nullable=False),
    Column("account_name", String(length=128), nullable=False),
    Column("base_currency", String(length=16), nullable=False),
    Column("starting_cash", Numeric(precision=38, scale=18), nullable=False),
    Column("current_cash", Numeric(precision=38, scale=18), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("status", String(length=16), nullable=False),
    PrimaryKeyConstraint(*PAPER_ACCOUNTS_PRIMARY_KEY, name="pk_portfolio_paper_accounts"),
    UniqueConstraint("account_name", name="uq_portfolio_paper_accounts_account_name"),
    CheckConstraint("starting_cash >= 0", name="paper_accounts_starting_cash_non_negative"),
    CheckConstraint("current_cash >= 0", name="paper_accounts_current_cash_non_negative"),
    CheckConstraint("status in ('active', 'archived')", name="paper_accounts_status_valid"),
    comment="Paper trading account state for model-only execution.",
)
Index("ix_portfolio_paper_accounts_status", paper_accounts.c.status)

positions = Table(
    "positions",
    portfolio_metadata,
    Column("position_id", BigInteger, Identity(always=True), nullable=False),
    Column("account_id", BigInteger, nullable=False),
    Column("opening_recommendation_id", BigInteger, nullable=True),
    Column("symbol", String(length=32), nullable=False),
    Column("direction", String(length=16), nullable=False),
    Column("status", String(length=16), nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("closed_at", DateTime(timezone=True), nullable=True),
    Column("average_entry_price", Numeric(precision=38, scale=18), nullable=True),
    Column("quantity", Numeric(precision=38, scale=18), nullable=False),
    Column("realized_pnl", Numeric(precision=38, scale=18), nullable=False),
    ForeignKeyConstraint(
        ["account_id"],
        ["portfolio.paper_accounts.account_id"],
        name="fk_portfolio_positions_account_id_paper_accounts",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["opening_recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_pf_positions_opening_recommendation",
        ondelete="SET NULL",
    ),
    PrimaryKeyConstraint(*POSITIONS_PRIMARY_KEY, name="pk_portfolio_positions"),
    CheckConstraint("direction in ('long', 'short')", name="positions_direction_valid"),
    CheckConstraint("status in ('open', 'closed', 'missed')", name="positions_status_valid"),
    CheckConstraint("quantity >= 0", name="positions_quantity_non_negative"),
    comment="Paper portfolio position lifecycle state.",
)
Index("ix_portfolio_positions_account_status", positions.c.account_id, positions.c.status)

tranches = Table(
    "tranches",
    portfolio_metadata,
    Column("tranche_id", BigInteger, Identity(always=True), nullable=False),
    Column("position_id", BigInteger, nullable=False),
    Column("recommendation_id", BigInteger, nullable=True),
    Column("tranche_number", BigInteger, nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("closed_at", DateTime(timezone=True), nullable=True),
    Column("entry_price", Numeric(precision=38, scale=18), nullable=False),
    Column("quantity", Numeric(precision=38, scale=18), nullable=False),
    Column("status", String(length=16), nullable=False),
    ForeignKeyConstraint(
        ["position_id"],
        ["portfolio.positions.position_id"],
        name="fk_portfolio_tranches_position_id_positions",
        ondelete="CASCADE",
    ),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_portfolio_tranches_recommendation_id_recommendations",
        ondelete="SET NULL",
    ),
    PrimaryKeyConstraint(*TRANCHES_PRIMARY_KEY, name="pk_portfolio_tranches"),
    UniqueConstraint("position_id", "tranche_number", name="uq_portfolio_tranches_position_number"),
    CheckConstraint("tranche_number >= 1", name="tranches_number_positive"),
    CheckConstraint("entry_price > 0", name="tranches_entry_price_positive"),
    CheckConstraint("quantity > 0", name="tranches_quantity_positive"),
    CheckConstraint("status in ('open', 'closed')", name="tranches_status_valid"),
    comment="Individual position tranches for anti-martingale adds and trims.",
)

paper_orders = Table(
    "paper_orders",
    portfolio_metadata,
    Column("order_id", BigInteger, Identity(always=True), nullable=False),
    Column("account_id", BigInteger, nullable=False),
    Column("position_id", BigInteger, nullable=True),
    Column("recommendation_id", BigInteger, nullable=True),
    Column("action", String(length=16), nullable=False),
    Column("side", String(length=8), nullable=False),
    Column("order_type", String(length=16), nullable=False),
    Column("status", String(length=16), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("submitted_at", DateTime(timezone=True), nullable=True),
    Column("filled_at", DateTime(timezone=True), nullable=True),
    Column("requested_quantity", Numeric(precision=38, scale=18), nullable=True),
    Column("filled_quantity", Numeric(precision=38, scale=18), nullable=True),
    Column("limit_price", Numeric(precision=38, scale=18), nullable=True),
    Column("stop_price", Numeric(precision=38, scale=18), nullable=True),
    Column("average_fill_price", Numeric(precision=38, scale=18), nullable=True),
    ForeignKeyConstraint(
        ["account_id"],
        ["portfolio.paper_accounts.account_id"],
        name="fk_portfolio_orders_account_id_paper_accounts",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["position_id"],
        ["portfolio.positions.position_id"],
        name="fk_portfolio_orders_position_id_positions",
        ondelete="SET NULL",
    ),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_portfolio_orders_recommendation_id_recommendations",
        ondelete="SET NULL",
    ),
    PrimaryKeyConstraint(*PAPER_ORDERS_PRIMARY_KEY, name="pk_portfolio_paper_orders"),
    CheckConstraint(
        "action in ('ENTER', 'ADD', 'TRIM', 'EXIT', 'MISSED')",
        name="paper_orders_action_valid",
    ),
    CheckConstraint("side in ('buy', 'sell')", name="paper_orders_side_valid"),
    CheckConstraint("order_type in ('market', 'limit', 'stop')", name="paper_orders_order_type_valid"),
    CheckConstraint(
        "status in ('created', 'submitted', 'filled', 'cancelled', 'missed')",
        name="paper_orders_status_valid",
    ),
    CheckConstraint(
        "requested_quantity is null or requested_quantity > 0",
        name="paper_orders_requested_quantity_positive",
    ),
    CheckConstraint(
        "filled_quantity is null or filled_quantity >= 0",
        name="paper_orders_filled_quantity_non_negative",
    ),
    comment="Paper execution orders derived from recommendations and lifecycle actions.",
)
Index("ix_portfolio_paper_orders_account_created_at", paper_orders.c.account_id, paper_orders.c.created_at)
Index("ix_portfolio_paper_orders_status", paper_orders.c.status)

stops = Table(
    "stops",
    portfolio_metadata,
    Column("stop_id", BigInteger, Identity(always=True), nullable=False),
    Column("position_id", BigInteger, nullable=False),
    Column("recommendation_id", BigInteger, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("stop_price", Numeric(precision=38, scale=18), nullable=False),
    Column("reason", String(length=64), nullable=False),
    Column("is_active", Boolean, nullable=False),
    ForeignKeyConstraint(
        ["position_id"],
        ["portfolio.positions.position_id"],
        name="fk_portfolio_stops_position_id_positions",
        ondelete="CASCADE",
    ),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_portfolio_stops_recommendation_id_recommendations",
        ondelete="SET NULL",
    ),
    PrimaryKeyConstraint(*STOPS_PRIMARY_KEY, name="pk_portfolio_stops"),
    CheckConstraint("stop_price > 0", name="stops_stop_price_positive"),
    comment="Structural stop history for paper positions, including stop moves.",
)
Index("ix_portfolio_stops_position_created_at", stops.c.position_id, stops.c.created_at)

position_events = Table(
    "position_events",
    portfolio_metadata,
    Column("event_id", BigInteger, Identity(always=True), nullable=False),
    Column("position_id", BigInteger, nullable=True),
    Column("account_id", BigInteger, nullable=False),
    Column("recommendation_id", BigInteger, nullable=True),
    Column("event_time", DateTime(timezone=True), nullable=False),
    Column("action", String(length=16), nullable=False),
    Column("quantity", Numeric(precision=38, scale=18), nullable=True),
    Column("price", Numeric(precision=38, scale=18), nullable=True),
    Column("risk_fraction_nav", Numeric(precision=12, scale=8), nullable=True),
    Column("notes", Text, nullable=True),
    ForeignKeyConstraint(
        ["account_id"],
        ["portfolio.paper_accounts.account_id"],
        name="fk_portfolio_position_events_account_id_paper_accounts",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["position_id"],
        ["portfolio.positions.position_id"],
        name="fk_portfolio_position_events_position_id_positions",
        ondelete="SET NULL",
    ),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_portfolio_position_events_recommendation_id_recommendations",
        ondelete="SET NULL",
    ),
    PrimaryKeyConstraint(*POSITION_EVENTS_PRIMARY_KEY, name="pk_portfolio_position_events"),
    CheckConstraint(
        "action in ('ENTER', 'HOLD', 'ADD', 'STOP_MOVE', 'TRIM', 'EXIT', 'MISSED')",
        name="position_events_action_valid",
    ),
    CheckConstraint("quantity is null or quantity >= 0", name="position_events_quantity_non_negative"),
    CheckConstraint("price is null or price > 0", name="position_events_price_positive"),
    CheckConstraint(
        "risk_fraction_nav is null or risk_fraction_nav >= 0",
        name="position_events_risk_fraction_nav_non_negative",
    ),
    comment="Chronological paper position events supporting full lifecycle replay.",
)
Index("ix_portfolio_position_events_account_time", position_events.c.account_id, position_events.c.event_time)
Index("ix_portfolio_position_events_position_time", position_events.c.position_id, position_events.c.event_time)

completed_trades = Table(
    "completed_trades",
    portfolio_metadata,
    Column("completed_trade_id", BigInteger, Identity(always=True), nullable=False),
    Column("position_id", BigInteger, nullable=False),
    Column("account_id", BigInteger, nullable=False),
    Column("symbol", String(length=32), nullable=False),
    Column("direction", String(length=16), nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("closed_at", DateTime(timezone=True), nullable=False),
    Column("entry_notional", Numeric(precision=38, scale=18), nullable=False),
    Column("exit_notional", Numeric(precision=38, scale=18), nullable=False),
    Column("realized_pnl", Numeric(precision=38, scale=18), nullable=False),
    Column("realized_r", Numeric(precision=18, scale=8), nullable=True),
    Column("max_risk_fraction_nav", Numeric(precision=12, scale=8), nullable=True),
    ForeignKeyConstraint(
        ["position_id"],
        ["portfolio.positions.position_id"],
        name="fk_portfolio_completed_trades_position_id_positions",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["account_id"],
        ["portfolio.paper_accounts.account_id"],
        name="fk_portfolio_completed_trades_account_id_paper_accounts",
        ondelete="RESTRICT",
    ),
    PrimaryKeyConstraint(*COMPLETED_TRADES_PRIMARY_KEY, name="pk_portfolio_completed_trades"),
    UniqueConstraint("position_id", name="uq_portfolio_completed_trades_position_id"),
    CheckConstraint("direction in ('long', 'short')", name="completed_trades_direction_valid"),
    CheckConstraint("closed_at >= opened_at", name="completed_trades_time_order"),
    CheckConstraint("entry_notional >= 0", name="completed_trades_entry_notional_non_negative"),
    CheckConstraint("exit_notional >= 0", name="completed_trades_exit_notional_non_negative"),
    CheckConstraint(
        "max_risk_fraction_nav is null or max_risk_fraction_nav >= 0",
        name="completed_trades_max_risk_fraction_nav_non_negative",
    ),
    comment="Finalized paper trade outcomes for research and reporting.",
)
Index("ix_portfolio_completed_trades_account_closed_at", completed_trades.c.account_id, completed_trades.c.closed_at)
