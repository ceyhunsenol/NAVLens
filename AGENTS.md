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

This project uses the independent `codebase-memory-mcp` knowledge graph.
Prefer graph tools over filesystem text search for code discovery:

1. `search_graph` for symbols and definitions;
2. `trace_path` for callers, callees, and data flow;
3. `get_code_snippet` for exact symbol source;
4. `query_graph` for architectural and complexity queries;
5. `get_architecture` for a high-level view.

Use text search only for literals, configuration, documentation, unsupported
file types, or when the graph is stale or insufficient. Refresh the index after
material structural changes.

Project graph identifier: `C-Users-devex-Documents-NAVLens`.

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
