# Backtest run manifests

Every successful `navlens-backtest-tefas` execution stores a versioned JSON
manifest under `data/runs/` by default. Use `--run-root PATH` to select another
local directory. Run artifacts are ignored by Git because they are generated
research outputs rather than project source.

## Version 1 contract

The schema identifier is `navlens-backtest-run-v1`. A manifest contains:

- a UUID `run_id` and timezone-aware `generated_at` value;
- the fund identifier and `next_published_nav_return_decimal` target;
- the common initial training size and confidence level;
- the linear model lookback;
- TEFAS acquisition date, request dates, source row count, cache status, path,
  and SHA-256 digest;
- model, version, and feature-schema identifiers;
- Rust-produced decimal-unit metrics for every compared model;
- every chronological prediction, actual return, interval, and training window.

The JSON layer does not calculate returns or metrics. It explicitly maps values
already produced by the dataset, prediction, and Rust backtest boundaries.

## Compatibility

Consumers must inspect `schema_version` before reading other fields. Version 1
may gain no incompatible field or semantic changes. Removing or renaming a
field, changing a unit, or changing nesting requires a new schema version.

Local manifests are append-only experiment evidence, not a production
database. A future repository may import them through an explicit mapper, but
application or API code must not depend directly on Python dataclasses.
