"""Deterministic synthetic fixtures for the volatility and Rulebook 24 hard-flag roots.

Group g4 of the RBT-002 correction R1 runtime cross-check. Every thunk builds
its own synthetic inputs from ``btc_predictor`` owner types and the stdlib
(``Decimal``, ``datetime`` with ``UTC``), calls exactly one decision-path root
(upstream inputs may come from other roots), and returns that root's result.

- No randomness, no wall clock, no network, no database, no file reads inside
  a thunk. All timestamps are fixed and lie inside 2021-01-01..2024-12-31.
- The champion configuration is loaded once, at import time, with
  ``load_strategy_config()`` so the thunks trace only the decision path and
  not the TOML loader. The Rulebook 24 flag thresholds come from
  ``StrategyConfig.volatility_flags``; ``config_metadata`` is
  ``StrategyConfig.run_metadata()``. Thresholds the champion configuration
  does not carry (orderliness, volatility-score, RV / percentile windows) stay
  at the owner defaults, which are the champion's values.
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from btc_predictor.config.strategy import load_strategy_config
from btc_predictor.data import OhlcvBar
from btc_predictor.features import volatility as vol


_CHAMPION = load_strategy_config()
_STRESS = _CHAMPION.volatility_flags.stress
_CAPITULATION = _CHAMPION.volatility_flags.capitulation
_EUPHORIA = _CHAMPION.volatility_flags.euphoria

_ROOT = "btc_predictor.features.volatility."


# --- synthetic builders ---------------------------------------------------------------


def _metadata() -> dict[str, str]:
    return dict(_CHAMPION.run_metadata())


def _daily_bar(timestamp: datetime, close: Decimal) -> OhlcvBar:
    # A canonical 1d bar, ingested five minutes after it closes.
    return OhlcvBar(
        timestamp=timestamp,
        exchange="coinbase",
        symbol="BTC/USD",
        timeframe="1d",
        open=close,
        high=close + Decimal("150"),
        low=close - Decimal("150"),
        close=close,
        volume=Decimal("1200"),
        provider="coinbase",
        ingested_at=timestamp + timedelta(days=1, minutes=5),
    )


_BAR_START = datetime(2023, 3, 1, tzinfo=UTC)


def _wavy_close(index: int) -> Decimal:
    # Deterministic, strictly positive closes with a slow drift and a
    # non-constant oscillation, so close-to-close returns are non-zero.
    return (
        Decimal("28000")
        + Decimal(20 * index)
        + Decimal(150 * ((index * 7) % 13))
        - Decimal(90 * (index % 5))
    )


def _daily_bars(count: int, *, flat: bool = False) -> tuple[OhlcvBar, ...]:
    return tuple(
        _daily_bar(
            _BAR_START + timedelta(days=index),
            Decimal("30000") if flat else _wavy_close(index),
        )
        for index in range(count)
    )


def _as_of_after(bars: tuple[OhlcvBar, ...]) -> datetime:
    # One hour after the last bar is both closed and ingested.
    return bars[-1].timestamp + timedelta(days=1, hours=1)


def _rv20_history(count: int) -> tuple[vol.RealizedVolatilityResult, ...]:
    """``count`` complete daily RV_20 owner results ending 2023-02-04."""

    start = datetime(2022, 1, 1, tzinfo=UTC)
    return tuple(
        vol.RealizedVolatilityResult(
            feature_id=vol.RV_20_FEATURE_ID,
            observation_time=start + timedelta(days=index),
            window_days=20,
            annualization_periods=vol.DEFAULT_REALIZED_VOLATILITY_ANNUALIZATION_PERIODS,
            realized_volatility=Decimal("0.35") + Decimal((index * 17) % 41) / Decimal("100"),
            return_count=20,
            source_bar_count=21 + index,
            complete=True,
            reason_codes=(),
        )
        for index in range(count)
    )


# --- realized_volatility_from_daily_bars ---------------------------------------------


def rv_complete() -> vol.RealizedVolatilityResult:
    """Main path: 80 closed daily bars, champion RV_20 window -> complete."""

    bars = _daily_bars(80)
    return vol.realized_volatility_from_daily_bars(bars, as_of=_as_of_after(bars), window_days=20)


def rv_insufficient_history() -> vol.RealizedVolatilityResult:
    """Refusal: 10 bars for RV_60 -> REALIZED_VOLATILITY_INSUFFICIENT_HISTORY."""

    bars = _daily_bars(10)
    return vol.realized_volatility_from_daily_bars(bars, as_of=_as_of_after(bars), window_days=60)


def rv_input_missing() -> vol.RealizedVolatilityResult:
    """Refusal: no bar has closed by ``as_of`` -> REALIZED_VOLATILITY_INPUT_MISSING."""

    bars = _daily_bars(30)
    return vol.realized_volatility_from_daily_bars(
        bars, as_of=_BAR_START + timedelta(hours=12), window_days=7
    )


# --- volatility_percentile -----------------------------------------------------------


def percentile_complete() -> vol.VolatilityPercentileResult:
    """Main path: 400 RV_20 results; 399 prior observations >= the 365 minimum."""

    results = _rv20_history(400)
    as_of = results[-1].observation_time + timedelta(hours=6)
    return vol.volatility_percentile(results, as_of=as_of)


def percentile_insufficient_history() -> vol.VolatilityPercentileResult:
    """Refusal: 40 RV_20 results -> VOL_PERCENTILE_INSUFFICIENT_HISTORY."""

    results = _rv20_history(40)
    as_of = results[-1].observation_time + timedelta(hours=6)
    return vol.volatility_percentile(results, as_of=as_of)


def percentile_input_missing() -> vol.VolatilityPercentileResult:
    """Refusal: an RV_20 produced by the owner with too few bars carries no value
    -> VOL_PERCENTILE_INPUT_MISSING."""

    bars = _daily_bars(12)
    as_of = _as_of_after(bars)
    current = vol.realized_volatility_from_daily_bars(bars, as_of=as_of, window_days=20)
    return vol.volatility_percentile((current,), as_of=as_of)


# --- volatility_compression_ratio_from_results ---------------------------------------


def _rv_results(bars: tuple[OhlcvBar, ...]) -> tuple[vol.RealizedVolatilityResult, ...]:
    as_of = _as_of_after(bars)
    return tuple(
        vol.realized_volatility_from_daily_bars(bars, as_of=as_of, window_days=window_days)
        for window_days in vol.REALIZED_VOLATILITY_WINDOWS
    )


def compression_complete() -> vol.VolatilityCompressionRatioResult:
    """Main path: RV_7 / RV_20 / RV_60 from 80 bars -> complete RV7/RV60 ratio."""

    return vol.volatility_compression_ratio_from_results(_rv_results(_daily_bars(80)))


def compression_input_missing() -> vol.VolatilityCompressionRatioResult:
    """Refusal: 30 bars complete RV_7 and RV_20 but not RV_60
    -> VOL_COMPRESSION_INPUT_MISSING."""

    return vol.volatility_compression_ratio_from_results(_rv_results(_daily_bars(30)))


def compression_zero_denominator() -> vol.VolatilityCompressionRatioResult:
    """Refusal: a flat close series gives RV_60 = 0 -> VOL_COMPRESSION_ZERO_DENOMINATOR."""

    return vol.volatility_compression_ratio_from_results(_rv_results(_daily_bars(80, flat=True)))


# --- calculate_orderliness_score -----------------------------------------------------


def orderliness_complete() -> vol.OrderlinessScoreResult:
    """Main path: every input inside the orderly band -> complete score 100."""

    return vol.calculate_orderliness_score(
        vol.OrderlinessScoreInput(
            range_percentile=Decimal("55"),
            downside_return=Decimal("-0.03"),
            liquidation_percentile=Decimal("40"),
            volatility_percentile=Decimal("50"),
        ),
        config_metadata=_metadata(),
    )


def orderliness_input_missing() -> vol.OrderlinessScoreResult:
    """Refusal: no liquidation percentile -> ORDERLINESS_INPUT_MISSING, score None."""

    return vol.calculate_orderliness_score(
        vol.OrderlinessScoreInput(
            range_percentile=Decimal("55"),
            downside_return=Decimal("-0.03"),
            liquidation_percentile=None,
            volatility_percentile=Decimal("50"),
        ),
        config_metadata=_metadata(),
    )


def orderliness_disorderly() -> vol.OrderlinessScoreResult:
    """Complete but penalised: extreme range and a liquidation cascade."""

    return vol.calculate_orderliness_score(
        vol.OrderlinessScoreInput(
            range_percentile=Decimal("96"),
            downside_return=Decimal("-0.09"),
            liquidation_percentile=Decimal("93"),
            volatility_percentile=Decimal("70"),
        ),
        config_metadata=_metadata(),
    )


# --- calculate_volatility_score ------------------------------------------------------


def volatility_score_complete() -> vol.VolatilityScoreResult:
    """Main path: compression, orderliness and percentile present -> complete."""

    return vol.calculate_volatility_score(
        vol.VolatilityScoreInput(
            compression_ratio=Decimal("0.82"),
            orderliness_score=Decimal("80"),
            volatility_percentile=Decimal("42"),
        ),
        config_metadata=_metadata(),
    )


def volatility_score_input_missing() -> vol.VolatilityScoreResult:
    """Refusal: no orderliness score and no percentile
    -> VOLATILITY_SCORE_INPUT_MISSING and VOLATILITY_REGIME_UNKNOWN, score None."""

    return vol.calculate_volatility_score(
        vol.VolatilityScoreInput(
            compression_ratio=Decimal("0.82"),
            orderliness_score=None,
            volatility_percentile=None,
        ),
        config_metadata=_metadata(),
    )


def volatility_score_from_upstream_owners() -> vol.VolatilityScoreResult:
    """Main path composed from upstream roots: RV -> compression ratio, and the
    orderliness owner's score, as the composer wires them."""

    compression = vol.volatility_compression_ratio_from_results(_rv_results(_daily_bars(80)))
    orderliness = vol.calculate_orderliness_score(
        vol.OrderlinessScoreInput(
            range_percentile=Decimal("60"),
            downside_return=Decimal("-0.02"),
            liquidation_percentile=Decimal("35"),
            volatility_percentile=Decimal("30"),
        ),
        config_metadata=_metadata(),
    )
    return vol.calculate_volatility_score(
        vol.VolatilityScoreInput(
            compression_ratio=compression.compression_ratio,
            orderliness_score=orderliness.score,
            volatility_percentile=Decimal("30"),
        ),
        config_metadata=_metadata(),
    )


