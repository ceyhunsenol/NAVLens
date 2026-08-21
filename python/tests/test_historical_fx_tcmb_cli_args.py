"""Tests for TCMB historical FX reconciliation CLI argument parsing and validation."""

import math
from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest
from navlens import CurrencyCode, FxRateKind, PriceAdjustment
from navlens.reconciliation.historical.errors import (
    InvalidHistoricalReconciliationRunConfigurationError,
)
from navlens.reconciliation.historical_fx_tcmb_cli_args import (
    HistoricalFxTcmbCliArguments,
    InvalidHistoricalFxTcmbCliArgumentsError,
    build_historical_fx_tcmb_cli_parser,
    extract_historical_fx_tcmb_cli_arguments,
    parse_historical_fx_tcmb_cli_arguments,
)
from navlens.sources.tcmb import TCMB_SOURCE_ID, TcmbCachePolicy


def _valid_tcmb_cli_argv(tmp_path: Path) -> list[str]:
    return [
        "--schedule-csv",
        str(tmp_path / "schedule.csv"),
        "--holdings-csv",
        str(tmp_path / "holdings.csv"),
        "--security-prices-csv",
        str(tmp_path / "prices.csv"),
        "--fund-unit-prices-csv",
        str(tmp_path / "fund_prices.csv"),
        "--fund-id",
        "TEST_FUND",
        "--holdings-source-id",
        "src_h",
        "--security-price-source-id",
        "src_p",
        "--fund-price-source-id",
        "src_f",
        "--fund-base-currency",
        "TRY",
        "--price-adjustment",
        "unadjusted",
        "--minimum-observations",
        "2",
        "--max-staleness-calendar-days",
        "5",
        "--required-fx-rate-kind",
        "non_cash_buying",
        "--max-fx-staleness-calendar-days",
        "3",
        "--price-history-start-date",
        "2026-01-01",
        "--tcmb-cache-root",
        str(tmp_path / "tcmb_cache"),
        "--tcmb-cache-policy",
        "cache_only",
    ]


def test_parse_valid_arguments_with_defaults(tmp_path: Path) -> None:
    argv = _valid_tcmb_cli_argv(tmp_path)
    args = parse_historical_fx_tcmb_cli_arguments(argv)

    assert isinstance(args, HistoricalFxTcmbCliArguments)
    assert args.base_arguments.schedule_csv == tmp_path / "schedule.csv"
    assert args.base_arguments.holdings_csv == tmp_path / "holdings.csv"
    assert args.base_arguments.security_prices_csv == tmp_path / "prices.csv"
    assert args.base_arguments.fund_unit_prices_csv == tmp_path / "fund_prices.csv"
    assert args.base_arguments.output_format == "text"
    assert args.price_history_start_date == date(2026, 1, 1)
    assert args.closed_dates == ()
    assert args.tcmb_cache_root == tmp_path / "tcmb_cache"
    assert args.tcmb_cache_policy is TcmbCachePolicy.cache_only
    assert args.tcmb_http_timeout_seconds == 30.0

    # Config verifies canonical TCMB source identity
    assert args.config.fx_source_id == TCMB_SOURCE_ID
    assert args.config.required_fx_rate_kind == FxRateKind("non_cash_buying")
    assert args.config.max_fx_staleness_calendar_days == 3
    assert args.config.base.fund_id == "TEST_FUND"
    assert args.config.base.fund_base_currency == CurrencyCode("TRY")
    assert args.config.base.required_price_adjustment == PriceAdjustment("unadjusted")


def test_parse_explicit_cache_policies_and_timeout(tmp_path: Path) -> None:
    argv_prefer = _valid_tcmb_cli_argv(tmp_path)
    argv_prefer[argv_prefer.index("--tcmb-cache-policy") + 1] = "prefer_cache"
    argv_prefer.extend(["--tcmb-http-timeout-seconds", "15.5"])

    args_prefer = parse_historical_fx_tcmb_cli_arguments(argv_prefer)
    assert args_prefer.tcmb_cache_policy is TcmbCachePolicy.prefer_cache
    assert args_prefer.tcmb_http_timeout_seconds == 15.5

    argv_refresh = _valid_tcmb_cli_argv(tmp_path)
    argv_refresh[argv_refresh.index("--tcmb-cache-policy") + 1] = "refresh"
    args_refresh = parse_historical_fx_tcmb_cli_arguments(argv_refresh)
    assert args_refresh.tcmb_cache_policy is TcmbCachePolicy.refresh


