"""create predictor recommendation schemas

Revision ID: 0015_predictor_recommendations
Revises: 0014_raw_generic_series
Create Date: 2026-08-25 00:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0015_predictor_recommendations"
down_revision = "0014_raw_generic_series"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.create_table(
        "predictor_runs",
        sa.Column("run_id", sa.BigInteger(), sa.Identity(always=True), nullable=False),
        sa.Column(
            "run_started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC time the predictor run started.",
        ),
        sa.Column(
            "evaluation_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC decision timestamp being evaluated.",
        ),
        sa.Column(
            "data_available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC data availability cutoff used for point-in-time reconstruction.",
        ),
        sa.Column("config_version", sa.String(length=64), nullable=False),
        sa.Column("strategy_version", sa.String(length=64), nullable=False),
        sa.Column("feature_version", sa.String(length=64), nullable=False),
        sa.Column("parameter_set_id", sa.String(length=128), nullable=False),
        sa.Column("code_commit", sa.String(length=64), nullable=False),
        sa.Column("data_snapshot_id", sa.String(length=128), nullable=True),
        sa.PrimaryKeyConstraint("run_id", name="pk_signals_predictor_runs"),
        schema="signals",
        comment="Immutable predictor run identity for reconstructing recommendations.",
    )
    op.create_index(
        "ix_signals_predictor_runs_evaluation_time",
        "predictor_runs",
        ["evaluation_time"],
        schema="signals",
    )
    op.create_index(
        "ix_signals_predictor_runs_strategy_version",
        "predictor_runs",
        ["strategy_version"],
        schema="signals",
    )

    op.create_table(
        "recommendations",
        sa.Column(
            "recommendation_id",
            sa.BigInteger(),
            sa.Identity(always=True),
            nullable=False,
        ),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC time this recommendation row was written.",
        ),
        sa.Column(
            "evaluation_time",
            sa.DateTime(timezone=True),
            nullable=False,
            comment="UTC decision timestamp this recommendation applies to.",
        ),
        sa.Column("symbol", sa.String(length=32), nullable=False),
        sa.Column("timeframe", sa.String(length=16), nullable=False),
        sa.Column("regime", sa.String(length=32), nullable=False),
        sa.Column("setup", sa.String(length=64), nullable=True),
        sa.Column("direction", sa.String(length=16), nullable=False),
        sa.Column("trend_score", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("regime_score", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("flow_score", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("positioning_score", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("volatility_score", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("structure_score", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("entry_conviction", sa.Numeric(precision=6, scale=3), nullable=False),
        sa.Column("hold_score", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("add_score", sa.Numeric(precision=6, scale=3), nullable=True),
        sa.Column("entry_zone_lower", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("entry_zone_upper", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("invalidation_level", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("initial_stop", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("rr_ratio", sa.Numeric(precision=12, scale=6), nullable=True),
        sa.Column("risk_fraction_nav", sa.Numeric(precision=12, scale=8), nullable=True),
        sa.Column("risk_amount", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("suggested_notional", sa.Numeric(precision=38, scale=18), nullable=True),
        sa.Column("action", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "direction in ('long', 'short', 'flat')",
            name="ck_recommendations_direction_valid",
        ),
        sa.CheckConstraint(
            "action in ('NO_TRADE', 'WATCH', 'ENTER', 'HOLD', 'ADD', 'TRIM', 'EXIT')",
            name="ck_recommendations_action_valid",
        ),
        sa.CheckConstraint(
            "trend_score between 0 and 100",
            name="ck_recommendations_trend_score_range",
        ),
        sa.CheckConstraint(
            "regime_score between 0 and 100",
            name="ck_recommendations_regime_score_range",
        ),
        sa.CheckConstraint(
            "flow_score between 0 and 100",
            name="ck_recommendations_flow_score_range",
        ),
        sa.CheckConstraint(
            "positioning_score between 0 and 100",
            name="ck_recommendations_positioning_score_range",
        ),
        sa.CheckConstraint(
            "volatility_score between 0 and 100",
            name="ck_recommendations_volatility_score_range",
        ),
        sa.CheckConstraint(
            "structure_score between 0 and 100",
            name="ck_recommendations_structure_score_range",
        ),
        sa.CheckConstraint(
            "entry_conviction between 0 and 100",
            name="ck_recommendations_entry_conviction_range",
        ),
        sa.CheckConstraint(
            "hold_score is null or hold_score between 0 and 100",
            name="ck_recommendations_hold_score_range",
        ),
        sa.CheckConstraint(
            "add_score is null or add_score between 0 and 100",
            name="ck_recommendations_add_score_range",
        ),
        sa.CheckConstraint(
            "entry_zone_lower is null or entry_zone_upper is null or entry_zone_lower <= entry_zone_upper",
            name="ck_recommendations_entry_zone_order",
        ),
        sa.CheckConstraint(
            "rr_ratio is null or rr_ratio >= 0",
            name="ck_recommendations_rr_ratio_non_negative",
        ),
        sa.CheckConstraint(
            "risk_fraction_nav is null or risk_fraction_nav >= 0",
            name="ck_recommendations_risk_fraction_nav_non_negative",
        ),
        sa.CheckConstraint(
            "risk_amount is null or risk_amount >= 0",
            name="ck_recommendations_risk_amount_non_negative",
        ),
        sa.CheckConstraint(
            "suggested_notional is null or suggested_notional >= 0",
            name="ck_recommendations_suggested_notional_non_negative",
        ),
        sa.ForeignKeyConstraint(
            ["run_id"],
            ["signals.predictor_runs.run_id"],
            name="fk_signals_recommendations_run_id_predictor_runs",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("recommendation_id", name="pk_signals_recommendations"),
        sa.UniqueConstraint(
            "run_id",
            "symbol",
            "timeframe",
            name="uq_signals_recommendations_run_symbol_timeframe",
        ),
        schema="signals",
        comment="Point-in-time predictor recommendations with full score and risk payload.",
    )
    op.create_index(
        "ix_signals_recommendations_evaluation_time",
        "recommendations",
        ["evaluation_time"],
        schema="signals",
    )
    op.create_index(
        "ix_signals_recommendations_action",
        "recommendations",
        ["action"],
        schema="signals",
    )

    op.create_table(
        "recommendation_reason_codes",
        sa.Column("recommendation_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "reason_rank",
            sa.BigInteger(),
            nullable=False,
            comment="Stable display order for reconstructing recommendation explanations.",
        ),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("source_component", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("detail", sa.Text(), nullable=False),
        sa.CheckConstraint(
            "reason_rank >= 0",
            name="ck_recommendation_reason_codes_rank_non_negative",
        ),
        sa.CheckConstraint(
            "severity in ('info', 'warning', 'veto')",
            name="ck_recommendation_reason_codes_severity_valid",
        ),
        sa.ForeignKeyConstraint(
            ["recommendation_id"],
            ["signals.recommendations.recommendation_id"],
            name="fk_signals_reason_codes_recommendation_id_recommendations",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint(
            "recommendation_id",
            "reason_rank",
            name="pk_signals_recommendation_reason_codes",
        ),
        schema="signals",
        comment="Ordered reason codes explaining each persisted recommendation.",
    )
    op.create_index(
        "ix_signals_recommendation_reason_codes_code",
        "recommendation_reason_codes",
        ["code"],
        schema="signals",
    )


def downgrade() -> None:
    if op.get_context().dialect.name != "postgresql":
        return

    op.drop_table("recommendation_reason_codes", schema="signals")
    op.drop_table("recommendations", schema="signals")
    op.drop_table("predictor_runs", schema="signals")
