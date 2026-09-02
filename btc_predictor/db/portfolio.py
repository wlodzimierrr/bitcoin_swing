"""Paper portfolio database table definitions."""

from __future__ import annotations

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKeyConstraint,
    Identity,
    Index,
    JSON,
    MetaData,
    Numeric,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    UniqueConstraint,
)

from btc_predictor.db.base import NAMING_CONVENTION


PORTFOLIO_SCHEMA = "portfolio"

PAPER_ACTIONS = ("ENTER", "HOLD", "ADD", "STOP_MOVE", "TRIM", "EXIT", "MISSED")
MANUAL_DECISIONS = ("FOLLOWED", "OVERRIDDEN", "SKIPPED", "MANUAL_ONLY")
# BTC-200: the disposition an operator records against one model recommendation.
# This is a decision about an advisory, not a record of an executed trade, so it
# is deliberately separate from the BTC-017 manual execution vocabulary above.
RECOMMENDATION_DECISIONS = ("APPROVED", "REJECTED", "MODIFIED", "MISSED")
# BTC-166: every persisted lifecycle event carries the strategy identity that
# produced it, so two parameter sets are never indistinguishable in the record.
LIFECYCLE_PROVENANCE_COLUMNS = (
    "recommendation_id",
    "strategy_version",
    "parameter_set_id",
)
LIFECYCLE_EVENT_TABLES = ("paper_orders", "position_events", "completed_trades")

PAPER_ACCOUNTS_PRIMARY_KEY = ("account_id",)
POSITIONS_PRIMARY_KEY = ("position_id",)
TRANCHES_PRIMARY_KEY = ("tranche_id",)
PAPER_ORDERS_PRIMARY_KEY = ("order_id",)
STOPS_PRIMARY_KEY = ("stop_id",)
POSITION_EVENTS_PRIMARY_KEY = ("event_id",)
COMPLETED_TRADES_PRIMARY_KEY = ("completed_trade_id",)
MANUAL_TRADE_JOURNAL_PRIMARY_KEY = ("manual_trade_id",)
RECOMMENDATION_DECISIONS_PRIMARY_KEY = ("decision_id",)

portfolio_metadata = MetaData(schema=PORTFOLIO_SCHEMA, naming_convention=NAMING_CONVENTION)

