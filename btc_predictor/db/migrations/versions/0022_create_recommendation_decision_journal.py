"""create recommendation decision journal

Revision ID: 0022_decision_journal
Revises: 0021_trade_accounting
Create Date: 2026-09-02 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0022_decision_journal"
down_revision = "0021_trade_accounting"
branch_labels = None
depends_on = None

# BTC-200 records what the operator decided about an advisory. The BTC-017
# manual execution journal cannot hold it: its decision vocabulary describes an
# executed trade, and every other column of that table describes a fill, while
# REJECTED and MISSED advisories produce no fill at all. Its own table also
# keeps the decision recordable at decision time, before any execution exists.


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.create_table(
        "recommendation_decisions",
        sa.Column("decision_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column("recommendation_id", sa.BigInteger(), nullable=False),
        # BTC-166 requires the full provenance triple on every persisted
        # decision row, so a decision can never be attributed to a strategy
        # version other than the one that produced the advisory.
        sa.Column("strategy_version", sa.String(length=64), nullable=False),
        sa.Column("parameter_set_id", sa.String(length=64), nullable=False),
        sa.Column("config_version", sa.String(length=64), nullable=False),
        sa.Column(
            "evaluation_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Advisory evaluation time; kept here so decision ordering is checkable in the row.",
        ),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("decision", sa.String(length=16), nullable=False),
        sa.Column("advised_action", sa.String(length=16), nullable=False),
        sa.Column(
            "modified_fields",
            sa.JSON(),
            nullable=False,
            comment="Advisory fields the operator departed from; empty unless the decision is MODIFIED.",
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("advisory_schema_version", sa.String(length=64), nullable=False),
        sa.Column(
            "advisory_body",
            sa.Text(),
            nullable=False,
            comment="Canonical BTC-172 advisory JSON exactly as decided against.",
        ),
        sa.Column(
            "advisory_digest",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 of advisory_body; proves which document the decision answers.",
        ),
        sa.Column("journal_policy_version", sa.String(length=64), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "decision in ('APPROVED', 'REJECTED', 'MODIFIED', 'MISSED')",
            name="decision_valid",
        ),
        sa.CheckConstraint(
            "advised_action in ('NO_TRADE', 'WATCH', 'ENTER', 'HOLD', 'ADD', 'TRIM', 'EXIT')",
            name="advised_action_valid",
        ),
        sa.CheckConstraint(
            "decided_at >= evaluation_time",
            name="decided_after_evaluation",
        ),
        sa.CheckConstraint(
            "length(btrim(strategy_version)) > 0",
            name="strategy_version_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(parameter_set_id)) > 0",
            name="parameter_set_id_not_blank",
        ),
        sa.CheckConstraint(
            "length(btrim(config_version)) > 0",
            name="config_version_not_blank",
        ),
        sa.CheckConstraint(
            "length(advisory_digest) = 64",
            name="advisory_digest_sha256",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["signals.recommendations.recommendation_id"],
            name="fk_portfolio_recommendation_decision_recommendation",
            # RESTRICT, not SET NULL: a decision without its recommendation is
            # not a weaker record, it is an unattributable one.
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint(
            "decision_id",
            name="pk_portfolio_recommendation_decisions",
        ),
        # One advisory carries one recorded disposition. A second row would
        # leave BTC-203 unable to say which decision the operator actually made.
        sa.UniqueConstraint(
            "recommendation_id",
            name="uq_portfolio_recommendation_decisions_recommendation",
        ),
        schema="portfolio",
        comment="Operator decisions recorded against model recommendations.",
    )
    op.create_index(
        "ix_portfolio_recommendation_decisions_decision_time",
        "recommendation_decisions",
        ["decision", "decided_at"],
        schema="portfolio",
    )
    op.create_index(
        "ix_portfolio_recommendation_decisions_strategy_identity",
        "recommendation_decisions",
        ["strategy_version", "parameter_set_id"],
        schema="portfolio",
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.drop_table("recommendation_decisions", schema="portfolio")
