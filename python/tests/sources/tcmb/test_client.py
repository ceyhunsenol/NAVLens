import math
from datetime import date
from io import BytesIO
from urllib.error import URLError

import pytest
from navlens.sources.tcmb import TcmbHttpClient, TcmbHttpResponse, TcmbTransportError


class FakeHttpResponse:
    def __init__(self, body: bytes) -> None:
        self._body_io = BytesIO(body)

    def read(self) -> bytes:
        return self._body_io.read()

    def __enter__(self) -> "FakeHttpResponse":
        return self

    def __exit__(self, exc_type: object, exc_val: object, exc_tb: object) -> None:
        pass


def test_fetch_daily_rates_response_current_date(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_request = None
    captured_timeout = None

    def fake_urlopen(request: object, timeout: float = 30.0) -> FakeHttpResponse:
        nonlocal captured_request, captured_timeout
        captured_request = request
        captured_timeout = timeout
        return FakeHttpResponse(b"<xml>today</xml>")

    monkeypatch.setattr("navlens.sources.tcmb.client.urlopen", fake_urlopen)

    client = TcmbHttpClient(timeout_seconds=15.0)
    response = client.fetch_daily_rates_response()

    assert isinstance(response, TcmbHttpResponse)
    assert response.body == b"<xml>today</xml>"
    assert response.source_url == "https://www.tcmb.gov.tr/kurlar/today.xml"
    assert response.requested_archive_date is None

    assert captured_request is not None
    assert captured_request.full_url == "https://www.tcmb.gov.tr/kurlar/today.xml"
    assert captured_request.get_method() == "GET"
    assert captured_request.headers["Accept"] == "application/xml, text/xml"
    assert captured_timeout == 15.0


def test_fetch_daily_rates_response_historical_date(monkeypatch: pytest.MonkeyPatch) -> None:
    captured_request = None

    def fake_urlopen(request: object, timeout: float = 30.0) -> FakeHttpResponse:
        nonlocal captured_request
        captured_request = request
        return FakeHttpResponse(b"<xml>historical</xml>")

    monkeypatch.setattr("navlens.sources.tcmb.client.urlopen", fake_urlopen)

    client = TcmbHttpClient()
    target_date = date(2026, 7, 22)
    response = client.fetch_daily_rates_response(archive_date=target_date)

    expected_url = "https://www.tcmb.gov.tr/kurlar/202607/22072026.xml"
    assert response.body == b"<xml>historical</xml>"
    assert response.source_url == expected_url
    assert response.requested_archive_date == target_date

    assert captured_request is not None
    assert captured_request.full_url == expected_url
    assert captured_request.get_method() == "GET"


def test_fetch_daily_rates_response_exact_bytes_preservation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    raw_payload = b"\xff\xfe<\x00x\x00m\x00l\x00>\x00   \n\r"

    def fake_urlopen(request: object, timeout: float = 30.0) -> FakeHttpResponse:
        return FakeHttpResponse(raw_payload)

    monkeypatch.setattr("navlens.sources.tcmb.client.urlopen", fake_urlopen)

    client = TcmbHttpClient()
    response = client.fetch_daily_rates_response()

    assert response.body == raw_payload


def test_url_error_mapped_to_tcmb_transport_error_with_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cause_error = URLError("Connection refused")

    def fake_urlopen(request: object, timeout: float = 30.0) -> None:
        raise cause_error

    monkeypatch.setattr("navlens.sources.tcmb.client.urlopen", fake_urlopen)

    client = TcmbHttpClient()
    with pytest.raises(TcmbTransportError, match="TCMB request to '.*' failed") as exc_info:
        client.fetch_daily_rates_response()

    assert exc_info.value.__cause__ is cause_error


def test_timeout_error_mapped_to_tcmb_transport_error_with_cause(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cause_error = TimeoutError("Connection timed out")

    def fake_urlopen(request: object, timeout: float = 30.0) -> None:
        raise cause_error

    monkeypatch.setattr("navlens.sources.tcmb.client.urlopen", fake_urlopen)

    client = TcmbHttpClient()
    with pytest.raises(TcmbTransportError, match="TCMB request to '.*' failed") as exc_info:
        client.fetch_daily_rates_response()

    assert exc_info.value.__cause__ is cause_error


@pytest.mark.parametrize("invalid_timeout", [0.0, -1.0, math.nan, math.inf, -math.inf])
def test_rejects_invalid_timeout_seconds(invalid_timeout: float) -> None:
    with pytest.raises(ValueError, match="timeout_seconds must be a finite positive number"):
        TcmbHttpClient(timeout_seconds=invalid_timeout)


def test_client_statelessness_across_calls(monkeypatch: pytest.MonkeyPatch) -> None:
    call_urls = []

    def fake_urlopen(request: object, timeout: float = 30.0) -> FakeHttpResponse:
        call_urls.append(request.full_url)
        return FakeHttpResponse(b"<xml/>")

    monkeypatch.setattr("navlens.sources.tcmb.client.urlopen", fake_urlopen)

    client = TcmbHttpClient()
    res1 = client.fetch_daily_rates_response(date(2026, 1, 15))
    res2 = client.fetch_daily_rates_response()
    res3 = client.fetch_daily_rates_response(date(2026, 7, 22))

    assert res1.source_url == "https://www.tcmb.gov.tr/kurlar/202601/15012026.xml"
    assert res2.source_url == "https://www.tcmb.gov.tr/kurlar/today.xml"
    assert res3.source_url == "https://www.tcmb.gov.tr/kurlar/202607/22072026.xml"
    assert call_urls == [
        "https://www.tcmb.gov.tr/kurlar/202601/15012026.xml",
        "https://www.tcmb.gov.tr/kurlar/today.xml",
        "https://www.tcmb.gov.tr/kurlar/202607/22072026.xml",
    ]
