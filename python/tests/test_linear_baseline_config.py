"""Tests for LinearBaselineConfig extraction and LinearBaselineWalkForward delegation."""

import pytest
from navlens.estimators import LinearBaselineConfig
from navlens.evaluation import LinearBaselineWalkForward


def test_linear_baseline_config_validation() -> None:
    """Verify LinearBaselineConfig parameter validation rules."""
    config = LinearBaselineConfig(lookback=5)
    assert config.lookback == 5
    assert config.required_minimum_returns == 8
    assert config.resolved_minimum_training_returns == 8

    config_custom = LinearBaselineConfig(lookback=5, minimum_training_returns=10)
    assert config_custom.resolved_minimum_training_returns == 10

    with pytest.raises(ValueError, match="lookback must be at least one"):
        LinearBaselineConfig(lookback=0)

    with pytest.raises(ValueError, match="minimum_training_returns must be at least 8"):
        LinearBaselineConfig(lookback=5, minimum_training_returns=7)

    with pytest.raises(ValueError, match="lookback must be at least one"):
        LinearBaselineConfig(lookback=True)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="minimum_training_returns must be an integer or None"):
        LinearBaselineConfig(lookback=5, minimum_training_returns=True)  # type: ignore[arg-type]


def test_walk_forward_delegates_to_linear_baseline_config() -> None:
    """Verify LinearBaselineWalkForward delegates to LinearBaselineConfig."""

    wf = LinearBaselineWalkForward(lookback=5, model_version="v1")
    assert wf.initial_training_size == 8

    wf_custom = LinearBaselineWalkForward(
        lookback=5, model_version="v1", minimum_training_returns=12
    )
    assert wf_custom.initial_training_size == 12

    with pytest.raises(ValueError, match="lookback must be at least one"):
        LinearBaselineWalkForward(lookback=0, model_version="v1")

    with pytest.raises(ValueError, match="minimum_training_returns must be at least 8"):
        LinearBaselineWalkForward(lookback=5, model_version="v1", minimum_training_returns=6)
