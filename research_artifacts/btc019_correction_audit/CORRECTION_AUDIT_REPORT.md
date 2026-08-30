# BTC-019 Correctness / Reproducibility Audit

Namespace: `research_artifacts/btc019_correction_audit/`

This directory holds **corrected** BTC-019 outputs regenerated after the
implementation audit. It is a separate correction namespace. The original frozen
artifacts under `research_artifacts/btc019/PRICE_SOURCE_POLICY_V1/` are
untouched and retain their original checksums and provenance.

Source data: `data/btc019/2023-01-01_2025-12-31` (already collected, immutable).
The sealed `BTC_REFERENCE_COMPOSITE_V2` validation period
(2015-07-20T21:00Z through 2019-11-30T23:00Z) was **not** opened.

## Fix inventory

| # | Defect | Impact class | Historical effect |
|---|---|---|---|
| 1 | `reviewed_at` / `decided_at` / `checked_at` were not bounded by `as_of` | `BTC019_ONLY` | `as_of` and 4 synthesized `checked_at` values change |
| 2 | Optional providers contaminated every V1 decision metric | `BTC019_ONLY` | none (latent — only required providers were supplied) |
| 3 | Revision selection kept the earliest revision; equal-`ingested_at` conflicts were input-order dependent | `BTC019_ONLY` | none (latent — no revisions in the collected set) |
| 4 | Isolated-wick classification used bare unique-extreme with no ATR materiality | `BTC019_ONLY` | 7 of 25 wick rows reclassified |
| 5 | Trade-path probes could be silently truncated by the comparison window | `BTC019_ONLY` | none (latent — probes were already inside the window) |
| 6 | p95 indexing | n/a — already correct | none (nearest-rank Decimal already in use; now pinned by tests) |
| 7 | Empty provider series lost `exchange`/`symbol` provenance | `BTC019_ONLY` | none (latent — every provider returned bars) |
| 8 | Breakout/reclaim identity collapsed distinct levels sharing a confirmation week | `BTC019_ONLY` | breakout count 2→4 |

No fix is classified `SHARED_IMPLEMENTATION_NO_PROTOCOL_CHANGE` or
`FROZEN_PROTOCOL_SEMANTICS_AFFECTED`. All edits are confined to
`price_source_policy.py` and the BTC-019 driver `btc019_empirical.py`. The only
symbol shared with composite research is `TradePathProbe`, whose definition and
`as_record()` are unchanged.

## Changed historical metrics

| Artifact | Metric | Old | New | Reason | Gate affected | Decision impact |
|---|---|---|---|---|---|---|
| `comparison_report.json` | `as_of` | `2026-08-29T13:55:40.343607+00:00` | `2026-08-29T14:13:30+00:00` | Fix 1: evaluation instant now dominates recorded provenance | none | none |
| `comparison_report.json` | `provider_access_diagnostics[0,1,3,4].checked_at` | `…13:55:40.343607+00:00` | `…14:13:30+00:00` | Fix 1: synthesized diagnostics stamped with the evaluation instant | none | none |
| `comparison_report.json` | `breakout_difference_count` | 2 | 4 | Fix 8: two breakouts sharing a confirmation week were previously merged | `breakout_disagreement_rate` (V2, not yet evaluated) | none |
| `comparison_report.json` | `breakout_reclaim_difference_count` | 11 | 13 | Follows from `breakout_difference_count` | none | none |
| `comparison_report.json` | `divergence_tiers[tier 3].event_count` | 22 | 24 | Follows from `breakout_difference_count` | none | none |
| `canonical_source_decision.json` | `tier_event_counts["3"]` | 22 | 24 | Same as above | none | none |
| `comparison_report.json` | `cross_venue_wick_diagnostics[*].candidate_flags` | 22 `WICK_ANOMALY_CANDIDATE`, 3 `CROSS_VENUE_CONFIRMED` | 18 `WICK_ANOMALY_CANDIDATE`, 7 unflagged | Fix 4: ATR materiality | none | none |