def test_parse_repeated_closed_dates_preserves_exact_dates(tmp_path: Path) -> None:
    argv = _valid_tcmb_cli_argv(tmp_path) + [
        "--closed-date",
        "2026-01-15",
        "--closed-date",
        "2026-01-16",
    ]
    args = parse_historical_fx_tcmb_cli_arguments(argv)

    assert args.closed_dates == (date(2026, 1, 15), date(2026, 1, 16))


def test_invalid_price_history_start_date_raises_typed_error(tmp_path: Path) -> None:
    parser = build_historical_fx_tcmb_cli_parser()
    argv = _valid_tcmb_cli_argv(tmp_path)
    argv[argv.index("--price-history-start-date") + 1] = "invalid-date"

    parsed_ns = parser.parse_args(argv)
    with pytest.raises(
        InvalidHistoricalFxTcmbCliArgumentsError,
        match="invalid price_history_start_date",
    ) as exc_info:
        extract_historical_fx_tcmb_cli_arguments(parsed_ns)

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_invalid_closed_date_raises_typed_error(tmp_path: Path) -> None:
    parser = build_historical_fx_tcmb_cli_parser()
    argv = _valid_tcmb_cli_argv(tmp_path) + ["--closed-date", "2026/01/15"]

    parsed_ns = parser.parse_args(argv)
    with pytest.raises(
        InvalidHistoricalFxTcmbCliArgumentsError,
        match="invalid closed_date",
    ) as exc_info:
        extract_historical_fx_tcmb_cli_arguments(parsed_ns)

    assert isinstance(exc_info.value.__cause__, ValueError)


def test_duplicate_closed_date_raises_typed_error(tmp_path: Path) -> None:
    parser = build_historical_fx_tcmb_cli_parser()
    argv = _valid_tcmb_cli_argv(tmp_path) + [
        "--closed-date",
        "2026-01-15",
        "--closed-date",
        "2026-01-15",
    ]

    parsed_ns = parser.parse_args(argv)
    with pytest.raises(
        InvalidHistoricalFxTcmbCliArgumentsError,
        match="must not contain duplicates",
    ):
        extract_historical_fx_tcmb_cli_arguments(parsed_ns)


@pytest.mark.parametrize("invalid_timeout", [0.0, -1.0, -0.01, math.nan, math.inf])
def test_invalid_timeout_raises_typed_error(tmp_path: Path, invalid_timeout: float) -> None:
    parser = build_historical_fx_tcmb_cli_parser()
    argv = _valid_tcmb_cli_argv(tmp_path)
    argv.extend(["--tcmb-http-timeout-seconds", str(invalid_timeout)])

    parsed_ns = parser.parse_args(argv)
    with pytest.raises(
        InvalidHistoricalFxTcmbCliArgumentsError,
        match="tcmb_http_timeout_seconds must be a finite positive number",
    ):
        extract_historical_fx_tcmb_cli_arguments(parsed_ns)


def test_negative_max_fx_staleness_raises_run_config_error(tmp_path: Path) -> None:
    argv = _valid_tcmb_cli_argv(tmp_path)
    argv[argv.index("--max-fx-staleness-calendar-days") + 1] = "-1"

    parser = build_historical_fx_tcmb_cli_parser()
    parsed_ns = parser.parse_args(argv)

    with pytest.raises(
        InvalidHistoricalReconciliationRunConfigurationError,
        match="max_fx_staleness_calendar_days must be non-negative",
    ):
        extract_historical_fx_tcmb_cli_arguments(parsed_ns)


def test_invalid_cache_policy_choice_exits_with_2(tmp_path: Path) -> None:
    argv = _valid_tcmb_cli_argv(tmp_path)
    argv[argv.index("--tcmb-cache-policy") + 1] = "invalid_policy"

    with pytest.raises(SystemExit) as exc_info:
        parse_historical_fx_tcmb_cli_arguments(argv)

    assert exc_info.value.code == 2


def test_direct_contract_rejects_non_tuple_closed_dates(tmp_path: Path) -> None:
    arguments = parse_historical_fx_tcmb_cli_arguments(_valid_tcmb_cli_argv(tmp_path))

    with pytest.raises(
        InvalidHistoricalFxTcmbCliArgumentsError,
        match="closed_dates must be a tuple",
    ):
        replace(arguments, closed_dates=[date(2026, 1, 1)])  # type: ignore[arg-type]


def test_direct_contract_rejects_noncanonical_fx_source_id(tmp_path: Path) -> None:
    arguments = parse_historical_fx_tcmb_cli_arguments(_valid_tcmb_cli_argv(tmp_path))
    invalid_config = replace(arguments.config, fx_source_id="not_tcmb")

    with pytest.raises(
        InvalidHistoricalFxTcmbCliArgumentsError,
        match="canonical TCMB source ID",
    ):
        replace(arguments, config=invalid_config)
