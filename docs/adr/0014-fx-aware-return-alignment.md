# ADR-0014: FX-aware holdings and security-price return alignment

- Status: Accepted
- Date: 2026-08-07

## Context

NAVLens currently aligns a holding with a security-price history only when the
history uses the fund's base currency. A different currency produces
`CoverageGapReason::CurrencyMismatch`. ADR-0013 introduced provider-neutral FX
types, point-in-time FX datasets, and the first TCMB source boundary, but it
deliberately deferred using FX observations in portfolio return calculations.

Price coverage and return coverage are separate lifecycle stages:

1. `align_holdings_prices` determines whether a holding has an acceptable
   security-price history as of `pricing_as_of_date`. It does not receive a
   target `ReturnPeriod`.
2. `calculate_return_contribution` matches an exact security-price return for a
   requested period and calculates the weighted contribution.

FX start and end observations cannot be selected correctly until the target
period is known. FX period matching therefore belongs to the return-contribution
stage, not price alignment.

This decision defines the first direct-pair FX-aware return slice. It preserves
point-in-time selection in Python, canonical financial arithmetic in Rust, and
explicit partial-coverage reporting.

## Current, planned, and deferred states

An accepted ADR defines the intended architecture. It does not imply that the
planned contracts below are already implemented.

**Current:**

- same-currency holdings/security-price alignment;
- separate price-coverage and return-coverage reports;
- canonical `CurrencyCode`, `CurrencyPair`, `FxRate`, `FxRateKind`,
  `DecimalReturn`, and portfolio contribution types;
- shared positive-ratio return calculation used by unit prices and FX rates;
- canonical FX-return (`calculate_fx_decimal_return`) and FX-adjusted-return
  (`FxAdjustedPeriodReturn`) arithmetic, including `GrossReturnComponent` and
  non-positive-gross-return rejection in `navlens-core`;
- chronological `FxRateObservation` and `FxRateSeries` types;
- pure boundary lookup (`latest_observation_on_or_before`) on `FxRateSeries` in
  `navlens-calendar`;
- typed FX return policy, evidence, results, and gaps in `navlens-application`;
- point-in-time `FxRateSnapshot` selection in Python;
- provider-isolated FX acquisition and provenance;
- `CoverageGapReason::CurrencyMismatch` for the existing base-currency-only
  price-alignment policy;
- explicit foreign-price permission (`PriceCurrencyPolicy`);
- an FX-aware return-contribution capability;
- thin PyO3 projections.

**Planned, in implementation order:**

1. Python point-in-time orchestration.

**Deferred:**

- reverse-pair inversion;
- bid/ask-kind transformation during inversion;
- cross-rate triangulation;
- currency hedging, forwards, derivatives, and collateral;
- transaction-level cash-flow conversion;
- intraday FX observations;
- automatic provider fallback or provider conflict resolution.

## Decision

### 1. Preserve the two-stage lifecycle

Price alignment continues to own security-price eligibility and price coverage.
It MAY explicitly permit a valid foreign-currency security-price series to
proceed as price-covered, but it MUST NOT inspect FX period boundaries or
calculate an FX return.

FX evidence is evaluated only after an exact target `ReturnPeriod` is known. An
FX failure becomes a return-coverage gap. It does not retroactively claim that
the holding lacked security-price coverage.

The existing `align_holdings_prices` and `calculate_return_contribution`
signatures and default behavior remain valid for current callers.

### 2. Use an explicit price-currency policy

`AlignmentPolicy` gains a typed policy rather than a boolean flag:

```rust
pub enum PriceCurrencyPolicy {
    FundBaseOnly,
    PermitForeign,
}
```

`AlignmentPolicy::new` continues to select
`PriceCurrencyPolicy::FundBaseOnly`, preserving existing behavior. A consuming
configuration method enables the new path explicitly:

```rust
pub fn with_price_currency_policy(
    self,
    policy: PriceCurrencyPolicy,
) -> Self
```

Under `FundBaseOnly`, a foreign-currency series still produces
`CoverageGapReason::CurrencyMismatch`. Under `PermitForeign`, the series MAY be
price-covered when every other price-series invariant succeeds. FX coverage is
not implied.

### 3. Require an exact direct currency pair in v0.1

For a security priced in currency `S` and a fund using base currency `F`, the
required pair is exactly:

```text
S/F
```

The rate means units of `F` for one unit of `S`. A USD-priced security in a TRY
fund therefore requires USD/TRY.

