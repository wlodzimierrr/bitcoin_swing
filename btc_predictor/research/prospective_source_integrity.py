"""Pre-data source provenance and completeness contracts for EPIC X.

The records in this module are deterministic reference interpretations of the
POSTP1-001R4 protocol.  They perform no network, clock-health, or persistence
I/O.  POSTP1-004 must collect the immutable inputs these owners validate; it
must not choose new scientific semantics while doing so.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, timedelta
from decimal import Context, Decimal, localcontext
from typing import Any, Mapping, Sequence


class ProspectiveSourceIntegrityError(ValueError):
    """A source lifecycle or provenance record is scientifically unusable."""


DECIMAL_CONTEXT = Context(prec=60)
CLOCK_INTEGRITY_VERSION = "PROSPECTIVE_CLOCK_INTEGRITY_V1"
CLOCK_MAXIMUM_PERMITTED_ERROR_SECONDS = Decimal("1")
CLOCK_MAXIMUM_WALL_STEP_SECONDS = Decimal("1")
STREAM_EPOCH_VERSION = "SOURCE_STREAM_EPOCH_V1"
STREAM_LIVENESS_VERSION = "STREAM_LIVENESS_POLICY_V1"
STREAM_LIVENESS_PING_CADENCE_SECONDS = Decimal("30")
STREAM_LIVENESS_PONG_TIMEOUT_SECONDS = Decimal("10")
STREAM_LIVENESS_MAXIMUM_GAP_SECONDS = Decimal("40")
CVD_INTERVAL_COMPLETENESS_VERSION = "CVD_INTERVAL_COMPLETENESS_V1"
LIQUIDATION_INTERVAL_COMPLETENESS_VERSION = (
    "LIQUIDATION_INTERVAL_COMPLETENESS_V1"
)
LIQUIDATION_DAY_CENSUS_VERSION = "LIQUIDATION_UTC_DAY_CENSUS_V1"
COINGECKO_RESPONSE_VALIDATION_VERSION = (
    "COINGECKO_MARKET_CAP_RESPONSE_VALIDATION_V1"
)

KRAKEN_SPOT_PROVIDER = "kraken_spot_websocket_v2_trade"
KRAKEN_SPOT_INSTRUMENT = "BTC/USD"
KRAKEN_FUTURES_PROVIDER = "kraken_futures_websocket_v1_trade"
KRAKEN_FUTURES_INSTRUMENT = "PI_XBTUSD"
KRAKEN_CHANNEL = "trade"
KRAKEN_IDENTITIES = {
    KRAKEN_SPOT_PROVIDER: KRAKEN_SPOT_INSTRUMENT,
    KRAKEN_FUTURES_PROVIDER: KRAKEN_FUTURES_INSTRUMENT,
}
KRAKEN_FUTURES_EVENT_TYPES = ("block", "fill", "liquidation", "termination")

STREAM_EPOCH_END_REASONS = (
    "BUFFER_OR_QUEUE_OVERFLOW",
    "CLOCK_INTEGRITY_FAILURE",
    "COLLECTOR_PROCESS_INTERRUPTION",
    "MISSED_LIVENESS_DEADLINE",
    "PARSER_FAILURE",
    "PROVIDER_OR_SERVER_RESTART_INDICATION",
    "RECONNECT",
    "RESUBSCRIPTION",
    "SERIALIZATION_OR_DURABLE_APPEND_FAILURE",
    "SOCKET_CLOSE",
    "SUBSCRIPTION_REJECTION",
    "TRANSPORT_ERROR",
    "UNRECOVERABLE_DUPLICATE_CONFLICT",
)

FEED_STATUS_OBSERVED_WITH_EVENTS = "OBSERVED_WITH_EVENTS"
FEED_STATUS_OBSERVED_ZERO_EVENTS = "OBSERVED_ZERO_EVENTS"
FEED_STATUS_SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"
FEED_STATUS_LATE = "LATE"
FEED_STATUS_INVALID = "INVALID"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime):
        normalized = _require_utc(value, "timestamp")
        return normalized.isoformat().replace("+00:00", "Z")
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_jsonable(item) for item in value]
    return value


def canonical_json(payload: Any) -> str:
    return json.dumps(
        _jsonable(payload),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )


def digest(payload: Any) -> str:
    return hashlib.sha256(canonical_json(payload).encode("ascii")).hexdigest()


def byte_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(re.fullmatch(r"[0-9a-f]{64}", value))


def _require_utc(value: datetime, field_name: str) -> datetime:
    if not isinstance(value, datetime) or value.tzinfo is None:
        raise ProspectiveSourceIntegrityError(f"{field_name} must be aware UTC")
    if value.utcoffset() != timedelta(0):
        raise ProspectiveSourceIntegrityError(f"{field_name} must be UTC")
    return value.astimezone(UTC)


def _require_text(value: str, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProspectiveSourceIntegrityError(f"{field_name} must be non-empty")
    return value


def _require_nonnegative_int(value: int, field_name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ProspectiveSourceIntegrityError(
            f"{field_name} must be a non-negative integer"
        )
    return value


def _with_digest(payload: dict[str, Any]) -> dict[str, Any]:
    result = dict(payload)
    result["record_sha256"] = digest(payload)
    return result


def _timedelta_seconds(value: timedelta) -> Decimal:
    """Convert a timedelta to exact Decimal seconds without a float round-trip."""

    with localcontext(DECIMAL_CONTEXT):
        return +(
            Decimal(value.days) * Decimal("86400")
            + Decimal(value.seconds)
            + Decimal(value.microseconds) / Decimal("1000000")
        )


@dataclass(frozen=True)
class ClockIntegrityRecord:
    """One OS/NTP/chrony health observation used by scientific wall time."""

    observed_at: datetime
    synchronization_mechanism: str
    synchronization_source: str
    synchronized: bool
    estimated_utc_offset_seconds: Decimal
    offset_uncertainty_seconds: Decimal | None
    collector_host_id: str
    collector_process_id: str
    health_query_succeeded: bool = True

    def as_record(self) -> dict[str, Any]:
        observed_at = _require_utc(self.observed_at, "clock observed_at")
        _require_text(self.synchronization_mechanism, "synchronization_mechanism")
        _require_text(self.synchronization_source, "synchronization_source")
        _require_text(self.collector_host_id, "collector_host_id")
        _require_text(self.collector_process_id, "collector_process_id")
        offset = self.estimated_utc_offset_seconds
        uncertainty = self.offset_uncertainty_seconds
        if not isinstance(offset, Decimal) or not offset.is_finite():
            raise ProspectiveSourceIntegrityError("clock offset must be finite")
        if uncertainty is not None and (
            not isinstance(uncertainty, Decimal)
            or not uncertainty.is_finite()
            or uncertainty < 0
        ):
            raise ProspectiveSourceIntegrityError(
                "clock offset uncertainty must be finite and non-negative"
            )
        reasons: list[str] = []
        if not self.health_query_succeeded:
            reasons.append("CLOCK_HEALTH_QUERY_FAILED")
        if not self.synchronized:
            reasons.append("CLOCK_UNSYNCHRONIZED")
        if offset.copy_abs() > CLOCK_MAXIMUM_PERMITTED_ERROR_SECONDS:
            reasons.append("CLOCK_OFFSET_OUT_OF_BOUND")
        if uncertainty is None:
            reasons.append("CLOCK_UNCERTAINTY_UNAVAILABLE")
        elif uncertainty > CLOCK_MAXIMUM_PERMITTED_ERROR_SECONDS:
            reasons.append("CLOCK_UNCERTAINTY_OUT_OF_BOUND")
        payload = {
            "collector_host_id": self.collector_host_id,
            "collector_process_id": self.collector_process_id,
            "estimated_utc_offset_seconds": offset,
            "health_query_succeeded": self.health_query_succeeded,
            "maximum_permitted_absolute_error_seconds": (
                str(CLOCK_MAXIMUM_PERMITTED_ERROR_SECONDS)
            ),
            "observed_at": observed_at,
            "offset_uncertainty_seconds": uncertainty,
            "reason_codes": sorted(reasons),
            "schema_version": CLOCK_INTEGRITY_VERSION,
            "synchronization_mechanism": self.synchronization_mechanism,
            "synchronization_source": self.synchronization_source,
            "synchronized": self.synchronized,
            "usable": not reasons,
        }
        return _with_digest(payload)

    @property
    def record_sha256(self) -> str:
        return self.as_record()["record_sha256"]

    @property
    def usable(self) -> bool:
        return bool(self.as_record()["usable"])


@dataclass(frozen=True)
class ClockIntervalEvidence:
    """Wall/monotonic cross-check for one scientific timing interval."""

    start_clock: ClockIntegrityRecord
    end_clock: ClockIntegrityRecord
    monotonic_elapsed_seconds: Decimal

    def as_record(self) -> dict[str, Any]:
        start = self.start_clock.as_record()
        end = self.end_clock.as_record()
        elapsed = self.monotonic_elapsed_seconds
        if not isinstance(elapsed, Decimal) or not elapsed.is_finite() or elapsed < 0:
            raise ProspectiveSourceIntegrityError(
                "monotonic elapsed duration must be finite and non-negative"
            )
        with localcontext(DECIMAL_CONTEXT):
            wall_elapsed = _timedelta_seconds(
                end["observed_at"] - start["observed_at"]
            )
            step = +(wall_elapsed - elapsed).copy_abs()
        reasons: list[str] = []
        if not start["usable"] or not end["usable"]:
            reasons.append("CLOCK_HEALTH_INVALID")
        if wall_elapsed < 0:
            reasons.append("WALL_CLOCK_MOVED_BACKWARD")
        if step > CLOCK_MAXIMUM_WALL_STEP_SECONDS:
            reasons.append("WALL_CLOCK_STEP_EXCEEDED")
        payload = {
            "end_clock_sha256": end["record_sha256"],
            "maximum_permitted_wall_step_seconds": (
                CLOCK_MAXIMUM_WALL_STEP_SECONDS
            ),
            "monotonic_elapsed_seconds": elapsed,
            "reason_codes": sorted(reasons),
            "start_clock_sha256": start["record_sha256"],
            "usable": not reasons,
            "wall_clock_elapsed_seconds": wall_elapsed,
            "wall_monotonic_divergence_seconds": step,
        }
        return _with_digest(payload)


def prospective_clock_integrity_contract() -> dict[str, Any]:
    payload = {
        "accuracy_selection": {
            "maximum_permitted_absolute_error_seconds": (
                str(CLOCK_MAXIMUM_PERMITTED_ERROR_SECONDS)
            ),
            "outcome_independent": True,
            "rationale": (
                "One second is 300 times smaller than the frozen five-minute "
                "decision delay and materially smaller than the 00:45/00:50/"
                "00:55 poll spacing and one-hour source intervals. It is a "
                "conservative pre-data infrastructure bound, not a historical "
                "strategy rule and not selected from Stage-B outcomes."
            ),
        },
        "accepted_health_interface": (
            "POSTP1-004 must query a real OS synchronization interface such as "
            "chronyc tracking, timedatectl/DBus, or an equivalently auditable "
            "NTP source and persist its source, offset and uncertainty."
        ),
        "duration_clock": "monotonic clock",
        "fail_closed_conditions": [
            "clock-health query failure",
            "synchronization unavailable",
            "absolute estimated UTC offset greater than one second",
            "offset uncertainty unavailable or greater than one second",
            "naive or non-UTC wall timestamp",
            "wall/monotonic divergence greater than one second",
        ],
        "maximum_wall_step_seconds": str(CLOCK_MAXIMUM_WALL_STEP_SECONDS),
        "scientific_timestamp_clock": "UTC wall clock",
        "schema_version": CLOCK_INTEGRITY_VERSION,
        "timeouts_and_liveness_use_wall_clock": False,
        "version": CLOCK_INTEGRITY_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload


@dataclass(frozen=True)
class CoinGeckoMarketCapRequest:
    """Exact immutable request/response pair for one requested UTC date."""

    requested_date: str
    scheduled_poll_time: datetime
    request_started_at: datetime
    response_completed_at: datetime
    http_status: int
    raw_response: bytes
    collector_version: str
    acquisition_contract_sha256: str
    request_start_clock: ClockIntegrityRecord
    response_completion_clock: ClockIntegrityRecord
    monotonic_elapsed_seconds: Decimal

    def as_record(self) -> dict[str, Any]:
        try:
            parsed_date = date.fromisoformat(self.requested_date)
        except (TypeError, ValueError) as exc:
            raise ProspectiveSourceIntegrityError(
                "CoinGecko requested_date must use YYYY-MM-DD"
            ) from exc
        if parsed_date.isoformat() != self.requested_date or not re.fullmatch(
            r"\d{4}-\d{2}-\d{2}", self.requested_date
        ):
            raise ProspectiveSourceIntegrityError(
                "CoinGecko requested_date must use YYYY-MM-DD"
            )
        scheduled = _require_utc(self.scheduled_poll_time, "scheduled_poll_time")
        started = _require_utc(self.request_started_at, "request_started_at")
        completed = _require_utc(
            self.response_completed_at, "response_completed_at"
        )
        if started < scheduled or completed < started:
            raise ProspectiveSourceIntegrityError(
                "CoinGecko request timing is not monotonic in UTC"
            )
        if (
            scheduled.hour != 0
            or scheduled.minute not in {45, 50, 55}
            or scheduled.second
            or scheduled.microsecond
        ):
            raise ProspectiveSourceIntegrityError(
                "CoinGecko scheduled poll must be exactly 00:45, 00:50, or 00:55 UTC"
            )
        requested_day_offset = (scheduled.date() - parsed_date).days
        if requested_day_offset not in {1, 2, 3}:
            raise ProspectiveSourceIntegrityError(
                "CoinGecko requested date must be poll-day minus 1, 2, or 3"
            )
        hard_cutoff = scheduled.replace(hour=0, minute=56)
        if completed > hard_cutoff:
            raise ProspectiveSourceIntegrityError(
                "CoinGecko response completed after the 00:56 UTC cycle cutoff"
            )
        if not isinstance(self.http_status, int) or isinstance(self.http_status, bool):
            raise ProspectiveSourceIntegrityError("HTTP status must be an integer")
        if not isinstance(self.raw_response, bytes):
            raise ProspectiveSourceIntegrityError("raw_response must be exact bytes")
        if not _is_sha256(self.acquisition_contract_sha256):
            raise ProspectiveSourceIntegrityError(
                "acquisition contract hash must be SHA-256"
            )
        _require_text(self.collector_version, "collector_version")
        start_clock = self.request_start_clock.as_record()
        completion_clock = self.response_completion_clock.as_record()
        if start_clock["observed_at"] != started:
            raise ProspectiveSourceIntegrityError(
                "request_started_at must equal its clock-health observed_at"
            )
        if completion_clock["observed_at"] != completed:
            raise ProspectiveSourceIntegrityError(
                "response_completed_at must equal its clock-health observed_at"
            )
        timing = ClockIntervalEvidence(
            start_clock=self.request_start_clock,
            end_clock=self.response_completion_clock,
            monotonic_elapsed_seconds=self.monotonic_elapsed_seconds,
        ).as_record()
        parameters = {
            "date": self.requested_date,
            "localization": "false",
        }
        serialized_parameters = (
            f"date={self.requested_date}&localization=false"
        )
        request_identity = {
            "asset_id": "bitcoin",
            "endpoint_identity": "/api/v3/coins/bitcoin/history",
            "endpoint_version": "CoinGecko API v3",
            "http_method": "GET",
            "parameter_canonicalization": (
                "UTF-8 RFC3986 query values; keys sorted lexicographically; "
                "date serialized exactly as YYYY-MM-DD"
            ),
            "provider": "coingecko",
            "query_parameters": parameters,
            "requested_currency": "usd",
            "requested_field": "market_data.market_cap.usd",
            "serialized_query": serialized_parameters,
        }
        request_digest = digest(request_identity)
        payload = {
            **request_identity,
            "acquisition_contract_sha256": self.acquisition_contract_sha256,
            "actual_request_started_at": started,
            "actual_response_completed_at": completed,
            "clock_interval_evidence_sha256": timing["record_sha256"],
            "collector_version": self.collector_version,
            "http_status": self.http_status,
            "request_digest": request_digest,
            "request_start_clock_sha256": start_clock["record_sha256"],
            "requested_date": self.requested_date,
            "response_completion_clock_sha256": completion_clock["record_sha256"],
            "response_digest": byte_digest(self.raw_response),
            "scheduled_poll_time": scheduled,
            "scientific_clock_usable": timing["usable"],
        }
        return _with_digest(payload)


@dataclass(frozen=True)
class ValidatedCoinGeckoMarketCapResponse:
    request: CoinGeckoMarketCapRequest
    market_cap_usd: Decimal

    def as_record(self) -> dict[str, Any]:
        request = self.request.as_record()
        value = self.market_cap_usd
        if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
            raise ProspectiveSourceIntegrityError(
                "validated CoinGecko USD market cap must be finite and positive"
            )
        payload = {
            "available_at": request["actual_response_completed_at"],
            "market_cap_usd": value,
            "observation_time": datetime.combine(
                date.fromisoformat(request["requested_date"]),
                datetime.min.time(),
                tzinfo=UTC,
            ),
            "provider": "coingecko",
            "request_digest": request["request_digest"],
            "request_record_sha256": request["record_sha256"],
            "requested_date": request["requested_date"],
            "response_digest": request["response_digest"],
            "source": "coingecko_v3_coins_bitcoin_history_market_cap_usd",
            "validation_contract": COINGECKO_RESPONSE_VALIDATION_VERSION,
            "validation_contract_sha256": (
                coingecko_market_cap_response_validation_contract()[
                    "definition_sha256"
                ]
            ),
        }
        return _with_digest(payload)


def validate_coingecko_market_cap_response(
    request: CoinGeckoMarketCapRequest,
) -> ValidatedCoinGeckoMarketCapResponse:
    record = request.as_record()
    if record["http_status"] != 200:
        raise ProspectiveSourceIntegrityError("CoinGecko HTTP status is not 200")
    if not record["scientific_clock_usable"]:
        raise ProspectiveSourceIntegrityError(
            "CoinGecko response has invalid local-clock integrity"
        )

    def unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ProspectiveSourceIntegrityError(
                    f"CoinGecko response contains duplicate JSON key {key!r}"
                )
            result[key] = value
        return result

    try:
        payload = json.loads(
            request.raw_response.decode("utf-8"),
            object_pairs_hook=unique_object,
            parse_float=Decimal,
            parse_int=Decimal,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ProspectiveSourceIntegrityError(
            "CoinGecko response is not valid UTF-8 JSON"
        ) from exc
    if not isinstance(payload, dict):
        raise ProspectiveSourceIntegrityError("CoinGecko response must be an object")
    if payload.get("id") != "bitcoin":
        raise ProspectiveSourceIntegrityError("unexpected CoinGecko asset id")
    if payload.get("symbol") != "btc":
        raise ProspectiveSourceIntegrityError(
            "unexpected CoinGecko symbol; validation is case-sensitive"
        )
    market_data = payload.get("market_data")
    if not isinstance(market_data, dict):
        raise ProspectiveSourceIntegrityError("CoinGecko market_data is missing")
    market_cap = market_data.get("market_cap")
    if not isinstance(market_cap, dict):
        raise ProspectiveSourceIntegrityError("CoinGecko market_cap is missing")
    value = market_cap.get("usd")
    if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
        raise ProspectiveSourceIntegrityError(
            "CoinGecko market_data.market_cap.usd must be finite and positive"
        )
    return ValidatedCoinGeckoMarketCapResponse(request=request, market_cap_usd=value)


def coingecko_market_cap_response_validation_contract() -> dict[str, Any]:
    payload = {
        "asset_id": "bitcoin",
        "clock_integrity_definition_sha256": prospective_clock_integrity_contract()[
            "definition_sha256"
        ],
        "date_binding": (
            "The response does not echo its requested date. observation_time is "
            "derived only as requested_date 00:00:00 UTC from the immutable "
            "request record bound to the exact response digest. Relabelling is "
            "refused."
        ),
        "http_status": 200,
        "missing_or_unexpected_schema_state": "INVALID / REQUIRED_INPUT_MISSING",
        "required_payload": {
            "id": "bitcoin (exact, case-sensitive)",
            "market_data.market_cap.usd": "finite Decimal strictly greater than zero",
            "symbol": "btc (exact, case-sensitive)",
        },
        "response_date_field_claimed": False,
        "schema_version": COINGECKO_RESPONSE_VALIDATION_VERSION,
        "validator": "validate_coingecko_market_cap_response",
        "version": COINGECKO_RESPONSE_VALIDATION_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload


@dataclass(frozen=True)
class CollectorHealthRecord:
    epoch_id: str
    period_start: datetime
    period_end: datetime
    observed_at: datetime
    clock_integrity: ClockIntegrityRecord
    parser_failure_count: int = 0
    serialization_failure_count: int = 0
    durable_append_failure_count: int = 0
    queue_overflow_count: int = 0
    dropped_event_count: int = 0
    unexpected_message_type_count: int = 0
    duplicate_conflict_count: int = 0
    collector_exception_count: int = 0
    provider_sequence_validation_failure_count: int = 0

    def as_record(self) -> dict[str, Any]:
        epoch_id = _require_text(self.epoch_id, "epoch_id")
        start = _require_utc(self.period_start, "health period_start")
        end = _require_utc(self.period_end, "health period_end")
        observed = _require_utc(self.observed_at, "health observed_at")
        if end < start or observed < end:
            raise ProspectiveSourceIntegrityError("collector-health timing is invalid")
        clock = self.clock_integrity.as_record()
        if clock["observed_at"] != observed:
            raise ProspectiveSourceIntegrityError(
                "collector-health observed_at must bind its clock record"
            )
        counters = {
            name: _require_nonnegative_int(getattr(self, name), name)
            for name in (
                "collector_exception_count",
                "dropped_event_count",
                "duplicate_conflict_count",
                "durable_append_failure_count",
                "parser_failure_count",
                "provider_sequence_validation_failure_count",
                "queue_overflow_count",
                "serialization_failure_count",
                "unexpected_message_type_count",
            )
        }
        reasons = [name.upper() for name, count in counters.items() if count]
        if not clock["usable"]:
            reasons.append("CLOCK_INTEGRITY_FAILURE")
        payload = {
            **counters,
            "clock_integrity_sha256": clock["record_sha256"],
            "epoch_id": epoch_id,
            "observed_at": observed,
            "period_end": end,
            "period_start": start,
            "reason_codes": sorted(reasons),
            "usable": not reasons,
        }
        return _with_digest(payload)


@dataclass(frozen=True)
class SourceStreamEpoch:
    provider: str
    instrument: str
    channel: str
    connection_session_id: str | None
    local_epoch_id: str
    connection_established_at: datetime
    subscription_acknowledged_at: datetime
    epoch_started_at: datetime
    collector_version: str
    collector_sha256: str
    source_contract_sha256: str
    establishment_clock: ClockIntegrityRecord
    establishment_health: CollectorHealthRecord
    epoch_ended_at: datetime | None = None
    end_reason: str | None = None

    def as_record(self) -> dict[str, Any]:
        expected_instrument = KRAKEN_IDENTITIES.get(self.provider)
        if expected_instrument != self.instrument or self.channel != KRAKEN_CHANNEL:
            raise ProspectiveSourceIntegrityError(
                "unexpected stream provider/instrument/channel identity"
            )
        _require_text(self.local_epoch_id, "local_epoch_id")
        _require_text(self.collector_version, "collector_version")
        if self.connection_session_id is not None:
            _require_text(self.connection_session_id, "connection_session_id")
        if not _is_sha256(self.collector_sha256) or not _is_sha256(
            self.source_contract_sha256
        ):
            raise ProspectiveSourceIntegrityError(
                "collector and source-contract hashes must be SHA-256"
            )
        connected = _require_utc(
            self.connection_established_at, "connection_established_at"
        )
        acknowledged = _require_utc(
            self.subscription_acknowledged_at, "subscription_acknowledged_at"
        )
        started = _require_utc(self.epoch_started_at, "epoch_started_at")
        if not (connected <= acknowledged <= started):
            raise ProspectiveSourceIntegrityError(
                "stream epoch may start only after connection and acknowledgement"
            )
        clock = self.establishment_clock.as_record()
        health = self.establishment_health.as_record()
        if clock["observed_at"] != started or not clock["usable"]:
            raise ProspectiveSourceIntegrityError(
                "stream epoch establishment needs valid clock integrity"
            )
        if (
            health["epoch_id"] != self.local_epoch_id
            or not health["usable"]
            or health["period_start"] > started
            or health["period_end"] < started
            or health["observed_at"] < started
        ):
            raise ProspectiveSourceIntegrityError(
                "stream epoch establishment needs valid collector health"
            )
        ended = (
            _require_utc(self.epoch_ended_at, "epoch_ended_at")
            if self.epoch_ended_at is not None
            else None
        )
        if (ended is None) != (self.end_reason is None):
            raise ProspectiveSourceIntegrityError(
                "epoch end timestamp and reason must appear together"
            )
        if ended is not None:
            if ended < started or self.end_reason not in STREAM_EPOCH_END_REASONS:
                raise ProspectiveSourceIntegrityError("invalid stream epoch end")
        payload = {
            "channel": self.channel,
            "collector_sha256": self.collector_sha256,
            "collector_version": self.collector_version,
            "connection_established_at": connected,
            "connection_session_id": self.connection_session_id,
            "end_reason": self.end_reason,
            "epoch_ended_at": ended,
            "epoch_started_at": started,
            "establishment_clock_sha256": clock["record_sha256"],
            "establishment_health_sha256": health["record_sha256"],
            "instrument": self.instrument,
            "local_epoch_id": self.local_epoch_id,
            "provider": self.provider,
            "schema_version": STREAM_EPOCH_VERSION,
            "source_contract_sha256": self.source_contract_sha256,
            "subscription_acknowledged_at": acknowledged,
        }
        return _with_digest(payload)


def end_stream_epoch(
    epoch: SourceStreamEpoch,
    *,
    ended_at: datetime,
    reason: str,
) -> SourceStreamEpoch:
    if epoch.epoch_ended_at is not None:
        raise ProspectiveSourceIntegrityError("a stream epoch may end only once")
    if reason not in STREAM_EPOCH_END_REASONS:
        raise ProspectiveSourceIntegrityError("unknown stream epoch end reason")
    ended = replace(epoch, epoch_ended_at=ended_at, end_reason=reason)
    ended.as_record()
    return ended


@dataclass(frozen=True)
class LivenessCheck:
    request_id: str
    ping_sent_monotonic_seconds: Decimal
    pong_received_monotonic_seconds: Decimal

    def as_record(self) -> dict[str, Any]:
        _require_text(self.request_id, "liveness request_id")
        ping = self.ping_sent_monotonic_seconds
        pong = self.pong_received_monotonic_seconds
        for value, name in ((ping, "ping"), (pong, "pong")):
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise ProspectiveSourceIntegrityError(
                    f"{name} monotonic timestamp must be finite and non-negative"
                )
        return {
            "ping_sent_monotonic_seconds": ping,
            "pong_received_monotonic_seconds": pong,
            "request_id": self.request_id,
        }


@dataclass(frozen=True)
class StreamLivenessEvidence:
    epoch_id: str
    interval_start: datetime
    interval_end: datetime
    interval_start_monotonic_seconds: Decimal
    interval_end_monotonic_seconds: Decimal
    checks: tuple[LivenessCheck, ...]

    def as_record(self) -> dict[str, Any]:
        _require_text(self.epoch_id, "liveness epoch_id")
        start = _require_utc(self.interval_start, "liveness interval_start")
        end = _require_utc(self.interval_end, "liveness interval_end")
        start_mono = self.interval_start_monotonic_seconds
        end_mono = self.interval_end_monotonic_seconds
        for value, name in ((start_mono, "start"), (end_mono, "end")):
            if not isinstance(value, Decimal) or not value.is_finite() or value < 0:
                raise ProspectiveSourceIntegrityError(
                    f"liveness {name} monotonic timestamp must be finite and non-negative"
                )
        if end <= start or end_mono <= start_mono:
            raise ProspectiveSourceIntegrityError("liveness interval is invalid")
        rows = sorted(
            (check.as_record() for check in self.checks),
            key=lambda row: (row["ping_sent_monotonic_seconds"], row["request_id"]),
        )
        reasons: list[str] = []
        request_ids = [row["request_id"] for row in rows]
        if len(request_ids) != len(set(request_ids)):
            reasons.append("DUPLICATE_LIVENESS_REQUEST_ID")
        if not rows:
            reasons.append("NO_LIVENESS_CHECKS")
        else:
            for row in rows:
                with localcontext(DECIMAL_CONTEXT):
                    response_duration = +(
                        row["pong_received_monotonic_seconds"]
                        - row["ping_sent_monotonic_seconds"]
                    )
                if response_duration < 0 or response_duration > (
                    STREAM_LIVENESS_PONG_TIMEOUT_SECONDS
                ):
                    reasons.append("MISSED_PONG_DEADLINE")
            pings = [row["ping_sent_monotonic_seconds"] for row in rows]
            with localcontext(DECIMAL_CONTEXT):
                initial_gap = +(start_mono - pings[0])
                cadence_gaps = [
                    +(right - left)
                    for left, right in zip(pings, pings[1:], strict=False)
                ]
                terminal_gap = +(
                    end_mono - rows[-1]["pong_received_monotonic_seconds"]
                )
            if pings[0] > start_mono or (
                initial_gap > STREAM_LIVENESS_MAXIMUM_GAP_SECONDS
            ):
                reasons.append("LIVENESS_STARTED_AFTER_INTERVAL")
            if any(
                gap > STREAM_LIVENESS_PING_CADENCE_SECONDS
                for gap in cadence_gaps
            ):
                reasons.append("PING_CADENCE_GAP")
            if terminal_gap > STREAM_LIVENESS_MAXIMUM_GAP_SECONDS:
                reasons.append("LIVENESS_ENDED_BEFORE_INTERVAL")
        payload = {
            "checks": rows,
            "collector_owned": True,
            "epoch_id": self.epoch_id,
            "interval_end": end,
            "interval_end_monotonic_seconds": end_mono,
            "interval_start": start,
            "interval_start_monotonic_seconds": start_mono,
            "maximum_permitted_liveness_gap_seconds": (
                STREAM_LIVENESS_MAXIMUM_GAP_SECONDS
            ),
            "ping_cadence_seconds": STREAM_LIVENESS_PING_CADENCE_SECONDS,
            "pong_timeout_seconds": STREAM_LIVENESS_PONG_TIMEOUT_SECONDS,
            "reason_codes": sorted(set(reasons)),
            "schema_version": STREAM_LIVENESS_VERSION,
            "usable": not reasons,
        }
        return _with_digest(payload)


@dataclass(frozen=True)
class CapturedSourceEvent:
    provider: str
    instrument: str
    channel: str
    epoch_id: str
    source_event_id: str
    event_time: datetime
    received_at: datetime
    side: str
    event_type: str
    quantity: Decimal
    price: Decimal
    raw_payload_sha256: str
    sequence_number: int | None = None

    def as_record(self) -> dict[str, Any]:
        expected_instrument = KRAKEN_IDENTITIES.get(self.provider)
        if expected_instrument != self.instrument or self.channel != KRAKEN_CHANNEL:
            raise ProspectiveSourceIntegrityError("unexpected source-event identity")
        _require_text(self.epoch_id, "event epoch_id")
        _require_text(self.source_event_id, "source_event_id")
        event_time = _require_utc(self.event_time, "event_time")
        received_at = _require_utc(self.received_at, "received_at")
        if self.side not in {"buy", "sell"}:
            raise ProspectiveSourceIntegrityError("source event side is invalid")
        allowed_types = (
            {"trade"}
            if self.provider == KRAKEN_SPOT_PROVIDER
            else set(KRAKEN_FUTURES_EVENT_TYPES)
        )
        if self.event_type not in allowed_types:
            raise ProspectiveSourceIntegrityError("source event type is invalid")
        for value, name in ((self.quantity, "quantity"), (self.price, "price")):
            if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
                raise ProspectiveSourceIntegrityError(
                    f"source event {name} must be finite and positive"
                )
        if not _is_sha256(self.raw_payload_sha256):
            raise ProspectiveSourceIntegrityError(
                "raw source-event payload digest must be SHA-256"
            )
        if self.provider == KRAKEN_SPOT_PROVIDER:
            if self.sequence_number is not None:
                raise ProspectiveSourceIntegrityError(
                    "spot trade_id is identity, not a separate global sequence"
                )
            with localcontext(DECIMAL_CONTEXT):
                unsigned_notional = +(self.price * self.quantity)
                signed_notional = (
                    +unsigned_notional
                    if self.side == "buy"
                    else -unsigned_notional
                )
        else:
            if (
                not isinstance(self.sequence_number, int)
                or isinstance(self.sequence_number, bool)
                or self.sequence_number <= 0
            ):
                raise ProspectiveSourceIntegrityError(
                    "Futures subscription-message seq must be positive"
                )
            with localcontext(DECIMAL_CONTEXT):
                unsigned_notional = +self.quantity
                signed_notional = (
                    +unsigned_notional
                    if self.side == "buy"
                    else -unsigned_notional
                )
        payload = {
            "channel": self.channel,
            "epoch_id": self.epoch_id,
            "event_time": event_time,
            "event_type": self.event_type,
            "instrument": self.instrument,
            "price": self.price,
            "provider": self.provider,
            "quantity": self.quantity,
            "raw_payload_sha256": self.raw_payload_sha256,
            "received_at": received_at,
            "sequence_number": self.sequence_number,
            "side": self.side,
            "signed_notional_usd": signed_notional,
            "source_event_id": self.source_event_id,
        }
        payload["scientific_payload_sha256"] = digest(
            {
                key: value
                for key, value in payload.items()
                if key not in {"raw_payload_sha256", "received_at"}
            }
        )
        return payload


@dataclass(frozen=True)
class StreamIntervalCompleteness:
    epoch: SourceStreamEpoch
    liveness: StreamLivenessEvidence
    collector_health: CollectorHealthRecord
    events: tuple[CapturedSourceEvent, ...]
    interval_start: datetime
    finalized_at: datetime
    finalization_clock: ClockIntegrityRecord
    epoch_to_finalization_clock: ClockIntervalEvidence

    def as_record(self) -> dict[str, Any]:
        start = _require_utc(self.interval_start, "interval_start")
        if start.minute or start.second or start.microsecond:
            raise ProspectiveSourceIntegrityError(
                "stream interval must start on an exact UTC hour"
            )
        end = start + timedelta(hours=1)
        finalized = _require_utc(self.finalized_at, "finalized_at")
        epoch = self.epoch.as_record()
        liveness = self.liveness.as_record()
        health = self.collector_health.as_record()
        final_clock = self.finalization_clock.as_record()
        timing = self.epoch_to_finalization_clock.as_record()
        reasons: list[str] = []
        if epoch["epoch_started_at"] >= start:
            reasons.append("SUBSCRIPTION_EPOCH_STARTED_AFTER_INTERVAL")
        if epoch["subscription_acknowledged_at"] >= start:
            reasons.append("SUBSCRIPTION_ACKNOWLEDGED_AFTER_INTERVAL")
        if epoch["epoch_ended_at"] is not None and epoch["epoch_ended_at"] < end:
            reasons.append("EPOCH_ENDED_INSIDE_INTERVAL")
        if liveness["epoch_id"] != epoch["local_epoch_id"]:
            reasons.append("LIVENESS_EPOCH_MISMATCH")
        if liveness["interval_start"] != start or liveness["interval_end"] != end:
            reasons.append("LIVENESS_INTERVAL_MISMATCH")
        if not liveness["usable"]:
            reasons.extend(liveness["reason_codes"])
        if health["epoch_id"] != epoch["local_epoch_id"]:
            reasons.append("COLLECTOR_HEALTH_EPOCH_MISMATCH")
        if health["period_start"] > start or health["period_end"] < end:
            reasons.append("COLLECTOR_HEALTH_INTERVAL_GAP")
        if not health["usable"]:
            reasons.extend(health["reason_codes"])
        if finalized < end:
            reasons.append("FINALIZED_BEFORE_INTERVAL_END")
        if final_clock["observed_at"] != finalized or not final_clock["usable"]:
            reasons.append("FINALIZATION_CLOCK_INVALID")
        if not timing["usable"]:
            reasons.extend(timing["reason_codes"])
        if (
            timing["start_clock_sha256"]
            != epoch["establishment_clock_sha256"]
            or timing["end_clock_sha256"] != final_clock["record_sha256"]
        ):
            reasons.append("CLOCK_INTERVAL_BINDING_MISMATCH")

        unique: dict[str, dict[str, Any]] = {}
        duplicate_retransmissions = 0
        for event in self.events:
            try:
                row = event.as_record()
            except ProspectiveSourceIntegrityError:
                reasons.append("INVALID_SOURCE_EVENT")
                continue
            if (
                row["provider"] != epoch["provider"]
                or row["instrument"] != epoch["instrument"]
                or row["channel"] != epoch["channel"]
                or row["epoch_id"] != epoch["local_epoch_id"]
            ):
                reasons.append("SOURCE_EVENT_EPOCH_OR_IDENTITY_MISMATCH")
                continue
            if not (start <= row["event_time"] < end):
                reasons.append("SOURCE_EVENT_OUTSIDE_INTERVAL")
                continue
            previous = unique.get(row["source_event_id"])
            if previous is None:
                unique[row["source_event_id"]] = row
            elif (
                previous["raw_payload_sha256"] == row["raw_payload_sha256"]
                or previous["scientific_payload_sha256"]
                == row["scientific_payload_sha256"]
            ):
                duplicate_retransmissions += 1
            else:
                reasons.append("UNRECOVERABLE_DUPLICATE_CONFLICT")
        event_rows = sorted(
            unique.values(),
            key=lambda row: (
                row["event_time"],
                row["source_event_id"],
                row["scientific_payload_sha256"],
            ),
        )
        payload = {
            "clock_integrity_reference": final_clock["record_sha256"],
            "collector_health_pass": health["usable"],
            "collector_health_sha256": health["record_sha256"],
            "complete": not reasons,
            "duplicate_retransmission_count": duplicate_retransmissions,
            "epoch_continuous_through_end": not (
                epoch["epoch_ended_at"] is not None
                and epoch["epoch_ended_at"] < end
            ),
            "epoch_id": epoch["local_epoch_id"],
            "event_census_sha256": digest(event_rows),
            "event_count": len(event_rows),
            "events": event_rows,
            "finalized_at": finalized,
            "interval_end": end,
            "interval_start": start,
            "liveness_pass": liveness["usable"],
            "liveness_sha256": liveness["record_sha256"],
            "provider": epoch["provider"],
            "provider_sequence_integrity_pass": (
                health["provider_sequence_validation_failure_count"] == 0
            ),
            "instrument": epoch["instrument"],
            "reason_codes": sorted(set(reasons)),
            "source_epoch_sha256": epoch["record_sha256"],
            "subscription_ack_before_start": (
                epoch["subscription_acknowledged_at"] < start
            ),
        }
        return _with_digest(payload)


@dataclass(frozen=True)
class CvdHourCompleteness:
    """One common CVD hour mechanically derived from both frozen streams."""

    spot: StreamIntervalCompleteness
    perp: StreamIntervalCompleteness

    def as_record(self) -> dict[str, Any]:
        spot = self.spot.as_record()
        perp = self.perp.as_record()
        reasons: list[str] = []
        if (
            spot["provider"] != KRAKEN_SPOT_PROVIDER
            or spot["instrument"] != KRAKEN_SPOT_INSTRUMENT
        ):
            reasons.append("SPOT_IDENTITY_INVALID")
        if (
            perp["provider"] != KRAKEN_FUTURES_PROVIDER
            or perp["instrument"] != KRAKEN_FUTURES_INSTRUMENT
        ):
            reasons.append("PERP_IDENTITY_INVALID")
        if (
            spot["interval_start"] != perp["interval_start"]
            or spot["interval_end"] != perp["interval_end"]
        ):
            reasons.append("COMMON_INTERVAL_MISMATCH")
        if not spot["complete"]:
            reasons.append("SPOT_INTERVAL_INCOMPLETE")
        if not perp["complete"]:
            reasons.append("PERP_INTERVAL_INCOMPLETE")
        with localcontext(DECIMAL_CONTEXT):
            spot_cvd = +sum(
                (row["signed_notional_usd"] for row in spot["events"]),
                Decimal("0"),
            )
            perp_cvd = +sum(
                (row["signed_notional_usd"] for row in perp["events"]),
                Decimal("0"),
            )
        payload = {
            "complete": not reasons,
            "finalized_at": max(spot["finalized_at"], perp["finalized_at"]),
            "interval_end": spot["interval_end"],
            "interval_start": spot["interval_start"],
            "perp_cvd_usd": perp_cvd if not reasons else None,
            "perp_epoch_id": perp["epoch_id"],
            "perp_event_census_sha256": perp["event_census_sha256"],
            "perp_event_count": perp["event_count"],
            "perp_epoch_continuous_through_end": perp[
                "epoch_continuous_through_end"
            ],
            "perp_collector_health_pass": perp["collector_health_pass"],
            "perp_clock_integrity_reference": perp[
                "clock_integrity_reference"
            ],
            "perp_liveness_pass": perp["liveness_pass"],
            "perp_sequence_integrity_pass": perp[
                "provider_sequence_integrity_pass"
            ],
            "perp_subscription_ack_before_start": perp[
                "subscription_ack_before_start"
            ],
            "perp_interval_completeness": perp,
            "perp_interval_completeness_sha256": perp["record_sha256"],
            "reason_codes": sorted(reasons),
            "schema_version": CVD_INTERVAL_COMPLETENESS_VERSION,
            "spot_cvd_usd": spot_cvd if not reasons else None,
            "spot_epoch_id": spot["epoch_id"],
            "spot_event_census_sha256": spot["event_census_sha256"],
            "spot_event_count": spot["event_count"],
            "spot_epoch_continuous_through_end": spot[
                "epoch_continuous_through_end"
            ],
            "spot_collector_health_pass": spot["collector_health_pass"],
            "spot_clock_integrity_reference": spot[
                "clock_integrity_reference"
            ],
            "spot_liveness_pass": spot["liveness_pass"],
            "spot_subscription_ack_before_start": spot[
                "subscription_ack_before_start"
            ],
            "spot_interval_completeness": spot,
            "spot_interval_completeness_sha256": spot["record_sha256"],
        }
        return _with_digest(payload)


def stream_liveness_policy_contract() -> dict[str, Any]:
    payload = {
        "clock": "monotonic",
        "failure_classification": (
            "MISSED_LIVENESS_DEADLINE_ENDS_EPOCH_AND_INVALIDATES_INTERVAL"
        ),
        "maximum_permitted_liveness_gap_seconds": (
            str(STREAM_LIVENESS_MAXIMUM_GAP_SECONDS)
        ),
        "mechanism": "collector-owned WebSocket ping/pong",
        "ping_cadence_seconds": str(STREAM_LIVENESS_PING_CADENCE_SECONDS),
        "pong_timeout_seconds": str(STREAM_LIVENESS_PONG_TIMEOUT_SECONDS),
        "provider_attribution": False,
        "provider_heartbeat_role": (
            "Optional provider/application liveness evidence only; never proof "
            "of trade-message completeness and no exact undocumented cadence."
        ),
        "schema_version": STREAM_LIVENESS_VERSION,
        "version": STREAM_LIVENESS_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload


def source_stream_epoch_contract() -> dict[str, Any]:
    payload = {
        "begin_conditions": [
            "connection established",
            "trade subscription acknowledged",
            "exact provider/instrument/channel validated",
            "clock integrity usable",
            "collector health usable",
        ],
        "clock_integrity_definition_sha256": prospective_clock_integrity_contract()[
            "definition_sha256"
        ],
        "end_reasons": list(STREAM_EPOCH_END_REASONS),
        "full_interval_rule": (
            "One epoch must be established strictly before interval start and "
            "remain valid through interval end; reconnect and resubscription "
            "always create a new epoch and intervals are never stitched."
        ),
        "identity_fields": [
            "provider",
            "instrument",
            "channel",
            "connection_session_id",
            "local_epoch_id",
            "subscription_acknowledged_at",
            "epoch_started_at",
            "epoch_ended_at",
            "end_reason",
            "collector_version",
            "collector_sha256",
            "source_contract_sha256",
            "establishment_clock_sha256",
            "establishment_health_sha256",
        ],
        "reconnect_continues_epoch": False,
        "schema_version": STREAM_EPOCH_VERSION,
        "version": STREAM_EPOCH_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload


def cvd_interval_completeness_contract() -> dict[str, Any]:
    payload = {
        "complete_is_caller_supplied": False,
        "event_census": (
            "Exact epoch-bound source records are sorted and deduplicated by "
            "provider event identity; identical retransmissions are idempotent "
            "and conflicting duplicates invalidate the interval."
        ),
        "futures_sequence_scope": "one subscription epoch",
        "futures_sequence_semantics": (
            "Kraken documents seq as a subscription-message sequence number "
            "but does not document cross-reconnect continuity here. Positive "
            "shape and duplicate conflicts are validated; no undocumented "
            "global or cross-reconnect increment guarantee is assumed."
        ),
        "liveness_definition_sha256": stream_liveness_policy_contract()[
            "definition_sha256"
        ],
        "required_markets": {
            "perp": [KRAKEN_FUTURES_PROVIDER, KRAKEN_FUTURES_INSTRUMENT],
            "spot": [KRAKEN_SPOT_PROVIDER, KRAKEN_SPOT_INSTRUMENT],
        },
        "schema_version": CVD_INTERVAL_COMPLETENESS_VERSION,
        "spot_trade_id_semantics": (
            "Unique per book source-event identity and deduplication key; not "
            "a documented lossless connection-level continuity proof."
        ),
        "stream_epoch_definition_sha256": source_stream_epoch_contract()[
            "definition_sha256"
        ],
        "version": CVD_INTERVAL_COMPLETENESS_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload


def classify_liquidation_interval(
    completeness: StreamIntervalCompleteness,
    *,
    decision_time: datetime,
) -> dict[str, Any]:
    interval = completeness.as_record()
    decision = _require_utc(decision_time, "decision_time")

    def unusable(status: str, reason: str) -> dict[str, Any]:
        payload = {
            "available_at": interval["finalized_at"],
            "clock_integrity_sha256": interval["clock_integrity_reference"],
            "collector_health_sha256": interval["collector_health_sha256"],
            "completeness_evidence_sha256": interval["record_sha256"],
            "contract_size_usd": Decimal("1"),
            "event_count": None,
            "event_type": "liquidation",
            "feed_status": status,
            "finalized_at": interval["finalized_at"],
            "instrument": interval["instrument"],
            "long_liquidation_notional_usd": None,
            "observation_time": interval["interval_start"],
            "provider": interval["provider"],
            "reason": reason,
            "short_liquidation_notional_usd": None,
            "source_record_ids_digest": None,
            "source_stream_epoch_sha256": interval["source_epoch_sha256"],
            "stream_liveness_sha256": interval["liveness_sha256"],
            "timeframe": "1h",
        }
        return _with_digest(payload)

    if (
        interval["provider"] != KRAKEN_FUTURES_PROVIDER
        or interval["instrument"] != KRAKEN_FUTURES_INSTRUMENT
    ):
        return unusable(FEED_STATUS_INVALID, "UNEXPECTED_PROVIDER_OR_INSTRUMENT")
    if interval["finalized_at"] > decision:
        return unusable(FEED_STATUS_LATE, "INTERVAL_EVIDENCE_LATE")
    if not interval["complete"]:
        invalid_reasons = {
            "INVALID_SOURCE_EVENT",
            "SOURCE_EVENT_EPOCH_OR_IDENTITY_MISMATCH",
            "SOURCE_EVENT_OUTSIDE_INTERVAL",
            "UNRECOVERABLE_DUPLICATE_CONFLICT",
            "PROVIDER_SEQUENCE_VALIDATION_FAILURE_COUNT",
        }
        status = (
            FEED_STATUS_INVALID
            if invalid_reasons.intersection(interval["reason_codes"])
            else FEED_STATUS_SOURCE_UNAVAILABLE
        )
        return unusable(status, "INTERVAL_COMPLETENESS_FAILED")

    liquidation_events = [
        row for row in interval["events"] if row["event_type"] == "liquidation"
    ]
    with localcontext(DECIMAL_CONTEXT):
        long_notional = +sum(
            (
                row["quantity"]
                for row in liquidation_events
                if row["side"] == "sell"
            ),
            Decimal("0"),
        )
        short_notional = +sum(
            (
                row["quantity"]
                for row in liquidation_events
                if row["side"] == "buy"
            ),
            Decimal("0"),
        )
    status = (
        FEED_STATUS_OBSERVED_WITH_EVENTS
        if liquidation_events
        else FEED_STATUS_OBSERVED_ZERO_EVENTS
    )
    ids = sorted(row["source_event_id"] for row in liquidation_events)
    payload = {
        "available_at": interval["finalized_at"],
        "clock_integrity_sha256": interval["clock_integrity_reference"],
        "collector_health_sha256": interval["collector_health_sha256"],
        "completeness_evidence_sha256": interval["record_sha256"],
        "contract_size_usd": Decimal("1"),
        "event_count": len(liquidation_events),
        "event_type": "liquidation",
        "feed_status": status,
        "finalized_at": interval["finalized_at"],
        "instrument": interval["instrument"],
        "long_liquidation_notional_usd": long_notional,
        "observation_time": interval["interval_start"],
        "provider": interval["provider"],
        "reason": None,
        "short_liquidation_notional_usd": short_notional,
        "source_record_ids_digest": digest(ids),
        "source_stream_epoch_sha256": interval["source_epoch_sha256"],
        "stream_liveness_sha256": interval["liveness_sha256"],
        "timeframe": "1h",
    }
    return _with_digest(payload)


def liquidation_interval_completeness_contract() -> dict[str, Any]:
    payload = {
        "classifier": "classify_liquidation_interval",
        "complete_is_caller_supplied": False,
        "cvd_stream_evidence_reused": True,
        "healthy_positive_rule": (
            "The same exact complete Futures hour required for zero, plus one "
            "or more valid liquidation-typed events."
        ),
        "healthy_zero_rule": (
            "Exact PI_XBTUSD liquidation source; one uninterrupted epoch over "
            "the full hour; liveness, clock, sequence-shape and collector "
            "health valid; zero valid liquidation events; timely finalization."
        ),
        "missing_can_become_zero": False,
        "notional": {
            "contract_size_usd": "1",
            "provider_buy": "short liquidation",
            "provider_sell": "long liquidation",
        },
        "schema_version": LIQUIDATION_INTERVAL_COMPLETENESS_VERSION,
        "stream_epoch_definition_sha256": source_stream_epoch_contract()[
            "definition_sha256"
        ],
        "stream_liveness_definition_sha256": stream_liveness_policy_contract()[
            "definition_sha256"
        ],
        "version": LIQUIDATION_INTERVAL_COMPLETENESS_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload


def expected_liquidation_hour_ids(day: date) -> tuple[str, ...]:
    start = datetime.combine(day, datetime.min.time(), tzinfo=UTC)
    return tuple(
        f"{(start + timedelta(hours=hour)).isoformat()}|"
        f"{(start + timedelta(hours=hour + 1)).isoformat()}"
        for hour in range(24)
    )


def aggregate_liquidation_utc_day(
    day: date,
    hourly_records: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    expected = expected_liquidation_hour_ids(day)
    seen: dict[str, Mapping[str, Any]] = {}
    duplicate_ids: list[str] = []
    for record in hourly_records:
        try:
            start = _require_utc(record["observation_time"], "observation_time")
        except (KeyError, ProspectiveSourceIntegrityError):
            payload = {
                "census_status": "INVALID",
                "date": day,
                "reason_codes": ["INVALID_INTERVAL_RECORD"],
            }
            return _with_digest(payload)
        interval_id = f"{start.isoformat()}|{(start + timedelta(hours=1)).isoformat()}"
        if interval_id in seen:
            duplicate_ids.append(interval_id)
        else:
            seen[interval_id] = record
    observed_ids = set(seen)
    expected_set = set(expected)
    reasons: list[str] = []
    status = "COMPLETE"
    if duplicate_ids:
        status = "INVALID"
        reasons.append("DUPLICATE_INTERVAL_IDENTITY")
    if observed_ids != expected_set:
        if status != "INVALID":
            status = "INCOMPLETE"
        reasons.append("EXACT_24_HOUR_CENSUS_MISMATCH")
    admissible_statuses = {
        FEED_STATUS_OBSERVED_WITH_EVENTS,
        FEED_STATUS_OBSERVED_ZERO_EVENTS,
    }
    if any(
        seen[interval_id].get("feed_status") not in admissible_statuses
        for interval_id in observed_ids.intersection(expected_set)
    ):
        if status != "INVALID":
            status = "INCOMPLETE"
        reasons.append("UNUSABLE_HOURLY_INTERVAL")
    for interval_id in observed_ids.intersection(expected_set):
        record = dict(seen[interval_id])
        declared_digest = record.pop("record_sha256", None)
        if not _is_sha256(declared_digest) or digest(record) != declared_digest:
            status = "INVALID"
            reasons.append("HOURLY_RECORD_DIGEST_INVALID")
            continue
        if (
            record.get("provider") != KRAKEN_FUTURES_PROVIDER
            or record.get("instrument") != KRAKEN_FUTURES_INSTRUMENT
            or record.get("timeframe") != "1h"
        ):
            status = "INVALID"
            reasons.append("HOURLY_SOURCE_IDENTITY_INVALID")
            continue
        if record.get("feed_status") not in admissible_statuses:
            continue
        count = record.get("event_count")
        long_value = record.get("long_liquidation_notional_usd")
        short_value = record.get("short_liquidation_notional_usd")
        values_valid = (
            isinstance(count, int)
            and not isinstance(count, bool)
            and count >= 0
            and isinstance(long_value, Decimal)
            and long_value.is_finite()
            and long_value >= 0
            and isinstance(short_value, Decimal)
            and short_value.is_finite()
            and short_value >= 0
        )
        if not values_valid:
            status = "INVALID"
            reasons.append("INVALID_HOURLY_VALUE")
            continue
        if record["feed_status"] == FEED_STATUS_OBSERVED_ZERO_EVENTS and (
            count != 0 or long_value != 0 or short_value != 0
        ):
            status = "INVALID"
            reasons.append("INVALID_ZERO_HOUR")
        if record["feed_status"] == FEED_STATUS_OBSERVED_WITH_EVENTS and (
            count <= 0 or (long_value == 0 and short_value == 0)
        ):
            status = "INVALID"
            reasons.append("INVALID_POSITIVE_HOUR")

    long_total: Decimal | None = None
    short_total: Decimal | None = None
    daily_total: Decimal | None = None
    event_count: int | None = None
    available_at: datetime | None = None
    if status == "COMPLETE":
        with localcontext(DECIMAL_CONTEXT):
            try:
                long_total = +sum(
                    (seen[key]["long_liquidation_notional_usd"] for key in expected),
                    Decimal("0"),
                )
                short_total = +sum(
                    (seen[key]["short_liquidation_notional_usd"] for key in expected),
                    Decimal("0"),
                )
                event_count = sum(seen[key]["event_count"] for key in expected)
                daily_total = +(long_total + short_total)
                available_at = max(seen[key]["available_at"] for key in expected)
            except (KeyError, TypeError, ArithmeticError):
                status = "INVALID"
                reasons.append("INVALID_HOURLY_VALUE")
                long_total = short_total = None
                daily_total = None
                event_count = None
                available_at = None
    payload = {
        "available_at": available_at,
        "census_status": status,
        "date": day,
        "duplicate_interval_ids": sorted(duplicate_ids),
        "event_count": event_count,
        "expected_hour_count": 24,
        "expected_interval_ids": list(expected),
        "hourly_record_digests": [
            seen[key].get("record_sha256") for key in expected if key in seen
        ],
        "long_liquidation_notional_usd": long_total,
        "missing_interval_ids": sorted(expected_set - observed_ids),
        "observed_hour_count": len(hourly_records),
        "observation_time": datetime.combine(
            day, datetime.min.time(), tzinfo=UTC
        ),
        "reason_codes": sorted(set(reasons)),
        "short_liquidation_notional_usd": short_total,
        "schema_version": LIQUIDATION_DAY_CENSUS_VERSION,
        "total_liquidation_notional_usd": daily_total,
        "unexpected_interval_ids": sorted(observed_ids - expected_set),
    }
    return _with_digest(payload)


def liquidation_utc_day_census_contract() -> dict[str, Any]:
    payload = {
        "admission": (
            "The observed interval-id set must equal the exact 24 expected UTC "
            "hour identities, every hour must be OBSERVED_ZERO_EVENTS or "
            "OBSERVED_WITH_EVENTS, and duplicate identities are forbidden."
        ),
        "daily_positive": "deterministic Decimal sum over the exact 24 hours",
        "daily_zero": (
            "All 24 exact hours exist, are complete, and each has event_count=0"
        ),
        "dst_adjustment": False,
        "expected_hour_count": 24,
        "hour_identity": "[D HH:00:00Z, D HH+1:00:00Z)",
        "interval_definition_sha256": liquidation_interval_completeness_contract()[
            "definition_sha256"
        ],
        "schema_version": LIQUIDATION_DAY_CENSUS_VERSION,
        "version": LIQUIDATION_DAY_CENSUS_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload
