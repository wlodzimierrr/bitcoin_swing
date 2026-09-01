import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from btc_predictor.config import load_strategy_config
from btc_predictor.portfolio import (
    ENTER,
    PENDING_ENTRY,
    apply_position_event,
    start_position_lifecycle,
)
from btc_predictor.reporting import (
    ADVISORY_JSON_DOCUMENT_TYPES,
    ADVISORY_JSON_ENCODING,
    ADVISORY_JSON_FEATURE_ID,
    ADVISORY_JSON_MEDIA_TYPE,
    ADVISORY_JSON_SCHEMA_VERSION,
    AdvisoryJsonResult,
    advisory_json_from_record,
    advisory_source_from_json,
    render_json_output,
    render_position_management_report,
    render_recommendation,
)
from btc_predictor.risk import calculate_risk_at_stop, calculate_trailing_stop


CONFIG = load_strategy_config()
METADATA = CONFIG.run_metadata()
EVALUATED_AT = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _recommendation():
    return render_recommendation(
        {
            "recommendation_id": 172,
            "run_id": 52,
            "evaluation_time": EVALUATED_AT,
            "symbol": "BTC-USD",
            "timeframe": "1d",
            "regime": "BULL",
            "setup": "BULLISH_RESET",
            "direction": "long",
            "trend_score": Decimal("82"),
            "regime_score": Decimal("72"),
            "flow_score": Decimal("78"),
            "positioning_score": Decimal("74"),
            "volatility_score": Decimal("68"),
            "structure_score": Decimal("86"),
            "entry_conviction": Decimal("84"),
            "hold_score": Decimal("76"),
            "add_score": Decimal("81"),
            "entry_zone_lower": None,
            "entry_zone_upper": None,
            "invalidation_level": None,
            "initial_stop": None,
            "rr_ratio": None,
            "risk_fraction_nav": None,
            "risk_amount": None,
            "suggested_notional": None,
            "action": "HOLD",
        },
        (
            {
                "recommendation_id": 172,
                "reason_rank": 0,
                "code": "TREND_12W_POSITIVE",
                "source_component": "trend",
                "severity": "info",
                "detail": "Twelve-week momentum remains positive.",
            },
        ),
        predictor_run={
            "run_id": 52,
            "evaluation_time": EVALUATED_AT,
            **METADATA,
        },
        strategy_config=CONFIG,
    )


def _management_report():
    lifecycle = start_position_lifecycle(
        symbol="BTC-USD",
        state=PENDING_ENTRY,
        config_metadata=METADATA,
    )
    lifecycle = apply_position_event(
        lifecycle,
        event=ENTER,
        event_time=EVALUATED_AT - timedelta(days=1),
        quantity="1",
        price="100000",
        stop_price="90000",
    )
    trailing = calculate_trailing_stop(
        direction="long",
        previous_stop="90000",
        current_price="105000",
        evaluated_at=EVALUATED_AT,
        config_metadata=METADATA,
    )
    risk = calculate_risk_at_stop(
        lifecycle.tranches,
        stop_price="90000",
        nav="2000000",
        config=CONFIG,
    )
    return render_position_management_report(
        advisory=_recommendation(),
        lifecycle=lifecycle,
        trailing_stop=trailing,
        risk_at_stop=risk,
        mark_price="105000",
        marked_at=EVALUATED_AT,
        mark_source_id="coinmetrics:BTC-USD:1d",
    )


def test_json_contract_and_recommendation_document_are_stable() -> None:
    result = render_json_output(_recommendation())
    document = json.loads(result.body)

    assert isinstance(result, AdvisoryJsonResult)
    assert result.feature_id == ADVISORY_JSON_FEATURE_ID
    assert result.schema_version == ADVISORY_JSON_SCHEMA_VERSION
    assert result.media_type == ADVISORY_JSON_MEDIA_TYPE
    assert result.document_type == "recommendation"
    assert result.complete is True
    assert document["schema_version"] == ADVISORY_JSON_SCHEMA_VERSION
    assert document["encoding"] == ADVISORY_JSON_ENCODING
    assert document["payload"]["config_metadata"] == METADATA
    assert document["payload"]["recommendation"]["entry_conviction"] == "84"
    assert document["payload"]["reasons"][0]["code"] == "TREND_12W_POSITIVE"
    assert " " not in result.body[: result.body.index('"BTC SWING SIGNAL')]


