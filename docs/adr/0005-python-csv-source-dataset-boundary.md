# ADR-0005: Python CSV source and dataset boundary

- Status: Accepted
- Date: 2026-07-20

## Context

Research workflows need a reproducible local source before a live TEFAS adapter
is introduced. CSV parsing, Rust domain mapping, pandas construction, and model
training are separate responsibilities. Combining them in one loader or trainer
would make provider replacement difficult and would encourage duplicate return
calculations in Python.

Downloaded market data may also have terms different from the MIT-licensed
source code and must not be committed by default.

## Decision

1. `navlens.sources.csv` owns CSV schema validation and parsing into explicit
   `CsvPriceRecord` values.
2. Its normalizer maps records to PyO3 `PriceObservation` values. It does not
   calculate returns or create pandas objects.
3. `navlens.datasets` owns conversion of validated Rust return observations to
   pandas and dataset provenance metadata.
4. One CSV represents one fund. The fund identifier is supplied once to the
   dataset loader and is validated by Rust; it is not repeated in every row.
5. The CSV schema is `date,unit_price`, with ISO-8601 market dates and decimal
   unit prices. Financial price validation and chronological-series validation
   remain in Rust.
6. Training accepts an explicit return series and never opens source files.
7. `data/raw/` and `data/processed/` are local and ignored. Only small synthetic
   fixtures and documentation are committed.

## Consequences

- A future TEFAS adapter can replace CSV parsing without changing dataset,
  feature, estimator, or Rust domain code.
- Native-return to pandas mapping has one implementation.
- Source errors retain CSV context while domain errors remain Rust errors.
- Repeated fund identifiers and mixed-fund CSV files are avoided by design.

## Alternatives considered

### Read CSV inside training

Rejected because training must operate on explicit, reproducible datasets and
must not absorb transport or filesystem concerns.

### Calculate returns with pandas

Rejected because Rust already owns the canonical price-return formula.

### Store the fund identifier on every CSV row

Rejected for the initial adapter because a file is intentionally scoped to one
fund and repeating the identifier permits accidental mixed-fund series.
