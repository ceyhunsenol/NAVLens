use navlens_core::DecimalReturn;

#[derive(Clone, Copy, Debug, PartialEq)]
pub struct EstimatePortfolioReturnResult {
    estimated_return: DecimalReturn,
}

impl EstimatePortfolioReturnResult {
    pub(crate) const fn new(estimated_return: DecimalReturn) -> Self {
        Self { estimated_return }
    }

    #[must_use]
    pub const fn estimated_return(self) -> DecimalReturn {
        self.estimated_return
    }
}
