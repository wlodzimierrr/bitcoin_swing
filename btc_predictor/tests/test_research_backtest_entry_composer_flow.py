"""RBT-004: Flow under ETF_CORE, the closure table and the per-window fund universe.

CVD is absent (policy V7 section 5), so the Rulebook section 6.2 fallback
``ETF_CORE`` applies. Every ETF flow window receives the loaded
``US_EQUITY_MARKET_CLOSURE_TABLE_V1`` as ``market_holidays``, and each window
passes the funds whose first US trading date is on or before its first
included publication date (policy V7 section 5, adopted verbatim). The three
flow z-scores follow ``UNIFORM_ZSCORE_V1`` over the native publication-day
series. Synthetic deterministic fixtures only.
"""

from __future__ import annotations

import ast
from dataclasses import replace
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

import pytest

from btc_predictor.features.flow import FLOW_MODEL_ETF_CORE, etf_flow_acceleration, five_day_etf_flow, twenty_day_etf_flow
from btc_predictor.features.rolling import rolling_zscore
from btc_predictor.research.us_equity_market_closures import COVERAGE_END, COVERAGE_START, TABLE_VERSION, load_closures
from btc_predictor.research_backtest import entry_composer
from btc_predictor.research_backtest.entry_composer import EntryComposer, EntryComposerError, EntryComposerInputs, EtfFundLaunch
from btc_predictor.tests.rbt004_composer_fixtures import (
    CONFIG,
    DEFAULT_FUNDS,
    HOUR,
    Scenario,
    recording,
    us_trading_days,
    utc,
    with_inputs,
)

# T: the latest visible publication day is D = 2024-04-05 (T+2 availability),
# and its 20-day window spans the listed Good Friday closure 2024-03-29.
T = utc(2024, 4, 9)
D = date(2024, 4, 5)
GOOD_FRIDAY = date(2024, 3, 29)
EARLY = utc(2024, 2, 20)  # its history reaches windows that start before the first launch
PRE_ETF = utc(2023, 12, 1)
FIRST_LAUNCH = date(2024, 1, 11)
TABLE = load_closures(COVERAGE_START, COVERAGE_END)
LAUNCHES = {spec.fund: spec.launch for spec in DEFAULT_FUNDS}
NAMES = ("five_day_etf_flow", "twenty_day_etf_flow", "etf_flow_acceleration", "calculate_flow_score", "spot_perp_cvd_spread", "detect_bullish_reset")


@pytest.fixture(scope="module")
def run():
    inputs = Scenario().build()
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    decisions = {}
    with recording(*NAMES) as calls:
        for label, instant in (("pre_etf", PRE_ETF), ("early", EARLY), ("t", T)):
            start = {name: len(calls[name]) for name in NAMES}
            decision = composer.decide(instant)
            composer.record(decision)
            decisions[label] = (decision.row, {name: calls[name][start[name] :] for name in NAMES})
    return {"inputs": inputs, "composer": composer, "decisions": decisions}


def _visible(inputs, instant):
    return tuple(flow for flow in inputs.dataset.shared_snapshot.etf_flows if flow.available_at <= instant)


def _window_calls(calls):
    return [("5", call) for call in calls["five_day_etf_flow"]] + [("20", call) for call in calls["twenty_day_etf_flow"]]


# --- the closure table ----------------------------------------------------------------------


def test_every_etf_window_call_receives_the_loaded_closure_table(run):
    assert run["composer"].closure_table_version == TABLE_VERSION == "US_EQUITY_MARKET_CLOSURE_TABLE_V1"
    assert run["composer"]._market_holidays == TABLE and GOOD_FRIDAY in TABLE
    count = 0
    for _, calls in run["decisions"].values():
        for _, call in _window_calls(calls):
            assert call.kwargs["market_holidays"] == TABLE
            count += 1
    assert count > 50  # every window of three decisions, plus the anchor and calendar pages


def test_every_etf_window_call_site_passes_market_holidays():
    tree = ast.parse(Path(entry_composer.__file__).read_text(encoding="utf-8"))
    sites = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in ("five_day_etf_flow", "twenty_day_etf_flow")
    ]
    assert len(sites) == 4
    for node in sites:
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        assert "market_holidays" in keywords, ast.unparse(node)
        assert "_market_holidays" in ast.unparse(keywords["market_holidays"]) or ast.unparse(keywords["market_holidays"]) == "holidays"


