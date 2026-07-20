# NAVLens

NAVLens is an open-source research toolkit for producing explainable,
probabilistic estimates of the next published unit-price return of investment
funds.

The project does **not** provide investment advice or promise future returns.
Every estimate must include its data timestamp, model version, uncertainty,
and an evaluation against historical observations.

## Architecture

- **Rust** owns canonical financial types, deterministic calculations,
  validation, calendars, backtesting, and the future API/CLI.
- **Python** owns data-source experiments, statistical research, model
  training, explainability, notebooks, and visualisation.
- **TypeScript** will own the web interface and will not duplicate financial
  calculations.

The mandatory layer boundaries, model taxonomy, repository/service rules, and
dependency direction are defined in
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md). Contributors must also follow
the decomposition rules in [`docs/CODE_STRUCTURE.md`](docs/CODE_STRUCTURE.md)
and [`CONTRIBUTING.md`](CONTRIBUTING.md).

## Current milestone

The initial workspace contains:

- `navlens-core`: portfolio-return estimation and validated domain types.
- `navlens-backtest`: regression and direction-accuracy metrics.
- `navlens-calendar`: deterministic market sessions and next-open-date rules.
- `navlens-prediction`: model-independent prediction and provenance contracts.
- `navlens-application`: transport-independent use-case orchestration.
- `navlens-python`: PyO3 mappings for the installable Python package.
- `navlens-cli`: executable command-line adapter.

Focused documentation:

- [`docs/PREDICTION_MODELS.md`](docs/PREDICTION_MODELS.md): implemented model
  cards, planned baselines, limitations, and admission rules.
- [`docs/BACKTESTING.md`](docs/BACKTESTING.md): chronological guarantees,
  metrics, and current leakage-protection limits.
- [`docs/PREDICTIONS.md`](docs/PREDICTIONS.md): point estimates, uncertainty
  intervals, and coverage interpretation.
- [`docs/CLI.md`](docs/CLI.md): executable commands and application flow.
- [`docs/DATA_PIPELINE.md`](docs/DATA_PIPELINE.md): source, normalization, and
  dataset boundaries.
- [`docs/TEFAS_DATA_ACCESS.md`](docs/TEFAS_DATA_ACCESS.md): supported TEFAS
  export workflow and automation limits.

Run the Rust test suite with:

```shell
cargo test --workspace
```

## Data licensing

The MIT license covers NAVLens source code only. It does not grant rights to
third-party market or fund data. Data-source adapters and users remain
responsible for complying with each provider's terms and applicable law.

## License

MIT
