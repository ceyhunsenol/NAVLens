# ADR-0004: Price-series and return ownership

- Status: Accepted
- Date: 2026-07-20

## Context

Python estimators need chronological decimal returns, while providers and users
naturally supply dated fund unit prices. Calculating returns independently in
Python would duplicate a canonical financial formula. `navlens-core` cannot own
dated observations because `MarketDate` belongs to `navlens-calendar`, and
moving or duplicating the date type would violate the dependency contract.

The boundary must also prevent invalid prices, empty or one-element series,
duplicate dates, and decreasing dates before data reaches feature engineering.
Provider payloads, persistence records, and pandas objects must remain outside
the domain contract.

## Decision

1. `navlens-core` owns `UnitPrice` and the canonical decimal-return calculation
   `(current_price / previous_price) - 1`.
2. A unit price must be finite and strictly positive.
3. `navlens-calendar` owns a qualified `pricing` capability containing dated
   price observations, dated decimal-return observations, and chronological
   price-series validation. It may depend on `navlens-core` as already allowed
   by the architecture contract.
4. `PriceSeries` owns one `FundId`; individual observations do not duplicate the
   identifier.
5. A price series requires at least two observations and rejects duplicate or
   decreasing dates. Whether a date is an open market session remains a
   separate policy requiring an explicit `MarketCalendar`.
6. Each calculated return is dated with the current observation date and uses
   only that observation and its immediate predecessor.
7. PyO3 exposes explicit projections and delegates all validation and financial
   arithmetic to Rust. Python feature code consumes the resulting decimal
   returns and never recalculates them from prices.

## Consequences

- Rust remains the only owner of the unit-price return formula.
- Python training receives chronological, validated decimal returns.
- Calendar and core dependency direction remains inward and acyclic.
- Provider-specific fields must be mapped before constructing domain prices.
- Adjustments for splits, distributions, fees, or provider corrections are not
  silently assumed; they require explicit future contracts.

## Alternatives considered

### Calculate percentage changes with pandas

Rejected because it would create a second implementation of a canonical
financial calculation and make Python library behavior part of the domain.

### Put dated prices in `navlens-core`

Rejected because it would duplicate `MarketDate` or reverse the established
dependency direction.

### Put price-series validation in the PyO3 adapter

Rejected because CLI, API, backtest, and infrastructure callers need the same
rules, while an adapter must only map values and errors.
