# NAVLens Agent Instructions

These instructions apply to the entire repository.

## Required reading

Before changing code, read and follow:

1. `docs/ARCHITECTURE.md`
2. `docs/CODE_STRUCTURE.md`
3. `CONTRIBUTING.md`

Code that violates a layer boundary or ownership rule must not be introduced,
even when it is functionally correct.

## Code discovery

Before adding a rule, calculation, mapper, port, or provider implementation,
search the repository for its existing owner and callers. Extend the canonical
implementation instead of creating a duplicate or an alternate path around
it. No specific editor, agent, indexer, or external development tool is
required to contribute.

## Quality gates

Rust changes must pass:

```shell
cargo fmt --all -- --check
cargo test --workspace --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
```

Run the relevant Python and TypeScript checks once those workspaces exist.

## Architectural changes

Do not silently change dependency direction, model ownership, persistence
strategy, public contracts, or cross-language boundaries. Create an ADR under
`docs/adr/` and update the architecture contract when the decision is accepted.
