"""Tests for CSV workflow orchestration of historical FX reconciliation evaluation."""

from pathlib import Path

import pytest
from navlens import CurrencyCode, FxRateKind, PriceAdjustment
from navlens.reconciliation.historical import (
    HistoricalFxReconciliationRunConfiguration,
    HistoricalReconciliationRunConfiguration,
    build_historical_fx_reconciliation_dataset,
    evaluate_historical_reconciliation_dataset,
    read_historical_fx_reconciliation_requests_csv,
)
from navlens.reconciliation.historical_cli_args import (
    HistoricalReconciliationCliArguments,
)
from navlens.reconciliation.historical_fx_cli_args import (
    HistoricalFxReconciliationCliArguments,
)
from navlens.reconciliation.historical_fx_csv import (
    evaluate_historical_fx_reconciliation_from_csv,
)
from navlens.sources import (
    read_fund_unit_prices_csv,
    read_fx_rates_csv,
    read_holdings_snapshots,
    read_security_prices_csv,
)


def _write_valid_fx_test_csv_files(tmp_path: Path) -> dict[str, Path]:
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

    fx_file = tmp_path / "fx_rates.csv"
    fx_file.write_text(
        "source_id,base_currency,quote_currency,market_date,rate,kind,available_at,ingested_at\n"
        "src_fx,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n"
        "src_fx,USD,TRY,2026-01-02,31.0,non_cash_buying,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n"
        "src_fx,USD,TRY,2026-01-03,32.0,non_cash_buying,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z\n",
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
        "fx_rates": fx_file,
        "fund_prices": fund_prices_file,
    }


def _valid_fx_cli_args(files: dict[str, Path]) -> HistoricalFxReconciliationCliArguments:
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
        fx_source_id="src_fx",
        required_fx_rate_kind=FxRateKind("non_cash_buying"),
        max_fx_staleness_calendar_days=3,
    )
    return HistoricalFxReconciliationCliArguments(
        base_arguments=base_args,
        fx_rates_csv=files["fx_rates"],
        config=fx_config,
    )


def test_evaluates_historical_fx_reconciliation_from_csv_parity(tmp_path: Path) -> None:
    files = _write_valid_fx_test_csv_files(tmp_path)
    cli_args = _valid_fx_cli_args(files)

    evaluation = evaluate_historical_fx_reconciliation_from_csv(cli_args)

    requests = read_historical_fx_reconciliation_requests_csv(files["schedule"], cli_args.config)
    holdings = read_holdings_snapshots(files["holdings"])
    prices = read_security_prices_csv(files["prices"])
    fx_rates = read_fx_rates_csv(files["fx_rates"])
    fund_prices = read_fund_unit_prices_csv(files["fund_prices"])

    direct_ds = build_historical_fx_reconciliation_dataset(
        requests, holdings, prices, fx_rates, fund_prices
    )
    direct_eval = evaluate_historical_reconciliation_dataset(direct_ds)

    assert evaluation.total_period_count == direct_eval.total_period_count
    assert evaluation.evaluated_period_count == direct_eval.evaluated_period_count
    assert evaluation.skipped_period_count == direct_eval.skipped_period_count
    assert evaluation.scope == direct_eval.scope
    assert evaluation.metrics is not None and direct_eval.metrics is not None
    assert evaluation.metrics.sample_count == direct_eval.metrics.sample_count
    assert evaluation.metrics.mean_absolute_residual == pytest.approx(
        direct_eval.metrics.mean_absolute_residual
    )


def test_orchestration_excludes_future_holdings_snapshots_by_prediction_timestamp(
    tmp_path: Path,
) -> None:
    files = _write_valid_fx_test_csv_files(tmp_path)
    # Holdings snapshot on day 1 published at 12:00 (after 10:00 prediction timestamp)
    files["holdings"].write_text(
        "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
        "TEST_FUND,2026-01-01,2026-01-02T12:00:00Z,2026-01-02T12:00:00Z,src_h,INST_USD,equity,1.0\n"
        "TEST_FUND,2026-01-02,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z,src_h,INST_USD,equity,1.0\n",
        encoding="utf-8",
    )

    cli_args = _valid_fx_cli_args(files)
    evaluation = evaluate_historical_fx_reconciliation_from_csv(cli_args)

    assert evaluation.skipped_period_count == 1
    assert evaluation.missing_holdings_count == 1


