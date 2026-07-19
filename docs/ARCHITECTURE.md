# NAVLens Architecture Contract

This document defines the mandatory architectural boundaries of NAVLens. Code
that violates these boundaries must not be merged, even when it works.

File, module, function, and class decomposition is governed by
[`CODE_STRUCTURE.md`](CODE_STRUCTURE.md). Both documents are mandatory.

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative.

## Core principles

1. Every concept has one canonical owner.
2. Dependencies point inward, toward domain rules.
3. Domain code is deterministic and independent of infrastructure.
4. Boundaries exchange explicit types, never persistence or framework objects.
5. A layer MUST NOT reimplement, bypass, or silently absorb another layer's job.
6. Shared code is extracted only after a real shared abstraction is identified.
7. Financial correctness is preferred over convenience and premature speed.

## Expected language balance

At medium project maturity, the expected ownership balance is:

| Scope | Rust | Python | TypeScript |
| --- | ---: | ---: | ---: |
| Rust and Python subsystems only | 60–70% | 30–40% | — |
| Entire production source tree | 55–60% | 25–30% | 10–15% |

The central expectation is approximately **65% Rust / 35% Python** when the web
interface is excluded. Rust remains the product's durable domain and execution
spine; Python remains the research, training, and data-science environment.

These percentages are an architectural health indicator, not a line-count quota.
Code MUST NOT be moved, duplicated, or rewritten merely to reach a percentage.
Responsibility ownership always takes precedence. A significant long-term drift
should trigger an architecture review because it may indicate one of these
problems:

- too much financial or application logic has leaked into Python;
- experimental Python code has become production code without a stable boundary;
- Rust has absorbed research workflows better expressed in Python;
- TypeScript has started duplicating application or financial logic.

When reporting the balance, count maintained production and test source files.
Exclude generated code, vendored dependencies, lock files, notebooks used only
for exploration, fixtures, data files, and build output. Report both production-
only and production-plus-test measurements so tests do not hide ownership drift.

## Dependency direction

```text
Web UI ────────► HTTP API ────────► Application ────────► Domain
                       │                    │
                       │                    ▼
                       └──────────► Repository ports
                                             ▲
                                             │
                                      Infrastructure

Python research ─► Python bindings ─► Rust domain/backtest
```

The domain knows nothing about the application, repositories, databases, HTTP,
Python, or the web UI. Infrastructure implements interfaces owned by an inner
layer; inner layers never depend on infrastructure implementations.

## Model taxonomy

The word `model` is ambiguous and MUST be qualified. A generic `models` module
or directory is forbidden.

### Domain models

Examples: `DecimalReturn`, `Portfolio`, `FundCalendar`, `PredictionInterval`.

- Express financial meaning and enforce invariants.
- Live in Rust domain crates such as `navlens-core`.
- MUST NOT contain database, JSON, HTTP, UI, or machine-learning concerns.
- MUST NOT permit invalid states when validation can prevent them.

### Persistence records

Examples: `FundRow`, `PredictionRecord`, `MarketPriceRecord`.

- Represent database storage and query results.
- Live inside an infrastructure persistence module.
- MAY reflect nullable columns and storage-specific identifiers.
- MUST be mapped explicitly to and from domain models.
- MUST NOT escape through application or HTTP boundaries.

### Transport DTOs

Examples: `FundResponse`, `EstimateRequest`, `BacktestResponse`.

- Represent public API input and output.
- Live in the API crate's `dto` modules.
- Own serialization names, API versioning, and validation of wire format.
- MUST be mapped explicitly to application commands/results.
- MUST NOT be used as domain or persistence models.

### Application commands and results

Examples: `EstimateFundReturn`, `EstimateFundResult`.

- Describe a use case without HTTP or database details.
- Live in the application layer.
- Coordinate domain operations through ports.
- MUST NOT contain SQL, HTTP clients, or framework request objects.

### Machine-learning artifacts

Examples: trained estimators, scalers, feature manifests, and model metadata.

- Live under qualified Python modules such as `training`, `estimators`, and
  `artifacts`; never under a generic `models` package.
- MUST declare feature schema version, training-data window, model version,
  target definition, and evaluation metrics.
- MUST NOT redefine canonical financial calculations owned by Rust.

### View models

- Exist only when the web UI needs a representation different from the API DTO.
- MUST remain inside the web application.
- MUST NOT perform canonical financial calculations.

## Layer responsibilities

### Domain

The domain owns:

- financial types and invariants;
- return, fee, risk, and portfolio calculations;
- fund pricing/calendar rules;
- deterministic feature definitions;
- domain errors.

The domain MUST be pure. It MUST NOT read files, query a database, call a
network service, inspect environment variables, log, or know the current time.
Time and external values are passed explicitly.

### Application

The application layer owns use-case orchestration:

- loading required information through repository ports;
- invoking domain operations;
- selecting an estimator through an estimator port;
- defining transaction boundaries;
- returning application results.

Application services MUST NOT contain SQL, parse provider responses, calculate
financial formulas, or return HTTP responses.