def test_a_window_spanning_a_listed_holiday_is_complete_only_with_the_table(run):
    visible = _visible(run["inputs"], T)
    funds = tuple(sorted(LAUNCHES))
    with_table = twenty_day_etf_flow(visible, as_of=T, funds=funds, market_holidays=TABLE, end_date=D)
    without = twenty_day_etf_flow(visible, as_of=T, funds=funds, end_date=D)
    assert with_table.complete and with_table.reason_codes == ()
    assert GOOD_FRIDAY not in with_table.included_observation_dates
    assert with_table.included_observation_dates[0] > date(2024, 3, 1)
    assert "ETF_FLOW_INPUT_MISSING" in without.reason_codes and not without.complete
    assert GOOD_FRIDAY in without.included_observation_dates
    # the composer's own 20-day window at T is that complete one
    row, calls = run["decisions"]["t"]
    window = next(call.result for call in calls["twenty_day_etf_flow"] if call.kwargs.get("end_date") == D and call.kwargs.get("funds"))
    assert window.complete and window.included_observation_dates == with_table.included_observation_dates
    assert row.owner_reason_codes["etf_flow_20d"]["complete"] is True
    assert row.components["flow"] is not None


# --- the per-window fund universe --------------------------------------------------------------


def test_each_window_passes_the_funds_launched_by_its_first_publication_date(run):
    included_arkb, excluded_arkb = 0, 0
    for _, calls in run["decisions"].values():
        for size, call in _window_calls(calls):
            funds = call.kwargs.get("funds", ())
            end = call.kwargs.get("end_date")
            if not funds:
                # Only the owner's latest-date anchor and the publication-calendar
                # pages run without a fund list; their window values are never consumed.
                assert (size, end is None) in (("5", True), ("20", False)), call.kwargs
                continue
            first = call.result.included_observation_dates[0]
            assert funds == tuple(sorted(fund for fund, launch in LAUNCHES.items() if launch <= first))
            assert first >= FIRST_LAUNCH
            if "ARKB" in funds:
                included_arkb += 1
            elif first < LAUNCHES["ARKB"]:
                excluded_arkb += 1
    assert included_arkb and excluded_arkb


def test_windows_before_the_first_launch_are_undefined_never_invented(run):
    row, calls = run["decisions"]["early"]
    firsts = [call.result.included_observation_dates[0] for _, call in _window_calls(calls) if call.kwargs.get("funds")]
    assert firsts and min(firsts) >= FIRST_LAUNCH
    # The 20-day series has too few defined pre-launch-free windows by then.
    flow = {item.component: item.causes for item in row.unevaluable}["flow"]
    assert "FLOW_Z_ETF_NORM_20D_INSUFFICIENT_HISTORY" in flow
    assert row.unaccounted == ()


def test_pre_etf_instants_call_no_window_and_record_the_missing_inputs(run):
    row, calls = run["decisions"]["pre_etf"]
    assert calls["five_day_etf_flow"] == [] and calls["twenty_day_etf_flow"] == []
    assert row.outcome == entry_composer.OUTCOME_STRUCTURALLY_UNEVALUABLE and "FLOW_INCOMPLETE" in row.reasons
    flow = {item.component: item.causes for item in row.unevaluable}["flow"]
    for input_id in ("FLOW_Z_ETF_NORM_5D", "FLOW_Z_ETF_NORM_20D", "FLOW_Z_FLOW_ACCEL"):
        assert f"{input_id}_INPUT_MISSING" in flow
    assert row.unaccounted == ()


def test_a_flow_row_for_a_fund_without_a_launch_record_is_refused(run):
    inputs = with_inputs(run["inputs"], etf_fund_launches=tuple(item for item in run["inputs"].etf_fund_launches if item.fund != "ARKB"))
    composer = EntryComposer(inputs, strategy_config=CONFIG)
    with pytest.raises(EntryComposerError) as refused:
        composer.decide(T)
    assert refused.value.code == "INPUT_REFUSED" and "ARKB" in str(refused.value)
    # before ARKB has any visible row, the missing record cannot matter
    assert composer.decide(utc(2024, 2, 1)).row.outcome in entry_composer.OUTCOMES


def test_fund_launch_records_need_source_evidence_and_are_unique(run):
    with pytest.raises(EntryComposerError):
        EtfFundLaunch("IBIT", date(2024, 1, 11), " ")
    with pytest.raises(EntryComposerError):
        EntryComposerInputs(dataset=run["inputs"].dataset, etf_fund_launches=(*run["inputs"].etf_fund_launches, run["inputs"].etf_fund_launches[0]))


# --- UNIFORM_ZSCORE_V1 over the native publication-day series ------------------------------------


