import pytest
from navlens import NavlensValidationError, estimate_portfolio_return


def test_estimates_portfolio_return_through_rust() -> None:
    result = estimate_portfolio_return(
        [(0.7, 0.02), (0.3, -0.01)],
        daily_expense_rate=0.0001,
    )

    assert result.estimated_return_decimal == pytest.approx(0.0109)
    assert result.estimated_return_percent == pytest.approx(1.09)
    assert repr(result) == "PortfolioReturnEstimate(estimated_return_decimal=0.0109)"


def test_maps_domain_failures_to_python_exception() -> None:
    with pytest.raises(NavlensValidationError, match="weights must sum to one"):
        estimate_portfolio_return([(0.8, 0.02), (0.3, -0.01)])
