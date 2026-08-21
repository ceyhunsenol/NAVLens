"""Tests for TCMB FX return contribution orchestration workflow."""

from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import navlens.alignment.fx_return_contribution_tcmb as tcmb_workflow
import pytest
from navlens import (
    AlignmentPolicy,
    CurrencyCode,
    FxRateKind,
    FxReturnPolicy,
    MarketDate,
    PriceAdjustment,
    PriceCurrencyPolicy,
    ReturnPeriod,
)
from navlens.alignment.cli_args import AlignmentCliArguments
from navlens.alignment.fx_result import PointInTimeFxAdjustedReturnContributionResult
from navlens.alignment.fx_return_contribution_tcmb import (
    calculate_fx_return_contribution_from_tcmb,
)
from navlens.alignment.fx_return_contribution_tcmb_cli_args import (
    FxReturnContributionTcmbCliArguments,
)
from navlens.alignment.request import PointInTimeAlignmentRequest
from navlens.sources.tcmb import (
    TcmbCachePolicy,
    TcmbHttpResponse,
    TcmbResponseClient,
    acquire_tcmb_daily_rates,
    store_tcmb_raw_artifact,
)
from navlens.sources.tcmb.composition import (
    TcmbSourceSettings,
    build_tcmb_market_calendar,
)
from navlens.sources.tcmb.revision_index import record_tcmb_revision


class FakeTcmbClient(TcmbResponseClient):
    """Fake client recording requested archive dates and returning synthetic XML."""

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
) -> None:
    cal = build_tcmb_market_calendar(())
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
            calendar=cal,
            retrieved_at=datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC),
        )
        entry = store_tcmb_raw_artifact(root, acq)
        record_tcmb_revision(root, acq, entry)


def _write_orchestration_test_files(tmp_path: Path) -> tuple[Path, Path]:
    holdings_file = tmp_path / "holdings.csv"
    holdings_file.write_text(
        "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
        "TEST_FUND,2026-01-01,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_h,INST_USD,equity,1.0\n",
        encoding="utf-8",
    )

    prices_file = tmp_path / "prices.csv"
    prices_file.write_text(
        "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at\n"
        "src_p,INST_USD,2026-01-01,10.0,USD,unadjusted,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n"
        "src_p,INST_USD,2026-01-02,11.0,USD,unadjusted,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n",
        encoding="utf-8",
    )

    return holdings_file, prices_file


def _make_tcmb_arguments(
    holdings_file: Path,
    prices_file: Path,
    cache_root: Path,
    cache_policy: TcmbCachePolicy,
    closed_dates: tuple[date, ...] = (),
) -> FxReturnContributionTcmbCliArguments:
    base_policy = AlignmentPolicy(
        fund_base_currency=CurrencyCode("TRY"),
        required_price_adjustment=PriceAdjustment("unadjusted"),
        pricing_as_of_date=MarketDate(2026, 1, 2),
        minimum_observations=2,
        max_staleness_calendar_days=5,
    )
    policy = base_policy.with_price_currency_policy(PriceCurrencyPolicy("permit_foreign"))
    request = PointInTimeAlignmentRequest(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        prediction_timestamp=datetime(2026, 1, 2, 10, 0, 0, tzinfo=UTC),
        policy=policy,
    )
    alignment_args = AlignmentCliArguments(
        holdings_csv=holdings_file,
        security_prices_csv=prices_file,
        request=request,
    )
    settings = TcmbSourceSettings(
        cache_root=cache_root,
        cache_policy=cache_policy,
        http_timeout_seconds=30.0,
    )
    return FxReturnContributionTcmbCliArguments(
        alignment_args=alignment_args,
        price_history_start_date=date(2026, 1, 1),
        closed_dates=closed_dates,
        fx_policy=FxReturnPolicy(FxRateKind("non_cash_buying"), 3),
        target_period=ReturnPeriod(MarketDate(2026, 1, 1), MarketDate(2026, 1, 2)),
        tcmb_source_settings=settings,
    )


