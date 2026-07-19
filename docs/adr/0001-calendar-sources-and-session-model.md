# ADR-0001: Calendar sources and market-session representation

- Status: Accepted
- Date: 2026-07-19

## Context

NAVLens must determine the next date on which a fund can be valued. Turkish
public holidays, religious holidays, market schedules, half-day sessions, and a
fund's prospectus can produce different answers for the same civil date.

Calculating a religious date does not prove that a market is closed. Likewise,
an administrative holiday does not necessarily close an exchange. Treating all
of these concepts as one boolean holiday flag would lose essential information.

Calendar arithmetic must also be correct for leap years, month boundaries, and
weekdays without exposing a third-party date type throughout the project.

## Decision

1. `navlens-calendar` owns market-date and session calculations.
2. `MarketDate` wraps the `time` crate's Gregorian `Date` and prevents that
   dependency type from entering public NAVLens contracts.
3. The workspace minimum supported Rust version is 1.88, matching the selected
   current `time` release.
4. A session is represented as `FullDay`, `HalfDay`, or `Closed`. Half days are
   open sessions and must not be reduced to a holiday boolean.
5. Weekends provide a default closure rule. Explicit session overrides may
   replace that default, including exceptional weekend sessions.
6. Religious dates are not calculated inside the domain. Verified Gregorian
   dates are supplied by infrastructure adapters from authoritative sources.
7. Legal public-holiday calendars, exchange calendars, and fund valuation
   calendars remain separate. A later composition policy will combine them for
   a specific fund.
8. Provider/source name, source version, publication time, and verification time
   belong to infrastructure records. The pure calendar domain consumes verified
   session overrides and performs no network or file access.

## Consequences

- Calendar calculations are deterministic and testable without external I/O.
- Incorrect or conflicting duplicate overrides are rejected at construction.
- Updating Diyanet, exchange, or prospectus data does not require changing
  domain algorithms.
- The Rust workspace requires Rust 1.88 or newer.
- Cut-off times and time zones are intentionally deferred until a concrete fund
  pricing policy requires them.

## Alternatives considered

### Calculate Hijri dates in Rust

Rejected because an astronomically calculated religious date is not sufficient
evidence of a legal holiday or market closure.

### Store only `is_holiday: bool`

Rejected because it cannot represent half-day or exceptional weekend sessions.

### Expose the dependency's `Date` type directly

Rejected because it would couple every NAVLens boundary and future binding to a
third-party representation.