# --- Rulebook 24 hard flags ----------------------------------------------------------


def _stress(inputs: vol.StressFlagInput) -> vol.StressFlagResult:
    return vol.calculate_stress_flag(
        inputs,
        volatility_percentile_min=_STRESS.volatility_percentile_min,
        liquidation_percentile_min=_STRESS.liquidation_percentile_min,
        downside_return_min=_STRESS.downside_return_min,
        funding_abs_zscore_min=_STRESS.funding_abs_zscore_min,
        basis_abs_zscore_min=_STRESS.basis_abs_zscore_min,
        max_exposure_multiplier=_STRESS.max_exposure_multiplier,
        block_new_trades=_STRESS.block_new_trades,
        config_metadata=_metadata(),
    )


def stress_flagged() -> vol.StressFlagResult:
    """Main path: complete inputs with extreme volatility and a liquidation
    cascade -> flagged, complete."""

    return _stress(
        vol.StressFlagInput(
            volatility_percentile=Decimal("97"),
            liquidation_percentile=Decimal("96"),
            downside_return=Decimal("-0.06"),
            funding_zscore=Decimal("1.2"),
            basis_zscore=Decimal("-0.8"),
            systemic_shock=False,
        )
    )


def stress_input_missing() -> vol.StressFlagResult:
    """Refusal: missing liquidation percentile and systemic-shock input
    -> STRESS_INPUT_MISSING, incomplete, not flagged."""

    return _stress(
        vol.StressFlagInput(
            volatility_percentile=Decimal("60"),
            liquidation_percentile=None,
            downside_return=Decimal("-0.02"),
            funding_zscore=Decimal("0.5"),
            basis_zscore=Decimal("0.4"),
            systemic_shock=None,
        )
    )


