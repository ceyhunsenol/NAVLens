# Command-line interface

The `navlens` binary is the first executable adapter for NAVLens. It parses
transport input, creates application commands, invokes one use case, and formats
the result. It does not implement financial calculations.

`main.rs` remains a process composition boundary only: parse arguments, invoke
the command dispatcher, write output/error, and select an exit code. Command
definitions, mapping, formatting, and use-case behavior live in focused modules
or inner crates.

## Exit-code and error contract

All public Python commands use the same process-level conventions:

- `--help` writes usage information and exits with `0`.
- Missing or invalid command-line arguments are handled by `argparse`, write to
  stderr, and exit with `2` before application orchestration starts.
- Expected data, validation, filesystem, and provider failures write an
  `error:` message to stderr without a traceback and return `1`.
- Unexpected programming errors are not converted into operational failures;
  they propagate so defects remain visible during development and CI.

Commands that support partial batch or historical outcomes may also return `2`
after producing a valid report. Their command-specific sections describe that
partial-success meaning. Scripts consuming NAVLens output must therefore use
both the documented command contract and the process exit code.

## Estimate a weighted portfolio return

Each `--component` uses `WEIGHT:DECIMAL_RETURN` format. Weights must sum to one.
Returns and the daily expense rate use decimal units.

```shell
cargo run -p navlens-cli -- estimate \
  --component 0.7:0.02 \
  --component 0.2:-0.01 \
  --component 0.1:0.001 \
  --daily-expense-rate 0.0001
```

Expected output:

```text
estimated_return_decimal=0.0120000000
estimated_return_percent=1.200000%
```

The command flow is:

```text
CLI arguments
    → EstimatePortfolioReturnCommand
    → navlens-application use case
    → navlens-core domain calculation
    → application result
    → CLI output
```

Invalid syntax is reported by `clap`. Domain violations such as negative or
out-of-range weights are mapped to application errors and result in a non-zero
process exit code.

## Reconcile published fund return against observed portfolio contribution

The `navlens-reconcile-fund-csv` Python CLI runs the point-in-time portfolio return
contribution pipeline and reconciles its results against the published fund return
represented by historical snapshots from CSV sources.

```shell
navlens-reconcile-fund-csv \
  --holdings-csv holdings.csv \
  --security-prices-csv prices.csv \
  --fund-unit-prices-csv fund_prices.csv \
  --fund-id FUND1 \
  --holdings-source-id tefas \
  --security-price-source-id kap \
  --fund-price-source-id tefas \
  --prediction-timestamp 2026-07-28T00:00:00Z \
  --pricing-as-of-date 2026-07-27 \
  --fund-base-currency TRY \
  --price-adjustment total_return_adjusted \
  --minimum-observations 2 \
  --max-staleness-calendar-days 5 \
  --return-start-date 2026-07-26 \
  --return-end-date 2026-07-27
```

Expected output includes the portfolio components' exact weighted contributions,
coverage ratios, and exact decimal values for the reconciliation terms.
For example:

```text
Published Fund Return (Decimal): 0.120000
Observed Portfolio Contribution (Decimal): 0.100000
Return Coverage (Ratio): 1.000000
Reconciliation Residual (Decimal): 0.020000
```

## Reconcile published fund return against observed FX-adjusted portfolio contribution

The `navlens-fx-reconcile-fund-csv` Python CLI runs the point-in-time FX-adjusted portfolio
return contribution pipeline and reconciles its results against the published fund return
represented by historical snapshots from CSV sources.

```shell
navlens-fx-reconcile-fund-csv \
  --holdings-csv holdings.csv \
  --security-prices-csv prices.csv \
  --fx-rates-csv fx_rates.csv \
  --fund-unit-prices-csv fund_prices.csv \
  --fund-id FUND1 \
  --holdings-source-id tefas \
  --security-price-source-id kap \
  --fx-source-id tcmb \
  --fund-price-source-id tefas \
  --required-fx-rate-kind non_cash_buying \
  --max-fx-staleness-calendar-days 5 \
  --prediction-timestamp 2026-07-28T00:00:00Z \
  --pricing-as-of-date 2026-07-27 \
  --fund-base-currency TRY \
  --price-adjustment total_return_adjusted \
  --minimum-observations 2 \
  --max-staleness-calendar-days 5 \
  --return-start-date 2026-07-26 \
  --return-end-date 2026-07-27
```

