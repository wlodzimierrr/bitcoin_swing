"""add paper lifecycle provenance columns

Revision ID: 0020_lifecycle_provenance
Revises: 0019_reference_composite
Create Date: 2026-08-31 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0020_lifecycle_provenance"
down_revision = "0019_reference_composite"
branch_labels = None
depends_on = None

# BTC-166 requires every persisted lifecycle event to carry the strategy
# identity that produced it. ``recommendation_id`` already exists on these
# tables; strategy version and parameter set had nowhere to live except a JSON
# note, which paper_orders does not even have. Without real columns a run's
# provenance is not queryable and two parameter sets are indistinguishable.
_EVENT_TABLES = ("paper_orders", "position_events", "completed_trades")


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    # completed_trades reached its recommendation only through positions. The
    # triple has to be uniform for the link to be queryable without a join.
    op.add_column(
        "completed_trades",
        sa.Column("recommendation_id", sa.BigInteger(), nullable=True),
        schema="portfolio",
    )
    op.create_foreign_key(
        "fk_pf_completed_trades_recommendation",
        "completed_trades",
        "recommendations",
        ["recommendation_id"],
        ["recommendation_id"],
        source_schema="portfolio",
        referent_schema="signals",
        ondelete="SET NULL",
    )

    for table in _EVENT_TABLES:
        op.add_column(
            table,
            sa.Column("strategy_version", sa.String(length=64), nullable=False),
            schema="portfolio",
        )
        op.add_column(
            table,
            sa.Column("parameter_set_id", sa.String(length=64), nullable=False),
            schema="portfolio",
        )
        op.create_check_constraint(
            f"{table}_strategy_version_not_blank",
            table,
            "length(btrim(strategy_version)) > 0",
            schema="portfolio",
        )
        op.create_check_constraint(
            f"{table}_parameter_set_id_not_blank",
            table,
            "length(btrim(parameter_set_id)) > 0",
            schema="portfolio",
        )
        op.create_index(
            f"ix_portfolio_{table}_strategy_identity",
            table,
            ["strategy_version", "parameter_set_id"],
            schema="portfolio",
        )

    # recommendation_id is deliberately left nullable. Its foreign keys are
    # ON DELETE SET NULL, so a NOT NULL column would make deleting a
    # recommendation fail instead of severing the link. BTC-166 therefore
    # enforces the recommendation link in the writer, which is the layer that
    # knows an event is model-driven.


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    for table in _EVENT_TABLES:
        op.drop_index(
            f"ix_portfolio_{table}_strategy_identity",
            table_name=table,
            schema="portfolio",
        )
        op.drop_constraint(
            f"{table}_parameter_set_id_not_blank",
            table,
            schema="portfolio",
            type_="check",
        )
        op.drop_constraint(
            f"{table}_strategy_version_not_blank",
            table,
            schema="portfolio",
            type_="check",
        )
        op.drop_column(table, "parameter_set_id", schema="portfolio")
        op.drop_column(table, "strategy_version", schema="portfolio")

    op.drop_constraint(
        "fk_pf_completed_trades_recommendation",
        "completed_trades",
        schema="portfolio",
        type_="foreignkey",
    )
    op.drop_column("completed_trades", "recommendation_id", schema="portfolio")
