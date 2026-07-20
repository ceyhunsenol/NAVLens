# Backtesting

NAVLens backtests evaluate predictions in chronological order for one fund at a
time. A backtest result is meaningful only when every input was available at the
time represented by the prediction date.

## Current guarantees

`BacktestSeries` enforces these invariants before evaluation:

- the series belongs to one validated `FundId`;
- the series contains at least one observation;
- every prediction date is earlier than its target date;
- prediction dates never move backwards;
- target dates increase strictly;
- duplicate target dates are rejected.

Because `evaluate` accepts a `BacktestSeries` instead of an arbitrary slice, it
does not need to repeat chronological validation.

## Current metrics

- **Mean absolute error (MAE):** average absolute distance between prediction
  and actual return.
- **Mean error:** signed average error, used to detect systematic over- or
  under-prediction.
- **Root mean squared error (RMSE):** error metric that penalizes larger misses
  more heavily.
- **Direction accuracy:** fraction of observations whose predicted and actual
  directions match. Positive, negative, and flat are distinct directions;
  positive and negative zero are both flat.

Returns use decimal units: `0.01` means one percent.

## What is not guaranteed yet

An earlier prediction date alone does not prove that every feature was known at
that date. Full leakage protection requires dataset metadata with at least:

- market/event time;
- provider publication time;
- NAVLens ingestion time;
- dataset snapshot identifier;
- feature schema version;
- model version.

A future dataset layer will reject features published after the prediction
boundary. Until that layer exists, NAVLens must describe the current protection
as chronological validation, not complete future-data-leakage prevention.

## Ownership

- `navlens-core` owns validated fund identifiers and return values.
- `navlens-calendar` owns market dates.
- `navlens-backtest` owns chronological series validation and evaluation
  metrics.
- Python may orchestrate experiments but must not reimplement these metrics.

The public Python package exposes `BacktestObservation` and
`evaluate_backtest` as thin PyO3 mappings. This lets walk-forward research use
the canonical Rust chronology checks and metrics without duplicating them in
Python.

## Expanding-window baseline

The Python evaluation package implements an expanding-window walk-forward
workflow. Each step trains only on returns through its `prediction_date`, then
predicts the next published NAV return at `target_date`. The actual target and
all later returns are excluded from that training call.

```python
from navlens.evaluation import LinearBaselineWalkForward, run_walk_forward

estimator = LinearBaselineWalkForward(
    lookback=3,
    model_version="0.1.0",
    confidence_level=0.80,
)
result = run_walk_forward("AAL", returns, estimator)
```

`WalkForwardEstimator` is the model lifecycle boundary. The current linear
baseline implements it without coupling the generic evaluator to scikit-learn.
Every scalar prediction is retained as a `WalkForwardRecord` for later tables
and charts, while `BacktestMetrics` is calculated only by Rust. The workflow
consumes an explicit return series and never fetches live data or requires an
API key during training or evaluation.
