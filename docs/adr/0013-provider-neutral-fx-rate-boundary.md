# ADR-0013: Provider-neutral FX-rate boundary

- Status: Accepted
- Date: 2026-07-29

## Context

NAVLens requires foreign exchange (FX) rates to value non-base-currency assets
in holdings-aware return estimates. Alignment currently requires a security
price series to use the fund's explicit base currency. A mismatch produces
`CoverageGapReason::CurrencyMismatch`.

Resolving these gaps in a future milestone requires a provider-neutral FX
boundary and a dedicated adapter for the Central Bank of the Republic of
Türkiye (TCMB) keyless XML archive. This ADR defines canonical FX types,
ownership, provenance, and source semantics. It does not introduce automatic
holdings conversion.

## Current, planned, and deferred states

An accepted ADR establishes architectural rules; it does not imply that its
planned code is already implemented.

**Current:**

- `CurrencyCode`
- `CoverageGapReason::CurrencyMismatch`
- canonical `CurrencyPair`, `FxRate`, `FxRateKind`, `FxRateObservation`, and
  `FxRateSeries` types;
- thin PyO3 projections for the canonical FX types (`CurrencyPair`, `FxRate`,
  `FxRateKind`, `FxRateObservation`, `FxRateSeries`);
- point-in-time `FxRateSnapshot` dataset envelope and `select_fx_rate_snapshots`
  selection;
- provider-neutral local FX CSV adapter (`read_fx_rates_csv`);
- TCMB daily rates XML record definitions and parser (`parse_tcmb_daily_rates_xml`);
- TCMB canonical mapping and Unit normalization (`map_tcmb_daily_rates`);
- initial scheduled TCMB availability policy (`initial_tcmb_available_at`).

**Planned:**

- separated TCMB XML HTTP client, acquisition, cache, and correction timing
  orchestration capabilities.

**Deferred:**

- FX-aware holdings and security-price alignment;
- amount conversion and rate inversion APIs;
- cross-rate triangulation;
- non-TCMB providers;
- conflicting-provider resolution.

## Decision

### Canonical FX types and invariants

`market_date` is the canonical date field name.

`CurrencyPair` belongs to `navlens-core` and contains:

- `base_currency: CurrencyCode`;
- `quote_currency: CurrencyCode`.

The currencies MUST differ. Identical pairs are invalid.

`FxRate` belongs to `navlens-core` and contains:

- `quote_currency_per_one_base_currency: f64`.

The value MUST be finite and strictly positive.

`FxRateKind` belongs to `navlens-core`. Its provider-neutral variants preserve
the economically meaningful distinction between non-cash transfers and
physical banknotes:

- `NonCashBuying`;
- `NonCashSelling`;
- `CashBuying`;
- `CashSelling`.

`FxRateObservation` belongs to `navlens-calendar::pricing` and contains:

- `pair: CurrencyPair`;
- `market_date: MarketDate`;
- `rate: FxRate`;
- `kind: FxRateKind`.

`FxRateSeries` also belongs to `navlens-calendar::pricing`. It MUST be non-empty,
homogeneous in both `CurrencyPair` and `FxRateKind`, and strictly chronological.
Duplicate or decreasing dates are invalid.

### Direction and conversion semantics

Ambiguous pair strings do not define financial direction. The value always
means quote-currency units per one base-currency unit. For example, base USD,
quote TRY, and rate 35 means 1 USD equals 35 TRY.

The recorded mathematical direction is:

```text
amount_in_quote =
    amount_in_base * quote_currency_per_one_base_currency
```

This milestone does not add amount-conversion or inversion methods. Those APIs
belong to a later FX-aware alignment decision. Silent inversion and implicit
cross-rate triangulation are forbidden.

### TCMB mapping and unit normalization

Provider field names MUST NOT enter the Rust domain. The TCMB mapper uses:

| TCMB field | Canonical kind |
| --- | --- |
| `ForexBuying` | `NonCashBuying` |
| `ForexSelling` | `NonCashSelling` |
| `BanknoteBuying` | `CashBuying` |
| `BanknoteSelling` | `CashSelling` |

TCMB's `Unit` field is a provider representation. The Python mapper normalizes
it before constructing canonical Rust-backed values:

```text
normalized_quote_per_base = parsed_rate / parsed_unit
```

`Unit` MUST be strictly positive. Missing, zero, or invalid values produce a
typed provider parsing or mapping error. The provider `Unit` MUST NOT leak into
the Rust domain. Dividing it out is representation normalization, not currency
conversion.

### Layer ownership

- `navlens-core` owns `CurrencyPair`, `FxRate`, and `FxRateKind`.
- `navlens-calendar::pricing` owns `FxRateObservation` and `FxRateSeries`
  because dated observations require `MarketDate`.
- `navlens-python` owns thin PyO3 projections only.
- `navlens.datasets` owns `FxRateSnapshot` and point-in-time selection.
- `navlens.sources.tcmb` owns separated transport, parsing, mapping,
  availability-policy, acquisition, and raw-cache capabilities.

These responsibilities MAY use cohesive functions, records, or collaborators.
They MUST NOT be forced into classes or combined into a generic adapter,
manager, service, or factory.

### Point-in-time snapshot contract

`FxRateSnapshot` contains:

