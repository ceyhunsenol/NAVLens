# NAVLens

NAVLens is an open-source research toolkit for producing explainable,
probabilistic estimates of the next published unit-price return of investment
funds.

The project does **not** provide investment advice or promise future returns.
Every estimate must include its data timestamp, model version, uncertainty,
and an evaluation against historical observations.

## Architecture

- **Rust** owns canonical financial types, deterministic calculations,
  validation, calendars, backtesting, production execution, and the planned
  API.
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

The current workspace contains:

- `navlens-core`: portfolio-return estimation and validated domain types.
- `navlens-backtest`: regression and direction-accuracy metrics.
- `navlens-calendar`: deterministic market sessions and next-open-date rules.
- `navlens-prediction`: model-independent prediction and provenance contracts.
- `navlens-application`: transport-independent use-case orchestration.
- `navlens-python`: PyO3 mappings for the installable Python package.
- `navlens-cli`: executable command-line adapter.

Planned components are:

- `navlens-infrastructure`: Rust database and provider implementations behind
  application-owned ports.
- `navlens-api`: Axum transport and composition root.
- A TypeScript web interface consuming versioned API contracts.

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
- [`docs/DATA_SOURCE_FEASIBILITY.md`](docs/DATA_SOURCE_FEASIBILITY.md): verified
  official-source options, access constraints, and the holdings-data roadmap.
- [`docs/TEFAS_DATA_ACCESS.md`](docs/TEFAS_DATA_ACCESS.md): supported TEFAS
  export workflow and automation limits.

## Installation

NAVLens requires Python 3.11 or newer. Starting with v0.1.0, GitHub Releases
provide wheels for Linux x86_64, Windows x86_64, macOS Apple Silicon, and macOS
Intel. Download the wheel matching your platform, then install it locally:

```shell
python -m pip install path/to/downloaded-navlens-wheel.whl
```

Release wheels contain the native Rust extension and install the Python runtime
dependencies automatically. NAVLens is not published to PyPI yet.

For development, clone the repository and install the mixed Python/Rust package
in editable mode:

```shell
python -m pip install -e ".[dev]"
```

Run the Rust test suite with:

```shell
cargo test --workspace
```

## Command-line tools

| Command | Purpose |
| --- | --- |
| `navlens-fetch-tefas` | Acquire and cache TEFAS fund unit prices. |
| `navlens-backtest-tefas` | Backtest one fund from TEFAS prices. |
| `navlens-backtest-batch` | Run isolated backtests for multiple funds. |
| `navlens-align-holdings-csv` | Align holdings with point-in-time security prices. |
| `navlens-return-contribution-csv` | Calculate covered portfolio return contribution. |
| `navlens-fx-return-contribution-csv` | Calculate FX-adjusted return contribution. |
| `navlens-reconcile-fund-csv` | Reconcile contribution with a published fund return. |
| `navlens-fx-reconcile-fund-csv` | Reconcile an FX-adjusted contribution. |
| `navlens-evaluate-historical-reconciliation-csv` | Evaluate historical reconciliation periods. |
| `navlens-evaluate-historical-fx-reconciliation-csv` | Evaluate FX-aware historical reconciliation periods. |
| `navlens-predict-fund-csv` | Produce one point-in-time next-NAV prediction. |
| `navlens-predict-tefas` | Acquire TEFAS prices and produce one next-NAV prediction. |
| `navlens-predict-tefas-batch` | Produce isolated next-NAV predictions for multiple funds. |
| `navlens-evaluate-historical-prediction-csv` | Evaluate historical point-in-time predictions. |

Every command supports `--help`. Detailed arguments, output contracts, and exit
codes are documented in [`docs/CLI.md`](docs/CLI.md).

The public `navlens.__version__` value is read from installed package metadata
and matches the Rust workspace release version. NumPy, pandas, and scikit-learn
are regular package dependencies because the public prediction commands use
the implemented linear baseline at runtime; they are not optional extras.

## Try the historical prediction pipeline

After installing the Python package with `maturin develop`, run the complete
offline example in
[`examples/historical_prediction`](examples/historical_prediction/README.md).
It evaluates two point-in-time predictions, reports Rust-produced aggregate
metrics, and prints the predicted and realized return for each period.

## Data licensing

The MIT license covers NAVLens source code only. It does not grant rights to
third-party market or fund data. Data-source adapters and users remain
responsible for complying with each provider's terms and applicable law.

## License

MIT
