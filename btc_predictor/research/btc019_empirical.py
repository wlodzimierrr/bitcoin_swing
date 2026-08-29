"""Real-data collection and artifact helpers for BTC-019 empirical research."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
from decimal import ROUND_CEILING, Decimal
from pathlib import Path
from statistics import median
from time import monotonic, sleep
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus
from urllib.request import Request, urlopen

from sqlalchemy import create_engine, func, select

from btc_predictor.data import (
    BITFINEX_BTC_USD_SYMBOL,
    BITFINEX_EXCHANGE,
    BITFINEX_PROVIDER_ID,
    BITSTAMP_BTC_USD_SYMBOL,
    BITSTAMP_EXCHANGE,
    BITSTAMP_PROVIDER_ID,
    COINBASE_BTC_USD_SYMBOL,
    COINBASE_EXCHANGE,
    COINBASE_PROVIDER_ID,
    BitfinexOhlcvProvider,
    BitstampOhlcvProvider,
    CoinbaseOhlcvProvider,
    OhlcvBar,
    build_canonical_market_bars,
    build_btc_ohlcv_insert_ignore,
    expected_bar_timestamps,
    require_utc_datetime,
)
from btc_predictor.db.raw import btc_ohlcv
from btc_predictor.levels import (
    BREAKOUT_LEVEL_TYPE,
    RECLAIM_LEVEL_TYPE,
    WEEKLY_SWING_HIGH,
    WEEKLY_SWING_LOW,
    detect_breakout_reclaim_levels,
    detect_weekly_swing_levels,
)
from btc_predictor.research.price_source_policy import (
    BITFINEX_PROVIDER_ID as POLICY_BITFINEX_PROVIDER_ID,
    BITSTAMP_PROVIDER_ID as POLICY_BITSTAMP_PROVIDER_ID,
    COINBASE_PROVIDER_ID as POLICY_COINBASE_PROVIDER_ID,
    CanonicalSourceDecision,
    DEFAULT_PRICE_SOURCE_POLICY,
    PRICE_SOURCE_POLICY_VERSION,
    PriceSourceDivergenceReview,
    PriceSourceOhlcvSnapshot,
    ProviderAccessDiagnostic,
    TradePathProbe,
    compare_price_sources,
)


RAW_ARTIFACT_SCHEMA_VERSION = "BTC019_RAW_OHLCV_V1"
COLLECTION_MANIFEST_SCHEMA_VERSION = "BTC019_COLLECTION_MANIFEST_V1"
EMPIRICAL_REPORT_SCHEMA_VERSION = "BTC019_EMPIRICAL_REPORT_V1"
MANUAL_REVIEW_SCHEMA_VERSION = "BTC019_MANUAL_REVIEWS_V1"
CANONICAL_DECISION_SCHEMA_VERSION = "BTC019_CANONICAL_DECISION_V1"
DEFAULT_EMPIRICAL_START = datetime(2023, 1, 1, tzinfo=UTC)
DEFAULT_EMPIRICAL_END = datetime(2025, 12, 31, 23, tzinfo=UTC)
DEFAULT_TRADE_PATH_DAYS = 28
DEFAULT_TRADE_PROBE_INTERVAL_DAYS = 7
MATERIAL_PATH_DIFFERENCE = Decimal("0.01")


@dataclass(frozen=True)
class ProviderCollectionSpec:
    provider_id: str
    exchange: str
    symbol: str
    minimum_request_interval_seconds: float


@dataclass(frozen=True)
class ProviderCollectionEvidence:
    provider: str
    instrument: str
    exchange: str
    first_timestamp: str | None
    last_timestamp: str | None
    expected_hourly_windows: int
    observed_bars: int
    missing_bar_count: int
    missing_bar_rate: str
    duplicate_bar_count: int
    conflicting_duplicate_count: int
    gap_count: int
    longest_gap_hours: int
    timestamp_alignment_anomalies: int
    collection_api_errors: tuple[dict[str, Any], ...]
    provider_outages_identified: int
    gap_classification: str
    api_request_count: int
    collection_started_at: str
    collection_completed_at: str
    raw_artifact_path: str
    raw_artifact_sha256: str
    raw_artifact_size_bytes: int
    database_records_inserted: int
    database_records_present: int


PROVIDER_SPECS = (
    ProviderCollectionSpec(
        provider_id=BITSTAMP_PROVIDER_ID,
        exchange=BITSTAMP_EXCHANGE,
        symbol=BITSTAMP_BTC_USD_SYMBOL,
        minimum_request_interval_seconds=0.05,
    ),
    ProviderCollectionSpec(
        provider_id=COINBASE_PROVIDER_ID,
        exchange=COINBASE_EXCHANGE,
        symbol=COINBASE_BTC_USD_SYMBOL,
        minimum_request_interval_seconds=0.15,
    ),
    ProviderCollectionSpec(
        provider_id=BITFINEX_PROVIDER_ID,
        exchange=BITFINEX_EXCHANGE,
        symbol=BITFINEX_BTC_USD_SYMBOL,
        minimum_request_interval_seconds=2.05,
    ),
)


class AuditedJsonRequester:
    """Rate-limited public JSON requester with bounded transient retries."""

    def __init__(
        self,
        *,
        minimum_interval_seconds: float,
        max_attempts: int = 5,
    ) -> None:
        self.minimum_interval_seconds = minimum_interval_seconds
        self.max_attempts = max_attempts
        self.request_count = 0
        self.errors: list[dict[str, Any]] = []
        self._last_request_started_at: float | None = None

    def __call__(self, url: str) -> Any:
        for attempt in range(1, self.max_attempts + 1):
            self._wait_for_rate_limit()
            self.request_count += 1
            self._last_request_started_at = monotonic()
            try:
                request = Request(
                    url,
                    headers={
                        "Accept": "application/json",
                        "User-Agent": "btc-predictor/1.0",
                    },
                )
                with urlopen(request, timeout=45) as response:
                    return json.load(response)
            except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
                error = {
                    "attempt": attempt,
                    "error_type": type(exc).__name__,
                    "message": str(exc),
                    "url": url,
                    "recorded_at": datetime.now(UTC).isoformat(),
                }
                self.errors.append(error)
                if attempt >= self.max_attempts or not _is_transient_error(exc):
                    raise
                sleep(min(30.0, float(2 ** (attempt - 1))))
        raise RuntimeError("request retry loop ended unexpectedly")

    def _wait_for_rate_limit(self) -> None:
        if self._last_request_started_at is None:
            return
        remaining = self.minimum_interval_seconds - (
            monotonic() - self._last_request_started_at
        )
        if remaining > 0:
            sleep(remaining)


def collect_real_histories(
    output_dir: Path,
    *,
    start: datetime = DEFAULT_EMPIRICAL_START,
    end: datetime = DEFAULT_EMPIRICAL_END,
    database_url: str | None = None,
) -> dict[str, Any]:
    """Collect and write immutable required-provider raw BTC-019 histories."""

    window_start = require_utc_datetime(start, "start")
    window_end = require_utc_datetime(end, "end")
    if window_end < window_start:
        raise ValueError("end must be >= start")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "collection_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(f"collection manifest already exists: {manifest_path}")

    policy_by_provider = {
        instrument.provider_id: instrument
        for instrument in DEFAULT_PRICE_SOURCE_POLICY.instruments
    }
    evidence = []
    for spec in PROVIDER_SPECS:
        requester = AuditedJsonRequester(
            minimum_interval_seconds=spec.minimum_request_interval_seconds,
        )
        provider = _provider_for(spec.provider_id, requester)
        collection_started_at = datetime.now(UTC)
        rows = provider.fetch_ohlcv(
            exchange=spec.exchange,
            symbol=spec.symbol,
            timeframe="1h",
            start=window_start,
            end=window_end,
        )
        collection_completed_at = datetime.now(UTC)
        bars = tuple(
            OhlcvBar(
                timestamp=row["timestamp"],
                exchange=spec.exchange,
                symbol=spec.symbol,
                timeframe="1h",
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                provider=spec.provider_id,
                ingested_at=collection_completed_at,
            )
            for row in rows
        )
        raw_path = output_dir / f"{spec.provider_id}_btc_usd_1h.jsonl.gz"
        _write_raw_artifact(
            raw_path,
            bars,
            roles=policy_by_provider[spec.provider_id].roles,
        )
        database_records_inserted, database_records_present = (
            _persist_raw_bars(database_url, bars)
            if database_url is not None
            else (0, 0)
        )
        evidence.append(
            _collection_evidence(
                spec,
                bars,
                start=window_start,
                end=window_end,
                requester=requester,
                collection_started_at=collection_started_at,
                collection_completed_at=collection_completed_at,
                raw_path=raw_path,
                database_records_inserted=database_records_inserted,
                database_records_present=database_records_present,
            ),
        )

    manifest = {
        "schema_version": COLLECTION_MANIFEST_SCHEMA_VERSION,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "historical_period_start": window_start.isoformat(),
        "historical_period_end": window_end.isoformat(),
        "required_provider_ids": [spec.provider_id for spec in PROVIDER_SPECS],
        "persistence_mode": "immutable_gzip_jsonl",
        "database_persistence": {
            "status": "persisted" if database_url is not None else "not_requested",
            "table": "raw.btc_ohlcv" if database_url is not None else None,
        },
        "providers": [asdict(item) for item in evidence],
        "completed_at": datetime.now(UTC).isoformat(),
    }
    _write_json_exclusive(manifest_path, manifest)
    return manifest


def load_raw_history(path: Path) -> tuple[OhlcvBar, ...]:
    bars = []
    with gzip.open(path, "rt", encoding="utf-8") as artifact:
        for line in artifact:
            record = json.loads(line)
            if record["schema_version"] != RAW_ARTIFACT_SCHEMA_VERSION:
                raise ValueError("unsupported BTC-019 raw artifact schema")
            if record["price_source_policy_version"] != PRICE_SOURCE_POLICY_VERSION:
                raise ValueError("raw artifact price-source policy version mismatch")
            bars.append(
                OhlcvBar(
                    timestamp=datetime.fromisoformat(record["timestamp"]),
                    exchange=record["exchange"],
                    symbol=record["symbol"],
                    timeframe=record["timeframe"],
                    open=Decimal(record["open"]),
                    high=Decimal(record["high"]),
                    low=Decimal(record["low"]),
                    close=Decimal(record["close"]),
                    volume=Decimal(record["volume"]),
                    provider=record["provider"],
                    ingested_at=datetime.fromisoformat(record["ingested_at"]),
                ),
            )
    return tuple(bars)


def build_weekly_trade_path_probes(
    baseline_bars: tuple[OhlcvBar, ...],
    *,
    start: datetime,
    end: datetime,
    path_days: int = DEFAULT_TRADE_PATH_DAYS,
    probe_interval_days: int = DEFAULT_TRADE_PROBE_INTERVAL_DAYS,
) -> tuple[TradePathProbe, ...]:
    """Build deterministic long probes with stops based only on prior bars."""

    window_start = require_utc_datetime(start, "start")
    window_end = require_utc_datetime(end, "end")
    if path_days < 1 or probe_interval_days < 1:
        raise ValueError("trade probe windows must be positive")
    ordered = tuple(sorted(baseline_bars, key=lambda bar: bar.timestamp))
    by_timestamp = {bar.timestamp: bar for bar in ordered}
    history_window = timedelta(days=path_days)
    exit_offset = history_window - timedelta(hours=1)
    entry_time = window_start + history_window
    probes = []
    while entry_time + exit_offset <= window_end:
        entry_bar = by_timestamp.get(entry_time)
        prior_lows = [
            bar.low
            for bar in ordered
            if entry_time - history_window <= bar.timestamp < entry_time
        ]
        if entry_bar is not None and prior_lows:
            probes.append(
                TradePathProbe(
                    entry_time=entry_time,
                    exit_time=entry_time + exit_offset,
                    entry_price=entry_bar.close,
                    direction="long",
                    stop_level=min(prior_lows),
                ),
            )
        entry_time += timedelta(days=probe_interval_days)
    return tuple(probes)


def run_empirical_validation(
    raw_dir: Path,
    output_dir: Path,
    *,
    review_assessments_path: Path,
) -> dict[str, Any]:
    """Create the decision-ready BTC-019 report from immutable raw histories."""

    manifest = _read_json(raw_dir / "collection_manifest.json")
    _validate_collection_manifest(raw_dir, manifest)
    provider_bars = {
        provider_id: load_raw_history(
            raw_dir / f"{provider_id}_btc_usd_1h.jsonl.gz",
        )
        for provider_id in (
            POLICY_BITSTAMP_PROVIDER_ID,
            POLICY_COINBASE_PROVIDER_ID,
            POLICY_BITFINEX_PROVIDER_ID,
        )
    }
    start = _parse_utc(manifest["historical_period_start"])
    end = _parse_utc(manifest["historical_period_end"])
    as_of = max(
        bar.ingested_at for bars in provider_bars.values() for bar in bars
    )
    probes = build_weekly_trade_path_probes(
        provider_bars[POLICY_BITSTAMP_PROVIDER_ID],
        start=start,
        end=end,
    )
    access_diagnostics = (
        ProviderAccessDiagnostic(
            provider_id="coin_metrics_community",
            status="entitlement_unavailable",
            checked_at=as_of,
            details=(
                "Historical pair-candle retrieval is unavailable without an "
                "entitled credential; the optional benchmark was not substituted."
            ),
            catalog_coverage_advertised=True,
            historical_retrieval_entitled=False,
        ),
    )
    preliminary = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        trade_path_probes=probes,
        provider_access_diagnostics=access_diagnostics,
        top_event_count=25,
    )
    assessments = _read_json(review_assessments_path)
    reviewed_at = _parse_utc(assessments["reviewed_at"])
    reviews = tuple(
        _build_price_event_review(
            event,
            provider_bars=provider_bars,
            as_of=as_of,
            assessment=_timestamp_assessment(assessments, event.timestamp),
            reviewed_at=reviewed_at,
        )
        for event in preliminary.top_divergence_events
    )
    decision_input = assessments["decision"]
    decision = CanonicalSourceDecision(
        policy_version=PRICE_SOURCE_POLICY_VERSION,
        provider_id=POLICY_BITSTAMP_PROVIDER_ID,
        status=decision_input["status"].lower(),
        decided_at=_parse_utc(decision_input["decided_at"]),
        reviewer=assessments["reviewer"],
        rationale=decision_input["rationale"],
    )
    report = compare_price_sources(
        provider_bars,
        start=start,
        end=end,
        as_of=as_of,
        trade_path_probes=probes,
        manual_reviews=reviews,
        provider_access_diagnostics=access_diagnostics,
        canonical_source_decision=decision,
        top_event_count=25,
    )
    if not report.policy_decision_ready:
        raise ValueError(
            f"BTC-019 report is not decision-ready: {report.reason_codes}",
        )

    price_distributions = _price_divergence_evidence(provider_bars)
    structural = _structural_sensitivity(
        provider_bars,
        as_of=as_of,
        assessments=assessments,
    )
    trade_paths = _trade_path_sensitivity(
        provider_bars,
        probes=probes,
        assessments=assessments,
    )
    top_wick_reviews = _top_wick_reviews(
        report,
        provider_bars=provider_bars,
        assessments=assessments,
    )
    required_price_reviews = _enriched_price_reviews(
        report,
        provider_bars=provider_bars,
        assessments=assessments,
    )
    tier_counts = {
        str(summary.tier): summary.event_count for summary in report.divergence_tiers
    }
    decision_artifact = {
        "schema_version": CANONICAL_DECISION_SCHEMA_VERSION,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "candidate_provider": POLICY_BITSTAMP_PROVIDER_ID,
        "candidate_status": decision.status.upper(),
        "decision": decision.status.upper(),
        "decision_timestamp": decision.decided_at.isoformat(),
        "reviewer": decision.reviewer,
        "historical_period_start": start.isoformat(),
        "historical_period_end": end.isoformat(),
        "common_bar_count": report.overlap_bar_count,
        "missing_bar_rates": {
            profile.provider_id: str(profile.missing_bar_rate)
            for profile in report.series_profiles
        },
        "tier_event_counts": tier_counts,
        "swing_disagreement_rate": structural["combined_swing"][
            "pairwise_disagreement_rate"
        ],
        "breakout_disagreement_rate": structural["breakout"][
            "pairwise_disagreement_rate"
        ],
        "reclaim_disagreement_rate": structural["reclaim"][
            "pairwise_disagreement_rate"
        ],
        "stop_touch_disagreement_rate": trade_paths[
            "pairwise_stop_disagreement_rate"
        ],
        "mfe_sensitivity_summary": trade_paths["mfe_summary"],
        "mae_sensitivity_summary": trade_paths["mae_summary"],
        "material_systematic_bias_detected": decision_input[
            "material_systematic_bias_detected"
        ],
        "isolated_wick_risk_acceptable": decision_input[
            "isolated_wick_risk_acceptable"
        ],
        "manual_review_count": (
            len(required_price_reviews)
            + len(top_wick_reviews)
            + len(structural["manual_event_reviews"])
            + len(trade_paths["material_event_reviews"])
        ),
        "decision_rationale": decision.rationale,
        "known_limitations": decision_input["known_limitations"],
        "follow_up_candidates": decision_input["follow_up_candidates"],
    }
    manual_review_artifact = {
        "schema_version": MANUAL_REVIEW_SCHEMA_VERSION,
        "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
        "reviewer": assessments["reviewer"],
        "reviewed_at": reviewed_at.isoformat(),
        "required_top_price_event_reviews": required_price_reviews,
        "top_atr_wick_reviews": top_wick_reviews,
        "structural_event_reviews": structural["manual_event_reviews"],
        "material_path_reviews": trade_paths["material_event_reviews"],
    }
    empirical_report = {
        "schema_version": EMPIRICAL_REPORT_SCHEMA_VERSION,
        "price_source_policy": DEFAULT_PRICE_SOURCE_POLICY.as_record(),
        "historical_period_start": start.isoformat(),
        "historical_period_end": end.isoformat(),
        "as_of": as_of.isoformat(),
        "collection": manifest,
        "gap_rechecks": assessments["gap_rechecks"],
        "price_distributions": price_distributions,
        "structural_sensitivity": structural,
        "trade_path_sensitivity": trade_paths,
        "comparison_report": report.as_record(),
        "decision": decision_artifact,
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    tracked_manifest = dict(manifest)
    tracked_manifest["gap_rechecks"] = assessments["gap_rechecks"]
    _write_json(output_dir / "collection_manifest.json", tracked_manifest)
    _write_json(output_dir / "comparison_report.json", report.as_record())
    _write_json(output_dir / "manual_reviews.json", manual_review_artifact)
    _write_json(
        output_dir / "canonical_source_decision.json",
        decision_artifact,
    )
    _write_json(
        output_dir / "supplemental_analysis.json",
        empirical_report,
    )
    report_markdown = _empirical_report_markdown(empirical_report)
    (output_dir / "empirical_validation_report.md").write_text(
        report_markdown,
        encoding="utf-8",
        newline="\n",
    )
    return empirical_report


def _build_price_event_review(
    event: Any,
    *,
    provider_bars: dict[str, tuple[OhlcvBar, ...]],
    as_of: datetime,
    assessment: dict[str, Any],
    reviewed_at: datetime,
) -> PriceSourceDivergenceReview:
    bars_by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in provider_bars.items()
    }
    synchronized = {
        provider_id: bars[event.timestamp]
        for provider_id, bars in bars_by_provider.items()
        if event.timestamp in bars
    }
    baseline_bar = synchronized[POLICY_BITSTAMP_PROVIDER_ID]
    validator_bar = synchronized[event.provider_id]
    median_high = Decimal(str(median([bar.high for bar in synchronized.values()])))
    median_low = Decimal(str(median([bar.low for bar in synchronized.values()])))
    median_close = Decimal(str(median([bar.close for bar in synchronized.values()])))
    median_by_metric = {
        "high": median_high,
        "low": median_low,
        "close": median_close,
    }
    atr_value = _baseline_atr_before(
        provider_bars[POLICY_BITSTAMP_PROVIDER_ID],
        timestamp=event.timestamp,
        as_of=as_of,
    )
    atr_divergence = (
        abs(getattr(validator_bar, event.metric) - median_by_metric[event.metric])
        / atr_value
        if atr_value is not None and atr_value > 0
        else None
    )
    return PriceSourceDivergenceReview(
        timestamp=event.timestamp,
        provider_id=event.provider_id,
        metric=event.metric,
        providers_involved=tuple(sorted(synchronized)),
        canonical_candidate_ohlc=PriceSourceOhlcvSnapshot.from_bar(baseline_bar),
        validator_ohlc=PriceSourceOhlcvSnapshot.from_bar(validator_bar),
        cross_provider_median_high=median_high,
        cross_provider_median_low=median_low,
        cross_provider_median_close=median_close,
        atr_normalized_divergence=atr_divergence,
        event_classification=assessment["event_classification"],
        swing_impact=assessment["swing_impact"],
        breakout_impact=assessment["breakout_impact"],
        reclaim_impact=assessment["reclaim_impact"],
        stop_touch_impact=assessment["stop_touch_impact"],
        mfe_impact=assessment["mfe_impact"],
        mae_impact=assessment["mae_impact"],
        trade_outcome_impact=assessment["trade_outcome_impact"],
        review_conclusion=assessment["review_conclusion"],
        review_notes=assessment["review_notes"],
        reviewed_at=reviewed_at,
    )


def _baseline_atr_before(
    baseline_bars: tuple[OhlcvBar, ...],
    *,
    timestamp: datetime,
    as_of: datetime,
    window_days: int = 14,
) -> Decimal | None:
    daily_bars = tuple(
        bar
        for bar in build_canonical_market_bars(
            baseline_bars,
            data_available_at=as_of,
            timeframes=("1d",),
        )
        if bar.timeframe == "1d"
    )
    true_ranges = []
    for previous, current in zip(daily_bars, daily_bars[1:]):
        true_ranges.append(
            (
                current.timestamp,
                max(
                    current.high - current.low,
                    abs(current.high - previous.close),
                    abs(current.low - previous.close),
                ),
            ),
        )
    atr_series = {
        current_timestamp: sum(
            (value for _, value in true_ranges[index - window_days + 1 : index + 1]),
            Decimal("0"),
        )
        / Decimal(window_days)
        for index, (current_timestamp, _) in enumerate(true_ranges)
        if index + 1 >= window_days
    }
    day_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
    available = [value for key, value in atr_series.items() if key < day_start]
    return available[-1] if available else None


def _price_divergence_evidence(
    provider_bars: dict[str, tuple[OhlcvBar, ...]],
) -> dict[str, Any]:
    by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in provider_bars.items()
    }
    baseline = by_provider[POLICY_BITSTAMP_PROVIDER_ID]
    evidence = {}
    for metric in ("close", "high", "low"):
        absolute_usd = []
        absolute_fraction = []
        signed_by_validator = {}
        for provider_id in (POLICY_COINBASE_PROVIDER_ID, POLICY_BITFINEX_PROVIDER_ID):
            validator = by_provider[provider_id]
            common = sorted(set(baseline) & set(validator))
            signed_fraction = []
            for timestamp in common:
                base_value = getattr(baseline[timestamp], metric)
                validator_value = getattr(validator[timestamp], metric)
                absolute_usd.append(abs(validator_value - base_value))
                difference = (validator_value - base_value) / base_value
                absolute_fraction.append(abs(difference))
                signed_fraction.append(difference)
            signed_by_validator[provider_id] = {
                "observation_count": len(signed_fraction),
                "mean_signed_fraction": str(
                    sum(signed_fraction, Decimal("0"))
                    / Decimal(len(signed_fraction)),
                ),
                "median_signed_fraction": str(
                    Decimal(str(median(signed_fraction))),
                ),
                "positive_count": sum(value > 0 for value in signed_fraction),
                "negative_count": sum(value < 0 for value in signed_fraction),
                "zero_count": sum(value == 0 for value in signed_fraction),
            }
        evidence[metric] = {
            "absolute_usd": _distribution_record(absolute_usd),
            "absolute_fraction": _distribution_record(absolute_fraction),
            "signed_by_validator": signed_by_validator,
        }
    return evidence


def _structural_sensitivity(
    provider_bars: dict[str, tuple[OhlcvBar, ...]],
    *,
    as_of: datetime,
    assessments: dict[str, Any],
) -> dict[str, Any]:
    weekly = {
        provider_id: tuple(
            bar
            for bar in build_canonical_market_bars(
                bars,
                data_available_at=as_of,
                timeframes=("1w",),
            )
            if bar.timeframe == "1w"
        )
        for provider_id, bars in provider_bars.items()
    }
    swings = {
        provider_id: detect_weekly_swing_levels(bars, as_of=as_of)
        for provider_id, bars in weekly.items()
    }
    breakout_reclaim = {
        provider_id: detect_breakout_reclaim_levels(
            swings[provider_id],
            weekly[provider_id],
            as_of=as_of,
        )
        for provider_id in weekly
    }
    specs = {
        "swing_high": (swings, WEEKLY_SWING_HIGH, "level_timestamp"),
        "swing_low": (swings, WEEKLY_SWING_LOW, "level_timestamp"),
        "breakout": (
            breakout_reclaim,
            BREAKOUT_LEVEL_TYPE,
            "confirmation_timestamp",
        ),
        "reclaim": (
            breakout_reclaim,
            RECLAIM_LEVEL_TYPE,
            "confirmation_timestamp",
        ),
    }
    result: dict[str, Any] = {
        "weekly_bar_counts": {
            provider_id: len(bars) for provider_id, bars in weekly.items()
        },
    }
    manual_reviews = []
    for category, (collection, level_type, timestamp_field) in specs.items():
        levels = {
            provider_id: {
                getattr(level, timestamp_field): level
                for level in provider_levels
                if level.level_type == level_type
            }
            for provider_id, provider_levels in collection.items()
        }
        baseline = levels[POLICY_BITSTAMP_PROVIDER_ID]
        pairwise = {}
        pairwise_difference_count = 0
        pairwise_union_count = 0
        for provider_id in (
            POLICY_COINBASE_PROVIDER_ID,
            POLICY_BITFINEX_PROVIDER_ID,
        ):
            validator = levels[provider_id]
            only_baseline = sorted(set(baseline) - set(validator))
            only_validator = sorted(set(validator) - set(baseline))
            difference_count = len(only_baseline) + len(only_validator)
            union_count = len(set(baseline) | set(validator))
            pairwise_difference_count += difference_count
            pairwise_union_count += union_count
            pairwise[provider_id] = {
                "bitstamp_count": len(baseline),
                "validator_count": len(validator),
                "only_bitstamp": [timestamp.isoformat() for timestamp in only_baseline],
                "only_validator": [
                    timestamp.isoformat() for timestamp in only_validator
                ],
                "difference_count": difference_count,
                "union_count": union_count,
                "disagreement_rate": _ratio_record(difference_count, union_count),
            }
        union_timestamps = sorted(set().union(*(set(items) for items in levels.values())))
        disagreement_events = []
        for timestamp in union_timestamps:
            present = [
                provider_id
                for provider_id in (
                    POLICY_BITSTAMP_PROVIDER_ID,
                    POLICY_COINBASE_PROVIDER_ID,
                    POLICY_BITFINEX_PROVIDER_ID,
                )
                if timestamp in levels[provider_id]
            ]
            if len(present) == 3:
                continue
            key = f"{category}|{timestamp.isoformat()}"
            assessment = assessments["structural_reviews"].get(key)
            if assessment is None:
                raise ValueError(f"missing structural review assessment: {key}")
            event = {
                "category": category,
                "timestamp": timestamp.isoformat(),
                "providers_present": present,
                "prices": {
                    provider_id: str(levels[provider_id][timestamp].price)
                    for provider_id in present
                },
                "candidate_alone": present == [POLICY_BITSTAMP_PROVIDER_ID],
                "candidate_absent_validator_consensus": present
                == [POLICY_COINBASE_PROVIDER_ID, POLICY_BITFINEX_PROVIDER_ID],
                "assessment": assessment,
            }
            disagreement_events.append(event)
            manual_reviews.append(event)
        result[category] = {
            "pairwise_difference_count": pairwise_difference_count,
            "pairwise_union_count": pairwise_union_count,
            "pairwise_disagreement_rate": _ratio_record(
                pairwise_difference_count,
                pairwise_union_count,
            ),
            "candidate_alone_count": sum(
                event["candidate_alone"] for event in disagreement_events
            ),
            "candidate_absent_validator_consensus_count": sum(
                event["candidate_absent_validator_consensus"]
                for event in disagreement_events
            ),
            "pairwise": pairwise,
            "disagreement_events": disagreement_events,
        }
    swing_differences = (
        result["swing_high"]["pairwise_difference_count"]
        + result["swing_low"]["pairwise_difference_count"]
    )
    swing_union = (
        result["swing_high"]["pairwise_union_count"]
        + result["swing_low"]["pairwise_union_count"]
    )
    result["combined_swing"] = {
        "pairwise_difference_count": swing_differences,
        "pairwise_union_count": swing_union,
        "pairwise_disagreement_rate": _ratio_record(swing_differences, swing_union),
    }
    result["manual_event_reviews"] = manual_reviews
    return result


def _trade_path_sensitivity(
    provider_bars: dict[str, tuple[OhlcvBar, ...]],
    *,
    probes: tuple[TradePathProbe, ...],
    assessments: dict[str, Any],
) -> dict[str, Any]:
    comparisons = []
    mfe_differences = []
    mae_differences = []
    for probe_index, probe in enumerate(probes):
        baseline = _path_metrics(
            provider_bars[POLICY_BITSTAMP_PROVIDER_ID],
            probe,
        )
        if baseline is None:
            continue
        for provider_id in (
            POLICY_COINBASE_PROVIDER_ID,
            POLICY_BITFINEX_PROVIDER_ID,
        ):
            validator = _path_metrics(provider_bars[provider_id], probe)
            if validator is None:
                continue
            mfe_difference = abs(validator["mfe"] - baseline["mfe"])
            mae_difference = abs(validator["mae"] - baseline["mae"])
            mfe_differences.append(mfe_difference)
            mae_differences.append(mae_difference)
            stop_disagreement = validator["stop_touched"] != baseline["stop_touched"]
            material = (
                max(mfe_difference, mae_difference) >= MATERIAL_PATH_DIFFERENCE
                or stop_disagreement
            )
            record = {
                "probe_index": probe_index,
                "entry_time": probe.entry_time.isoformat(),
                "exit_time": probe.exit_time.isoformat(),
                "entry_price": str(probe.entry_price),
                "stop_level": str(probe.stop_level),
                "validator_provider": provider_id,
                "bitstamp": _path_metric_record(baseline),
                "validator": _path_metric_record(validator),
                "mfe_difference_fraction": str(mfe_difference),
                "mae_difference_fraction": str(mae_difference),
                "stop_touch_disagreement": stop_disagreement,
                "material": material,
            }
            if material:
                key = f"{probe_index}|{provider_id}"
                assessment = assessments["path_reviews"].get(key)
                if assessment is None:
                    raise ValueError(f"missing path review assessment: {key}")
                record["assessment"] = assessment
            comparisons.append(record)
    stop_disagreements = [
        item for item in comparisons if item["stop_touch_disagreement"]
    ]
    unique_stop_probes = {item["probe_index"] for item in stop_disagreements}
    material_reviews = [item for item in comparisons if item["material"]]
    pairwise_count = len(comparisons)
    mfe_distribution = _distribution_record(mfe_differences)
    mae_distribution = _distribution_record(mae_differences)
    return {
        "probe_count": len(probes),
        "pairwise_comparison_count": pairwise_count,
        "probe_definition": {
            "direction": "long",
            "entry_interval_days": DEFAULT_TRADE_PROBE_INTERVAL_DAYS,
            "path_days": DEFAULT_TRADE_PATH_DAYS,
            "stop_rule": "minimum Bitstamp low from the 28 days before entry",
            "point_in_time": True,
        },
        "material_path_difference_fraction": str(MATERIAL_PATH_DIFFERENCE),
        "mfe_distribution": mfe_distribution,
        "mae_distribution": mae_distribution,
        "mfe_summary": {
            **mfe_distribution,
            "material_pairwise_count": sum(
                Decimal(item["mfe_difference_fraction"])
                >= MATERIAL_PATH_DIFFERENCE
                for item in comparisons
            ),
        },
        "mae_summary": {
            **mae_distribution,
            "material_pairwise_count": sum(
                Decimal(item["mae_difference_fraction"])
                >= MATERIAL_PATH_DIFFERENCE
                for item in comparisons
            ),
        },
        "material_pairwise_path_count": len(material_reviews),
        "material_pairwise_path_rate": _ratio_record(
            len(material_reviews),
            pairwise_count,
        ),
        "pairwise_stop_disagreement_count": len(stop_disagreements),
        "pairwise_stop_disagreement_rate": _ratio_record(
            len(stop_disagreements),
            pairwise_count,
        ),
        "unique_probe_stop_disagreement_count": len(unique_stop_probes),
        "unique_probe_stop_disagreement_rate": _ratio_record(
            len(unique_stop_probes),
            len(probes),
        ),
        "bitstamp_hit_validator_did_not_count": sum(
            item["bitstamp"]["stop_touched"]
            and not item["validator"]["stop_touched"]
            for item in stop_disagreements
        ),
        "validator_hit_bitstamp_did_not_count": sum(
            item["validator"]["stop_touched"]
            and not item["bitstamp"]["stop_touched"]
            for item in stop_disagreements
        ),
        "bitstamp_alone_hit_stop_probe_count": _bitstamp_alone_stop_count(
            comparisons,
        ),
        "validators_consensus_hit_bitstamp_missed_probe_count": (
            _validator_consensus_stop_count(comparisons)
        ),
        "stop_disagreements": stop_disagreements,
        "material_event_reviews": material_reviews,
        "all_pairwise_comparisons": comparisons,
    }


def _path_metrics(
    bars: tuple[OhlcvBar, ...],
    probe: TradePathProbe,
) -> dict[str, Any] | None:
    path = [
        bar
        for bar in bars
        if probe.entry_time <= bar.timestamp <= probe.exit_time
    ]
    if not path:
        return None
    max_high = max(bar.high for bar in path)
    min_low = min(bar.low for bar in path)
    high_bar = next(bar for bar in path if bar.high == max_high)
    low_bar = next(bar for bar in path if bar.low == min_low)
    if probe.direction == "long":
        mfe = (max_high - probe.entry_price) / probe.entry_price
        mae = (min_low - probe.entry_price) / probe.entry_price
        touched = any(bar.low <= probe.stop_level for bar in path)
        touch_bar = next(
            (bar for bar in path if bar.low <= probe.stop_level),
            None,
        )
    else:
        mfe = (probe.entry_price - min_low) / probe.entry_price
        mae = (probe.entry_price - max_high) / probe.entry_price
        touched = any(bar.high >= probe.stop_level for bar in path)
        touch_bar = next(
            (bar for bar in path if bar.high >= probe.stop_level),
            None,
        )
    return {
        "mfe": mfe,
        "mae": mae,
        "max_high": max_high,
        "max_high_timestamp": high_bar.timestamp,
        "min_low": min_low,
        "min_low_timestamp": low_bar.timestamp,
        "stop_touched": touched,
        "first_stop_touch_timestamp": touch_bar.timestamp if touch_bar else None,
    }


def _path_metric_record(metrics: dict[str, Any]) -> dict[str, Any]:
    return {
        key: (
            value.isoformat()
            if isinstance(value, datetime)
            else str(value)
            if isinstance(value, Decimal)
            else value
        )
        for key, value in metrics.items()
    }


def _bitstamp_alone_stop_count(comparisons: list[dict[str, Any]]) -> int:
    by_probe: dict[int, list[dict[str, Any]]] = {}
    for item in comparisons:
        by_probe.setdefault(item["probe_index"], []).append(item)
    return sum(
        items[0]["bitstamp"]["stop_touched"]
        and all(not item["validator"]["stop_touched"] for item in items)
        for items in by_probe.values()
    )


def _validator_consensus_stop_count(comparisons: list[dict[str, Any]]) -> int:
    by_probe: dict[int, list[dict[str, Any]]] = {}
    for item in comparisons:
        by_probe.setdefault(item["probe_index"], []).append(item)
    return sum(
        not items[0]["bitstamp"]["stop_touched"]
        and all(item["validator"]["stop_touched"] for item in items)
        for items in by_probe.values()
    )


def _top_wick_reviews(
    report: Any,
    *,
    provider_bars: dict[str, tuple[OhlcvBar, ...]],
    assessments: dict[str, Any],
) -> list[dict[str, Any]]:
    bars_by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in provider_bars.items()
    }
    reviews = []
    for rank, diagnostic in enumerate(report.cross_venue_wick_diagnostics, 1):
        assessment = _timestamp_assessment(assessments, diagnostic.timestamp)
        reviews.append(
            {
                "rank": rank,
                **diagnostic.as_record(),
                "divergence_tier": 1,
                "all_provider_ohlc": {
                    provider_id: _ohlc_record(bars[diagnostic.timestamp])
                    for provider_id, bars in bars_by_provider.items()
                    if diagnostic.timestamp in bars
                },
                "manual_assessment": assessment,
            },
        )
    return reviews


def _enriched_price_reviews(
    report: Any,
    *,
    provider_bars: dict[str, tuple[OhlcvBar, ...]],
    assessments: dict[str, Any],
) -> list[dict[str, Any]]:
    bars_by_provider = {
        provider_id: {bar.timestamp: bar for bar in bars}
        for provider_id, bars in provider_bars.items()
    }
    reviews = []
    for rank, (event, review) in enumerate(
        zip(report.top_divergence_events, report.manual_reviews),
        1,
    ):
        reviews.append(
            {
                "rank": rank,
                "divergence_tier": _event_divergence_tier(
                    _timestamp_assessment(assessments, event.timestamp),
                ),
                "event": event.as_record(),
                "core_review": review.as_record(),
                "all_provider_ohlc": {
                    provider_id: _ohlc_record(bars[event.timestamp])
                    for provider_id, bars in bars_by_provider.items()
                    if event.timestamp in bars
                },
            },
        )
    return reviews


def _event_divergence_tier(assessment: dict[str, Any]) -> int:
    if assessment["trade_outcome_impact"] or assessment["stop_touch_impact"]:
        return 4
    if assessment["mfe_impact"] or assessment["mae_impact"]:
        return 4
    if (
        assessment["swing_impact"]
        or assessment["breakout_impact"]
        or assessment["reclaim_impact"]
    ):
        return 3
    return 1


def _ohlc_record(bar: OhlcvBar) -> dict[str, str]:
    return {
        "provider": bar.provider,
        "exchange": bar.exchange,
        "symbol": bar.symbol,
        "open": str(bar.open),
        "high": str(bar.high),
        "low": str(bar.low),
        "close": str(bar.close),
    }


def _timestamp_assessment(
    assessments: dict[str, Any],
    timestamp: datetime,
) -> dict[str, Any]:
    key = timestamp.isoformat()
    assessment = assessments["timestamp_reviews"].get(key)
    if assessment is None:
        raise ValueError(f"missing timestamp review assessment: {key}")
    return {**assessments["default_timestamp_assessment"], **assessment}


def _distribution_record(values: list[Decimal]) -> dict[str, Any]:
    ordered = sorted(abs(value) for value in values)
    if not ordered:
        return {
            key: 0 if key == "observation_count" else None
            for key in (
                "observation_count",
                "mean_abs",
                "median_abs",
                "standard_deviation_abs",
                "p90_abs",
                "p95_abs",
                "p99_abs",
                "p995_abs",
                "max_abs",
            )
        }
    mean_value = sum(ordered, Decimal("0")) / Decimal(len(ordered))
    variance = sum(
        ((value - mean_value) ** 2 for value in ordered),
        Decimal("0"),
    ) / Decimal(len(ordered))
    return {
        "observation_count": len(ordered),
        "mean_abs": str(mean_value),
        "median_abs": str(Decimal(str(median(ordered)))),
        "standard_deviation_abs": str(variance.sqrt()),
        "p90_abs": str(_percentile(ordered, Decimal("0.90"))),
        "p95_abs": str(_percentile(ordered, Decimal("0.95"))),
        "p99_abs": str(_percentile(ordered, Decimal("0.99"))),
        "p995_abs": str(_percentile(ordered, Decimal("0.995"))),
        "max_abs": str(ordered[-1]),
    }


def _percentile(ordered: list[Decimal], probability: Decimal) -> Decimal:
    rank = int(
        (probability * Decimal(len(ordered))).to_integral_value(
            rounding=ROUND_CEILING,
        ),
    )
    return ordered[max(0, rank - 1)]


def _ratio_record(numerator: int, denominator: int) -> str:
    return str(
        Decimal(numerator) / Decimal(denominator)
        if denominator
        else Decimal("0")
    )


def _validate_collection_manifest(raw_dir: Path, manifest: dict[str, Any]) -> None:
    if manifest["schema_version"] != COLLECTION_MANIFEST_SCHEMA_VERSION:
        raise ValueError("unsupported BTC-019 collection manifest schema")
    if manifest["price_source_policy_version"] != PRICE_SOURCE_POLICY_VERSION:
        raise ValueError("collection manifest price-source policy mismatch")
    expected_ids = {
        POLICY_BITSTAMP_PROVIDER_ID,
        POLICY_COINBASE_PROVIDER_ID,
        POLICY_BITFINEX_PROVIDER_ID,
    }
    providers = {item["provider"]: item for item in manifest["providers"]}
    if set(providers) != expected_ids:
        raise ValueError("collection manifest must contain all required providers")
    for provider_id, item in providers.items():
        artifact = raw_dir / f"{provider_id}_btc_usd_1h.jsonl.gz"
        if _sha256(artifact) != item["raw_artifact_sha256"]:
            raise ValueError(f"raw artifact hash mismatch: {provider_id}")


def _read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as artifact:
        value = json.load(artifact)
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _empirical_report_markdown(report: dict[str, Any]) -> str:
    comparison = report["comparison_report"]
    structural = report["structural_sensitivity"]
    trade = report["trade_path_sensitivity"]
    decision = report["decision"]
    profiles = {item["provider_id"]: item for item in comparison["series_profiles"]}
    return f"""# BTC-019 Empirical Price-Source Validation