paper_accounts = Table(
    "paper_accounts",
    portfolio_metadata,
    Column("account_id", BigInteger, Identity(always=True), nullable=False),
    Column("account_name", String(length=128), nullable=False),
    Column("base_currency", String(length=16), nullable=False),
    Column("starting_cash", Numeric(precision=38, scale=18), nullable=False),
    Column("current_cash", Numeric(precision=38, scale=18), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("status", String(length=16), nullable=False),
    PrimaryKeyConstraint(*PAPER_ACCOUNTS_PRIMARY_KEY, name="pk_portfolio_paper_accounts"),
    UniqueConstraint("account_name", name="uq_portfolio_paper_accounts_account_name"),
    CheckConstraint("starting_cash >= 0", name="paper_accounts_starting_cash_non_negative"),
    CheckConstraint("current_cash >= 0", name="paper_accounts_current_cash_non_negative"),
    CheckConstraint("status in ('active', 'archived')", name="paper_accounts_status_valid"),
    comment="Paper trading account state for model-only execution.",
)
Index("ix_portfolio_paper_accounts_status", paper_accounts.c.status)

positions = Table(
    "positions",
    portfolio_metadata,
    Column("position_id", BigInteger, Identity(always=True), nullable=False),
    Column("account_id", BigInteger, nullable=False),
    Column("opening_recommendation_id", BigInteger, nullable=True),
    Column("symbol", String(length=32), nullable=False),
    Column("direction", String(length=16), nullable=False),
    Column("status", String(length=16), nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("closed_at", DateTime(timezone=True), nullable=True),
    Column("average_entry_price", Numeric(precision=38, scale=18), nullable=True),
    Column("quantity", Numeric(precision=38, scale=18), nullable=False),
    Column("realized_pnl", Numeric(precision=38, scale=18), nullable=False),
    ForeignKeyConstraint(
        ["account_id"],
        ["portfolio.paper_accounts.account_id"],
        name="fk_portfolio_positions_account_id_paper_accounts",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["opening_recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_pf_positions_opening_recommendation",
        ondelete="SET NULL",
    ),
    PrimaryKeyConstraint(*POSITIONS_PRIMARY_KEY, name="pk_portfolio_positions"),
    CheckConstraint("direction in ('long', 'short')", name="positions_direction_valid"),
    CheckConstraint("status in ('open', 'closed', 'missed')", name="positions_status_valid"),
    CheckConstraint("quantity >= 0", name="positions_quantity_non_negative"),
    comment="Paper portfolio position lifecycle state.",
)
Index("ix_portfolio_positions_account_status", positions.c.account_id, positions.c.status)

tranches = Table(
    "tranches",
    portfolio_metadata,
    Column("tranche_id", BigInteger, Identity(always=True), nullable=False),
    Column("position_id", BigInteger, nullable=False),
    Column("recommendation_id", BigInteger, nullable=True),
    Column("tranche_number", BigInteger, nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("closed_at", DateTime(timezone=True), nullable=True),
    Column("entry_price", Numeric(precision=38, scale=18), nullable=False),
    Column("quantity", Numeric(precision=38, scale=18), nullable=False),
    Column("status", String(length=16), nullable=False),
    ForeignKeyConstraint(
        ["position_id"],
        ["portfolio.positions.position_id"],
        name="fk_portfolio_tranches_position_id_positions",
        ondelete="CASCADE",
    ),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_portfolio_tranches_recommendation_id_recommendations",
        ondelete="SET NULL",
    ),
    PrimaryKeyConstraint(*TRANCHES_PRIMARY_KEY, name="pk_portfolio_tranches"),
    UniqueConstraint("position_id", "tranche_number", name="uq_portfolio_tranches_position_number"),
    CheckConstraint("tranche_number >= 1", name="tranches_number_positive"),
    CheckConstraint("entry_price > 0", name="tranches_entry_price_positive"),
    CheckConstraint("quantity > 0", name="tranches_quantity_positive"),
    CheckConstraint("status in ('open', 'closed')", name="tranches_status_valid"),
    comment="Individual position tranches for anti-martingale adds and trims.",
)

paper_orders = Table(
    "paper_orders",
    portfolio_metadata,
    Column("order_id", BigInteger, Identity(always=True), nullable=False),
    Column("account_id", BigInteger, nullable=False),
    Column("position_id", BigInteger, nullable=True),
    Column("recommendation_id", BigInteger, nullable=True),
    Column("action", String(length=16), nullable=False),
    Column("side", String(length=8), nullable=False),
    Column("order_type", String(length=16), nullable=False),
    Column("status", String(length=16), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("submitted_at", DateTime(timezone=True), nullable=True),
    Column("filled_at", DateTime(timezone=True), nullable=True),
    Column("requested_quantity", Numeric(precision=38, scale=18), nullable=True),
    Column("filled_quantity", Numeric(precision=38, scale=18), nullable=True),
    Column("limit_price", Numeric(precision=38, scale=18), nullable=True),
    Column("stop_price", Numeric(precision=38, scale=18), nullable=True),
    Column("average_fill_price", Numeric(precision=38, scale=18), nullable=True),
    Column("strategy_version", String(length=64), nullable=False),
    Column("parameter_set_id", String(length=64), nullable=False),
    ForeignKeyConstraint(
        ["account_id"],
        ["portfolio.paper_accounts.account_id"],
        name="fk_portfolio_orders_account_id_paper_accounts",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["position_id"],
        ["portfolio.positions.position_id"],
        name="fk_portfolio_orders_position_id_positions",
        ondelete="SET NULL",
    ),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_portfolio_orders_recommendation_id_recommendations",
        ondelete="SET NULL",
    ),
    PrimaryKeyConstraint(*PAPER_ORDERS_PRIMARY_KEY, name="pk_portfolio_paper_orders"),
    CheckConstraint(
        "action in ('ENTER', 'ADD', 'TRIM', 'EXIT', 'MISSED')",
        name="paper_orders_action_valid",
    ),
    CheckConstraint("side in ('buy', 'sell')", name="paper_orders_side_valid"),
    CheckConstraint("order_type in ('market', 'limit', 'stop')", name="paper_orders_order_type_valid"),
    CheckConstraint(
        "status in ('created', 'submitted', 'filled', 'cancelled', 'missed')",
        name="paper_orders_status_valid",
    ),
    CheckConstraint(
        "requested_quantity is null or requested_quantity > 0",
        name="paper_orders_requested_quantity_positive",
    ),
    CheckConstraint(
        "filled_quantity is null or filled_quantity >= 0",
        name="paper_orders_filled_quantity_non_negative",
    ),
    comment="Paper execution orders derived from recommendations and lifecycle actions.",
)
Index("ix_portfolio_paper_orders_account_created_at", paper_orders.c.account_id, paper_orders.c.created_at)
Index("ix_portfolio_paper_orders_status", paper_orders.c.status)

stops = Table(
    "stops",
    portfolio_metadata,
    Column("stop_id", BigInteger, Identity(always=True), nullable=False),
    Column("position_id", BigInteger, nullable=False),
    Column("recommendation_id", BigInteger, nullable=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("stop_price", Numeric(precision=38, scale=18), nullable=False),
    Column("reason", String(length=64), nullable=False),
    Column("is_active", Boolean, nullable=False),
    ForeignKeyConstraint(
        ["position_id"],
        ["portfolio.positions.position_id"],
        name="fk_portfolio_stops_position_id_positions",
        ondelete="CASCADE",
    ),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_portfolio_stops_recommendation_id_recommendations",
        ondelete="SET NULL",
    ),
    PrimaryKeyConstraint(*STOPS_PRIMARY_KEY, name="pk_portfolio_stops"),
    CheckConstraint("stop_price > 0", name="stops_stop_price_positive"),
    comment="Structural stop history for paper positions, including stop moves.",
)
Index("ix_portfolio_stops_position_created_at", stops.c.position_id, stops.c.created_at)

position_events = Table(
    "position_events",
    portfolio_metadata,
    Column("event_id", BigInteger, Identity(always=True), nullable=False),
    Column("position_id", BigInteger, nullable=True),
    Column("account_id", BigInteger, nullable=False),
    Column("recommendation_id", BigInteger, nullable=True),
    Column("event_time", DateTime(timezone=True), nullable=False),
    Column("action", String(length=16), nullable=False),
    Column("quantity", Numeric(precision=38, scale=18), nullable=True),
    Column("price", Numeric(precision=38, scale=18), nullable=True),
    Column("risk_fraction_nav", Numeric(precision=12, scale=8), nullable=True),
    Column("notes", Text, nullable=True),
    Column("strategy_version", String(length=64), nullable=False),
    Column("parameter_set_id", String(length=64), nullable=False),
    ForeignKeyConstraint(
        ["account_id"],
        ["portfolio.paper_accounts.account_id"],
        name="fk_portfolio_position_events_account_id_paper_accounts",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["position_id"],
        ["portfolio.positions.position_id"],
        name="fk_portfolio_position_events_position_id_positions",
        ondelete="SET NULL",
    ),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_portfolio_position_events_recommendation_id_recommendations",
        ondelete="SET NULL",
    ),
    PrimaryKeyConstraint(*POSITION_EVENTS_PRIMARY_KEY, name="pk_portfolio_position_events"),
    CheckConstraint(
        "action in ('ENTER', 'HOLD', 'ADD', 'STOP_MOVE', 'TRIM', 'EXIT', 'MISSED')",
        name="position_events_action_valid",
    ),
    CheckConstraint("quantity is null or quantity >= 0", name="position_events_quantity_non_negative"),
    CheckConstraint("price is null or price > 0", name="position_events_price_positive"),
    CheckConstraint(
        "risk_fraction_nav is null or risk_fraction_nav >= 0",
        name="position_events_risk_fraction_nav_non_negative",
    ),
    comment="Chronological paper position events supporting full lifecycle replay.",
)
Index("ix_portfolio_position_events_account_time", position_events.c.account_id, position_events.c.event_time)
Index("ix_portfolio_position_events_position_time", position_events.c.position_id, position_events.c.event_time)

completed_trades = Table(
    "completed_trades",
    portfolio_metadata,
    Column("completed_trade_id", BigInteger, Identity(always=True), nullable=False),
    Column("position_id", BigInteger, nullable=False),
    Column("account_id", BigInteger, nullable=False),
    Column("symbol", String(length=32), nullable=False),
    Column("direction", String(length=16), nullable=False),
    Column("opened_at", DateTime(timezone=True), nullable=False),
    Column("closed_at", DateTime(timezone=True), nullable=False),
    Column("entry_notional", Numeric(precision=38, scale=18), nullable=False),
    Column("exit_notional", Numeric(precision=38, scale=18), nullable=False),
    Column("gross_pnl", Numeric(precision=38, scale=18), nullable=False),
    Column("fees", Numeric(precision=38, scale=18), nullable=False),
    Column("funding", Numeric(precision=38, scale=18), nullable=False),
    Column("realized_pnl", Numeric(precision=38, scale=18), nullable=False),
    Column("initial_risk", Numeric(precision=38, scale=18), nullable=False),
    Column("realized_r", Numeric(precision=18, scale=8), nullable=True),
    Column("mfe", Numeric(precision=38, scale=18), nullable=True),
    Column("mae", Numeric(precision=38, scale=18), nullable=True),
    Column("mfe_r", Numeric(precision=18, scale=8), nullable=True),
    Column("mae_r", Numeric(precision=18, scale=8), nullable=True),
    Column("holding_days", Numeric(precision=38, scale=18), nullable=False),
    Column("maximum_quantity", Numeric(precision=38, scale=18), nullable=False),
    Column("maximum_entry_notional", Numeric(precision=38, scale=18), nullable=False),
    Column("add_count", BigInteger, nullable=False),
    Column("trim_count", BigInteger, nullable=False),
    Column("exit_reason", String(length=255), nullable=False),
    Column("initial_stop_source_id", String(length=255), nullable=False),
    Column("exit_reason_source_id", String(length=255), nullable=False),
    Column("accounting_evidence_digest", String(length=64), nullable=False),
    Column("accounting_policy_version", String(length=64), nullable=False),
    Column("r_multiple_convention", String(length=64), nullable=False),
    Column("funding_convention", String(length=64), nullable=False),
    Column("excursion_convention", String(length=64), nullable=False),
    Column("maximum_size_convention", String(length=64), nullable=False),
    Column("config_version", String(length=64), nullable=False),
    Column("accounting_record", JSON, nullable=False),
    Column("max_risk_fraction_nav", Numeric(precision=12, scale=8), nullable=True),
    Column("recommendation_id", BigInteger, nullable=True),
    Column("strategy_version", String(length=64), nullable=False),
    Column("parameter_set_id", String(length=64), nullable=False),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_pf_completed_trades_recommendation",
        ondelete="SET NULL",
    ),
    ForeignKeyConstraint(
        ["position_id"],
        ["portfolio.positions.position_id"],
        name="fk_portfolio_completed_trades_position_id_positions",
        ondelete="RESTRICT",
    ),
    ForeignKeyConstraint(
        ["account_id"],
        ["portfolio.paper_accounts.account_id"],
        name="fk_portfolio_completed_trades_account_id_paper_accounts",
        ondelete="RESTRICT",
    ),
    PrimaryKeyConstraint(*COMPLETED_TRADES_PRIMARY_KEY, name="pk_portfolio_completed_trades"),
    UniqueConstraint("position_id", name="uq_portfolio_completed_trades_position_id"),
    CheckConstraint("direction in ('long', 'short')", name="completed_trades_direction_valid"),
    CheckConstraint("closed_at >= opened_at", name="completed_trades_time_order"),
    CheckConstraint("entry_notional >= 0", name="completed_trades_entry_notional_non_negative"),
    CheckConstraint("exit_notional >= 0", name="completed_trades_exit_notional_non_negative"),
    CheckConstraint("fees >= 0", name="completed_trades_fees_non_negative"),
    CheckConstraint("initial_risk >= 0", name="completed_trades_initial_risk_non_negative"),
    CheckConstraint("holding_days >= 0", name="completed_trades_holding_days_non_negative"),
    CheckConstraint("maximum_quantity > 0", name="completed_trades_maximum_quantity_positive"),
    CheckConstraint(
        "maximum_entry_notional > 0",
        name="completed_trades_maximum_entry_notional_positive",
    ),
    CheckConstraint("add_count >= 0", name="completed_trades_add_count_non_negative"),
    CheckConstraint("trim_count >= 0", name="completed_trades_trim_count_non_negative"),
    CheckConstraint(
        "max_risk_fraction_nav is null or max_risk_fraction_nav >= 0",
        name="completed_trades_max_risk_fraction_nav_non_negative",
    ),
    comment="Finalized paper trade outcomes for research and reporting.",
)
Index("ix_portfolio_completed_trades_account_closed_at", completed_trades.c.account_id, completed_trades.c.closed_at)

manual_trade_journal = Table(
    "manual_trade_journal",
    portfolio_metadata,
    Column("manual_trade_id", BigInteger, Identity(always=True), nullable=False),
    Column("recommendation_id", BigInteger, nullable=True),
    Column("symbol", String(length=32), nullable=False),
    Column("direction", String(length=16), nullable=False),
    Column("journaled_at", DateTime(timezone=True), nullable=False),
    Column("manual_decision", String(length=32), nullable=False),
    Column("override_reason", Text, nullable=True),
    Column("actual_entry_time", DateTime(timezone=True), nullable=True),
    Column("actual_entry_price", Numeric(precision=38, scale=18), nullable=True),
    Column("actual_size", Numeric(precision=38, scale=18), nullable=True),
    Column("actual_size_unit", String(length=16), nullable=True),
    Column("actual_stop", Numeric(precision=38, scale=18), nullable=True),
    Column("actual_exit_time", DateTime(timezone=True), nullable=True),
    Column("actual_exit_price", Numeric(precision=38, scale=18), nullable=True),
    Column("notes", Text, nullable=True),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_portfolio_manual_trade_recommendation",
        ondelete="RESTRICT",
    ),
    PrimaryKeyConstraint(*MANUAL_TRADE_JOURNAL_PRIMARY_KEY, name="pk_portfolio_manual_trade_journal"),
    CheckConstraint("direction in ('long', 'short', 'flat')", name="manual_trade_journal_direction_valid"),
    CheckConstraint(
        "manual_decision in ('FOLLOWED', 'OVERRIDDEN', 'SKIPPED', 'MANUAL_ONLY')",
        name="manual_trade_journal_decision_valid",
    ),
    CheckConstraint(
        "manual_decision = 'MANUAL_ONLY' or recommendation_id is not null",
        name="manual_trade_journal_recommendation_required",
    ),
    CheckConstraint(
        "manual_decision != 'OVERRIDDEN' or override_reason is not null",
        name="manual_trade_journal_override_reason_required",
    ),
    CheckConstraint(
        "actual_entry_price is null or actual_entry_price > 0",
        name="manual_trade_journal_actual_entry_price_positive",
    ),
    CheckConstraint(
        "actual_size is null or actual_size >= 0",
        name="manual_trade_journal_actual_size_non_negative",
    ),
    CheckConstraint(
        "actual_stop is null or actual_stop > 0",
        name="manual_trade_journal_actual_stop_positive",
    ),
    CheckConstraint(
        "actual_exit_price is null or actual_exit_price > 0",
        name="manual_trade_journal_actual_exit_price_positive",
    ),
    CheckConstraint(
        "actual_entry_time is null or actual_exit_time is null or actual_exit_time >= actual_entry_time",
        name="manual_trade_journal_actual_time_order",
    ),
    comment="Manual execution journal linked to model recommendations for suggested-versus-actual comparison.",
)
Index("ix_portfolio_manual_trade_journal_recommendation", manual_trade_journal.c.recommendation_id)
Index("ix_portfolio_manual_trade_journal_symbol_time", manual_trade_journal.c.symbol, manual_trade_journal.c.journaled_at)