def test_orchestration_excludes_future_security_price_snapshots_by_prediction_timestamp(
    tmp_path: Path,
) -> None:
    files = _write_valid_fx_test_csv_files(tmp_path)
    # Security price on 2026-01-02 available at 12:00 (after 10:00 prediction timestamp)
    files["prices"].write_text(
        "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at\n"
        "src_p,INST_USD,2026-01-01,10.0,USD,unadjusted,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n"
        "src_p,INST_USD,2026-01-02,10.5,USD,unadjusted,2026-01-02T12:00:00Z,2026-01-02T12:00:00Z\n"
        "src_p,INST_USD,2026-01-03,11.0,USD,unadjusted,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z\n",
        encoding="utf-8",
    )

    cli_args = _valid_fx_cli_args(files)
    evaluation = evaluate_historical_fx_reconciliation_from_csv(cli_args)

    # Prove point-in-time exclusion via coverage gap metric (period 1 coverage is 0.0)
    assert evaluation.evaluated_period_count == 2
    assert evaluation.skipped_period_count == 0
    assert evaluation.metrics is not None
    assert evaluation.metrics.mean_return_coverage == pytest.approx(0.5)
    assert evaluation.metrics.full_return_coverage_ratio == pytest.approx(0.5)


def test_orchestration_excludes_future_fx_rate_snapshots_by_prediction_timestamp(
    tmp_path: Path,
) -> None:
    files = _write_valid_fx_test_csv_files(tmp_path)
    # FX rates on 2026-01-01 and 2026-01-02 available at 12:00 (after 10:00 prediction timestamp)
    files["fx_rates"].write_text(
        "source_id,base_currency,quote_currency,market_date,rate,kind,available_at,ingested_at\n"
        "src_fx,USD,TRY,2026-01-01,30.0,non_cash_buying,2026-01-02T12:00:00Z,2026-01-02T12:00:00Z\n"
        "src_fx,USD,TRY,2026-01-02,31.0,non_cash_buying,2026-01-02T12:00:00Z,2026-01-02T12:00:00Z\n"
        "src_fx,USD,TRY,2026-01-03,32.0,non_cash_buying,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z\n",
        encoding="utf-8",
    )

    cli_args = _valid_fx_cli_args(files)
    evaluation = evaluate_historical_fx_reconciliation_from_csv(cli_args)

    # Missing FX evidence produces evaluated outcome with coverage gap
    assert evaluation.evaluated_period_count == 2
    assert evaluation.skipped_period_count == 0
    assert evaluation.metrics is not None
    assert evaluation.metrics.mean_return_coverage == pytest.approx(0.5)


def test_orchestration_excludes_future_fund_unit_price_snapshots_by_prediction_timestamp(
    tmp_path: Path,
) -> None:
    files = _write_valid_fx_test_csv_files(tmp_path)
    # Fund price for 2026-01-02 available at 12:00 (after 10:00 prediction timestamp)
    files["fund_prices"].write_text(
        "fund_id,market_date,available_at,ingested_at,source_id,unit_price\n"
        "TEST_FUND,2026-01-01,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,100.0\n"
        "TEST_FUND,2026-01-02,2026-01-02T12:00:00Z,2026-01-02T12:00:00Z,src_f,108.5\n"
        "TEST_FUND,2026-01-03,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z,src_f,118.0\n",
        encoding="utf-8",
    )

    cli_args = _valid_fx_cli_args(files)
    evaluation = evaluate_historical_fx_reconciliation_from_csv(cli_args)

    assert evaluation.skipped_period_count == 1
    assert evaluation.missing_fund_price_count == 1


def test_missing_exact_fund_price_produces_skipped_outcome(tmp_path: Path) -> None:
    files = _write_valid_fx_test_csv_files(tmp_path)
    # Remove fund price for 2026-01-03
    files["fund_prices"].write_text(
        "fund_id,market_date,available_at,ingested_at,source_id,unit_price\n"
        "TEST_FUND,2026-01-01,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,100.0\n"
        "TEST_FUND,2026-01-02,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,108.5\n",
        encoding="utf-8",
    )

    cli_args = _valid_fx_cli_args(files)
    evaluation = evaluate_historical_fx_reconciliation_from_csv(cli_args)

    assert evaluation.skipped_period_count == 1
    assert evaluation.missing_fund_price_count == 1


def test_orchestration_creates_no_files_on_disk(tmp_path: Path) -> None:
    files = _write_valid_fx_test_csv_files(tmp_path)
    cli_args = _valid_fx_cli_args(files)

    initial_files = set(tmp_path.rglob("*"))
    evaluate_historical_fx_reconciliation_from_csv(cli_args)
    final_files = set(tmp_path.rglob("*"))

    assert final_files == initial_files
