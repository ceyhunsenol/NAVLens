"""Tests for the FX-adjusted point-in-time fund-return reconciliation CLI."""

from pathlib import Path
from unittest.mock import patch

import pytest
from navlens.reconciliation.fx_cli import main
from navlens.reconciliation.fx_cli_args import parse_fx_reconciliation_cli_arguments

HOLDINGS_CSV = """\
fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight
AAL,2026-01-31,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,kap,INST_A,equity,{weight}
"""

SECURITY_PRICES_CSV = """\
instrument_id,market_date,price,currency,adjustment,available_at,ingested_at,source_id
INST_A,2026-01-30,100.0,USD,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,market
INST_A,2026-01-31,110.0,USD,total_return_adjusted,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,market
"""

FX_RATES_CSV = """\
base_currency,quote_currency,market_date,rate,kind,available_at,ingested_at,source_id
USD,TRY,2026-01-30,30.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,tcmb
USD,TRY,2026-01-31,31.0,non_cash_buying,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,tcmb
"""

FUND_PRICES_CSV = """\
fund_id,market_date,unit_price,available_at,ingested_at,source_id
AAL,2026-01-30,10.0,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,tefas
AAL,2026-01-31,11.2,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,tefas
"""


def _write(path: Path, content: str) -> Path:
    path.write_text(content, encoding="utf-8")
    return path


def _cli_arguments(
    tmp_path: Path,
    *,
    weight: float = 1.0,
    fx_rates: str = FX_RATES_CSV,
    fund_prices: str = FUND_PRICES_CSV,
) -> list[str]:
    holdings_path = _write(tmp_path / "holdings.csv", HOLDINGS_CSV.format(weight=weight))
    security_prices_path = _write(tmp_path / "security_prices.csv", SECURITY_PRICES_CSV)
    fx_rates_path = _write(tmp_path / "fx_rates.csv", fx_rates)
    fund_prices_path = _write(tmp_path / "fund_prices.csv", fund_prices)

    return [
        "--holdings-csv",
        str(holdings_path),
        "--security-prices-csv",
        str(security_prices_path),
        "--fx-rates-csv",
        str(fx_rates_path),
        "--fund-unit-prices-csv",
        str(fund_prices_path),
        "--fund-id",
        "AAL",
        "--holdings-source-id",
        "kap",
        "--security-price-source-id",
        "market",
        "--fx-source-id",
        "tcmb",
        "--fund-price-source-id",
        "tefas",
        "--required-fx-rate-kind",
        "non_cash_buying",
        "--max-fx-staleness-calendar-days",
        "5",
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


def test_cli_arguments_reuse_nested_fx_return_contribution_contract(tmp_path: Path) -> None:
    arguments = parse_fx_reconciliation_cli_arguments(_cli_arguments(tmp_path))

    assert arguments.fund_unit_prices_csv == tmp_path / "fund_prices.csv"
    assert arguments.fund_price_source_id == "tefas"
    fx_arguments = arguments.fx_contribution_args
    assert fx_arguments.fx_source_id == "tcmb"
    assert fx_arguments.fx_policy.required_fx_rate_kind.name == "non_cash_buying"
    assert fx_arguments.alignment_args.request.fund_id == "AAL"
    assert fx_arguments.alignment_args.request.policy.price_currency_policy.name == "permit_foreign"
    assert str(fx_arguments.target_period.period_start_date) == "2026-01-30"
    assert str(fx_arguments.target_period.period_end_date) == "2026-01-31"


def test_cli_success_and_deterministic_output(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    arguments = _cli_arguments(tmp_path)

    assert main(arguments) == 0
    first_output = capsys.readouterr().out
    assert main(arguments) == 0
    second_output = capsys.readouterr().out

    assert first_output == second_output
    assert "FX-Adjusted Return Contribution Report" in first_output
    assert "Selected FX Snapshots Provenance:" in first_output
    assert "pair: USD/TRY" in first_output
    assert "source_id: tcmb" in first_output
    assert "Fund Return Reconciliation" in first_output
    assert "Exact Period: 2026-01-30 to 2026-01-31" in first_output
    assert "Fund Price Source ID: tefas" in first_output
    assert "  Market Date: 2026-01-30" in first_output
    assert "  Unit Price: 10.000000" in first_output
    assert "  Market Date: 2026-01-31" in first_output
    assert "  Unit Price: 11.200000" in first_output
    assert "Published Fund Return (Decimal): 0.120000" in first_output
    assert "Observed Portfolio Contribution (Decimal): 0.136667" in first_output
    assert "Return Coverage (Ratio): 1.000000" in first_output
    assert "Reconciliation Residual (Decimal): -0.016667" in first_output
    assert "WARNING" not in first_output


def test_cli_partial_coverage_warning(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main(_cli_arguments(tmp_path, weight=0.5)) == 0

    assert (
        "WARNING: The observed portfolio contribution is incomplete (return coverage < 1.0)."
        in capsys.readouterr().out
    )


def test_cli_missing_fund_price_snapshot(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    missing_start = """\
fund_id,market_date,unit_price,available_at,ingested_at,source_id
AAL,2026-01-31,11.2,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,tefas
"""

    assert main(_cli_arguments(tmp_path, fund_prices=missing_start)) == 1
    error_output = capsys.readouterr().err
    assert "error:" in error_output
    assert "no exact fund unit-price snapshot found" in error_output


@pytest.mark.parametrize(
    ("fx_rates", "expected_error"),
    [
        (
            """\
base_currency,quote_currency,market_date,rate
USD,TRY,2026-01-30,30.0
""",
            "missing required columns",
        ),
        (
            """\
base_currency,quote_currency,market_date,rate,kind,available_at,ingested_at,source_id
USD,TRY,2026-01-30,30.0,invalid_kind,2026-02-01T10:00:00Z,2026-02-01T10:00:00Z,tcmb
""",
            "invalid kind",
        ),
    ],
)
def test_cli_invalid_fx_csv(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    fx_rates: str,
    expected_error: str,
) -> None:
    assert main(_cli_arguments(tmp_path, fx_rates=fx_rates)) == 1
    error_output = capsys.readouterr().err
    assert "error:" in error_output
    assert expected_error in error_output


@pytest.mark.parametrize(
    ("fund_prices", "expected_error"),
    [
        (
            """\
fund_id,market_date,unit_price
AAL,2026-01-30,10.0
""",
            "missing required columns",
        ),
        (
            """\
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
    fund_prices: str,
    expected_error: str,
) -> None:
    assert main(_cli_arguments(tmp_path, fund_prices=fund_prices)) == 1
    error_output = capsys.readouterr().err
    assert "error:" in error_output
    assert expected_error in error_output


def test_cli_delegates_without_reimplementing_financial_arithmetic(tmp_path: Path) -> None:
    with (
        patch(
            "navlens.reconciliation.fx_csv.reconcile_point_in_time_fx_adjusted_fund_return",
            return_value="reconciliation_result",
        ) as reconcile,
        patch(
            "navlens.reconciliation.fx_cli."
            "format_point_in_time_fx_adjusted_fund_return_reconciliation_result",
            return_value="report",
        ) as formatter,
    ):
        assert main(_cli_arguments(tmp_path)) == 0

    reconcile.assert_called_once()
    formatter.assert_called_once_with("reconciliation_result")