Policy: `{PRICE_SOURCE_POLICY_VERSION}`

Decision: **{decision['decision']} Bitstamp as the V1 canonical reference source**

## Scope

- Historical period: `{report['historical_period_start']}` through `{report['historical_period_end']}`
- Synchronized common bars: `{comparison['overlap_bar_count']}`
- Bitstamp missing rate: `{profiles['bitstamp']['missing_bar_rate']}`
- Coinbase missing rate: `{profiles['coinbase']['missing_bar_rate']}`
- Bitfinex missing rate: `{profiles['bitfinex']['missing_bar_rate']}`

## Strategy Sensitivity

- Swing pairwise disagreement: `{structural['combined_swing']['pairwise_difference_count']}/{structural['combined_swing']['pairwise_union_count']}` (`{structural['combined_swing']['pairwise_disagreement_rate']}`)
- Breakout pairwise disagreement: `{structural['breakout']['pairwise_difference_count']}/{structural['breakout']['pairwise_union_count']}` (`{structural['breakout']['pairwise_disagreement_rate']}`)
- Reclaim pairwise disagreement: `{structural['reclaim']['pairwise_difference_count']}/{structural['reclaim']['pairwise_union_count']}` (`{structural['reclaim']['pairwise_disagreement_rate']}`)
- Stop-touch pairwise disagreement: `{trade['pairwise_stop_disagreement_count']}/{trade['pairwise_comparison_count']}` (`{trade['pairwise_stop_disagreement_rate']}`)
- Validator-consensus stop hits missed by Bitstamp: `{trade['validators_consensus_hit_bitstamp_missed_probe_count']}`
- Maximum MFE difference: `{trade['mfe_distribution']['max_abs']}`
- Maximum MAE difference: `{trade['mae_distribution']['max_abs']}`

