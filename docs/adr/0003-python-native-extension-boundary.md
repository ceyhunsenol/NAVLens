# ADR-0003: Python native-extension boundary

- Status: Accepted
- Date: 2026-07-19

## Context

Python will own model research, training, explainability, and visualization,
while Rust remains the canonical owner of financial validation and deterministic
calculations. Calling Rust from Python must not create a second implementation
of application or domain rules.

## Decision

1. PyO3 provides the native binding and maturin builds the Python distribution.
2. The public package is `navlens`; the compiled implementation is the private
   `navlens._native` module.
3. `navlens-python` is an adapter and may depend on application and domain
   crates. Those crates never depend on PyO3 or Python.
4. Binding functions only map Python values, invoke one public Rust operation,
   and map the result or error back to Python.
5. Domain validation failures become `NavlensValidationError`, a Python
   `ValueError` subclass.
6. Python 3.11 is the minimum supported version. Wheels use PyO3's `abi3-py311`
   stable ABI where supported.
7. Checked-in type stubs describe the native API for editors and type checkers.

## Consequences

- Python callers reuse Rust calculations without subprocess overhead or code
  duplication.
- The adapter remains replaceable and contains no model-training logic.
- Building from source requires a Rust toolchain and maturin.
- ABI3 wheels can support multiple compatible CPython versions from one build.

## Alternatives considered

### Embed Python inside the Rust API process

Deferred because interpreter lifecycle, environment isolation, and failure
containment are unnecessary for the first research workflow.

### Duplicate calculations in Python

Rejected because it would create two sources of financial truth.

### Exchange JSON through a subprocess

Still available for isolated workers, but rejected as the primary local research
interface because direct native calls are simpler and faster.