A reverse F/S series is not accepted or silently inverted. Reciprocal
floating-point arithmetic is not exact, and bid/ask semantics mean that
inverting a buying quote cannot retain the same rate-kind meaning without an
explicit spread-aware policy. Reverse-pair support requires a later ADR.

### 4. Use one explicit FX return policy

FX period matching uses a return-stage policy:

```rust
pub struct FxReturnPolicy {
    required_fx_rate_kind: FxRateKind,
    max_fx_staleness_calendar_days: u32,
}
```

A staleness value of zero requires an exact boundary date. The rate kind is
mandatory; buying, selling, cash, and non-cash observations are never mixed or
substituted silently.

`FxReturnPolicy` belongs to `navlens-application`. It is not part of the generic
calendar series.

### 5. Reuse `FxRateSeries` without duplicating its identity

The application accepts `&[FxRateSeries]` directly. It does not introduce a
candidate type that repeats `CurrencyPair` or `FxRateKind`, because
`FxRateSeries` already owns and validates both.

The input is indexed by `(CurrencyPair, FxRateKind)`. More than one series with
the same key is an ambiguous contract violation and is rejected before any
holding is processed. Input order MUST NOT choose a winner.

Provider identity does not enter this Rust contract. Python selects one exact
provider before constructing each `FxRateSeries`. Rust therefore MUST NOT claim
to detect provider mixing that is not represented in its input.

### 6. Keep point-in-time selection in Python

Python selects `FxRateSnapshot` values using the existing dataset boundary and
enforces at least:

```text
source_id == requested_source_id
available_at <= prediction_timestamp
market_date <= pricing_as_of_date
currency_pair == required_pair
rate_kind == required_kind
```

Only selected `FxRateObservation` values cross the PyO3 boundary into an
`FxRateSeries`. `FxRateObservation` does not contain publication timestamps, so
Rust does not produce a false `FuturePublishedFxObservation` gap. If no
point-in-time-safe boundary remains, Rust reports the corresponding missing FX
observation.

PyO3 remains a thin typed projection. Python MUST NOT calculate FX returns,
invert rates, or compose security and currency returns.

### 7. Add a pure FX boundary lookup

`FxRateSeries` gains a policy-free lookup:

```rust
pub fn latest_observation_on_or_before(
    &self,
    date: MarketDate,
) -> Option<&FxRateObservation>
```

The series owns chronological lookup only. `navlens-application` calculates the
calendar-day difference, applies `FxReturnPolicy`, and constructs evidence or a
typed gap.

The selected start and end observations MAY have dates earlier than their
requested boundaries. These actual dates must remain visible.

### 8. Centralize FX-return arithmetic in `navlens-core`

The return between two positive rates uses the same canonical ratio formula as
positive unit prices:

```text
fx_return = (end_rate / start_rate) - 1
```

`navlens-core` adds a canonical operation for `FxRate` inputs. Its internal
positive-ratio calculation MUST be shared with the existing unit-price return
calculation rather than duplicating the formula in another language or layer.

The base-currency return is:

```text
(1 + security_return) * (1 + fx_return) - 1
```

This is algebraically equivalent to converting both boundary values:

```text
((security_end * fx_end) / (security_start * fx_start)) - 1
```

The canonical result is represented by:

```rust
pub struct FxAdjustedPeriodReturn(DecimalReturn);

impl FxAdjustedPeriodReturn {
    pub fn calculate(
        security_return: DecimalReturn,
        fx_return: DecimalReturn,
    ) -> Result<Self, CoreError>;

    pub fn decimal_return(self) -> DecimalReturn;
}
```

Both input returns must be strictly greater than `-1.0`, because they originate
from ratios of strictly positive prices or rates and therefore require positive
gross-return factors. `navlens-core` adds a structured error:

```rust
pub enum GrossReturnComponent {
    Security,
    ForeignExchange,
}

CoreError::NonPositiveGrossReturn {
    component: GrossReturnComponent,
    decimal_return: f64,
}
```

The final result must also be finite; overflow, NaN, and infinity remain invalid.

The returns MUST NOT be added. Addition would omit the interaction term
`security_return * fx_return`.

Examples:

- TRY security in TRY fund: a 10% security return remains 10%; no FX evidence is
  fabricated.
- USD security rises 10% and USD/TRY rises 10%: the result is 21%.
- USD security falls 10% and USD/TRY rises 10%: the result is -1%.
- only TRY/USD exists for a required USD/TRY pair: the result is a
  `MissingDirectFxCandidate` return gap.

