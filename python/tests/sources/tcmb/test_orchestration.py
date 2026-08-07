"""Tests for cache-aware TCMB request orchestration boundary."""

from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from navlens import MarketCalendar, MarketDate
from navlens.sources.artifact_digest import sha256_bytes
from navlens.sources.tcmb import (
    TcmbAcquisitionContext,
    TcmbCacheMissError,
    TcmbCachePolicy,
    TcmbHttpResponse,
    TcmbMappingError,
    TcmbOrchestrationError,
    TcmbRevisionIndexError,
    TcmbSnapshotMaterializationError,
    TcmbTransportError,
    TcmbVerifiedPublication,
    TcmbXmlParseError,
    load_tcmb_raw_artifact,
    load_tcmb_revision_index,
)
from navlens.sources.tcmb import (
    TcmbFxRateSnapshotResult as TcmbOrchestratedSnapshots,
)
from navlens.sources.tcmb import (
    obtain_tcmb_fx_rate_snapshots as load_tcmb_fx_rate_snapshots,
)


class DummyClient:
    """Mock implementation of TcmbResponseClient."""

    def __init__(self, responses: list[TcmbHttpResponse] | None = None) -> None:
        self.responses = responses or []
        self.call_count = 0
        self.requested_dates: list[date | None] = []

    def fetch_daily_rates_response(self, archive_date: date | None = None) -> TcmbHttpResponse:
        self.call_count += 1
        self.requested_dates.append(archive_date)
        if not self.responses:
            raise TcmbTransportError("No mock response configured")
        return self.responses.pop(0)


def make_xml(market_date_str: str = "01.01.2024", rate_str: str = "30.00") -> bytes:
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<Tarih_Date Tarih="{market_date_str}" Date="{market_date_str}" Bulten_No="2024/1">
    <Currency CrossOrder="0" Kod="USD" CurrencyCode="USD">
        <Unit>1</Unit>
        <Isim>US DOLLAR</Isim>
        <CurrencyName>US DOLLAR</CurrencyName>
        <ForexBuying>{rate_str}</ForexBuying>
        <ForexSelling>30.50</ForexSelling>
        <BanknoteBuying>29.90</BanknoteBuying>
        <BanknoteSelling>30.60</BanknoteSelling>
    </Currency>
