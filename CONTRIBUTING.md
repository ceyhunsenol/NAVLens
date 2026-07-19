# Contributing to NAVLens

Thank you for improving NAVLens. All contributions are expected to preserve the
architecture contract in [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).
Code decomposition must also follow
[`docs/CODE_STRUCTURE.md`](docs/CODE_STRUCTURE.md).

## Before coding

Identify the owner of the change:

- financial rule or invariant: Rust domain;
- use-case coordination: Rust application;
- persistence or provider integration: infrastructure/adapter;
- statistical experiment or estimator training: Python;
- HTTP representation: API DTO;
- presentation: TypeScript web application.

If ownership is unclear, open an ADR before implementation. Do not solve
uncertainty by placing code in `common`, `utils`, `helpers`, or generic
`models`/`services` modules.

## Required checks

Rust changes must pass:

```shell
cargo fmt --all -- --check
cargo test --workspace
cargo clippy --workspace --all-targets -- -D warnings
```

Python and web checks will be added when those workspaces are introduced.
VS Code users can install the workspace recommendations from
`.vscode/extensions.json`; shared formatting and language-server settings are
defined in `.vscode/settings.json`.

## Pull-request checklist

- [ ] The change has one clearly identified layer owner.
- [ ] Domain, persistence, transport, ML, and view models remain separate.
- [ ] No financial formula is duplicated across languages or layers.
- [ ] Handlers do not access repositories or contain business logic.
- [ ] Repositories do not make business decisions.
- [ ] External/provider types are mapped at the infrastructure boundary.
- [ ] New behavior and bug fixes include tests.
- [ ] Time-series code prevents future-data leakage.
- [ ] New dependencies have a clear layer-specific justification.
- [ ] Public behavior and assumptions are documented.
- [ ] Financial outputs state their units and data timestamp.
- [ ] Files, functions, classes, and implementations remain below the structure
      guardrails or the pull request documents a justified exception.
- [ ] Crate roots and package initializers contain composition/exports, not
      accumulated implementation logic.

## Commit scope

Keep commits focused on one architectural responsibility. Avoid mixing a domain
change, provider integration, API redesign, and UI work in one commit.
