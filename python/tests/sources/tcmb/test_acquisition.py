from datetime import UTC, date, datetime, timedelta, timezone
from pathlib import Path

import pytest
from navlens import FxRateObservation, MarketCalendar, MarketDate, SessionKind, SessionOverride
from navlens.datasets.fx_rate_snapshots import FxRateSnapshot
from navlens.sources.artifact_digest import sha256_artifact, sha256_bytes
from navlens.sources.tcmb import (
    TCMB_AVAILABILITY_POLICY_ID,
    TCMB_AVAILABILITY_POLICY_VERSION,
    TCMB_SOURCE_ID,
    TcmbAcquiredDailyRates,
    TcmbAcquisitionError,
    TcmbAcquisitionProvenance,
    TcmbHttpResponse,
    TcmbMappingError,
    TcmbTransportError,
    TcmbXmlParseError,
    acquire_tcmb_daily_rates,
)
from navlens.sources.tcmb.records import TcmbDailyRatesDocument

VALID_TCMB_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="15.01.2026" Date="01/15/2026">
    <Currency Kod="USD" CurrencyCode="USD">
        <Unit>1</Unit>
        <Isim>ABD DOLARI</Isim>
        <CurrencyName>US DOLLAR</CurrencyName>
        <ForexBuying>35.5000</ForexBuying>
        <ForexSelling>35.6000</ForexSelling>
        <BanknoteBuying>35.4000</BanknoteBuying>
        <BanknoteSelling>35.7000</BanknoteSelling>
    </Currency>
</Tarih_Date>"""

ALT_TCMB_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="15.01.2026" Date="01/15/2026">
    <Currency Kod="USD" CurrencyCode="USD">
        <Unit>1</Unit>
        <Isim>ABD DOLARI</Isim>
        <CurrencyName>US DOLLAR</CurrencyName>
        <ForexBuying>36.0000</ForexBuying>
        <ForexSelling>36.1000</ForexSelling>
        <BanknoteBuying>35.9000</BanknoteBuying>
        <BanknoteSelling>36.2000</BanknoteSelling>
    </Currency>
</Tarih_Date>"""

MALFORMED_XML = b"<invalid>xml"
INVALID_MAPPER_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="15.01.2026" Date="01/15/2026">
    <Currency Kod="USD" CurrencyCode="USD">
        <Unit>0</Unit>
        <ForexBuying>35.5000</ForexBuying>
    </Currency>