Expected output includes the FX-adjusted component contributions, currency adjustments, coverage ratios, and exact decimal values for the reconciliation terms.

## Predict next published NAV return from CSV fund unit price snapshots

The `navlens-predict-fund-csv` CLI runs the provider-neutral point-in-time prediction pipeline for a single fund return.

```shell
navlens-predict-fund-csv \
  --fund-unit-prices-csv fund_prices.csv \
  --fund-id AAL \
  --source-id tefas \
  --prediction-timestamp 2026-07-28T00:00:00Z \
  --prediction-date 2026-07-27 \
  --pricing-as-of-date 2026-07-27 \
  --target-date 2026-07-28 \
  --lookback 5 \
  --output-format text
```

JSON output (`--output-format json`) emits deterministic UTF-8 versioned JSON matching schema `navlens-single-return-prediction-v1`.

## Acquire TEFAS prices and predict the next published NAV return

The `navlens-predict-tefas` CLI combines keyless TEFAS acquisition with the
same canonical point-in-time prediction pipeline used by the CSV command.
The target date can be explicit or selected by the canonical Rust market
calendar. Provider price history does not encode exceptional future closures,
so automatic selection accepts repeatable `--closed-date` overrides.

```shell
navlens-predict-tefas AAL --days 365 --target-date 2026-08-13 \
  --lookback 5 --confidence-level 0.90 --max-price-age-days 4
```

To select the next open weekday automatically:

```shell
navlens-predict-tefas AAL --days 365 --auto-target-date
```

Declare known holidays or exceptional closures explicitly. The Rust calendar
then skips both weekends and the supplied dates:

```shell
navlens-predict-tefas AAL --days 365 --auto-target-date \
  --closed-date 2026-08-14 --closed-date 2026-08-17
```

NAVLens does not yet embed an official Turkish market-holiday provider.
Use explicit `--target-date` when the future publication calendar is uncertain.
Use `--output-format json` for the versioned single-prediction JSON schema.
Use `--output PATH` to atomically store the selected text or JSON representation
instead of writing it to standard output. Existing files are never overwritten.
Historical TEFAS observations do not include individual publication
timestamps, so this command conservatively treats every acquired observation
as available at the current acquisition timestamp.
The command rejects a latest unit price older than four calendar days by
default. Use `--max-price-age-days` to set an explicit alternative for known
market closures; the configured limit is never silently relaxed.

### Predict multiple TEFAS funds

`navlens-predict-tefas-batch` applies one acquisition interval, target-date
policy, freshness policy, and model configuration to multiple unique funds.
Funds execute sequentially in input order. An expected provider or validation
failure is isolated to its fund and does not discard successful predictions.

```shell
navlens-predict-tefas-batch AAL PHE TLY --days 365 --auto-target-date \
  --lookback 5 --max-price-age-days 4
```

Text output contains batch counts followed by CSV-compatible success and
failure rows. `--output-format json` emits the deterministic
`navlens-tefas-prediction-batch-v1` schema; each successful entry embeds the
existing single-prediction schema without recalculating prediction fields.

Exit code `0` means every fund succeeded, `2` means partial success, and `1`
means every requested fund failed.

Batch output supports `--output PATH` with the same atomic, no-overwrite
contract. This is the recommended form for retaining prediction artifacts that
will later be compared with published NAV returns.

### Evaluate a stored TEFAS prediction

`navlens-evaluate-tefas-prediction` loads a JSON artifact produced by
`navlens-predict-tefas`, acquires the exact last-observation and target-date NAV
values, and delegates realized-return and prediction-metric calculations to
the canonical Rust boundaries.

