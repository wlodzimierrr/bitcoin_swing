"""Complete paper trade lifecycle persistence (BTC-166).

BTC-160 through BTC-165 each know how to shape their own database row. What none
of them can know alone is whether the *set* of rows for one trade is complete
and consistently attributed, which is what this module assembles and checks.

The requirement is that every event is linked to ``recommendation_id``,
``strategy_version`` and ``parameter_set_id``. Only the first of those had a
column. Strategy version and parameter set had nowhere to live except a JSON
note, and ``paper_orders`` has no note column at all, so an order row carried no
strategy identity whatsoever. Migration ``0020`` adds real, indexed columns to
``paper_orders``, ``position_events`` and ``completed_trades``; a run's
provenance has to be queryable, or two parameter sets are indistinguishable in
the record and no backtest-versus-paper comparison means anything.

``recommendation_id`` stays nullable in the schema on purpose: its foreign keys
are ``ON DELETE SET NULL``, so a NOT NULL column would make deleting a
recommendation fail rather than sever the link. The requirement is enforced
here instead, in the layer that knows an event is model-driven.

Stamping is not trusted to a convention. ``verify_lifecycle_rows`` re-checks
every row for the full triple and for column names the target table actually
has, so a builder that drifts from the schema fails here rather than at the
first INSERT.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from btc_predictor.config.strategy import StrategyConfig
from btc_predictor.db.portfolio import (
    LIFECYCLE_PROVENANCE_COLUMNS,
    completed_trades,
    paper_orders,
    position_events,
)
from btc_predictor.portfolio.state_machine import position_event_records


PAPER_LIFECYCLE_PERSISTENCE_FEATURE_ID = "PAPER_LIFECYCLE_PERSISTENCE"
PAPER_LIFECYCLE_PERSISTENCE_POLICY_VERSION = "PAPER_LIFECYCLE_PERSISTENCE_V1"

ORDERS_TABLE = "paper_orders"
EVENTS_TABLE = "position_events"
COMPLETED_TRADES_TABLE = "completed_trades"

_TABLE_COLUMNS = {
    ORDERS_TABLE: frozenset(column.name for column in paper_orders.columns),
    EVENTS_TABLE: frozenset(column.name for column in position_events.columns),
    COMPLETED_TRADES_TABLE: frozenset(
        column.name for column in completed_trades.columns
    ),
}

LIFECYCLE_PERSISTENCE_REASON_CODES = (
    "LIFECYCLE_PERSISTENCE_COMPLETE",
    "LIFECYCLE_PERSISTENCE_TRADE_NOT_CLOSED",
    "LIFECYCLE_PERSISTENCE_NO_ORDERS",
    "LIFECYCLE_PERSISTENCE_NO_EVENTS",
)


@dataclass(frozen=True)
class LifecycleProvenance:
    """The identity every persisted lifecycle event must carry."""

    recommendation_id: int
    strategy_version: str
    parameter_set_id: str

    @classmethod
    def from_config(
        cls,
        strategy_config: StrategyConfig,
        *,
        recommendation_id: int,
    ) -> LifecycleProvenance:
        """Take the strategy identity from the config that produced the trade."""

        if not isinstance(strategy_config, StrategyConfig):
            raise TypeError("strategy_config must be a StrategyConfig")
        metadata = strategy_config.run_metadata()
        return cls(
            recommendation_id=recommendation_id,
            strategy_version=metadata["strategy_version"],
            parameter_set_id=metadata["parameter_set_id"],
        )

    def as_columns(self) -> dict[str, Any]:
        recommendation_id = self.recommendation_id
        if (
            isinstance(recommendation_id, bool)
            or not isinstance(recommendation_id, int)
            or recommendation_id < 1
        ):
            raise ValueError("recommendation_id must be a positive integer")
        return {
            "recommendation_id": recommendation_id,
            "strategy_version": _identity(self.strategy_version, "strategy_version"),
            "parameter_set_id": _identity(self.parameter_set_id, "parameter_set_id"),
        }

    def as_record(self) -> dict[str, Any]:
        return self.as_columns()


@dataclass(frozen=True)
class PaperTradeLifecycleRows:
    """Every database row for one paper trade, uniformly attributed."""

    feature_id: str
    policy_version: str
    provenance: LifecycleProvenance
    account_id: int
    position_id: int
    orders: tuple[dict[str, Any], ...]
    events: tuple[dict[str, Any], ...]
    completed_trade: dict[str, Any] | None
    complete: bool
    reason_codes: tuple[str, ...]

    @property
    def all_rows(self) -> tuple[tuple[str, dict[str, Any]], ...]:
        rows: list[tuple[str, dict[str, Any]]] = []
        rows.extend((ORDERS_TABLE, row) for row in self.orders)
        rows.extend((EVENTS_TABLE, row) for row in self.events)
        if self.completed_trade is not None:
            rows.append((COMPLETED_TRADES_TABLE, self.completed_trade))
        return tuple(rows)

    def as_record(self) -> dict[str, Any]:
        verify_lifecycle_rows(self)
        return {
            "feature_id": self.feature_id,
            "policy_version": self.policy_version,
            "provenance": self.provenance.as_record(),
            "account_id": self.account_id,
            "position_id": self.position_id,
            "row_counts": {
                ORDERS_TABLE: len(self.orders),
                EVENTS_TABLE: len(self.events),
                COMPLETED_TRADES_TABLE: 0 if self.completed_trade is None else 1,
            },
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def build_paper_trade_lifecycle_rows(
    *,
    provenance: LifecycleProvenance,
    account_id: int,
    position_id: int,
    executions: Sequence[Any] = (),
    lifecycle: Any | None = None,
    accounting: Any | None = None,
) -> PaperTradeLifecycleRows:
    """Assemble every row for one trade and stamp each with its provenance.

    ``executions`` are BTC-161 through BTC-164 results, ``lifecycle`` a BTC-150
    position, and ``accounting`` a BTC-165 closed trade. Each contributes the
    rows it already knows how to shape; this adds the identity none of them
    carries and refuses a set that is not uniformly attributed.
    """

    if not isinstance(provenance, LifecycleProvenance):
        raise TypeError("provenance must be a LifecycleProvenance")
    account = _identifier(account_id, "account_id")
    position = _identifier(position_id, "position_id")
    columns = provenance.as_columns()

    orders = tuple(
        _stamped(
            _order_record(execution, account_id=account, position_id=position),
            columns,
            table=ORDERS_TABLE,
        )
        for execution in executions
    )
    events = (
        ()
        if lifecycle is None
        else tuple(
            _stamped(
                {**row, "account_id": account, "position_id": position},
                columns,
                table=EVENTS_TABLE,
            )
            for row in position_event_records(lifecycle)
        )
    )
    completed_trade = (
        None
        if accounting is None
        else _stamped(
            _accounting_record(
                accounting,
                provenance=provenance,
                account_id=account,
                position_id=position,
            ),
            columns,
            table=COMPLETED_TRADES_TABLE,
        )
    )

    reasons: list[str] = []
    if not orders:
        reasons.append("LIFECYCLE_PERSISTENCE_NO_ORDERS")
    if not events:
        reasons.append("LIFECYCLE_PERSISTENCE_NO_EVENTS")
    if completed_trade is None:
        reasons.append("LIFECYCLE_PERSISTENCE_TRADE_NOT_CLOSED")
    complete = not reasons
    if complete:
        reasons.append("LIFECYCLE_PERSISTENCE_COMPLETE")

    rows = PaperTradeLifecycleRows(
        feature_id=PAPER_LIFECYCLE_PERSISTENCE_FEATURE_ID,
        policy_version=PAPER_LIFECYCLE_PERSISTENCE_POLICY_VERSION,
        provenance=provenance,
        account_id=account,
        position_id=position,
        orders=orders,
        events=events,
        completed_trade=completed_trade,
        complete=complete,
        reason_codes=tuple(reasons),
    )
    verify_lifecycle_rows(rows)
    return rows


def verify_lifecycle_rows(rows: PaperTradeLifecycleRows) -> None:
    """Raise unless every row is fully attributed and schema-compatible."""

    if not isinstance(rows, PaperTradeLifecycleRows):
        raise TypeError("rows must be a PaperTradeLifecycleRows")
    expected = rows.provenance.as_columns()
    for table, row in rows.all_rows:
        unknown = set(row) - _TABLE_COLUMNS[table]
        if unknown:
            # A builder that drifted from the schema fails here rather than at
            # the first INSERT.
            raise ValueError(
                f"{table} row carries columns the table does not have: "
                f"{sorted(unknown)}",
            )
        for column in LIFECYCLE_PROVENANCE_COLUMNS:
            if row.get(column) != expected[column]:
                raise ValueError(
                    f"{table} row is not attributed to {column}={expected[column]!r}",
                )
        if row.get("account_id") != rows.account_id:
            raise ValueError(f"{table} row does not belong to the account")
        if row.get("position_id") not in (None, rows.position_id):
            raise ValueError(f"{table} row does not belong to the position")


def _order_record(
    execution: Any,
    *,
    account_id: int,
    position_id: int,
) -> dict[str, Any]:
    builder = getattr(execution, "as_order_record", None)
    if not callable(builder):
        raise TypeError("executions must expose as_order_record()")
    return builder(account_id=account_id, position_id=position_id)


def _accounting_record(
    accounting: Any,
    *,
    provenance: LifecycleProvenance,
    account_id: int,
    position_id: int,
) -> dict[str, Any]:
    metadata = getattr(accounting, "config_metadata", None)
    if not isinstance(metadata, Mapping):
        raise TypeError("accounting must expose config_metadata")
    expected = {
        "strategy_version": provenance.strategy_version,
        "parameter_set_id": provenance.parameter_set_id,
    }
    for key, value in expected.items():
        if metadata.get(key) != value:
            raise ValueError(f"accounting {key} does not match lifecycle provenance")
    builder = getattr(accounting, "as_completed_trade_record", None)
    if not callable(builder):
        raise TypeError("accounting must expose as_completed_trade_record()")
    return builder(account_id=account_id, position_id=position_id)


def _stamped(
    row: Mapping[str, Any],
    columns: Mapping[str, Any],
    *,
    table: str,
) -> dict[str, Any]:
    stamped = {**dict(row), **dict(columns)}
    unknown = set(stamped) - _TABLE_COLUMNS[table]
    if unknown:
        raise ValueError(
            f"{table} row carries columns the table does not have: {sorted(unknown)}",
        )
    return stamped


def _identifier(value: Any, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ValueError(f"{name} must be a positive integer")
    return value


def _identity(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string")
    return value


__all__ = [
    "COMPLETED_TRADES_TABLE",
    "EVENTS_TABLE",
    "LIFECYCLE_PERSISTENCE_REASON_CODES",
    "ORDERS_TABLE",
    "PAPER_LIFECYCLE_PERSISTENCE_FEATURE_ID",
    "PAPER_LIFECYCLE_PERSISTENCE_POLICY_VERSION",
    "LifecycleProvenance",
    "PaperTradeLifecycleRows",
    "build_paper_trade_lifecycle_rows",
    "verify_lifecycle_rows",
]
