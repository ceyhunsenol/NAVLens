"""Tests for HistoricalPredictionEvaluationScope."""

from dataclasses import FrozenInstanceError

import pytest
from navlens.prediction.historical import (
    HistoricalPredictionEvaluationScope,
    InvalidHistoricalPredictionScopeError,
)


def test_valid_scope_construction_defaults() -> None:
    scope = HistoricalPredictionEvaluationScope(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        lookback=5,
        confidence_level=0.95,
        model_version="v1.0.0",
    )
    assert scope.fund_id == "FUND_A"
    assert scope.source_id == "SOURCE_1"
    assert scope.lookback == 5
    assert scope.confidence_level == 0.95
    assert scope.model_version == "v1.0.0"
    assert scope.minimum_training_returns is None
    assert scope.resolved_minimum_training_returns == 8


def test_valid_scope_construction_explicit_minimum_training_returns() -> None:
    scope = HistoricalPredictionEvaluationScope(
        fund_id="FUND_B",
        source_id="SOURCE_2",
        lookback=5,
        confidence_level=0.90,
        model_version="v2.0",
        minimum_training_returns=12,
    )
    assert scope.minimum_training_returns == 12
    assert scope.resolved_minimum_training_returns == 12


def test_scope_immutability() -> None:
    scope = HistoricalPredictionEvaluationScope(
        fund_id="FUND_A",
        source_id="SOURCE_1",
        lookback=5,
        confidence_level=0.95,
        model_version="v1.0.0",
    )
    with pytest.raises(FrozenInstanceError):
        scope.fund_id = "OTHER"  # type: ignore[misc]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("fund_id", ""),
        ("fund_id", "   "),
        ("fund_id", 123),
        ("source_id", ""),
        ("source_id", "   "),
        ("source_id", None),
        ("model_version", ""),
        ("model_version", "   "),
        ("model_version", []),
    ],
)
def test_invalid_identifiers_and_model_version(field: str, value: object) -> None:
    kwargs = {
        "fund_id": "FUND_A",
        "source_id": "SOURCE_1",
        "lookback": 5,
        "confidence_level": 0.95,
        "model_version": "v1.0.0",
    }
    kwargs[field] = value
    with pytest.raises(InvalidHistoricalPredictionScopeError):
        HistoricalPredictionEvaluationScope(**kwargs)


@pytest.mark.parametrize(
    "invalid_lookback",
    [
        True,
        False,
        0,
        -1,
        -5,
        "5",
        5.0,
    ],
)
def test_invalid_lookback_rejection(invalid_lookback: object) -> None:
    with pytest.raises(InvalidHistoricalPredictionScopeError) as exc_info:
        HistoricalPredictionEvaluationScope(
            fund_id="FUND_A",
            source_id="SOURCE_1",
            lookback=invalid_lookback,  # type: ignore[arg-type]
            confidence_level=0.95,
            model_version="v1.0.0",
        )
    assert isinstance(exc_info.value.__cause__, ValueError)


@pytest.mark.parametrize(
    "invalid_min_returns",
    [
        True,
        False,
        1,
        7,  # lookback is 5, required minimum is 8
        "10",
        10.5,
    ],
)
def test_invalid_minimum_training_returns_rejection(invalid_min_returns: object) -> None:
    with pytest.raises(InvalidHistoricalPredictionScopeError) as exc_info:
        HistoricalPredictionEvaluationScope(
            fund_id="FUND_A",
            source_id="SOURCE_1",
            lookback=5,
            confidence_level=0.95,
            model_version="v1.0.0",
            minimum_training_returns=invalid_min_returns,  # type: ignore[arg-type]
        )
    assert isinstance(exc_info.value.__cause__, ValueError)


@pytest.mark.parametrize(
    "invalid_confidence",
    [
        True,
        False,
        0.0,
        1.0,
        -0.1,
        1.5,
        float("nan"),
        float("inf"),
        float("-inf"),
        "0.95",
    ],
)
def test_invalid_confidence_level_rejection(invalid_confidence: object) -> None:
    with pytest.raises(InvalidHistoricalPredictionScopeError):
        HistoricalPredictionEvaluationScope(
            fund_id="FUND_A",
            source_id="SOURCE_1",
            lookback=5,
            confidence_level=invalid_confidence,  # type: ignore[arg-type]
            model_version="v1.0.0",
        )
