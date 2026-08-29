from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from btc_predictor.data import OhlcvBar
from btc_predictor.research.btc019_empirical import build_weekly_trade_path_probes


def test_weekly_trade_path_probes_use_only_pre_entry_stop_history() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)
    bars = tuple(
        OhlcvBar(
            timestamp=start + timedelta(hours=offset),
            exchange="bitstamp",
            symbol="BTC/USD",
            timeframe="1h",
            open=Decimal("100"),
            high=Decimal("101"),
            low=(
                Decimal("90")
                if offset == 24
                else Decimal("80")
                if offset == 24 * 40
                else Decimal("99")
            ),
            close=Decimal("100"),
            volume=Decimal("1"),
            provider="bitstamp",
            ingested_at=start + timedelta(days=90),
        )
        for offset in range(24 * 84)
    )

    probes = build_weekly_trade_path_probes(
        bars,
        start=start,
        end=start + timedelta(days=84) - timedelta(hours=1),
    )

    assert len(probes) == 5
    assert probes[0].entry_time == start + timedelta(days=28)
    assert probes[0].exit_time == start + timedelta(days=56) - timedelta(hours=1)
    assert probes[0].stop_level == Decimal("90")
    assert probes[2].stop_level == Decimal("80")
    assert all(probe.direction == "long" for probe in probes)


def test_weekly_trade_path_probe_parameters_must_be_positive() -> None:
    start = datetime(2024, 1, 1, tzinfo=UTC)

    with pytest.raises(ValueError, match="must be positive"):
        build_weekly_trade_path_probes(
            (),
            start=start,
            end=start,
            path_days=0,
        )
