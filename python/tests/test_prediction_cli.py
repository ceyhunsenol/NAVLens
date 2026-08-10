"""Tests for navlens-predict-fund-csv CLI and serialization formatters."""

import json
from datetime import UTC, date, datetime, timedelta

import pytest
from navlens import MarketDate
from navlens.prediction import (
    SingleReturnPredictionResult,
    format_prediction_text,
    predict_next_published_nav_return_from_csv,
    serialize_single_return_prediction,
)
from navlens.prediction.cli import main
from navlens.prediction.serialization import SCHEMA_VERSION


def _create_sample_csv(tmp_path, count: int = 15) -> str:
    csv_file = tmp_path / "fund_prices.csv"
    lines = ["fund_id,market_date,unit_price,available_at,ingested_at,source_id"]
    base_date = date(2026, 7, 1)
    base_ts = datetime(2026, 7, 1, 18, 0, tzinfo=UTC)
    price = 100.0

    for i in range(count):
        m_date = (base_date + timedelta(days=i)).isoformat()
        ts = (base_ts + timedelta(days=i)).isoformat()
        price *= 1.002
        lines.append(f"AAL,{m_date},{price:.4f},{ts},{ts},tefas")

    csv_file.write_text("\n".join(lines), encoding="utf-8")
    return str(csv_file)


def test_csv_helper_and_formatters(tmp_path) -> None:
    """Test CSV helper function, text formatting, and versioned JSON serialization."""
    csv_path = _create_sample_csv(tmp_path, count=15)
    pred_ts = datetime(2026, 7, 20, 0, 0, tzinfo=UTC)

    result = predict_next_published_nav_return_from_csv(
        csv_path,
        fund_id="AAL",
        source_id="tefas",
        prediction_timestamp=pred_ts,
        prediction_date=MarketDate(2026, 7, 15),
        pricing_as_of_date=MarketDate(2026, 7, 15),
        target_date=MarketDate(2026, 7, 16),
        lookback=5,
    )

    assert isinstance(result, SingleReturnPredictionResult)

    # Test text formatting
    text_output = format_prediction_text(result)
    assert "=== NAVLens Point-in-Time Return Prediction ===" in text_output
    assert "Fund ID: AAL" in text_output
    assert "Source ID: tefas" in text_output
    assert "Target Semantics: next_published_nav_return_decimal" in text_output

    # Test versioned JSON serialization
    json_bytes = serialize_single_return_prediction(result)
    assert isinstance(json_bytes, bytes)
    payload = json.loads(json_bytes.decode("utf-8"))
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["fund_id"] == "AAL"
    assert payload["source_id"] == "tefas"
    assert payload["prediction_date"] == "2026-07-15"
    assert payload["target_date"] == "2026-07-16"
    assert payload["selected_snapshot_count"] == 15
    assert payload["canonical_return_count"] == 14
    assert payload["training_return_count"] == 14


def test_cli_main_text_and_json(tmp_path, capsys) -> None:
    """Test CLI main composition root with text and json output formats."""
    csv_path = _create_sample_csv(tmp_path, count=15)

    argv_text = [
        "--fund-unit-prices-csv",
        csv_path,
        "--fund-id",
        "AAL",
        "--source-id",
        "tefas",
        "--prediction-timestamp",
        "2026-07-20T00:00:00Z",
        "--prediction-date",
        "2026-07-15",
        "--pricing-as-of-date",
        "2026-07-15",
        "--target-date",
        "2026-07-16",
        "--lookback",
        "5",
        "--output-format",
        "text",
    ]
    exit_code = main(argv_text)
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "=== NAVLens Point-in-Time Return Prediction ===" in captured.out

    argv_json = [
        "--fund-unit-prices-csv",
        csv_path,
        "--fund-id",
        "AAL",
        "--source-id",
        "tefas",
        "--prediction-timestamp",
        "2026-07-20T00:00:00Z",
        "--prediction-date",
        "2026-07-15",
        "--pricing-as-of-date",
        "2026-07-15",
        "--target-date",
        "2026-07-16",
        "--lookback",
        "5",
        "--output-format",
        "json",
    ]
    exit_code_json = main(argv_json)
    assert exit_code_json == 0


def test_cli_operational_error_handling(capsys) -> None:
    """Test CLI catches expected operational errors and returns exit code 1."""
    argv_bad = [
        "--fund-unit-prices-csv",
        "non_existent_file.csv",
        "--fund-id",
        "AAL",
        "--source-id",
        "tefas",
        "--prediction-timestamp",
        "2026-07-20T00:00:00Z",
        "--prediction-date",
        "2026-07-15",
        "--pricing-as-of-date",
        "2026-07-15",
        "--target-date",
        "2026-07-16",
    ]
    exit_code = main(argv_bad)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "error:" in captured.err


def test_cli_unexpected_error_propagation(monkeypatch) -> None:
    """Test that unexpected RuntimeError or TypeError is NOT caught by main and propagates."""

    def _mock_predict(*args, **kwargs):
        raise RuntimeError("Unexpected internal engine error")

    monkeypatch.setattr(
        "navlens.prediction.cli.predict_next_published_nav_return_from_csv",
        _mock_predict,
    )

    argv = [
        "--fund-unit-prices-csv",
        "dummy.csv",
        "--fund-id",
        "AAL",
        "--source-id",
        "tefas",
        "--prediction-timestamp",
        "2026-07-20T00:00:00Z",
        "--prediction-date",
        "2026-07-15",
        "--pricing-as-of-date",
        "2026-07-15",
        "--target-date",
        "2026-07-16",
    ]
    with pytest.raises(RuntimeError, match="Unexpected internal engine error"):
        main(argv)


def test_cli_cross_field_model_config_error(tmp_path, capsys) -> None:
    """Test that invalid cross-field model config outputs expected error and returns exit code 1."""
    csv_path = _create_sample_csv(tmp_path, count=15)
    argv = [
        "--fund-unit-prices-csv",
        csv_path,
        "--fund-id",
        "AAL",
        "--source-id",
        "tefas",
        "--prediction-timestamp",
        "2026-07-20T00:00:00Z",
        "--prediction-date",
        "2026-07-15",
        "--pricing-as-of-date",
        "2026-07-15",
        "--target-date",
        "2026-07-16",
        "--lookback",
        "5",
        "--minimum-training-returns",
        "1",
    ]
    exit_code = main(argv)
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "error: minimum_training_returns must be at least 8" in captured.err


def test_cli_type_error_propagation(monkeypatch) -> None:
    """Test that unexpected TypeError is NOT caught by main and propagates traceback."""

    def _mock_predict_type_error(*args, **kwargs):
        raise TypeError("Unexpected type mismatch inside orchestration")

    monkeypatch.setattr(
        "navlens.prediction.cli.predict_next_published_nav_return_from_csv",
        _mock_predict_type_error,
    )

    argv = [
        "--fund-unit-prices-csv",
        "dummy.csv",
        "--fund-id",
        "AAL",
        "--source-id",
        "tefas",
        "--prediction-timestamp",
        "2026-07-20T00:00:00Z",
        "--prediction-date",
        "2026-07-15",
        "--pricing-as-of-date",
        "2026-07-15",
        "--target-date",
        "2026-07-16",
    ]
    with pytest.raises(TypeError, match="Unexpected type mismatch inside orchestration"):
        main(argv)
