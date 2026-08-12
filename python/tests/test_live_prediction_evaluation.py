from dataclasses import replace
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
from navlens.prediction.artifact import load_single_return_prediction_artifact
from navlens.prediction.errors import (
    MissingRealizedPriceObservationError,
    UnsupportedPredictionArtifactSourceError,
)
from navlens.prediction.live_evaluation import evaluate_tefas_prediction_artifact
from navlens.prediction.live_evaluation_output import serialize_live_prediction_evaluation
from navlens.sources.tefas import TefasAcquisitionResult, TefasPriceRecord
from prediction_artifact_fixtures import write_prediction_artifact


def test_delegates_realized_return_and_metrics_to_native_boundaries(tmp_path: Path) -> None:
    artifact = load_single_return_prediction_artifact(
        write_prediction_artifact(tmp_path / "prediction.json")
    )

    result = evaluate_tefas_prediction_artifact(
        artifact,
        _acquisition(tmp_path),
        evaluated_at=datetime(2026, 7, 21, 12, tzinfo=UTC),
    )

    assert result.realized_return.return_decimal == pytest.approx(0.02)
    assert result.metrics.sample_count == 1
    assert result.metrics.mean_absolute_error == pytest.approx(0.01)
    assert result.metrics.direction_accuracy == 1.0
    assert result.metrics.interval is not None
    assert result.metrics.interval.coverage == 1.0
    assert b'"realized_return_decimal": 0.02' in serialize_live_prediction_evaluation(result)


def test_requires_exact_target_observation(tmp_path: Path) -> None:
    artifact = load_single_return_prediction_artifact(
        write_prediction_artifact(tmp_path / "prediction.json")
    )
    acquisition = replace(_acquisition(tmp_path), records=_acquisition(tmp_path).records[:1])

    with pytest.raises(MissingRealizedPriceObservationError, match="2026-07-21"):
        evaluate_tefas_prediction_artifact(
            artifact,
            acquisition,
            evaluated_at=datetime(2026, 7, 21, 12, tzinfo=UTC),
        )


def test_rejects_non_tefas_artifact(tmp_path: Path) -> None:
    artifact = load_single_return_prediction_artifact(
        write_prediction_artifact(tmp_path / "prediction.json", source_id="other")
    )

    with pytest.raises(UnsupportedPredictionArtifactSourceError):
        evaluate_tefas_prediction_artifact(
            artifact,
            _acquisition(tmp_path),
            evaluated_at=datetime(2026, 7, 21, 12, tzinfo=UTC),
        )


def _acquisition(tmp_path: Path) -> TefasAcquisitionResult:
    records = (
        TefasPriceRecord(date(2026, 7, 20), "AAL", 100.0),
        TefasPriceRecord(date(2026, 7, 21), "AAL", 102.0),
    )
    return TefasAcquisitionResult(records, tmp_path / "tefas.json", True)