Explicitly **unchanged**: `overlap_bar_count` (26292), `missing_bar_rate` per
provider, `close`/`high`/`low`/`extreme_wick`/`daily_return`/`atr` divergence
distributions, `swing_high_difference_count` (4), `swing_low_difference_count`
(7), `swing_level_difference_count` (11), `reclaim_difference_count` (9),
`stop_touch_difference_count` (3), `mfe_divergence`, `mae_divergence`,
`top_divergence_events`, `manual_reviews`, `policy_decision_ready` (true),
`reason_codes` (empty), and the decision **REJECTED**.

The set of 25 top wick rows is unchanged in `(timestamp, provider_id)`; only
their flags moved.

### Why the wick reclassification is a correction, not a suppression

The old rule flagged any venue holding a unique extreme, so ordinary
independent-venue dispersion produced false positives, and it attributed the
flag to the wrong venue in three cases.

- `2023-10-23T22:00Z` — Bitfinex was flagged `WICK_ANOMALY_CANDIDATE` because
  its low was **$1.11** below Coinbase's (0.012 ATR). Meanwhile Coinbase's high
  stood **1.77 ATR** above the pack and was *not* flagged. After the fix,
  Coinbase is flagged and Bitfinex is not.
- `2023-08-17T21:00Z` — Bitstamp held neither extreme yet was labelled
  `CROSS_VENUE_CONFIRMED`; Bitfinex's low was 3.45 ATR below the pack. After the
  fix, Bitfinex is flagged and Bitstamp is not.
- `2025-02-25T07:00Z` — Bitfinex held the unique maximum high but only 0.10 ATR
  above the pack. Correctly unflagged after the fix.

All 25 rows were re-derived independently from the persisted provider OHLC and
agree with the documented rule.

## Threshold and numerical policy

- `WICK_ANOMALY_ATR_THRESHOLD = Decimal("0.30")`, version
  `PRICE_SOURCE_WICK_ANOMALY_V1`. It reuses the established cross-venue
  high/low materiality threshold already frozen as
  `reference_composite.DEFAULT_TWO_PROVIDER_RANGE_DISAGREEMENT_ATR` and as the
  V2 protocol's `quality_thresholds.high_low_or_range_disagreement_atr`. A test
  pins the two constants together so they cannot drift apart.
- Percentiles use nearest-rank, `rank = ceil(p * n)`, `index = rank - 1`,
  computed in `Decimal` with `ROUND_CEILING`. This was already the convention in
  `price_source_policy`, `btc019_empirical`, and `reference_composite_empirical`;
  it is now pinned by exact tests at n = 1, 2, 10, 20, 100.
- All comparisons in the touched code are `Decimal`-to-`Decimal` and exact.
  `DECISION_COMPARISON_V1` governs migrated `float64`-to-Decimal threshold
  comparisons and is unmodified; no raw float comparison was introduced.

## Conclusions revalidated

| Conclusion | Status after fixes |
|---|---|
| Bitstamp sole canonical | **REJECTED** — unchanged, reproduced from corrected code |
| `BTC_REFERENCE_COMPOSITE_V1` | **RESEARCH_INCONCLUSIVE** — unchanged |
| BTC-019B | **MIXED** — unchanged |
| `BTC_REFERENCE_COMPOSITE_V2` | **FROZEN_RESEARCH_PROTOCOL** — unchanged, definition SHA-256 recomputes to `bc312f3e…6106a` |
| `PRICE_SOURCE_POLICY_V1` | **UNCHANGED** |
| BTC-019 | **IN PROGRESS** |

## Known limitation carried forward

The original BTC-019 run recorded manual review and canonical-decision
provenance approximately 18 minutes after its recorded `as_of`, because `as_of`
was derived from the maximum bar `ingested_at` rather than from the evaluation
instant. No market information after the data cutoff entered the study — human
review necessarily follows collection — but the recorded provenance was not
internally consistent with the recorded point-in-time boundary. The driver now
derives the evaluation instant so that it dominates all recorded provenance;
widening it exposes no additional observations because every collected bar was
already ingested before the earlier cutoff.
