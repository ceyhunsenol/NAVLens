from pathlib import Path

import pytest


@pytest.fixture
def shared_price_csv_path() -> Path:
    return (
        Path(__file__).parents[2]
        / "crates"
        / "navlens-calendar"
        / "tests"
        / "fixtures"
        / "prices.csv"
    )