def stress_clear() -> vol.StressFlagResult:
    """Complete, not flagged: every input below its stress threshold."""

    return _stress(
        vol.StressFlagInput(
            volatility_percentile=Decimal("50"),
            liquidation_percentile=Decimal("45"),
            downside_return=Decimal("-0.01"),
            funding_zscore=Decimal("0.3"),
            basis_zscore=Decimal("0.2"),
            systemic_shock=False,
        )
    )


def _capitulation(inputs: vol.CapitulationFlagInput) -> vol.CapitulationFlagResult:
    return vol.calculate_capitulation_flag(
        inputs,
        range_percentile_min=_CAPITULATION.range_percentile_min,
        downside_return_min=_CAPITULATION.downside_return_min,
        liquidation_percentile_min=_CAPITULATION.liquidation_percentile_min,
        volatility_percentile_min=_CAPITULATION.volatility_percentile_min,
        funding_zscore_max=_CAPITULATION.funding_zscore_max,
        config_metadata=_metadata(),
    )


def capitulation_flagged() -> vol.CapitulationFlagResult:
    """Main path: severe downside with liquidation and funding-flush
    confirmation -> flagged, complete."""

    return _capitulation(
        vol.CapitulationFlagInput(
            range_percentile=Decimal("97"),
            downside_return=Decimal("-0.15"),
            liquidation_percentile=Decimal("98"),
            volatility_percentile=Decimal("88"),
            funding_zscore=Decimal("-2.5"),
            systemic_shock=False,
        )
    )


