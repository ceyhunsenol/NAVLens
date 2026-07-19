# Data pipeline

NAVLens keeps transport, normalization, financial validation, dataset mapping,
and training as separate capabilities.

## Current CSV path

```text
CSV file
  -> navlens.sources.csv.parser
  -> CsvPriceRecord
  -> navlens.sources.csv.normalizer
  -> Rust PriceObservation / UnitPrice
  -> Rust calculate_price_returns
  -> navlens.datasets.pandas_returns
  -> pandas decimal-return Series
  -> feature and estimator modules
```

A CSV contains one fund and has this schema:

```csv
date,unit_price
2026-01-02,100.0
2026-01-05,101.0
```

The fund identifier is supplied once to `load_fund_returns_csv`. The parser owns
only encoding, columns, dates, and numeric transport conversion. Rust owns fund
identifier validation, positive-price validation, chronological ordering, and
the decimal-return formula.

```python
from navlens.datasets import load_fund_returns_csv

dataset = load_fund_returns_csv("ABC", "data/raw/abc-prices.csv")
returns = dataset.returns
```

Training receives `returns`; it never opens this file itself.

## Data ownership

- `data/raw/` contains unmodified local downloads and is ignored.
- `data/processed/` contains reproducible derived data and is ignored.
- Only small synthetic test fixtures are committed.
- External data is not relicensed under the repository's MIT license.

## Planned provider path

A future TEFAS source will own HTTP transport and provider response parsing. It
will produce the same normalized Rust price contracts, so datasets, features,
estimators, and financial calculations will not change.
