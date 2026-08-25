"""Signal database table definitions."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
)

from btc_predictor.db.base import NAMING_CONVENTION


SIGNALS_SCHEMA = "signals"

PREDICTOR_RUNS_PRIMARY_KEY = ("run_id",)
RECOMMENDATIONS_PRIMARY_KEY = ("recommendation_id",)
RECOMMENDATION_REASON_CODES_PRIMARY_KEY = ("recommendation_id", "reason_rank")

RECONSTRUCTABLE_RECOMMENDATION_COLUMNS = (
    "recommendation_id",
    "run_id",
    "evaluation_time",
    "symbol",
    "timeframe",
    "regime",
    "setup",
    "direction",
    "trend_score",
    "regime_score",
    "flow_score",
    "positioning_score",
    "volatility_score",
    "structure_score",
    "entry_conviction",
    "hold_score",
    "add_score",
    "entry_zone_lower",
    "entry_zone_upper",
    "invalidation_level",
    "initial_stop",
    "rr_ratio",
    "risk_fraction_nav",
    "risk_amount",
    "suggested_notional",
    "action",
)

signals_metadata = MetaData(schema=SIGNALS_SCHEMA, naming_convention=NAMING_CONVENTION)

predictor_runs = Table(
    "predictor_runs",
    signals_metadata,
    Column("run_id", BigInteger, Identity(always=True), nullable=False),
    Column(
        "run_started_at",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC time the predictor run started.",
    ),
    Column(
        "evaluation_time",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC decision timestamp being evaluated.",
    ),
    Column(
        "data_available_at",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC data availability cutoff used for point-in-time reconstruction.",
    ),
    Column("config_version", String(length=64), nullable=False),
    Column("strategy_version", String(length=64), nullable=False),
    Column("feature_version", String(length=64), nullable=False),
    Column("parameter_set_id", String(length=128), nullable=False),
    Column("code_commit", String(length=64), nullable=False),
    Column("data_snapshot_id", String(length=128), nullable=True),
    PrimaryKeyConstraint(*PREDICTOR_RUNS_PRIMARY_KEY, name="pk_signals_predictor_runs"),
    comment="Immutable predictor run identity for reconstructing recommendations.",
)
Index("ix_signals_predictor_runs_evaluation_time", predictor_runs.c.evaluation_time)
Index("ix_signals_predictor_runs_strategy_version", predictor_runs.c.strategy_version)

recommendations = Table(
    "recommendations",
    signals_metadata,
    Column("recommendation_id", BigInteger, Identity(always=True), nullable=False),
    Column("run_id", BigInteger, nullable=False),
    Column(
        "created_at",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC time this recommendation row was written.",
    ),
    Column(
        "evaluation_time",
        DateTime(timezone=True),
        nullable=False,
        comment="UTC decision timestamp this recommendation applies to.",
    ),
    Column("symbol", String(length=32), nullable=False),
    Column("timeframe", String(length=16), nullable=False),
    Column("regime", String(length=32), nullable=False),
    Column("setup", String(length=64), nullable=True),
    Column("direction", String(length=16), nullable=False),
    Column("trend_score", Numeric(precision=6, scale=3), nullable=False),
    Column("regime_score", Numeric(precision=6, scale=3), nullable=False),
    Column("flow_score", Numeric(precision=6, scale=3), nullable=False),
    Column("positioning_score", Numeric(precision=6, scale=3), nullable=False),
    Column("volatility_score", Numeric(precision=6, scale=3), nullable=False),
    Column("structure_score", Numeric(precision=6, scale=3), nullable=False),
    Column("entry_conviction", Numeric(precision=6, scale=3), nullable=False),
    Column("hold_score", Numeric(precision=6, scale=3), nullable=True),
    Column("add_score", Numeric(precision=6, scale=3), nullable=True),
    Column("entry_zone_lower", Numeric(precision=38, scale=18), nullable=True),
    Column("entry_zone_upper", Numeric(precision=38, scale=18), nullable=True),
    Column("invalidation_level", Numeric(precision=38, scale=18), nullable=True),
    Column("initial_stop", Numeric(precision=38, scale=18), nullable=True),
    Column("rr_ratio", Numeric(precision=12, scale=6), nullable=True),
    Column("risk_fraction_nav", Numeric(precision=12, scale=8), nullable=True),
    Column("risk_amount", Numeric(precision=38, scale=18), nullable=True),
    Column("suggested_notional", Numeric(precision=38, scale=18), nullable=True),
    Column("action", String(length=32), nullable=False),
    ForeignKeyConstraint(
        ["run_id"],
        ["signals.predictor_runs.run_id"],
        name="fk_signals_recommendations_run_id_predictor_runs",
        ondelete="RESTRICT",
    ),
    PrimaryKeyConstraint(*RECOMMENDATIONS_PRIMARY_KEY, name="pk_signals_recommendations"),
    UniqueConstraint(
        "run_id",
        "symbol",
        "timeframe",
        name="uq_signals_recommendations_run_symbol_timeframe",
    ),
    CheckConstraint("direction in ('long', 'short', 'flat')", name="recommendations_direction_valid"),
    CheckConstraint(
        "action in ('NO_TRADE', 'WATCH', 'ENTER', 'HOLD', 'ADD', 'TRIM', 'EXIT')",
        name="recommendations_action_valid",
    ),
    CheckConstraint(
        "trend_score between 0 and 100",
        name="recommendations_trend_score_range",
    ),
    CheckConstraint(
        "regime_score between 0 and 100",
        name="recommendations_regime_score_range",
    ),
    CheckConstraint("flow_score between 0 and 100", name="recommendations_flow_score_range"),
    CheckConstraint(
        "positioning_score between 0 and 100",
        name="recommendations_positioning_score_range",
    ),
    CheckConstraint(
        "volatility_score between 0 and 100",
        name="recommendations_volatility_score_range",
    ),
    CheckConstraint(
        "structure_score between 0 and 100",
        name="recommendations_structure_score_range",
    ),
    CheckConstraint(
        "entry_conviction between 0 and 100",
        name="recommendations_entry_conviction_range",
    ),
    CheckConstraint(
        "hold_score is null or hold_score between 0 and 100",
        name="recommendations_hold_score_range",
    ),
    CheckConstraint(
        "add_score is null or add_score between 0 and 100",
        name="recommendations_add_score_range",
    ),
    CheckConstraint(
        "entry_zone_lower is null or entry_zone_upper is null or entry_zone_lower <= entry_zone_upper",
        name="recommendations_entry_zone_order",
    ),
    CheckConstraint("rr_ratio is null or rr_ratio >= 0", name="recommendations_rr_ratio_non_negative"),
    CheckConstraint(
        "risk_fraction_nav is null or risk_fraction_nav >= 0",
        name="recommendations_risk_fraction_nav_non_negative",
    ),
    CheckConstraint(
        "risk_amount is null or risk_amount >= 0",
        name="recommendations_risk_amount_non_negative",
    ),
    CheckConstraint(
        "suggested_notional is null or suggested_notional >= 0",
        name="recommendations_suggested_notional_non_negative",
    ),
    comment="Point-in-time predictor recommendations with full score and risk payload.",
)
Index("ix_signals_recommendations_evaluation_time", recommendations.c.evaluation_time)
Index("ix_signals_recommendations_action", recommendations.c.action)

recommendation_reason_codes = Table(
    "recommendation_reason_codes",
    signals_metadata,
    Column("recommendation_id", BigInteger, nullable=False),
    Column(
        "reason_rank",
        BigInteger,
        nullable=False,
        comment="Stable display order for reconstructing recommendation explanations.",
    ),
    Column("code", String(length=64), nullable=False),
    Column("source_component", String(length=64), nullable=False),
    Column("severity", String(length=16), nullable=False),
    Column("detail", Text, nullable=False),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_signals_reason_codes_recommendation_id_recommendations",
        ondelete="CASCADE",
    ),
    PrimaryKeyConstraint(
        *RECOMMENDATION_REASON_CODES_PRIMARY_KEY,
        name="pk_signals_recommendation_reason_codes",
    ),
    CheckConstraint("reason_rank >= 0", name="recommendation_reason_codes_rank_non_negative"),
    CheckConstraint(
        "severity in ('info', 'warning', 'veto')",
        name="recommendation_reason_codes_severity_valid",
    ),
    comment="Ordered reason codes explaining each persisted recommendation.",
)
Index(
    "ix_signals_recommendation_reason_codes_code",
    recommendation_reason_codes.c.code,
)
