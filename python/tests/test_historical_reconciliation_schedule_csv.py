"""Tests for schedule CSV parsing and run configuration validation."""

from pathlib import Path
from unittest.mock import patch

import pytest
from navlens import CurrencyCode, MarketDate, PriceAdjustment
from navlens.reconciliation.historical import (
    CsvHistoricalScheduleSourceError,
    HistoricalReconciliationRunConfiguration,
    InvalidHistoricalReconciliationRunConfigurationError,
    read_historical_reconciliation_requests_csv,
)


def _valid_config() -> HistoricalReconciliationRunConfiguration:
    return HistoricalReconciliationRunConfiguration(
        fund_id="TEST_FUND",
        holdings_source_id="src_h",
        security_price_source_id="src_p",
        fund_price_source_id="src_f",
        fund_base_currency=CurrencyCode("TRY"),
        required_price_adjustment=PriceAdjustment("unadjusted"),
        minimum_observations=2,
        max_staleness_calendar_days=5,
    )


@pytest.mark.parametrize(
    "field_name",
    [
        "fund_id",
        "holdings_source_id",
        "security_price_source_id",
        "fund_price_source_id",
    ],
)
@pytest.mark.parametrize("blank_val", ["", "   ", "\t"])
def test_run_configuration_rejects_empty_identifiers(field_name: str, blank_val: str) -> None:
    kwargs: dict[str, object] = {
        "fund_id": "TEST_FUND",
        "holdings_source_id": "src_h",
        "security_price_source_id": "src_p",
        "fund_price_source_id": "src_f",
        "fund_base_currency": CurrencyCode("TRY"),
        "required_price_adjustment": PriceAdjustment("unadjusted"),
        "minimum_observations": 2,
        "max_staleness_calendar_days": 5,
    }
    kwargs[field_name] = blank_val

    with pytest.raises(
        InvalidHistoricalReconciliationRunConfigurationError,
        match=f"{field_name} must be a non-empty string",
    ):
        HistoricalReconciliationRunConfiguration(**kwargs)  # type: ignore[arg-type]


@pytest.mark.parametrize("min_obs", [0, 1])
def test_run_configuration_rejects_minimum_observations_below_2(
    min_obs: int,
) -> None:
    with pytest.raises(
        InvalidHistoricalReconciliationRunConfigurationError,
        match="minimum_observations must be at least 2",
    ):
        HistoricalReconciliationRunConfiguration(
            fund_id="TEST_FUND",
            holdings_source_id="src_h",
            security_price_source_id="src_p",
            fund_price_source_id="src_f",
            fund_base_currency=CurrencyCode("TRY"),
            required_price_adjustment=PriceAdjustment("unadjusted"),
            minimum_observations=min_obs,
            max_staleness_calendar_days=5,
        )


def test_run_configuration_rejects_negative_staleness() -> None:
    with pytest.raises(
        InvalidHistoricalReconciliationRunConfigurationError,
        match="max_staleness_calendar_days must be non-negative",
    ):
        HistoricalReconciliationRunConfiguration(
            fund_id="TEST_FUND",
            holdings_source_id="src_h",
            security_price_source_id="src_p",
            fund_price_source_id="src_f",
            fund_base_currency=CurrencyCode("TRY"),
            required_price_adjustment=PriceAdjustment("unadjusted"),
            minimum_observations=2,
            max_staleness_calendar_days=-1,
        )


@pytest.mark.parametrize("field_name", ["minimum_observations", "max_staleness_calendar_days"])
def test_run_configuration_rejects_bool_for_integer_fields(
    field_name: str,
) -> None:
    kwargs: dict[str, object] = {
        "fund_id": "TEST_FUND",
        "holdings_source_id": "src_h",
        "security_price_source_id": "src_p",
        "fund_price_source_id": "src_f",
        "fund_base_currency": CurrencyCode("TRY"),
        "required_price_adjustment": PriceAdjustment("unadjusted"),
        "minimum_observations": 2,
        "max_staleness_calendar_days": 5,
    }
    kwargs[field_name] = True

    with pytest.raises(TypeError, match=f"{field_name} must be a non-bool integer"):
        HistoricalReconciliationRunConfiguration(**kwargs)  # type: ignore[arg-type]


def test_run_configuration_validates_types() -> None:
    with pytest.raises(TypeError, match="fund_base_currency must be a CurrencyCode"):
        HistoricalReconciliationRunConfiguration(
            fund_id="TEST_FUND",
            holdings_source_id="src_h",
            security_price_source_id="src_p",
            fund_price_source_id="src_f",
            fund_base_currency="TRY",  # type: ignore[arg-type]
            required_price_adjustment=PriceAdjustment("unadjusted"),
            minimum_observations=2,
            max_staleness_calendar_days=5,
        )

    with pytest.raises(TypeError, match="required_price_adjustment must be a PriceAdjustment"):
        HistoricalReconciliationRunConfiguration(
            fund_id="TEST_FUND",
            holdings_source_id="src_h",
            security_price_source_id="src_p",
            fund_price_source_id="src_f",
            fund_base_currency=CurrencyCode("TRY"),
            required_price_adjustment="unadjusted",  # type: ignore[arg-type]
            minimum_observations=2,
            max_staleness_calendar_days=5,
        )


