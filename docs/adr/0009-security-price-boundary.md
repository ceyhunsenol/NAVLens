# ADR-0009: Provider-neutral security price boundary

- Status: Accepted
- Date: 2026-07-21

## Context

NAVLens requires security price series to value fund holdings and construct
holdings-aware return estimates. Existing fund unit-price abstractions
(`PriceObservation` under `navlens-calendar`) contain only `MarketDate` and
`UnitPrice`. They assume an implicit single-fund context and a single local
currency (`TRY`).

Holding portfolios contain diverse instruments across multiple asset classes and
currencies. Reusing fund unit-price types for individual security prices would
introduce ambiguity:
- securities lack explicit identification in `PriceObservation`;
- prices lack explicit currency tags, risking silent cross-currency mixing;
- corporate action status (unadjusted vs. split-adjusted vs. total-return-adjusted)
  is untracked;
- single-date price observations lack availability timestamps, risking
  future-data leakage in backtests.

A provider-neutral security price boundary must define canonical Rust types for
financial validation while establishing a publication-time-safe Python dataset
envelope.

## Decision

### 1. Scope of initial implementation

The first implementation covers end-of-day monetary security prices only.
Intraday prices, foreign-exchange (FX) rates, index levels, commodities, and
corporate-action adjustment calculations are explicitly deferred.

### 2. Crate placement and dependency direction

To preserve the acyclic dependency direction (`navlens-calendar` depends on
`navlens-core`):
- `CurrencyCode` belongs to `navlens-core`.
- `SecurityPriceObservation` and `PriceAdjustment` belong under
  `navlens-calendar::pricing`.
- No new crate is created for this milestone.

`SecurityPriceObservation` MUST NOT be placed in `navlens-core` because
`MarketDate` is owned by `navlens-calendar`.

### 3. Canonical Rust types

The Rust security price boundary reuses existing domain types and introduces
narrow value objects:

- `InstrumentId` (`navlens-core`): validated provider-neutral identifier. Its
  validation covers length, whitespace, and control characters; it does not
  assert ISIN checksum validity or ticker stability.
- `MarketDate` (`navlens-calendar`): Gregorian trade date.
- `UnitPrice` (`navlens-core`): finite, strictly positive price value (`f64`).
- `CurrencyCode` (`navlens-core`): validated 3-letter ASCII value object (e.g.
  `TRY`, `USD`, `EUR`). It validates format (`[A-Z]{3}`) without claiming full
  ISO-4217 registry membership validation.
- `PriceAdjustment` (`navlens-calendar::pricing`): enum with explicit variants:
  - `Unadjusted`
  - `SplitAdjusted`
  - `TotalReturnAdjusted`

`SecurityPriceObservation` encapsulates these five Rust types:

```text
SecurityPriceObservation
├── instrument_id: InstrumentId
├── market_date: MarketDate
├── price: UnitPrice
├── currency: CurrencyCode
└── adjustment: PriceAdjustment
```

### 4. Layer ownership and Python provenance envelope

Rust owns financial types, invariants, and series validation. Python owns
transport parsing, dataset mapping, and provenance tracking.

Python wraps `SecurityPriceObservation` inside an immutable envelope:

`SecurityPriceSnapshot`:
- `observation`: `SecurityPriceObservation` (Rust-backed PyO3 object)
- `available_at`: timezone-aware UTC `datetime`
- `ingested_at`: timezone-aware UTC `datetime`
- `source_id`: `str`

`SecurityPriceSnapshot` MUST NOT duplicate `instrument_id`, `market_date`,
`currency`, or `price` as top-level Python fields outside the inner observation.

### 5. Point-in-time rules and leakage prevention

- `available_at` is defined precisely as the earliest defensible UTC timestamp at
  which the price observation was published and could be consumed by a model.
- Point-in-time selection MUST reject any observation where `available_at` is
  later than the simulated prediction timestamp (`available_at <= prediction_timestamp`).
- `ingested_at` MUST NOT precede `available_at`.

### 6. Observation identity and corrections

The dataset correction identity is defined by the five-tuple:
`(source_id, instrument_id, market_date, currency, adjustment)`

A corrected observation for the same identity supersedes an earlier observation
only after the correction's `available_at` timestamp has passed. Prior to that
timestamp, backtests MUST continue to consume the original observation.
Observations from different sources MUST NOT supersede one another implicitly;
cross-source preference requires a separate, explicit selection policy.

### 7. Series homogeneity rule

A security price series MUST NOT silently mix currencies or adjustment policies.
All observations in a series MUST share the same `instrument_id`, `currency`,
and `adjustment`.

### 8. Future FX and index separation

- FX rates MUST later use a separate `FxRateObservation` with explicit base and
  quote currencies.
- Index levels MUST later use a separate `IndexLevelObservation`. Index points
  MUST NEVER be represented as a currency price.

## Smallest implementation sequence

1. Add `CurrencyCode` to `navlens-core`.
2. Add `PriceAdjustment` and `SecurityPriceObservation` under
   `navlens-calendar::pricing`.
3. Expose `CurrencyCode`, `PriceAdjustment`, and `SecurityPriceObservation`
   through `navlens-python`.
4. Add `SecurityPriceSnapshot` and selection logic in `navlens.datasets`.
5. Add local CSV parser `read_security_prices_csv` in `navlens.sources`.

## Consequences

- Security price observations gain explicit identification, currency tags, and
  adjustment tracking.
- Dependency direction between `navlens-core` and `navlens-calendar` remains
  acyclic.
- Backtests prevent lookahead leakage via `available_at` timestamps.
- Price series avoid silent cross-currency or mixed-adjustment corruption.

## Deferred decisions

- Corporate-action ratio adjustment arithmetic and dataset transformations.
- Deterministic FX currency conversion calculations.
- `FxRateObservation` and `IndexLevelObservation` contracts.
- Automated external market data provider integration.

## Alternatives considered

### Place `SecurityPriceObservation` in `navlens-core`

Rejected because `MarketDate` lives in `navlens-calendar`. Moving `MarketDate`
or creating duplicate date types in core would violate architectural boundaries.

### Represent currencies as an enum

Rejected because an enum would require maintaining an exhaustive ISO registry,
whereas a 3-letter uppercase ASCII value object provides sufficient validation
without premature coupling.

### Duplicate identity fields on `SecurityPriceSnapshot`

Rejected because duplicating `instrument_id` or `currency` on the Python envelope
creates a second unvalidated representation alongside the Rust observation.
