"""add actual trade entry metadata

Revision ID: 0024_actual_trade_entry
Revises: 0023_discretionary_reasons
Create Date: 2026-09-02 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0024_actual_trade_entry"
down_revision = "0023_discretionary_reasons"
branch_labels = None
depends_on = None

_LEGACY_POLICY_VERSION = "MANUAL_EXECUTION_JOURNAL_LEGACY"
_V1_POLICY_VERSION = "MANUAL_EXECUTION_JOURNAL_V1"


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    # BTC-017 predates the writer implemented by BTC-202. Existing rows cannot
    # be attributed retrospectively without inventing decision/config evidence,
    # so they retain nullable linkage metadata and an explicit legacy policy.
    op.add_column(
        "manual_trade_journal",
        sa.Column("strategy_version", sa.String(length=64), nullable=True),
        schema="portfolio",
    )
    op.add_column(
        "manual_trade_journal",
        sa.Column("parameter_set_id", sa.String(length=64), nullable=True),
        schema="portfolio",
    )
    op.add_column(
        "manual_trade_journal",
        sa.Column("config_version", sa.String(length=64), nullable=True),
        schema="portfolio",
    )
    op.add_column(
        "manual_trade_journal",
        sa.Column("decision_journal_policy_version", sa.String(length=64), nullable=True),
        schema="portfolio",
    )
    op.add_column(
        "manual_trade_journal",
        sa.Column("decision_decided_at", sa.DateTime(timezone=True), nullable=True),
        schema="portfolio",
    )
    op.add_column(
        "manual_trade_journal",
        sa.Column(
            "decision_reason_codes",
            sa.JSON(),
            nullable=True,
            comment="BTC-200 decision reason codes snapshotted at execution time.",
        ),
        schema="portfolio",
    )
    op.add_column(
        "manual_trade_journal",
        sa.Column(
            "discretionary_reason_policy_version",
            sa.String(length=64),
            nullable=True,
        ),
        schema="portfolio",
    )
    op.add_column(
        "manual_trade_journal",
        sa.Column(
            "discretionary_reason_codes",
            sa.JSON(),
            nullable=True,
            comment="BTC-201 discretionary reason codes snapshotted at execution time.",
        ),
        schema="portfolio",
    )
    op.add_column(
        "manual_trade_journal",
        sa.Column(
            "execution_journal_policy_version",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text(f"'{_LEGACY_POLICY_VERSION}'"),
        ),
        schema="portfolio",
    )
    op.alter_column(
        "manual_trade_journal",
        "execution_journal_policy_version",
        server_default=None,
        schema="portfolio",
    )
    op.create_check_constraint(
        "execution_journal_policy_version_not_blank",
        "manual_trade_journal",
        "length(btrim(execution_journal_policy_version)) > 0",
        schema="portfolio",
    )
    op.create_check_constraint(
        "actual_trade_v1_fill_complete",
        "manual_trade_journal",
        (
            f"execution_journal_policy_version != '{_V1_POLICY_VERSION}' or ("
            "direction in ('long', 'short') and "
            "manual_decision in ('FOLLOWED', 'OVERRIDDEN', 'MANUAL_ONLY') and "
            "actual_entry_time is not null and actual_entry_price is not null and "
            "actual_size is not null and actual_size > 0 and "
            "actual_size_unit is not null and length(btrim(actual_size_unit)) > 0 and "
            "journaled_at >= actual_entry_time and "
            "((actual_exit_time is null and actual_exit_price is null) or "
            "(actual_exit_time is not null and actual_exit_price is not null and "
            "journaled_at >= actual_exit_time)))"
        ),
        schema="portfolio",
    )
    op.create_check_constraint(
        "actual_trade_v1_attribution_complete",
        "manual_trade_journal",
        (
            f"execution_journal_policy_version != '{_V1_POLICY_VERSION}' or ("
            "(manual_decision = 'MANUAL_ONLY' and recommendation_id is null and "
            "strategy_version is null and parameter_set_id is null and "
            "config_version is null and decision_journal_policy_version is null and "
            "decision_decided_at is null and decision_reason_codes is null and "
            "discretionary_reason_policy_version is null and "
            "discretionary_reason_codes is null and override_reason is null) or "
            "(manual_decision in ('FOLLOWED', 'OVERRIDDEN') and "
            "recommendation_id is not null and strategy_version is not null and "
            "parameter_set_id is not null and config_version is not null and "
            "decision_journal_policy_version is not null and "
            "decision_decided_at is not null and decision_reason_codes is not null and "
            "discretionary_reason_policy_version is not null and "
            "discretionary_reason_codes is not null and "
            "decision_decided_at <= actual_entry_time and "
            "((manual_decision = 'FOLLOWED' and override_reason is null) or "
            "(manual_decision = 'OVERRIDDEN' and override_reason is not null))))"
        ),
        schema="portfolio",
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    for constraint_name in (
        "actual_trade_v1_attribution_complete",
        "actual_trade_v1_fill_complete",
        "execution_journal_policy_version_not_blank",
    ):
        op.drop_constraint(
            constraint_name,
            "manual_trade_journal",
            schema="portfolio",
            type_="check",
        )
    for column_name in (
        "execution_journal_policy_version",
        "discretionary_reason_codes",
        "discretionary_reason_policy_version",
        "decision_reason_codes",
        "decision_decided_at",
        "decision_journal_policy_version",
        "config_version",
        "parameter_set_id",
        "strategy_version",
    ):
        op.drop_column("manual_trade_journal", column_name, schema="portfolio")
