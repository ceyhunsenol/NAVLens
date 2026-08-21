"""Tests for TCMB FX return contribution CLI main and exit code behavior."""

from datetime import UTC, date, datetime
from pathlib import Path
from unittest.mock import patch

import pytest
from navlens.alignment.fx_return_contribution_formatting import (
    format_fx_return_contribution_result,
)
from navlens.alignment.fx_return_contribution_tcmb import (
    calculate_fx_return_contribution_from_tcmb,
)
from navlens.alignment.fx_return_contribution_tcmb_cli import main
from navlens.alignment.fx_return_contribution_tcmb_cli_args import (
    parse_fx_return_contribution_tcmb_cli_arguments,
)
from navlens.sources.tcmb import (
    TcmbHttpResponse,
    TcmbResponseClient,
    acquire_tcmb_daily_rates,
    store_tcmb_raw_artifact,
)
from navlens.sources.tcmb.composition import build_tcmb_market_calendar
from navlens.sources.tcmb.revision_index import record_tcmb_revision


class FakeTcmbClient(TcmbResponseClient):
    """Fake client returning synthetic XML response."""

    def __init__(self, responses: dict[date | None, bytes] | None = None) -> None:
        self.responses = responses or {}

    def fetch_daily_rates_response(self, archive_date: date | None = None) -> TcmbHttpResponse:
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


def _seed_tcmb_cache(root: Path, dates: list[date], rates: dict[date, float]) -> None:
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


def _write_tcmb_cli_test_files(tmp_path: Path) -> list[str]:
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

    cache_dir = tmp_path / "tcmb_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
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
    _seed_tcmb_cache(cache_dir, all_dates, rates_map)

    return [
        "--holdings-csv",
        str(holdings_file),
        "--security-prices-csv",
        str(prices_file),
        "--fund-id",
        "TEST_FUND",
        "--holdings-source-id",
        "src_h",
        "--security-price-source-id",
        "src_p",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "unadjusted",
        "--prediction-timestamp",
        "2026-01-02T10:00:00Z",
        "--pricing-as-of-date",
        "2026-01-02",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
        "--return-start-date",
        "2026-01-01",
        "--return-end-date",
        "2026-01-02",
        "--required-fx-rate-kind",
        "non_cash_buying",
        "--max-fx-staleness-calendar-days",
        "3",
        "--price-history-start-date",
        "2026-01-01",
        "--tcmb-cache-root",
        str(cache_dir),
        "--tcmb-cache-policy",
        "cache_only",
    ]


def test_main_success_prints_formatted_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_tcmb_cli_test_files(tmp_path)
    args = parse_fx_return_contribution_tcmb_cli_arguments(argv)
    expected_result = calculate_fx_return_contribution_from_tcmb(args)
    expected_text = format_fx_return_contribution_result(expected_result)

    exit_code = main(argv)
    assert exit_code == 0

    captured = capsys.readouterr()
    assert captured.out == expected_text + "\n"
    assert captured.err == ""


def test_main_cache_miss_returns_1_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_tcmb_cli_test_files(tmp_path)
    empty_cache = tmp_path / "empty_cache"
    empty_cache.mkdir()
    argv[argv.index("--tcmb-cache-root") + 1] = str(empty_cache)

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: ")


def test_main_invalid_argument_returns_1_without_traceback(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    argv = _write_tcmb_cli_test_files(tmp_path)
    argv[argv.index("--price-history-start-date") + 1] = "invalid_date"

    exit_code = main(argv)
    assert exit_code == 1

    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err.startswith("error: invalid price_history_start_date")


def test_main_does_not_catch_unexpected_programmer_errors(tmp_path: Path) -> None:
    argv = _write_tcmb_cli_test_files(tmp_path)

    with patch(
        "navlens.alignment.fx_return_contribution_tcmb_cli.calculate_fx_return_contribution_from_tcmb",
        side_effect=TypeError("unexpected type error in code"),
    ):
        with pytest.raises(TypeError, match="unexpected type error in code"):
            main(argv)
