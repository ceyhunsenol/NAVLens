# Data Source Feasibility

Status: research note, verified on 2026-07-21.

This document records which external data sources can support NAVLens without
silently coupling the domain to a provider. It is not an approval to automate
every public website described below. A source adapter may be implemented only
after its access method, publication timing, and data contract have been
verified with representative samples.

## Decision vocabulary

- **Accepted**: suitable for an implementation spike under the stated scope.
- **Conditional**: useful data exists, but access, licensing, or format
  stability must be resolved before production automation.
- **Reference only**: useful for validation or metadata, but insufficient for
  the required feature.
- **Unverified**: no official, keyless machine-readable source has been
  confirmed.

## Source matrix

| Need | Candidate source | Frequency and detail | Authentication | Status | Boundary |
| --- | --- | --- | --- | --- | --- |
| Fund unit prices and target returns | TEFAS website price history | Published unit prices by fund and date | No API key; no documented public API | Accepted for the existing experimental adapter | `FundPriceSource` |
| Exact fund holdings | KAP monthly Portfolio Allocation Reports | Monthly; reports can contain security name, currency, ISIN, nominal value, valuation, and portfolio weights | Public pages and attachments are viewable; the documented REST service requires a Borsa Istanbul data-distribution agreement and API key | Conditional | Future `HoldingSnapshotSource` |
| Consolidated fund values and allocation categories | SPK portfolio-value pages and web services | Daily or periodic consolidated values; publicly documented endpoints do not establish an exact per-fund security-holdings feed | Public documentation is visible | Reference only | Separate reference-data adapter if needed |
| TRY foreign-exchange reference rates | TCMB daily XML archive | Daily official indicative buying and selling rates; no rate on weekends and full/half-day holidays | No API key for the published XML files | Accepted for an implementation spike | Future `FxRateSource` |
| Broad TCMB time series | EVDS web service | Series-dependent; JSON, XML, or CSV | Registration and API key required | Conditional and outside the no-key default | Optional future adapter |
| Borsa Istanbul security and index prices | Borsa Istanbul data products | Official real-time, end-of-day, reference, and analytical products | No official keyless historical-price interface was verified | Unverified for the independent MVP | Keep behind a future `SecurityPriceSource` |

## Findings

### TEFAS unit prices

The existing TEFAS adapter remains the target-label source for the first
models. It is deliberately isolated because TEFAS does not publish a documented
public API contract for the website JSON endpoint. It does not provide the
exact security-level holdings required for a holdings-aware estimator. See
[`TEFAS_DATA_ACCESS.md`](TEFAS_DATA_ACCESS.md) for the current operational
contract.

### KAP holdings reports

The Capital Markets Board states that Portfolio Allocation Reports are
prepared and announced through KAP within six days after each month. A sampled
KAP report includes a KAP submission timestamp and an attached PDF whose
portfolio table contains security identifiers and weights. This makes KAP the
strongest official candidate for monthly holdings snapshots.

Public availability must not be confused with an open automation contract.
KAP's documented Data Distribution REST service requires a Borsa Istanbul data
distribution agreement, IP authorization, and an API key. Its documentation
also directs high-volume demand away from the public site and toward that
service. MKK separately offers free registration, application keys, and a test
environment through its API Portal; this does not establish free production
Data Distribution access. Therefore:

- manual sampling of public reports is accepted for schema research;
- the free MKK API Portal is suitable for contract discovery and test calls;
- a low-volume public-page/PDF adapter is conditional on an access and terms
  review;
- the contracted KAP REST service may be added later as a separate adapter;
- NAVLens must not present either route as a public, keyless KAP API.

Report layouts may vary by fund manager, fund type, asset class, and reporting
period. A parser must not be designed from one PDF. At least three managers and
multiple asset classes must be sampled before a provider-neutral holdings
contract is frozen.

The first contract sample set now covers:

| Fund | Manager | Observed exposure types | KAP publication time |
| --- | --- | --- | --- |
| AFT technology foreign equity fund | Ak Portfoy | Foreign equities, repo, deposits, investment funds, and currencies | 2026-06-03 12:02:40 |
| DBA gold fund | Deniz Portfoy | Debt securities, repo, ETFs, precious metals, investment funds, collateral, and currencies | 2026-06-04 10:00:24 |
| GAF domestic equity fund | Inveo Portfoy | Domestic equities, derivatives, collateral, ETFs, and investment funds | 2026-03-10 17:43:42 |

All three expose an instrument description, currency, an identifier where
available, nominal amount, valuation, and multiple percentage columns. NAVLens
normalizes the percentage based on fund total value as `fund_total_weight`.
Provider-specific group and portfolio-value percentages remain outside the
canonical Rust holding position.

### SPK portfolio data

