# ADR-0007: Versioned backtest run manifests

- Status: Accepted
- Date: 2026-07-20

## Context

NAVLens can acquire a source artifact and compare estimators chronologically,
but its results currently exist only as terminal output. Reproducing a result
requires an explicit record of the source artifact, model configuration,
prediction rows, and canonical Rust metrics. Future API and visualization
layers also need a stable result boundary that does not recalculate finance or
evaluation logic.

## Decision

1. The Python evaluation layer owns a versioned JSON run-manifest schema for
   research backtests.
2. Each manifest records a unique run identifier, timezone-aware generation
   time, target definition, acquisition date, source SHA-256 digest, request
   interval, model metadata, predictions, and metrics already calculated by
   Rust.
3. Local JSON persistence is an infrastructure concern and uses atomic file
   replacement under an ignored `data/runs/` directory by default.
4. Mapping into manifest records is explicit. Provider records, Python
   estimator objects, and PyO3 objects do not leak into the JSON contract.
5. Consumers must select a parser by `schema_version`. An incompatible shape
   requires a new schema version rather than silently changing version 1.
6. The manifest layer serializes canonical values; it must not calculate
   returns, intervals, or backtest metrics.

## Consequences

- A CLI run becomes auditable and can be consumed later without rerunning the
  provider request or model evaluation.
- Run files may be large because version 1 retains every prediction for every
  compared estimator.
- Local JSON is appropriate for the research stage but is not a database or a
  repository implementation for a future production application layer.
- Any future Rust/API reader must implement the versioned contract and verify
  compatibility rather than importing Python implementation details.

## Alternatives considered

### Store only terminal output

Rejected because it loses typed structure, schema identity, and reliable
provenance.

### Introduce PostgreSQL now

Rejected because the current need is local, append-only experiment evidence;
a database would add operational complexity before query requirements exist.

### Recalculate metrics while serializing

Rejected because Rust already owns canonical evaluation metrics and a second
implementation would violate ownership and parity rules.
