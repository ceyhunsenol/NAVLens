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

The authoritative model inputs, interval method, limitations, status, and
admission rules are recorded in
[`PREDICTION_MODELS.md`](PREDICTION_MODELS.md).

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

## TEFAS command

The installed package provides a composition-root command that connects the
keyless TEFAS acquisition adapter to the canonical dataset and walk-forward
evaluation pipeline:

```text
navlens-backtest-tefas AAL --days 365 --lookback 5
```

The command compares linear regression, historical mean, and last return on
identical out-of-sample dates. It reports source provenance, model
configuration, a compact decimal-unit Rust metrics table, and one
CSV-compatible row for every linear-model prediction. It uses the existing
raw-response cache and does not introduce a second TEFAS client, return
calculation, or metric implementation.

Every successful run also writes a versioned JSON artifact to `data/runs/`.
The terminal output includes its `run_id` and path. A different destination can
be selected explicitly:

```text
navlens-backtest-tefas AAL --days 365 --lookback 5 --run-root artifacts/runs
```

The complete schema and compatibility rules are documented in
[`RUN_MANIFESTS.md`](RUN_MANIFESTS.md).

## Multi-fund TEFAS batch

The batch command applies the same acquisition, dataset, estimator comparison,
Rust metrics, and run-manifest pipeline to each requested fund:

```text
navlens-backtest-batch AAL YAY MAC --days 365 --lookback 5
```

Funds execute sequentially in input order. Cached artifacts are reused without
delay; consecutive live provider requests retain the TEFAS adapter's configured
minimum interval. The batch layer does not contain an alternative provider
client, estimator, return calculation, or metrics implementation.

An expected source, validation, or local-storage failure is isolated to its
fund and does not prevent later funds from running. The compact output contains
one metrics row per successful fund/model and one error row per failed fund.
Every successful fund retains its own versioned run manifest. Batch output is
not yet persisted as a separate aggregate artifact.

Exit codes are:

- `0`: every fund succeeded;
- `2`: at least one fund succeeded and at least one failed;
- `1`: every fund failed.

## Historical reconciliation evaluation scope

Evaluating historical reconciliation outcomes across multiple periods requires
a homogeneous fund and data-source scope.
`evaluate_historical_reconciliation_dataset` verifies that every outcome (both
successful and skipped) in an evaluated dataset shares exact equality for:

- `fund_id`;
- `holdings_source_id`;
- `security_price_source_id`;
- `fund_price_source_id`;
- `fx_source_id` (for FX-aware datasets; `None` for legacy datasets);
- dataset `kind` (`LEGACY` versus `FX_AWARE`).

The derived `HistoricalReconciliationEvaluationScope` is exposed on
`HistoricalReconciliationEvaluation.scope`. Outcome scope mismatches fail fast
with `MixedHistoricalReconciliationScopeError`.

## Historical reconciliation evaluation reporting

The Python evaluation package provides two in-memory reporting functions under
`navlens.reconciliation.historical`:

- `format_historical_reconciliation_evaluation(evaluation)`: returns a
  deterministic multi-line human-readable text report.
- `serialize_historical_reconciliation_evaluation(evaluation)`: returns
  deterministic UTF-8 JSON bytes adhering to versioned schema version 1
  (`schema_version = 1`).

All metrics formatted or serialized by these functions originate strictly from
native Rust calculations via `ReconciliationMetrics`; Python does not calculate or
recalculate financial metrics. These functions provide in-memory presentation of
existing `HistoricalReconciliationEvaluation` instances and are distinct from CLI
commands, file persistence, or backtest run manifests.

## Historical reconciliation evaluation CLI

The package provides a provider-neutral CSV command line interface for historical
fund-return reconciliation evaluation over multiple periods:

```text
navlens-evaluate-historical-reconciliation-csv \
  --schedule-csv schedule.csv \
  --holdings-csv holdings.csv \
  --security-prices-csv prices.csv \
  --fund-unit-prices-csv fund_prices.csv \
  --fund-id AAL \
  --holdings-source-id src_h \
  --security-price-source-id src_p \
  --fund-price-source-id src_f \
  --fund-base-currency TRY \
  --price-adjustment unadjusted \
  --minimum-observations 2 \
  --max-staleness-calendar-days 5 \
  --output-format text
```

### Schedule CSV format

The request schedule CSV specifies the period schedule and prediction timestamps:

- `return_start_date`: Period start date (`YYYY-MM-DD`).
- `return_end_date`: Period end date (`YYYY-MM-DD`).
- `pricing_as_of_date`: Holding/price alignment as-of date (`YYYY-MM-DD`).
- `prediction_timestamp`: Timezone-aware UTC ISO-8601 timestamp (`YYYY-MM-DDTHH:MM:SSZ`).

### Exit codes

- `0`: Dataset evaluated successfully and 0 periods were skipped.
- `2`: Evaluation completed, but 1 or more periods were skipped (or all periods were skipped). Command-line syntax or invalid argument choice errors terminate with `argparse`'s standard exit code `2` before evaluation begins.
- `1`: Handled operational, CSV format/parsing, or domain validation error (message printed to `stderr`).

## Historical FX reconciliation evaluation CLI

The package also provides an FX-aware historical reconciliation command line interface
(`navlens-evaluate-historical-fx-reconciliation-csv`) extending legacy evaluation:

```text
navlens-evaluate-historical-fx-reconciliation-csv \
  --schedule-csv schedule.csv \
  --holdings-csv holdings.csv \
  --security-prices-csv prices.csv \
  --fx-rates-csv fx_rates.csv \
  --fund-unit-prices-csv fund_prices.csv \
  --fund-id AAL \
  --holdings-source-id src_h \
  --security-price-source-id src_p \
  --fx-source-id src_fx \
  --fund-price-source-id src_f \
  --fund-base-currency TRY \
  --price-adjustment unadjusted \
  --required-fx-rate-kind non_cash_buying \
  --minimum-observations 2 \
  --max-staleness-calendar-days 5 \
  --max-fx-staleness-calendar-days 3 \
  --output-format text
```

It includes four FX-specific arguments:
- `--fx-rates-csv`: Path to CSV containing FX rate observations.
- `--fx-source-id`: Source identifier for FX rates.
- `--required-fx-rate-kind`: Required FX rate variant (e.g. `non_cash_buying`).
- `--max-fx-staleness-calendar-days`: Maximum allowed FX rate staleness in calendar days.

`navlens-evaluate-historical-fx-reconciliation-csv` shares the exact schedule CSV format,
output formats (`text`, `json`), and exit-code semantics (`0`, `2`, `1`) with the legacy
historical reconciliation CLI.
