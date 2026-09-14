"""Collector-only PostgreSQL append and reader-only envelope rehydration."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Connection, Select, select
from sqlalchemy.dialects.postgresql import insert

from btc_predictor.db.research import etf_calendar_trusted_acquisitions
from btc_predictor.research.trusted_acquisition import (
    AUTHORITY_VERSION,
    ENVELOPE_KIND,
    PRODUCTION_KEY_REGISTRY,
    TrustedAcquisitionError,
    VerificationKey,
    verify_envelope,
)


class PostgresTrustedAcquisitionAppender:
    """Use only with a connection authenticated as the collector-writer role."""

    def __init__(
        self,
        connection: Connection,
        *,
        registry: Mapping[str, VerificationKey] = PRODUCTION_KEY_REGISTRY,
    ) -> None:
        if connection.dialect.name != "postgresql":
            raise TrustedAcquisitionError("authoritative acquisition append requires PostgreSQL")
        self._connection = connection
        self._registry = registry

    def append(self, envelope: Mapping[str, Any]) -> str:
        """Verify and atomically insert one complete envelope; never update."""

        payload = verify_envelope(envelope, registry=self._registry)
        values = {
            "envelope_sha256": envelope["envelope_sha256"],
            "signed_payload": payload,
            "signed_payload_sha256": envelope["signed_payload_sha256"],
            "signing_key_id": envelope["signing_key_id"],
            "signature_algorithm": envelope["signature_algorithm"],
            "signature": envelope["signature"],
            "response_sha256": payload["response_sha256"],
            "response_received_at": _utc(payload["response_received_at"]),
            "acquired_at": _utc(payload["acquired_at"]),
            "available_at": _utc(payload["available_at"]),
            "source_profile_id": payload["source_profile_id"],
            "venue_id": payload["venue_id"],
            "source_authority_id": payload["source_authority_id"],
            "created_at": datetime.now(UTC),
        }
        statement = insert(etf_calendar_trusted_acquisitions).values(**values)
        statement = statement.on_conflict_do_nothing(
            index_elements=[etf_calendar_trusted_acquisitions.c.envelope_sha256]
        )
        self._connection.execute(statement)
        return str(envelope["envelope_sha256"])


def authoritative_envelope_query(envelope_sha256: str | None = None) -> Select:
    query = select(etf_calendar_trusted_acquisitions)
    if envelope_sha256 is not None:
        query = query.where(
            etf_calendar_trusted_acquisitions.c.envelope_sha256 == envelope_sha256
        )
    return query.order_by(etf_calendar_trusted_acquisitions.c.envelope_sha256)


def rehydrate_verified_envelopes(
    rows: Sequence[Mapping[str, Any]],
    *,
    registry: Mapping[str, VerificationKey] = PRODUCTION_KEY_REGISTRY,
) -> tuple[dict[str, Any], ...]:
    envelopes: list[dict[str, Any]] = []
    for row in rows:
        envelope = {
            "record_kind": ENVELOPE_KIND,
            "schema_version": 1,
            "authority_identity": AUTHORITY_VERSION,
            "signed_payload": row["signed_payload"],
            "signed_payload_sha256": row["signed_payload_sha256"],
            "signing_key_id": row["signing_key_id"],
            "signature_algorithm": row["signature_algorithm"],
            "signature": row["signature"],
            "envelope_sha256": row["envelope_sha256"],
        }
        verify_envelope(envelope, registry=registry)
        envelopes.append(envelope)
    return tuple(envelopes)


def _utc(value: Any) -> datetime:
    parsed = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(parsed, datetime) or parsed.tzinfo is None or parsed.utcoffset() != UTC.utcoffset(None):
        raise TrustedAcquisitionError("persisted acquisition timestamp must be UTC")
    return parsed
