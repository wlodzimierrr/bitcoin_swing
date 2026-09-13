# ETF_PUBLICATION_CALENDAR_AUTHORITY_V1

- Ticket: `POSTP1-001V2A`
- Definition hash: `a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9`
- Status: `FROZEN_PRE_DATA_ETF_CALENDAR_AUTHORITY_AWAITING_XHIGH_REVIEW`
- Classification: `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_XHIGH_REVIEW`
- Material children: 8

## Frozen decision

ETF publication-date eligibility is the intersection of the NYSE Arca, Nasdaq,
and Cboe BZX U.S. equity session calendars. Regular and early-close sessions
are expected; full closures are not. Weekends are closed independently. Any
missing, invalid, or unresolved conflicting official evidence fails closed.

Calendar evidence is append-only, PIT-selected by `available_at`, and binds exact
official-source bytes, their digest, a normalized schedule digest, and each
replayed venue/date row. Mutable URLs and third-party calendars are not authority.

## Non-persistent official-source verification (2026-09-13)

- NYSE / NYSE Arca: the official Holidays & Trading Hours page identifies
  regular NYSE Arca equity hours, 2026 full-day closures, and the November 27
  and December 24 early closes:
  https://www.nyse.com/trade/hours-calendars
- Nasdaq Trader: the official 2026 U.S. Equity and Options Markets calendar
  identifies closed dates and the two 1:00 p.m. early closes:
  https://www.nasdaqtrader.com/Trader.aspx?id=calendar
- Cboe: the official U.S. Equities Hours & Holidays page identifies BZX regular
  trading hours, full closures, and the two 2026 equities early closes; official
  schedule-update notices provide the frozen extraordinary-change source class:
  https://www.cboe.com/about/hours
- This verification did not persist live pages as calendar evidence. Operational
  rows become authority only through the source-snapshot and extraction contracts.

## Material child hashes

| child | definition hash |
| --- | --- |
| `authority_completion_semantic_diff` | `b6f82f911827f3bab98e29978060828e2d2f848953333e661c9a0734074d5f95` |
| `calendar_extraction_contract` | `a1fda4fef4894ca4bf61710c2812b1338211ef2b3f1069310420e36efd29153f` |
| `common_session_rule` | `e731875421320560284d4727a30ab1f73e20af48fd1547b3203926464950fd8f` |
| `etf_feature_adapter_contract` | `c5f1f2138e5419d53ae673286c28a6d6e6d6d89eb4765adf5b1c181a09a19733` |
| `official_source_snapshot_contract` | `488b3c7616822b17b3276ad4e8dc0f9c3c02519da7e8b86ec9e73d5cd53353a7` |
| `pit_revision_rule` | `41de74e8a2aad084096cfaf79dab45776ed27e91e44169dc44099e3f4cfcef62` |
| `venue_authority_registry` | `74215541a9c19c280348a967668d345ac67dab51e2e69b3a0110a2e649104ccb` |
| `venue_session_record_schema` | `8a0daa3774b1b42d84fe416575ceea2c6f4ef3692da069a6a822fb48c2415a85` |

## Safety

No prospective observation was collected. The failed V2 corpus was not changed
or certified. POSTP1-003R3, POSTP1-004, collection, and BTC-019 remain blocked.