- `observation: FxRateObservation`;
- `available_at: datetime` in UTC;
- `ingested_at: datetime` in UTC;
- `source_id: str`.

`available_at` is the earliest time at which NAVLens can conservatively
establish that the observation was available to the market. Selection uses
`available_at <= prediction_timestamp`.

`ingested_at` records when NAVLens received the artifact. It is not market
availability. It MAY break a tie between revisions but MUST NOT make a later
revision visible at an earlier prediction timestamp.

Selection requires:

- exact `source_id`, `CurrencyPair`, and explicit `FxRateKind`;
- `available_at <= prediction_timestamp`;
- `market_date <= pricing_as_of_date`;
- publication-safe revision precedence for one `market_date`;
- strictly chronological output;
- no silent provider mixing.

The existing private correction-selection utility MAY be reused only when its
semantics match these rules. It MUST NOT bypass TCMB-specific availability
constraints.

### TCMB availability policy and correction safety

The XML parser parses provider fields only. It does not assign or guess market
availability.

The TCMB mapper and availability-policy capability:

- map the XML date to `MarketDate`;
- derive the initial availability time from the verified 15:30
  `Europe/Istanbul` publication rule and convert it to UTC;
- produce no new observation for weekends, official holidays, or half-day
  holidays;
- identify the source-derived availability-policy version in acquisition
  provenance.

The Rust domain and generic dataset selection know neither TCMB nor its
publication schedule.

An initial historical observation MAY use the verified scheduled publication
time. A later revision MUST NOT be assigned that original time unless its
actual correction-publication time is verifiable.

- A verifiable correction uses its source publication timestamp.
- When that timestamp is unavailable, the correction's `available_at` is its
  first observed `ingested_at`.
- A correction is never backfilled into earlier prediction timestamps.

### TCMB acquisition provenance

The adapter uses TCMB's official keyless current and historical XML resources.
Transport and XML parsing remain in Python.

Client, parser, mapper, availability policy, acquisition orchestration, and
cache remain separate cohesive modules or collaborators. Raw acquisition
preserves:

- requested archive date and URL;
- `retrieved_at` in UTC;
- exact raw response bytes;
- SHA-256 content digest;
- cache hit or miss;
- availability-policy identifier and version;
- atomic raw-artifact storage.

FX rates and security prices remain separate source capabilities.

## Consequences

- FX direction and rate kind remain explicit across providers.
- TCMB's `Unit` representation cannot silently scale JPY and similar currencies
  incorrectly.
- Historical backtests can reject later revisions until those revisions were
  actually observable.
- The domain remains independent of XML, HTTP, TCMB schedules, and provider
  field names.
- FX-aware valuation remains incomplete until a separate alignment decision is
  accepted and implemented.
- Supporting another provider requires a new mapper and availability policy,
  not new canonical financial types.

## Smallest implementation sequence

1. Add `CurrencyPair`, `FxRate`, and `FxRateKind` to `navlens-core`.
2. Add `FxRateObservation` and `FxRateSeries` to
   `navlens-calendar::pricing`.
3. Add thin PyO3 projections in `navlens-python`.
4. Add point-in-time `FxRateSnapshot` selection in `navlens.datasets`.
5. Add a provider-neutral local FX CSV adapter in `navlens.sources`.
6. Add separated TCMB client, parser, mapper, availability-policy,
   acquisition, and cache capabilities in `navlens.sources.tcmb`.
7. Create a separate ADR for FX-aware alignment, amount conversion, inversion,
   and holdings integration.

## Test strategy

- `navlens-core`: reject identical pairs and non-finite, zero, or negative
  rates; preserve all four rate kinds.
- `navlens-calendar`: accept homogeneous chronological series and reject empty,
  mixed-pair, mixed-kind, duplicate-date, and decreasing-date series.
- `navlens-python`: verify typed projection parity and native error mapping.
- Python datasets: verify source/pair/kind isolation, point-in-time visibility,
  chronological output, and correction precedence.
- Local CSV mapping: verify canonical direction, UTC provenance, typed row
  errors, and no provider mixing.
- TCMB mapping: verify all four provider-field mappings, `Unit=1`, `Unit=100`,
  missing/zero/invalid units, and absent optional rate fields.
- TCMB availability: verify UTC conversion, weekends, official holidays,
  half-days, known corrections, and conservative unknown-correction timing.
- Acquisition/cache: verify exact-byte preservation, digest stability, atomic
  storage, cache behavior, and provenance metadata.

## Alternatives considered

### Naked tuples, strings, and floats

Rejected because they permit ambiguous direction, flipped pairs, and invalid
rates.

### Python-owned conversion arithmetic

Rejected because canonical financial arithmetic belongs in Rust. Provider
`Unit` normalization remains Python mapping because it removes an external
representation detail.

### TCMB XML records as domain models

Rejected because XML names, `Unit`, and publication rules are provider
concerns.

### Buying and selling without cash semantics

Rejected because it would silently merge non-cash and banknote rates.

### FX data represented as security prices

Rejected because FX and security pricing have different identities, semantics,
sources, and correction policies.

### Silent inversion or cross-rate construction

Rejected because direction changes require explicit domain APIs and additional
validation.

### Backfilling later revisions

Rejected because assigning a correction to the original publication time can
introduce lookahead bias.
