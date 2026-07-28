"""Tests for point-in-time fund-return reconciliation CLI."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from navlens.reconciliation.cli import main
from navlens.reconciliation.cli_args import parse_reconciliation_cli_arguments


def _create_file(path: Path, content: str) -> str:
    path.write_text(content.lstrip(), encoding="utf-8")
    return str(path)


def test_cli_arguments_reuse_nested_return_contribution_contract(tmp_path: Path) -> None:
    fund_prices_path = tmp_path / "fund_prices.csv"
    arguments = parse_reconciliation_cli_arguments(
        [
            "--holdings-csv",
            str(tmp_path / "holdings.csv"),
            "--security-prices-csv",
            str(tmp_path / "security_prices.csv"),
            "--fund-unit-prices-csv",
            str(fund_prices_path),
            "--fund-id",
            "AAL",
            "--holdings-source-id",
            "kap",
            "--security-price-source-id",
            "market",
            "--fund-price-source-id",
            "tefas",
            "--prediction-timestamp",
            "2026-02-01T12:00:00Z",
            "--pricing-as-of-date",
            "2026-01-31",
            "--fund-base-currency",
            "TRY",
            "--price-adjustment",
            "total_return_adjusted",
            "--minimum-observations",
            "2",
            "--max-staleness-calendar-days",
            "5",
            "--return-start-date",
            "2026-01-30",
            "--return-end-date",
            "2026-01-31",
        ]
    )

    assert arguments.fund_unit_prices_csv == fund_prices_path
    assert arguments.fund_price_source_id == "tefas"
    assert arguments.contribution_args.alignment_args.request.fund_id == "AAL"
    assert str(arguments.contribution_args.target_period.period_start_date) == "2026-01-30"
    assert str(arguments.contribution_args.target_period.period_end_date) == "2026-01-31"


def test_cli_success(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings_csv = _create_file(
        tmp_path / "holdings.csv",
        """
fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight
AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,kap,INST_A,equity,1.0
""",
    )
    prices_csv = _create_file(
        tmp_path / "prices.csv",
        """
instrument_id,market_date,price,currency,adjustment,available_at,ingested_at,source_id
INST_A,2026-01-30,100.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,market
INST_A,2026-01-31,110.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,market
""",
    )
    fund_prices_csv = _create_file(
        tmp_path / "fund_prices.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
AAL,2026-01-30,10.0,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,tefas
AAL,2026-01-31,11.2,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,tefas
""",
    )

    args = [
        "--holdings-csv",
        holdings_csv,
        "--security-prices-csv",
        prices_csv,
        "--fund-unit-prices-csv",
        fund_prices_csv,
        "--fund-id",
        "AAL",
        "--holdings-source-id",
        "kap",
        "--security-price-source-id",
        "market",
        "--fund-price-source-id",
        "tefas",
        "--prediction-timestamp",
        "2026-02-01T12:00:00Z",
        "--pricing-as-of-date",
        "2026-01-31",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "total_return_adjusted",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
        "--return-start-date",
        "2026-01-30",
        "--return-end-date",
        "2026-01-31",
    ]

    with patch.object(sys, "argv", ["navlens-reconcile-fund-csv", *args]):
        result = main()

    assert result == 0
    captured = capsys.readouterr()
    assert "Fund Return Reconciliation" in captured.out
    assert "Exact Period: 2026-01-30 to 2026-01-31" in captured.out
    assert "Fund Price Source ID: tefas" in captured.out
    assert "Published Fund Return (Decimal): 0.120000" in captured.out
    assert "Observed Portfolio Contribution (Decimal): 0.100000" in captured.out
    assert "Return Coverage (Ratio): 1.000000" in captured.out
    assert "Reconciliation Residual (Decimal): 0.020000" in captured.out