### Repository ports

A repository is a persistence abstraction for domain-oriented data access.

- Interfaces are defined by the layer that consumes them.
- Methods use domain/application types, not database records.
- Repositories load and save data; they do not implement business decisions.
- Repositories MUST NOT call application services.
- A provider HTTP client is a gateway/adapter, not a repository, unless it
  implements a persistence-oriented port explicitly.

Bad repository methods:

```text
calculate_best_fund()
predict_tomorrow_return()
send_notification()
```

Good repository methods:

```text
find_fund(fund_id)
load_prices(fund_id, period)
save_prediction(prediction)
```

### Infrastructure

Infrastructure owns PostgreSQL, files, HTTP providers, queues, and system time.
It implements inner-layer ports and maps external representations at the edge.
Provider-specific fields MUST NOT leak into the domain.

### HTTP API

The API owns routing, authentication, wire validation, status codes, and DTO
mapping. A handler MUST perform only these steps:

1. parse and validate transport input;
2. create an application command;
3. invoke one application use case;
4. map its result/error to an HTTP response.

Handlers MUST NOT query repositories directly or perform financial logic.

### Web UI

The UI owns presentation and interaction. It MAY calculate display-only values
such as pixel positions. It MUST NOT reproduce return, fee, risk, calendar, or
prediction calculations.

### Python research

Python owns data-source experiments, dataset construction, statistical
analysis, estimator training, explainability, notebooks, and visualisation.

- Canonical calculations MUST call Rust through bindings or consume Rust
  outputs.
- Notebook code is exploratory and MUST move into a tested Python module before
  production use.
- A trained artifact MUST be reproducible from a versioned configuration.
- Provider adapters output raw or explicitly normalized records; they do not
  train models or make investment decisions.

## Rust workspace boundaries

The intended crates and their allowed roles are:

| Crate | Responsibility | May depend on |
| --- | --- | --- |
| `navlens-core` | Domain types and calculations | standard library, narrowly approved domain crates |
| `navlens-calendar` | Pricing days, business days, settlement | `navlens-core` |
| `navlens-prediction` | Model-independent prediction contracts and provenance | `navlens-core`, `navlens-calendar` |
| `navlens-backtest` | Evaluation engine and metrics | `navlens-core` |
| `navlens-application` | Use cases and ports | domain crates |
| `navlens-infrastructure` | Database/provider implementations | application and domain crates |
| `navlens-python` | PyO3 mapping only | domain/backtest crates |
| `navlens-api` | Axum transport and composition root | application and infrastructure |
| `navlens-cli` | CLI transport and composition root | application and infrastructure |

Sibling domain crates SHOULD NOT depend on each other unless the dependency is
part of their stated responsibility. Cyclic crate dependencies are forbidden.

`navlens-python`, `navlens-api`, and `navlens-cli` are adapters. They MUST NOT
become alternate locations for business logic.

## Service rules

The suffix `Service` is allowed only for an application-level orchestration
object with a clearly named use case. Generic containers such as
`FundService`, `DataService`, and `CommonService` are forbidden.

Prefer names that describe intent:

- `EstimateFundReturn`
- `RunHistoricalBacktest`
- `ImportProviderPrices`

A service MUST NOT become a miscellaneous collection of related functions. If
it coordinates unrelated use cases, split it.

## Mapping rules

- Every boundary crossing has an explicit mapper or conversion implementation.
- Fallible conversion uses `TryFrom`; infallible conversion MAY use `From`.
- Mapping code lives at the outer side of the boundary.
- No reflection-based or untyped dictionary mapping for core financial data.
- Units MUST be encoded in names or types: decimal return versus percentage,
  UTC timestamp versus market date, gross versus net return.

## Errors

- Domain errors describe violated financial/domain rules.
- Application errors describe use-case failures.
- Infrastructure errors retain provider/database context internally.
- API code maps errors to stable public error codes and MUST NOT expose SQL,
  stack traces, credentials, or provider secrets.
- Errors MUST NOT be represented by magic strings or sentinel numeric values.

## Testing boundaries

- Domain calculations require unit tests for success, boundaries, and invalid
  input.
- Every bug fix requires a regression test.
- Application tests use fake port implementations, not a real database.
- Repository implementations require integration tests against their actual
  storage boundary.
- API tests verify DTO mapping and error/status mapping.
- Cross-language bindings require parity tests using identical fixtures.
- Time-series tests MUST preserve chronological order and prevent future-data
  leakage.

## Dependency policy

A new dependency requires a documented reason. Before adding one, verify:

- which layer owns it;
- whether it changes public types;
- licence compatibility with MIT;
- maintenance and security implications;
- whether the standard library or an existing dependency is sufficient.

Domain crates keep dependencies minimal. Framework dependencies belong only in
adapters and infrastructure.

## Architectural change process

A change to dependency direction, layer ownership, public data contracts, model
artifact format, or persistence strategy requires an Architecture Decision
Record under `docs/adr/`. An ADR records context, decision, consequences, and
alternatives. It does not silently rewrite this contract.
