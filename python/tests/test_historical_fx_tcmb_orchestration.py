"""Tests for TCMB historical FX reconciliation workflow orchestration and composition."""

from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from navlens import (
    CurrencyCode,
    FxRateKind,
    MarketCalendar,
    MarketDate,
    PriceAdjustment,
    SessionKind,
    SessionOverride,
)
from navlens.reconciliation.historical import (
    HistoricalFxReconciliationRunConfiguration,
    HistoricalReconciliationRunConfiguration,
)
from navlens.reconciliation.historical_cli_args import (
    HistoricalReconciliationCliArguments,
)
from navlens.reconciliation.historical_fx_tcmb import (
    create_tcmb_acquisition_context_factory,
    evaluate_historical_fx_reconciliation_from_tcmb,
)
from navlens.reconciliation.historical_fx_tcmb_cli_args import (
    HistoricalFxTcmbCliArguments,
)
from navlens.sources.tcmb import (
    TCMB_SOURCE_ID,
    TcmbCachePolicy,
    TcmbHttpResponse,
    TcmbResponseClient,
    acquire_tcmb_daily_rates,
    store_tcmb_raw_artifact,
)
from navlens.sources.tcmb.revision_index import record_tcmb_revision


class FakeTcmbClient(TcmbResponseClient):
    """Fake client recording request archive dates and returning synthetic XML response."""

    def __init__(self, responses: dict[date | None, bytes] | None = None) -> None:
        self.responses = responses or {}
        self.requested_dates: list[date | None] = []

    def fetch_daily_rates_response(self, archive_date: date | None = None) -> TcmbHttpResponse:
        self.requested_dates.append(archive_date)
        body = self.responses.get(archive_date)
        if body is None:
            day_fmt = archive_date.strftime("%d.%m.%Y") if archive_date else "01.01.2026"
            iso_d = archive_date.isoformat() if archive_date else "2026-01-01"
            body = (
                f'<Tarih_Date Tarih="{day_fmt}" Date="{iso_d}" Bulten_No="2026/1">'
                f'<Currency CurrencyCode="USD">'
                f"<Unit>1</Unit><ForexBuying>30.0000</ForexBuying>"
                f"<ForexSelling>30.0500</ForexSelling>"
                f"</Currency></Tarih_Date>"
            ).encode()
        return TcmbHttpResponse(
            body=body,
            source_url=f"https://www.tcmb.gov.tr/kurlar/{archive_date}.xml",
            requested_archive_date=archive_date,
        )


def _seed_tcmb_cache_for_dates(
    root: Path,
    dates: list[date],
    rates: dict[date, float],
    calendar: MarketCalendar,
) -> None:
    for d in dates:
        rate_val = rates.get(d, 30.0)
        day_fmt = d.strftime("%d.%m.%Y")
        iso_d = d.isoformat()
        xml_bytes = (
            f'<Tarih_Date Tarih="{day_fmt}" Date="{iso_d}" Bulten_No="2026/1">'
            f'<Currency CurrencyCode="USD">'
            f"<Unit>1</Unit><ForexBuying>{rate_val:.4f}</ForexBuying>"
            f"<ForexSelling>{rate_val + 0.05:.4f}</ForexSelling>"
            f"</Currency></Tarih_Date>"
        ).encode()
        client = FakeTcmbClient(responses={d: xml_bytes})
        acq = acquire_tcmb_daily_rates(
            client,
            archive_date=d,
            calendar=calendar,
            retrieved_at=datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC),
        )
        entry = store_tcmb_raw_artifact(root, acq)
        record_tcmb_revision(root, acq, entry)


def _write_orchestration_test_files(tmp_path: Path) -> dict[str, Path]:
    schedule_file = tmp_path / "schedule.csv"
    schedule_file.write_text(
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
        "2026-01-02,2026-01-03,2026-01-03,2026-01-03T10:00:00Z\n",
        encoding="utf-8",
    )

    holdings_file = tmp_path / "holdings.csv"
    holdings_file.write_text(
        "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
        "TEST_FUND,2026-01-01,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_h,INST_USD,equity,1.0\n"
        "TEST_FUND,2026-01-02,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z,src_h,INST_USD,equity,1.0\n",
        encoding="utf-8",
    )

    prices_file = tmp_path / "security_prices.csv"
    prices_file.write_text(
        "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at\n"
        "src_p,INST_USD,2026-01-01,10.0,USD,unadjusted,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n"
        "src_p,INST_USD,2026-01-02,10.5,USD,unadjusted,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n"
        "src_p,INST_USD,2026-01-03,11.0,USD,unadjusted,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z\n",
        encoding="utf-8",
    )

    fund_prices_file = tmp_path / "fund_prices.csv"
    fund_prices_file.write_text(
        "fund_id,market_date,available_at,ingested_at,source_id,unit_price\n"
        "TEST_FUND,2026-01-01,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,100.0\n"
        "TEST_FUND,2026-01-02,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,108.5\n"
        "TEST_FUND,2026-01-03,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z,src_f,118.0\n",
        encoding="utf-8",
    )

    return {
        "schedule": schedule_file,
        "holdings": holdings_file,
        "prices": prices_file,
        "fund_prices": fund_prices_file,
    }


