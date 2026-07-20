import json
from datetime import date
from urllib.error import URLError

import navlens.sources.tefas.client as client_module
import pytest
from navlens.sources.tefas import (
    TefasHttpClient,
    TefasPriceRequest,
    TefasRequestError,
    TefasTransportError,
)


class FakeResponse:
    def __init__(self, body: bytes) -> None:
        self._body = body

    def __enter__(self):
        return self

    def __exit__(self, *_args) -> None:
        return None

    def read(self) -> bytes:
        return self._body


def test_posts_provider_price_query(monkeypatch) -> None:
    captured = {}

    def fake_urlopen(request, timeout):
        captured.update(url=request.full_url, body=json.loads(request.data), timeout=timeout)
        return FakeResponse(b'{"resultList": []}')

    monkeypatch.setattr(client_module, "urlopen", fake_urlopen)
    request = TefasPriceRequest(" aal ", date(2026, 1, 20), date(2026, 7, 20))

    payload = TefasHttpClient(timeout_seconds=9).fetch_price_payload(
        request, as_of=date(2026, 7, 20)
    )

    assert payload == {"resultList": []}
    assert captured["body"] == {"fonKodu": "AAL", "dil": "TR", "periyod": 6}
    assert captured["timeout"] == 9


def test_maps_network_failure_to_source_error(monkeypatch) -> None:
    def failing_urlopen(_request, *, timeout):
        assert timeout == 30.0
        raise URLError("offline")

    monkeypatch.setattr(client_module, "urlopen", failing_urlopen)
    request = TefasPriceRequest("AAL", date(2026, 7, 1), date(2026, 7, 20))

    with pytest.raises(TefasTransportError, match="request failed"):
        TefasHttpClient().fetch_price_payload(request, as_of=date(2026, 7, 20))


def test_rejects_interval_beyond_provider_history() -> None:
    request = TefasPriceRequest("AAL", date(2021, 7, 19), date(2026, 7, 20))

    with pytest.raises(TefasRequestError, match="60 months"):
        TefasHttpClient().fetch_price_payload(request, as_of=date(2026, 7, 20))
