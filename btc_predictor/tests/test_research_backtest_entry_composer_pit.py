"""RBT-004 point-in-time property test (policy V7 section 4; ticket acceptance criterion).

The composer reads only replay inputs whose modelled availability is at or
before the decision instant. For deterministic seeds, every input family is
perturbed or extended *after* ``t`` (later bars, later volume, ETF revisions
and new dates, funding / open-interest / perp-volume / basis rows observed or
available after ``t``, late market-cap revisions and later liquidation days),
and every ledger row and intent must be byte-identical. The converse controls
show the property is not vacuous: an input available exactly at ``t`` does
change the decision record.
"""

from __future__ import annotations

import hashlib
from dataclasses import replace
from datetime import timedelta
from decimal import Decimal

import pytest

from btc_predictor.research_backtest.entry_composer import OUTCOME_ARM_ENTRY, EntryComposer
from btc_predictor.tests.rbt004_composer_fixtures import CONFIG, DAY, HOUR, Scenario, trending_close, utc

SEEDS = range(4)
INSTANTS = (utc(2023, 6, 1), utc(2024, 4, 8), utc(2024, 4, 9))


def _factor(seed: int, family: str, index: int) -> Decimal:
    """A deterministic multiplier in [0.5, 1.5) for one record of one family."""

    digest = hashlib.sha256(f"rbt004-pit:{seed}:{family}:{index}".encode()).digest()
    return Decimal(500 + int.from_bytes(digest[:4], "big") % 1000) / Decimal(1000)


def _scaled_bar(bar, factor):
    return replace(bar, open=bar.open * factor, high=bar.high * factor, low=bar.low * factor, close=bar.close * factor, volume=bar.volume * factor)


def perturb_after(inputs, t, seed):
    """Every family changed or extended only where its modelled availability is after ``t``."""

    dataset = inputs.dataset
    shared = dataset.shared_snapshot
    price = tuple(_scaled_bar(bar, _factor(seed, "price", index)) if bar.ingested_at > t else bar for index, bar in enumerate(dataset.price_bars))
    volume = tuple(
        replace(bar, volume=bar.volume * _factor(seed, "volume", index)) if bar.ingested_at > t else bar for index, bar in enumerate(shared.volume_bars)
    )
    visible_flows = [flow for flow in shared.etf_flows if flow.available_at <= t]
    revisions = tuple(
        replace(
            flow,
            flow_usd=flow.flow_usd * _factor(seed, "etf", index) - Decimal(index),
            aum_usd=flow.aum_usd * _factor(seed, "aum", index),
            revision=f"pit-revision-{seed}",
            available_at=t + HOUR * (1 + index % 30),
        )
        for index, flow in enumerate(visible_flows[-60:])
    )
    future_flows = tuple(
        replace(flow, flow_usd=flow.flow_usd * _factor(seed, "etf-future", index)) if flow.available_at > t else flow
        for index, flow in enumerate(shared.etf_flows)
    )
    funding = tuple(
        replace(row, funding_rate=row.funding_rate * _factor(seed, "funding", index)) if row.observation_time > t else row
        for index, row in enumerate(shared.funding_rates)
    )
    late_funding = tuple(
        replace(row, observation_time=row.observation_time - 3 * HOUR, available_at=t + HOUR * (1 + index), funding_rate=row.funding_rate * 5)
        for index, row in enumerate(row for row in shared.funding_rates if t - 10 * DAY < row.observation_time <= t)
    )
    oi = tuple(
        replace(row, open_interest=row.open_interest * _factor(seed, "oi", index)) if row.observation_time > t else row
        for index, row in enumerate(shared.open_interest)
    )
    late_oi = tuple(
        replace(row, observation_time=row.observation_time - 5 * HOUR, available_at=t + 2 * HOUR, open_interest=row.open_interest * 3)
        for row in shared.open_interest
        if t - 8 * DAY < row.observation_time <= t
    )
    perp = tuple(
        replace(row, notional_usd=row.notional_usd * _factor(seed, "perp", index)) if row.observation_time > t else row
        for index, row in enumerate(shared.perp_volumes)
    )
    late_perp = tuple(
        replace(row, observation_time=row.observation_time - timedelta(minutes=30), available_at=t + HOUR)
        for row in shared.perp_volumes
        if t - 20 * HOUR < row.observation_time <= t
    )
    basis = tuple(
        replace(row, annualized_basis_rate=row.annualized_basis_rate * _factor(seed, "basis", index)) if row.available_at > t else row
        for index, row in enumerate(inputs.futures_basis)
    )
    late_basis = tuple(
        replace(row, observation_time=row.observation_time - 7 * HOUR, available_at=t + 3 * HOUR, annualized_basis_rate=row.annualized_basis_rate * 4)
        for row in inputs.futures_basis
        if t - 9 * DAY < row.observation_time <= t
    )
    caps = tuple(
        replace(cap, market_cap_usd=cap.market_cap_usd * _factor(seed, "cap", index)) if cap.available_at > t else cap
        for index, cap in enumerate(inputs.market_caps)
    )
    late_caps = tuple(
        replace(cap, market_cap_usd=cap.market_cap_usd * 2, provider="fixture-marketcap-revision", available_at=t + HOUR)
        for cap in inputs.market_caps
        if cap.available_at <= t and cap.observation_time > t - 10 * DAY
    )
    liquidations = tuple(
        replace(item, liquidation_percentile=(item.liquidation_percentile * _factor(seed, "liq", index)).min(Decimal(100)))
        if item.available_at > t and item.liquidation_percentile is not None
        else item
        for index, item in enumerate(inputs.liquidation_percentiles)
    )
    snapshot = replace(
        shared,
        volume_bars=volume,
        etf_flows=(*future_flows, *revisions),
        funding_rates=(*funding, *late_funding),
        open_interest=(*oi, *late_oi),
        perp_volumes=(*perp, *late_perp),
    )
    return replace(
        inputs,
        dataset=replace(dataset, price_bars=price, shared_snapshot=snapshot),
        futures_basis=(*basis, *late_basis),
        market_caps=(*caps, *late_caps),
        liquidation_percentiles=liquidations,
    )


