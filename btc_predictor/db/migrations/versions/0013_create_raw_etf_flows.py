"""create raw etf flows

Revision ID: 0013_create_raw_etf_flows
Revises: 0012_create_derivatives_raw_schemas
Create Date: 2026-08-25 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_create_raw_etf_flows"
down_revision = "0012_create_derivatives_raw_schemas"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.create_table(
        "etf_flows",
        sa.Column(
            "fund",
            sa.String(length=64),
            nullable=False,
            comment="ETF ticker or fund identifier reported by the provider.",
        ),
        sa.Column(
            "observation_date",
            sa.Date(),
            nullable=False,
            comment="Fund flow observation date in the fund's reporting calendar.",
        ),
        sa.Column(
            "flow_usd",
            sa.Numeric(precision=38, scale=18),
            nullable=False,
            comment="Net fund flow in USD; positive is inflow, negative is outflow.",
        ),
        sa.Column(
            "aum_usd",
            sa.Numeric(precision=38, scale=18),
            nullable=True,
            comment="Assets under management in USD when reported by the source.",
        ),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("source", sa.String(length=255), nullable=False),
        sa.Column(
            "revision",
            sa.String(length=64),
            nullable=False,
            comment="Provider revision identifier; use initial when no explicit revision exists.",
        ),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC time this specific flow revision first became available.",
        ),
        sa.Column("ingested_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "aum_usd is null or aum_usd >= 0",
            name="ck_etf_flows_aum_usd_non_negative",
        ),
        sa.PrimaryKeyConstraint(
            "fund",
            "observation_date",
            "provider",
            "revision",
            "available_at",
            name="pk_raw_etf_flows",
        ),
        schema="raw",
        comment="Point-in-time raw ETF flow observations with historical revisions preserved.",
    )
    op.create_index(
        "ix_raw_etf_flows_available_at",
        "etf_flows",
        ["available_at"],
        schema="raw",
    )
    op.create_index(
        "ix_raw_etf_flows_observation_date",
        "etf_flows",
        ["observation_date"],
        schema="raw",
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.drop_table("etf_flows", schema="raw")