SPK links to daily and consolidated fund portfolio values, TEFAS, and its own
OpenAPI-described web services. The published service catalogue exposes
investment-company portfolio values and institutional-investor aggregates, but
the reviewed documentation does not establish an endpoint for exact,
security-level holdings of every investment fund. SPK is therefore useful for
cross-checks, aggregate allocation features, and metadata, not yet as the
primary exact-holdings source.

### TCMB foreign-exchange rates

TCMB explicitly documents automatic consumption of its published daily XML
files, including the current `today.xml` file and dated archive paths. These
files are an appropriate official, keyless source for daily TRY reference-rate
features.

The rate's publication time matters. TCMB states that indicative rates are
determined on business days at 15:30 and are not determined on weekends,
official holidays, or half-day holidays. A model run must only use a rate after
it was available; it must not backfill that rate into an earlier prediction
timestamp.

EVDS is a different access path. Its web-service guide requires registration
and an API key, so it is not the default for the project's no-key objective.

### Security and index prices

Borsa Istanbul documents real-time, end-of-day, reference, and analytical data
products, including security prices and index components. The reviewed
official material did not confirm a stable, keyless historical-price API that
can cover all holdings needed by NAVLens. This is the largest remaining source
gap for a fully automated holdings-aware model.

Until that gap is resolved, the domain and model layers will accept normalized
security-price observations without knowing their provider. Tests and research
can use committed synthetic fixtures or user-supplied CSV files. Choosing an
unofficial provider requires a separate review of history depth, corrections,
symbol mapping, rate limits, and redistribution terms.

## Publication-time safety

Every external record must preserve three different times where applicable:

- `effective_date`: the date or period described by the observation;
- `published_at`: when the source made it available;
- `ingested_at`: when NAVLens acquired it.

A backtest may consume a record only when `published_at` is not later than the
simulated prediction time. In particular, a month-end holdings report published
several days into the next month must not be used for predictions made before
its publication. A correction supersedes the original only from the
correction's publication time onward. Raw artifacts must retain their source
identifier, retrieval time, and content hash.

## Adapter rules

External data is a real substitution boundary, so an interface is justified
when the first adapter is introduced. The interface belongs to the consuming
application layer, not to the provider package.

Each provider implementation must keep these responsibilities separate:

1. the client performs transport and captures provenance;
2. the parser understands provider-specific fields and document layout;
3. the mapper produces provider-neutral input records;
4. Rust validates canonical financial types and deterministic calculations;
5. Python builds research datasets and estimators from validated records.

Provider payload types, URLs, and column names must not cross into the domain,
model, or CLI layers. A generic `BaseAdapter`, speculative factory, or manager
class is not justified before there are real interchangeable implementations.

## Recommended sequence

1. Derive the dataset-level holdings snapshot envelope, including effective,
   publication, and ingestion timestamps, from the accepted Rust position
   primitives.
2. Implement CSV/synthetic holdings and security-price adapters first so the
   time-safe join and valuation logic can be tested independently of a website.
3. Implement the TCMB daily XML adapter as the first official keyless market
   reference source.
4. Decide separately whether automated KAP public-document acquisition is
   acceptable or whether NAVLens will support manual files and an optional
   contracted KAP adapter.
5. Select a security-price provider only after its access and redistribution
   constraints are documented.

The first holdings-aware model is not considered fully automated until both a
holdings source and price coverage for its constituent securities pass these
checks.

## Official references

- [SPK investment-fund guide: monthly Portfolio Allocation Reports](https://spk.gov.tr/kurumlar/fonlar/yatirim-fonlari/menkul-kiymet-yatirim-fonlari/tanitim-rehberi)
- [KAP sample monthly Portfolio Allocation Report](https://www.kap.org.tr/tr/Bildirim/1612354)
- [KAP Data Distribution REST service conditions](https://www.kap.org.tr/tr/api/about/content-file/8a019492945fbe080194b26d8bed4873)
- [MKK API Portal registration and test environment](https://www.mkk.com.tr/haberler/mkk-api-portal-yayinda)
- [SPK portfolio values and web-service links](https://spk.gov.tr/kurumlar/fonlar/yatirim-fonlari/borsa-yatirim-fonlari/portfoy-degerleri)
- [SPK OpenAPI service catalogue](https://ws.spk.gov.tr/help/index.html)
- [TCMB daily exchange-rate archive](https://www.tcmb.gov.tr/kurlar/kurlar_tr.html)
- [TCMB indicative-rate publication rules](https://www.tcmb.gov.tr/wps/wcm/connect/TR/TCMB%2BTR/Main%2BMenu/Temel%2BFaaliyetler/Doviz%2BEfektif/Doviz%2Bve%2BEfektif%2BPiyasalari/Gosterge%2BNiteligindeki%2BKurlar)
- [TCMB EVDS web-service guide](https://evds2.tcmb.gov.tr/help/videos/EVDS_Web_Servis_Kullanim_Kilavuzu.pdf)
- [Borsa Istanbul data products](https://borsaistanbul.com/veriler/veri-yayini/veri-yayin-urunleri)
