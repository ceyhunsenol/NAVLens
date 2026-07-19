# Predictions

NAVLens predictions distinguish a point estimate from an uncertainty interval.
Neither value is a guarantee of a future fund return.

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

## Interpretation

Nominal confidence and observed coverage are different. A model producing
ninety-percent intervals should be evaluated over sufficient out-of-sample data
to determine whether observed coverage is close to that level. Wider intervals
can increase coverage without improving usefulness, so coverage and width must
be reported together.

NAVLens will display the model version, data snapshot, target date, and nominal
confidence beside every probabilistic prediction once those metadata layers are
implemented.