def capitulation_input_missing() -> vol.CapitulationFlagResult:
    """Refusal: missing range percentile and funding z-score
    -> CAPITULATION_INPUT_MISSING, incomplete."""

    return _capitulation(
        vol.CapitulationFlagInput(
            range_percentile=None,
            downside_return=Decimal("-0.04"),
            liquidation_percentile=Decimal("50"),
            volatility_percentile=Decimal("55"),
            funding_zscore=None,
            systemic_shock=False,
        )
    )


def capitulation_confirmation_missing() -> vol.CapitulationFlagResult:
    """Complete, not flagged: downside without confirmation
    -> CAPITULATION_CONFIRMATION_MISSING."""

    return _capitulation(
        vol.CapitulationFlagInput(
            range_percentile=Decimal("70"),
            downside_return=Decimal("-0.13"),
            liquidation_percentile=Decimal("60"),
            volatility_percentile=Decimal("65"),
            funding_zscore=Decimal("-0.5"),
            systemic_shock=False,
        )
    )


def _euphoria(inputs: vol.EuphoriaFlagInput) -> vol.EuphoriaFlagResult:
    return vol.calculate_euphoria_flag(
        inputs,
        range_percentile_min=_EUPHORIA.range_percentile_min,
        upside_return_min=_EUPHORIA.upside_return_min,
        funding_zscore_min=_EUPHORIA.funding_zscore_min,
        basis_zscore_min=_EUPHORIA.basis_zscore_min,
        oi_intensity_percentile_min=_EUPHORIA.oi_intensity_percentile_min,
        volatility_percentile_min=_EUPHORIA.volatility_percentile_min,
        config_metadata=_metadata(),
    )