def _make_tcmb_cli_arguments(
    files: dict[str, Path],
    cache_root: Path,
    policy: TcmbCachePolicy = TcmbCachePolicy.cache_only,
) -> HistoricalFxTcmbCliArguments:
    base_config = HistoricalReconciliationRunConfiguration(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        fund_price_source_id="src_f",
        fund_base_currency=CurrencyCode("TRY"),
        required_price_adjustment=PriceAdjustment("unadjusted"),
        minimum_observations=2,
        max_staleness_calendar_days=5,
    )
    base_args = HistoricalReconciliationCliArguments(
        schedule_csv=files["schedule"],
        holdings_csv=files["holdings"],
        security_prices_csv=files["prices"],
        fund_unit_prices_csv=files["fund_prices"],
        output_format="text",
        config=base_config,
    )
    fx_config = HistoricalFxReconciliationRunConfiguration(
        base=base_config,
        fx_source_id=TCMB_SOURCE_ID,
        required_fx_rate_kind=FxRateKind("non_cash_buying"),
        max_fx_staleness_calendar_days=3,
    )
    return HistoricalFxTcmbCliArguments(
        base_arguments=base_args,
        price_history_start_date=date(2026, 1, 1),
        closed_dates=(),
        tcmb_cache_root=cache_root,
        tcmb_cache_policy=policy,
        tcmb_http_timeout_seconds=30.0,
        config=fx_config,
    )


def test_acquisition_context_factory_invokes_clock_and_shares_calendar_and_client() -> None:
    client = FakeTcmbClient()
    calendar = MarketCalendar([SessionOverride(MarketDate(2026, 1, 1), SessionKind("closed"))])
    timestamps = [
        datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC),
        datetime(2026, 1, 2, 10, 0, 5, tzinfo=UTC),
    ]
    call_index = 0

    def fake_clock() -> datetime:
        nonlocal call_index
        val = timestamps[call_index]
        call_index += 1
        return val

    factory = create_tcmb_acquisition_context_factory(calendar, client, clock=fake_clock)

    ctx1 = factory(MarketDate(2026, 1, 2))
    ctx2 = factory(MarketDate(2026, 1, 3))

    assert ctx1 is not ctx2
    assert ctx1.retrieved_at == timestamps[0]
    assert ctx2.retrieved_at == timestamps[1]
    assert ctx1.calendar is calendar
    assert ctx2.calendar is calendar
    assert ctx1.client is client
    assert ctx2.client is client


def test_evaluate_historical_fx_reconciliation_from_tcmb_cache_only(tmp_path: Path) -> None:
    files = _write_orchestration_test_files(tmp_path)
    cache_root = tmp_path / "tcmb_cache"
    cache_root.mkdir(parents=True)

    cal = MarketCalendar()
    all_dates = [
        date(2025, 12, 29),
        date(2025, 12, 30),
        date(2025, 12, 31),
        date(2026, 1, 1),
        date(2026, 1, 2),
        date(2026, 1, 3),
    ]
    rates_map = {
        date(2025, 12, 29): 29.8,
        date(2025, 12, 30): 29.9,
        date(2025, 12, 31): 29.95,
        date(2026, 1, 1): 30.0,
        date(2026, 1, 2): 31.0,
        date(2026, 1, 3): 32.0,
    }
    _seed_tcmb_cache_for_dates(cache_root, all_dates, rates_map, cal)

    args = _make_tcmb_cli_arguments(files, cache_root, TcmbCachePolicy.cache_only)
    evaluation = evaluate_historical_fx_reconciliation_from_tcmb(args)

    assert evaluation.total_period_count == 2
    assert evaluation.evaluated_period_count == 2
    assert evaluation.skipped_period_count == 0
    assert evaluation.metrics is not None
    assert evaluation.metrics.sample_count == 2


def test_evaluate_historical_fx_prefer_cache_with_fake_client(
    tmp_path: Path,
) -> None:
    files = _write_orchestration_test_files(tmp_path)
    cache_root = tmp_path / "tcmb_cache"
    cache_root.mkdir(parents=True)

    client = FakeTcmbClient()
    args = _make_tcmb_cli_arguments(files, cache_root, TcmbCachePolicy.prefer_cache)

    clock_time = datetime(2026, 1, 5, 8, 0, 0, tzinfo=UTC)
    evaluation = evaluate_historical_fx_reconciliation_from_tcmb(
        args,
        client=client,
        clock=lambda: clock_time,
    )

    assert evaluation.total_period_count == 2
    assert len(client.requested_dates) > 0


def test_evaluate_historical_fx_reconciliation_raises_type_error_for_invalid_input() -> None:
    with pytest.raises(TypeError, match="HistoricalFxTcmbCliArguments"):
        evaluate_historical_fx_reconciliation_from_tcmb("invalid_args")  # type: ignore[arg-type]
