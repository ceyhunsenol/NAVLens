"""Tests for the historical prediction schedule CSV boundary."""

from datetime import UTC, datetime
from pathlib import Path
from re import escape

import pytest
from navlens import MarketDate
from navlens.prediction.historical import (
    CsvHistoricalPredictionScheduleSourceError,
    read_historical_prediction_requests_csv,
)


def _write_schedule(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "schedule.csv"
    path.write_text(body, encoding="utf-8")
    return path


def test_reads_typed_historical_prediction_requests(tmp_path: Path) -> None:
    path = _write_schedule(
        tmp_path,
        "prediction_date,pricing_as_of_date,target_date,"
        "prediction_timestamp,evaluation_timestamp\n"
        "2026-01-10,2026-01-09,2026-01-11,"
        "2026-01-10T18:00:00Z,2026-01-11T18:00:00Z\n",
    )

    requests = read_historical_prediction_requests_csv(path)

    assert len(requests) == 1
    request = requests[0]
    assert request.prediction_date == MarketDate(2026, 1, 10)
    assert request.pricing_as_of_date == MarketDate(2026, 1, 9)
    assert request.target_date == MarketDate(2026, 1, 11)
    assert request.prediction_timestamp == datetime(2026, 1, 10, 18, tzinfo=UTC)
    assert request.evaluation_timestamp == datetime(2026, 1, 11, 18, tzinfo=UTC)


@pytest.mark.parametrize(
    "body,expected",
    [
        ("", "header is missing"),
        (
            "prediction_date,target_date,prediction_timestamp,evaluation_timestamp\n",
            "pricing_as_of_date",
        ),
        (
            "prediction_date,pricing_as_of_date,target_date,"
            "prediction_timestamp,evaluation_timestamp\n",
            "contains no rows",
        ),
    ],
)
def test_rejects_missing_structure(tmp_path: Path, body: str, expected: str) -> None:
    path = _write_schedule(tmp_path, body)

    with pytest.raises(CsvHistoricalPredictionScheduleSourceError, match=expected):
        read_historical_prediction_requests_csv(path)


def test_reports_path_and_physical_row_for_invalid_values(tmp_path: Path) -> None:
    path = _write_schedule(
        tmp_path,
        "prediction_date,pricing_as_of_date,target_date,"
        "prediction_timestamp,evaluation_timestamp\n"
        "2026-01-10,2026-01-10,2026-01-11,"
        "2026-01-10T18:00:00+03:00,2026-01-11T18:00:00Z\n",
    )

    with pytest.raises(
        CsvHistoricalPredictionScheduleSourceError,
        match=rf"{escape(str(path))} at row 2:.*UTC",
    ):
        read_historical_prediction_requests_csv(path)


def test_wraps_request_contract_errors_with_row_context(tmp_path: Path) -> None:
    path = _write_schedule(
        tmp_path,
        "prediction_date,pricing_as_of_date,target_date,"
        "prediction_timestamp,evaluation_timestamp\n"
        "2026-01-10,2026-01-10,2026-01-09,"
        "2026-01-10T18:00:00Z,2026-01-11T18:00:00Z\n",
    )

    with pytest.raises(
        CsvHistoricalPredictionScheduleSourceError,
        match=rf"{escape(str(path))} at row 2:.*strictly after",
    ):
        read_historical_prediction_requests_csv(path)


def test_reports_physical_line_after_multiline_csv_field(tmp_path: Path) -> None:
    path = _write_schedule(
        tmp_path,
        "prediction_date,pricing_as_of_date,target_date,"
        "prediction_timestamp,evaluation_timestamp,note\n"
        "invalid,2026-01-10,2026-01-11,"
        '2026-01-10T18:00:00Z,2026-01-11T18:00:00Z,"line one\nline two"\n',
    )

    with pytest.raises(
        CsvHistoricalPredictionScheduleSourceError,
        match=rf"{escape(str(path))} at row 3:",
    ):
        read_historical_prediction_requests_csv(path)
