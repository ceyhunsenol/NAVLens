# ADR-0010: Holdings and security-price alignment and coverage policy

- Status: Proposed
- Date: 2026-07-22

## Context

Fund holdings and security prices are published independently and at different
frequencies. A holdings-aware estimate must align the latest usable holdings
snapshot with point-in-time-safe security-price histories without hiding
missing exposures, mixing currencies, or using information that was unavailable
at prediction time.

The existing contracts intentionally carry different availability fields:

- `HoldingSnapshot.published_at` is the earliest time a holdings disclosure may
  be used;
- `SecurityPriceSnapshot.available_at` is the earliest defensible time a price
  observation may be used;
- `ingested_at` records local acquisition time and must not precede the relevant
  publication or availability time.

`HoldingPosition` does not carry a currency. Currency belongs to the matched
`SecurityPriceSeries`, while the fund base currency must be supplied explicitly
to an alignment run. Holding snapshots may also represent less than the entire
fund and currently do not enforce a total-weight invariant. Coverage therefore
requires an explicit accounting policy rather than assuming the listed weights
sum to one.

## Decision

### 1. Canonical identity and duplicate holdings

Holding and security-price alignment MUST use exact `InstrumentId` equality.
Fuzzy matching, display-name matching, and provider-specific fallback mappings
are forbidden at this boundary.

A canonical holdings input MUST contain at most one position for an
`InstrumentId`. Duplicate identifiers make weight accounting ambiguous and MUST
fail the alignment input with `DuplicateHoldingInstrument`; they MUST NOT be
silently aggregated. A source-specific normalizer may combine duplicate source
rows before constructing the canonical snapshot when that transformation is
explicit and tested.

### 2. Point-in-time eligibility

At a supplied `prediction_timestamp`:

- a holdings snapshot is eligible only when
  `published_at <= prediction_timestamp`;
- a security-price snapshot is eligible only when
  `available_at <= prediction_timestamp`;
- a security-price observation is eligible for the aligned history only when
  `market_date <= pricing_as_of_date`.

Later corrections remain invisible until their respective publication or
availability timestamp. `ingested_at` is provenance and does not replace these
eligibility rules. Records excluded by these rules MUST NOT influence matching,
coverage, staleness, or return calculations.

### 3. Explicit alignment policy

Every alignment run MUST receive an explicit policy containing at least:

- `fund_base_currency: CurrencyCode`;
- `required_price_adjustment: PriceAdjustment`;
- `pricing_as_of_date: MarketDate`;
- `minimum_observations` as an integer of at least two;
- `max_staleness_calendar_days` as a non-negative integer.

There are no implicit defaults for currency, adjustment, observation count, or
staleness. The initial calendar-day staleness unit is intentionally explicit and
provider-neutral. Exchange-calendar-aware staleness is deferred until security
venue/calendar identity exists.

### 4. Initial supported asset classes

The first holdings-aware security-price matcher supports only:

- `AssetClass::Equity`;
- `AssetClass::ExchangeTradedFund`.

All other asset classes are reported as `UnsupportedAssetClass`. In particular,
debt securities require accrued-interest and clean/dirty-price policy;
investment funds use the distinct fund unit-price boundary; and repo, deposits,
precious metals, derivatives, cash, and `Other` require dedicated return
contracts. They MUST NOT be forced through `SecurityPriceObservation` merely
because a numeric value is available.

### 5. Price-history requirements

For a supported holding, the selected history MUST:

- match the holding's `InstrumentId` exactly;
- contain at least `minimum_observations` eligible observations;
- be strictly chronological and homogeneous as guaranteed by
  `SecurityPriceSeries`;
- have a latest `market_date` no later than `pricing_as_of_date`.

The minimum may be larger than two when a calculation needs a longer history.
Insufficient history is a coverage gap and MUST NOT be replaced with a zero
return.

### 6. Currency policy

Because `HoldingPosition` has no currency, alignment compares the matched
`SecurityPriceSeries.currency` with the explicit `fund_base_currency`. A mismatch
is reported as `CurrencyMismatch` and the holding remains uncovered. Until an FX
contract exists, local-currency returns MUST NOT be treated as fund-base-currency
returns.

