use crate::DecimalReturn;

/// One component of a fund portfolio and its observed market return.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PortfolioComponent {
    pub weight: f64,
    pub market_return: DecimalReturn,
}