</Tarih_Date>""".encode()


def test_cache_only_hit(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml = make_xml()
    client = DummyClient(
        [TcmbHttpResponse(body=xml, source_url="http://example.com", requested_archive_date=None)]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    # First populate cache using refresh
    initial = load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
    )
    assert initial.acquired is True
    assert initial.index_changed is True
    assert len(initial.snapshots) == 4
    assert client.call_count == 1

    # Now load cache-only (no acquisition_context allowed)
    cached = load_tcmb_fx_rate_snapshots(tmp_path, market_date, TcmbCachePolicy.cache_only)
    assert isinstance(cached, TcmbOrchestratedSnapshots)
    assert cached.acquired is False
    assert cached.index_changed is False
    assert cached.requested_policy == TcmbCachePolicy.cache_only
    assert len(cached.snapshots) == 4
    assert client.call_count == 1  # No additional network call


def test_cache_only_miss_raises_typed_error(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    with pytest.raises(TcmbCacheMissError, match="no cached revision index found"):
        load_tcmb_fx_rate_snapshots(tmp_path, market_date, TcmbCachePolicy.cache_only)


def test_cache_only_rejects_acquisition_context(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    context = TcmbAcquisitionContext(
        client=DummyClient(),
        calendar=MarketCalendar(),
        retrieved_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    )
    with pytest.raises(TcmbOrchestrationError, match="acquisition_context must not be supplied"):
        load_tcmb_fx_rate_snapshots(
            tmp_path, market_date, TcmbCachePolicy.cache_only, acquisition_context=context
        )


def test_prefer_cache_hit_without_client_invocation(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml = make_xml()
    client = DummyClient(
        [TcmbHttpResponse(body=xml, source_url="http://example.com", requested_archive_date=None)]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
    )
    assert client.call_count == 1

    # Second call with prefer_cache should hit cache without network fetch
    res = load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.prefer_cache, acquisition_context=context
    )
    assert res.acquired is False
    assert res.index_changed is False
    assert res.requested_policy == TcmbCachePolicy.prefer_cache
    assert len(res.snapshots) == 4
    assert client.call_count == 1


def test_prefer_cache_miss_with_exactly_one_client_invocation(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml = make_xml()
    client = DummyClient(
        [TcmbHttpResponse(body=xml, source_url="http://example.com", requested_archive_date=None)]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    res = load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.prefer_cache, acquisition_context=context
    )
    assert res.acquired is True
    assert res.revision_added is True
    assert res.index_changed is True
    assert res.requested_policy == TcmbCachePolicy.prefer_cache
    assert len(res.snapshots) == 4
    assert client.call_count == 1


def test_refresh_always_performs_acquisition(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml1 = make_xml(rate_str="30.00")
    xml2 = make_xml(rate_str="31.00")
    client = DummyClient(
        [
            TcmbHttpResponse(
                body=xml1, source_url="http://example.com", requested_archive_date=None
            ),
            TcmbHttpResponse(
                body=xml2, source_url="http://example.com", requested_archive_date=None
            ),
        ]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    r1 = load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
    )
    assert r1.acquired is True
    assert r1.revision_added is True
    assert len(r1.snapshots) == 4
    assert client.call_count == 1

    r2 = load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
    )
    assert r2.acquired is True
    assert r2.revision_added is True
    assert len(r2.snapshots) == 8  # Both initial and correction snapshots materialized
    assert client.call_count == 2


def test_unchanged_digest_idempotent_revision(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml = make_xml(rate_str="30.00")
    client = DummyClient(
        [
            TcmbHttpResponse(
                body=xml, source_url="http://example.com", requested_archive_date=None
            ),
            TcmbHttpResponse(
                body=xml, source_url="http://example.com", requested_archive_date=None
            ),
        ]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    r1 = load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
    )
    assert r1.revision_added is True

    r2 = load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
    )
    assert r2.acquired is True
    assert r2.revision_added is False
    assert r2.index_changed is False
    assert len(r2.snapshots) == 4


def test_same_digest_with_earlier_observation_changes_index(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    xml = make_xml()
    response = TcmbHttpResponse(
        body=xml,
        source_url="http://example.com",
        requested_archive_date=None,
    )
    first_context = TcmbAcquisitionContext(
        client=DummyClient([response]),
        calendar=MarketCalendar(),
        retrieved_at=datetime(2024, 1, 1, 13, 0, tzinfo=UTC),
    )
    earlier_context = TcmbAcquisitionContext(
        client=DummyClient([response]),
        calendar=MarketCalendar(),
        retrieved_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    )

    load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=first_context
    )
    result = load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=earlier_context
    )

    assert result.revision_added is False
    assert result.index_changed is True


def test_corrupted_raw_artifact_remains_fatal_no_fallback(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml = make_xml()
    client = DummyClient(
        [
            TcmbHttpResponse(
                body=xml, source_url="http://example.com", requested_archive_date=None
            ),
            TcmbHttpResponse(
                body=xml, source_url="http://example.com", requested_archive_date=None
            ),
        ]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
    )
    with (
        patch(
            "navlens.sources.tcmb.orchestration.materialize_tcmb_fx_rate_snapshots",
            side_effect=TcmbSnapshotMaterializationError("corrupted raw artifact"),
        ),
        pytest.raises(TcmbOrchestrationError, match="failed to resolve or materialize"),
    ):
        load_tcmb_fx_rate_snapshots(
            tmp_path, market_date, TcmbCachePolicy.prefer_cache, acquisition_context=context
        )
    assert client.call_count == 1


def test_missing_artifact_referenced_by_index_remains_fatal(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml = make_xml()
    client = DummyClient(
        [TcmbHttpResponse(body=xml, source_url="http://example.com", requested_archive_date=None)]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
    )
    with (
        patch(
            "navlens.sources.tcmb.orchestration.materialize_tcmb_fx_rate_snapshots",
            side_effect=TcmbSnapshotMaterializationError("missing raw artifact"),
        ),
        pytest.raises(TcmbOrchestrationError, match="missing raw artifact"),
    ):
        load_tcmb_fx_rate_snapshots(tmp_path, market_date, TcmbCachePolicy.cache_only)


def test_network_acquisition_failure_with_chained_cause(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    client = DummyClient([])
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    with pytest.raises(TcmbOrchestrationError, match="acquisition failed") as exc_info:
        load_tcmb_fx_rate_snapshots(
            tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
        )
    assert isinstance(exc_info.value.__cause__, TcmbTransportError)


def test_raw_storage_failure(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml = make_xml()
    client = DummyClient(
        [TcmbHttpResponse(body=xml, source_url="http://example.com", requested_archive_date=None)]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    with (
        patch(
            "navlens.sources.tcmb.orchestration.store_tcmb_raw_artifact",
            side_effect=OSError("Disk full"),
        ),
        patch("navlens.sources.tcmb.orchestration.record_tcmb_revision") as record_revision,
        pytest.raises(TcmbOrchestrationError, match="failed to store raw artifact"),
    ):
        load_tcmb_fx_rate_snapshots(
            tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
        )
    record_revision.assert_not_called()


def test_revision_index_read_failure(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    with (
        patch(
            "navlens.sources.tcmb.orchestration.load_tcmb_revision_index",
            side_effect=TcmbRevisionIndexError("invalid index"),
        ),
        pytest.raises(TcmbOrchestrationError, match="failed to load revision index"),
    ):
        load_tcmb_fx_rate_snapshots(tmp_path, market_date, TcmbCachePolicy.cache_only)


def test_revision_index_write_failure(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml = make_xml()
    client = DummyClient(
        [TcmbHttpResponse(body=xml, source_url="http://example.com", requested_archive_date=None)]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    with (
        patch(
            "navlens.sources.tcmb.orchestration.record_tcmb_revision",
            side_effect=OSError("Write permission denied"),
        ),
        pytest.raises(TcmbOrchestrationError, match="failed to record revision index"),
    ):
        load_tcmb_fx_rate_snapshots(
            tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
        )

    digest = sha256_bytes(xml)
    assert load_tcmb_raw_artifact(tmp_path, digest) == xml
    assert load_tcmb_revision_index(tmp_path, market_date) is None


def test_forwarding_initial_revision_and_verified_publications(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml = make_xml()
    client = DummyClient(
        [TcmbHttpResponse(body=xml, source_url="http://example.com", requested_archive_date=None)]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    digest = sha256_bytes(xml)
    pub = TcmbVerifiedPublication(
        sha256_hex=digest, published_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC)
    )

    res = load_tcmb_fx_rate_snapshots(
        tmp_path,
        market_date,
        TcmbCachePolicy.refresh,
        acquisition_context=context,
        initial_revision_sha256_hex=digest,
        verified_publications=[pub],
    )
    assert res.snapshots[0].available_at == datetime(2024, 1, 1, 10, 0, tzinfo=UTC)


def test_no_point_in_time_winner_selection_inside_orchestration(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    calendar = MarketCalendar()
    xml1 = make_xml(rate_str="30.00")
    xml2 = make_xml(rate_str="31.00")
    client = DummyClient(
        [
            TcmbHttpResponse(
                body=xml1, source_url="http://example.com", requested_archive_date=None
            ),
            TcmbHttpResponse(
                body=xml2, source_url="http://example.com", requested_archive_date=None
            ),
        ]
    )
    context = TcmbAcquisitionContext(client=client, calendar=calendar, retrieved_at=retrieved_at)

    load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
    )
    res = load_tcmb_fx_rate_snapshots(
        tmp_path, market_date, TcmbCachePolicy.refresh, acquisition_context=context
    )

    assert len(res.snapshots) == 8
    assert res.snapshots[0].observation.rate.quote_currency_per_one_base_currency == 30.0
    assert res.snapshots[4].observation.rate.quote_currency_per_one_base_currency == 31.0


def test_verified_publication_generator_is_consumed_once(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)
    retrieved_at = datetime(2024, 1, 1, 12, 0, tzinfo=UTC)
    xml = make_xml()
    digest = sha256_bytes(xml)
    client = DummyClient(
        [TcmbHttpResponse(body=xml, source_url="http://example.com", requested_archive_date=None)]
    )
    context = TcmbAcquisitionContext(
        client=client,
        calendar=MarketCalendar(),
        retrieved_at=retrieved_at,
    )
    iterations = 0

    def publications():
        nonlocal iterations
        iterations += 1
        yield TcmbVerifiedPublication(
            sha256_hex=digest,
            published_at=datetime(2024, 1, 1, 10, 0, tzinfo=UTC),
        )

    result = load_tcmb_fx_rate_snapshots(
        tmp_path,
        market_date,
        TcmbCachePolicy.refresh,
        acquisition_context=context,
        verified_publications=publications(),
    )

    assert iterations == 1
    assert result.snapshots[0].available_at == datetime(2024, 1, 1, 10, 0, tzinfo=UTC)


@pytest.mark.parametrize(
    ("body", "cause_type"),
    [
        (b"<invalid", TcmbXmlParseError),
        (make_xml(rate_str="0"), TcmbMappingError),
    ],
)
def test_parse_and_mapping_failures_keep_their_cause(
    tmp_path: Path,
    body: bytes,
    cause_type: type[Exception],
) -> None:
    client = DummyClient(
        [TcmbHttpResponse(body=body, source_url="http://example.com", requested_archive_date=None)]
    )
    context = TcmbAcquisitionContext(
        client=client,
        calendar=MarketCalendar(),
        retrieved_at=datetime(2024, 1, 1, 12, 0, tzinfo=UTC),
    )

    with pytest.raises(TcmbOrchestrationError, match="acquisition failed") as exc_info:
        load_tcmb_fx_rate_snapshots(
            tmp_path,
            MarketDate(2024, 1, 1),
            TcmbCachePolicy.refresh,
            acquisition_context=context,
        )

    assert isinstance(exc_info.value.__cause__, cause_type)


def test_market_date_mismatch_is_rejected_before_storage(tmp_path: Path) -> None:
    client = DummyClient(
        [
            TcmbHttpResponse(
                body=make_xml(market_date_str="02.01.2024"),
                source_url="http://example.com",
                requested_archive_date=None,
            )
        ]
    )
    context = TcmbAcquisitionContext(
        client=client,
        calendar=MarketCalendar(),
        retrieved_at=datetime(2024, 1, 2, 12, 0, tzinfo=UTC),
    )

    with (
        patch("navlens.sources.tcmb.orchestration.store_tcmb_raw_artifact") as store_raw,
        pytest.raises(TcmbOrchestrationError, match="does not match requested market date"),
    ):
        load_tcmb_fx_rate_snapshots(
            tmp_path,
            MarketDate(2024, 1, 1),
            TcmbCachePolicy.refresh,
            acquisition_context=context,
        )
    store_raw.assert_not_called()


def test_invalid_policy_and_input_validations(tmp_path: Path) -> None:
    market_date = MarketDate(2024, 1, 1)

    with pytest.raises(TcmbOrchestrationError, match="policy must be a TcmbCachePolicy"):
        load_tcmb_fx_rate_snapshots(tmp_path, market_date, "invalid_policy")  # type: ignore

    with pytest.raises(
        TcmbOrchestrationError, match="acquisition_context is required for prefer_cache policy"
    ):
        load_tcmb_fx_rate_snapshots(tmp_path, market_date, TcmbCachePolicy.prefer_cache)

    with pytest.raises(TcmbOrchestrationError, match="root must be a string or Path"):
        load_tcmb_fx_rate_snapshots(42, market_date, TcmbCachePolicy.cache_only)  # type: ignore

    with pytest.raises(TcmbOrchestrationError, match="market_date must be a MarketDate"):
        load_tcmb_fx_rate_snapshots(tmp_path, date(2024, 1, 1), TcmbCachePolicy.cache_only)  # type: ignore

    with pytest.raises(TcmbOrchestrationError, match="retrieved_at must include a timezone"):
        TcmbAcquisitionContext(
            client=DummyClient(),
            calendar=MarketCalendar(),
            retrieved_at=datetime(2024, 1, 1, 12, 0),
        )
