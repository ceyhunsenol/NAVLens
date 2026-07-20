# ADR-0006: TEFAS data access boundary

- Status: Accepted
- Date: 2026-07-20

## Context

NAVLens needs historical fund unit prices, and TEFAS is an authoritative public
information platform for Turkish investment funds. The TEFAS website exposes
interactive tables and visible export controls, but its official frequently
asked questions state that API access to platform data is not provided.
The verified source is the official
[TEFAS fund-returns page](https://www.tefas.gov.tr/tr/fon-getirileri?fundType=YAT).

The current website obtains per-fund historical prices from a JSON endpoint
with fixed look-back periods. This is not a documented public API, so the
provider contract may change independently of NAVLens.

## Decision

1. NAVLens will access the website's JSON price endpoint through a dedicated
   Python HTTP adapter.
2. Endpoint paths, request fields, and response fields remain confined to
   `navlens.sources.tefas`.
3. Original response artifacts live under ignored `data/raw/tefas/` paths and are never
   relicensed under MIT.
4. Aggregate period returns shown on the fund-returns page are not accepted as
   unit prices.
5. TEFAS and CSV records use one shared Python-to-Rust normalizer. Rust remains
   the canonical owner of price validation and return calculation.
6. Live provider access is not used by the deterministic unit test suite.

## Consequences

- Scheduled ingestion is best-effort and depends on the website endpoint
  remaining available.
- A provider change is contained within the TEFAS adapter.
- Dataset preparation is visible and reproducible instead of being hidden in a
  model-training workflow.
- Provider parsing is covered by synthetic schema fixtures; live verification
  remains an explicit integration check.

## Alternatives considered

### Automate the browser export

Rejected for the initial implementation because direct JSON transport is
simpler, faster, and does not require a browser runtime.

### Parse aggregate returns as price history

Rejected because period returns and dated unit-price observations have
different semantics. Substitution would corrupt the canonical return pipeline.

### Postpone all TEFAS-related work

Rejected because an isolated HTTP adapter provides a usable automated source
without moving provider details into datasets or training.
