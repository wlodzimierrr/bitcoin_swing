"""Historical replay inputs extended to ``RESEARCH_BACKTEST_POLICY_V7`` (RBT-001A).

``HISTORICAL_REPLAY_AVAILABILITY_V2`` is policy V7 section 4: every input the
champion consumes has exactly one *record shape*, and its shape fixes when a
replay may see it. The reviewed RBT-001 builder (:mod:`replay_inputs`,
``HISTORICAL_REPLAY_AVAILABILITY_V1``) already replays the bar, ETF, funding,
open-interest and perpetual-volume families under rules that V7 keeps
unchanged; it refuses futures basis, liquidations and market cap, because V2
of the policy gave them no rule. This module is additive: it never changes the
V1 builder, its constants or its manifests. It takes a finished V1
:class:`SharedReplaySnapshot`, binds it by manifest digest, and adds the
families V3 introduced:

- futures basis at the hour close ``t``: ``SNAPSHOT``, available at ``t``
  (``FUTURES_BASIS_CONTRACT_V1``, policy section 4A), for the contracts a
  hash-bound listing evidence file shows listed at ``t``;
- liquidations, Kraken Futures ``PI_XBTUSD`` per-side ``1h`` aggregates stamped
  at the hour start ``h``: ``INTERVAL``, available at ``h + 1h``;
- BTC market cap for UTC day D: ``DAILY_PUBLISHED``, stamped ``D+1 00:00`` and
  available at ``D+2 00:00`` (RBT-002's pinned semantics);
- ``LIQUIDATION_PERCENTILE`` for day D: derived, available at ``D+1 00:00``;
- discretionary assertions: ``DISCRETIONARY``, never back-filled, not asserted
  (``None``).

The owner rulings of 2026-11-01 (RBT-001A block) fix three points the policy
left open:

1. This builder produces ``LIQUIDATION_PERCENTILE``. No executable owner
   computes it; EPIC X froze it as the contract
   ``PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1``, which is executed here by
   reference: its window, minimum and percentile convention are imported, and
   the convention runs through the volatility owner's own ``_percentile_rank``.
   A day enters only under ``HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1``: all
   24 hours observed. Day D is observed at ``D 00:00`` (the owner's bar-start
   convention, so the half-open window holds the 730 prior days) and available
   at ``D+1 00:00``.
2. A disagreement with Kraken's hourly liquidation-volume series refuses the
   build. The rule says the series "must agree within rounding".
3. Futures-basis rows within 7 days of expiry are excluded from the replay
   inputs and recorded in the manifest; every other breach of the contract is
   refused.

The owner's review rulings of 2026-11-03 add three more:

4. "Listed at t" comes from a hash-bound listing evidence file
   (``FUTURES_BASIS_CONTRACT_LISTING_EVIDENCE_V1``): each contract's symbol,
   the open time of its first ``1h`` kline and its delivery instant. No naming
   or calendar rule decides which contracts exist.
5. One basis row per contract and instant, whatever its provider.
6. The annualised rate is exactly the stored 18-place basis rate's
   annualisation; RBT-003 derives it from the persisted basis rate.

Evidence records (market cap, contract listings) are verified again against
their file digests when the builder admits them, and no result depends on the
caller's decimal context.

Inputs that RBT-002 found unsourceable (CVD and spot dominance, macro,
on-chain and liquidity) are refused, never approximated: the manifest names
each with its policy fallback, and an owner record of one is refused wherever
it is supplied.

Nothing here opens a database or network connection. Everything produced is
``RESEARCH_BACKTEST_NON_CERTIFYING`` evidence with the canonical reference
``UNRESOLVED``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime, time, timedelta
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Context, Decimal, DivisionByZero, InvalidOperation, Overflow, localcontext
from pathlib import Path
from typing import Any

from btc_predictor.data import FuturesBasis, Liquidation
from btc_predictor.features.flow import CvdObservation
from btc_predictor.features.positioning import MarketCapObservation
from btc_predictor.features.volatility import _percentile_rank
from btc_predictor.research import prospective_integration_corpus as epic_x
from btc_predictor.research import us_equity_market_closures as closures
from btc_predictor.research_backtest import coverage
from btc_predictor.research_backtest import replay_inputs as v1
from btc_predictor.research_backtest.entry_composer import (
    EntryComposerInputs,
    EtfFundLaunch,
    LiquidationPercentileObservation,
)


REPLAY_INPUTS_V2_BUILDER_VERSION = "EXTEND_REPLAY_INPUTS_TO_POLICY_V3"
RESEARCH_BACKTEST_POLICY_V7 = "RESEARCH_BACKTEST_POLICY_V7"
REPLAY_AVAILABILITY_POLICY_V2 = "HISTORICAL_REPLAY_AVAILABILITY_V2"
EXTENDED_SNAPSHOT_MANIFEST_VERSION = "HISTORICAL_REPLAY_SHARED_SNAPSHOT_MANIFEST_V2"

REPLAY_V2_REFUSAL_REASON_CODES = (
    *v1.REPLAY_REFUSAL_REASON_CODES,
    "FUTURES_BASIS_CONTRACT_REFUSED",
    "FUTURES_BASIS_CONTRACT_NOT_LISTED",
    "FUTURES_BASIS_LISTING_EVIDENCE_REFUSED",
    "MARKET_CAP_EVIDENCE_REFUSED",
    "LIQUIDATION_UNIVERSE_REFUSED",
    "LIQUIDATION_NOTIONAL_MISSING",
    "LIQUIDATION_HOUR_EVIDENCE_REFUSED",
    "LIQUIDATION_HOUR_EVIDENCE_MISSING",
    "LIQUIDATION_HOUR_STATUS_INCONSISTENT",
    "LIQUIDATION_CORROBORATION_DISAGREES",
    "LIQUIDATION_CORROBORATION_UNAVAILABLE",
    "CLOSURE_TABLE_REQUIRED",
    "UNSOURCEABLE_INPUT_REFUSED",
    "SHARED_SNAPSHOT_MISMATCH",
)


class ExtendedReplayInputRefused(v1.ReplayInputRefused):
    """An input cannot enter a V2 replay. The build fails; nothing is dropped.

    A subclass of the V1 refusal, so a caller that catches V1 refusals also
    catches these; the V1 class and its closed code set are unchanged.
    """

    def __init__(self, reason_code: str, message: str) -> None:
        if reason_code not in REPLAY_V2_REFUSAL_REASON_CODES:
            raise ValueError(f"undeclared replay refusal reason code: {reason_code}")
        ValueError.__init__(self, f"{reason_code}: {message}")
        self.reason_code = reason_code


# --- the policy V7 section 4 shape table --------------------------------------------

FUTURES_BASIS_FAMILY = "FUTURES_BASIS"
LIQUIDATIONS_FAMILY = "LIQUIDATIONS"
BTC_MARKET_CAP_FAMILY = "BTC_MARKET_CAP"
US_EQUITY_MARKET_CLOSURES_FAMILY = "US_EQUITY_MARKET_CLOSURES"
DISCRETIONARY_FAMILY = "DISCRETIONARY_ASSERTION"
LIQUIDATION_HOUR_EVIDENCE_FAMILY = "LIQUIDATION_HOUR_COMPLETENESS_EVIDENCE"
LIQUIDATION_PERCENTILE_INPUT = "LIQUIDATION_PERCENTILE"

# One shape per input family (policy V7 section 4 "current assignments").
REPLAY_SHAPES_V2: Mapping[str, str] = {
    v1.REFERENCE_PRICE_FAMILY: coverage.SHAPE_INTERVAL,
    v1.SHARED_VOLUME_FAMILY: coverage.SHAPE_INTERVAL,
    v1.ETF_FLOW_FAMILY: coverage.SHAPE_DAILY_PUBLISHED,
    v1.FUNDING_RATE_FAMILY: coverage.SHAPE_SETTLEMENT,
    v1.OPEN_INTEREST_FAMILY: coverage.SHAPE_SNAPSHOT,
    v1.PERP_VOLUME_FAMILY: coverage.SHAPE_INTERVAL,
    FUTURES_BASIS_FAMILY: coverage.SHAPE_SNAPSHOT,
    LIQUIDATIONS_FAMILY: coverage.SHAPE_INTERVAL,
    BTC_MARKET_CAP_FAMILY: coverage.SHAPE_DAILY_PUBLISHED,
    US_EQUITY_MARKET_CLOSURES_FAMILY: coverage.SHAPE_DAILY_PUBLISHED,
    DISCRETIONARY_FAMILY: coverage.SHAPE_DISCRETIONARY,
}

REPLAY_AVAILABILITY_RULES_V2: Mapping[str, v1.ReplayAvailabilityRule] = {
    FUTURES_BASIS_FAMILY: v1.ReplayAvailabilityRule(
        FUTURES_BASIS_FAMILY,
        owner_record="FuturesBasis",
        observation_convention="HOUR_CLOSE_SNAPSHOT",
        observation_convention_basis=(
            "FUTURES_BASIS_CONTRACT_V1 (policy V7 section 4A): futures 1h close / COIN-M "
            "BTCUSD index 1h close - 1 at the hour close t"
        ),
        modelled_availability="SNAPSHOT_INSTANT",
        availability_field="available_at",
        raw_time_fields=("available_at", "ingested_at"),
    ),
    LIQUIDATIONS_FAMILY: v1.ReplayAvailabilityRule(
        LIQUIDATIONS_FAMILY,
        owner_record="Liquidation",
        observation_convention="INTERVAL_START_1H",
        observation_convention_basis=(
            "RBT-002 pinned semantics: per-side 1h aggregates of Kraken Futures PI_XBTUSD "
            "Liquidation fills, stamped at the hour start"
        ),
        modelled_availability="INTERVAL_END",
        availability_field="available_at",
        raw_time_fields=("available_at", "ingested_at"),
    ),
    BTC_MARKET_CAP_FAMILY: v1.ReplayAvailabilityRule(
        BTC_MARKET_CAP_FAMILY,
        owner_record="MarketCapObservation",
        observation_convention="UTC_DAY_D_STAMPED_D_PLUS_1_0000",
        observation_convention_basis=(
            "RBT-002 pinned semantics: the end-of-day value of UTC day D is stamped "
            "D+1 00:00, where the OI-intensity owner joins it to open interest by "
            "exact instant"
        ),
        modelled_availability="D_PLUS_2_0000_UTC",
        availability_field="available_at",
        raw_time_fields=("evidence_retrieved_at",),
    ),
}

_HOUR = timedelta(hours=1)
_DAY = timedelta(days=1)
_ONE_MICROSECOND = timedelta(microseconds=1)
_SHA256 = re.compile(r"[0-9a-f]{64}")

# No result of this builder depends on the caller's decimal context (review F3).
# Every rate and notional it admits fits the raw tables' NUMERIC(38,18) (at most
# 20 integer and 18 fractional digits), so its sums and the contract's
# annualisation are exact or correctly rounded at 80 digits. The percentile runs
# the volatility owner's convention under the decimal module's documented default
# context (28 digits, half-even), the context the replay's owners and composers
# run under, stated here so that a caller's own context cannot change it.
_WIDE_CONTEXT = Context(
    prec=80, rounding=ROUND_HALF_EVEN, Emin=-999_999, Emax=999_999, capitals=1, clamp=0, flags=[], traps=[InvalidOperation, DivisionByZero, Overflow]
)
_OWNER_CONTEXT = Context(
    prec=28, rounding=ROUND_HALF_EVEN, Emin=-999_999, Emax=999_999, capitals=1, clamp=0, flags=[], traps=[InvalidOperation, DivisionByZero, Overflow]
)
# Both rates and the liquidation notional are persisted as NUMERIC(38,18), which
# rounds half away from zero.
RAW_NUMERIC_QUANTUM = Decimal("1e-18")
_RAW_NUMERIC_LIMIT = Decimal(10) ** 20


def _require_raw_numeric(record: Any, fields: Sequence[str], what: str) -> None:
    """Refuse a value the raw table's ``NUMERIC(38,18)`` column cannot hold.

    Such a value is not a persisted row. ``copy_abs`` and the wide context keep
    the check itself independent of the caller's context.
    """

    for name in fields:
        value = getattr(record, name)
        if value is None:
            continue
        if value.copy_abs() >= _RAW_NUMERIC_LIMIT or value != value.quantize(RAW_NUMERIC_QUANTUM, context=_WIDE_CONTEXT):
            raise ExtendedReplayInputRefused("RECORD_TYPE_REFUSED", f"{what}: {name} {value} does not fit the raw table's NUMERIC(38,18)")


# --- futures basis: FUTURES_BASIS_CONTRACT_V1 ----------------------------------------

FUTURES_BASIS_CONTRACT_VERSION = "FUTURES_BASIS_CONTRACT_V1"
# The contract's universe: Binance COIN-M BTCUSD quarterly delivery contracts
# listed at t. Which contracts exist, when each was listed and when it delivers
# come only from a hash-bound listing evidence file (owner review ruling 4),
# never from a naming or calendar rule.
FUTURES_BASIS_EXCHANGE = "binance"
FUTURES_BASIS_SYMBOL = "BTCUSD"
FUTURES_BASIS_EXCLUSION_WINDOW = timedelta(days=7)
FUTURES_BASIS_ANNUALIZATION_DAYS = 365
FUTURES_BASIS_WITHIN_7D_OF_EXPIRY = "FUTURES_BASIS_WITHIN_7D_OF_EXPIRY"

FUTURES_BASIS_LISTING_EVIDENCE_VERSION = "FUTURES_BASIS_CONTRACT_LISTING_EVIDENCE_V1"
_LISTING_EVIDENCE_KEYS = frozenset(
    {"evidence_version", "exchange", "symbol", "source", "licence", "retrieved_at", "response_sha256", "contracts"}
)
_LISTING_CONTRACT_KEYS = frozenset({"instrument", "first_kline_open_at", "delivery_at"})


@dataclass(frozen=True)
class FuturesBasisContractListing:
    """One contract's source-backed identity and listing window (owner review ruling 4).

    ``instrument`` is the exchange's symbol for the contract,
    ``first_kline_open_at`` the open time of its first ``1h`` kline in the
    source archive, and ``delivery_at`` its delivery instant. A basis at the
    hour close ``t`` uses the kline that closes at ``t``, so the contract is
    listed at ``t`` when ``first_kline_open_at + 1h <= t < delivery_at``.
    """

    instrument: str
    first_kline_open_at: datetime
    delivery_at: datetime

    def listed_at(self, t: datetime) -> bool:
        return self.first_kline_open_at + _HOUR <= t < self.delivery_at

    def as_record(self) -> dict[str, Any]:
        return {
            "instrument": self.instrument,
            "first_kline_open_at": _iso(self.first_kline_open_at),
            "delivery_at": _iso(self.delivery_at),
        }


@dataclass(frozen=True)
class FuturesBasisListingEvidence:
    """One verified ``FUTURES_BASIS_CONTRACT_LISTING_EVIDENCE_V1`` file."""

    file_sha256: str
    source: str
    licence: str
    retrieved_at: datetime
    response_sha256: tuple[str, ...]
    contracts: tuple[FuturesBasisContractListing, ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "evidence_version": FUTURES_BASIS_LISTING_EVIDENCE_VERSION,
            "file_sha256": self.file_sha256,
            "exchange": FUTURES_BASIS_EXCHANGE,
            "symbol": FUTURES_BASIS_SYMBOL,
            "source": self.source,
            "licence": self.licence,
            "retrieved_at": _iso(self.retrieved_at),
            "response_sha256": list(self.response_sha256),
            "contract_count": len(self.contracts),
            "contracts": [contract.as_record() for contract in self.contracts],
        }


def futures_basis_listing_evidence_bytes(
    *,
    source: str,
    licence: str,
    retrieved_at: datetime,
    response_sha256: Sequence[str],
    contracts: Sequence[FuturesBasisContractListing],
) -> bytes:
    """The canonical bytes of a listing evidence file (RBT-003 writes these)."""

    return v1.canonical_json_bytes(
        {
            "evidence_version": FUTURES_BASIS_LISTING_EVIDENCE_VERSION,
            "exchange": FUTURES_BASIS_EXCHANGE,
            "symbol": FUTURES_BASIS_SYMBOL,
            "source": source,
            "licence": licence,
            "retrieved_at": _iso(retrieved_at),
            "response_sha256": list(response_sha256),
            "contracts": [contract.as_record() for contract in contracts],
        }
    )


def load_futures_basis_listing_evidence(path: str | Path, *, expected_sha256: str) -> FuturesBasisListingEvidence:
    """Read and verify one listing evidence file against its expected SHA-256."""

    return parse_futures_basis_listing_evidence(Path(path).read_bytes(), expected_sha256=expected_sha256)


def parse_futures_basis_listing_evidence(data: bytes, *, expected_sha256: str) -> FuturesBasisListingEvidence:
    """Verify a listing evidence file's bytes: digest, canonical form, schema and contracts."""

    def refuse(reason: str) -> Any:
        raise ExtendedReplayInputRefused("FUTURES_BASIS_LISTING_EVIDENCE_REFUSED", reason)

    digest, payload = _bound_evidence_payload(data, expected_sha256, _LISTING_EVIDENCE_KEYS, refuse)
    declared = {key: payload[key] for key in ("evidence_version", "exchange", "symbol")}
    expected = {
        "evidence_version": FUTURES_BASIS_LISTING_EVIDENCE_VERSION,
        "exchange": FUTURES_BASIS_EXCHANGE,
        "symbol": FUTURES_BASIS_SYMBOL,
    }
    if declared != expected:
        return refuse(f"the evidence declares {declared}, not the contract's universe {expected}")
    retrieved_at, responses = _evidence_provenance(payload, refuse)
    if not isinstance(payload["contracts"], list) or not payload["contracts"]:
        return refuse("contracts must list at least one contract")
    contracts: list[FuturesBasisContractListing] = []
    for item in payload["contracts"]:
        if not isinstance(item, dict) or set(item) != _LISTING_CONTRACT_KEYS:
            return refuse(f"each contract is exactly {sorted(_LISTING_CONTRACT_KEYS)}")
        instrument = item["instrument"]
        if not isinstance(instrument, str) or not instrument or instrument != instrument.strip():
            return refuse(f"contract {instrument!r}: the instrument must be the exchange's symbol")
        first = _evidence_instant(item["first_kline_open_at"], f"{instrument} first_kline_open_at", refuse)
        delivery = _evidence_instant(item["delivery_at"], f"{instrument} delivery_at", refuse)
        if (first.minute, first.second, first.microsecond) != (0, 0, 0):
            return refuse(f"contract {instrument}: a 1h kline opens on the hour")
        if first >= delivery:
            return refuse(f"contract {instrument}: its first kline must open before its delivery")
        if any(other.instrument == instrument for other in contracts):
            return refuse(f"contract {instrument} is listed twice")
        if contracts and delivery <= contracts[-1].delivery_at:
            return refuse(f"contract {instrument}: contracts are ordered by strictly increasing delivery")
        contracts.append(FuturesBasisContractListing(instrument, first, delivery))
    return FuturesBasisListingEvidence(
        file_sha256=digest,
        source=payload["source"],
        licence=payload["licence"],
        retrieved_at=retrieved_at,
        response_sha256=responses,
        contracts=tuple(contracts),
    )


