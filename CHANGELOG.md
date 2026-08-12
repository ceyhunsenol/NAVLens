# Changelog

All notable changes to NAVLens will be documented in this file. The project
follows Semantic Versioning from the first public release.

## [Unreleased]

### Added

- Keyless `navlens-predict-tefas` command that acquires TEFAS unit prices and
  runs the canonical point-in-time next-NAV baseline prediction pipeline.
- Shared baseline model options across CSV and direct TEFAS prediction commands.

## [0.1.0] - 2026-08-12

### Added

- Canonical Rust financial types, calendars, portfolio-return calculations,
  reconciliation metrics, and backtesting boundaries.
- Point-in-time Python datasets and orchestration for holdings, security
  prices, fund unit prices, and FX rates.
- PyO3 bindings that preserve Rust-owned validation and calculation rules.
- Historical prediction, reconciliation, evaluation, formatting, and
  deterministic JSON output.
- Provider-neutral CSV adapters and TEFAS fund-price retrieval commands.
- Cross-platform wheel validation and tag-driven GitHub release automation.

### Known limitations

- Holdings disclosures may lag the fund's current portfolio.
- Intraday portfolio changes cannot be reconstructed from monthly disclosures.
- The implemented prediction model is a research baseline, not investment
  advice or a promise of future returns.

[Unreleased]: https://github.com/ceyhunsenol/NAVLens/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/ceyhunsenol/NAVLens/releases/tag/v0.1.0