### 7. Price-adjustment policy

`SecurityPriceSeries` already rejects mixed adjustment variants. In addition,
the series adjustment MUST equal the run's explicit
`required_price_adjustment`; otherwise the holding is reported as
`IncompatiblePriceAdjustment`.

NAVLens does not choose a universal adjustment default in this ADR. The chosen
policy must be recorded with the run because unadjusted, split-adjusted, and
total-return-adjusted histories have different financial meanings.

### 8. Staleness policy

Staleness is evaluated from the latest eligible observation's `market_date` to
`pricing_as_of_date` in whole calendar days. A series is `StalePrices` when this
distance exceeds `max_staleness_calendar_days`.

Staleness does not remove arbitrary observations from an otherwise selected
series. It classifies the holding as covered or uncovered after point-in-time
selection. The future `target_date` is not used to measure input staleness.

### 9. Provider isolation

One alignment run MUST select one explicit holdings `source_id` and one explicit
security-price `source_id`. Python MUST NOT choose a holdings correction from a
different source or fill missing instruments by silently mixing price
providers. A future multi-provider policy requires a separate decision and
explicit conflict resolution.

### 10. Coverage and weight accounting

Rust owns the following arithmetic over canonical `PortfolioWeight` values:

- `declared_weight`: sum of all positions in the holdings snapshot;
- `covered_weight`: sum of positions with an accepted aligned price series;
- `uncovered_listed_weight`: sum of listed positions with a coverage gap;
- `unrepresented_weight`: `1.0 - declared_weight`;
- `total_uncovered_weight`: `uncovered_listed_weight + unrepresented_weight`;
- `coverage_ratio`: `covered_weight`, because every position weight is already
  expressed as a share of total fund value.

If `declared_weight > 1.0`, the alignment input is invalid and MUST fail with
`DeclaredWeightExceedsFundTotal`. No tolerance or normalization is implicit in
this ADR. For valid input:

```text
covered_weight + total_uncovered_weight = 1.0
```

Covered positions MUST NOT be renormalized. Unrepresented fund weight remains
explicitly uncovered rather than being assigned to a fabricated instrument or
return.

### 11. Coverage gaps and fatal input errors

An uncovered listed position carries exactly one primary reason, using this
precedence order:

- `UnsupportedAssetClass`;
- `MissingPriceSeries`;
- `InsufficientObservations`;
- `CurrencyMismatch`;
- `IncompatiblePriceAdjustment`;
- `StalePrices`.

This makes reports deterministic when more than one condition could apply.

The following invalidate the alignment input rather than becoming per-position
coverage gaps:

- `DuplicateHoldingInstrument`;
- `DeclaredWeightExceedsFundTotal`;
- a chronologically invalid or heterogeneous history candidate;
- mixed provider input presented as one source selection;
- invalid alignment-policy values.

### 12. Type safety

Fund `PriceObservation`/unit-price series and
`SecurityPriceObservation`/security-price series are distinct contracts and
MUST NOT be used interchangeably.

## Layer ownership

Python owns:

- selecting `HoldingSnapshot` by `published_at`;
- selecting corrections of `SecurityPriceSnapshot` by `available_at`;
- enforcing one configured source per run;
- retaining source, ingestion, publication, and prediction-time provenance;
- grouping selected Rust-backed `SecurityPriceObservation` values into explicit
  per-instrument history candidates without calculating returns or coverage.

Rust owns:

- exact `InstrumentId` matching and duplicate detection;
- validating each history candidate and constructing `SecurityPriceSeries`;
- supported-asset, currency, adjustment, observation-count, and staleness
  decisions from explicit policy inputs;
- security-return and coverage-weight arithmetic;
- deterministic coverage reasons and fatal alignment errors.

Python MUST NOT reimplement Rust's financial, coverage, or weight arithmetic.
Rust domain code MUST NOT depend on Python timestamps, source files, provider
records, or dataset envelopes.

## Proposed contracts

The Rust application boundary conceptually receives canonical holdings,
preselected per-instrument history candidates containing canonical
`SecurityPriceObservation` values, and an explicit alignment policy. A history
candidate is an input contract rather than an alternate price-series domain
model: it may contain too few observations so Rust can report
`InsufficientObservations`. Rust validates candidate identity and chronology and
constructs `SecurityPriceSeries` only after the candidate is eligible. The
boundary returns a `PortfolioCoverageReport` containing:

