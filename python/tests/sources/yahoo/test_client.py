from datetime import UTC, date, datetime
from urllib.error import HTTPError

import pytest
from navlens.sources.yahoo import (
    YahooChartHttpClient,
    YahooSecurityPriceRateLimitError,
    YahooSecurityPriceRequest,
    YahooSymbolMapping,
)


class FakeUrlResponse:
    def __enter__(self) -> "FakeUrlResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return b'{"chart": {"result": [], "error": null}}'


def test_builds_bounded_daily_chart_request(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    captured: dict[str, object] = {}

    def fake_urlopen(request, timeout):  # type: ignore[no-untyped-def]
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeUrlResponse()

    monkeypatch.setattr("navlens.sources.yahoo.client.urlopen", fake_urlopen)
    retrieved_at = datetime(2026, 7, 23, 12, tzinfo=UTC)
    client = YahooChartHttpClient(timeout_seconds=5.0, clock=lambda: retrieved_at)
    request = YahooSecurityPriceRequest(
        YahooSymbolMapping("SYNTH", "synth.is"),
        date(2026, 7, 20),
        date(2026, 7, 22),
    )

    response = client.fetch_chart_response(request)

    url = str(captured["url"])
    assert "/SYNTH.IS?" in url
    assert "interval=1d" in url
    assert "events=div%2Csplits" in url
    assert "includeAdjustedClose=true" in url
    assert "period1=" in url and "period2=" in url
    assert captured["timeout"] == 5.0
    assert response.retrieved_at is retrieved_at


def test_maps_http_429_without_retrying(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    calls = 0

    def rate_limited(request, timeout):  # type: ignore[no-untyped-def]
        nonlocal calls
        calls += 1
        raise HTTPError(request.full_url, 429, "Too Many Requests", None, None)

    monkeypatch.setattr("navlens.sources.yahoo.client.urlopen", rate_limited)
    client = YahooChartHttpClient()
    request = YahooSecurityPriceRequest(
        YahooSymbolMapping("SYNTH", "SYNTH.IS"),
        date(2026, 7, 20),
        date(2026, 7, 22),
    )

    with pytest.raises(YahooSecurityPriceRateLimitError, match="rate limit") as exc_info:
        client.fetch_chart_response(request)
    assert calls == 1
    assert exc_info.value.retry_after is None
    assert exc_info.value.retry_after_seconds is None


def test_captures_retry_after_integer_seconds(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def rate_limited(request, timeout):  # type: ignore[no-untyped-def]
        headers = {"Retry-After": "120"}
        raise HTTPError(request.full_url, 429, "Too Many Requests", headers, None)  # type: ignore[arg-type]

    monkeypatch.setattr("navlens.sources.yahoo.client.urlopen", rate_limited)
    client = YahooChartHttpClient()
    request = YahooSecurityPriceRequest(
        YahooSymbolMapping("SYNTH", "SYNTH.IS"),
        date(2026, 7, 20),
        date(2026, 7, 22),
    )

    with pytest.raises(YahooSecurityPriceRateLimitError) as exc_info:
        client.fetch_chart_response(request)
    assert exc_info.value.retry_after == "120"
    assert exc_info.value.retry_after_seconds == 120


def test_captures_retry_after_http_date_losslessly(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    date_str = "Wed, 21 Oct 2026 07:28:00 GMT"

    def rate_limited(request, timeout):  # type: ignore[no-untyped-def]
        headers = {"Retry-After": f"  {date_str}  "}
        raise HTTPError(request.full_url, 429, "Too Many Requests", headers, None)  # type: ignore[arg-type]

    monkeypatch.setattr("navlens.sources.yahoo.client.urlopen", rate_limited)
    client = YahooChartHttpClient()
    request = YahooSecurityPriceRequest(
        YahooSymbolMapping("SYNTH", "SYNTH.IS"),
        date(2026, 7, 20),
        date(2026, 7, 22),
    )

    with pytest.raises(YahooSecurityPriceRateLimitError) as exc_info:
        client.fetch_chart_response(request)
    assert exc_info.value.retry_after == date_str
    assert exc_info.value.retry_after_seconds is None


def test_rate_limit_error_rejects_non_string_retry_after() -> None:
    with pytest.raises(TypeError, match="retry_after must be a string or None"):
        YahooSecurityPriceRateLimitError("rate limited", retry_after=120)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("raw_header", "expected_seconds"),
    [
        ("120", 120),
        ("0", 0),
        ("  45  ", 45),
        ("-10", None),
        ("12.5", None),
        ("٢", None),  # Unicode digit rejected
        ("invalid", None),
        ("", None),
    ],
)
def test_rate_limit_error_retry_after_seconds_parsing(
    raw_header: str, expected_seconds: int | None
) -> None:
    error = YahooSecurityPriceRateLimitError("rate limited", retry_after=raw_header)
    assert error.retry_after == raw_header
    assert error.retry_after_seconds == expected_seconds
