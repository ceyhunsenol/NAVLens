from datetime import date

import pytest
from navlens.sources.tefas import (
    TefasPayloadError,
    TefasPriceRequest,
    parse_price_records,
    to_price_observations,
)


def test_parses_and_filters_provider_prices() -> None:
    payload = {
        "resultList": [
            {"tarih": "2026-01-01", "fonKodu": "AAL", "fiyat": 1.20},
            {"tarih": "2026-01-02", "fonKodu": "AAL", "fiyat": "1.25"},
            {"tarih": "2026-01-05", "fonKodu": "AAL", "fiyat": 1.30},
        ]
    }
    request = TefasPriceRequest("AAL", date(2026, 1, 2), date(2026, 1, 5))

    records = parse_price_records(payload, request)
    observations = to_price_observations(records)

    assert [record.market_date for record in records] == [date(2026, 1, 2), date(2026, 1, 5)]
    assert [record.unit_price for record in records] == [1.25, 1.30]
    assert [str(observation.date) for observation in observations] == ["2026-01-02", "2026-01-05"]


def test_rejects_unexpected_fund_code() -> None:
    payload = {"resultList": [{"tarih": "2026-01-02", "fonKodu": "XYZ", "fiyat": 1.25}]}
    request = TefasPriceRequest("AAL", date(2026, 1, 2), date(2026, 1, 2))

    with pytest.raises(TefasPayloadError, match="unexpected fund code"):
        parse_price_records(payload, request)


def test_rejects_provider_error_envelope() -> None:
    payload = {"errorCode": "INVALID", "errorMessage": "Sistem Hatası", "resultList": []}
    request = TefasPriceRequest("AAL", date(2026, 1, 2), date(2026, 1, 2))

    with pytest.raises(TefasPayloadError, match="INVALID"):
        parse_price_records(payload, request)
