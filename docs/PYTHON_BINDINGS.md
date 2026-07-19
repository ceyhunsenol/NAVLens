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
.venv/Scripts/python -m pip install -e ".[dev,research]"
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

## Prediction contracts

Python estimators hand their result to the canonical Rust prediction contract:

```python
from navlens import ModelDescriptor, create_return_prediction

model = ModelDescriptor("ridge-baseline", "0.1.0", "market-v1")
prediction = create_return_prediction(
    expected_return=0.0062,
    lower_bound=-0.0041,
    upper_bound=0.0158,
    confidence_level=0.90,
    model=model,
)
```

`MarketDate`, `UtcTimestamp`, and `PredictionRequest` separately represent the
market horizon and auditable UTC data cut-offs. Rust rejects a target that does
not follow the prediction date and data timestamps later than generation time.
The binding performs no duplicate validation.

## Linear baseline research workflow

The optional `research` dependencies provide NumPy, pandas, and scikit-learn.
The first baseline consumes chronological decimal returns that have already
crossed the canonical Rust financial boundary; it does not recalculate returns
from NAV values in Python:

```python
import pandas as pd

from navlens.estimators import predict_next_return
from navlens.training import train_linear_baseline

returns = pd.Series(
    [0.0010, -0.0004, 0.0012, 0.0003, 0.0015],
    index=pd.date_range("2026-01-02", periods=5, freq="B"),
)
artifact = train_linear_baseline(
    returns,
    lookback=2,
    model_version="0.1.0",
    confidence_level=0.80,
)
prediction = predict_next_return(artifact, returns)
```

Each feature row contains only observations preceding its target. The artifact
records its feature-schema version, target definition, training window, model
version, confidence level, and evaluation metrics. Linear-regression training
metrics are reported beside a mean `DummyRegressor` benchmark. Its residual
interval is a transparent baseline for research comparison, not a production
uncertainty guarantee.

## Boundary rules

- PyO3 modules map inputs, outputs, and exceptions only.
- Financial calculations and invariants remain in domain/application crates.
- Public Python types receive checked-in `.pyi` stubs and the `py.typed` marker.
- Python tests exercise the compiled extension rather than reimplementing its
  calculations.
