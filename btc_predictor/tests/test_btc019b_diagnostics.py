from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btc_predictor.data import OhlcvBar
from btc_predictor.research.btc019b_diagnostics import (
    DIAGNOSTIC_ATR_GRID,
    ISOLATED_PROVIDER_OUTLIER,
    MISSING_PROVIDER,
    PERSISTENT_PROVIDER_DISLOCATION,
    ECONOMICALLY_EQUIVALENT,
    _closest_close_pair,
    _group_degraded_episodes,
    _primary_degraded_classification,
    _state_consequence,
    diagnostic_protocol,
)


def _bar(provider: str, close: str) -> OhlcvBar:
    timestamp = datetime(2020, 1, 1, tzinfo=UTC)
    value = Decimal(close)
    return OhlcvBar(
        timestamp=timestamp,
        exchange=provider,
        symbol="BTC/USD",
        timeframe="1h",
        open=value,
        high=value,
        low=value,
        close=value,
        volume=Decimal("1"),
        provider=provider,
        ingested_at=timestamp + timedelta(hours=1),
    )


def test_protocol_preserves_v1_and_predeclares_full_atr_grid() -> None:
    protocol = diagnostic_protocol()

    assert protocol["frozen_v1_invariants"]["formula_changed"] is False
    assert protocol["frozen_v1_invariants"]["approval_thresholds_changed"] is False
    assert protocol["frozen_v1_invariants"]["v1_decision"] == "RESEARCH_INCONCLUSIVE"
    assert protocol["atr_material_grid"] == [str(value) for value in DIAGNOSTIC_ATR_GRID]


def test_closest_close_pair_identifies_isolated_provider() -> None:
    pair, outlier, pair_dispersion, outlier_dispersion = _closest_close_pair(
        {
            "bitstamp": _bar("bitstamp", "100"),
            "coinbase": _bar("coinbase", "100.1"),
            "bitfinex": _bar("bitfinex", "104"),
        }
    )

    assert pair == ("bitstamp", "coinbase")
    assert outlier == "bitfinex"
    assert pair_dispersion is not None and pair_dispersion < Decimal("50")
    assert outlier_dispersion is not None and outlier_dispersion > Decimal("50")


def test_primary_classification_has_deterministic_precedence() -> None:
    assert _primary_degraded_classification(
        missing=True,
        pair=None,
        outlier=None,
        genuine_volatility=True,
        discontinuity=True,
        persistent=True,
        range_disagreement=True,
    ) == MISSING_PROVIDER
    assert _primary_degraded_classification(
        missing=False,
        pair=("bitstamp", "coinbase"),
        outlier="bitfinex",
        genuine_volatility=False,
        discontinuity=False,
        persistent=True,
        range_disagreement=False,
    ) == PERSISTENT_PROVIDER_DISLOCATION
    assert _primary_degraded_classification(
        missing=False,
        pair=("bitstamp", "coinbase"),
        outlier="bitfinex",
        genuine_volatility=False,
        discontinuity=False,
        persistent=False,
        range_disagreement=False,
    ) == ISOLATED_PROVIDER_OUTLIER


def test_episode_grouping_uses_strictly_contiguous_hours() -> None:
    start = datetime(2020, 1, 1, tzinfo=UTC)
    records = [
        {"timestamp": start},
        {"timestamp": start + timedelta(hours=1)},
        {"timestamp": start + timedelta(hours=3)},
    ]

    episodes = _group_degraded_episodes(records)

    assert [len(item) for item in episodes] == [2, 1]
    assert records[0]["episode_id"] == records[1]["episode_id"]
    assert records[2]["episode_id"] != records[1]["episode_id"]


def test_unchanged_episode_is_economically_equivalent() -> None:
    state = {
        "weekly": {},
        "swings": {},
        "breakout_reclaim": {},
        "daily_atr": {},
    }

    consequence = _state_consequence(
        state,
        state,
        actual_paths=(),
        counter_paths={},
        relevant_probe_indexes=(),
        trailing_atr={},
    )

    assert consequence["classification"] == ECONOMICALLY_EQUIVALENT
