from datetime import UTC, date, datetime, timedelta

from navlens.sources.tefas import (
    AcquireTefasPrices,
    TefasAccessPolicy,
    TefasPriceRequest,
    TefasTransportError,
)
from navlens.sources.tefas.cache import price_cache_paths
from navlens.sources.tefas.response import TefasHttpResponse, decode_response


class FakeClient:
    def __init__(self, outcomes) -> None:
        self._outcomes = iter(outcomes)
        self.calls = 0

    def fetch_price_response(self, _request, _as_of) -> TefasHttpResponse:
        self.calls += 1
        outcome = next(self._outcomes)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def response(price: float = 1.25) -> TefasHttpResponse:
    body = (
        '{"errorCode":null,"errorMessage":null,"resultList":['
        f'{{"tarih":"2026-07-01","fonKodu":"AAL","fiyat":{price}}}]}}'
    ).encode()
    return decode_response(body, "https://www.tefas.gov.tr/api/funds/fonFiyatBilgiGetir")


def request() -> TefasPriceRequest:
    return TefasPriceRequest("AAL", date(2026, 7, 1), date(2026, 7, 20))


def test_stores_exact_response_and_reuses_fresh_cache(tmp_path) -> None:
    fetched = response()
    client = FakeClient([fetched])
    acquisition = AcquireTefasPrices(client, tmp_path)
    acquired_at = datetime(2026, 7, 20, 9, tzinfo=UTC)

    first = acquisition.acquire(request(), date(2026, 7, 20), acquired_at)
    second = acquisition.acquire(request(), date(2026, 7, 20), acquired_at + timedelta(hours=1))

    assert first.payload_path.read_bytes() == fetched.body
    assert first.from_cache is False
    assert second.from_cache is True
    assert second.records == first.records
    assert client.calls == 1


def test_replaces_cache_when_payload_checksum_changes(tmp_path) -> None:
    client = FakeClient([response(1.25), response(1.30)])
    acquisition = AcquireTefasPrices(client, tmp_path)
    acquired_at = datetime(2026, 7, 20, 9, tzinfo=UTC)
    first = acquisition.acquire(request(), date(2026, 7, 20), acquired_at)
    first.payload_path.write_text("corrupt", encoding="utf-8")

    refreshed = acquisition.acquire(request(), date(2026, 7, 20), acquired_at + timedelta(hours=1))

    assert refreshed.from_cache is False
    assert refreshed.records[0].unit_price == 1.30
    assert client.calls == 2


def test_retries_transport_failure_with_policy_delay(tmp_path) -> None:
    client = FakeClient([TefasTransportError("temporary"), response()])
    delays = []
    policy = TefasAccessPolicy(minimum_interval=timedelta(seconds=5))
    acquisition = AcquireTefasPrices(client, tmp_path, policy, delays.append)

    result = acquisition.acquire(request(), date(2026, 7, 20), datetime(2026, 7, 20, 9, tzinfo=UTC))

    assert len(result.records) == 1
    assert delays == [5.0]
    assert client.calls == 2


def test_cache_paths_do_not_embed_untrusted_fund_text(tmp_path) -> None:
    unsafe = TefasPriceRequest("../AAL", date(2026, 7, 1), date(2026, 7, 20))

    paths = price_cache_paths(tmp_path, unsafe, date(2026, 7, 20))

    assert paths.payload.parent == tmp_path
    assert "AAL" not in paths.payload.name
