from datetime import UTC, date, datetime, timedelta
from hashlib import sha256

import pytest
from navlens.sources.tefas import (
    TefasAccessPolicy,
    TefasPriceRequest,
    TefasRequestError,
    capture_payload_provenance,
)


def test_rejects_reversed_price_interval() -> None:
    with pytest.raises(TefasRequestError, match="start date"):
        TefasPriceRequest("AAL", date(2026, 1, 3), date(2026, 1, 2))


def test_keeps_access_single_threaded_and_backs_off() -> None:
    policy = TefasAccessPolicy()

    assert policy.maximum_concurrency == 1
    assert policy.retry_delay(1) == timedelta(seconds=2)
    assert policy.retry_delay(2) == timedelta(seconds=4)


def test_captures_payload_checksum_and_context(tmp_path) -> None:
    payload = tmp_path / "aal.json"
    payload.write_bytes(b'{"resultList": []}')
    request = TefasPriceRequest("AAL", date(2026, 1, 2), date(2026, 1, 2))
    downloaded_at = datetime(2026, 1, 3, 8, 30, tzinfo=UTC)

    provenance = capture_payload_provenance(
        payload, request, downloaded_at, "https://www.tefas.gov.tr/"
    )

    assert provenance.original_filename == "aal.json"
    assert provenance.sha256_hex == sha256(payload.read_bytes()).hexdigest()
    assert provenance.request == request


def test_rejects_timestamp_without_timezone(tmp_path) -> None:
    payload = tmp_path / "aal.json"
    payload.write_text("fixture", encoding="utf-8")
    request = TefasPriceRequest("AAL", date(2026, 1, 2), date(2026, 1, 2))

    with pytest.raises(ValueError, match="timezone"):
        capture_payload_provenance(
            payload, request, datetime(2026, 1, 3), "https://www.tefas.gov.tr/"
        )