### 9. Preserve auditable boundary evidence

Application evidence records both requested and actual dates:

```rust
pub struct FxBoundaryEvidence {
    requested_date: MarketDate,
    observation: FxRateObservation,
    staleness_calendar_days: u32,
}
```

Its constructor validates that the observation is not after the requested date
and that `staleness_calendar_days` equals their actual calendar-day difference.

Applied FX evidence is:

```rust
pub struct FxAdjustmentEvidence {
    start: FxBoundaryEvidence,
    end: FxBoundaryEvidence,
    fx_return: DecimalReturn,
}
```

Both observations must have the same pair and kind. Pair and kind getters
delegate to the observations rather than storing duplicate identity fields.
`fx_return` must equal the canonical return calculated from
`start.observation.rate()` and `end.observation.rate()`.

Same-currency components do not use optional or synthetic FX fields:

```rust
pub enum CurrencyReturnAdjustment {
    NotRequired,
    Applied(FxAdjustmentEvidence),
}
```

### 10. Return a truthful FX-aware result

The existing `ComponentContribution` and `ReturnContributionResult` keep their
current semantics. They MUST NOT display an unadjusted security return while
silently calculating a contribution from a different adjusted return.

The FX-aware capability uses:

```rust
pub struct FxAdjustedComponentContribution {
    holding: HoldingPosition,
    security_period_return: PeriodDecimalReturn,
    currency_adjustment: CurrencyReturnAdjustment,
    effective_base_currency_return: DecimalReturn,
    contribution: PortfolioComponentContribution,
}

pub struct FxAdjustedReturnContributionResult {
    period: ReturnPeriod,
    component_contributions: Vec<FxAdjustedComponentContribution>,
    observed_contribution: PortfolioReturnContribution,
    breakdown: ReturnCoverageBreakdown,
}
```

For `NotRequired`, `effective_base_currency_return` equals the security period
return. For `Applied`, it equals the canonical `FxAdjustedPeriodReturn`. The
`PortfolioComponentContribution` must be calculated from that same effective
return.

`ReturnCoverageBreakdown` remains an internal shared representation exposed
through result getters, as it is today. Price gaps, return gaps, and their
weights retain their established meanings.

The new entry point is:

```rust
pub fn calculate_fx_adjusted_return_contribution(
    report: &PortfolioCoverageReport,
    target_period: ReturnPeriod,
    fx_candidates: &[FxRateSeries],
    fx_policy: &FxReturnPolicy,
) -> Result<FxAdjustedReturnContributionResult, CalculateReturnContributionError>
```

### 11. Prevent duplicate contribution implementations

The existing and FX-aware entry points share private operations for:

- matching the exact security `PeriodDecimalReturn`;
- constructing a component contribution from one effective return;
- aggregating `PortfolioReturnContribution`;
- building `ReturnCoverageBreakdown`.

The same-currency branch in the FX-aware capability delegates through these
operations. It does not copy the existing formula or maintain a parallel
implementation. Parity tests must prove that same-currency effective returns,
weighted contributions, gaps, and aggregate contribution equal the legacy
result.

### 12. Use mutually exclusive return gaps

FX-aware return matching uses these reasons:

```rust
pub enum ReturnCoverageGapReason {
    MissingExactPeriodReturn,
    MissingDirectFxCandidate {
        required_pair: CurrencyPair,
        required_kind: FxRateKind,
    },
    FxRateKindMismatch {
        required_pair: CurrencyPair,
        required_kind: FxRateKind,
        available_kinds: Vec<FxRateKind>,
    },
    MissingFxStartObservation {
        required_pair: CurrencyPair,
        required_kind: FxRateKind,
        requested_date: MarketDate,
    },
    StaleFxStartObservation {
        evidence: FxBoundaryEvidence,
        maximum_staleness_calendar_days: u32,
    },
    StaleFxEndObservation {
        evidence: FxBoundaryEvidence,
        maximum_staleness_calendar_days: u32,
    },
}
```

Candidate and gap precedence is deterministic:

1. duplicate `(CurrencyPair, FxRateKind)` input series is a fatal application
   contract error;
2. missing exact security-period return;
3. same-currency fast path, for which no FX gap can occur;
4. no series for the required direct pair: `MissingDirectFxCandidate`;
5. direct pair exists but not with the required kind: `FxRateKindMismatch`;
6. no observation on or before the start boundary:
   `MissingFxStartObservation`;
7. start observation exceeds maximum staleness: `StaleFxStartObservation`;
8. end observation exceeds maximum staleness: `StaleFxEndObservation`.

