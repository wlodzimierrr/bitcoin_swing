"""create BTC reference composite derived schema

Revision ID: 0019_reference_composite
Revises: 0018_ingestion_audit
Create Date: 2026-08-29 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0019_reference_composite"
down_revision = "0018_ingestion_audit"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.create_table(
        "btc_reference_composite",
        sa.Column("reference_policy_version", sa.String(length=64), nullable=False),
        sa.Column("observation_time", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="Fixed composite decision time: one-hour bar close plus five minutes.",
        ),
        sa.Column("input_providers_expected", sa.JSON(), nullable=False),
        sa.Column("input_providers_available", sa.JSON(), nullable=False),
        sa.Column("bitstamp_observation_id", sa.String(length=64), nullable=True),
        sa.Column("coinbase_observation_id", sa.String(length=64), nullable=True),
        sa.Column("bitfinex_observation_id", sa.String(length=64), nullable=True),
        sa.Column("input_count", sa.SmallInteger(), nullable=False),
        sa.Column("composite_method", sa.String(length=64), nullable=False),
        sa.Column("composite_method_version", sa.String(length=64), nullable=False),
        sa.Column("open", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("high", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("low", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("close", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("quality_state", sa.String(length=32), nullable=False),
        sa.Column("confirmation_state", sa.String(length=48), nullable=False),
        sa.Column("fallback_used", sa.Boolean(), nullable=False),
        sa.Column("diagnostics", sa.JSON(), nullable=False),
        sa.Column("reason_codes", sa.JSON(), nullable=False),
        sa.CheckConstraint(
            "input_count between 0 and 3",
            name="ck_btc_reference_composite_input_count_range",
        ),
        sa.CheckConstraint(
            "quality_state in ('REFERENCE_OK', 'REFERENCE_DEGRADED', "
            "'REFERENCE_UNAVAILABLE', 'VENUE_DISAGREEMENT')",
            name="ck_btc_reference_composite_quality_state_valid",
        ),
        sa.CheckConstraint(
            "confirmation_state in ('SINGLE_PROVIDER_OBSERVATION', "
            "'TWO_PROVIDER_CONSENSUS', 'THREE_PROVIDER_CONSENSUS', "
            "'UNRESOLVED_PROVIDER_DISAGREEMENT')",
            name="ck_btc_reference_composite_confirmation_state_valid",
        ),
        sa.CheckConstraint(
            "fallback_used = false",
            name="ck_btc_reference_composite_fallback_splicing_prohibited",
        ),
        sa.CheckConstraint(
            "((open is null and high is null and low is null and close is null) or "
            "(open is not null and high is not null and low is not null and close is not null))",
            name="ck_btc_reference_composite_ohlc_all_present_or_absent",
        ),
        sa.CheckConstraint(
            "high is null or (open > 0 and high >= open and high >= close and "
            "low > 0 and low <= open and low <= close and high >= low)",
            name="ck_btc_reference_composite_ohlc_valid",
        ),
        sa.PrimaryKeyConstraint(
            "reference_policy_version",
            "observation_time",
            "composite_method_version",
            name="pk_derived_btc_reference_composite",
        ),
        schema="derived",
        comment=(
            "Immutable point-in-time cross-venue BTC reference-composite research "
            "observations with full raw provenance."
        ),
    )
    op.create_index(
        "ix_derived_btc_reference_composite_available_at",
        "btc_reference_composite",
        ["available_at"],
        schema="derived",
    )
    op.create_index(
        "ix_derived_btc_reference_composite_quality_state",
        "btc_reference_composite",
        ["quality_state"],
        schema="derived",
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.drop_table("btc_reference_composite", schema="derived")
