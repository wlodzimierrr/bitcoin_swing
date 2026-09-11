"""Pre-data source provenance and completeness contracts for EPIC X.

The records in this module are deterministic reference interpretations of the
POSTP1-001R5 protocol. They perform no network, clock-health, or persistence
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
CLOCK_HEALTH_POLL_CADENCE_SECONDS = Decimal("30")
CLOCK_HEALTH_MAXIMUM_RECORD_AGE_SECONDS = Decimal("40")
CLOCK_HEALTH_MAXIMUM_GAP_SECONDS = Decimal("40")
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
COINGECKO_REQUEST_ATTEMPT_VERSION = "COINGECKO_MARKET_CAP_REQUEST_ATTEMPT_V1"
COINGECKO_HTTP_TIMEOUT_SECONDS = Decimal("45")
KRAKEN_FUTURES_METADATA_VALIDATION_VERSION = (
    "KRAKEN_FUTURES_INSTRUMENT_METADATA_VALIDATION_V1"
)
KRAKEN_FUTURES_METADATA_MAXIMUM_AGE_SECONDS = Decimal("300")
KRAKEN_FUTURES_METADATA_ENDPOINT = (
    "https://futures.kraken.com/derivatives/api/v3/instruments"
)
SCIENTIFIC_EVIDENCE_RESOLVER_VERSION = "SCIENTIFIC_EVIDENCE_RESOLVER_V1"
COLLECTOR_HEALTH_VERSION = "STREAM_COLLECTOR_HEALTH_V1"
SOURCE_EVENT_VERSION = "PROSPECTIVE_SOURCE_EVENT_V1"
STREAM_INTERVAL_COMPLETENESS_VERSION = "STREAM_INTERVAL_COMPLETENESS_V1"
VERIFIED_LIQUIDATION_HOUR_VERSION = "VERIFIED_LIQUIDATION_HOUR_V1"

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

COINGECKO_ATTEMPT_OUTCOMES = (
    "SUCCESS",
    "TIMEOUT",
    "HTTP_ERROR",
    "TRANSPORT_ERROR",
    "INVALID_RESPONSE",
    "CLOCK_INVALID",
    "CYCLE_CUTOFF",
)

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
    if isinstance(value, bytes):
        # Exact bytes remain bytes in scientific records and BYTEA in the
        # PostgreSQL contract. This tagged form is only for deterministic
        # hashing/JSON comparison and is losslessly reversible.
        return {"__exact_bytes_hex__": value.hex()}
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


def _require_bool(value: bool, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise ProspectiveSourceIntegrityError(f"{field_name} must be boolean")
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


def _decimal(value: Any, field_name: str, *, nonnegative: bool = True) -> Decimal:
    if not isinstance(value, Decimal) or not value.is_finite():
        raise ProspectiveSourceIntegrityError(f"{field_name} must be finite Decimal")
    if nonnegative and value < 0:
        raise ProspectiveSourceIntegrityError(f"{field_name} must be non-negative")
    return value


@dataclass(frozen=True)
class MonotonicDomainIdentity:
    """One process/boot domain inside which monotonic subtraction is valid."""

    collector_host_id: str
    collector_process_id: str
    process_start_identity: str
    boot_id: str

    def as_record(self) -> dict[str, Any]:
        payload = {
            "boot_id": _require_text(self.boot_id, "boot_id"),
            "collector_host_id": _require_text(
                self.collector_host_id, "collector_host_id"
            ),
            "collector_process_id": _require_text(
                self.collector_process_id, "collector_process_id"
            ),
            "process_start_identity": _require_text(
                self.process_start_identity, "process_start_identity"
            ),
        }
        payload["monotonic_domain_id"] = digest(payload)
        return payload

    @property
    def monotonic_domain_id(self) -> str:
        return self.as_record()["monotonic_domain_id"]


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
    monotonic_observed_seconds: Decimal = Decimal("0")
    process_start_identity: str = "UNSPECIFIED_PROCESS_START"
    boot_id: str = "UNSPECIFIED_BOOT"

    @property
    def monotonic_domain(self) -> MonotonicDomainIdentity:
        return MonotonicDomainIdentity(
            collector_host_id=self.collector_host_id,
            collector_process_id=self.collector_process_id,
            process_start_identity=self.process_start_identity,
            boot_id=self.boot_id,
        )

    def as_record(self) -> dict[str, Any]:
        observed_at = _require_utc(self.observed_at, "clock observed_at")
        _require_text(self.synchronization_mechanism, "synchronization_mechanism")
        _require_text(self.synchronization_source, "synchronization_source")
        _require_bool(self.synchronized, "synchronized")
        _require_bool(self.health_query_succeeded, "health_query_succeeded")
        _require_text(self.collector_host_id, "collector_host_id")
        _require_text(self.collector_process_id, "collector_process_id")
        _require_text(self.process_start_identity, "process_start_identity")
        _require_text(self.boot_id, "boot_id")
        monotonic = _decimal(
            self.monotonic_observed_seconds,
            "monotonic_observed_seconds",
        )
        domain = self.monotonic_domain.as_record()
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
        if (
            self.process_start_identity == "UNSPECIFIED_PROCESS_START"
            or self.boot_id == "UNSPECIFIED_BOOT"
        ):
            reasons.append("MONOTONIC_DOMAIN_UNSPECIFIED")
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
            "monotonic_domain": domain,
            "monotonic_domain_id": domain["monotonic_domain_id"],
            "monotonic_observed_seconds": monotonic,
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
    monotonic_elapsed_seconds: Decimal | None = None
    health_records: tuple[ClockIntegrityRecord, ...] = ()

    def as_record(self) -> dict[str, Any]:
        start = self.start_clock.as_record()
        end = self.end_clock.as_record()
        with localcontext(DECIMAL_CONTEXT):
            elapsed = +(
                end["monotonic_observed_seconds"]
                - start["monotonic_observed_seconds"]
            )
        if elapsed < 0:
            raise ProspectiveSourceIntegrityError(
                "derived monotonic elapsed duration must be non-negative"
            )
        supplied = self.monotonic_elapsed_seconds
        if supplied is not None:
            _decimal(supplied, "supplied monotonic elapsed duration")
        with localcontext(DECIMAL_CONTEXT):
            wall_elapsed = _timedelta_seconds(
                end["observed_at"] - start["observed_at"]
            )
            step = +(wall_elapsed - elapsed).copy_abs()
        reasons: list[str] = []
        if not start["usable"] or not end["usable"]:
            reasons.append("CLOCK_HEALTH_INVALID")
        if start["monotonic_domain_id"] != end["monotonic_domain_id"]:
            reasons.append("MONOTONIC_DOMAIN_MISMATCH")
        if supplied is not None and supplied != elapsed:
            reasons.append("SUPPLIED_ELAPSED_MISMATCH")
        if wall_elapsed < 0:
            reasons.append("WALL_CLOCK_MOVED_BACKWARD")
        if step > CLOCK_MAXIMUM_WALL_STEP_SECONDS:
            reasons.append("WALL_CLOCK_STEP_EXCEEDED")

        health_by_digest: dict[str, dict[str, Any]] = {
            start["record_sha256"]: start,
            end["record_sha256"]: end,
        }
        for record in self.health_records:
            row = record.as_record()
            health_by_digest[row["record_sha256"]] = row
        health = sorted(
            health_by_digest.values(),
            key=lambda row: (
                row["observed_at"],
                row["monotonic_observed_seconds"],
                row["record_sha256"],
            ),
        )
        in_interval = [
            row
            for row in health
            if start["observed_at"] <= row["observed_at"] <= end["observed_at"]
        ]
        if any(not row["usable"] for row in in_interval):
            reasons.append("CLOCK_HEALTH_INVALID")
        if any(
            row["monotonic_domain_id"] != start["monotonic_domain_id"]
            for row in in_interval
        ):
            reasons.append("CLOCK_HEALTH_DOMAIN_MISMATCH")
        if not in_interval or in_interval[0]["record_sha256"] != start["record_sha256"]:
            reasons.append("CLOCK_HEALTH_MISSING_AT_START")
        if not in_interval or in_interval[-1]["record_sha256"] != end["record_sha256"]:
            reasons.append("CLOCK_HEALTH_MISSING_AT_END")
        for left, right in zip(in_interval, in_interval[1:], strict=False):
            wall_gap = _timedelta_seconds(right["observed_at"] - left["observed_at"])
            with localcontext(DECIMAL_CONTEXT):
                monotonic_gap = +(
                    right["monotonic_observed_seconds"]
                    - left["monotonic_observed_seconds"]
                )
                gap_divergence = +(wall_gap - monotonic_gap).copy_abs()
            if wall_gap > CLOCK_HEALTH_MAXIMUM_GAP_SECONDS:
                reasons.append("CLOCK_HEALTH_RENEWAL_GAP_EXCEEDED")
            if monotonic_gap < 0:
                reasons.append("CLOCK_MONOTONIC_ORDER_INVALID")
            if gap_divergence > CLOCK_MAXIMUM_WALL_STEP_SECONDS:
                reasons.append("CLOCK_HEALTH_WALL_MONOTONIC_DIVERGENCE")
        payload = {
            "clock_health_record_sha256s": [
                row["record_sha256"] for row in in_interval
            ],
            "end_clock_sha256": end["record_sha256"],
            "maximum_permitted_wall_step_seconds": (
                CLOCK_MAXIMUM_WALL_STEP_SECONDS
            ),
            "maximum_clock_health_gap_seconds": CLOCK_HEALTH_MAXIMUM_GAP_SECONDS,
            "monotonic_domain_id": start["monotonic_domain_id"],
            "monotonic_elapsed_seconds": elapsed,
            "reason_codes": sorted(reasons),
            "schema_version": CLOCK_INTEGRITY_VERSION,
            "start_clock_sha256": start["record_sha256"],
            "usable": not reasons,
            "wall_clock_elapsed_seconds": wall_elapsed,
            "wall_monotonic_divergence_seconds": step,
        }
        return _with_digest(payload)

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        rows = [self.start_clock, *self.health_records, self.end_clock]
        result = {row.record_sha256: row.as_record() for row in rows}
        interval = self.as_record()
        result[interval["record_sha256"]] = interval
        return result


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
        "health_freshness": {
            "maximum_gap_between_valid_observations_seconds": str(
                CLOCK_HEALTH_MAXIMUM_GAP_SECONDS
            ),
            "maximum_health_record_age_seconds": str(
                CLOCK_HEALTH_MAXIMUM_RECORD_AGE_SECONDS
            ),
            "polling_cadence_seconds": str(CLOCK_HEALTH_POLL_CADENCE_SECONDS),
            "request_start_and_end": (
                "Each timing anchor references a valid same-domain health record "
                "no older than 40 seconds; the R5 executable reference uses exact "
                "start/end observations."
            ),
            "stream_interval_and_finalization": (
                "Persist valid same-domain health observations covering the full "
                "interval and finalization path, with no wall or monotonic gap "
                "greater than 40 seconds."
            ),
        },
        "fail_closed_conditions": [
            "clock-health query failure",
            "synchronization unavailable",
            "absolute estimated UTC offset greater than one second",
            "offset uncertainty unavailable or greater than one second",
            "naive or non-UTC wall timestamp",
            "wall/monotonic divergence greater than one second",
            "different host/process/process-start/boot monotonic domains",
            "clock-health record older than 40 seconds",
            "clock-health renewal gap greater than 40 seconds",
        ],
        "monotonic_domain_identity_fields": [
            "collector_host_id",
            "collector_process_id",
            "process_start_identity",
            "boot_id",
        ],
        "maximum_wall_step_seconds": str(CLOCK_MAXIMUM_WALL_STEP_SECONDS),
        "scientific_timestamp_clock": "UTC wall clock",
        "schema_version": CLOCK_INTEGRITY_VERSION,
        "timeouts_and_liveness_use_wall_clock": False,
        "version": CLOCK_INTEGRITY_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload


def _parse_coingecko_market_cap(raw_response_bytes: bytes) -> Decimal:
    if not isinstance(raw_response_bytes, bytes):
        raise ProspectiveSourceIntegrityError(
            "CoinGecko raw_response_bytes must be exact bytes"
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
            raw_response_bytes.decode("utf-8"),
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
    return value


@dataclass(frozen=True)
class CoinGeckoMarketCapRequestAttempt:
    """One immutable scheduled attempt, whether or not an HTTP response exists."""

    attempt_id: str
    requested_date: str
    scheduled_poll_time: datetime
    request_started_at: datetime
    terminated_at: datetime
    outcome: str
    reason_code: str | None
    http_status: int | None
    raw_response_bytes: bytes | None
    collector_version: str
    acquisition_contract_sha256: str
    request_start_clock: ClockIntegrityRecord
    termination_clock: ClockIntegrityRecord
    clock_health_records: tuple[ClockIntegrityRecord, ...] = ()
    supplied_monotonic_elapsed_seconds: Decimal | None = None

    @property
    def response_completed_at(self) -> datetime:
        """Compatibility name; termination is present for every outcome."""

        return self.terminated_at

    @property
    def raw_response(self) -> bytes | None:
        """Compatibility name for callers migrating from R4."""

        return self.raw_response_bytes

    def _identity(self, scheduled: datetime) -> dict[str, Any]:
        return {
            "acquisition_contract_sha256": self.acquisition_contract_sha256,
            "asset_id": "bitcoin",
            "collector_version": self.collector_version,
            "endpoint_identity": (
                "https://api.coingecko.com/api/v3/coins/bitcoin/history"
            ),
            "endpoint_version": "CoinGecko API v3",
            "http_method": "GET",
            "parameter_canonicalization": (
                "UTF-8 RFC3986 query values; keys sorted lexicographically; "
                "date serialized exactly as YYYY-MM-DD"
            ),
            "provider": "coingecko",
            "query_parameters": {
                "date": self.requested_date,
                "localization": "false",
            },
            "requested_currency": "usd",
            "requested_date": self.requested_date,
            "requested_field": "market_data.market_cap.usd",
            "scheduled_poll_time": scheduled,
            "serialized_query": f"date={self.requested_date}&localization=false",
            "source_contract_version": COINGECKO_REQUEST_ATTEMPT_VERSION,
        }

    def as_record(self) -> dict[str, Any]:
        _require_text(self.attempt_id, "attempt_id")
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
        terminated = _require_utc(self.terminated_at, "terminated_at")
        if started < scheduled or terminated < started:
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
        if (scheduled.date() - parsed_date).days not in {1, 2, 3}:
            raise ProspectiveSourceIntegrityError(
                "CoinGecko requested date must be poll-day minus 1, 2, or 3"
            )
        if self.outcome not in COINGECKO_ATTEMPT_OUTCOMES:
            raise ProspectiveSourceIntegrityError("unknown CoinGecko attempt outcome")
        if self.outcome == "SUCCESS" and self.reason_code is not None:
            raise ProspectiveSourceIntegrityError(
                "successful CoinGecko attempt cannot carry a failure reason"
            )
        if self.outcome != "SUCCESS":
            _require_text(self.reason_code or "", "reason_code")
        if self.http_status is not None and (
            not isinstance(self.http_status, int) or isinstance(self.http_status, bool)
        ):
            raise ProspectiveSourceIntegrityError("HTTP status must be integer or null")
        if self.http_status is not None and not 100 <= self.http_status <= 599:
            raise ProspectiveSourceIntegrityError(
                "HTTP status must be null or a real 100..599 status"
            )
        if self.raw_response_bytes is not None and not isinstance(
            self.raw_response_bytes, bytes
        ):
            raise ProspectiveSourceIntegrityError(
                "raw_response_bytes must be exact bytes or null"
            )
        if not _is_sha256(self.acquisition_contract_sha256):
            raise ProspectiveSourceIntegrityError(
                "acquisition contract hash must be SHA-256"
            )
        _require_text(self.collector_version, "collector_version")
        start_clock = self.request_start_clock.as_record()
        termination_clock = self.termination_clock.as_record()
        if start_clock["observed_at"] != started:
            raise ProspectiveSourceIntegrityError(
                "request_started_at must equal its clock-health observed_at"
            )
        if termination_clock["observed_at"] != terminated:
            raise ProspectiveSourceIntegrityError(
                "terminated_at must equal its clock-health observed_at"
            )
        timing_object = ClockIntervalEvidence(
            start_clock=self.request_start_clock,
            end_clock=self.termination_clock,
            monotonic_elapsed_seconds=self.supplied_monotonic_elapsed_seconds,
            health_records=self.clock_health_records,
        )
        timing = timing_object.as_record()
        elapsed = timing["monotonic_elapsed_seconds"]
        hard_cutoff = scheduled.replace(hour=0, minute=56)

        payload_valid = False
        if self.raw_response_bytes is not None:
            try:
                _parse_coingecko_market_cap(self.raw_response_bytes)
                payload_valid = True
            except ProspectiveSourceIntegrityError:
                payload_valid = False
        if not timing["usable"]:
            derived_outcome = "CLOCK_INVALID"
        elif elapsed > COINGECKO_HTTP_TIMEOUT_SECONDS:
            derived_outcome = "TIMEOUT"
        elif terminated > hard_cutoff:
            derived_outcome = "CYCLE_CUTOFF"
        elif self.http_status is None:
            derived_outcome = (
                "TIMEOUT"
                if elapsed >= COINGECKO_HTTP_TIMEOUT_SECONDS
                else "TRANSPORT_ERROR"
            )
        elif self.http_status != 200:
            derived_outcome = "HTTP_ERROR"
        elif self.raw_response_bytes is None:
            derived_outcome = "TRANSPORT_ERROR"
        elif not payload_valid:
            derived_outcome = "INVALID_RESPONSE"
        else:
            derived_outcome = "SUCCESS"
        if self.outcome != derived_outcome:
            raise ProspectiveSourceIntegrityError(
                f"CoinGecko attempt outcome must be {derived_outcome}"
            )

        request_identity = self._identity(scheduled)
        request_sha256 = digest(request_identity)
        payload = {
            **request_identity,
            "actual_request_started_at": started,
            "attempt_id": self.attempt_id,
            "clock_interval_evidence_sha256": timing["record_sha256"],
            "http_status": self.http_status,
            "maximum_success_elapsed_seconds": COINGECKO_HTTP_TIMEOUT_SECONDS,
            "monotonic_elapsed_seconds": elapsed,
            "outcome": self.outcome,
            "raw_response_bytes": self.raw_response_bytes,
            "reason_code": self.reason_code,
            "request_sha256": request_sha256,
            "request_start_clock_sha256": start_clock["record_sha256"],
            "response_sha256": (
                byte_digest(self.raw_response_bytes)
                if self.raw_response_bytes is not None
                else None
            ),
            "schema_version": COINGECKO_REQUEST_ATTEMPT_VERSION,
            "scientific_clock_usable": timing["usable"],
            "terminated_at": terminated,
            "termination_clock_sha256": termination_clock["record_sha256"],
        }
        return _with_digest(payload)

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        timing = ClockIntervalEvidence(
            start_clock=self.request_start_clock,
            end_clock=self.termination_clock,
            monotonic_elapsed_seconds=self.supplied_monotonic_elapsed_seconds,
            health_records=self.clock_health_records,
        )
        records = timing.evidence_records()
        attempt = self.as_record()
        records[attempt["record_sha256"]] = attempt
        return records


# R4 callers imported this name. R5 changes its semantics to a first-class
# attempt, while keeping the import path stable.
CoinGeckoMarketCapRequest = CoinGeckoMarketCapRequestAttempt


@dataclass(frozen=True)
class ValidatedCoinGeckoMarketCapResponse:
    request: CoinGeckoMarketCapRequestAttempt
    market_cap_usd: Decimal

    def as_record(self) -> dict[str, Any]:
        request = self.request.as_record()
        value = self.market_cap_usd
        if not isinstance(value, Decimal) or not value.is_finite() or value <= 0:
            raise ProspectiveSourceIntegrityError(
                "validated CoinGecko USD market cap must be finite and positive"
            )
        payload = {
            "available_at": request["terminated_at"],
            "market_cap_usd": value,
            "observation_time": datetime.combine(
                date.fromisoformat(request["requested_date"]),
                datetime.min.time(),
                tzinfo=UTC,
            ),
            "provider": "coingecko",
            "request_sha256": request["request_sha256"],
            "request_record_sha256": request["record_sha256"],
            "requested_date": request["requested_date"],
            "response_sha256": request["response_sha256"],
            "source": "coingecko_v3_coins_bitcoin_history_market_cap_usd",
            "validation_contract": COINGECKO_RESPONSE_VALIDATION_VERSION,
            "validation_contract_sha256": (
                coingecko_market_cap_response_validation_contract()[
                    "definition_sha256"
                ]
            ),
        }
        return _with_digest(payload)

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        records = self.request.evidence_records()
        validated = self.as_record()
        records[validated["record_sha256"]] = validated
        return records


def validate_coingecko_market_cap_response(
    request: CoinGeckoMarketCapRequestAttempt,
) -> ValidatedCoinGeckoMarketCapResponse:
    record = request.as_record()
    if record["outcome"] != "SUCCESS":
        raise ProspectiveSourceIntegrityError(
            "CoinGecko attempt is not a scientifically successful response"
        )
    raw = record["raw_response_bytes"]
    if raw is None or byte_digest(raw) != record["response_sha256"]:
        raise ProspectiveSourceIntegrityError(
            "CoinGecko exact response bytes do not reproduce their digest"
        )
    value = _parse_coingecko_market_cap(raw)
    return ValidatedCoinGeckoMarketCapResponse(request=request, market_cap_usd=value)


def coingecko_market_cap_request_attempt_contract() -> dict[str, Any]:
    payload = {
        "exact_response_bytes_persistence": "PostgreSQL BYTEA; nullable outside response-bearing outcomes",
        "http_timeout_seconds": str(COINGECKO_HTTP_TIMEOUT_SECONDS),
        "outcome_vocabulary": list(COINGECKO_ATTEMPT_OUTCOMES),
        "request_identity_fields": [
            "provider",
            "endpoint_identity",
            "http_method",
            "asset_id",
            "requested_date",
            "query_parameters",
            "scheduled_poll_time",
            "collector_version",
            "acquisition_contract_sha256",
        ],
        "scientific_success_boundary": (
            "SUCCESS requires mechanically derived monotonic_elapsed_seconds <= 45; "
            "45.000 is admitted and 45.001 is not. The 00:56 cycle cutoff is a "
            "separate independent bound."
        ),
        "schema_version": COINGECKO_REQUEST_ATTEMPT_VERSION,
        "timeout_nullability": {
            "http_status": "null permitted",
            "market_cap_usd": "absent",
            "raw_response_bytes": "null permitted",
            "response_sha256": "null iff raw_response_bytes is null",
        },
        "version": COINGECKO_REQUEST_ATTEMPT_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload


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
        "request_attempt_definition_sha256": (
            coingecko_market_cap_request_attempt_contract()["definition_sha256"]
        ),
        "scientific_replay": (
            "Resolve the exact attempt, clock interval and all clock-health "
            "records; recompute request_sha256 and response_sha256; require "
            "SUCCESS within the inclusive 45-second monotonic timeout and cycle "
            "cutoff; parse raw_response_bytes; then derive value, observation_time "
            "and available_at without trusting surface fields."
        ),
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
            "schema_version": COLLECTOR_HEALTH_VERSION,
            "usable": not reasons,
        }
        return _with_digest(payload)

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        clock = self.clock_integrity.as_record()
        health = self.as_record()
        return {
            clock["record_sha256"]: clock,
            health["record_sha256"]: health,
        }


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
    connection_clock: ClockIntegrityRecord | None = None
    subscription_ack_clock: ClockIntegrityRecord | None = None
    end_clock: ClockIntegrityRecord | None = None

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
        health_clock = self.establishment_health.clock_integrity.as_record()
        if self.connection_clock is None or self.subscription_ack_clock is None:
            raise ProspectiveSourceIntegrityError(
                "connection and subscription acknowledgement need clock evidence"
            )
        connection_clock = self.connection_clock.as_record()
        acknowledgement_clock = self.subscription_ack_clock.as_record()
        if (
            connection_clock["observed_at"] != connected
            or acknowledgement_clock["observed_at"] != acknowledged
            or not connection_clock["usable"]
            or not acknowledgement_clock["usable"]
        ):
            raise ProspectiveSourceIntegrityError(
                "stream connection/acknowledgement clock evidence is invalid"
            )
        if clock["observed_at"] != started or not clock["usable"]:
            raise ProspectiveSourceIntegrityError(
                "stream epoch establishment needs valid clock integrity"
            )
        if (
            health["epoch_id"] != self.local_epoch_id
            or not health["usable"]
            or health["period_start"] > started
            or health["period_end"] < started
            or health["observed_at"] != started
        ):
            raise ProspectiveSourceIntegrityError(
                "stream epoch establishment needs valid collector health"
            )
        if (
            health_clock["monotonic_domain_id"] != clock["monotonic_domain_id"]
            or health_clock["monotonic_observed_seconds"]
            != clock["monotonic_observed_seconds"]
        ):
            raise ProspectiveSourceIntegrityError(
                "stream epoch establishment health uses another clock domain"
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
            if self.end_clock is None:
                raise ProspectiveSourceIntegrityError(
                    "ended stream epoch needs end clock evidence"
                )
        elif self.end_clock is not None:
            raise ProspectiveSourceIntegrityError(
                "open stream epoch cannot carry end clock evidence"
            )
        end_clock = self.end_clock.as_record() if self.end_clock is not None else None
        clock_rows = [connection_clock, acknowledgement_clock, clock]
        if end_clock is not None:
            clock_rows.append(end_clock)
        if end_clock is not None and (
            end_clock["observed_at"] != ended or not end_clock["usable"]
        ):
            raise ProspectiveSourceIntegrityError("epoch end clock evidence is invalid")
        if len({row["monotonic_domain_id"] for row in clock_rows}) != 1:
            raise ProspectiveSourceIntegrityError(
                "stream epoch clocks must share one monotonic domain"
            )
        monotonic_values = [row["monotonic_observed_seconds"] for row in clock_rows]
        if monotonic_values != sorted(monotonic_values):
            raise ProspectiveSourceIntegrityError(
                "stream epoch clocks are not monotonic inside their domain"
            )
        payload = {
            "channel": self.channel,
            "collector_sha256": self.collector_sha256,
            "collector_version": self.collector_version,
            "connection_clock_sha256": connection_clock["record_sha256"],
            "connection_established_at": connected,
            "connection_session_id": self.connection_session_id,
            "end_clock_sha256": (
                end_clock["record_sha256"] if end_clock is not None else None
            ),
            "end_reason": self.end_reason,
            "epoch_ended_at": ended,
            "epoch_started_at": started,
            "establishment_clock_sha256": clock["record_sha256"],
            "establishment_health_sha256": health["record_sha256"],
            "instrument": self.instrument,
            "local_epoch_id": self.local_epoch_id,
            "monotonic_domain_id": clock["monotonic_domain_id"],
            "provider": self.provider,
            "schema_version": STREAM_EPOCH_VERSION,
            "source_contract_sha256": self.source_contract_sha256,
            "subscription_ack_clock_sha256": acknowledgement_clock["record_sha256"],
            "subscription_acknowledged_at": acknowledged,
        }
        return _with_digest(payload)

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        records = self.establishment_health.evidence_records()
        clocks = [
            self.connection_clock,
            self.subscription_ack_clock,
            self.establishment_clock,
            self.end_clock,
        ]
        for clock in clocks:
            if clock is not None:
                row = clock.as_record()
                records[row["record_sha256"]] = row
        epoch = self.as_record()
        records[epoch["record_sha256"]] = epoch
        return records


def end_stream_epoch(
    epoch: SourceStreamEpoch,
    *,
    ended_at: datetime,
    reason: str,
    end_clock: ClockIntegrityRecord,
) -> SourceStreamEpoch:
    if epoch.epoch_ended_at is not None:
        raise ProspectiveSourceIntegrityError("a stream epoch may end only once")
    if reason not in STREAM_EPOCH_END_REASONS:
        raise ProspectiveSourceIntegrityError("unknown stream epoch end reason")
    ended = replace(
        epoch,
        epoch_ended_at=ended_at,
        end_reason=reason,
        end_clock=end_clock,
    )
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
    monotonic_domain_id: str | None = None
    interval_clock_evidence: ClockIntervalEvidence | None = None

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
        wall_elapsed = _timedelta_seconds(end - start)
        with localcontext(DECIMAL_CONTEXT):
            monotonic_elapsed = +(end_mono - start_mono)
            interval_divergence = +(wall_elapsed - monotonic_elapsed).copy_abs()
        rows = sorted(
            (check.as_record() for check in self.checks),
            key=lambda row: (row["ping_sent_monotonic_seconds"], row["request_id"]),
        )
        reasons: list[str] = []
        if self.monotonic_domain_id is None or not _is_sha256(
            self.monotonic_domain_id
        ):
            reasons.append("LIVENESS_MONOTONIC_DOMAIN_MISSING")
        if interval_divergence > CLOCK_MAXIMUM_WALL_STEP_SECONDS:
            reasons.append("LIVENESS_WALL_MONOTONIC_DIVERGENCE")
        interval_clock_sha256: str | None = None
        if self.interval_clock_evidence is None:
            reasons.append("LIVENESS_CLOCK_INTERVAL_MISSING")
        else:
            interval_clock = self.interval_clock_evidence.as_record()
            interval_clock_sha256 = interval_clock["record_sha256"]
            if not interval_clock["usable"]:
                reasons.append("LIVENESS_CLOCK_INTERVAL_INVALID")
            if (
                interval_clock["monotonic_domain_id"] != self.monotonic_domain_id
                or interval_clock["wall_clock_elapsed_seconds"] != wall_elapsed
                or interval_clock["monotonic_elapsed_seconds"] != monotonic_elapsed
            ):
                reasons.append("LIVENESS_CLOCK_INTERVAL_BINDING_MISMATCH")
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
            "interval_clock_evidence_sha256": interval_clock_sha256,
            "monotonic_domain_id": self.monotonic_domain_id,
            "monotonic_elapsed_seconds": monotonic_elapsed,
            "maximum_permitted_liveness_gap_seconds": (
                STREAM_LIVENESS_MAXIMUM_GAP_SECONDS
            ),
            "ping_cadence_seconds": STREAM_LIVENESS_PING_CADENCE_SECONDS,
            "pong_timeout_seconds": STREAM_LIVENESS_PONG_TIMEOUT_SECONDS,
            "reason_codes": sorted(set(reasons)),
            "schema_version": STREAM_LIVENESS_VERSION,
            "usable": not reasons,
            "wall_elapsed_seconds": wall_elapsed,
            "wall_monotonic_divergence_seconds": interval_divergence,
        }
        return _with_digest(payload)

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        records: dict[str, dict[str, Any]] = {}
        if self.interval_clock_evidence is not None:
            records.update(self.interval_clock_evidence.evidence_records())
        liveness = self.as_record()
        records[liveness["record_sha256"]] = liveness
        return records


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
    received_at_clock: ClockIntegrityRecord | None = None

    def as_record(self) -> dict[str, Any]:
        expected_instrument = KRAKEN_IDENTITIES.get(self.provider)
        if expected_instrument != self.instrument or self.channel != KRAKEN_CHANNEL:
            raise ProspectiveSourceIntegrityError("unexpected source-event identity")
        _require_text(self.epoch_id, "event epoch_id")
        _require_text(self.source_event_id, "source_event_id")
        event_time = _require_utc(self.event_time, "event_time")
        received_at = _require_utc(self.received_at, "received_at")
        if self.received_at_clock is None:
            raise ProspectiveSourceIntegrityError(
                "source event received_at needs clock evidence"
            )
        received_clock = self.received_at_clock.as_record()
        if received_clock["observed_at"] != received_at or not received_clock["usable"]:
            raise ProspectiveSourceIntegrityError(
                "source event received_at clock evidence is invalid"
            )
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
            "received_at_clock_sha256": received_clock["record_sha256"],
            "received_at_monotonic_seconds": received_clock[
                "monotonic_observed_seconds"
            ],
            "sequence_number": self.sequence_number,
            "side": self.side,
            "signed_notional_usd": signed_notional,
            "source_event_id": self.source_event_id,
            "schema_version": SOURCE_EVENT_VERSION,
        }
        payload["scientific_payload_sha256"] = digest(
            {
                key: value
                for key, value in payload.items()
                if key
                not in {
                    "raw_payload_sha256",
                    "received_at",
                    "received_at_clock_sha256",
                    "received_at_monotonic_seconds",
                }
            }
        )
        return _with_digest(payload)

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        if self.received_at_clock is None:
            self.as_record()
        assert self.received_at_clock is not None
        clock = self.received_at_clock.as_record()
        event = self.as_record()
        return {
            clock["record_sha256"]: clock,
            event["record_sha256"]: event,
        }


@dataclass(frozen=True)
class KrakenFuturesInstrumentMetadataValidation:
    """Runtime PI_XBTUSD metadata evidence, independently rechecked per hour."""

    validation_id: str
    retrieved_at: datetime
    retrieval_clock: ClockIntegrityRecord
    product_id: str
    instrument_type: str
    underlying: str
    contract_size_usd: Decimal
    tradeable: bool
    raw_payload_sha256: str
    endpoint: str = KRAKEN_FUTURES_METADATA_ENDPOINT
    query_succeeded: bool = True

    def as_record(self) -> dict[str, Any]:
        _require_text(self.validation_id, "metadata validation_id")
        retrieved = _require_utc(self.retrieved_at, "metadata retrieved_at")
        _require_bool(self.query_succeeded, "query_succeeded")
        clock = self.retrieval_clock.as_record()
        if clock["observed_at"] != retrieved:
            raise ProspectiveSourceIntegrityError(
                "metadata retrieved_at must bind its clock record"
            )
        if not _is_sha256(self.raw_payload_sha256):
            raise ProspectiveSourceIntegrityError(
                "metadata raw payload digest must be SHA-256"
            )
        size = _decimal(self.contract_size_usd, "contract_size_usd")
        reasons: list[str] = []
        if not self.query_succeeded:
            reasons.append("METADATA_UNAVAILABLE")
        if not clock["usable"]:
            reasons.append("METADATA_CLOCK_INVALID")
        if self.endpoint != KRAKEN_FUTURES_METADATA_ENDPOINT:
            reasons.append("METADATA_ENDPOINT_MISMATCH")
        if self.product_id != KRAKEN_FUTURES_INSTRUMENT:
            reasons.append("METADATA_PRODUCT_ID_MISMATCH")
        if self.instrument_type != "futures_inverse":
            reasons.append("METADATA_INSTRUMENT_TYPE_MISMATCH")
        if self.underlying != "rr_xbtusd":
            reasons.append("METADATA_UNDERLYING_MISMATCH")
        if size != Decimal("1"):
            reasons.append("METADATA_CONTRACT_SIZE_DRIFT")
        if self.tradeable is not True:
            reasons.append("METADATA_NOT_TRADEABLE")
        payload = {
            "contract_size_usd": size,
            "endpoint": self.endpoint,
            "instrument_type": self.instrument_type,
            "maximum_age_seconds": KRAKEN_FUTURES_METADATA_MAXIMUM_AGE_SECONDS,
            "product_id": self.product_id,
            "query_succeeded": self.query_succeeded,
            "raw_payload_sha256": self.raw_payload_sha256,
            "reason_codes": sorted(reasons),
            "retrieval_clock_sha256": clock["record_sha256"],
            "retrieved_at": retrieved,
            "schema_version": KRAKEN_FUTURES_METADATA_VALIDATION_VERSION,
            "tradeable": self.tradeable,
            "underlying": self.underlying,
            "usable": not reasons,
            "validation_id": self.validation_id,
        }
        return _with_digest(payload)

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        clock = self.retrieval_clock.as_record()
        metadata = self.as_record()
        return {
            clock["record_sha256"]: clock,
            metadata["record_sha256"]: metadata,
        }


@dataclass(frozen=True)
class PersistedEvidenceResolver:
    """Content-addressed resolver used by every higher scientific derivation."""

    records: Mapping[str, Mapping[str, Any]]

    def resolve(
        self,
        record_sha256: str,
        *,
        schema_version: str | None = None,
    ) -> dict[str, Any]:
        if not _is_sha256(record_sha256):
            raise ProspectiveSourceIntegrityError(
                "evidence reference must be a SHA-256 digest"
            )
        try:
            record = dict(self.records[record_sha256])
        except KeyError as exc:
            raise ProspectiveSourceIntegrityError(
                f"referenced evidence {record_sha256} is missing"
            ) from exc
        declared = record.pop("record_sha256", None)
        if declared != record_sha256 or digest(record) != record_sha256:
            raise ProspectiveSourceIntegrityError(
                f"referenced evidence {record_sha256} does not reproduce"
            )
        record["record_sha256"] = declared
        if schema_version is not None and record.get("schema_version") != schema_version:
            raise ProspectiveSourceIntegrityError(
                f"referenced evidence {record_sha256} has wrong schema/version"
            )
        return record

    @classmethod
    def from_objects(cls, *objects: Any) -> PersistedEvidenceResolver:
        records: dict[str, dict[str, Any]] = {}
        for obj in objects:
            if not hasattr(obj, "evidence_records"):
                raise ProspectiveSourceIntegrityError(
                    "scientific evidence object does not expose persistence records"
                )
            for key, value in obj.evidence_records().items():
                existing = records.get(key)
                if existing is not None and existing != value:
                    raise ProspectiveSourceIntegrityError(
                        "content-addressed evidence collision"
                    )
                records[key] = value
        return cls(records=records)


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
    runtime_metadata_start: KrakenFuturesInstrumentMetadataValidation | None = None
    runtime_metadata_finalization: (
        KrakenFuturesInstrumentMetadataValidation | None
    ) = None

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
        health_clock = self.collector_health.clock_integrity.as_record()
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
        if health["observed_at"] > finalized:
            reasons.append("COLLECTOR_HEALTH_OBSERVED_AFTER_FINALIZATION")
        if health_clock["monotonic_domain_id"] != epoch["monotonic_domain_id"]:
            reasons.append("COLLECTOR_HEALTH_CLOCK_DOMAIN_MISMATCH")
        if finalized < end:
            reasons.append("FINALIZED_BEFORE_INTERVAL_END")
        if final_clock["observed_at"] != finalized or not final_clock["usable"]:
            reasons.append("FINALIZATION_CLOCK_INVALID")
        if final_clock["monotonic_domain_id"] != epoch["monotonic_domain_id"]:
            reasons.append("FINALIZATION_CLOCK_DOMAIN_MISMATCH")
        if not timing["usable"]:
            reasons.extend(timing["reason_codes"])
        if health_clock["record_sha256"] not in timing[
            "clock_health_record_sha256s"
        ]:
            reasons.append("COLLECTOR_HEALTH_CLOCK_NOT_IN_INTERVAL_EVIDENCE")
        if (
            timing["start_clock_sha256"]
            != epoch["establishment_clock_sha256"]
            or timing["end_clock_sha256"] != final_clock["record_sha256"]
        ):
            reasons.append("CLOCK_INTERVAL_BINDING_MISMATCH")
        if liveness.get("monotonic_domain_id") != epoch["monotonic_domain_id"]:
            reasons.append("LIVENESS_MONOTONIC_DOMAIN_MISMATCH")

        metadata_rows: list[dict[str, Any]] = []
        if epoch["provider"] == KRAKEN_FUTURES_PROVIDER:
            if (
                self.runtime_metadata_start is None
                or self.runtime_metadata_finalization is None
            ):
                reasons.append("FUTURES_RUNTIME_METADATA_MISSING")
            else:
                start_metadata = self.runtime_metadata_start.as_record()
                final_metadata = self.runtime_metadata_finalization.as_record()
                metadata_rows = [start_metadata, final_metadata]
                if not start_metadata["usable"] or not final_metadata["usable"]:
                    reasons.append("FUTURES_RUNTIME_METADATA_INVALID")
                start_age = _timedelta_seconds(
                    start - start_metadata["retrieved_at"]
                )
                if (
                    start_age < 0
                    or start_age > KRAKEN_FUTURES_METADATA_MAXIMUM_AGE_SECONDS
                ):
                    reasons.append("FUTURES_START_METADATA_STALE")
                if not (
                    end <= final_metadata["retrieved_at"] <= finalized
                ) or _timedelta_seconds(
                    finalized - final_metadata["retrieved_at"]
                ) > KRAKEN_FUTURES_METADATA_MAXIMUM_AGE_SECONDS:
                    reasons.append("FUTURES_FINAL_METADATA_STALE")
                material_fields = (
                    "product_id",
                    "instrument_type",
                    "underlying",
                    "contract_size_usd",
                    "tradeable",
                )
                if any(
                    start_metadata[field] != final_metadata[field]
                    for field in material_fields
                ):
                    reasons.append("FUTURES_RUNTIME_METADATA_DRIFT")
                if any(
                    row["retrieval_clock_sha256"]
                    not in timing["clock_health_record_sha256s"]
                    for row in metadata_rows
                ):
                    reasons.append("FUTURES_METADATA_CLOCK_NOT_IN_INTERVAL_EVIDENCE")
        elif (
            self.runtime_metadata_start is not None
            or self.runtime_metadata_finalization is not None
        ):
            reasons.append("SPOT_INTERVAL_HAS_FUTURES_METADATA")

        unique: dict[str, dict[str, Any]] = {}
        captured_event_rows: list[dict[str, Any]] = []
        duplicate_retransmissions = 0
        for event in self.events:
            try:
                row = event.as_record()
            except ProspectiveSourceIntegrityError:
                reasons.append("INVALID_SOURCE_EVENT")
                continue
            captured_event_rows.append(row)
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
            if row["received_at"] > finalized:
                reasons.append("SOURCE_EVENT_RECEIVED_AFTER_FINALIZATION")
                continue
            if row["received_at_clock_sha256"] not in timing[
                "clock_health_record_sha256s"
            ]:
                reasons.append("SOURCE_EVENT_CLOCK_NOT_IN_INTERVAL_EVIDENCE")
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
                if (
                    row["received_at"],
                    row["raw_payload_sha256"],
                    row["record_sha256"],
                ) < (
                    previous["received_at"],
                    previous["raw_payload_sha256"],
                    previous["record_sha256"],
                ):
                    unique[row["source_event_id"]] = row
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
            "event_record_sha256s": sorted(
                row["record_sha256"] for row in captured_event_rows
            ),
            "events": event_rows,
            "finalized_at": finalized,
            "finalization_clock_sha256": final_clock["record_sha256"],
            "interval_end": end,
            "interval_start": start,
            "interval_clock_evidence_sha256": liveness.get(
                "interval_clock_evidence_sha256"
            ),
            "liveness_pass": liveness["usable"],
            "liveness_sha256": liveness["record_sha256"],
            "metadata_validation_sha256s": [
                row["record_sha256"] for row in metadata_rows
            ],
            "monotonic_domain_id": epoch["monotonic_domain_id"],
            "provider": epoch["provider"],
            "provider_sequence_integrity_pass": (
                health["provider_sequence_validation_failure_count"] == 0
            ),
            "instrument": epoch["instrument"],
            "reason_codes": sorted(set(reasons)),
            "schema_version": STREAM_INTERVAL_COMPLETENESS_VERSION,
            "source_epoch_sha256": epoch["record_sha256"],
            "epoch_to_finalization_clock_sha256": timing["record_sha256"],
            "subscription_ack_before_start": (
                epoch["subscription_acknowledged_at"] < start
            ),
        }
        return _with_digest(payload)

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        records = self.epoch.evidence_records()
        records.update(self.liveness.evidence_records())
        records.update(self.collector_health.evidence_records())
        records.update(self.epoch_to_finalization_clock.evidence_records())
        final_clock = self.finalization_clock.as_record()
        records[final_clock["record_sha256"]] = final_clock
        for event in self.events:
            records.update(event.evidence_records())
        for metadata in (
            self.runtime_metadata_start,
            self.runtime_metadata_finalization,
        ):
            if metadata is not None:
                records.update(metadata.evidence_records())
        interval = self.as_record()
        records[interval["record_sha256"]] = interval
        return records


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

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        records = self.spot.evidence_records()
        records.update(self.perp.evidence_records())
        common = self.as_record()
        records[common["record_sha256"]] = common
        return records


def _clock_from_record(record: Mapping[str, Any]) -> ClockIntegrityRecord:
    domain = record.get("monotonic_domain")
    if not isinstance(domain, Mapping):
        raise ProspectiveSourceIntegrityError("clock monotonic domain is missing")
    result = ClockIntegrityRecord(
        observed_at=record["observed_at"],
        synchronization_mechanism=record["synchronization_mechanism"],
        synchronization_source=record["synchronization_source"],
        synchronized=record["synchronized"],
        estimated_utc_offset_seconds=record["estimated_utc_offset_seconds"],
        offset_uncertainty_seconds=record["offset_uncertainty_seconds"],
        collector_host_id=domain["collector_host_id"],
        collector_process_id=domain["collector_process_id"],
        health_query_succeeded=record["health_query_succeeded"],
        monotonic_observed_seconds=record["monotonic_observed_seconds"],
        process_start_identity=domain["process_start_identity"],
        boot_id=domain["boot_id"],
    )
    if result.as_record() != dict(record):
        raise ProspectiveSourceIntegrityError("clock record does not replay")
    return result


def replay_clock_interval(
    record_sha256: str,
    resolver: PersistedEvidenceResolver,
) -> ClockIntervalEvidence:
    record = resolver.resolve(record_sha256, schema_version=CLOCK_INTEGRITY_VERSION)
    start = _clock_from_record(resolver.resolve(record["start_clock_sha256"]))
    end = _clock_from_record(resolver.resolve(record["end_clock_sha256"]))
    health = tuple(
        _clock_from_record(resolver.resolve(item))
        for item in record["clock_health_record_sha256s"]
    )
    result = ClockIntervalEvidence(
        start_clock=start,
        end_clock=end,
        monotonic_elapsed_seconds=record["monotonic_elapsed_seconds"],
        health_records=health,
    )
    if result.as_record() != record:
        raise ProspectiveSourceIntegrityError("clock interval evidence does not replay")
    return result


def replay_coingecko_market_cap_attempt(
    record_sha256: str,
    resolver: PersistedEvidenceResolver,
) -> CoinGeckoMarketCapRequestAttempt:
    record = resolver.resolve(
        record_sha256,
        schema_version=COINGECKO_REQUEST_ATTEMPT_VERSION,
    )
    timing = replay_clock_interval(record["clock_interval_evidence_sha256"], resolver)
    start = _clock_from_record(resolver.resolve(record["request_start_clock_sha256"]))
    end = _clock_from_record(resolver.resolve(record["termination_clock_sha256"]))
    health = tuple(
        _clock_from_record(resolver.resolve(item))
        for item in timing.as_record()["clock_health_record_sha256s"]
    )
    attempt = CoinGeckoMarketCapRequestAttempt(
        attempt_id=record["attempt_id"],
        requested_date=record["requested_date"],
        scheduled_poll_time=record["scheduled_poll_time"],
        request_started_at=record["actual_request_started_at"],
        terminated_at=record["terminated_at"],
        outcome=record["outcome"],
        reason_code=record["reason_code"],
        http_status=record["http_status"],
        raw_response_bytes=record["raw_response_bytes"],
        collector_version=record["collector_version"],
        acquisition_contract_sha256=record["acquisition_contract_sha256"],
        request_start_clock=start,
        termination_clock=end,
        clock_health_records=health,
        supplied_monotonic_elapsed_seconds=record["monotonic_elapsed_seconds"],
    )
    if attempt.as_record() != record:
        raise ProspectiveSourceIntegrityError("CoinGecko attempt does not replay")
    return attempt


def replay_coingecko_market_cap_response(
    attempt_record_sha256: str,
    resolver: PersistedEvidenceResolver,
) -> ValidatedCoinGeckoMarketCapResponse:
    attempt = replay_coingecko_market_cap_attempt(attempt_record_sha256, resolver)
    return validate_coingecko_market_cap_response(attempt)


def _collector_health_from_record(
    record: Mapping[str, Any], resolver: PersistedEvidenceResolver
) -> CollectorHealthRecord:
    clock = _clock_from_record(resolver.resolve(record["clock_integrity_sha256"]))
    result = CollectorHealthRecord(
        epoch_id=record["epoch_id"],
        period_start=record["period_start"],
        period_end=record["period_end"],
        observed_at=record["observed_at"],
        clock_integrity=clock,
        parser_failure_count=record["parser_failure_count"],
        serialization_failure_count=record["serialization_failure_count"],
        durable_append_failure_count=record["durable_append_failure_count"],
        queue_overflow_count=record["queue_overflow_count"],
        dropped_event_count=record["dropped_event_count"],
        unexpected_message_type_count=record["unexpected_message_type_count"],
        duplicate_conflict_count=record["duplicate_conflict_count"],
        collector_exception_count=record["collector_exception_count"],
        provider_sequence_validation_failure_count=record[
            "provider_sequence_validation_failure_count"
        ],
    )
    if result.as_record() != dict(record):
        raise ProspectiveSourceIntegrityError("collector health does not replay")
    return result


def _epoch_from_record(
    record: Mapping[str, Any], resolver: PersistedEvidenceResolver
) -> SourceStreamEpoch:
    establishment_health_record = resolver.resolve(
        record["establishment_health_sha256"],
        schema_version=COLLECTOR_HEALTH_VERSION,
    )
    health = _collector_health_from_record(establishment_health_record, resolver)
    result = SourceStreamEpoch(
        provider=record["provider"],
        instrument=record["instrument"],
        channel=record["channel"],
        connection_session_id=record["connection_session_id"],
        local_epoch_id=record["local_epoch_id"],
        connection_established_at=record["connection_established_at"],
        subscription_acknowledged_at=record["subscription_acknowledged_at"],
        epoch_started_at=record["epoch_started_at"],
        collector_version=record["collector_version"],
        collector_sha256=record["collector_sha256"],
        source_contract_sha256=record["source_contract_sha256"],
        establishment_clock=_clock_from_record(
            resolver.resolve(record["establishment_clock_sha256"])
        ),
        establishment_health=health,
        epoch_ended_at=record["epoch_ended_at"],
        end_reason=record["end_reason"],
        connection_clock=_clock_from_record(
            resolver.resolve(record["connection_clock_sha256"])
        ),
        subscription_ack_clock=_clock_from_record(
            resolver.resolve(record["subscription_ack_clock_sha256"])
        ),
        end_clock=(
            _clock_from_record(resolver.resolve(record["end_clock_sha256"]))
            if record["end_clock_sha256"] is not None
            else None
        ),
    )
    if result.as_record() != dict(record):
        raise ProspectiveSourceIntegrityError("source stream epoch does not replay")
    return result


def _liveness_from_record(
    record: Mapping[str, Any], resolver: PersistedEvidenceResolver
) -> StreamLivenessEvidence:
    interval_clock = replay_clock_interval(
        record["interval_clock_evidence_sha256"], resolver
    )
    checks = tuple(
        LivenessCheck(
            request_id=row["request_id"],
            ping_sent_monotonic_seconds=row["ping_sent_monotonic_seconds"],
            pong_received_monotonic_seconds=row["pong_received_monotonic_seconds"],
        )
        for row in record["checks"]
    )
    result = StreamLivenessEvidence(
        epoch_id=record["epoch_id"],
        interval_start=record["interval_start"],
        interval_end=record["interval_end"],
        interval_start_monotonic_seconds=record[
            "interval_start_monotonic_seconds"
        ],
        interval_end_monotonic_seconds=record["interval_end_monotonic_seconds"],
        checks=checks,
        monotonic_domain_id=record["monotonic_domain_id"],
        interval_clock_evidence=interval_clock,
    )
    if result.as_record() != dict(record):
        raise ProspectiveSourceIntegrityError("stream liveness does not replay")
    return result


def _event_from_record(
    record: Mapping[str, Any], resolver: PersistedEvidenceResolver
) -> CapturedSourceEvent:
    result = CapturedSourceEvent(
        provider=record["provider"],
        instrument=record["instrument"],
        channel=record["channel"],
        epoch_id=record["epoch_id"],
        source_event_id=record["source_event_id"],
        event_time=record["event_time"],
        received_at=record["received_at"],
        side=record["side"],
        event_type=record["event_type"],
        quantity=record["quantity"],
        price=record["price"],
        raw_payload_sha256=record["raw_payload_sha256"],
        sequence_number=record["sequence_number"],
        received_at_clock=_clock_from_record(
            resolver.resolve(record["received_at_clock_sha256"])
        ),
    )
    if result.as_record() != dict(record):
        raise ProspectiveSourceIntegrityError("source event does not replay")
    return result


def _metadata_from_record(
    record: Mapping[str, Any], resolver: PersistedEvidenceResolver
) -> KrakenFuturesInstrumentMetadataValidation:
    result = KrakenFuturesInstrumentMetadataValidation(
        validation_id=record["validation_id"],
        retrieved_at=record["retrieved_at"],
        retrieval_clock=_clock_from_record(
            resolver.resolve(record["retrieval_clock_sha256"])
        ),
        product_id=record["product_id"],
        instrument_type=record["instrument_type"],
        underlying=record["underlying"],
        contract_size_usd=record["contract_size_usd"],
        tradeable=record["tradeable"],
        raw_payload_sha256=record["raw_payload_sha256"],
        endpoint=record["endpoint"],
        query_succeeded=record["query_succeeded"],
    )
    if result.as_record() != dict(record):
        raise ProspectiveSourceIntegrityError("runtime metadata does not replay")
    return result


def replay_stream_interval_completeness(
    record_sha256: str,
    resolver: PersistedEvidenceResolver,
) -> StreamIntervalCompleteness:
    record = resolver.resolve(
        record_sha256,
        schema_version=STREAM_INTERVAL_COMPLETENESS_VERSION,
    )
    epoch = _epoch_from_record(
        resolver.resolve(record["source_epoch_sha256"], schema_version=STREAM_EPOCH_VERSION),
        resolver,
    )
    liveness = _liveness_from_record(
        resolver.resolve(record["liveness_sha256"], schema_version=STREAM_LIVENESS_VERSION),
        resolver,
    )
    health = _collector_health_from_record(
        resolver.resolve(
            record["collector_health_sha256"],
            schema_version=COLLECTOR_HEALTH_VERSION,
        ),
        resolver,
    )
    events = tuple(
        _event_from_record(
            resolver.resolve(item, schema_version=SOURCE_EVENT_VERSION), resolver
        )
        for item in record["event_record_sha256s"]
    )
    metadata = tuple(
        _metadata_from_record(
            resolver.resolve(
                item,
                schema_version=KRAKEN_FUTURES_METADATA_VALIDATION_VERSION,
            ),
            resolver,
        )
        for item in record["metadata_validation_sha256s"]
    )
    if len(metadata) not in {0, 2}:
        raise ProspectiveSourceIntegrityError(
            "stream interval metadata evidence has invalid cardinality"
        )
    result = StreamIntervalCompleteness(
        epoch=epoch,
        liveness=liveness,
        collector_health=health,
        events=events,
        interval_start=record["interval_start"],
        finalized_at=record["finalized_at"],
        finalization_clock=_clock_from_record(
            resolver.resolve(record["finalization_clock_sha256"])
        ),
        epoch_to_finalization_clock=replay_clock_interval(
            record["epoch_to_finalization_clock_sha256"], resolver
        ),
        runtime_metadata_start=metadata[0] if metadata else None,
        runtime_metadata_finalization=metadata[1] if metadata else None,
    )
    if result.as_record() != record:
        raise ProspectiveSourceIntegrityError(
            "stream interval completeness does not replay"
        )
    return result


def replay_cvd_hour_completeness(
    record_sha256: str,
    resolver: PersistedEvidenceResolver,
) -> CvdHourCompleteness:
    record = resolver.resolve(
        record_sha256,
        schema_version=CVD_INTERVAL_COMPLETENESS_VERSION,
    )
    result = CvdHourCompleteness(
        spot=replay_stream_interval_completeness(
            record["spot_interval_completeness_sha256"], resolver
        ),
        perp=replay_stream_interval_completeness(
            record["perp_interval_completeness_sha256"], resolver
        ),
    )
    if result.as_record() != record:
        raise ProspectiveSourceIntegrityError("CVD hour completeness does not replay")
    return result


def kraken_futures_instrument_metadata_validation_contract() -> dict[str, Any]:
    payload = {
        "endpoint": KRAKEN_FUTURES_METADATA_ENDPOINT,
        "fail_closed": True,
        "frozen_material_fields": {
            "contractSize": "1 USD",
            "symbol": KRAKEN_FUTURES_INSTRUMENT,
            "tradeable": True,
            "type": "futures_inverse",
            "underlying": "rr_xbtusd",
        },
        "maximum_start_record_age_seconds": str(
            KRAKEN_FUTURES_METADATA_MAXIMUM_AGE_SECONDS
        ),
        "maximum_final_record_age_at_finalization_seconds": str(
            KRAKEN_FUTURES_METADATA_MAXIMUM_AGE_SECONDS
        ),
        "revalidation_cadence": (
            "Validate no more than five minutes before each exact UTC hour and "
            "revalidate at or after interval close but no later than scientific "
            "finalization. Both records must match every material field."
        ),
        "semantic_change_rule": (
            "Any material drift makes the hour INVALID / REQUIRED_INPUT_MISSING; "
            "do not change contract size or substitute an instrument. A source "
            "semantic change requires successor pre-data governance."
        ),
        "schema_version": KRAKEN_FUTURES_METADATA_VALIDATION_VERSION,
        "selection_used_stage_b_outcomes": False,
        "version": KRAKEN_FUTURES_METADATA_VALIDATION_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload


def scientific_evidence_resolver_contract() -> dict[str, Any]:
    payload = {
        "content_addressed_store": {
            "canonical_payload_encoding": (
                "canonical ASCII JSON of the normalized payload without "
                "record_sha256, using the frozen lossless exact-bytes tag and "
                "schema-versioned Decimal/timestamp decoding"
            ),
            "digest_rule": "sha256(canonical_payload_bytes) == record_sha256",
            "table": "research.prospective_scientific_evidence_record",
            "typed_tables_are_authority": False,
        },
        "digest_role": "identity and integrity check, never semantic authority",
        "missing_reference": "REFUSE",
        "replay_order": [
            "load exact persisted record",
            "recompute digest and validate schema/version",
            "resolve every transitive material reference",
            "re-run the owner predicate",
            "verify cross-record interval/provider/instrument/epoch/clock identity",
            "compare every scientific surface field with the replay-derived field",
        ],
        "scientific_surface_records_are_authorities": False,
        "substitution_reference": "REFUSE",
        "version": SCIENTIFIC_EVIDENCE_RESOLVER_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload


def stream_liveness_policy_contract() -> dict[str, Any]:
    payload = {
        "clock": "monotonic",
        "clock_interval_cross_binding": (
            "The exact wall interval and same-domain monotonic start/end anchors "
            "must differ by no more than one second. A 3600-second wall hour "
            "backed by 20 monotonic seconds is invalid."
        ),
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
            "monotonic_domain_id",
            "subscription_acknowledged_at",
            "epoch_started_at",
            "epoch_ended_at",
            "end_reason",
            "collector_version",
            "collector_sha256",
            "source_contract_sha256",
            "establishment_clock_sha256",
            "establishment_health_sha256",
            "connection_clock_sha256",
            "subscription_ack_clock_sha256",
            "end_clock_sha256",
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
        "event_receipt_cutoff": (
            "Every event persists provider event_time, local received_at and its "
            "clock record; event_time must be in the half-open hour and received_at "
            "must be no later than finalized_at. Later arrivals can appear only in "
            "an append-only later revision with a later available_at."
        ),
        "evidence_replay": (
            "Resolve and recompute the complete epoch, liveness, collector-health, "
            "clock interval, runtime metadata and canonical event census before "
            "trusting complete or any CVD value."
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
        "runtime_futures_metadata_definition_sha256": (
            kraken_futures_instrument_metadata_validation_contract()[
                "definition_sha256"
            ]
        ),
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
            "decision_time": decision,
            "event_count": None,
            "event_type": "liquidation",
            "feed_status": status,
            "finalized_at": interval["finalized_at"],
            "instrument": interval["instrument"],
            "long_liquidation_notional_usd": None,
            "observation_time": interval["interval_start"],
            "provider": interval["provider"],
            "reason": reason,
            "schema_version": VERIFIED_LIQUIDATION_HOUR_VERSION,
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
        "decision_time": decision,
        "event_count": len(liquidation_events),
        "event_type": "liquidation",
        "feed_status": status,
        "finalized_at": interval["finalized_at"],
        "instrument": interval["instrument"],
        "long_liquidation_notional_usd": long_notional,
        "observation_time": interval["interval_start"],
        "provider": interval["provider"],
        "reason": None,
        "schema_version": VERIFIED_LIQUIDATION_HOUR_VERSION,
        "short_liquidation_notional_usd": short_notional,
        "source_record_ids_digest": digest(ids),
        "source_stream_epoch_sha256": interval["source_epoch_sha256"],
        "stream_liveness_sha256": interval["liveness_sha256"],
        "timeframe": "1h",
    }
    return _with_digest(payload)


@dataclass(frozen=True)
class VerifiedLiquidationHour:
    """Surface row whose values exist only as a replay of cited completeness."""

    completeness: StreamIntervalCompleteness
    decision_time: datetime

    def as_record(self) -> dict[str, Any]:
        return classify_liquidation_interval(
            self.completeness,
            decision_time=self.decision_time,
        )

    def evidence_records(self) -> dict[str, dict[str, Any]]:
        records = self.completeness.evidence_records()
        row = self.as_record()
        records[row["record_sha256"]] = row
        return records


def replay_verified_liquidation_hour(
    record_sha256: str,
    resolver: PersistedEvidenceResolver,
) -> dict[str, Any]:
    persisted = resolver.resolve(
        record_sha256,
        schema_version=VERIFIED_LIQUIDATION_HOUR_VERSION,
    )
    completeness = replay_stream_interval_completeness(
        persisted["completeness_evidence_sha256"], resolver
    )
    derived = classify_liquidation_interval(
        completeness,
        decision_time=persisted["decision_time"],
    )
    if derived != persisted:
        raise ProspectiveSourceIntegrityError(
            "liquidation surface differs from replayed completeness evidence"
        )
    return derived


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
        "surface_record_authoritative": False,
        "verified_hour_version": VERIFIED_LIQUIDATION_HOUR_VERSION,
        "verification_rule": (
            "Resolve completeness_evidence_sha256 and its transitive graph, "
            "replay completeness, rederive status/count/notionals and verify "
            "interval identity before accepting the hourly surface."
        ),
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
    *,
    resolver: PersistedEvidenceResolver | None = None,
) -> dict[str, Any]:
    if resolver is None:
        raise ProspectiveSourceIntegrityError(
            "daily liquidation aggregation requires a persisted evidence resolver"
        )
    expected = expected_liquidation_hour_ids(day)
    seen: dict[str, dict[str, Any]] = {}
    duplicate_ids: list[str] = []
    for record in hourly_records:
        try:
            declared_sha256 = record["record_sha256"]
            persisted = resolver.resolve(
                declared_sha256,
                schema_version=VERIFIED_LIQUIDATION_HOUR_VERSION,
            )
            if persisted != dict(record):
                raise ProspectiveSourceIntegrityError(
                    "hourly liquidation row differs from content-addressed evidence"
                )
            verified = replay_verified_liquidation_hour(declared_sha256, resolver)
            start = _require_utc(verified["observation_time"], "observation_time")
        except (KeyError, ProspectiveSourceIntegrityError):
            raise ProspectiveSourceIntegrityError(
                "daily reducer refused unresolved or invalid hourly evidence"
            )
        interval_id = f"{start.isoformat()}|{(start + timedelta(hours=1)).isoformat()}"
        if interval_id in seen:
            duplicate_ids.append(interval_id)
        else:
            seen[interval_id] = verified
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
        record = seen[interval_id]
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
        "hourly_completeness_evidence_digests": [
            seen[key].get("completeness_evidence_sha256")
            for key in expected
            if key in seen
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
            "All 24 exact hours exist, independently replay complete through the "
            "persisted resolver, and each replay-derived event_count is zero"
        ),
        "dst_adjustment": False,
        "expected_hour_count": 24,
        "hour_identity": "[D HH:00:00Z, D HH+1:00:00Z)",
        "interval_definition_sha256": liquidation_interval_completeness_contract()[
            "definition_sha256"
        ],
        "resolver_definition_sha256": scientific_evidence_resolver_contract()[
            "definition_sha256"
        ],
        "surface_digest_is_authority": False,
        "schema_version": LIQUIDATION_DAY_CENSUS_VERSION,
        "version": LIQUIDATION_DAY_CENSUS_VERSION,
    }
    payload["definition_sha256"] = digest(payload)
    return payload
