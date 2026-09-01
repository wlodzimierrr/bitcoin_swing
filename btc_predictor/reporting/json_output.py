"""Canonical machine-readable advisory output (BTC-172)."""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from json import JSONDecodeError
from typing import Any, TypeAlias

from btc_predictor.reporting.position_management import (
    POSITION_MANAGEMENT_REPORT_VERSION,
    PositionManagementReportResult,
    position_management_report_from_record,
)
from btc_predictor.reporting.recommendation import (
    RECOMMENDATION_RENDERER_VERSION,
    RecommendationRendererResult,
    recommendation_renderer_from_record,
)


ADVISORY_JSON_FEATURE_ID = "ADVISORY_JSON_OUTPUT"
ADVISORY_JSON_SCHEMA_VERSION = "ADVISORY_JSON_SCHEMA_V1"
ADVISORY_JSON_MEDIA_TYPE = "application/json"
ADVISORY_JSON_REASON_CODES = ("ADVISORY_JSON_RENDERED",)
ADVISORY_JSON_DOCUMENT_TYPES = ("recommendation", "position_management")
ADVISORY_JSON_ENCODING = {
    "decimal": "decimal_string",
    "timestamp": "iso8601_utc",
}

AdvisorySource: TypeAlias = (
    RecommendationRendererResult | PositionManagementReportResult
)


@dataclass(frozen=True)
class AdvisoryJsonResult:
    """Canonical JSON plus the validated source object that produced it."""

    feature_id: str
    schema_version: str
    media_type: str
    document_type: str
    source: AdvisorySource
    body: str
    complete: bool
    reason_codes: tuple[str, ...]

    @property
    def document(self) -> dict[str, Any]:
        return _document(self.source, document_type=self.document_type)

    def as_record(self) -> dict[str, Any]:
        """Return a validated persistence record with parsed and encoded forms."""

        _validate_result(self)
        document = self.document
        expected_body = _canonical_json(document)
        if self.body != expected_body:
            raise ValueError("body is not the canonical JSON for the source record")
        return {
            "feature_id": self.feature_id,
            "schema_version": self.schema_version,
            "media_type": self.media_type,
            "document_type": self.document_type,
            "source_feature_id": self.source.feature_id,
            "source_version": _source_version(self.source),
            "config_metadata": _config_metadata(self.source.config_metadata),
            "source_reason_codes": list(self.source.reason_codes),
            "document": document,
            "body": self.body,
            "complete": self.complete,
            "reason_codes": list(self.reason_codes),
        }


def render_json_output(source: AdvisorySource) -> AdvisoryJsonResult:
    """Encode one BTC-170 or BTC-171 result as canonical compact JSON."""

    document_type = _document_type(source)
    source.as_record()
    document = _document(source, document_type=document_type)
    result = AdvisoryJsonResult(
        feature_id=ADVISORY_JSON_FEATURE_ID,
        schema_version=ADVISORY_JSON_SCHEMA_VERSION,
        media_type=ADVISORY_JSON_MEDIA_TYPE,
        document_type=document_type,
        source=source,
        body=_canonical_json(document),
        complete=True,
        reason_codes=ADVISORY_JSON_REASON_CODES,
    )
    result.as_record()
    return result


def advisory_json_from_record(
    source: Mapping[str, Any] | Any,
) -> AdvisoryJsonResult:
    """Restore a persisted JSON result and reject envelope or payload drift."""

    row = _mapping(source, "JSON output record")
    body = _text(row.get("body"), "body")
    document = _parse_document(body)
    document_type = _document_type_value(document.get("document_type"))
    restored_source = _restore_source(
        document_type,
        _mapping(document.get("payload"), "payload"),
    )
    result = AdvisoryJsonResult(
        feature_id=row.get("feature_id"),
        schema_version=row.get("schema_version"),
        media_type=row.get("media_type"),
        document_type=row.get("document_type"),
        source=restored_source,
        body=body,
        complete=_bool(row.get("complete"), "complete"),
        reason_codes=_reason_codes(row.get("reason_codes")),
    )
    if result.as_record() != dict(row):
        raise ValueError("JSON output record does not match its canonical body")
    return result


def advisory_source_from_json(body: str) -> AdvisorySource:
    """Decode and fully validate a standalone BTC advisory JSON document."""

    document = _parse_document(body)
    if _canonical_json(document) != body:
        raise ValueError("body must use canonical advisory JSON encoding")
    document_type = _document_type_value(document.get("document_type"))
    return _restore_source(
        document_type,
        _mapping(document.get("payload"), "payload"),
    )


