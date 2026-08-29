# BTC Price-Source Policy V1

Policy identifier: `PRICE_SOURCE_POLICY_V1`

Validation status: **provisional, pending historical evidence**

## Provider Roles

| Role | Provider | Display instrument | API instrument |
| --- | --- | --- | --- |
| Canonical reference price | Coin Metrics Community pair candles | `BTC/USD` | `btc-usd` |
| Primary raw OHLCV | Bitstamp | `BTC/USD` | `btcusd` |
| Secondary validation/live fallback | Coinbase Exchange | `BTC-USD` | `BTC-USD` |
| Noncanonical sanity check | yfinance | `BTC-USD` | `BTC-USD` |

The canonical reference-price role is not an execution-venue selection.
Historical fallback splicing is prohibited in V1. Provider outages remain
explicit gaps. A later policy may allow splicing only by assigning a new policy
version and preserving source provenance on every affected record.

An isolated exchange wick cannot move a structural level, stop result, or
MFE/MAE result unless it is confirmed by the reference and validation sources.

## Reproducible Validation

`btc_predictor.research.compare_price_sources` requires point-in-time `1h`
`OhlcvBar` histories. A report is decision-ready only when:

- Coin Metrics, Bitstamp, and Coinbase have at least two years of synchronized
  bars;
- missing and duplicate bars are measured per provider;
- price, wick, daily-return, ATR, swing, breakout/reclaim, stop-touch, and
  MFE/MAE sensitivity results are generated; and
- every reported top divergence event has an exact structured manual review.

yfinance can contribute short-window sanity checks but does not reduce the
required three-provider overlap window.

## API Practicality

- [Coin Metrics pair candles](https://docs.coinmetrics.io/api/v4/): use
  `next_page_url` pagination. Pair candles are reference-rate candles and do not
  contain exchange volume. Historical access entitlement must be verified.
- [Bitstamp OHLC](https://www.bitstamp.net/api/): maximum 1,000 candles per
  request. The documented standard public limits are 400 requests per second
  and 10,000 requests per 10 minutes.
- [Coinbase Exchange candles](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles):
  maximum 300 candles per request. Empty no-tick intervals may be omitted.
- [yfinance download API](https://ranaroussi.github.io/yfinance/reference/yfinance.functions.html):
  intraday history is limited to the latest 60 days and is restricted to
  noncanonical research checks.

## Current Gate

On 2026-08-29, the unauthenticated Coin Metrics Community catalog advertised
long `btc-usd` `1h` coverage and current pair candles were accessible, but
explicit older timeseries windows returned no rows in this environment.
Bitstamp and Coinbase historical sample windows were accessible.

BTC-019 remains in progress until a credential-backed Coin Metrics history or
equivalent export is supplied, the real multi-year comparison is persisted,
and the top divergence events are reviewed. Until then, the provider selection
above is provisional and must not be treated as a validated permanent strategy
reference-price decision.