def _independent_flow_series(inputs, instant):
    """ETF_NORM_5D, ETF_NORM_20D and FLOW_ACCEL at each publication day, newest first."""

    visible = _visible(inputs, instant)
    latest = max(flow.observation_date for flow in visible)
    days = list(reversed(us_trading_days(date(2023, 12, 1), latest)))
    series = []
    for index, day in enumerate(days):
        values = {}
        windows = {}
        for size, owner in (("5", five_day_etf_flow), ("20", twenty_day_etf_flow)):
            span = days[index : index + int(size)]
            if len(span) < int(size):
                windows[size] = None
                continue
            funds = tuple(sorted(fund for fund, launch in LAUNCHES.items() if launch <= span[-1]))
            windows[size] = owner(visible, as_of=instant, funds=funds, market_holidays=TABLE, end_date=day) if funds else None
            values[size] = windows[size].normalized_flow if windows[size] is not None and windows[size].complete else None
        accel = None
        if windows["5"] is not None and windows["20"] is not None:
            result = etf_flow_acceleration(windows["5"], windows["20"])
            accel = result.acceleration if result.complete else None
        series.append({"day": day, "5": values.get("5"), "20": values.get("20"), "accel": accel})
    return latest, series


def _uniform(series_newest_first, key):
    current = series_newest_first[0][key]
    history = [item[key] for item in series_newest_first[1:] if item[key] is not None][:20]
    history = list(reversed(history))
    if current is None or len(history) < 20 or all(value == history[0] for value in history):
        return None
    return rolling_zscore((*history, current), window=20, min_periods=20, sample=False)[-1]


@pytest.fixture(scope="module")
def independent(run):
    return _independent_flow_series(run["inputs"], T)


def test_the_flow_zscores_follow_the_uniform_rule_on_publication_days(run, independent):
    latest, series = independent
    assert latest == D and series[0]["day"] == D
    row, calls = run["decisions"]["t"]
    (score_call,) = calls["calculate_flow_score"]
    flow_input = score_call.args[0]
    assert flow_input.etf_norm_5_zscore == _uniform(series, "5") is not None
    assert flow_input.etf_norm_20_zscore == _uniform(series, "20") is not None
    assert flow_input.flow_accel_zscore == _uniform(series, "accel") is not None
    assert row.features["ETF_NORM_5D"] == series[0]["5"]
    assert row.features["ETF_NORM_20D"] == series[0]["20"]
    assert row.features["FLOW_ACCEL"] == series[0]["accel"]
    # a listed holiday is never a publication day D'
    window_ends = {call.kwargs.get("end_date") for _, call in _window_calls(calls)}
    assert GOOD_FRIDAY not in window_ends and date(2024, 3, 30) not in window_ends


def test_flow_is_etf_core_with_cvd_absent(run):
    row, calls = run["decisions"]["t"]
    (score_call,) = calls["calculate_flow_score"]
    assert score_call.args[0].cvd_spread_zscore is None and score_call.args[0].spot_dominance_zscore is None
    assert score_call.result.flow_model == FLOW_MODEL_ETF_CORE and score_call.result.complete
    assert "FLOW_SCORE_P1_INPUT_MISSING" in score_call.result.reason_codes
    (cvd_call,) = calls["spot_perp_cvd_spread"]
    assert cvd_call.args[0] == () and cvd_call.kwargs == {"as_of": T}
    assert row.features["CVD_SPREAD"] is None and row.features["SPOT_DOMINANCE"] is None
    assert entry_composer.accounted_cause("FLOW_SCORE_P1_INPUT_MISSING") is not None
    assert row.unaccounted == ()


def test_setup_b_reads_the_native_flow_accel_history(run, independent):
    _, series = independent
    _, calls = run["decisions"]["t"]
    (reset_call,) = calls["detect_bullish_reset"]
    lookback = int(CONFIG.setup_requirements.bullish_reset["flow_accel_improving_days"])
    expected = tuple(item["accel"] for item in reversed(series[: lookback + 1]))
    assert tuple(reset_call.args[0].flow_accel_history) == expected
    assert len(expected) == lookback + 1


# --- point in time ------------------------------------------------------------------------------


def test_a_revision_available_after_t_never_changes_the_flow(run):
    inputs = run["inputs"]
    shared = inputs.dataset.shared_snapshot
    originals = [flow for flow in shared.etf_flows if flow.observation_date in (date(2024, 4, 4), date(2024, 3, 20)) and flow.fund == "IBIT"]
    revisions = tuple(
        replace(flow, flow_usd=flow.flow_usd * 7 + Decimal("12345"), revision="late-revision", available_at=T + HOUR) for flow in originals
    )
    revised = replace(inputs, dataset=replace(inputs.dataset, shared_snapshot=replace(shared, etf_flows=(*shared.etf_flows, *revisions))))
    baseline = EntryComposer(inputs, strategy_config=CONFIG)
    candidate = EntryComposer(revised, strategy_config=CONFIG)
    at_t = (baseline.decide(T).row, candidate.decide(T).row)
    assert at_t[0].as_record() == at_t[1].as_record()
    # once the revision is available it is the owner's latest revision (the test is not vacuous)
    later = T + timedelta(days=1)
    assert baseline.decide(later).row.features["ETF_NORM_5D"] != candidate.decide(later).row.features["ETF_NORM_5D"]
