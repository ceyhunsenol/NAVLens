# ADR-0008: Keyless holdings source boundary

- Status: Accepted
- Date: 2026-07-21

## Context

NAVLens needs fund composition data before it can estimate a return from the
fund's underlying instruments. KAP monthly Portfolio Allocation Reports are the
strongest official candidate observed so far. Sample reports from Ak Portfoy,
Deniz Portfoy, and Inveo Portfoy contain a common security table, but the rows
cover materially different assets: domestic and foreign equities, debt
securities, repo, deposits, investment funds, exchange-traded funds, precious
metals, derivatives, cash collateral, and currencies.

KAP's public pages and report attachments are viewable without credentials.
The MKK API Portal offers free registration and a test environment, while the
documented production Data Distribution service requires an agreement, IP
authorization, and an API key. An API key improves notification discovery,
attachment retrieval, and correction tracking; it does not supply the market
prices of the reported instruments.

The project must remain useful without credentials and must not freeze a domain
contract around one provider's PDF columns.

## Decision

1. NAVLens is keyless-first. Price-only research, local holdings import, and
   official TCMB XML workflows must not require a provider credential.
2. Credentialed sources are optional adapter implementations. Their absence
   disables only their advertised acquisition capability and must not break
   unrelated workflows.
3. Automated acquisition from KAP's public website is not accepted by this ADR.
   Initial holdings research uses user-supplied documents or synthetic CSV
   fixtures. A public-site adapter requires a separate access-policy decision.
4. KAP API Portal and a future production KAP adapter may be added without
   changing domain or dataset contracts.
5. Python owns document acquisition experiments, provider-specific parsing,
   provenance, and publication-time-safe dataset construction.
6. Rust owns provider-neutral instrument identity, asset classification,
   portfolio-weight validation, and deterministic portfolio calculations.
7. The canonical holding weight is the share of fund total value, represented
   as a decimal in `0.0..=1.0`. KAP's group percentage and portfolio-value
   percentage are provider fields and must not be silently substituted for it.
8. Every dataset-level holdings snapshot must retain `effective_date`,
   `published_at`, and `ingested_at`. A backtest may use a snapshot only after
   `published_at`.
9. Security and index prices remain a separate source capability. KAP access,
   with or without a key, must not be presented as a market-price feed.

## Consequences

- A contributor can run the core project without creating an external account.
- API credentials improve automation and operational reliability rather than
  changing financial semantics.
- Provider payloads can evolve without changing Rust domain types.
- PDF parsing remains a research adapter concern and may require more than one
  layout implementation.
- A holdings-aware estimate still requires a separate security-price source and
  currency conversion where applicable.
- The first Rust change is intentionally limited to reusable holding-position
  primitives; snapshot persistence and live acquisition are not implied.

## Alternatives considered

### Require the KAP API

Rejected because it would make the open-source project dependent on account
approval and potentially contracted production access.

### Scrape KAP by default

Rejected because public visibility is not an open automation contract, and KAP
directs high-volume access toward its Data Distribution service.

### Model only equities

Rejected because the sampled official reports contain several asset classes,
including mixed exposures within a single fund.

### Treat KAP access as a market-price source

Rejected because holdings disclosure and market pricing are distinct data
capabilities with different providers, timing, and licensing constraints.

