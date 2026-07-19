# Python bindings

NAVLens exposes selected Rust application operations through a thin PyO3
adapter. Python code imports the stable `navlens` package; the compiled module is
an internal implementation detail named `navlens._native`.

## Development setup

Create and activate a Python 3.11 or newer virtual environment, then install the
development package:

```text
python -m venv .venv
.venv/Scripts/python -m pip install --upgrade pip
.venv/Scripts/python -m pip install -e ".[dev]"
```

On Unix-like systems, use `.venv/bin/python` instead. Maturin reads
`pyproject.toml`, builds `crates/navlens-python`, and installs the native module
inside the editable package.

Run the Python checks with:

```text
.venv/Scripts/python -m pytest
.venv/Scripts/python -m ruff check python
```

## Public operation

The first binding delegates portfolio-return estimation to
`navlens-application`:

```python
from navlens import estimate_portfolio_return

result = estimate_portfolio_return(
    [(0.7, 0.02), (0.3, -0.01)],
    daily_expense_rate=0.0001,
)

print(result.estimated_return_decimal)
print(result.estimated_return_percent)
```

Each component tuple contains `(portfolio_weight, decimal_market_return)`.
Invalid values raise `NavlensValidationError`, a `ValueError` subclass, while
the financial validation remains implemented only in Rust.

## Boundary rules

- PyO3 modules map inputs, outputs, and exceptions only.
- Financial calculations and invariants remain in domain/application crates.
- Public Python types receive checked-in `.pyi` stubs and the `py.typed` marker.
- Python tests exercise the compiled extension rather than reimplementing its
  calculations.