def test_position_management_document_retains_every_nested_source() -> None:
    result = render_json_output(_management_report())
    payload = json.loads(result.body)["payload"]

    assert result.document_type == "position_management"
    assert payload["advisory"]["recommendation"]["action"] == "HOLD"
    assert payload["lifecycle"]["state"] == "OPEN_INITIAL"
    assert payload["trailing_stop"]["reason_codes"] == [
        "TRAILING_STOP_NO_NEW_STRUCTURE",
    ]
    assert payload["risk_at_stop"]["risk_fraction_nav"] == "0.005"
    assert payload["metrics"]["unrealized_pnl"] == "5000.0"
    assert payload["mark"]["marked_at"] == EVALUATED_AT.isoformat()


@pytest.mark.parametrize("source_factory", (_recommendation, _management_report))
def test_encoding_is_deterministic_and_standalone_json_restores_source(
    source_factory,
) -> None:
    source = source_factory()
    first = render_json_output(source)
    second = render_json_output(source_factory())

    assert first.body == second.body
    assert first.body == json.dumps(
        json.loads(first.body),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
    assert advisory_source_from_json(first.body) == source


@pytest.mark.parametrize("source_factory", (_recommendation, _management_report))
def test_persistence_record_replays_exactly(source_factory) -> None:
    result = render_json_output(source_factory())
    record = result.as_record()
    restored = advisory_json_from_record(record)

    assert restored == result
    assert restored.as_record() == record
    assert record["source_feature_id"] == result.source.feature_id
    assert record["config_metadata"] == METADATA
    assert record["source_reason_codes"] == list(result.source.reason_codes)


def test_noncanonical_or_invalid_json_is_rejected() -> None:
    body = render_json_output(_recommendation()).body

    with pytest.raises(ValueError, match="canonical"):
        advisory_source_from_json(json.dumps(json.loads(body), indent=2))
    with pytest.raises(ValueError, match="valid JSON"):
        advisory_source_from_json("{not-json")
    with pytest.raises(ValueError, match="root must be an object"):
        advisory_source_from_json("[]")


def test_envelope_schema_encoding_and_document_type_are_validated() -> None:
    document = json.loads(render_json_output(_recommendation()).body)

    changed_schema = deepcopy(document)
    changed_schema["schema_version"] = "V2"
    with pytest.raises(ValueError, match="schema_version"):
        advisory_source_from_json(_canonical(changed_schema))

    changed_encoding = deepcopy(document)
    changed_encoding["encoding"]["decimal"] = "float"
    with pytest.raises(ValueError, match="encoding conventions"):
        advisory_source_from_json(_canonical(changed_encoding))

    changed_type = deepcopy(document)
    changed_type["document_type"] = "trade_execution"
    with pytest.raises(ValueError, match="document_type"):
        advisory_source_from_json(_canonical(changed_type))


def test_record_rejects_body_document_and_metadata_drift() -> None:
    record = render_json_output(_recommendation()).as_record()

    changed_document = deepcopy(record)
    changed_document["document"]["payload"]["body"] = "changed"
    with pytest.raises(ValueError, match="does not match"):
        advisory_json_from_record(changed_document)

    changed_metadata = deepcopy(record)
    changed_metadata["config_metadata"]["parameter_set_id"] = "other"
    with pytest.raises(ValueError, match="does not match"):
        advisory_json_from_record(changed_metadata)


def test_unsupported_source_is_rejected() -> None:
    with pytest.raises(TypeError, match="source must be"):
        render_json_output({})  # type: ignore[arg-type]


def _canonical(document) -> str:
    return json.dumps(
        document,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    )