def test_cli_missing_start_snapshot(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings_csv = _create_file(
        tmp_path / "holdings.csv",
        """
fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight
AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,kap,INST_A,equity,1.0
""",
    )
    prices_csv = _create_file(
        tmp_path / "prices.csv",
        """
instrument_id,market_date,price,currency,adjustment,available_at,ingested_at,source_id
INST_A,2026-01-30,100.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,market
INST_A,2026-01-31,110.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,market
""",
    )
    fund_prices_csv = _create_file(
        tmp_path / "fund_prices.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
AAL,2026-01-31,11.2,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,tefas
""",
    )

    args = [
        "--holdings-csv",
        holdings_csv,
        "--security-prices-csv",
        prices_csv,
        "--fund-unit-prices-csv",
        fund_prices_csv,
        "--fund-id",
        "AAL",
        "--holdings-source-id",
        "kap",
        "--security-price-source-id",
        "market",
        "--fund-price-source-id",
        "tefas",
        "--prediction-timestamp",
        "2026-02-01T12:00:00Z",
        "--pricing-as-of-date",
        "2026-01-31",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "total_return_adjusted",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
        "--return-start-date",
        "2026-01-30",
        "--return-end-date",
        "2026-01-31",
    ]

    result = main(args)
    assert result == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "no exact fund unit-price snapshot found" in captured.err
    assert "2026-01-30" in captured.err


def test_cli_missing_end_snapshot(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    holdings_csv = _create_file(
        tmp_path / "holdings.csv",
        """
fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight
AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,kap,INST_A,equity,1.0
""",
    )
    prices_csv = _create_file(
        tmp_path / "prices.csv",
        """
instrument_id,market_date,price,currency,adjustment,available_at,ingested_at,source_id
INST_A,2026-01-30,100.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,market
INST_A,2026-01-31,110.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,market
""",
    )
    fund_prices_csv = _create_file(
        tmp_path / "fund_prices.csv",
        """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
AAL,2026-01-30,10.0,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,tefas
""",
    )

    args = [
        "--holdings-csv",
        holdings_csv,
        "--security-prices-csv",
        prices_csv,
        "--fund-unit-prices-csv",
        fund_prices_csv,
        "--fund-id",
        "AAL",
        "--holdings-source-id",
        "kap",
        "--security-price-source-id",
        "market",
        "--fund-price-source-id",
        "tefas",
        "--prediction-timestamp",
        "2026-02-01T12:00:00Z",
        "--pricing-as-of-date",
        "2026-01-31",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "total_return_adjusted",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
        "--return-start-date",
        "2026-01-30",
        "--return-end-date",
        "2026-01-31",
    ]

    result = main(args)
    assert result == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert "no exact fund unit-price snapshot found" in captured.err
    assert "2026-01-31" in captured.err


@pytest.mark.parametrize(
    ("fund_price_content", "expected_error"),
    [
        (
            """
fund_id,market_date,unit_price
AAL,2026-01-30,10.0
""",
            "missing required columns",
        ),
        (
            """
fund_id,market_date,unit_price,available_at,ingested_at,source_id
AAL,2026-01-30,10.0,2026-02-01T10:00:00+03:00,2026-02-01T10:00:00+03:00,tefas
""",
            "must be in UTC",
        ),
    ],
)
def test_cli_invalid_fund_price_csv(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    fund_price_content: str,
    expected_error: str,
) -> None:
    holdings_csv = _create_file(
        tmp_path / "holdings.csv",
        """
fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight
AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,kap,INST_A,equity,1.0
""",
    )
    prices_csv = _create_file(
        tmp_path / "prices.csv",
        """
instrument_id,market_date,price,currency,adjustment,available_at,ingested_at,source_id
INST_A,2026-01-30,100.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,market
INST_A,2026-01-31,110.0,TRY,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,market
""",
    )
    fund_prices_csv = _create_file(
        tmp_path / "fund_prices.csv",
        fund_price_content,
    )

    args = [
        "--holdings-csv",
        holdings_csv,
        "--security-prices-csv",
        prices_csv,
        "--fund-unit-prices-csv",
        fund_prices_csv,
        "--fund-id",
        "AAL",
        "--holdings-source-id",
        "kap",
        "--security-price-source-id",
        "market",
        "--fund-price-source-id",
        "tefas",
        "--prediction-timestamp",
        "2026-02-01T12:00:00Z",
        "--pricing-as-of-date",
        "2026-01-31",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "total_return_adjusted",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
        "--return-start-date",
        "2026-01-30",
        "--return-end-date",
        "2026-01-31",
    ]

    result = main(args)
    assert result == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err
    assert expected_error in captured.err
