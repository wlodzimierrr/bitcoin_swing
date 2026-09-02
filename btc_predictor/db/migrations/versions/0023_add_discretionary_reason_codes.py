"""add discretionary reason codes

Revision ID: 0023_discretionary_reasons
Revises: 0022_decision_journal
Create Date: 2026-09-02 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0023_discretionary_reasons"
down_revision = "0022_decision_journal"
branch_labels = None
depends_on = None

_POLICY_VERSION = "DISCRETIONARY_REASON_CODES_V1"


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    # Existing BTC-200 decisions predate discretionary classification. Empty
    # reasons preserve that fact; a server default is used only for the
    # migration backfill and removed so every new writer must be explicit.
    op.add_column(
        "recommendation_decisions",
        sa.Column(
            "discretionary_reason_policy_version",
            sa.String(length=64),
            nullable=False,
            server_default=sa.text(f"'{_POLICY_VERSION}'"),
        ),
        schema="portfolio",
    )
    op.add_column(
        "recommendation_decisions",
        sa.Column(
            "discretionary_reason_codes",
            sa.JSON(),
            nullable=False,
            server_default=sa.text("'[]'::json"),
            comment=(
                "Ordered BTC-201 codes explaining the operator's discretionary "
                "decision."
            ),
        ),
        schema="portfolio",
    )
    op.alter_column(
        "recommendation_decisions",
        "discretionary_reason_policy_version",
        server_default=None,
        schema="portfolio",
    )
    op.alter_column(
        "recommendation_decisions",
        "discretionary_reason_codes",
        server_default=None,
        schema="portfolio",
    )
    op.create_check_constraint(
        "discretionary_reason_policy_version_not_blank",
        "recommendation_decisions",
        "length(btrim(discretionary_reason_policy_version)) > 0",
        schema="portfolio",
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.drop_constraint(
        "discretionary_reason_policy_version_not_blank",
        "recommendation_decisions",
        schema="portfolio",
        type_="check",
    )
    op.drop_column(
        "recommendation_decisions",
        "discretionary_reason_codes",
        schema="portfolio",
    )
    op.drop_column(
        "recommendation_decisions",
        "discretionary_reason_policy_version",
        schema="portfolio",
    )
