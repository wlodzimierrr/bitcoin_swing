"""persist complete paper trade accounting

Revision ID: 0021_trade_accounting
Revises: 0020_lifecycle_provenance
Create Date: 2026-08-31 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0021_trade_accounting"
down_revision = "0020_lifecycle_provenance"
branch_labels = None
depends_on = None

_COLUMNS = (
    sa.Column("gross_pnl", sa.Numeric(precision=38, scale=18), nullable=False),
    sa.Column("fees", sa.Numeric(precision=38, scale=18), nullable=False),
    sa.Column("funding", sa.Numeric(precision=38, scale=18), nullable=False),
    sa.Column("initial_risk", sa.Numeric(precision=38, scale=18), nullable=False),
    sa.Column("mfe", sa.Numeric(precision=38, scale=18), nullable=True),
    sa.Column("mae", sa.Numeric(precision=38, scale=18), nullable=True),
    sa.Column("mfe_r", sa.Numeric(precision=18, scale=8), nullable=True),
    sa.Column("mae_r", sa.Numeric(precision=18, scale=8), nullable=True),
    sa.Column("holding_days", sa.Numeric(precision=38, scale=18), nullable=False),
    sa.Column("maximum_quantity", sa.Numeric(precision=38, scale=18), nullable=False),
    sa.Column(
        "maximum_entry_notional",
        sa.Numeric(precision=38, scale=18),
        nullable=False,
    ),
    sa.Column("add_count", sa.BigInteger(), nullable=False),
    sa.Column("trim_count", sa.BigInteger(), nullable=False),
    sa.Column("exit_reason", sa.String(length=255), nullable=False),
    sa.Column("initial_stop_source_id", sa.String(length=255), nullable=False),
    sa.Column("exit_reason_source_id", sa.String(length=255), nullable=False),
    sa.Column("accounting_evidence_digest", sa.String(length=64), nullable=False),
    sa.Column("accounting_policy_version", sa.String(length=64), nullable=False),
    sa.Column("r_multiple_convention", sa.String(length=64), nullable=False),
    sa.Column("funding_convention", sa.String(length=64), nullable=False),
    sa.Column("excursion_convention", sa.String(length=64), nullable=False),
    sa.Column("maximum_size_convention", sa.String(length=64), nullable=False),
    sa.Column("config_version", sa.String(length=64), nullable=False),
    sa.Column("accounting_record", sa.JSON(), nullable=False),
)

_CHECKS = (
    ("completed_trades_fees_non_negative", "fees >= 0"),
    ("completed_trades_initial_risk_non_negative", "initial_risk >= 0"),
    ("completed_trades_holding_days_non_negative", "holding_days >= 0"),
    ("completed_trades_maximum_quantity_positive", "maximum_quantity > 0"),
    (
        "completed_trades_maximum_entry_notional_positive",
        "maximum_entry_notional > 0",
    ),
    ("completed_trades_add_count_non_negative", "add_count >= 0"),
    ("completed_trades_trim_count_non_negative", "trim_count >= 0"),
)


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    for column in _COLUMNS:
        op.add_column("completed_trades", column, schema="portfolio")
    for name, condition in _CHECKS:
        op.create_check_constraint(
            name,
            "completed_trades",
            condition,
            schema="portfolio",
        )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return
    for name, _ in reversed(_CHECKS):
        op.drop_constraint(
            name,
            "completed_trades",
            schema="portfolio",
            type_="check",
        )
    for column in reversed(_COLUMNS):
        op.drop_column("completed_trades", column.name, schema="portfolio")
