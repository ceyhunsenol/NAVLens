# Prediction model catalog

This document is the authoritative catalog of statistical estimators executed
by NAVLens. It covers machine-learning and statistical prediction models only;
Rust domain models, persistence records, API DTOs, and view models are governed
by the taxonomy in [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Status definitions

- **Implemented:** executable, tested, and reachable through a documented API
  or command.
- **Experimental:** implemented but not established as useful across funds and
  market regimes.
- **Planned:** design intent only; it MUST NOT be described as available.

## Catalog

| Model identifier | Status | Inputs | Purpose |
| --- | --- | --- | --- |
| `linear-regression-baseline` | Implemented, experimental | Last `N` canonical fund returns | First trainable reference model |
| `historical-mean-baseline` | Planned | Earlier canonical fund returns | Naive level benchmark |
| `last-return-baseline` | Planned | Most recent canonical fund return | Naive persistence benchmark |

No holdings-aware, market-aware, macroeconomic, calendar-aware, or news model
is implemented yet.

## Shared prediction target

The current target identifier is
`next_published_nav_return_decimal`. It means the decimal return between the
latest two consecutively published fund unit prices in a chronological series.
For example, `0.01` means a positive one-percent return.

Python MUST NOT calculate this target from raw prices. Provider prices are
mapped to validated Rust values and `calculate_price_returns` owns the canonical
price-to-return calculation. A model consumes the resulting dated decimal
returns.

The target is the next *published* NAV return, not necessarily a one-calendar-
day return. Weekends, holidays, and missing publication dates can make the
elapsed calendar period longer.

## Linear regression baseline

### Identity

- Model identifier: `linear-regression-baseline`
- Implementation: `python/navlens/estimators/linear_baseline.py`
- Trainer: `python/navlens/training/linear_baseline.py`
- Feature schema: `lagged-returns-v1`
- Library: scikit-learn `LinearRegression`
- Status: implemented and experimental

### Features

For a configured `lookback=N`, one row contains only the `N` returns preceding
its target:

```text
return_decimal_lag_1
return_decimal_lag_2
...
return_decimal_lag_N
```

With `--lookback 5`, the model has five numeric inputs. It does not currently
receive fund holdings, security prices, exchange rates, interest rates, fund
size, investor count, day of week, elapsed calendar days, news, or economic
indicators.

### Training and inference

Backtests use an expanding window. At every target date NAVLens:

1. takes only returns available through the prediction date;
2. rebuilds lagged features from that history;
3. fits a fresh linear-regression artifact;
4. predicts the next published NAV return;
5. records the actual return only after prediction;
6. advances the window and repeats.

The minimum history is `lookback + 3` returns because fitting requires at least
three supervised feature rows. A larger initial history can be selected with
`--minimum-training-returns`.

### Prediction interval

The baseline calculates absolute residuals on its training rows and selects the
configured quantile with NumPy's `higher` method. The resulting residual radius
is subtracted from and added to the point estimate. Rust then validates the
point estimate, bounds, and confidence level as one `ReturnPrediction`.

This is an intentionally transparent baseline interval. It is calibrated on
training residuals, not a separate calibration set, and is not a production
uncertainty guarantee. Out-of-sample interval coverage and mean width MUST be
reported together.

### Evaluation

The supported end-to-end command is:

```text
navlens-backtest-tefas AAL --days 365 --lookback 5
```

Python owns model fitting and chronological orchestration. Rust owns series
validation and the published backtest metrics:

- mean absolute error;
- mean error;
- root mean squared error;
- direction accuracy;
- interval coverage and mean width.

The artifact also contains `linear_train_*` and mean-dummy training diagnostics.
Those in-sample values MUST NOT be presented as evidence of forecasting
performance. Model comparisons use identical out-of-sample walk-forward dates
and Rust metrics.

### Known limitations

- Autocorrelation in recent returns is the only predictive signal available.
- Calendar duration and publication gaps are not explicit features.
- Direction accuracy can be misleading for funds whose returns are almost
  always positive or almost always negative.
- The residual interval can be too narrow, especially in early training steps.
- One fund or one period cannot establish general model quality.
- Chronological slicing does not yet prove publication-time correctness for
  future holdings or external feature sources.

## Model admission rules

A new estimator is accepted only when all of the following are satisfied:

1. It has a stable model identifier and explicit model version.
2. Its target and decimal/percentage units are documented.
3. Its feature schema has a version and lists every input.
4. Training receives an explicit dataset and performs no hidden network access.
5. It implements the consumer-owned `WalkForwardEstimator` protocol.
6. Its output crosses the validated Rust `ReturnPrediction` boundary.
7. Tests demonstrate that target and future observations cannot affect an
   earlier prediction.
8. It runs on the same evaluation dates as its comparison baselines.
9. Canonical metrics are delegated to Rust rather than reimplemented.
10. Prediction interval construction and limitations are documented.
11. Dependencies are MIT-compatible and justified for the Python research
    layer.
12. This catalog is updated in the same change.

## Next comparison milestone

The next implemented models will be `historical-mean-baseline` and
`last-return-baseline`. They will use the same `WalkForwardEstimator` boundary,
dates, target, Rust validation, and Rust metrics as linear regression. Until
that comparison exists, a high score from `linear-regression-baseline` MUST NOT
be interpreted as proof that it adds predictive value.

Machine-readable run manifests and persisted comparison artifacts are planned
but are not implemented yet.
