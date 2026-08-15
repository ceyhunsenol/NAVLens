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

    with pytest.raises(YahooSecurityPriceRateLimitError, match="rate limit"):
        client.fetch_chart_response(request)
    assert calls == 1
