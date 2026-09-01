"""Market state for every decision date (BTC-190).

Research into rejected opportunities needs the dates the strategy did *not*
trade as much as the dates it did.  This module joins one immutable row per
decision date:

``scores``
    the point-in-time BTC-048 feature-matrix cells named by the versioned
    store definition;
``setup`` and ``decision``
    the categorical state recorded by the evaluating path, validated against
    the authoritative owner vocabularies; and
``future_1w_return`` .. ``future_MAE``
    the BTC-048 forward targets that had become available by the extraction
    time.

Coverage is complete by construction: the recorded decision states must cover
the feature-matrix decision grid exactly, so a store can never silently omit a
rejected date.  Nothing is zero-filled; every absent score or outcome keeps an
explicit status and its provenance.  Outcomes that only became available after
the extraction time are rejected rather than joined, which keeps the store
replayable as of that time.

The store is research evidence only.  It has no strategy or configuration
mutation path and records BTC-193 as the required promotion boundary.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime
from typing import Any

import numpy as np
from numpy.typing import NDArray

from btc_predictor.data import require_utc_datetime
from btc_predictor.features.regime import REGIME_CLASSIFICATION_LABELS
from btc_predictor.features.setup import (
    BEARISH_DISTRIBUTION_SETUP,
    BULL_TREND_CONTINUATION_SETUP,
    BULLISH_RESET_SETUP,
    CAPITULATION_REVERSAL_SETUP,
)
from btc_predictor.quant.arrays import FloatArray
from btc_predictor.research.feature_matrix import (
    ForwardTargetMatrix,
    PointInTimeFeatureMatrix,
    TargetSpecification,
)
from btc_predictor.signals.data_quality import (
    RECOMMENDATION_ACTIONS,
    RecommendationReasonCode,
)


DECISION_STATE_FEATURE_ID = "DECISION_STATE_STORE"
DECISION_STATE_POLICY_VERSION = "DECISION_STATE_STORE_V1"
DECISION_STATE_COVERAGE_POLICY_VERSION = "EVERY_DECISION_DATE_REQUIRED_V1"
DECISION_STATE_MISSING_VALUE_POLICY_VERSION = "EXPLICIT_STATUS_NO_ZERO_FILL_V1"
DECISION_STATE_OUTCOME_AVAILABILITY_POLICY_VERSION = (
    "OUTCOME_AVAILABLE_BY_EXTRACTION_TIME_V1"
)
DECISION_STATE_PROMOTION_POLICY_VERSION = "BTC_193_REQUIRED_V1"
DECISION_STATE_PRODUCTION_STATUS = "RESEARCH_ONLY_NOT_PRODUCTION"
DECISION_STATE_PROMOTION_TICKET = "BTC-193"

# Categorical vocabularies stay owned by their implementing modules; only the
# explicit research sentinels below are added here.
NO_SETUP = "NO_SETUP"
DECISION_STATE_SETUPS = (
    BULL_TREND_CONTINUATION_SETUP,
    BULLISH_RESET_SETUP,
    CAPITULATION_REVERSAL_SETUP,
    BEARISH_DISTRIBUTION_SETUP,
    NO_SETUP,
)
UNCLASSIFIED_REGIME = "UNCLASSIFIED"
DECISION_STATE_REGIMES = (*REGIME_CLASSIFICATION_LABELS, UNCLASSIFIED_REGIME)
DECISION_STATE_DECISIONS = RECOMMENDATION_ACTIONS

TRADED = "TRADED"
NOT_TRADED = "NOT_TRADED"
DECISION_EXECUTION_STATUSES = (TRADED, NOT_TRADED)

SCORE_AVAILABLE = "AVAILABLE"
SCORE_MISSING_VALUE = "MISSING_VALUE"
SCORE_NOT_OBSERVED = "NOT_OBSERVED"
DECISION_STATE_SCORE_STATUSES = (
    SCORE_AVAILABLE,
    SCORE_MISSING_VALUE,
    SCORE_NOT_OBSERVED,
)

OUTCOME_AVAILABLE = "AVAILABLE"
OUTCOME_MISSING_VALUE = "MISSING_VALUE"
OUTCOME_PENDING_HORIZON = "PENDING_HORIZON"
OUTCOME_NOT_RECORDED = "NOT_RECORDED"
DECISION_STATE_OUTCOME_STATUSES = (
    OUTCOME_AVAILABLE,
    OUTCOME_MISSING_VALUE,
    OUTCOME_PENDING_HORIZON,
    OUTCOME_NOT_RECORDED,
)

# The v1.2 composite scores persisted for every decision date.  A caller may
# declare a wider set through the versioned definition as long as the feature
# matrix supplies those columns point-in-time.
DECISION_STATE_SCORE_NAMES = (
    "TREND_SCORE",
    "FLOW_SCORE",
    "POSITIONING_SCORE",
    "VOLATILITY_SCORE",
    "STRUCTURE_SCORE",
    "REGIME_SCORE",
)
DECISION_STATE_OUTCOME_NAMES = (
    "future_1w_return",
    "future_2w_return",
    "future_4w_return",
    "future_8w_return",
    "future_MFE",
    "future_MAE",
)

DECISION_STATE_REASON_CODES = (
    "DECISION_STATE_EVERY_DECISION_DATE_COVERED",
    "DECISION_STATE_REJECTED_OPPORTUNITIES_RETAINED",
    "DECISION_STATE_POINT_IN_TIME_SCORES",
    "DECISION_STATE_FORWARD_OUTCOMES_SEPARATED",
    "DECISION_STATE_OUTCOME_AVAILABILITY_ENFORCED",
    "DECISION_STATE_MISSING_VALUES_EXPLICIT",
    "DECISION_STATE_RESEARCH_ONLY",
    "DECISION_STATE_BTC_193_PROMOTION_REQUIRED",
    "DECISION_STATE_COMPLETE",
)


class DecisionStateError(ValueError):
    """Raised when decision-state inputs violate the BTC-190 contract."""


@dataclass(frozen=True)
class DecisionStateDefinition:
    """Versioned column contract for one decision-state store."""

    version: str = DECISION_STATE_POLICY_VERSION
    score_names: tuple[str, ...] = DECISION_STATE_SCORE_NAMES
    outcome_names: tuple[str, ...] = DECISION_STATE_OUTCOME_NAMES
    coverage_policy_version: str = DECISION_STATE_COVERAGE_POLICY_VERSION
    missing_value_policy_version: str = DECISION_STATE_MISSING_VALUE_POLICY_VERSION
    outcome_availability_policy_version: str = (
        DECISION_STATE_OUTCOME_AVAILABILITY_POLICY_VERSION
    )
    promotion_policy_version: str = DECISION_STATE_PROMOTION_POLICY_VERSION

    def __post_init__(self) -> None:
        expected = {
            "version": DECISION_STATE_POLICY_VERSION,
            "coverage_policy_version": DECISION_STATE_COVERAGE_POLICY_VERSION,
            "missing_value_policy_version": (
                DECISION_STATE_MISSING_VALUE_POLICY_VERSION
            ),
            "outcome_availability_policy_version": (
                DECISION_STATE_OUTCOME_AVAILABILITY_POLICY_VERSION
            ),
            "promotion_policy_version": DECISION_STATE_PROMOTION_POLICY_VERSION,
        }
        for field_name, value in expected.items():
            if getattr(self, field_name) != value:
                raise DecisionStateError(f"{field_name} must be {value!r}")
        object.__setattr__(
            self,
            "score_names",
            _validate_names(self.score_names, field_name="score_names"),
        )
        object.__setattr__(
            self,
            "outcome_names",
            _validate_names(self.outcome_names, field_name="outcome_names"),
        )

    @property
    def fingerprint(self) -> str:
        return _digest(_definition_payload(self))

    def as_record(self) -> dict[str, Any]:
        return {**_definition_payload(self), "fingerprint": self.fingerprint}


@dataclass(frozen=True)
class DecisionStateObservation:
    """The categorical market state recorded at one decision timestamp."""

    decision_timestamp: datetime
    data_available_at: datetime
    decision: str
    setup: str
    regime: str
    execution_status: str
    source_id: str
    trade_reference: str | None = None
    reason_codes: tuple[RecommendationReasonCode, ...] = ()

    def __post_init__(self) -> None:
        decision_timestamp = require_utc_datetime(
            self.decision_timestamp, "decision_timestamp"
        )
        data_available_at = require_utc_datetime(
            self.data_available_at, "data_available_at"
        )
        if data_available_at > decision_timestamp:
            raise DecisionStateError(
                "data_available_at must be <= decision_timestamp"
            )
        _require_member(self.decision, DECISION_STATE_DECISIONS, "decision")
        _require_member(self.setup, DECISION_STATE_SETUPS, "setup")
        _require_member(self.regime, DECISION_STATE_REGIMES, "regime")
        _require_member(
            self.execution_status,
            DECISION_EXECUTION_STATUSES,
            "execution_status",
        )
        _non_empty(self.source_id, "source_id")
        if self.execution_status == TRADED:
            if self.trade_reference is None:
                raise DecisionStateError(
                    "a traded decision date requires a trade_reference"
                )
            _non_empty(self.trade_reference, "trade_reference")
        elif self.trade_reference is not None:
            raise DecisionStateError(
                "a not-traded decision date must not carry a trade_reference"
            )
        reason_codes = tuple(self.reason_codes)
        if any(
            not isinstance(item, RecommendationReasonCode) for item in reason_codes
        ):
            raise DecisionStateError(
                "reason_codes must contain RecommendationReasonCode values"
            )
        object.__setattr__(self, "decision_timestamp", decision_timestamp)
        object.__setattr__(self, "data_available_at", data_available_at)
        object.__setattr__(self, "reason_codes", reason_codes)


@dataclass(frozen=True)
class DecisionStateScore:
    """One persisted score cell and the provenance that produced it."""

    score_name: str
    status: str
    value: float | None
    observation_time: datetime | None
    available_at: datetime | None
    source_id: str | None
    revision: int | None

    def __post_init__(self) -> None:
        _non_empty(self.score_name, "score_name")
        _require_member(self.status, DECISION_STATE_SCORE_STATUSES, "status")
        _validate_cell_value(self.value, "score value")
        observed = self.status != SCORE_NOT_OBSERVED
        _validate_cell_provenance(
            observed=observed,
            times=((self.observation_time, "observation_time"),),
            available_at=self.available_at,
            source_id=self.source_id,
            revision=self.revision,
        )
        if (self.status == SCORE_AVAILABLE) != (self.value is not None):
            raise DecisionStateError(
                "score value must be present exactly when the status is AVAILABLE"
            )
        if observed:
            assert self.observation_time is not None
            assert self.available_at is not None
            if self.available_at < self.observation_time:
                raise DecisionStateError(
                    "score available_at must be >= observation_time"
                )

    def as_record(self) -> dict[str, Any]:
        return {
            "score_name": self.score_name,
            "status": self.status,
            "value": self.value,
            "observation_time": _isoformat(self.observation_time),
            "available_at": _isoformat(self.available_at),
            "source_id": self.source_id,
            "revision": self.revision,
        }


@dataclass(frozen=True)
class DecisionStateOutcome:
    """One persisted forward outcome and its availability status."""

    outcome_name: str
    status: str
    value: float | None
    outcome_time: datetime | None
    available_at: datetime | None
    source_id: str | None
    revision: int | None

    def __post_init__(self) -> None:
        _non_empty(self.outcome_name, "outcome_name")
        _require_member(self.status, DECISION_STATE_OUTCOME_STATUSES, "status")
        _validate_cell_value(self.value, "outcome value")
        recorded = self.status in (OUTCOME_AVAILABLE, OUTCOME_MISSING_VALUE)
        _validate_cell_provenance(
            observed=recorded,
            times=((self.outcome_time, "outcome_time"),),
            available_at=self.available_at,
            source_id=self.source_id,
            revision=self.revision,
        )
        if (self.status == OUTCOME_AVAILABLE) != (self.value is not None):
            raise DecisionStateError(
                "outcome value must be present exactly when the status is AVAILABLE"
            )
        if recorded:
            assert self.outcome_time is not None
            assert self.available_at is not None
            if self.available_at < self.outcome_time:
                raise DecisionStateError(
                    "outcome available_at must be >= outcome_time"
                )

    def as_record(self) -> dict[str, Any]:
        return {
            "outcome_name": self.outcome_name,
            "status": self.status,
            "value": self.value,
            "outcome_time": _isoformat(self.outcome_time),
            "available_at": _isoformat(self.available_at),
            "source_id": self.source_id,
            "revision": self.revision,
        }


@dataclass(frozen=True)
class DecisionStateRow:
    """Complete persisted market state for one decision date."""

    decision_timestamp: datetime
    data_available_at: datetime
    decision: str
    setup: str
    regime: str
    execution_status: str
    trade_reference: str | None
    source_id: str
    scores: tuple[DecisionStateScore, ...]
    outcomes: tuple[DecisionStateOutcome, ...]
    reason_codes: tuple[RecommendationReasonCode, ...]

    def __post_init__(self) -> None:
        decision_timestamp = require_utc_datetime(
            self.decision_timestamp, "decision_timestamp"
        )
        data_available_at = require_utc_datetime(
            self.data_available_at, "data_available_at"
        )
        if data_available_at > decision_timestamp:
            raise DecisionStateError(
                "data_available_at must be <= decision_timestamp"
            )
        _require_member(self.decision, DECISION_STATE_DECISIONS, "decision")
        _require_member(self.setup, DECISION_STATE_SETUPS, "setup")
        _require_member(self.regime, DECISION_STATE_REGIMES, "regime")
        _require_member(
            self.execution_status,
            DECISION_EXECUTION_STATUSES,
            "execution_status",
        )
        _non_empty(self.source_id, "source_id")
        if self.execution_status == TRADED:
            if self.trade_reference is None:
                raise DecisionStateError(
                    "a traded decision date requires a trade_reference"
                )
            _non_empty(self.trade_reference, "trade_reference")
        elif self.trade_reference is not None:
            raise DecisionStateError(
                "a not-traded decision date must not carry a trade_reference"
            )
        scores = tuple(self.scores)
        outcomes = tuple(self.outcomes)
        if any(not isinstance(item, DecisionStateScore) for item in scores):
            raise DecisionStateError("scores must contain DecisionStateScore values")
        if any(not isinstance(item, DecisionStateOutcome) for item in outcomes):
            raise DecisionStateError(
                "outcomes must contain DecisionStateOutcome values"
            )
        _reject_duplicates(
            tuple(item.score_name for item in scores), field_name="score_names"
        )
        _reject_duplicates(
            tuple(item.outcome_name for item in outcomes), field_name="outcome_names"
        )
        for score in scores:
            if score.available_at is not None and (
                score.available_at > decision_timestamp
            ):
                raise DecisionStateError(
                    "score provenance must not exceed the decision timestamp"
                )
        for outcome in outcomes:
            if outcome.outcome_time is not None and (
                outcome.outcome_time <= decision_timestamp
            ):
                raise DecisionStateError(
                    "outcome_time must be after the decision timestamp"
                )
        reason_codes = tuple(self.reason_codes)
        if any(
            not isinstance(item, RecommendationReasonCode) for item in reason_codes
        ):
            raise DecisionStateError(
                "reason_codes must contain RecommendationReasonCode values"
            )
        object.__setattr__(self, "decision_timestamp", decision_timestamp)
        object.__setattr__(self, "data_available_at", data_available_at)
        object.__setattr__(self, "scores", scores)
        object.__setattr__(self, "outcomes", outcomes)
        object.__setattr__(self, "reason_codes", reason_codes)

    @property
    def traded(self) -> bool:
        return self.execution_status == TRADED

    def score(self, score_name: str) -> DecisionStateScore:
        for item in self.scores:
            if item.score_name == score_name:
                return item
        raise KeyError(score_name)

    def outcome(self, outcome_name: str) -> DecisionStateOutcome:
        for item in self.outcomes:
            if item.outcome_name == outcome_name:
                return item
        raise KeyError(outcome_name)

    def as_record(self) -> dict[str, Any]:
        return {
            "decision_timestamp": self.decision_timestamp.isoformat(),
            "data_available_at": self.data_available_at.isoformat(),
            "decision": self.decision,
            "setup": self.setup,
            "regime": self.regime,
            "execution_status": self.execution_status,
            "trade_reference": self.trade_reference,
            "source_id": self.source_id,
            "scores": [item.as_record() for item in self.scores],
            "outcomes": [item.as_record() for item in self.outcomes],
            "reason_codes": [_reason_code_record(item) for item in self.reason_codes],
        }


@dataclass(frozen=True)
class DecisionStateCoverage:
    """Deterministic census proving traded and rejected dates are both kept."""

    decision_date_count: int
    traded_count: int
    not_traded_count: int
    decision_counts: dict[str, int]
    setup_counts: dict[str, int]
    regime_counts: dict[str, int]
    score_status_counts: dict[str, dict[str, int]]
    outcome_status_counts: dict[str, dict[str, int]]

    def as_record(self) -> dict[str, Any]:
        return {
            "decision_date_count": self.decision_date_count,
            "traded_count": self.traded_count,
            "not_traded_count": self.not_traded_count,
            "decision_counts": dict(self.decision_counts),
            "setup_counts": dict(self.setup_counts),
            "regime_counts": dict(self.regime_counts),
            "score_status_counts": {
                name: dict(counts)
                for name, counts in self.score_status_counts.items()
            },
            "outcome_status_counts": {
                name: dict(counts)
                for name, counts in self.outcome_status_counts.items()
            },
        }


@dataclass(frozen=True)
class DecisionStateStore:
    """Replayable BTC-190 market state for every decision date."""

    store_id: str
    evidence_digest: str
    feature_id: str
    policy_version: str
    definition: DecisionStateDefinition
    extraction_time: datetime
    config_metadata: dict[str, str]
    feature_definition: dict[str, Any]
    target_definition: dict[str, Any]
    feature_definition_fingerprint: str
    target_definition_fingerprint: str
    input_digest: str
    production_status: str
    promotion_ticket: str
    rows: tuple[DecisionStateRow, ...]
    coverage: DecisionStateCoverage
    reason_codes: tuple[str, ...]

    @property
    def decision_timestamps(self) -> tuple[datetime, ...]:
        return tuple(row.decision_timestamp for row in self.rows)

    def row(self, decision_timestamp: datetime) -> DecisionStateRow:
        wanted = require_utc_datetime(decision_timestamp, "decision_timestamp")
        for item in self.rows:
            if item.decision_timestamp == wanted:
                return item
        raise KeyError(wanted)

    def traded_rows(self) -> tuple[DecisionStateRow, ...]:
        return tuple(row for row in self.rows if row.traded)

    def rejected_rows(self) -> tuple[DecisionStateRow, ...]:
        """Return the decision dates that produced no trade."""

        return tuple(row for row in self.rows if not row.traded)

    def score_matrix(self) -> tuple[FloatArray, NDArray[np.bool_]]:
        """Return score values and their missing mask for NumPy consumers."""

        return _cell_matrix(
            [[item.value for item in row.scores] for row in self.rows],
            width=len(self.definition.score_names),
        )

    def outcome_matrix(self) -> tuple[FloatArray, NDArray[np.bool_]]:
        """Return outcome values and their missing mask for NumPy consumers."""

        return _cell_matrix(
            [[item.value for item in row.outcomes] for row in self.rows],
            width=len(self.definition.outcome_names),
        )

    def as_record(self) -> dict[str, Any]:
        """Return a deterministic, JSON-compatible persistence record."""

        _validate_store(self)
        payload = _store_payload(self)
        if _digest(payload) != self.evidence_digest:
            raise DecisionStateError("decision state evidence does not match digest")
        return {**payload, "evidence_digest": self.evidence_digest}


def build_decision_state_store(
    observations: Sequence[DecisionStateObservation],
    features: PointInTimeFeatureMatrix,
    targets: ForwardTargetMatrix,
    *,
    extraction_time: datetime,
    definition: DecisionStateDefinition | None = None,
) -> DecisionStateStore:
    """Join point-in-time state and forward outcomes for every decision date."""

    if not isinstance(features, PointInTimeFeatureMatrix):
        raise TypeError("features must be a PointInTimeFeatureMatrix")
    if not isinstance(targets, ForwardTargetMatrix):
        raise TypeError("targets must be a ForwardTargetMatrix")
    store_definition = definition or DecisionStateDefinition()
    if not isinstance(store_definition, DecisionStateDefinition):
        raise TypeError("definition must be a DecisionStateDefinition")
    recorded = tuple(observations)
    if any(
        not isinstance(item, DecisionStateObservation) for item in recorded
    ):
        raise TypeError("observations must be DecisionStateObservation values")
    extraction = require_utc_datetime(extraction_time, "extraction_time")

    ordered = tuple(sorted(recorded, key=lambda item: item.decision_timestamp))
    _validate_inputs(
        ordered,
        features,
        targets,
        definition=store_definition,
        extraction_time=extraction,
    )

    score_columns = tuple(
        features.definition.feature_names.index(name)
        for name in store_definition.score_names
    )
    outcome_columns = tuple(
        targets.definition.target_names.index(name)
        for name in store_definition.outcome_names
    )
    specifications = tuple(
        targets.definition.specification(name)
        for name in store_definition.outcome_names
    )

    rows = tuple(
        DecisionStateRow(
            decision_timestamp=observation.decision_timestamp,
            data_available_at=observation.data_available_at,
            decision=observation.decision,
            setup=observation.setup,
            regime=observation.regime,
            execution_status=observation.execution_status,
            trade_reference=observation.trade_reference,
            source_id=observation.source_id,
            scores=tuple(
                _score_cell(
                    features,
                    row_index=index,
                    column=column,
                    score_name=name,
                )
                for name, column in zip(
                    store_definition.score_names, score_columns, strict=True
                )
            ),
            outcomes=tuple(
                _outcome_cell(
                    targets,
                    row_index=index,
                    column=column,
                    outcome_name=name,
                    specification=specification,
                    decision_timestamp=observation.decision_timestamp,
                    extraction_time=extraction,
                )
                for name, column, specification in zip(
                    store_definition.outcome_names,
                    outcome_columns,
                    specifications,
                    strict=True,
                )
            ),
            reason_codes=observation.reason_codes,
        )
        for index, observation in enumerate(ordered)
    )

    input_digest = _digest(
        {
            "observations": [_observation_record(item) for item in ordered],
            "features": features.as_record(),
            "targets": targets.as_record(),
        }
    )
    store = DecisionStateStore(
        store_id="",
        evidence_digest="",
        feature_id=DECISION_STATE_FEATURE_ID,
        policy_version=DECISION_STATE_POLICY_VERSION,
        definition=store_definition,
        extraction_time=extraction,
        config_metadata=features.definition.provenance.as_record(),
        feature_definition=features.definition.as_record(),
        target_definition=targets.definition.as_record(),
        feature_definition_fingerprint=features.definition.fingerprint,
        target_definition_fingerprint=targets.definition.fingerprint,
        input_digest=input_digest,
        production_status=DECISION_STATE_PRODUCTION_STATUS,
        promotion_ticket=DECISION_STATE_PROMOTION_TICKET,
        rows=rows,
        coverage=_coverage(rows, store_definition),
        reason_codes=DECISION_STATE_REASON_CODES,
    )
    store = replace(store, store_id=_store_id(store))
    _validate_store(store, allow_empty_digest=True)
    return replace(store, evidence_digest=_digest(_store_payload(store)))


def restore_decision_state_store(record: Mapping[str, Any]) -> DecisionStateStore:
    """Restore persisted BTC-190 state and reject drift or tampering."""

    source = _mapping(record, "record")
    definition = _definition_from_record(
        _mapping(source.get("definition"), "definition")
    )
    rows = tuple(
        _row_from_record(_mapping(item, "row"))
        for item in _sequence(source.get("rows"), "rows")
    )
    store = DecisionStateStore(
        store_id=_string(source.get("store_id"), "store_id"),
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
        feature_definition=dict(
            _mapping(source.get("feature_definition"), "feature_definition")
        ),
        target_definition=dict(
            _mapping(source.get("target_definition"), "target_definition")
        ),
        feature_definition_fingerprint=_string(
            source.get("feature_definition_fingerprint"),
            "feature_definition_fingerprint",
        ),
        target_definition_fingerprint=_string(
            source.get("target_definition_fingerprint"),
            "target_definition_fingerprint",
        ),
        input_digest=_string(source.get("input_digest"), "input_digest"),
        production_status=_string(
            source.get("production_status"), "production_status"
        ),
        promotion_ticket=_string(source.get("promotion_ticket"), "promotion_ticket"),
        rows=rows,
        coverage=_coverage_from_record(
            _mapping(source.get("coverage"), "coverage")
        ),
        reason_codes=_string_tuple(source.get("reason_codes"), "reason_codes"),
    )
    _validate_row_columns(rows, definition)
    if store.coverage.as_record() != _coverage(rows, definition).as_record():
        raise DecisionStateError("coverage does not match the persisted rows")
    if store.as_record() != dict(source):
        raise DecisionStateError("record does not match reconstructed decision state")
    return store


def _score_cell(
    features: PointInTimeFeatureMatrix,
    *,
    row_index: int,
    column: int,
    score_name: str,
) -> DecisionStateScore:
    source_id = features.source_ids[row_index][column]
    raw = features.values[row_index, column]
    value = None if bool(np.isnan(raw)) else float(raw)
    if source_id is None:
        status = SCORE_NOT_OBSERVED
    elif value is None:
        status = SCORE_MISSING_VALUE
    else:
        status = SCORE_AVAILABLE
    return DecisionStateScore(
        score_name=score_name,
        status=status,
        value=value,
        observation_time=features.observation_times[row_index][column],
        available_at=features.available_ats[row_index][column],
        source_id=source_id,
        revision=features.revisions[row_index][column],
    )


def _outcome_cell(
    targets: ForwardTargetMatrix,
    *,
    row_index: int,
    column: int,
    outcome_name: str,
    specification: TargetSpecification,
    decision_timestamp: datetime,
    extraction_time: datetime,
) -> DecisionStateOutcome:
    source_id = targets.source_ids[row_index][column]
    if source_id is None:
        pending = (
            specification.horizon is not None
            and decision_timestamp + specification.horizon > extraction_time
        )
        return DecisionStateOutcome(
            outcome_name=outcome_name,
            status=OUTCOME_PENDING_HORIZON if pending else OUTCOME_NOT_RECORDED,
            value=None,
            outcome_time=None,
            available_at=None,
            source_id=None,
            revision=None,
        )
    raw = targets.values[row_index, column]
    value = None if bool(np.isnan(raw)) else float(raw)
    return DecisionStateOutcome(
        outcome_name=outcome_name,
        status=OUTCOME_MISSING_VALUE if value is None else OUTCOME_AVAILABLE,
        value=value,
        outcome_time=targets.outcome_times[row_index][column],
        available_at=targets.available_ats[row_index][column],
        source_id=source_id,
        revision=targets.revisions[row_index][column],
    )


def _coverage(
    rows: Sequence[DecisionStateRow],
    definition: DecisionStateDefinition,
) -> DecisionStateCoverage:
    decision_counts = dict.fromkeys(DECISION_STATE_DECISIONS, 0)
    setup_counts = dict.fromkeys(DECISION_STATE_SETUPS, 0)
    regime_counts = dict.fromkeys(DECISION_STATE_REGIMES, 0)
    score_status_counts = {
        name: dict.fromkeys(DECISION_STATE_SCORE_STATUSES, 0)
        for name in definition.score_names
    }
    outcome_status_counts = {
        name: dict.fromkeys(DECISION_STATE_OUTCOME_STATUSES, 0)
        for name in definition.outcome_names
    }
    traded = 0
    for row in rows:
        decision_counts[row.decision] += 1
        setup_counts[row.setup] += 1
        regime_counts[row.regime] += 1
        traded += 1 if row.traded else 0
        for score in row.scores:
            score_status_counts[score.score_name][score.status] += 1
        for outcome in row.outcomes:
            outcome_status_counts[outcome.outcome_name][outcome.status] += 1
    return DecisionStateCoverage(
        decision_date_count=len(rows),
        traded_count=traded,
        not_traded_count=len(rows) - traded,
        decision_counts=decision_counts,
        setup_counts=setup_counts,
        regime_counts=regime_counts,
        score_status_counts=score_status_counts,
        outcome_status_counts=outcome_status_counts,
    )


def _validate_inputs(
    observations: Sequence[DecisionStateObservation],
    features: PointInTimeFeatureMatrix,
    targets: ForwardTargetMatrix,
    *,
    definition: DecisionStateDefinition,
    extraction_time: datetime,
) -> None:
    if features.decision_timestamps != targets.decision_timestamps:
        raise DecisionStateError(
            "feature and target decision timestamps must match exactly"
        )
    grid = features.decision_timestamps
    recorded = tuple(item.decision_timestamp for item in observations)
    _reject_duplicates(recorded, field_name="decision timestamps")
    if recorded != grid:
        missing = sorted(set(grid) - set(recorded))
        extra = sorted(set(recorded) - set(grid))
        if missing:
            raise DecisionStateError(
                "every decision date requires a recorded decision state; missing "
                + ", ".join(value.isoformat() for value in missing)
            )
        raise DecisionStateError(
            "decision states outside the decision grid: "
            + ", ".join(value.isoformat() for value in extra)
        )
    if grid and extraction_time < grid[-1]:
        raise DecisionStateError(
            "extraction_time must be >= the last decision timestamp"
        )
    missing_scores = sorted(
        set(definition.score_names) - set(features.definition.feature_names)
    )
    if missing_scores:
        raise DecisionStateError(
            "feature matrix does not contain scores: " + ", ".join(missing_scores)
        )
    missing_outcomes = sorted(
        set(definition.outcome_names) - set(targets.definition.target_names)
    )
    if missing_outcomes:
        raise DecisionStateError(
            "target matrix does not contain outcomes: " + ", ".join(missing_outcomes)
        )
    if (
        targets.data_available_at is not None
        and targets.data_available_at != extraction_time
    ):
        raise DecisionStateError(
            "target matrix data_available_at must equal the extraction time"
        )
    provenance = features.definition.provenance
    for name in definition.outcome_names:
        specification = targets.definition.specification(name)
        if (
            specification.price_source_policy_version
            != provenance.price_source_policy_version
        ):
            raise DecisionStateError(
                "outcome price-source policy must match feature-matrix provenance"
            )
    for name in definition.outcome_names:
        column = targets.definition.target_names.index(name)
        for row_index in range(len(grid)):
            available_at = targets.available_ats[row_index][column]
            if available_at is not None and available_at > extraction_time:
                raise DecisionStateError(
                    f"{name} became available after the extraction time; rebuild "
                    "the forward-target matrix with that data_available_at cutoff"
                )


def _validate_row_columns(
    rows: Sequence[DecisionStateRow],
    definition: DecisionStateDefinition,
) -> None:
    for row in rows:
        if tuple(item.score_name for item in row.scores) != definition.score_names:
            raise DecisionStateError(
                "every row must carry the defined scores in definition order"
            )
        if tuple(item.outcome_name for item in row.outcomes) != (
            definition.outcome_names
        ):
            raise DecisionStateError(
                "every row must carry the defined outcomes in definition order"
            )


def _validate_store(
    store: DecisionStateStore,
    *,
    allow_empty_digest: bool = False,
) -> None:
    if not isinstance(store.definition, DecisionStateDefinition):
        raise DecisionStateError("definition must be a DecisionStateDefinition")
    expected = {
        "feature_id": DECISION_STATE_FEATURE_ID,
        "policy_version": DECISION_STATE_POLICY_VERSION,
        "production_status": DECISION_STATE_PRODUCTION_STATUS,
        "promotion_ticket": DECISION_STATE_PROMOTION_TICKET,
    }
    for field_name, value in expected.items():
        if getattr(store, field_name) != value:
            raise DecisionStateError(f"{field_name} must be {value!r}")
    if store.reason_codes != DECISION_STATE_REASON_CODES:
        raise DecisionStateError("reason_codes must be the BTC-190 reason codes")
    _non_empty(store.store_id, "store_id")
    if not allow_empty_digest:
        _non_empty(store.evidence_digest, "evidence_digest")
    _non_empty(store.input_digest, "input_digest")
    _non_empty(
        store.feature_definition_fingerprint, "feature_definition_fingerprint"
    )
    _non_empty(store.target_definition_fingerprint, "target_definition_fingerprint")
    require_utc_datetime(store.extraction_time, "extraction_time")
    if not isinstance(store.coverage, DecisionStateCoverage):
        raise DecisionStateError("coverage must be a DecisionStateCoverage")
    if any(not isinstance(row, DecisionStateRow) for row in store.rows):
        raise DecisionStateError("rows must contain DecisionStateRow values")
    timestamps = tuple(row.decision_timestamp for row in store.rows)
    _reject_duplicates(timestamps, field_name="decision timestamps")
    if list(timestamps) != sorted(timestamps):
        raise DecisionStateError("rows must be ordered by decision timestamp")
    if timestamps and store.extraction_time < timestamps[-1]:
        raise DecisionStateError(
            "extraction_time must be >= the last decision timestamp"
        )
    _validate_row_columns(store.rows, store.definition)
    for row in store.rows:
        for outcome in row.outcomes:
            if (
                outcome.available_at is not None
                and outcome.available_at > store.extraction_time
            ):
                raise DecisionStateError(
                    "outcome availability must not exceed the extraction time"
                )
    if store.coverage.as_record() != _coverage(
        store.rows, store.definition
    ).as_record():
        raise DecisionStateError("coverage does not match the persisted rows")
    if store.store_id != _store_id(store):
        raise DecisionStateError("store_id does not match the store identity")


def _store_identity(store: DecisionStateStore) -> dict[str, Any]:
    return {
        "feature_id": store.feature_id,
        "policy_version": store.policy_version,
        "definition": store.definition.as_record(),
        "extraction_time": store.extraction_time.isoformat(),
        "config_metadata": dict(store.config_metadata),
        "feature_definition_fingerprint": store.feature_definition_fingerprint,
        "target_definition_fingerprint": store.target_definition_fingerprint,
        "input_digest": store.input_digest,
    }


def _store_id(store: DecisionStateStore) -> str:
    return _digest(_store_identity(store))


def _store_payload(store: DecisionStateStore) -> dict[str, Any]:
    return {
        **_store_identity(store),
        "store_id": store.store_id,
        "feature_definition": dict(store.feature_definition),
        "target_definition": dict(store.target_definition),
        "production_status": store.production_status,
        "promotion_ticket": store.promotion_ticket,
        "rows": [row.as_record() for row in store.rows],
        "coverage": store.coverage.as_record(),
        "reason_codes": list(store.reason_codes),
    }


def _definition_payload(definition: DecisionStateDefinition) -> dict[str, Any]:
    return {
        "version": definition.version,
        "score_names": list(definition.score_names),
        "outcome_names": list(definition.outcome_names),
        "coverage_policy_version": definition.coverage_policy_version,
        "missing_value_policy_version": definition.missing_value_policy_version,
        "outcome_availability_policy_version": (
            definition.outcome_availability_policy_version
        ),
        "promotion_policy_version": definition.promotion_policy_version,
    }


def _observation_record(observation: DecisionStateObservation) -> dict[str, Any]:
    return {
        "decision_timestamp": observation.decision_timestamp.isoformat(),
        "data_available_at": observation.data_available_at.isoformat(),
        "decision": observation.decision,
        "setup": observation.setup,
        "regime": observation.regime,
        "execution_status": observation.execution_status,
        "trade_reference": observation.trade_reference,
        "source_id": observation.source_id,
        "reason_codes": [
            _reason_code_record(item) for item in observation.reason_codes
        ],
    }


def _reason_code_record(reason_code: RecommendationReasonCode) -> dict[str, str]:
    return {
        "code": reason_code.code,
        "source_component": reason_code.source_component,
        "severity": reason_code.severity,
        "detail": reason_code.detail,
    }


def _definition_from_record(record: Mapping[str, Any]) -> DecisionStateDefinition:
    definition = DecisionStateDefinition(
        version=_string(record.get("version"), "version"),
        score_names=_string_tuple(record.get("score_names"), "score_names"),
        outcome_names=_string_tuple(record.get("outcome_names"), "outcome_names"),
        coverage_policy_version=_string(
            record.get("coverage_policy_version"), "coverage_policy_version"
        ),
        missing_value_policy_version=_string(
            record.get("missing_value_policy_version"),
            "missing_value_policy_version",
        ),
        outcome_availability_policy_version=_string(
            record.get("outcome_availability_policy_version"),
            "outcome_availability_policy_version",
        ),
        promotion_policy_version=_string(
            record.get("promotion_policy_version"), "promotion_policy_version"
        ),
    )
    if definition.as_record() != dict(record):
        raise DecisionStateError("definition record does not match its fingerprint")
    return definition


def _row_from_record(record: Mapping[str, Any]) -> DecisionStateRow:
    return DecisionStateRow(
        decision_timestamp=_utc_from_record(
            record.get("decision_timestamp"), "decision_timestamp"
        ),
        data_available_at=_utc_from_record(
            record.get("data_available_at"), "data_available_at"
        ),
        decision=_string(record.get("decision"), "decision"),
        setup=_string(record.get("setup"), "setup"),
        regime=_string(record.get("regime"), "regime"),
        execution_status=_string(
            record.get("execution_status"), "execution_status"
        ),
        trade_reference=_optional_string(
            record.get("trade_reference"), "trade_reference"
        ),
        source_id=_string(record.get("source_id"), "source_id"),
        scores=tuple(
            _score_from_record(_mapping(item, "score"))
            for item in _sequence(record.get("scores"), "scores")
        ),
        outcomes=tuple(
            _outcome_from_record(_mapping(item, "outcome"))
            for item in _sequence(record.get("outcomes"), "outcomes")
        ),
        reason_codes=tuple(
            _reason_code_from_record(_mapping(item, "reason_code"))
            for item in _sequence(record.get("reason_codes"), "reason_codes")
        ),
    )


def _score_from_record(record: Mapping[str, Any]) -> DecisionStateScore:
    return DecisionStateScore(
        score_name=_string(record.get("score_name"), "score_name"),
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


def _outcome_from_record(record: Mapping[str, Any]) -> DecisionStateOutcome:
    return DecisionStateOutcome(
        outcome_name=_string(record.get("outcome_name"), "outcome_name"),
        status=_string(record.get("status"), "status"),
        value=_optional_float(record.get("value"), "value"),
        outcome_time=_optional_utc_from_record(
            record.get("outcome_time"), "outcome_time"
        ),
        available_at=_optional_utc_from_record(
            record.get("available_at"), "available_at"
        ),
        source_id=_optional_string(record.get("source_id"), "source_id"),
        revision=_optional_non_negative_integer(record.get("revision"), "revision"),
    )


def _reason_code_from_record(record: Mapping[str, Any]) -> RecommendationReasonCode:
    return RecommendationReasonCode(
        code=_string(record.get("code"), "code"),
        source_component=_string(
            record.get("source_component"), "source_component"
        ),
        severity=_string(record.get("severity"), "severity"),
        detail=_string(record.get("detail"), "detail"),
    )


def _coverage_from_record(record: Mapping[str, Any]) -> DecisionStateCoverage:
    return DecisionStateCoverage(
        decision_date_count=_non_negative_integer(
            record.get("decision_date_count"), "decision_date_count"
        ),
        traded_count=_non_negative_integer(
            record.get("traded_count"), "traded_count"
        ),
        not_traded_count=_non_negative_integer(
            record.get("not_traded_count"), "not_traded_count"
        ),
        decision_counts=_count_mapping(
            record.get("decision_counts"), "decision_counts"
        ),
        setup_counts=_count_mapping(record.get("setup_counts"), "setup_counts"),
        regime_counts=_count_mapping(record.get("regime_counts"), "regime_counts"),
        score_status_counts=_nested_count_mapping(
            record.get("score_status_counts"), "score_status_counts"
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


def _validate_cell_value(value: float | None, field_name: str) -> None:
    if value is None:
        return
    if isinstance(value, bool) or not isinstance(value, float | int):
        raise DecisionStateError(f"{field_name} must be a real number")
    if not np.isfinite(value):
        raise DecisionStateError(f"{field_name} must be finite")


def _validate_cell_provenance(
    *,
    observed: bool,
    times: Sequence[tuple[datetime | None, str]],
    available_at: datetime | None,
    source_id: str | None,
    revision: int | None,
) -> None:
    provenance: list[Any] = [available_at, source_id, revision]
    provenance.extend(value for value, _ in times)
    if observed:
        if any(value is None for value in provenance):
            raise DecisionStateError("recorded cells require complete provenance")
        for value, field_name in times:
            assert value is not None
            require_utc_datetime(value, field_name)
        assert available_at is not None
        require_utc_datetime(available_at, "available_at")
        _non_empty(source_id, "source_id")
        assert revision is not None
        _non_negative_integer(revision, "revision")
        return
    if any(value is not None for value in provenance):
        raise DecisionStateError("unrecorded cells must not carry provenance")


def _validate_names(values: Sequence[str], *, field_name: str) -> tuple[str, ...]:
    names = tuple(values)
    if not names:
        raise DecisionStateError(f"{field_name} must not be empty")
    for name in names:
        _non_empty(name, field_name)
    _reject_duplicates(names, field_name=field_name)
    return names


def _reject_duplicates(values: Sequence[Any], *, field_name: str) -> None:
    if len(set(values)) != len(values):
        raise DecisionStateError(f"{field_name} must be unique")


def _require_member(value: Any, allowed: Sequence[str], field_name: str) -> str:
    if not isinstance(value, str) or value not in allowed:
        raise DecisionStateError(
            f"{field_name} must be one of: " + ", ".join(allowed)
        )
    return value


def _non_empty(value: Any, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DecisionStateError(f"{field_name} must be a non-empty string")
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
        raise DecisionStateError(f"{field_name} must be a real number")
    return float(value)


def _non_negative_integer(value: Any, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise DecisionStateError(f"{field_name} must be a non-negative integer")
    return value


def _optional_non_negative_integer(value: Any, field_name: str) -> int | None:
    if value is None:
        return None
    return _non_negative_integer(value, field_name)


def _mapping(value: Any, field_name: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DecisionStateError(f"{field_name} must be a mapping")
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
        raise DecisionStateError(f"{field_name} must be a sequence")
    return tuple(value)


def _string_tuple(value: Any, field_name: str) -> tuple[str, ...]:
    return tuple(_non_empty(item, field_name) for item in _sequence(value, field_name))


def _utc_from_record(value: Any, field_name: str) -> datetime:
    if not isinstance(value, str):
        raise DecisionStateError(f"{field_name} must be an ISO-8601 string")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise DecisionStateError(f"{field_name} must be an ISO-8601 string") from error
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
    "DECISION_EXECUTION_STATUSES",
    "DECISION_STATE_COVERAGE_POLICY_VERSION",
    "DECISION_STATE_DECISIONS",
    "DECISION_STATE_FEATURE_ID",
    "DECISION_STATE_MISSING_VALUE_POLICY_VERSION",
    "DECISION_STATE_OUTCOME_AVAILABILITY_POLICY_VERSION",
    "DECISION_STATE_OUTCOME_NAMES",
    "DECISION_STATE_OUTCOME_STATUSES",
    "DECISION_STATE_POLICY_VERSION",
    "DECISION_STATE_PRODUCTION_STATUS",
    "DECISION_STATE_PROMOTION_POLICY_VERSION",
    "DECISION_STATE_PROMOTION_TICKET",
    "DECISION_STATE_REASON_CODES",
    "DECISION_STATE_REGIMES",
    "DECISION_STATE_SCORE_NAMES",
    "DECISION_STATE_SCORE_STATUSES",
    "DECISION_STATE_SETUPS",
    "NOT_TRADED",
    "NO_SETUP",
    "OUTCOME_AVAILABLE",
    "OUTCOME_MISSING_VALUE",
    "OUTCOME_NOT_RECORDED",
    "OUTCOME_PENDING_HORIZON",
    "SCORE_AVAILABLE",
    "SCORE_MISSING_VALUE",
    "SCORE_NOT_OBSERVED",
    "TRADED",
    "UNCLASSIFIED_REGIME",
    "DecisionStateCoverage",
    "DecisionStateDefinition",
    "DecisionStateError",
    "DecisionStateObservation",
    "DecisionStateOutcome",
    "DecisionStateRow",
    "DecisionStateScore",
    "DecisionStateStore",
    "build_decision_state_store",
    "restore_decision_state_store",
]
