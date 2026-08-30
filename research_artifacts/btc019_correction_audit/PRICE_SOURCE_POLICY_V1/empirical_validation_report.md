# BTC-019 Empirical Price-Source Validation

Policy: `PRICE_SOURCE_POLICY_V1`

Decision: **REJECTED Bitstamp as the V1 canonical reference source**

## Scope

- Historical period: `2023-01-01T00:00:00+00:00` through `2025-12-31T23:00:00+00:00`
- Synchronized common bars: `26292`
- Bitstamp missing rate: `0`
- Coinbase missing rate: `0.0003041362530413625304136253041`
- Bitfinex missing rate: `0.0001520681265206812652068126521`

## Strategy Sensitivity

- Swing pairwise disagreement: `11/66` (`0.1666666666666666666666666667`)
- Breakout pairwise disagreement: `2/16` (`0.125`)
- Reclaim pairwise disagreement: `9/18` (`0.5`)
- Stop-touch pairwise disagreement: `3/298` (`0.01006711409395973154362416107`)
- Validator-consensus stop hits missed by Bitstamp: `1`
- Maximum MFE difference: `0.0243290043290043290043290044`
- Maximum MAE difference: `0.04605450328899157707792711626`

## Decision

Bitstamp had perfect continuity and no material persistent close-price bias versus Coinbase, but source choice changed strategy-relevant outcomes. Bitstamp alone created one swing and its breakout, failed to create a validator-consensus swing/reclaim sequence, and missed a 107270 stop that both validators hit during the 10 October 2025 selloff. Maximum MFE and MAE sensitivities were 2.433 and 4.605 percentage points. Those rare but consequential range differences make the isolated-wick risk unacceptable for a sole V1 canonical structural reference without a separate cross-venue confirmation or composite policy.

## Limitations

The study covers three calendar years and three spot venues. The 149 weekly 28-day probes measure source sensitivity rather than a full strategy backtest. Root causes of persistent Coinbase and Bitfinex gaps remain UNKNOWN. Coin Metrics history was entitlement-unavailable and was not substituted.
