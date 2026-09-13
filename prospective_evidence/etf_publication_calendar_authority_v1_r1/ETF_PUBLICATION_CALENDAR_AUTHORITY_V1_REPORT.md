# ETF_PUBLICATION_CALENDAR_AUTHORITY_V1

- Ticket: `POSTP1-001V2A-R1`
- Definition hash: `b81c1702c65e1e042b7a2f948216305618fd21fabe2e629edc46376882b357af`
- Status: `CORRECTED_FROZEN_PRE_DATA_ETF_CALENDAR_AUTHORITY_AWAITING_REPEAT_XHIGH_REVIEW`
- Classification: `ETF_PUBLICATION_CALENDAR_AUTHORITY_V1_READY_FOR_REPEAT_XHIGH_REVIEW`
- Material children: 10

## Frozen decision

ETF publication-date eligibility is the intersection of the NYSE Arca, Nasdaq,
and Cboe BZX U.S. equity session calendars. Regular and early-close sessions
are expected; full closures are not. Weekends are closed independently. Any
missing, invalid, or unresolved conflicting official evidence fails closed.

Calendar evidence is append-only. A validated HTTPS acquisition binds request/final
URLs, exact response bytes, receipt/acquisition time and a uniquely resolved frozen
source profile. Venue, product scope, coverage, closures and early closes are then
derived by the frozen source-specific parser; caller-authored schedules are refused.

Scientific `available_at` equals response receipt and acquisition time. PIT filtering
precedes revision replay, so future evidence cannot affect an earlier decision.
The normalized AST of every parser/reducer/adapter owner is hash-bound and runtime
replay refuses when the executable semantic identity differs.

## Retained official fixtures (2026-09-13)

Exact compressed response bytes and acquisition provenance for the NYSE, Nasdaq
Trader and Cboe official formats used for certification are retained under
`btc_predictor/tests/fixtures/etf_calendar/`. Their response SHA-256 values are
validated before parser extraction. No fixture is a prospective strategy observation.

## Failed lineage

The failed authority `a1ceb66bc0f6b90066d3da123447ae6e7dd983047adf363790336bfb557db0b9` remains non-authoritative,
non-certified, unused, and preserved in its original artifact directory.

## Material child hashes

| child | definition hash |
| --- | --- |
| `authority_completion_semantic_diff` | `b413d3cd46038672a5ae61a5e97910f3d43c4d0cc206f9eb863620d877af87cc` |
| `common_session_rule` | `e731875421320560284d4727a30ab1f73e20af48fd1547b3203926464950fd8f` |
| `etf_feature_adapter_contract` | `640d3cb22a321d3e8d09affe9890a92251a36ee121b0c7303a61c7cc5e9df3b7` |
| `executable_semantic_manifest` | `e222b18449805ac09131ca44638b7bd22a384d1fbf7d7ea784e9a8852b24bacf` |
| `http_acquisition_schema` | `3a905bd2cf08b529e4ad8fa8b90fa996e6ab748837dbe11e0a9cf88a31ecb416` |
| `normalized_schedule_contract` | `bc84a9e73206382506bbca11b4d832a47ab573934fbdee5b3f00c4fd742fec87` |
| `official_source_profile_registry` | `07e771ac05fb347a78282a1ff5fc8d29044f14b124d8fbf4230a231ac5f8abe8` |
| `pit_revision_rule` | `f2f1e748c64d9f1433e4d544fe844cdfa93524eac97d30c9428eadbbbaa6330f` |
| `source_parser_registry` | `e00ac6259a44aef565d990d3195da09f0b89104b2fc5b7caab04d4a74aead4a2` |
| `venue_session_record_schema` | `75f3948d61513cc4ec5cedb5227797fb52747e0e380e23eaaeae33544d43a29e` |

## Safety

No prospective observation was collected. The failed V2 corpus was not changed
or certified. POSTP1-003R3, POSTP1-004, collection, and BTC-019 remain blocked.
