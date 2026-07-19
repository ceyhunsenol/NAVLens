from pathlib import Path

import pytest
from navlens.datasets import (
    FundReturnDatasetError,
    dated_returns_to_series,
    load_fund_returns_csv,
)
from navlens.estimators import predict_next_return
from navlens.training import train_linear_baseline


def test_builds_provenance_carrying_return_dataset(shared_price_csv_path: Path) -> None:
    dataset = load_fund_returns_csv("ABC", shared_price_csv_path)

    assert dataset.fund_id == "ABC"
    assert dataset.source_path == shared_price_csv_path
    assert dataset.source_row_count == 6
    assert dataset.returns.tolist() == pytest.approx([0.01, -0.005, 0.015, -0.002, 0.01])
    assert dataset.returns.index[0].isoformat() == "2026-01-05T00:00:00"


def test_dataset_feeds_training_without_file_access_in_trainer(
    shared_price_csv_path: Path,
) -> None:
    dataset = load_fund_returns_csv("ABC", shared_price_csv_path)
    artifact = train_linear_baseline(
        dataset.returns,
        lookback=1,
        model_version="0.1.0",
        confidence_level=0.80,
    )

    prediction = predict_next_return(artifact, dataset.returns)

    assert prediction.lower_bound <= prediction.expected_return <= prediction.upper_bound


def test_rejects_empty_native_return_mapping() -> None:
    with pytest.raises(FundReturnDatasetError, match="at least one"):
        dated_returns_to_series([])