```shell
navlens-evaluate-tefas-prediction artifacts/predictions/aal.json \
  --as-of 2026-08-14 --output-format json \
  --output artifacts/evaluations/aal.json
```

Evaluation fails explicitly when the artifact schema or source is unsupported,
the target date is later than `--as-of`, or either exact period-boundary NAV is
missing. It never substitutes a nearby date. The report includes predicted and
realized returns, signed and absolute error, direction correctness, interval
coverage, evaluation timestamp, and TEFAS raw-artifact provenance.

For multiple explicit prediction artifacts, or one JSON artifact produced by
`navlens-predict-tefas-batch`, use the failure-isolated batch command:

```shell
navlens-evaluate-tefas-prediction-batch \
  artifacts/predictions/aal-2026-08-14.json \
  artifacts/predictions/aal-2026-08-15.json \
  --as-of 2026-08-16 --output-format json \
  --output artifacts/evaluations/aal-batch.json
```

An expected failure in one artifact does not discard successful evaluations.
The exit code is `0` for complete success, `2` for partial success, and `1`
when every artifact fails. Successful entries retain the complete versioned
evaluation contract and can be consumed directly by the history command.

### Summarize stored live prediction evaluations

`navlens-summarize-prediction-evaluations` combines explicit single or batch
evaluation artifacts into one native backtest report:

```shell
navlens-summarize-prediction-evaluations \
  artifacts/evaluations/aal-2026-08-14.json \
  artifacts/evaluations/aal-2026-08-15.json \
  --output-format json \
  --output artifacts/evaluations/aal-history.json
```

All inputs must describe the same fund, source, and model identity, and must be
supplied in chronological order. NAVLens performs no implicit directory scan.
Duplicate or decreasing dates are rejected by the canonical Rust backtest
boundary. Aggregate error, direction, and interval metrics are also calculated
there. File output is atomic and refuses to overwrite an existing artifact.

### Compare live model histories fairly

Use one repeated `--history` group per model. Every group may contain single
evaluation artifacts, batch evaluation artifacts, or a mixture:

```shell
navlens-compare-prediction-histories \
  --history ridge-day-1.json ridge-day-2.json \
  --history last-return-day-1.json last-return-day-2.json \
  --output-format json --output model-comparison.json
```

Comparison requires the same fund, source, prediction/target periods, realized
returns, and confidence level. Model identities must be unique. NAVLens reports
each model's Rust-produced error, direction, and interval metrics without
declaring a subjective winner or silently ranking unlike samples.

## Evaluate historical point-in-time NAV return predictions

The `navlens-evaluate-historical-prediction-csv` CLI replays a chronological
prediction schedule against provider-neutral fund unit-price snapshots. Each
prediction sees only snapshots available at its `prediction_timestamp`; the
realized target is selected independently at `evaluation_timestamp`.

```shell
navlens-evaluate-historical-prediction-csv \
  --schedule-csv prediction_schedule.csv \
  --fund-unit-prices-csv fund_prices.csv \
  --fund-id AAL \
  --source-id tefas \
  --lookback 5 \
  --confidence-level 0.90 \
  --model-version v1 \
  --output-format text
```

The schedule CSV requires these columns:

```text
prediction_date,pricing_as_of_date,target_date,prediction_timestamp,evaluation_timestamp
```

Dates use `YYYY-MM-DD`; timestamps must be timezone-aware UTC values. Text
output reports Rust-produced aggregate backtest metrics followed by one ordered
audit row per period. Successful rows include predicted and realized decimal
returns; skipped rows include a stable typed reason code. JSON output contains
the same aggregate evaluation and period provenance as deterministic UTF-8
schema version `1`. Exit code `0` means every period was evaluated, `2` means
at least one period was skipped, and `1` means an operational input or
evaluation error occurred.

A network-free executable example is available under
[`examples/historical_prediction`](../examples/historical_prediction/README.md).
It uses synthetic provider-neutral snapshots and exercises the same CLI path.