def _verified_listing_evidence(evidence: FuturesBasisListingEvidence) -> FuturesBasisListingEvidence:
    """Re-verify a whole listing record against its file digest at admission, as for market caps."""

    try:
        data = futures_basis_listing_evidence_bytes(
            source=evidence.source,
            licence=evidence.licence,
            retrieved_at=evidence.retrieved_at,
            response_sha256=evidence.response_sha256,
            contracts=evidence.contracts,
        )
    except (AttributeError, TypeError, ValueError, InvalidOperation) as error:
        raise ExtendedReplayInputRefused(
            "FUTURES_BASIS_LISTING_EVIDENCE_REFUSED",
            f"the evidence cannot be written back as its {FUTURES_BASIS_LISTING_EVIDENCE_VERSION} file: {error}",
        ) from None
    return parse_futures_basis_listing_evidence(data, expected_sha256=evidence.file_sha256)


def contract_annualized_basis_rate(basis_rate: Decimal, observation_time: datetime, expiry: datetime) -> Decimal:
    """``basis_rate * 365 days / (expiry - t)`` at the raw table's 18 decimal places.

    Owner review ruling 6: ``basis_rate`` is the stored 18-place rate, and the
    annualised rate RBT-003 persists must be derived from it. The computation
    runs in the builder's own 80-digit context, whatever the caller's.
    """

    span = (_utc(expiry, "expiry") - _utc(observation_time, "observation_time")) // _ONE_MICROSECOND
    if span <= 0:
        raise ExtendedReplayInputRefused("FUTURES_BASIS_CONTRACT_REFUSED", "the contract has expired at t")
    year = FUTURES_BASIS_ANNUALIZATION_DAYS * 86_400 * 1_000_000
    with localcontext(_WIDE_CONTEXT):
        value = basis_rate * Decimal(year) / Decimal(span)
        return value.quantize(RAW_NUMERIC_QUANTUM, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class ExcludedFuturesBasis:
    """A raw basis row the contract excludes, kept in the manifest (owner ruling 3)."""

    row: FuturesBasis
    reason_code: str

    def as_record(self) -> dict[str, Any]:
        record = self.row.as_record()
        return {
            "identity": dict(_basis_identity(self.row)),
            "content_sha256": v1.replay_record_content_sha256(FUTURES_BASIS_FAMILY, record),
            "time_to_expiry_seconds": int((self.row.expiry - self.row.observation_time).total_seconds()),
            "reason_code": self.reason_code,
        }


def _basis_identity(row: FuturesBasis) -> tuple[tuple[str, str], ...]:
    return (*v1._derivative_identity(row, "instrument"), ("expiry", _iso(row.expiry)))


def _replay_futures_basis(
    rows: Sequence[FuturesBasis],
    listing: FuturesBasisListingEvidence | None,
    *,
    window: v1.ReplayWindow,
) -> tuple[
    tuple[FuturesBasis, ...],
    tuple[v1.ReplayInputAvailability, ...],
    tuple[ExcludedFuturesBasis, ...],
    FuturesBasisListingEvidence | None,
]:
    rows = tuple(rows)
    if listing is not None:
        _refuse_unsourceable(listing)
        if type(listing) is not FuturesBasisListingEvidence:
            raise ExtendedReplayInputRefused("FUTURES_BASIS_LISTING_EVIDENCE_REFUSED", "contract listings come only from a verified evidence file")
        listing = _verified_listing_evidence(listing)
    elif rows:
        raise ExtendedReplayInputRefused(
            "FUTURES_BASIS_LISTING_EVIDENCE_REFUSED",
            "futures basis rows need the contract listing evidence that shows each contract listed at t (owner review ruling 4)",
        )
    contracts = {} if listing is None else {contract.instrument: contract for contract in listing.contracts}
    kept: dict[tuple[Any, ...], FuturesBasis] = {}
    excluded: dict[tuple[Any, ...], FuturesBasis] = {}
    for row in rows:
        _require_record(row, FuturesBasis, "futures basis")
        t = _utc(row.observation_time, "futures_basis.observation_time")
        what = f"{FUTURES_BASIS_FAMILY} {t.isoformat()}"
        v1._require_admitted(window, t, t, what=what)
        v1._require_owner_record(row, "futures basis")
        v1._require_decimal_fields(row, ("basis_rate", "annualized_basis_rate"), ())
        _require_raw_numeric(row, ("basis_rate", "annualized_basis_rate"), what)
        _require_contract_row(row, t, what, contracts)
        # owner review ruling 5: one row per contract and instant, whatever its
        # provider, so the owner's average counts each listed contract once
        key = (t, row.instrument)
        if key in kept or key in excluded:
            raise ExtendedReplayInputRefused(
                "DUPLICATE_RECORD_REFUSED",
                f"{what} {row.instrument} is supplied twice (one row per contract and instant, whatever its provider)",
            )
        if row.expiry - t <= FUTURES_BASIS_EXCLUSION_WINDOW:
            excluded[key] = row
        else:
            kept[key] = row

    replayed: list[FuturesBasis] = []
    entries: list[v1.ReplayInputAvailability] = []
    for key in sorted(kept):
        row = kept[key]
        modelled = _utc(row.observation_time, "futures_basis.observation_time")
        replayed.append(replace(row, available_at=modelled))
        entries.append(
            v1._availability(
                FUTURES_BASIS_FAMILY,
                identity=_basis_identity(row),
                record=row.as_record(),
                observation_end=modelled,
                raw_times=(("available_at", row.available_at), ("ingested_at", row.ingested_at)),
                source_published_at=None,
                modelled_available_at=modelled,
            )
        )
    dropped = tuple(ExcludedFuturesBasis(excluded[key], FUTURES_BASIS_WITHIN_7D_OF_EXPIRY) for key in sorted(excluded))
    return tuple(replayed), tuple(entries), dropped, listing


def _require_contract_row(
    row: FuturesBasis,
    t: datetime,
    what: str,
    contracts: Mapping[str, FuturesBasisContractListing],
) -> None:
    def refuse(reason: str, code: str = "FUTURES_BASIS_CONTRACT_REFUSED") -> None:
        raise ExtendedReplayInputRefused(code, f"{what}: {reason} ({FUTURES_BASIS_CONTRACT_VERSION})")

    if (t.minute, t.second, t.microsecond) != (0, 0, 0):
        refuse("the basis is taken at an hour close, so observation_time must be on the hour")
    if (row.exchange, row.symbol) != (FUTURES_BASIS_EXCHANGE, FUTURES_BASIS_SYMBOL):
        refuse(f"{row.exchange}/{row.symbol} is not Binance COIN-M {FUTURES_BASIS_SYMBOL}")
    expiry = _utc(row.expiry, "futures_basis.expiry")
    # owner review ruling 4: identity, listing and delivery from the listing evidence
    contract = contracts.get(row.instrument) if isinstance(row.instrument, str) else None
    if contract is None:
        refuse(f"{row.instrument!r} is not a contract in the listing evidence", "FUTURES_BASIS_CONTRACT_NOT_LISTED")
        return
    if expiry != contract.delivery_at:
        refuse(f"expiry {expiry.isoformat()} is not {row.instrument}'s delivery instant {contract.delivery_at.isoformat()}")
    if not contract.listed_at(t):
        refuse(
            f"{row.instrument} is listed for the hour closes from {(contract.first_kline_open_at + _HOUR).isoformat()} "
            f"to before its delivery {contract.delivery_at.isoformat()}, not at t",
            "FUTURES_BASIS_CONTRACT_NOT_LISTED",
        )
    # owner review ruling 6: exactly the stored rate's annualisation, compared by
    # value (a comparison never rounds, so no context is involved)
    if row.annualized_basis_rate != contract_annualized_basis_rate(row.basis_rate, t, expiry):
        refuse("annualized_basis_rate is not basis_rate * 365 days / (expiry - t) at 18 decimal places")


# --- BTC market cap: hash-bound evidence files ---------------------------------------

MARKET_CAP_EVIDENCE_VERSION = "BTC_MARKET_CAP_EVIDENCE_V1"
# RBT-002's selected provider series (rank 1, USD 0): Coin Metrics Community
# CapMrktCurUSD, daily, final values only. One declared series, shared by every
# venue run, never derived from a venue's reference price (policy V7 section 5).
MARKET_CAP_PROVIDER = "coinmetrics_community"
MARKET_CAP_ASSET = "btc"
MARKET_CAP_METRIC = "CapMrktCurUSD"
MARKET_CAP_FREQUENCY = "1d"
_MARKET_CAP_EVIDENCE_KEYS = frozenset(
    {"evidence_version", "provider", "asset", "metric", "frequency", "source", "licence", "retrieved_at", "response_sha256", "rows"}
)


@dataclass(frozen=True)
class MarketCapEvidence:
    """One verified ``BTC_MARKET_CAP_EVIDENCE_V1`` file: the daily series and its provenance."""

    file_sha256: str
    source: str
    licence: str
    retrieved_at: datetime
    response_sha256: tuple[str, ...]
    rows: tuple[tuple[date, Decimal], ...]

    def as_record(self) -> dict[str, Any]:
        return {
            "evidence_version": MARKET_CAP_EVIDENCE_VERSION,
            "file_sha256": self.file_sha256,
            "provider": MARKET_CAP_PROVIDER,
            "asset": MARKET_CAP_ASSET,
            "metric": MARKET_CAP_METRIC,
            "frequency": MARKET_CAP_FREQUENCY,
            "source": self.source,
            "licence": self.licence,
            "retrieved_at": _iso(self.retrieved_at),
            "response_sha256": list(self.response_sha256),
            "row_count": len(self.rows),
            "first_date": self.rows[0][0].isoformat() if self.rows else None,
            "last_date": self.rows[-1][0].isoformat() if self.rows else None,
        }


def market_cap_evidence_bytes(
    *,
    source: str,
    licence: str,
    retrieved_at: datetime,
    response_sha256: Sequence[str],
    rows: Sequence[tuple[date, Decimal]],
) -> bytes:
    """The canonical bytes of a ``BTC_MARKET_CAP_EVIDENCE_V1`` file (RBT-003 writes these)."""

    return v1.canonical_json_bytes(
        {
            "evidence_version": MARKET_CAP_EVIDENCE_VERSION,
            "provider": MARKET_CAP_PROVIDER,
            "asset": MARKET_CAP_ASSET,
            "metric": MARKET_CAP_METRIC,
            "frequency": MARKET_CAP_FREQUENCY,
            "source": source,
            "licence": licence,
            "retrieved_at": _iso(retrieved_at),
            "response_sha256": list(response_sha256),
            "rows": [{"date": day.isoformat(), "market_cap_usd": v1.canonical_decimal(value)} for day, value in rows],
        }
    )


def load_market_cap_evidence(path: str | Path, *, expected_sha256: str) -> MarketCapEvidence:
    """Read and verify one evidence file against its expected SHA-256."""

    return parse_market_cap_evidence(Path(path).read_bytes(), expected_sha256=expected_sha256)


def parse_market_cap_evidence(data: bytes, *, expected_sha256: str) -> MarketCapEvidence:
    """Verify an evidence file's bytes: digest, canonical form, schema and rows."""

    def refuse(reason: str) -> Any:
        raise ExtendedReplayInputRefused("MARKET_CAP_EVIDENCE_REFUSED", reason)

    digest, payload = _bound_evidence_payload(data, expected_sha256, _MARKET_CAP_EVIDENCE_KEYS, refuse)
    declared = {key: payload[key] for key in ("evidence_version", "provider", "asset", "metric", "frequency")}
    expected = {
        "evidence_version": MARKET_CAP_EVIDENCE_VERSION,
        "provider": MARKET_CAP_PROVIDER,
        "asset": MARKET_CAP_ASSET,
        "metric": MARKET_CAP_METRIC,
        "frequency": MARKET_CAP_FREQUENCY,
    }
    if declared != expected:
        return refuse(f"the evidence declares {declared}, not the selected series {expected}")
    retrieved_at, responses = _evidence_provenance(payload, refuse)
    if not isinstance(payload["rows"], list):
        return refuse("rows must be a list")
    rows: list[tuple[date, Decimal]] = []
    for item in payload["rows"]:
        if not isinstance(item, dict) or set(item) != {"date", "market_cap_usd"}:
            return refuse("each row is exactly {date, market_cap_usd}")
        try:
            day = date.fromisoformat(item["date"])
            value = Decimal(item["market_cap_usd"])
        except (TypeError, ValueError, InvalidOperation):
            return refuse(f"row {item!r} has no ISO date or decimal value")
        if day.isoformat() != item["date"]:
            # one spelling per date, so every file this accepts re-verifies at admission
            return refuse(f"row {item['date']!r}: a date is written YYYY-MM-DD")
        if not value.is_finite() or value <= 0 or v1.canonical_decimal(value) != item["market_cap_usd"]:
            return refuse(f"row {item['date']}: the value must be a positive canonical decimal")
        if rows and day <= rows[-1][0]:
            return refuse(f"row {item['date']}: dates must be unique and increasing")
        rows.append((day, value))
    return MarketCapEvidence(
        file_sha256=digest,
        source=payload["source"],
        licence=payload["licence"],
        retrieved_at=retrieved_at,
        response_sha256=tuple(responses),
        rows=tuple(rows),
    )


def _bound_evidence_payload(data: Any, expected_sha256: Any, keys: frozenset[str], refuse: Any) -> tuple[str, dict[str, Any]]:
    """An evidence file's digest and canonical JSON object, with exactly ``keys``."""

    if not isinstance(data, bytes):
        return refuse("evidence must be the file's bytes")
    if not isinstance(expected_sha256, str) or not _SHA256.fullmatch(expected_sha256):
        return refuse("the expected SHA-256 must be 64 lowercase hex digits")
    digest = v1.sha256_hex(data)
    if digest != expected_sha256:
        return refuse(f"the file's SHA-256 {digest} is not the bound {expected_sha256}")
    try:
        payload = json.loads(data)
    except (UnicodeDecodeError, ValueError):
        return refuse("the file is not JSON")
    if not isinstance(payload, dict) or v1.canonical_json_bytes(payload) != data:
        return refuse("the file is not canonical JSON (sorted keys, no whitespace, ASCII)")
    if set(payload) != keys:
        return refuse(f"the evidence keys must be exactly {sorted(keys)}")
    return digest, payload


def _evidence_provenance(payload: Mapping[str, Any], refuse: Any) -> tuple[datetime, tuple[str, ...]]:
    """An evidence file's source, licence, retrieval instant and response digests."""

    for key in ("source", "licence"):
        if not isinstance(payload[key], str) or not payload[key].strip():
            return refuse(f"{key} must be a non-empty string")
    retrieved_at = _evidence_instant(payload["retrieved_at"], "retrieved_at", refuse)
    responses = payload["response_sha256"]
    if not isinstance(responses, list) or not responses or not all(isinstance(item, str) and _SHA256.fullmatch(item) for item in responses):
        return refuse("response_sha256 must list each retrieved response's SHA-256")
    return retrieved_at, tuple(responses)


def _evidence_instant(value: Any, name: str, refuse: Any) -> datetime:
    """An evidence file's UTC instant, in the one spelling the file writer uses.

    ``datetime.fromisoformat`` also reads ``Z``, a space separator or another
    offset. Admission writes the record back in the canonical spelling and checks
    its digest, so a file this parser accepted in another spelling would be
    refused there; it is refused here instead.
    """

    try:
        instant = _utc(datetime.fromisoformat(value), name)
    except (TypeError, ValueError):
        return refuse(f"{name} must be an ISO-8601 UTC instant")
    if _iso(instant) != value:
        return refuse(f"{name} {value!r} must be written {_iso(instant)!r}")
    return instant


def _verified_market_cap_evidence(evidence: MarketCapEvidence) -> MarketCapEvidence:
    """Re-verify a whole evidence record against its file digest at admission (review F1).

    ``MarketCapEvidence`` is frozen, but ``dataclasses.replace`` can still make
    one with changed rows and the original digest. The builder therefore
    writes the record's canonical bytes again and parses them against the
    digest it claims: a changed field, a malformed digest or a duplicate date is
    refused, and the replay uses the verified copy.
    """

    try:
        data = market_cap_evidence_bytes(
            source=evidence.source,
            licence=evidence.licence,
            retrieved_at=evidence.retrieved_at,
            response_sha256=evidence.response_sha256,
            rows=evidence.rows,
        )
    except (AttributeError, TypeError, ValueError, InvalidOperation) as error:
        raise ExtendedReplayInputRefused(
            "MARKET_CAP_EVIDENCE_REFUSED",
            f"the evidence cannot be written back as its {MARKET_CAP_EVIDENCE_VERSION} file: {error}",
        ) from None
    return parse_market_cap_evidence(data, expected_sha256=evidence.file_sha256)


def market_cap_observation_time(day: date) -> datetime:
    """RBT-002's pinned stamp of day D's end-of-day value: ``D+1 00:00`` UTC."""

    return datetime.combine(day, time(0), tzinfo=UTC) + _DAY


def modelled_market_cap_available_at(day: date) -> datetime:
    """``DAILY_PUBLISHED``: ``00:00`` UTC on ``D+2``; the source supplies no later time."""

    return datetime.combine(day, time(0), tzinfo=UTC) + 2 * _DAY


def _replay_market_caps(
    evidence: MarketCapEvidence | None,
    *,
    window: v1.ReplayWindow,
) -> tuple[tuple[MarketCapObservation, ...], tuple[v1.ReplayInputAvailability, ...], MarketCapEvidence | None]:
    if evidence is None:
        return (), (), None
    _refuse_unsourceable(evidence)
    if type(evidence) is not MarketCapEvidence:
        raise ExtendedReplayInputRefused("MARKET_CAP_EVIDENCE_REFUSED", "market caps come only from a verified evidence file")
    evidence = _verified_market_cap_evidence(evidence)
    replayed: list[MarketCapObservation] = []
    entries: list[v1.ReplayInputAvailability] = []
    for day, value in evidence.rows:
        start = datetime.combine(day, time(0), tzinfo=UTC)
        v1._require_admitted(window, start, start + _DAY - _ONE_MICROSECOND, what=f"{BTC_MARKET_CAP_FAMILY} {day.isoformat()}")
        observation = MarketCapObservation(
            observation_time=market_cap_observation_time(day),
            market_cap_usd=value,
            provider=MARKET_CAP_PROVIDER,
            available_at=modelled_market_cap_available_at(day),
        )
        record = v1._require_owner_record(observation, "market cap")
        replayed.append(observation)
        entries.append(
            v1._availability(
                BTC_MARKET_CAP_FAMILY,
                identity=(("observation_date", day.isoformat()), ("provider", MARKET_CAP_PROVIDER), ("metric", MARKET_CAP_METRIC)),
                record=record,
                observation_end=observation.observation_time,
                raw_times=(("evidence_retrieved_at", evidence.retrieved_at),),
                source_published_at=None,
                modelled_available_at=observation.available_at,
            )
        )
    return tuple(replayed), tuple(entries), evidence


# --- liquidations: HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1 -----------------------

LIQUIDATION_COMPLETENESS_VERSION = "HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1"
# The EPIC X universe (policy V7 section 4A reuses it by reference): Kraken
# Futures PI_XBTUSD, per-side 1h aggregates, sides as the derivatives owner
# names positions.
LIQUIDATION_EXCHANGE = "kraken_futures"
LIQUIDATION_SYMBOL = epic_x.LIQUIDATION_INSTRUMENT
LIQUIDATION_TIMEFRAME = epic_x.LIQUIDATION_TIMEFRAME
LIQUIDATION_SIDES = tuple(sorted(set(epic_x.LIQUIDATION_SIDE_TO_POSITION.values())))
LIQUIDATION_HOUR_STATUSES = (
    epic_x.FEED_STATUS_OBSERVED_WITH_EVENTS,
    epic_x.FEED_STATUS_OBSERVED_ZERO_EVENTS,
    epic_x.FEED_STATUS_SOURCE_UNAVAILABLE,
)
CORROBORATION_AGREES = "AGREES"
CORROBORATION_DISAGREES = "DISAGREES"
CORROBORATION_SERIES_UNAVAILABLE = "SERIES_UNAVAILABLE"
CORROBORATION_NOT_APPLICABLE = "NOT_APPLICABLE"
CORROBORATION_RESULTS = (
    CORROBORATION_AGREES,
    CORROBORATION_DISAGREES,
    CORROBORATION_SERIES_UNAVAILABLE,
    CORROBORATION_NOT_APPLICABLE,
)
# The two reason codes the frozen adapter contract names for a missing value.
LIQUIDATION_FEED_UNAVAILABLE = "LIQUIDATION_FEED_UNAVAILABLE"
LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY = "LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY"
LIQUIDATION_PERCENTILE_CONVENTION_OWNER = "btc_predictor.features.volatility._percentile_rank"
LIQUIDATION_DAY_OBSERVATION_CONVENTION = "UTC_DAY_START"
LIQUIDATION_DAY_AVAILABILITY = "UTC_DAY_END"


@dataclass(frozen=True)
class LiquidationHourEvidence:
    """RBT-003's record of one hour of the Kraken Futures REST execution log.

    ``feed_status`` is the ``HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1`` state:
    ``OBSERVED_WITH_EVENTS`` or ``OBSERVED_ZERO_EVENTS`` when the log was read
    contiguously across the hour and at least one execution of any type is
    stamped in it, and ``SOURCE_UNAVAILABLE`` for an hour with no execution or a
    reported incident hour. ``corroboration`` is the comparison of the hour's
    liquidation total with Kraken's hourly liquidation-volume series:
    ``AGREES`` (within rounding), ``DISAGREES`` or ``SERIES_UNAVAILABLE`` for an
    observed hour, ``NOT_APPLICABLE`` for an unavailable one. ``evidence_sha256``
    addresses the acquisition evidence RBT-003 keeps (the event-id digests).
    """

    hour_start: datetime
    feed_status: str
    corroboration: str
    evidence_sha256: str

    def as_record(self) -> dict[str, Any]:
        return {
            "hour_start": _iso(self.hour_start),
            "feed_status": self.feed_status,
            "corroboration": self.corroboration,
            "evidence_sha256": self.evidence_sha256,
        }


def modelled_liquidation_available_at(row: Liquidation) -> datetime:
    """A ``1h`` liquidation aggregate stamped at its hour start is available at the hour's end."""

    _require_record(row, Liquidation, "liquidation")
    return _utc(row.observation_time, "liquidation.observation_time") + _HOUR


def _replay_liquidations(
    rows: Sequence[Liquidation],
    hours: Sequence[LiquidationHourEvidence],
    *,
    window: v1.ReplayWindow,
) -> tuple[
    tuple[Liquidation, ...],
    tuple[v1.ReplayInputAvailability, ...],
    tuple[LiquidationHourEvidence, ...],
]:
    evidence: dict[datetime, LiquidationHourEvidence] = {}
    for hour in tuple(hours):
        _require_hour_evidence(hour, window)
        if hour.hour_start in evidence:
            raise ExtendedReplayInputRefused("DUPLICATE_RECORD_REFUSED", f"hour {hour.hour_start.isoformat()} has two evidence records")
        evidence[hour.hour_start] = hour

    by_key: dict[tuple[datetime, str], Liquidation] = {}
    for row in tuple(rows):
        _require_record(row, Liquidation, "liquidation")
        start = _utc(row.observation_time, "liquidation.observation_time")
        what = f"{LIQUIDATIONS_FAMILY} {row.side} {start.isoformat()}"
        if (row.exchange, row.symbol, row.timeframe) != (LIQUIDATION_EXCHANGE, LIQUIDATION_SYMBOL, LIQUIDATION_TIMEFRAME) or row.side not in LIQUIDATION_SIDES:
            raise ExtendedReplayInputRefused(
                "LIQUIDATION_UNIVERSE_REFUSED",
                f"{what}: {row.exchange}/{row.symbol}/{row.timeframe}/{row.side} is not a {LIQUIDATION_EXCHANGE} "
                f"{LIQUIDATION_SYMBOL} {LIQUIDATION_TIMEFRAME} per-side aggregate",
            )
        if (start.minute, start.second, start.microsecond) != (0, 0, 0):
            raise ExtendedReplayInputRefused("LIQUIDATION_UNIVERSE_REFUSED", f"{what}: a 1h aggregate is stamped at its hour start")
        v1._require_admitted(window, start, start + _HOUR - _ONE_MICROSECOND, what=what)
        v1._require_owner_record(row, "liquidation")
        if row.notional_usd is None:
            raise ExtendedReplayInputRefused(
                "LIQUIDATION_NOTIONAL_MISSING",
                f"{what}: the adapter's quantity is USD notional, which this row does not carry",
            )
        v1._require_decimal_fields(row, ("quantity", "notional_usd"), ())
        _require_raw_numeric(row, ("quantity", "notional_usd"), what)
        if row.notional_usd < 0:
            raise ExtendedReplayInputRefused("RECORD_TYPE_REFUSED", f"{what}: notional_usd must be >= 0")
        if start not in evidence:
            raise ExtendedReplayInputRefused("LIQUIDATION_HOUR_EVIDENCE_MISSING", f"{what}: the hour has no completeness evidence")
        key = (start, row.side)
        if key in by_key:
            raise ExtendedReplayInputRefused("DUPLICATE_RECORD_REFUSED", f"{what} is supplied twice")
        by_key[key] = row

    positive = {start for (start, _), row in by_key.items() if row.notional_usd > 0}
    present = {start for start, _ in by_key}
    for start, hour in evidence.items():
        status = hour.feed_status
        if status == epic_x.FEED_STATUS_OBSERVED_WITH_EVENTS and start not in positive:
            reason = "is OBSERVED_WITH_EVENTS but carries no liquidation notional"
        elif status == epic_x.FEED_STATUS_OBSERVED_ZERO_EVENTS and start in positive:
            reason = "is OBSERVED_ZERO_EVENTS but carries liquidation notional"
        elif status == epic_x.FEED_STATUS_SOURCE_UNAVAILABLE and start in present:
            reason = "is SOURCE_UNAVAILABLE but carries liquidation rows"
        else:
            continue
        raise ExtendedReplayInputRefused("LIQUIDATION_HOUR_STATUS_INCONSISTENT", f"hour {start.isoformat()} {reason}")

    replayed: list[Liquidation] = []
    entries: list[v1.ReplayInputAvailability] = []
    for key in sorted(by_key):
        row = by_key[key]
        modelled = modelled_liquidation_available_at(row)
        replayed.append(replace(row, available_at=modelled))
        entries.append(
            v1._availability(
                LIQUIDATIONS_FAMILY,
                identity=v1._derivative_identity(row, "side"),
                record=row.as_record(),
                observation_end=modelled,
                raw_times=(("available_at", row.available_at), ("ingested_at", row.ingested_at)),
                source_published_at=None,
                modelled_available_at=modelled,
            )
        )
    return tuple(replayed), tuple(entries), tuple(evidence[start] for start in sorted(evidence))


def _require_hour_evidence(hour: Any, window: v1.ReplayWindow) -> None:
    _refuse_unsourceable(hour)
    if type(hour) is not LiquidationHourEvidence:
        raise ExtendedReplayInputRefused("RECORD_TYPE_REFUSED", f"liquidation hour evidence must be a LiquidationHourEvidence, not {type(hour).__name__}")
    start = _utc(hour.hour_start, "hour_start")

    def refuse(reason: str) -> None:
        raise ExtendedReplayInputRefused("LIQUIDATION_HOUR_EVIDENCE_REFUSED", f"hour {start.isoformat()}: {reason}")

    if (start.minute, start.second, start.microsecond) != (0, 0, 0):
        refuse("hour_start must be on the hour")
    v1._require_admitted(window, start, start + _HOUR - _ONE_MICROSECOND, what=f"{LIQUIDATION_HOUR_EVIDENCE_FAMILY} {start.isoformat()}")
    if hour.feed_status not in LIQUIDATION_HOUR_STATUSES:
        refuse(f"{hour.feed_status!r} is not a {LIQUIDATION_COMPLETENESS_VERSION} status")
    if hour.corroboration not in CORROBORATION_RESULTS:
        refuse(f"{hour.corroboration!r} is not a corroboration result")
    if not isinstance(hour.evidence_sha256, str) or not _SHA256.fullmatch(hour.evidence_sha256):
        refuse("evidence_sha256 must be 64 lowercase hex digits")
    observed = hour.feed_status in epic_x.LIQUIDATION_OBSERVED_FEED_STATUSES
    if observed and hour.corroboration == CORROBORATION_DISAGREES:
        # Owner ruling 2: the series "must agree within rounding".
        raise ExtendedReplayInputRefused(
            "LIQUIDATION_CORROBORATION_DISAGREES",
            f"hour {start.isoformat()}: the liquidation total disagrees with Kraken's hourly liquidation-volume series",
        )
    if observed and hour.corroboration == CORROBORATION_SERIES_UNAVAILABLE:
        raise ExtendedReplayInputRefused(
            "LIQUIDATION_CORROBORATION_UNAVAILABLE",
            f"hour {start.isoformat()}: Kraken's hourly series has no value to agree with",
        )
    if observed != (hour.corroboration != CORROBORATION_NOT_APPLICABLE):
        refuse(f"{hour.feed_status} cannot carry corroboration {hour.corroboration}")


# --- LIQUIDATION_PERCENTILE: PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_V1 by reference


@dataclass(frozen=True)
class LiquidationDay:
    """One UTC day's census and its percentile, as the manifest records it."""

    observation_date: date
    complete: bool
    daily_notional_usd: Decimal | None
    history_observation_count: int | None
    observation: LiquidationPercentileObservation

    def as_record(self) -> dict[str, Any]:
        return {
            "observation_date": self.observation_date.isoformat(),
            "complete": self.complete,
            "daily_notional_usd": self.daily_notional_usd,
            "history_observation_count": self.history_observation_count,
            "liquidation_percentile": self.observation.liquidation_percentile,
            "available_at": self.observation.available_at,
            "reason_codes": list(self.observation.reason_codes),
        }


def _liquidation_percentiles(
    rows: Sequence[Liquidation],
    hours: Sequence[LiquidationHourEvidence],
) -> tuple[LiquidationDay, ...]:
    """Execute the frozen adapter contract over complete UTC days.

    A day is complete when all 24 of its hours are observed
    (``HISTORICAL_LIQUIDATION_HOUR_COMPLETENESS_V1``); its quantity is the
    long-plus-short USD notional over those hours. Any other day yields no
    value (``LIQUIDATION_FEED_UNAVAILABLE``) and enters no history. A complete
    day with fewer than the minimum complete days in its half-open trailing
    window yields no value (``LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY``).
    """

    if not hours:
        return ()
    status = {hour.hour_start: hour.feed_status for hour in hours}
    notional: dict[date, Decimal] = {}
    with localcontext(_WIDE_CONTEXT):
        # exact: every admitted notional fits NUMERIC(38,18) (review F3)
        for row in rows:
            day = row.observation_time.date()
            notional[day] = notional.get(day, Decimal("0")) + row.notional_usd
    first = min(status).date()
    last = max(status).date()
    window = timedelta(days=epic_x.LIQUIDATION_PERCENTILE_WINDOW_DAYS)
    minimum = epic_x.LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS
    complete_days: list[tuple[datetime, Decimal]] = []
    days: list[LiquidationDay] = []
    day = first
    while day <= last:
        start = datetime.combine(day, time(0), tzinfo=UTC)
        available_at = start + _DAY
        complete = all(
            status.get(start + offset * _HOUR) in epic_x.LIQUIDATION_OBSERVED_FEED_STATUSES for offset in range(24)
        )
        if not complete:
            observation = LiquidationPercentileObservation(day, None, available_at, (LIQUIDATION_FEED_UNAVAILABLE,))
            days.append(LiquidationDay(day, False, None, None, observation))
        else:
            value = notional.get(day, Decimal("0"))
            history = [prior for prior_start, prior in complete_days if start - window <= prior_start < start]
            if len(history) < minimum:
                observation = LiquidationPercentileObservation(
                    day, None, available_at, (LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY,)
                )
            else:
                with localcontext(_OWNER_CONTEXT):
                    percentile = _percentile_rank(value, history)
                observation = LiquidationPercentileObservation(day, percentile, available_at)
            days.append(LiquidationDay(day, True, value, len(history), observation))
            complete_days.append((start, value))
        day += _DAY
    return tuple(days)


# --- declared inputs: discretionary and unsourceable ---------------------------------

# Policy V7 section 4: never back-filled; supplied as not asserted (None).
DISCRETIONARY_INPUTS: Mapping[str, str] = {
    "MANUAL_RESEARCH_OVERRIDE": "the exit owner's manual research override is never asserted",
    "SYSTEMIC_EUPHORIA": "the EUPHORIA flag's systemic assertion is never asserted",
    "SYSTEMIC_SHOCK": "the STRESS flag's systemic assertion is never asserted",
}
# RBT-002's absent families: no persisted point-in-time source exists, so each
# is refused, never approximated, and the policy fallback applies.
UNSOURCEABLE_INPUTS: Mapping[str, str] = {
    "CVD": "absent: Rulebook 6.2 Phase-1 fallback FLOW_MODEL = ETF_CORE (policy V7 section 5)",
    "SPOT_DOMINANCE_ZSCORE": "absent: Rulebook 6.2 Phase-1 fallback FLOW_MODEL = ETF_CORE (policy V7 section 5)",
    "MACRO": "declared unavailable: the Rulebook core regime fallback applies (policy V7 section 5)",
    "ONCHAIN": "declared unavailable: the Rulebook core regime fallback applies (policy V7 section 5)",
    "LIQUIDITY": "declared unavailable: the Rulebook core regime fallback applies (policy V7 section 5)",
}
# The owner records of an unsourceable input: refused wherever supplied.
_UNSOURCEABLE_RECORD_TYPES: Mapping[type, str] = {CvdObservation: "CVD"}


# --- the extended snapshot ------------------------------------------------------------


@dataclass(frozen=True)
class ExtendedReplaySnapshot:
    """The V1 shared snapshot plus every family policy V3 added, under one manifest."""

    window: v1.ReplayWindow
    shared_snapshot: v1.SharedReplaySnapshot
    futures_basis: tuple[FuturesBasis, ...]
    excluded_futures_basis: tuple[ExcludedFuturesBasis, ...]
    market_caps: tuple[MarketCapObservation, ...]
    liquidations: tuple[Liquidation, ...]
    liquidation_hours: tuple[LiquidationHourEvidence, ...]
    liquidation_days: tuple[LiquidationDay, ...]
    availability: tuple[v1.ReplayInputAvailability, ...]
    manifest_bytes: bytes
    manifest_sha256: str

    @property
    def manifest(self) -> dict[str, Any]:
        """A fresh decoded copy; the canonical bytes stay authoritative."""

        return json.loads(self.manifest_bytes)

    @property
    def liquidation_percentiles(self) -> tuple[LiquidationPercentileObservation, ...]:
        return tuple(day.observation for day in self.liquidation_days)

    def entry_composer_inputs(
        self,
        dataset: v1.VenueReplayDataset,
        *,
        etf_fund_launches: Sequence[EtfFundLaunch] = (),
    ) -> EntryComposerInputs:
        """The entry composer's inputs for one venue run over this snapshot."""

        if (
            type(dataset) is not v1.VenueReplayDataset
            or dataset.window != self.window
            or dataset.shared_snapshot.manifest_sha256 != self.shared_snapshot.manifest_sha256
        ):
            raise ExtendedReplayInputRefused(
                "SHARED_SNAPSHOT_MISMATCH",
                "the venue dataset must replay the shared snapshot this extended snapshot binds",
            )
        return EntryComposerInputs(
            dataset=dataset,
            futures_basis=self.futures_basis,
            market_caps=self.market_caps,
            liquidation_percentiles=self.liquidation_percentiles,
            etf_fund_launches=tuple(etf_fund_launches),
        )


def build_extended_replay_snapshot(
    *,
    shared_snapshot: v1.SharedReplaySnapshot,
    futures_basis: Sequence[FuturesBasis] = (),
    futures_basis_listing: FuturesBasisListingEvidence | None = None,
    market_cap_evidence: MarketCapEvidence | None = None,
    liquidations: Sequence[Liquidation] = (),
    liquidation_hours: Sequence[LiquidationHourEvidence] = (),
) -> ExtendedReplaySnapshot:
    """Extend a finished V1 shared snapshot to ``HISTORICAL_REPLAY_AVAILABILITY_V2``.

    The V1 snapshot must have been built with ``US_EQUITY_MARKET_CLOSURE_TABLE_V1``
    as its ETF market holidays (policy V7 section 5 requires the table). Its
    manifest is bound by digest and never rebuilt here, so V1-built manifests
    stay reproducible byte for byte.
    """

    if type(shared_snapshot) is not v1.SharedReplaySnapshot:
        raise ExtendedReplayInputRefused("RECORD_TYPE_REFUSED", "shared_snapshot must be a V1 SharedReplaySnapshot")
    window = v1.require_replay_window(shared_snapshot.window)
    shared = shared_snapshot.manifest
    closure_record = _require_closure_table(shared)

    basis_replay, basis_entries, basis_excluded, listing = _replay_futures_basis(futures_basis, futures_basis_listing, window=window)
    cap_replay, cap_entries, cap_evidence = _replay_market_caps(market_cap_evidence, window=window)
    liquidation_replay, liquidation_entries, hour_evidence = _replay_liquidations(liquidations, liquidation_hours, window=window)
    days = _liquidation_percentiles(liquidation_replay, hour_evidence)

    basis_section = _family_section(FUTURES_BASIS_FAMILY, basis_entries, _basis_series(basis_replay))
    basis_section["contract"] = FUTURES_BASIS_CONTRACT_VERSION
    basis_section["listing_evidence"] = None if listing is None else listing.as_record()
    basis_section["excluded"] = [item.as_record() for item in basis_excluded]
    basis_section["excluded_count"] = len(basis_excluded)
    cap_section = _family_section(BTC_MARKET_CAP_FAMILY, cap_entries, _market_cap_series(cap_replay))
    cap_section["evidence"] = None if cap_evidence is None else cap_evidence.as_record()
    liquidation_section = _family_section(LIQUIDATIONS_FAMILY, liquidation_entries, _liquidation_series(liquidation_replay))
    liquidation_section["completeness_rule"] = LIQUIDATION_COMPLETENESS_VERSION
    liquidation_section["hour_evidence"] = _hour_evidence_section(hour_evidence)

    availability = (*basis_entries, *cap_entries, *liquidation_entries)
    own_unavailable = v1._revision_count(availability)
    manifest = {
        "manifest_version": EXTENDED_SNAPSHOT_MANIFEST_VERSION,
        "builder_version": REPLAY_INPUTS_V2_BUILDER_VERSION,
        "policy": RESEARCH_BACKTEST_POLICY_V7,
        "availability_policy": REPLAY_AVAILABILITY_POLICY_V2,
        "evidence_class": v1.RESEARCH_EVIDENCE_CLASS,
        "canonical_reference": v1.CANONICAL_REFERENCE_UNRESOLVED,
        "window": window.as_record(),
        "shared_snapshot": {
            "manifest_version": shared["manifest_version"],
            "builder_version": shared["builder_version"],
            "availability_policy": shared["availability_policy"],
            "manifest_sha256": shared_snapshot.manifest_sha256,
            "families": sorted(shared["families"]),
            "rules_unchanged_under": REPLAY_AVAILABILITY_POLICY_V2,
        },
        "shapes": dict(sorted(REPLAY_SHAPES_V2.items())),
        "closure_table": closure_record,
        "families": {
            FUTURES_BASIS_FAMILY: basis_section,
            BTC_MARKET_CAP_FAMILY: cap_section,
            LIQUIDATIONS_FAMILY: liquidation_section,
        },
        "liquidation_percentile": _percentile_section(days),
        "discretionary_inputs": {
            input_id: {
                "shape": coverage.SHAPE_DISCRETIONARY,
                "status": "NOT_ASSERTED",
                "supplied": None,
                "handling": f"{handling}; the owner's documented handling of None applies and it is reported "
                "as a named limitation (policy V7 section 4)",
            }
            for input_id, handling in sorted(DISCRETIONARY_INPUTS.items())
        },
        "unsourceable_inputs": {
            input_id: {"status": "REFUSED_NOT_APPROXIMATED", "treatment": treatment}
            for input_id, treatment in sorted(UNSOURCEABLE_INPUTS.items())
        },
        "revision_history_unavailable_count": own_unavailable + shared["revision_history_unavailable_count"],
    }
    manifest_bytes = v1.canonical_json_bytes(_jsonable(manifest))
    return ExtendedReplaySnapshot(
        window=window,
        shared_snapshot=shared_snapshot,
        futures_basis=basis_replay,
        excluded_futures_basis=basis_excluded,
        market_caps=cap_replay,
        liquidations=liquidation_replay,
        liquidation_hours=hour_evidence,
        liquidation_days=days,
        availability=availability,
        manifest_bytes=manifest_bytes,
        manifest_sha256=v1.sha256_hex(manifest_bytes),
    )


def _require_closure_table(shared: Mapping[str, Any]) -> dict[str, Any]:
    table = sorted(closures.load_closures(closures.COVERAGE_START, closures.COVERAGE_END))
    if shared["etf_market_holidays"] != [day.isoformat() for day in table]:
        raise ExtendedReplayInputRefused(
            "CLOSURE_TABLE_REQUIRED",
            f"the shared snapshot must count ETF gaps with {closures.TABLE_VERSION} over its whole coverage",
        )
    return {
        "table_version": closures.TABLE_VERSION,
        "definition_sha256": closures.DEFINITION_SHA256,
        "closure_table_file_sha256": closures.CLOSURE_TABLE_FILE_SHA256,
        "coverage_start": closures.COVERAGE_START.isoformat(),
        "coverage_end": closures.COVERAGE_END.isoformat(),
        "closure_count": len(table),
    }


# --- manifest sections ----------------------------------------------------------------


def _family_section(
    family: str,
    entries: Sequence[v1.ReplayInputAvailability],
    series: Sequence[dict[str, Any]],
) -> dict[str, Any]:
    """V1's family section layout, with this module's rule and shape."""

    records = [entry.as_record() for entry in entries]
    evaluated = [item["gaps"] for item in series if item["gaps"]["gap_count"] is not None]
    reasons = (
        sorted({item["gaps"]["not_evaluated_reason"] for item in series if item["gaps"]["gap_count"] is None})
        if series
        else ["FAMILY_HAS_NO_RECORDS"]
    )
    return {
        "rule": REPLAY_AVAILABILITY_RULES_V2[family].as_record(),
        "shape": REPLAY_SHAPES_V2[family],
        "record_count": len(records),
        "records_sha256": v1.sha256_hex(v1.canonical_json_bytes(records)),
        "revision_history_unavailable_count": v1._revision_count(entries),
        "series": list(series),
        "gap_count": None if reasons else sum(gaps["gap_count"] for gaps in evaluated),
        "missing_slot_count": (
            None
            if reasons or any(gaps["missing_slot_count"] is None for gaps in evaluated)
            else sum(gaps["missing_slot_count"] for gaps in evaluated)
        ),
        "gap_not_evaluated_reasons": reasons,
        "records": records,
    }


def _basis_series(rows: Sequence[FuturesBasis]) -> tuple[dict[str, Any], ...]:
    grouped: dict[tuple[str, str, str], list[datetime]] = {}
    for row in rows:
        grouped.setdefault((row.exchange, row.symbol, row.provider), []).append(row.observation_time)
    return tuple(
        {
            "identity": {"exchange": exchange, "symbol": symbol, "provider": provider},
            "record_count": len(times),
            "first_observation": _iso(min(times)),
            "last_observation": _iso(max(times)),
            # an hour with no kept contract is a gap, whichever contract is current
            "gaps": v1._grid_gaps(times, "1h", method="OWNER_BAR_GRID_ACROSS_CONTRACTS"),
        }
        for (exchange, symbol, provider), times in sorted(grouped.items())
    )


def _market_cap_series(caps: Sequence[MarketCapObservation]) -> tuple[dict[str, Any], ...]:
    if not caps:
        return ()
    times = [cap.observation_time for cap in caps]
    return (
        {
            "identity": {"provider": MARKET_CAP_PROVIDER, "metric": MARKET_CAP_METRIC},
            "record_count": len(caps),
            "first_observation": _iso(min(times)),
            "last_observation": _iso(max(times)),
            "gaps": v1._grid_gaps(times, "1d", method="OWNER_BAR_GRID"),
        },
    )


def _liquidation_series(rows: Sequence[Liquidation]) -> tuple[dict[str, Any], ...]:
    grouped: dict[tuple[str, str, str, str], list[datetime]] = {}
    for row in rows:
        grouped.setdefault((row.exchange, row.symbol, row.side, row.provider), []).append(row.observation_time)
    return tuple(
        {
            "identity": {"exchange": exchange, "symbol": symbol, "side": side, "provider": provider},
            "record_count": len(times),
            "first_observation": _iso(min(times)),
            "last_observation": _iso(max(times)),
            # an hour with no liquidation has no row; completeness is the hour evidence
            "gaps": v1._not_evaluated("HOUR_COMPLETENESS_EVIDENCE", "COMPLETENESS_BY_HOUR_EVIDENCE"),
        }
        for (exchange, symbol, side, provider), times in sorted(grouped.items())
    )


def _hour_evidence_section(hours: Sequence[LiquidationHourEvidence]) -> dict[str, Any]:
    records = [hour.as_record() for hour in hours]
    counts = {status: sum(1 for hour in hours if hour.feed_status == status) for status in LIQUIDATION_HOUR_STATUSES}
    return {
        "record_count": len(records),
        "records_sha256": v1.sha256_hex(v1.canonical_json_bytes(records)),
        "status_counts": counts,
        "first_hour": _iso(hours[0].hour_start) if hours else None,
        "last_hour": _iso(hours[-1].hour_start) if hours else None,
        "gaps": (
            v1._grid_gaps([hour.hour_start for hour in hours], "1h", method="OWNER_BAR_GRID")
            if hours
            else v1._not_evaluated("OWNER_BAR_GRID", "FAMILY_HAS_NO_RECORDS")
        ),
        "records": records,
    }


def _percentile_section(days: Sequence[LiquidationDay]) -> dict[str, Any]:
    contract = epic_x.prospective_liquidation_percentile_adapter_contract()
    records = []
    for day in days:
        record = day.as_record()
        records.append(
            {
                "observation_date": record["observation_date"],
                "complete": day.complete,
                "valued": day.observation.liquidation_percentile is not None,
                "reason_codes": list(day.observation.reason_codes),
                "available_at": _iso(day.observation.available_at),
                "content_sha256": _content_sha256(LIQUIDATION_PERCENTILE_INPUT, record),
            }
        )
    return {
        "input_id": LIQUIDATION_PERCENTILE_INPUT,
        "adapter": {
            "version": epic_x.PROSPECTIVE_LIQUIDATION_PERCENTILE_ADAPTER_VERSION,
            "definition_sha256": contract["definition_sha256"],
            "window_days": epic_x.LIQUIDATION_PERCENTILE_WINDOW_DAYS,
            "minimum_prior_observations": epic_x.LIQUIDATION_PERCENTILE_MIN_OBSERVATIONS,
            "convention": epic_x.LIQUIDATION_PERCENTILE_CONVENTION,
            "convention_owner": LIQUIDATION_PERCENTILE_CONVENTION_OWNER,
        },
        "completeness_rule": LIQUIDATION_COMPLETENESS_VERSION,
        "observation_convention": LIQUIDATION_DAY_OBSERVATION_CONVENTION,
        "modelled_availability": LIQUIDATION_DAY_AVAILABILITY,
        "day_count": len(days),
        "complete_day_count": sum(1 for day in days if day.complete),
        "valued_day_count": sum(1 for day in days if day.observation.liquidation_percentile is not None),
        "reason_code_counts": {
            code: sum(1 for day in days if code in day.observation.reason_codes)
            for code in (LIQUIDATION_FEED_UNAVAILABLE, LIQUIDATION_PERCENTILE_INSUFFICIENT_HISTORY)
        },
        "records_sha256": v1.sha256_hex(v1.canonical_json_bytes(records)),
        "records": records,
    }


# --- helpers --------------------------------------------------------------------------


def _require_record(value: Any, expected: type, name: str) -> None:
    _refuse_unsourceable(value)
    v1._require_type(value, expected, name)


def _refuse_unsourceable(value: Any) -> None:
    unsourceable = _UNSOURCEABLE_RECORD_TYPES.get(type(value))
    if unsourceable is not None:
        raise ExtendedReplayInputRefused(
            "UNSOURCEABLE_INPUT_REFUSED",
            f"{unsourceable} is unsourceable ({UNSOURCEABLE_INPUTS[unsourceable]}); it is refused, never approximated",
        )


def _content_sha256(family: str, record: Mapping[str, Any]) -> str:
    """V1's content-digest layout, for a derived record that may hold lists."""

    return v1.sha256_hex(v1.canonical_json_bytes({"family": family, "record": _jsonable(record)}))


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return v1._jsonable(value)


def _iso(value: datetime | None) -> str | None:
    return v1._iso(value)


def _utc(value: Any, name: str) -> datetime:
    return v1._utc(value, name)