After a start observation has been selected, `MissingFxEndObservation` is not a
possible portfolio gap. The end boundary is later than the start boundary, so
the selected start observation is necessarily also on or before the end. A
failure to retrieve an end observation after selecting the start is therefore
an internal contract error rather than a coverage condition.

Only a reverse pair being present still counts as
`MissingDirectFxCandidate`. There is no overlapping fallback variant.

`available_kinds` is unique and sorted in the canonical `FxRateKind` declaration
order. It does not inherit caller input order.

### 13. Exact orchestration flow

Python performs the following operations for an FX-aware calculation:

1. select one holdings snapshot and point-in-time-safe security-price snapshots;
2. align holdings and security prices with `PriceCurrencyPolicy::PermitForeign`;
3. derive the distinct direct pairs required by price-covered foreign holdings;
4. select FX snapshots for one explicit provider, pair, and kind under the same
   prediction timestamp and pricing-as-of boundary;
5. construct homogeneous `FxRateSeries` values through PyO3;
6. call `calculate_fx_adjusted_return_contribution` with an explicit
   `FxReturnPolicy`;
7. preserve selected snapshot provenance alongside the returned typed Rust
   result in the Python orchestration envelope.

Rust then:

1. indexes and validates candidate-series uniqueness;
2. matches each holding's exact security period;
3. bypasses FX for same-currency holdings;
4. selects the required direct pair and kind for foreign holdings;
5. selects and validates both FX boundaries;
6. calculates the FX return and adjusted base-currency return;
7. calculates the weighted component contribution;
8. aggregates only successful components without renormalizing weights;
9. reports every failed component as a typed return gap.

## Consequences

- Foreign-currency holdings can contribute to base-currency estimates without
  hiding FX assumptions.
- Same-currency behavior remains backward compatible and requires no artificial
  exchange-rate series.
- Missing FX data reduces return coverage instead of being treated as zero
  return or causing weight renormalization.
- Direct-pair and rate-kind requirements are explicit and auditable.
- Actual boundary observations and staleness remain visible in results.
- Python retains provider and publication-time ownership; Rust retains
  financial arithmetic and deterministic matching.
- The new result surface is larger because an explainable adjusted contribution
  must preserve both security and FX evidence.

## Test strategy

### Core arithmetic

- positive, negative, and flat security/FX combinations;
- the multiplicative interaction term;
- parity with boundary-value conversion;
- rejection of either input at or below `-1.0`;
- rejection of non-finite inputs and overflow;
- FX rate-return parity with the shared positive-ratio calculation.

### Calendar lookup

- exact boundary date;
- latest prior observation;
- no observation on or before a boundary;
- deterministic behavior at the first and last observations.

### Application contracts

- default `FundBaseOnly` compatibility;
- explicit `PermitForeign` behavior;
- duplicate pair/kind series rejection;
- exact rate-kind selection;
- every gap and the declared precedence;
- inclusive staleness boundary;
- requested and actual evidence-date validation;
- reverse-only pair producing `MissingDirectFxCandidate`.

### Contribution behavior

- same-currency parity with `calculate_return_contribution`;
- USD security up / USDTRY up;
- USD security down / USDTRY up;
- FX-only gain and FX-only loss;
- partial FX coverage without renormalization;
- effective return and component contribution using the same scalar;
- component ordering and aggregate contribution determinism.

### Cross-language orchestration

- provider-isolated point-in-time selection;
- future FX corrections excluded before Rust input construction;
- thin PyO3 type parity;
- provenance envelope preserving the source and selected snapshot timestamps.

## Alternatives considered

### Evaluate FX during price alignment

Rejected because the target return-period boundaries are unknown at that stage
and because it would collapse price coverage and return coverage into one
concept.

### Convert only one period boundary

Rejected because a foreign-currency return requires both the start and end
exchange rates.

### Add security and FX returns

Rejected because addition omits the multiplicative interaction term.

### Silently invert a reverse pair

Rejected because reciprocal floating-point arithmetic and bid/ask-kind
transformation require an explicit future policy.

### Represent same-currency conversion with a synthetic 1.0 rate

Rejected because no exchange occurs and fabricated evidence would obscure that
fact.

### Duplicate an FX candidate model in Python

Rejected because the Rust/PyO3 `FxRateSeries` is the canonical typed input.

### Reuse the existing component result without showing FX evidence

Rejected because the displayed security return and the scalar used for the
weighted contribution would diverge silently.