def test_calculate_fx_return_contribution_from_tcmb_cache_only(tmp_path: Path) -> None:
    holdings_file, prices_file = _write_orchestration_test_files(tmp_path)
    cache_root = tmp_path / "tcmb_cache"
    cache_root.mkdir(parents=True)

    all_dates = [
        date(2025, 12, 29),
        date(2025, 12, 30),
        date(2025, 12, 31),
        date(2026, 1, 1),
        date(2026, 1, 2),
    ]
    rates_map = {
        date(2025, 12, 29): 29.8,
        date(2025, 12, 30): 29.9,
        date(2025, 12, 31): 29.95,
        date(2026, 1, 1): 30.0,
        date(2026, 1, 2): 31.0,
    }
    _seed_tcmb_cache_for_dates(cache_root, all_dates, rates_map)

    args = _make_tcmb_arguments(holdings_file, prices_file, cache_root, TcmbCachePolicy.cache_only)
    result = calculate_fx_return_contribution_from_tcmb(args)

    assert isinstance(result, PointInTimeFxAdjustedReturnContributionResult)
    assert len(result.contribution_result.component_contributions) == 1
    comp = result.contribution_result.component_contributions[0]
    assert comp.currency_adjustment.is_applied
    assert len(result.selected_fx_snapshots) > 0


def test_delegates_to_canonical_source_backed_owners(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    holdings_file, prices_file = _write_orchestration_test_files(tmp_path)
    cache_root = tmp_path / "tcmb_cache"
    cache_root.mkdir(parents=True)
    dates = [date(2025, 12, 29) + timedelta(days=offset) for offset in range(5)]
    _seed_tcmb_cache_for_dates(cache_root, dates, {value: 30.0 for value in dates})
    args = _make_tcmb_arguments(
        holdings_file,
        prices_file,
        cache_root,
        TcmbCachePolicy.cache_only,
    )
    observed: dict[str, object] = {}
    original_align = tcmb_workflow.align_point_in_time_from_source
    original_calculate = (
        tcmb_workflow.calculate_point_in_time_fx_adjusted_return_contribution_from_source
    )

    def align_spy(*call_args: object) -> object:
        observed["alignment_request"] = call_args[0]
        observed["price_history_start_date"] = call_args[3]
        result = original_align(*call_args)
        observed["alignment_result"] = result
        observed["align_calls"] = int(observed.get("align_calls", 0)) + 1
        return result

    def calculate_spy(*call_args: object) -> object:
        request = call_args[0]
        observed["request"] = request
        observed["calculate_calls"] = int(observed.get("calculate_calls", 0)) + 1
        return original_calculate(*call_args)

    monkeypatch.setattr(tcmb_workflow, "align_point_in_time_from_source", align_spy)
    monkeypatch.setattr(
        tcmb_workflow,
        "calculate_point_in_time_fx_adjusted_return_contribution_from_source",
        calculate_spy,
    )

    tcmb_workflow.calculate_fx_return_contribution_from_tcmb(args)

    assert observed["align_calls"] == 1
    assert observed["calculate_calls"] == 1
    assert observed["alignment_request"] is args.alignment_args.request
    assert observed["price_history_start_date"] is args.price_history_start_date
    assert observed["request"].alignment_result is observed["alignment_result"]


def test_calculate_fx_return_contribution_prefer_cache_with_fake_client(
    tmp_path: Path,
) -> None:
    holdings_file, prices_file = _write_orchestration_test_files(tmp_path)
    cache_root = tmp_path / "tcmb_cache"
    cache_root.mkdir(parents=True)

    client = FakeTcmbClient()
    clock_time = datetime(2026, 1, 2, 8, 0, 0, tzinfo=UTC)
    args = _make_tcmb_arguments(
        holdings_file, prices_file, cache_root, TcmbCachePolicy.prefer_cache
    )

    result = calculate_fx_return_contribution_from_tcmb(
        args,
        client=client,
        clock=lambda: clock_time,
    )

    assert isinstance(result, PointInTimeFxAdjustedReturnContributionResult)
    assert len(result.contribution_result.component_contributions) == 1
    assert len(client.requested_dates) > 0


def test_calculate_fx_return_contribution_raises_type_error_for_invalid_input() -> None:
    with pytest.raises(TypeError, match="FxReturnContributionTcmbCliArguments"):
        calculate_fx_return_contribution_from_tcmb("invalid")  # type: ignore[arg-type]
