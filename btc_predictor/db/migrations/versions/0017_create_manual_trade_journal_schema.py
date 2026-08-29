"""create manual trade journal schema

Revision ID: 0017_manual_trade_journal
Revises: 0016_paper_portfolio
Create Date: 2026-08-25 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0017_manual_trade_journal"
down_revision = "0016_paper_portfolio"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.create_table(
        "manual_trade_journal",
        sa.Column("manual_trade_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("recommendation_id", sa.BigInteger(), nullable=True),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("journaled_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("manual_decision", sa.String(length=32), nullable=False),
        sa.Column("override_reason", sa.Text(), nullable=True),
        sa.Column("actual_entry_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_entry_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("actual_size", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column(
            "actual_size_unit",
            sa.String(length=16),
            nullable=True,
            comment="Unit for actual_size, for example BTC or USD.",
        ),
        sa.Column("actual_stop", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("actual_exit_time", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_exit_price", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "direction in ('long', 'short', 'flat')",
            name="ck_manual_trade_journal_direction_valid",
        ),
        sa.CheckConstraint(
            "manual_decision in ('FOLLOWED', 'OVERRIDDEN', 'SKIPPED', 'MANUAL_ONLY')",
            name="ck_manual_trade_journal_decision_valid",
        ),
        sa.CheckConstraint(
            "manual_decision = 'MANUAL_ONLY' or recommendation_id is not null",
            name="ck_manual_trade_journal_recommendation_required",
        ),
        sa.CheckConstraint(
            "manual_decision != 'OVERRIDDEN' or override_reason is not null",
            name="ck_manual_trade_journal_override_reason_required",
        ),
        sa.CheckConstraint(
            "actual_entry_price is null or actual_entry_price > 0",
            name="ck_manual_trade_journal_actual_entry_price_positive",
        ),
        sa.CheckConstraint(
            "actual_size is null or actual_size >= 0",
            name="ck_manual_trade_journal_actual_size_non_negative",
        ),
        sa.CheckConstraint(
            "actual_stop is null or actual_stop > 0",
            name="ck_manual_trade_journal_actual_stop_positive",
        ),
        sa.CheckConstraint(
            "actual_exit_price is null or actual_exit_price > 0",
            name="ck_manual_trade_journal_actual_exit_price_positive",
        ),
        sa.CheckConstraint(
            "actual_entry_time is null or actual_exit_time is null or actual_exit_time >= actual_entry_time",
            name="ck_manual_trade_journal_actual_time_order",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["signals.recommendations.recommendation_id"],
            name="fk_portfolio_manual_trade_recommendation",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("manual_trade_id", name="pk_portfolio_manual_trade_journal"),
        schema="portfolio",
        comment="Manual execution journal linked to model recommendations for suggested-versus-actual comparison.",
    )
    op.create_index(
        "ix_portfolio_manual_trade_journal_recommendation",
        "manual_trade_journal",
        ["recommendation_id"],
        schema="portfolio",
    )
    op.create_index(
        "ix_portfolio_manual_trade_journal_symbol_time",
        "manual_trade_journal",
        ["symbol", "journaled_at"],
        schema="portfolio",
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.drop_table("manual_trade_journal", schema="portfolio")
