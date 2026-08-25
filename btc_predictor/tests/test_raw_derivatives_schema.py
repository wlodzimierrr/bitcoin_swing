from btc_predictor.db import (
    FUNDING_RATES_PRIMARY_KEY,
    FUTURES_BASIS_PRIMARY_KEY,
    LIQUIDATIONS_PRIMARY_KEY,
    OPEN_INTEREST_PRIMARY_KEY,
    PERP_VOLUME_PRIMARY_KEY,
    funding_rates,
    futures_basis,
    liquidations,
    open_interest,
    perp_volume,
)


def test_derivatives_tables_preserve_exchange_source_and_point_in_time_columns() -> None:
    for table in (funding_rates, open_interest, futures_basis, liquidations, perp_volume):
        assert "exchange" in table.c
        assert "provider" in table.c
        assert "source" in table.c
        assert "observation_time" in table.c
        assert "available_at" in table.c
        assert "ingested_at" in table.c


def test_derivatives_tables_have_expected_primary_keys() -> None:
    assert FUNDING_RATES_PRIMARY_KEY == (
        "observation_time",
        "exchange",
        "symbol",
        "instrument",
        "provider",
    )
    assert OPEN_INTEREST_PRIMARY_KEY == FUNDING_RATES_PRIMARY_KEY
    assert FUTURES_BASIS_PRIMARY_KEY == (
        "observation_time",
        "exchange",
        "symbol",
        "instrument",
        "expiry",
        "provider",
    )
    assert LIQUIDATIONS_PRIMARY_KEY == (
        "observation_time",
        "exchange",
        "symbol",
        "timeframe",
        "side",
        "provider",
    )
    assert PERP_VOLUME_PRIMARY_KEY == (
        "observation_time",
        "exchange",
        "symbol",
        "timeframe",
        "provider",
    )
