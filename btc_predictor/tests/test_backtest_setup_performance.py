"""BTC-184: deterministic setup-level performance comparison."""

from copy import deepcopy
from datetime import timedelta
from decimal import ROUND_HALF_EVEN, Decimal

import pytest

from btc_predictor.backtest import (
    OPEN_TRADE_MARK_POLICY_VERSION,
    PROFIT_FACTOR_AVAILABLE,
    PROFIT_FACTOR_NO_CLOSED_LOSSES,
    PROFIT_FACTOR_NO_CLOSED_TRADES,
    SETUP_BUCKETS,
    SETUP_METRIC_POLICY_VERSION,
    SETUP_PERFORMANCE_FEATURE_ID,
    SETUP_PERFORMANCE_POLICY_VERSION,
    SETUP_PERFORMANCE_REASON_CODES,
    SETUP_PROFIT_FACTOR_POLICY_VERSION,
    restore_setup_performance_report,
    run_regime_performance_breakdown,
    run_setup_performance_report,
    setup_performance_report_from_breakdown,
)
from btc_predictor.data import OhlcvBar
from btc_predictor.features.setup import BULL_TREND_CONTINUATION_SETUP
from btc_predictor.tests.test_backtest_regime_performance import (
    CONFIG,
    METADATA,
    START,
    contexts_for,
    enter_then_exit,
    feature_context,
    stand_aside,
    validation,
)


EXPONENT = Decimal("1E-12")


def contexts_with_setups(source):
    contexts = contexts_for(source)
    return tuple(
        feature_context(
            fold_number=context.fold_number,
            source_id=context.entry_source_id,
            decision_at=context.decision_at,
            setup=setup,
        )
        for context, setup in zip(contexts, SETUP_BUCKETS, strict=True)
    )


def priced_bar(day: int, price: str) -> OhlcvBar:
    timestamp = START + timedelta(days=day)
    value = Decimal(price)
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC-USD",
        timeframe="1d",
        open=value,
        high=value + Decimal("0.1"),
        low=value - Decimal("0.1"),
        close=value,
        volume=Decimal("100"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(days=1),
    )


def test_setup_report_policies_and_metric_vocabularies_are_versioned() -> None:
    assert SETUP_PERFORMANCE_FEATURE_ID == "SETUP_LEVEL_PERFORMANCE_REPORT"
    assert SETUP_PERFORMANCE_POLICY_VERSION == "SETUP_LEVEL_PERFORMANCE_REPORT_V1"
    assert SETUP_METRIC_POLICY_VERSION == "CLOSED_NET_OUTCOME_METRICS_V1"
    assert SETUP_PROFIT_FACTOR_POLICY_VERSION.endswith("_V1")
    assert OPEN_TRADE_MARK_POLICY_VERSION == "FOLD_END_MARK_TO_MARKET_V1"


def test_report_emits_all_four_setups_in_canonical_order_and_reconciles() -> None:
    source = validation()
    contexts = contexts_with_setups(source)

    report = run_setup_performance_report(source, contexts)

    assert tuple(item.setup for item in report.setups) == SETUP_BUCKETS
    assert tuple(item.trade_count for item in report.setups) == (1, 1, 1, 1)
    assert report.trade_count == source.trade_count == 4
    assert sum((item.total_pnl for item in report.setups), Decimal("0")) == sum(
        (fold.total_pnl for fold in source.folds), Decimal("0")
    )
    assert report.config_metadata == METADATA == CONFIG.run_metadata()
    assert report.validation_id == source.validation_id


def test_open_trades_are_marked_but_excluded_from_closed_quality_metrics() -> None:
    source = validation()
    report = run_setup_performance_report(source, contexts_for(source))
    trend = report.performance(BULL_TREND_CONTINUATION_SETUP)

    assert trend.open_trade_count == trend.trade_count == 4
    assert trend.marked_unrealized_pnl != 0
    assert trend.closed_trade_expectancy is None
    assert trend.closed_trade_win_rate is None
    assert trend.profit_factor is None
    assert trend.profit_factor_status == PROFIT_FACTOR_NO_CLOSED_TRADES
    assert trend.average_closed_holding_days is None
    assert "SETUP_PERFORMANCE_OPEN_TRADES_MARKED" in report.reason_codes


