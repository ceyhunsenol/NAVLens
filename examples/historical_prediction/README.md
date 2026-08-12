# Historical prediction example

This example replays two next-published-NAV predictions against synthetic fund
unit-price snapshots. The data is intentionally provider-neutral and requires
no network access or API key.

From the repository root, after installing the development package, run:

```powershell
navlens-evaluate-historical-prediction-csv `
  --schedule-csv examples/historical_prediction/prediction_schedule.csv `
  --fund-unit-prices-csv examples/historical_prediction/fund_unit_prices.csv `
  --fund-id DEMO `
  --source-id example `
  --lookback 5 `
  --confidence-level 0.95 `
  --model-version v1.0 `
  --output-format text
```

The output contains native aggregate backtest metrics followed by one audit
row for each requested period. These CSV values are fixtures, not market data
or investment guidance.