def test_reads_valid_schedule_csv_preserving_row_order(tmp_path: Path) -> None:
    csv_file = tmp_path / "schedule.csv"
    csv_content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
        "2026-01-02,2026-01-03,2026-01-03,2026-01-03T10:00:00+00:00\n"
    )
    csv_file.write_text(csv_content, encoding="utf-8")

    requests = read_historical_reconciliation_requests_csv(csv_file, _valid_config())
    assert len(requests) == 2

    assert requests[0].period.period_start_date == MarketDate(2026, 1, 1)
    assert requests[0].period.period_end_date == MarketDate(2026, 1, 2)
    assert requests[1].period.period_start_date == MarketDate(2026, 1, 2)
    assert requests[1].period.period_end_date == MarketDate(2026, 1, 3)


def test_reads_utf8_bom_schedule_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "schedule_bom.csv"
    csv_content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
    )
    csv_file.write_bytes(b"\xef\xbb\xbf" + csv_content.encode("utf-8"))

    requests = read_historical_reconciliation_requests_csv(csv_file, _valid_config())
    assert len(requests) == 1


def test_rejects_completely_empty_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "empty.csv"
    csv_file.write_bytes(b"")

    with pytest.raises(
        CsvHistoricalScheduleSourceError,
        match=r"empty schedule CSV file",
    ):
        read_historical_reconciliation_requests_csv(csv_file, _valid_config())


def test_rejects_header_only_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "header_only.csv"
    csv_file.write_text(
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CsvHistoricalScheduleSourceError,
        match=r"empty schedule CSV file",
    ):
        read_historical_reconciliation_requests_csv(csv_file, _valid_config())


def test_rejects_missing_required_header_reporting_exact_path_and_row_1(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "missing_header.csv"
    csv_file.write_text(
        "return_start_date,return_end_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02T10:00:00Z\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CsvHistoricalScheduleSourceError,
        match=r"at row 1: missing required columns: 'pricing_as_of_date'",
    ):
        read_historical_reconciliation_requests_csv(csv_file, _valid_config())


def test_rejects_blank_required_data_cell_reporting_exact_path_and_row(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "blank_cell.csv"
    csv_file.write_text(
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,,2026-01-02T10:00:00Z\n",
        encoding="utf-8",
    )

    with pytest.raises(
        CsvHistoricalScheduleSourceError,
        match=r"at row 2: missing required value for 'pricing_as_of_date'",
    ):
        read_historical_reconciliation_requests_csv(csv_file, _valid_config())


def test_unreadable_file_preserves_os_error_behavior_and_cause(
    tmp_path: Path,
) -> None:
    non_existent = tmp_path / "does_not_exist.csv"

    with pytest.raises(OSError) as exc_info:
        read_historical_reconciliation_requests_csv(non_existent, _valid_config())

    assert f"cannot read CSV file {non_existent}" in str(exc_info.value)
    assert exc_info.value.__cause__ is not None
    assert isinstance(exc_info.value.__cause__, FileNotFoundError)


@pytest.mark.parametrize(
    "invalid_date",
    ["20260101", "2026/01/01", "2026-1-1", "01-01-2026", "invalid"],
)
def test_rejects_non_strict_yyyy_mm_dd_dates(tmp_path: Path, invalid_date: str) -> None:
    csv_file = tmp_path / "bad_date.csv"
    content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        f"{invalid_date},2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
    )
    csv_file.write_text(content, encoding="utf-8")

    with pytest.raises(
        CsvHistoricalScheduleSourceError,
        match=r"at row 2: date must be YYYY-MM-DD format",
    ):
        read_historical_reconciliation_requests_csv(csv_file, _valid_config())


def test_rejects_naive_timestamp(tmp_path: Path) -> None:
    csv_file = tmp_path / "naive_ts.csv"
    content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T10:00:00\n"
    )
    csv_file.write_text(content, encoding="utf-8")

    with pytest.raises(
        CsvHistoricalScheduleSourceError,
        match=r"at row 2:",
    ):
        read_historical_reconciliation_requests_csv(csv_file, _valid_config())


def test_rejects_non_utc_timestamp(tmp_path: Path) -> None:
    csv_file = tmp_path / "non_utc_ts.csv"
    content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T13:00:00+03:00\n"
    )
    csv_file.write_text(content, encoding="utf-8")

    with pytest.raises(
        CsvHistoricalScheduleSourceError,
        match=r"at row 2:",
    ):
        read_historical_reconciliation_requests_csv(csv_file, _valid_config())


def test_reports_actual_physical_csv_line_number_with_blank_lines(
    tmp_path: Path,
) -> None:
    csv_file = tmp_path / "blank_lines.csv"
    content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
        "20260102,2026-01-03,2026-01-03,2026-01-03T10:00:00Z\n"
    )
    csv_file.write_text(content, encoding="utf-8")

    with pytest.raises(
        CsvHistoricalScheduleSourceError,
        match=r"at row 4: date must be YYYY-MM-DD format",
    ):
        read_historical_reconciliation_requests_csv(csv_file, _valid_config())


def test_unexpected_programmer_error_propagates_unchanged(tmp_path: Path) -> None:
    csv_file = tmp_path / "schedule.csv"
    content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
    )
    csv_file.write_text(content, encoding="utf-8")

    with patch(
        "navlens.reconciliation.historical._schedule_csv_entry.ReturnPeriod",
        side_effect=RuntimeError("unexpected construction bug"),
    ):
        with pytest.raises(RuntimeError, match="unexpected construction bug"):
            read_historical_reconciliation_requests_csv(csv_file, _valid_config())
