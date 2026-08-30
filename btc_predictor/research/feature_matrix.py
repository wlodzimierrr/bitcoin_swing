"""Point-in-time feature and forward-target matrices for quantitative research."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from itertools import pairwise
from typing import Any

import numpy as np
from numpy.typing import NDArray

from btc_predictor.quant.arrays import FloatArray, as_float64_matrix

FEATURE_MATRIX_VERSION = "POINT_IN_TIME_FEATURE_MATRIX_V1"
FORWARD_TARGET_MATRIX_VERSION = "FORWARD_TARGET_MATRIX_V1"

# Frozen numeric research schema. Categorical states remain outside X until an
# encoding policy is versioned explicitly.
INITIAL_FEATURE_NAMES = (
    "TREND_SCORE",
    "FLOW_SCORE",
    "POSITIONING_SCORE",
    "VOLATILITY_SCORE",
    "STRUCTURE_SCORE",
    "REGIME_SCORE",
    "REGIME_SMOOTHED_SCORE",
    "ORDERLINESS_SCORE",
    "MOMENTUM_4W",
    "MOMENTUM_12W",
    "MA_DISTANCE_20W",
    "HIGH_DISTANCE_52W",
    "ETF_NORM_5D",
    "ETF_NORM_20D",
    "FLOW_ACCEL",
    "CVD_SPREAD",
    "SPOT_DOMINANCE",
    "FUNDING_7D_AVG",
    "FUNDING_ZSCORE_180D",
    "FUNDING_HEALTH",
    "OI_GROWTH_7D",
    "OI_GROWTH_ZSCORE_180D",
    "OI_GROWTH_HEALTH",
    "OI_INTENSITY",
    "OI_INTENSITY_PERCENTILE_180D",
    "FUTURES_BASIS_AVG",
    "FUTURES_BASIS_ZSCORE_180D",
    "FUTURES_BASIS_HEALTH",
    "RV_7",
    "RV_20",
    "RV_60",
    "VOL_COMPRESSION_RATIO",
    "VOL_PERCENTILE_2Y",
)

FORWARD_TARGET_NAMES = (
    "future_1w_return",
    "future_2w_return",
    "future_4w_return",
    "future_8w_return",
    "future_MFE",
    "future_MAE",
    "hit_2R_before_1R",
)
BINARY_FORWARD_TARGET_NAMES = ("hit_2R_before_1R",)

type NumericValue = float | int | Decimal | np.floating[Any] | None
type TimestampCells = tuple[tuple[datetime | None, ...], ...]
type SourceCells = tuple[tuple[str | None, ...], ...]


class FeatureMatrixError(ValueError):
    """Raised when research-matrix inputs violate the frozen data contract."""


@dataclass(frozen=True)
class FeatureMatrixDefinition:
    """Versioned feature names whose order defines matrix columns."""

    feature_names: tuple[str, ...] = INITIAL_FEATURE_NAMES
    version: str = FEATURE_MATRIX_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "feature_names",
            _validate_names(self.feature_names, field_name="feature_names"),
        )
        _require_non_empty_string(self.version, "version")

    @property
    def fingerprint(self) -> str:
        return _definition_fingerprint(
            version=self.version,
            names=self.feature_names,
            names_field="feature_names",
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "feature_names": list(self.feature_names),
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class ForwardTargetDefinition:
    """Versioned target names kept physically separate from feature columns."""

    target_names: tuple[str, ...] = FORWARD_TARGET_NAMES
    version: str = FORWARD_TARGET_MATRIX_VERSION

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "target_names",
            _validate_names(self.target_names, field_name="target_names"),
        )
        _require_non_empty_string(self.version, "version")

    @property
    def fingerprint(self) -> str:
        return _definition_fingerprint(
            version=self.version,
            names=self.target_names,
            names_field="target_names",
        )

    def as_record(self) -> dict[str, Any]:
        return {
            "version": self.version,
            "target_names": list(self.target_names),
            "fingerprint": self.fingerprint,
        }


@dataclass(frozen=True)
class FeatureObservation:
    """A numeric feature value and the times needed for as-of selection."""

    feature_name: str
    value: NumericValue
    observation_time: datetime
    available_at: datetime
    source_id: str
    revision: int = 0

    def __post_init__(self) -> None:
        _require_non_empty_string(self.feature_name, "feature_name")
        _require_non_empty_string(self.source_id, "source_id")
        observation_time = _require_utc(self.observation_time, "observation_time")
        available_at = _require_utc(self.available_at, "available_at")
        if available_at < observation_time:
            raise FeatureMatrixError("available_at must be >= observation_time")
        object.__setattr__(self, "observation_time", observation_time)
        object.__setattr__(self, "available_at", available_at)
        object.__setattr__(self, "value", _normalize_value(self.value, "value"))
        _validate_revision(self.revision)


@dataclass(frozen=True)
class ForwardTargetObservation:
    """A future label associated with one earlier decision timestamp."""

    target_name: str
    value: NumericValue | bool
    decision_timestamp: datetime
    outcome_time: datetime
    available_at: datetime
    source_id: str
    revision: int = 0

    def __post_init__(self) -> None:
        _require_non_empty_string(self.target_name, "target_name")
        _require_non_empty_string(self.source_id, "source_id")
        decision_timestamp = _require_utc(
            self.decision_timestamp,
            "decision_timestamp",
        )
        outcome_time = _require_utc(self.outcome_time, "outcome_time")
        available_at = _require_utc(self.available_at, "available_at")
        if outcome_time <= decision_timestamp:
            raise FeatureMatrixError("outcome_time must be after decision_timestamp")
        if available_at < outcome_time:
            raise FeatureMatrixError("available_at must be >= outcome_time")
        value = _normalize_target_value(self.target_name, self.value)
        object.__setattr__(self, "decision_timestamp", decision_timestamp)
        object.__setattr__(self, "outcome_time", outcome_time)
        object.__setattr__(self, "available_at", available_at)
        object.__setattr__(self, "value", value)
        _validate_revision(self.revision)


@dataclass(frozen=True)
class PointInTimeFeatureMatrix:
    """Immutable matrix X[t, f] with cell-level availability provenance."""

    definition: FeatureMatrixDefinition
    decision_timestamps: tuple[datetime, ...]
    values: FloatArray
    missing_mask: NDArray[np.bool_]
    observation_times: TimestampCells
    available_ats: TimestampCells
    source_ids: SourceCells

    def __post_init__(self) -> None:
        if not isinstance(self.definition, FeatureMatrixDefinition):
            raise FeatureMatrixError("definition must be a FeatureMatrixDefinition")
        timestamps = _validate_matrix_timestamps(self.decision_timestamps)
        expected_shape = (len(timestamps), len(self.definition.feature_names))
        values = _readonly_values(self.values, expected_shape=expected_shape)
        missing_mask = _readonly_missing_mask(
            self.missing_mask,
            values=values,
            expected_shape=expected_shape,
        )
        observation_times = _validate_timestamp_cells(
            self.observation_times,
            field_name="observation_times",
            expected_shape=expected_shape,
        )
        available_ats = _validate_timestamp_cells(
            self.available_ats,
            field_name="available_ats",
            expected_shape=expected_shape,
        )
        source_ids = _validate_source_cells(
            self.source_ids,
            expected_shape=expected_shape,
        )
        _validate_feature_provenance(
            timestamps,
            values,
            observation_times,
            available_ats,
            source_ids,
        )
        object.__setattr__(self, "decision_timestamps", timestamps)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "missing_mask", missing_mask)
        object.__setattr__(self, "observation_times", observation_times)
        object.__setattr__(self, "available_ats", available_ats)
        object.__setattr__(self, "source_ids", source_ids)

    def to_numpy(self, *, copy: bool = True) -> FloatArray:
        """Return X as float64; the zero-copy form is read-only."""

        if copy:
            return np.array(self.values, dtype=np.float64, order="C", copy=True)
        return self.values

    def as_record(self) -> dict[str, Any]:
        """Return a deterministic, JSON-compatible persistence record."""

        return {
            "definition": self.definition.as_record(),
            "decision_timestamps": [
                value.isoformat() for value in self.decision_timestamps
            ],
            "values": _serializable_values(self.values),
            "missing_mask": self.missing_mask.tolist(),
            "observation_times": _serializable_timestamp_cells(self.observation_times),
            "available_ats": _serializable_timestamp_cells(self.available_ats),
            "source_ids": [list(row) for row in self.source_ids],
        }


@dataclass(frozen=True)
class ForwardTargetMatrix:
    """Immutable future-label matrix Y kept outside contemporaneous X."""

    definition: ForwardTargetDefinition
    decision_timestamps: tuple[datetime, ...]
    values: FloatArray
    missing_mask: NDArray[np.bool_]
    outcome_times: TimestampCells
    available_ats: TimestampCells
    source_ids: SourceCells

    def __post_init__(self) -> None:
        if not isinstance(self.definition, ForwardTargetDefinition):
            raise FeatureMatrixError("definition must be a ForwardTargetDefinition")
        timestamps = _validate_matrix_timestamps(self.decision_timestamps)
        expected_shape = (len(timestamps), len(self.definition.target_names))
        values = _readonly_values(self.values, expected_shape=expected_shape)
        missing_mask = _readonly_missing_mask(
            self.missing_mask,
            values=values,
            expected_shape=expected_shape,
        )
        outcome_times = _validate_timestamp_cells(
            self.outcome_times,
            field_name="outcome_times",
            expected_shape=expected_shape,
        )
        available_ats = _validate_timestamp_cells(
            self.available_ats,
            field_name="available_ats",
            expected_shape=expected_shape,
        )
        source_ids = _validate_source_cells(
            self.source_ids,
            expected_shape=expected_shape,
        )
        _validate_target_provenance(
            timestamps,
            values,
            outcome_times,
            available_ats,
            source_ids,
        )
        object.__setattr__(self, "decision_timestamps", timestamps)
        object.__setattr__(self, "values", values)
        object.__setattr__(self, "missing_mask", missing_mask)
        object.__setattr__(self, "outcome_times", outcome_times)
        object.__setattr__(self, "available_ats", available_ats)
        object.__setattr__(self, "source_ids", source_ids)

    def to_numpy(self, *, copy: bool = True) -> FloatArray:
        """Return Y as float64; the zero-copy form is read-only."""

        if copy:
            return np.array(self.values, dtype=np.float64, order="C", copy=True)
        return self.values

    def as_record(self) -> dict[str, Any]:
        """Return a deterministic, JSON-compatible persistence record."""

        return {
            "definition": self.definition.as_record(),
            "decision_timestamps": [
                value.isoformat() for value in self.decision_timestamps
            ],
            "values": _serializable_values(self.values),
            "missing_mask": self.missing_mask.tolist(),
            "outcome_times": _serializable_timestamp_cells(self.outcome_times),
            "available_ats": _serializable_timestamp_cells(self.available_ats),
            "source_ids": [list(row) for row in self.source_ids],
        }


def decision_timestamp_range(
    start: datetime,
    end: datetime,
    *,
    step: timedelta = timedelta(days=1),
) -> tuple[datetime, ...]:
    """Generate an inclusive, deterministic UTC decision-time range."""

    start = _require_utc(start, "start")
    end = _require_utc(end, "end")
    if end < start:
        raise FeatureMatrixError("end must be >= start")
    if not isinstance(step, timedelta) or step <= timedelta(0):
        raise FeatureMatrixError("step must be a positive timedelta")
    output: list[datetime] = []
    current = start
    while current <= end:
        output.append(current)
        if end - current < step:
            break
        current += step
    return tuple(output)


def build_point_in_time_feature_matrix(
    observations: Iterable[FeatureObservation],
    decision_timestamps: Iterable[datetime],
    *,
    definition: FeatureMatrixDefinition | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
) -> PointInTimeFeatureMatrix:
    """Build X using only observations available by each decision timestamp."""

    matrix_definition = definition or FeatureMatrixDefinition()
    if not isinstance(matrix_definition, FeatureMatrixDefinition):
        raise FeatureMatrixError("definition must be a FeatureMatrixDefinition")
    timestamps = _select_decision_timestamps(
        decision_timestamps,
        start=start,
        end=end,
    )
    rows = _feature_observations(observations)
    relevant_names = set(matrix_definition.feature_names)
    relevant = tuple(row for row in rows if row.feature_name in relevant_names)
    _reject_duplicate_feature_observations(relevant)

    shape = (len(timestamps), len(matrix_definition.feature_names))
    values = np.full(shape, np.nan, dtype=np.float64)
    observation_times = _empty_timestamp_cells(shape)
    available_ats = _empty_timestamp_cells(shape)
    source_ids = _empty_source_cells(shape)
    grouped = _group_feature_observations(relevant)

    for column, feature_name in enumerate(matrix_definition.feature_names):
        events = sorted(
            grouped.get(feature_name, ()),
            key=lambda row: (
                row.available_at,
                row.observation_time,
                row.revision,
                row.source_id,
            ),
        )
        selected: FeatureObservation | None = None
        cursor = 0
        for row_index, decision_time in enumerate(timestamps):
            while cursor < len(events) and events[cursor].available_at <= decision_time:
                candidate = events[cursor]
                if selected is None or _feature_selection_key(
                    candidate
                ) > _feature_selection_key(selected):
                    selected = candidate
                cursor += 1
            if selected is None:
                continue
            if selected.value is not None:
                values[row_index, column] = selected.value
            observation_times[row_index][column] = selected.observation_time
            available_ats[row_index][column] = selected.available_at
            source_ids[row_index][column] = selected.source_id

    return PointInTimeFeatureMatrix(
        definition=matrix_definition,
        decision_timestamps=timestamps,
        values=values,
        missing_mask=np.isnan(values),
        observation_times=_freeze_cells(observation_times),
        available_ats=_freeze_cells(available_ats),
        source_ids=_freeze_cells(source_ids),
    )


def build_forward_target_matrix(
    observations: Iterable[ForwardTargetObservation],
    decision_timestamps: Iterable[datetime],
    *,
    definition: ForwardTargetDefinition | None = None,
    start: datetime | None = None,
    end: datetime | None = None,
    data_available_at: datetime | None = None,
) -> ForwardTargetMatrix:
    """Build Y from exact decision-time labels, optionally as of an extraction time."""

    matrix_definition = definition or ForwardTargetDefinition()
    if not isinstance(matrix_definition, ForwardTargetDefinition):
        raise FeatureMatrixError("definition must be a ForwardTargetDefinition")
    timestamps = _select_decision_timestamps(
        decision_timestamps,
        start=start,
        end=end,
    )
    cutoff = (
        None
        if data_available_at is None
        else _require_utc(data_available_at, "data_available_at")
    )
    rows = _target_observations(observations)
    relevant_names = set(matrix_definition.target_names)
    relevant_timestamps = set(timestamps)
    relevant = tuple(
        row
        for row in rows
        if row.target_name in relevant_names
        and row.decision_timestamp in relevant_timestamps
        and (cutoff is None or row.available_at <= cutoff)
    )
    _reject_duplicate_target_observations(relevant)

    shape = (len(timestamps), len(matrix_definition.target_names))
    values = np.full(shape, np.nan, dtype=np.float64)
    outcome_times = _empty_timestamp_cells(shape)
    available_ats = _empty_timestamp_cells(shape)
    source_ids = _empty_source_cells(shape)
    row_indexes = {timestamp: index for index, timestamp in enumerate(timestamps)}
    column_indexes = {
        name: index for index, name in enumerate(matrix_definition.target_names)
    }
    selected: dict[tuple[datetime, str], ForwardTargetObservation] = {}
    for row in relevant:
        key = (row.decision_timestamp, row.target_name)
        existing = selected.get(key)
        if existing is None or _target_selection_key(row) > _target_selection_key(
            existing
        ):
            selected[key] = row
    for (decision_time, target_name), row in selected.items():
        row_index = row_indexes[decision_time]
        column = column_indexes[target_name]
        if row.value is not None:
            values[row_index, column] = row.value
        outcome_times[row_index][column] = row.outcome_time
        available_ats[row_index][column] = row.available_at
        source_ids[row_index][column] = row.source_id

    return ForwardTargetMatrix(
        definition=matrix_definition,
        decision_timestamps=timestamps,
        values=values,
        missing_mask=np.isnan(values),
        outcome_times=_freeze_cells(outcome_times),
        available_ats=_freeze_cells(available_ats),
        source_ids=_freeze_cells(source_ids),
    )


def _feature_observations(
    observations: Iterable[FeatureObservation],
) -> tuple[FeatureObservation, ...]:
    rows = tuple(observations)
    if any(not isinstance(row, FeatureObservation) for row in rows):
        raise FeatureMatrixError(
            "feature observations must be FeatureObservation values"
        )
    return rows


def _target_observations(
    observations: Iterable[ForwardTargetObservation],
) -> tuple[ForwardTargetObservation, ...]:
    rows = tuple(observations)
    if any(not isinstance(row, ForwardTargetObservation) for row in rows):
        raise FeatureMatrixError(
            "target observations must be ForwardTargetObservation values"
        )
    return rows


def _group_feature_observations(
    observations: Sequence[FeatureObservation],
) -> dict[str, list[FeatureObservation]]:
    grouped: dict[str, list[FeatureObservation]] = {}
    for row in observations:
        grouped.setdefault(row.feature_name, []).append(row)
    return grouped


def _reject_duplicate_feature_observations(
    observations: Sequence[FeatureObservation],
) -> None:
    seen: set[tuple[str, datetime, datetime, int]] = set()
    for row in observations:
        identity = (
            row.feature_name,
            row.observation_time,
            row.available_at,
            row.revision,
        )
        if identity in seen:
            raise FeatureMatrixError("duplicate feature observation identity")
        seen.add(identity)


def _reject_duplicate_target_observations(
    observations: Sequence[ForwardTargetObservation],
) -> None:
    seen: set[tuple[str, datetime, datetime, datetime, int]] = set()
    for row in observations:
        identity = (
            row.target_name,
            row.decision_timestamp,
            row.outcome_time,
            row.available_at,
            row.revision,
        )
        if identity in seen:
            raise FeatureMatrixError("duplicate target observation identity")
        seen.add(identity)


def _feature_selection_key(row: FeatureObservation) -> tuple[datetime, datetime, int]:
    return row.observation_time, row.available_at, row.revision


def _target_selection_key(
    row: ForwardTargetObservation,
) -> tuple[datetime, int, datetime]:
    return row.available_at, row.revision, row.outcome_time


def _select_decision_timestamps(
    decision_timestamps: Iterable[datetime],
    *,
    start: datetime | None,
    end: datetime | None,
) -> tuple[datetime, ...]:
    normalized = tuple(
        _require_utc(value, "decision_timestamp") for value in decision_timestamps
    )
    if len(set(normalized)) != len(normalized):
        raise FeatureMatrixError("decision timestamps must be unique")
    start_value = None if start is None else _require_utc(start, "start")
    end_value = None if end is None else _require_utc(end, "end")
    if start_value is not None and end_value is not None and end_value < start_value:
        raise FeatureMatrixError("end must be >= start")
    return tuple(
        value
        for value in sorted(normalized)
        if (start_value is None or value >= start_value)
        and (end_value is None or value <= end_value)
    )


def _validate_matrix_timestamps(values: Sequence[datetime]) -> tuple[datetime, ...]:
    timestamps = tuple(_require_utc(value, "decision_timestamp") for value in values)
    if any(right <= left for left, right in pairwise(timestamps)):
        raise FeatureMatrixError("decision timestamps must be strictly increasing")
    return timestamps


def _validate_names(values: Sequence[str], *, field_name: str) -> tuple[str, ...]:
    if isinstance(values, (str, bytes)):
        raise FeatureMatrixError(f"{field_name} must be a sequence of names")
    names = tuple(values)
    if not names:
        raise FeatureMatrixError(f"{field_name} must contain at least one name")
    for name in names:
        _require_non_empty_string(name, field_name)
    if len(set(names)) != len(names):
        raise FeatureMatrixError(f"{field_name} must be unique")
    return names


def _definition_fingerprint(
    *,
    version: str,
    names: Sequence[str],
    names_field: str,
) -> str:
    payload = json.dumps(
        {"version": version, names_field: list(names)},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalize_value(value: NumericValue, field_name: str) -> float | None:
    if value is None:
        return None
    if isinstance(value, (bool, np.bool_)):
        raise FeatureMatrixError(f"{field_name} must not be boolean")
    try:
        normalized = np.float64(value)
    except (TypeError, ValueError, OverflowError) as error:
        raise FeatureMatrixError(f"{field_name} must be float64-compatible") from error
    if not np.isfinite(normalized):
        raise FeatureMatrixError(f"{field_name} must be finite or None")
    return float(normalized)


def _normalize_target_value(
    target_name: str,
    value: NumericValue | bool,
) -> float | None:
    if target_name in BINARY_FORWARD_TARGET_NAMES and isinstance(
        value,
        (bool, np.bool_),
    ):
        return float(value)
    normalized = _normalize_value(value, "value")
    if (
        target_name in BINARY_FORWARD_TARGET_NAMES
        and normalized is not None
        and normalized not in (0.0, 1.0)
    ):
        raise FeatureMatrixError(f"{target_name} must be binary")
    return normalized


def _validate_revision(value: int) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise FeatureMatrixError("revision must be a non-negative integer")


def _require_non_empty_string(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise FeatureMatrixError(f"{field_name} must be a non-empty string")
    return value


def _require_utc(value: datetime, field_name: str) -> datetime:
    if (
        not isinstance(value, datetime)
        or value.tzinfo is None
        or value.utcoffset() is None
    ):
        raise FeatureMatrixError(f"{field_name} must be timezone-aware UTC")
    if value.utcoffset() != timedelta(0):
        raise FeatureMatrixError(f"{field_name} must be UTC")
    return value.astimezone(UTC)


def _readonly_values(values: Any, *, expected_shape: tuple[int, int]) -> FloatArray:
    try:
        output = as_float64_matrix(
            values,
            allow_empty=True,
            nan_policy="propagate",
        )
    except ValueError as error:
        raise FeatureMatrixError(str(error)) from error
    if output.shape != expected_shape:
        raise FeatureMatrixError(f"values must have shape {expected_shape}")
    output.setflags(write=False)
    return output


def _readonly_missing_mask(
    missing_mask: Any,
    *,
    values: FloatArray,
    expected_shape: tuple[int, int],
) -> NDArray[np.bool_]:
    mask = np.asarray(missing_mask)
    if mask.dtype.kind != "b" or mask.shape != expected_shape:
        raise FeatureMatrixError(
            f"missing_mask must be boolean with shape {expected_shape}"
        )
    output = np.array(mask, dtype=np.bool_, order="C", copy=True)
    if not np.array_equal(output, np.isnan(values)):
        raise FeatureMatrixError("missing_mask must exactly identify NaN values")
    output.setflags(write=False)
    return output


def _validate_timestamp_cells(
    values: Sequence[Sequence[datetime | None]],
    *,
    field_name: str,
    expected_shape: tuple[int, int],
) -> TimestampCells:
    rows = tuple(tuple(row) for row in values)
    if len(rows) != expected_shape[0] or any(
        len(row) != expected_shape[1] for row in rows
    ):
        raise FeatureMatrixError(f"{field_name} must have shape {expected_shape}")
    return tuple(
        tuple(
            None if value is None else _require_utc(value, field_name) for value in row
        )
        for row in rows
    )


def _validate_source_cells(
    values: Sequence[Sequence[str | None]],
    *,
    expected_shape: tuple[int, int],
) -> SourceCells:
    rows = tuple(tuple(row) for row in values)
    if len(rows) != expected_shape[0] or any(
        len(row) != expected_shape[1] for row in rows
    ):
        raise FeatureMatrixError(f"source_ids must have shape {expected_shape}")
    for row in rows:
        for value in row:
            if value is not None:
                _require_non_empty_string(value, "source_id")
    return rows


def _validate_feature_provenance(
    decision_timestamps: Sequence[datetime],
    values: FloatArray,
    observation_times: TimestampCells,
    available_ats: TimestampCells,
    source_ids: SourceCells,
) -> None:
    for row_index, decision_time in enumerate(decision_timestamps):
        for column in range(values.shape[1]):
            observation_time = observation_times[row_index][column]
            available_at = available_ats[row_index][column]
            source_id = source_ids[row_index][column]
            provenance = (observation_time, available_at, source_id)
            if any(value is None for value in provenance):
                if not all(value is None for value in provenance):
                    raise FeatureMatrixError(
                        "feature provenance cells must be complete"
                    )
                if not np.isnan(values[row_index, column]):
                    raise FeatureMatrixError(
                        "present feature values require provenance"
                    )
                continue
            assert observation_time is not None
            assert available_at is not None
            if observation_time > decision_time or available_at > decision_time:
                raise FeatureMatrixError(
                    "feature provenance must not exceed decision time"
                )
            if available_at < observation_time:
                raise FeatureMatrixError("available_at must be >= observation_time")


def _validate_target_provenance(
    decision_timestamps: Sequence[datetime],
    values: FloatArray,
    outcome_times: TimestampCells,
    available_ats: TimestampCells,
    source_ids: SourceCells,
) -> None:
    for row_index, decision_time in enumerate(decision_timestamps):
        for column in range(values.shape[1]):
            outcome_time = outcome_times[row_index][column]
            available_at = available_ats[row_index][column]
            source_id = source_ids[row_index][column]
            provenance = (outcome_time, available_at, source_id)
            if any(value is None for value in provenance):
                if not all(value is None for value in provenance):
                    raise FeatureMatrixError("target provenance cells must be complete")
                if not np.isnan(values[row_index, column]):
                    raise FeatureMatrixError("present target values require provenance")
                continue
            assert outcome_time is not None
            assert available_at is not None
            if outcome_time <= decision_time:
                raise FeatureMatrixError("target outcome must follow decision time")
            if available_at < outcome_time:
                raise FeatureMatrixError("target available_at must be >= outcome_time")


def _empty_timestamp_cells(shape: tuple[int, int]) -> list[list[datetime | None]]:
    return [[None for _ in range(shape[1])] for _ in range(shape[0])]


def _empty_source_cells(shape: tuple[int, int]) -> list[list[str | None]]:
    return [[None for _ in range(shape[1])] for _ in range(shape[0])]


def _freeze_cells(values: Sequence[Sequence[Any]]) -> tuple[tuple[Any, ...], ...]:
    return tuple(tuple(row) for row in values)


def _serializable_values(values: FloatArray) -> list[list[float | None]]:
    return [
        [None if np.isnan(value) else float(value) for value in row] for row in values
    ]


def _serializable_timestamp_cells(values: TimestampCells) -> list[list[str | None]]:
    return [
        [None if value is None else value.isoformat() for value in row]
        for row in values
    ]
