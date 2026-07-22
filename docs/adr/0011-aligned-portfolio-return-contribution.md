# ADR-0011: Aligned Portfolio Return Contribution

- Status: Proposed
- Date: 2026-07-22

## Context

After completing the holdings and security-price alignment process described in ADR-0010, the system yields a `PortfolioCoverageReport`. This report contains covered holdings (where a `SecurityPriceSeries` is available) and a list of coverage gaps. 

To evaluate the fund's observed portfolio return contribution, we must calculate the aggregate return contribution of these covered holdings for a specific target period. The current `navlens-core` domain logic provides `PortfolioEstimate::calculate`, which enforces that portfolio weights sum to 1.0 and directly subtracts an expense rate. However, aligned holdings typically have a coverage ratio of less than 1.0. 

We must decide how to safely compute a partial, observed return contribution from covered holdings without violating mathematical invariants, incorrectly applying expenses, or blurring the distinction between price availability and return calculation.

## Decision

We will introduce a distinct financial capability to calculate the "Observed Portfolio Return Contribution" from partially covered holdings. 

This calculation will explicitly require a target return period (not just a single date) to prevent mixing returns of different lengths (e.g., 1-day vs. 3-day returns). It will extract returns exactly matching that period. It will not attempt to guess or synthesize a full portfolio return from a partial slice.

### Invariants

- **Exact Period Matching:** A single `target_date` is insufficient. The orchestration MUST define a common return period. Because `DatedDecimalReturn` currently only carries an end date, we propose a new canonical Rust calendar contract `PeriodDecimalReturn` carrying `period_start_date`, `period_end_date`, and a `DecimalReturn`. Only a return matching this exact period is valid.
- **Canonical Return Source:** The return calculation formula MUST NOT be rewritten. `SecurityPriceSeries::period_returns` remains the canonical owner and sole generator of these period returns.
- **Preserved Weights:** The original `fund_total_weight` of each holding MUST be preserved.
- **No Renormalization:** Covered weights MUST NOT be renormalized to 100%. 
- **No Implicit Zeroes:** Uncovered or missing weights MUST NOT be treated as having a 0% return.
- **Coverage Separation:** Price coverage and return coverage MUST be modeled as distinct concepts:
  - `price_coverage` is defined exactly as `PortfolioCoverageReport.covered_weight`.
  - `return_coverage` is defined as the sum of the original `fund_total_weight` of holdings that successfully yielded the target period return. The denominator remains the fund's 1.0 total weight; there is no renormalization.
- **Floating-Point Tolerance:** The equality check to determine if `return_coverage` reaches full coverage (1.0) MUST use a canonical floating-point tolerance constant defined securely within the Rust domain policy.
- **Nomenclature:** A partial coverage calculation MUST NOT be named or treated as a "full fund estimate". It is an observed "return contribution". Achieving `return_coverage == 1.0` is a necessary condition for a full fund estimate, but it is not sufficient on its own due to deferred effects like expense processing and unmodeled complex instruments.
- **Strict Separation from PortfolioEstimate:** The existing `PortfolioEstimate::calculate` MUST NOT be bypassed, disabled, or misused to force partial-coverage data through its 1.0 sum invariant.

## Layer Ownership

- **Rust `navlens-core::portfolio`** owns the new deterministic partial-coverage arithmetic, floating-point tolerance policies, and its specific domain models (e.g., `PortfolioReturnContribution`).
- **Rust `navlens-calendar`** owns the new period-based security return contract and remains the sole owner of generating calendar-dated security returns.
- **Rust `navlens-application`** orchestrates the output of the alignment step with the contribution calculation, routing the target period to match the generated returns.
- **Python** retains dataset selection, point-in-time orchestration, and provenance handling. Python MUST NOT reimplement the weighted-return mathematical formula.

## Proposed Contracts

The application boundary will output a result containing:
- `period_start_date` and `period_end_date`: The specific period for which the contribution was calculated.
- `component_contributions`: A list detailing each holding's preserved weight, its period return, and its weighted contribution.
- `observed_contribution`: The mathematically sound sum of the component contributions.
- `price_coverage`: The weight of the portfolio that had a valid price series (`PortfolioCoverageReport.covered_weight`).
- `return_coverage`: The sum of the original `fund_total_weight` of holdings that successfully yielded a return for the exact target period.
- `price_gaps` and `return_gaps`: Separate lists that explicitly categorize gaps. Both lists MUST preserve the original holding order from the input snapshot.

## Failure Semantics

- Failing to find a return for the exact target period within a covered security's series is not an application error or panic. It is mapped deterministically to a return-coverage gap.
- Invalid weights (e.g., negative, non-finite) or invalid returns will still yield canonical `navlens-core` domain errors.

## Consequences

- The distinction between price coverage and return coverage becomes transparent and explainable to researchers.
- A strict period contract prevents the silent corruption of mixing 1-day returns with multi-day returns (e.g., over a weekend or holiday).
- Financial correctness is strictly maintained by rejecting silent renormalization or fallback values.
- Full-fund estimation is safely gated behind a mathematically rigorous 1.0 return-coverage requirement backed by a domain-owned tolerance constant.
- The boundary between Python dataset orchestration and Rust financial calculation remains absolute.

## Rejected Alternatives

### Renormalizing covered shares to 100%
Rejected because it mathematically misrepresents the fund's allocation, inflating the contribution of covered assets and hiding uncertainty.

### Using the last return of a stale series for the target day
Rejected because it breaks point-in-time accuracy. A return on Monday cannot be silently recorded as a return on Tuesday.

### Giving 0% return to missing or uncovered shares
Rejected because a 0% return is a specific, active market outcome. It is not equivalent to missing data.

### Rewriting the weighted-return formula in Python
Rejected because `navlens-core` is the canonical owner of all financial arithmetic. Replicating the logic in Python violates the core architecture contract.

### Misusing the existing full-portfolio estimate
Rejected because bypassing the 1.0 weight-sum invariant in `PortfolioEstimate::calculate` to accommodate partial coverage destroys the safety guarantees of the domain model.

## Deferred Decisions

- **Expense Rates:** Deducting expense rates from a partial contribution is deferred. The current expense logic is fund-wide and cannot be trivially applied to a partial coverage slice.
- **Complex Instruments:** FX impact, derivatives, corporate actions, and residual-return estimation models are deferred and remain out of scope for this initial contribution slice.
