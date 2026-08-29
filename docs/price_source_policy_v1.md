# BTC Price-Source Policy V1

Policy identifier: `PRICE_SOURCE_POLICY_V1`

Validation status: **Bitstamp candidate rejected by empirical validation**

## Provider Roles

| Role | Provider | Display instrument | API instrument | Required for V1 |
| --- | --- | --- | --- | --- |
| Rejected canonical candidate and retained raw OHLCV source | Bitstamp | `BTC/USD` | `btcusd` | Yes |
| Independent validation | Coinbase Exchange | `BTC-USD` | `BTC-USD` | Yes |
| Independent validation | Bitfinex | `BTC/USD` | `tBTCUSD` | Yes |
| Optional institutional reference benchmark | Coin Metrics Community | `BTC/USD` | `btc-usd` | No |
| Noncanonical sanity check | yfinance | `BTC-USD` | `BTC-USD` | No |

Bitstamp is not an approved permanent reference source. The persisted BTC-019
decision rejects it as the sole V1 structural reference after real evidence
review. Its raw-data role does not promote it to strategy-canonical status, and
the reference-price role remains separate from execution-venue selection.

Historical fallback splicing is prohibited in V1. Provider outages remain
explicit gaps. Any future policy that permits substitution must use a new
version and retain source provenance on every affected record.

## Reproducible Validation

`btc_predictor.research.compare_price_sources` consumes point-in-time `1h`
`OhlcvBar` histories. A report is decision-ready only when:

- Bitstamp, Coinbase, and Bitfinex have at least two years of synchronized bars;
- missing and duplicate bars are measured per required provider;
- price, indicator, decision, and portfolio sensitivity results are generated;
- an explicit canonical-source approval or rejection is persisted; and
- every reported top divergence event has an exact structured manual review.

The policy-required provider set controls the completion gate. Optional Coin
Metrics or yfinance observations can enrich a report but cannot shorten or
replace the required three-venue overlap.

Each analyzed provider profile persists its policy version, source-role set,
and `fallback_used` state alongside exchange, symbol, timeframe, coverage, and
continuity evidence. Roles live in the versioned research/run record because a
raw candle's factual provider must remain immutable while its policy role may
change in a future version.

## Divergence Tiers

The report separates source divergence by impact:

1. **Price:** close, high, low, wick, continuity, and cross-venue wick evidence.
2. **Indicator:** daily returns and ATR.
3. **Decision:** swing highs/lows and breakout/reclaim outcomes.
4. **Portfolio:** stop touches, MFE, and MAE.

This ordering keeps raw price differences distinct from differences that would
actually alter a strategy decision or portfolio result.

## Cross-Venue Wicks

For each synchronized required-provider bar, research output records the median
high, low, and close. High and low divergence are normalized by trailing ATR
and retained as distributions rather than compared with a permanent hardcoded
threshold.

Diagnostics use these explicit flags:

```text
WICK_ANOMALY_CANDIDATE
CROSS_VENUE_CONFIRMED
CROSS_VENUE_UNCONFIRMED
```

Raw records are immutable. A flagged venue-specific wick is research evidence;
it does not silently rewrite structural levels, stop results, or MFE/MAE.

Manual reviews persist the source OHLC snapshots, cross-venue medians,
ATR-normalized divergence, event classification, affected providers, and
whether the event changes swings, breakouts, reclaims, stops, MFE, MAE, or the
trade outcome.

## Access Diagnostics

Provider-access evidence distinguishes catalog visibility from actual
historical entitlement. Supported outcomes include:

```text
available
not_requested
credentials_unavailable
entitlement_unavailable
provider_outage
api_error
```

Coin Metrics entitlement or credential limits are recorded but do not block
V1. Malformed data from any supplied optional provider still fails validation
instead of being ignored.

## API Practicality

- [Bitstamp OHLC](https://www.bitstamp.net/api/): maximum 1,000 candles per
  request. The documented standard public limits are 400 requests per second
  and 10,000 requests per 10 minutes.
- [Coinbase Exchange candles](https://docs.cdp.coinbase.com/api-reference/exchange-api/rest-api/products/get-product-candles):
  maximum 300 candles per request. Empty no-tick intervals may be omitted.
- [Bitfinex candles](https://docs.bitfinex.com/reference/rest-public-candles):
  use `trade:1h:tBTCUSD`, millisecond `start`/`end`, ascending sort, and at most
  10,000 candles per request. The public endpoint documents 30 requests per
  minute.
- [Coin Metrics API](https://docs.coinmetrics.io/api/v4/): preserve access and
  entitlement diagnostics. V1 does not require historical pair-candle access.
- [yfinance download API](https://ranaroussi.github.io/yfinance/reference/yfinance.functions.html):
  intraday history is limited and is restricted to noncanonical research
  checks.

## Empirical Decision

The persisted study covers `2023-01-01 00:00 UTC` through
`2025-12-31 23:00 UTC`, with 26,292 synchronized common bars. Bitstamp had no
missing bars and no material persistent close-price bias versus Coinbase, but
source choice changed strategy-relevant outcomes:

- Bitstamp alone created one weekly swing and its resulting breakout.
- Both validators created a swing/reclaim sequence that Bitstamp did not.
- Both validators touched a `107270` stop that Bitstamp missed during the
  10 October 2025 selloff.
- Maximum MFE and MAE differences were 2.433 and 4.605 percentage points.

The Bitstamp candidate is therefore **REJECTED**. BTC-019 remains
**IN PROGRESS** because no canonical V1 reference is approved. Coinbase and
Bitfinex require follow-up rather than automatic promotion. A separate
`BTC_REFERENCE_COMPOSITE_V1` research ticket is recommended; no composite or
historical splicing is introduced here.

The full evidence is persisted under
`research_artifacts/btc019/PRICE_SOURCE_POLICY_V1/`.

Coin Metrics historical access is not a mandatory Phase 1 blocker. Promoting
Coin Metrics to canonical status later requires a new policy version and its
own empirical validation.

## Phase 2 Research Note

`BTC_REFERENCE_COMPOSITE_V1` is reserved as a post-Phase-1 research candidate.
It would investigate a robust cross-venue reference built from approved spot
sources after `PRICE_SOURCE_POLICY_V1` has a certified baseline. That research
must define constituent eligibility, robust aggregation, outage behavior,
versioning, provenance, and decision/portfolio sensitivity before promotion.

The composite is not implemented by BTC-019 and must not be used by Phase 1
strategy, backtest, or live-shadow decisions.
