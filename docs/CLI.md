# Command-line interface

The `navlens` binary is the first executable adapter for NAVLens. It parses
transport input, creates application commands, invokes one use case, and formats
the result. It does not implement financial calculations.

`main.rs` remains a process composition boundary only: parse arguments, invoke
the command dispatcher, write output/error, and select an exit code. Command
definitions, mapping, formatting, and use-case behavior live in focused modules
or inner crates.

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