</Tarih_Date>"""


class FakeTcmbClient:
    def __init__(self, response: TcmbHttpResponse | Exception) -> None:
        self._response = response
        self.call_count = 0
        self.last_archive_date: date | None = None

    def fetch_daily_rates_response(self, archive_date: date | None = None) -> TcmbHttpResponse:
        self.call_count += 1
        self.last_archive_date = archive_date
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


def test_acquisition_single_client_call_and_archive_date_passthrough() -> None:
    response = TcmbHttpResponse(
        body=VALID_TCMB_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/202601/15012026.xml",
        requested_archive_date=date(2026, 1, 15),
    )
    client = FakeTcmbClient(response)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    result = acquire_tcmb_daily_rates(
        client,
        archive_date=date(2026, 1, 15),
        calendar=calendar,
        retrieved_at=retrieved_at,
    )

    assert client.call_count == 1
    assert client.last_archive_date == date(2026, 1, 15)
    assert isinstance(result, TcmbAcquiredDailyRates)


def test_acquisition_preserves_exact_bytes_and_sha256() -> None:
    response = TcmbHttpResponse(
        body=VALID_TCMB_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/today.xml",
        requested_archive_date=None,
    )
    client = FakeTcmbClient(response)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    result = acquire_tcmb_daily_rates(
        client,
        archive_date=None,
        calendar=calendar,
        retrieved_at=retrieved_at,
    )

    assert result.raw_body == VALID_TCMB_XML
    assert result.provenance.sha256_hex == sha256_bytes(VALID_TCMB_XML)


def test_acquisition_preserves_document_and_mapped_observations_order() -> None:
    response = TcmbHttpResponse(
        body=VALID_TCMB_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/today.xml",
        requested_archive_date=None,
    )
    client = FakeTcmbClient(response)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    result = acquire_tcmb_daily_rates(
        client,
        archive_date=None,
        calendar=calendar,
        retrieved_at=retrieved_at,
    )

    assert isinstance(result.document, TcmbDailyRatesDocument)
    assert result.document.date_text == "15.01.2026"
    assert isinstance(result.observations, tuple)
    assert len(result.observations) == 4
    assert all(isinstance(obs, FxRateObservation) for obs in result.observations)

    kinds = [obs.kind.name for obs in result.observations]
    assert kinds == [
        "non_cash_buying",
        "non_cash_selling",
        "cash_buying",
        "cash_selling",
    ]


def test_acquisition_scheduled_candidate_full_day() -> None:
    response = TcmbHttpResponse(
        body=VALID_TCMB_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/today.xml",
        requested_archive_date=None,
    )
    client = FakeTcmbClient(response)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    result = acquire_tcmb_daily_rates(
        client,
        archive_date=None,
        calendar=calendar,
        retrieved_at=retrieved_at,
    )

    assert result.scheduled_initial_available_at == datetime(2026, 1, 15, 12, 30, 0, tzinfo=UTC)


def test_acquisition_scheduled_candidate_closed_and_half_day() -> None:
    response = TcmbHttpResponse(
        body=VALID_TCMB_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/today.xml",
        requested_archive_date=None,
    )
    client = FakeTcmbClient(response)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)

    closed_cal = MarketCalendar([SessionOverride(MarketDate(2026, 1, 15), SessionKind("closed"))])
    result_closed = acquire_tcmb_daily_rates(
        client,
        archive_date=None,
        calendar=closed_cal,
        retrieved_at=retrieved_at,
    )
    assert result_closed.scheduled_initial_available_at is None

    half_cal = MarketCalendar([SessionOverride(MarketDate(2026, 1, 15), SessionKind("half_day"))])
    result_half = acquire_tcmb_daily_rates(
        client,
        archive_date=None,
        calendar=half_cal,
        retrieved_at=retrieved_at,
    )
    assert result_half.scheduled_initial_available_at is None


def test_provenance_fields_and_cache_hit_false() -> None:
    source_url = "https://www.tcmb.gov.tr/kurlar/202601/15012026.xml"
    req_date = date(2026, 1, 15)
    response = TcmbHttpResponse(
        body=VALID_TCMB_XML,
        source_url=source_url,
        requested_archive_date=req_date,
    )
    client = FakeTcmbClient(response)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    result = acquire_tcmb_daily_rates(
        client,
        archive_date=req_date,
        calendar=calendar,
        retrieved_at=retrieved_at,
    )

    prov = result.provenance
    assert prov.source_id == TCMB_SOURCE_ID
    assert prov.source_url == source_url
    assert prov.requested_archive_date == req_date
    assert prov.retrieved_at == retrieved_at
    assert prov.availability_policy_id == TCMB_AVAILABILITY_POLICY_ID
    assert prov.availability_policy_version == TCMB_AVAILABILITY_POLICY_VERSION
    assert prov.cache_hit is False


def test_rejects_naive_or_non_utc_retrieved_at() -> None:
    response = TcmbHttpResponse(
        body=VALID_TCMB_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/today.xml",
        requested_archive_date=None,
    )
    client = FakeTcmbClient(response)
    calendar = MarketCalendar()

    naive_dt = datetime(2026, 1, 15, 13, 0, 0)
    with pytest.raises(TcmbAcquisitionError, match="must include a timezone"):
        acquire_tcmb_daily_rates(
            client,
            archive_date=None,
            calendar=calendar,
            retrieved_at=naive_dt,
        )

    non_utc_dt = datetime(2026, 1, 15, 16, 0, 0, tzinfo=timezone(timedelta(hours=3)))
    with pytest.raises(TcmbAcquisitionError, match="must be in UTC timezone"):
        acquire_tcmb_daily_rates(
            client,
            archive_date=None,
            calendar=calendar,
            retrieved_at=non_utc_dt,
        )


def test_rejects_response_for_a_different_archive_date() -> None:
    response = TcmbHttpResponse(
        body=VALID_TCMB_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/today.xml",
        requested_archive_date=None,
    )
    client = FakeTcmbClient(response)

    with pytest.raises(TcmbAcquisitionError, match="response archive date"):
        acquire_tcmb_daily_rates(
            client,
            archive_date=date(2026, 1, 15),
            calendar=MarketCalendar(),
            retrieved_at=datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC),
        )


def test_transport_error_propagates_unwrapped() -> None:
    transport_err = TcmbTransportError("HTTP 500 Server Error")
    client = FakeTcmbClient(transport_err)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    with pytest.raises(TcmbTransportError, match="HTTP 500 Server Error"):
        acquire_tcmb_daily_rates(
            client,
            archive_date=None,
            calendar=calendar,
            retrieved_at=retrieved_at,
        )


def test_parser_error_propagates_unwrapped() -> None:
    response = TcmbHttpResponse(
        body=MALFORMED_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/today.xml",
        requested_archive_date=None,
    )
    client = FakeTcmbClient(response)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    with pytest.raises(TcmbXmlParseError):
        acquire_tcmb_daily_rates(
            client,
            archive_date=None,
            calendar=calendar,
            retrieved_at=retrieved_at,
        )


def test_mapper_error_propagates_unwrapped() -> None:
    response = TcmbHttpResponse(
        body=INVALID_MAPPER_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/today.xml",
        requested_archive_date=None,
    )
    client = FakeTcmbClient(response)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    with pytest.raises(TcmbMappingError):
        acquire_tcmb_daily_rates(
            client,
            archive_date=None,
            calendar=calendar,
            retrieved_at=retrieved_at,
        )


def test_different_raw_bytes_produce_different_digests() -> None:
    client1 = FakeTcmbClient(TcmbHttpResponse(VALID_TCMB_XML, "url", None))
    client2 = FakeTcmbClient(TcmbHttpResponse(ALT_TCMB_XML, "url", None))
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    res1 = acquire_tcmb_daily_rates(
        client1, archive_date=None, calendar=calendar, retrieved_at=retrieved_at
    )
    res2 = acquire_tcmb_daily_rates(
        client2, archive_date=None, calendar=calendar, retrieved_at=retrieved_at
    )

    assert res1.provenance.sha256_hex != res2.provenance.sha256_hex


def test_no_fx_rate_snapshot_contained() -> None:
    response = TcmbHttpResponse(
        body=VALID_TCMB_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/today.xml",
        requested_archive_date=None,
    )
    client = FakeTcmbClient(response)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    result = acquire_tcmb_daily_rates(
        client,
        archive_date=None,
        calendar=calendar,
        retrieved_at=retrieved_at,
    )

    assert not isinstance(result, FxRateSnapshot)
    assert not hasattr(result, "snapshots")
    assert not hasattr(result, "available_at")


def test_retrieved_at_is_caller_driven_only() -> None:
    response = TcmbHttpResponse(
        body=VALID_TCMB_XML,
        source_url="https://www.tcmb.gov.tr/kurlar/today.xml",
        requested_archive_date=None,
    )
    client = FakeTcmbClient(response)
    retrieved_at = datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC)
    calendar = MarketCalendar()

    result = acquire_tcmb_daily_rates(
        client,
        archive_date=None,
        calendar=calendar,
        retrieved_at=retrieved_at,
    )

    assert result.provenance.retrieved_at == retrieved_at


def test_existing_artifact_file_digest_behavior_unchanged(tmp_path: Path) -> None:
    test_content = b"artifact content for file digest test"
    artifact_path = tmp_path / "artifact.xml"
    artifact_path.write_bytes(test_content)

    assert sha256_artifact(artifact_path) == sha256_bytes(test_content)


def test_provenance_constructor_enforces_source_and_digest_invariants() -> None:
    values = {
        "source_id": TCMB_SOURCE_ID,
        "requested_archive_date": None,
        "source_url": "https://www.tcmb.gov.tr/kurlar/today.xml",
        "retrieved_at": datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC),
        "sha256_hex": sha256_bytes(VALID_TCMB_XML),
        "availability_policy_id": TCMB_AVAILABILITY_POLICY_ID,
        "availability_policy_version": TCMB_AVAILABILITY_POLICY_VERSION,
        "cache_hit": False,
    }

    with pytest.raises(TcmbAcquisitionError, match="source_id"):
        TcmbAcquisitionProvenance(**(values | {"source_id": "other"}))
    with pytest.raises(TcmbAcquisitionError, match="sha256_hex"):
        TcmbAcquisitionProvenance(**(values | {"sha256_hex": "invalid"}))


def test_acquired_result_rejects_raw_body_digest_mismatch() -> None:
    result = acquire_tcmb_daily_rates(
        FakeTcmbClient(TcmbHttpResponse(VALID_TCMB_XML, "url", None)),
        archive_date=None,
        calendar=MarketCalendar(),
        retrieved_at=datetime(2026, 1, 15, 13, 0, 0, tzinfo=UTC),
    )

    with pytest.raises(TcmbAcquisitionError, match="does not match"):
        TcmbAcquiredDailyRates(
            raw_body=ALT_TCMB_XML,
            document=result.document,
            observations=result.observations,
            scheduled_initial_available_at=result.scheduled_initial_available_at,
            provenance=result.provenance,
        )