- matched holdings and their accepted series or calculated return inputs;
- uncovered listed holdings with one deterministic reason;
- declared, covered, uncovered-listed, unrepresented, and total-uncovered
  weights;
- the policy values used for the calculation.

The Python orchestration result wraps the Rust report with dataset provenance,
including holdings source, security-price source, prediction timestamp,
publication/availability timestamps, and `pricing_as_of_date`. Provider strings
do not enter Rust domain types.

A trait or Python protocol MUST be introduced only when an actual consumer
requires interchangeable implementations. The initial in-memory alignment
operation does not justify a repository, provider, or matcher interface.

## Point-in-time sequence

1. Receive `prediction_timestamp`, `pricing_as_of_date`, one holdings source,
   one security-price source, and the explicit alignment policy.
2. Python selects the latest eligible `HoldingSnapshot` using
   `published_at <= prediction_timestamp`.
3. Python selects eligible security-price corrections using
   `available_at <= prediction_timestamp`, discards observations after
   `pricing_as_of_date`, and keeps providers isolated.
4. Python groups selected canonical observations into per-instrument history
   candidates without validating series-level financial rules.
5. Rust validates the holdings and history candidates, constructs accepted
   `SecurityPriceSeries` values, aligns exact `InstrumentId` values, classifies
   gaps, and computes coverage weights.
6. Rust calculates security returns only for covered holdings.
7. Python combines the Rust result with dataset provenance for research and
   backtest outputs.

## Smallest implementation sequence

1. Add Rust alignment-policy and history-candidate input types, fatal error
   taxonomy, coverage-reason taxonomy, and weight-report result types without
   Python or provider concerns.
2. Add Rust security-return calculation for homogeneous
   `SecurityPriceSeries`.
3. Implement deterministic Rust series construction, alignment, and coverage
   reporting over canonical holdings and preselected observation candidates.
4. Expose the accepted Rust contracts through thin PyO3 mappings.
5. Add Python point-in-time orchestration that supplies validated series and
   attaches provenance.
6. Add integration fixtures covering future corrections, partial holdings,
   missing prices, currency/adjustment mismatch, stale data, duplicate holdings,
   unsupported assets, and non-normalized coverage.

## Consequences

- Missing and unsupported exposures remain visible in every result.
- Coverage arithmetic represents total fund weight without silently
  renormalizing the covered subset.
- Current FX absence produces an explicit gap rather than a false local-currency
  estimate.
- Provider timing remains in Python while deterministic financial decisions
  remain in Rust.
- Initial support is intentionally narrow; additional asset classes require
  their own financially correct return contracts.
- Calendar-day staleness is reproducible but less market-aware than a future
  venue-calendar policy.

## Deferred decisions

- `FxRateObservation` and explicit base/quote currency conversion.
- Debt-security accrued interest and clean/dirty-price treatment.
- Return contracts for repo, deposits, precious metals, derivatives, cash, and
  investment funds held by another fund.
- Exchange-calendar-aware staleness after venue/calendar identity is modeled.
- Corporate-action transformations; this ADR only requires an explicit
  adjustment policy on already classified price series.
- Multi-provider preference and conflict resolution.

## Alternatives considered

### Silently ignore missing weights and renormalize

Rejected because it inflates the contribution of covered holdings and hides
uncertainty about the actual fund.

### Treat missing returns as zero

Rejected because zero is a valid market outcome and is not evidence of missing
data.

### Perform fuzzy instrument matching

Rejected because it is non-deterministic and can align unrelated instruments.
Provider-specific aliases belong in an explicit source normalizer before the
canonical boundary.

### Aggregate duplicate canonical holdings inside the matcher

Rejected because implicit aggregation can hide source-classification errors and
double counting. Explicit source normalization is auditable.

### Compute local-currency returns without FX

Rejected because it treats currency exposure as irrelevant and produces a
different economic return from the fund-base-currency return.

### Use target date for staleness

Rejected because target date may lie in the future. Input staleness is measured
against the pricing as-of date available at prediction time.
