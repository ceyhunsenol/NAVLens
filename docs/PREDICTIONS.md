# Predictions

NAVLens predictions distinguish a point estimate from an uncertainty interval.
Neither value is a guarantee of a future fund return.

`navlens-prediction` owns the model-independent contract shared by Rust
applications and future Python bindings. It composes canonical types from
`navlens-core` and `navlens-calendar`; it does not train or execute models.

## Request and audit times

`PredictionRequest` identifies the fund, prediction market date, target market
date, generation timestamp, and latest included data timestamp. Market dates and
UTC instants remain separate because converting an instant to a market date
requires an explicit market time-zone and cut-off policy.

The target date must follow the prediction date. `data_as_of` must not be later
than `generated_at`, preventing a prediction from claiming access to future
data. UTC timestamps use signed Unix seconds at the domain boundary; formatting
and Python datetime conversion belong to adapters.

## Decimal units

Returns and interval bounds use decimal units:

- `0.01` means a positive one-percent return;
- `-0.005` means a negative half-percent return;
- confidence level `0.90` means a nominal ninety-percent interval.

## Point estimate

A point estimate is the model's single central return estimate. It is evaluated
with error and direction metrics, but it does not describe uncertainty by
itself.

## Prediction interval

`PredictionInterval` contains an inclusive lower bound, upper bound, and
`ConfidenceLevel`. The domain rejects reversed bounds and confidence levels
outside the open interval from zero to one.

Backtests evaluate interval predictions with:

- coverage: fraction of actual returns inside the inclusive interval;
- mean width: average distance between lower and upper bounds;
- sample count: number of observations that contain an interval.

A series may contain point-only observations, but all intervals within one
series must use the same confidence level. Mixing nominal confidence levels
would make aggregate coverage misleading and is rejected.

## Provenance

`ReturnPrediction` combines the expected decimal return, its inclusive
`PredictionInterval`, and a `ModelDescriptor`. The expected return must fall
inside the interval. The descriptor records a non-blank model name, model
version, and feature-set version so a result can be reproduced and compared
without knowing which Python library produced it.

## Interpretation

Nominal confidence and observed coverage are different. A model producing
ninety-percent intervals should be evaluated over sufficient out-of-sample data
to determine whether observed coverage is close to that level. Wider intervals
can increase coverage without improving usefulness, so coverage and width must
be reported together.

NAVLens transports the model version, feature-set version, data cut-off, target
date, and nominal confidence with every probabilistic prediction. Persistence
and UI display of that metadata remain future adapter responsibilities.
