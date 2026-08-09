"""Tests for FX historical reconciliation schedule CSV parsing and configuration."""

from pathlib import Path
from unittest.mock import patch

import pytest
from navlens import (
    CurrencyCode,
    FxRateKind,
    MarketDate,
    PriceAdjustment,
    PriceCurrencyPolicy,
)
from navlens.reconciliation.historical import (
    CsvHistoricalScheduleSourceError,
    HistoricalFxReconciliationRunConfiguration,
    HistoricalReconciliationRunConfiguration,
    InvalidHistoricalReconciliationRunConfigurationError,
    read_historical_fx_reconciliation_requests_csv,
)


def _valid_base_config() -> HistoricalReconciliationRunConfiguration:
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


def _valid_fx_config() -> HistoricalFxReconciliationRunConfiguration:
    return HistoricalFxReconciliationRunConfiguration(
        base=_valid_base_config(),
        fx_source_id="src_fx",
        required_fx_rate_kind=FxRateKind("non_cash_buying"),
        max_fx_staleness_calendar_days=3,
    )


def test_fx_run_configuration_valid_instantiation() -> None:
    config = _valid_fx_config()
    assert config.fx_source_id == "src_fx"
    assert config.required_fx_rate_kind == FxRateKind("non_cash_buying")
    assert config.max_fx_staleness_calendar_days == 3
    assert config.base.fund_id == "TEST_FUND"


def test_fx_run_configuration_rejects_invalid_base_type() -> None:
    with pytest.raises(TypeError, match="base must be a HistoricalReconciliationRunConfiguration"):
        HistoricalFxReconciliationRunConfiguration(
            base="invalid",  # type: ignore[arg-type]
            fx_source_id="src_fx",
            required_fx_rate_kind=FxRateKind("non_cash_buying"),
            max_fx_staleness_calendar_days=3,
        )


@pytest.mark.parametrize("blank_val", ["", "   ", "\t"])
def test_fx_run_configuration_rejects_empty_fx_source_id(blank_val: str) -> None:
    with pytest.raises(
        InvalidHistoricalReconciliationRunConfigurationError,
        match="fx_source_id must be a non-empty string",
    ):
        HistoricalFxReconciliationRunConfiguration(
            base=_valid_base_config(),
            fx_source_id=blank_val,
            required_fx_rate_kind=FxRateKind("non_cash_buying"),
            max_fx_staleness_calendar_days=3,
        )


def test_fx_run_configuration_rejects_raw_string_for_fx_rate_kind() -> None:
    with pytest.raises(TypeError, match="required_fx_rate_kind must be an FxRateKind"):
        HistoricalFxReconciliationRunConfiguration(
            base=_valid_base_config(),
            fx_source_id="src_fx",
            required_fx_rate_kind="non_cash_buying",  # type: ignore[arg-type]
            max_fx_staleness_calendar_days=3,
        )


@pytest.mark.parametrize("bad_val", [True, False, 3.5, "3"])
def test_fx_run_configuration_rejects_non_int_staleness(bad_val: object) -> None:
    with pytest.raises(
        TypeError, match="max_fx_staleness_calendar_days must be a non-bool integer"
    ):
        HistoricalFxReconciliationRunConfiguration(
            base=_valid_base_config(),
            fx_source_id="src_fx",
            required_fx_rate_kind=FxRateKind("non_cash_buying"),
            max_fx_staleness_calendar_days=bad_val,  # type: ignore[arg-type]
        )


def test_fx_run_configuration_rejects_negative_staleness() -> None:
    with pytest.raises(
        InvalidHistoricalReconciliationRunConfigurationError,
        match="max_fx_staleness_calendar_days must be non-negative",
    ):
        HistoricalFxReconciliationRunConfiguration(
            base=_valid_base_config(),
            fx_source_id="src_fx",
            required_fx_rate_kind=FxRateKind("non_cash_buying"),
            max_fx_staleness_calendar_days=-1,
        )


def test_reads_valid_fx_schedule_csv_mapping_requests(tmp_path: Path) -> None:
    csv_file = tmp_path / "schedule.csv"
    csv_content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
        "2026-01-02,2026-01-03,2026-01-03,2026-01-03T10:00:00Z\n"
    )
    csv_file.write_text(csv_content, encoding="utf-8")

    config = _valid_fx_config()
    requests = read_historical_fx_reconciliation_requests_csv(csv_file, config)

    assert len(requests) == 2
    req1, req2 = requests

    # Verify per-row pricing_as_of_date
    assert req1.alignment_request.policy.pricing_as_of_date == MarketDate(2026, 1, 2)
    assert req2.alignment_request.policy.pricing_as_of_date == MarketDate(2026, 1, 3)

    # Verify permit_foreign policy
    assert req1.alignment_request.policy.price_currency_policy == PriceCurrencyPolicy(
        "permit_foreign"
    )
    assert req2.alignment_request.policy.price_currency_policy == PriceCurrencyPolicy(
        "permit_foreign"
    )

    # Verify run-wide fx policy object identity reuse
    assert req1.fx_policy is req2.fx_policy
    assert req1.fx_policy.required_fx_rate_kind == FxRateKind("non_cash_buying")
    assert req1.fx_policy.max_fx_staleness_calendar_days == 3

    # Verify provenance fields
    assert req1.fx_source_id == "src_fx"
    assert req1.fund_price_source_id == "src_f"
    assert req1.alignment_request.fund_id == "TEST_FUND"


def test_reads_utf8_bom_fx_schedule_csv(tmp_path: Path) -> None:
    csv_file = tmp_path / "schedule_bom.csv"
    csv_content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
    )
    csv_file.write_bytes(b"\xef\xbb\xbf" + csv_content.encode("utf-8"))

    requests = read_historical_fx_reconciliation_requests_csv(csv_file, _valid_fx_config())
    assert len(requests) == 1


def test_fx_schedule_rejects_non_utc_timestamp(tmp_path: Path) -> None:
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
        read_historical_fx_reconciliation_requests_csv(csv_file, _valid_fx_config())


def test_fx_schedule_reports_actual_physical_csv_line_number_with_blank_lines(
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
        read_historical_fx_reconciliation_requests_csv(csv_file, _valid_fx_config())


def test_fx_schedule_csv_error_preserves_path_line_and_cause(tmp_path: Path) -> None:
    csv_file = tmp_path / "bad_date.csv"
    content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "20260101,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
    )
    csv_file.write_text(content, encoding="utf-8")

    with pytest.raises(
        CsvHistoricalScheduleSourceError,
        match=r"at row 2: date must be YYYY-MM-DD format",
    ) as exc_info:
        read_historical_fx_reconciliation_requests_csv(csv_file, _valid_fx_config())

    assert exc_info.value.__cause__ is not None
    assert f"cannot parse schedule CSV {csv_file} at row 2:" in str(exc_info.value)


def test_fx_schedule_unexpected_runtime_error_propagates(tmp_path: Path) -> None:
    csv_file = tmp_path / "schedule.csv"
    content = (
        "return_start_date,return_end_date,pricing_as_of_date,prediction_timestamp\n"
        "2026-01-01,2026-01-02,2026-01-02,2026-01-02T10:00:00Z\n"
    )
    csv_file.write_text(content, encoding="utf-8")

    with patch(
        "navlens.reconciliation.historical.fx_schedule_csv.PointInTimeAlignmentRequest",
        side_effect=RuntimeError("unexpected bug"),
    ):
        with pytest.raises(RuntimeError, match="unexpected bug"):
            read_historical_fx_reconciliation_requests_csv(csv_file, _valid_fx_config())