def _document(
    source: AdvisorySource,
    *,
    document_type: str,
) -> dict[str, Any]:
    return {
        "document_type": document_type,
        "encoding": dict(ADVISORY_JSON_ENCODING),
        "payload": source.as_record(),
        "schema_version": ADVISORY_JSON_SCHEMA_VERSION,
    }


def _validate_result(result: AdvisoryJsonResult) -> None:
    if result.feature_id != ADVISORY_JSON_FEATURE_ID:
        raise ValueError(f"feature_id must be {ADVISORY_JSON_FEATURE_ID}")
    if result.schema_version != ADVISORY_JSON_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {ADVISORY_JSON_SCHEMA_VERSION}")
    if result.media_type != ADVISORY_JSON_MEDIA_TYPE:
        raise ValueError(f"media_type must be {ADVISORY_JSON_MEDIA_TYPE}")
    expected_type = _document_type(result.source)
    if result.document_type != expected_type:
        raise ValueError("document_type does not match source type")
    if result.complete is not True:
        raise ValueError("a validated JSON output must be complete")
    if result.reason_codes != ADVISORY_JSON_REASON_CODES:
        raise ValueError("reason_codes do not match JSON output state")
    result.source.as_record()
    _config_metadata(result.source.config_metadata)


def _document_type(source: AdvisorySource) -> str:
    if isinstance(source, RecommendationRendererResult):
        return "recommendation"
    if isinstance(source, PositionManagementReportResult):
        return "position_management"
    raise TypeError(
        "source must be a RecommendationRendererResult or "
        "PositionManagementReportResult",
    )


def _document_type_value(value: Any) -> str:
    if value not in ADVISORY_JSON_DOCUMENT_TYPES:
        raise ValueError(
            f"document_type must be one of {ADVISORY_JSON_DOCUMENT_TYPES}",
        )
    return value


def _source_version(source: AdvisorySource) -> str:
    if isinstance(source, RecommendationRendererResult):
        return RECOMMENDATION_RENDERER_VERSION
    if isinstance(source, PositionManagementReportResult):
        return POSITION_MANAGEMENT_REPORT_VERSION
    raise TypeError("unsupported advisory source")


def _restore_source(
    document_type: str,
    payload: Mapping[str, Any],
) -> AdvisorySource:
    if document_type == "recommendation":
        return recommendation_renderer_from_record(payload)
    if document_type == "position_management":
        return position_management_report_from_record(payload)
    raise ValueError(f"unsupported document_type: {document_type}")


def _parse_document(body: str) -> dict[str, Any]:
    try:
        parsed = json.loads(body)
    except JSONDecodeError as exc:
        raise ValueError("body must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError("advisory JSON root must be an object")
    if set(parsed) != {"document_type", "encoding", "payload", "schema_version"}:
        raise ValueError("advisory JSON envelope fields do not match schema")
    if parsed.get("schema_version") != ADVISORY_JSON_SCHEMA_VERSION:
        raise ValueError(f"schema_version must be {ADVISORY_JSON_SCHEMA_VERSION}")
    if parsed.get("encoding") != ADVISORY_JSON_ENCODING:
        raise ValueError("encoding conventions do not match advisory JSON schema")
    _document_type_value(parsed.get("document_type"))
    _mapping(parsed.get("payload"), "payload")
    return parsed


def _canonical_json(document: Mapping[str, Any]) -> str:
    try:
        return json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("advisory document is not JSON serializable") from exc


def _config_metadata(source: Mapping[str, Any] | Any) -> dict[str, str]:
    row = _mapping(source, "config_metadata")
    required = ("config_version", "strategy_version", "parameter_set_id")
    if set(row) != set(required):
        raise ValueError(f"config_metadata must exactly contain {required}")
    result = {}
    for key in required:
        value = row[key]
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"config_metadata.{key} must be a non-empty string")
        result[key] = value
    return result


def _mapping(source: Mapping[str, Any] | Any, name: str) -> Mapping[str, Any]:
    if isinstance(source, Mapping):
        return source
    row = getattr(source, "_mapping", None)
    if isinstance(row, Mapping):
        return row
    raise TypeError(f"{name} must be a mapping or database row")


def _text(value: Any, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{name} must be non-empty text")
    return value


def _bool(value: Any, name: str) -> bool:
    if not isinstance(value, bool):
        raise TypeError(f"{name} must be a bool")
    return value


def _reason_codes(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise TypeError("reason_codes must be a sequence")
    reasons = tuple(value)
    if any(not isinstance(code, str) or not code.strip() for code in reasons):
        raise ValueError("reason_codes must contain non-empty strings")
    return reasons
