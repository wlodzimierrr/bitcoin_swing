"""create paper portfolio schemas

Revision ID: 0016_create_paper_portfolio_schemas
Revises: 0015_create_predictor_recommendation_schemas
Create Date: 2026-08-25 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0016_create_paper_portfolio_schemas"
down_revision = "0015_create_predictor_recommendation_schemas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    _create_paper_accounts()
    _create_positions()
    _create_tranches()
    _create_paper_orders()
    _create_stops()
    _create_position_events()
    _create_completed_trades()


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.drop_table("completed_trades", schema="portfolio")
    op.drop_table("position_events", schema="portfolio")
    op.drop_table("stops", schema="portfolio")
    op.drop_table("paper_orders", schema="portfolio")
    op.drop_table("tranches", schema="portfolio")
    op.drop_table("positions", schema="portfolio")
    op.drop_table("paper_accounts", schema="portfolio")


def _create_paper_accounts() -> None:
    op.create_table(
        "paper_accounts",
        sa.Column("account_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("account_name", sa.String(length=128), nullable=False),
        sa.Column("base_currency", sa.String(length=16), nullable=False),
        sa.Column("starting_cash", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("current_cash", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.CheckConstraint("starting_cash >= 0", name="ck_paper_accounts_starting_cash_non_negative"),
        sa.CheckConstraint("current_cash >= 0", name="ck_paper_accounts_current_cash_non_negative"),
        sa.CheckConstraint("status in ('active', 'archived')", name="ck_paper_accounts_status_valid"),
        sa.PrimaryKeyConstraint("account_id", name="pk_portfolio_paper_accounts"),
        sa.UniqueConstraint("account_name", name="uq_portfolio_paper_accounts_account_name"),
        schema="portfolio",
        comment="Paper trading account state for model-only execution.",
    )
    op.create_index("ix_portfolio_paper_accounts_status", "paper_accounts", ["status"], schema="portfolio")


def _create_positions() -> None:
    op.create_table(
        "positions",
        sa.Column("position_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("opening_recommendation_id", sa.BigInteger(), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("average_entry_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.CheckConstraint("direction in ('long', 'short')", name="ck_positions_direction_valid"),
        sa.CheckConstraint("status in ('open', 'closed', 'missed')", name="ck_positions_status_valid"),
        sa.CheckConstraint("quantity >= 0", name="ck_positions_quantity_non_negative"),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["portfolio.paper_accounts.account_id"],
            name="fk_portfolio_positions_account_id_paper_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["opening_recommendation_id"],
            ["signals.recommendations.recommendation_id"],
            name="fk_pf_positions_opening_recommendation",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("position_id", name="pk_portfolio_positions"),
        schema="portfolio",
        comment="Paper portfolio position lifecycle state.",
    )
    op.create_index(
        "ix_portfolio_positions_account_status",
        "positions",
        ["account_id", "status"],
        schema="portfolio",
    )


def _create_tranches() -> None:
    op.create_table(
        "tranches",
        sa.Column("tranche_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("position_id", sa.BigInteger(), nullable=False),
        sa.Column("recommendation_id", sa.BigInteger(), nullable=True),
        sa.Column("tranche_number", sa.BigInteger(), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("entry_price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.CheckConstraint("tranche_number >= 1", name="ck_tranches_number_positive"),
        sa.CheckConstraint("entry_price > 0", name="ck_tranches_entry_price_positive"),
        sa.CheckConstraint("quantity > 0", name="ck_tranches_quantity_positive"),
        sa.CheckConstraint("status in ('open', 'closed')", name="ck_tranches_status_valid"),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["portfolio.positions.position_id"],
            name="fk_portfolio_tranches_position_id_positions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["signals.recommendations.recommendation_id"],
            name="fk_portfolio_tranches_recommendation_id_recommendations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("tranche_id", name="pk_portfolio_tranches"),
        sa.UniqueConstraint("position_id", "tranche_number", name="uq_portfolio_tranches_position_number"),
        schema="portfolio",
        comment="Individual position tranches for anti-martingale adds and trims.",
    )


def _create_paper_orders() -> None:
    op.create_table(
        "paper_orders",
        sa.Column("order_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("position_id", sa.BigInteger(), nullable=True),
        sa.Column("recommendation_id", sa.BigInteger(), nullable=True),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("side", sa.String(length=8), nullable=False),
        sa.Column("order_type", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("filled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("requested_quantity", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("filled_quantity", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("limit_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("stop_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("average_fill_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.CheckConstraint(
            "action in ('ENTER', 'ADD', 'TRIM', 'EXIT', 'MISSED')",
            name="ck_paper_orders_action_valid",
        ),
        sa.CheckConstraint("side in ('buy', 'sell')", name="ck_paper_orders_side_valid"),
        sa.CheckConstraint(
            "order_type in ('market', 'limit', 'stop')",
            name="ck_paper_orders_order_type_valid",
        ),
        sa.CheckConstraint(
            "status in ('created', 'submitted', 'filled', 'cancelled', 'missed')",
            name="ck_paper_orders_status_valid",
        ),
        sa.CheckConstraint(
            "requested_quantity is null or requested_quantity > 0",
            name="ck_paper_orders_requested_quantity_positive",
        ),
        sa.CheckConstraint(
            "filled_quantity is null or filled_quantity >= 0",
            name="ck_paper_orders_filled_quantity_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["portfolio.paper_accounts.account_id"],
            name="fk_portfolio_orders_account_id_paper_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["portfolio.positions.position_id"],
            name="fk_portfolio_orders_position_id_positions",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["signals.recommendations.recommendation_id"],
            name="fk_portfolio_orders_recommendation_id_recommendations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("order_id", name="pk_portfolio_paper_orders"),
        schema="portfolio",
        comment="Paper execution orders derived from recommendations and lifecycle actions.",
    )
    op.create_index(
        "ix_portfolio_paper_orders_account_created_at",
        "paper_orders",
        ["account_id", "created_at"],
        schema="portfolio",
    )
    op.create_index("ix_portfolio_paper_orders_status", "paper_orders", ["status"], schema="portfolio")


def _create_stops() -> None:
    op.create_table(
        "stops",
        sa.Column("stop_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("position_id", sa.BigInteger(), nullable=False),
        sa.Column("recommendation_id", sa.BigInteger(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stop_price", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("reason", sa.String(length=64), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("stop_price > 0", name="ck_stops_stop_price_positive"),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["portfolio.positions.position_id"],
            name="fk_portfolio_stops_position_id_positions",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["signals.recommendations.recommendation_id"],
            name="fk_portfolio_stops_recommendation_id_recommendations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("stop_id", name="pk_portfolio_stops"),
        schema="portfolio",
        comment="Structural stop history for paper positions, including stop moves.",
    )
    op.create_index(
        "ix_portfolio_stops_position_created_at",
        "stops",
        ["position_id", "created_at"],
        schema="portfolio",
    )


def _create_position_events() -> None:
    op.create_table(
        "position_events",
        sa.Column("event_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("position_id", sa.BigInteger(), nullable=True),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("recommendation_id", sa.BigInteger(), nullable=True),
        sa.Column("event_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column("action", sa.String(length=16), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("risk_fraction_nav", sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "action in ('ENTER', 'HOLD', 'ADD', 'STOP_MOVE', 'TRIM', 'EXIT', 'MISSED')",
            name="ck_position_events_action_valid",
        ),
        sa.CheckConstraint(
            "quantity is null or quantity >= 0",
            name="ck_position_events_quantity_non_negative",
        ),
        sa.CheckConstraint("price is null or price > 0", name="ck_position_events_price_positive"),
        sa.CheckConstraint(
            "risk_fraction_nav is null or risk_fraction_nav >= 0",
            name="ck_position_events_risk_fraction_nav_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["portfolio.paper_accounts.account_id"],
            name="fk_portfolio_position_events_account_id_paper_accounts",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["portfolio.positions.position_id"],
            name="fk_portfolio_position_events_position_id_positions",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["signals.recommendations.recommendation_id"],
            name="fk_portfolio_position_events_recommendation_id_recommendations",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("event_id", name="pk_portfolio_position_events"),
        schema="portfolio",
        comment="Chronological paper position events supporting full lifecycle replay.",
    )
    op.create_index(
        "ix_portfolio_position_events_account_time",
        "position_events",
        ["account_id", "event_time"],
        schema="portfolio",
    )
    op.create_index(
        "ix_portfolio_position_events_position_time",
        "position_events",
        ["position_id", "event_time"],
        schema="portfolio",
    )


def _create_completed_trades() -> None:
    op.create_table(
        "completed_trades",
        sa.Column("completed_trade_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("position_id", sa.BigInteger(), nullable=False),
        sa.Column("account_id", sa.BigInteger(), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("entry_notional", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("exit_notional", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("realized_pnl", sa.Numeric(precision=38, scale=18), nullable=False),
        sa.Column("realized_r", sa.Numeric(precision=18, scale=8), nullable=True),
        sa.Column("max_risk_fraction_nav", sa.Numeric(precision=12, scale=8), nullable=True),
        sa.CheckConstraint("direction in ('long', 'short')", name="ck_completed_trades_direction_valid"),
        sa.CheckConstraint("closed_at >= opened_at", name="ck_completed_trades_time_order"),
        sa.CheckConstraint(
            "entry_notional >= 0",
            name="ck_completed_trades_entry_notional_non_negative",
        ),
        sa.CheckConstraint(
            "exit_notional >= 0",
            name="ck_completed_trades_exit_notional_non_negative",
        ),
        sa.CheckConstraint(
            "max_risk_fraction_nav is null or max_risk_fraction_nav >= 0",
            name="ck_completed_trades_max_risk_fraction_nav_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["position_id"],
            ["portfolio.positions.position_id"],
            name="fk_portfolio_completed_trades_position_id_positions",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["account_id"],
            ["portfolio.paper_accounts.account_id"],
            name="fk_portfolio_completed_trades_account_id_paper_accounts",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("completed_trade_id", name="pk_portfolio_completed_trades"),
        sa.UniqueConstraint("position_id", name="uq_portfolio_completed_trades_position_id"),
        schema="portfolio",
        comment="Finalized paper trade outcomes for research and reporting.",
    )
    op.create_index(
        "ix_portfolio_completed_trades_account_closed_at",
        "completed_trades",
        ["account_id", "closed_at"],
        schema="portfolio",
    )