def euphoria_flagged() -> vol.EuphoriaFlagResult:
    """Main path: upside extension with overheated funding and OI intensity
    -> flagged, complete."""

    return _euphoria(
        vol.EuphoriaFlagInput(
            range_percentile=Decimal("90"),
            upside_return=Decimal("0.18"),
            funding_zscore=Decimal("2.6"),
            basis_zscore=Decimal("1.5"),
            oi_intensity_percentile=Decimal("97"),
            volatility_percentile=Decimal("80"),
            systemic_euphoria=False,
        )
    )


def euphoria_input_missing() -> vol.EuphoriaFlagResult:
    """Refusal: missing basis z-score and OI-intensity percentile
    -> EUPHORIA_INPUT_MISSING, incomplete."""

    return _euphoria(
        vol.EuphoriaFlagInput(
            range_percentile=Decimal("60"),
            upside_return=Decimal("0.04"),
            funding_zscore=Decimal("0.7"),
            basis_zscore=None,
            oi_intensity_percentile=None,
            volatility_percentile=Decimal("50"),
            systemic_euphoria=False,
        )
    )


def euphoria_confirmation_missing() -> vol.EuphoriaFlagResult:
    """Complete, not flagged: upside without confirmation
    -> EUPHORIA_CONFIRMATION_MISSING."""

    return _euphoria(
        vol.EuphoriaFlagInput(
            range_percentile=Decimal("70"),
            upside_return=Decimal("0.14"),
            funding_zscore=Decimal("0.9"),
            basis_zscore=Decimal("0.6"),
            oi_intensity_percentile=Decimal("60"),
            volatility_percentile=Decimal("65"),
            systemic_euphoria=False,
        )
    )


FIXTURES: dict[str, tuple[Callable[[], object], ...]] = {
    _ROOT + "calculate_volatility_score": (
        volatility_score_complete,
        volatility_score_input_missing,
        volatility_score_from_upstream_owners,
    ),
    _ROOT + "realized_volatility_from_daily_bars": (
        rv_complete,
        rv_insufficient_history,
        rv_input_missing,
    ),
    _ROOT + "volatility_percentile": (
        percentile_complete,
        percentile_insufficient_history,
        percentile_input_missing,
    ),
    _ROOT + "volatility_compression_ratio_from_results": (
        compression_complete,
        compression_input_missing,
        compression_zero_denominator,
    ),
    _ROOT + "calculate_orderliness_score": (
        orderliness_complete,
        orderliness_input_missing,
        orderliness_disorderly,
    ),
    _ROOT + "calculate_stress_flag": (
        stress_flagged,
        stress_input_missing,
        stress_clear,
    ),
    _ROOT + "calculate_capitulation_flag": (
        capitulation_flagged,
        capitulation_input_missing,
        capitulation_confirmation_missing,
    ),
    _ROOT + "calculate_euphoria_flag": (
        euphoria_flagged,
        euphoria_input_missing,
        euphoria_confirmation_missing,
    ),
}


# --- RBT-002 R1 runtime cross-check -------------------------------------------------------

import functools as _functools  # noqa: E402

import pytest as _pytest  # noqa: E402

from btc_predictor.research_backtest import input_census as _input_census  # noqa: E402


@_functools.cache
def _census() -> _input_census.DecisionPathCensus:
    return _input_census.discover_decision_path()


@_pytest.mark.parametrize(
    "root, index",
    [(root, index) for root, thunks in sorted(FIXTURES.items()) for index in range(len(thunks))],
)
def test_the_static_census_contains_everything_this_root_traces(root: str, index: int) -> None:
    """Run the root on its synthetic fixture under sys.setprofile: every
    btc_predictor function entered and dataclass constructed must be in the
    static census, and the root itself must have run."""

    result, traced = _input_census.trace_owner_calls(FIXTURES[root][index])
    assert root in traced.functions
    assert _input_census.uncovered_traced(_census(), traced) == {"functions": [], "dataclasses": []}
    if index == 0 and hasattr(result, "complete"):
        assert result.complete is True
