import json
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import pytest
from navlens import MarketDate
from navlens.prediction import (
    InvalidPredictionArtifactError,
    PredictionModelSuiteOptions,
    PredictionModelSuiteResult,
    load_single_return_prediction_artifacts,
    predict_tefas_model_suite,
    serialize_prediction_model_suite,
)
from navlens.sources.tefas import TefasAcquisitionResult, TefasPriceRecord


def _acquisition() -> TefasAcquisitionResult:
    start = date(2026, 7, 20)
    records = tuple(
        TefasPriceRecord(start + timedelta(days=index), "AAL", 1.0 + index * 0.01)
        for index in range(14)
    )
    return TefasAcquisitionResult(records, Path("raw.json"), False)


def _suite() -> PredictionModelSuiteResult:
    return predict_tefas_model_suite(
        _acquisition(),
        acquired_at=datetime(2026, 8, 12, 12, tzinfo=UTC),
        prediction_date=MarketDate(2026, 8, 2),
        target_date=MarketDate(2026, 8, 3),
        options=PredictionModelSuiteOptions(model_version="suite-v1"),
    )


def test_runs_every_model_over_identical_point_in_time_provenance() -> None:
    suite = _suite()

    assert [item.model_name for item in suite.predictions] == [
        "linear-regression-baseline",
        "historical-mean-baseline",
        "last-return-baseline",
    ]
    expected_snapshots = suite.predictions[0].selected_snapshots
    expected_timestamp = suite.predictions[0].prediction_timestamp
    assert all(item.selected_snapshots == expected_snapshots for item in suite.predictions)
    assert all(item.prediction_timestamp == expected_timestamp for item in suite.predictions)


def test_serialized_suite_is_consumable_as_prediction_collection(tmp_path: Path) -> None:
    payload = serialize_prediction_model_suite(_suite())
    decoded = json.loads(payload)
    artifact = tmp_path / "suite.json"
    artifact.write_bytes(payload)

    assert decoded["schema_version"] == "navlens-prediction-model-suite-v1"
    assert len(decoded["predictions"]) == 3
    loaded = load_single_return_prediction_artifacts(artifact)
    assert [item.prediction.model.name for item in loaded] == [
        "linear-regression-baseline",
        "historical-mean-baseline",
        "last-return-baseline",
    ]


def test_suite_contract_rejects_missing_model() -> None:
    with pytest.raises(ValueError, match="every implemented"):
        PredictionModelSuiteResult(_suite().predictions[:2])


def test_loader_rejects_duplicate_model_identity(tmp_path: Path) -> None:
    payload = json.loads(serialize_prediction_model_suite(_suite()))
    payload["predictions"][1] = payload["predictions"][0]
    artifact = tmp_path / "duplicate-suite.json"
    artifact.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(InvalidPredictionArtifactError, match="unique model identities"):
        load_single_return_prediction_artifacts(artifact)
