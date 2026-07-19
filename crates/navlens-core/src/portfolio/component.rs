use crate::{DecimalReturn, PortfolioWeight};

/// One component of a fund portfolio and its observed market return.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PortfolioComponent {
    pub weight: PortfolioWeight,
    pub market_return: DecimalReturn,
}
