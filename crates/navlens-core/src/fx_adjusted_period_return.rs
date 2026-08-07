use crate::{CoreError, DecimalReturn, GrossReturnComponent};

/// An effective base-currency period return adjusted for foreign exchange movements.
///
/// Composes a security return and an FX return using the canonical formula:
/// `(1 + security_return) * (1 + fx_return) - 1`.
#[derive(Clone, Copy, Debug, PartialEq, PartialOrd)]
pub struct FxAdjustedPeriodReturn(DecimalReturn);

impl FxAdjustedPeriodReturn {
    /// Calculates the FX-adjusted period return from a security return and an FX return.
    ///
    /// Both input returns must be strictly greater than `-1.0` (their gross return factors `1 + r` must be positive).
    ///
    /// # Errors
    /// Returns [`CoreError::NonPositiveGrossReturn`] if either return is less than or equal to `-1.0`.
    /// Returns [`CoreError::NonFiniteNumber`] if the calculation yields a non-finite result.
    pub fn calculate(
        security_return: DecimalReturn,
        fx_return: DecimalReturn,
    ) -> Result<Self, CoreError> {
        if security_return.value() <= -1.0 {
            return Err(CoreError::NonPositiveGrossReturn {
                component: GrossReturnComponent::Security,
                decimal_return: security_return.value(),
            });
        }
        if fx_return.value() <= -1.0 {
            return Err(CoreError::NonPositiveGrossReturn {
                component: GrossReturnComponent::ForeignExchange,
                decimal_return: fx_return.value(),
            });
        }

        let gross_security = 1.0 + security_return.value();
        let gross_fx = 1.0 + fx_return.value();
        let combined = (gross_security * gross_fx) - 1.0;
        let decimal_return = DecimalReturn::new(combined)?;

        Ok(Self(decimal_return))
    }

    /// Returns the underlying calculated decimal return.
    #[must_use]
    pub const fn decimal_return(self) -> DecimalReturn {
        self.0
    }
}