def _ledger(inputs, instants):
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    records = []
    for instant in instants:
        decision = composer.decide(instant)
        composer.record(decision)
        records.append((decision.row.as_record(), decision.intent))
    return records


@pytest.fixture(scope="module")
def inputs():
    return Scenario().build()


@pytest.fixture(scope="module")
def baseline(inputs):
    return _ledger(inputs, INSTANTS)


@pytest.mark.parametrize("seed", SEEDS)
def test_inputs_available_after_t_never_change_a_decision(inputs, baseline, seed):
    t = INSTANTS[-1]
    perturbed = perturb_after(inputs, t, seed)
    # the perturbation really touches every family after t
    assert perturbed.dataset.price_bars != inputs.dataset.price_bars
    assert len(perturbed.dataset.shared_snapshot.etf_flows) > len(inputs.dataset.shared_snapshot.etf_flows)
    assert len(perturbed.futures_basis) > len(inputs.futures_basis) and len(perturbed.market_caps) > len(inputs.market_caps)
    assert _ledger(perturbed, INSTANTS) == baseline


@pytest.fixture(scope="module")
def armed():
    inputs = Scenario(end=utc(2024, 4, 15), close_at=trending_close(daily_drift=0.0003, cycle_days=80.0, cycle_amplitude=0.07)).build()
    instants = tuple(utc(2024, 3, 25) + offset * DAY for offset in range(7))
    return inputs, instants, _ledger(inputs, instants)


@pytest.mark.parametrize("seed", [0, 1])
def test_an_armed_entry_is_unchanged_by_later_inputs(armed, seed):
    inputs, instants, records = armed
    assert records[-1][0]["outcome"] == OUTCOME_ARM_ENTRY and records[-1][1] is not None
    assert _ledger(perturb_after(inputs, instants[-1], seed), instants) == records


# --- converse controls: inputs available exactly at t are read ------------------------------------


def test_the_decision_bar_closing_at_t_is_read(inputs, baseline):
    t = INSTANTS[-1]
    changed = tuple(_scaled_bar(bar, Decimal("1.01")) if bar.ingested_at == t else bar for bar in inputs.dataset.price_bars)
    row = _ledger(replace(inputs, dataset=replace(inputs.dataset, price_bars=changed)), INSTANTS)[-1][0]
    assert row != baseline[-1][0]


def test_a_liquidation_day_available_exactly_at_t_is_read(inputs, baseline):
    t = INSTANTS[-1]
    changed = tuple(
        replace(item, liquidation_percentile=Decimal("99")) if item.available_at == t else item for item in inputs.liquidation_percentiles
    )
    assert any(item.available_at == t for item in inputs.liquidation_percentiles)
    row = _ledger(replace(inputs, liquidation_percentiles=changed), INSTANTS)[-1][0]
    assert row["components"]["volatility"] != baseline[-1][0]["components"]["volatility"]


def test_a_funding_settlement_at_t_is_read(inputs, baseline):
    t = INSTANTS[-1]
    shared = inputs.dataset.shared_snapshot
    changed = tuple(replace(row, funding_rate=row.funding_rate * 4) if row.observation_time == t else row for row in shared.funding_rates)
    assert any(row.observation_time == t and row.available_at <= t for row in shared.funding_rates)
    perturbed = replace(inputs, dataset=replace(inputs.dataset, shared_snapshot=replace(shared, funding_rates=changed)))
    row = _ledger(perturbed, INSTANTS)[-1][0]
    assert row["features"]["FUNDING_7D_AVG"] != baseline[-1][0]["features"]["FUNDING_7D_AVG"]