# BTC-200: a recommendation decision is a record about an advisory, not about a
# trade. It exists for advisories that were never traded (REJECTED, MISSED), so
# it cannot live in the BTC-017 execution journal, whose every column describes
# a fill. The advisory body is stored verbatim because the decision is only
# auditable against the exact document the operator was shown.
recommendation_decisions = Table(
    "recommendation_decisions",
    portfolio_metadata,
    Column("decision_id", BigInteger, Identity(always=True), nullable=False),
    Column("recommendation_id", BigInteger, nullable=False),
    Column("strategy_version", String(length=64), nullable=False),
    Column("parameter_set_id", String(length=64), nullable=False),
    Column("config_version", String(length=64), nullable=False),
    Column("evaluation_time", DateTime(timezone=True), nullable=False),
    Column("decided_at", DateTime(timezone=True), nullable=False),
    Column("decision", String(length=16), nullable=False),
    Column("advised_action", String(length=16), nullable=False),
    Column("modified_fields", JSON, nullable=False),
    Column("discretionary_reason_policy_version", String(length=64), nullable=False),
    Column("discretionary_reason_codes", JSON, nullable=False),
    Column("note", Text, nullable=True),
    Column("advisory_schema_version", String(length=64), nullable=False),
    Column("advisory_body", Text, nullable=False),
    Column("advisory_digest", String(length=64), nullable=False),
    Column("journal_policy_version", String(length=64), nullable=False),
    Column("reason_codes", JSON, nullable=False),
    ForeignKeyConstraint(
        ["recommendation_id"],
        ["signals.recommendations.recommendation_id"],
        name="fk_portfolio_recommendation_decision_recommendation",
        ondelete="RESTRICT",
    ),
    PrimaryKeyConstraint(
        *RECOMMENDATION_DECISIONS_PRIMARY_KEY,
        name="pk_portfolio_recommendation_decisions",
    ),
    UniqueConstraint(
        "recommendation_id",
        name="uq_portfolio_recommendation_decisions_recommendation",
    ),
    CheckConstraint(
        "decision in ('APPROVED', 'REJECTED', 'MODIFIED', 'MISSED')",
        name="decision_valid",
    ),
    CheckConstraint(
        "advised_action in ('NO_TRADE', 'WATCH', 'ENTER', 'HOLD', 'ADD', 'TRIM', 'EXIT')",
        name="advised_action_valid",
    ),
    CheckConstraint(
        "decided_at >= evaluation_time",
        name="decided_after_evaluation",
    ),
    CheckConstraint(
        "length(btrim(strategy_version)) > 0",
        name="strategy_version_not_blank",
    ),
    CheckConstraint(
        "length(btrim(parameter_set_id)) > 0",
        name="parameter_set_id_not_blank",
    ),
    CheckConstraint(
        "length(btrim(config_version)) > 0",
        name="config_version_not_blank",
    ),
    CheckConstraint(
        "length(btrim(discretionary_reason_policy_version)) > 0",
        name="discretionary_reason_policy_version_not_blank",
    ),
    CheckConstraint(
        "length(advisory_digest) = 64",
        name="advisory_digest_sha256",
    ),
    comment="Operator decisions recorded against model recommendations.",
)
Index("ix_portfolio_recommendation_decisions_decision_time", recommendation_decisions.c.decision, recommendation_decisions.c.decided_at)
Index("ix_portfolio_recommendation_decisions_strategy_identity", recommendation_decisions.c.strategy_version, recommendation_decisions.c.parameter_set_id)
