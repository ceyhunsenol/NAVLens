use crate::{CoreError, DecimalReturn, PortfolioComponent, PortfolioWeight};

/// The weighted return contribution of a single portfolio component.
///
/// This represents `weight * market_return` for a single holding.
#[derive(Clone, Copy, Debug, PartialEq)]
pub struct PortfolioComponentContribution {
    weight: PortfolioWeight,
    market_return: DecimalReturn,
    weighted_contribution: DecimalReturn,
}

impl PortfolioComponentContribution {
    /// Calculates the weighted return contribution for a single portfolio component.
    ///
    /// The mathematical formula is `weighted_contribution = weight * market_return`.
    ///
    /// # Errors
    /// Returns [`CoreError::NonFiniteNumber`] if the calculation yields a non-finite float.
    pub fn calculate(component: &PortfolioComponent) -> Result<Self, CoreError> {
        let weighted = component.weight.value() * component.market_return.value();
        let weighted_contribution = DecimalReturn::new(weighted)?;

        Ok(Self {
            weight: component.weight,
            market_return: component.market_return,
            weighted_contribution,
        })
    }

    /// Returns the preserved weight of the component.
    #[must_use]
    pub const fn weight(&self) -> PortfolioWeight {
        self.weight
    }

    /// Returns the market return of the component.
    #[must_use]
    pub const fn market_return(&self) -> DecimalReturn {
        self.market_return
    }

    /// Returns the weighted contribution (`weight * market_return`) of the component.
    #[must_use]
    pub const fn weighted_contribution(&self) -> DecimalReturn {
        self.weighted_contribution
    }
}
