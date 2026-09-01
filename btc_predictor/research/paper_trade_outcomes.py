"""Paper-trade outcome dataset (BTC-191).

Learning from paper trading needs the state that justified an entry sitting in
the same row as what the trade finally did.  This module joins, one immutable
row per completed paper trade:

``entry_features``
    the BTC-048 point-in-time feature cells as of the trade's entry decision
    timestamp, so only information available when the entry was decided
    describes it;
``outcomes``
    the BTC-165 accounting figures for the finished trade, read from the
    accounting record rather than recomputed here; and
``recommendation_id`` / ``strategy_version`` / ``parameter_set_id``
    the BTC-166 lifecycle provenance triple, so a row can be traced back to the
    run that produced it and two parameter sets never merge into one dataset.

Only closed trades enter: an open position has no final outcome, and joining
its running numbers would silently turn a partial result into a final one.
Nothing is zero-filled -- an absent feature keeps an explicit status and its
provenance, and an outcome BTC-165 could not measure keeps the BTC-165 reason
code that explains why.

The dataset is research evidence only.  It has no strategy or configuration
mutation path and records BTC-193 as the required promotion boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any

import numpy as np
from numpy.typing import NDArray

from btc_predictor.data import require_utc_datetime
from btc_predictor.portfolio.accounting import (
    EXCURSION_CONVENTION,
    FUNDING_CONVENTION,
    MAXIMUM_SIZE_CONVENTION,
    PAPER_TRADE_ACCOUNTING_POLICY_VERSION,
    R_MULTIPLE_CONVENTION,
    TRADE_DIRECTIONS,
    PaperTradeAccounting,
)
from btc_predictor.portfolio.lifecycle_persistence import LifecycleProvenance
from btc_predictor.quant.arrays import FloatArray
from btc_predictor.research.decision_state import (
    DECISION_STATE_DECISIONS,
    DECISION_STATE_REGIMES,
    DECISION_STATE_SETUPS,
)
from btc_predictor.research.feature_matrix import (
    INITIAL_FEATURE_NAMES,
    PointInTimeFeatureMatrix,
)
from btc_predictor.signals.data_quality import RecommendationReasonCode


PAPER_TRADE_OUTCOME_FEATURE_ID = "PAPER_TRADE_OUTCOME_DATASET"
PAPER_TRADE_OUTCOME_POLICY_VERSION = "PAPER_TRADE_OUTCOME_DATASET_V1"
PAPER_TRADE_OUTCOME_JOIN_POLICY_VERSION = "ENTRY_STATE_TO_FINAL_OUTCOME_JOIN_V1"
PAPER_TRADE_OUTCOME_ENTRY_STATE_POLICY_VERSION = (
    "ENTRY_STATE_AS_OF_ENTRY_DECISION_TIMESTAMP_V1"
)
PAPER_TRADE_OUTCOME_FINALITY_POLICY_VERSION = "CLOSED_TRADES_ONLY_BY_EXTRACTION_TIME_V1"
PAPER_TRADE_OUTCOME_PROVENANCE_POLICY_VERSION = "ONE_STRATEGY_PROVENANCE_PER_DATASET_V1"
PAPER_TRADE_OUTCOME_MISSING_VALUE_POLICY_VERSION = "EXPLICIT_STATUS_NO_ZERO_FILL_V1"
PAPER_TRADE_OUTCOME_PROMOTION_POLICY_VERSION = "BTC_193_REQUIRED_V1"
PAPER_TRADE_OUTCOME_PRODUCTION_STATUS = "RESEARCH_ONLY_NOT_PRODUCTION"
PAPER_TRADE_OUTCOME_PROMOTION_TICKET = "BTC-193"

# The research categorical vocabularies stay owned by BTC-190, so a paper trade
# and the decision date that produced it carry identical labels.
PAPER_TRADE_DECISIONS = DECISION_STATE_DECISIONS
PAPER_TRADE_SETUPS = DECISION_STATE_SETUPS
PAPER_TRADE_REGIMES = DECISION_STATE_REGIMES

ENTRY_FEATURE_AVAILABLE = "AVAILABLE"
ENTRY_FEATURE_MISSING_VALUE = "MISSING_VALUE"
ENTRY_FEATURE_NOT_OBSERVED = "NOT_OBSERVED"
ENTRY_FEATURE_STATUSES = (
    ENTRY_FEATURE_AVAILABLE,
    ENTRY_FEATURE_MISSING_VALUE,
    ENTRY_FEATURE_NOT_OBSERVED,
)

TRADE_OUTCOME_AVAILABLE = "AVAILABLE"
TRADE_OUTCOME_NOT_MEASURED = "NOT_MEASURED"
TRADE_OUTCOME_STATUSES = (TRADE_OUTCOME_AVAILABLE, TRADE_OUTCOME_NOT_MEASURED)

# Outcome names are BTC-165 field names, so the dataset never renames or
# reinterprets an accounting output.
PAPER_TRADE_OUTCOME_NAMES = (
    "gross_pnl",
    "fees",
    "funding",
    "net_pnl",
    "initial_risk",
    "r_multiple",
    "maximum_favourable_excursion",
    "maximum_adverse_excursion",
    "mfe_r",
    "mae_r",
    "holding_days",
    "entry_notional",
    "exit_notional",
    "maximum_quantity",
    "maximum_entry_notional",
    "add_count",
    "trim_count",
)
_EXCURSION_OUTCOME_NAMES = (
    "maximum_favourable_excursion",
    "maximum_adverse_excursion",
    "mfe_r",
    "mae_r",
)
_NO_EXCURSION_BARS_REASON = "TRADE_ACCOUNTING_NO_EXCURSION_BARS"
_R_UNDEFINED_REASON = "TRADE_ACCOUNTING_R_UNDEFINED"
_POSITION_STILL_OPEN_REASON = "TRADE_ACCOUNTING_POSITION_STILL_OPEN"

PAPER_TRADE_OUTCOME_REASON_CODES = (
    "PAPER_TRADE_OUTCOME_ONE_ROW_PER_COMPLETED_TRADE",
    "PAPER_TRADE_OUTCOME_ENTRY_STATE_POINT_IN_TIME",
    "PAPER_TRADE_OUTCOME_FINAL_OUTCOMES_FROM_BTC_165",
    "PAPER_TRADE_OUTCOME_LIFECYCLE_PROVENANCE_PERSISTED",
    "PAPER_TRADE_OUTCOME_UNMEASURED_OUTCOMES_EXPLAINED",
    "PAPER_TRADE_OUTCOME_MISSING_VALUES_EXPLICIT",
    "PAPER_TRADE_OUTCOME_RESEARCH_ONLY",
    "PAPER_TRADE_OUTCOME_BTC_193_PROMOTION_REQUIRED",
    "PAPER_TRADE_OUTCOME_COMPLETE",
)


class PaperTradeOutcomeError(ValueError):
    """Raised when outcome-dataset inputs violate the BTC-191 contract."""


@dataclass(frozen=True)
class PaperTradeOutcomeDefinition:
    """Versioned column contract for one paper-trade outcome dataset."""

    version: str = PAPER_TRADE_OUTCOME_POLICY_VERSION
    entry_feature_names: tuple[str, ...] = INITIAL_FEATURE_NAMES
    outcome_names: tuple[str, ...] = PAPER_TRADE_OUTCOME_NAMES
    join_policy_version: str = PAPER_TRADE_OUTCOME_JOIN_POLICY_VERSION
    entry_state_policy_version: str = PAPER_TRADE_OUTCOME_ENTRY_STATE_POLICY_VERSION
    finality_policy_version: str = PAPER_TRADE_OUTCOME_FINALITY_POLICY_VERSION
    provenance_policy_version: str = PAPER_TRADE_OUTCOME_PROVENANCE_POLICY_VERSION
    missing_value_policy_version: str = PAPER_TRADE_OUTCOME_MISSING_VALUE_POLICY_VERSION
    promotion_policy_version: str = PAPER_TRADE_OUTCOME_PROMOTION_POLICY_VERSION

    def __post_init__(self) -> None:
        expected = {
            "version": PAPER_TRADE_OUTCOME_POLICY_VERSION,
            "join_policy_version": PAPER_TRADE_OUTCOME_JOIN_POLICY_VERSION,
            "entry_state_policy_version": (
                PAPER_TRADE_OUTCOME_ENTRY_STATE_POLICY_VERSION
            ),
            "finality_policy_version": PAPER_TRADE_OUTCOME_FINALITY_POLICY_VERSION,
            "provenance_policy_version": PAPER_TRADE_OUTCOME_PROVENANCE_POLICY_VERSION,
            "missing_value_policy_version": (
                PAPER_TRADE_OUTCOME_MISSING_VALUE_POLICY_VERSION
            ),
            "promotion_policy_version": PAPER_TRADE_OUTCOME_PROMOTION_POLICY_VERSION,
        }
        for field_name, value in expected.items():
            if getattr(self, field_name) != value:
                raise PaperTradeOutcomeError(f"{field_name} must be {value!r}")
        object.__setattr__(
            self,
            "entry_feature_names",
            _validate_names(self.entry_feature_names, field_name="entry_feature_names"),
        )
        outcome_names = _validate_names(
            self.outcome_names, field_name="outcome_names"
        )
        unknown = tuple(
            name for name in outcome_names if name not in PAPER_TRADE_OUTCOME_NAMES
        )
        if unknown:
            raise PaperTradeOutcomeError(
                "outcome_names must be BTC-165 accounting outputs; unknown: "
                + ", ".join(unknown)
            )
        object.__setattr__(self, "outcome_names", outcome_names)

    @property
    def fingerprint(self) -> str:
        return _digest(_definition_payload(self))

    def as_record(self) -> dict[str, Any]:
        return {**_definition_payload(self), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class PaperTradeEntry:
    """The recorded entry state of one paper trade, before its outcome."""

    trade_reference: str
    entry_decision_timestamp: datetime
    data_available_at: datetime
    symbol: str
    direction: str
    decision: str
    setup: str
    regime: str
    provenance: LifecycleProvenance
    source_id: str
    reason_codes: tuple[RecommendationReasonCode, ...] = ()

    def __post_init__(self) -> None:
        entry_decision_timestamp = require_utc_datetime(
            self.entry_decision_timestamp, "entry_decision_timestamp"
        )
        data_available_at = require_utc_datetime(
            self.data_available_at, "data_available_at"
        )
        if data_available_at > entry_decision_timestamp:
            raise PaperTradeOutcomeError(
                "data_available_at must be <= entry_decision_timestamp"
            )
        _non_empty(self.trade_reference, "trade_reference")
        _non_empty(self.symbol, "symbol")
        _require_member(self.direction, TRADE_DIRECTIONS, "direction")
        _require_member(self.decision, PAPER_TRADE_DECISIONS, "decision")
        _require_member(self.setup, PAPER_TRADE_SETUPS, "setup")
        _require_member(self.regime, PAPER_TRADE_REGIMES, "regime")
        _non_empty(self.source_id, "source_id")
        if not isinstance(self.provenance, LifecycleProvenance):
            raise PaperTradeOutcomeError("provenance must be a LifecycleProvenance")
        self.provenance.as_columns()
        object.__setattr__(
            self, "entry_decision_timestamp", entry_decision_timestamp
        )
        object.__setattr__(self, "data_available_at", data_available_at)
        object.__setattr__(
            self, "reason_codes", _reason_codes(self.reason_codes)
        )


@dataclass(frozen=True)
class EntryStateFeature:
    """One persisted entry-state feature cell and its provenance."""

    feature_name: str
    status: str
    value: float | None
    observation_time: datetime | None
    available_at: datetime | None
    source_id: str | None
    revision: int | None

    def __post_init__(self) -> None:
        _non_empty(self.feature_name, "feature_name")
        _require_member(self.status, ENTRY_FEATURE_STATUSES, "status")
        _validate_float(self.value, "entry feature value")
        observed = self.status != ENTRY_FEATURE_NOT_OBSERVED
        _validate_cell_provenance(
            observed=observed,
            observation_time=self.observation_time,
            available_at=self.available_at,
            source_id=self.source_id,
            revision=self.revision,
        )
        if (self.status == ENTRY_FEATURE_AVAILABLE) != (self.value is not None):
            raise PaperTradeOutcomeError(
                "entry feature value must be present exactly when the status is "
                "AVAILABLE"
            )

    def as_record(self) -> dict[str, Any]:
        return {
            "feature_name": self.feature_name,
            "status": self.status,
            "value": self.value,
            "observation_time": _isoformat(self.observation_time),
            "available_at": _isoformat(self.available_at),
            "source_id": self.source_id,
            "revision": self.revision,
        }


@dataclass(frozen=True)
class PaperTradeOutcome:
    """One persisted BTC-165 outcome cell for a completed trade."""

    outcome_name: str
    status: str
    value: Decimal | None
    reason_code: str | None

    def __post_init__(self) -> None:
        _require_member(
            self.outcome_name, PAPER_TRADE_OUTCOME_NAMES, "outcome_name"
        )
        _require_member(self.status, TRADE_OUTCOME_STATUSES, "status")
        if self.status == TRADE_OUTCOME_AVAILABLE:
            if not isinstance(self.value, Decimal):
                raise PaperTradeOutcomeError(
                    "an available outcome must carry a Decimal value"
                )
            if not self.value.is_finite():
                raise PaperTradeOutcomeError("outcome value must be finite")
            if self.reason_code is not None:
                raise PaperTradeOutcomeError(
                    "an available outcome must not carry a missing-value reason code"
                )
            return
        if self.value is not None:
            raise PaperTradeOutcomeError(
                "an unmeasured outcome must not carry a value"
            )
        _non_empty(self.reason_code, "reason_code")

    def as_record(self) -> dict[str, Any]:
        return {
            "outcome_name": self.outcome_name,
            "status": self.status,
            "value": None if self.value is None else str(self.value),
            "reason_code": self.reason_code,
        }


@dataclass(frozen=True)
class PaperTradeOutcomeRow:
    """One completed paper trade: its entry state and its final outcome."""

    trade_reference: str
    entry_decision_timestamp: datetime
    data_available_at: datetime
    opened_at: datetime
    closed_at: datetime
    symbol: str
    direction: str
    decision: str
    setup: str
    regime: str
    recommendation_id: int
    strategy_version: str
    parameter_set_id: str
    source_id: str
    exit_reason: str
    exit_reason_source_id: str
    initial_stop_source_id: str
    accounting_evidence_digest: str
    entry_features: tuple[EntryStateFeature, ...]
    outcomes: tuple[PaperTradeOutcome, ...]
    entry_reason_codes: tuple[RecommendationReasonCode, ...]
    accounting_reason_codes: tuple[str, ...]

    def __post_init__(self) -> None:
        entry_decision_timestamp = require_utc_datetime(
            self.entry_decision_timestamp, "entry_decision_timestamp"
        )
        data_available_at = require_utc_datetime(
            self.data_available_at, "data_available_at"
        )
        opened_at = require_utc_datetime(self.opened_at, "opened_at")
        closed_at = require_utc_datetime(self.closed_at, "closed_at")
        if data_available_at > entry_decision_timestamp:
            raise PaperTradeOutcomeError(
                "data_available_at must be <= entry_decision_timestamp"
            )
        if entry_decision_timestamp > opened_at:
            raise PaperTradeOutcomeError(
                "the entry decision must not follow the opening fill"
            )
        if closed_at < opened_at:
            raise PaperTradeOutcomeError("closed_at must be >= opened_at")
        _non_empty(self.trade_reference, "trade_reference")
        _non_empty(self.symbol, "symbol")
        _require_member(self.direction, TRADE_DIRECTIONS, "direction")
        _require_member(self.decision, PAPER_TRADE_DECISIONS, "decision")
        _require_member(self.setup, PAPER_TRADE_SETUPS, "setup")
        _require_member(self.regime, PAPER_TRADE_REGIMES, "regime")
        for field_name in (
            "source_id",
            "strategy_version",
            "parameter_set_id",
            "exit_reason",
            "exit_reason_source_id",
            "initial_stop_source_id",
            "accounting_evidence_digest",
        ):
            _non_empty(getattr(self, field_name), field_name)
        if (
            isinstance(self.recommendation_id, bool)
            or not isinstance(self.recommendation_id, int)
            or self.recommendation_id < 1
        ):
            raise PaperTradeOutcomeError(
                "recommendation_id must be a positive integer"
            )
        entry_features = tuple(self.entry_features)
        outcomes = tuple(self.outcomes)
        if any(not isinstance(item, EntryStateFeature) for item in entry_features):
            raise PaperTradeOutcomeError(
                "entry_features must contain EntryStateFeature values"
            )
        if any(not isinstance(item, PaperTradeOutcome) for item in outcomes):
            raise PaperTradeOutcomeError(
                "outcomes must contain PaperTradeOutcome values"
            )
        _reject_duplicates(
            tuple(item.feature_name for item in entry_features),
            field_name="entry_feature_names",
        )
        _reject_duplicates(
            tuple(item.outcome_name for item in outcomes), field_name="outcome_names"
        )
        for feature in entry_features:
            if feature.available_at is not None and (
                feature.available_at > entry_decision_timestamp
            ):
                raise PaperTradeOutcomeError(
                    "entry-state provenance must not exceed the entry decision "
                    "timestamp"
                )
        accounting_reason_codes = tuple(self.accounting_reason_codes)
        for code in accounting_reason_codes:
            _non_empty(code, "accounting_reason_codes")
        if _POSITION_STILL_OPEN_REASON in accounting_reason_codes:
            raise PaperTradeOutcomeError(
                "an open position has no final outcome; close the trade first"
            )
        for outcome in outcomes:
            if (
                outcome.reason_code is not None
                and outcome.reason_code not in accounting_reason_codes
            ):
                raise PaperTradeOutcomeError(
                    "an unmeasured outcome must cite a BTC-165 reason code the "
                    "accounting actually raised"
                )
        object.__setattr__(
            self, "entry_decision_timestamp", entry_decision_timestamp
        )
        object.__setattr__(self, "data_available_at", data_available_at)
        object.__setattr__(self, "opened_at", opened_at)
        object.__setattr__(self, "closed_at", closed_at)
        object.__setattr__(self, "entry_features", entry_features)
        object.__setattr__(self, "outcomes", outcomes)
        object.__setattr__(
            self, "entry_reason_codes", _reason_codes(self.entry_reason_codes)
        )
        object.__setattr__(
            self, "accounting_reason_codes", accounting_reason_codes
        )

    @property
    def provenance(self) -> LifecycleProvenance:
        return LifecycleProvenance(
            recommendation_id=self.recommendation_id,
            strategy_version=self.strategy_version,
            parameter_set_id=self.parameter_set_id,
        )

    def entry_feature(self, feature_name: str) -> EntryStateFeature:
        for item in self.entry_features:
            if item.feature_name == feature_name:
                return item
        raise KeyError(feature_name)

    def outcome(self, outcome_name: str) -> PaperTradeOutcome:
        for item in self.outcomes:
            if item.outcome_name == outcome_name:
                return item
        raise KeyError(outcome_name)

    def as_record(self) -> dict[str, Any]:
        return {
            "trade_reference": self.trade_reference,
            "entry_decision_timestamp": self.entry_decision_timestamp.isoformat(),
            "data_available_at": self.data_available_at.isoformat(),
            "opened_at": self.opened_at.isoformat(),
            "closed_at": self.closed_at.isoformat(),
            "symbol": self.symbol,
            "direction": self.direction,
            "decision": self.decision,
            "setup": self.setup,
            "regime": self.regime,
            "recommendation_id": self.recommendation_id,
            "strategy_version": self.strategy_version,
            "parameter_set_id": self.parameter_set_id,
            "source_id": self.source_id,
            "exit_reason": self.exit_reason,
            "exit_reason_source_id": self.exit_reason_source_id,
            "initial_stop_source_id": self.initial_stop_source_id,
            "accounting_evidence_digest": self.accounting_evidence_digest,
            "entry_features": [item.as_record() for item in self.entry_features],
            "outcomes": [item.as_record() for item in self.outcomes],
            "entry_reason_codes": [
                _reason_code_record(item) for item in self.entry_reason_codes
            ],
            "accounting_reason_codes": list(self.accounting_reason_codes),
        }


@dataclass(frozen=True)
class PaperTradeOutcomeCoverage:
    """Deterministic census of the joined trades."""

    trade_count: int
    direction_counts: dict[str, int]
    decision_counts: dict[str, int]
    setup_counts: dict[str, int]
    regime_counts: dict[str, int]
    exit_reason_counts: dict[str, int]
    entry_feature_status_counts: dict[str, dict[str, int]]
    outcome_status_counts: dict[str, dict[str, int]]

    def as_record(self) -> dict[str, Any]:
        return {
            "trade_count": self.trade_count,
            "direction_counts": dict(self.direction_counts),
            "decision_counts": dict(self.decision_counts),
            "setup_counts": dict(self.setup_counts),
            "regime_counts": dict(self.regime_counts),
            "exit_reason_counts": dict(self.exit_reason_counts),
            "entry_feature_status_counts": {
                name: dict(counts)
                for name, counts in self.entry_feature_status_counts.items()
            },
            "outcome_status_counts": {
                name: dict(counts)
                for name, counts in self.outcome_status_counts.items()
            },
        }


@dataclass(frozen=True)
class PaperTradeOutcomeDataset:
    """Replayable BTC-191 join of entry state and final paper-trade outcome."""

    dataset_id: str
    evidence_digest: str
    feature_id: str
    policy_version: str
    definition: PaperTradeOutcomeDefinition
    extraction_time: datetime
    config_metadata: dict[str, str]
    accounting_policy_version: str
    r_multiple_convention: str
    funding_convention: str
    excursion_convention: str
    maximum_size_convention: str
    feature_definition: dict[str, Any]
    feature_definition_fingerprint: str
    input_digest: str
    production_status: str
    promotion_ticket: str
    rows: tuple[PaperTradeOutcomeRow, ...]
    coverage: PaperTradeOutcomeCoverage
    reason_codes: tuple[str, ...]

    @property
    def trade_references(self) -> tuple[str, ...]:
        return tuple(row.trade_reference for row in self.rows)

    def row(self, trade_reference: str) -> PaperTradeOutcomeRow:
        for item in self.rows:
            if item.trade_reference == trade_reference:
                return item
        raise KeyError(trade_reference)

    def entry_feature_matrix(self) -> tuple[FloatArray, NDArray[np.bool_]]:
        """Return entry-state values and their missing mask for NumPy users."""

        return _cell_matrix(
            [[item.value for item in row.entry_features] for row in self.rows],
            width=len(self.definition.entry_feature_names),
        )

    def outcome_matrix(self) -> tuple[FloatArray, NDArray[np.bool_]]:
        """Return outcome values and their unmeasured mask for NumPy users."""

        return _cell_matrix(
            [
                [
                    None if item.value is None else float(item.value)
                    for item in row.outcomes
                ]
                for row in self.rows
            ],
            width=len(self.definition.outcome_names),
        )

    def outcome_series(self, outcome_name: str) -> tuple[Decimal | None, ...]:
        """Return one outcome exactly, in row order, without float rounding."""

        if outcome_name not in self.definition.outcome_names:
            raise KeyError(outcome_name)
        return tuple(row.outcome(outcome_name).value for row in self.rows)

    def as_record(self) -> dict[str, Any]:
        """Return a deterministic, JSON-compatible persistence record."""

        _validate_dataset(self)
        payload = _dataset_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise PaperTradeOutcomeError(
                "paper-trade outcome evidence does not match digest"
            )
        return {**payload, "evidence_digest": self.evidence_digest}


def build_paper_trade_outcome_dataset(
    entries: Sequence[PaperTradeEntry],
    accountings: Mapping[str, PaperTradeAccounting],
    features: PointInTimeFeatureMatrix,
    *,
    extraction_time: datetime,
    definition: PaperTradeOutcomeDefinition | None = None,
) -> PaperTradeOutcomeDataset:
    """Join entry-state features to the final outcome of every closed trade."""

    if not isinstance(features, PointInTimeFeatureMatrix):
        raise TypeError("features must be a PointInTimeFeatureMatrix")
    if not isinstance(accountings, Mapping):
        raise TypeError("accountings must be a mapping keyed by trade reference")
    dataset_definition = definition or PaperTradeOutcomeDefinition()
    if not isinstance(dataset_definition, PaperTradeOutcomeDefinition):
        raise TypeError("definition must be a PaperTradeOutcomeDefinition")
    recorded = tuple(entries)
    if any(not isinstance(item, PaperTradeEntry) for item in recorded):
        raise TypeError("entries must be PaperTradeEntry values")
    if any(
        not isinstance(item, PaperTradeAccounting) for item in accountings.values()
    ):
        raise TypeError("accountings must be PaperTradeAccounting values")
    extraction = require_utc_datetime(extraction_time, "extraction_time")

    ordered = tuple(
        sorted(
            recorded,
            key=lambda item: (item.entry_decision_timestamp, item.trade_reference),
        )
    )
    _validate_inputs(
        ordered,
        accountings,
        features,
        definition=dataset_definition,
        extraction_time=extraction,
    )

    feature_columns = tuple(
        features.definition.feature_names.index(name)
        for name in dataset_definition.entry_feature_names
    )
    rows = tuple(
        _row(
            entry,
            accountings[entry.trade_reference],
            features,
            definition=dataset_definition,
            feature_columns=feature_columns,
        )
        for entry in ordered
    )

    input_digest = _digest(
        {
            "entries": [_entry_record(item) for item in ordered],
            "accountings": {
                reference: accountings[reference].as_record()
                for reference in sorted(accountings)
            },
            "features": features.as_record(),
        }
    )
    dataset = PaperTradeOutcomeDataset(
        dataset_id="",
        evidence_digest="",
        feature_id=PAPER_TRADE_OUTCOME_FEATURE_ID,
        policy_version=PAPER_TRADE_OUTCOME_POLICY_VERSION,
        definition=dataset_definition,
        extraction_time=extraction,
        config_metadata=features.definition.provenance.as_record(),
        accounting_policy_version=PAPER_TRADE_ACCOUNTING_POLICY_VERSION,
        r_multiple_convention=R_MULTIPLE_CONVENTION,
        funding_convention=FUNDING_CONVENTION,
        excursion_convention=EXCURSION_CONVENTION,
        maximum_size_convention=MAXIMUM_SIZE_CONVENTION,
        feature_definition=features.definition.as_record(),
        feature_definition_fingerprint=features.definition.fingerprint,
        input_digest=input_digest,
        production_status=PAPER_TRADE_OUTCOME_PRODUCTION_STATUS,
        promotion_ticket=PAPER_TRADE_OUTCOME_PROMOTION_TICKET,
        rows=rows,
        coverage=_coverage(rows, dataset_definition),
        reason_codes=PAPER_TRADE_OUTCOME_REASON_CODES,
    )
    dataset = replace(dataset, dataset_id=_dataset_id(dataset))
    _validate_dataset(dataset, allow_empty_digest=True)
    return replace(dataset, evidence_digest=_digest(_dataset_payload(dataset)))


def restore_paper_trade_outcome_dataset(
    record: Mapping[str, Any],
) -> PaperTradeOutcomeDataset:
    """Restore a persisted BTC-191 dataset and reject drift or tampering."""

    source = _mapping(record, "record")
    definition = _definition_from_record(
        _mapping(source.get("definition"), "definition")
    )
    rows = tuple(
        _row_from_record(_mapping(item, "row"))
        for item in _sequence(source.get("rows"), "rows")
    )
    dataset = PaperTradeOutcomeDataset(
        dataset_id=_string(source.get("dataset_id"), "dataset_id"),
        evidence_digest=_string(source.get("evidence_digest"), "evidence_digest"),
        feature_id=_string(source.get("feature_id"), "feature_id"),
        policy_version=_string(source.get("policy_version"), "policy_version"),
        definition=definition,
        extraction_time=_utc_from_record(
            source.get("extraction_time"), "extraction_time"
        ),
        config_metadata=_string_mapping(
            source.get("config_metadata"), "config_metadata"
        ),
        accounting_policy_version=_string(
            source.get("accounting_policy_version"), "accounting_policy_version"
        ),
        r_multiple_convention=_string(
            source.get("r_multiple_convention"), "r_multiple_convention"
        ),
        funding_convention=_string(
            source.get("funding_convention"), "funding_convention"
        ),
        excursion_convention=_string(
            source.get("excursion_convention"), "excursion_convention"
        ),
        maximum_size_convention=_string(
            source.get("maximum_size_convention"), "maximum_size_convention"
        ),
        feature_definition=dict(
            _mapping(source.get("feature_definition"), "feature_definition")
        ),
        feature_definition_fingerprint=_string(
            source.get("feature_definition_fingerprint"),
            "feature_definition_fingerprint",
        ),
        input_digest=_string(source.get("input_digest"), "input_digest"),
        production_status=_string(
            source.get("production_status"), "production_status"
        ),
        promotion_ticket=_string(source.get("promotion_ticket"), "promotion_ticket"),
        rows=rows,
        coverage=_coverage_from_record(_mapping(source.get("coverage"), "coverage")),
        reason_codes=_string_tuple(source.get("reason_codes"), "reason_codes"),
    )
    _validate_row_columns(rows, definition)
    if dataset.coverage.as_record() != _coverage(rows, definition).as_record():
        raise PaperTradeOutcomeError("coverage does not match the persisted rows")
    if dataset.as_record() != dict(source):
        raise PaperTradeOutcomeError(
            "record does not match reconstructed paper-trade outcomes"
        )
    return dataset


def _row(
    entry: PaperTradeEntry,
    accounting: PaperTradeAccounting,
    features: PointInTimeFeatureMatrix,
    *,
    definition: PaperTradeOutcomeDefinition,
    feature_columns: Sequence[int],
) -> PaperTradeOutcomeRow:
    row_index = features.decision_timestamps.index(entry.entry_decision_timestamp)
    assert accounting.closed_at is not None
    assert accounting.exit_reason is not None
    assert accounting.exit_reason_source_id is not None
    return PaperTradeOutcomeRow(
        trade_reference=entry.trade_reference,
        entry_decision_timestamp=entry.entry_decision_timestamp,
        data_available_at=entry.data_available_at,
        opened_at=accounting.opened_at,
        closed_at=accounting.closed_at,
        symbol=entry.symbol,
        direction=entry.direction,
        decision=entry.decision,
        setup=entry.setup,
        regime=entry.regime,
        recommendation_id=entry.provenance.recommendation_id,
        strategy_version=entry.provenance.strategy_version,
        parameter_set_id=entry.provenance.parameter_set_id,
        source_id=entry.source_id,
        exit_reason=accounting.exit_reason,
        exit_reason_source_id=accounting.exit_reason_source_id,
        initial_stop_source_id=accounting.initial_stop_source_id,
        accounting_evidence_digest=accounting.evidence_digest,
        entry_features=tuple(
            _entry_feature_cell(
                features,
                row_index=row_index,
                column=column,
                feature_name=name,
            )
            for name, column in zip(
                definition.entry_feature_names, feature_columns, strict=True
            )
        ),
        outcomes=tuple(
            _outcome_cell(accounting, outcome_name=name)
            for name in definition.outcome_names
        ),
        entry_reason_codes=entry.reason_codes,
        accounting_reason_codes=accounting.reason_codes,
    )


def _entry_feature_cell(
    features: PointInTimeFeatureMatrix,
    *,
    row_index: int,
    column: int,
    feature_name: str,
) -> EntryStateFeature:
    source_id = features.source_ids[row_index][column]
    raw = features.values[row_index, column]
    value = None if bool(np.isnan(raw)) else float(raw)
    if source_id is None:
        status = ENTRY_FEATURE_NOT_OBSERVED
    elif value is None:
        status = ENTRY_FEATURE_MISSING_VALUE
    else:
        status = ENTRY_FEATURE_AVAILABLE
    return EntryStateFeature(
        feature_name=feature_name,
        status=status,
        value=value,
        observation_time=features.observation_times[row_index][column],
        available_at=features.available_ats[row_index][column],
        source_id=source_id,
        revision=features.revisions[row_index][column],
    )


def _outcome_cell(
    accounting: PaperTradeAccounting, *, outcome_name: str
) -> PaperTradeOutcome:
    raw = getattr(accounting, outcome_name)
    if raw is None:
        return PaperTradeOutcome(
            outcome_name=outcome_name,
            status=TRADE_OUTCOME_NOT_MEASURED,
            value=None,
            reason_code=_unmeasured_reason(accounting, outcome_name=outcome_name),
        )
    value = Decimal(raw) if isinstance(raw, int) else raw
    if not isinstance(value, Decimal):
        raise PaperTradeOutcomeError(
            f"{outcome_name} must be a Decimal accounting output"
        )
    return PaperTradeOutcome(
        outcome_name=outcome_name,
        status=TRADE_OUTCOME_AVAILABLE,
        value=value,
        reason_code=None,
    )


def _unmeasured_reason(
    accounting: PaperTradeAccounting, *, outcome_name: str
) -> str:
    if (
        outcome_name in _EXCURSION_OUTCOME_NAMES
        and accounting.maximum_favourable_excursion is None
    ):
        code = _NO_EXCURSION_BARS_REASON
    else:
        code = _R_UNDEFINED_REASON
    if code not in accounting.reason_codes:
        raise PaperTradeOutcomeError(
            f"{outcome_name} is absent without an explanatory BTC-165 reason code"
        )
    return code


def _coverage(
    rows: Sequence[PaperTradeOutcomeRow],
    definition: PaperTradeOutcomeDefinition,
) -> PaperTradeOutcomeCoverage:
    direction_counts = dict.fromkeys(TRADE_DIRECTIONS, 0)
    decision_counts = dict.fromkeys(PAPER_TRADE_DECISIONS, 0)
    setup_counts = dict.fromkeys(PAPER_TRADE_SETUPS, 0)
    regime_counts = dict.fromkeys(PAPER_TRADE_REGIMES, 0)
    # Exit reasons are BTC-165 identifiers with no frozen research vocabulary,
    # so the census reports exactly the reasons observed.
    exit_reason_counts: dict[str, int] = {}
    entry_feature_status_counts = {
        name: dict.fromkeys(ENTRY_FEATURE_STATUSES, 0)
        for name in definition.entry_feature_names
    }
    outcome_status_counts = {
        name: dict.fromkeys(TRADE_OUTCOME_STATUSES, 0)
        for name in definition.outcome_names
    }
    for row in rows:
        direction_counts[row.direction] += 1
        decision_counts[row.decision] += 1
        setup_counts[row.setup] += 1
        regime_counts[row.regime] += 1
        exit_reason_counts[row.exit_reason] = (
            exit_reason_counts.get(row.exit_reason, 0) + 1
        )
        for feature in row.entry_features:
            entry_feature_status_counts[feature.feature_name][feature.status] += 1
        for outcome in row.outcomes:
            outcome_status_counts[outcome.outcome_name][outcome.status] += 1
    return PaperTradeOutcomeCoverage(
        trade_count=len(rows),
        direction_counts=direction_counts,
        decision_counts=decision_counts,
        setup_counts=setup_counts,
        regime_counts=regime_counts,
        exit_reason_counts={
            name: exit_reason_counts[name] for name in sorted(exit_reason_counts)
        },
        entry_feature_status_counts=entry_feature_status_counts,
        outcome_status_counts=outcome_status_counts,
    )


def _validate_inputs(
    entries: Sequence[PaperTradeEntry],
    accountings: Mapping[str, PaperTradeAccounting],
    features: PointInTimeFeatureMatrix,
    *,
    definition: PaperTradeOutcomeDefinition,
    extraction_time: datetime,
) -> None:
    references = tuple(entry.trade_reference for entry in entries)
    _reject_duplicates(references, field_name="trade references")
    missing = sorted(set(references) - set(accountings))
    if missing:
        raise PaperTradeOutcomeError(
            "every entry requires its BTC-165 accounting; missing "
            + ", ".join(missing)
        )
    unmatched = sorted(set(accountings) - set(references))
    if unmatched:
        raise PaperTradeOutcomeError(
            "accountings without a recorded entry state: " + ", ".join(unmatched)
        )
    for reference in accountings:
        _non_empty(reference, "trade reference")
    unknown_features = sorted(
        set(definition.entry_feature_names) - set(features.definition.feature_names)
    )
    if unknown_features:
        raise PaperTradeOutcomeError(
            "feature matrix does not contain entry-state features: "
            + ", ".join(unknown_features)
        )
    provenance = features.definition.provenance
    for entry in entries:
        accounting = accountings[entry.trade_reference]
        _validate_join(
            entry,
            accounting,
            features,
            extraction_time=extraction_time,
            feature_strategy_version=provenance.strategy_version,
            feature_parameter_set_id=provenance.parameter_set_id,
        )


def _validate_join(
    entry: PaperTradeEntry,
    accounting: PaperTradeAccounting,
    features: PointInTimeFeatureMatrix,
    *,
    extraction_time: datetime,
    feature_strategy_version: str,
    feature_parameter_set_id: str,
) -> None:
    reference = entry.trade_reference
    if accounting.policy_version != PAPER_TRADE_ACCOUNTING_POLICY_VERSION:
        raise PaperTradeOutcomeError(
            f"{reference}: accounting policy version must be "
            f"{PAPER_TRADE_ACCOUNTING_POLICY_VERSION}"
        )
    for field_name, expected in (
        ("r_multiple_convention", R_MULTIPLE_CONVENTION),
        ("funding_convention", FUNDING_CONVENTION),
        ("excursion_convention", EXCURSION_CONVENTION),
        ("maximum_size_convention", MAXIMUM_SIZE_CONVENTION),
    ):
        if getattr(accounting, field_name) != expected:
            raise PaperTradeOutcomeError(
                f"{reference}: accounting {field_name} must be {expected!r}"
            )
    if not accounting.closed or accounting.closed_at is None:
        raise PaperTradeOutcomeError(
            f"{reference}: an open position has no final outcome; the dataset "
            "joins closed trades only"
        )
    if accounting.symbol != entry.symbol:
        raise PaperTradeOutcomeError(
            f"{reference}: entry symbol does not match the executed trade"
        )
    if accounting.direction != entry.direction:
        raise PaperTradeOutcomeError(
            f"{reference}: entry direction does not match the executed trade"
        )
    if entry.entry_decision_timestamp > accounting.opened_at:
        raise PaperTradeOutcomeError(
            f"{reference}: the entry decision must not follow the opening fill"
        )
    if accounting.closed_at > extraction_time:
        raise PaperTradeOutcomeError(
            f"{reference}: the trade closed after the extraction time; rebuild "
            "the dataset with a later extraction_time"
        )
    metadata = accounting.config_metadata
    for key, entry_value, feature_value in (
        (
            "strategy_version",
            entry.provenance.strategy_version,
            feature_strategy_version,
        ),
        (
            "parameter_set_id",
            entry.provenance.parameter_set_id,
            feature_parameter_set_id,
        ),
    ):
        if metadata.get(key) != entry_value:
            raise PaperTradeOutcomeError(
                f"{reference}: accounting {key} does not match the recorded "
                "lifecycle provenance"
            )
        if entry_value != feature_value:
            raise PaperTradeOutcomeError(
                f"{reference}: lifecycle {key} does not match the feature-matrix "
                "provenance; one dataset holds one strategy provenance"
            )
    if entry.entry_decision_timestamp not in features.decision_timestamps:
        raise PaperTradeOutcomeError(
            f"{reference}: entry decision timestamp "
            f"{entry.entry_decision_timestamp.isoformat()} is not a feature-matrix "
            "decision timestamp"
        )


def _validate_row_columns(
    rows: Sequence[PaperTradeOutcomeRow],
    definition: PaperTradeOutcomeDefinition,
) -> None:
    for row in rows:
        if tuple(item.feature_name for item in row.entry_features) != (
            definition.entry_feature_names
        ):
            raise PaperTradeOutcomeError(
                "every row must carry the defined entry features in definition order"
            )
        if tuple(item.outcome_name for item in row.outcomes) != (
            definition.outcome_names
        ):
            raise PaperTradeOutcomeError(
                "every row must carry the defined outcomes in definition order"
            )


def _validate_dataset(
    dataset: PaperTradeOutcomeDataset,
    *,
    allow_empty_digest: bool = False,
) -> None:
    if not isinstance(dataset.definition, PaperTradeOutcomeDefinition):
        raise PaperTradeOutcomeError(
            "definition must be a PaperTradeOutcomeDefinition"
        )
    expected = {
        "feature_id": PAPER_TRADE_OUTCOME_FEATURE_ID,
        "policy_version": PAPER_TRADE_OUTCOME_POLICY_VERSION,
        "accounting_policy_version": PAPER_TRADE_ACCOUNTING_POLICY_VERSION,
        "r_multiple_convention": R_MULTIPLE_CONVENTION,
        "funding_convention": FUNDING_CONVENTION,
        "excursion_convention": EXCURSION_CONVENTION,
        "maximum_size_convention": MAXIMUM_SIZE_CONVENTION,
        "production_status": PAPER_TRADE_OUTCOME_PRODUCTION_STATUS,
        "promotion_ticket": PAPER_TRADE_OUTCOME_PROMOTION_TICKET,
    }
    for field_name, value in expected.items():
        if getattr(dataset, field_name) != value:
            raise PaperTradeOutcomeError(f"{field_name} must be {value!r}")
    if dataset.reason_codes != PAPER_TRADE_OUTCOME_REASON_CODES:
        raise PaperTradeOutcomeError("reason_codes must be the BTC-191 reason codes")
    _non_empty(dataset.dataset_id, "dataset_id")
    if not allow_empty_digest:
        _non_empty(dataset.evidence_digest, "evidence_digest")
    _non_empty(dataset.input_digest, "input_digest")
    _non_empty(
        dataset.feature_definition_fingerprint, "feature_definition_fingerprint"
    )
    require_utc_datetime(dataset.extraction_time, "extraction_time")
    if not isinstance(dataset.coverage, PaperTradeOutcomeCoverage):
        raise PaperTradeOutcomeError("coverage must be a PaperTradeOutcomeCoverage")
    if any(not isinstance(row, PaperTradeOutcomeRow) for row in dataset.rows):
        raise PaperTradeOutcomeError("rows must contain PaperTradeOutcomeRow values")
    references = tuple(row.trade_reference for row in dataset.rows)
    _reject_duplicates(references, field_name="trade references")
    keys = [
        (row.entry_decision_timestamp, row.trade_reference) for row in dataset.rows
    ]
    if keys != sorted(keys):
        raise PaperTradeOutcomeError(
            "rows must be ordered by entry decision timestamp then trade reference"
        )
    for row in dataset.rows:
        if row.closed_at > dataset.extraction_time:
            raise PaperTradeOutcomeError(
                "a trade must not close after the extraction time"
            )
        if row.strategy_version != dataset.config_metadata.get("strategy_version"):
            raise PaperTradeOutcomeError(
                "row strategy_version must match the dataset provenance"
            )
        if row.parameter_set_id != dataset.config_metadata.get("parameter_set_id"):
            raise PaperTradeOutcomeError(
                "row parameter_set_id must match the dataset provenance"
            )
    _validate_row_columns(dataset.rows, dataset.definition)
    if dataset.coverage.as_record() != _coverage(
        dataset.rows, dataset.definition
    ).as_record():
        raise PaperTradeOutcomeError("coverage does not match the persisted rows")
    if dataset.dataset_id != _dataset_id(dataset):
        raise PaperTradeOutcomeError("dataset_id does not match the dataset identity")


def _dataset_identity(dataset: PaperTradeOutcomeDataset) -> dict[str, Any]:
    return {
        "feature_id": dataset.feature_id,
        "policy_version": dataset.policy_version,
        "definition": dataset.definition.as_record(),
        "extraction_time": dataset.extraction_time.isoformat(),
        "config_metadata": dict(dataset.config_metadata),
        "accounting_policy_version": dataset.accounting_policy_version,
        "r_multiple_convention": dataset.r_multiple_convention,
        "funding_convention": dataset.funding_convention,
        "excursion_convention": dataset.excursion_convention,
        "maximum_size_convention": dataset.maximum_size_convention,
        "feature_definition_fingerprint": dataset.feature_definition_fingerprint,
        "input_digest": dataset.input_digest,
    }


def _dataset_id(dataset: PaperTradeOutcomeDataset) -> str:
    return _digest(_dataset_identity(dataset))


def _dataset_payload(dataset: PaperTradeOutcomeDataset) -> dict[str, Any]:
    return {
        **_dataset_identity(dataset),
        "dataset_id": dataset.dataset_id,
        "feature_definition": dict(dataset.feature_definition),
        "production_status": dataset.production_status,
        "promotion_ticket": dataset.promotion_ticket,
        "rows": [row.as_record() for row in dataset.rows],
        "coverage": dataset.coverage.as_record(),
        "reason_codes": list(dataset.reason_codes),
    }


def _definition_payload(definition: PaperTradeOutcomeDefinition) -> dict[str, Any]:
    return {
        "version": definition.version,
        "entry_feature_names": list(definition.entry_feature_names),
        "outcome_names": list(definition.outcome_names),
        "join_policy_version": definition.join_policy_version,
        "entry_state_policy_version": definition.entry_state_policy_version,
        "finality_policy_version": definition.finality_policy_version,
        "provenance_policy_version": definition.provenance_policy_version,
        "missing_value_policy_version": definition.missing_value_policy_version,
        "promotion_policy_version": definition.promotion_policy_version,
    }


def _entry_record(entry: PaperTradeEntry) -> dict[str, Any]:
    return {
        "trade_reference": entry.trade_reference,
        "entry_decision_timestamp": entry.entry_decision_timestamp.isoformat(),
        "data_available_at": entry.data_available_at.isoformat(),
        "symbol": entry.symbol,
        "direction": entry.direction,
        "decision": entry.decision,
        "setup": entry.setup,
        "regime": entry.regime,
        "provenance": entry.provenance.as_record(),
        "source_id": entry.source_id,
        "reason_codes": [
            _reason_code_record(item) for item in entry.reason_codes
        ],
    }


def _reason_code_record(reason_code: RecommendationReasonCode) -> dict[str, str]:
    return {
        "code": reason_code.code,
        "source_component": reason_code.source_component,
        "severity": reason_code.severity,
        "detail": reason_code.detail,
    }


def _definition_from_record(
    record: Mapping[str, Any],
) -> PaperTradeOutcomeDefinition:
    definition = PaperTradeOutcomeDefinition(
        version=_string(record.get("version"), "version"),
        entry_feature_names=_string_tuple(
            record.get("entry_feature_names"), "entry_feature_names"
        ),
        outcome_names=_string_tuple(record.get("outcome_names"), "outcome_names"),
        join_policy_version=_string(
            record.get("join_policy_version"), "join_policy_version"
        ),
        entry_state_policy_version=_string(
            record.get("entry_state_policy_version"), "entry_state_policy_version"
        ),
        finality_policy_version=_string(
            record.get("finality_policy_version"), "finality_policy_version"
        ),
        provenance_policy_version=_string(
            record.get("provenance_policy_version"), "provenance_policy_version"
        ),
        missing_value_policy_version=_string(
            record.get("missing_value_policy_version"),
            "missing_value_policy_version",
        ),
        promotion_policy_version=_string(
            record.get("promotion_policy_version"), "promotion_policy_version"
        ),
    )
    if definition.as_record() != dict(record):
        raise PaperTradeOutcomeError(
            "definition record does not match its fingerprint"
        )
    return definition


def _row_from_record(record: Mapping[str, Any]) -> PaperTradeOutcomeRow:
    return PaperTradeOutcomeRow(
        trade_reference=_string(record.get("trade_reference"), "trade_reference"),
        entry_decision_timestamp=_utc_from_record(
            record.get("entry_decision_timestamp"), "entry_decision_timestamp"
        ),
        data_available_at=_utc_from_record(
            record.get("data_available_at"), "data_available_at"
        ),
        opened_at=_utc_from_record(record.get("opened_at"), "opened_at"),
        closed_at=_utc_from_record(record.get("closed_at"), "closed_at"),
        symbol=_string(record.get("symbol"), "symbol"),
        direction=_string(record.get("direction"), "direction"),
        decision=_string(record.get("decision"), "decision"),
        setup=_string(record.get("setup"), "setup"),
        regime=_string(record.get("regime"), "regime"),
        recommendation_id=_recommendation_id(record.get("recommendation_id")),
        strategy_version=_string(
            record.get("strategy_version"), "strategy_version"
        ),
        parameter_set_id=_string(
            record.get("parameter_set_id"), "parameter_set_id"
        ),
        source_id=_string(record.get("source_id"), "source_id"),
        exit_reason=_string(record.get("exit_reason"), "exit_reason"),
        exit_reason_source_id=_string(
            record.get("exit_reason_source_id"), "exit_reason_source_id"
        ),
        initial_stop_source_id=_string(
            record.get("initial_stop_source_id"), "initial_stop_source_id"
        ),
        accounting_evidence_digest=_string(
            record.get("accounting_evidence_digest"), "accounting_evidence_digest"
        ),
        entry_features=tuple(
            _entry_feature_from_record(_mapping(item, "entry_feature"))
            for item in _sequence(record.get("entry_features"), "entry_features")
        ),
        outcomes=tuple(
            _outcome_from_record(_mapping(item, "outcome"))
            for item in _sequence(record.get("outcomes"), "outcomes")
        ),
        entry_reason_codes=tuple(
            _reason_code_from_record(_mapping(item, "reason_code"))
            for item in _sequence(
                record.get("entry_reason_codes"), "entry_reason_codes"
            )
        ),
        accounting_reason_codes=_string_tuple(
            record.get("accounting_reason_codes"), "accounting_reason_codes"
        ),
    )


def _entry_feature_from_record(record: Mapping[str, Any]) -> EntryStateFeature:
    return EntryStateFeature(
        feature_name=_string(record.get("feature_name"), "feature_name"),
        status=_string(record.get("status"), "status"),
        value=_optional_float(record.get("value"), "value"),
        observation_time=_optional_utc_from_record(
            record.get("observation_time"), "observation_time"
        ),
        available_at=_optional_utc_from_record(
            record.get("available_at"), "available_at"
        ),
        source_id=_optional_string(record.get("source_id"), "source_id"),
        revision=_optional_non_negative_integer(record.get("revision"), "revision"),
    )


def _outcome_from_record(record: Mapping[str, Any]) -> PaperTradeOutcome:
    return PaperTradeOutcome(
        outcome_name=_string(record.get("outcome_name"), "outcome_name"),
        status=_string(record.get("status"), "status"),
        value=_optional_decimal(record.get("value"), "value"),
        reason_code=_optional_string(record.get("reason_code"), "reason_code"),
    )


def _reason_code_from_record(record: Mapping[str, Any]) -> RecommendationReasonCode:
    return RecommendationReasonCode(
        code=_string(record.get("code"), "code"),
        source_component=_string(record.get("source_component"), "source_component"),
        severity=_string(record.get("severity"), "severity"),
        detail=_string(record.get("detail"), "detail"),
    )


def _coverage_from_record(record: Mapping[str, Any]) -> PaperTradeOutcomeCoverage:
    return PaperTradeOutcomeCoverage(
        trade_count=_non_negative_integer(
            record.get("trade_count"), "trade_count"
        ),
        direction_counts=_count_mapping(
            record.get("direction_counts"), "direction_counts"
        ),
        decision_counts=_count_mapping(
            record.get("decision_counts"), "decision_counts"
        ),
        setup_counts=_count_mapping(record.get("setup_counts"), "setup_counts"),
        regime_counts=_count_mapping(record.get("regime_counts"), "regime_counts"),
        exit_reason_counts=_count_mapping(
            record.get("exit_reason_counts"), "exit_reason_counts"
        ),
        entry_feature_status_counts=_nested_count_mapping(
            record.get("entry_feature_status_counts"), "entry_feature_status_counts"
        ),
        outcome_status_counts=_nested_count_mapping(
            record.get("outcome_status_counts"), "outcome_status_counts"
        ),
    )


def _cell_matrix(
    values: Sequence[Sequence[float | None]],
    *,
    width: int,
) -> tuple[FloatArray, NDArray[np.bool_]]:
    matrix = np.full((len(values), width), np.nan, dtype=np.float64)
    for row_index, row in enumerate(values):
        for column, value in enumerate(row):
            if value is not None:
                matrix[row_index, column] = value
    mask = np.isnan(matrix)
    matrix.setflags(write=False)
    mask.setflags(write=False)
    return matrix, mask


def _validate_float(value: float | None, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, float | int):
        raise PaperTradeOutcomeError(f"{field_name} must be a real number")
    if not np.isfinite(value):
        raise PaperTradeOutcomeError(f"{field_name} must be finite")


def _validate_cell_provenance(
    *,
    observed: bool,
    observation_time: datetime | None,
    available_at: datetime | None,
    source_id: str | None,
    revision: int | None,
) -> None:
    provenance = (observation_time, available_at, source_id, revision)
    if observed:
        if any(value is None for value in provenance):
            raise PaperTradeOutcomeError(
                "observed cells require complete provenance"
            )
        assert observation_time is not None
        assert available_at is not None
        require_utc_datetime(observation_time, "observation_time")
        require_utc_datetime(available_at, "available_at")
        if available_at < observation_time:
            raise PaperTradeOutcomeError("available_at must be >= observation_time")
        _non_empty(source_id, "source_id")
        assert revision is not None
        _non_negative_integer(revision, "revision")
        return
    if any(value is not None for value in provenance):
        raise PaperTradeOutcomeError("unobserved cells must not carry provenance")


def _reason_codes(
    values: Sequence[RecommendationReasonCode],
) -> tuple[RecommendationReasonCode, ...]:
    reason_codes = tuple(values)
    if any(
        not isinstance(item, RecommendationReasonCode) for item in reason_codes
    ):
        raise PaperTradeOutcomeError(
            "reason_codes must contain RecommendationReasonCode values"
        )
    return reason_codes


def _validate_names(values: Sequence[str], *, field_name: str) -> tuple[str, ...]:
    names = tuple(values)
    if not names:
        raise PaperTradeOutcomeError(f"{field_name} must not be empty")
    for name in names:
        _non_empty(name, field_name)
    _reject_duplicates(names, field_name=field_name)
    return names


def _reject_duplicates(values: Sequence[Any], *, field_name: str) -> None:
    if len(set(values)) != len(values):
        raise PaperTradeOutcomeError(f"{field_name} must be unique")


def _require_member(value: Any, allowed: Sequence[str], field_name: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise PaperTradeOutcomeError(
            f"{field_name} must be one of: " + ", ".join(allowed)
        )
    return value


def _non_empty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaperTradeOutcomeError(f"{field_name} must be a non-empty string")
    return value


def _string(value: Any, field_name: str) -> str:
    return _non_empty(value, field_name)


def _optional_string(value: Any, field_name: str) -> str | None:
    if value is None:
        return None
    return _non_empty(value, field_name)


def _optional_float(value: Any, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, float | int):
        raise PaperTradeOutcomeError(f"{field_name} must be a real number")
    return float(value)


def _optional_decimal(value: Any, field_name: str) -> Decimal | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise PaperTradeOutcomeError(f"{field_name} must be a decimal string")
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise PaperTradeOutcomeError(
            f"{field_name} must be a decimal string"
        ) from error


def _recommendation_id(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise PaperTradeOutcomeError("recommendation_id must be a positive integer")
    return value


def _non_negative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise PaperTradeOutcomeError(
            f"{field_name} must be a non-negative integer"
        )
    return value


def _optional_non_negative_integer(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _non_negative_integer(value, field_name)


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PaperTradeOutcomeError(f"{field_name} must be a mapping")
    return value


def _string_mapping(value: Any, field_name: str) -> dict[str, str]:
    source = _mapping(value, field_name)
    return {
        _non_empty(key, field_name): _non_empty(item, field_name)
        for key, item in source.items()
    }


def _count_mapping(value: Any, field_name: str) -> dict[str, int]:
    source = _mapping(value, field_name)
    return {
        _non_empty(key, field_name): _non_negative_integer(item, field_name)
        for key, item in source.items()
    }


def _nested_count_mapping(value: Any, field_name: str) -> dict[str, dict[str, int]]:
    source = _mapping(value, field_name)
    return {
        _non_empty(key, field_name): _count_mapping(item, field_name)
        for key, item in source.items()
    }


def _sequence(value: Any, field_name: str) -> tuple[Any, ...]:
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise PaperTradeOutcomeError(f"{field_name} must be a sequence")
    return tuple(value)


def _string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    return tuple(
        _non_empty(item, field_name) for item in _sequence(value, field_name)
    )


def _utc_from_record(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise PaperTradeOutcomeError(f"{field_name} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise PaperTradeOutcomeError(
            f"{field_name} must be an ISO-8601 string"
        ) from error
    return require_utc_datetime(parsed, field_name)


def _optional_utc_from_record(value: Any, field_name: str) -> datetime | None:
    if value is None:
        return None
    return _utc_from_record(value, field_name)


def _isoformat(value: datetime | None) -> str | None:
    return None if value is None else value.isoformat()


def _digest(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


__all__ = [
    "ENTRY_FEATURE_AVAILABLE",
    "ENTRY_FEATURE_MISSING_VALUE",
    "ENTRY_FEATURE_NOT_OBSERVED",
    "ENTRY_FEATURE_STATUSES",
    "PAPER_TRADE_DECISIONS",
    "PAPER_TRADE_OUTCOME_ENTRY_STATE_POLICY_VERSION",
    "PAPER_TRADE_OUTCOME_FEATURE_ID",
    "PAPER_TRADE_OUTCOME_FINALITY_POLICY_VERSION",
    "PAPER_TRADE_OUTCOME_JOIN_POLICY_VERSION",
    "PAPER_TRADE_OUTCOME_MISSING_VALUE_POLICY_VERSION",
    "PAPER_TRADE_OUTCOME_NAMES",
    "PAPER_TRADE_OUTCOME_POLICY_VERSION",
    "PAPER_TRADE_OUTCOME_PRODUCTION_STATUS",
    "PAPER_TRADE_OUTCOME_PROMOTION_POLICY_VERSION",
    "PAPER_TRADE_OUTCOME_PROMOTION_TICKET",
    "PAPER_TRADE_OUTCOME_PROVENANCE_POLICY_VERSION",
    "PAPER_TRADE_OUTCOME_REASON_CODES",
    "PAPER_TRADE_REGIMES",
    "PAPER_TRADE_SETUPS",
    "TRADE_OUTCOME_AVAILABLE",
    "TRADE_OUTCOME_NOT_MEASURED",
    "TRADE_OUTCOME_STATUSES",
    "EntryStateFeature",
    "PaperTradeEntry",
    "PaperTradeOutcome",
    "PaperTradeOutcomeCoverage",
    "PaperTradeOutcomeDataset",
    "PaperTradeOutcomeDefinition",
    "PaperTradeOutcomeError",
    "PaperTradeOutcomeRow",
    "build_paper_trade_outcome_dataset",
    "restore_paper_trade_outcome_dataset",
]
