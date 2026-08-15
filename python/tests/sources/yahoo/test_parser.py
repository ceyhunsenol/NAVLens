import json

import pytest
from navlens.sources.yahoo import YahooSecurityPricePayloadError
from navlens.sources.yahoo.parser import parse_yahoo_chart_response


def _body(*, timestamps: object, closes: object) -> bytes:
    payload = {
        "chart": {
            "error": None,
            "result": [
                {
                    "meta": {
                        "symbol": "SYNTH.IS",
                        "currency": "TRY",
                        "exchangeTimezoneName": "Europe/Istanbul",
                    },
                    "timestamp": timestamps,
                    "indicators": {"quote": [{"close": closes}]},
                }
            ],
        }
    }
    return json.dumps(payload).encode()


def test_parses_non_null_daily_closes_and_preserves_order() -> None:
    document = parse_yahoo_chart_response(
        _body(timestamps=[1784514600, 1784601000, 1784687400], closes=[100.0, None, 101.5])
    )

    assert document.provider_symbol == "SYNTH.IS"
    assert document.currency == "TRY"
    assert document.exchange_timezone_name == "Europe/Istanbul"
    assert [(bar.timestamp, bar.close) for bar in document.closes] == [
        (1784514600, 100.0),
        (1784687400, 101.5),
    ]


@pytest.mark.parametrize(
    ("timestamps", "closes", "message"),
    [
        ([1784514600], [100.0, 101.0], "lengths differ"),
        ([1784514600], [0.0], "finite positive"),
        ([1784514600], [float("nan")], "finite positive"),
        (["bad"], [100.0], "invalid timestamp"),
        ([1784514600], [True], "invalid timestamp"),
    ],
)
def test_rejects_invalid_bar_shapes(timestamps: object, closes: object, message: str) -> None:
    with pytest.raises(YahooSecurityPricePayloadError, match=message):
        parse_yahoo_chart_response(_body(timestamps=timestamps, closes=closes))


def test_rejects_provider_errors_and_invalid_json() -> None:
    provider_error = json.dumps(
        {"chart": {"result": None, "error": {"code": "Not Found"}}}
    ).encode()
    with pytest.raises(YahooSecurityPricePayloadError, match="provider error"):
        parse_yahoo_chart_response(provider_error)
    with pytest.raises(YahooSecurityPricePayloadError, match="valid JSON"):
        parse_yahoo_chart_response(b"not-json")
