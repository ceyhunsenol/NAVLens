"""Tests for HistoricalPredictionEvaluation JSON serialization."""

import json
from datetime import UTC, datetime

import pytest
from navlens import MarketDate
from navlens.prediction.historical import (
    HistoricalPredictionEvaluation,
    evaluate_historical_prediction_dataset,
    serialize_historical_prediction_evaluation,
)
from tests.historical_prediction_fixtures import (
    make_real_historical_prediction_dataset,
    make_request,
)


def test_invalid_type_raises_type_error() -> None:
    with pytest.raises(TypeError, match="HistoricalPredictionEvaluation"):
        serialize_historical_prediction_evaluation("invalid_input")  # type: ignore

    with pytest.raises(TypeError, match="HistoricalPredictionEvaluation"):
        serialize_historical_prediction_evaluation(123)  # type: ignore


def test_empty_evaluation_serialization() -> None:
    evaluation = HistoricalPredictionEvaluation(
        metrics=None,
        scope=None,
        total_period_count=0,
        evaluated_period_count=0,
        skipped_period_count=0,
        no_eligible_snapshots_count=0,
        insufficient_history_count=0,
        target_not_yet_available_count=0,
        missing_target_observation_count=0,
    )

    serialized = serialize_historical_prediction_evaluation(evaluation)
    assert isinstance(serialized, bytes)
    assert serialized.endswith(b"\n")
    assert not serialized.endswith(b"\r\n")

    decoded = serialized.decode("utf-8")
    data = json.loads(decoded)

    assert data["schema_version"] == 1
    assert data["scope"] is None
    assert data["metrics"] is None
    assert data["counts"] == {
        "evaluated_period_count": 0,
        "insufficient_history_count": 0,
        "missing_target_observation_count": 0,
        "no_eligible_snapshots_count": 0,
        "skipped_period_count": 0,
        "target_not_yet_available_count": 0,
        "total_period_count": 0,
    }


def test_all_skipped_evaluation_serialization() -> None:
    req = make_request()
    dataset = make_real_historical_prediction_dataset((req,), snapshots=[])
    evaluation = evaluate_historical_prediction_dataset(dataset)

    serialized = serialize_historical_prediction_evaluation(evaluation)
    data = json.loads(serialized.decode("utf-8"))

    assert data["schema_version"] == 1
    assert data["metrics"] is None
    assert data["scope"] == {
        "confidence_level": 0.95,
        "fund_id": "FUND_A",
        "lookback": 5,
        "minimum_training_returns": None,
        "model_version": "v1.0",
        "source_id": "SOURCE_1",
    }
    assert data["counts"]["total_period_count"] == 1
    assert data["counts"]["evaluated_period_count"] == 0
    assert data["counts"]["skipped_period_count"] == 1
    assert data["counts"]["no_eligible_snapshots_count"] == 1


def test_successful_evaluation_serialization() -> None:
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    dataset = make_real_historical_prediction_dataset((req,))
    evaluation = evaluate_historical_prediction_dataset(dataset)

    serialized = serialize_historical_prediction_evaluation(evaluation)
    data = json.loads(serialized.decode("utf-8"))

    assert data["schema_version"] == 1
    assert data["scope"]["fund_id"] == "FUND_A"

    metrics = data["metrics"]
    assert metrics is not None
    assert "direction_accuracy_ratio" in metrics
    assert "mean_absolute_error_decimal" in metrics
    assert "mean_error_decimal" in metrics
    assert "root_mean_squared_error_decimal" in metrics
    assert metrics["sample_count"] == 1

    interval = metrics["interval"]
    assert interval is not None
    assert interval["confidence_level"] == 0.95
    assert "coverage_ratio" in interval
    assert "mean_width_decimal" in interval
    assert interval["sample_count"] == 1


def test_exact_json_key_structure_and_alphabetical_ordering() -> None:
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    dataset = make_real_historical_prediction_dataset((req,))
    evaluation = evaluate_historical_prediction_dataset(dataset)

    serialized = serialize_historical_prediction_evaluation(evaluation)
    decoded = serialized.decode("utf-8")

    # Top-level keys must be in alphabetical order: counts, metrics, schema_version, scope
    top_keys = list(json.loads(decoded, object_pairs_hook=lambda pairs: [k for k, _ in pairs]))
    assert top_keys == ["counts", "metrics", "schema_version", "scope"]


def test_allow_nan_false_argument_passed(monkeypatch: pytest.MonkeyPatch) -> None:
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    dataset = make_real_historical_prediction_dataset((req,))
    evaluation = evaluate_historical_prediction_dataset(dataset)

    real_dumps = json.dumps
    dumps_kwargs: dict[str, object] = {}

    def spy_dumps(obj: object, **kwargs: object) -> str:
        nonlocal dumps_kwargs
        dumps_kwargs = kwargs
        return real_dumps(obj, **kwargs)

    monkeypatch.setattr("json.dumps", spy_dumps)

    serialize_historical_prediction_evaluation(evaluation)
    assert dumps_kwargs.get("allow_nan") is False
    assert dumps_kwargs.get("sort_keys") is True
    assert dumps_kwargs.get("indent") == 2


def test_deterministic_repeated_serialization() -> None:
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    dataset = make_real_historical_prediction_dataset((req,))
    evaluation = evaluate_historical_prediction_dataset(dataset)

    first = serialize_historical_prediction_evaluation(evaluation)
    second = serialize_historical_prediction_evaluation(evaluation)
    assert first == second


def test_evaluation_state_unmodified_after_serialization() -> None:
    req = make_request(
        prediction_date=MarketDate(2026, 1, 10),
        target_date=MarketDate(2026, 1, 11),
        prediction_timestamp=datetime(2026, 1, 10, 18, 0, 0, tzinfo=UTC),
        evaluation_timestamp=datetime(2026, 1, 11, 18, 0, 0, tzinfo=UTC),
    )
    dataset = make_real_historical_prediction_dataset((req,))
    evaluation = evaluate_historical_prediction_dataset(dataset)

    scope_before = evaluation.scope
    metrics_before = evaluation.metrics
    total_before = evaluation.total_period_count

    _ = serialize_historical_prediction_evaluation(evaluation)

    assert evaluation.scope is scope_before
    assert evaluation.metrics is metrics_before
    assert evaluation.total_period_count == total_before
