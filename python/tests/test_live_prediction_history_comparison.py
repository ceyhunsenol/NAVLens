import json
from pathlib import Path

import pytest
from navlens.prediction.artifact import load_live_prediction_evaluation_artifact
from navlens.prediction.errors import InvalidLivePredictionHistoryComparisonError
from navlens.prediction.live_history import evaluate_live_prediction_history
from navlens.prediction.live_history_comparison import compare_live_prediction_histories
from navlens.prediction.live_history_comparison_output import (
    serialize_live_prediction_history_comparison,
)
from prediction_artifact_fixtures import write_evaluation_artifact


def test_compares_native_metrics_over_identical_realized_periods(tmp_path: Path) -> None:
    first = _history(tmp_path, "first", "ridge", (0.01, 0.02))
    second = _history(tmp_path, "second", "last-return", (0.0, 0.0))

    result = compare_live_prediction_histories((first, second))

    payload = json.loads(serialize_live_prediction_history_comparison(result))
    assert result.histories == (first, second)
    assert payload["sample_count"] == 2
    assert payload["histories"][0]["mean_absolute_error_decimal"] == pytest.approx(0.02)
    assert payload["histories"][1]["mean_absolute_error_decimal"] == pytest.approx(0.015)
    assert "winner" not in payload


def test_rejects_different_realized_returns(tmp_path: Path) -> None:
    first = _history(tmp_path, "first", "ridge", (0.01, 0.02))
    second = _history(
        tmp_path,
        "second",
        "last-return",
        (0.0, 0.0),
        second_realized=0.03,
    )

    with pytest.raises(InvalidLivePredictionHistoryComparisonError, match="realized"):
        compare_live_prediction_histories((first, second))


def test_rejects_duplicate_model_identity(tmp_path: Path) -> None:
    first = _history(tmp_path, "first", "ridge", (0.01, 0.02))
    second = _history(tmp_path, "second", "ridge", (0.0, 0.0))

    with pytest.raises(InvalidLivePredictionHistoryComparisonError, match="unique model"):
        compare_live_prediction_histories((first, second))


def test_rejects_different_confidence_levels(tmp_path: Path) -> None:
    first = _history(tmp_path, "first", "ridge", (0.01, 0.02))
    second = _history(
        tmp_path,
        "second",
        "last-return",
        (0.0, 0.0),
        confidence_level=0.8,
    )

    with pytest.raises(InvalidLivePredictionHistoryComparisonError, match="confidence"):
        compare_live_prediction_histories((first, second))


def test_rejects_different_period_sequences(tmp_path: Path) -> None:
    first = _history(tmp_path, "first", "ridge", (0.01, 0.02))
    second = _history(
        tmp_path,
        "second",
        "last-return",
        (0.0, 0.0),
        second_target_date="2026-07-23",
    )

    with pytest.raises(InvalidLivePredictionHistoryComparisonError, match="identical prediction"):
        compare_live_prediction_histories((first, second))


def _history(
    root: Path,
    prefix: str,
    model_name: str,
    predictions: tuple[float, float],
    *,
    confidence_level: float = 0.9,
    second_realized: float = -0.01,
    second_target_date: str = "2026-07-22",
):
    first_path = write_evaluation_artifact(
        root / f"{prefix}-first.json",
        confidence_level=confidence_level,
        model_name=model_name,
        predicted_return_decimal=predictions[0],
    )
    second_path = write_evaluation_artifact(
        root / f"{prefix}-second.json",
        evaluated_at="2026-07-22T12:00:00+00:00",
        confidence_level=confidence_level,
        last_observation_date="2026-07-21",
        model_name=model_name,
        predicted_return_decimal=predictions[1],
        prediction_date="2026-07-21",
        prediction_timestamp="2026-07-21T12:00:00+00:00",
        realized_return_decimal=second_realized,
        target_date=second_target_date,
    )
    artifacts = tuple(
        load_live_prediction_evaluation_artifact(path) for path in (first_path, second_path)
    )
    return evaluate_live_prediction_history(artifacts)