## Decision

{decision['decision_rationale']}

## Limitations

{decision['known_limitations']}
"""


def _provider_for(provider_id: str, requester: AuditedJsonRequester):
    if provider_id == BITSTAMP_PROVIDER_ID:
        return BitstampOhlcvProvider(request_json=requester)
    if provider_id == COINBASE_PROVIDER_ID:
        return CoinbaseOhlcvProvider(request_json=requester)
    if provider_id == BITFINEX_PROVIDER_ID:
        return BitfinexOhlcvProvider(request_json=requester)
    raise ValueError(f"unsupported BTC-019 provider: {provider_id}")


def _write_raw_artifact(
    path: Path,
    bars: tuple[OhlcvBar, ...],
    *,
    roles: tuple[str, ...],
) -> None:
    if path.exists():
        raise FileExistsError(f"raw artifact already exists: {path}")
    with gzip.open(path, "xt", encoding="utf-8", newline="\n") as artifact:
        for bar in bars:
            record = {
                "schema_version": RAW_ARTIFACT_SCHEMA_VERSION,
                "price_source_policy_version": PRICE_SOURCE_POLICY_VERSION,
                "price_source_roles": list(roles),
                "fallback_used": False,
                **{
                    key: value.isoformat() if isinstance(value, datetime) else str(value)
                    for key, value in bar.as_record().items()
                },
            }
            artifact.write(json.dumps(record, sort_keys=True, separators=(",", ":")))
            artifact.write("\n")


def _collection_evidence(
    spec: ProviderCollectionSpec,
    bars: tuple[OhlcvBar, ...],
    *,
    start: datetime,
    end: datetime,
    requester: AuditedJsonRequester,
    collection_started_at: datetime,
    collection_completed_at: datetime,
    raw_path: Path,
    database_records_inserted: int,
    database_records_present: int,
) -> ProviderCollectionEvidence:
    expected = expected_bar_timestamps(start=start, end=end, timeframe="1h")
    observed = [bar.timestamp for bar in bars]
    observed_set = set(observed)
    missing = tuple(timestamp for timestamp in expected if timestamp not in observed_set)
    gap_lengths = _gap_lengths(missing)
    return ProviderCollectionEvidence(
        provider=spec.provider_id,
        instrument=spec.symbol,
        exchange=spec.exchange,
        first_timestamp=bars[0].timestamp.isoformat() if bars else None,
        last_timestamp=bars[-1].timestamp.isoformat() if bars else None,
        expected_hourly_windows=len(expected),
        observed_bars=len(bars),
        missing_bar_count=len(missing),
        missing_bar_rate=str(
            Decimal(len(missing)) / Decimal(len(expected)) if expected else Decimal("0"),
        ),
        duplicate_bar_count=len(observed) - len(observed_set),
        conflicting_duplicate_count=0,
        gap_count=len(gap_lengths),
        longest_gap_hours=max(gap_lengths, default=0),
        timestamp_alignment_anomalies=sum(
            bool(timestamp.minute or timestamp.second or timestamp.microsecond)
            for timestamp in observed
        ),
        collection_api_errors=tuple(requester.errors),
        provider_outages_identified=0,
        gap_classification="UNKNOWN" if missing else "NONE",
        api_request_count=requester.request_count,
        collection_started_at=collection_started_at.isoformat(),
        collection_completed_at=collection_completed_at.isoformat(),
        raw_artifact_path=str(raw_path),
        raw_artifact_sha256=_sha256(raw_path),
        raw_artifact_size_bytes=raw_path.stat().st_size,
        database_records_inserted=database_records_inserted,
        database_records_present=database_records_present,
    )


def _persist_raw_bars(
    database_url: str,
    bars: tuple[OhlcvBar, ...],
    *,
    batch_size: int = 1_000,
) -> tuple[int, int]:
    if not bars:
        return 0, 0
    engine = create_engine(database_url)
    try:
        with engine.begin() as connection:
            count_statement = (
                select(func.count())
                .select_from(btc_ohlcv)
                .where(
                    btc_ohlcv.c.provider == bars[0].provider,
                    btc_ohlcv.c.exchange == bars[0].exchange,
                    btc_ohlcv.c.symbol == bars[0].symbol,
                    btc_ohlcv.c.timeframe == bars[0].timeframe,
                    btc_ohlcv.c.timestamp >= bars[0].timestamp,
                    btc_ohlcv.c.timestamp <= bars[-1].timestamp,
                )
            )
            count_before = int(connection.execute(count_statement).scalar_one())
            for offset in range(0, len(bars), batch_size):
                connection.execute(
                    build_btc_ohlcv_insert_ignore(bars[offset : offset + batch_size]),
                )
            count_after = int(connection.execute(count_statement).scalar_one())
        return count_after - count_before, count_after
    finally:
        engine.dispose()


def _gap_lengths(missing: tuple[datetime, ...]) -> tuple[int, ...]:
    if not missing:
        return ()
    lengths = []
    current = 1
    for previous, timestamp in zip(missing, missing[1:]):
        if timestamp == previous + timedelta(hours=1):
            current += 1
        else:
            lengths.append(current)
            current = 1
    lengths.append(current)
    return tuple(lengths)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as artifact:
        for chunk in iter(lambda: artifact.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json_exclusive(path: Path, payload: dict[str, Any]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as artifact:
        json.dump(payload, artifact, indent=2, sort_keys=True)
        artifact.write("\n")


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as artifact:
        json.dump(payload, artifact, indent=2, sort_keys=True)
        artifact.write("\n")


def _is_transient_error(exc: Exception) -> bool:
    return not isinstance(exc, HTTPError) or exc.code == 429 or exc.code >= 500


def _parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return require_utc_datetime(parsed, "timestamp")


def _database_url_from_environment() -> str:
    required = (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
        "POSTGRES_DB",
    )
    missing = [name for name in required if not os.getenv(name)]
    if missing:
        raise ValueError(f"missing PostgreSQL environment variables: {missing}")
    return (
        f"postgresql+psycopg://{quote_plus(os.environ['POSTGRES_USER'])}:"
        f"{quote_plus(os.environ['POSTGRES_PASSWORD'])}@{os.environ['POSTGRES_HOST']}:"
        f"{os.environ['POSTGRES_PORT']}/{os.environ['POSTGRES_DB']}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("collect", "analyze"))
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path)
    parser.add_argument("--review-assessments", type=Path)
    parser.add_argument("--start", type=_parse_utc, default=DEFAULT_EMPIRICAL_START)
    parser.add_argument("--end", type=_parse_utc, default=DEFAULT_EMPIRICAL_END)
    parser.add_argument("--persist-database", action="store_true")
    args = parser.parse_args()
    if args.command == "collect":
        manifest = collect_real_histories(
            args.output_dir,
            start=args.start,
            end=args.end,
            database_url=(
                _database_url_from_environment() if args.persist_database else None
            ),
        )
        print(json.dumps(manifest, indent=2, sort_keys=True))
    elif args.command == "analyze":
        if args.raw_dir is None or args.review_assessments is None:
            parser.error("analyze requires --raw-dir and --review-assessments")
        report = run_empirical_validation(
            args.raw_dir,
            args.output_dir,
            review_assessments_path=args.review_assessments,
        )
        print(json.dumps(report["decision"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
