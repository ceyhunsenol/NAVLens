# Data pipeline

NAVLens keeps transport, normalization, financial validation, dataset mapping,
and training as separate capabilities.

## Current CSV path

```text
CSV file
  -> navlens.sources.csv.parser
  -> CsvPriceRecord
  -> navlens.sources.price_observations
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

## TEFAS source boundary

TEFAS does not provide a documented public API. NAVLens calls the JSON price
endpoint used by the website through an isolated Python adapter. The client
owns HTTP transport, the parser owns provider fields, and the shared source
normalizer performs the single Python-to-Rust price mapping.

`AcquireTefasPrices` checks the local cache, fetches when necessary, stores the
exact response bytes and provenance metadata atomically, then invokes the TEFAS
parser. Training never triggers this acquisition implicitly.

`build_tefas_fund_returns` accepts an already completed acquisition, verifies
that its records describe one fund, and delegates to the same
`build_fund_return_dataset` path used by CSV. That shared path maps records to
PyO3 observations, invokes the Rust return calculation, and creates the pandas
series. Dataset construction never performs an HTTP request.

The Python data-source entry point exposes this same orchestration without
duplicating it:

```shell
navlens-fetch-tefas AAL --days 30
```

This narrowly scoped acquisition command is distinct from the Rust `navlens`
product CLI. It owns command-line mapping and output only; provider transport,
cache, storage, and parsing remain in their existing TEFAS modules.

The aggregate one-month, three-month, and similar return columns on the TEFAS
fund-returns page are not dated unit prices and cannot feed this pipeline as
prices. See [`TEFAS_DATA_ACCESS.md`](TEFAS_DATA_ACCESS.md) for the verified
boundary and provenance requirements, and
[`ADR-0006`](adr/0006-tefas-data-access.md) for the decision.
