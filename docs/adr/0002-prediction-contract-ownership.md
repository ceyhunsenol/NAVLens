# ADR-0002: Prediction contract ownership

- Status: Accepted
- Date: 2026-07-19

## Context

Rust application entry points, Python models, backtests, and future HTTP APIs
need one model-independent description of a prediction. The contract combines
financial values owned by `navlens-core` with market dates owned by
`navlens-calendar`.

Placing a second market-date representation in `navlens-core` would violate the
single-owner rule. Making `navlens-core` depend on `navlens-calendar` would also
reverse the intended domain dependency direction. Placing the contract in an
adapter such as PyO3 would make an outer layer the owner of domain invariants.

## Decision

1. `navlens-prediction` owns model-independent prediction requests, results,
   audit timestamps, and model provenance metadata.
2. It may depend on `navlens-core` and `navlens-calendar` and contains no model
   execution, serialization, persistence, or framework code.
3. Market dates and UTC instants are separate values. Market time-zone and
   publication cut-off policies remain explicit future domain decisions.
4. UTC instants cross the domain boundary as signed Unix seconds. Adapters own
   conversion to Python datetime, JSON, database, or display formats.
5. A request rejects targets that do not follow its prediction date and data
   timestamps later than generation time.
6. A result rejects point estimates outside its interval and blank or unsafe
   provenance metadata.
7. Future PyO3 bindings map these types without reproducing their validation.

## Consequences

- Rust and Python will share one validated vocabulary without coupling the
  domain to PyO3 or a Python modeling library.
- `navlens-core` and `navlens-calendar` retain canonical ownership of their
  existing concepts.
- Callers must provide both a market date and UTC audit timestamps deliberately.
- Serialization formats are deferred until the first concrete adapter is built.

## Alternatives considered

### Put every prediction type in `navlens-core`

Rejected because the request would either duplicate `MarketDate` or introduce
an inward dependency on the calendar crate.

### Own the contract in `navlens-python`

Rejected because CLI, API, persistence, and backtest callers also require it,
and an adapter must not own domain rules.

### Exchange untyped dictionaries

Rejected because invalid or ambiguous units would cross the Rust-Python
boundary and validation would be duplicated.