def test_closed_metrics_use_authoritative_net_outcomes_costs_r_and_holding_days() -> None:
    source = validation(
        enter_then_exit,
        bars=tuple(priced_bar(day, str(100 + day)) for day in range(11)),
        test_periods=4,
    )
    report = run_setup_performance_report(source, contexts_for(source))
    trend = report.performance(BULL_TREND_CONTINUATION_SETUP)
    trades = tuple(trade for fold in source.folds for trade in fold.result.trades)
    net = sum((trade.net_pnl for trade in trades), Decimal("0"))

    assert trend.closed_trade_count == len(trades) == 2
    assert trend.realized_net_pnl == net
    assert trend.closed_trade_expectancy == (net / Decimal(2)).quantize(
        EXPONENT, rounding=ROUND_HALF_EVEN
    )
    assert trend.fees == sum((trade.fees for trade in trades), Decimal("0"))
    assert trend.funding == sum((trade.funding for trade in trades), Decimal("0"))
    assert trend.total_costs == trend.fees + trend.funding
    assert trend.summed_r_multiple == sum(
        (trade.r_multiple for trade in trades if trade.r_multiple is not None),
        Decimal("0"),
    )
    assert trend.average_closed_holding_days == (
        sum((trade.holding_days for trade in trades), Decimal("0")) / Decimal(2)
    ).quantize(EXPONENT, rounding=ROUND_HALF_EVEN)
    assert trend.profit_factor is None
    assert trend.profit_factor_status == PROFIT_FACTOR_NO_CLOSED_LOSSES
    assert "SETUP_PERFORMANCE_PROFIT_FACTOR_UNBOUNDED" in report.reason_codes


def test_profit_factor_uses_closed_net_profit_over_absolute_closed_net_loss() -> None:
    prices = (
        "100", "100", "100", "100", "100", "110", "110",
        "110", "110", "100", "100",
    )
    source = validation(
        enter_then_exit,
        bars=tuple(priced_bar(day, price) for day, price in enumerate(prices)),
        test_periods=4,
    )
    report = run_setup_performance_report(source, contexts_for(source))
    trend = report.performance(BULL_TREND_CONTINUATION_SETUP)

    assert trend.winning_closed_trades == 1
    assert trend.losing_closed_trades == 1
    assert trend.profit_factor_status == PROFIT_FACTOR_AVAILABLE
    assert trend.profit_factor == (
        trend.closed_net_profit / abs(trend.closed_net_loss)
    ).quantize(EXPONENT, rounding=ROUND_HALF_EVEN)
    assert trend.average_winner is not None and trend.average_winner > 0
    assert trend.average_loser is not None and trend.average_loser < 0


def test_no_trade_report_retains_missing_metrics_and_declared_rows() -> None:
    source = validation(stand_aside)
    report = run_setup_performance_report(source, ())

    assert report.trade_count == 0
    assert tuple(item.setup for item in report.setups) == SETUP_BUCKETS
    assert all(item.trade_count == 0 for item in report.setups)
    assert all(item.closed_trade_expectancy is None for item in report.setups)
    assert all(item.mean_r_multiple is None for item in report.setups)
    assert all(
        item.profit_factor_status == PROFIT_FACTOR_NO_CLOSED_TRADES
        for item in report.setups
    )
    assert "SETUP_PERFORMANCE_NO_TRADES" in report.reason_codes
    assert report.reason_codes[-1] == "SETUP_PERFORMANCE_COMPLETE"


def test_existing_breakdown_and_direct_entry_points_have_exact_parity() -> None:
    source = validation()
    contexts = contexts_for(source)
    breakdown = run_regime_performance_breakdown(source, contexts)

    direct = run_setup_performance_report(source, contexts)
    reused = setup_performance_report_from_breakdown(breakdown)

    assert direct == reused
    assert direct.source_breakdown == breakdown
    assert direct.source_breakdown.breakdown("setup").buckets[0].trade_count == (
        direct.setups[0].trade_count
    )


def test_report_is_deterministic_under_context_input_order_and_restores() -> None:
    source = validation()
    contexts = contexts_for(source)

    first = run_setup_performance_report(source, contexts)
    second = run_setup_performance_report(source, tuple(reversed(contexts)))

    assert first == second
    assert first.report_id == second.report_id
    assert first.evidence_digest == second.evidence_digest
    assert restore_setup_performance_report(first.as_record()) == first
    assert set(first.reason_codes).issubset(SETUP_PERFORMANCE_REASON_CODES)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda row: row["setups"][0].__setitem__("trade_count", 999),
        lambda row: row["setups"][0].__setitem__("profit_factor", "999"),
        lambda row: row.__setitem__("metric_policy_version", "changed"),
        lambda row: row.__setitem__("validation_id", "changed"),
        lambda row: row["source_breakdown"]["contexts"][0].__setitem__(
            "setup", "changed"
        ),
    ],
)
def test_restore_rejects_derived_policy_identity_and_nested_tampering(mutate) -> None:
    source = validation()
    report = run_setup_performance_report(source, contexts_for(source))
    record = deepcopy(report.as_record())
    mutate(record)

    with pytest.raises((TypeError, ValueError)):
        restore_setup_performance_report(record)


def test_performance_lookup_and_breakdown_builder_fail_closed() -> None:
    source = validation(stand_aside)
    report = run_setup_performance_report(source, ())

    with pytest.raises(KeyError):
        report.performance("UNKNOWN_SETUP")
    with pytest.raises(TypeError, match="RegimePerformanceBreakdown"):
        setup_performance_report_from_breakdown(source)  # type: ignore[arg-type]
