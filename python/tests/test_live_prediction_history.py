from pathlib import Path

import pytest
from navlens import NavlensValidationError
from navlens.prediction.artifact import load_live_prediction_evaluation_artifact
from navlens.prediction.errors import InvalidLivePredictionHistoryError
from navlens.prediction.live_history import evaluate_live_prediction_history
from navlens.prediction.live_history_output import serialize_live_prediction_history
from prediction_artifact_fixtures import write_evaluation_artifact


def test_aggregates_multiple_evaluations_through_native_metrics(tmp_path: Path) -> None:
    artifacts = _history_artifacts(tmp_path)

    result = evaluate_live_prediction_history(artifacts)

    assert result.metrics.sample_count == 2
    assert result.metrics.mean_absolute_error == pytest.approx(0.02)
    assert result.metrics.mean_error == pytest.approx(0.01)
    assert result.metrics.direction_accuracy == pytest.approx(0.5)
    assert result.metrics.interval is not None
    assert result.metrics.interval.coverage == 1.0
    payload = serialize_live_prediction_history(result)
    assert b'"schema_version": "navlens-live-prediction-history-v1"' in payload


def test_rejects_empty_history() -> None:
    with pytest.raises(InvalidLivePredictionHistoryError, match="empty"):
        evaluate_live_prediction_history(())


def test_rejects_mixed_fund_scope(tmp_path: Path) -> None:
    artifacts = list(_history_artifacts(tmp_path))
    mixed_path = write_evaluation_artifact(
        tmp_path / "mixed.json",
        fund_id="PHE",
        prediction_date="2026-07-22",
        target_date="2026-07-23",
    )
    artifacts[1] = load_live_prediction_evaluation_artifact(mixed_path)

    with pytest.raises(InvalidLivePredictionHistoryError, match="share fund"):
        evaluate_live_prediction_history(artifacts)


def test_rust_rejects_non_chronological_history(tmp_path: Path) -> None:
    artifacts = tuple(reversed(_history_artifacts(tmp_path)))

    with pytest.raises(NavlensValidationError, match="chronological"):
        evaluate_live_prediction_history(artifacts)


def _history_artifacts(tmp_path: Path):
    first = write_evaluation_artifact(tmp_path / "first.json")
    second = write_evaluation_artifact(
        tmp_path / "second.json",
        evaluated_at="2026-07-22T12:00:00+00:00",
        last_observation_date="2026-07-21",
        predicted_return_decimal=0.02,
        prediction_date="2026-07-21",
        prediction_timestamp="2026-07-21T12:00:00+00:00",
        realized_return_decimal=-0.01,
        target_date="2026-07-22",
    )
    return tuple(load_live_prediction_evaluation_artifact(path) for path in (first, second))
