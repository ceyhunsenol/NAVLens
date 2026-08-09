"""Tests for explicit JSON serialization of historical reconciliation evaluation summaries."""

import json

import pytest
from navlens import MarketDate
from navlens.reconciliation.historical import (
    HistoricalReconciliationDataset,
    MissingFundPriceSkip,
    MissingHoldingsSkip,
    evaluate_historical_reconciliation_dataset,
    serialize_historical_reconciliation_evaluation,
)
from tests.historical_reconciliation_evaluation_fixtures import (
    build_two_period_fx_dataset,
    build_two_period_legacy_dataset,
    make_skipped_legacy_record,
)


def test_serializes_empty_legacy_evaluation() -> None:
    ds = HistoricalReconciliationDataset(outcomes=())
    evaluation = evaluate_historical_reconciliation_dataset(ds)
    data_bytes = serialize_historical_reconciliation_evaluation(evaluation)

    _assert_valid_lf_newline(data_bytes)
    payload = json.loads(data_bytes.decode("utf-8"))

    assert payload["schema_version"] == 1
    assert payload["scope"] is None
    assert payload["metrics"] is None
    assert payload["counts"] == {
        "evaluated_period_count": 0,
        "missing_fund_price_count": 0,
        "missing_holdings_count": 0,
        "skipped_period_count": 0,
        "total_period_count": 0,
    }


def test_serializes_successful_legacy_evaluation_with_native_parity() -> None:
    ds = build_two_period_legacy_dataset()
    evaluation = evaluate_historical_reconciliation_dataset(ds)
    data_bytes = serialize_historical_reconciliation_evaluation(evaluation)

    _assert_valid_lf_newline(data_bytes)
    payload = json.loads(data_bytes.decode("utf-8"))

    assert payload["schema_version"] == 1
    assert payload["scope"] == {
        "fund_id": "TEST_FUND",
        "fund_price_source_id": "src_f",
        "fx_source_id": None,
        "holdings_source_id": "src_h",
        "kind": "legacy",
        "security_price_source_id": "src_p",
    }
    assert payload["counts"] == {
        "evaluated_period_count": 2,
        "missing_fund_price_count": 0,
        "missing_holdings_count": 0,
        "skipped_period_count": 0,
        "total_period_count": 2,
    }

    metrics = evaluation.metrics
    assert metrics is not None
    assert payload["metrics"] == {
        "full_return_coverage_ratio": metrics.full_return_coverage_ratio,
        "mean_absolute_residual_decimal": metrics.mean_absolute_residual,
        "mean_residual_decimal": metrics.mean_residual,
        "mean_return_coverage_ratio": metrics.mean_return_coverage,
        "root_mean_squared_residual_decimal": metrics.root_mean_squared_residual,
        "sample_count": metrics.sample_count,
    }


def test_serializes_successful_fx_aware_evaluation() -> None:
    ds = build_two_period_fx_dataset()
    evaluation = evaluate_historical_reconciliation_dataset(ds)
    data_bytes = serialize_historical_reconciliation_evaluation(evaluation)

    _assert_valid_lf_newline(data_bytes)
    payload = json.loads(data_bytes.decode("utf-8"))
    assert payload["scope"]["kind"] == "fx_aware"
    assert payload["scope"]["fx_source_id"] == "src_fx"


def test_serializes_all_skipped_evaluation() -> None:
    skip1 = make_skipped_legacy_record(MissingHoldingsSkip(), 1, 2)
    skip2 = make_skipped_legacy_record(MissingFundPriceSkip(MarketDate(2026, 1, 3)), 2, 3)

    ds = HistoricalReconciliationDataset(outcomes=(skip1, skip2))
    evaluation = evaluate_historical_reconciliation_dataset(ds)
    data_bytes = serialize_historical_reconciliation_evaluation(evaluation)

    _assert_valid_lf_newline(data_bytes)
    payload = json.loads(data_bytes.decode("utf-8"))
    assert payload["scope"] is not None
    assert payload["metrics"] is None
    assert payload["counts"]["total_period_count"] == 2
    assert payload["counts"]["evaluated_period_count"] == 0
    assert payload["counts"]["skipped_period_count"] == 2
    assert payload["counts"]["missing_holdings_count"] == 1
    assert payload["counts"]["missing_fund_price_count"] == 1


def test_serializes_exact_alphabetical_key_ordering() -> None:
    ds = build_two_period_legacy_dataset()
    evaluation = evaluate_historical_reconciliation_dataset(ds)
    data_bytes = serialize_historical_reconciliation_evaluation(evaluation)

    payload_dict = json.loads(data_bytes.decode("utf-8"))
    assert list(payload_dict.keys()) == ["counts", "metrics", "schema_version", "scope"]
    assert list(payload_dict["counts"].keys()) == [
        "evaluated_period_count",
        "missing_fund_price_count",
        "missing_holdings_count",
        "skipped_period_count",
        "total_period_count",
    ]
    assert list(payload_dict["scope"].keys()) == [
        "fund_id",
        "fund_price_source_id",
        "fx_source_id",
        "holdings_source_id",
        "kind",
        "security_price_source_id",
    ]
    assert list(payload_dict["metrics"].keys()) == [
        "full_return_coverage_ratio",
        "mean_absolute_residual_decimal",
        "mean_residual_decimal",
        "mean_return_coverage_ratio",
        "root_mean_squared_residual_decimal",
        "sample_count",
    ]


def test_serialization_preserves_evaluation_instance_unmodified() -> None:
    ds = build_two_period_legacy_dataset()
    evaluation = evaluate_historical_reconciliation_dataset(ds)

    metrics_id = id(evaluation.metrics)
    scope_id = id(evaluation.scope)
    total_count = evaluation.total_period_count
    evaluated_count = evaluation.evaluated_period_count
    skipped_count = evaluation.skipped_period_count
    missing_holdings = evaluation.missing_holdings_count
    missing_price = evaluation.missing_fund_price_count

    serialize_historical_reconciliation_evaluation(evaluation)

    assert id(evaluation.metrics) == metrics_id
    assert id(evaluation.scope) == scope_id
    assert evaluation.total_period_count == total_count
    assert evaluation.evaluated_period_count == evaluated_count
    assert evaluation.skipped_period_count == skipped_count
    assert evaluation.missing_holdings_count == missing_holdings
    assert evaluation.missing_fund_price_count == missing_price


def test_serialization_output_is_deterministic() -> None:
    ds = build_two_period_legacy_dataset()
    evaluation = evaluate_historical_reconciliation_dataset(ds)

    bytes1 = serialize_historical_reconciliation_evaluation(evaluation)
    bytes2 = serialize_historical_reconciliation_evaluation(evaluation)

    assert bytes1 == bytes2
    text = bytes1.decode("utf-8")
    assert "<HistoricalReconciliationEvaluation" not in text
    assert "0x" not in text


def test_serialize_raises_type_error_for_invalid_input() -> None:
    with pytest.raises(TypeError, match="evaluation must be a HistoricalReconciliationEvaluation"):
        serialize_historical_reconciliation_evaluation("invalid")  # type: ignore[arg-type]


def _assert_valid_lf_newline(data_bytes: bytes) -> None:
    assert data_bytes.endswith(b"\n")
    assert not data_bytes.endswith(b"\n\n")
    assert b"\r" not in data_bytes
