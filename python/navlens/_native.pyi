from collections.abc import Sequence

class NavlensValidationError(ValueError): ...

class PortfolioReturnEstimate:
    @property
    def estimated_return_decimal(self) -> float: ...

    @property
    def estimated_return_percent(self) -> float: ...

def estimate_portfolio_return(
    components: Sequence[tuple[float, float]],
    daily_expense_rate: float = ...,
) -> PortfolioReturnEstimate: ...
