"""Tests for CSV workflow orchestration of historical reconciliation evaluation."""

from pathlib import Path

import pytest
from navlens import CurrencyCode, PriceAdjustment
from navlens.reconciliation.historical import (
    HistoricalReconciliationRunConfiguration,
    build_historical_reconciliation_dataset,
    evaluate_historical_reconciliation_dataset,
    read_historical_reconciliation_requests_csv,
)
from navlens.reconciliation.historical_cli_args import HistoricalReconciliationCliArguments
from navlens.reconciliation.historical_csv import evaluate_historical_reconciliation_from_csv
from navlens.sources import (
    read_fund_unit_prices_csv,
    read_holdings_snapshots,
    read_security_prices_csv,
)


def _write_valid_test_csv_files(tmp_path: Path) -> dict[str, Path]:
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
        "TEST_FUND,2026-01-01,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_h,INST_A,equity,1.0\n"
        "TEST_FUND,2026-01-02,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z,src_h,INST_A,equity,1.0\n",
        encoding="utf-8",
    )

    prices_file = tmp_path / "security_prices.csv"
    prices_file.write_text(
        "source_id,instrument_id,market_date,price,currency,adjustment,available_at,ingested_at\n"
        "src_p,INST_A,2026-01-01,100.0,TRY,unadjusted,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n"
        "src_p,INST_A,2026-01-02,105.0,TRY,unadjusted,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z\n"
        "src_p,INST_A,2026-01-03,110.0,TRY,unadjusted,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z\n",
        encoding="utf-8",
    )

    fund_prices_file = tmp_path / "fund_prices.csv"
    fund_prices_file.write_text(
        "fund_id,market_date,available_at,ingested_at,source_id,unit_price\n"
        "TEST_FUND,2026-01-01,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,10.0\n"
        "TEST_FUND,2026-01-02,2026-01-02T08:00:00Z,2026-01-02T08:00:00Z,src_f,10.5\n"
        "TEST_FUND,2026-01-03,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z,src_f,11.0\n",
        encoding="utf-8",
    )

    return {
        "schedule": schedule_file,
        "holdings": holdings_file,
        "prices": prices_file,
        "fund_prices": fund_prices_file,
    }


def test_evaluates_historical_reconciliation_from_csv_parity(tmp_path: Path) -> None:
    files = _write_valid_test_csv_files(tmp_path)
    config = HistoricalReconciliationRunConfiguration(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        fund_price_source_id="src_f",
        fund_base_currency=CurrencyCode("TRY"),
        required_price_adjustment=PriceAdjustment("unadjusted"),
        minimum_observations=2,
        max_staleness_calendar_days=5,
    )
    cli_args = HistoricalReconciliationCliArguments(
        schedule_csv=files["schedule"],
        holdings_csv=files["holdings"],
        security_prices_csv=files["prices"],
        fund_unit_prices_csv=files["fund_prices"],
        output_format="text",
        config=config,
    )

    evaluation = evaluate_historical_reconciliation_from_csv(cli_args)

    requests = read_historical_reconciliation_requests_csv(files["schedule"], config)
    holdings = read_holdings_snapshots(files["holdings"])
    prices = read_security_prices_csv(files["prices"])
    fund_prices = read_fund_unit_prices_csv(files["fund_prices"])

    direct_ds = build_historical_reconciliation_dataset(requests, holdings, prices, fund_prices)
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


def test_orchestration_excludes_future_snapshots_by_prediction_timestamp(
    tmp_path: Path,
) -> None:
    files = _write_valid_test_csv_files(tmp_path)

    # Overwrite holdings file with future published_at timestamp (12:00 vs 10:00)
    files["holdings"].write_text(
        "fund_id,effective_date,published_at,ingested_at,source_id,instrument_id,asset_class,weight\n"
        "TEST_FUND,2026-01-01,2026-01-02T12:00:00Z,2026-01-02T12:00:00Z,src_h,INST_A,equity,1.0\n"
        "TEST_FUND,2026-01-02,2026-01-03T08:00:00Z,2026-01-03T08:00:00Z,src_h,INST_A,equity,1.0\n",
        encoding="utf-8",
    )

    config = HistoricalReconciliationRunConfiguration(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        fund_price_source_id="src_f",
        fund_base_currency=CurrencyCode("TRY"),
        required_price_adjustment=PriceAdjustment("unadjusted"),
        minimum_observations=2,
        max_staleness_calendar_days=5,
    )
    cli_args = HistoricalReconciliationCliArguments(
        schedule_csv=files["schedule"],
        holdings_csv=files["holdings"],
        security_prices_csv=files["prices"],
        fund_unit_prices_csv=files["fund_prices"],
        output_format="text",
        config=config,
    )

    evaluation = evaluate_historical_reconciliation_from_csv(cli_args)
    # First period will be skipped due to missing holding snapshot as of prediction timestamp
    assert evaluation.skipped_period_count == 1
    assert evaluation.missing_holdings_count == 1
