"""Tests for shared TCMB source composition builder and settings."""

import math
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from navlens import MarketCalendar, MarketDate, SessionKind
from navlens.sources.tcmb import (
    TcmbAcquisitionError,
    TcmbCachePolicy,
    TcmbFxRateSource,
    TcmbHttpResponse,
    TcmbResponseClient,
)
from navlens.sources.tcmb.composition import (
    TcmbSourceSettings,
    build_tcmb_fx_rate_source,
    build_tcmb_market_calendar,
    create_tcmb_acquisition_context_factory,
)


class DummyTcmbClient(TcmbResponseClient):
    """Dummy client recording requested dates."""

    def __init__(self) -> None:
        self.requested_dates: list[date | None] = []

    def fetch_daily_rates_response(self, archive_date: date | None = None) -> TcmbHttpResponse:
        self.requested_dates.append(archive_date)
        return TcmbHttpResponse(
            body=b"<xml/>",
            source_url="https://example.com/rates.xml",
            requested_archive_date=archive_date,
        )


def test_tcmb_source_settings_valid_construction(tmp_path: Path) -> None:
    settings = TcmbSourceSettings(
        cache_root=tmp_path,
        cache_policy=TcmbCachePolicy.prefer_cache,
        http_timeout_seconds=15.5,
    )
    assert settings.cache_root == tmp_path
    assert settings.cache_policy == TcmbCachePolicy.prefer_cache
    assert settings.http_timeout_seconds == 15.5


@pytest.mark.parametrize(
    ("cache_root", "cache_policy", "timeout", "match"),
    [
        ("invalid_str_path", TcmbCachePolicy.cache_only, 30.0, "cache_root must be a Path"),
        (Path("/tmp"), "cache_only", 30.0, "cache_policy must be a TcmbCachePolicy"),
        (Path("/tmp"), TcmbCachePolicy.cache_only, True, "http_timeout_seconds must be a numeric"),
        (Path("/tmp"), TcmbCachePolicy.cache_only, "30", "http_timeout_seconds must be a numeric"),
        (
            Path("/tmp"),
            TcmbCachePolicy.cache_only,
            0.0,
            "http_timeout_seconds must be a finite positive",
        ),
        (
            Path("/tmp"),
            TcmbCachePolicy.cache_only,
            -5.0,
            "http_timeout_seconds must be a finite positive",
        ),
        (
            Path("/tmp"),
            TcmbCachePolicy.cache_only,
            math.nan,
            "http_timeout_seconds must be a finite positive",
        ),
        (
            Path("/tmp"),
            TcmbCachePolicy.cache_only,
            math.inf,
            "http_timeout_seconds must be a finite positive",
        ),
    ],
)
def test_tcmb_source_settings_invalid_construction_raises(
    cache_root: object,
    cache_policy: object,
    timeout: object,
    match: str,
) -> None:
    with pytest.raises(TcmbAcquisitionError, match=match):
        TcmbSourceSettings(
            cache_root=cache_root,  # type: ignore[arg-type]
            cache_policy=cache_policy,  # type: ignore[arg-type]
            http_timeout_seconds=timeout,  # type: ignore[arg-type]
        )


def test_build_tcmb_market_calendar_constructs_overrides() -> None:
    closed_dates = (date(2026, 1, 15), date(2026, 1, 16))
    calendar = build_tcmb_market_calendar(closed_dates)
    assert isinstance(calendar, MarketCalendar)
    assert calendar.session_on(MarketDate(2026, 1, 15)) == SessionKind("closed")
    assert calendar.session_on(MarketDate(2026, 1, 16)) == SessionKind("closed")
    assert calendar.session_on(MarketDate(2026, 1, 14)) == SessionKind("full_day")


def test_build_tcmb_market_calendar_rejects_duplicates() -> None:
    closed_dates = (date(2026, 1, 15), date(2026, 1, 15))
    with pytest.raises(ValueError, match="closed_dates must not contain duplicates"):
        build_tcmb_market_calendar(closed_dates)


def test_create_tcmb_acquisition_context_factory_invokes_clock_and_shares_instances() -> None:
    cal = MarketCalendar()
    client = DummyTcmbClient()
    times = [
        datetime(2026, 1, 1, 8, 0, tzinfo=UTC),
        datetime(2026, 1, 2, 9, 30, tzinfo=UTC),
    ]
    clock_iter = iter(times)

    factory = create_tcmb_acquisition_context_factory(
        calendar=cal,
        client=client,
        clock=lambda: next(clock_iter),
    )

    ctx1 = factory(MarketDate(2026, 1, 1))
    ctx2 = factory(MarketDate(2026, 1, 2))

    assert ctx1 is not ctx2
    assert ctx1.retrieved_at == times[0]
    assert ctx2.retrieved_at == times[1]
    assert ctx1.calendar is cal
    assert ctx2.calendar is cal
    assert ctx1.client is client
    assert ctx2.client is client


def test_build_tcmb_fx_rate_source_cache_only_creates_no_client_and_does_not_call_clock(
    tmp_path: Path,
) -> None:
    cal = MarketCalendar()
    settings = TcmbSourceSettings(
        cache_root=tmp_path,
        cache_policy=TcmbCachePolicy.cache_only,
    )

    def exploding_clock() -> datetime:
        raise AssertionError("clock should not be called in cache_only mode")

    source = build_tcmb_fx_rate_source(
        settings=settings,
        calendar=cal,
        client=None,
        clock=exploding_clock,
    )

    assert isinstance(source, TcmbFxRateSource)
    assert source._calendar is cal
    assert source.source_id == "tcmb"


def test_build_tcmb_fx_rate_source_prefer_cache_uses_injected_client_and_clock(
    tmp_path: Path,
) -> None:
    cal = MarketCalendar()
    client = DummyTcmbClient()
    fixed_time = datetime(2026, 1, 2, 10, 0, tzinfo=UTC)
    settings = TcmbSourceSettings(
        cache_root=tmp_path,
        cache_policy=TcmbCachePolicy.prefer_cache,
    )

    source = build_tcmb_fx_rate_source(
        settings=settings,
        calendar=cal,
        client=client,
        clock=lambda: fixed_time,
    )

    assert isinstance(source, TcmbFxRateSource)
    assert source._calendar is cal
    assert source.source_id == "tcmb"


def test_build_tcmb_fx_rate_source_raises_type_error_for_invalid_arguments(
    tmp_path: Path,
) -> None:
    cal = MarketCalendar()
    settings = TcmbSourceSettings(
        cache_root=tmp_path,
        cache_policy=TcmbCachePolicy.prefer_cache,
    )

    with pytest.raises(TypeError, match="settings must be a TcmbSourceSettings"):
        build_tcmb_fx_rate_source("invalid", cal)  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="calendar must be a MarketCalendar"):
        build_tcmb_fx_rate_source(settings, "invalid")  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="clock must be a callable"):
        build_tcmb_fx_rate_source(settings, cal, clock=None)
