"""Compatibility exports for the estimator boundary consumed by evaluation."""

from navlens.estimators.contracts import FittedPrediction, NextReturnEstimator

WalkForwardEstimator = NextReturnEstimator

__all__ = ["FittedPrediction", "WalkForwardEstimator"]
